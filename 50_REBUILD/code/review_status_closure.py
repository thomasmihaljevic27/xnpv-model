"""Independent reproduction and targeted probes of skater signing-date candidate 5864cb7."""


import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/status_closure_review'
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
elif mode=='pipeline':
    import run_npv_simulation as N
    import run_valuation_sensitivity as V
    import run_valuation_integration as I
    import run_production_reconciliation as P
    for runner in [N,V,I,P]:
        print('REVIEW_RUNNING',runner.__name__,flush=True)
        runner.main()
elif mode=='carry':
    import run_status_carry_sensitivity as R
    R.main()
elif mode=='leakage':
    import run_leakage_tests as R
    R.main()
elif mode=='negative':
    import inspect
    import textwrap
    import repair_checks as R
    import run_valuation_sensitivity as V
    import run_npv_simulation as N
    import participation_model as P
    from player_season_table import build,birthdate_source
    original=V.FORECASTS
    V.FORECASTS=[(name,N.PRIOR_LEADER if name==V.ADOPTED else cls) for name,cls in original]
    try:
        R.c44(None)
    except AssertionError as exc:
        print('STALE_LEADER_CAUGHT',str(exc))
    else:
        raise AssertionError('stale leader survived')
    finally:
        V.FORECASTS=original
    table=build(birthdate_csv=birthdate_source()[0],verbose=False)
    original=P.ParticipationModel._rows
    src=textwrap.dedent(inspect.getsource(original))
    import re
    src,count=re.subn(r' if np.isfinite\(t\)\s+else pd.NaT','',src)
    assert count==1
    scope={}
    exec(src,P.__dict__,scope)
    P.ParticipationModel._rows=scope['_rows']
    try:
        R.c45(table)
    except ValueError as exc:
        print('MISSING_HISTORY_MUTANT_CAUGHT',str(exc))
    else:
        raise AssertionError('missing-history mutant survived')
    finally:
        P.ParticipationModel._rows=original
elif mode=='audit':
    v=pd.read_csv(C.out_path('valuation_sensitivity.csv'))
    n=pd.read_csv(C.out_path('npv_simulation.csv'))
    a=v[v.forecast=='the adopted candidate']
    j=a.merge(n,on='contract_id',validate='one_to_one')
    print('POINT_PARITY',len(j),float((j.surplus-j.surplus_point).abs().max()))
    names=['below 0','0 to 0.5','0.5 to 1','1 to 2','2+']
    changes=a[a.fixed_group!=a.previous_group]
    print('GROUP_CHANGES',pd.crosstab(changes.previous_group,changes.fixed_group).to_dict())
    for col in ['fixed_group','previous_group']:
        means=v.groupby(['forecast',col],observed=True).surplus.mean().unstack().reindex(columns=names)
        print('ORDERS',col,means.apply(lambda row:tuple(row.sort_values().index),axis=1).nunique())
        print('SIGNS',col,np.sign(means).nunique().to_dict())
    d=pd.read_csv(C.out_path('status_carry_sensitivity.csv'))
    keys=['career_key','page','h']
    base=d[d.variant=='adopted'].set_index(keys).sort_index()
    carry=d[d.variant=='carried'].set_index(keys).sort_index()
    assert base.index.equals(carry.index) and base.index.is_unique
    for col in ['rate_82','gp_share']:
        assert np.array_equal(base[col],carry[col])
    changed=base[base.p_play!=carry.p_play]
    print('SEASON_CHANGED_CELLS',changed.reset_index().groupby(['page','h']).size().to_dict())
