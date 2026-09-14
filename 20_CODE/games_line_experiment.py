"""games_line_experiment.py -- price availability and term, not only wins.

Test only; nothing in production changes (engine patched in-process, hashes
checked). Companion to pipeline_experiment.py and market_line_search.py.

WHY
---
market_line_experiment.py found that a cap-hit line with the player's games
share predicts signings 17% better out of sample than the production line,
and that once games are in, the price per win falls from about $2.0M to about
$0.8M. market_line_search.py adds contract term. This script asks what those
lines do inside the NPV chain, against a production line refitted the same
rolling way, so the comparison is line against line and not in-sample
against out-of-sample.

THE LINES (all fitted rolling on signings 2018..t0-1 with the production
censored estimator; for the 2018 and 2019 pages the fit uses 2018-2019
signings and is in sample, so those pages are reported separately)
  prod       the locked production line, fitted once on 2018-2025 (reference)
  prod_roll  the production specification, refitted rolling
  G          + games share
  GT         + games share + term
For the chain, "term" is the number of seasons left on the contract at the
valuation (the length of the replacement deal under the remaining-term
framing); in the fitting sample it is the contract length at signing. Term
is the same on the projected and realised sides of a season, so it changes
the level of value (and so surplus) but cancels out of the error except
through the other coefficients it changes.

PROJECTED GAMES SHARE per season: a rolling rule fitted on 2009..t0-1,
games_share_t = a + b x games-share blend, by position and source, held flat.

SCORING: each played contract season, S_k x line(WAR_k, games_k, term)
against line(WAR_real, games_real, term), $0 on exit -- the same line on both
sides, so each variant is on its own currency. Comparable across variants:
WAR error (line-free), bias as a share of realised value, error as a share of
realised value, and the tilt on the starting level. Anchors: production, and
the rolling L pull-back.
v1.1: prod_roll and GT added; the 2018-19 pages split out.
"""
from pathlib import Path
import json
import os
import time

import numpy as np
import pandas as pd

import skater_forward_projection as sfp
from contract_npv import NPVEngine, G
from npv_realized_by_tier import realized_lookup, tier_of, TIERS, LAST_OBS
from pipeline_experiment import season_table, Features, Rules, ols, pred, CAL_FIRST
from market_line_experiment import censored_fit
from anchor_shrink_test import rate_sample
from aging_bandwidth_test import digest

SCRIPT_VERSION = '1.1'
SEED = 20260914
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
PREFIX = 'games_line_experiment'
LINES = {'prod': None, 'prod_roll': [], 'G': ['gp_b'], 'GT': ['gp_b', 'term']}
ANCHORS = ['prod', 'L']
CAP_SHOW = 95.5


def fit_line(tr, extras):
    X = np.column_stack([np.ones(len(tr)), tr.wWAR, tr.is_d * tr.wWAR] + [tr[c].to_numpy(float) for c in extras])
    b = censored_fit(X, tr.cap_pct.to_numpy(), tr.floor_pct.to_numpy())
    return dict(c=float(b[0]), bF=float(b[1]), bD=float(b[1] + b[2]),
                extra=dict(zip(extras, [float(x) for x in b[3:]])), n=len(tr))


def main():
    clock = time.time()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in [
        ROOT / '10_SOURCE/WAR.csv', ROOT / '20_CODE/skater_forward_projection.py',
        ROOT / '20_CODE/contract_npv.py', ROOT / '20_CODE/skater_value_engine.py']}
    eng = NPVEngine(); sp = eng.sp; spine = sp.spine
    real = realized_lookup()
    tab = season_table(); feats = Features(tab)
    gp_real = tab['gp_share'].to_dict()

    # ---- rolling anchor (L) and games rules -------------------------------
    rows = []
    for nk in {k for k, _ in tab.index}:
        pos = nk.rsplit('|', 1)[1]
        for t in range(CAL_FIRST, LAST_OBS + 1):
            f = feats.get(nk, t); r = real.get((nk, t))
            if pd.isna(f['anchor']) or r is None or r[1] <= 0:
                continue
            f.update(t=t, pos=pos, real=r[0], gp_real=gp_real[(nk, t)]); rows.append(f)
    cal = pd.DataFrame(rows); rules = Rules(cal)
    gp_fit = {}
    def games_rule(t0, pos, s2):
        if (t0, pos, s2) not in gp_fit:
            d = cal[(cal.t <= t0 - 1) & (cal.pos == pos) & (cal.src2 == s2)]
            gp_fit[(t0, pos, s2)] = ols(d[['gp_b']].to_numpy(), d.gp_real.to_numpy())
        return gp_fit[(t0, pos, s2)]

    # ---- rolling lines --------------------------------------------------------
    sk = rate_sample()
    F = pd.DataFrame([feats.get(nk, int(y)) for nk, y in zip(sk.nk, sk.start_yr)], index=sk.index)
    keep = F.anchor.notna() & F.gp_b.notna()
    sk, F = sk[keep].copy(), F[keep]
    sk['gp_b'] = F.gp_b.to_numpy(); sk['term'] = sk['length'].astype(float)
    lines = {}
    for name, extras in LINES.items():
        if extras is None:
            continue
        for t0 in range(2018, 2026):
            tr = sk[sk.start_yr.between(2018, max(t0 - 1, 2019))]
            lines[(name, t0)] = fit_line(tr, extras)
    for name in ['prod_roll', 'G', 'GT']:
        v = lines[(name, 2025)]
        print(f"{name} line, 2025 page ($M at $95.5M cap): base {v['c']*CAP_SHOW:+.2f}, {v['bF']*CAP_SHOW:.2f}/win F, "
              f"{v['bD']*CAP_SHOW:.2f}/win D" + ''.join(f", {k} {x*CAP_SHOW:+.2f}" for k, x in v['extra'].items()) + f" (n={v['n']})")

    def price(name, t0, posgrp, war, gshare, term, ceil, lm):
        if name == 'prod':
            return max((sfp.ALPHA + sfp.skater_slope(posgrp) * war) * ceil, lm)
        L = lines[(name, t0)]; slope = L['bD'] if posgrp == 'D' else L['bF']
        x = L['c'] + slope * war + L['extra'].get('gp_b', 0.0) * gshare + L['extra'].get('term', 0.0) * term
        return max(x * ceil, lm)

    orig_anchor = sp.anchor
    def L_anchor(nk, t0):
        a, src = orig_anchor(nk, t0)
        if pd.isna(a):
            return a, src
        return rules.predict(t0, 'L', feats.get(nk, t0), nk.rsplit('|', 1)[1]), src

    firsts = spine.sort_values('season_start').groupby('contract_id').head(1)
    firsts = firsts[firsts['season_start'].between(2018, 2025)]
    nk_of = spine.drop_duplicates('player_id').set_index('player_id')['nk'].to_dict()
    seasons, contracts = [], []
    try:
        for anchor in ANCHORS:
            sp.anchor = L_anchor if anchor == 'L' else orig_anchor
            for r in firsts.itertuples():
                pid, t0 = int(r.player_id), int(r.season_start)
                d, s = eng.npv(pid, t0)
                if s.get('status') != 'ok':
                    continue
                nk = nk_of[pid]; pos = nk.rsplit('|', 1)[1]
                raw_a, _ = orig_anchor(nk, t0)
                f = feats.get(nk, t0)
                gproj = pred(games_rule(t0, pos, f['src2']), [f['gp_b']]) if pd.notna(f['gp_b']) else 0.669
                c = d[d['row_type'] == 'contract']
                term = float(len(c))                      # seasons left at valuation
                for name in LINES:
                    vname = f'{anchor}|{name}'
                    npv_c = 0.0
                    for x in c.itertuples():
                        season = int(x.season_start)
                        pv = x.value_dollars if name == 'prod' else price(name, t0, pos, x.projected_war, gproj, term, x.cap_ceiling_exante, x.league_min)
                        npv_c += (x.survival * pv - x.cost_dollars) * x.discount
                        if season > LAST_OBS:
                            continue
                        war_r, gp_r = real.get((nk, season), (0.0, 0))
                        g_r = gp_real.get((nk, season), 0.0)
                        val_r = price(name, t0, pos, war_r, g_r, term, x.cap_ceiling_exante, x.league_min) if gp_r > 0 else 0.0
                        seasons.append(dict(variant=vname, contract_id=int(r.contract_id), player_id=pid, t0=t0,
                                            k=int(x.k), tier=tier_of(raw_a), raw_anchor=raw_a,
                                            exp_war=x.survival * x.projected_war, real_war=war_r if gp_r > 0 else 0.0,
                                            exp_value=x.survival * pv, real_value=val_r, err=x.survival * pv - val_r))
                    contracts.append(dict(variant=vname, contract_id=int(r.contract_id), full_name=s['full_name'], t0=t0,
                                          tier=tier_of(raw_a), npv_contract=npv_c, npv_terminal=s['npv_terminal'],
                                          npv_total=npv_c + s['npv_terminal']))
            print(f'anchor {anchor}: done ({time.time() - clock:.0f}s)', flush=True)
    finally:
        sp.anchor = orig_anchor
    S = pd.DataFrame(seasons); S.to_csv(OUT / f'{PREFIX}_seasons.csv', index=False)
    C = pd.DataFrame(contracts); C.to_csv(OUT / f'{PREFIX}_contracts.csv', index=False)
    out = []
    for scope, sub in [('all pages', S), ('2020-25 pages', S[S.t0 >= 2020])]:
        for lab, tsel in [('all', None)] + [(t, t) for _, _, t in TIERS]:
            for v in sorted(S.variant.unique(), key=lambda x: (ANCHORS.index(x.split('|')[0]), list(LINES).index(x.split('|')[1]))):
                g = sub[sub.variant == v]
                if tsel: g = g[g.tier == tsel]
                e = g.err; we = g.exp_war - g.real_war
                out.append(dict(scope=scope, group=lab, variant=v, seasons=len(g), war_mae=we.abs().mean(),
                                bias_pct=e.sum() / g.real_value.sum() * 100, mae_pct_of_real=e.abs().sum() / g.real_value.sum() * 100,
                                tilt_M_per_war=np.polyfit(g.raw_anchor, e, 1)[0] / 1e6, mean_real_value_M=g.real_value.mean() / 1e6,
                                mean_exp_value_M=g.exp_value.mean() / 1e6))
    summ = pd.DataFrame(out); summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)
    P = C.pivot_table(index=['contract_id', 'tier', 't0'], columns='variant', values='npv_total').reset_index()
    mv = pd.DataFrame({v: (P[v] - P['prod|prod']).groupby(P.tier).mean() / 1e6 for v in P.columns if '|' in v and v != 'prod|prod'})
    mv.loc['net total $M'] = [(P[v] - P['prod|prod']).sum() / 1e6 for v in mv.columns]
    mv.to_csv(OUT / f'{PREFIX}_npv_movement.csv')
    assert all(digest(ROOT / k) == v for k, v in hashes.items())
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(dict(script_version=SCRIPT_VERSION,
        lines={f'{k[0]}|{k[1]}': v for k, v in lines.items()}, seasons=len(S), elapsed_seconds=time.time() - clock,
        input_hashes=hashes), indent=2))
    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 40)
    print(summ[summ.scope == '2020-25 pages'].round(3).to_string(index=False))
    print('\nmean NPV change vs production by tier ($M):'); print(mv.round(2).to_string())
    print(f'{time.time() - clock:.0f}s; production files unchanged.')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
