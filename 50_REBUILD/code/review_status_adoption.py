"""Independent reproduction and targeted probes of skater signing-date candidate 7fee59b."""


import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/status_adoption_review'
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
elif mode=='simulation':
    import run_npv_simulation as R
    R.main()
elif mode=='probe':
    import pickle
    import run_npv_simulation as R
    import npv_simulation as SIM
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    sample=R.contract_sample()
    sample=sample[(sample.latest_complete==2020)&(~sample.start_yr.isin(C.CONFIRMATORY_START_YEARS))]
    blocks,spreads=R.forecast_blocks(sample,table)
    pers,rets=R.page_dependence(spreads,table)
    with open(C.out_path('review_2021_blocks.pkl'),'wb') as f:
        pickle.dump((blocks,spreads,pers,rets),f)
    print('BLOCKS',len(blocks))
    for cid,(page,mu,sg,p,yrs) in blocks.items():
        e,n=SIM.exit_schedule(p,rets[page])
        q=[p[0]]
        for j in range(1,len(p)):
            q.append(q[-1]*(1-e[j])+(1-q[-1])*rets[page])
        q=np.array(q)
        if n or (len(p)>1 and np.diff(p).min()<-.3):
            print('MARGINAL',cid,'clipped',n,'p',p.tolist(),'actual',q.tolist(),'mu',mu.tolist(),'mean_WAR_gap',float(np.mean(mu*(q-p))),'max_prob_gap',float(np.max(np.abs(q-p))))
elif mode=='sensitivity':
    import run_valuation_sensitivity as R
    R.main()
elif mode=='leakage':
    import run_leakage_tests as R
    from run_npv_simulation import LEADER
    R.LEADER=LEADER
    R.main()
elif mode=='negative':
    import repair_checks as R
    import ability_forecast as A
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    import run_npv_simulation as N
    original=N.forecast_blocks
    def wrong(*args,**kwargs):
        original_signed=A._ParticipationMixin.p_play_signed
        def july(self,iset,keys,horizons,dates):
            return original_signed(self,iset,keys,horizons,[pd.Timestamp(year=iset.t0,month=7,day=1)]*len(keys))
        A._ParticipationMixin.p_play_signed=july
        try:
            return original(*args,**kwargs)
        finally:
            A._ParticipationMixin.p_play_signed=original_signed
    N.forecast_blocks=wrong
    try:
        R.c43(table)
    except AssertionError as exc:
        print('PAGE_DATED_SIMULATION_CAUGHT',str(exc))
    else:
        raise AssertionError('c43 accepted page-dated simulation')
    finally:
        N.forecast_blocks=original
elif mode=='marginals':
    import run_npv_simulation as R
    import npv_simulation as SIM
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    s=pd.read_csv(C.out_path('npv_simulation.csv'))
    bad=s[s.marginal_clipped>0]
    sample=R.contract_sample()
    sample=sample[sample.contract_id.isin(bad.contract_id)]
    blocks,_=R.forecast_blocks(sample,table)
    rows=[]
    for cid,(page,mu,sg,p,yrs) in blocks.items():
        ret=SIM.return_rate(table,before=page)
        e,n=SIM.exit_schedule(p,ret)
        q=[p[0]]
        for j in range(1,len(p)):
            q.append(q[-1]*(1-e[j])+(1-q[-1])*ret)
        gap=float(np.mean(mu*(np.array(q)-p)))
        rows.append({'contract_id':cid,'exact_gap':gap,'max_p_gap':float(np.max(np.abs(np.array(q)-p)))})
    d=pd.DataFrame(rows).merge(bad[['contract_id','wps_point','wps_sim']],on='contract_id',validate='one_to_one')
    assert len(d)==len(bad)==15
    print(d.to_string(index=False))
    print('EXACT_MEAN_ABS_GAP',d.exact_gap.abs().mean(),'MAX',d.exact_gap.abs().max(),'SIGNED',d.exact_gap.mean())
    print('MC_MEAN_ABS_GAP',(d.wps_sim-d.wps_point).abs().mean(),'MAX',(d.wps_sim-d.wps_point).abs().max())
    d.to_csv(C.out_path('review_marginal_bias.csv'),index=False)
elif mode=='integration':
    import run_valuation_integration as R
    R.main()
elif mode=='missing_history':
    import information_set as I
    import forecast_harness as H
    from run_npv_simulation import LEADER,PRIOR_LEADER
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    page=2015
    base=I.build(table,I.decision_date_for_page(page),t0=page)
    subs=H.subjects_at(base)
    changed=I.build(table[table.syr!=2014],I.decision_date_for_page(page),t0=page)
    for cls in [PRIOR_LEADER,LEADER]:
        model=cls().fit(base.seasons,before=page)
        try:
            model.predict(changed,subs,[0])
        except ValueError as exc:
            print('MISSING_HISTORY',cls.__name__,type(exc).__name__,str(exc))
        else:
            print('MISSING_HISTORY',cls.__name__,'no exception')
elif mode=='vendor_future':
    import contract_source as CS
    import run_npv_simulation as R
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    sample=R.contract_sample()
    row=sample[sample.contract_id==7041]
    a,sa=R.forecast_blocks(row,table)
    original=CS.load_contracts
    def changed(*args,**kwargs):
        data,path=original(*args,**kwargs)
        data=data.copy()
        mask=pd.to_datetime(data.signing_date)>row.signed.iloc[0]
        data.loc[mask,'contract_end']='2050-51'
        data.loc[mask,'length']=50
        return data,path
    CS.load_contracts=changed
    try:
        b,sb=R.forecast_blocks(row,table)
    finally:
        CS.load_contracts=original
    for idx in [1,2,3]:
        assert np.array_equal(a[7041][idx],b[7041][idx])
    assert np.array_equal(sa[2021].zs_,sb[2021].zs_)
    print('NEW_LEADER_FUTURE_CONTRACT_INVARIANCE',a[7041][3].tolist())
