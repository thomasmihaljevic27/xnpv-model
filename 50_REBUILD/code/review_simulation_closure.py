"""Verify db0c6b2's shared draws and that c25 detects broken consumers."""
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
candidate = root / '50_REBUILD/output/simulation_closure_review'
os.environ['SOURCE_DIR'] = str(root / '10_SOURCE')
os.environ['OUTPUT_DIR'] = str(root / '30_OUTPUT')
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root / '10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
sys.path.insert(0, str(candidate / '50_REBUILD/code'))
import numpy as np
import pandas as pd
import rebuild_config as C
import npv_simulation as S
import run_npv_simulation as R
import repair_checks as checks
from player_season_table import build, birthdate_source

result = {}
table = build(birthdate_csv=birthdate_source()[0], verbose=False)
original = R.page_dependence
def broken(*args, **kwargs):
    raise AssertionError('Deliberately disabled page_dependence')
try:
    R.page_dependence = broken
    try:
        checks.c25(table)
    except AssertionError as exc:
        assert 'Deliberately disabled' in str(exc)
        result['disabled_consumer'] = str(exc)
    else:
        raise RuntimeError('c25 ignored the disabled consumer')
finally:
    R.page_dependence = original

original = R.calibration_for
def latest_page(page, spreads, pers, rets):
    page = max(spreads)
    return spreads[page], pers[page], rets[page]
try:
    R.calibration_for = latest_page
    try:
        checks.c25(table)
    except AssertionError as exc:
        assert 'give the same paths' in str(exc)
        result['latest_page_mutation'] = str(exc)
    else:
        raise RuntimeError('c25 missed restored latest-page selection')
finally:
    R.calibration_for = original

# Shared uniforms must control participation even when unrelated RNGs are supplied.
rng = np.random.default_rng(99)
normals = rng.standard_normal((2000, 1))
uniforms = rng.random((2000, 1))
p = S.Persistence()
p.w_perm_, p.w_fade_, p.phi_ = .2, .3, .6
independent = S.Persistence()
paths = [S.draw_paths([1.], [.5], [.7], np.linspace(-2, 2, 1001), per,
                      2000, np.random.default_rng(seed), r_return=ret,
                      normals=normals, u_part=uniforms)
         for per, seed, ret in [(p, 1, .1), (independent, 2, .1), (p, 3, 0.)]]
assert np.array_equal(paths[0], paths[1]) and np.array_equal(paths[0], paths[2])
result['one_year_synthetic_all_three_arms'] = 'exact equality'

d = pd.read_csv(C.out_path('npv_simulation.csv'))
one = d[d.term == 1]
assert len(one) == 605
assert np.array_equal(one.sim_sd, one.sd_indep_errors)
assert np.array_equal(one.sim_sd, one.sd_absorbing)
assert np.array_equal(one.surplus_sim, one.surplus_absorbing)
eight = d[d.term == 8]
result['runner'] = dict(contracts=len(d), one_year_contracts=len(one),
    one_year_largest_sd_gap=float(np.abs(one.sim_sd-one.sd_indep_errors).max()),
    eight_year_sd=float(eight.sim_sd.mean()), eight_year_absorbing_sd=float(eight.sd_absorbing.mean()),
    contract_sign_changes=int((np.sign(d.surplus_point) != np.sign(d.surplus_sim)).sum()),
    mean_gap=float(d.gap.mean()))
out = root / '50_REBUILD/output/simulation_closure_audit.json'
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
