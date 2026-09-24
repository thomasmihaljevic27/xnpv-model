"""Independent sustained-quality review of f83240a.

Run setup, checks, run, probe and audit in the review Python environment.
The isolated candidate is star_sustained_review; historical coefficients and
forecasts are compared against prior independently reviewed checkouts.
Generated evidence stays in ignored output. No candidate is adopted.
"""
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/star_sustained_review'
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
elif mode=='run':
    import run_star_residual as R
    R.main()
elif mode=='checks':
    import repair_checks as R
    R.main()
elif mode=='probe':
    import importlib.util
    from aging_additive import AdditiveAging
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    spec=importlib.util.spec_from_file_location('old_aging',ROOT/'50_REBUILD/output/star_walk_review/50_REBUILD/code/aging_additive.py')
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    s=pd.DataFrame({'career_key':['a','a','a','a','b','c','c','d','d'],
                    'syr':[2018,2019,2020,2021,2019,2018,2019,2018,2020],
                    'WAR_82':[1.,4.,999.,888.,3.,4.,-2.,2.,999.]})
    frame=pd.DataFrame({'career_key':['c','a','d','b'],'syr':[2020]*4},index=[8,2,9,11])
    model=AdditiveAging(sustained=True,selection='impute')
    got=model._sustained_level(s,frame,'WAR_82')
    assert np.allclose(got,[-2.,1.,np.nan,3.],equal_nan=True)
    assert got.index.equals(frame.index)
    changed=s.copy(); changed.loc[changed.syr>=2020,'WAR_82']=-10000.
    assert np.allclose(got,model._sustained_level(changed,frame,'WAR_82'),equal_nan=True,rtol=0,atol=0)
    design=model._design([27.,28.],[3.,2.],[0.,1.],[0.,0.])
    assert np.array_equal(design[:,5:7],design[:,7:9])
    print('SUSTAINED_ARITHMETIC_MISSING_DATES_INDEX_AND_WALK_DUPLICATION_PASS')
    for page in C.DEV_PAGES:
        ref=AdditiveAging(level_mode='lagged',selection='impute').fit(table,page)
        fit=AdditiveAging(sustained=True,selection='impute').fit(table,page)
        prior=old.AdditiveAging(level_mode='lagged',selection='impute').fit(table,page)
        assert ref.fit_key_==fit.fit_key_ and np.array_equal(ref.coef_,prior.coef_)
        future=table.copy(); future.loc[future.syr>=page,'WAR_82']+=10000
        trial=AdditiveAging(sustained=True,selection='impute').fit(future,page)
        assert fit.fit_key_==trial.fit_key_ and np.array_equal(fit.coef_,trial.coef_)
        print('SAME_ROWS_PRIOR_COEFFICIENTS_FUTURE_INVARIANCE',page,fit.n_fit_)
    print('2021_COEFFICIENTS',ref.coef_.tolist(),fit.coef_.tolist())
    print('2021_STEP',ref.step([27.],[3.2],[0.]),fit.step([27.],[3.2],[0.]))
elif mode=='audit':
    from run_skater_contract_test import Boot
    d=pd.read_csv(C.out_path('star_residual_v13.csv'))
    keys=['career_key','page','h']
    ref=d[d.variant=='adopted'].set_index(keys)
    new=d[d.variant=='sustained'].set_index(keys).reindex(ref.index)
    assert ref.index.is_unique and new.index.is_unique
    for col in ['p_play','gp_share']:
        assert np.array_equal(ref[col],new[col])
    assert np.array_equal(ref.xs(0,level='h').rate_82,new.xs(0,level='h').rate_82)
    old=pd.read_csv(ROOT/'50_REBUILD/output/star_multi_review/50_REBUILD/output/star_residual_v12.csv')
    old=old[old.variant=='adopted'].set_index(keys).reindex(ref.index)
    for col in ['rate_82','gp_share','p_play','pred_war']:
        assert np.array_equal(old[col],ref[col])
    print('PRIOR_BASELINE_AND_UNCHANGED_COMPONENTS_EXACT',len(ref))
    boot=Boot(ref.reset_index().career_key)
    print('MAE',ref.e_war.abs().mean(),new.e_war.abs().mean(),'wins',round(2000*boot.lower_share(ref.e_war.abs(),new.e_war.abs())))
    print('MAE_DIFFERENCE_CI',boot.mean_ci(new.e_war.abs()-ref.e_war.abs()))
    print('ADOPTED_TIER_RATE',ref.reset_index().groupby(['tier','h']).e_rate.mean().unstack().to_string())
