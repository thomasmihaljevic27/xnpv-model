"""aging_comp_limit_test.py -- how many comparables should the aging curve blend?

Test only. Production (aging_curve.py, skater_forward_projection.py) is never
edited or monkeypatched; hashes are checked at start and finish.

QUESTION
--------
The curve scores every same-age, same-position player in the pool with a
Gaussian similarity weight exp(-d^2 / 2h^2), h = 2.526 (the shared bandwidth).
Because h is the MEDIAN pairwise distance, almost nobody scores near zero, so
the "comparable" estimate is close to a lightly tilted age-group average. A
fixed pooled weight SHRINK_K = 10 then pulls toward the plain league average.
This script (1) measures how that plays out, on real ages, and (2) tests,
against held-out careers, rules that limit the blend: keep only the top-N most
similar, drop anyone below a similarity cutoff, or sharpen h -- each with the
pooled weight at 10 and at ~0 (0.01; exactly 0 divides by zero when no
comparable has a value at an age, see _shrunk in aging_curve.py).

Two further arms re-run last session's ideas:
  * evidence_lambda: the kept share of own form rises with career length,
    lambda_i = n_i / (n_i + n0), n0 fixed so the MEDIAN origin keeps 0.55
    (set from the input distribution of n only, before any error is seen).
  * no_shrink: lambda = 1. On the rate outcome this is "no mean reversion"
    (known to lose). On the season-total outcome the curve's level never
    reaches the valuation -- ratio_path() divides by the curve's own base --
    so this isolates whether shrinking the DENOMINATOR (which turns into a
    steeper percentage decline for above-average players) helps or hurts.

DESIGN (inherited from aging_bandwidth_test.py v1.0, same guards)
------------------------------------------------------------------
* Five whole-career folds, stratified by position. Target career never in its
  training bank. Target sees only its own seasons <= the origin age.
* career_holdout: full-era training, raw WAR/82 outcomes 1-6 years ahead.
  historical_window: training seasons <= origin year, origins 2017-2022,
  1-3 years ahead (removes other careers' future seasons).
* Outcome 'curve' = future raw WAR/82 (>=20 GP). Outcome 'season_total' =
  production-style ratio applied to a 60/40 trailing season-total baseline
  (ratio_prediction imported unchanged from aging_bandwidth_test.py: negative
  baseline -> 0, curve base <= 0.25 -> flat, ratio clipped to [0, 3]).
* Every variant is scored on the SAME forecast-outcome pairs.
* The 'prod' arm is recomputed here AND via AgingModel.project(); they must
  agree to 1e-10 on every origin (reproduction guard).
* Test-only exclusion of ambiguous career-age keys (Erik Gustafsson collision)
  from training and evaluation, exactly as v1.0 of the bandwidth test.

TIERS use the player's smoothed per-82 level at the origin -- the quantity the
curve shrinks. elite_3plus = 3.0+ WAR/82.

LIMITS: contemporary reconstructed data, surviving >=20-GP seasons only, no
exit hazard, no dollars, fixed feature weights. Bootstrap resamples careers and
conditions on fitted folds. Many variants are compared, so a small win by one
of them is weak evidence on its own.
"""
from pathlib import Path
import json
import os
import tempfile
import time

import numpy as np
import pandas as pd

from aging_curve import AgingModel, career_key, _profile, LAMBDA, SHRINK_K, WIN
from aging_bandwidth_test import truncated_player, ratio_prediction, digest

SCRIPT_VERSION = '1.0'
SEED = 20260913
FOLDS = 5
BOOTSTRAPS = 2000
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
SOURCE = OUT / 'WAR_with_age.csv'
PREFIX = 'aging_comp_limit_test'
POOL_OFF = 0.01          # "pooled weight removed"; 0 itself divides by zero
ELITE = 3.0              # WAR/82, smoothed origin level
TIERS = [(-np.inf, 0.0, 'below_0'), (0.0, 1.5, '0_to_1.5'),
         (1.5, ELITE, '1.5_to_3'), (ELITE, np.inf, 'elite_3plus')]

# Each arm changes ONLY the keys it names; everything else is production.
#   hm   = multiplier on the shared bandwidth h (smaller = stricter similarity)
#   topk = keep only the N highest-weighted comparables
#   cut  = zero any comparable whose similarity weight is below this (max 1.0)
#   K    = pooled weight on the league age-position average (production 10)
#   lam  = kept share of own form (production 0.55)
VARIANTS = {
    'prod':            {},
    'pool_off':        {'K': POOL_OFF},
    'h_half':          {'hm': 0.5},
    'h_quarter':       {'hm': 0.25},
    'h_half_pool_off': {'hm': 0.5, 'K': POOL_OFF},
    'top50':           {'topk': 50},
    'top25':           {'topk': 25},
    'top10':           {'topk': 10},
    'top25_pool_off':  {'topk': 25, 'K': POOL_OFF},
    'top10_pool_off':  {'topk': 10, 'K': POOL_OFF},
    'cut50':           {'cut': 0.5},
    'cut80':           {'cut': 0.8},
    'cut80_pool_off':  {'cut': 0.8, 'K': POOL_OFF},
    'evidence_lambda': {'lam': 'evidence'},
    'no_shrink':       {'lam': 1.0},
}


def tier_of(x):
    for lo, hi, lab in TIERS:
        if lo <= x < hi:
            return lab
    raise ValueError(x)


def variant_weights(h, d2, v):
    """Similarity weights under one arm. d2 = squared weighted distance from
    the target to each same-age same-position candidate (production scale)."""
    hh = h * v.get('hm', 1.0)
    w = np.exp(-d2 / (2 * hh * hh))
    k = v.get('topk')
    if k is not None and len(w) > k:
        keep = np.argpartition(-w, k - 1)[:k]
        m = np.zeros(len(w), bool); m[keep] = True
        w = np.where(m, w, 0.0)
    c = v.get('cut')
    if c is not None:
        w = np.where(w >= c, w, 0.0)
    return w


def shrunk(col, w, glob, K):
    """Same arithmetic as AgingModel._shrunk, with K as an argument."""
    m = ~np.isnan(col); ww = w * m
    return (np.nansum(ww * np.where(m, col, 0.0)) + K * glob) / (ww.sum() + K)


def prepare(model, target, pos, age):
    """Target profile, candidate rows and distances -- built exactly as
    AgingModel.project() builds them (same fallback to a single season when
    the previous qualifying season is not one year earlier)."""
    ss = target['seasons']; idx = len(ss) - 1
    assert ss[idx]['age'] == age
    sm = target['sm'][age]
    lo = idx if not target['adjacent'].get(age, False) else max(0, idx - (WIN - 1))
    mu, sd = model.stats[pos]
    z = ((_profile(ss[lo: idx + 1], sm) - mu) / sd) * np.sqrt(model.fw)
    cand = model.by_age.get(age, np.array([], int))
    cand = cand[model.pos[cand] == pos] if len(cand) else cand
    d2 = ((model.Zw[cand] - z) ** 2).sum(1) if len(cand) else np.array([])
    return dict(sm=sm, cand=cand, d2=d2, pos=pos, age=age, n=len(ss))


def walk(model, o, horizon, v, lam):
    """Production project() logic with the arm's weights, K and lambda.
    Returns ({age: level}, weights, compnorm)."""
    K = v.get('K', SHRINK_K)
    cand, pos, age, sm = o['cand'], o['pos'], o['age'], o['sm']
    if len(cand):
        w = variant_weights(model.h, o['d2'], v)
        compnorm = shrunk(model.Lser[cand, age - model.AMIN], w,
                          model.glevel.get((pos, age), sm), K)
    else:
        w, compnorm = None, sm
    level = lam * sm + (1 - lam) * compnorm
    out = {age: level}
    for k in range(1, horizon + 1):
        a = age + k - 1
        if (pos, a) not in model.gdelta and not len(cand):
            break
        if len(cand):
            step = shrunk(model.Dser[cand, a - model.AMIN], w,
                          model.gdelta.get((pos, a), 0.0), K)
        else:
            step = model.gdelta.get((pos, a), 0.0)
        level += step
        out[a + 1] = level
    return out, w, compnorm


def lam_for(v, n, n0):
    lam = v.get('lam', LAMBDA)
    return n / (n + n0) if lam == 'evidence' else lam


# ---------------------------------------------------------------------------
# PART 1 -- AUDIT: what the blend actually does, production model, real ages
# ---------------------------------------------------------------------------
def audit(model):
    """One row per comparables-pool entry (player x age), scored the way the
    production projection scores it (self excluded)."""
    rows = []
    maxage = model.AMIN + model.nages - 1
    for r in range(len(model.names)):
        name, pos, age = model.names[r], model.pos[r], int(model.agek[r])
        p = model.players[name]
        if p['pos'] != pos:
            continue
        cand = model.by_age[age]; cand = cand[(model.pos[cand] == pos) & (model.names[cand] != name)]
        if not len(cand):
            continue
        d2 = ((model.Zw[cand] - model.Zw[r]) ** 2).sum(1)
        sm = p['sm'][age]; glev = model.glevel.get((pos, age), sm)
        Lc = model.Lser[cand, age - model.AMIN]
        o = dict(sm=sm, cand=cand, d2=d2, pos=pos, age=age, n=0)
        hor = min(8, maxage - age - 1)
        lv, w, cn = walk(model, o, hor, {}, LAMBDA)
        _, _, cn_off = walk(model, o, 0, {'K': POOL_OFF}, LAMBDA)
        sw = w.sum()
        # counterfactual path: same yearly steps, walked from the UNSHRUNK level
        raw = {a: x - lv[age] + sm for a, x in lv.items()}
        row = dict(name=name, pos=pos, age=age, sm=sm, tier=tier_of(sm), glev=glev,
                   pool_n=len(cand), sum_w=sw, ess=sw ** 2 / (w ** 2).sum(),
                   league_share=SHRINK_K / (sw + SHRINK_K),
                   nnz_w_above_0_5=int((w >= 0.5).sum()),
                   compnorm=cn, compnorm_pool_off=cn_off, anchor=lv[age],
                   n_at_level=int((np.abs(Lc - sm) <= 0.5).sum()),
                   wshare_at_level=float(w[np.abs(Lc - sm) <= 0.5].sum() / sw),
                   n_ge3=int((Lc >= ELITE).sum()), wshare_ge3=float(w[Lc >= ELITE].sum() / sw))
        # gap kept: share of (own level - age/position average) that survives
        gap = sm - glev
        row['gap'] = gap
        row['comp_gap_kept'] = (cn - glev) / gap if abs(gap) > 0.25 else np.nan
        row['comp_gap_kept_pool_off'] = (cn_off - glev) / gap if abs(gap) > 0.25 else np.nan
        # percentage path after valuation (valuation = age+1, like ratio_path)
        if (age + 1) in lv and lv[age + 1] > 0.25 and raw[age + 1] > 0.25:
            for k in (2, 4, 6):
                if (age + 1 + k) in lv:
                    row[f'ratio_shrunk_k{k}'] = lv[age + 1 + k] / lv[age + 1]
                    row[f'ratio_unshrunk_k{k}'] = raw[age + 1 + k] / raw[age + 1]
        rows.append(row)
    return pd.DataFrame(rows)


def audit_tables(a):
    out = []
    for (pos, tier), g in [(('all', 'all'), a)] + list(a.groupby(['pos', 'tier'])) + \
            [(('all', t), g) for t, g in a.groupby('tier')]:
        d = dict(pos=pos, tier=tier, n=len(g), mean_level=g.sm.mean(),
                 median_pool_n=g.pool_n.median(), median_sum_w=g.sum_w.median(),
                 median_league_share=g.league_share.median(), median_ess=g.ess.median(),
                 median_ess_share_of_pool=(g.ess / g.pool_n).median(),
                 median_n_w_above_0_5=g.nnz_w_above_0_5.median(),
                 median_n_at_level=g.n_at_level.median(),
                 median_wshare_at_level=g.wshare_at_level.median(),
                 median_comp_gap_kept=g.comp_gap_kept.median(),
                 median_comp_gap_kept_pool_off=g.comp_gap_kept_pool_off.median())
        d['median_anchor_gap_kept'] = LAMBDA + (1 - LAMBDA) * d['median_comp_gap_kept']
        for k in (2, 4, 6):
            if f'ratio_shrunk_k{k}' in g:
                d[f'median_ratio_shrunk_k{k}'] = g[f'ratio_shrunk_k{k}'].median()
                d[f'median_ratio_unshrunk_k{k}'] = g[f'ratio_unshrunk_k{k}'].median()
        out.append(d)
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# PART 2 -- HELD-OUT TEST
# ---------------------------------------------------------------------------
def summarise(df, rng_seed):
    """Paired MAE/bias/RMSE per arm; career-cluster bootstrap on the MAE
    difference vs prod. Negative delta = the arm beats production."""
    res = []
    e0 = (df['pred_prod'] - df.actual).abs().to_numpy()
    codes, uniq = pd.factorize(df.name)
    n = len(uniq)
    cnt = np.bincount(codes, minlength=n).astype(float)
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, n, (BOOTSTRAPS, n))
    cnt_b = cnt[idx].sum(1)
    for v in VARIANTS:
        err = df[f'pred_{v}'] - df.actual
        e1 = err.abs().to_numpy()
        d = dict(variant=v, n=len(df), players=n, mae=e1.mean(), bias=err.mean(),
                 rmse=float(np.sqrt((err ** 2).mean())), mae_prod=e0.mean())
        d['delta'] = d['mae'] - d['mae_prod']
        d['pct_change'] = d['delta'] / d['mae_prod'] * 100
        if v != 'prod':
            s = np.bincount(codes, weights=e1 - e0, minlength=n)
            boots = s[idx].sum(1) / cnt_b
            d['ci_low'], d['ci_high'] = np.quantile(boots, [.025, .975])
        res.append(d)
    return res


def main():
    start = time.time()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in
              [SOURCE, ROOT / '20_CODE/aging_curve.py', ROOT / '20_CODE/skater_forward_projection.py']}
    design = dict(script_version=SCRIPT_VERSION, seed=SEED, folds=FOLDS, bootstraps=BOOTSTRAPS,
                  variants=VARIANTS, fixed=dict(lambda_kept=LAMBDA, pooled_weight=SHRINK_K),
                  pool_off_value=POOL_OFF, elite_threshold=ELITE, input_hashes=hashes)
    (OUT / f'{PREFIX}_design.json').write_text(json.dumps(design, indent=2, default=str))

    # ---- audit on the production fit (all careers, as the chain runs it) --
    prod_model = AgingModel(str(SOURCE))
    print(f'production fit: {len(prod_model.players)} careers, {len(prod_model.names)} pool entries, '
          f'h={prod_model.h:.3f}', flush=True)
    a = audit(prod_model)
    a.to_csv(OUT / f'{PREFIX}_audit_rows.csv', index=False)
    at = audit_tables(a)
    at.to_csv(OUT / f'{PREFIX}_audit.csv', index=False)
    for pos in ['F', 'D']:
        b = a[a.pos == pos]
        slope = np.polyfit(b.gap, b.compnorm - b.glev, 1)[0]
        design[f'audit_slope_comp_gap_{pos}'] = slope
        design[f'audit_anchor_gap_kept_{pos}'] = LAMBDA + (1 - LAMBDA) * slope
    print(at[at.pos == 'all'].T.to_string(), flush=True)

    # ---- held-out data prep (identical to aging_bandwidth_test v1.0) --------
    raw = pd.read_csv(SOURCE); raw['career'] = raw.Player.map(career_key)
    raw['year'] = raw.Season.str[:2].astype(int) + 2000
    keys = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
            .agg(age=('age', 'first'), GP=('GP', 'sum')))
    bad = [n for n, g in keys[keys.GP >= 20].groupby('career')
           if g.age.duplicated().any() or (g.year - g.age).nunique() > 1]
    design['excluded_ambiguous_age_careers'] = bad
    print('test-only ambiguous-age exclusions:', bad, flush=True)
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

    # evidence-lambda anchor: n0 so the median origin keeps exactly LAMBDA.
    # Uses the distribution of career length at origin (an input), never errors.
    ns = [i + 1 for p in full.players.values() for i in range(1, len(p['seasons']))]
    n_med = float(np.median(ns)); n0 = n_med * (1 - LAMBDA) / LAMBDA
    design['evidence_lambda'] = dict(median_n=n_med, n0=n0)
    (OUT / f'{PREFIX}_design.json').write_text(json.dumps(design, indent=2, default=str))

    rows, diag = [], []
    with tempfile.TemporaryDirectory(prefix='aging_comp_') as td:
        for mode in ['career_holdout', 'historical_window']:
            years = [None] if mode == 'career_holdout' else list(range(2017, 2023))
            for year in years:
                for f in range(FOLDS):
                    train = raw[raw.career.map(fold).ne(f)].copy()
                    if year is not None:
                        train = train[train.year <= year]
                    tp = Path(td) / 'train.csv'; train.drop(columns=['career', 'year']).to_csv(tp, index=False)
                    model = AgingModel(str(tp))
                    assert not any(fold.get(n) == f for n in model.players)
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
                            # reproduction guard against the production code path
                            assert name not in model.players and name not in set(model.names[o['cand']])
                            model.players[name] = target
                            try:
                                ref = model.project(name, age, horizon)
                            finally:
                                del model.players[name]
                            preds = {}
                            info = dict(mode=mode, cutoff=year, fold=f, name=name, pos=pos, origin=origin,
                                        age=age, sm=o['sm'], tier=tier_of(o['sm']), n_seasons=o['n'],
                                        pool_n=len(o['cand']))
                            for v, cfg in VARIANTS.items():
                                lv, w, cn = walk(model, o, horizon, cfg, lam_for(cfg, o['n'], n0))
                                preds[v] = lv
                                if w is not None:
                                    info[f'nnz_{v}'] = int((w > 0).sum())
                                    info[f'league_share_{v}'] = cfg.get('K', SHRINK_K) / (w.sum() + cfg.get('K', SHRINK_K))
                            got = np.array([preds['prod'][x] for x in ref.age])
                            assert np.allclose(got, ref.projected_war_per_82.to_numpy(), atol=1e-10, rtol=0), name
                            assert all(preds[v].keys() == preds['prod'].keys() for v in VARIANTS)
                            diag.append(info)
                            recent, prior = totals.get((name, origin)), totals.get((name, origin - 1))
                            baseline = (.6 * recent + .4 * prior if recent is not None and prior is not None
                                        else recent if recent is not None else prior)
                            for fa in fut:
                                if fa not in preds['prod']:
                                    continue
                                h = fa - age
                                assert age_to_year[name][fa] == origin + h
                                rows.append(dict(**{k: info[k] for k in ['mode', 'cutoff', 'fold', 'name', 'pos',
                                                                          'origin', 'age', 'sm', 'tier', 'n_seasons']},
                                                 endpoint='curve', horizon=h, actual=p['raw'][fa],
                                                 **{f'pred_{v}': preds[v][fa] for v in VARIANTS}))
                                if h >= 2 and (age + 1) in preds['prod'] and baseline is not None:
                                    act = totals.get((name, origin + h))
                                    if act is not None:
                                        rows.append(dict(**{k: info[k] for k in ['mode', 'cutoff', 'fold', 'name', 'pos',
                                                                                  'origin', 'age', 'sm', 'tier', 'n_seasons']},
                                                         endpoint='season_total', horizon=h - 1, actual=act,
                                                         **{f'pred_{v}': ratio_prediction(preds[v], age, baseline, h)
                                                            for v in VARIANTS}))
                    print(f'{mode} cutoff={year} fold={f}: {len(rows)} outcomes '
                          f'({time.time() - start:.0f}s)', flush=True)

    df = pd.DataFrame(rows); dg = pd.DataFrame(diag)
    pc = [f'pred_{v}' for v in VARIANTS]
    assert np.isfinite(df[['actual'] + pc].to_numpy()).all()
    assert not df.duplicated(['mode', 'endpoint', 'name', 'origin', 'horizon']).any()
    df.to_csv(OUT / f'{PREFIX}_predictions.csv', index=False)
    dg.to_csv(OUT / f'{PREFIX}_origins.csv', index=False)

    res = []
    for (mode, ep), g in df.groupby(['mode', 'endpoint']):
        groups = [('all', g)] + [(f'tier_{t}', x) for t, x in g.groupby('tier')] + \
                 [(f'horizon_{h}', x) for h, x in g.groupby('horizon')] + \
                 [(f'position_{q}', x) for q, x in g.groupby('pos')] + \
                 [(f'elite_{q}', x) for q, x in g[g.tier == 'elite_3plus'].groupby('pos')]
        for i, (lab, part) in enumerate(groups):
            for d in summarise(part, SEED + i):
                res.append(dict(mode=mode, endpoint=ep, group=lab, **d))
    summ = pd.DataFrame(res)
    summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)
    assert all(digest(ROOT / k) == v for k, v in hashes.items()), 'input or production code changed during test'

    design.update(elapsed_seconds=time.time() - start, rows=len(df), origins=len(dg), players=df.name.nunique())
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(design, indent=2, default=str))
    show = summ[summ.group.isin(['all', 'tier_elite_3plus'])]
    print(show[['mode', 'endpoint', 'group', 'variant', 'n', 'mae', 'pct_change', 'ci_low', 'ci_high', 'bias']]
          .to_string(index=False), flush=True)
    print(f'complete in {time.time() - start:.0f}s; production files unchanged.', flush=True)


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
