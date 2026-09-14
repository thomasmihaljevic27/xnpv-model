# Ground-up player-model review - 2026-09-14

Thomas explicitly invited reconsideration of all assumptions and locked decisions for market pricing, current form, aging and future performance. These are recommendations, not adopted changes. Reviewed state, implementing code, recent experiment reports and primary research; no statistical rerun or production modification.

## Recommended rebuild

1. Information-at-date data layer: stable player IDs, audited birthdates, signing dates distinct from contract starts, publication dates and historical training cutoffs. Share loaders. Preserve source revisions; acknowledge missing historical vendor vintages.
2. Estimate current ability from component performance, exposure and context, with evidence-dependent shrinkage and learned recency weights. Separate games availability, playing time and performance rates. Use a simple three-season age-aware forecast as the benchmark. Update at trade dates using only admissible pre-trade observations.
3. Estimate aging inside the forecast with smooth age effects, player differences and explicit selection into NHL opportunity. Start pooled; estimate individual deviations only with evidence. Keep comparables as a challenger and explanation rather than a required multiplier.
4. Forecast joint distributions of rate, games, deployment and NHL participation, allowing absence and return. Integrate participation exactly once and score zeros. Keep goalies separate, using shot exposure and workload.
5. Fit a distinct signing-date contract-market model on expected production across the whole deal. Include term, rights, availability and market conditions as candidates. Separate salary prediction from production valuation. Use a declared common reference market for production dollars and model restricted rights on the cost/control side, with alternative-market sensitivities.
6. Fit and tune the entire chain historically. Compare models on fixed performance targets and a common dollar yardstick. Report calibration by horizon, age, level, position and experience. Repeated inspection has consumed much of the existing holdout's independence.

## Code-grounded findings and qualifications

- `skater_forward_projection.anchor()` returns the raw 60/40 season-total blend. `ratio_path()` forces the first-season multiplier to one, preventing the stabilized curve level from replacing that starting forecast. Shrinkage still affects later ratios.
- `aging_curve.py` fits scaling, bandwidth, comparable outcomes and global curves on its full loaded history. Direct self-exclusion does not remove the target from global quantities. Recent rolling experiments did not refit the aging curve historically.
- The coverage audit finds only six eligible age-19 defencemen because comparables require two consecutive 20+ GP seasons. Admit short histories with uncertainty rather than an invented zero trend or automatic flat forecast.
- `anchor_shrink_test.rate_sample()` and its caller `market_line_search.py` use contract start year for performance inputs and evaluation splits. Early extensions can therefore use information unavailable when signed. A signing-date audit must quantify exposure; the NPV chain's separate signing-date guard does not fix this sample builder.
- `_proj_sd_war(0)` is zero; uncertainty beyond year three is held flat at the year-three estimate. Replace these placeholders with calibrated forecast distributions. A legal minimum wage does not by itself establish a minimum production value.
- The September 14 exit-population finding supports refitting participation for the appropriate contract state. That state must be known at the valuation date, not selected using later signings. Distinguish temporary absence from permanent exit.
- New-signing term prices cannot automatically be applied to years remaining on existing deals without validation.

Existing results are promising candidate evidence: the age-aware three-season rule reduced WAR error 6.4% on 2020-2025 pages; the market search reported $1.235M to $0.755M cap-hit MAE on 842 contracts in 2023-2025 at a $95.5M cap. Neither establishes fully historical whole-chain performance.

Games and term coefficients are conditional associations, not isolated causal prices. Lower error after redefining the dollar currency is not better hockey forecasting. The cap-hit-informed diagnostic is not a ceiling for statistics-only accuracy or an identified private-information measure. Separate Game Value outcomes offer triangulation, not proof that every identification concern is resolved.

Build order: identity/date repair and evaluation harness; simple calibrated forecast; rate/workload/participation model; richer aging challengers; signing-date market model; joint uncertainty through contract and control years. Judge changes by predictive evidence, not aggregate NPV neutrality.

## Primary references

- Schuckers, Lopez and Macdonald, *What does not get observed can be used to make age curves stronger*: https://arxiv.org/abs/2110.14017 . Selection concerns both who plays and when they are observed; player-skill and imputation approaches are evaluated in simulations.
- Cavan, Cao and Swartz, *NHL Aging Curves using Functional Principal Component Analysis*: https://www.sfu.ca/~tswartz/papers/aging.pdf . Individual smooth curves and selection-aware methodology provide a relevant challenger, not a proven winner for this dataset.
