# Goalie branch review

Reviewed `08731eb`, including the RFA corrections in `b36a738`, on 2026-09-17.
All work ran in an isolated checkout. Production code and canonical outputs were
unchanged.

## Decision

The RFA reporting and draw corrections are verified within the previously agreed
prototype scope. The goalie panel runs, and the reported forecast table reproduces.
The goalie forecast comparison needs three corrections before it can support the
proposed forecast choice or the claims about production and aging.

The most consequential correction changes the headline: production's actual
projector, evaluated with the same participation estimator, has MAE 1.48784;
the proposed fitted-weight rule has MAE 1.49123. The small difference is
inconclusive. The claimed improvement over production is not established.

## Reproduction

- Full suite: **30 passed, 0 skipped, 0 failed**.
- Panel: 1,560 goalie-seasons, 280 goalies, age coverage 76.09%.
- Forecast run: six rules, 3,683 scored cells each, 22,098 output rows.
- The six published pooled MAEs and biases reproduce to displayed precision.
- RFA run: 398 contracts; the 356 unchanged eligibility windows return identical
  values. Salary coverage is 339, split 221 within 1%, 110 above, and 8 below.
  The revised age-only difference still rounds to $0.026M and is described as a
  sensitivity. The stopping-policy approximation is now disclosed.

## 1. The production-labelled candidate does not implement production [P1]

`run_goalie_bakeoff.py:189-206` forecasts from qualifying seasons with at least
10 games. Its trailing helper at lines 62-93 uses whichever two observations
exist within the three-year window, and the rule always shrinks toward 2.189.

Production's `GoalieProjector.shrunk_projection`, in `20_CODE/contract_npv.py`,
does something different:

- It retains low-games seasons in the trailing calculation.
- Its 60/40 branch specifically requires the immediately preceding two seasons.
  A gap does not turn any two observations into that branch.
- When the most recent season is absent, it searches backward for an older
  anchor and shrinks that population toward **0.650**, rather than 2.189.

The independent audit executes the production class extracted from the candidate
source, using the source panel's aggregated and prorated observations. It recovers
the league target from the regenerated production spine. This avoids copying the
forecast logic into another implementation. It keeps the bake-off's participation
and scoring unchanged, so this tests the forecast component rather than the full
production NPV or hazard chain.

Across 629 goalie/page anchors, **209 differ** from the production-labelled
candidate. The largest difference is **1.88022 WAR**; 117 anchors use production's
stale-history branch. For example, Anders Nilsson on page 2015 receives 0.42627
from production versus 1.42673 from the candidate labelled production.

| Forecast through the shared participation estimator | MAE | Bias |
|---|---:|---:|
| Candidate labelled production | 1.58195 | +0.21778 |
| Actual production projector | **1.48784** | +0.10062 |
| Fitted-weight candidate | 1.49123 | +0.03569 |

The fitted candidate minus actual production MAE is +0.00339. A correctly paired
goalie-cluster bootstrap gives a 95% interval of **[-0.01516, +0.02206]**, and the
fitted candidate wins 36.8% of 2,000 resamples. Neither rule wins decisively.

Required correction: add parity checks against the actual projector, including
low-games and missing-prior cases. Either use that projector as the benchmark or
label the current rule as a simplified challenger. Re-run comparisons before
claiming the production constant has aged or choosing a replacement from this
table. A rolling average improves the simplified rule; that result alone does not
identify why production differs.

## 2. Bootstrap pairing omits the forecast page [P2]

`run_goalie_bakeoff.py:349-367` merges on goalie and horizon, omitting `page`.
A goalie appearing on several pages consequently matches each page in one model
to all pages in the other. **3,683 intended pairs become 19,853 rows.** This also
changes the weighting toward goalies with more forecast pages.

Correct pairing uses `(career_key, page, h)` and one-to-one merge validation.
Resampling should then retain the complete set of those paired rows for each
sampled goalie. The existing harness comparison already uses the full key.

| Challenger versus the original labelled baseline | Reported win share | Correct pairing |
|---|---:|---:|
| League average | 3% | **0.1%** |
| Workload weighting | 78% | **37.5%** |
| Page-specific average | 100% | 100% |
| Fitted weight | 100% | 100% |
| Common drift labelled aging | 0% | 0% |

The corrected workload MAE-difference interval is [-0.01488, +0.02138], consistent
with an inconclusive comparison. The raw pooled MAEs are unaffected because the
runner computes them before the incorrect bootstrap join.

Required correction: retain the page in the pairing, reject duplicate or missing
cells, and test the paired row count on goalies appearing on multiple pages.

## 3. The aging conclusion exceeds what the candidate tests [P2]

At `run_goalie_bakeoff.py:334`, `np.polyfit(x, y, 1)[1]` selects the fitted
**intercept**, discarding the age slope. The prediction at lines 336-342 then adds
this same annual change to every goalie, regardless of age. This tests a common
drift in season WAR, not an age-dependent forecast.

On page 2021, adding 20 years to all subjects' ages changes predictions by
**exactly zero**. Goalies without an age also receive the adjustment, contrary
to the runner's statement that they retain a flat projection.

The reported +0.117 to -0.106 sign change describes the common fitted drift at
the training sample's pivot age. It does not demonstrate that the panel cannot
identify aging, nor establish that survivor selection caused the sign change.
Selection into consecutive played seasons is a relevant limitation, but this
comparison does not separate it from other explanations. The losing rule also
extends the workload challenger, rather than the strongest flat candidate.

Required correction: label the current candidate as common drift and narrow the
conclusion to its measured performance. If an aging claim is needed, implement
an age-dependent challenger with an explicit missing-age rule and compare it
against the corresponding flat forecast. A sign change alone is not a test of
identification or proof of selection bias.

## Smaller fitting qualification

The fitted-weight calculation estimates an unrestricted regression slope, then
replaces the fitted intercept with `(1 - keep) * league_average`. That is not
exactly the least-squares fit for the stated fixed-target shrinkage formula.
On the same 679 training pairs, the reported slope is 0.427574; minimizing squared
error for that fixed target gives 0.420547. Training MSE changes only from
6.089799 to 6.089607. This is small in this run, but the fitting description should
match the implemented objective. The 0.43 figure is the final development page's
estimate, not one common weight used on all pages.

## Tests and next step

The 30 passing checks cover panel arithmetic, the fit-date assertion, shared
participation, and the inherited rebuild checks. They do not establish production
forecast parity, correct bootstrap pairing, or that predictions respond to age.
Those are the missing checks demonstrated above.

Keep the panel and the six-rule experiment. Correct the benchmark and comparison
before carrying a selected goalie forecast into the price line. Aging can remain
an explicitly untested extension after the common-drift claims are corrected.
RFA prototype work does not need reopening; its established adoption limitations
remain. No confirmatory forecast pages were opened in this review.

Reproduction: `50_REBUILD/code/review_goalie_branch.py`, modes `setup`, `run`,
`checks`, `audit`, and `rfa`. Generated logs and audit evidence are ignored under
`50_REBUILD/output/goalie_review_*`; the actual-projector scored rows are in
`goalie_actual_projector_scored.csv` in that same output directory.
