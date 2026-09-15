"""Audit the named-player runner's claimed shared currency without editing it.

Run with --candidate-root pointing to an isolated checkout with birthdates.csv.
Capture actual fitted equations and reprice live forecasts on the rebuild's
equation for the same quarter. Write only aggregate review evidence.
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
    os.environ['SOURCE_DIR'] = str(root/'10_SOURCE')
    os.environ['OUTPUT_DIR'] = str(root/'30_OUTPUT')
    os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
    sys.path.insert(0, str(args.candidate_root.resolve()/'50_REBUILD/code'))
    import numpy as np
    import pandas as pd
    import rebuild_config as C
    import contract_price_model as CP
    import run_player_comparison as runner
    from production_currency import ProductionCurrency
    from player_season_table import norm_name
    original_fit, original_value = ProductionCurrency.fit, ProductionCurrency.value
    records = []

    def fit(self, d, before_date=None):
        self.review_cut = str(before_date)
        return original_fit(self, d, before_date)

    def value(self, d):
        out = original_value(self, d)
        records.append((self.review_cut, self.coef_.copy(), d.copy(), out.copy()))
        return out

    # Wrappers observe the executed path; calculations and input frames are
    # unchanged. Restore methods before counterfactual repricing.
    try:
        ProductionCurrency.fit, ProductionCurrency.value = fit, value
        runner.main()
    finally:
        ProductionCurrency.fit, ProductionCurrency.value = original_fit, original_value
    by_cut = {}
    for record in records:
        by_cut.setdefault(record[0], []).append(record)
    named = {(norm_name(raw)+'|'+pos, year) for raw,pos,year,term,note in runner.CASES}
    deltas, coefficient_errors = [], []
    paired = 0
    for cut, pair in by_cut.items():
        if len(pair) != 2:
            continue
        paired += 1
        rebuilt, live = pair  # main prices rebuilt first, then live
        coefficient_errors.append(float(np.max(np.abs(rebuilt[1]-live[1]))))
        common = ProductionCurrency('in')
        common.coef_ = rebuilt[1]
        same_equation = common.value(live[2])
        for idx, row in live[2].iterrows():
            if (row.pkey, int(row.start_yr)) in named:
                deltas.append(float(same_equation.loc[idx]-live[3].loc[idx]))
    results = dict(candidate=str(args.candidate_root), paired_quarters=paired,
        quarters_with_different_coefficients=sum(x>1e-9 for x in coefficient_errors),
        max_coefficient_difference=max(coefficient_errors), named_rows=len(deltas),
        max_named_value_change_using_shared_currency=max(abs(x) for x in deltas),
        mean_absolute_named_value_change_using_shared_currency=float(np.mean(np.abs(deltas))))

    # Exercise the new rejection path when *every* contract lacks history.
    # This is an expected coverage outcome for early/unseen players, not an
    # invalid price or a model-estimation failure.
    import player_season_table as T
    table = T.build(birthdate_csv=C.OUT_DIR/'birthdates.csv', verbose=False)
    class Complete:
        def fit(self, *args, **kwargs):
            pass
        def predict_beyond_fit(self, iset, subjects, horizons):
            return pd.DataFrame([dict(career_key=r.career_key,h=h,rate_82=1.,
                p_play=1.,gp_share=1.,extrapolated=0.)
                for r in subjects.itertuples() for h in horizons])
    missing = pd.DataFrame(dict(pkey=['review_nonexistent|F'],latest_complete=[2020],
        start_yr=[2021],end_yr=[2022],length=[2]))
    try:
        out = CP.attach_forecasts(missing, Complete, table, verbose=False)
        results['all_rejected_result'] = dict(returned_rows=len(out),rejections=len(CP.attach_forecasts.rejected_))
    except Exception as exc:
        results['all_rejected_result'] = f'{type(exc).__name__}: {exc}'
    (root/'50_REBUILD/output/current_named_review.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
