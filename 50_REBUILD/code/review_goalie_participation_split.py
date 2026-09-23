"""Independent reproduction and targeted probes of goalie candidate b02a851."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_participation_split_review'
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

parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['setup','checks','top','period','none','compare','dollars','dollars_with_none'])
args=parser.parse_args()
if args.mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
    # Reuse the two independently generated c4ddcf0 valuation fixtures. The
    # common model and currency implementation are unchanged in this repair.
    import shutil
    for filename in ['goalie_control_years.pkl','goalie_control_years_observable.pkl']:
        shutil.copyfile(ROOT/'50_REBUILD/output/goalie_participation_top_review/50_REBUILD/output'/filename,C.out_path(filename))
elif args.mode=='checks':
    import repair_checks as R
    R.main()
elif args.mode=='top':
    import run_goalie_participation_top as G
    G.ci,G.paired=fast_ci,paired
    # Dollars are run separately once the new period-only artifact exists.
    G.dollars_across_runs=lambda:None
    G.main()
elif args.mode in ['period','none']:
    import run_goalie_control_years as G
    G.ci=fast_ci
    def bootstrap(d,a,b,n=2000,seed=20260922):
        delta=(d[b]-d[a]).groupby(d.pkey).sum()
        ix=np.random.default_rng(seed).choice(len(delta),(n,len(delta)),replace=True)
        return float((delta.to_numpy()[ix].sum(axis=1)<0).mean())
    G.career_bootstrap=bootstrap
    sys.argv=['review','--participation','period_only' if args.mode=='period' else 'none']
    G.main()
elif args.mode=='compare':
    import run_goalie_participation as GP
    old=pd.read_csv(ROOT/'50_REBUILD/output/goalie_participation_top_ablation.csv')
    new=pd.read_csv(C.out_path('goalie_participation_top.csv'))
    mapping={'current: export membership':'current: contract state as known',
             'no contract inputs':'no contract data',
             'period + contract status':'contract state where observable',
             'period indicator only':'observable era flag only',
             'contract status only':'observable under-contract only'}
    keys=['career_key','page','h']
    for label,prior in mapping.items():
        a=new[new.variant==label].set_index(keys).sort_index()
        b=old[old.variant==prior].set_index(keys).sort_index()
        assert a.index.equals(b.index)
        for col in ['p_play','war_hat','brier','e_war']:
            if col not in a: continue
            gap=(a[col]-b[col]).abs().max()
            assert gap<1e-12,(label,col,gap)
            print('FORECAST_PARITY',label,col,len(a),gap)
    for variant, expected in GP.PART_VARIANTS.items():
        state,exclude=GP.part_settings(variant)
        assert state==expected[0] and exclude==GP.PART_EXCLUDE+expected[1]
    print('FIVE_SETTINGS_PARITY_PASS')
elif args.mode=='dollars':
    import run_goalie_participation_top as G
    G.dollars_across_runs()
elif args.mode=='dollars_with_none':
    import inspect
    import run_goalie_participation_top as G
    for suffix in ['', '_observable', '_period_only', '_none']:
        assert C.out_path('goalie_control_years'+suffix+'.pkl').exists(),suffix
    source=inspect.getsource(G.dollars_across_runs)
    revised=source.replace('("observable", "period_only")', '("observable", "period_only", "none")')
    assert revised!=source
    # Same candidate scoring implementation, with the independently generated
    # no-input run added to the files it loads. Candidate files stay untouched.
    exec(revised,G.__dict__)
    G.dollars_across_runs()
