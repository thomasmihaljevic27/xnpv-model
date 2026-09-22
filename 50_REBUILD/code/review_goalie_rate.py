"""Independent reproduction and targeted probes of goalie candidate 0bec937."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_rate_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['setup','run','checks','price','audit','bridge','scores'])
args=parser.parse_args()
if args.mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif args.mode=='checks':
    import repair_checks
    repair_checks.main()
elif args.mode=='run':
    import run_goalie_rate as P
    P.main()
elif args.mode=='price':
    import run_goalie_price_line as P
    prep=P.prep_pooled
    samples=[]
    def capture(sk,go):
        d=prep(sk,go)
        samples.append(d)
        d.to_csv(ROOT/f'50_REBUILD/output/goalie_rate_price_{len(samples)}.csv',index=False)
        return d
    P.prep_pooled=capture
    P.main()
elif args.mode=='audit':
    import run_goalie_rate as R
    import run_goalie_price_line as P
    import information_set as I
    import repair_checks as RC
    from player_season_table import birthdate_source
    bd,_=birthdate_source()
    table=R.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    result={};mismatches=[]
    for page in C.DEV_PAGES:
        iset=I.build(table,I.decision_date_for_page(page),t0=page)
        model=R.FlatShare().fit(iset.seasons,page)
        subs=R.H.subjects_at(iset)
        pred=model.predict(iset,subs,R.HORIZONS)
        consumer=P.rate_at_page(table,page)
        for h in R.HORIZONS:
            d=pred[pred.h==h].set_index('career_key').reindex(subs.career_key)
            scored=d.rate_82.to_numpy()*d.gp_share.to_numpy()
            priced=consumer(subs.pkey.tolist(),h)
            delta=priced-scored
            if np.max(abs(delta))>1e-10:
                mismatches.append(dict(page=int(page),h=int(h),n=int((abs(delta)>1e-10).sum()),max=float(abs(delta).max()),mean=float(delta.mean())))
    result['consumer_mismatches']=mismatches
    # Exercise the full annual runner's prediction against a changed future.
    page=2019
    def predict(t):
        iset=I.build(t,I.decision_date_for_page(page),t0=page)
        model=R.FlatShare().fit(iset.seasons,page)
        return model.predict(iset,R.H.subjects_at(iset),R.HORIZONS)
    a=predict(table)
    poisoned=table.copy();mask=poisoned.syr>=page
    poisoned.loc[mask,'WAR_82']=100;poisoned.loc[mask,'WAR']=100
    poisoned.loc[mask,'GP']=70;poisoned.loc[mask,'gp_share']=.9
    b=predict(poisoned)
    result['future_max_change']=float(abs(a[['rate_82','gp_share','p_play']].to_numpy()-b[['rate_82','gp_share','p_play']].to_numpy()).max())
    assert result['future_max_change']==0
    # Reintroduce defects guarded by c36, restoring each immediately.
    original=R.trailing_rates
    def wrong_weights(t,pages):
        bad=t.copy();bad['GP']=10
        return original(bad,pages)
    R.trailing_rates=wrong_weights
    try: RC.c36(None);result['equal_games_mutant']='MISSED'
    except AssertionError: result['equal_games_mutant']='caught'
    finally:R.trailing_rates=original
    predict_method=R.RateModel.predict
    def overshoot(self,a,h):
        norm=self.norm(a.s_trail,h)
        return 2*a.r_trail.to_numpy()-norm
    R.RateModel.predict=overshoot
    try: RC.c36(None);result['overshoot_mutant']='MISSED'
    except AssertionError: result['overshoot_mutant']='caught'
    finally:R.RateModel.predict=predict_method
    def wrong_window(t,pages):
        # Leak the current season by shifting season labels back one year.
        t=t.copy();t['syr']=t.syr-1
        return original(t,pages)
    R.trailing_rates=wrong_window
    try: RC.c36(None);result['window_mutant']='MISSED'
    except AssertionError: result['window_mutant']='caught'
    finally:R.trailing_rates=original
    assert all(result[k]=='caught' for k in ['equal_games_mutant','overshoot_mutant','window_mutant'])
    print(json.dumps(result,indent=2))
    (ROOT/'50_REBUILD/output/goalie_rate_review_audit.json').write_text(json.dumps(result,indent=2))
elif args.mode=='bridge':
    import run_goalie_rate as R
    import run_goalie_price_line as P
    import information_set as I
    from player_season_table import birthdate_source
    bd,_=birthdate_source()
    table=R.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    d=pd.read_csv(ROOT/'50_REBUILD/output/goalie_rate_price_4.csv',parse_dates=['signed'])
    old=d[d.is_G==1].copy()
    original=P.rate_at_page
    def aligned(t,page):
        iset=I.build(t,I.decision_date_for_page(page),t0=page)
        m=R.FlatShare().fit(iset.seasons,page)
        subs=R.H.subjects_at(iset)
        pred=m.predict(iset,subs,R.HORIZONS)
        pred=pred.merge(subs[['career_key','pkey']],on='career_key',validate='many_to_one')
        pred['conditional']=pred.rate_82*pred.gp_share
        lookup=pred.set_index(['pkey','h']).conditional
        def f(keys,h):
            ix=pd.MultiIndex.from_arrays([list(keys),[min(h,max(R.HORIZONS))]*len(keys)])
            return lookup.reindex(ix).to_numpy()
        return f
    P.rate_at_page=aligned
    corrected=P.goalie_forecasts(old,table,participation='model',ability='rate')
    P.rate_at_page=original
    j=old.merge(corrected,on='contract_id',suffixes=('_old','_new'),validate='one_to_one')
    delta=j.war_per_season_new-j.war_per_season_old
    changed=j.loc[delta.abs()>1e-9,['contract_id','pkey','start_yr','length','war_per_season_old','war_per_season_new']]
    changed.to_csv(ROOT/'50_REBUILD/output/goalie_rate_bridge_changes.csv',index=False)
    print('MATCHED',len(j),'CHANGED',len(changed),'MAX',delta.abs().max())
    print(changed.to_string(index=False))
    # Reprice after replacing only the conditional ability/share forecast.
    for col in ['war_per_season','war_year1']:
        lookup=corrected.set_index('contract_id')[col]
        mask=d.is_G==1
        d.loc[mask,col]=d.loc[mask,'contract_id'].map(lookup).to_numpy()
    d['rfa_x_war']=d.is_RFA*d.war_per_season
    d['g_x_war']=d.is_G*d.war_per_season
    d['cut']=d.signed.dt.to_period('Q').dt.start_time
    P.compare_specs(d)
    P.last_fit_responses(d)
elif args.mode=='scores':
    d=pd.read_csv(C.out_path('goalie_rate.csv'))
    base="production's total, trailing share"
    rate='rate, flat norm, trailing share'
    a=d[(d.arm==base)&d.played];b=d[(d.arm==rate)&d.played]
    keys=['career_key','page','h']
    j=a[keys+['e_rate','act_gp']].merge(b[keys+['e_rate']],on=keys,suffixes=('_a','_b'),validate='one_to_one')
    assert len(j)==len(a)==len(b)
    j['a']=j.e_rate_a.abs()*j.act_gp;j['b']=j.e_rate_b.abs()*j.act_gp
    grouped=j.groupby('career_key')[['a','b','act_gp']].sum().to_numpy()
    idx=np.random.default_rng(22).integers(0,len(grouped),(2000,len(grouped)))
    totals=grouped[idx].sum(axis=1)
    gaps=(totals[:,1]-totals[:,0])/totals[:,2]
    result=dict(weighted_rate_win=float((gaps<0).mean()),weighted_rate_difference_ci=np.quantile(gaps,[.025,.975]).tolist(),arms={})
    for arm,g in d.groupby('arm'):
        result['arms'][arm]=dict(n=len(g),mae=float(g.e_war.abs().mean()),rmse=float(np.sqrt((g.e_war**2).mean())),bias=float(g.e_war.mean()))
    print(json.dumps(result,indent=2))
    (ROOT/'50_REBUILD/output/goalie_rate_review_scores.json').write_text(json.dumps(result,indent=2))
