"""Independent review of star-walk diagnostic 55f23cb.

Use the isolated checkout at 50_REBUILD/output/star_walk_review. Run modes
setup, cohort, run, then audit with the review Python environment. The full
cohort is regenerated with the current leader before running the diagnostic.
The audit rebuilds membership and every row's arithmetic, checks the projected
steps against full-harness forecasts, and resamples entire careers.
Generated evidence stays in ignored output directories. No candidate is adopted.
"""
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/star_walk_review'
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
    import run_star_walk_diagnostic as D
    D.main()
elif mode=='cohort':
    from player_season_table import build,birthdate_source
    from run_npv_simulation import LEADER
    from forecast_harness import Harness
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    h=Harness(table).run(LEADER(),pages=C.DEV_PAGES,horizons=(0,1,2,3,4,5))
    h.assign(variant='adopted').to_csv(C.out_path('star_residual_v12.csv'),index=False)
    print('FRESH_COHORT',len(h))
elif mode=='audit':
    from player_season_table import build,birthdate_source
    from aging_additive import AdditiveAging
    from information_set import build as info,decision_date_for_page
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    s=table[table.GP>=C.MIN_GP].set_index(['career_key','syr'])
    d=pd.read_csv(C.out_path('star_walk_diagnostic.csv'))
    h=pd.read_csv(C.out_path('star_residual_v12.csv'))
    h=h.set_index(['career_key','page','h'])
    assert not d.duplicated(['career_key','page','k']).any()
    assert np.isfinite(d[['w','obs','arm1','arm2','arm3','ref_surv','lvl_err']]).all().all()
    assert (d.w>0).all()
    curves={}; refs={}
    for page in C.DEV_PAGES:
        t=info(table,decision_date_for_page(page),t0=page).seasons
        curves[page]=AdditiveAging(level_mode='lagged',selection='impute').fit(t,page)
        refs[page]=AdditiveAging(level_mode='lagged',selection='none').fit(t,page)
    expected=[]
    raw=table.set_index(['career_key','syr'])
    eligible=played=qualified=0
    for (ck,page,k),r in h.iterrows():
        if r.tier!='3+' or k>=5 or page+k+1>C.LAST_SOURCE_SEASON: continue
        t=page+k
        eligible+=1
        played+=int(all((ck,y) in raw.index and raw.loc[(ck,y),'GP']>=C.PARTICIPATION_GP for y in [t-1,t,t+1]))
        qualified+=int(all((ck,y) in s.index for y in [t-1,t,t+1]))
        if all((ck,y) in s.index for y in [t-1,t,t+1]) and np.isfinite(s.loc[(ck,t),'age']):
            expected.append((ck,page,k))
    assert set(expected)==set(d[['career_key','page','k']].itertuples(index=False,name=None))
    print('ATTRITION',eligible,'calendar-observable;',played,'three played;',qualified,'three >=10 GP;',len(expected),'age available')
    err=[]
    for r in d.itertuples():
        t=r.page+r.k
        a,b,c=[s.loc[(r.career_key,y)] for y in [t-1,t,t+1]]
        p0=h.loc[(r.career_key,r.page,r.k),'rate_82']
        p1=h.loc[(r.career_key,r.page,r.k+1),'rate_82']
        curve=curves[r.page]
        x=curve.step([b.age],[a.WAR_82],[float(b.pos=='D')])[0]
        y=curve.step([b.age],[b.WAR_82],[float(b.pos=='D')])[0]
        z=refs[r.page].step([b.age],[a.WAR_82],[float(b.pos=='D')])[0]
        want=[min(b.GP,c.GP),c.WAR_82-b.WAR_82,x,y,p1-p0,z,p0-b.WAR_82]
        got=[r.w,r.obs,r.arm1,r.arm2,r.arm3,r.ref_surv,r.lvl_err]
        assert np.allclose(want,got,rtol=0,atol=1e-12)
        err.append(curve.step([b.age],[p0],[float(b.pos=='D')])[0]-r.arm3)
    print('ALL_ROWS_MEMBERSHIP_INPUTS_ARITHMETIC_IDENTICAL',len(d))
    print('PROJECTED_STEP_AGE_POSITION_MAX_DIFF',max(abs(np.array(err))))
    d['season']=d.page+d.k
    print('COUNTS',len(d),'careers',d.career_key.nunique(),'distinct_transitions',len(d.drop_duplicates(['career_key','season'])))
    print('MEANS',{col:np.average(d[col],weights=d.w) for col in ['obs','arm1','arm2','arm3','ref_surv']})
    rng=np.random.default_rng(20260924)
    careers=sorted(d.career_key.unique())
    idx=rng.integers(0,len(careers),(2000,len(careers)))
    sums=d.groupby('career_key').w.sum().reindex(careers).to_numpy()
    for col in ['arm1','arm2','arm3','ref_surv']:
        numerator=(d.w*(d[col]-d.obs)).groupby(d.career_key).sum().reindex(careers).to_numpy()
        boot=numerator[idx].sum(axis=1)/sums[idx].sum(axis=1)
        print('PAIRED_CAREER_BOOTSTRAP',col,np.percentile(boot,[2.5,97.5]).tolist())
    print('PAGE_ERRORS',d.assign(err=d.arm1-d.obs).groupby('page').apply(lambda g:np.average(g.err,weights=g.w),include_groups=False).to_dict())
