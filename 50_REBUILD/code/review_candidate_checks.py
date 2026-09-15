"""Independent review probes. Development forecasts only; no model edits."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import rebuild_config as C
import information_set as I
import forecast_harness as H
from player_season_table import build
from ability_forecast import A1HingeExposure, A0Production
from contract_price_model import contract_sample
from contract_source import birthdate_table


def main():
    results = {}
    bd = C.out_path('review_birthdates.csv')
    birthdate_table(C.SOURCE_DIR / 'ep_birthdates.csv').to_csv(bd, index=False)
    table = build(birthdate_csv=bd, verbose=False)
    results['age_coverage'] = float(table.has_age.mean())
    short = table[table.syr.isin([2019, 2020]) & (table.GP > 0)].copy()
    ratio = short.WAR_82 * short.gp_share / short.WAR
    results['rate_times_share_over_prorated_total'] = {
        str(y): float(ratio[short.syr == y].median()) for y in [2019, 2020]}
    results['source_rows_1_to_9_games'] = int(table.GP.between(1, 9).sum())
    c = contract_sample()
    counts = []
    for r in c.itertuples():
        tr = c[c.start_yr < r.start_yr]
        counts.append(int((tr.signed > r.signed).sum()))
    results['contracts_with_future_signings_in_start_year_training_pool'] = int(np.count_nonzero(counts))
    results['maximum_future_signings_in_pool'] = int(max(counts))
    iset = I.build(table, I.decision_date_for_page(2021), t0=2021)
    subs = H.subjects_at(iset)
    recent = iset.seasons[(iset.seasons.syr == 2018) & (iset.seasons.GP >= C.MIN_GP)]
    results['eligible_third_year_only_careers_dropped'] = len(set(recent.career_key) - set(subs.career_key))

    class DropsRows(A0Production):
        name = 'review deliberately incomplete predictor'
        def predict(self, iset, subs, horizons):
            return super().predict(iset, subs.iloc[:1], horizons)
    got = H.Harness(table).run(DropsRows(), pages=(2021,), horizons=(0,))
    results['harness_accepts_missing_predictions'] = {'returned': len(got), 'required': len(subs)}
    # Dates alone expose the canonical-page substitution without looking at outcomes.
    results['may_2025_automatic_information_set'] = ''
    try:
        I.build(table, pd.Timestamp('2025-06-01').date())
    except AssertionError as e:
        results['may_2025_automatic_information_set'] = str(e)
    m = A1HingeExposure()
    m.fit(iset.seasons, before=2021)
    pred = m.predict(iset, subs, (5, 6, 7, 8))
    results['participation_by_horizon'] = {
        str(h): {'min': float(g.p_play.min()), 'max': float(g.p_play.max()),
                 'unique': int(g.p_play.nunique())} for h, g in pred.groupby('h')}
    pairs = m._training_pairs(iset.seasons, 2021, [0])
    results['rate_fit_rows_below_participation_threshold'] = int((pairs.y_rate.notna() & ~pairs.y_played).sum())
    results['finite_predictions'] = bool(np.isfinite(pred[['rate_82','gp_share','p_play']]).all().all())
    results['participation_fitted_horizons'] = [int(h) for h, c in m.part_.coef_.items() if c is not None]
    p = C.out_path('review_candidate_checks.json')
    p.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
