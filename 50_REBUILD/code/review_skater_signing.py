"""Independent reproduction and targeted probes of skater signing-date candidate d2be5b0."""


import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/skater_signing_review'
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
elif mode=='skater':
    import run_skater_contract_test as S
    S.main()
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

elif mode=='negative':
    import inspect
    import repair_checks as R
    import contract_price_model as P
    import ability_forecast as A
    from player_season_table import build, birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    original=P.attach_forecasts
    def page(*args,**kwargs):
        kwargs['participation_date']='page'
        return original(*args,**kwargs)
    P.attach_forecasts=page
    try:
        R.c42(table)
    except AssertionError as exc:
        print('FORCED_PAGE_CAUGHT',repr(str(exc)))
    else:
        raise AssertionError('forced page date survived')
    finally:
        P.attach_forecasts=original
    original=A._ParticipationMixin.p_play_signed
    import textwrap
    source=textwrap.dedent(inspect.getsource(original))
    assert 'p * g_play ** (h - fitted[-1])' in source
    source=source.replace('p * g_play ** (h - fitted[-1])','p')
    scope={}
    exec(source,A.__dict__,scope)
    A._ParticipationMixin.p_play_signed=scope['p_play_signed']
    try:
        R.c42(table)
    except AssertionError as exc:
        print('REMOVED_DECAY_CAUGHT',str(exc))
    else:
        raise AssertionError('removed decay survived')
    finally:
        A._ParticipationMixin.p_play_signed=original
elif mode=='future':
    import contract_source as CS
    import contract_price_model as P
    import run_skater_contract_test as S
    from player_season_table import build, birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    sample=P.contract_sample()
    row=sample[sample.contract_id==7041]
    cls=S.VARIANTS['contract_only']
    a=P.attach_forecasts(row,cls,table,verbose=False)
    original=CS.load_contracts
    def changed(*args,**kwargs):
        contracts,path=original(*args,**kwargs)
        contracts=contracts.copy()
        future=pd.to_datetime(contracts.signing_date)>row.signed.iloc[0]
        assert future.sum()>0
        contracts.loc[future,'contract_end']='2050-51'
        contracts.loc[future,'length']=50
        print('CORRUPTED_FUTURE_CONTRACTS',int(future.sum()))
        return contracts,path
    CS.load_contracts=changed
    try:
        b=P.attach_forecasts(row,cls,table,verbose=False)
    finally:
        CS.load_contracts=original
    cols=['war_total','war_year1','p_first']
    assert np.array_equal(a[cols].to_numpy(),b[cols].to_numpy())
    print('FUTURE_CONTRACT_INVARIANCE',a[cols].to_dict('records'))
elif mode=='dollars_exact':
    import run_skater_contract_test as S
    from player_season_table import build,birthdate_source
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    original=S.Boot.lower_share
    def measured(self,a,b):
        v=original(self,a,b)
        print('EXACT_BOOTSTRAP_WIN_SHARE',v)
        return v
    S.Boot.lower_share=measured
    S.dollars(table)
