"""Reproduce bc724e5 and audit the definitions used in its reconciliation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
candidate = root / '50_REBUILD/output/integration_review'
prod = root / '50_REBUILD/output/integration_production'
prod.mkdir(exist_ok=True)
os.environ['SOURCE_DIR'] = str(root / '10_SOURCE')
os.environ['OUTPUT_DIR'] = str(prod)
os.environ['PUCKPEDIA_CONTRACTS_XLSX'] = str(root / '10_SOURCE/PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx')
# Use the bundled Excel reader; keep the review environment's scientific packages first.
bundled = Path(sys.base_prefix) / 'Lib/site-packages'
sys.path.append(str(bundled))
os.environ['PYTHONPATH'] = str(Path(sys.prefix) / 'Lib/site-packages') + os.pathsep + str(bundled)
ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=['production', 'integration', 'audit', 'guards'])
args = ap.parse_args()

if args.mode == 'production':
    for name in ['contract_season_spine.csv', 'WAR_with_age.csv', 'goalie_value_spine.csv']:
        shutil.copy2(root / '30_OUTPUT' / name, prod / name)
    for name in ['skater_value_engine', 'skater_forward_projection', 'rfa_terminal_value',
                 'exit_hazard', 'goalie_value_engine', 'contract_npv']:
        with (prod / (name + '_review.log')).open('w') as f:
            subprocess.run([sys.executable, str(candidate / '20_CODE' / (name + '.py'))],
                           env=os.environ.copy(), stdout=f, stderr=subprocess.STDOUT, check=True)
        print(name, 'PASS', flush=True)
    sys.exit()

sys.path.insert(0, str(candidate / '50_REBUILD/code'))
import numpy as np
import pandas as pd
import rebuild_config as C
if args.mode == 'integration':
    import run_valuation_integration as I
    I.main()
    sys.exit()

if args.mode == 'guards':
    import contextlib
    import io
    import run_valuation_integration as I
    original_read, original_write = pd.read_csv, pd.DataFrame.to_csv
    original_log, original_write_log = C.log, C.write_log
    baseline = original_read(C.out_path('contract_valuation.csv'))
    tests = {}
    for mutation in ['mismatched_simulation_baseline', 'duplicate_production_id', 'reserved_cohort']:
        captured = []
        def read(path, *a, **kw):
            frame = original_read(path, *a, **kw)
            if mutation == 'mismatched_simulation_baseline' and Path(path).name == 'npv_simulation.csv':
                frame['surplus_point'] += 1e6
            if mutation == 'duplicate_production_id' and Path(path).name == 'contract_npv_spine.csv':
                row = frame[frame.contract_id.isin(baseline.contract_id)].iloc[[0]]
                frame = pd.concat([frame, row], ignore_index=True)
            if mutation == 'reserved_cohort' and Path(path).name == 'valuation_sensitivity.csv':
                frame['start_yr'] = 2022
            return frame
        try:
            pd.read_csv = read
            pd.DataFrame.to_csv = lambda self, *a, **kw: captured.append(self.copy())
            C.log = C.write_log = lambda *a, **kw: None
            with contextlib.redirect_stdout(io.StringIO()):
                I.main()
            tests[mutation] = dict(accepted=True, output_rows=len(captured[-1]),
                duplicate_ids=int(captured[-1].contract_id.duplicated().sum()))
        except Exception as exc:
            tests[mutation] = dict(accepted=False, error=str(exc))
        finally:
            pd.read_csv, pd.DataFrame.to_csv = original_read, original_write
            C.log, C.write_log = original_log, original_write_log
    print(json.dumps(tests, indent=2))
    (root/'50_REBUILD/output/integration_guard_audit.json').write_text(json.dumps(tests,indent=2))
    sys.exit()

sys.path.insert(0, str(candidate / '20_CODE'))
import contract_npv as N
eng = N.NPVEngine()
d = pd.read_csv(C.out_path('contract_valuation.csv'))
spine = pd.read_csv(prod / 'contract_npv_spine.csv')
j = d.merge(spine, on='contract_id', suffixes=('', '_spine'), validate='one_to_one')
rows = []
for r in j.itertuples():
    detail, summary = eng.npv(int(r.player_id), int(r.valuation_season))
    contract = detail[detail.row_type == 'contract']
    # Remove only survival: preserve discount factors, cost, and terminal value.
    no_hazard = float(((contract.value_dollars-contract.cost_dollars)*contract.discount).sum()) + summary['npv_terminal']
    hazard = no_hazard-summary['npv_total']
    rows.append(dict(contract_id=r.contract_id, length=r.length, rebuild=r.surplus,
        production=summary['npv_total'], true_no_hazard=no_hazard, hazard=hazard,
        nominal_no_survival=summary['surplus_no_survival'], terminal=summary['npv_terminal'],
        production_cost=float((contract.cost_dollars*contract.discount).sum()), rebuild_cost=r.cost,
        valuation_season=r.valuation_season, start_yr=r.start_yr,
        signed_year=pd.Timestamp(r.signed).year, n_seasons=len(contract),
        distinct_contracts=contract.contract_id.nunique(),
        actual_contract_ids=';'.join(str(int(v)) for v in contract.contract_id.unique()),
        expected_id_present=bool((contract.contract_id==r.contract_id).any())))
a = pd.DataFrame(rows)
a.to_csv(root/'50_REBUILD/output/integration_definition_audit.csv', index=False)
result = dict(n=len(a), per_term=a.groupby('length')[['rebuild','production','hazard','true_no_hazard','nominal_no_survival','terminal']].mean().to_dict('index'),
    wrong_contract_ids=int((~a.expected_id_present).sum()),
    valuation_start_mismatch=int((a.valuation_season!=a.start_yr).sum()),
    signing_year_differs=int((a.signed_year!=a.valuation_season).sum()),
    nonzero_terminal=int((a.terminal.abs()>1e-6).sum()),
    multiple_contracts=int((a.distinct_contracts>1).sum()),
    term_length_mismatch=int((a.n_seasons!=a.length).sum()),
    max_cost_gap=float((a.production_cost-a.rebuild_cost).abs().max()))
print(json.dumps(result, indent=2))
(root/'50_REBUILD/output/integration_definition_audit.json').write_text(json.dumps(result,indent=2))
