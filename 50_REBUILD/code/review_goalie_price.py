"""Independent reproduction and targeted probes of goalie candidate 16d1d5f."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_price_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser=argparse.ArgumentParser()
parser.add_argument('mode', choices=['setup','run','checks','audit','mutations','qualification'])
args=parser.parse_args()
if args.mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif args.mode=='checks':
    import repair_checks
    repair_checks.main()
elif args.mode=='qualification':
    import run_goalie_bakeoff as B
    d=pd.read_csv(ROOT/'50_REBUILD/output/goalie_repair_review/50_REBUILD/output/goalie_bakeoff.csv')
    scored={name:g for name,g in d.groupby('rule')}
    B.bias_diagnostic(scored,scored[B.ProductionProjector.name])
elif args.mode=='mutations':
    import repair_checks as RC
    import run_goalie_price_line as P
    results={}
    saved=P.dollars_per_win
    P.dollars_per_win=lambda coef,feats,cap,extra=None: (coef[1+feats.index(extra)]*cap if extra else saved(coef,feats,cap))
    try:
        RC.c33(None)
        results['interaction only']='MISSED'
    except AssertionError:
        results['interaction only']='caught'
    finally:
        P.dollars_per_win=saved
    fit=P.fit_rolling
    P.fit_rolling=lambda d,feats,cut:fit(d.assign(signed=pd.Timestamp('2019-01-01')),feats,cut)
    try:
        RC.c33(None)
        results['future signings']='MISSED'
    except AssertionError:
        results['future signings']='caught'
    finally:
        P.fit_rolling=fit
    print(json.dumps(results,indent=2))
    assert all(v=='caught' for v in results.values())
    (ROOT/'50_REBUILD/output/goalie_price_mutations.json').write_text(json.dumps(results,indent=2))
elif args.mode=='run':
    import run_goalie_price_line as P
    prepare=P.prep_pooled
    def capture(sk,go):
        d=prepare(sk,go)
        d.to_csv(ROOT/'50_REBUILD/output/goalie_price_sample.csv',index=False)
        return d
    P.prep_pooled=capture
    fit=P.fit_rolling
    fits=[]
    underlying=P.tobit
    convergence=[]
    def optimizer(*a,**kw):
        result=underlying(*a,**kw)
        convergence.append(bool(result[2]))
        return result
    P.tobit=optimizer
    def capture_fit(d,feats,cut):
        before=len(convergence)
        coef,n=fit(d,feats,cut)
        fits.append(dict(cut=str(cut),features=feats,goalie_only=bool(d.is_G.eq(1).all()),
                         n=n,coef=None if coef is None else coef.tolist(),
                         converged=convergence[-1] if len(convergence)>before else None))
        return coef,n
    P.fit_rolling=capture_fit
    P.main()
    (ROOT/'50_REBUILD/output/goalie_price_fits.json').write_text(json.dumps(fits,indent=2))
else:
    import run_goalie_price_line as P
    d=pd.read_csv(ROOT/'50_REBUILD/output/goalie_price_sample.csv',parse_dates=['signed'])
    d['cut']=d.signed.dt.to_period('Q').dt.start_time
    fits=json.loads((ROOT/'50_REBUILD/output/goalie_price_fits.json').read_text())
    lookup={(pd.Timestamp(f['cut']),tuple(f['features']),f['goalie_only']):f
            for f in fits if f['coef'] is not None}
    rows=[]
    for cut,te in d.groupby('cut'):
        g=te[te.is_G==1]
        if g.empty or (cut,tuple(P.POOLED),False) not in lookup:
            continue
        level_features=P.FEATURES+['is_G']
        level,n=P.fit_rolling(d,level_features,cut)
        for name,features,coef in [
            ('plain',P.FEATURES,lookup[(cut,tuple(P.FEATURES),False)]['coef']),
            ('both',P.POOLED,lookup[(cut,tuple(P.POOLED),False)]['coef']),
            ('level_only',level_features,level)]:
            pred=np.maximum(P.predict_tobit(np.asarray(coef),g[features].to_numpy(float)),g.floor_share.to_numpy())
            rows.append(pd.DataFrame(dict(contract_id=g.contract_id,pkey=g.pkey,
                cut=cut,rule=name,error=pred-g.cap_share.to_numpy())))
    scored=pd.concat(rows,ignore_index=True)
    scored.to_csv(ROOT/'50_REBUILD/output/goalie_price_independent_scores.csv',index=False)
    summary={n:dict(n=len(g),mae=float(g.error.abs().mean()),bias=float(g.error.mean()))
             for n,g in scored.groupby('rule')}
    j=scored[scored.rule=='both'].merge(scored[scored.rule=='level_only'],on='contract_id',suffixes=('_both','_level'),validate='one_to_one')
    z=j.assign(delta=j.error_both.abs()-j.error_level.abs()).groupby('pkey_both').delta.agg(['sum','count'])
    rng=np.random.default_rng(18); idx=rng.integers(0,len(z),size=(2000,len(z)))
    diffs=z['sum'].to_numpy()[idx].sum(axis=1)/z['count'].to_numpy()[idx].sum(axis=1)
    last=max((f for f in fits if f['features']==P.POOLED and f['coef'] is not None),key=lambda f:f['cut'])
    b=dict(zip(['intercept']+P.POOLED,last['coef']))
    cut=pd.Timestamp(last['cut']); cap=C.cap_path(cut,[cut.year])[cut.year]
    rates={}
    finite_difference_error=0.
    for rfa in [0,1]:
        sk=b['war_per_season']+rfa*b['rfa_x_war']
        go=sk+b['g_x_war']
        rates[str(rfa)]=dict(partial_skater=sk*cap,partial_goalie=go*cap,
            whole_path_skater=(sk+b['war_year1'])*cap,
            whole_path_goalie=(go+b['war_year1'])*cap)
        for goalie in [0,1]:
            # A defined intervention: one additional expected win in EACH
            # contract season, holding term and rights fixed. Evaluate the
            # latent price directly; the salary floor is a separate step.
            x=dict(war_per_season=2.,war_year1=2.,length=3.,is_RFA=rfa,
                   rfa_x_war=2.*rfa,is_D=0.,one_year=0.,is_G=goalie,g_x_war=2.*goalie)
            y=dict(x,war_per_season=3.,war_year1=3.,rfa_x_war=3.*rfa,g_x_war=3.*goalie)
            values=P.predict_tobit(np.asarray(last['coef']),pd.DataFrame([x,y])[P.POOLED].to_numpy())*cap
            expected=(sk+b['war_year1']+goalie*b['g_x_war'])*cap
            finite_difference_error=max(finite_difference_error,abs(float(values[1]-values[0])-expected))
    assert finite_difference_error < 1e-6
    result=dict(sample_rows=len(d),goalies=int(d.is_G.sum()),
        duplicate_contracts=int(d.contract_id.duplicated().sum()),scores=summary,
        both_minus_level_ci=np.quantile(diffs,[.025,.975]).tolist(),
        fits_attempted=sum(f['coef'] is not None for f in fits),
        fits_failed=sum(f['converged'] is False for f in fits),
        failed_cuts=sorted(set(f['cut'] for f in fits if f['converged'] is False)),
        last_cut=str(cut),last_coefficients=b,cap=cap,marginal_rates=rates,
        finite_difference_error_dollars=finite_difference_error)
    census=P.contract_sample(('G',))
    result['eligible_goalie_development']=int(census.start_yr.between(2015,2021).sum())
    print(json.dumps(result,indent=2))
    (ROOT/'50_REBUILD/output/goalie_price_independent_audit.json').write_text(json.dumps(result,indent=2))
