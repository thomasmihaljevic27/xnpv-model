"""pipeline_experiment.py -- one harness, many ways to fix the level tilt.

Test only. The production NPV engine is built once and patched IN-PROCESS
(instance attributes, module globals, a bound method on the curve); every
patch is reverted, and production/source hashes are checked at the start and
the end. Nothing in 20_CODE or 30_OUTPUT production files changes.

THE PROBLEM BEING ATTACKED
--------------------------
npv_realized_by_tier.py: priced value is right on average but tilted by the
player's level at valuation (-25% below 0 WAR, +14% at 3+). anchor_shrink_test
showed a fixed 2009-2017 pull-back of the starting point removes the tilt in
the middle but overshoots stars, partly because the calibration was stale.

EVERY CALIBRATION HERE IS ROLLING. For a valuation at season t0 (page date
July 1 of t0), a rule is fitted on seasons 2009..t0-1 only -- the same
information set the anchor already uses. No rule sees the season it prices.

STARTING-POINT RULES (what replaces the raw 60/40 season-total blend)
  prod  raw 60/40 blend (locked)
  L     a + b x blend, by position and by one-vs-two-season source
  L6    L fitted on the last six seasons only (drift-following)
  P     L with a second slope above 2 WAR (knot at 2), so stars can keep a
        different share than the middle
  LB    learned blend: real ~ w1 + w2, weights free instead of 60/40
  LB3   LB plus season t-3 where available
  RG    rate x availability: real ~ per-82 rate blend and rate x games share,
        so an injury-shortened season lowers the anchor through games, not rate
  C     the aging curve's own mean reversion passed through: raw blend x
        (curve anchor / curve smoothed level) at the base age. Production
        computes this and throws it away when it renormalises the ratio path.
        Falls back to L where the curve base is <= 0.25 or missing.
  M     market-informed: real ~ blend + implied WAR from the player's own cap
        hit, non-ELC contract seasons. DIAGNOSTIC ONLY: value built from cost
        makes surplus partly circular. It measures how much the market knows
        that the stats do not.

OTHER PIECES
  top50 aging curve keeps only the 50 most similar comparables (best rule in
        Aging_Comparable_Limit_Test.md); pooled weight kept
  H     exit hazard estimated on CONTRACTED transitions only: player-seasons
        t where the player holds a spine contract for t+1. Production
        estimates it on every GP>=10 season, most of which end in an expiring
        contract, and over-predicts exits for contract seasons (11.7% vs
        7.0% realised at k>=1).
  S0    apply the exit hazard to the valuation season too (S_0 = 1 - h).
        Production sets S_0 = 1, but 9.6% of contracts' players had no NHL
        game in the valuation season.

SCORING (as npv_realized_by_tier.py): every played contract season of the
2,591 spine contracts, projected survival x value against realised value at
the production price line ($0 on exit). WAR columns are line-free. Dollar
columns all use the production line, so variants are directly comparable.
LIMITS: the curve, its comparables pool and both hazard tables are fitted on
all seasons (the same for every variant); contract seasons only; RFA control
years move NPV but are not scored; ~19 variants are compared, so a single
narrow win is weak evidence by itself.
"""
from pathlib import Path
import json
import os
import time
import types

import numpy as np
import pandas as pd

import skater_forward_projection as sfp
from contract_npv import NPVEngine, G
from exit_hazard import build_transitions, build_hazard_table
from npv_realized_by_tier import realized_lookup, tier_of, TIERS, LAST_OBS
from aging_bandwidth_test import digest

SCRIPT_VERSION = '1.0'
SEED = 20260914
BOOTSTRAPS = 2000
CAL_FIRST = 2009
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
PREFIX = 'pipeline_experiment'
SEASON_LEN = {2019: 70, 2020: 56}          # D20 proration seasons
MIN_GP = sfp.MIN_GP                         # 10, the anchor's own filter
TOPK = 50
KNOT = 2.0
NAMED = ['Connor McDavid', 'Auston Matthews', 'Nathan MacKinnon', 'Cale Makar',
         'Leon Draisaitl', 'David Pastrnak', 'Johnny Gaudreau', 'Mitch Marner',
         'Aleksander Barkov', 'Quinn Hughes', 'William Karlsson', 'Seth Jones']

# name -> (anchor rule, top50 curve, hazard, S0)
VARIANTS = {
    'prod':       ('prod', False, 'prod', False),
    'L':          ('L',    False, 'prod', False),
    'L6':         ('L6',   False, 'prod', False),
    'P':          ('P',    False, 'prod', False),
    'LB':         ('LB',   False, 'prod', False),
    'LB3':        ('LB3',  False, 'prod', False),
    'RG':         ('RG',   False, 'prod', False),
    'C':          ('C',    False, 'prod', False),
    'M':          ('M',    False, 'prod', False),
    'top50':      ('prod', True,  'prod', False),
    'H':          ('prod', False, 'H',    False),
    'S0':         ('prod', False, 'prod', True),
    'L+top50':    ('L',    True,  'prod', False),
    'L+H':        ('L',    False, 'H',    False),
    'L+S0':       ('L',    False, 'prod', True),
    'L+all':      ('L',    True,  'H',    True),
    'LB+all':     ('LB',   True,  'H',    True),
    'LB3+all':    ('LB3',  True,  'H',    True),
    'RG+all':     ('RG',   True,  'H',    True),
}


# ---------------------------------------------------------------------------
# season table and anchor features
# ---------------------------------------------------------------------------
def season_table():
    """(nk, syr) -> prorated total WAR, GP, per-82 rate, games share. Same
    keys, cleaning and team-half summing as SkaterProjector.__init__."""
    w = pd.read_csv(sfp.F_WAR_SKATERS)
    w['syr'] = w['Season'].str.split('-').str[0].astype(int) + 2000
    w['nk'] = w['Player'].map(sfp.norm_name) + '|' + w['Position']
    w = w[~w['Player'].map(sfp.norm_name).isin(sfp.MERGED_WAR_NAMES)]
    a = w.groupby(['nk', 'syr'], as_index=False).agg(WAR=('WAR', 'sum'), GP=('GP', 'sum'))
    a['len'] = a['syr'].map(SEASON_LEN).fillna(82.0)
    a['war_pr'] = a['WAR'] * 82.0 / a['len']            # season total, prorated
    a['rate'] = a['WAR'] / a['GP'] * 82.0                # per-82 rate (raw WAR / raw GP)
    a['gp_share'] = a['GP'] / a['len']
    return a.set_index(['nk', 'syr'])


class Features:
    """Trailing features for (nk, t0), reading seasons t0-1..t0-3 only."""
    def __init__(self, tab):
        q = tab[tab['GP'] >= MIN_GP]                     # the anchor's own filter
        self.w = q['war_pr'].to_dict(); self.r = q['rate'].to_dict(); self.g = q['gp_share'].to_dict()

    def get(self, nk, t0):
        f = {}
        for j in (1, 2, 3):
            k = (nk, t0 - j)
            f[f'w{j}'] = self.w.get(k, np.nan); f[f'r{j}'] = self.r.get(k, np.nan); f[f'g{j}'] = self.g.get(k, np.nan)
        w1, w2 = f['w1'], f['w2']
        if pd.notna(w1) and pd.notna(w2):
            f['anchor'], f['src'] = sfp.W_T1 * w1 + sfp.W_T2 * w2, 'both'
            f['rate_b'] = sfp.W_T1 * f['r1'] + sfp.W_T2 * f['r2']
            f['gp_b'] = sfp.W_T1 * f['g1'] + sfp.W_T2 * f['g2']
        elif pd.notna(w1):
            f['anchor'], f['src'], f['rate_b'], f['gp_b'] = w1, 't1_only', f['r1'], f['g1']
        elif pd.notna(w2):
            f['anchor'], f['src'], f['rate_b'], f['gp_b'] = w2, 't2_only', f['r2'], f['g2']
        else:
            f['anchor'], f['src'], f['rate_b'], f['gp_b'] = np.nan, 'none', np.nan, np.nan
        f['src2'] = 'both' if f['src'] == 'both' else 'single'
        return f


def ols(X, y):
    X = np.column_stack([np.ones(len(y)), X])
    return np.linalg.lstsq(X, y, rcond=None)[0]


def pred(beta, x):
    return float(beta[0] + np.dot(beta[1:], x))


# ---------------------------------------------------------------------------
# rolling calibrations: one predictor per (rule, t0), fitted on t <= t0-1
# ---------------------------------------------------------------------------
class Rules:
    def __init__(self, cal):
        self.cal = cal
        self.cache = {}

    def train(self, t0, rule):
        c = self.cal
        lo = t0 - 6 if rule == 'L6' else CAL_FIRST
        return c[(c.t >= lo) & (c.t <= t0 - 1)]

    def fit(self, t0, rule):
        key = (t0, rule)
        if key in self.cache:
            return self.cache[key]
        d = self.train(t0, rule); out = {}
        if rule in ('L', 'L6'):
            for (pos, s2), g in d.groupby(['pos', 'src2']):
                out[(pos, s2)] = ols(g[['anchor']].to_numpy(), g.real.to_numpy())
        elif rule == 'P':
            for (pos, s2), g in d.groupby(['pos', 'src2']):
                X = np.column_stack([g.anchor, np.maximum(g.anchor - KNOT, 0)])
                out[(pos, s2)] = ols(X, g.real.to_numpy())
        elif rule == 'LB':
            for (pos, src), g in d.groupby(['pos', 'src']):
                cols = {'both': ['w1', 'w2'], 't1_only': ['w1'], 't2_only': ['w2']}[src]
                out[(pos, src)] = ols(g[cols].to_numpy(), g.real.to_numpy())
        elif rule == 'LB3':
            out = dict(self.fit(t0, 'LB'))
            for pos, g in d[(d.src == 'both') & d.w3.notna()].groupby('pos'):
                out[(pos, 'all3')] = ols(g[['w1', 'w2', 'w3']].to_numpy(), g.real.to_numpy())
        elif rule == 'RG':
            for (pos, s2), g in d.groupby(['pos', 'src2']):
                X = np.column_stack([g.rate_b, g.rate_b * g.gp_b])
                out[(pos, s2)] = ols(X, g.real.to_numpy())
        elif rule == 'M':
            m = d[d.implied.notna() & ~d.elc]
            for (pos, s2), g in m.groupby(['pos', 'src2']):
                out[(pos, s2)] = ols(g[['anchor', 'implied']].to_numpy(), g.real.to_numpy())
        self.cache[key] = out
        return out

    def predict(self, t0, rule, f, pos):
        b = self.fit(t0, rule)
        if rule in ('L', 'L6'):
            return pred(b[(pos, f['src2'])], [f['anchor']])
        if rule == 'P':
            return pred(b[(pos, f['src2'])], [f['anchor'], max(f['anchor'] - KNOT, 0)])
        if rule == 'LB':
            cols = {'both': ['w1', 'w2'], 't1_only': ['w1'], 't2_only': ['w2']}[f['src']]
            return pred(b[(pos, f['src'])], [f[c] for c in cols])
        if rule == 'LB3':
            if f['src'] == 'both' and pd.notna(f['w3']):
                return pred(b[(pos, 'all3')], [f['w1'], f['w2'], f['w3']])
            return self.predict(t0, 'LB', f, pos)
        if rule == 'RG':
            return pred(b[(pos, f['src2'])], [f['rate_b'], f['rate_b'] * f['gp_b']])
        if rule == 'M':
            if f.get('elc', True) or pd.isna(f.get('implied', np.nan)):
                return self.predict(t0, 'L', f, pos)
            return pred(b[(pos, f['src2'])], [f['anchor'], f['implied']])
        raise ValueError(rule)


# ---------------------------------------------------------------------------
def contracted_hazard(spine):
    """Exit-hazard table from transitions where the player holds a contract
    for t+1. Same builder and fitted model as production; only the
    population changes."""
    d = build_transitions(sfp.F_WAR_SKATERS, sfp.F_WAR_AGE)
    w = pd.read_csv(sfp.F_WAR_SKATERS)
    pos_of = w.drop_duplicates('Player', keep='last').set_index('Player')['Position'].to_dict()
    d['nk'] = d['player'].map(sfp.norm_name) + '|' + d['player'].map(pos_of)
    covered = set(zip(spine['nk'], spine['season_start']))
    dh = d[[(nk, t + 1) in covered for nk, t in zip(d['nk'], d['t'])]].copy()
    return build_hazard_table(dh), len(d), len(dh), float(d.exited.mean()), float(dh.exited.mean())


def topk_weights(curve):
    orig = curve._weights
    def _w(self, target_z, pos, age, exclude=None):
        cand, w = orig(target_z, pos, age, exclude)
        if w is not None and len(w) > TOPK:
            keep = np.argpartition(-w, TOPK - 1)[:TOPK]
            m = np.zeros(len(w), bool); m[keep] = True
            w = np.where(m, w, 0.0)
        return cand, w
    return types.MethodType(_w, curve), orig


def boot_ci(m, e0, e1, rng):
    d = pd.DataFrame({'p': m['player_id'].to_numpy(), 'e': e1.abs().to_numpy() - e0.abs().to_numpy()})
    g = d.groupby('p')['e'].agg(['sum', 'count'])
    s, c = g['sum'].to_numpy(), g['count'].to_numpy()
    idx = rng.integers(0, len(g), (BOOTSTRAPS, len(g)))
    return np.quantile(s[idx].sum(1) / c[idx].sum(1), [.025, .975])


# ---------------------------------------------------------------------------
def main():
    clock = time.time()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in [
        ROOT / '10_SOURCE/WAR.csv', OUT / 'WAR_with_age.csv',
        ROOT / '20_CODE/aging_curve.py', ROOT / '20_CODE/skater_forward_projection.py',
        ROOT / '20_CODE/contract_npv.py', ROOT / '20_CODE/exit_hazard.py',
        ROOT / '20_CODE/rfa_terminal_value.py']}
    eng = NPVEngine()
    sp = eng.sp
    real = realized_lookup()
    tab = season_table()
    feats = Features(tab)
    spine = sp.spine
    # reproduction guard: my features reproduce the production anchor exactly
    for (nk, t), v in list(sp.war_lut.items())[:3000]:
        f = feats.get(nk, t + 1)
        a, src = sp.anchor(nk, t + 1)
        assert abs(f['anchor'] - a) < 1e-9 and f['src'] == src, (nk, t)

    # ---- calibration table: every (nk, t) with an anchor and a played season t
    bd = spine.drop_duplicates('nk').set_index('nk')['bd'].to_dict()
    cost_at = spine.drop_duplicates(['nk', 'season_start']).set_index(['nk', 'season_start'])
    elc_at = cost_at['cs_entry_level'].fillna(False).astype(bool).to_dict()
    cost_at = cost_at['cost'].to_dict()
    def implied(nk, t):
        c = cost_at.get((nk, t)); ceil = sfp.CAP_CEILING.get(t)
        if c is None or pd.isna(c) or ceil is None:
            return np.nan
        return (c / ceil - sfp.ALPHA) / sfp.skater_slope(nk.rsplit('|', 1)[1])
    rows = []
    for nk in {k for k, _ in tab.index}:
        pos = nk.rsplit('|', 1)[1]
        for t in range(CAL_FIRST, LAST_OBS + 1):
            f = feats.get(nk, t)
            if pd.isna(f['anchor']):
                continue
            r = real.get((nk, t))
            if r is None or r[1] <= 0:
                continue                                  # exit is the hazard's job
            f.update(nk=nk, t=t, pos=pos, real=r[0], implied=implied(nk, t),
                     elc=elc_at.get((nk, t), True))
            rows.append(f)
    cal = pd.DataFrame(rows)
    rules = Rules(cal)
    drift = {t0: {str(k): [round(float(x), 4) for x in v] for k, v in rules.fit(t0, 'L').items()}
             for t0 in (2018, 2022, 2025)}
    print('rolling L coefficients [a, b] by (pos, source):')
    for t0, d in drift.items():
        print(f'  t0={t0}: ' + '  '.join(f'{k}: {v}' for k, v in d.items()))
    print('LB weights 2025 (a, w1, w2):', {str(k): [round(float(x), 3) for x in v] for k, v in rules.fit(2025, 'LB').items()})
    print('RG 2025 (a, rate, rate x games):', {str(k): [round(float(x), 3) for x in v] for k, v in rules.fit(2025, 'RG').items()})

    # ---- contracted hazard ------------------------------------------------
    h_table, n_all, n_cov, ex_all, ex_cov = contracted_hazard(spine)
    print(f'hazard population: all GP>=10 transitions {n_all} (exit {ex_all:.1%}); '
          f'with a contract for t+1 {n_cov} (exit {ex_cov:.1%})')
    prod_h = eng.h_sk

    # ---- curve pass-through helper (rule C) -------------------------------
    curve = sp.curve
    def curve_factor(nk, t0):
        raw = sp.raw_name.get(nk); key = sfp.career_key(raw) if raw else None
        age = sp.age_at(bd.get(nk), t0)
        if key is None or key not in curve.players or age is None:
            return None
        p = curve.players[key]
        for lag in (1, 2):                                # D21: base at t-1, then t-2
            ba = age - lag
            if ba in p['sm'] and p['sm'][ba] > sfp.CURVE_BASE_FLOOR:
                try:
                    tr = curve.project(key, ba, horizon=1)
                except (ValueError, KeyError, IndexError):
                    return None
                return float(tr.iloc[0]['projected_war_per_82'] / p['sm'][ba])
        return None

    orig_anchor = sp.anchor
    def make_anchor(rule):
        def _a(nk, t0):
            a, src = orig_anchor(nk, t0)
            if pd.isna(a):
                return a, src
            pos = nk.rsplit('|', 1)[1]
            f = feats.get(nk, t0)
            assert abs(f['anchor'] - a) < 1e-9
            if rule == 'C':
                fac = curve_factor(nk, t0)
                return (a * fac, src) if fac is not None else (rules.predict(t0, 'L', f, pos), src)
            if rule == 'M':
                f['implied'] = implied(nk, t0); f['elc'] = elc_at.get((nk, t0), True)
            return rules.predict(t0, rule, f, pos), src
        return _a

    # ---- the sweeps -----------------------------------------------------------
    firsts = spine.sort_values('season_start').groupby('contract_id').head(1)
    firsts = firsts[firsts['season_start'].between(2018, 2025)]
    nk_of = spine.drop_duplicates('player_id').set_index('player_id')['nk'].to_dict()
    topk_m, orig_w = topk_weights(curve)
    seasons, contracts = [], []
    try:
        for name, (rule, top, haz, s0) in VARIANTS.items():
            sp.anchor = orig_anchor if rule == 'prod' else make_anchor(rule)
            curve._weights = topk_m if top else orig_w
            eng.h_sk = h_table if haz == 'H' else prod_h
            n = 0
            for r in firsts.itertuples():
                pid, t0 = int(r.player_id), int(r.season_start)
                d, s = eng.npv(pid, t0)
                if s.get('status') != 'ok':
                    continue
                n += 1
                nk = nk_of[pid]
                raw_a, _ = orig_anchor(nk, t0)
                c = d[d['row_type'] == 'contract'].copy()
                if s0:                                     # S_0 = 1 - h(anchor state, age0)
                    h0 = eng._hazard(eng.h_sk, c.iloc[0]['anchor_war'], c.iloc[0]['age_at_valuation'])
                    c['survival'] = c['survival'] * (1 - h0)
                    c['pv_dollars'] = (c['survival'] * c['value_dollars'] - c['cost_dollars']) * c['discount']
                    npv_c = float(c['pv_dollars'].sum())
                else:
                    npv_c = s['npv_contract']
                contracts.append(dict(variant=name, contract_id=int(r.contract_id), player_id=pid,
                                      full_name=s['full_name'], t0=t0, raw_anchor=raw_a,
                                      tier=tier_of(raw_a), npv_contract=npv_c,
                                      npv_terminal=s['npv_terminal'], npv_total=npv_c + s['npv_terminal']))
                for x in c.itertuples():
                    season = int(x.season_start)
                    if season > LAST_OBS:
                        break
                    war_r, gp_r = real.get((nk, season), (0.0, 0))
                    slope = sfp.skater_slope(x.posgrp)
                    val_r = (max((sfp.ALPHA + slope * war_r) * x.cap_ceiling_exante, x.league_min)
                             if gp_r > 0 else 0.0)
                    seasons.append(dict(variant=name, contract_id=int(r.contract_id), player_id=pid,
                                        k=int(x.k), tier=tier_of(raw_a), raw_anchor=raw_a,
                                        survival=x.survival, present=gp_r > 0,
                                        exp_war=x.survival * x.projected_war,
                                        real_war=war_r if gp_r > 0 else 0.0,
                                        exp_value=x.survival * x.value_dollars, real_value=val_r,
                                        err=x.survival * x.value_dollars - val_r,
                                        disc=(1 + G) ** (-int(x.k))))
            print(f'{name}: {n} contracts ({time.time() - clock:.0f}s)', flush=True)
    finally:
        sp.anchor = orig_anchor; curve._weights = orig_w; eng.h_sk = prod_h

    S = pd.DataFrame(seasons); C = pd.DataFrame(contracts)
    S.to_csv(OUT / f'{PREFIX}_seasons.csv', index=False)
    C.to_csv(OUT / f'{PREFIX}_contracts.csv', index=False)

    # ---- scoring --------------------------------------------------------------
    W = S.pivot_table(index=['contract_id', 'k', 'player_id', 'tier', 'raw_anchor', 'present', 'real_value', 'real_war'],
                      columns='variant', values=['err', 'exp_war', 'survival', 'disc']).reset_index()
    W.columns = [c if isinstance(c, str) else (c[0] if c[1] == '' else f'{c[0]}_{c[1]}') for c in W.columns]
    assert W.notna().all().all(), 'variants did not score the same contract seasons'
    rng = np.random.default_rng(SEED)
    out = []
    groups = [('all', W)] + [(t, W[W.tier == t]) for _, _, t in TIERS] + \
             [('k=0', W[W.k == 0]), ('k>=1', W[W.k >= 1]), ('3+ k>=1', W[(W.tier == '3+') & (W.k >= 1)])]
    for lab, g in groups:
        for v in VARIANTS:
            e = g[f'err_{v}']; we = g[f'exp_war_{v}'] - g['real_war']
            pc = (e * g[f'disc_{v}']).groupby(g.contract_id).sum()
            row = dict(group=lab, variant=v, seasons=len(g), players=g.player_id.nunique(),
                       war_bias=we.mean(), war_mae=we.abs().mean(),
                       bias_M=e.mean() / 1e6, mae_M=e.abs().mean() / 1e6,
                       bias_pct=e.sum() / g.real_value.sum() * 100,
                       contract_mae_M=pc.abs().mean() / 1e6,
                       tilt_M_per_war=np.polyfit(g.raw_anchor, e, 1)[0] / 1e6,
                       exp_exit=1 - g[f'survival_{v}'].mean(), real_exit=1 - g.present.mean())
            if v != 'prod':
                we0 = g['exp_war_prod'] - g['real_war']
                lo, hi = boot_ci(g, g['err_prod'], e, rng)
                wlo, whi = boot_ci(g, we0, we, rng)
                row.update(mae_change_pct=(e.abs().mean() / g.err_prod.abs().mean() - 1) * 100,
                           ci_low_M=lo / 1e6, ci_high_M=hi / 1e6,
                           war_mae_change_pct=(we.abs().mean() / we0.abs().mean() - 1) * 100,
                           war_ci_low=wlo, war_ci_high=whi)
            out.append(row)
    summ = pd.DataFrame(out); summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)

    P = C.pivot_table(index=['contract_id', 'full_name', 't0', 'tier', 'raw_anchor'],
                      columns='variant', values='npv_total').reset_index()
    mv = pd.DataFrame({v: (P[v] - P['prod']).groupby(P.tier).mean() / 1e6 for v in VARIANTS if v != 'prod'})
    mv.loc['net total $M'] = [(P[v] - P['prod']).sum() / 1e6 for v in VARIANTS if v != 'prod']
    mv.to_csv(OUT / f'{PREFIX}_npv_movement.csv')
    named = P[P.full_name.isin(NAMED)].sort_values(['full_name', 't0'])

    assert all(digest(ROOT / k) == v for k, v in hashes.items()), 'input or production code changed during run'
    run = dict(script_version=SCRIPT_VERSION, seed=SEED, variants=VARIANTS, rolling_L=drift,
               hazard=dict(n_all=n_all, n_contracted=n_cov, exit_all=ex_all, exit_contracted=ex_cov),
               contract_seasons_scored=len(W), contracts=int(P.shape[0]),
               elapsed_seconds=time.time() - clock, input_hashes=hashes)
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(run, indent=2, default=str))

    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 40)
    cols = ['group', 'variant', 'war_bias', 'war_mae', 'war_mae_change_pct', 'war_ci_low', 'war_ci_high',
            'bias_M', 'mae_M', 'mae_change_pct', 'ci_low_M', 'ci_high_M', 'contract_mae_M', 'tilt_M_per_war',
            'exp_exit', 'real_exit']
    for lab in ['all', 'below 0', '0 to 1', '1 to 2', '2 to 3', '3+', 'k=0', 'k>=1', '3+ k>=1']:
        print(f'\n=== {lab}'); print(summ[summ.group == lab][cols].round(3).to_string(index=False))
    print('\nmean NPV change vs production by tier ($M):'); print(mv.round(2).to_string())
    show = ['prod', 'L', 'LB', 'C', 'L+all', 'LB+all']
    print('\nnamed contracts ($M):')
    print(named[['full_name', 't0', 'raw_anchor'] + show].assign(**{v: named[v] / 1e6 for v in show})
          .round(2).to_string(index=False))
    print(f'\n{time.time() - clock:.0f}s; production files unchanged.')


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
