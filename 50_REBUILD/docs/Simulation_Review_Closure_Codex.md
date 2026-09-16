# Simulation review closure

Reviewed `db0c6b2` on 2026-09-16 in an isolated checkout.

## Decision

Both findings from the preceding repair review are closed. The runner now shares
participation draws, and the leakage test exercises the same calibration selector
used by the runner. Proceed with valuation integration. No additional simulator
redesign is required to close these findings.

This closes the repair review, not Phase 5 or model validation. RFA walk-away and
control years, goalies, the remaining joint-path design, development dollar scoring,
and contract-by-contract reconciliation remain open under the plan.

## Verification

- Reran the full simulator: 1,217 contracts, 2,000 paths each. Its exact one-year
  path assertion passed for all 605 one-year contracts.
- Independently checked the resulting CSV: all 605 one-year standard deviations
  are exactly equal between the dependence arms, with largest difference zero.
  Their absorbing-arm standard deviations and mean values are also exactly equal
  to the return-capable arm, as they should be for one season.
- Tested shared inputs with deliberately different random-generator seeds: all
  three one-season arms still return identical paths. Supplied performance and
  participation draws now control the result.
- Deliberately disabled `page_dependence`: check 25 fails at that function.
- Deliberately restored latest-page selection in `calibration_for`: check 25
  fails because pages 2016 and 2023 now give the same paths. These mutations were
  temporary changes to imported functions in the audit process, not file edits.
- Inspected the runner's call to `calibration_for`: it uses the current contract's
  page. The guard and runner share that selection function.

The full suite passed: **25 passed, 0 skipped, 0 failed**, including production
adapters and all 34 registered variants. The preceding correlation and return-model tests remain applicable; no
changes to those algorithms were introduced in this commit.

## Reproduced numbers and their limits

| Quantity | Local reproduction |
|---|---:|
| Contracts simulated | 1,217 |
| One-year contracts with exact equality | 605 / 605 |
| Individual contract sign changes | 223 |
| Average simulation surplus uplift | $182,944.30 |
| Eight-year average within-contract standard deviation, returns | $11.012715M |
| Same statistic, absorbing participation | $11.074470M |
| Zero-uncertainty currency identity, 300 contracts | Largest gap $7.45e-09 |

The eight-year comparison supports Claude's approximate $11.01M/$11.08M statement,
but this run rounds to $11.01M/$11.07M. The report's unchanged average-production
sentence also retains 0.3495; this run gives 0.3487 versus the point forecast's 0.3491.
These small numerical differences do not affect closure of either code finding.

Shared draws remove the unnecessary difference between two independently drawn
participation samples. They do not eliminate Monte Carlo error from a multi-year
comparison whose transition rules differ. The return-versus-absorbing difference
remains an estimate from 2,000 paths, not an exact effect with zero sampling error.
Only the one-year comparison is an exact identity.

## Scope of the leakage guard

Check 25 now covers the previously broken selection and proves that its answer
changes under the old defect. It compares simulated production paths on fixed
forecast inputs; despite its docstring's pricing language, it does not perform
contract-dollar reconciliation. Its future-scramble leg holds the original `mu`,
`sigma` and participation forecast fixed while checking selected shape, dependence
and return rate. Forecast and interval leakage have separate suite checks.

This is sufficient to close the specific selection finding. It is not a substitute
for the planned end-to-end dollar validation, nor a guarantee against every possible
future change to the runner.

The homogeneous return-rate assumption and the two small marginal-clipping exceptions
remain recorded prototype limitations. No new blocking defect was found in the repairs.

## Evidence

The isolated candidate is `50_REBUILD/output/simulation_closure_review`. Commands:

```powershell
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_npv_simulation.py --candidate-root 50_REBUILD/output/simulation_closure_review --mode run
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_valuation_sensitivity.py --candidate-root 50_REBUILD/output/simulation_closure_review --mode checks
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_simulation_closure.py
```

Run the first command to completion before the last, which reads its output CSV.
The first audit invocation was started too early and reached a missing CSV; rerunning
after simulator completion passed. This was review orchestration, not a candidate failure.
Generated logs and JSON are ignored under `50_REBUILD/output/simulation_closure_*`.
No candidate implementation was changed or merged, and no production/source data or
unrelated documents were modified.
