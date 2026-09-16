# Simulation repair verification

Reviewed commit `8239d29` on 2026-09-16 in an isolated checkout. No candidate
implementation was changed or merged. This review supersedes the open-defect status
of the previous simulation review where explicitly stated below.

## Decision

The three substantive repairs are present: uncertainty is selected at the contract's
date, the copula converts rank correlation correctly, and participation allows returns.
Continue valuation integration. Two small implementation/testing corrections remain
before closing this repair pass: actually share participation draws in comparisons,
and make the leakage guard exercise the runner that selects the calibration.

This is still an aggregate simulator. RFA walk-away/control years, goalies, the plan's
joint path design, development dollar scoring and contract-level reconciliation remain
outside this implementation. No final back-test or adoption sign-off follows from it.

## Findings

### 1. The supposedly common draws still redraw participation [P2]

In `run_npv_simulation.py:253-278`, the runner generates both `normals` and `u_part`,
but passes only `normals` to the three calls to `draw_paths`. At
`npv_simulation.py:337`, every call generates fresh participation uniforms. The existing
`u_part` is used only to count clipping afterwards.

The participation model is the same in the dependence comparison, but the sampled
participation paths are not. This does not invalidate either arm's marginal estimator;
it adds avoidable sampling noise to their difference. It also disproves the claimed
exact one-year identity. All 605 one-year contracts have unequal standard deviations
between the two arms. Their cohort-average contrast is **-0.1056556%**, which prints
as zero at the report's precision. A synthetic one-year case with the same supplied
normals gives 802 different participation outcomes among 2,000 paired paths.

Required correction: accept and pass the same participation uniforms to all arms.
For the dependence comparison the resulting participation indicators should be identical.
For the return-versus-absorbing comparison, share uniforms while allowing the different
transition rules to change the indicators. Assert exact one-year path and dollar
equality, then regenerate the sensitivity figures. Do not use a Monte Carlo tolerance
for an identity that should hold path by path.

The reproduced $11.02M versus $11.09M return comparison is one Monte Carlo estimate;
its small difference has not been separated from simulation error by the claimed
common-draw design.

### 2. Check 25 does not test the runner's original failure [P2]

`repair_checks.py:843-897` constructs its own fixed-2018 calibrator and compares that
calibrator before and after corrupting future outcomes. It imports only `page_scale`
from the runner. It never exercises `per_season`, `page_dependence`, the contract's
shape/persistence selection, or a returned simulation value.

I replaced both `run_npv_simulation.main` and `page_dependence` with functions that
raise immediately. Check 25 still passed. Restoring the old latest-page selection in
the runner would likewise leave this test's execution unchanged. The test checks the
calibration components, while the original defect was in how the consumer selected them.

The actual selection at `run_npv_simulation.py:250-252` is corrected: all three objects
are indexed by the current contract's page. This finding is a missing regression guard,
not evidence that the present runner still uses future calibration.

Required correction: run the actual consumption path on an early contract while a later
page is also present, corrupt outcomes at/after the early decision date, and compare
the objects actually supplied to the simulator and its values on fixed draws. Confirm
that restoring latest-page selection makes this test fail. An extracted shared helper
is fine if the production runner and test both use it.

## What reproduced

| Check | Independent result |
|---|---:|
| Complete repair suite, including production adapters and all 34 variants | 25 passed, 0 skipped, 0 failed |
| Full runner | 1,217 contracts, 2,000 paths each |
| Page 2018 permanent/fading/decay | 0.198435704 / 0.367304064 / 0.56 |
| Page 2018 return probability | 0.095536087 |
| Large-sample simulation self-test | Pass at 600,000 paths |
| Restore missing rank conversion | Analytic test fails at 3,000 paths |
| Rank correlation error from actual eight-season matrices, all fitted pages | At most 5.56e-17 |
| Zero-uncertainty identity against `ProductionCurrency.value`, 300 contracts | Largest gap $7.45e-09 |
| Mean simulation surplus uplift | $188,119.10 per contract |
| Individual contract sign changes | 228 of 1,217 |
| Eight-year average within-contract standard deviation, returns | $11.023773M |
| Same statistic, absorbing participation | $11.091201M |

Claude's $1.49e-08 identity discrepancy differs from this environment's $7.45e-09;
both are negligible floating-point differences. The contract and tier tables reproduce
at the stated precision apart from minor rounding in a sensitivity column.

## Returns and remaining assumptions

The two-state recursion reproduces target playing probabilities when its solved exit
probability is feasible. The two disclosed exceptions are contract IDs 4921 and 6809:
their second-season playing probabilities differ from target by 0.00044947 and
0.00380745 respectively (0.045 and 0.381 percentage points). Their average annual
production shifts are -0.0000243 and +0.0000772 wins. These are small, documented
exceptions, not a reason to restart participation development.

The return rate is estimated from recent absences but applied to every absent state,
regardless of age or how long the player has been absent. That is a simplifying model
assumption, not an established return law. Retain it as a prototype limitation and
assess it during validation; this review does not require another subgroup model first.

The dependence model has a persistent component plus a geometrically fading component.
It resembles an autoregressive error model with an additional lasting component, but
the fitted parameters describe rank dependence and are imposed through a copula. They
are not identified percentages of mistakes caused by permanent versus temporary factors.

Several source comments still describe absorbing exits, a separate bending tobit
prediction, and point valuations assuming independent errors. The revised report
corrects these statements, but the source explanations should be brought into agreement.

## Evidence and scope

Reproduction commands from the repository root, using the existing review environment:

```powershell
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_npv_simulation.py --candidate-root 50_REBUILD/output/simulation_repair_review --mode run
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_valuation_sensitivity.py --candidate-root 50_REBUILD/output/simulation_repair_review --mode checks
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_simulation_repairs.py
```

The last script consumes the first run's local calibrator capture. Evidence is ignored
under `50_REBUILD/output/`: `simulation_repair_run.log`, `simulation_repair_checks.log`,
`simulation_repair_audit.log`, `simulation_repair_audit.json`, and the candidate's output
CSV. No vendor data, generated output, or unrelated documents are included in the review
commit. No reserved-cohort trade valuation was evaluated.
