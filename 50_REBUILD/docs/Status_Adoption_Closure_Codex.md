# Contract-status adoption repair and sensitivity review

Reviewed 2026-09-23. Candidate `5864cb7` in an isolated checkout.

## Decision

The three adoption-review findings are closed. Fresh integration and production
reconciliation complete, the missing-history diagnostic completes, and the
clipping effect is reported separately from simulation noise. No new
implementation blocker was found. Keep the provisional status-only baseline,
retain the carried method as a scored sensitivity, and proceed to the declared
star forecast residual work. The reporting qualifications below do not require
another implementation repair cycle.

## Scope

This review checks the three findings in `Status_Adoption_Review_Codex.md` and
the newly scored carry-forward sensitivity. It does not close Phase 5 or the
trade back-test. The matched comparison of simulated value distributions under
the previous and adopted leaders remains outstanding.

## Implementation

The valuation comparison now imports `LEADER` and `PRIOR_LEADER` from the
simulation runner. It retains the previous model under its own label. Both
the comparison and simulation write the class name; integration requires those
names to agree and retains its independent dollar consistency check. Category
membership is declared: the adopted-model grouping is primary and the previous
grouping is reported separately.

The missing-history fix preserves the requested subject list. Missing anchors
receive no lookup date and a participation fallback; the missing production
rate leaves them visibly unanswered. The runner can therefore count these
cases instead of crashing or silently changing its subjects.

Independent deliberate reversions were caught:

| Reversion | Result |
| --- | --- |
| Comparison's adopted label mapped back to the old class | Check 44 fails |
| Missing-anchor date changed back to `int(NaN)` | Check 45 fails |

Check 44 also exercises the integration caller on mismatched model names and
an artifact without a model name. The revised exact clipping calculation uses
the transition recursion, separating its expected effect from simulation noise.

## How to read the carry-forward experiment

The tested method carries the **whole participation fit** from the last supported
horizon, holds its non-contract features at that horizon, substitutes contract
status for the target season, and applies an observed participation decay.
It is a defined sensitivity, but its outcome does not isolate the effect of
extending only the contract-status coefficient while retaining the target
horizon's other coefficients. Rejecting this method does not establish that
all methods of extending the status effect would fail, or that the baseline
cliff represents an actual change in player survival.

The current decision is appropriately limited: retain the provisional baseline
and record this sensitivity's result. There is no need to search indefinitely
for a smoother version that wins before proceeding to the next declared task.
The resample counts describe comparative performance on these development
contracts. They are not probabilities that one model is true. The roughly
$5,000 dollar-RMSE difference is small; retaining the incumbent does not require
claiming that the alternative is decisively worse in the population.

## Reporting qualifications

- "All 29 moves were upward" conflicts with the report's own transition counts:
  24 move from 0-0.5 to 0.5-1, four from 0.5-1 to 1-2, and one from 0-0.5 to
  below zero. That is 28 upward and one downward.
- The 0.000744 WAR mean absolute clipping effect is averaged over the **18
  clipped terms**, not all 1,473 terms. The 15 priced clipped terms are a
  different population and retain the earlier 0.000415 figure.
- Exact zero change refers to the three future-data invariance checks. The
  shuffled-player placebo passes by worsening forecast error, not by producing
  zero change.

These are qualifications to the report, not reasons to reopen the earlier
signing-date repairs or the goalie baseline decision.

## Reproduction

The full suite returns **45 passed, 0 skipped, 0 failed**. The complete leakage
runner finishes, with zero change in the three future-data checks on each
development page and the expected loss of skill in the shuffled-player test.
Removing the last season leaves 4,764 of 41,496 requested subject-horizons
unanswered; the count is reported and the diagnostic completes.

The carry-forward score comparison reproduces:

| Score | Carried method beats adopted |
| --- | ---: |
| Season participation Brier score | 329 / 2,000 |
| Season WAR squared error | 2 / 2,000 |
| Point dollars on adopted currency | 119 / 2,000 |
| Point dollars on previous currency | 124 / 2,000 |

Primary dollar RMSE is $3.513M adopted and $3.518M carried. On the previous
currency, this run gives $3.518M and $3.523M, respectively, within $0.001M of
Claude's displayed values. The conclusion and exact resample counts agree.

The fresh simulation, six-forecast comparison, integration, and production
reconciliation all complete. Both valuation artifacts name
`A1HingeExposureStatus`; point surplus matches exactly on all **1,217 contracts**.
An independent artifact audit confirms each group's sign and the group ordering
agree across all six forecasts under both declared membership rules. The 29
membership changes comprise 28 upward moves and one downward move.

The eight-year production gap is $33.82M on the looser 22-contract comparison.
The strict asset-and-year screen has only five eight-year contracts and still
suppresses that cell. Term-group means account for 85.0% of squared variation
in the gap. These remain comparisons between models with the stated dating
and asset screens; they are not scores against realized trade outcomes.

On 1,473 returned development terms, the carried method reduces contracts with
a fall greater than 0.25 in participation from **34 to 15**. Both methods have
**18 clipped terms**. Their respective mean absolute clipping effects, among
those affected terms, reproduce at **0.000744** and **0.000751 WAR/season**.
Contract 6500's final-season participation changes from 0.449 to 0.773.

The season artifacts have the same unique keys, ability forecasts, and games
shares. The participation change is confined to **974 player forecasts in the
2019-page, horizon-five cell**. This is one page-horizon group, not one player
observation. The longer contract-dollar test supplies additional horizon coverage.

This review reruns the full repair suite, leakage diagnostic, valuation chain,
and carry-forward study. It checks the shared leader imports in the other
diagnostics but does not independently rerun their stress, uncertainty, or
coverage reports. It does not certify those reports' individual figures.

`50_REBUILD/code/review_status_closure.py` provides setup, suite, pipeline,
leakage, carry-forward, negative-test, and artifact-audit modes. Generated
artifacts remain under ignored `50_REBUILD/output`. No candidate merge, model
change, vendor write, or canonical production-output write was made by this
review.
