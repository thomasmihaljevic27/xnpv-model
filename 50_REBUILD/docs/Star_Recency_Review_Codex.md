# Recency-weighted aging review

Reviewed candidate `293f4d6` on 2026-09-24 in an isolated checkout.

## Decision

Close this sequence of star-residual experiments and retain the adopted forecast
with its measured subgroup bias recorded. The recency candidate is implemented
as declared, its results reproduce, and it does not earn adoption. No
implementation blocker was found. Correct the horizon label below when carrying
the limitation forward; this does not require another modeling experiment.

Proceed to the remaining Phase 5 acceptance work. Closing the investigation
means stopping the current search for a repair. The bias remains unresolved.

## Independent verification

- Full suite: **46 passed, zero skipped, zero failed**.
- Full scoring run: 40,510 forecasts per variant, 1,217 contracts valued, and
  1,176 ended terms scored.
- On each of the seven development pages, the actual least-squares inputs
  preserve row identities, targets, and explanatory variables. Both observed
  and imputed rows receive exactly the declared recency factor.
- The code dates a row by its starting season t and uses `(page - 2) - t`.
  This equals `(page - 1) - (t + 1)`, the declared age of the outcome season.
  All outcome seasons precede the page.
- An infinite half-life gives weights of one and reproduces the adopted
  coefficients exactly. Corrupting future rates leaves the candidate's fitted
  coefficients and weights unchanged. Changing the candidate's half-life to
  four makes check 46 fail as intended.
- Adopted aging coefficients match the preceding implementation. The adopted
  forecasts are exactly unchanged on all 40,510 rows. Participation, games
  share, and horizon-zero rates are identical across the two variants.

| Measure | Adopted | Recency candidate |
|---|---:|---:|
| Season WAR RMSE | 0.8151 | 0.8156 |
| Season WAR MAE | 0.456457 | 0.457016 |
| Overall squared-error wins | -- | 69/2,000 |
| Star rate bias at h5 | -0.921 | -0.947 |
| Star squared-error wins | -- | 463/2,000 |
| Primary dollar RMSE | $3.513M | $3.522M |
| Primary dollar squared-error wins | -- | 155/2,000 |
| Recency-line dollar squared-error wins | -- | 116/2,000 |

All principal reported comparisons reproduce. Absolute error also worsens:
the career-resampled difference is +0.000559 WAR, with a 95% interval of
[+0.000346, +0.000775]. This is a small difference. Participation is unchanged.
These resampling counts describe the development sample; they are not a fresh
confirmatory test after the preceding candidate comparisons.

## Corrections to the retained limitation

### The 0.17 WAR figure belongs to h0

The attachment and the new limitation summary associate 0.17 / 0.64 / 0.87 WAR
under-forecasting with one / three / five seasons ahead. The first belongs to
the valuation season. The independently reproduced adopted results are:

| Seasons ahead | Rate bias among seasons played | Season WAR bias over all forecasts |
|---|---:|---:|
| 0 | -0.027 | -0.170 |
| 1 | -0.265 | -0.419 |
| 3 | -0.632 | -0.643 |
| 5 | -0.921 | -0.866 |

Use **0.42 / 0.64 / 0.87 WAR low at one / three / five seasons ahead**.
The report's original table has the correct numbers; the new closure paragraph
and queue summary need the same horizon labels.

### Carry the forecast limitation into dollars without asserting its size

The adopted forecast underestimates future production for the predefined star
group on these development pages. That is a reason to examine star-contract
valuation results carefully. It is not a measured dollar undervaluation of each
star contract. The contract sample, term, price coefficients, floor, and control
rights also affect the dollar result. The page-level star group and a group of
contracts must not be treated as identical without a stated membership rule.

The prior diagnostic finds an excessive annual step on 84 careers selected for
observable consecutive seasons. It supports that conditional finding, while
leaving survivor selection and the underlying cause unresolved. Retain that
qualification beside the limitation. A failed five-season half-life sensitivity
does not establish that calendar-period differences play no role.

## Next work and plan adherence

The remaining Phase 5 acceptance tasks are appropriate: compare simulated
distributions under the previous and adopted leaders on the same contracts,
score development dollars, and reconcile contract by contract with production.
Use fixed group membership, common random draws, the same pricing convention,
and calibration dated to each decision. Declare whether uncertainty is held
fixed or refitted for each leader; those answer different comparison questions.
Carry unmatched contracts and reasons explicitly.

The plan also requires the simulation's zero-uncertainty identity and records
full-chain differences against production. The present point-forecast scoring
does not complete those simulation acceptance requirements. Reserved cohorts
were not rerun in this review, and Phase 5 remains open.

## Artifacts and scope

`50_REBUILD/code/review_star_recency.py` provides setup, checks, run, probe, and
audit modes. Logs are under ignored `50_REBUILD/output/star_recency_*.txt`;
fresh candidate results remain in the isolated review checkout. No forecast,
production implementation, or vendor input was changed. The candidate branch
was not merged or adopted.
