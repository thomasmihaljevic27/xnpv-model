"""aging_weight_sweep_test.py -- are equal group weights the best proportions?

Test only. Production (aging_curve.py) is never edited; hashes are checked.

WHAT IS TESTED
--------------
The current curve measures the distance between two players on eight measures
in four groups, and `_attr_weights()` gives each GROUP equal weight: style (the
five WAR-component shares, 1/5 each), ice time, level, and trend each carry one
quarter of the total weight. (Equal weights, not equal contributions: what a
group adds to a given distance depends on how far apart the two players are on
it.) aging_arbitrary_choices_test.py v1.0 scored only removals and the
all-measures-equal set. This sweeps the PROPORTIONS.

Only proportions matter. The yardstick is the median distance on whatever
scale the weights define, so multiplying every weight by c multiplies every
distance AND the yardstick by sqrt(c), and every similarity weight is unchanged
(asserted below on one scaled copy). Each weight set is therefore written as
four group weights with the others' scale fixed, and sets that are multiples of
one another are scored once.

  one at a time   one group at 0.25, 0.5, 2 or 4 times the other three (16 sets)
  joint grid      every group at 0.5, 1 or 2 (81 combinations, 57 distinct
                  proportions once multiples are merged; equal is one of them)
  65 distinct sets in all, equal included, since the grid's points at 0.5 and 2
  repeat eight of the one-at-a-time sets.

Each set's yardstick is rebuilt on its own scale by production's rule (seed 0,
up to 1,200 profiles per position), exactly as the choices test did.

DESIGN
------
The same held-out design and code as aging_arbitrary_choices_test.py (five
whole-career folds, same seed; the target never in its own pool; the target
sees only its own seasons up to the forecast age), on the age table that the
two 2026-09-28 decisions make production:
  * the Elite Prospects pass applied (30_OUTPUT/aging_ep_pool_test_war_with_age.csv,
    built by aging_ep_pool_test.py), and
  * the pool limited to seasons up to the forecast year: the historical mode,
    forecast years 2017-2022, one to three seasons ahead. PRIMARY.
  The full-era mode (one to six seasons ahead) is reported beside it.
Outcomes: WAR per 82, and production's ratio on a 60/40 trailing season total.
Score: mean absolute error; intervals resample careers (2,000 draws).

SELECTION, declared before the run. With 65 sets, the best of them will
beat equal weights by chance. So: (1) equal weights' RANK among all sets is
reported for each of the four comparisons; (2) the best set is chosen on ONE
comparison (primary mode, WAR per 82) and then scored on the other three,
which it was not chosen on. A set is called better than equal weights only if
it wins on all four and its interval excludes zero on the primary comparison.

LIMITS: weights only; the 55% kept share, the yardstick rule, the kernel and
the league weight stay at production. Development-era data already inspected
by the earlier aging tests.
"""

# Moved from 20_CODE/ to 25_TESTS/ on 2026-09-30 (finished one-off test). The
# production modules it imports stay in 20_CODE/, so put that folder on the path.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "20_CODE"))

from itertools import product
from pathlib import Path
import json
import os
import sys
import tempfile
import time

import numpy as np
import pandas as pd

from aging_curve import AgingModel, career_key, _attr_weights, FEATS, SHARE, LAMBDA, SHRINK_K
from aging_bandwidth_test import truncated_player, ratio_prediction, digest
import aging_arbitrary_choices_test as T

SCRIPT_VERSION = '1.0'
OUT = Path(os.environ['OUTPUT_DIR'])
TABLE = OUT / 'aging_ep_pool_test_war_with_age.csv'
PREFIX = 'aging_weight_sweep_test'
GROUPS = ('style', 'ice_time', 'level', 'trend')
PRIMARY = ('historical_window', 'curve')


def fw_from_groups(g):
    """Group weights (style, ice time, level, trend) -> the eight-measure
    vector aging_curve uses (style split equally over its five shares)."""
    s, u, l, t = g
    return np.array([s / len(SHARE)] * len(SHARE) + [u, l, t], dtype=float)


def weight_sets():
    """name -> group weights. Multiples of one another are merged."""
    sets, seen = {}, {}
    def add(name, g):
        key = tuple(np.round(np.asarray(g, float) / max(g), 9))
        if key in seen:
            return seen[key]
        seen[key] = name; sets[name] = tuple(float(x) for x in g)
        return name
    add('prod', (1.0, 1.0, 1.0, 1.0))
    for i, grp in enumerate(GROUPS):
        for m in (0.25, 0.5, 2.0, 4.0):
            g = [1.0] * 4; g[i] = m
            add(f'{grp}_x{m:g}', g)
    for g in product((0.5, 1.0, 2.0), repeat=4):
        add('grid_' + '_'.join(f'{x:g}' for x in g), g)
    return sets


class SweepScale(T.Scale):
    """T.Scale with the sweep's weight sets in place of the choices test's."""

    def __init__(self, model, sets):
        self.model = model
        fw0 = _attr_weights()
        assert np.array_equal(fw0, model.fw), 'production feature weights moved'
        assert np.allclose(fw_from_groups(sets['prod']), fw0), 'equal groups != production weights'
        self.Z = model.Zw / np.sqrt(model.fw)
        self.fw = {k: fw_from_groups(g) for k, g in sets.items()}
        self.fw['prod'] = fw0
        self.yard = {'prod': T.yardsticks(model, model.Zw)}
        assert self.yard['prod']['prod'] == model.h, 'yardstick differs from AgingModel.h'
        for k, w in self.fw.items():
            if k != 'prod':
                self.yard[k] = T.yardsticks(model, self.Z * np.sqrt(w))


def main():
    start = time.time()
    assert TABLE.exists(), f'{TABLE} missing: run aging_ep_pool_test.py first'
    root = Path(__file__).resolve().parents[1]
    hashes = {str(p): digest(p) for p in [TABLE, root / '20_CODE/aging_curve.py']}
    sets = weight_sets()
    arms = {k: {'fw': k} if k != 'prod' else {} for k in sets}
    print(f'{len(sets)} distinct weight sets', flush=True)

    raw = pd.read_csv(TABLE); raw['career'] = raw.Player.map(career_key)
    raw['year'] = raw.Season.str[:2].astype(int) + 2000
    keys = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
            .agg(age=('age', 'first'), GP=('GP', 'sum')))
    bad = [n for n, g in keys[keys.GP >= 20].groupby('career')
           if g.age.duplicated().any() or (g.year - g.age).nunique() > 1]
    raw = raw[~raw.career.isin(bad)].copy()

    with tempfile.TemporaryDirectory(prefix='aging_sweep_') as td:
        def fit(frame, tag):
            p = Path(td) / f'{tag}.csv'
            frame.drop(columns=['career', 'year']).to_csv(p, index=False)
            return AgingModel(str(p))
        full = fit(raw, 'full')
        # SCALE INVARIANCE, checked once: every weight x 3 leaves similarity unchanged.
        sc = SweepScale(full, {'prod': sets['prod'], 'x3': (3.0, 3.0, 3.0, 3.0)})
        r = full.by_age[27][:50]; z = sc.Z[r[0]]
        for k in ('prod', 'x3'):
            d2 = (((sc.Z[r] - z) ** 2) * sc.fw[k]).sum(1)
            w = T.kernel(d2, sc.yard[k]['prod'], 'gauss')
            if k == 'prod':
                w0 = w
        # the sampled yardstick is a median of sampled pairs, so it scales exactly
        assert np.allclose(w, w0, rtol=1e-9, atol=0), 'weights are not scale-free'

        names = sorted(full.players)
        fold = {}; rng = np.random.default_rng(T.SEED)
        for pos in sorted({p['pos'] for p in full.players.values()}):
            g = np.array([n for n in names if full.players[n]['pos'] == pos]); rng.shuffle(g)
            fold.update({str(n): i % T.FOLDS for i, n in enumerate(g)})
        obs = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
               .agg(age=('age', 'first'), GP=('GP', 'sum'), WAR=('WAR', 'sum'), pos=('Position', 'last')))
        obs = obs[obs.career.isin(full.players)].copy()
        age_to_year = {n: {int(r.age): int(r.year) for r in g[g.GP >= 20].itertuples()}
                       for n, g in obs.groupby('career')}
        pos_at = {(r.career, int(r.year)): r.pos for r in obs.itertuples()}
        pr = obs[obs.GP >= 10].copy()
        pr['total'] = pr.WAR * pr.year.map({2019: 82 / 70, 2020: 82 / 56}).fillna(1.0)
        totals = {(r.career, int(r.year)): float(r.total) for r in pr.itertuples()}

        rows = []
        for mode in ['historical_window', 'career_holdout']:
            years = [None] if mode == 'career_holdout' else list(range(2017, 2023))
            for year in years:
                for f in range(T.FOLDS):
                    sel = raw.career.map(fold).ne(f)
                    if year is not None:
                        sel &= raw.year <= year
                    model = fit(raw[sel], 'train'); scale = SweepScale(model, sets)
                    maxage = model.AMIN + model.nages - 1
                    for name in names:
                        if fold[name] != f:
                            continue
                        p = full.players[name]
                        for s in p['seasons'][1:]:
                            age = s['age']; origin = age_to_year[name][age]
                            if year is not None and origin != year:
                                continue
                            fut = [x for x in p['raw'] if 1 <= x - age <= (6 if year is None else 3)]
                            if not fut:
                                continue
                            pos = pos_at[(name, origin)]
                            if pos not in model.stats or not model.AMIN <= age < maxage:
                                continue
                            horizon = min(max(fut) - age, maxage - age)
                            target = truncated_player(p, age); target['pos'] = pos
                            o = T.prepare(model, target, pos, age)
                            ref = T.project_guarded(model, name, target, age, horizon)
                            preds = {k: T.walk(scale, o, horizon, v)[0] for k, v in arms.items()}
                            got = np.array([preds['prod'][x] for x in ref.age])
                            assert np.allclose(got, ref.projected_war_per_82.to_numpy(), atol=1e-10, rtol=0), name
                            recent, prior = totals.get((name, origin)), totals.get((name, origin - 1))
                            baseline = (.6 * recent + .4 * prior if recent is not None and prior is not None
                                        else recent if recent is not None else prior)
                            base = dict(mode=mode, cutoff=year, fold=f, name=name, pos=pos, origin=origin,
                                        age=age, sm=o['sm'], tier=T.tier_of(o['sm']))
                            for fa in fut:
                                if fa not in preds['prod']:
                                    continue
                                h = fa - age
                                rows.append(dict(**base, endpoint='curve', horizon=h, actual=p['raw'][fa],
                                                 **{f'pred_{k}': preds[k][fa] for k in arms}))
                                if h >= 2 and (age + 1) in preds['prod'] and baseline is not None:
                                    act = totals.get((name, origin + h))
                                    if act is not None:
                                        rows.append(dict(**base, endpoint='season_total', horizon=h - 1, actual=act,
                                                         **{f'pred_{k}': ratio_prediction(preds[k], age, baseline, h)
                                                            for k in arms}))
                    print(f'{mode} cutoff={year} fold={f}: {len(rows)} outcomes ({time.time() - start:.0f}s)',
                          flush=True)

    df = pd.DataFrame(rows)
    assert np.isfinite(df[['actual'] + [f'pred_{k}' for k in arms]].to_numpy()).all()
    res = []
    for (mode, ep), g in df.groupby(['mode', 'endpoint']):
        for lab, part in [('all', g), ('tier_elite_3plus', g[g.tier == 'elite_3plus'])]:
            for d in T.summarise(part, list(arms), T.SEED):
                res.append(dict(mode=mode, endpoint=ep, group=lab, **d))
    summ = pd.DataFrame(res)
    summ['groups'] = summ.variant.map(lambda k: sets[k])
    summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)

    run = select(summ, sets)
    run.update(script_version=SCRIPT_VERSION, rows=len(df), players=df.name.nunique(),
               input_hashes=hashes, fixed=dict(lambda_kept=LAMBDA, pooled_weight=SHRINK_K),
               elapsed_seconds=time.time() - start)
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(run, indent=2, default=str))
    assert all(digest(Path(k)) == v for k, v in hashes.items()), 'input or production code changed'
    report(summ, run)
    print(f'complete in {time.time() - start:.0f}s; production files unchanged.', flush=True)


def select(summ, sets):
    """The declared selection (see the docstring). Columns are read by name
    with [...] because DataFrame.pct_change is a method (v1.0's first run
    crashed here after the summary was saved; the selection was then run on
    that saved summary with --select-only)."""
    allg = summ[summ['group'] == 'all']
    comps = [PRIMARY, ('historical_window', 'season_total'), ('career_holdout', 'curve'),
             ('career_holdout', 'season_total')]
    ranks = {}
    for c in comps:
        g = allg[(allg['mode'] == c[0]) & (allg['endpoint'] == c[1])].sort_values('mae')
        ranks[f'{c[0]}/{c[1]}'] = dict(n=int(g['n'].iloc[0]), players=int(g['players'].iloc[0]),
                                       equal_rank=int(list(g['variant']).index('prod')) + 1, of=len(g),
                                       best=g['variant'].iloc[0], best_groups=sets[g['variant'].iloc[0]],
                                       best_pct=float(g['pct_change'].iloc[0]),
                                       worst=g['variant'].iloc[-1],
                                       worst_pct=float(g['pct_change'].iloc[-1]))
    g = allg[(allg['mode'] == PRIMARY[0]) & (allg['endpoint'] == PRIMARY[1])].sort_values('mae')
    chosen = g['variant'].iloc[0]
    held = {}
    for c in comps:
        x = allg[(allg['mode'] == c[0]) & (allg['endpoint'] == c[1]) & (allg['variant'] == chosen)].iloc[0]
        held[f'{c[0]}/{c[1]}'] = dict(pct=float(x['pct_change']),
                                      ci=None if chosen == 'prod' else (float(x['ci_low']), float(x['ci_high'])),
                                      lower_in=None if chosen == 'prod' else int(x['lower_in']))
    key = f'{PRIMARY[0]}/{PRIMARY[1]}'
    verdict = (chosen != 'prod' and all(v['pct'] < 0 for v in held.values())
               and held[key]['ci'][1] < 0)
    return dict(sets=len(sets), ranks=ranks, chosen_on_primary=chosen, chosen_groups=sets[chosen],
                chosen_scored=held, better_than_equal_by_declared_rule=bool(verdict))


def report(summ, run):
    print(json.dumps(run, indent=1, default=str), flush=True)
    allg = summ[summ['group'] == 'all']
    pd.set_option('display.width', 220)
    one = allg[~allg['variant'].str.startswith('grid_')]
    print(one.pivot_table(index='variant', columns=['mode', 'endpoint'], values='pct_change', sort=False)
          .round(3).to_string(), flush=True)


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    if '--select-only' in sys.argv:
        # the selection and report on a saved summary, without re-scoring
        summ = pd.read_csv(OUT / f'{PREFIX}_summary.csv')
        run = select(summ, weight_sets())
        run.update(script_version=SCRIPT_VERSION, from_saved_summary=True)
        (OUT / f'{PREFIX}_run.json').write_text(json.dumps(run, indent=2, default=str))
        report(summ, run)
    else:
        main()
