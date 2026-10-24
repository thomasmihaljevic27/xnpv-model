"""One-time user-supplied extension scenario; canonical inputs remain unchanged."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / '30_OUTPUT' / 'minten_stubs'))
import os
os.environ['SOURCE_DIR'] = str(Path.cwd() / '10_SOURCE')
os.environ['OUTPUT_DIR'] = str(Path.cwd() / '30_OUTPUT')
sys.path.insert(1, str(Path.cwd() / '20_CODE'))
import pandas as pd
import skater_forward_projection as fp
from exit_hazard import bucket, age_group

# Reuse the fitted table printed by the current locked exit-hazard run log.
# This keeps the one-time calculation independent of statsmodels installation.
FIT = {
 ('star','<=22'): .0042, ('star','23-26'): .0081, ('star','27-30'): .0079, ('star','31-34'): .0120, ('star','35+'): .0391,
 ('regular','<=22'): .0050, ('regular','23-26'): .0096, ('regular','27-30'): .0094, ('regular','31-34'): .0142, ('regular','35+'): .0460,
 ('fringe','<=22'): .0522, ('fringe','23-26'): .0957, ('fringe','27-30'): .0937, ('fringe','31-34'): .1358, ('fringe','35+'): .3454,
 ('negative','<=22'): .1005, ('negative','23-26'): .1768, ('negative','27-30'): .1734, ('negative','31-34'): .2419, ('negative','35+'): .5172,
}
MARG = {'star': .0097, 'regular': .0110, 'fringe': .1055, 'negative': .1941}

sp = fp.SkaterProjector()
base = sp.spine[(sp.spine.player_id == 19198) & (sp.spine.season_start == 2026)].iloc[0].copy()
supplied = pd.read_csv(r'C:\Users\thoma\Downloads\WAR_2526.csv')
minten = supplied[supplied.Player == 'Fraser Minten']
assert len(minten) == 1
assert abs(float(minten.iloc[0].WAR) - sp.war_lut[(base.nk, 2025)]) < 1e-12
assert base.cost == 816666
# Treat the ELC and signed extension as a single known eight-season schedule
# in memory, so the production projection retains one information date.
rows = []
for year in range(2026, 2034):
    r = base.copy()
    r['season_start'] = year
    r['cost'] = float(base.cost) if year == 2026 else 7200000.0
    rows.append(r)
sp.spine = pd.DataFrame(rows)
fp.CAP_CEILING[2026] = 104000000.0
_original_cap_path = fp.cap_path
def cap_path_with_supplied_forecast(t0, k):
    year = int(t0) + int(k)
    if year == 2026:
        return 104000000.0
    if year == 2027:
        return 113500000.0
    if year == 2028:
        return 123000000.0
    return 123000000.0 * (1 + fp.CAP_GROWTH) ** (year - 2028)
fp.cap_path = cap_path_with_supplied_forecast
h = {**FIT, **{(b, 'ALL'): p for b, p in MARG.items()}}
out = []
original_anchor = sp.anchor
for scenario in ['standard_60_40', 'latest_season_only']:
    if scenario == 'latest_season_only':
        sp.anchor = lambda nk, t0: (float(minten.iloc[0].WAR), 'latest_season_sensitivity')
    pr = sp.project_contract(19198, 2026)
    assert len(pr) == 8 and pr.season_start.tolist() == list(range(2026, 2034))
    S, prev = 1.0, None
    for _, r in pr.iterrows():
        k = int(r.k)
        if k:
            b, a = bucket(prev), age_group(int(r.age_at_valuation) + k - 1)
            S *= 1 - h.get((b, a), h.get((b, 'ALL'), 0.0))
        prev = r.projected_war
        discount = (1 + fp.CAP_GROWTH) ** (-k)
        out.append({**r.to_dict(), 'scenario': scenario, 'survival': S,
                    'pv_value': S * r.value_dollars * discount,
                    'pv_cost': r.cost_dollars * discount,
                    'pv_surplus': (S * r.value_dollars - r.cost_dollars) * discount})
    sp.anchor = original_anchor
detail = pd.DataFrame(out)
detail.to_csv(fp.OUTPUT_DIR / 'minten_one_time_npv_detail.csv', index=False)
for scenario, d in detail.groupby('scenario', sort=False):
    print('\nSCENARIO', scenario, 'path', d.iloc[0]['path'], 'anchor', d.iloc[0].anchor_war)
    print(d[['season_start','projected_war','survival','value_dollars','pv_surplus']].to_string(index=False))
    for label, part in [('ELC', d[d.k == 0]), ('extension', d[d.k > 0]), ('total', d)]:
        print(label, part[['pv_value','pv_cost','pv_surplus']].sum().to_dict())
    assert abs(d.pv_surplus.sum() - (d.pv_value.sum() - d.pv_cost.sum())) < 1e-7
print('CHECKS PASSED: supplied WAR match; ELC cost; eight ordered seasons; PV reconciliation.')
