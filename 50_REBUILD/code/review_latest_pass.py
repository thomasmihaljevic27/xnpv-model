"""Independent regression probes for Claude's 0e70d4b repair pass.

Read-only model review. Use --candidate-root for an isolated checkout with a
merged output/birthdates.csv. Only aggregate evidence is written under output.
"""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate-root', type=Path, required=True)
    ap.add_argument('--development', action='store_true',
                    help='Also reproduce the development leaderboard; never unseals holdouts.')
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    os.environ['SOURCE_DIR'] = str(root/'10_SOURCE')
    os.environ['OUTPUT_DIR'] = str(root/'30_OUTPUT')
    os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
    sys.path.insert(0, str(args.candidate_root.resolve()/'50_REBUILD/code'))
    import numpy as np
    import pandas as pd
    import rebuild_config as C
    import information_set as I
    import forecast_harness as H
    import player_season_table as T
    import contract_price_model as CP
    from ability_forecast import A1HingeExposure
    from production_adapter import ProductionChain
    from production_currency import ProductionCurrency
    table = T.build(birthdate_csv=C.OUT_DIR/'birthdates.csv', verbose=False)
    iset = I.build(table, I.decision_date_for_page(2021), t0=2021)
    subs = H.subjects_at(iset)
    results = {'age_coverage': float(table.has_age.mean())}
    live = ProductionChain()
    live.fit(iset.seasons, 2021)
    pred = live.predict(iset, subs, range(6)).set_index(['career_key', 'h'])
    # Compare every projected rate and survival transition against the imported
    # production methods, including positive anchors and curve fallback paths.
    from contract_npv import NPVEngine
    rate_errors, survival_errors, paths = [], [], {}
    missing = negative = 0
    for row in subs.itertuples():
        anchor, source = live.proj_.anchor(row.pkey, 2021)
        if pd.isna(anchor):
            missing += 1
            assert pred.loc[(row.career_key, 0), 'outside_production'] == 1
            continue
        negative += int(anchor < 0)
        age = None if pd.isna(row.age) else int(round(row.age))
        ratios, tag = live.proj_.ratio_path(row.pkey, age, 5)
        paths[tag] = paths.get(tag, 0) + 1
        survival, previous = 1., None
        for h in range(6):
            expected = anchor*live.proj_.multiplier(anchor, ratios[h], h)
            if h:
                hazard = NPVEngine._hazard(None, live.haz_, previous,
                                            None if age is None else age+h-1)
                survival *= 1-hazard
            rate_errors.append(abs(expected-pred.loc[(row.career_key,h),'rate_82']))
            survival_errors.append(abs(survival-pred.loc[(row.career_key,h),'p_play']))
            previous = expected
    results['production_method_parity'] = dict(max_rate_error=max(rate_errors),
        max_survival_error=max(survival_errors), rows=len(rate_errors), paths=paths,
        negative_anchors=negative, outside_production=missing)
    m = A1HingeExposure()
    m.fit(iset.seasons, 2021)
    m.fitted_horizons_ = tuple(range(6))
    def tail(s, hs):
        p = m.predict_beyond_fit(iset, s, hs).query('h == 6').set_index('career_key')
        return p.rate_82*p.p_play*p.gp_share
    reference = tail(subs, [4,5,6])
    variants = {'same_endpoint': tail(subs,[3,5,6]),
                'different_endpoint': tail(subs,[3,4,6]),
                'one_subject': tail(subs.head(1),[4,5,6]),
                'reversed_subjects': tail(subs.iloc[::-1],[4,5,6])}
    results['tail_query_max_war_difference'] = {
        k: float((v-reference.reindex(v.index)).abs().max()) for k,v in variants.items()}
    try:
        tail(subs, [6])
        results['tail_only_request'] = 'accepted'
    except ValueError as e:
        results['tail_only_request'] = str(e)
    c = CP.contract_sample()
    original_caps = C.CAP_CEILING.copy()
    # Perturb only caps unavailable at the cutoff under the candidate policy.
    try:
        for year in C.CAP_CEILING:
            if year >= 2019:
                C.CAP_CEILING[year] *= 2
        changed = CP.contract_sample()
    finally:
        C.CAP_CEILING.clear()
        C.CAP_CEILING.update(original_caps)
    ix = c.index[c.signed < pd.Timestamp('2019-01-01')]
    results['historical_cap_target_perturbation'] = {
        'rows': len(ix), 'max_cap_share_change': float((c.loc[ix,'cap_share']-changed.loc[ix,'cap_share']).abs().max()),
        'max_floor_share_change': float((c.loc[ix,'floor_share']-changed.loc[ix,'floor_share']).abs().max())}
    cur = ProductionCurrency()
    frame = pd.DataFrame({'signed':pd.to_datetime(['2017-07-01','2018-07-01']),
        'start_yr':[2019,2019], 'end_yr':[2019,2019], 'length':[1,1], 'aav':[1e6,1e6]})
    costs = cur.cost(frame).to_numpy()
    assert np.allclose(costs, [1e6/1.03**2,1e6/1.03])
    results['one_year_costs'] = costs.tolist()
    # A deterministic oracle answers every requested year. This isolates the
    # attachment interface from model support and tests a ten-year term.
    class CompleteForecast:
        def fit(self, *args, **kwargs):
            pass
        def predict_beyond_fit(self, iset, subjects, horizons):
            return pd.DataFrame([{'career_key':r.career_key,'h':h,'rate_82':1.,
                'p_play':1.,'gp_share':1.,'extrapolated':float(h>5)}
                for r in subjects.itertuples() for h in horizons])
    sample = pd.DataFrame({'pkey':[subs.iloc[0].pkey]*2,'latest_complete':[2020]*2,
        'start_yr':[2021]*2,'end_yr':[2022,2030], 'length':[2,10]})
    attached = CP.attach_forecasts(sample, CompleteForecast, table, verbose=False)
    results['attachment_synthetic_terms'] = {'requested_lengths':sample.length.tolist(),
        'returned_lengths':attached.length.tolist()}
    results['current_contracts_above_h8'] = int((c.end_yr-(c.latest_complete+1)>8).sum())
    if args.development:
        harness = H.Harness(table)
        keys = ['page', 'career_key', 'h']
        old = harness.run(ProductionChain(), pages=range(2015,2022), horizons=range(6))
        new = harness.run(A1HingeExposure(), pages=range(2015,2022), horizons=range(6))
        old = old[old.outside_production == 0].set_index(keys)
        new = new.set_index(keys).loc[old.index]
        results['development'] = []
        for h in range(6):
            x = old.xs(h,level='h').e_war.abs()
            y = new.xs(h,level='h').e_war.abs()
            results['development'].append(dict(h=h, n=len(x), live=float(x.mean()),
                rebuilt=float(y.mean()), improvement_pct=float(100*(y.mean()/x.mean()-1))))
    out = root/'50_REBUILD/output/review_latest_pass.json'
    out.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
