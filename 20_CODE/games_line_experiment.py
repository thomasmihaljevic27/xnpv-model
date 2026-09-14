"""games_line_experiment.py -- price availability, not only wins.

Test only; nothing in production changes (engine patched in-process, hashes
checked). Companion to pipeline_experiment.py and market_line_experiment.py.

WHY
---
market_line_experiment.py found that a cap-hit line with the player's games
share alongside his two trailing seasons predicts signings 17% better out of
sample than the production line, and that once games are in, the price per
win falls from about $2.0M to about $0.8M. The production line therefore
charges wins for what teams partly pay for availability. This script asks
what that does inside the NPV chain.

THE GAMES-AWARE VALUE LINE (spec 'w1w2+age+gp' with the age terms dropped,
because the chain's future seasons carry no age-varying price)
    cap share = c + b x WAR_total + bD x D x WAR_total + g x games_share
  fitted rolling on signings 2018..t0-1 (censored ML, as production). For
  t0 = 2018 and 2019 the line is fitted on 2018-2019 signings (the first
  years the production sample covers), which is the one place this test is
  in sample; those pages are flagged and the results are reported with and
  without them.

PROJECTED GAMES SHARE per season: a rolling rule fitted on 2009..t0-1,
    games_share_t = a + b x games_share blend (60/40, same seasons as the
    anchor), by position and source,
  held flat over the contract. Projected WAR per season comes from the rule
  in force (raw production anchor, or the rolling L pull-back), walked by the
  production aging ratios and survival exactly as npv() does.

SCORING: each played contract season, priced value S_k x line(WAR_k, games_k)
against realised value line(WAR_real, games_real), $0 on exit -- the same
line on both sides, so the dollar error is on that line's own currency and is
NOT comparable to the production-line dollar errors in the other scripts.
Comparable across scripts are: WAR error (line-free), the percentage bias by
tier, and the tilt of dollar error on the starting level.

VARIANTS
  prod          production anchor, production line   (reference)
  prod+G        production anchor, games-aware line
  L             rolling L anchor, production line
  L+G           rolling L anchor, games-aware line
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
from pipeline_experiment import season_table, Features, Rules, ols, pred, CAL_FIRST, boot_ci
from market_line_experiment import censored_fit
from anchor_shrink_test import rate_sample
from aging_bandwidth_test import digest

SCRIPT_VERSION = '1.0'
SEED = 20260914
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
PREFIX = 'games_line_experiment'
VARS = ['prod', 'prod+G', 'L', 'L+G']


def games_design(d):
    w, isd = d['wWAR'].to_numpy(float), d['is_d'].to_numpy(float)
    return np.column_stack([np.ones(len(d)), w, isd * w, d['gp_b'].to_numpy(float)])


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

    # ---- rolling games-aware line --------------------------------------------
    sk = rate_sample()
    F = pd.DataFrame([feats.get(nk, int(y)) for nk, y in zip(sk.nk, sk.start_yr)], index=sk.index)
    keep = F.anchor.notna() & F.gp_b.notna()
    sk, F = sk[keep].copy(), F[keep]
    sk['gp_b'] = F.gp_b.to_numpy()
    lines = {}
    for t0 in range(2018, 2026):
        tr = sk[sk.start_yr.between(2018, max(t0 - 1, 2019))]      # 2018/2019 pages: in sample
        b = censored_fit(games_design(tr), tr.cap_pct.to_numpy(), tr.floor_pct.to_numpy())
        lines[t0] = dict(c=float(b[0]), bF=float(b[1]), bD=float(b[1] + b[2]), g=float(b[3]),
                         n=len(tr), in_sample=t0 <= 2019)
    print('games-aware line by page ($M at $95.5M cap): ' + '; '.join(
        f"{t0}: base {v['c']*95.5:.2f} + {v['bF']*95.5:.2f}/win F, {v['bD']*95.5:.2f}/win D, "
        f"+{v['g']*95.5:.2f} x games (n={v['n']})" for t0, v in lines.items()))

    def price(t0, posgrp, war, gshare, ceil, lm, use_G):
        if use_G:
            L = lines[t0]; slope = L['bD'] if posgrp == 'D' else L['bF']
            return max((L['c'] + slope * war + L['g'] * gshare) * ceil, lm)
        return max((sfp.ALPHA + sfp.skater_slope(posgrp) * war) * ceil, lm)

    orig_anchor = sp.anchor
    def L_anchor(nk, t0):
        a, src = orig_anchor(nk, t0)
        if pd.isna(a):
            return a, src
        return rules.predict(t0, 'L', feats.get(nk, t0), nk.rsplit('|', 1)[1]), src

    firsts = spine.sort_values('season_start').groupby('contract_id').head(1)
    firsts = firsts[firsts['season_start'].between(2018, 2025)]
    nk_of = spine.drop_duplicates('player_id').set_index('player_id')['nk'].to_dict()
    seasons = []
    try:
        for name in VARS:
            use_G = name.endswith('+G'); sp.anchor = L_anchor if name.startswith('L') else orig_anchor
            for r in firsts.itertuples():
                pid, t0 = int(r.player_id), int(r.season_start)
                d, s = eng.npv(pid, t0)
                if s.get('status') != 'ok':
                    continue
                nk = nk_of[pid]; pos = nk.rsplit('|', 1)[1]
                raw_a, _ = orig_anchor(nk, t0)
                f = feats.get(nk, t0)
                gproj = pred(games_rule(t0, pos, f['src2']), [f['gp_b']]) if pd.notna(f['gp_b']) else np.nan
                c = d[d['row_type'] == 'contract']
                for x in c.itertuples():
                    season = int(x.season_start)
                    if season > LAST_OBS:
                        break
                    war_r, gp_r = real.get((nk, season), (0.0, 0))
                    g_r = gp_real.get((nk, season), 0.0)
                    gp_use = gproj if pd.notna(gproj) else 0.669           # sample mean, rare
                    # k=0 keeps the production anchor identity only for the production line;
                    # the games line re-prices every season, k=0 included.
                    pv = price(t0, pos, x.projected_war, gp_use, x.cap_ceiling_exante, x.league_min, use_G)
                    pv = x.value_dollars if not use_G else pv          # production keeps item 3.6 correction
                    val_r = price(t0, pos, war_r, g_r, x.cap_ceiling_exante, x.league_min, use_G) if gp_r > 0 else 0.0
                    seasons.append(dict(variant=name, contract_id=int(r.contract_id), player_id=pid, t0=t0,
                                        in_sample_line=use_G and t0 <= 2019, k=int(x.k), tier=tier_of(raw_a),
                                        raw_anchor=raw_a, exp_war=x.survival * x.projected_war,
                                        real_war=war_r if gp_r > 0 else 0.0, gproj=gp_use, greal=g_r,
                                        exp_value=x.survival * pv, real_value=val_r,
                                        err=x.survival * pv - val_r, disc=(1 + G) ** (-int(x.k))))
            print(f'{name}: done ({time.time() - clock:.0f}s)', flush=True)
    finally:
        sp.anchor = orig_anchor
    S = pd.DataFrame(seasons); S.to_csv(OUT / f'{PREFIX}_seasons.csv', index=False)
    rng = np.random.default_rng(SEED)
    out = []
    for oos_only in (False, True):
        for lab, tsel in [('all', None)] + [(t, t) for _, _, t in TIERS]:
            for v in VARS:
                g = S[S.variant == v]
                if tsel: g = g[g.tier == tsel]
                if oos_only: g = g[g.t0 >= 2020]
                base = S[(S.variant == ('prod' if not v.startswith('L') else 'L'))]
                e = g.err; we = g.exp_war - g.real_war
                out.append(dict(scope='2020-25 pages' if oos_only else 'all pages', group=lab, variant=v, seasons=len(g),
                                war_bias=we.mean(), war_mae=we.abs().mean(),
                                bias_pct=e.sum() / g.real_value.sum() * 100,
                                mae_pct_of_real=e.abs().sum() / g.real_value.sum() * 100,
                                mae_M=e.abs().mean() / 1e6, tilt_M_per_war=np.polyfit(g.raw_anchor, e, 1)[0] / 1e6,
                                mean_real_value_M=g.real_value.mean() / 1e6,
                                games_bias=(g.gproj - g.greal)[g.real_war != 0].mean()))
    summ = pd.DataFrame(out); summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)
    assert all(digest(ROOT / k) == v for k, v in hashes.items())
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(dict(script_version=SCRIPT_VERSION, lines=lines,
                                                            seasons=len(S), elapsed_seconds=time.time() - clock,
                                                            input_hashes=hashes), indent=2))
    pd.set_option('display.width', 250)
    print(summ.round(3).to_string(index=False))
    print(f'{time.time() - clock:.0f}s; production files unchanged.')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
