# Multi-season aging level review

Reviewed candidate `3ba71cd` (model/report commit `7bff643`) on 2026-09-24.

## Decision

Keep the adopted forecast. The multi-season candidate is implemented as declared
and does not earn adoption. Proceed to a short diagnostic before fitting more
candidates, with the cohort and comparisons specified below. The proposed
pass/fail interpretation cannot by itself distinguish recursive forecast error
from differences between player groups.

## Implementation and guard checks

- The weighted level uses seasons t-1, t-2 and t-3 with weights 1, 0.667 and
  0.667 squared, renormalized over qualifying seasons. These are recency weights,
  not weights based on player age.
- The t-1 season is required. An independent synthetic check covers a missing
  intermediate season, a missing required season, future values and non-default
  row indices. Only the intended past seasons enter the average.
- All seven development pages retain the adopted aging fit's rows and weights.
  The adopted curve's coefficients match the preceding implementation exactly.
- Corrupting every rate at or after each decision page leaves the multi-season
  aging coefficients and fitting fingerprint bit-identical.
- The complete suite passes **46 checks, zero skipped or failed**. Check 46
  covers sample matching; the independent arithmetic/date checks above test the
  new weighted-input recipe itself.

The reported 2021 coefficient and step reproduce: level coefficient -0.061921
under the adopted curve and -0.071153 under the multi-season curve; at age 27,
forward, level 3.2, the respective steps are -0.250787 and -0.265415. With the
level-by-age interaction present, the quoted coefficient is the level slope
at age 27, not one common slope at every age.

## What the result establishes

The full v1.2 runner reproduces the reported results on 40,510 forecasts per
variant, 1,217 priced contracts and 1,176 ended terms scored in dollars:

| Multi-season candidate measure | Independent result |
|---|---:|
| Star rate bias, five seasons ahead | -0.956 |
| Below-zero tier rate bias, five seasons ahead | -0.025 |
| Star season squared-error wins | 1/2,000 |
| Pooled season squared-error wins | 234/2,000 |
| Main-currency dollar squared-error wins | 826/2,000 |
| Sensitivity-currency dollar squared-error wins | 778/2,000 |

Primary dollar RMSE is $3.514M versus the adopted $3.513M. The final audit
confirms that the adopted forecast is exactly unchanged on all 40,510 rows;
participation, games share and horizon-zero rates are identical across the three
versions. The matched no-level reference still reproduces the independent
implementation within 1e-12.

This construction does not repair the star bias. A more negative coefficient on
the changed input does not by itself reject double shrinkage as a mechanism.
The input remains a weighted history, while prediction still passes a projected
current-season level to a relationship fitted on a level ending one season
earlier. The failed score establishes that this particular substitution does
not help; it does not identify why the original forecast is biased.

The previous requested cleanup is substantially applied: missing-lag treatment,
the lack of guaranteed independent noise, the 0.866 season-total miss, the file
list and the narrower hinge conclusion are corrected.

## Correct the cohort description before the next diagnostic

The report calls the forecast's star group a three-season weighted total. The
harness actually uses a **60/40 total over the two latest page seasons** when
both exist. Otherwise it uses the available latest season, then the second,
then the third as fallbacks. The forecast itself can read three seasons; that
is different from the reporting group's membership rule.

Use `forecast_harness.subjects_at` and its `tier == "3+"` labels for the new
diagnostic. Do not reconstruct a different group from the new multi-season rate.
Keep player/page membership fixed across all arms, and report how many members
have the consecutive played seasons required to observe each rate change.

## A diagnostic that can locate differences

Fit once using information available on each development page and freeze those
coefficients for every diagnostic arm. The initial forecast rate is separately
calibrated. The aging walk's first transition is the page season to page+1;
the last observed season to the page is not that first aging step.

On common star player/page/transition rows, compare:

1. **Training-aligned observed inputs:** predict each observed change from t to
   t+1 using age at t and the actual lagged level ending at t-1. For the new
   candidate, construct that lagged level using its declared weighted window.
2. **Observed current-level inputs:** keep the same fit, rows and age, but pass
   the actual level at t, as the walk's current-level convention would. This
   separates a change in the input's timing and definition from recursion.
3. **Frozen forecast path:** use the projected current levels from the original
   page's walk on those same rows. Report both the starting-level error and
   subsequent increments, rather than assigning all later error to the steps.

Arms using realized future seasons are diagnostic hindsight comparisons, not
deployable forecasts or predictive-performance improvements. Compare all three
on the same observed changes and weights. Keep the full-cohort season-WAR score
with absences counted separately, because rate changes cannot be observed for
players who do not play both seasons.

A first-step success does not establish that repeated application causes the
long-run error: later selection, ages, level inputs and errors can differ. A
failure does not establish that group membership causes it either. To investigate
membership, apply the correctly aligned arm to explicitly defined comparison
groups using the same dates and weighting, and report their counts. Treat the
result as a localization exercise, not a binary identification test.

## Scope and artifacts

Review helper: `50_REBUILD/code/review_star_multi.py`; logs and generated tables
remain in ignored review output. No production code, adopted model or vendor
input is changed by this review. Full simulation distributions, control years,
production reconciliation and confirmatory testing remain outside this rerun.
