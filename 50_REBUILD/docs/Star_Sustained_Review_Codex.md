# Sustained-quality aging review

Reviewed candidate `f83240a` (results commit `81d885f`) on 2026-09-24.

## Decision

Keep the adopted forecast. The sustained-quality construction is implemented
as declared and its principal results reproduce. No implementation blocker was
found. Correct the claim that every score worsens: season WAR absolute error
improves slightly, while the declared squared-error primary scores worsen.

One predeclared recency-weighted aging candidate is a reasonable next experiment.
The current evidence does not establish that an older-versus-newer-season
difference causes the bias.

## Independent verification

- Full repair suite: **46 passed, zero skipped, zero failed**.
- Direct tests of the sustained input cover min(t-1, t-2), the t-1 fallback,
  missing required t-1, future values and non-default row indices.
- All seven development pages preserve the adopted fit's rows and weights.
  Corrupting future rates leaves the new aging coefficients unchanged.
- Adopted aging coefficients match the preceding implementation exactly.
- The final forecast audit confirms the adopted model is unchanged on all
  40,510 rows. Participation, games share and horizon-zero rates are identical
  across the two candidates.
- The complete runner prices 1,217 contracts and scores 1,176 ended terms.

| Measure | Adopted | Sustained candidate |
|---|---:|---:|
| Season WAR RMSE | 0.8151 | 0.8170 |
| Season squared-error wins against adopted | -- | 0/2,000 |
| Star rate bias, five seasons ahead | -0.921 | -1.017 |
| Star squared-error wins against adopted | -- | 0/2,000 |
| Primary dollar RMSE | $3.513M | $3.529M |
| Primary dollar squared-error wins | -- | 42/2,000 |
| Sensitivity dollar squared-error wins | -- | 85/2,000 |

These reported comparisons reproduce exactly. Neither candidate adoption nor a
change to the scoring rule is justified.

## Reporting corrections and limits

### Absolute error improves slightly

Season WAR MAE falls from **0.4564566 to 0.4560089**. It is lower in 1,897/2,000
career resamples, with a mean difference of -0.000448 and a 95% resampled interval
of [-0.000990, +0.000098]. The improvement is small and the interval includes
zero, but "worse on every declared score" is still incorrect. Participation
scores are unchanged by construction. Say that the candidate loses on the
declared primary squared-error scores and worsens the star bias.

### Horizon drift is descriptive, not a calendar-period test

Every tier's rate bias is lower at horizon five than at horizon zero. It is not
monotonic at every intervening step: the 2-to-3 tier moves -0.079 to +0.023,
then -0.146 to -0.095. That tier also starts negative, so not every non-star tier
starts too high. The broad end-to-end drift reproduces.

Longer horizons also change player age, observed survivor composition and
outcome-season composition. Failed level-input constructions plus downward
horizon drift do not isolate a calendar-period change. A recency experiment can
test whether downweighting older training rows improves prediction without
establishing a causal period effect.

### The tested sustained input is a particular proxy and application rule

Training uses the lower of the two past rates, with a single-season fallback.
At prediction the model passes the same projected level into both level terms,
as declared. Therefore the forecast walk uses the sum of their coefficients;
it does not carry a separate observed consistency measure along the path.
This result rejects that construction, not every use of sustained performance.

The quoted -0.034 is a partial coefficient at age 27, conditional on the other
level input. On the 2021 fit the level coefficients are -0.036265 and -0.033619;
their sum is -0.069884 in the walk, versus -0.061921 in the adopted fit. The
3.2-level, age-27 forward step reproduces at -0.279995 versus -0.250787.

## Recommended next experiment

Use **one fixed five-season half-life** as a declared sensitivity, not a fitted
or established optimal setting. Keep the full training row set. Multiply each
existing observed or imputed row weight by:

`2 ** (-(latest_completed_season - row_outcome_season) / 5)`

The row's outcome is the second season of its annual change, including an imputed
departure outcome. All outcomes must predate the page. Fit the same adopted
formula; change no participation, games, initial-rate or pricing rule. Do not
sweep half-lives after seeing this candidate's scores.

This intentionally changes weights. Its guard should assert identical row
identities and targets, then verify each new weight equals the base weight times
the declared factor. Do not require the existing rows-and-weights fingerprint
to remain equal, and do not disable the other candidates' matching guard. Check
future-data invariance and an all-ones weighting identity separately.

Use the same pooled squared-error primary score, all-tier/horizon diagnostics,
career resampling and adopted primary dollar line. Report the candidate's own
currency as sensitivity. A hard recent-only cutoff would change the sample too;
if tested later, label that explicitly as a separate experiment.

If this candidate also fails, retaining the existing model with the quantified
subgroup bias is reasonable unless a new diagnostic supplies a more specific
reason to continue. Further variations should not be generated solely until
one happens to win on the development sample.

## Artifacts and scope

Helper: `50_REBUILD/code/review_star_sustained.py`, modes `setup`, `checks`, `run`,
`probe`, `audit`. Generated results remain in ignored review output. The review
changes no forecast implementation, production code or vendor input. Full
simulation integration and confirmatory cohorts were not rerun. Phase 5 remains
open; the next experiment above is recommended, not implemented or adopted here.
