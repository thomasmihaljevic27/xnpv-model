"""anchor_shrink_test.py -- would pulling the valuation's starting point toward
typical (fix A), and also refitting the market line on that pulled-back WAR
(fix A+B), give NPVs closer to what players went on to produce?

Test only. Production files are never edited; the engine is patched on its
INSTANCE (anchor), on module globals (the price line) and on the aging
curve's module-level LAMBDA inside this process, restored at the end, and
every production/source hash is checked at start and finish.

THE FIXES
---------
A  Starting point. Production feeds the raw 60/40 trailing WAR (anchor) into
   the price line and the aging ratios. A replaces it with the expected WAR
   given that anchor:  anchor' = a + b x anchor,  where a, b come from an OLS
   of realized season WAR on the production anchor over seasons 2009-2017
   (players who played that season; exit is the hazard's job), fitted
   separately by position (F/D) and by anchor source (two seasons vs one).
   Calibration ends before the first contract valued here (2018), so A is
   out of sample for every contract scored.
A2 A, plus the aging curve's kept share set to 1 (aging_curve.LAMBDA) for the
   ratio path only. The curve's pull toward comparables enters the valuation
   solely through the ratio's denominator, where it steepens the percentage
   decline of above-average players (Aging_Comparable_Limit_Test.md, Part 1).
   With the starting point already shrunk, that is a second pull-back. A2
   shrinks once and lets the curve supply ageing only.
B  Market line. The locked rate is a left-censored fit of cap share at
   signing on the raw anchor (skater_value_engine, n = 2,349 contracts
   starting 2018-2025, common intercept, position slope). B refits the same
   model, same sample, same function, on anchor' instead. It only makes sense
   together with A (a line in units of expected wins applied to expected
   wins), so B is not run alone.

WHAT "BETTER" MEANS HERE
------------------------
1. Contract seasons already played (<= 2025-26): priced value (survival x
   projected value) against realized value, priced with the SAME line as the
   variant ($0 on exit; construction as npv_realized_by_tier.py). The WAR
   columns are line-free and are the cleanest comparison across variants;
   AB's dollar errors are on a different price per win and are not directly
   comparable with the others.
2. The tilt: slope of that error on the RAW starting level (0 = no tilt).
3. The market line's own job: predicting cap hits of 2022-2025 signings from
   a line fitted on 2018-2021 signings, raw vs shrunk regressor.
4. NPV movement against production, by tier.

LIMITS: the aging curve and exit table were fitted on data that include the
scored seasons (same for every variant). Contract seasons only in the
realized comparison; RFA control years move in NPV but are not scored.
v1.1 adds A2; v1.0 ran prod / A / AB only (same seed, same results for those).
"""
from pathlib import Path
import json
import os
import time

import numpy as np
import pandas as pd

import aging_curve as ac
import skater_forward_projection as sfp
import rfa_terminal_value as rtv
import contract_npv as cnpv
from contract_npv import NPVEngine, G
from skater_value_engine import (build_skater_war_lookup, trailing_weighted_war,
                                 _fit_censored_interaction, NEW_LOCKED,
                                 TOL_NEW_COEF, TOL_NEW_N, F_CONTRACT_XLSX,
                                 CAP_CEILING as SVE_CAP,
                                 LEAGUE_MIN_SALARY as SVE_MIN,
                                 POSGRP as SVE_POSGRP, norm_name as sve_norm)
from npv_realized_by_tier import realized_lookup, tier_of, TIERS, LAST_OBS
from aging_bandwidth_test import digest

SCRIPT_VERSION = '1.1'
SEED = 20260913
BOOTSTRAPS = 2000
CAL_FIRST, CAL_LAST = 2009, 2017     # shrink calibration seasons (pre-2018)
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
PREFIX = 'anchor_shrink_test'
VARS = ['prod', 'A', 'A2', 'AB']
NAMED = ['Connor McDavid', 'Auston Matthews', 'Nathan MacKinnon', 'Cale Makar',
         'Leon Draisaitl', 'Nikita Kucherov', 'David Pastrnak', 'Johnny Gaudreau',
         'Artemi Panarin', 'Quinn Hughes', 'Mitch Marner', 'Aleksander Barkov']


def src_group(src):
    return 'both' if src == 'both' else 'single'


def calibrate(sp, real):
    """OLS of realized WAR_t on the production anchor at t, 2009-2017."""
    rows = []
    for nk in sorted({k for k, _ in sp.war_lut.index}):
        for t in range(CAL_FIRST, CAL_LAST + 1):
            a, src = sp.anchor(nk, t)                 # production rule, unpatched
            if pd.isna(a):
                continue
            r = real.get((nk, t))
            if r is None or r[1] <= 0:                # did not play: hazard's job
                continue
            rows.append((nk.rsplit('|', 1)[1], src_group(src), a, r[0]))
    cal = pd.DataFrame(rows, columns=['pos', 'grp', 'anchor', 'real'])
    coef = {}
    for (pos, grp), g in cal.groupby(['pos', 'grp']):
        b, a = np.polyfit(g.anchor, g.real, 1)
        coef[(pos, grp)] = dict(a=float(a), b=float(b), n=len(g),
                                target=float(a / (1 - b)) if b < 1 else None)
    return coef, cal


def shrink(nk, a, src, coef):
    c = coef[(nk.rsplit('|', 1)[1], src_group(src))]
    return c['a'] + c['b'] * a


def rate_sample():
    """The locked n=2,349 market sample, built as skater_value_engine.stage0()."""
    raw = pd.read_excel(F_CONTRACT_XLSX)
    raw['end_yr'] = pd.to_numeric(raw['contract_end'].astype(str).str.extract(r'^(\d{4})')[0],
                                  errors='coerce')
    raw['start_yr'] = raw['end_yr'] - raw['length'] + 1
    raw['posgrp'] = raw['position'].map(SVE_POSGRP)
    raw['nk'] = ((raw['first_name'].astype(str) + ' ' + raw['last_name'].astype(str))
                 .map(sve_norm) + '|' + raw['posgrp'].astype(str))
    raw['cap_pct'] = raw['aav'] / raw['start_yr'].map(SVE_CAP)
    ss = raw['signing_status'].astype(str)
    sk = raw[raw['start_yr'].between(2018, 2025) & (raw['contract_level'] == 'standard_level')
             & ss.isin(['UFA', 'RFA']) & (raw['posgrp'] != 'G') & raw['cap_pct'].notna()].copy()
    lut = build_skater_war_lookup(exclude_merged=False, prorate=True)
    res = [trailing_weighted_war(k, y, lut) for k, y in zip(sk['nk'], sk['start_yr'])]
    sk['wWAR'] = [r[0] for r in res]
    sk['src'] = [r[1] for r in res]
    sk = sk[sk['wWAR'].notna()].copy()
    sk['is_d'] = (sk['posgrp'] == 'D').astype(float)
    sk['floor_pct'] = sk['start_yr'].map(SVE_MIN) / sk['start_yr'].map(SVE_CAP)
    return sk


def fit(sk, col):
    f = _fit_censored_interaction(sk['cap_pct'].values, sk[col].values,
                                  sk['is_d'].values, sk['floor_pct'].values)
    assert f['converged'], f
    return f


def line_pred(f, war, is_d, floor):
    return np.maximum(f['alpha'] + (f['beta'] + f['beta_d_add'] * is_d) * war, floor)


def set_line(alpha, bF, bD):
    """Point every module that prices skater WAR at one line."""
    sfp.ALPHA, sfp.BETA, sfp.BETA_D = alpha, bF, bD
    rtv.ALPHA, rtv.BETA_F, rtv.BETA_D = alpha, bF, bD
    cnpv.ALPHA, cnpv.BETA = alpha, bF


def boot_delta(m, e0, e1, rng):
    """95% interval for the change in per-season MAE, resampling players."""
    d = pd.DataFrame({'p': m['player_id'], 'e': m[e1].abs() - m[e0].abs()})
    g = d.groupby('p')['e'].agg(['sum', 'count'])
    s, c = g['sum'].to_numpy(), g['count'].to_numpy()
    idx = rng.integers(0, len(g), (BOOTSTRAPS, len(g)))
    return np.quantile(s[idx].sum(1) / c[idx].sum(1), [.025, .975])


def main():
    t0_clock = time.time()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in [
        ROOT / '10_SOURCE/WAR.csv', OUT / 'WAR_with_age.csv',
        ROOT / '20_CODE/aging_curve.py', ROOT / '20_CODE/skater_forward_projection.py',
        ROOT / '20_CODE/contract_npv.py', ROOT / '20_CODE/exit_hazard.py',
        ROOT / '20_CODE/rfa_terminal_value.py', ROOT / '20_CODE/skater_value_engine.py']}
    eng = NPVEngine()
    real = realized_lookup()
    prod_line = (sfp.ALPHA, sfp.BETA, sfp.BETA_D)
    prod_lambda = ac.LAMBDA
    assert (rtv.ALPHA, rtv.BETA_F, rtv.BETA_D) == prod_line, 'modules disagree on the line'

    # ---- 1. calibrate fix A on 2009-2017 ------------------------------------
    coef, cal = calibrate(eng.sp, real)
    print('shrink calibration (realized WAR = a + b x anchor), 2009-2017:')
    for k, c in coef.items():
        print(f'  {k}: a={c["a"]:+.3f}  b={c["b"]:.3f}  n={c["n"]}  pulls toward {c["target"]:+.2f}')

    # ---- 2. market line: guard, refit on shrunk WAR, out-of-sample check -----
    sk = rate_sample()
    f_raw = fit(sk, 'wWAR')
    assert abs(len(sk) - NEW_LOCKED['n']) <= TOL_NEW_N, len(sk)
    for key in ['alpha', 'beta', 'beta_d_add']:
        assert abs(f_raw[key] - NEW_LOCKED[key]) <= TOL_NEW_COEF, (key, f_raw[key])
    sk['wWAR_s'] = [shrink(k, a, s, coef) for k, a, s in zip(sk['nk'], sk['wWAR'], sk['src'])]
    f_s = fit(sk, 'wWAR_s')
    same = np.abs(line_pred(f_raw, sk.wWAR, sk.is_d, sk.floor_pct)
                  - line_pred(f_s, sk.wWAR_s, sk.is_d, sk.floor_pct))
    tr, te = sk[sk.start_yr <= 2021], sk[sk.start_yr >= 2022]
    oos = {}
    for col in ['wWAR', 'wWAR_s']:
        f = fit(tr, col)
        p = line_pred(f, te[col], te.is_d, te.floor_pct)
        oos[col] = dict(mae_cap_pct=float(np.mean(np.abs(p - te.cap_pct))),
                        bias_cap_pct=float(np.mean(p - te.cap_pct)))
    rate = dict(n=len(sk), raw=f_raw, shrunk=f_s,
                fitted_price_gap_mean_cap_pct=float(same.mean()),
                fitted_price_gap_max_cap_pct=float(same.max()),
                oos_2022_2025=oos, n_train=len(tr), n_test=len(te))
    print(f"\nmarket line, raw:    alpha {f_raw['alpha']:.5f}  beta_F {f_raw['beta']:.5f}  "
          f"beta_D {f_raw['beta'] + f_raw['beta_d_add']:.5f}")
    print(f"market line, shrunk: alpha {f_s['alpha']:.5f}  beta_F {f_s['beta']:.5f}  "
          f"beta_D {f_s['beta'] + f_s['beta_d_add']:.5f}")
    print(f"fitted price, raw line on raw WAR vs shrunk line on shrunk WAR: mean gap "
          f"{same.mean() * 95.5:.3f}M, max {same.max() * 95.5:.3f}M (at a $95.5M cap)")
    for col, r in oos.items():
        print(f"  out of sample (fit 2018-21, predict 2022-25 signings), {col}: "
              f"MAE ${r['mae_cap_pct'] * 95.5:.3f}M  bias ${r['bias_cap_pct'] * 95.5:+.3f}M")
    line_B = (f_s['alpha'], f_s['beta'], f_s['beta'] + f_s['beta_d_add'])

    # ---- 3. the NPV runs ------------------------------------------------------
    spine = eng.sp.spine
    firsts = spine.sort_values('season_start').groupby('contract_id').head(1)
    firsts = firsts[firsts['season_start'].between(2018, 2025)]
    nk_of = spine.drop_duplicates('player_id').set_index('player_id')['nk'].to_dict()
    orig_anchor = eng.sp.anchor

    def shrunk_anchor(nk, t0):
        a, src = orig_anchor(nk, t0)
        return (a, src) if pd.isna(a) else (shrink(nk, a, src, coef), src)

    #            name  shrink start  price line  curve kept share
    variants = [('prod', False, prod_line, prod_lambda),
                ('A', True, prod_line, prod_lambda),
                ('A2', True, prod_line, 1.0),
                ('AB', True, line_B, prod_lambda)]
    seasons, contracts = [], []
    try:
        for name, use_shrink, line, lam in variants:
            set_line(*line)
            ac.LAMBDA = lam
            eng.sp.anchor = shrunk_anchor if use_shrink else orig_anchor
            alpha, bF, bD = line
            for r in firsts.itertuples():
                pid, t0 = int(r.player_id), int(r.season_start)
                d, s = eng.npv(pid, t0)
                if s.get('status') != 'ok':
                    continue
                nk = nk_of[pid]
                raw_a, _ = orig_anchor(nk, t0)
                contracts.append(dict(variant=name, contract_id=int(r.contract_id), player_id=pid,
                                      full_name=s['full_name'], t0=t0, raw_anchor=raw_a,
                                      tier=tier_of(raw_a), npv_total=s['npv_total'],
                                      npv_contract=s['npv_contract'], npv_terminal=s['npv_terminal']))
                c = d[d['row_type'] == 'contract']
                for x in c.itertuples():
                    season = int(x.season_start)
                    if season > LAST_OBS:
                        break
                    if x.k == 0 and name != 'prod':
                        # guard: the patched line and start reached the pricing
                        assert abs(x.value_point_estimate - max((alpha + x.slope_used * x.projected_war)
                                                                * x.cap_ceiling_exante, x.league_min)) < 1e-6
                    war_r, gp_r = real.get((nk, season), (0.0, 0))
                    slope = bD if x.posgrp == 'D' else bF
                    val_r = (max((alpha + slope * war_r) * x.cap_ceiling_exante, x.league_min)
                             if gp_r > 0 else 0.0)
                    seasons.append(dict(variant=name, contract_id=int(r.contract_id), player_id=pid,
                                        k=int(x.k), tier=tier_of(raw_a), raw_anchor=raw_a,
                                        exp_war=x.survival * x.projected_war,
                                        real_war=war_r if gp_r > 0 else 0.0,
                                        exp_value=x.survival * x.value_dollars, real_value=val_r,
                                        err=x.survival * x.value_dollars - val_r,
                                        disc=(1 + G) ** (-int(x.k))))
            print(f'{name}: {sum(1 for c in contracts if c["variant"] == name)} contracts '
                  f'({time.time() - t0_clock:.0f}s)', flush=True)
    finally:
        set_line(*prod_line)
        ac.LAMBDA = prod_lambda
        eng.sp.anchor = orig_anchor

    S = pd.DataFrame(seasons)
    C = pd.DataFrame(contracts)
    S.to_csv(OUT / f'{PREFIX}_seasons.csv', index=False)
    C.to_csv(OUT / f'{PREFIX}_contracts.csv', index=False)

    # ---- 4. scoring ----------------------------------------------------------
    W = S.pivot_table(index=['contract_id', 'k', 'player_id', 'tier', 'raw_anchor'],
                      columns='variant', values=['err', 'real_value', 'exp_war', 'real_war', 'disc'])
    W.columns = [f'{a}_{b}' for a, b in W.columns]
    W = W.reset_index()
    assert W.notna().all().all(), 'variants did not score the same contract seasons'
    rng = np.random.default_rng(SEED)
    out = []
    for lab, g in [('all', W)] + [(t, W[W.tier == t]) for _, _, t in TIERS] + \
                  [('k=0', W[W.k == 0]), ('k>=1', W[W.k >= 1]),
                   ('3+ k=0', W[(W.tier == '3+') & (W.k == 0)]),
                   ('3+ k>=1', W[(W.tier == '3+') & (W.k >= 1)])]:
        for v in VARS:
            e = g[f'err_{v}']
            pc = (g[f'err_{v}'] * g[f'disc_{v}']).groupby(g.contract_id).sum()
            row = dict(group=lab, variant=v, seasons=len(g), players=g.player_id.nunique(),
                       bias_M=e.mean() / 1e6, mae_M=e.abs().mean() / 1e6,
                       rmse_M=np.sqrt((e ** 2).mean()) / 1e6,
                       mae_pct_of_real=e.abs().sum() / g[f'real_value_{v}'].sum() * 100,
                       bias_pct_of_real=e.sum() / g[f'real_value_{v}'].sum() * 100,
                       war_bias=(g[f'exp_war_{v}'] - g[f'real_war_{v}']).mean(),
                       war_mae=(g[f'exp_war_{v}'] - g[f'real_war_{v}']).abs().mean(),
                       contract_mae_M=pc.abs().mean() / 1e6,
                       tilt_M_per_war=np.polyfit(g.raw_anchor, e, 1)[0] / 1e6 if len(g) > 2 else np.nan)
            if v != 'prod':
                lo, hi = boot_delta(g, 'err_prod', f'err_{v}', rng)
                row.update(mae_change_M=(e.abs().mean() - g.err_prod.abs().mean()) / 1e6,
                           ci_low_M=lo / 1e6, ci_high_M=hi / 1e6)
            out.append(row)
    summ = pd.DataFrame(out)
    summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)

    P = C.pivot_table(index=['contract_id', 'full_name', 't0', 'tier', 'raw_anchor'],
                      columns='variant', values='npv_total').reset_index()
    agg = dict(contracts=('prod', 'size'), prod_mean_M=('prod', lambda x: x.mean() / 1e6))
    for v in VARS[1:]:
        P[f'{v}_minus_prod_M'] = (P[v] - P['prod']) / 1e6
        agg[f'{v}_change_mean_M'] = (f'{v}_minus_prod_M', 'mean')
        agg[f'{v}_change_total_M'] = (f'{v}_minus_prod_M', 'sum')
    mv = P.groupby('tier').agg(**agg)
    mv.to_csv(OUT / f'{PREFIX}_npv_movement.csv')
    named = P[P.full_name.isin(NAMED)].sort_values(['full_name', 't0'])
    named = named.assign(**{f'{v}_M': named[v] / 1e6 for v in VARS})

    assert all(digest(ROOT / k) == v for k, v in hashes.items()), \
        'input or production code changed during run'
    run = dict(script_version=SCRIPT_VERSION, seed=SEED, calibration_seasons=[CAL_FIRST, CAL_LAST],
               shrink={f'{p}|{g}': c for (p, g), c in coef.items()}, market_line=rate,
               contract_seasons_scored=len(W), contracts=int(P.shape[0]),
               elapsed_seconds=time.time() - t0_clock, input_hashes=hashes)
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(run, indent=2, default=float))

    pd.set_option('display.width', 250)
    cols = ['group', 'variant', 'seasons', 'bias_M', 'mae_M', 'bias_pct_of_real', 'mae_pct_of_real',
            'war_bias', 'war_mae', 'contract_mae_M', 'tilt_M_per_war', 'mae_change_M', 'ci_low_M', 'ci_high_M']
    print('\n' + summ[cols].round(3).to_string(index=False))
    print('\nNPV movement by tier (contracts valued 2018-2025):')
    print(mv.round(2).to_string())
    print('\nnamed contracts, NPV total ($M):')
    print(named[['full_name', 't0', 'raw_anchor'] + [f'{v}_M' for v in VARS]].round(2).to_string(index=False))
    print(f'\n{time.time() - t0_clock:.0f}s; production files unchanged.')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
