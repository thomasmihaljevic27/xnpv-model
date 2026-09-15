# Review of uncertainty estimates and leakage diagnostics

Reviewed 2026-09-15 at `73b77ee`, branch `claude/amazing-johnson-cllbgl`.
Source report: `Predictive_Uncertainty_and_Leakage.md` on that branch.
Implementation inspected and executed in isolated checkout `50_REBUILD/output/uncertainty_review`.

## Assessment

The reported coverage numbers reproduce. The model's nominal 80% prediction ranges contain
about 82-84% of outcomes overall, but only about 60% for the highest trailing-WAR group five
seasons ahead and 66% for players aged 22 or younger. This is a real limitation of the current
ranges on the development sample.

Two diagnostic implementations do not measure what their descriptions claim. The sensitivity
experiment refits the model after changing inputs despite saying its coefficients are fixed.
The residual-shape and optimism reports use the final page's calibrator for all pages rather
than the calibrator that generated each forecast's range. The first must be corrected before
interpreting its reported pass-through; the second changes the reported subgroup details.

There is also a distribution-consistency issue to settle before simulation: the distribution's
mean differs from the expected WAR reported in the unchanged point-forecast columns.

## Numbers reproduced

All **21 repair checks pass with zero skips** using the local XLSX and merged birthdates.
This includes the two production comparisons Claude could not run on his machine. The contract
CSV reproduction guard passes: alpha **0.01324290**, forward slope **0.02123747**, defence
slope increment **0.00286762**, on 2,349 contracts. These match the quoted run within its
displayed precision and remain inside the existing guard tolerances.

Age coverage reproduces as 98.3% of source season rows and 98.4% on source seasons 2015 and
later. The latter is how the runner defines its coverage diagnostic; it is not separately
calculated on the forecast subject grid.

| Stated range | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| 80% | 0.829 | 0.828 | 0.825 | 0.816 | 0.836 | 0.832 |
| 90% | 0.915 | 0.913 | 0.914 | 0.909 | 0.921 | 0.913 |

These are fractions of realized season WAR values inside each forecast's prediction range.
There are 6,916 observations at each of h0-h4 and 5,930 at h5, for 40,510 total scored rows.
The 50% coverage table also reproduces. Non-participation creates a probability mass at zero,
so an interval can exceed its nominal coverage without simply being too wide.

The reported 80% subgroup results reproduce:

- 3+ trailing WAR: **0.852 at h0, 0.596 at h5**.
- Age 22 or younger: **0.754 at h0, 0.663 at h5**.
- Age 34 or older: **0.977 at h5**.

The replay has 32,946 played-season residuals in its final, 2021 calibrator. The code uses
parameters fitted at the current decision date to replay earlier seasons. Those are in-sample
residuals for estimating the spread, not a sequence of forecasts fitted afresh at each earlier
date. The documentation acknowledges that limitation. Future development outcomes are still
used separately to assess interval coverage.

## Findings

The published leakage battery completes successfully. The three future-data interventions
produce zero change on all seven development pages, across rates, games shares, participation
and interval endpoints. Its fourth check is a shuffled-outcome placebo, not another zero-change
test. In this reproduction the placebo increases MAE by **44-68%**, rather than the report's
29-39%. The direction supports player-specific predictive information. Neither the placebo nor
these forecast tests validates market timing or the complete future dollar simulation.

### 1. P1: the sensitivity experiment changes the fitted model as well as its inputs

`run_leakage_tests._predict_at()` constructs a new model and calls `fit()` on every invocation.
Test 5 calls that helper on both the original and altered tables. Altering the latest completed
season therefore changes training outcomes and the fitted regression, aging and participation
models. Deleting a season can also change the eligible population; the subsequent inner join
keeps only subjects answered in both runs.

This contradicts the test's statement that the fit is held fixed. Its results measure a
combination of parameter re-estimation and changed forecast inputs. They cannot be presented
as the direct weight on the most recent season.

The independent audit repeats the experiment with one fitted object per page, the same subjects,
and changes only the information handed to `predict()`. Both the published and corrected
results are retained in ignored output. The published rise from roughly 0.45 to 0.65 is a
fraction of the 0.5-WAR-per-82 shock, not a 0.45-to-0.65 WAR movement.

| Response to +0.5 WAR per 82 in the latest season | h0 | h5 |
|---|---:|---:|
| Published experiment, including refitting | +0.226 | +0.325 |
| Fixed fitted model, input change only | **+0.116** | **+0.073** |
| Fixed-model response as a fraction of the shock | **23.1%** | **14.5%** |

The response declines at every horizon in the corrected experiment. The reported backwards
pattern is not evidence that the fitted model increasingly weights recent performance with
distance. It is produced by a different experiment that also re-estimates the model.

These sensitivity figures average the seven page-level mean responses, matching the runner's
aggregation. The shock experiment retains finite forecasts for all 6,916 requested subjects at
each horizon; no realized outcomes are required, so h5 also includes the 2021 page here.
Deleting the oldest season leaves only 6,124 finite responses out of 6,916 requested subjects.
The audit records that loss, and the deletion experiment must not be described as a complete
same-population response. Its available-response mean moves from -0.020 at h0 to -0.008 at h5.

Required: use a frozen fitted object for the input-sensitivity test; report a separately named
refit sensitivity if that is also useful. Carry counts for subjects lost or retained when
testing missing history. A rising sensitivity alone is not proof of a model bug: its source
must be identified in the regression and aging walk.

### 2. P2: residual diagnostics use the wrong calibration year

After `Harness.run(banded)` finishes, `banded.spread_` belongs to the last page, 2021.
Reports 5 and 6 in `run_uncertainty.py` use that object to scale residuals from every development
page. They describe this as dividing each miss by the range it was given, which is not what
the code does. Earlier forecasts received different fitted scales and error distributions.

Captured each actual page's calibrator while running the unmodified calculations. Recomputed
the played-season h5 residual diagnostics using those original scales:

| Group | Played rows | Published median / 95th | Corrected median / 95th |
|---|---:|---:|---:|
| 3+ trailing WAR | 151 | +0.44 / +3.41 | **+0.51 / +3.64** |
| Age 22 or younger | 389 | +0.18 / +3.65 | **+0.17 / +3.55** |

Units are residual divided by fitted scale, not WAR. Using each page's own fitted 95th
percentile, 16.6% of these played star observations and 11.1% of played young observations exceed
that threshold. The intended tail fraction is 5%. The concern about unexpectedly high outcomes
therefore survives the correction.

The stated **1.045 width ratio** reproduces numerically, but it is not an isolated estimate of
in-sample optimism. It compares different year/sample mixtures using the last calibrator.
Comparing each page with its own fitted shape gives ratios from **0.942 to 1.114**. These too
are descriptive differences, not an experiment isolating overfitting. Do not apply a 4.5%
inflation as an estimated correction on this evidence.

The stronger claim that forecast bias explains "most" of the coverage problem is not established
by medians and tail quantiles. The diagnostic conditions on playing, while the coverage table
includes non-participation and its estimated probability. A proper attribution also needs that
component assessed and a controlled comparison of location and spread adjustments. Current
evidence supports investigating low forecasts and upper-tail undercoverage together.

### 3. P2: the predictive distribution does not preserve the stated expectation

`SpreadModel._fit_shape()` retains the empirical standardized residuals without centering them.
Their mean is positive on every development page. The conditional distribution is therefore
`mu + sigma * Z`, with expectation `mu + sigma * E[Z]`, not `mu`.

Including participation, its mean exceeds `rate_82 * gp_share * p_play` by **0.0374 WAR on
average** and up to **0.2265 WAR** over the 40,510 scored rows. The independent audit integrates
the piecewise-linear residual quantile function to calculate its mean.

Preserving the point-forecast columns does not preserve the distribution's expectation. The
zero-spread test passes because it replaces the fitted residual shape with zeros; it does not
test this nonzero-uncertainty discrepancy. Before using this distribution for simulated career
paths, choose explicitly whether the residual mean is a bias correction to the point forecast
or whether the error distribution should preserve that forecast's mean. Then test agreement
between the distribution's mean and the reported expectation, and reassess coverage.

## What the findings do and do not change

The coverage table is computed from the bounds returned on each page, so the reporting bug in
finding 2 does not invalidate its numbers. The weak star/young coverage is reproduced evidence.
The new work supplies marginal distributions for season-total WAR, not a joint distribution
over rate, games, participation and multiple career seasons. It is not yet a contract-value
simulation. The prior trade-date, control-year, goalie and dollar-reconciliation work remains.

The report's certainty exceeds the diagnostic evidence when it says horizon pooling "holds,"
that 4.5% is measured optimism, or that most undercoverage has been assigned to the forecast.
These should be written as findings with their measured samples and remaining alternatives.

## Reproduction

`50_REBUILD/code/review_uncertainty.py --candidate-root <checkout> --mode uncertainty` runs
the published uncertainty report and captures its calibrators for the independent calculations.
Mode `leakage` runs the published battery and the frozen-model sensitivity; mode `guard` runs
the export reproduction guard in its own scratch directory. The candidate repair suite was
also run with the same source paths and local production workbook.

Logs and aggregate JSON stay ignored in `50_REBUILD/output/`. No candidate implementation was
changed or merged, no production output was rewritten, and no reserved evaluation was unsealed.
