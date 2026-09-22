# Goalie control years and dollar scoring: independent review

Reviewed 2026-09-22. Candidate `088546f`, isolated from main in
`50_REBUILD/output/goalie_control_review`. Nothing merged or adopted.

## Decision

The runner and its two shared repairs work. The dollar evaluation needs two
corrections before this stage closes. Neither finding calls for a new forecast or
an immediate change to the simulated spread. Keep production as the provisional
default and the rate forecast as the sensitivity while correcting the evaluation.

## What reproduced

- Full suite: **39 passed, no skips or failures**.
- Restoring the old replay dating fails check 38. Restoring the old persistence
  search and subsequent clipping fails check 39. Both mutations were made only
  in the review process, without editing the candidate.
- 137 contracts simulated per forecast, 133 completed terms scored, and 21 of
  74 contracts owning control years reaching the simulation.
- Informed control value: $1.072M production, $1.162M rate. Production-style
  point rule: $0.129M and $0.063M. The information-only increments are $0.036M
  and $0.052M. Control-value rank correlation is 0.908.
- Production point/simulation RMSE: $6.8587M/$6.8822M; rate:
  $7.0029M/$6.9536M. These reproduce the reported calculation, with immaterial
  last-digit differences. They do not establish a fair cross-forecast comparison.

The replay now reads the requested historical page. The persistence search
evaluates the constrained weights it returns. Those repairs can stand.

## 1. Score both forecasts against the same realised-dollar target [P2]

`run_goalie_control_years.py:317` fits a separate price line for each forecast.
Lines 357-360 then apply that forecast's line to realised WAR. Lines 432-447
compare the resulting errors as though the outcome were common.

It is legitimate to investigate separate price fits. It is not a forecast
accuracy comparison on one dollar target when the forecast also changes the
target. Across the same 133 completed contracts, the two realised-dollar targets
differ by **$0.514M on average in absolute value**, with a **$5.565M maximum**.

The review retained the drawn WAR paths and repriced both forecasts and actual
WAR with each reference line in turn. Dates, contract rows, costs and discount
factors remain fixed within each comparison. RMSE, $M:

| Common reference price line | Production point | Rate point | Production simulation | Rate simulation | Rate simulation wins in career resamples |
|---|---:|---:|---:|---:|---:|
| Production forecast's line | 6.859 | 7.022 | 6.882 | 6.923 | 44.4% |
| Rate forecast's line | 6.877 | 7.003 | 6.923 | 6.954 | 46.3% |

Production retains the lower sample RMSE. Its reported 64% bootstrap advantage
becomes **55.6% or 53.7%**, depending on the shared reference currency. This
supports retaining the provisional default, not a dollar-performance victory.
The point-versus-simulation comparisons within one forecast already use a common
target and are not invalidated by this finding.

**Required correction:** declare a common scoring currency before comparing
forecasts; optionally report the other currency as a sensitivity. Apply it to
both predictions and the realised path. Assert that the realised-dollar target
is identical by contract across arms. Preserve each arm's own-price valuation as
a separate sensitivity rather than relabelling it as common-target scoring.

## 2. Account for the floor and non-participation before diagnosing spread [P2]

Lines 419-421 say 10th-to-90th percentile coverage should be near 80% if the
spread is right. That is not generally true when the distribution puts a lump of
probability at one value. Here the salary floor puts many dollar paths at exactly
the same lower value. Including the lower endpoint includes the entire lump.
The season distribution has the same issue at zero from non-participation.

The audit counted the runner's own simulated dollar draws inside each contract's
reported interval, then averaged over the identical 133-contract scoring sample:

| Forecast | Interval | Coverage on the model's own draws | Coverage on actual outcomes | Excess over model benchmark |
|---|---|---:|---:|---:|
| Production | 10th-90th percentiles | 89.55% | 93.23% | 3.68 percentage points |
| Rate | 10th-90th percentiles | 89.34% | 91.73% | 2.39 percentage points |
| Production | 25th-75th percentiles | 71.49% | 78.95% | 7.46 percentage points |
| Rate | 25th-75th percentiles | 70.14% | 73.68% | 3.55 percentage points |

The model-draw calculation measures the effect of endpoint masses. It is not an
independent validation of the model. It shows why 93% versus 80% alone does not
establish that the spread is too wide.

Using 2,000 career resamples, the excess-coverage 95% percentile intervals are:
production 80% interval **-0.46 to +7.42 points**; rate 80% **-1.72 to +6.39**;
production 50% **+1.25 to +13.21**; rate 50% **-2.97 to +9.75**. These are
descriptive development-sample intervals with the fitted model and draws held
fixed. The production central interval still merits investigation; this audit
does not declare the bands calibrated.

Likewise, 66% coverage among played seasons does not establish a narrow
conditional band when the interval being tested was built for the unconditional
mixture of playing and not playing. A correctly specified mixture need not have
80% coverage in each of those two groups.

**Required correction:** replace the categorical diagnosis in the runner, report
and state records with an evaluation that accounts for point masses. Compare
observed tail frequencies with their model-implied probabilities, or use a
distribution calibration test that handles ties. Test conditional performance
with conditional intervals. Add a correctly specified floor/zero-mass example
that would fail a naive nominal-coverage check. Establish which component is
miscalibrated before shrinking its spread or dismissing its simulated premium.

## Scope and plan

This is useful progress on Phase 5, not completion of the full plan. The goalie
branch uses the shared walk-away policies; their approximate stopping design,
average-salary offer approximation, snapshot eligibility and selected population
remain limitations. The report discloses eight priced contracts with eligibility
earlier than the age-only rule; that disclosure is not independent verification
of signing-date eligibility. No new eligibility correction is imposed by this
review. The joint rate/games/participation design and the eventual declared
back-test remain outstanding.

The full review suite and new goalie runner were rerun. The claim that every
older skater output is unchanged was not independently reproduced by rerunning
both complete skater valuation runners in this review. Source data and canonical
production outputs were not written.

## Reproduction

Review script: `50_REBUILD/code/review_goalie_control.py`. Run `setup`, `run`,
`checks`, `mutants`, `audit`, then `scores` with the review Python environment.
The script points to the isolated candidate and generated production-adapter
fixtures. `audit` captures the actual paths used by the runner and reprices them;
`scores` computes paired career resamples and coverage differences.

Generated evidence is ignored under `50_REBUILD/output/`: the
`goalie_control_review_run.log`, `goalie_control_review_checks.log`,
`goalie_control_mutants.log`, `goalie_control_audit.log`,
`goalie_control_audit.csv` and `goalie_control_scores.log` files.
