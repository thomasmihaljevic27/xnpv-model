"""Reproduce the valuation comparison and audit its sample and comparison controls."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate-root', type=Path, required=True)
    ap.add_argument('--mode', choices=['valuation', 'checks', 'component', 'attrition'], default='valuation')
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
    from contract_source import birthdate_table
    from player_season_table import build, birthdate_source
    birthdate_table(root / '10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'), index=False)
    if args.mode == 'checks':
        import repair_checks
        repair_checks.main()
        return
    if args.mode == 'component':
        import traceback
        from ability_forecast import A2AgingParticipationImputed
        table = build(birthdate_csv=birthdate_source()[0], verbose=False)
        try:
            A2AgingParticipationImputed().fit(table[table.syr < 2015], before=2015)
        except Exception:
            traceback.print_exc()
        else:
            raise AssertionError('Reported component fit error did not reproduce')
        return

    import run_valuation_sensitivity as V
    from ability_forecast import A1AgingParticipationImputedNC
    if args.mode == 'attrition':
        import forecast_harness as H
        import information_set as I
        table = build(birthdate_csv=birthdate_source()[0], verbose=False)
        sample = V.contract_sample()
        sample = sample[~sample.start_yr.isin(C.CONFIRMATORY_START_YEARS)].copy()
        attached = pd.read_pickle(root / '50_REBUILD/output/valuation_attached_A1HingeExposure.pkl')
        attached = attached[~attached.start_yr.isin(C.CONFIRMATORY_START_YEARS)].copy()
        priced = pd.read_csv(C.out_path('valuation_sensitivity.csv'))
        priced = priced[priced.forecast == 'the adopted candidate']
        priced_ids = set(priced.contract_id)
        categories = []
        for L, grp in sample.groupby('latest_complete'):
            t0 = int(L) + 1
            iset = I.build(table, I.decision_date_for_page(t0), t0=t0)
            subjects = set(H.subjects_at(iset).pkey)
            for r in grp.itertuples():
                if r.contract_id in priced_ids:
                    reason = 'priced'
                elif r.Index in attached.index:
                    cut = r.signed.to_period('Q').start_time
                    n_train = int((attached.signed < cut).sum())
                    reason = 'price_fit_below_200' if n_train < 200 else 'other_after_attachment'
                elif t0 < C.FIRST_SOURCE_SEASON + 3:
                    reason = 'early_page'
                elif r.pkey not in subjects:
                    reason = 'no_matching_subject'
                elif r.start_yr < t0:
                    reason = 'term_includes_pre_forecast_season'
                else:
                    reason = 'other_missing_forecast'
                categories.append(dict(term=int(r.length), reason=reason))
        counts = pd.DataFrame(categories)
        result = dict(total=len(counts), reasons=counts.reason.value_counts().to_dict(),
                      by_term=pd.crosstab(counts.term, counts.reason).to_dict())
        (root / '50_REBUILD/output/valuation_attrition.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return
    attached = {}
    samples = []
    tables = []
    original = V.attach_forecasts
    def capture(sample, cls, table, **kw):
        d = original(sample, cls, table, **kw)
        attached[cls.__name__] = d.copy()
        if not samples:
            samples.append(sample.copy())
            tables.append(table)
        d.to_pickle(root / '50_REBUILD/output' / ('valuation_attached_' + cls.__name__ + '.pkl'))
        return d
    V.attach_forecasts = capture
    try:
        V.main()
    finally:
        V.attach_forecasts = original
    out = pd.read_csv(C.out_path('valuation_sensitivity.csv'))
    key = ['pkey', 'start_yr']
    leader = out[out.forecast == 'the adopted candidate'].copy()
    leader['fixed_tier'] = pd.cut(leader.war_per_season, V.TIER_EDGES, labels=V.TIER_NAMES)
    fixed = leader[key + ['fixed_tier']]
    result = {'candidate': str(candidate), 'forecasts': [], 'retention': []}
    for lab, r in out.groupby('forecast', sort=False):
        tiers = pd.cut(r.war_per_season, V.TIER_EDGES, labels=V.TIER_NAMES)
        same = r.merge(fixed, on=key, validate='one_to_one')
        result['forecasts'].append(dict(forecast=lab, n=len(r),
            own_tier_counts=r.groupby(tiers, observed=False).size().to_dict(),
            fixed_tier_surplus_M=(same.groupby('fixed_tier', observed=False).surplus.mean()/1e6).to_dict(),
            own_top_mean_length=float(r.loc[tiers == '2+', 'length'].mean())))
    sample = samples[0]
    elig = sample[~sample.start_yr.isin(C.CONFIRMATORY_START_YEARS)].copy()
    for cls, d in attached.items():
        matched = elig.index.isin(d.index)
        priced = elig.contract_id.isin(leader.contract_id).to_numpy()
        result['retention'].append(dict(model=cls, eligible=len(elig), attached=int(matched.sum()),
            without_forecast=int((~matched).sum()), attached_but_not_common_priced=int((matched & ~priced).sum()),
            common_priced=int(priced.sum())))
    # A true participation-only ablation retains the same aging adjustment.
    class WithoutParticipation(A1AgingParticipationImputedNC):
        def _p_play(self, a, subs, h):
            return np.ones(len(subs))
    print('\nINDEPENDENT PARTICIPATION-ONLY ABLATION', flush=True)
    d_alt = V.prep(original(sample, WithoutParticipation, tables[0], verbose=False))
    d_base = V.prep(attached['A1AgingParticipationImputedNC'])
    d_alt = d_alt[~d_alt.start_yr.isin(C.CONFIRMATORY_START_YEARS)].copy()
    d_base = d_base[~d_base.start_yr.isin(C.CONFIRMATORY_START_YEARS)].copy()
    for d in [d_alt, d_base]:
        d['cut'] = d.signed.dt.to_period('Q').dt.start_time
    own = V.price(d_alt, 'in').merge(fixed, on=key, validate='one_to_one')
    # Hold the base currency fixed by quarter to distinguish repricing from
    # changes in expected production. This is a diagnostic, not an adopted model.
    held = []
    for cut, te in d_alt.groupby('cut'):
        cur = V.ProductionCurrency('in').fit(d_base, before_date=cut)
        if cur.coef_ is None:
            continue
        te = te.copy()
        te['surplus'] = cur.value(te) - cur.cost(te)
        held.append(te)
    held = pd.concat(held).merge(fixed, on=key, validate='one_to_one')
    base = out[out.forecast == 'calibrated total + aging + participation'].merge(fixed, on=key, validate='one_to_one')
    result['participation_only'] = {}
    for lab, r in [('base', base), ('refitted_currency', own), ('held_currency', held)]:
        result['participation_only'][lab] = (r.groupby('fixed_tier', observed=False).surplus.mean()/1e6).to_dict()
        r.to_csv(root / '50_REBUILD/output' / ('valuation_participation_' + lab + '.csv'), index=False)
    dest = root / '50_REBUILD/output/review_valuation_sensitivity.json'
    dest.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
