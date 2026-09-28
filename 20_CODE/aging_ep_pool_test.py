"""aging_ep_pool_test.py -- what the missing older careers do to the aging curve's pool.

Test only. Production (age_join.py, aging_curve.py, skater_forward_projection.py)
is never edited; their hashes are checked at start and finish, and the live
30_OUTPUT/WAR_with_age.csv is read, never written.

WHY THIS EXISTS
---------------
The age table the aging curve is fitted on has no Elite Prospects matches:
1,278 of 3,199 skaters have no age, most of them careers that ended before the
2018 contract export (2026-09-28). The cause is a path. age_join.py reads the
scrape from OUTPUT_DIR/ep_out/ep_birthdates.csv (EP_BIRTHDATES_PATH); the
2026-07-30 migration placed it at 10_SOURCE/ep_birthdates.csv, and Pass 4
checks os.path.exists() and skips silently. So the curve's comparables pool
holds only careers that lasted into the contract years.

WHAT IT DOES
------------
1. Builds the table age_join.py would have written with the scrape present,
   WITHOUT re-running age_join.py (that needs the confidential PuckPedia
   export, not in this container). Pass 4 only fills players whose birthdate
   is still missing after Passes 1-3 and the plausibility gate, keyed on the
   exact WAR `Player` string, first row per name; the hand corrections
   (EP_BIRTHDATE_OVERRIDES) then override. In the live table those
   corrections are already applied and every other player either has a
   PuckPedia birthdate or has none. So applying Pass 4 to the rows with no
   birthdate, then the overrides again, reproduces age_join.py's rule; ages
   come from age_join.compute_age (imported, not copied). Guard: every row
   that already had an age keeps it exactly.
   Written to 30_OUTPUT/aging_ep_pool_test_war_with_age.csv (a test artifact,
   not the live file).
2. Scores production's own AgingModel.project() fitted on each table, on the
   SAME forecast-outcome pairs: the targets are the careers of the live table,
   in the folds of aging_arbitrary_choices_test.py (same seed); the careers
   the scrape adds are never targets and join every fold's training pool.
   Both modes of that test: full-era training (1-6 seasons ahead) and
   historical training (seasons up to the forecast year, 2017-2022, 1-3
   ahead). Outcomes: WAR per 82 and the production-style season total.
   Reproduction guard: the live-table forecasts equal that test's saved
   production forecasts on every row.

LIMITS: the added careers change four things together, as any pool change
does here (the comparables, the z-score means and SDs, the yardstick and the
league-average curves). The exit hazard, which also reads the age table, is
not refitted. The table is rebuilt by rule rather than by running age_join.py.
"""
from pathlib import Path
import json
import os
import tempfile
import time

import numpy as np
import pandas as pd

import age_join as AJ
from aging_curve import AgingModel, career_key, LAMBDA, SHRINK_K
from aging_bandwidth_test import truncated_player, ratio_prediction, digest
import aging_arbitrary_choices_test as T

SCRIPT_VERSION = '1.0'
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['OUTPUT_DIR'])
SRC = Path(os.environ['SOURCE_DIR'])
LIVE = OUT / 'WAR_with_age.csv'
EP = SRC / 'ep_birthdates.csv'
PREFIX = 'aging_ep_pool_test'
AUG = OUT / f'{PREFIX}_war_with_age.csv'
ARMS = ['prod', 'ep_pool']


def augmented_table():
    """age_join.py's Pass 4 and override pass, applied to the live table."""
    w = pd.read_csv(LIVE)
    ep = pd.read_csv(EP).dropna(subset=['birthdate'])
    ep_map = ep.drop_duplicates('war_name').set_index('war_name')['birthdate'].to_dict()
    a = w.copy()
    a['birthdate'] = a['birthdate'].astype(object)
    miss = a['birthdate'].isna() & a['Player'].isin(ep_map)
    a.loc[miss, 'birthdate'] = a.loc[miss, 'Player'].map(ep_map)
    a.loc[miss & a['match_type'].eq('unmatched'), 'match_type'] = 'ep'
    for nm, bd in AJ.EP_BIRTHDATE_OVERRIDES.items():
        m = a['Player'] == nm
        a.loc[m, 'birthdate'] = bd
        a.loc[m, 'match_type'] = 'ep_fixed'
    ages = [AJ.compute_age(b, AJ.season_end_year(s)) for b, s in zip(a['birthdate'], a['Season'])]
    a['age'] = [x[0] for x in ages]
    a['age_exact'] = [x[1] for x in ages]
    # GUARD: every row the live table aged keeps exactly its age.
    had = w['age'].notna()
    assert (a.loc[had, 'age'].astype(float).to_numpy() == w.loc[had, 'age'].to_numpy()).all(), \
        'a row that already had an age changed'
    assert np.allclose(a.loc[had, 'age_exact'].astype(float), w.loc[had, 'age_exact']), \
        'an exact age changed'
    info = dict(rows=len(a), rows_aged_live=int(had.sum()), rows_aged_aug=int(a['age'].notna().sum()),
                players_added=int(a.loc[miss, 'Player'].nunique()),
                players_still_unmatched=int(a.loc[a['age'].isna(), 'Player'].nunique()),
                match_types=a.drop_duplicates('Player')['match_type'].value_counts().to_dict())
    syr = a['Season'].str[:2].astype(int) + 2000
    info['coverage_by_season'] = {int(k): round(float(v), 3) for k, v in
                                  a['age'].notna().groupby(syr).mean().items()}
    a.to_csv(AUG, index=False)
    return info


def prep(path):
    raw = pd.read_csv(path); raw['career'] = raw.Player.map(career_key)
    raw['year'] = raw.Season.str[:2].astype(int) + 2000
    keys = (raw[raw.age.notna()].groupby(['career', 'year'], as_index=False)
            .agg(age=('age', 'first'), GP=('GP', 'sum')))
    bad = [n for n, g in keys[keys.GP >= 20].groupby('career')
           if g.age.duplicated().any() or (g.year - g.age).nunique() > 1]
    return raw, bad


def fit(frame, td, tag):
    p = Path(td) / f'{tag}.csv'
    frame.drop(columns=['career', 'year']).to_csv(p, index=False)
    return AgingModel(str(p))


def main():
    start = time.time()
    hashes = {str(p): digest(p) for p in
              [LIVE, EP, ROOT / '20_CODE/age_join.py', ROOT / '20_CODE/aging_curve.py',
               ROOT / '20_CODE/skater_forward_projection.py']}
    info = augmented_table()
    print('AUGMENTED TABLE:', json.dumps(info, indent=1), flush=True)

    raw_p, bad_p = prep(LIVE)
    raw_a, bad_a = prep(AUG)
    bad = sorted(set(bad_p) | set(bad_a))
    raw_p = raw_p[~raw_p.career.isin(bad)].copy()
    raw_a = raw_a[~raw_a.career.isin(bad)].copy()
    with tempfile.TemporaryDirectory(prefix='aging_ep_') as td:
        full = fit(raw_p, td, 'full_p')
        full_a = fit(raw_a, td, 'full_a')
        yard = dict(live=dict(h=full.h, pool=len(full.names), careers=len(set(full.names))),
                    added=dict(h=full_a.h, pool=len(full_a.names), careers=len(set(full_a.names))))
        for nm, m in [('live', full), ('added', full_a)]:
            y = T.yardsticks(m, m.Zw)
            yard[nm].update(by_position=y['by_position'],
                            pool_by_position={p: v['pool_profiles'] for p, v in y['info'].items()},
                            careers_by_position={p: v['careers'] for p, v in y['info'].items()})
        print('POOL:', json.dumps(yard, indent=1, default=str), flush=True)

        # folds exactly as aging_arbitrary_choices_test.py (same seed, same names)
        names = sorted(full.players)
        fold = {}; rng = np.random.default_rng(T.SEED)
        for pos in sorted({p['pos'] for p in full.players.values()}):
            g = np.array([n for n in names if full.players[n]['pos'] == pos]); rng.shuffle(g)
            fold.update({str(n): i % T.FOLDS for i, n in enumerate(g)})
        new = sorted(set(full_a.players) - set(full.players))
        assert not (set(new) & set(fold)), 'an added career is also a target'
        # a career present in both must have identical seasons and ages
        for n in names:
            assert [s['age'] for s in full.players[n]['seasons']] == \
                   [s['age'] for s in full_a.players[n]['seasons']], n

        obs = (raw_p[raw_p.age.notna()].groupby(['career', 'year'], as_index=False)
               .agg(age=('age', 'first'), GP=('GP', 'sum'), WAR=('WAR', 'sum'), pos=('Position', 'last')))
        obs = obs[obs.career.isin(full.players)].copy()
        age_to_year = {n: {int(r.age): int(r.year) for r in g[g.GP >= 20].itertuples()}
                       for n, g in obs.groupby('career')}
        pos_at = {(r.career, int(r.year)): r.pos for r in obs.itertuples()}
        pr = obs[obs.GP >= 10].copy()
        pr['total'] = pr.WAR * pr.year.map({2019: 82 / 70, 2020: 82 / 56}).fillna(1.0)
        totals = {(r.career, int(r.year)): float(r.total) for r in pr.itertuples()}

        rows = []
        for mode in ['career_holdout', 'historical_window']:
            years = [None] if mode == 'career_holdout' else list(range(2017, 2023))
            for year in years:
                for f in range(T.FOLDS):
                    sel_p = raw_p.career.map(fold).ne(f)
                    sel_a = raw_a.career.map(fold).ne(f)          # added careers: NaN, always in
                    if year is not None:
                        sel_p &= raw_p.year <= year; sel_a &= raw_a.year <= year
                    mp, ma = fit(raw_p[sel_p], td, 'tp'), fit(raw_a[sel_a], td, 'ta')
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
                            ok = [pos in m.stats and m.AMIN <= age < m.AMIN + m.nages - 1 for m in (mp, ma)]
                            if not ok[0]:
                                continue          # production cannot answer: not a row in either test
                            assert ok[1], 'the added-careers pool cannot answer a live-pool origin'
                            hz = min(max(fut) - age, mp.AMIN + mp.nages - 1 - age,
                                     ma.AMIN + ma.nages - 1 - age)
                            target = truncated_player(p, age); target['pos'] = pos
                            preds = {}
                            for arm, m in (('prod', mp), ('ep_pool', ma)):
                                tr = T.project_guarded(m, name, target, age, hz)
                                preds[arm] = dict(zip(tr.age.astype(int), tr.projected_war_per_82))
                            recent, prior = totals.get((name, origin)), totals.get((name, origin - 1))
                            baseline = (.6 * recent + .4 * prior if recent is not None and prior is not None
                                        else recent if recent is not None else prior)
                            base = dict(mode=mode, cutoff=year, fold=f, name=name, pos=pos, origin=origin,
                                        age=age, sm=p['sm'][age], tier=T.tier_of(p['sm'][age]))
                            for fa in fut:
                                if fa not in preds['prod'] or fa not in preds['ep_pool']:
                                    continue
                                h = fa - age
                                rows.append(dict(**base, endpoint='curve', horizon=h, actual=p['raw'][fa],
                                                 **{f'pred_{k}': preds[k][fa] for k in ARMS}))
                                if h >= 2 and (age + 1) in preds['prod'] and baseline is not None:
                                    act = totals.get((name, origin + h))
                                    if act is not None:
                                        rows.append(dict(**base, endpoint='season_total', horizon=h - 1,
                                                         actual=act,
                                                         **{f'pred_{k}': ratio_prediction(preds[k], age, baseline, h)
                                                            for k in ARMS}))
                    print(f'{mode} cutoff={year} fold={f}: {len(rows)} outcomes ({time.time() - start:.0f}s)',
                          flush=True)

    df = pd.DataFrame(rows)
    assert np.isfinite(df[['actual', 'pred_prod', 'pred_ep_pool']].to_numpy()).all()
    # REPRODUCTION GUARD against the choices test's saved production forecasts
    prev_path = OUT / f'{T.PREFIX}_predictions.csv'
    if prev_path.exists():
        prev = pd.read_csv(prev_path)
        k = ['mode', 'endpoint', 'name', 'origin', 'horizon']
        j = df.merge(prev[k + ['pred_prod', 'actual']], on=k, suffixes=('', '_prev'), how='outer',
                     indicator=True)
        only = j['_merge'].value_counts().to_dict()
        both = j[j['_merge'] == 'both']
        assert np.allclose(both.pred_prod, both.pred_prod_prev, atol=1e-10, rtol=0), 'live forecasts differ'
        assert np.allclose(both.actual, both.actual_prev), 'outcomes differ'
        guard = dict(rows_matched=int(len(both)), merge=only)
    else:
        guard = 'choices test predictions not found; guard not run'
    print('GUARD:', guard, flush=True)
    df.to_csv(OUT / f'{PREFIX}_predictions.csv', index=False)

    res = []
    for (mode, ep_), g in df.groupby(['mode', 'endpoint']):
        groups = [('all', g)] + [(f'tier_{t}', x) for t, x in g.groupby('tier')] + \
                 [(f'horizon_{h}', x) for h, x in g.groupby('horizon')] + \
                 [(f'position_{q}', x) for q, x in g.groupby('pos')]
        for i, (lab, part) in enumerate(groups):
            for d in T.summarise(part, ARMS, T.SEED + i):
                res.append(dict(mode=mode, endpoint=ep_, group=lab, **d))
    summ = pd.DataFrame(res)
    summ.to_csv(OUT / f'{PREFIX}_summary.csv', index=False)
    assert all(digest(Path(k)) == v for k, v in hashes.items()), 'input or production code changed'
    run = dict(script_version=SCRIPT_VERSION, table=info, pool=yard, guard=guard,
               excluded_ambiguous_age_careers=bad, rows=len(df), players=df.name.nunique(),
               fixed=dict(lambda_kept=LAMBDA, pooled_weight=SHRINK_K), input_hashes=hashes,
               elapsed_seconds=time.time() - start)
    (OUT / f'{PREFIX}_run.json').write_text(json.dumps(run, indent=2, default=str))
    pd.set_option('display.width', 220)
    show = summ[(summ.variant == 'ep_pool')]
    print(show[['mode', 'endpoint', 'group', 'n', 'players', 'mae_prod', 'mae', 'pct_change', 'ci_low',
                'ci_high', 'lower_in', 'rmse_pct_change', 'bias', 'mean_abs_move']].to_string(index=False))
    print(f'complete in {time.time() - start:.0f}s; production files unchanged.', flush=True)


if __name__ == '__main__':
    print(f'SCRIPT_VERSION={SCRIPT_VERSION}', flush=True)
    main()
