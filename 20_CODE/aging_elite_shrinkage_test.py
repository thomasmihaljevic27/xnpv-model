"""Does the curve's pooling weight or its similarity bandwidth deflate elite players?

Run from the repository root. Outputs go to OUTPUT_DIR under a new prefix; no
production artifact is read-modified or overwritten. Production code is hashed
before and after and the run asserts it did not change.

THE QUESTION
------------
`aging_curve.py` builds a player's anchor in two shrinkage steps:

    compnorm = (sum(w_i * L_i) + SHRINK_K * glevel[pos, age]) / (sum(w_i) + SHRINK_K)
    anchor   = LAMBDA * own_smoothed_level + (1 - LAMBDA) * compnorm

with SHRINK_K = 10 and LAMBDA = 0.55, and comparable weights

    w_i = exp(-d_i^2 / (2 * h^2)),   h = median within-position pairwise distance.

Two separate mechanisms can push an unusual player's anchor toward the
position-and-age average, and they are easy to confuse:

  (A) POOLING WEIGHT. w_i is an UNNORMALISED kernel weight, so sum(w_i) is
      smaller for a player who sits far from the cloud. SHRINK_K is a fixed
      pseudo-count against that smaller sum, so an elite player's compnorm
      leans harder on glevel than a median player's does.

  (B) BANDWIDTH. h is the median pairwise distance in the same weighted-z
      space the weights are computed in, which makes the kernel about as wide
      as the whole candidate cloud. A near-flat kernel barely distinguishes a
      close comparable from a distant one, so the comparable-weighted level is
      itself close to the position-and-age mean BEFORE SHRINK_K is applied.

If (B) dominates, changing SHRINK_K will move elite projections very little,
because the comparable side is already near the broad average by construction.
This test separates them by sweeping each lever alone and then jointly -- the
cell `40_DOCS/Aging_Yardstick_Comparison.md` explicitly records as untested.

WHY BIAS, NOT ONLY MAE
----------------------
Pooled MAE is dominated by the middle of the distribution, so a systematic
under-projection confined to the top band is nearly invisible in it. The
production `validate()` table and the bandwidth test both report pooled error
only. This test reports SIGNED mean error within fixed anchor-level bands, so
structural deflation shows up as a negative bias that grows with level, and
reports the anchor itself so the size of the pull can be read directly.

WHY THE RATIO ENDPOINT MATTERS MORE THAN THE CURVE ENDPOINT
-----------------------------------------------------------
`skater_forward_projection.ratio_path()` takes `base = levels[0]` -- the
mean-reverted level -- and prices off `l / base`, then applies that ratio to
the player's UNSHRUNK 60/40 raw-WAR anchor. The forward steps added to the
numerator are age-conditional deltas in absolute WAR units. A shrunken base
therefore does not cancel out of the ratio: it shrinks the denominator while
the numerator's increments stay the same size, which steepens the projected
percentage decline. So the season-total endpoint can move even where the
per-82 curve endpoint barely does, and it is the one that reaches dollars.

ARMS
----
  production   SHRINK_K = 10, h as fitted                    (baseline)
  K_eps / K_5 / K_20                                         lever (A) alone
  h_0.70 / h_0.50 / h_0.35   h scaled down                   lever (B) alone
  h_0.50_K_eps                                               (A) and (B) jointly
  reliability_lambda   LAMBDA_i = n_i / (n_i + n0), n_i = the player's own
                       qualifying seasons at the origin, n0 set from the
                       TRAINING median so the arm reproduces LAMBDA = 0.55 at
                       a median-length record and only redistributes around it

Nothing here is proposed for production. The arms exist to locate the lever.

WHAT THIS DOES NOT TEST
-----------------------
Exit hazard, survival weights, dollar conversion, contract-level NPV, or the
back-test. Evaluation conditions on observed seasons of at least 20 GP, so it
inherits the same survivorship conditioning as the bandwidth test.

USAGE
-----
    python 20_CODE/aging_elite_shrinkage_test.py

REQUIRES `OUTPUT_DIR/WAR_with_age.csv`, which `age_join.py` builds from the
PuckPedia birthdate export. That export is confidential vendor data and is not
in the repository, so this test cannot run in an environment that lacks it.
"""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import time

import numpy as np
import pandas as pd

import aging_curve
from aging_curve import AgingModel, career_key
# Imported rather than re-implemented so the two tests can never drift apart on
# what "hold this career out" means. A private copy is exactly how two competing
# holdout conventions end up in one repository.
from aging_bandwidth_test import truncated_player, ratio_prediction

SCRIPT_VERSION = '1.0'
SEED = 20260914
FOLDS = 5
BOOTSTRAPS = 2000
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
SOURCE = OUT / 'WAR_with_age.csv'
PREFIX = 'aging_elite_shrinkage_test'

# Production values, captured at import so an arm can always restore them.
BASE_K = aging_curve.SHRINK_K
BASE_LAMBDA = aging_curve.LAMBDA

# Fixed anchor-level bands, in WAR per 82 games, declared before any error is
# examined. Fixed cutoffs rather than sample quantiles: a quantile binning
# computed on the evaluation set would move with the arm being tested.
BANDS = [(-np.inf, 0.0, 'neg'), (0.0, 1.0, 'lo'), (1.0, 2.0, 'mid'),
         (2.0, 3.0, 'high'), (3.0, np.inf, 'elite')]

# SHRINK_K IS ALSO A DIVIDE-BY-ZERO GUARD, not only a weighting choice.
# `_shrunk` masks the candidate weights to those with an OBSERVED value at the
# age being estimated, so sum(w) is exactly 0 whenever no comparable has one --
# routine for the delta column at the oldest ages and at the end of a career.
# At SHRINK_K = 0 that is 0/0 and the projection returns NaN. Setting the arm to
# a true zero therefore tests "remove the guard" rather than "remove the
# pooling", which is not the question. K_eps is the smallest pooling weight that
# leaves the estimator defined: the comparable side takes essentially all the
# weight wherever any comparable exists, and the global target is used only
# where there is literally no comparable information to use instead.
K_EPS = 1e-9

# (name, shrink_k, h_scale, reliability_lambda)
#
# NOTE ON THE h ARMS. Narrowing h shrinks every w_i, so it mechanically RAISES
# reliance on the global average at a fixed SHRINK_K -- the opposite of the
# intended effect. The h arms and the K arms therefore push in opposite
# directions on the pooling share, and only the joint cell separates "sharpen
# the comparable set" from "lean less on the broad average".
ARMS = [
    ('production',         BASE_K, 1.00, False),
    ('K_eps',              K_EPS,  1.00, False),
    ('K_5',                5.0,    1.00, False),
    ('K_20',               20.0,   1.00, False),
    ('h_0.70',             BASE_K, 0.70, False),
    ('h_0.50',             BASE_K, 0.50, False),
    ('h_0.35',             BASE_K, 0.35, False),
    ('h_0.50_K_eps',       K_EPS,  0.50, False),
    ('reliability_lambda', BASE_K, 1.00, True),
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def band_of(level):
    for lo, hi, tag in BANDS:
        if lo <= level < hi:
            return tag
    return 'elite'


def reliability_lambda(n_seasons, n0):
    """Weight on the player's own form, rising with the length of his record.

    This is the standard reliability form lambda = n / (n + n0). n0 is solved
    from the TRAINING pool's median record length so that a median-length
    record reproduces the locked LAMBDA exactly; the arm therefore adds no new
    tuned constant and only redistributes weight between short and long
    records. Bounded away from 0 and 1 so no player is either fully shrunk or
    fully unshrunk.
    """
    return float(np.clip(n_seasons / (n_seasons + n0), 0.20, 0.90))


def project_all_arms(model, name, target, age, horizon, n0):
    """One fold fit, one candidate set, every arm.

    Arms differ only in what happens AFTER the comparable set is assembled, so
    the expensive part (fitting the bank, standardising, computing the shared
    bandwidth) is done once per fold and shared. Each arm restores the module
    constants it touched in a finally block, so a raise inside one arm cannot
    leak a setting into the next.
    """
    if target['pos'] not in model.stats or not model.AMIN <= age < model.AMIN + model.nages - 1:
        return None
    horizon = min(horizon, model.AMIN + model.nages - 1 - age)
    if horizon < 1:
        return None
    # The target is never in the bank: folds hold whole careers out. project()
    # reads self.players, so the truncated history is installed for the call
    # and removed immediately afterwards.
    assert name not in model.players and name not in set(model.names)
    model.players[name] = truncated_player(target, age)
    base_h = model.h
    n_seasons = len(model.players[name]['seasons'])
    out = {}
    try:
        for arm, k, hs, rel in ARMS:
            try:
                aging_curve.SHRINK_K = k
                model.h = base_h * hs
                aging_curve.LAMBDA = (reliability_lambda(n_seasons, n0) if rel
                                      else BASE_LAMBDA)
                tr = model.project(name, age, horizon)
                out[arm] = dict(zip(tr.age, tr.projected_war_per_82))
            finally:
                aging_curve.SHRINK_K = BASE_K
                aging_curve.LAMBDA = BASE_LAMBDA
                model.h = base_h
        # Every arm must span the same ages, or the paired comparison is not paired.
        ages = {a: sorted(v) for a, v in out.items()}
        assert all(v == ages['production'] for v in ages.values()), 'arm age grids differ'
        return out, n_seasons
    finally:
        del model.players[name]


def cluster_summary(g, arm):
    """Paired against production, resampling whole careers rather than seasons.

    A player contributes many correlated forecast dates, so the resample unit is
    the career. The interval conditions on the fitted folds and does not refit;
    it is exploratory, exactly as in the bandwidth test.
    """
    e_prod = (g['pred_production'] - g.actual).abs()
    e_arm = (g[f'pred_{arm}'] - g.actual).abs()
    per = pd.DataFrame({'name': g.name, 'delta': e_arm - e_prod}) \
        .groupby('name').delta.agg(['sum', 'count'])
    rng = np.random.default_rng(SEED)
    sums, counts, n = per['sum'].to_numpy(), per['count'].to_numpy(), len(per)
    boots = [sums[i].sum() / counts[i].sum()
             for i in (rng.integers(0, n, n) for _ in range(BOOTSTRAPS))]
    return dict(
        arm=arm, n=len(g), players=n,
        mae=float(e_arm.mean()), mae_production=float(e_prod.mean()),
        delta_mae=float((e_arm - e_prod).mean()),
        improvement_percent=float((e_prod.mean() - e_arm.mean()) / e_prod.mean() * 100),
        delta_ci_low=float(np.quantile(boots, .025)),
        delta_ci_high=float(np.quantile(boots, .975)),
        rmse=float(np.sqrt(np.mean((g[f'pred_{arm}'] - g.actual) ** 2))),
        # Signed error. This is the column the elite question turns on: a
        # structurally deflated projection shows up here as a negative number
        # that grows with the level band, not in MAE.
        bias=float((g[f'pred_{arm}'] - g.actual).mean()),
        bias_production=float((g['pred_production'] - g.actual).mean()))


def main():
    start = time.time()
    # OUTPUT_DIR is not required to sit inside the repository, so a watched
    # path is keyed by its repo-relative name only when it actually is one.
    watched = [SOURCE, ROOT / '20_CODE/aging_curve.py',
               ROOT / '20_CODE/skater_forward_projection.py',
               ROOT / '20_CODE/aging_bandwidth_test.py']
    def key(p):
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return p.name
    watched = [(key(p), p) for p in watched]
    hashes = {k: digest(p) for k, p in watched}
    design = dict(
        script_version=SCRIPT_VERSION, seed=SEED, folds=FOLDS, bootstraps=BOOTSTRAPS,
        arms=[dict(name=a, shrink_k=k, h_scale=h, reliability_lambda=r) for a, k, h, r in ARMS],
        baseline='production', bands=[[str(lo), str(hi), t] for lo, hi, t in BANDS],
        fixed=dict(lambda_kept=BASE_LAMBDA, pooled_weight=BASE_K,
                   features='unchanged', profiles='unchanged', projection_rules='unchanged'),
        primary='Five-fold whole-career holdout; one-to-six-year raw WAR/82 outcomes with >=20 GP',
        secondary='Season-total projection via the production ratio guards; same surviving observations',
        temporal='Same folds, training seasons <= origin year, origins 2017-2022, one-to-three-year outcomes',
        reported='MAE, RMSE and SIGNED BIAS within fixed anchor-level bands, plus the anchor itself',
        limitations=[
            'Contemporary reconstructed data, not vintage snapshots',
            'Observed surviving seasons only; no exit/hazard, survival, dollar or contract test',
            'Full-era training admits future seasons of OTHER careers; the temporal check removes those',
            'Arms sweep two levers and one lambda rule; feature weights and profiles are held fixed',
            'Bootstrap conditions on the fitted folds and does not refit',
            'Many arms on one evaluation set: treat a winning arm as a lead to re-test, not a result'],
        input_hashes=hashes)
    # Written before any model is fitted, so the protocol cannot be edited after
    # the errors are seen.
    (OUT / f'{PREFIX}_design.json').write_text(json.dumps(design, indent=2))

    raw = pd.read_csv(SOURCE)
    raw['career'] = raw.Player.map(career_key)
    raw['year'] = raw.Season.str[:2].astype(int) + 2000
    # Same test-only exclusion the bandwidth test makes, for the same reason and
    # from BOTH arms including training: a career whose cleaned key collides
    # carries two qualifying seasons at one age. Not a production repair.
    keys = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
            .agg(age=('age', 'first'), GP=('GP', 'sum')))
    bad = [n for n, g in keys[keys.GP >= 20].groupby('career')
           if g.age.duplicated().any() or (g.year - g.age).nunique() > 1]
    design['excluded_ambiguous_age_careers'] = bad
    (OUT / f'{PREFIX}_design.json').write_text(json.dumps(design, indent=2))
    print('Test-only ambiguous-age exclusions:', bad, flush=True)
    raw = raw[~raw.career.isin(bad)].copy()

    with tempfile.TemporaryDirectory(prefix='aging_clean_') as clean_dir:
        clean_path = Path(clean_dir) / 'clean.csv'
        raw.drop(columns=['career', 'year']).to_csv(clean_path, index=False)
        full = AgingModel(str(clean_path))
    names = sorted(full.players)

    rng = np.random.default_rng(SEED)
    fold = {}
    for pos in sorted({p['pos'] for p in full.players.values()}):
        group = np.array([n for n in names if full.players[n]['pos'] == pos])
        rng.shuffle(group)
        fold.update({str(n): i % FOLDS for i, n in enumerate(group)})

    obs = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
           .agg(age=('age', 'first'), GP=('GP', 'sum'), WAR=('WAR', 'sum'), pos=('Position', 'last')))
    obs = obs[obs.career.isin(full.players)].copy()
    age_to_year = {}
    for name, g in obs.groupby('career'):
        good = g[g.GP >= 20]
        assert not good.age.duplicated().any(), f'duplicate career-age: {name}'
        age_to_year[name] = {int(r.age): int(r.year) for r in good.itertuples()}
    # Season totals keep missed games (availability is signal, D20) and rescale
    # only the two shortened schedules.
    prod = obs[obs.GP >= 10].copy()
    prod['total'] = prod.WAR * prod.year.map({2019: 82 / 70, 2020: 82 / 56}).fillna(1.0)
    totals = {(r.career, int(r.year)): float(r.total) for r in prod.itertuples()}

    rows, diagnostics = [], []
    with tempfile.TemporaryDirectory(prefix='aging_elite_') as td:
        for mode in ['career_holdout', 'historical_window']:
            years = [None] if mode == 'career_holdout' else list(range(2017, 2023))
            for year in years:
                for f in range(FOLDS):
                    train = raw[raw.career.map(fold).ne(f)].copy()
                    if year is not None:
                        train = train[train.year <= year]
                    training_path = Path(td) / 'training.csv'
                    train.drop(columns=['career', 'year']).to_csv(training_path, index=False)
                    model = AgingModel(str(training_path))
                    assert not any(fold.get(n) == f for n in model.players)
                    # n0 is solved on TRAINING careers only, so the reliability
                    # arm never sees the held-out players it is scored on.
                    n_med = float(np.median([len(p['seasons']) for p in model.players.values()]))
                    n0 = n_med * (1 - BASE_LAMBDA) / BASE_LAMBDA
                    for name in names:
                        if fold[name] != f:
                            continue
                        p = full.players[name]
                        for s in p['seasons'][1:]:
                            age = s['age']
                            origin = age_to_year[name][age]
                            if year is not None and origin != year:
                                continue
                            horizon = 6 if year is None else 3
                            fut = [a for a in p['raw'] if 1 <= a - age <= horizon]
                            if not fut:
                                continue
                            # Position as at the forecast origin, not career end.
                            actual_pos = obs[(obs.career == name) & (obs.year == origin)].pos.iloc[0]
                            target = dict(p)
                            target['pos'] = actual_pos
                            res = project_all_arms(model, name, target, age, max(fut) - age, n0)
                            if res is None:
                                continue
                            arms, n_seasons = res
                            own = p['sm'][age]          # trailing smoothed level at the origin
                            info = dict(mode=mode, fold=f, name=name, pos=actual_pos,
                                        origin=origin, age=age, own_level=own,
                                        band=band_of(own), star=s['w82'] >= 3,
                                        record_seasons=n_seasons,
                                        **{f'anchor_{a}': arms[a][age] for a, *_ in ARMS})
                            diagnostics.append(info)
                            recent, prior = totals.get((name, origin)), totals.get((name, origin - 1))
                            baseline = (.6 * recent + .4 * prior if recent is not None and prior is not None
                                        else recent if recent is not None else prior)
                            for fa in fut:
                                if fa not in arms['production']:
                                    continue
                                h = fa - age
                                assert age_to_year[name][fa] == origin + h
                                rows.append(dict(**info, endpoint='curve', horizon=h,
                                                 actual=p['raw'][fa],
                                                 **{f'pred_{a}': arms[a][fa] for a, *_ in ARMS}))
                                # The ratio endpoint: this is where a shrunken
                                # base turns into a steeper percentage path.
                                if h >= 2 and (age + 1) in arms['production'] and baseline is not None:
                                    actual = totals.get((name, origin + h))
                                    if actual is not None:
                                        rows.append(dict(
                                            **info, endpoint='season_total', horizon=h - 1, actual=actual,
                                            **{f'pred_{a}': ratio_prediction(arms[a], age, baseline, h)
                                               for a, *_ in ARMS}))
                    print(f'{mode} cutoff={year} fold={f}: cumulative {len(rows)} outcomes', flush=True)

    df = pd.DataFrame(rows)
    diag = pd.DataFrame(diagnostics)
    pred_cols = [f'pred_{a}' for a, *_ in ARMS]
    bad_cols = [c for c in ['actual'] + pred_cols if not np.isfinite(df[c]).all()]
    assert not bad_cols, f'non-finite predictions in: {bad_cols}'
    assert not df.duplicated(['mode', 'endpoint', 'name', 'origin', 'horizon']).any()
    df.to_csv(OUT / f'{PREFIX}_predictions.csv', index=False)
    diag.to_csv(OUT / f'{PREFIX}_origins.csv', index=False)

    results = []
    for (mode, endpoint), g in df.groupby(['mode', 'endpoint']):
        selections = ([('all', g)]
                      + [(f'band_{b}', v) for b, v in g.groupby('band')]
                      + [('stars', g[g.star])]
                      + [(f'horizon_{h}', v) for h, v in g.groupby('horizon')]
                      + [(f'position_{p}', v) for p, v in g.groupby('pos')])
        for label, part in selections:
            if len(part):
                for arm, *_ in ARMS:
                    results.append(dict(mode=mode, endpoint=endpoint, group=label,
                                        **cluster_summary(part, arm)))
    result = pd.DataFrame(results)
    result.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)

    # Re-hash the same path objects, not a reconstructed path.
    assert all(digest(p) == hashes[k] for k, p in watched), \
        'Input or production code changed during the test'
    design.update(elapsed_seconds=time.time() - start, rows=len(df),
                  origins=len(diag), players=int(df.name.nunique()))
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(design, indent=2))

    # The headline read: signed bias by level band on the endpoint that reaches
    # dollars. If production's bias falls as the band rises, elite deflation is
    # real; the arm that flattens it names the lever.
    head = result[(result['mode'] == 'career_holdout')
                  & (result.endpoint == 'season_total')
                  & (result.group.str.startswith('band_') | (result.group == 'all'))]
    print(head[['group', 'arm', 'n', 'mae', 'bias', 'delta_mae',
                'delta_ci_low', 'delta_ci_high']].to_string(index=False), flush=True)
    print(f'Complete in {time.time() - start:.1f}s; production files unchanged.', flush=True)


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
