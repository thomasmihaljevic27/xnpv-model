# Star residual review

Reviewed 2026-09-23 against Claude candidate `477316d` in an isolated checkout.

## Decision

Keep the adopted forecast. The new experiments support further work on the
aging formula, but the claim that removing its level terms was a single-change
test needs correction. It also admitted additional training seasons. Separate
those effects before using this experiment to choose the next specification.

The previous status-adoption review remains closed. Its three reporting
corrections are present in this candidate. No model or default was changed by
this review.

## Finding: removing level terms also changes the fitting sample

**P2.** `A1StatusNoLevelAging` sets `AGING_LEVEL_MODE = "none"`. In
`AdditiveAging.fit`, the adopted lagged-level design contains missing values
when a player has no qualifying season before the change begins. The final
finite-design mask drops those rows. Removing the level columns makes those
same rows eligible. This affects both observed changes and imputed departures.

Actual row counts passed to least squares:

| Forecast page | Adopted, with level terms | Claude's no-level version |
|---|---:|---:|
| 2015 | 3,494 | 5,018 |
| 2018 | 5,299 | 7,212 |
| 2021 | 7,164 | 9,459 |

The source comments say that missing-lag rows use age and position alone instead
of being dropped. That fallback is not implemented in the adopted fit. Consequently,
the experiment changes the regression terms and its population together. This is
an interpretation problem even though both forecasts can be scored legitimately.

### Matched-row diagnostic

The review fits the five age/position columns while retaining the adopted
lagged-level missingness mask, outcomes, weights, imputation and dates. This is
a diagnostic in the review helper, not an adopted model.

| Measure | Adopted | Claude's no-level version | No level terms, original rows |
|---|---:|---:|---:|
| Season WAR RMSE, all players | 0.8151 | 0.8147 | 0.8133 |
| Season WAR MAE, all players | 0.4565 | 0.4619 | 0.4628 |
| Star rate bias, five seasons ahead | -0.921 | -0.261 | -0.328 |
| Below-zero tier rate bias, five seasons ahead | -0.068 | -0.364 | -0.351 |
| Star season WAR RMSE, all horizons | 1.8591 | 1.8012 | 1.7984 |

The direction survives: removing the terms on the original rows helps stars and
worsens the lowest tier. It removes about 64% of the five-year star rate bias,
rather than the approximately 72% attributed to the terms in the original run.
The pooled squared-error difference remains inconclusive and absolute error is
worse. There is no basis here to adopt either no-level version.

Using the runner's original row ordering, seed and player resampling, the matched
version beats the adopted forecast on pooled squared error in 1,610/2,000 draws
and on star squared error in 1,993/2,000. Its pooled mean squared-error difference
is -0.00289, with a 95% resampled interval of [-0.00993, +0.00375]. The helper
asserts identical weighted age/position design matrices and weighted targets on
all seven pages, rather than treating equal row counts as proof of equal inputs.

Required correction: retain the original experiment as a combined specification
and sample change, add the matched-row comparison, and make a guard compare the
training-row identities and weights when an experiment claims to change only
regressors. Missing-lag treatment itself can be a separate candidate. Correct the
fallback description in the aging module and carry the narrower conclusion into
the report and state records.

## Interpretation

The rate bias is measured among players who actually played. It is a forecast
diagnostic, not an estimate of how all stars age. The unconditional season-total
miss confirms that the overall forecast underpredicts this group, but cannot
separate rate, games and participation errors by itself.

The direction is not merely an artifact of comparing different endpoint samples:
on 150 matched player/page pairs that played at both endpoints, observed rate
falls from 3.226 to 2.802 and the forecast falls from 3.258 to 1.898. Those are
still survivors. The evidence supports testing the aging formula; it does not
identify a biological aging effect or establish why the fitted coefficients
behave this way.

## Scope and reproduction

The full repair suite passes **45 checks, zero skipped, zero failed**, including
the fit-and-predict sweep of all 39 registered variants. That sweep checks that
the candidates answer the requested prediction grid; it does not assert equal
training populations in a mechanism comparison.

The complete star runner was rerun: 40,510 scored forecasts per version,
1,217 priced contracts and 1,176 ended terms scored in dollars. Participation,
games share and horizon-zero rates are exactly equal across all four versions,
checked row by row, not inferred from rounded Brier scores.

| Candidate | Pooled season squared-error wins /2,000 | Primary dollar wins /2,000 | Primary dollar RMSE |
|---|---:|---:|---:|
| Survivors-only aging | 1,601 | 1,065 | $3.512M |
| No level terms | 1,130 | 1,183 | $3.500M |
| Direct horizon regression | 1,288 | 1,212 | $3.507M |

These counts reproduce exactly. The adopted dollar RMSE is $3.513M. On the
sensitivity currency, the counts are 537, 449 and 735, versus the published
537, 449 and 734; survivor RMSE prints $3.759M rather than $3.760M. These small
reproduction differences do not change any conclusion; their cause was not
isolated. The decision to adopt none of the three is supported.

One housekeeping correction belongs with the finding: the star runner's header
still says the five-year season WAR miss is 1.06. The current run gives 0.866,
which the report correctly rounds to 0.87.

The helper is `50_REBUILD/code/review_star_residual.py`. Its modes are `setup`,
`checks`, `run`, `probe`, and `audit`. It reads vendor inputs and writes only to
ignored review outputs. The matched-row diagnostic has not been scored in
contract dollars. Simulation distributions, control years and the full production
chain were not rerun for this review. Phase 5 and confirmatory testing remain open.
