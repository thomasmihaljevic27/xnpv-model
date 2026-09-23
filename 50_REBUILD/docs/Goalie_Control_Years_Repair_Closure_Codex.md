# Goalie control-year evaluation: repair verification

Reviewed 2026-09-22. Candidate `6c9ab2c` in the isolated
`50_REBUILD/output/goalie_control_repairs_review` checkout.

## Decision

Close the two findings in the preceding goalie control-year review. The runner
now compares forecasts on one realised-dollar target, and its calibration tests
account for the salary floor and non-participation. Proceed to investigating the
participation model's most confident predictions. Keep production as the
provisional default and the rate forecast as a sensitivity. No model is adopted
by this review, and Phase 5 as a whole remains open.

## Common-dollar scoring

The production forecast's price line is the primary scoring currency. Both
forecasts and the realised WAR path are repriced on it; the rate forecast's
price line is a second common-currency comparison. Own-line results remain
explicitly labelled sensitivities. The 133-contract sample is unchanged.

| Common scoring line | Production simulated RMSE, $M | Rate simulated RMSE, $M | Rate wins on squared error in career resamples |
|---|---:|---:|---:|
| Production | 6.882 | 6.923 | 44% |
| Rate | 6.923 | 6.954 | 46% |

These reproduce the previous review's independent repricing. The new scored
artifact matches the previous independent audit exactly: all 133
realised targets and both arms' point values and simulated means have zero
maximum difference after loading the saved CSVs. The rate forecast
has lower mean absolute error and smaller absolute sample bias. Production has
slightly lower sample RMSE, without a persuasive advantage in the resampling
comparison. The provisional default can stand.

The actual nested `score_on` function was extracted from the candidate for a
synthetic guard test. Different forecasts with the same contract and actual WAR
pass. Restoring own-line realised targets fails the assertion; changing the
restricted-status contract feature in only one arm also fails. This tests the
candidate's guard, not a copied approximation of it.

## Calibration with tied outcomes

The two new PIT helpers place each actual outcome within the forecast
distribution. An outcome tied with a block of forecast probability is assigned
a random position within that block. This handles the floor and zero-season
masses that invalidated the earlier nominal-coverage diagnosis.

Check 40's correctly specified synthetic examples reproduce:

| Example | Naive 80% interval coverage | Randomized PIT central 80% share |
|---|---:|---:|
| Salary floor | 89.2% | 79.7% |
| Non-participation at zero | 83.8% | 80.3% |

Disabling randomization in either helper makes check 40 fail. Its histogram and
mean checks detect failures that its central-coverage check alone would miss.

On the primary common currency, the production contract PIT mean is about
0.438, with a career-resampled interval excluding 0.5. Production's realised
outcomes tend to fall low within its predicted distribution. Both forecasts
underpredict the frequency of floor outcomes. The rate forecast's coverage
figures differ from the previous review's own-line coverage because it is now
being priced on the primary common line; this is an intended change of currency.

The top fifth of season participation predictions averages about 0.95, against
about 0.86 observed participation. The predicted-minus-observed gap is about
0.096, with a career-resampled interval of +0.057 to +0.141. That is a reasonable
next investigation. It does not establish the cause of the floor discrepancy or
how much a participation repair would improve contract values.

## Qualification to retain when moving on

The report and chat say the conditional band and whole-season distribution
"are calibrated." The narrower supported statement is: **these pooled
diagnostics did not detect a departure in the statistics tested**. Passing
central shares, a mean and a variance does not prove full distributional
calibration, and pooled results can hide subgroup errors. The participation
finding is an example of exactly that limitation.

Similarly, PIT variance alone does not isolate a spread defect from other
distribution errors. It is appropriate to withdraw the instruction to narrow
the band; it would be premature to declare every part of its shape correct.
This is a reporting qualification, not another implementation blocker or a
reason to repeat the completed repairs.

## Verification and scope

Full suite: **40 passed, 0 skipped, 0 failed**. The shared-target and PIT
mutation tests described above also pass by rejecting the deliberately broken
versions. The complete runner is rerun on the real development sample.

The review script is `50_REBUILD/code/review_goalie_control_repairs.py`.
Its `run` mode invokes the candidate runner and captures the tables supplied to
the existing PIT reporter. The initial run was interrupted after the production
season diagnostics, before the final artifacts were written. Completion used
`fast_run`: the same 2,000 career resamples, with sums and squared sums instead
of repeatedly concatenating DataFrames. Before use, the aggregation was checked
against the original functions on 30 resamples of four captured real tables,
including means, variance, central shares and coverage differences, to 1e-12.
No forecasts, fitted parameters, paths or sample selections change. `compare` checks
the primary scored artifact against the previous independent audit.
`target_guard` and `mutants` deliberately restore the defects described above.

Evidence is ignored under `50_REBUILD/output/`, prefixed
`goalie_control_repairs_`. No source data or canonical production output was
written. Candidate implementation remains isolated; review documents and state
records are the changes to main. Earlier closures and declared prototype
limitations remain in force.
