"""Independent reproduction and targeted probes of goalie candidate 8d1efc6."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_participation_repair_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['setup','run','checks','price','ablation','audit','ablation_fast'])
args=parser.parse_args()
if args.mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif args.mode=='checks':
    import repair_checks
    repair_checks.main()
elif args.mode=='run':
    import run_goalie_participation as P
    P.main()
elif args.mode=='price':
    import run_goalie_price_line as P
    prep=P.prep_pooled
    samples=[]
    def capture(sk,go):
        d=prep(sk,go)
        samples.append(d)
        d.to_csv(ROOT/f'50_REBUILD/output/goalie_participation_repair_price_{len(samples)}.csv',index=False)
        return d
    P.prep_pooled=capture
    P.main()
elif args.mode=='ablation':
    import run_contract_ablation as A
    A.main()
elif args.mode=='audit':
    import run_goalie_participation as G
    import run_goalie_price_line as P
    import participation_model as PM
    import contract_source as CS
    import repair_checks as RC
    from player_season_table import birthdate_source
    bd,_=birthdate_source()
    table=G.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    results={}
    # Same goalie, same page, different dates, including a reversed batch.
    pfun=P.participation_at_page(table,2018)
    keys=['jon gillies|G']*2
    dates=pd.to_datetime(['2018-07-01','2018-07-16'])
    base=pfun(keys,0,dates)
    reverse=pfun(keys[::-1],0,dates[::-1])
    assert np.array_equal(base,reverse[::-1])
    assert base[1]>base[0]+.2
    results['same_player_two_dates']=base.tolist()
    # Adding a contract that is not yet signed must not change the real
    # price consumer's fitted or predicted participation.
    loader=CS.load_contracts
    contracts,meta=loader()
    future=contracts.iloc[[0]].copy()
    future['first_name']='Jon';future['last_name']='Gillies'
    future['position']='Goaltender';future['signing_date']='2099-07-16'
    future['contract_end']='2100-2101';future['length']=2
    CS.load_contracts=lambda:(pd.concat([contracts,future],ignore_index=True),meta)
    try:
        poisoned=P.participation_at_page(table,2018)(keys,0,dates)
        assert np.array_equal(base,poisoned)
        results['future_contract_max_change']=float(abs(base-poisoned).max())
    finally: CS.load_contracts=loader
    # Reintroduce each repaired defect. These mutations are in-memory only.
    pred=PM.ParticipationModel.predict
    PM.ParticipationModel.predict=lambda self,a,h,as_of=None:pd.Series(.999,index=a.career_key)
    try:
        RC.c34(None);results['constant_mutant']='MISSED'
    except AssertionError: results['constant_mutant']='caught'
    finally: PM.ParticipationModel.predict=pred
    PM.ParticipationModel.predict=lambda self,a,h,as_of=None:pred(self,a,h,as_of=None)
    try:
        RC.c34(None);results['date_mutant']='MISSED'
    except AssertionError: results['date_mutant']='caught'
    finally: PM.ParticipationModel.predict=pred
    rank=PM._full_rank
    PM._full_rank=lambda d,use:(list(use),[])
    try:
        RC.c35(None);results['rank_mutant']='MISSED'
    except AssertionError: results['rank_mutant']='caught'
    finally: PM._full_rank=rank
    assert all(results[k]=='caught' for k in ['constant_mutant','date_mutant','rank_mutant'])
    import statsmodels.api as sm
    fit=sm.Logit.fit_regularized
    designs=[]
    def checked(self,*a,**kw):
        ncols=self.exog.shape[1]
        rank=int(np.linalg.matrix_rank(self.exog,tol=1e-8))
        assert rank==ncols,(rank,ncols)
        result=fit(self,*a,**kw)
        designs.append(dict(n=len(self.endog),columns=ncols,rank=rank,converged=bool(result.mle_retvals.get('converged',False))))
        return result
    sm.Logit.fit_regularized=checked
    hits={}
    try:
        for page in C.DEV_PAGES:
            m=PM.ParticipationModel(contracts,exclude=G.PART_EXCLUDE).fit(table[table.syr<page],page,G.goalie_anchors,horizons=G.HORIZONS)
            hits[str(page)]={h:x for h,x in m.rank_dropped_.items() if x}
    finally: sm.Logit.fit_regularized=fit
    results['goalie_designs']=designs
    results['rank_drops']=hits
    from player_season_table import build
    import ability_forecast as AF
    sk=build(birthdate_csv=bd,verbose=False)
    skhits={}; nc_hits=0
    for page in C.DEV_PAGES:
        past=sk[sk.syr<page]
        anchor=lambda d:AF._anchors(d,3,AF.W_T2/AF.W_T1)
        wc=PM.ParticipationModel(contracts).fit(past,page,anchor,horizons=G.HORIZONS)
        skhits[str(page)]={h:v for h,v in wc.rank_dropped_.items() if v}
        nc=PM.ParticipationModel().fit(past,page,anchor,horizons=G.HORIZONS)
        nc_hits+=sum(bool(v) for v in nc.rank_dropped_.values())
    assert nc_hits==0
    results['skater_contract_rank_drops']=skhits
    results['skater_no_contract_rank_drops']=nc_hits
    print(json.dumps(results,indent=2))
    (ROOT/'50_REBUILD/output/goalie_participation_repair_audit.json').write_text(json.dumps(results,indent=2))
elif args.mode=='ablation_fast':
    import run_contract_ablation as A
    # Equivalent career bootstrap using sufficient sums. This avoids building
    # millions of temporary data frames and independently reconstructs metrics.
    def effect(with_c,without_c,n=1000,seed=20260922):
        keys=['career_key','page','h']
        assert len(with_c)==len(without_c)
        j=with_c[keys+['e_war']].merge(without_c[keys+['e_war']],on=keys,suffixes=('_w','_o'),validate='one_to_one')
        assert len(j)==len(with_c)
        rng=np.random.default_rng(seed);out=[]
        for h,g in j.groupby('h'):
            x=g.assign(w=g.e_war_w.abs(),o=g.e_war_o.abs()).groupby('career_key')[['w','o']].sum()
            indices=rng.integers(0,len(x),size=(n,len(x)))
            totals=x.to_numpy()[indices].sum(axis=1)
            boot=100*(totals[:,0]-totals[:,1])/totals[:,1]
            pct=100*(g.e_war_w.abs().mean()-g.e_war_o.abs().mean())/g.e_war_o.abs().mean()
            lo,hi=np.percentile(boot,[2.5,97.5])
            out.append(dict(h=int(h),pct=pct,lo=lo,hi=hi,brier_w=None,n=len(g)))
        return pd.DataFrame(out)
    A.effect=effect
    run=A.H.Harness.run
    count=[0]
    def capture(self,*a,**kw):
        d=run(self,*a,**kw);count[0]+=1
        d.to_csv(ROOT/f'50_REBUILD/output/goalie_participation_repair_skater_arm_{count[0]}.csv',index=False)
        return d
    A.H.Harness.run=capture
    A.main()
