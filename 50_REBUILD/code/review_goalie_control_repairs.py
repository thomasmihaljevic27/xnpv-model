"""Independent reproduction and targeted probes of goalie candidate 6c9ab2c."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_control_repairs_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['setup', 'run', 'fast_run', 'checks', 'mutants', 'compare', 'target_guard'])
args = parser.parse_args()
if args.mode == 'setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'), index=False)
elif args.mode == 'checks':
    import repair_checks as R
    R.main()
elif args.mode == 'target_guard':
    import ast
    import textwrap
    import run_goalie_control_years as G
    source = Path(G.__file__).read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name=='score_on')
    body = textwrap.dedent('\n'.join(source.splitlines()[node.lineno-1:node.end_lineno]))
    cut = pd.Timestamp('2018-07-01')
    row = dict(contract_id=1, pkey='synthetic', cut=cut, signed=cut, start_yr=2018, end_yr=2018,
               length=1, is_RFA=0., rfa_x_war=0., is_D=0., one_year=1., war_per_season=1., war_year1=1., floor_share=.005)
    rows = {lab: pd.DataFrame([row]).set_index('contract_id') for lab in ['production','rate']}
    rows['rate'].loc[1,['war_per_season','war_year1']] = 2.
    lines = {}
    for lab, intercept in [('production',.01),('rate',.02)]:
        cur = G.ProductionCurrency('in')
        cur.coef_ = np.array([intercept,.02,0.,.01,0.,0.,0.,0.])
        lines[lab] = (None,{cut:cur})
    context = dict(G.__dict__, common=[1], rows_of=rows, priced=lines,
                   real=lambda pkey, yrs: np.ones(len(yrs)),
                   draws={lab:{1:(np.array([1.,2.]),np.array([1.,2.]))} for lab in rows})
    exec(body, context)
    baseline = context['score_on']('production')
    assert baseline.point_production.iloc[0] != baseline.point_rate.iloc[0]
    print('COMMON_TARGET_BASE_PASS', baseline.realised.iloc[0])
    changed = body.replace('SIM.contract_value(cur, row, np.array([w.mean()])', 'SIM.contract_value(priced[lab][1][rp["cut"]], row, np.array([w.mean()])')
    assert changed != body
    for name, code in [('own_line_target', changed), ('contract_feature_mismatch', body)]:
        if name=='contract_feature_mismatch':
            rows['rate'].loc[1,'is_RFA']=1.
        exec(code, context)
        try:
            context['score_on']('production')
        except AssertionError as e:
            print('TARGET_MUTANT_REJECTED',name,str(e))
        else:
            raise AssertionError(f'{name} survived')
elif args.mode == 'compare':
    scored = pd.read_csv(C.out_path('goalie_control_years_scored.csv')).set_index('contract_id')
    previous = pd.read_csv(ROOT/'50_REBUILD/output/goalie_control_audit.csv')
    for lab in ['production', 'rate']:
        old = previous[(previous.reference=='production') & (previous.forecast==lab)].set_index('contract_id')
        assert set(old.index) == set(scored.index)
        for new, prior in [('realised','target'), (f'point_{lab}','point'), (f'sim_{lab}','sim')]:
            gap = (scored[new]-old[prior]).abs().max()
            assert gap < 1.0, (new, gap)
            print('PREVIOUS_INDEPENDENT_AUDIT_PARITY',lab,new,len(old),gap)
    for i in range(1,7):
        d = pd.read_pickle(ROOT/f'50_REBUILD/output/goalie_control_repairs_pit_{i}.pkl')
        print('PIT_CAPTURE',i,len(d),'mean',d.pit.mean(),'variance',d.pit.var(ddof=0),'central80',d.pit.between(.1,.9).mean())
        if 'pq' in d and 'played' in d and not d.played.all():
            top=d[d.pq==d.pq.max()]
            print('TOP_FIFTH',len(top),'predicted',top.p_play.mean(),'observed',top.played.mean())
elif args.mode in ['run', 'fast_run']:
    import run_goalie_control_years as G
    if args.mode == 'fast_run':
        # Same career resamples and statistics, aggregated from sufficient
        # statistics instead of building thousands of repeated DataFrames.
        # Verify against the original implementation on captured real tables.
        original_ci, original_bootstrap = G.ci, G.career_bootstrap
        def fast_ci(values, stat, n=2000, seed=20260923):
            groups = list(values.groupby('pkey'))
            counts = np.array([len(g) for _,g in groups])
            indices = np.random.default_rng(seed).choice(len(groups), (n,len(groups)), replace=True)
            total = counts[indices].sum(axis=1)
            if 'var' in stat.__code__.co_names:
                sums = np.array([g.pit.sum() for _,g in groups])
                squares = np.array([(g.pit**2).sum() for _,g in groups])
                draws = squares[indices].sum(axis=1)/total-(sums[indices].sum(axis=1)/total)**2
            else:
                sums = np.array([stat(g)*len(g) for _,g in groups])
                draws = sums[indices].sum(axis=1)/total
            assert np.isfinite(draws).all()
            lo,hi = np.percentile(draws,[2.5,97.5])
            return float(stat(values)),float(lo),float(hi)
        def fast_bootstrap(d,a,b,n=2000,seed=20260922):
            assert np.isfinite(d[[a,b]].to_numpy()).all()
            groups=d.groupby('pkey')[[a,b]].sum()
            indices=np.random.default_rng(seed).choice(len(groups),(n,len(groups)),replace=True)
            return float((groups[b].to_numpy()[indices].sum(axis=1)<groups[a].to_numpy()[indices].sum(axis=1)).mean())
        tests = [lambda x:x.pit.mean(), lambda x:x.pit.var(ddof=0), lambda x:x.pit.between(.1,.9).mean()]
        for i in [1,2,3,4]:
            d=pd.read_pickle(ROOT/f'50_REBUILD/output/goalie_control_repairs_pit_{i}.pkl')
            for stat in tests:
                a,b=original_ci(d,stat,n=30),fast_ci(d,stat,n=30)
                assert np.allclose(a,b,rtol=0,atol=1e-12),(i,a,b)
            if 'own80' in d:
                stat=lambda x:(x.obs80-x.own80).mean()
                assert np.allclose(original_ci(d,stat,n=30),fast_ci(d,stat,n=30),rtol=0,atol=1e-12)
                assert original_bootstrap(d,'own80','obs80',n=30)==fast_bootstrap(d,'own80','obs80',n=30)
        print('BOOTSTRAP_AGGREGATION_PARITY_PASS',flush=True)
        G.ci,G.career_bootstrap=fast_ci,fast_bootstrap
    original = G.pit_block
    count = [0]
    def capture(d, label):
        count[0] += 1
        d.to_pickle(ROOT/f'50_REBUILD/output/goalie_control_repairs_pit_{count[0]}.pkl')
        print('CAPTURE', count[0], label, flush=True)
        return original(d, label)
    G.pit_block = capture
    G.main()
elif args.mode == 'mutants':
    import repair_checks as R
    import predictive_interval as PI
    print('BASE', R.c40(None))
    for name in ['randomized_pit', 'mixture_pit']:
        original = getattr(PI, name)
        if name == 'randomized_pit':
            mutant = lambda draws, outcome, u: original(draws, outcome, 1.0)
        else:
            mutant = lambda x, p, mu, sigma, zs, u: original(x,p,mu,sigma,zs,np.ones_like(u))
        setattr(PI, name, mutant)
        try:
            R.c40(None)
        except AssertionError as e:
            print('MUTANT_REJECTED', name, str(e))
        else:
            raise AssertionError(f'{name} mutant survived')
        finally:
            setattr(PI, name, original)
