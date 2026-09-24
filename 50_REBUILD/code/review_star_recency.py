"""Independent recency review of 293f4d6.

Run setup, checks, run, probe and audit in the review Python environment.
The isolated candidate is star_recency_review; historical coefficients and
forecasts are compared against prior independently reviewed checkouts.
Generated evidence stays in ignored output. No candidate is adopted.
"""
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/star_recency_review'
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
    from unittest.mock import patch
    import importlib.util
    from aging_additive import AdditiveAging
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    spec=importlib.util.spec_from_file_location('old_aging',ROOT/'50_REBUILD/output/star_sustained_review/50_REBUILD/code/aging_additive.py')
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    sys.path.insert(0,str(CANDIDATE/'50_REBUILD/code'))
    original=np.linalg.lstsq
    def capture(model,page):
        saved=[]
        def record(X,y,**kw):
            saved.append((X.copy(),y.copy()))
            return original(X,y,**kw)
        with patch.object(np.linalg,'lstsq',record):
            model.fit(table,page)
        return model,saved[-1]
    for page in C.DEV_PAGES:
        ref,(Xa,ya)=capture(AdditiveAging(selection='impute'),page)
        rc,(Xr,yr)=capture(AdditiveAging(selection='impute',recency_halflife=5),page)
        assert ref.fit_rows_.id.equals(rc.fit_rows_.id)
        outcome=ref.fit_rows_.id.str.split('|').str[1].astype(float).to_numpy()+1
        assert (outcome<page).all()
        factor=2.**(-((page-1)-outcome)/5.)
        np.testing.assert_allclose(rc.fit_rows_.w,ref.fit_rows_.w*factor,rtol=1e-14,atol=0)
        # Divide the actual least-squares inputs by sqrt(weight): same target
        # and design matrix, including imputed departures, before weighting.
        wa=np.sqrt(ref.fit_rows_.w.to_numpy()); wr=np.sqrt(rc.fit_rows_.w.to_numpy())
        np.testing.assert_allclose(Xa/wa[:,None],Xr/wr[:,None],rtol=1e-13,atol=1e-12)
        np.testing.assert_allclose(ya/wa,yr/wr,rtol=1e-13,atol=1e-12)
        prior=old.AdditiveAging(selection='impute').fit(table,page)
        assert np.array_equal(prior.coef_,ref.coef_)
        ones=AdditiveAging(selection='impute',recency_halflife=np.inf).fit(table,page)
        assert np.array_equal(ones.coef_,ref.coef_) and ones.fit_key_==ref.fit_key_
        future=table.copy(); future.loc[future.syr>=page,'WAR_82']+=10000
        trial=AdditiveAging(selection='impute',recency_halflife=5).fit(future,page)
        assert np.array_equal(trial.coef_,rc.coef_) and trial.fit_key_==rc.fit_key_
        print('ROWS_TARGETS_DESIGN_WEIGHTS_FUTURE_ONES_PRIOR_PASS',page,rc.n_fit_)
    print('2021_STEPS',ref.step([27.,31.],[3.2,3.2],[0.,0.]),rc.step([27.,31.],[3.2,3.2],[0.,0.]))
    import repair_checks as checks
    from ability_forecast import A1StatusAgingRecency
    with patch.object(A1StatusAgingRecency,'AGING_RECENCY_HALFLIFE',4.):
        try:
            checks.c46(table)
        except AssertionError as e:
            print('HALFLIFE_MUTATION_CAUGHT',str(e))
        else:
            raise AssertionError('half-life mutation escaped')
elif mode=='audit':
    from run_skater_contract_test import Boot
    d=pd.read_csv(C.out_path('star_residual_v14.csv'))
    keys=['career_key','page','h']
    ref=d[d.variant=='adopted'].set_index(keys)
    new=d[d.variant=='recency'].set_index(keys).reindex(ref.index)
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
    print('ADOPTED_STAR_BIASES',ref.reset_index().query("tier == '3+'").groupby('h')[['e_rate','e_war']].mean().to_string())
    print('ADOPTED_TIER_RATE',ref.reset_index().groupby(['tier','h']).e_rate.mean().unstack().to_string())
