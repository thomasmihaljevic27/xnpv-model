# Goalie participation review

Reviewed 2026-09-22. Candidate `6e9286e`, isolated from main at
`50_REBUILD/output/goalie_participation_review`.

## Decision

Keep the participation prototype, but leave this review open. It improves forecast
accuracy in the independent run. The contract-price integration uses the wrong date
for contract status, check 34 does not test all the behavior it claims to protect,
and the report rules out participation as a source of bias without establishing it.
Repair and rerun the price comparison before using its results. Earlier closures
stand. No candidate merge or model adoption in this review.

## 1. Contract participation uses the page date instead of the signing date (P1)

`run_goalie_price_line.py:83-105` fits and caches participation by season page and
player. `goalie_forecasts` calls it at line 130 without passing the contract's
signing date. The shared participation model's `_rows` obtains contract state at
1 July of the anchor year. That date is appropriate for the annual forecast harness;
it is not the information date of every contract being priced.

A contract signed after 1 July can therefore be forecast as though the new deal
were not yet known. For contract 4518, Jon Gillies, signed 2018-07-16:

| Forecast season | Current probability | With contract status at signing |
| --- | ---: | ---: |
| First | 0.4443 | 0.9272 |
| Second | 0.4117 | 0.9950 |

I held the training sample, fitted coefficients, performance history and all other
predictors fixed. Only the date used for `under_contract` and `contract_unknown`
changed. Probabilities change for **92 of 205** forecast-attached development
contracts. This is a real input error in the new price comparison, not evidence
that the corrected probabilities themselves are calibrated.

There are also 28 contracts signed before their page's July date. I found no
intervening future contract in this sample that changed their applicable coverage,
but the API lacks the date boundary needed to prevent one. Neither later contracts
nor an arbitrary earlier July snapshot should determine status at signing.

**Required repair:** retain historical dates on training rows; pass the actual
signing date when constructing prediction features. Include that date in prediction
cache keys, test earlier and later signings on the same page, and prove that adding
a contract signed after the decision cannot alter an earlier prediction. Rerun all
price specifications on matching contract IDs.

## 2. Check 34 does not exercise the promised forecast dating (P2)

At `repair_checks.py:1442-1450`, future GP and share values are altered, then those
rows are removed before either share fit receives them. The two fits receive the
same table. The participation model is fitted only once, and its predictions are
never exercised by this check.

Replacing `ParticipationModel.predict` with a constant 0.999 still passes check 34.
Its base-rate assertion is useful for the missing-age selection defect, but it does
not guard the new predictor or its signing-date consumer. The skater comparison
also compares two calls to the new function, rather than a saved pre-change output.
The small anchor code diff preserves the default by inspection; that is distinct
from a historical byte comparison.

My independent test drives `Both.fit/predict` through the information-set builder
before and after future GP, share and WAR changes. The current implementation gives
exactly the same participation and share forecasts on page 2019. This is positive
evidence for the annual runner; it does not make check 34 comprehensive or cover
the separate contract-date defect above.

**Required repair:** test the actual annual and contract prediction paths, assert
matching forecast grids, and demonstrate that a deliberate future-reading defect
fails. Keep the existing selection check as a separate guard.

## 3. The remaining WAR bias has not been assigned to a cause (P2)

`Goalie_Participation.md:126-132` says the remaining bias comes from somewhere other
than participation. An improved average probability and little change in overall
WAR bias cannot establish that. The probabilities are still imperfect, and errors
for high-production and low-production goalies receive different weights in WAR.

An exact accounting identity illustrates the distinction. Let q be the conditional
season forecast and y indicate whether the goalie appeared:

    forecast error = (p - y) * q + y * (q - actual WAR)

In this rerun, the first term averages -0.0343 WAR under flat participation and
-0.0161 under the new model. The second averages +0.1347 in both, because conditional
production is unchanged. They add to the observed biases +0.1004 and +0.1186.
This is an accounting identity using outcomes, not a causal attribution or an
identified estimate of what repairing participation would achieve. It does show
why participation accuracy and WAR bias need not move together.

**Required correction:** state that this replacement improves prediction error but
does not eliminate pooled WAR bias. Retain uncertainty about its causes. The earlier
+.167 calculation remains an illustration, as already agreed in the closed review.

## Reproduction and limits

**Full suite: 34 passed, 0 skipped, 0 failed.** Every arm answers 3,683 scored cells.
The source panel has 1,560 rows and 280 goalies. The direction of the main gain and
the share-model result reproduce, but some exact participation figures do not:

| Metric | Report | Independent run |
| --- | ---: | ---: |
| Mean participation forecast | 0.580 | 0.590 |
| Observed participation | 0.553 | 0.553 |
| Participation Brier score | 0.2075 | 0.2101 |
| Participation plus trailing-share WAR MAE | 1.437 | 1.446 |
| Its WAR bias | +0.104 | +0.119 |
| Both models WAR MAE | 1.499 | 1.513 |

The difference is concentrated at horizon two: predicted participation is 0.633
rather than 0.577. The independent Brier and season-WAR comparisons still win in
100% of the runner's career resamples. A targeted fit audit captured 32 executed
regularized logistic fits, all reporting convergence. Turning automatic coefficient
trimming off did not materially change predictions; that probe does not explain
the discrepancy. Reconcile input/package versions and per-page fits before claiming
exact reproduction. No cause is established here.

Share error reproduces: 0.1801 to 0.1686. The 2,035 played observations are forecast
cells across pages and horizons, covering 668 distinct goalie-seasons. Whole-career
resampling retains this repeated structure. At horizon five Brier improves from
0.2965 to 0.2359; the report's blanket statement that horizons three to five roughly
tie the flat rate is too broad for its own table.

Before repairing the date defect, my price rerun gives MAE 0.009399 without goalie
terms, 0.007304 with level only and 0.007259 with level and slope, all on 174 contracts.
The last-fit UFA whole-path ratio is still approximately 0.75. These are reproducible
outputs of the current implementation, not approved price-comparison conclusions.

The mean forecast change is +0.0008 WAR in my run, but mean absolute change is
0.2543 and the largest is 1.2353 across 205 contracts. The 10th and 90th percentiles
are -0.4652 and +0.4357. This supports sensitivity to a different forecast and its
ranking of goalies; it does not establish numerical instability under a tiny input
perturbation. The report does acknowledge reordering, and should lead with its size.

The missing-age selection is a sound reason not to fit only age-covered goalies.
A separate rate forecast is a reasonable next experiment, but production's season
projector is not a previously validated per-game ability forecast. Rate, workload
and participation must be assessed jointly before adoption. The source's observed
minimum is two games; appearances missing from this source remain outside the
measured participation event. D7 and the goalie price specification stay provisional.

## Evidence and scope

`50_REBUILD/code/review_goalie_participation.py` supports setup, full runner, full
suite, price rerun, independent audit, fit audit and signing-date comparison.
Generated logs and JSON use the `goalie_participation_` prefix under
`50_REBUILD/output/`; no source data or canonical production output was changed.
Review documents stay under `50_REBUILD/docs/`; project state stays in `00_STATE/`.
