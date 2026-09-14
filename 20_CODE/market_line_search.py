"""market_line_search.py -- which combination of features predicts cap hits
best, with contract term allowed in?

Test only; no production file changes. Same sample, estimator and rolling
design as market_line_experiment.py (2,347 signings 2018-2025, left-censored
maximum likelihood, fit on years up to y-1, predict year y).

WHY TERM IS ALLOWED HERE
------------------------
The value line asks what the free-agent market charges for a player of this
quality. Two framings of that alternative exist: replace him with a one-year
deal each remaining season (term-free), or replace him with one deal covering
the remaining term (term enters). Neither is privileged. What term carries is
a mix of the market's price for commitment and the private information teams
have when they commit long, so a line with term moves the term premium from
"mispricing to be measured" into "fair value". That is a design decision for
the back-test, recorded in the report; this script only measures.

SELECTION DISCIPLINE. Forward stepwise selection scores each candidate by
rolling out-of-sample error on the SELECTION years (2020-2022). The chosen
path is then scored, unchanged, on the HELD-OUT years (2023-2025). Selecting
and reporting on the same years would flatter the winner.

FEATURES (all at the signing, from seasons before the start year)
  WAR blocks (one at a time): blend = 60/40 total with D slope [production];
      w1w2 = the two seasons weighted freely; rate = per-82 rate + games
  single    one-season-anchor flag
  age, age2 at the start season
  gp        games share blend
  rfa       RFA at signing
  term, term2, termXwar, ageXterm   contract length in seasons
"""
from pathlib import Path
import itertools
import json
import os
import time

import numpy as np
import pandas as pd

from market_line_experiment import censored_fit
from anchor_shrink_test import rate_sample
from pipeline_experiment import season_table, Features
from npv_realized_by_tier import tier_of
from aging_bandwidth_test import digest

SCRIPT_VERSION = '1.0'
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
PREFIX = 'market_line_search'
CAP_SHOW = 95.5
SELECT_YEARS = [2020, 2021, 2022]
HOLDOUT_YEARS = [2023, 2024, 2025]
TIER_NAMES = ['below 0', '0 to 1', '1 to 2', '2 to 3', '3+']
BLOCKS = {'blend': ['wWAR', 'dxwWAR'], 'w1w2': ['w1f', 'w2f', 'dxw1f', 'dxw2f'], 'rate': ['rate_b', 'dxrate_b', 'gp_b']}
EXTRAS = ['single', 'age', 'age2', 'gp_b', 'rfa', 'term', 'term2', 'termXwar', 'ageXterm']


def build():
    sk = rate_sample()
    bd = pd.to_datetime(sk['birthdate'], errors='coerce')
    ref = pd.to_datetime((sk.start_yr + 1).astype(int).astype(str) + '-02-01')
    sk['age'] = ((ref - bd).dt.days / 365.25).astype(float)
    sk = sk[sk.age.notna()].copy()
    feats = Features(season_table())
    F = pd.DataFrame([feats.get(nk, int(y)) for nk, y in zip(sk.nk, sk.start_yr)], index=sk.index)
    bad = F.anchor.isna() | ((F.anchor - sk.wWAR).abs() > 1e-9)
    assert bad.sum() <= 2, int(bad.sum())
    sk, F = sk[~bad].copy(), F[~bad]
    sk['w1f'] = F.w1.fillna(0.0).to_numpy(); sk['w2f'] = F.w2.fillna(0.0).to_numpy()
    sk['rate_b'] = F.rate_b.to_numpy(); sk['gp_b'] = F.gp_b.fillna(F.gp_b.mean()).to_numpy()
    for c in ['wWAR', 'w1f', 'w2f', 'rate_b']:
        sk['dx' + c] = sk.is_d * sk[c]
    sk['single'] = (sk.src != 'both').astype(float)
    sk['age2'] = sk.age ** 2
    sk['rfa'] = (sk.signing_status.astype(str) == 'RFA').astype(float)
    sk['term'] = sk['length'].astype(float); sk['term2'] = sk.term ** 2
    sk['termXwar'] = sk.term * sk.wWAR; sk['ageXterm'] = sk.age * sk.term
    sk['tier'] = sk.wWAR.map(tier_of)
    return sk


def rolling_error(sk, cols, years):
    """Mean absolute error ($M at $95.5M cap) of rolling out-of-sample
    predictions over `years`; also returns the per-row errors."""
    errs = pd.Series(np.nan, index=sk.index)
    for y in years:
        tr, te = sk[sk.start_yr.between(2018, y - 1)], sk[sk.start_yr == y]
        X = np.column_stack([np.ones(len(tr))] + [tr[c].to_numpy(float) for c in cols])
        b = censored_fit(X, tr.cap_pct.to_numpy(), tr.floor_pct.to_numpy())
        Xt = np.column_stack([np.ones(len(te))] + [te[c].to_numpy(float) for c in cols])
        errs.loc[te.index] = (np.maximum(Xt @ b, te.floor_pct) - te.cap_pct) * CAP_SHOW
    e = errs.dropna()
    return float(e.abs().mean()), errs


def stepwise(sk, block, allow_term):
    cands = [c for c in EXTRAS if allow_term or not c.startswith('term') and c != 'ageXterm']
    cands = [c for c in cands if c not in BLOCKS[block]]
    chosen = list(BLOCKS[block]); path = []
    best, _ = rolling_error(sk, chosen, SELECT_YEARS)
    hold, _ = rolling_error(sk, chosen, HOLDOUT_YEARS)
    path.append(dict(step=0, added='(block)', features=list(chosen), select_mae=best, holdout_mae=hold))
    while cands:
        trial = {c: rolling_error(sk, chosen + [c], SELECT_YEARS)[0] for c in cands}
        c, m = min(trial.items(), key=lambda kv: kv[1])
        if m >= best - 0.002:                       # stop when the gain is under $2k
            break
        chosen.append(c); cands.remove(c); best = m
        hold, _ = rolling_error(sk, chosen, HOLDOUT_YEARS)
        path.append(dict(step=len(path), added=c, features=list(chosen), select_mae=m, holdout_mae=hold))
    return chosen, path


def main():
    clock = time.time()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in [ROOT / '20_CODE/skater_value_engine.py']}
    sk = build()
    hold = sk[sk.start_yr.isin(HOLDOUT_YEARS)]
    results, paths = [], {}
    for block in BLOCKS:
        for allow_term in (False, True):
            label = f'{block}{"+term" if allow_term else ""}'
            chosen, path = stepwise(sk, block, allow_term)
            paths[label] = path
            mae, errs = rolling_error(sk, chosen, HOLDOUT_YEARS)
            e = errs.loc[hold.index]
            row = dict(search=label, features=' + '.join(chosen), n_features=len(chosen),
                       select_mae=path[-1]['select_mae'], holdout_mae=mae, holdout_bias=e.mean())
            for t in TIER_NAMES:
                m = (hold.tier == t).to_numpy(); row[f'bias_{t}'] = e[m].mean(); row[f'mae_{t}'] = e[m].abs().mean()
            results.append(row)
            print(f'{label}: ' + ' -> '.join(f"{p['added']} ({p['select_mae']:.3f}/{p['holdout_mae']:.3f})" for p in path), flush=True)
    base_mae, be = rolling_error(sk, BLOCKS['blend'], HOLDOUT_YEARS)
    be = be.loc[hold.index]
    row = dict(search='production', features='wWAR + dxwWAR', n_features=2, select_mae=rolling_error(sk, BLOCKS['blend'], SELECT_YEARS)[0],
               holdout_mae=base_mae, holdout_bias=be.mean())
    for t in TIER_NAMES:
        m = (hold.tier == t).to_numpy(); row[f'bias_{t}'] = be[m].mean(); row[f'mae_{t}'] = be[m].abs().mean()
    res = pd.DataFrame([row] + results)
    res['holdout_change_pct'] = (res.holdout_mae / base_mae - 1) * 100
    res.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)
    # full-sample coefficients of the best term-free and best with-term specs, in $M
    coefs = {}
    for label in [res.sort_values('holdout_mae').search.iloc[0]] + [r['search'] for r in results]:
        cols = [c for c in res.set_index('search').loc[label, 'features'].split(' + ')]
        X = np.column_stack([np.ones(len(sk))] + [sk[c].to_numpy(float) for c in cols])
        b = censored_fit(X, sk.cap_pct.to_numpy(), sk.floor_pct.to_numpy())
        coefs[label] = dict(zip(['const'] + cols, [round(float(v) * CAP_SHOW, 4) for v in b]))
    assert all(digest(ROOT / k) == v for k, v in hashes.items())
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(dict(script_version=SCRIPT_VERSION, n=len(sk),
        select_years=SELECT_YEARS, holdout_years=HOLDOUT_YEARS, paths=paths, coefficients_M=coefs,
        holdout_tier_counts={str(k): int(v) for k, v in hold.tier.value_counts().items()},
        elapsed_seconds=time.time() - clock, input_hashes=hashes), indent=2, default=str))
    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 40)
    print(f'\nheld-out 2023-2025 signings ({len(hold)}), $M at a $95.5M cap')
    print(res[['search', 'n_features', 'select_mae', 'holdout_mae', 'holdout_change_pct', 'holdout_bias'] +
              [f'bias_{t}' for t in TIER_NAMES] + [f'mae_{t}' for t in TIER_NAMES]].round(3).to_string(index=False))
    for k, v in coefs.items():
        print(f'\n{k}: ' + ', '.join(f'{a} {b:+.3f}' for a, b in v.items()))
    print(f'\n{time.time() - clock:.0f}s; production files unchanged.')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
