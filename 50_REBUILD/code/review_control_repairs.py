"""Independent, isolated reproduction of fc4190d control-year repairs."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / '50_REBUILD/output/control_repair_review'
os.environ['SOURCE_DIR'] = str(ROOT / '10_SOURCE')
os.environ['OUTPUT_DIR'] = str(ROOT / '50_REBUILD/output/integration_production')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(ROOT / '10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(CANDIDATE / '50_REBUILD/code'))
sys.path.append(str(Path(sys.base_prefix) / 'Lib/site-packages'))
import numpy as np
import pandas as pd
import rebuild_config as C
import control_years as CY

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['setup', 'checks', 'run', 'audit', 'policy', 'paired', 'mutations'])
args = parser.parse_args()
if args.mode == 'setup':
    from contract_source import birthdate_table
    birthdate_table(ROOT/'10_SOURCE/ep_birthdates.csv').to_csv(C.out_path('birthdates.csv'), index=False)
elif args.mode == 'checks':
    import repair_checks
    repair_checks.main()
elif args.mode == 'paired':
    import inspect
    import run_control_years as R
    source = inspect.getsource(R.price_span)
    old = 'normals = rng.standard_normal((N_PATHS, T))\n        u_part = rng.random((N_PATHS, T))'
    new = ('rng = np.random.default_rng(20260917 + cid)\n'
           '        assert T <= 32\n'
           '        normals = rng.standard_normal((N_PATHS, 32))[:, :T]\n'
           '        u_part = rng.random((N_PATHS, 32))[:, :T]')
    assert old in source
    exec(compile(source.replace(old, new), '<paired review draws>', 'exec'), R.__dict__)
    original_span = R.price_span
    def save_paired(*a, **kw):
        frame = original_span(*a, **kw)
        label = str(a[5]).replace(' ', '_')
        frame.to_csv(ROOT/f'50_REBUILD/output/control_paired_{label}.csv', index=False)
        return frame
    R.price_span = save_paired
    R.main()
elif args.mode == 'mutations':
    import repair_checks as RC
    results = {}
    def trial(name, attr, replacement, check):
        saved = getattr(CY, attr)
        setattr(CY, attr, replacement)
        try:
            check(None)
            results[name] = 'MISSED'
        except AssertionError as exc:
            results[name] = 'caught: '+str(exc)
        finally:
            setattr(CY, attr, saved)
    span = CY.control_span
    trial('expiry_argument', 'control_span', lambda end, ufa, expiry=None: span(end, ufa), RC.c26)
    nodes = CY.conditional_nodes
    trial('hidden_history', 'conditional_nodes',
          lambda g, mat, j, shape, played=None, upto=None: nodes(g, mat, j, shape, None, upto), RC.c28)
    trial('future_bands', 'new_bands_knowable', lambda date: True, RC.c26)
    trial('myopic', 'best_outlook', lambda expected, disc, j: expected[:, 0]>0, RC.c27)
    print(json.dumps(results, indent=2))
    assert all(v.startswith('caught:') for v in results.values())
    (ROOT/'50_REBUILD/output/control_repair_mutations.json').write_text(json.dumps(results, indent=2))
elif args.mode == 'run':
    import run_control_years as R
    original = CY.value_paths
    records = []
    def capture(currency, row, years, mu, sigma, p_play, shape, mat, war, g,
                played, e, ret, offset):
        vals = original(currency, row, years, mu, sigma, p_play, shape, mat,
                        war, g, played, e, ret, offset)
        altered = g.copy()
        altered[:, :offset] += 3 * (played[:, :offset] == 0)
        before, _ = CY.conditional_nodes(g, mat, offset, shape, played)
        after, _ = CY.conditional_nodes(altered, mat, offset, shape, played)
        records.append(dict(contract_id=int(row.contract_id), years=list(years),
            hidden_max_shift=float(np.abs(before-after).max()),
            paths_with_hidden_history=int((played[:, :offset] == 0).any(axis=1).sum()),
            shape_ties=int((np.diff(shape) == 0).sum()),
            zero_history_sigma=int((sigma[:offset] == 0).sum())))
        return vals
    CY.value_paths = capture
    original_span = R.price_span
    def save_span(*a, **kw):
        frame = original_span(*a, **kw)
        label = str(a[5]).replace(' ', '_')
        frame.to_csv(ROOT/f'50_REBUILD/output/control_repair_{label}.csv', index=False)
        return frame
    R.price_span = save_span
    R.main()
    (ROOT/'50_REBUILD/output/control_repair_hidden.json').write_text(json.dumps(records, indent=2))
elif args.mode == 'policy':
    from types import SimpleNamespace
    from scipy import stats
    from production_currency import FEATURES
    coef = np.zeros(len(FEATURES)+1)
    coef[1+FEATURES.index('war_per_season')] = 1.
    currency = SimpleNamespace(coef_=coef)
    row = pd.Series({f:0. for f in FEATURES})
    mat = np.array([[1., .9], [.9, 1.]])
    rng = np.random.default_rng(17)
    g = rng.standard_normal((40000, 2)) @ np.linalg.cholesky(mat).T
    mu, sigma = np.array([.99, .9]), np.array([.01, .5])
    shape = stats.norm.ppf(np.linspace(.000001, .999999, 100001))
    war = mu + sigma*np.interp(stats.norm.cdf(g), np.linspace(0, 1, len(shape)), shape)
    played = np.ones_like(g)
    saved = CY.control_inputs
    CY.control_inputs = lambda r, yrs: dict(cap=np.ones(2), floor=np.zeros(2),
                                          qo=np.ones(2), disc=np.ones(2))
    try:
        vals = CY.value_paths(currency, row, [2020, 2021], mu, sigma,
            np.ones(2), shape, mat, war, g, played, np.zeros(2), 0., offset=0)
        next_expected = CY.expected_surplus(currency, row, g, np.ones(len(g)),
            mat, 1, mu[1], sigma[1], shape, 1., 0., 1., played=played, upto=1)
        # Pay for year one; only then use its observed production to decide
        # year two. No future observation enters either decision.
        feasible = np.maximum(war[:, 0], 0)-1 + (next_expected>0)*(np.maximum(war[:, 1], 0)-1)
        result = dict(unconditional_surpluses=vals['_uncond_surplus'].tolist(),
            implemented_value=float(vals['informed'].mean()),
            feasible_value=float(feasible.mean()),
            feasible_standard_error=float(feasible.std(ddof=1)/np.sqrt(len(feasible))),
            implemented_paths_taking_any=int((vals['_taken_informed']>0).sum()),
            n=len(g))
        print(json.dumps(result, indent=2))
        (ROOT/'50_REBUILD/output/control_repair_policy.json').write_text(json.dumps(result, indent=2))
    finally:
        CY.control_inputs = saved
else:
    base = pd.read_csv(ROOT/'50_REBUILD/output/control_repair_eligibility.csv')
    age = pd.read_csv(ROOT/'50_REBUILD/output/control_repair_age_rule.csv')
    joined = base.merge(age, on='contract_id', suffixes=('', '_age'), validate='one_to_one')
    same = joined[joined.n_ctrl == joined.n_ctrl_age]
    hidden = json.loads((ROOT/'50_REBUILD/output/control_repair_hidden.json').read_text())
    result = dict(n=len(base), means={r:float(base['ctrl_'+r].mean()) for r in CY.RULES},
        information=float((base.ctrl_informed-base.ctrl_declared).mean()),
        continuation=float((base.ctrl_informed-base.ctrl_informed_myopic).mean()),
        age_n=len(age), shared_n=len(joined),
        age_shared_delta=float((joined.ctrl_informed_age-joined.ctrl_informed).mean()),
        same_window_n=len(same), same_window_delta=float((same.ctrl_informed_age-same.ctrl_informed).mean()),
        same_window_max_abs_delta=float((same.ctrl_informed_age-same.ctrl_informed).abs().max()),
        hidden_max_shift=max(r['hidden_max_shift'] for r in hidden),
        hidden_path_count=sum(r['paths_with_hidden_history'] for r in hidden),
        shape_max_ties=max(r['shape_ties'] for r in hidden),
        zero_history_sigma=sum(r['zero_history_sigma'] for r in hidden))
    # Adapted feasible policy: pay 1 now; an observed fair signal then reveals
    # whether the final season is worth +10 or -10. Only exercise the +10 arm.
    # Neither current expected prefix is positive, so best_outlook stops now.
    result['future_option_example'] = dict(
        implemented_keep=bool(CY.best_outlook(np.array([[-1., 0.]]), np.ones(2), 0)[0]),
        feasible_expected_value=-1.+.5*10., informed_at_decision=False)
    paired_base = ROOT/'50_REBUILD/output/control_paired_eligibility.csv'
    paired_age = ROOT/'50_REBUILD/output/control_paired_age_rule.csv'
    if paired_base.exists() and paired_age.exists():
        p = pd.read_csv(paired_base).merge(pd.read_csv(paired_age), on='contract_id',
            suffixes=('', '_age'), validate='one_to_one')
        unchanged = p[p.n_ctrl == p.n_ctrl_age]
        result['paired_age'] = dict(n=len(p), unchanged_n=len(unchanged),
            mean_difference=float((p.ctrl_informed_age-p.ctrl_informed).mean()),
            unchanged_max_abs=float((unchanged.ctrl_informed_age-unchanged.ctrl_informed).abs().max()))
    print(json.dumps(result, indent=2))
    (ROOT/'50_REBUILD/output/control_repair_audit.json').write_text(json.dumps(result, indent=2))
