"""Independent closure review of matched-aging candidate 670b614.

Use the isolated checkout at 50_REBUILD/output/star_matched_review. Run modes
setup, checks, run, probe, negative, then audit with the review Python environment.
The probe compares the adopted curve to the preceding 477316d implementation.
Generated evidence stays in ignored output directories. No candidate is adopted.
"""


import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/star_matched_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
mode=sys.argv[1]
if mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif mode=='checks':
    import repair_checks as R
    R.main()
elif mode=='run':
    import run_star_residual as R
    R.main()
elif mode=='negative':
    from player_season_table import build,birthdate_source
    import repair_checks as R
    from ability_forecast import A1StatusNoLevelAgingMatched
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    A1StatusNoLevelAgingMatched.AGING_SAMPLE='own'
    try:
        R.c46(table)
    except AssertionError as e:
        print('SAMPLE_REVERSION_CAUGHT',e)
    else:
        raise AssertionError('sample reversion escaped check 46')
    finally:
        A1StatusNoLevelAgingMatched.AGING_SAMPLE='lagged'
    # A separate mutation preserves row membership but changes the weights.
    # With a 1.01 multiplier no integer game count crosses the MIN_GP cutoff.
    from aging_additive import AdditiveAging
    original=AdditiveAging.fit
    def changed_weights(self,table,*args,**kwargs):
        if self.level_mode=='none' and self.sample=='lagged':
            table=table.copy()
            table['GP']=table.GP*1.01
        return original(self,table,*args,**kwargs)
    AdditiveAging.fit=changed_weights
    try:
        R.c46(table)
    except AssertionError as e:
        print('WEIGHT_MUTATION_CAUGHT',e)
    else:
        raise AssertionError('weight mutation escaped check 46')
    finally:
        AdditiveAging.fit=original
elif mode=='probe':
    import importlib.util
    from player_season_table import build,birthdate_source
    from aging_additive import AdditiveAging
    from information_set import build as info,decision_date_for_page
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    spec=importlib.util.spec_from_file_location('old_aging',ROOT/'50_REBUILD/output/star_residual_review/50_REBUILD/code/aging_additive.py')
    old=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    for page in C.DEV_PAGES:
        t=info(table,decision_date_for_page(page),t0=page).seasons
        before=old.AdditiveAging(level_mode='lagged',selection='impute').fit(t,page)
        ref=AdditiveAging(level_mode='lagged',selection='impute').fit(t,page)
        matched=AdditiveAging(level_mode='none',selection='impute',sample='lagged').fit(t,page)
        hinge=AdditiveAging(level_mode='lagged',selection='impute',level_knot=2.0).fit(t,page)
        assert np.array_equal(before.coef_,ref.coef_)
        assert ref.fit_key_==matched.fit_key_==hinge.fit_key_
        print('OLD_COEFFICIENTS_IDENTICAL_AND_ROWS_MATCH',page,ref.n_fit_,flush=True)
    s=t[t.GP>=C.MIN_GP]
    p=s.merge(s.assign(syr=s.syr-1),on=['career_key','syr'],suffixes=('','_n'))
    p=p[(p.syr+1<2021)&p.age.notna()]
    lag=s[['career_key','syr','WAR_82']].rename(columns={'WAR_82':'lag'})
    lag.syr+=1
    p=p.merge(lag,on=['career_key','syr'],how='left').dropna(subset=['lag'])
    p['observed']=p.WAR_82_n-p.WAR_82
    p['fitted']=ref.step(p.age,p.lag,p.pos=='D')
    for col in ['lag','WAR_82']:
        d=p[p[col]>=3]
        print('TRAINING_DIAGNOSTIC',col,len(d),d[['observed','fitted']].mean().to_dict(),flush=True)
        print('TRAINING_WEIGHTED',col,{x:np.average(d[x],weights=np.minimum(d.GP,d.GP_n)) for x in ['observed','fitted']},flush=True)
elif mode=='audit':
    keys=['career_key','page','h']
    data=pd.read_csv(C.out_path('star_residual_v11.csv'))
    runs={k:d.set_index(keys) for k,d in data.groupby('variant')}
    ref=runs['adopted']
    for name,d in runs.items():
        assert d.index.is_unique and d.index.equals(ref.index)
        for col in ['p_play','gp_share']:
            assert np.array_equal(d[col].to_numpy(),ref[col].to_numpy())
        assert np.array_equal(d.xs(0,level='h').rate_82.to_numpy(),ref.xs(0,level='h').rate_82.to_numpy())
        print('UNCHANGED_COMPONENTS',name,len(d))
    prior=pd.read_csv(ROOT/'50_REBUILD/output/star_residual_review/50_REBUILD/output/star_residual.csv')
    prior=prior[prior.variant=='adopted'].set_index(keys).reindex(ref.index)
    for col in ['rate_82','gp_share','p_play','pred_war']:
        assert np.array_equal(prior[col].to_numpy(),ref[col].to_numpy())
    matched=pd.read_csv(ROOT/'50_REBUILD/output/star_residual_review/50_REBUILD/output/review_matched_no_level.csv').set_index(keys).reindex(ref.index)
    d=runs['no_level_matched']
    for col in ['rate_82','gp_share','p_play','pred_war']:
        assert np.allclose(matched[col],d[col],atol=1e-12,rtol=0)
    print('PRIOR_ADOPTED_EXACT_AND_INDEPENDENT_MATCHED_REPRODUCED',len(ref))
