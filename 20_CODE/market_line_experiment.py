"""market_line_experiment.py -- can the market line be made to predict cap
hits better, and is its error tilted by player level?

Test only; no production file changes. The sample is the locked rate sample
(anchor_shrink_test.rate_sample: 2,349 skater contracts starting 2018-2025,
standard-level UFA/RFA signings, prorated 60/40 trailing WAR). Every
specification is fitted with the production estimator (left-censored at the
league minimum, maximum likelihood), generalised to any design matrix.

ROLLING OUT OF SAMPLE: for each signing year y = 2020..2025, fit on contracts
starting 2018..y-1 and predict the year-y signings. Error is mean absolute
error in cap share, shown in $M at the 2025-26 ceiling ($95.5M). Bias by
trailing-WAR tier says whether the line systematically over- or under-prices
a level of player.

SPECIFICATIONS (all include the intercept and the position x WAR slope of the
production line unless noted)
  base      production: WAR, D x WAR
  quad      + WAR^2                     (item 3.2 rejected a bend; re-test)
  age       + age, age^2 at the start season
  ageXwar   + age, age x WAR
  rfa       + RFA indicator            (D7 found no RFA/UFA difference)
  length    + contract length
  single    + one-season-anchor flag
  w1w2      w1, w2 free (and D x each) instead of the 60/40 blend
  rate      per-82 rate blend and games share instead of the total
  shrunk    rolling pull-back of WAR (fit on seasons <= y-1) as the regressor
  kitchen   base + age + age^2 + RFA + length + single
  w1w2+age, w1w2+age+gp   the admissible combinations (no contract terms)
ADMISSIBILITY: length and RFA status describe the contract being priced. A
value line that reads them prices a contract partly off itself, so they are
reported for what they say about the market, not as candidates.
LIMITS: contract-start population only; six test years; no attempt to price
clauses, bonuses or retained salary.
"""
from pathlib import Path
import json
import os
import time

import numpy as np
import pandas as pd
from scipy import optimize, stats

from anchor_shrink_test import rate_sample
from pipeline_experiment import season_table, Features, Rules, CAL_FIRST
from npv_realized_by_tier import realized_lookup, tier_of
from aging_bandwidth_test import digest

SCRIPT_VERSION = '1.0'
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
PREFIX = 'market_line_experiment'
CAP_SHOW = 95.5
TEST_YEARS = list(range(2020, 2026))
TIER_NAMES = ['below 0', '0 to 1', '1 to 2', '2 to 3', '3+']
SPECS = ['base', 'quad', 'age', 'ageXwar', 'rfa', 'length', 'single', 'w1w2', 'rate', 'shrunk', 'kitchen',
         'w1w2+age', 'w1w2+age+gp']
KITCHEN_NAMES = ['const', 'war', 'dxwar', 'age', 'age2', 'rfa', 'length', 'single']


def censored_fit(X, y, lo):
    """Production's left-censored ML on an arbitrary design (intercept in X)."""
    y = y * 100.0; lo = lo * 100.0
    cens = y <= lo + 1e-12; k = X.shape[1]
    def nll(p):
        b, s = p[:k], np.exp(p[k]); mu = X @ b
        ll = np.empty_like(y)
        ll[~cens] = -np.log(s) + stats.norm.logpdf((y[~cens] - mu[~cens]) / s)
        ll[cens] = stats.norm.logcdf((lo[cens] - mu[cens]) / s)
        return 1e10 if not np.all(np.isfinite(ll)) else -ll.sum()
    b0 = np.linalg.lstsq(X, y, rcond=None)[0]
    p0 = np.append(b0, np.log(max(np.std(y - X @ b0), 1e-6)))
    r = optimize.minimize(nll, p0, method='BFGS', options=dict(maxiter=20000, gtol=1e-9))
    if not r.success:
        r2 = optimize.minimize(nll, r.x, method='Nelder-Mead', options=dict(maxiter=50000, xatol=1e-10, fatol=1e-10))
        if r2.fun < r.fun:
            r = r2
    return r.x[:k] / 100.0


def design(spec, d):
    w, isd = d.wWAR.to_numpy(), d.is_d.to_numpy()
    cols = [np.ones(len(d))]
    if spec.startswith('w1w2'):
        cols += [d.w1f, d.w2f, isd * d.w1f, isd * d.w2f, d.single]
        if 'age' in spec:
            cols += [d.age, d.age ** 2]
        if 'gp' in spec:
            cols += [d.gp_b.fillna(d.gp_b.mean())]
    elif spec == 'rate':
        cols += [d.rate_b, isd * d.rate_b, d.gp_b, d.single]
    elif spec == 'shrunk':
        cols += [d.shrunk, isd * d.shrunk]
    else:
        cols += [w, isd * w]
        if spec == 'quad':
            cols += [w ** 2]
        if spec in ('age', 'kitchen'):
            cols += [d.age, d.age ** 2]
        if spec == 'ageXwar':
            cols += [d.age, d.age * w]
        if spec in ('rfa', 'kitchen'):
            cols += [d.rfa]
        if spec in ('length', 'kitchen'):
            cols += [d.length]
        if spec in ('single', 'kitchen'):
            cols += [d.single]
    return np.column_stack([np.asarray(c, float) for c in cols])


def main():
    clock = time.time()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in [ROOT / '20_CODE/skater_value_engine.py']}
    sk = rate_sample()
    bd = pd.to_datetime(sk['birthdate'], errors='coerce')
    ref = pd.to_datetime((sk.start_yr + 1).astype(int).astype(str) + '-02-01')
    sk['age'] = ((ref - bd).dt.days / 365.25).astype(float)
    sk = sk[sk.age.notna()].copy()
    sk['rfa'] = (sk.signing_status.astype(str) == 'RFA').astype(float)
    sk['single'] = (sk.src != 'both').astype(float)
    sk['length'] = sk['length'].astype(float)
    tab = season_table(); feats = Features(tab)
    F = pd.DataFrame([feats.get(nk, int(y)) for nk, y in zip(sk.nk, sk.start_yr)], index=sk.index)
    # The rate sample keeps the two locked merged-name careers (Ryan Johnson,
    # Nathan Smith); the feature table excludes them as the engine does. Drop
    # those rows here and guard that nothing else differs.
    bad = F.anchor.isna() | ((F.anchor - sk.wWAR).abs() > 1e-9)
    assert bad.sum() <= 2, f'{int(bad.sum())} rows differ from the rate sample anchor'
    sk, F = sk[~bad].copy(), F[~bad]
    assert np.allclose(F.anchor, sk.wWAR, atol=1e-9)
    sk['w1f'] = F.w1.fillna(0.0); sk['w2f'] = F.w2.fillna(0.0)
    sk['rate_b'] = F.rate_b; sk['gp_b'] = F.gp_b
    # rolling pull-back, fitted on played seasons <= start_yr - 1
    real = realized_lookup(); rows = []
    for nk in {k for k, _ in tab.index}:
        pos = nk.rsplit('|', 1)[1]
        for t in range(CAL_FIRST, 2026):
            f = feats.get(nk, t)
            r = real.get((nk, t))
            if pd.isna(f['anchor']) or r is None or r[1] <= 0:
                continue
            f.update(t=t, pos=pos, real=r[0]); rows.append(f)
    rules = Rules(pd.DataFrame(rows))
    sk['shrunk'] = [rules.predict(int(y), 'L', f, nk.rsplit('|', 1)[1])
                    for (nk, y), (_, f) in zip(zip(sk.nk, sk.start_yr), F.iterrows())]
    sk['tier'] = sk.wWAR.map(tier_of)

    preds = {}
    for spec in SPECS:
        p = pd.Series(np.nan, index=sk.index)
        for y in TEST_YEARS:
            tr, te = sk[sk.start_yr.between(2018, y - 1)], sk[sk.start_yr == y]
            b = censored_fit(design(spec, tr), tr.cap_pct.to_numpy(), tr.floor_pct.to_numpy())
            p.loc[te.index] = np.maximum(design(spec, te) @ b, te.floor_pct)
        preds[spec] = p
    te = sk[sk.start_yr.isin(TEST_YEARS)]
    base_e = ((preds['base'].loc[te.index] - te.cap_pct) * CAP_SHOW).abs().mean()
    out = []
    for spec in SPECS:
        e = (preds[spec].loc[te.index] - te.cap_pct) * CAP_SHOW
        row = dict(spec=spec, n=len(te), mae_M=e.abs().mean(), bias_M=e.mean(),
                   mae_change_pct=(e.abs().mean() / base_e - 1) * 100)
        for t in TIER_NAMES:
            m = (te.tier == t).to_numpy()
            row[f'bias_{t}'] = e[m].mean(); row[f'mae_{t}'] = e[m].abs().mean()
        out.append(row)
    res = pd.DataFrame(out); res.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)
    b_k = censored_fit(design('kitchen', sk), sk.cap_pct.to_numpy(), sk.floor_pct.to_numpy())
    assert all(digest(ROOT / k) == v for k, v in hashes.items())
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(dict(
        script_version=SCRIPT_VERSION, n=len(sk), test_years=TEST_YEARS, specs=SPECS,
        kitchen_full_sample_coefs=dict(zip(KITCHEN_NAMES, b_k.tolist())),
        tier_counts={str(k): int(v) for k, v in te.tier.value_counts().items()},
        elapsed_seconds=time.time() - clock, input_hashes=hashes), indent=2))
    pd.set_option('display.width', 250)
    print(f'rolling out-of-sample cap-hit prediction, {len(te)} signings 2020-2025 ($M at a $95.5M cap)')
    print(res.round(3).to_string(index=False))
    print('\nkitchen-sink coefficients, full sample (cap share units):',
          {k: round(float(v), 5) for k, v in zip(KITCHEN_NAMES, b_k)})
    print(f'{time.time() - clock:.0f}s; production files unchanged.')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
