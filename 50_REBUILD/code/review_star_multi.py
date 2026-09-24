"""Independent review of multi-season aging candidate 3ba71cd.

Use the isolated checkout at 50_REBUILD/output/star_multi_review. Run modes
setup, checks, run, multi_probe, then audit with the review Python environment.
The probe compares the adopted curve to 670b614 and independently tests the
weighted level arithmetic, required prior season and future-data invariance.
The final audit also compares predictions to earlier independent review outputs.
Generated evidence stays in ignored output directories. No candidate is adopted.
"""
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/star_multi_review'
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
elif mode=='audit':
    keys=['career_key','page','h']
    data=pd.read_csv(C.out_path('star_residual_v12.csv'))
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

elif mode=='multi_probe':
    import importlib.util
    from aging_additive import AdditiveAging
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    spec=importlib.util.spec_from_file_location('prior_aging',ROOT/'50_REBUILD/output/star_matched_review/50_REBUILD/code/aging_additive.py')
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    model=AdditiveAging(level_mode='multi',selection='impute')
    s=pd.DataFrame({'career_key':['a']*5+['b','c','d','d'],
                    'syr':[2017,2018,2019,2020,2021,2018,2019,2017,2019],
                    'WAR_82':[-2.,1.,3.,999.,888.,2.,4.,-2.,3.]})
    frame=pd.DataFrame({'career_key':['c','a','b','d'],'syr':[2020]*4},index=[7,2,9,11])
    expected=np.array([4.,(3.+0.667-2.*0.667**2)/(1.+0.667+0.667**2),
                       np.nan,(3.-2.*0.667**2)/(1.+0.667**2)])
    got=model._multi_level(s,frame,'WAR_82')
    assert np.allclose(got,expected,equal_nan=True,rtol=0,atol=1e-14)
    assert got.index.equals(frame.index)
    future=s.copy(); future.loc[future.syr>=2020,'WAR_82']=-999999.
    assert np.allclose(got,model._multi_level(future,frame,'WAR_82'),equal_nan=True,rtol=0,atol=0)
    print('MULTI_ARITHMETIC_DATES_MISSING_T1_AND_INDEX_PASS',got.to_list(),flush=True)
    for page in C.DEV_PAGES:
        a=AdditiveAging(level_mode='lagged',selection='impute').fit(table,page)
        b=AdditiveAging(level_mode='multi',selection='impute').fit(table,page)
        prior=old.AdditiveAging(level_mode='lagged',selection='impute').fit(table,page)
        assert a.fit_key_==b.fit_key_
        assert np.array_equal(a.coef_,prior.coef_)
        changed=table.copy()
        changed.loc[changed.syr>=page,'WAR_82']+=10000
        c=AdditiveAging(level_mode='multi',selection='impute').fit(changed,page)
        assert b.fit_key_==c.fit_key_ and np.array_equal(b.coef_,c.coef_)
        print('SAME_ROWS_PRIOR_BASELINE_AND_FUTURE_INVARIANCE',page,a.n_fit_,flush=True)
    print('2021_LEVEL_COEFFICIENTS',a.coef_[5],b.coef_[5],flush=True)
    print('2021_AGE27_FORWARD_STEP',a.step([27.],[3.2],[0.]),b.step([27.],[3.2],[0.]),flush=True)
