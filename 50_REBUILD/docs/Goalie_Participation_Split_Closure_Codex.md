# Goalie participation comparison: repair verification

Reviewed 2026-09-23. Candidate `b02a851`, isolated in
`50_REBUILD/output/goalie_participation_split_review`.

## Decision

Close the preceding finding about attributing the time-indicator gain to
contract information. The five specifications are now explicit, scored together
and interpreted separately. No new blocking implementation defect was found in
the changed paths. This closes the comparison repair, not the entire goalie
branch or Phase 5. No candidate is merged or adopted by this review.

## Verification

- Full suite: **41 passed, no skips or failures**.
- All five season forecasts reproduce the preceding independent audit across
  3,683 matched cells per specification. Participation probabilities are exactly
  equal; the maximum checked WAR-error difference is 4.44e-16 after CSV loading.
- The named settings select the intended input combinations. Both the scored
  arm and price consumer read the shared `part_settings` helper.
- The period-only contract runner was rerun. Its contract forecast-parity and
  observation-model guards pass. The separate no-input contract runner was also
  run by this review to fill a gap in the candidate's decision table.

Season-level results, lower is better:

| Participation specification | Brier | WAR RMSE |
|---|---:|---:|
| Current export-membership definition | 0.205589 | 2.073319 |
| Neither input | 0.195769 | 2.065093 |
| Period and contract status | 0.194038 | 2.061840 |
| Period only | 0.192665 | 2.061686 |
| Contract status only | 0.195583 | 2.065049 |

The report now correctly separates the period effect from contract information.
It also qualifies the vendor-completeness assumption and withdraws the claim
that the remaining dollar error is necessarily noise. Those corrections stand.

## Dollar reproduction and the missing no-input option

All figures below use the current run's production price line for predictions
and realised outcomes, on the same 133 completed contracts. The no-input rows
are this review's extension; the other rows reproduce the candidate's results
apart from immaterial last-digit differences.

| Ability forecast | Participation | RMSE, $M | MAE, $M | Bias, $M | Beats current on squared error |
|---|---|---:|---:|---:|---:|
| Production | Current | 6.882 | 3.985 | +0.566 | |
| Production | Both inputs | 6.879 | 3.849 | +0.187 | 51% |
| Production | Period only | 6.932 | 3.766 | -0.064 | 33% |
| Production | **No inputs** | **6.931** | **3.807** | **-0.006** | **32%** |
| Rate | Current | 6.923 | 3.730 | -0.159 | |
| Rate | Both inputs | 6.961 | 3.619 | -0.475 | 24% |
| Rate | Period only | 7.033 | 3.559 | -0.674 | 10% |
| Rate | **No inputs** | **7.035** | **3.593** | **-0.632** | **10%** |

The no-input alternative removes nearly all of production's sample mean bias,
but increases its sample RMSE and does not win on squared dollar error. Its
rate-forecast squared error and negative bias also worsen. There is no new
accuracy victory to claim for the simpler specification.

**Recommendation, not adoption:** use no contract inputs as the provisional
goalie participation baseline. It removes the problematic export-membership
signal without imposing the vendor's 2018 boundary or assuming complete contract
coverage. That recommendation favours a simpler specification without the
identified data-availability signal; it is not the winner under the declared
squared-dollar-error criterion. Preserve the measured dollar trade-off and keep
the other specifications as sensitivities. Retain the production ability
forecast as the provisional main arm. A recency-weighted fit is optional future
work, not necessary to close this repair. Changing the experimental default and
rerunning its dependent results requires an explicit adoption decision.

## Qualifications when choosing a specification

The candidate says each specification was carried through the dollar runner,
but its cross-run table loads only current, observable and period-only files.
The no-input and contract-only alternatives are not in that reported dollar
comparison. Therefore "no replacement improves contract dollars" must be scoped
to the two replacements actually priced. The review adds the no-input result
separately; it does not imply Claude had already run it.

The annual residual table reproduces: every reported target-season interval
includes zero. That is evidence of no clearly detected aggregate step, not proof
that no step exists or an identification of what the period indicator absorbs.
The intervals are fairly wide, and the mix of forecast horizons changes by
target year. The report's caution about tying the model to the vendor's coverage
boundary is appropriate. Recency weighting remains an untested alternative,
not a necessary new prerequisite for closing this repair.

Neither mean bias near zero nor a bootstrap win share near one half establishes
that a model is calibrated or equivalent to another. Those are development
diagnostics. Removing a known problematic membership signal can be justified
without claiming a demonstrated gain in contract-dollar accuracy.

## Reproduction and scope

Audit: `50_REBUILD/code/review_goalie_participation_split.py`. Modes `setup`,
`checks`, `top`, `period`, `none`, `compare`, `dollars`, `dollars_with_none`.
Evidence is ignored under `50_REBUILD/output/`, prefixed
`goalie_participation_split_`.

The two current/observable pickle fixtures are reused from the independently
reproduced `c4ddcf0` review. Their underlying model and currency implementations
are unchanged; the new named settings produce the same scored forecasts.
Period-only and no-input paths are freshly generated in this checkout.
The extended dollar audit invokes the candidate's comparison function with
the no-input file added to its file list; no pricing or scoring formula changes.
All comparisons assert common realised targets.

Career-resampling statistics use the same 2,000 draws, aggregated from group
sums as verified in the preceding reviews. Vendor inputs and canonical
production outputs are not written. Only review, audit and state/session files
change on main.
