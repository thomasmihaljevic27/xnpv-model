"""Independent checks of 8239d29; consumes the local runner capture, no model edits."""
import os
from pathlib import Path
import pickle
import sys
import json

root = Path(__file__).resolve().parents[2]
candidate = root / '50_REBUILD/output/simulation_repair_review'
os.environ['SOURCE_DIR'] = str(root / '10_SOURCE')
os.environ['OUTPUT_DIR'] = str(root / '30_OUTPUT')
sys.path.insert(0, str(candidate / '50_REBUILD/code'))
import numpy as np
import pandas as pd
import npv_simulation as S
import run_npv_simulation as R
import repair_checks as checks
from player_season_table import build, birthdate_source
import rebuild_config as C

result = {}
S.self_test(n_paths=600000)
result['large_sample_self_test'] = 'PASS'
original = S.Persistence.gaussian_from_rank
try:
    S.Persistence.gaussian_from_rank = staticmethod(lambda x: np.asarray(x))
    try:
        S.self_test(n_paths=3000)
    except AssertionError as exc:
        result['old_conversion_mutation'] = str(exc)
    else:
        raise AssertionError('The analytic test missed the old conversion bug')
finally:
    S.Persistence.gaussian_from_rank = staticmethod(original)

# Same performance normals, different participation uniforms: exactly the runner's calls.
rng = np.random.default_rng(99)
normals = rng.standard_normal((2000, 1))
p = S.Persistence()
args = ([1.0], [0.0], [.7], np.zeros(1001), p, 2000, rng)
a = S.draw_paths(*args, normals=normals, r_return=.1)
b = S.draw_paths(*args, normals=normals, r_return=.1)
result['one_year_common_draw_counterexample'] = {
    'different_paths': int((a != b).sum()), 'total': len(a),
    'means': [float(a.mean()), float(b.mean())]}

table = build(birthdate_csv=birthdate_source()[0], verbose=False)
# A consumer that fails on entry still leaves c25 green: c25 never executes it.
def broken_consumer(*args, **kwargs):
    raise AssertionError('Runner consumer was reached')
old_main, old_dependence = R.main, R.page_dependence
try:
    R.main = R.page_dependence = broken_consumer
    result['c25_with_disabled_consumers'] = checks.c25(table)
finally:
    R.main, R.page_dependence = old_main, old_dependence

with (root / '50_REBUILD/output/simulation_review_seasons.pkl').open('rb') as f:
    seasons, spreads = pickle.load(f)
pers, rets = R.page_dependence(spreads, table)
result['page2018'] = dict(permanent=pers[2018].w_perm_, fading=pers[2018].w_fade_,
                          phi=pers[2018].phi_, return_rate=rets[2018])
result['matrix_max_rank_error'] = max(float(np.max(np.abs(
    S.Persistence.rank_from_gaussian(p.matrix(8)) -
    p.rho(np.abs(np.arange(8)[:, None] - np.arange(8)[None, :])))))
    for p in pers.values())
d = pd.read_csv(C.out_path('npv_simulation.csv'))
one, eight = d[d.term == 1], d[d.term == 8]
result['runner'] = dict(n=len(d), sign_changes=int((np.sign(d.surplus_point) != np.sign(d.surplus_sim)).sum()),
    mean_gap=float(d.gap.mean()), one_year_sd_contrast_pct=float(100*(one.sim_sd.mean()/one.sd_indep_errors.mean()-1)),
    one_year_unequal_sd=int((one.sim_sd != one.sd_indep_errors).sum()),
    eight_year_sd=float(eight.sim_sd.mean()), eight_year_absorbing_sd=float(eight.sd_absorbing.mean()))

# Exact marginal recursion quantifies clipping, without Monte Carlo noise.
clips = []
for row in d[d.marginal_clipped > 0].itertuples():
    page, mu, sg, target = seasons[row.contract_id]
    rate = rets[page]
    actual = [target[0]]
    for h in range(1, len(target)):
        exit_prob = np.clip(1-(target[h]-(1-target[h-1])*rate)/target[h-1], 0, 1)
        actual.append(actual[-1]*(1-exit_prob)+(1-actual[-1])*rate)
    error = np.asarray(actual)-target
    clips.append(dict(contract_id=int(row.contract_id), target=target.tolist(), actual=actual,
        max_probability_gap=float(np.abs(error).max()), mean_war_gap=float(np.mean(mu*error))))
result['clipped_terms'] = clips
dest = root / '50_REBUILD/output/simulation_repair_audit.json'
dest.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
