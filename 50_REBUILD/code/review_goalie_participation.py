"""Independent reproduction and targeted probes of goalie candidate 6e9286e."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_participation_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['setup','run','checks','price','audit','fits','dates'])
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
        d.to_csv(ROOT/f'50_REBUILD/output/goalie_participation_price_{len(samples)}.csv',index=False)
        return d
    P.prep_pooled=capture
    P.main()
elif args.mode=='audit':
    import run_goalie_participation as G
    import run_goalie_price_line as P
    import information_set as I
    from contract_source import load_contracts
    from participation_model import contract_spans,under_contract_at,players_with_any_contract
    from player_season_table import birthdate_source
    bd,_=birthdate_source()
    table=G.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    contracts,_=load_contracts()
    spans=contract_spans(contracts)
    result={}
    sample=P.contract_sample(('G',))
    sample=sample[sample.start_yr.between(2015,2021)]
    discrepancies=[]
    for r in sample.itertuples():
        t0=int(r.latest_complete)+1
        july=pd.Timestamp(t0,7,1)
        signed=pd.Timestamp(r.signed)
        if july<=signed: continue
        relevant=spans[(spans.pkey==r.pkey)&(spans.signed>signed)&(spans.signed<=july)]
        for deal in relevant.itertuples():
            if deal.end_yr>=r.start_yr and deal.start_yr<=r.start_yr+r.length-1:
                discrepancies.append(dict(contract_id=int(r.contract_id),pkey=r.pkey,signed=str(signed),page_date=str(july),future_signed=str(deal.signed),start=int(r.start_yr),length=int(r.length)))
    result['future_contract_visibility']=discrepancies
    # Direct prediction at July page under altered outcomes. The production
    # projector is independently dated in earlier reviews; focus on new outputs.
    page=2019
    def forecast(t):
        iset=I.build(t,I.decision_date_for_page(page),t0=page)
        m=G.Both().fit(iset.seasons,page)
        return m.predict(iset,G.H.subjects_at(iset),G.HORIZONS)
    original=forecast(table)
    changed=table.copy()
    mask=changed.syr>=page
    changed.loc[mask,'GP']=70
    changed.loc[mask,'gp_share']=.9
    changed.loc[mask,'WAR']=100
    perturbed=forecast(changed)
    result['runner_future_max_change']=float(np.abs(original[['p_play','gp_share']].to_numpy()-perturbed[['p_play','gp_share']].to_numpy()).max())
    scored_path=C.out_path('goalie_participation.csv')
    if scored_path.exists():
        d=pd.read_csv(scored_path)
        result['columns']=d.columns.tolist()
        stats={}
        for arm,g in d.groupby('arm'):
            played=g.played.astype(float)
            q=g.rate_82*g.gp_share
            # Exact algebra, not a causal attribution or an oracle repair.
            stats[arm]=dict(n=len(g),bias=float(g.e_war.mean()),participation_weighted=float(((g.p_play-played)*q).mean()),conditional_term=float((played*(q-g.act_war)).mean()),played_unique_seasons=int(g[g.played].drop_duplicates(['career_key','season']).shape[0]))
        result['bias_identity']=stats
    old=pd.read_csv(ROOT/'50_REBUILD/output/goalie_participation_price_1.csv')
    new=pd.read_csv(ROOT/'50_REBUILD/output/goalie_participation_price_2.csv')
    j=old[old.is_G==1].merge(new[new.is_G==1],on='contract_id',suffixes=('_old','_new'),validate='one_to_one')
    delta=j.war_per_season_new-j.war_per_season_old
    result['forecast_change']=dict(n=len(j),mean=float(delta.mean()),mean_absolute=float(delta.abs().mean()),max_absolute=float(delta.abs().max()),quantiles=delta.quantile([.1,.5,.9]).to_dict())
    # The new test claims to exercise participation dating. Replace the exact
    # consumer it should guard with constant answers and see whether it notices.
    import repair_checks as RC
    from player_season_table import build
    sk=build(birthdate_csv=bd,verbose=False)
    saved=G.ParticipationModel.predict
    G.ParticipationModel.predict=lambda self,anchors,h,as_of=None: pd.Series(.999,index=anchors.career_key)
    try:
        RC.c34(sk)
        result['c34_ignores_participation_prediction']='MISSED'
    except AssertionError as e:
        result['c34_ignores_participation_prediction']='caught: '+str(e)
    finally:
        G.ParticipationModel.predict=saved
    print(json.dumps(result,indent=2))
    (ROOT/'50_REBUILD/output/goalie_participation_independent_audit.json').write_text(json.dumps(result,indent=2))
elif args.mode=='fits':
    import statsmodels.api as sm
    import run_goalie_participation as G
    import information_set as I
    from player_season_table import birthdate_source
    bd,_=birthdate_source()
    table=G.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    original=sm.Logit.fit_regularized
    context={}
    records=[]
    def capture(self,*args,**kwargs):
        res=original(self,*args,**kwargs)
        retry=original(self,*args,**dict(kwargs,trim_mode='off'))
        p=res.predict(); p2=retry.predict()
        records.append(dict(page=context['page'],n=len(self.endog),
            params=res.params.tolist(),params_untrimmed=retry.params.tolist(),
            converged=bool(res.mle_retvals.get('converged',False)),
            max_prediction_change=float(np.max(np.abs(p-p2))),
            likelihood=float(self.loglike(res.params)),likelihood_untrimmed=float(self.loglike(retry.params))))
        return res
    sm.Logit.fit_regularized=capture
    for page in C.DEV_PAGES:
        context['page']=int(page)
        iset=I.build(table,I.decision_date_for_page(page),t0=page)
        G.PartOnly().fit(iset.seasons,page)
    sm.Logit.fit_regularized=original
    print(json.dumps(records,indent=2))
    (ROOT/'50_REBUILD/output/goalie_participation_fit_audit.json').write_text(json.dumps(records,indent=2))
elif args.mode=='dates':
    import run_goalie_participation as G
    import run_goalie_price_line as P
    from player_season_table import birthdate_source
    from contract_source import load_contracts
    from participation_model import ParticipationModel,under_contract_at,players_with_any_contract
    bd,_=birthdate_source()
    table=G.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    contracts,_=load_contracts()
    sample=pd.read_csv(ROOT/'50_REBUILD/output/goalie_participation_price_2.csv',parse_dates=['signed'])
    sample=sample[sample.is_G==1]
    records=[]
    for L,group in sample.groupby('latest_complete'):
        t0=int(L)+1
        past=table[table.syr<t0]
        pm=ParticipationModel(contracts,exclude=G.PART_EXCLUDE).fit(past,t0,G.goalie_anchors,horizons=G.HORIZONS)
        anchors=G.goalie_anchors(past[past.GP>=C.MIN_GP])
        anchors=anchors[anchors.t0==t0].drop_duplicates('pkey').set_index('pkey',drop=False)
        original=pm._rows
        for r in group.itertuples():
            if r.pkey not in anchors.index: continue
            a=anchors.loc[[r.pkey]]
            diffs=[]; old_values=[]; new_values=[]
            def dated_rows(anchors,h,as_of=None,table=None):
                d=original(anchors,h)
                known=players_with_any_contract(pm.spans,r.signed)
                uc=under_contract_at(pm.spans,r.signed,d.season.unique())
                keys=set(map(tuple,uc[['pkey','season']].to_numpy()))
                d['contract_unknown']=(~d.pkey.isin(known)).astype(float)
                d['under_contract']=[float((k,t) in keys) for k,t in zip(d.pkey,d.season)]
                return d
            for h in range(int(r.start_yr)-t0,int(r.start_yr)-t0+int(r.length)):
                hh=min(h,max(G.HORIZONS))
                old=float(pm.predict(a,hh).iloc[0])
                pm._rows=dated_rows
                new=float(pm.predict(a,hh).iloc[0])
                pm._rows=original
                diffs.append(new-old); old_values.append(old); new_values.append(new)
            if max(abs(x) for x in diffs)>1e-9:
                records.append(dict(contract_id=int(r.contract_id),pkey=r.pkey,signed=str(r.signed),page=t0,probability_changes=diffs,original_probabilities=old_values,signing_date_probabilities=new_values))
    print(json.dumps(records,indent=2))
    (ROOT/'50_REBUILD/output/goalie_participation_date_audit.json').write_text(json.dumps(records,indent=2))
