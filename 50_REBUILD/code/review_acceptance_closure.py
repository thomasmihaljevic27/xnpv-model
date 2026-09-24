"""Independent Phase 5 acceptance review of 7b046a3.

Run setup, checks, scorecard, repairs, and audit in the review environment.
The isolated candidate is acceptance_closure_review; scoring and refactors are checked against prior independently reviewed checkouts.
Generated evidence stays in ignored output. No candidate is adopted.
"""
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/acceptance_closure_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
# Exact player-resampling using group sums, avoiding millions of DataFrame
# concatenations. Used only by the review rerun; validated against the original.
_BOOT_COUNTS={}
def counts(groups,n,seed):
    key=(groups,n,seed)
    if key not in _BOOT_COUNTS:
        rng=np.random.default_rng(seed)
        _BOOT_COUNTS[key]=np.array([np.bincount(rng.choice(groups,groups,replace=True),minlength=groups) for _ in range(n)])
    return _BOOT_COUNTS[key]
def fast_boot(d,a,b,n=2000,seed=20260922):
    g=d.groupby('pkey')
    delta=(g[b].sum()-g[a].sum()).to_numpy()
    return float(np.mean(counts(len(delta),n,seed)@delta<0))
def fast_ci(d,stat,n=2000,seed=20260923):
    groups=[v for _,v in d.groupby('pkey')]
    weights=counts(len(groups),n,seed)
    size=np.array([len(g) for g in groups]); den=weights@size
    if 'var' in stat.__code__.co_names:
        sums=np.array([g.pit.sum() for g in groups])
        squares=np.array([(g.pit**2).sum() for g in groups])
        vals=(weights@squares)/den-((weights@sums)/den)**2
    else:
        sums=np.array([float(stat(g))*len(g) for g in groups])
        vals=(weights@sums)/den
    lo,hi=np.percentile(vals,[2.5,97.5])
    return float(stat(d)),float(lo),float(hi)
def validate_fast():
    import dollar_scoring as DS
    rng=np.random.default_rng(442)
    d=pd.DataFrame({'pkey':np.repeat(np.arange(40),rng.integers(1,8,40))})
    d['a']=rng.normal(size=len(d))**2; d['b']=d.a+rng.normal(0,.2,len(d)); d['pit']=rng.random(len(d))
    assert DS.career_bootstrap(d,'a','b',n=60)==fast_boot(d,'a','b',n=60)
    for stat in [lambda x:(x.a-x.b).mean(),lambda x:x.pit.var(ddof=0),lambda x:x.pit.between(.1,.9).mean()]:
        np.testing.assert_allclose(DS.ci(d,stat,n=60),fast_ci(d,stat,n=60),rtol=0,atol=1e-12)
    print('GROUP_SUM_RESAMPLING_MATCHES_ORIGINAL')
mode=sys.argv[1]
if mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif mode=='checks':
    import repair_checks as R
    R.main()
elif mode=='repairs':
    import repair_checks as R
    import dollar_scoring as DS
    print('CHECK47', R.c47(None))
    print('CHECK48', R.c48(None))
    DS.MONEY_DECIMALS=12
    try:
        R.c48(None)
    except AssertionError as e:
        print('BROKEN_PRECISION_REJECTED',e)
    else:
        raise AssertionError('precision mutation escaped')
    DS.MONEY_DECIMALS=6
    # Test the identity repair by loading precisely the preceding scorer.
    import importlib.util
    spec=importlib.util.spec_from_file_location('old_scoring', ROOT/'50_REBUILD/output/acceptance_review/50_REBUILD/code/dollar_scoring.py')
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    current=DS.score_on_line
    captured=[]
    def capture_fixture(*args,**kwargs):
        if not captured:
            captured.append(args)
        return current(*args,**kwargs)
    DS.score_on_line=capture_fixture
    R.c47(None)
    ids,rows,lines,draws,labels,real=captured[0]
    for field in DS.IDENTITY_FIELDS:
        altered=rows['b'].copy()
        if field=='pkey': altered[field]=altered[field]+'_other'
        elif field=='signed': altered[field]+=pd.Timedelta(days=30)
        elif field=='cut': altered[field]='q2'
        else: altered[field]+=1
        try:
            current(ids,{'a':rows['a'],'b':altered},lines,draws,labels,real)
        except AssertionError as e:
            assert 'disagree on '+field in str(e)
            print('IDENTITY_MUTATION_REJECTED',field)
        else: raise AssertionError(field+' escaped')
    altered=rows['b'].copy(); altered['pkey']+='_other'
    old.score_on_line(ids,{'a':rows['a'],'b':altered},lines,draws,labels,real)
    print('OLD_SCORER_ACCEPTS_CHANGED_PLAYER_CONFIRMED')
    DS.score_on_line=old.score_on_line
    try:
        R.c47(None)
    except AssertionError as e:
        print('OLD_SCORER_REJECTED',e)
    else:
        raise AssertionError('old scorer escaped')
    finally:
        DS.score_on_line=current
elif mode=='audit':
    d=pd.read_csv(C.out_path('model_scorecard_seasons.csv'),low_memory=False)
    print('COLUMNS',list(d.columns))
    key=['career_key','page','h']
    current=d[d.model=='current']
    print('FALLBACK',current.outside_production.value_counts().to_dict())
    keys=current.loc[current.outside_production.eq(0),key]
    subset=d.merge(keys,on=key,validate='many_to_one')
    for label,g in subset.groupby('model'):
        print('ANSWERABLE',label,len(g),'RMSE',np.sqrt((g.e_war**2).mean()),'MAE',g.e_war.abs().mean(),'BIAS',g.e_war.mean())
    import run_skater_contract_test as RSC
    RSC.season_scores({k:g for k,g in subset.groupby('model')},ref='current',pairs=(('current','adopted'),('current','previous')))
    old=pd.read_pickle(ROOT/'50_REBUILD/output/acceptance_review/50_REBUILD/output/review_scored_0.pkl').set_index('contract_id')
    new=pd.read_pickle(C.out_path('review_scorecard_0.pkl')).set_index('contract_id')
    shared=[c for c in old.columns if c in new.columns and c!='pkey' and not c.startswith('draws_')]
    delta=(old[shared]-new.loc[old.index,shared]).abs().max()
    print('PRIOR_ACCEPTANCE_SCORING_MAX_DELTA',delta.to_dict())
    import dollar_scoring as DS
    for label in ['adopted','previous']:
        q=DS.calibration_rows(new.reset_index(),label)
        print('CORRECTED_CALIBRATION',label,'PIT',q.pit.mean(),'CENTRAL50',q.pit.between(.25,.75).mean())
    from production_adapter import ProductionChain
    from contract_price_model import contract_sample
    prod=ProductionChain(); prod.fit(pd.DataFrame(),before=2021)
    sample=contract_sample().set_index('contract_id').loc[new.index]
    missing=[int(cid) for cid,r in sample.iterrows() if pd.isna(prod._anchor(r.pkey,int(r.latest_complete)+1)[0])]
    print('DOLLAR_SAMPLE_WITHOUT_PRODUCTION_ANCHOR',len(missing),missing)
    for line in range(2):
        scored=pd.read_pickle(C.out_path(f'review_scorecard_{line}.pkl'))
        scored=scored[~scored.contract_id.isin(missing)].copy()
        print('ANSWERABLE_DOLLARS_LINE',line,len(scored))
        DS.career_bootstrap=fast_boot
        DS.report_scores(scored,('current','adopted','previous'),exact=True)
elif mode=='scorecard':
    import dollar_scoring as DS
    validate_fast()
    DS.career_bootstrap=fast_boot
    DS.ci=fast_ci
    import run_model_scorecard as R
    original=R.score_on_line
    num=[]
    def capture(*args,**kwargs):
        result=original(*args,**kwargs)
        result.to_pickle(C.out_path('review_scorecard_'+str(len(num))+'.pkl'))
        num.append(1)
        return result
    R.score_on_line=capture
    R.main()
