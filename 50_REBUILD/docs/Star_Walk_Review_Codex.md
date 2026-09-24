# Star-walk diagnostic review

Reviewed `55f23cb` on 2026-09-24 in an isolated checkout.

## Decision

The diagnostic reproduces and is a useful basis for the next candidate. No
implementation defect was found in the reported run. Keep the adopted forecast
until a candidate passes the declared forecast and dollar comparisons.

The supported conclusion is that the frozen curve overstates decline on these
observed star transitions, including when supplied with training-aligned actual
inputs. Recursive projected inputs are not required to produce that discrepancy.
This does not identify the full population's aging process or establish that
selection and every possible forecast-path issue have been excluded.

## Independent reproduction

The review regenerated the adopted leader's full 40,510-row harness output before
running the diagnostic, rather than trusting a saved full-cohort CSV. All 876
transition rows were checked independently for membership, season alignment,
positive weights, complete arm values and arithmetic. The observed changes and
all four predicted steps match within 1e-12. The projected-path differences also
match the curve evaluated at projected levels with actual age and position; the
maximum numerical difference is 4.72e-16. The arm contrast is not an unnoticed
age or position change.

Weighted change in WAR per 82 games per season:

| Quantity | Reproduced mean |
|---|---:|
| Observed change | -0.111772 |
| Frozen curve, actual prior-season level | -0.352124 |
| Frozen curve, actual current-season level | -0.328269 |
| Original forecast path | -0.278699 |
| Survivors-only fit, actual prior-season level | -0.306863 |

The five transition-by-horizon rows, both comparison groups and the full-cohort
season-WAR table reproduce the report's rounded figures. The full-cohort star
bias remains -0.170 initially and -0.866 at horizon five, with absences counted.

## Sample and uncertainty

There are **876 player/page/transition rows, 84 careers and 492 distinct
player-season transitions**. Repeated pages can forecast the same eventual
transition; 876 is not a count of independent outcomes.

The selection sequence is:

| Screen | Rows remaining |
|---|---:|
| Star transitions with an observable t+1 season | 983 |
| Player appears at t-1, t and t+1, at least one game each | 894 |
| At least 10 games in each of those seasons | 883 |
| Age available for the step | 876 |

The report should call this three qualifying seasons, not merely three seasons
played. Conditioning on future games and age availability can select a different
population from the whole initial star cohort.

An additional review check resamples complete careers 2,000 times, preserving
all their repeated rows and min-games weights. Predicted-minus-observed change:

| Arm | Mean error | 95% career-resampled interval |
|---|---:|---:|
| Actual prior-season input | -0.240 | [-0.347, -0.130] |
| Actual current-season input | -0.216 | [-0.325, -0.103] |
| Original projected path | -0.167 | [-0.264, -0.067] |
| Survivors-only reference | -0.195 | [-0.299, -0.090] |

All seven pages have a negative mean error under the prior-season-input arm.
The discrepancy survives this check for repeated observations. These intervals
are conditional on the selected data and fitted curves; they neither correct
survivor selection nor account for every shared calendar-season shock.

## Interpretation to retain

- **Before recursion:** the excess decline already appears in observed-input
  one-step evaluations. The projected-path arm is less negative on average here.
  Say that recursion is not needed to produce the selected-sample discrepancy;
  do not turn this into a general exclusion of forecast-path problems.
- **Imputation:** removing the departure imputation changes the mean step by
  about +0.045, leaving a -0.195 error on these rows. It does not explain the
  whole observed discrepancy. A survivors-only historical fit still does not
  make later surviving stars representative of every initial star, nor does it
  eliminate differences in season, age or prior-history composition.
- **Membership:** the comparison groups are descriptive checks with a common
  weighting rule. They do not hold every other characteristic fixed, so their
  different errors do not isolate a causal membership effect.

A sustained-quality candidate is reasonable to test. Define its inputs from
information available before the predicted change, preserve training rows and
weights, and keep the adopted currency as the primary dollar score. Score all
tiers and horizons; improvement among these 84 observed careers alone is not
an adoption criterion. State the candidate as a proposed predictive repair, not
as a mechanism already identified by this diagnostic.

## Test coverage and artifacts

The underlying model and existing repair suite are unchanged from `3ba71cd`,
whose 46/46 result was independently verified in the preceding review. The suite
was not rerun here and does not automatically validate the new diagnostic.
This review instead ran the new diagnostic, regenerated its full-cohort input,
and audited every output row independently. Keeping common-row and finite-arm
assertions in the runner would help preserve those properties on later edits;
currently `wmean` silently omits a missing value separately for each column.

Helper: `50_REBUILD/code/review_star_walk.py` (`setup`, `cohort`, `run`, `audit`).
Generated evidence remains in ignored review output. No candidate or production
change was adopted, no vendor data was written, and confirmatory cohorts were
not opened. Full valuation/simulation integration was not rerun. Phase 5 remains
open.
