"""Independent reproduction and targeted probes of goalie candidate f90e6fe."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_rate_repair_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['setup','run','checks','price','audit','regression','parity'])
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
        d.to_csv(ROOT/f'50_REBUILD/output/goalie_rate_repair_price_{len(samples)}.csv',index=False)
        return d
    P.prep_pooled=capture
    P.main()
elif args.mode=='regression':
    import run_goalie_bakeoff as B
    import run_goalie_participation as P
    import run_goalie_rate as R
    from player_season_table import birthdate_source
    bd,_=birthdate_source()
    table=R.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    specs=[('bakeoff',B.CANDIDATES,'rule','goalie_repair_review','goalie_bakeoff.csv'),
           ('participation',P.ARMS,'arm','goalie_participation_repair_review','goalie_participation.csv'),
           ('rate',R.ARMS,'arm','goalie_rate_review','goalie_rate.csv')]
    result={}
    for label,classes,column,prior,filename in specs:
        frames=[]
        for cls in classes:
            model=cls();d=R.H.Harness(table).run(model,pages=C.DEV_PAGES,horizons=R.HORIZONS)
            if label=='rate':d['se_war']=d.e_war**2
            frames.append(d.assign(**{column:model.name}))
        new=pd.concat(frames,ignore_index=True)
        old=pd.read_csv(ROOT/f'50_REBUILD/output/{prior}/50_REBUILD/output/{filename}')
        new=new[old.columns]
        pd.testing.assert_frame_equal(new,old,check_dtype=False,check_categorical=False,check_exact=False,rtol=1e-12,atol=1e-12)
        result[label]=dict(rows=len(new),all_columns_match=True)
        print(label,result[label],flush=True)
    (ROOT/'50_REBUILD/output/goalie_rate_repair_regression.json').write_text(json.dumps(result,indent=2))
elif args.mode=='audit':
    import run_goalie_price_line as P
    import run_goalie_rate as R
    import repair_checks as RC
    results={}
    saved=P.rate_at_page
    def old_fallback(table,page):
        original=saved(table,page)
        cs=original.conditional
        def f(keys,h):
            hh=min(h,max(R.HORIZONS));ck=original.keymap.reindex(list(keys)).to_numpy()
            if cs.sm.coef_.get(hh) is None:
                sh=cs.tr_.reindex(ck).s_trail.to_numpy()
                return cs.rate(ck,h)*np.clip(sh,.02,1.)
            return original(keys,h)
        f.conditional=cs;f.keymap=original.keymap
        return f
    P.rate_at_page=old_fallback
    try:RC.c37(None);results['old_fallback']='MISSED'
    except AssertionError as e:results['old_fallback']=str(e)
    finally:P.rate_at_page=saved
    def wrong_clamp(table,page):
        original=saved(table,page)
        def f(keys,h):return original(keys,4 if h>5 else h)
        f.conditional=original.conditional;f.keymap=original.keymap
        return f
    P.rate_at_page=wrong_clamp
    try:RC.c37(None);results['consumer_clamp']='MISSED'
    except AssertionError as e:results['consumer_clamp']=str(e)
    finally:P.rate_at_page=saved
    assert all(v!='MISSED' for v in results.values())
    print(json.dumps(results,indent=2))
    (ROOT/'50_REBUILD/output/goalie_rate_repair_mutations.json').write_text(json.dumps(results,indent=2))
elif args.mode=='parity':
    import run_goalie_rate as R
    import run_goalie_price_line as P
    import information_set as I
    from player_season_table import birthdate_source
    bd,_=birthdate_source()
    table=R.GST.build(birthdate_csv=bd,verbose=False,allow_thin_ages=True)
    cells=0;worst=0.
    for page in C.DEV_PAGES:
        iset=I.build(table,I.decision_date_for_page(page),t0=page)
        subs=R.H.subjects_at(iset)
        model=R.FlatShare().fit(iset.seasons,page)
        pred=model.predict(iset,subs,R.HORIZONS)
        consumer=P.rate_at_page(table,page)
        for h in range(8):
            scored=pred[pred.h==min(h,5)].set_index('career_key').reindex(subs.career_key)
            want=scored.rate_82.to_numpy()*scored.gp_share.to_numpy()
            got=consumer(subs.pkey.tolist(),h)
            assert np.isfinite(got).all()
            gap=float(abs(want-got).max())
            assert gap<1e-10
            cells+=len(got);worst=max(worst,gap)
    result=dict(cells=cells,maximum_gap=worst)
    print(json.dumps(result,indent=2))
    (ROOT/'50_REBUILD/output/goalie_rate_repair_parity.json').write_text(json.dumps(result,indent=2))
