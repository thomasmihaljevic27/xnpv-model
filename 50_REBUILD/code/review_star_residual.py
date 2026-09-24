"""Independent review of star candidate 477316d.

Use the isolated checkout at 50_REBUILD/output/star_residual_review. Run modes
setup, checks, run, probe, then audit with the review Python environment.
Generated evidence stays in ignored output directories. The probe is a
diagnostic, not a new adopted forecast; its contract-dollar score is not run.
"""


import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/star_residual_review'
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
elif mode=='probe':
    from player_season_table import build,birthdate_source
    from aging_additive import AdditiveAging
    import forecast_harness as H
    from ability_forecast import A1StatusNoLevelAging
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    original=np.linalg.lstsq
    calls=[]
    def capture(x,y,*args,**kwargs):
        calls.append(x.shape)
        return original(x,y,*args,**kwargs)
    np.linalg.lstsq=capture
    for page in C.DEV_PAGES:
        for mode_ in ['lagged','none']:
            calls.clear()
            model=AdditiveAging(level_mode=mode_,selection='impute').fit(table,page)
            print('AGING_FIT',page,mode_,calls,flush=True)
    np.linalg.lstsq=original
    class MatchedAging(AdditiveAging):
        def _design(self,age,level,is_d,exp):
            # Build with lagged levels so BOTH observed and imputed seasons
            # keep the adopted fit's eligibility. Remove the two level columns,
            # retaining their missingness mask: only the regressors change.
            x=super()._design(age,level,is_d,exp)[:,:5].copy()
            x[~np.isfinite(np.asarray(level,float)),:]=np.nan
            return x
    class MatchedNoLevel(A1StatusNoLevelAging):
        name='review: no level on adopted fitting rows'
        def fit(self,table,before):
            super().fit(table,before)
            self.aging_=MatchedAging(level_mode='lagged',selection='impute').fit(table,before)
            return self
    # Prove the diagnostic preserves the actual weighted design and target,
    # rather than relying on equal row counts as evidence of equal samples.
    matrices=[]
    def capture_matrix(x,y,*args,**kwargs):
        matrices.append((x.copy(),y.copy()))
        return original(x,y,*args,**kwargs)
    np.linalg.lstsq=capture_matrix
    try:
        for page in C.DEV_PAGES:
            matrices.clear()
            AdditiveAging(level_mode='lagged',selection='impute').fit(table,page)
            MatchedAging(level_mode='lagged',selection='impute').fit(table,page)
            (x0,y0),(xm,ym)=matrices
            assert np.array_equal(x0[:,:5],xm)
            assert np.array_equal(y0,ym)
            print('MATCHED_DESIGN_IDENTICAL',page,len(y0),flush=True)
    finally:
        np.linalg.lstsq=original
    out=H.Harness(table).run(MatchedNoLevel(),pages=C.DEV_PAGES,horizons=(0,1,2,3,4,5))
    out.to_csv(C.out_path('review_matched_no_level.csv'),index=False)
    print('MATCHED_DONE',len(out),flush=True)
elif mode=='audit':
    from run_skater_contract_test import Boot
    path=C.out_path('star_residual.csv')
    allruns=pd.read_csv(path)
    print('VARIANTS',allruns.variant.unique())
    a=allruns[allruns.variant=='adopted'].copy()
    keys=['career_key','page','h']
    m=pd.read_csv(C.out_path('review_matched_no_level.csv'))
    runs={k:d.set_index(keys) for k,d in allruns.groupby('variant')}
    runs['matched']=m.set_index(keys).reindex(runs['adopted'].index)
    base=runs['adopted']
    for label,d in runs.items():
        assert d.index.equals(base.index)
        assert d.index.is_unique
        for col in ['p_play','gp_share']:
            assert np.array_equal(d[col].to_numpy(),base[col].to_numpy())
        assert np.array_equal(d.xs(0,level='h').rate_82.to_numpy(),
                              base.xs(0,level='h').rate_82.to_numpy())
        mask=(d.tier=='3+')
        b=Boot(base.loc[mask].reset_index().career_key)
        print('VARIANT',label,'rmse',np.sqrt((d.e_war**2).mean()),'star_rmse',np.sqrt((d.loc[mask].e_war**2).mean()),'star_wins',round(2000*b.lower_share(base.loc[mask].e_war**2,d.loc[mask].e_war**2)))
        for tier in ['below 0','3+']:
            s=d[(d.tier==tier)&(d.index.get_level_values('h')==5)]
            print('H5',label,tier,len(s),'rate_bias',s.e_rate.mean(),'war_bias',s.e_war.mean())
        print('UNCHANGED',label,{c:float((d[c]-base[c]).abs().max()) for c in ['p_play','gp_share']},'h0_rate',float((d.xs(0,level='h').rate_82-base.xs(0,level='h').rate_82).abs().max()))
    s=a[a.tier=='3+']
    print('HORIZON_SUMMARY',s.groupby('h').agg(n=('career_key','size'),played=('played','sum'),pred_rate=('rate_82','mean'),actual=('act_rate_82','mean'),bias=('e_rate','mean')).to_string())
    p0=s[(s.h==0)&s.played].set_index(['career_key','page'])
    p5=s[(s.h==5)&s.played].set_index(['career_key','page'])
    ix=p0.index.intersection(p5.index)
    print('MATCHED_ENDPOINTS',len(ix),'h0_actual',p0.loc[ix,'act_rate_82'].mean(),'h5_actual',p5.loc[ix,'act_rate_82'].mean(),'h0_pred',p0.loc[ix,'rate_82'].mean(),'h5_pred',p5.loc[ix,'rate_82'].mean())
    b=Boot(base.reset_index().career_key)
    dm=runs['matched']
    print('MATCHED_PRIMARY',round(2000*b.lower_share(base.e_war**2,dm.e_war**2)),b.mean_ci(dm.e_war**2-base.e_war**2),'MAE',dm.e_war.abs().mean())
    print('TIER_RATE_BIAS',base.reset_index().groupby(['tier','h']).e_rate.mean().unstack().to_string())
