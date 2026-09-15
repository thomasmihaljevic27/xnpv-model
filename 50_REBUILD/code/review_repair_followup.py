"""Independent checks of repair commit d651998, in an explicit candidate checkout.

Run with --candidate-root pointing to that checkout. Reads shared vendor and
production inputs from this repository; generated evidence stays in output/.
"""
import argparse
import json
import os
from pathlib import Path
import sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate-root', type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    candidate = args.candidate_root.resolve()
    os.environ['SOURCE_DIR'] = str(root / '10_SOURCE')
    os.environ['OUTPUT_DIR'] = str(root / '30_OUTPUT')
    os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root / '10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
    sys.path.insert(0, str(candidate / '50_REBUILD/code'))
    import numpy as np
    import pandas as pd
    import rebuild_config as C
    import information_set as I
    import forecast_harness as H
    import player_season_table as T
    import repair_checks
    from production_adapter import ProductionChain
    from ability_forecast import A1HingeExposure
    from production_currency import ProductionCurrency
    from contract_price_model import contract_sample
    table = T.build(birthdate_csv=C.OUT_DIR/'birthdates.csv', verbose=False)
    results = {'candidate_root': str(candidate), 'check12': repair_checks.c12(table)}
    iset = I.build(table, I.decision_date_for_page(2021), t0=2021)
    subs = H.subjects_at(iset)
    live = ProductionChain()
    live.fit(iset.seasons, 2021)
    own, prod, missing = [], [], 0
    for r in subs.itertuples():
        a = live._anchor(r.pkey, 2021)
        b, _ = live.proj_.anchor(r.pkey, 2021)
        if pd.isna(b):
            missing += 1
        else:
            own.append(a)
            prod.append(b)
    results['anchor_parity_2021'] = {
        'different_where_production_defined': int(np.count_nonzero(np.abs(np.array(own)-prod)>1e-9)),
        'production_undefined': missing,
        'max_difference': float(np.max(np.abs(np.array(own)-prod)))}
    p = live.predict(iset, subs, [0,1,5])
    neg = set(p.loc[(p.h == 0) & (p.rate_82 < 0), 'career_key'])
    pn = p[p.career_key.isin(neg) & (p.h == 1)]
    results['negative_anchor_h1'] = {
        'subjects': len(neg), 'nonzero_adapter_forecasts': int((pn.rate_82.abs()>1e-9).sum()),
        'mean_adapter_forecast': float(pn.rate_82.mean()),
        'production_multiplier_negative_h1': live.proj_.multiplier(-1, 0.8, 1)}
    real_negative = {r.career_key for r in subs.itertuples()
                     if live.proj_.anchor(r.pkey,2021)[0] < 0}
    results['negative_anchor_h1']['production_negative_subjects_with_nonzero_adapter'] = int(
        ((p.h == 1) & p.career_key.isin(real_negative) & (p.rate_82.abs()>1e-9)).sum())
    m = A1HingeExposure()
    m.fit(iset.seasons, 2021)
    m.fitted_horizons_ = (0,1,2,3,4,5)
    a = m.predict_beyond_fit(iset, subs, [4,5,6]).set_index(['career_key','h'])
    b = m.predict_beyond_fit(iset, subs, [3,5,6]).set_index(['career_key','h'])
    prod_fn = lambda x: x.rate_82*x.gp_share*x.p_play
    delta = prod_fn(a.xs(6,level='h'))-prod_fn(b.xs(6,level='h'))
    results['extrapolation_depends_on_requested_other_horizons'] = {
        'max_war_difference': float(delta.abs().max()), 'mean_abs_difference': float(delta.abs().mean())}
    one = subs[subs.career_key == subs.iloc[0].career_key]
    single = m.predict_beyond_fit(iset, one, [4,5,6]).set_index(['career_key','h'])
    ix = single.xs(6,level='h').index
    results['extrapolation_depends_on_other_players'] = float((prod_fn(a.xs(6,level='h').loc[ix])-prod_fn(single.xs(6,level='h'))).abs().max())
    cur = ProductionCurrency()
    costframe = pd.DataFrame({'signed': pd.to_datetime(['2017-07-01','2018-07-01']),
                              'start_yr':[2019,2019], 'end_yr':[2019,2019],
                              'length':[1,1], 'aav':[1_000_000.,1_000_000.]})
    results['early_signing_one_year_costs'] = cur.cost(costframe).tolist()
    c = contract_sample()
    early_train = c[(c.signed < pd.Timestamp('2019-01-01')) & (c.start_yr >= 2019)]
    results['2019_january_training_rows_using_future_start_cap'] = len(early_train)
    results['contracts_with_horizon_above_attachment_limit'] = int(
        (c.end_yr - (c.latest_complete + 1) > 8).sum())
    results['fixed_named_player_guard_refuses_seven_year_term'] = bool(
        set(range(7))-set(C.FITTED_HORIZONS))
    out = root/'50_REBUILD/output/review_repair_followup.json'
    out.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))

if __name__ == '__main__':
    main()
