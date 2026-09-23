"""Independent reproduction and targeted probes of goalie candidate 1b7d9a7."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_adoption_skater_review'
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

mode=sys.argv[1]
if mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif mode=='checks':
    import repair_checks as R
    R.main()
elif mode=='skater':
    import run_skater_contract_test as S
    S.main()
elif mode=='dates':
    from contract_price_model import contract_sample
    from participation_model import contract_spans, under_contract_at
    from contract_source import load_contracts
    d=contract_sample(); d=d[~d.start_yr.isin(C.CONFIRMATORY_START_YEARS)]
    spans=contract_spans(load_contracts()[0])
    changed=[]
    for r in d.itertuples():
        page=pd.Timestamp(year=int(r.latest_complete)+1,month=7,day=1)
        h=int(r.start_yr)-page.year
        old=set(under_contract_at(spans,page,[int(r.start_yr)]).pkey)
        new=set(under_contract_at(spans,pd.Timestamp(r.signed),[int(r.start_yr)]).pkey)
        if (r.pkey in old)!=(r.pkey in new): changed.append((r.contract_id,str(page.date()),str(r.signed),r.pkey))
    print('DATE_STATUS_DIFFERENCES',len(changed),'of',len(d),changed[:10])


    import run_skater_contract_test as S
    import information_set as I
    from ability_forecast import _anchors
    from player_season_table import build, birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    for cid in [4989,7041]:
        r=d[d.contract_id==cid].iloc[0]
        page=int(r.latest_complete)+1
        iset=I.build(table,I.decision_date_for_page(page),t0=page)
        for name in ['as_known','contract_only']:
            m=S.VARIANTS[name]().fit(iset.seasons,before=page)
            a=_anchors(iset.seasons[iset.seasons.GP>=C.MIN_GP],m.N_SEASONS,m.decay_)
            a=a[(a.t0==page)&(a.pkey==r.pkey)]
            h=int(r.start_yr)-page
            print('DATED_PROBE',name,int(r.contract_id),page,str(r.signed),'h',h,'July',m.part_.predict(a,h).to_list(),'signing',m.part_.predict(a,h,as_of=r.signed).to_list())
elif mode=='goalie':
    import run_goalie_control_years as G
    G.ci=fast_ci
    def bootstrap(d,a,b,n=2000,seed=20260922):
        delta=(d[b]-d[a]).groupby(d.pkey).sum()
        ix=np.random.default_rng(seed).choice(len(delta),(n,len(delta)),replace=True)
        return float((delta.to_numpy()[ix].sum(axis=1)<0).mean())
    G.career_bootstrap=bootstrap
    sys.argv=['review']
    G.main()

elif mode=='audit':
    d=pd.read_csv(C.out_path('skater_contract_test.csv'))
    keys=['career_key','page','h']
    lead=d[d.variant=='leader'].set_index(keys).sort_index()
    assert lead.index.is_unique
    for name,g in d.groupby('variant'):
        g=g.set_index(keys).sort_index()
        assert g.index.is_unique and g.index.equals(lead.index)
        assert np.isfinite(g[['p_play','e_war','brier']].to_numpy()).all()
        for col in ['rate_82','gp_share']:
            assert np.array_equal(g[col].to_numpy(),lead[col].to_numpy()),(name,col)
        print('MATCHED',name,len(g),'Brier',g.brier.mean(),'RMSE',np.sqrt((g.e_war**2).mean()))
