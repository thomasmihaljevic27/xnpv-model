# Goalie forecast review closure

Reviewed `e42f57c` on 2026-09-17 in the isolated `goalie_repair_review` checkout.

## Decision

The three preceding review findings are closed. Proceed to the goalie price-line
prototype with production's projector as the provisional forecast. This is a
development comparison; it does not establish that production is the best possible
forecast, complete the participation model, or authorize adoption.

## Verification

- The full suite returns **32 passed, 0 skipped, 0 failed**.
- The runner answers 3,683 cells per candidate across seven candidates, producing
  25,781 scored rows. The published table and bootstrap percentages reproduce.
- The imported production forecast matches the independent source-class calculation
  from the preceding review on all 3,683 scored cells. The largest error difference
  is **1.78e-15 WAR**, which is floating-point precision.
- Replacing all source WAR observations from each forecast page onward with 500
  changes forecasts by **exactly zero** over 629 goalie/page subjects.
- The bootstrap now pairs `(career_key, page, h)` and requires a one-to-one merge.
- Age now affects predictions. A 20-year age intervention changes out-year forecasts;
  check 32 also verifies that it leaves h0 unchanged. The fitted slope and drift are
  reported separately, and the previous identification claim is withdrawn.
- Independently reintroduced four defects: a non-production factory, the simplified
  rule substituted for the production candidate, an omitted page key, and a predictor
  that ignores age. Checks 31-32 reject all four.

The future-observation test establishes the seasonal lookup's dating. It does not
establish the historical availability of the locked production calibration constants.
Keep that distinction when moving from a current-rule benchmark to a historical
valuation protocol.

## Reproduced forecast comparison

| Rule | MAE, WAR | Mean error, WAR |
|---|---:|---:|
| Production projector | 1.48784 | +0.10062 |
| Simplified cascade | 1.58195 | +0.21778 |
| Simplified cascade with page average | 1.51071 | +0.04478 |
| Fitted-weight candidate | 1.49123 | +0.03569 |
| Workload weighting | 1.58528 | +0.16410 |
| Age-slope challenger | 1.552, rounded | +0.034, rounded |

The runner's fitted-weight win share is 34%, as reported. The independent bootstrap
uses a different deterministic ordering of goalie clusters and gives 36.8%; both
describe an inconclusive comparison. The independent MAE-difference interval for
fitted weight minus production is **[-0.01516, +0.02206]**, around +0.00339 WAR.
Production is the lowest pooled-MAE rule in this run. It is not a demonstrated
winner over the fitted-weight rule.

## Carry bias as a diagnostic, not a price adjustment

The **+0.10062 WAR** mean error reproduces. Calling it an established persistent
defect requiring a downstream correction is stronger than this evidence supports.
A goalie-cluster bootstrap of that mean gives a 95% interval of
**[-0.12155, +0.31314] WAR**. The interval includes zero. This does not prove that
the forecast is unbiased; it limits the certainty of the claim.

The scored prediction includes the shared participation estimator. Its average
predicted participation is **0.64098**, versus **0.55254** observed across the scored
cells. Thus the mean WAR error cannot be assigned solely to the production projector.
Holding participation constant across candidates makes relative comparisons useful;
it does not remove participation error from either candidate's absolute bias.

Retain the observed bias, examine it alongside the forthcoming participation model,
and evaluate any correction on the declared development protocol. Do not alter the
dollar price line solely to cancel this pooled WAR error. That could conceal a
forecast error without fixing it. This qualification does not block the price-line
prototype.

## Remaining scope

The aging result concerns this challenger, fitted on consecutive observed seasons.
Missing ages are imputed to the pivot age in its prediction. Its negative slopes do
not establish a causal aging relationship or solve survivor selection. The smaller
fixed-target shrinkage fitting discrepancy documented in the previous review remains
in the unselected challenger and does not block use of the production benchmark.

Goalie participation, the control-year gate, dollar scoring, and the declared
back-test remain open. Earlier RFA, simulator, and reconciliation review closures
retain their stated limits.

## Reproduction

`50_REBUILD/code/review_goalie_repairs.py` provides `setup`, `run`, `checks`,
`audit`, and `mutations` modes. Evidence is ignored under
`50_REBUILD/output/goalie_repair_*`. Source inputs were read-only; canonical
production outputs and model code were unchanged. No candidate merge or adoption
occurred, and no confirmatory forecast pages were opened.
