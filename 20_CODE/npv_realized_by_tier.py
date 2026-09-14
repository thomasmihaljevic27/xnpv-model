"""npv_realized_by_tier.py -- does the priced NPV over- or under-shoot what
players actually produced, and does the miss depend on how good they were?

Diagnostic only. Calls the production NPVEngine unchanged; production code
and source hashes are checked at start and finish.

WHAT IS COMPARED
----------------
Every skater contract the spine prices (first season 2018-2025, the same
set contract_npv.py's [3] sweep writes). For each contract season k that has
already been played (season <= 2025, the last season in WAR.csv):

  projected value  = S_k x Value_k              (exactly as npv() prices it)
  realized value   = max((ALPHA + slope x WAR_real) x ceiling_k, league_min)
                     if the player has ANY WAR.csv row that season, else $0

  * WAR_real: that season's WAR.csv total, team halves summed, D20 schedule
    proration applied -- the same construction as the projection's anchor
    lookup, but with NO games filter (a 5-game season produced what it
    produced).
  * "Present" uses the exit hazard's own definition (exit_hazard.py: exit =
    no WAR.csv row of any GP), so S_k and realized presence mean the same
    thing.
  * ceiling_k and the slope are the ones the projection used for that row
    (ex-ante D11 ceiling path, position slope). Only the PRODUCTION forecast
    differs between the two sides, not the price or the cap forecast.
  * Cost is identical on both sides and cancels, so the value error IS the
    error in the contract part of NPV. Differences are discounted at the
    engine's own (1+g)^-k before summing per contract.
  * RFA terminal years are not compared (realized control years depend on
    qualifying decisions); the result covers the contract part only.

Tiers use anchor_war, the trailing 60/40 season-total WAR the valuation
starts from. "Sustained" = both t-1 and t-2 seasons at 3.0+ WAR; the rest of
the 3+ tier reached it on one strong season or a mixed pair.

READ THIS BEFORE QUOTING A NUMBER: the aging curve and the exit-hazard table
are fitted on data that INCLUDE these realized seasons. The check is
therefore in-sample and, if anything, flatters the model.
"""
from pathlib import Path
import json
import os
import time

import numpy as np
import pandas as pd

from contract_npv import NPVEngine, G
from skater_forward_projection import (norm_name, MERGED_WAR_NAMES, ALPHA,
                                       F_WAR_SKATERS)
from aging_bandwidth_test import digest

SCRIPT_VERSION = '1.0'
SEED = 20260913
BOOTSTRAPS = 2000
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
PREFIX = 'npv_realized_by_tier'
LAST_OBS = 2025                      # last season_start present in WAR.csv
TIERS = [(-np.inf, 0, 'below 0'), (0, 1, '0 to 1'), (1, 2, '1 to 2'),
         (2, 3, '2 to 3'), (3, np.inf, '3+')]


def tier_of(a):
    for lo, hi, lab in TIERS:
        if lo <= a < hi:
            return lab


def realized_lookup():
    """(nk, season_start) -> (prorated WAR, GP). Same keys, proration and
    team-half summing as SkaterProjector.__init__, minus the GP>=10 filter."""
    try:
        from skater_value_engine import PRORATION as pr
    except ImportError:
        pr = {2019: 82 / 70, 2020: 82 / 56}
    w = pd.read_csv(F_WAR_SKATERS)
    w['syr'] = w['Season'].str.split('-').str[0].astype(int) + 2000
    w['WAR'] = w['WAR'] * w['syr'].map(pr).fillna(1.0)
    w['nk'] = w['Player'].map(norm_name) + '|' + w['Position']
    w = w[~w['Player'].map(norm_name).isin(MERGED_WAR_NAMES)]
    a = w.groupby(['nk', 'syr'], as_index=False).agg(WAR=('WAR', 'sum'), GP=('GP', 'sum'))
    return {(r.nk, int(r.syr)): (float(r.WAR), int(r.GP)) for r in a.itertuples()}


def boot_ci(df, col, rng):
    """95% interval for the per-season mean of `col`, resampling players."""
    g = df.groupby('player_id')[col].agg(['sum', 'count'])
    s, c = g['sum'].to_numpy(), g['count'].to_numpy()
    idx = rng.integers(0, len(g), (BOOTSTRAPS, len(g)))
    b = s[idx].sum(1) / c[idx].sum(1)
    return np.quantile(b, [.025, .975])


def main():
    t_start = time.time()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in [
        ROOT / '10_SOURCE/WAR.csv', OUT / 'WAR_with_age.csv',
        ROOT / '20_CODE/aging_curve.py', ROOT / '20_CODE/skater_forward_projection.py',
        ROOT / '20_CODE/contract_npv.py', ROOT / '20_CODE/exit_hazard.py']}
    eng = NPVEngine()
    real = realized_lookup()
    # guard: on qualifying seasons the realized lookup must equal the anchor lookup
    for (nk, syr), v in eng.sp.war_lut.items():
        assert abs(real[(nk, syr)][0] - v) < 1e-9, (nk, syr)

    spine = eng.sp.spine
    firsts = spine.sort_values('season_start').groupby('contract_id').head(1)
    firsts = firsts[firsts['season_start'].between(2018, 2025)]
    nk_of = spine.drop_duplicates('player_id').set_index('player_id')['nk'].to_dict()

    rows, priced = [], 0
    for r in firsts.itertuples():
        pid, t0 = int(r.player_id), int(r.season_start)
        d, s = eng.npv(pid, t0)
        if s.get('status') != 'ok':
            continue
        priced += 1
        nk = nk_of[pid]
        w1 = eng.sp.war_lut.get((nk, t0 - 1), np.nan)
        w2 = eng.sp.war_lut.get((nk, t0 - 2), np.nan)
        c = d[d['row_type'] == 'contract']
        for x in c.itertuples():
            season = int(x.season_start)
            if season > LAST_OBS:
                break
            war_r, gp_r = real.get((nk, season), (0.0, 0))
            present = gp_r > 0
            val_r = (max((ALPHA + x.slope_used * war_r) * x.cap_ceiling_exante, x.league_min)
                     if present else 0.0)
            rows.append(dict(contract_id=int(r.contract_id), player_id=pid, full_name=x.full_name,
                             t0=t0, k=int(x.k), season=season, anchor_war=x.anchor_war,
                             tier=tier_of(x.anchor_war), w_t1=w1, w_t2=w2,
                             sustained=bool(w1 >= 3 and w2 >= 3), path=x.path,
                             survival=x.survival, proj_war=x.projected_war,
                             exp_war=x.survival * x.projected_war, real_war=war_r if present else 0.0,
                             present=present, real_gp=gp_r,
                             exp_value=x.survival * x.value_dollars, real_value=val_r,
                             value_error=x.survival * x.value_dollars - val_r,
                             disc=(1 + G) ** (-int(x.k))))
    df = pd.DataFrame(rows)
    df['disc_value_error'] = df.value_error * df.disc
    df['war_error'] = df.exp_war - df.real_war
    df.to_csv(OUT / f'{PREFIX}_seasons.csv', index=False)

    rng = np.random.default_rng(SEED)
    out = []
    def summarise(label, g):
        if g.empty:
            return
        lo, hi = boot_ci(g, 'value_error', rng)
        per_c = g.groupby('contract_id').disc_value_error.sum()
        sv = g[g.present]
        out.append(dict(
            group=label, seasons=len(g), contracts=g.contract_id.nunique(),
            players=g.player_id.nunique(), mean_anchor=g.anchor_war.mean(),
            exp_war=g.exp_war.mean(), real_war=g.real_war.mean(), war_bias=g.war_error.mean(),
            war_bias_if_present=(sv.proj_war - sv.real_war).mean(),
            exp_exit=1 - g.survival.mean(), real_exit=1 - g.present.mean(),
            exp_value_M=g.exp_value.mean() / 1e6, real_value_M=g.real_value.mean() / 1e6,
            value_bias_M=g.value_error.mean() / 1e6, ci_low_M=lo / 1e6, ci_high_M=hi / 1e6,
            pct_of_real=g.value_error.sum() / g.real_value.sum() * 100,
            per_contract_disc_M=per_c.mean() / 1e6, total_disc_M=per_c.sum() / 1e6))
    for kset, kl in [(None, 'all k'), ([0], 'k=0'), ('ge1', 'k>=1')]:
        sub = df if kset is None else (df[df.k == 0] if kset == [0] else df[df.k >= 1])
        summarise(f'ALL | {kl}', sub)
        for _, _, lab in TIERS:
            summarise(f'{lab} | {kl}', sub[sub.tier == lab])
        e = sub[sub.tier == '3+']
        summarise(f'3+ sustained | {kl}', e[e.sustained])
        summarise(f'3+ not sustained | {kl}', e[~e.sustained])
    summ = pd.DataFrame(out)
    summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)

    # biggest over-projected 3+ contracts, for a sanity read
    top = (df[df.tier == '3+'].groupby(['contract_id', 'full_name', 't0'])
           .agg(anchor=('anchor_war', 'first'), seasons=('k', 'size'),
                err_M=('disc_value_error', 'sum')).sort_values('err_M'))
    top['err_M'] /= 1e6
    assert all(digest(ROOT / k if not k.startswith('30_OUTPUT') else ROOT / k) == v
               for k, v in hashes.items()), 'input or production code changed during run'
    run = dict(script_version=SCRIPT_VERSION, contracts_priced=priced, seasons=len(df),
               last_observed_season=LAST_OBS, elapsed_seconds=time.time() - t_start,
               input_hashes=hashes)
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(run, indent=2))
    pd.set_option('display.width', 250)
    print(summ.round(3).to_string(index=False))
    print('\nmost over-projected 3+ contracts ($M, discounted, observed seasons):')
    print(top.tail(8).round(2).to_string())
    print('\nmost under-projected 3+ contracts:')
    print(top.head(8).round(2).to_string())
    print(f'\ncontracts priced {priced}, seasons compared {len(df)}; '
          f'{time.time() - t_start:.0f}s; production files unchanged.')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
