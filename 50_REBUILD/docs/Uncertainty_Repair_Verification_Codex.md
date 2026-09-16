# Uncertainty repair verification

Reviewed 2026-09-15. Candidate: `9c27042` on
`claude/amazing-johnson-cllbgl`, tested in an isolated checkout.

## Verdict

All three findings in [the preceding review](Uncertainty_Implementation_Review_Codex.md)
are resolved on the tested paths. No new blocking implementation defect was found in these
repairs. The reported revised numbers reproduce. This closes the diagnostic and distribution
mean bugs; it does not establish that the uncertainty model is adequately calibrated for
stars or young players.

## 1. Sensitivity now holds the fitted model fixed

The repaired runner fits once for each evaluation year and supplies that same model and
original subject list to the altered-input predictions. Refitting is a separate, labelled
comparison. An independent frozen-model rerun reproduces the following mean changes after
adding 0.5 wins per 82 games to the latest observed season:

| Forecast horizon | Change in predicted wins |
| --- | ---: |
| h0 | +0.115650 |
| h1 | +0.107525 |
| h2 | +0.098975 |
| h3 | +0.090184 |
| h4 | +0.081332 |
| h5 | +0.072587 |

Here h0 is the first forecast season and h5 is five seasons later. The share of the shock
passed into the forecast falls from 23.1% to 14.5%. The previously reported increasing
response came from changing both the inputs and the fitted model.

The separate refitted comparison reproduces +0.226 at h0 and +0.325 at h5.
The runner also discloses missing answers: deleting the latest season loses 4,764 of 41,496
requested player-horizon predictions; deleting the oldest loses 4,752; reducing games played
by 10% loses 234. The additive shock answers all 6,916 subjects at each horizon.

## 2. Residual reports use the correct evaluation year's calibration

The wrapper retains calibrators by evaluation year. Reports 5 and 6 retrieve the matching
one for each year's predictions. Independently recomputing the scaled residuals confirms
the played-star h5 median of +0.511 and 95th percentile of +3.637.

Of 151 played star seasons at h5, 28 (18.5%) exceed their own fitted 95th percentile.
The intended upper-tail rate is 5%. This is a conditional-on-playing comparison; it does
not isolate how much unconditional undercoverage comes from the forecast centre,
participation probabilities, or the spread.

The page-specific realized/fitted width ratios range from 0.942 to 1.114. They compare
different season/player mixtures and do not identify a percentage of overfitting.
Withdrawing the earlier 4.5% optimism claim is appropriate.

## 3. The distribution mean agrees with the reported forecast

The fitted residual quantile function is centred using its integral under the interpolation
rule actually used by the wrapper. Averaging the raw residual observations would not exactly
centre that interpolated function, because its two endpoints receive half weight.

An independent audit of all 40,510 scored rows finds a maximum absolute difference of
2.60e-16 WAR between the distribution expectation and the point expectation. Point forecast
columns remain unchanged. The candidate's separate numerical integration on 4,000 rows
has a maximum gap of 0.00063 WAR, consistent with its finite integration grid.

The removed 2021 shape mean is +0.09685 in standardized residual units, not WAR.
Keeping the forecast centre fixed is an explicit modelling choice; the empirical residual
mean is not silently applied as a forecast correction.

The full repair suite passes **22 checks, with zero skips or failures**, including both
production-adapter checks using the local confidential workbook. Check 22's numerical
integration gap is 0.000485 WAR. I also disabled centring in memory and reran that check:
it failed as intended, detecting a distribution mean up to 0.2228 wins from its forecast.
No candidate source file was changed for this adversarial test.

## Remaining model limitation

The revised nominal 80% interval coverage reproduces:

| Group | h0 | h1 | h2 | h3 | h4 | h5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| All scored rows | 83.6% | 83.2% | 82.7% | 82.2% | 84.3% | 83.6% |
| Stars: 3+ trailing wins | 84.7% | 81.8% | 73.9% | 73.9% | 75.9% | 60.8% |
| Age 22 or younger | 76.1% | 76.0% | 71.4% | 66.1% | 69.0% | 66.3% |

Aggregate coverage hides substantial subgroup errors. These are still open model questions.
The changed centring also changes percentile thresholds, so the revised exceedance rate
does not itself mean the unchanged point forecast became worse.

The three future-data interventions still produce exactly zero changes across the seven
evaluation years. The placebo increases MAE by 44-68%; it is not another zero-change test.

The rebuild remains a development candidate. Simulation, A3, control/goalie comparisons,
dollar reconciliation and final reserved evaluation remain separate plan work. This review
does not merge the candidate, rerun the full point-forecast leaderboard, or unseal a holdout.

## Reproduction record

Used the existing `50_REBUILD/code/review_uncertainty.py` with candidate root
`50_REBUILD/output/uncertainty_repair_review`, separately in `uncertainty` and `leakage`
modes, plus the candidate repair suite and the in-memory negative test described above.
Local logs are ignored and contain no new committed vendor exports:

- `50_REBUILD/output/uncertainty_repair_checks.log`
- `50_REBUILD/output/uncertainty_repair_uncertainty.log`
- `50_REBUILD/output/uncertainty_repair_leakage.log`
- `50_REBUILD/output/uncertainty_repair_adversarial.log`

The aggregate JSON audit files identify the tested candidate directory. Candidate-generated
coverage and shape CSVs remain inside that isolated checkout's ignored output directory.

