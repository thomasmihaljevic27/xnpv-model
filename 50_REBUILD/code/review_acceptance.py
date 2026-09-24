"""Independent Phase 5 acceptance review of 01e78a9.

Run setup, checks, skater, goalie, probe, refactor, and audit in the review environment.
The isolated candidate is acceptance_review; scoring and refactors are checked against prior independently reviewed checkouts.
Generated evidence stays in ignored output. No candidate is adopted.
"""
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/acceptance_review'
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
if mode=='skater_fast':
    import dollar_scoring as DS
    validate_fast()
    DS.career_bootstrap=fast_boot
    DS.ci=fast_ci
    import run_skater_dollar_scoring as R
    original=R.score_on_line
    saved=[]
    def capture(*args,**kwargs):
        d=original(*args,**kwargs)
        d.to_pickle(C.out_path('review_scored_'+str(len(saved))+'.pkl'))
        saved.append(d)
        return d
    R.score_on_line=capture
    R.main()
elif mode=='fast_check':
    validate_fast()
elif mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif mode=='probe':
    from unittest.mock import patch
    import dollar_scoring as DS
    import repair_checks as checks
    import npv_simulation as SIM
    captured=[]
    original=DS.score_on_line
    def capture(*args,**kwargs):
        if not captured:
            captured.append(args)
        return original(*args,**kwargs)
    with patch.object(DS,'score_on_line',capture):
        print('C47_BASELINE',checks.c47(None))
    common,rows,lines,draws,labels,real=captured[0]
    # Run the previous inline scorer itself on the same real-row fixture.
    import ast
    tree=ast.parse((ROOT/'50_REBUILD/output/star_recency_review/50_REBUILD/code/run_goalie_control_years.py').read_text(encoding='utf-8'))
    fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='score_on')
    r2={'production':rows['a'],'rate':rows['b']}
    dr2={'production':draws['a'],'rate':draws['b']}
    env=dict(common=common,rows_of=r2,priced={'production':(None,lines)},draws=dr2,real=real,SIM=SIM,np=np,pd=pd,KEY='contract_id')
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<previous-inline-scorer>','exec'),env)
    old=env['score_on']('production')
    new=original(common,r2,lines,dr2,('production','rate'),real)
    pd.testing.assert_frame_equal(old,new,check_exact=True)
    print('OLD_INLINE_SCORER_EXACT_ON_REAL_ROW_FIXTURE',len(new))
    cid=common[0]
    # The scorer claims its equality assertion covers identity and dates.
    # Change only arm b's player, making that player's actual WAR different.
    changed={k:v.copy() for k,v in rows.items()}
    changed['b'].loc[cid,'pkey']='review-other-player'
    def actual(key,yrs):
        return np.full(len(yrs),2.0 if key=='review-other-player' else 0.8)
    result=original(common,changed,lines,draws,labels,actual)
    r=changed['b'].loc[cid]
    w=actual(r.pkey,range(int(r.start_yr),int(r.end_yr)+1))
    own=float(SIM.contract_value(lines[r.cut],r,[w.mean()],[w[0]],SIM.dollar_factor(r))[0])
    shared=float(result.loc[result.contract_id==cid,'realised'].iloc[0])
    assert abs(own-shared)>1
    print('IDENTITY_MISMATCH_ACCEPTED',cid,'TARGET_GAP',own-shared)
    # A decision-date mismatch also goes unchecked, while point valuation
    # uses its own date and simulated valuation uses arm a's dollar factor.
    changed={k:v.copy() for k,v in rows.items()}
    changed['b'].loc[cid,'signed']=pd.Timestamp('2020-07-01')
    result=original(common,changed,lines,draws,labels,real)
    r=changed['b'].loc[cid]
    own=float(SIM.contract_value(lines[r.cut],r,[0.8],[0.8],SIM.dollar_factor(r))[0])
    shared=float(result.loc[result.contract_id==cid,'realised'].iloc[0])
    print('SIGNING_MISMATCH_ACCEPTED',cid,'TARGET_GAP',own-shared)
    assert abs(own-shared)>1
    # Prototype the narrow repair in the reviewer helper only: prove valid
    # values stay identical and mismatches are refused before shared inputs.
    def guarded(ids,rs,ls,ds,labs,rf):
        fields=['pkey','signed','start_yr','end_yr','length','cut']
        for c in ids:
            a=rs[labs[0]].loc[c]
            for lab in labs[1:]:
                b=rs[lab].loc[c]
                for field in fields:
                    assert a[field]==b[field],f'contract {c}: {field} differs'
        return original(ids,rs,ls,ds,labs,rf)
    pd.testing.assert_frame_equal(guarded(common,rows,lines,draws,labels,real),original(common,rows,lines,draws,labels,real),check_exact=True)
    for field in ['pkey','signed','start_yr','end_yr','cut']:
        bad={k:v.copy() for k,v in rows.items()}
        val=bad['b'].loc[cid,field]
        bad['b'].loc[cid,field]=val+1 if field.endswith('_yr') else (pd.Timestamp('2020-07-01') if field=='signed' else 'review-change')
        try:
            guarded(common,bad,lines,draws,labels,real)
        except AssertionError as e:
            assert field in str(e)
        else:
            raise AssertionError('prototype missed '+field)
    print('PROTOTYPE_REPAIR_VALID_VALUES_EXACT_AND_FIVE_MUTATIONS_CAUGHT')
elif mode=='refactor':
    import ast
    base=ROOT/'50_REBUILD/output/star_recency_review/50_REBUILD/code'
    new=CANDIDATE/'50_REBUILD/code'
    def functions(p):
        return {x.name:x for x in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(x,ast.FunctionDef)}
    a,b=functions(base/'run_goalie_control_years.py'),functions(new/'dollar_scoring.py')
    for name in ['realised_path','term_extra','ci','pit_block','career_bootstrap']:
        x,y=a[name],b[name]
        x.body=x.body[1:]; y.body=y.body[1:]
        assert ast.dump(x)==ast.dump(y),name
        print('UNCHANGED_HELPER',name)
    a,b=functions(base/'run_npv_simulation.py'),functions(new/'run_npv_simulation.py')
    old=a['main'].body
    start=next(i for i,x in enumerate(old) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='d' for t in x.targets))
    end=next(i for i,x in enumerate(old[start:],start) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Subscript) and ast.unparse(t)=="pt['surplus_point']" for t in x.targets))
    fragment=ast.Module(body=old[start:end+1],type_ignores=[])
    extracted=ast.Module(body=b['point_valuation'].body[1:-1],type_ignores=[])
    class Default(ast.NodeTransformer):
        def visit_BoolOp(self,node):
            if ast.unparse(node)=='model_cls or LEADER': return ast.Name(id='LEADER',ctx=ast.Load())
            return self.generic_visit(node)
    assert ast.dump(fragment)==ast.dump(Default().visit(extracted))
    print('POINT_EXTRACTION_EXACT')
elif mode=='calibration_audit':
    import dollar_scoring as DS
    import predictive_interval as PI
    d=pd.read_pickle(C.out_path('review_scored_0.pkl'))
    for lab in ['adopted','previous']:
        changed=[]
        for r in d.itertuples():
            v=getattr(r,'draws_'+lab); y=r.realised
            u=np.random.default_rng([DS.PIT_SEED,int(r.contract_id)]).random()
            raw=PI.randomized_pit(v,y,u)
            canonical=PI.randomized_pit(np.round(v,6),round(y,6),u)
            if abs(raw-canonical)>1e-10:
                changed.append((r.contract_id,float(np.min(np.abs(v-y))),canonical-raw))
        print('DOLLAR_TIES',lab,'CONTRACTS',len(changed),'EXAMPLES',changed[:5])
    stable=d.copy()
    stable['realised']=stable.realised.round(6)
    for lab in ['adopted','previous']:
        stable['draws_'+lab]=stable['draws_'+lab].map(lambda x:np.round(x,6))
    DS.ci=fast_ci
    DS.calibration_block(stable,('adopted','previous'))
elif mode=='audit':
    d=pd.read_csv(C.out_path('skater_dollar_scoring.csv'))
    assert d.contract_id.is_unique
    print('SCORED',len(d),'PLAYERS',d.pkey.nunique())
    for lab in ['adopted','previous']:
        for how in ['point','sim']:
            e=(d[how+'_'+lab]-d.realised)/1e6
            print(lab,how,'RMSE',np.sqrt((e*e).mean()),'MAE',e.abs().mean(),'BIAS',e.mean())
    prior=pd.read_csv(ROOT/'50_REBUILD/output/status_closure_review/50_REBUILD/output/contract_valuation.csv')
    j=d.merge(prior[['contract_id','value']],on='contract_id',validate='one_to_one')
    assert len(j)==len(d)
    gap=(j.point_adopted-j.value).abs().max()
    assert gap<1e-6,gap
    print('PRIOR_INTEGRATED_POINT_VALUE_MAX_GAP',gap)
    goal=pd.read_csv(C.out_path('goalie_control_years_scored_none.csv'))
    assert goal.contract_id.is_unique and len(goal)==133
    print('GOALIE_FRESH_SCORED',len(goal))
    import ast,pickle
    import dollar_scoring as DS
    import npv_simulation as SIM
    import goalie_season_table as GST
    from player_season_table import birthdate_source
    with open(C.out_path('goalie_control_years_none.pkl'),'rb') as fh:
        payload=pickle.load(fh)
    priced=payload['priced']; rows={k:v[0].set_index('contract_id') for k,v in priced.items()}
    table=GST.build(birthdate_csv=birthdate_source()[0],verbose=False,allow_thin_ages=True)
    actual=DS.realised_path(table)
    tree=ast.parse((ROOT/'50_REBUILD/output/star_recency_review/50_REBUILD/code/run_goalie_control_years.py').read_text(encoding='utf-8'))
    fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='score_on')
    env=dict(common=payload['common'],rows_of=rows,priced=priced,draws=payload['draws'],real=actual,SIM=SIM,np=np,pd=pd,KEY='contract_id')
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<old-goalie-scorer>','exec'),env)
    for line in ['production','rate']:
        old=env['score_on'](line)
        new=DS.score_on_line(payload['common'],rows,priced[line][1],payload['draws'],('production','rate'),actual)
        pd.testing.assert_frame_equal(old,new,check_exact=True)
        print('OLD_GOALIE_SCORER_EXACT_FULL_SAMPLE',line,len(new))
    # Validate the faster resampling against the reference on the real sample.
    d['a']=(d.point_adopted-d.realised)**2
    d['b']=(d.point_previous-d.realised)**2
    assert DS.career_bootstrap(d,'a','b',n=20)==fast_boot(d,'a','b',n=20)
    np.testing.assert_allclose(DS.ci(d,lambda x:((x.a-x.b)/1e12).mean(),n=20),fast_ci(d,lambda x:((x.a-x.b)/1e12).mean(),n=20),rtol=0,atol=1e-12)
    print('REAL_SAMPLE_FAST_RESAMPLING_MATCHES_REFERENCE')

else:
    import importlib
    modules={'skater':'run_skater_dollar_scoring','goalie':'run_goalie_control_years','checks':'repair_checks'}
    importlib.import_module(modules[mode]).main()
