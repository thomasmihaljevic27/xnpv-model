"""Reproduce 61c62bc and probe control-year information and decision rules."""
import argparse
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
candidate = root/'50_REBUILD/output/control_review'
os.environ['SOURCE_DIR'] = str(root/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(root/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0,str(candidate/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
import control_years as CY
from contract_source import birthdate_table
birthdate_table(root/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
ap=argparse.ArgumentParser()
ap.add_argument('mode',choices=['run','checks','audit'])
args=ap.parse_args()
if args.mode=='checks':
    import repair_checks
    repair_checks.main()
elif args.mode=='run':
    import run_control_years as R
    original=CY.value_paths
    records=[]
    def capture(currency,row,years,mu,sigma,p_play,shape,mat,war,g,played,e,ret,offset):
        vals=original(currency,row,years,mu,sigma,p_play,shape,mat,war,g,played,e,ret,offset)
        inp=CY.control_inputs(row,years)
        t=offset
        altered=g.copy()
        altered[:,:t] += 3*(played[:,:t]==0)
        kwargs=dict(currency=currency,row=row,alive_prev=played[:,t-1],sigma_mat=mat,j=t,
            mu_j=mu[t],sigma_j=sigma[t],shape=shape,e_j=float(e[t]),r_return=ret,
            cap_j=inp['cap'][0],floor_j=inp['floor'][0],qo_j=inp['qo'][0])
        before=CY.expected_surplus(g=g,**kwargs)
        after=CY.expected_surplus(g=altered,**kwargs)
        records.append(dict(contract_id=int(row.contract_id),signed=str(row.signed),years=list(years),
            paths_with_missing_history=int((played[:,:t]==0).any(axis=1).sum()),
            hidden_history_max_dollar_shift=float(np.abs(after-before).max()),
            hidden_history_decision_flips=int(((before>0)!=(after>0)).sum())))
        return vals
    CY.value_paths=capture
    try:
        R.main()
    finally:
        CY.value_paths=original
    (root/'50_REBUILD/output/control_hidden_information.json').write_text(json.dumps(records,indent=2))
else:
    from contract_price_model import contract_sample
    sample=contract_sample()
    dev=pd.read_csv(root/'50_REBUILD/output/integration_repair_review/50_REBUILD/output/contract_valuation.csv')
    s=sample[sample.contract_id.isin(dev.contract_id)]
    no=s[s.expiry_status=='UFA no QO'].copy()
    no['hypothetical_span']=[CY.control_span('RFA',r.end_yr,r.ufa_year) for r in no.itertuples()]
    # Deterministic payoffs: there is no informational advantage to explain a policy gap.
    pay=np.array([[5.,-1.,10.]])
    actual=float((CY.take_matrix('informed',pay,pay[0],pay)*pay).sum())
    result=dict(development_expiry_counts=s.expiry_status.value_counts().to_dict(),
        nonqualified_with_future_ufa=int(no.hypothetical_span.map(bool).sum()),
        nonqualified_examples=no[no.hypothetical_span.map(bool)][['contract_id','signed','start_yr','end_yr','ufa_year']].head(8).astype(str).to_dict('records'),
        deterministic_stopping=dict(myopic=actual,feasible_take_all=float(pay.sum()),oracle=float(CY.best_stop(pay)[0])))
    # A historical decision should not acquire a future agreement's QO bands.
    result['historical_qo']=dict(decision='2019-07-01',salary=1200000,control_year=2026,
        output=float(CY.qo_schedule(1200000,1200000,[2026],2019,decision_date='2019-07-01')[0]),
        old_bands_with_same_floor=float(CY.qualifying_offer(1200000,1200000,2025,False,floor=C.league_min_path(2026,'2019-07-01'))))
    sp=pd.read_csv(root/'30_OUTPUT/contract_season_spine.csv')
    import run_control_years as R
    cmap=R.control_map(sample)
    end=sp[sp.contract_id.isin(cmap)].sort_values('season_start').groupby('contract_id').tail(1)
    end=end.merge(sample[['contract_id','aav']],on='contract_id').dropna(subset=['cs_nhl_salary'])
    ratio=end.cs_nhl_salary/end.aav
    result['salary_direction']=dict(n=len(end),higher=int((ratio>1.01).sum()),lower=int((ratio<.99).sum()),equal=int(ratio.between(.99,1.01).sum()))
    from types import SimpleNamespace
    from scipy import stats
    # With zero dependence and certain participation, observing history adds no information.
    currency=SimpleNamespace(coef_=np.array([0.,1.,0.,0.,0.,0.,0.,0.]))
    row=pd.Series({'is_D':0})
    expected=CY.expected_surplus(currency,row,np.zeros((1,2)),np.ones(1),np.eye(2),1,
        0.,1.,stats.norm.ppf(np.linspace(.0001,.9999,10001)),0.,0.,1.,0.,.1)
    point=float(CY.season_share(currency,row,np.array([0.]),0.)[0]-.1)
    result['no_new_information_counterexample']=dict(declared_expected_surplus=point,
        informed_expected_surplus=float(expected[0]),dependence=0,participation_probability=1)
    r=sample[sample.contract_id==6876].iloc[0]
    years=CY.control_span(r.expiry_status,r.end_yr,r.ufa_year)
    original=CY.qualifying_offer
    current=CY.control_inputs(r,years)['qo']
    try:
        CY.qualifying_offer=lambda sal,hit,year,s20,floor=None: original(sal,hit,min(year,2025),s20,floor)
        old=CY.control_inputs(r,years)['qo']
    finally:
        CY.qualifying_offer=original
    result['actual_future_rule_case']=dict(contract_id=6876,signed=str(r.signed),years=years,
        implemented=current.tolist(),old_bands_same_floor=old.tolist())
    print(json.dumps(result,indent=2))
    (root/'50_REBUILD/output/control_independent_audit.json').write_text(json.dumps(result,indent=2))
