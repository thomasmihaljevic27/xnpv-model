"""Independent reproduction and targeted probes of goalie candidate 088546f."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT/'50_REBUILD/output/goalie_control_review'
os.environ['SOURCE_DIR'] = str(ROOT/'10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT/'50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT/'10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE/'50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['setup','run','checks','price','audit','mutants','scores'])
args=parser.parse_args()
if args.mode=='setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'),index=False)
elif args.mode=='scores':
    audit = pd.read_csv(ROOT/'50_REBUILD/output/goalie_control_audit.csv')
    saved = pd.read_csv(C.out_path('goalie_control_years.csv'))
    for ref in ['production','rate']:
        d = audit[audit.reference == ref].copy()
        d['se'] = ((d.sim-d.target)/1e6)**2
        a = d[d.forecast=='production'].set_index('contract_id')
        b = d[d.forecast=='rate'].set_index('contract_id')
        diff = (b.se-a.se).groupby(a.pkey).agg(['sum','count'])
        rng = np.random.default_rng(20260922)
        indices = rng.choice(len(diff), (2000,len(diff)), replace=True)
        means = diff['sum'].to_numpy()[indices].sum(axis=1)/diff['count'].to_numpy()[indices].sum(axis=1)
        print('MATCHED_RATE_WIN_PROBABILITY',ref, float((means<0).mean()))
        s = saved[(saved.forecast==ref)&saved.term_realised.notna()].set_index('contract_id')
        m = d[d.forecast==ref].set_index('contract_id')
        assert set(s.index)==set(m.index)
        for level,lo,hi in [(80,'term_sim_q10','term_sim_q90'),(50,'term_sim_q25','term_sim_q75')]:
            observed = ((s.term_realised>=s[lo])&(s.term_realised<=s[hi])).astype(float)
            residual = observed-m[f'model{level}']
            g = residual.groupby(s.pkey).agg(['sum','count'])
            indices = np.random.default_rng(20260922).choice(len(g),(2000,len(g)),replace=True)
            estimates = g['sum'].to_numpy()[indices].sum(axis=1)/g['count'].to_numpy()[indices].sum(axis=1)
            print('COVERAGE',ref,level,'observed',observed.mean(),'model',m[f'model{level}'].mean(),'gap',residual.mean(),'career_bootstrap95',np.quantile(estimates,[.025,.975]))
elif args.mode=='checks':
    import repair_checks
    repair_checks.main()
elif args.mode=='mutants':
    import repair_checks as R
    import run_goalie_bakeoff as GB
    import npv_simulation as S
    print('BASE38', R.c38(None))
    print('BASE39', R.c39(None))
    orig = GB.GoalieModel._at_page
    GB.GoalieModel._at_page = lambda self, iset: None
    try:
        R.c38(None)
    except AssertionError as e:
        print('MUTANT38_REJECTED', str(e))
    else:
        raise AssertionError('old replay unexpectedly passed')
    finally:
        GB.GoalieModel._at_page = orig
    def old_curve(self, gaps, y):
        best = None
        for phi in np.linspace(.05, .95, 91):
            X = np.column_stack([np.ones(len(gaps)), phi**gaps])
            c = np.linalg.lstsq(X,y,rcond=None)[0]
            e = float(((X@c-y)**2).sum())
            if best is None or e < best[0]:
                best = (e,phi,c)
        self.sse_, self.phi_, c = best
        self.w_perm_ = float(np.clip(c[0],0,1))
        self.w_fade_ = float(np.clip(c[1],0,1-self.w_perm_))
        return self
    S.Persistence._fit_curve = old_curve
    try:
        R.c39(None)
    except AssertionError as e:
        print('MUTANT39_REJECTED', str(e))
    else:
        raise AssertionError('old clipping unexpectedly passed')
elif args.mode=='run':
    import run_goalie_control_years as P
    P.main()
elif args.mode=='price':
    import run_goalie_price_line as P
    prep=P.prep_pooled
    samples=[]
    def capture(sk,go):
        d=prep(sk,go)
        samples.append(d)
        d.to_csv(ROOT/f'50_REBUILD/output/goalie_control_price_{len(samples)}.csv',index=False)
        return d
    P.prep_pooled=capture
    P.main()
elif args.mode=='audit':
    import run_goalie_control_years as P
    captures = {}
    original = P.term_extra
    def capture(pt, lines):
        label = ['production', 'rate'][len(captures)]
        captures[label] = {'pt': pt, 'lines': lines, 'paths': {}}
        base = original(pt, lines)
        def f(cid, r, paths):
            L = int(r['length'])
            avg, first = paths[:, :L].mean(axis=1), paths[:, 0]
            v = P.SIM.contract_value(lines[r['cut']], r, avg, first, P.SIM.dollar_factor(r))
            q = np.percentile(v, [10, 25, 75, 90])
            captures[label]['paths'][cid] = (avg, first, float(((v >= q[0]) & (v <= q[3])).mean()), float(((v >= q[1]) & (v <= q[2])).mean()))
            return base(cid, r, paths)
        return f
    P.term_extra = capture
    P.main()
    saved = pd.read_csv(C.out_path('goalie_control_years.csv'))
    print('AUDIT_COLUMNS', saved.columns.tolist())
    path, _ = P.birthdate_source()
    table = P.GST.build(birthdate_csv=path, verbose=False, allow_thin_ages=True)
    real = P.realised_path(table)
    common = sorted(set.intersection(*[set(d['pt'].loc[d['pt']['end_yr'] <= C.LAST_SOURCE_SEASON, P.KEY]) & set(d['paths']) for d in captures.values()]))
    rows = []
    for ref, rd in captures.items():
        for label, d in captures.items():
            for cid in common:
                r = rd['pt'].set_index(P.KEY).loc[cid]
                forecast = d['pt'].set_index(P.KEY).loc[cid]
                cur, k = rd['lines'][r['cut']], P.SIM.dollar_factor(r)
                w = real(r['pkey'], range(int(r['start_yr']), int(r['end_yr']) + 1))
                target = P.SIM.contract_value(cur, r, [w.mean()], [w[0]], k)[0]
                avg, first, c80, c50 = d['paths'][cid]
                sim = P.SIM.contract_value(cur, r, avg, first, k).mean()
                point = P.SIM.contract_value(cur, r, [forecast['war_per_season']], [forecast['war_year1']], k)[0]
                rows.append(dict(reference=ref, forecast=label, contract_id=cid, pkey=r['pkey'], target=target, sim=sim, point=point, model80=c80, model50=c50))
    audit = pd.DataFrame(rows)
    audit.to_csv(ROOT/'50_REBUILD/output/goalie_control_audit.csv', index=False)
    for (ref,label), d in audit.groupby(['reference','forecast']):
        for how in ['point','sim']:
            err=(d[how]-d.target)/1e6
            print('AUDIT_SCORE',ref,label,how,len(d),'RMSE',np.sqrt((err**2).mean()),'bias',err.mean())
        print('MODEL_INCLUSIVE_COVERAGE',label,d.model80.mean(),d.model50.mean())
    targets = audit[audit.forecast=='production'].pivot(index='contract_id',columns='reference',values='target')
    print('TARGET_DIFFERENCE_M', (targets.production-targets.rate).abs().mean()/1e6, (targets.production-targets.rate).abs().max()/1e6)
    for ref in captures:
        d = audit[audit.reference == ref].copy()
        d['se'] = ((d.sim-d.target)/1e6)**2
        a = d[d.forecast=='production'].set_index('contract_id')
        b = d[d.forecast=='rate'].set_index('contract_id')
        diff = (b.se-a.se).groupby(a.pkey).agg(['sum','count'])
        rng = np.random.default_rng(20260922)
        indices = rng.choice(len(diff), (2000,len(diff)), replace=True)
        means = diff['sum'].to_numpy()[indices].sum(axis=1)/diff['count'].to_numpy()[indices].sum(axis=1)
        print('MATCHED_RATE_WIN_PROBABILITY',ref, float((means<0).mean()))
