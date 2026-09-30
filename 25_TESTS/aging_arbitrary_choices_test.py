"""aging_arbitrary_choices_test.py -- the current aging curve's hand-set choices, each scored.

Test only. Production (aging_curve.py, skater_forward_projection.py) is never
edited or monkeypatched; their hashes are checked at start and finish.

WHY THIS EXISTS
---------------
A supervisor walkthrough of the aging curve (2026-09-28) listed six things the
curve does without a stated reason. Each is scored here against held-out
careers, one change at a time, on identical forecast-outcome pairs:

  1  what the yardstick is built from. It is the median distance between
     pairs drawn from a RANDOM SAMPLE of up to 1,200 profiles per position
     (seed 0), and one player's two seasons can form a pair.
       yard_all_pairs        every pair in the pool, no sampling
       yard_no_same_career   the production sample, same-career pairs removed
  2  the feature weights (why the square root). sqrt(w) on the z-score before
     squaring is the same arithmetic as w on the squared difference, so the
     square root itself is not a choice. The weights are: each of the four
     groups (style, ice time, level, trend) gets 1, the five style shares 0.2
     each. The alternatives, with the yardstick rebuilt on each reweighted
     scale by production's own rule (otherwise the weight change would also
     silently change how wide "one yardstick" is):
       fw_equal_features     all eight measures weight 1
       fw_no_style           style shares weight 0
       fw_no_trend           trend weight 0
       fw_level_only         level alone
  3  one yardstick for forwards and defence: the forward-forward and
     defence-defence distances are pooled into one median.
       yard_by_position      a separate median for each position
  4  the weight formula exp(-d^2 / 2h^2), a Gaussian kernel with h = one
     yardstick. u = d / h below.
       kernel_flat           every same-age, same-position player weight 1
                             (a plain age-group average: does weighting help?)
       kernel_epanechnikov   max(0, 1 - (u/2)^2), zero beyond two yardsticks
       kernel_tricube        (1 - (u/2)^3)^3, zero beyond two yardsticks
       kernel_cauchy         1 / (1 + u^2), heavier tails than the Gaussian
       gauss_h_double        Gaussian, yardstick x 2
       gauss_h_half          Gaussian, yardstick x 1/2
     The two-yardstick support and the Cauchy form are DECLARED, not searched.
  5  the pool uses every season in the data, including seasons played after
     the valuation date by other players. Scored only in the historical-window
     mode, where the pre-valuation pool is the baseline:
       full_era_pool         production's rule with the full-era pool. This
                             moves four things together, because production
                             builds all four from the whole file: the
                             comparables, the z-score means and SDs, the
                             yardstick, and the league-average level and
                             yearly-change curves. Its error is NOT a reason
                             to prefer it: it uses information no team had.
  6  the league average enters as one more comparable carrying SHRINK_K = 10
     units of weight.
       K_off (0.01), K_5, K_20, K_50
       share_5pct, share_10pct   the league average takes a FIXED share of
                             every estimate (the supervisor's suggestion);
                             the comparables share the rest in proportion to
                             their weights; with no comparable value at an
                             age, the league average alone.

LAMBDA = 0.55 (the kept share of own form) was selected by cross-validation
and re-tested in review item 1.7, so it is held fixed and not re-tested here.
It was selected with the production comparables, so an arm that changes the
comparables is scored at a lambda that was not chosen for it.

DESIGN (inherited from aging_comp_limit_test.py v1.0, same guards)
-----------------------------------------------------------------
* Five whole-career folds, stratified by position, same seed as that test.
  The target's career is never in its own training bank. The target sees
  only its own seasons up to the origin age.
* career_holdout: full-era training, raw WAR/82 outcomes 1-6 years ahead.
  historical_window: training seasons <= origin year, origins 2017-2022,
  1-3 years ahead.
* Outcome 'curve' = the future raw WAR/82 (seasons with 20+ GP). Outcome
  'season_total' = production-style ratio on a 60/40 trailing season-total
  baseline (ratio_prediction imported unchanged from aging_bandwidth_test.py).
* Every arm is scored on the SAME forecast-outcome pairs (asserted).
* Reproduction guards: the prod arm, rebuilt here through this script's own
  distance/weight code, must equal AgingModel.project() to 1e-10 on every
  origin; the yardstick recomputed here must equal AgingModel.h exactly; the
  feature weights must equal aging_curve._attr_weights().
* The primary score is mean absolute error, as in the two earlier aging
  tests, so these figures sit beside theirs; RMSE and bias are printed with
  it. The interval resamples CAREERS (2,000 draws), not rows.

LIMITS: contemporary reconstructed data; surviving 20+ GP seasons only; no
exit hazard, no dollars. Nineteen arms plus the look-ahead are compared, so a small win by one
of them is weak evidence on its own, and the arms are single changes: none is
tuned, and no combination is scored. A loss rules out the construction tried,
not the idea behind it.
"""

# Moved from 20_CODE/ to 25_TESTS/ on 2026-09-30 (finished one-off test). The
# production modules it imports stay in 20_CODE/, so put that folder on the path.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "20_CODE"))

from pathlib import Path
import json
import os
import tempfile
import time

import numpy as np
import pandas as pd

from aging_curve import (AgingModel, career_key, _profile, _attr_weights,
                         LAMBDA, SHRINK_K, WIN, FEATS, SHARE)
from aging_bandwidth_test import truncated_player, ratio_prediction, digest

SCRIPT_VERSION = '1.0'
SEED = 20260913          # the comparables-limit test's seed: same folds
FOLDS = 5
BOOTSTRAPS = 2000
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
SOURCE = OUT / 'WAR_with_age.csv'
PREFIX = 'aging_arbitrary_choices_test'
ELITE = 3.0
TIERS = [(-np.inf, 0.0, 'below_0'), (0.0, 1.5, '0_to_1.5'),
         (1.5, ELITE, '1.5_to_3'), (ELITE, np.inf, 'elite_3plus')]
# yardstick sampling, copied from AgingModel._build_bank (guarded to equality)
YARD_SEED, YARD_SAMPLE = 0, 1200
SEED_SPREAD = 20         # seeds tried for the sampling-noise diagnostic

# ---- FEATURE-WEIGHT SETS, over FEATS = 5 style shares + toi_pg, lvl, slope --
_S = len(SHARE)
FW = {
    'prod':           None,                                   # _attr_weights()
    'equal_features': np.ones(len(FEATS)),
    'no_style':       np.array([0.0] * _S + [1.0, 1.0, 1.0]),
    'no_trend':       np.array([1.0 / _S] * _S + [1.0, 1.0, 0.0]),
    'level_only':     np.array([0.0] * _S + [0.0, 1.0, 0.0]),
}
assert FEATS[_S:] == ['toi_pg', 'lvl', 'slope'], 'feature order changed in aging_curve.py'

# ---- THE ARMS. Each changes only the keys it names; the rest is production.
#   fw     feature-weight set (keys of FW)
#   yard   'prod' | 'all_pairs' | 'no_same_career' | 'by_position'
#   kernel 'gauss' | 'flat' | 'epanechnikov' | 'tricube' | 'cauchy'
#   hm     multiplier on the yardstick
#   K      league-average weight in comparable-weight units (production 10)
#   share  fixed league-average share (replaces K)
#   pool   'full_era' (historical mode only)
VARIANTS = {
    'prod':                {},
    'yard_all_pairs':      {'yard': 'all_pairs'},
    'yard_no_same_career': {'yard': 'no_same_career'},
    'yard_by_position':    {'yard': 'by_position'},
    'fw_equal_features':   {'fw': 'equal_features'},
    'fw_no_style':         {'fw': 'no_style'},
    'fw_no_trend':         {'fw': 'no_trend'},
    'fw_level_only':       {'fw': 'level_only'},
    'kernel_flat':         {'kernel': 'flat'},
    'kernel_epanechnikov': {'kernel': 'epanechnikov'},
    'kernel_tricube':      {'kernel': 'tricube'},
    'kernel_cauchy':       {'kernel': 'cauchy'},
    'gauss_h_double':      {'hm': 2.0},
    'gauss_h_half':        {'hm': 0.5},
    'K_off':               {'K': 0.01},    # exactly 0 divides by zero, see _shrunk
    'K_5':                 {'K': 5.0},
    'K_20':                {'K': 20.0},
    'K_50':                {'K': 50.0},
    'share_5pct':          {'share': 0.05},
    'share_10pct':         {'share': 0.10},
}
HIST_ONLY = {'full_era_pool': {'pool': 'full_era'}}
QUESTION = {   # which supervisor question each arm answers, for the report
    'yard_all_pairs': 1, 'yard_no_same_career': 1, 'yard_by_position': 3,
    'fw_equal_features': 2, 'fw_no_style': 2, 'fw_no_trend': 2, 'fw_level_only': 2,
    'kernel_flat': 4, 'kernel_epanechnikov': 4, 'kernel_tricube': 4, 'kernel_cauchy': 4,
    'gauss_h_double': 4, 'gauss_h_half': 4, 'full_era_pool': 5,
    'K_off': 6, 'K_5': 6, 'K_20': 6, 'K_50': 6, 'share_5pct': 6, 'share_10pct': 6,
}


def tier_of(x):
    for lo, hi, lab in TIERS:
        if lo <= x < hi:
            return lab
    raise ValueError(x)


# ---------------------------------------------------------------------------
# THE SCALE: feature weights and yardsticks for one fitted model
# ---------------------------------------------------------------------------
def _pair_d(X):
    """Upper-triangle pairwise Euclidean distances, production's arithmetic."""
    sq = (X ** 2).sum(1)
    d2 = np.clip(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0, None)
    return np.sqrt(d2[np.triu_indices(len(X), 1)])


def _all_pairs_d(X, chunk=1500):
    """Every pair, in row blocks so a 5,000-profile position fits in memory."""
    out, sq = [], (X ** 2).sum(1)
    for i in range(0, len(X), chunk):
        a = X[i:i + chunk]
        d2 = np.clip((a ** 2).sum(1)[:, None] + sq[None, :] - 2 * a @ X.T, 0, None)
        r = np.arange(i, i + len(a))[:, None]
        c = np.arange(len(X))[None, :]
        out.append(np.sqrt(d2[c > r]))           # j > i only: each pair once
    return np.concatenate(out)


def yardsticks(model, Zw, want_all=False, seed=YARD_SEED):
    """Production's yardstick rule on a (possibly reweighted) scale Zw, plus
    the alternatives. With seed 0 and production's Zw, 'prod' must equal
    AgingModel.h exactly (guarded by the caller)."""
    rng = np.random.default_rng(seed)
    ds, same, by_pos, info = [], [], {}, {}
    for pp in np.unique(model.pos):
        sel = np.flatnonzero(model.pos == pp)
        if len(sel) < 3:
            continue
        idx = rng.choice(len(sel), size=min(YARD_SAMPLE, len(sel)), replace=False)
        rows = sel[idx]
        d = _pair_d(Zw[rows])
        iu = np.triu_indices(len(rows), 1)
        nm = model.names[rows]
        s = nm[iu[0]] == nm[iu[1]]                # a player's own two seasons
        ds.append(d); same.append(s); by_pos[pp] = float(np.median(d))
        info[pp] = dict(pool_profiles=int(len(sel)), careers=int(len(set(model.names[sel]))),
                        sampled=int(len(rows)), pairs=int(len(d)),
                        same_career_pairs=int(s.sum()),
                        median=float(np.median(d)),
                        median_same_career=float(np.median(d[s])) if s.any() else np.nan)
    d, s = np.concatenate(ds), np.concatenate(same)
    out = dict(prod=float(np.median(d)), no_same_career=float(np.median(d[~s])),
               by_position=by_pos, info=info)
    if want_all:
        out['all_pairs'] = float(np.median(np.concatenate(
            [_all_pairs_d(Zw[model.pos == pp]) for pp in np.unique(model.pos)
             if (model.pos == pp).sum() >= 3])))
    return out


class Scale:
    """For one fitted model: unweighted standardised pool, and for each
    feature-weight set the reweighted pool and its yardsticks."""

    def __init__(self, model):
        self.model = model
        fw0 = _attr_weights()
        assert np.array_equal(fw0, model.fw), 'production feature weights moved'
        self.Z = model.Zw / np.sqrt(model.fw)             # every prod weight is > 0
        self.fw = {k: (fw0 if v is None else v) for k, v in FW.items()}
        self.yard = {}
        for k, w in self.fw.items():
            # production's own array for 'prod', so the guard below can demand
            # exact equality (Z * sqrt(w) round-trips to within an ulp only)
            Zw = model.Zw if k == 'prod' else self.Z * np.sqrt(w)
            self.yard[k] = yardsticks(model, Zw, want_all=(k == 'prod'))
        # REPRODUCTION GUARD: production's yardstick, exactly.
        assert self.yard['prod']['prod'] == model.h, (self.yard['prod']['prod'], model.h)

    def h(self, v, pos):
        rule = v.get('yard', 'prod')
        y = self.yard[v.get('fw', 'prod')]
        base = y['by_position'][pos] if rule == 'by_position' else y[rule]
        return base * v.get('hm', 1.0)


# ---------------------------------------------------------------------------
# ONE FORECAST under one arm
# ---------------------------------------------------------------------------
def kernel(d2, h, name):
    u2 = d2 / (h * h)
    if name == 'gauss':
        return np.exp(-u2 / 2)
    if name == 'flat':
        return np.ones_like(u2)
    if name == 'epanechnikov':
        return np.clip(1 - u2 / 4, 0, None)
    if name == 'tricube':
        u = np.sqrt(u2) / 2
        return np.where(u < 1, (1 - u ** 3) ** 3, 0.0)
    if name == 'cauchy':
        return 1 / (1 + u2)
    raise ValueError(name)


def blend(col, w, glob, v):
    """The comparable estimate mixed with the league average. Production is
    (sum w x + K g) / (sum w + K) over comparables with a value at that age,
    exactly AgingModel._shrunk. Returns (estimate, league share)."""
    m = ~np.isnan(col)
    ww = w * m
    sw = ww.sum()
    if 'share' in v:
        if sw <= 0:
            return glob, 1.0
        s = v['share']
        return (1 - s) * np.nansum(ww * np.where(m, col, 0.0)) / sw + s * glob, s
    K = v.get('K', SHRINK_K)
    return (np.nansum(ww * np.where(m, col, 0.0)) + K * glob) / (sw + K), K / (sw + K)


def prepare(model, target, pos, age):
    """The target's standardised profile and its same-age, same-position
    candidates, built exactly as AgingModel.project() builds them."""
    ss = target['seasons']; idx = len(ss) - 1
    assert ss[idx]['age'] == age
    sm = target['sm'][age]
    lo = idx if not target['adjacent'].get(age, False) else max(0, idx - (WIN - 1))
    mu, sd = model.stats[pos]
    z = (_profile(ss[lo: idx + 1], sm) - mu) / sd
    cand = model.by_age.get(age, np.array([], int))
    cand = cand[model.pos[cand] == pos] if len(cand) else cand
    return dict(sm=sm, z=z, cand=cand, pos=pos, age=age)


def walk(scale, o, horizon, v):
    """production project() with the arm's distance, weight and blend.
    Returns ({age: level}, weights, [league share at each step])."""
    model = scale.model
    cand, pos, age, sm = o['cand'], o['pos'], o['age'], o['sm']
    shares = []
    if len(cand):
        fw = scale.fw[v.get('fw', 'prod')]
        d2 = (((scale.Z[cand] - o['z']) ** 2) * fw).sum(1)
        w = kernel(d2, scale.h(v, pos), v.get('kernel', 'gauss'))
        compnorm, sh = blend(model.Lser[cand, age - model.AMIN], w,
                             model.glevel.get((pos, age), sm), v)
        shares.append(sh)
    else:
        w, compnorm = None, sm
    level = LAMBDA * sm + (1 - LAMBDA) * compnorm
    out = {age: level}
    for k in range(1, horizon + 1):
        a = age + k - 1
        if (pos, a) not in model.gdelta and not len(cand):
            break
        if len(cand):
            step, sh = blend(model.Dser[cand, a - model.AMIN], w,
                             model.gdelta.get((pos, a), 0.0), v)
            shares.append(sh)
        else:
            step = model.gdelta.get((pos, a), 0.0)
        level += step
        out[a + 1] = level
    return out, w, shares


def project_guarded(model, name, target, age, horizon):
    """AgingModel.project() on the truncated target, for the reproduction guard."""
    assert name not in model.players
    model.players[name] = target
    try:
        return model.project(name, age, horizon)
    finally:
        del model.players[name]


# ---------------------------------------------------------------------------
# SUMMARY: paired, career-clustered
# ---------------------------------------------------------------------------
def summarise(df, arms, rng_seed):
    res = []
    e0 = (df['pred_prod'] - df.actual).abs().to_numpy()
    codes, uniq = pd.factorize(df.name)
    n = len(uniq)
    cnt = np.bincount(codes, minlength=n).astype(float)
    idx = np.random.default_rng(rng_seed).integers(0, n, (BOOTSTRAPS, n))
    cnt_b = cnt[idx].sum(1)
    for v in arms:
        err = df[f'pred_{v}'] - df.actual
        e1 = err.abs().to_numpy()
        d = dict(variant=v, question=QUESTION.get(v, 0), n=len(df), players=n,
                 mae=e1.mean(), rmse=float(np.sqrt((err ** 2).mean())), bias=err.mean(),
                 mae_prod=e0.mean(),
                 rmse_prod=float(np.sqrt(((df['pred_prod'] - df.actual) ** 2).mean())),
                 mean_abs_move=float((df[f'pred_{v}'] - df['pred_prod']).abs().mean()))
        d['pct_change'] = (d['mae'] - d['mae_prod']) / d['mae_prod'] * 100
        d['rmse_pct_change'] = (d['rmse'] - d['rmse_prod']) / d['rmse_prod'] * 100
        if v != 'prod':
            s = np.bincount(codes, weights=e1 - e0, minlength=n)
            boots = s[idx].sum(1) / cnt_b
            d['ci_low'], d['ci_high'] = np.quantile(boots, [.025, .975])
            d['lower_in'] = int((boots < 0).sum())          # of BOOTSTRAPS
        res.append(d)
    return res


# ---------------------------------------------------------------------------
def main():
    start = time.time()
    hashes = {str(p): digest(p) for p in
              [SOURCE, ROOT / '20_CODE/aging_curve.py', ROOT / '20_CODE/skater_forward_projection.py']}
    design = dict(script_version=SCRIPT_VERSION, seed=SEED, folds=FOLDS, bootstraps=BOOTSTRAPS,
                  variants=VARIANTS, historical_only=HIST_ONLY,
                  feature_weight_sets={k: (None if v is None else v.tolist()) for k, v in FW.items()},
                  fixed=dict(lambda_kept=LAMBDA, pooled_weight=SHRINK_K, yardstick_seed=YARD_SEED,
                             yardstick_sample=YARD_SAMPLE),
                  input_hashes=hashes)
    (OUT / f'{PREFIX}_design.json').write_text(json.dumps(design, indent=2, default=str))

    # ---- PART 1: the yardstick on the production fit, as the chain runs it ----
    prod_model = AgingModel(str(SOURCE))
    sc = Scale(prod_model)
    spread = [yardsticks(prod_model, prod_model.Zw, seed=s)['prod'] for s in range(SEED_SPREAD)]
    yinfo = dict(production_h=prod_model.h,
                 all_pairs=sc.yard['prod']['all_pairs'],
                 no_same_career=sc.yard['prod']['no_same_career'],
                 by_position=sc.yard['prod']['by_position'],
                 per_position=sc.yard['prod']['info'],
                 seed_spread=dict(seeds=SEED_SPREAD, min=min(spread), max=max(spread),
                                  sd=float(np.std(spread))),
                 by_feature_weights={k: sc.yard[k]['prod'] for k in FW},
                 pool_entries_per_career=dict(
                     mean=float(pd.Series(prod_model.names).value_counts().mean()),
                     max=int(pd.Series(prod_model.names).value_counts().max()),
                     careers=int(len(set(prod_model.names))),
                     entries=int(len(prod_model.names))))
    design['yardstick_production_fit'] = yinfo
    print('YARDSTICK on the production fit:', json.dumps(yinfo, indent=1, default=str), flush=True)

    # ---- held-out data prep (identical to aging_comp_limit_test v1.0) ------
    raw = pd.read_csv(SOURCE); raw['career'] = raw.Player.map(career_key)
    raw['year'] = raw.Season.str[:2].astype(int) + 2000
    keys = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
            .agg(age=('age', 'first'), GP=('GP', 'sum')))
    bad = [n for n, g in keys[keys.GP >= 20].groupby('career')
           if g.age.duplicated().any() or (g.year - g.age).nunique() > 1]
    design['excluded_ambiguous_age_careers'] = bad
    raw = raw[~raw.career.isin(bad)].copy()
    with tempfile.TemporaryDirectory(prefix='aging_clean_') as cd:
        cp = Path(cd) / 'clean.csv'; raw.drop(columns=['career', 'year']).to_csv(cp, index=False)
        full = AgingModel(str(cp))
    names = sorted(full.players)
    fold = {}; rng = np.random.default_rng(SEED)
    for pos in sorted({p['pos'] for p in full.players.values()}):
        g = np.array([n for n in names if full.players[n]['pos'] == pos]); rng.shuffle(g)
        fold.update({str(n): i % FOLDS for i, n in enumerate(g)})
    obs = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
           .agg(age=('age', 'first'), GP=('GP', 'sum'), WAR=('WAR', 'sum'), pos=('Position', 'last')))
    obs = obs[obs.career.isin(full.players)].copy()
    age_to_year = {}
    for n, g in obs.groupby('career'):
        good = g[g.GP >= 20]
        assert not good.age.duplicated().any(), f'duplicate career-age: {n}'
        age_to_year[n] = {int(r.age): int(r.year) for r in good.itertuples()}
    pos_at = {(r.career, int(r.year)): r.pos for r in obs.itertuples()}
    prod_rows = obs[obs.GP >= 10].copy()
    prod_rows['total'] = prod_rows.WAR * prod_rows.year.map({2019: 82 / 70, 2020: 82 / 56}).fillna(1.0)
    totals = {(r.career, int(r.year)): float(r.total) for r in prod_rows.itertuples()}

    rows, diag, fold_yards = [], [], []
    full_era = {}                                  # fold -> (model, Scale), reused by Q5
    with tempfile.TemporaryDirectory(prefix='aging_arb_') as td:
        for mode in ['career_holdout', 'historical_window']:
            years = [None] if mode == 'career_holdout' else list(range(2017, 2023))
            arms = dict(VARIANTS, **(HIST_ONLY if mode == 'historical_window' else {}))
            for year in years:
                for f in range(FOLDS):
                    if year is None or f not in full_era:
                        tr = raw[raw.career.map(fold).ne(f)].copy()
                        tp = Path(td) / 'train_full.csv'
                        tr.drop(columns=['career', 'year']).to_csv(tp, index=False)
                        fm = AgingModel(str(tp)); full_era[f] = (fm, Scale(fm))
                    if year is None:
                        model, scale = full_era[f]
                    else:
                        train = raw[raw.career.map(fold).ne(f) & (raw.year <= year)].copy()
                        tp = Path(td) / 'train.csv'; train.drop(columns=['career', 'year']).to_csv(tp, index=False)
                        model = AgingModel(str(tp)); scale = Scale(model)
                    assert not any(fold.get(n) == f for n in model.players)
                    fold_yards.append(dict(mode=mode, cutoff=year, fold=f, h=model.h,
                                           h_all_pairs=scale.yard['prod']['all_pairs'],
                                           h_no_same=scale.yard['prod']['no_same_career'],
                                           **{f'h_{p}': x for p, x in scale.yard['prod']['by_position'].items()}))
                    maxage = model.AMIN + model.nages - 1
                    for name in names:
                        if fold[name] != f:
                            continue
                        p = full.players[name]
                        for s in p['seasons'][1:]:
                            age = s['age']; origin = age_to_year[name][age]
                            if year is not None and origin != year:
                                continue
                            hmax = 6 if year is None else 3
                            fut = [x for x in p['raw'] if 1 <= x - age <= hmax]
                            if not fut:
                                continue
                            pos = pos_at[(name, origin)]
                            if pos not in model.stats or not model.AMIN <= age < maxage:
                                continue
                            horizon = min(max(fut) - age, maxage - age)
                            target = truncated_player(p, age); target['pos'] = pos
                            o = prepare(model, target, pos, age)
                            assert name not in set(model.names[o['cand']])
                            ref = project_guarded(model, name, target, age, horizon)
                            preds, info = {}, dict(mode=mode, cutoff=year, fold=f, name=name, pos=pos,
                                                   origin=origin, age=age, sm=o['sm'], tier=tier_of(o['sm']),
                                                   pool_n=len(o['cand']))
                            for v, cfg in arms.items():
                                if cfg.get('pool') == 'full_era':
                                    fm, fs = full_era[f]
                                    if pos not in fm.stats or not fm.AMIN <= age < fm.AMIN + fm.nages - 1:
                                        raise AssertionError('full-era model cannot answer a windowed origin')
                                    fo = prepare(fm, target, pos, age)
                                    lv, w, sh = walk(fs, fo, horizon, {})
                                    fref = project_guarded(fm, name, target, age, horizon)
                                    got = np.array([lv.get(x, np.nan) for x in fref.age])
                                    assert np.allclose(got, fref.projected_war_per_82.to_numpy(),
                                                       atol=1e-10, rtol=0), name
                                else:
                                    lv, w, sh = walk(scale, o, horizon, cfg)
                                preds[v] = lv
                                if w is not None:
                                    info[f'ess_{v}'] = float(w.sum() ** 2 / (w ** 2).sum()) if (w > 0).any() else 0.0
                                    info[f'league_share0_{v}'] = sh[0]
                                    info[f'league_share_last_{v}'] = sh[-1]
                            # REPRODUCTION GUARD against the production code path
                            got = np.array([preds['prod'][x] for x in ref.age])
                            assert np.allclose(got, ref.projected_war_per_82.to_numpy(), atol=1e-10, rtol=0), name
                            # SAME ROWS: every arm answers exactly the ages production does
                            for v in arms:
                                assert all(x in preds[v] for x in preds['prod']), (v, name)
                            diag.append(info)
                            recent, prior = totals.get((name, origin)), totals.get((name, origin - 1))
                            baseline = (.6 * recent + .4 * prior if recent is not None and prior is not None
                                        else recent if recent is not None else prior)
                            base = {k: info[k] for k in ['mode', 'cutoff', 'fold', 'name', 'pos',
                                                         'origin', 'age', 'sm', 'tier']}
                            for fa in fut:
                                if fa not in preds['prod']:
                                    continue
                                h = fa - age
                                assert age_to_year[name][fa] == origin + h
                                rows.append(dict(**base, endpoint='curve', horizon=h, actual=p['raw'][fa],
                                                 **{f'pred_{v}': preds[v][fa] for v in arms}))
                                if h >= 2 and (age + 1) in preds['prod'] and baseline is not None:
                                    act = totals.get((name, origin + h))
                                    if act is not None:
                                        rows.append(dict(**base, endpoint='season_total', horizon=h - 1, actual=act,
                                                         **{f'pred_{v}': ratio_prediction(preds[v], age, baseline, h)
                                                            for v in arms}))
                    print(f'{mode} cutoff={year} fold={f}: {len(rows)} outcomes '
                          f'({time.time() - start:.0f}s)', flush=True)

    df = pd.DataFrame(rows); dg = pd.DataFrame(diag); fy = pd.DataFrame(fold_yards)
    all_arms = list(VARIANTS) + list(HIST_ONLY)
    for mode, g in df.groupby('mode'):
        pc = [f'pred_{v}' for v in (all_arms if mode == 'historical_window' else VARIANTS)]
        assert np.isfinite(g[['actual'] + pc].to_numpy()).all(), mode
    assert not df.duplicated(['mode', 'endpoint', 'name', 'origin', 'horizon']).any()
    df.to_csv(OUT / f'{PREFIX}_predictions.csv', index=False)
    dg.to_csv(OUT / f'{PREFIX}_origins.csv', index=False)
    fy.to_csv(OUT / f'{PREFIX}_fold_yardsticks.csv', index=False)

    res = []
    for (mode, ep), g in df.groupby(['mode', 'endpoint']):
        arms = all_arms if mode == 'historical_window' else list(VARIANTS)
        groups = [('all', g)] + [(f'tier_{t}', x) for t, x in g.groupby('tier')] + \
                 [(f'horizon_{h}', x) for h, x in g.groupby('horizon')] + \
                 [(f'position_{q}', x) for q, x in g.groupby('pos')]
        for i, (lab, part) in enumerate(groups):
            for d in summarise(part, arms, SEED + i):
                res.append(dict(mode=mode, endpoint=ep, group=lab, **d))
    summ = pd.DataFrame(res)
    summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)

    # league share along the walk (production): step 0 vs the last step
    ls = dg[['mode', 'tier', 'league_share0_prod', 'league_share_last_prod', 'ess_prod', 'pool_n']]
    ls.groupby(['mode', 'tier']).median().to_csv(OUT / f'{PREFIX}_league_share.csv')

    assert all(digest(Path(k)) == v for k, v in hashes.items()), 'input or production code changed during test'
    design.update(elapsed_seconds=time.time() - start, rows=len(df), origins=len(dg), players=df.name.nunique())
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(design, indent=2, default=str))
    show = summ[summ.group.isin(['all', 'tier_elite_3plus'])]
    pd.set_option('display.width', 220)
    print(show[['mode', 'endpoint', 'group', 'question', 'variant', 'n', 'players', 'mae', 'pct_change',
                'ci_low', 'ci_high', 'lower_in', 'rmse_pct_change', 'bias', 'mean_abs_move']]
          .to_string(index=False), flush=True)
    print('\nleague share of the comparable estimate, production (median):')
    print(ls.groupby(['mode', 'tier']).median().to_string(), flush=True)
    print(f'complete in {time.time() - start:.0f}s; production files unchanged.', flush=True)


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
