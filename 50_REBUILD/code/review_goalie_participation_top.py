"""Independent reproduction and targeted probes of goalie candidate c4ddcf0."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_participation_top_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
def fast_ci(values, stat, n=2000, seed=20260923):
    key = 'career_key' if 'career_key' in values else 'pkey'
    groups = list(values.groupby(key))
    counts = np.array([len(g) for _,g in groups])
    ix = np.random.default_rng(seed).choice(len(groups), (n,len(groups)), replace=True)
    total = counts[ix].sum(axis=1)
    if 'var' in stat.__code__.co_names:
        sums = np.array([g.pit.sum() for _,g in groups])
        squares = np.array([(g.pit**2).sum() for _,g in groups])
        draws = squares[ix].sum(axis=1)/total-(sums[ix].sum(axis=1)/total)**2
    else:
        sums = np.array([stat(g)*len(g) for _,g in groups])
        draws = sums[ix].sum(axis=1)/total
    assert np.isfinite(draws).all()
    lo,hi = np.percentile(draws,[2.5,97.5])
    return float(stat(values)),float(lo),float(hi)

def paired(a,b,col,n=2000):
    keys=['career_key','page','h']
    j=a[keys+[col]].merge(b[keys+[col]],on=keys,suffixes=('_a','_b'),validate='one_to_one')
    assert len(j)==len(a)==len(b)
    delta=(j[col+'_b']-j[col+'_a']).groupby(j.career_key).sum()
    ix=np.random.default_rng(20260923).choice(len(delta),(n,len(delta)),replace=True)
    return float((delta.to_numpy()[ix].sum(axis=1)<0).mean())

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['setup','checks','top','ablation','control-current','control-observable','dollars','mutant','summary'])
args = parser.parse_args()
if args.mode == 'setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif args.mode == 'checks':
    import repair_checks as R
    R.main()
elif args.mode == 'mutant':
    import repair_checks as R
    import participation_model as PM
    print('BASE41', R.c41(None))
    original=PM.ParticipationModel.__init__
    def ignore_option(self,contracts=None,exclude=(),contract_state='as_known'):
        original(self,contracts,exclude,contract_state='as_known')
    PM.ParticipationModel.__init__=ignore_option
    try:
        R.c41(None)
    except AssertionError:
        print('IGNORED_OPTION_MUTANT_REJECTED')
    else:
        raise AssertionError('ignored option mutant survived')
elif args.mode == 'summary':
    import run_goalie_participation_top as G
    d=pd.read_csv(ROOT/'50_REBUILD/output/goalie_participation_top_ablation.csv')
    groups={name:g for name,g in d.groupby('variant')}
    for name,g in groups.items():
        q=pd.qcut(g.p_play,5,labels=False,duplicates='drop')
        top=g[q==q.max()]
        stat=lambda x:(x.p_play-x.played.astype(float)).mean()
        print('TOP',name,len(top),fast_ci(top,stat))
    # Check sufficient-statistic resampling against the candidate's original
    # DataFrame implementation, without changing the number of final draws.
    a=groups[G.Observable.name]; b=groups['observable era flag only']
    for col in ['brier','se_war']:
        assert paired(a,b,col,n=30)==G.paired(a,b,col,n=30)
    stat=lambda x:(x.p_play-x.played.astype(float)).mean()
    assert np.allclose(fast_ci(a,stat,n=30),G.ci(a,stat,n=30),rtol=0,atol=1e-12)
    print('BOOTSTRAP_PARITY_PASS')
    old=pd.read_csv(ROOT/'50_REBUILD/output/goalie_control_repairs_review/50_REBUILD/output/goalie_control_years_scored.csv').set_index('contract_id')
    new=pd.read_csv(C.out_path('goalie_control_years_scored.csv')).set_index('contract_id')
    assert set(old.index)==set(new.index)
    for col in ['realised','point_production','point_rate','sim_production','sim_rate']:
        gap=(old[col]-new[col]).abs().max()
        assert gap < 1.0,(col,gap)
        print('DEFAULT_DOLLAR_PARITY',col,gap)
elif args.mode == 'top':
    import run_goalie_participation_top as G
    G.ci, G.paired = fast_ci, paired
    G.main()
elif args.mode == 'ablation':
    import run_goalie_participation_top as G
    class EraOnly(G.Observable):
        name='observable era flag only'
        part_exclude=G.GP.PART_EXCLUDE+('under_contract',)
    class ContractOnly(G.Observable):
        name='observable under-contract only'
        part_exclude=G.GP.PART_EXCLUDE+('contract_unknown',)
    path,_=G.birthdate_source()
    table=G.GST.build(birthdate_csv=path,verbose=False,allow_thin_ages=True)
    har=G.H.Harness(table)
    base=pd.read_csv(C.out_path('goalie_participation_top.csv'))
    runs={name:d for name,d in base.groupby('variant')}
    for cls in [EraOnly,ContractOnly]:
        d=har.run(cls(),pages=C.DEV_PAGES,horizons=G.HORIZONS)
        d['se_war']=d.e_war**2
        runs[cls.name]=d
    for name,d in runs.items():
        print('ABLATION',name,len(d),'Brier',d.brier.mean(),'WAR_RMSE',np.sqrt(d.se_war.mean()))
    for name in [EraOnly.name,ContractOnly.name]:
        for ref in [G.Observable.name,G.NoContracts.name]:
            print('PAIR',ref,'versus',name,'Brier',paired(runs[ref],runs[name],'brier'),'WAR',paired(runs[ref],runs[name],'se_war'))
    pd.concat([d.assign(variant=name) for name,d in runs.items()]).to_csv(ROOT/'50_REBUILD/output/goalie_participation_top_ablation.csv',index=False)
elif args.mode.startswith('control-'):
    import run_goalie_control_years as G
    G.ci=fast_ci
    def bootstrap(d,a,b,n=2000,seed=20260922):
        delta=(d[b]-d[a]).groupby(d.pkey).sum()
        ix=np.random.default_rng(seed).choice(len(delta),(n,len(delta)),replace=True)
        return float((delta.to_numpy()[ix].sum(axis=1)<0).mean())
    G.career_bootstrap=bootstrap
    sys.argv=['review'] if args.mode=='control-current' else ['review','--participation','observable']
    G.main()
elif args.mode == 'dollars':
    import run_goalie_participation_top as G
    G.dollars_across_runs()
