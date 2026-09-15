# Player-model rebuild: proposed execution plan for Claude

Date: 2026-09-14. Status: proposal for Thomas to compare and select. Claude is the intended builder. This document does not authorize implementation, adopt new decisions, or reorder the active work queue.

## 1. Objective and recommended decisions

Build a forecast of each player's contribution from the information available on the decision date. Convert it into an explicit, consistent production-value currency and compare that value with the costs and rights attached to the asset. The model must work at signings and trade dates, not only at season starts.

Recommended choices if this plan is selected:

- Component-specific, exposure-aware forecasting is the lead candidate. A calibrated three-season total-WAR model is the mandatory benchmark. The candidate becomes production only after matched historical evaluation.
- Model performance rate, deployment, availability and NHL participation distinctly, while preserving their dependence. Estimate one coherent expected total; do not multiply an already unconditional forecast by another survival probability.
- Use a smooth additive age-by-position model first. Allow a level-by-age effect based on estimated ability. Comparables are a challenger and explanation; richer individual curves must earn their complexity.
- Keep contract-price prediction separate from production valuation. Term and rights enter contract-price prediction. The primary production currency prices annual contribution using a common rights-neutral benchmark without adding the asset's own term premium to gross production value. Term-inclusive valuation is a required sensitivity, not the primary result.
- Use shared market estimation rather than a standalone open-market-star curve. Standardizing a pooled model to a reference market at the top is an extrapolation and must be labelled.
- Forecast and price the full contracted/control horizon with uncertainty. Preserve coherent absence, return, renewal and expiry paths.
- Use dollar surplus differences as the primary trade comparison. A gross-value-normalized difference is secondary, with explicit handling of a zero or nonpositive scaling quantity.

This production-currency choice measures output-based surplus. It does not claim an equivalent star can actually be hired for one year. A term-matched contract-market comparison answers a second, legitimate question: how the acquired contract compares with similarly structured market deals. Both should be available, with the primary estimand fixed before examining trade results.

## 2. What stays, and what is reopened

Preserve the source data, Python/SQLite stack, flat folder structure, existing live filenames, hash checks, contract-cost and retention accounting where verified, D28's signed-extension logic, cap-share reporting, separate goalie treatment and Game Value as a secondary outcome. Retain the censored straight salary equation with position slope as the initial market specification. Curvature was tested previously; a single optional retest after input changes is sufficient.

Preserve the purpose of reproduction guards: first reproduce the old model on a frozen baseline. Do not preserve old numerical coefficients or the first-season Layer 1 identity as acceptance requirements for the new model. Once a changed specification passes, replace those obsolete expected values deliberately and record why.

Reopen the raw 60/40 anchor, universal shrinkage, ratio aging, flat fallbacks for sparse history, participation population, control-year gates, static market coefficients, uncertainty placeholders and surplus ratios. Keep the minimum-value floor as a documented provisional convention during forecast development; measure its effect under a signed/unfloored sensitivity before the final currency lock. Simulation alone cannot justify that floor economically.

## 3. Phase A - Reproducible baseline and historical information

### Build

1. Capture the baseline commit, input hashes, output hashes and coverage. Confirm the contract export's observation end and quantify missing later signings. Historical tests use complete historical slices; current valuations require current contract coverage.
2. Save reproducible versions of Claude's signing-date and component diagnostics. Record exact filtering, definitions, denominators and outcomes. The supplied 85/616/1,648 signing counts and 7.1% component improvement are Claude-reported until these are reproduced.
3. Create one audited player-ID/birthdate mapping and one shared season loader. Resolve collisions only on evidence; quarantine unresolved identities and report coverage. Never infer identity from fuzzy names alone.
4. Separate event date, contract signing date, contract start, data publication/availability date and outcome window. Use the actual regular-season completion dates, including unusual schedules. Conservatively exclude same-day observations without known ordering. Completed-season vendor WAR is usable only after it was available, not automatically at the final horn.
5. Build two historical datasets: signing observations for salary modelling and trade-date/season-start observations for performance and valuation. An early extension must not see the completed intervening season. Interim statistics may enter only through the in-season updater.
6. Date the cap-information schedule by announcement. Use announced future ranges only after announcement and extrapolate beyond the known schedule under an explicit common assumption. Separate dollar/cap conversion from any economic time discount.

### Deliverables and gate

An audit report and machine-readable exclusion/exposure tables. Every feature has a documented availability rule. In a meaningful automated test, removing all observations after a decision date must leave its forecast unchanged. Test selected early extensions, deadline trades, short seasons, identity collisions and signed extension chains.

Current-vintage WAR cannot be turned into genuinely archived WAR by filtering rows. Label historical results as reconstructed where vintage archives do not exist. Retain this limitation in the final report.

## 4. Phase B - Fix the evaluation before comparing forecasts

Register the candidate set and scoring rule before examining new results. Fit preprocessing, priors, recency weights, aging, participation and prices within each training window. Training examples are usable only once their outcome windows have completed. In particular, a three-year outcome beginning before the cutoff can still extend past it.

Use rolling historical evaluation with model tuning confined to earlier inner windows. Use the same eligible observations for head-to-head comparisons, and separately report each model's full coverage. Preserve short histories, no-history routing and zero-NHL seasons. Do not select scoring rows by whether players subsequently appeared. Cluster uncertainty estimates by player and examine stability across calendar periods; repeated overlapping horizons are not independent observations.

Primary forecast objectives: next-season total WAR MAE and three-season cumulative WAR MAE. Report horizon-specific bias, RMSE, games error, participation calibration and interval coverage. Show splits by F/D/G, age, forecast quality, experience, stale history and availability. Five-year scoring uses only completed windows; outstanding contract years are not zeros.

Historical 2020-2025 results are development evidence after repeated inspection. Nested historical testing reduces selection optimism but does not create a never-seen final test. Freeze dated future predictions for prospective evaluation; the thesis can proceed with honestly labelled historical evidence.

Promote added complexity when paired comparisons show a stable useful improvement across periods, without a recurring material subgroup failure. When the gain is within sampling uncertainty, choose the simpler model. Do not choose on NPV level or on whether stars look appropriately valued.

Deliverable: a reusable evaluation report with one row per candidate/horizon/population, outcome definitions, coverage and paired uncertainty intervals.

## 5. Phase C - Ability and current form

Build exactly two initial models:

- Benchmark: three seasons of total WAR with fitted recency weights, age/position adjustment and calibrated shrinkage. Missing-history handling is explicit; no forecast silently requires three complete seasons.
- Lead candidate: forecasts of the available WAR components with separately fitted recency/reliability, age and position. Model rate and exposure separately and aggregate components consistently. Use opportunities appropriate to each component, such as minutes by strength or shots where definitions support them. Low exposure means weak evidence, not automatic exclusion.

Check whether any source component is already shrunk or model-adjusted. Avoid assuming its year-to-year correlation is a noise fraction. Sum component forecasts with their dependencies retained; do not force marginal variance shares to add to 100% when covariance exists.

Use a simple pooled prior for thin histories, clearly flagged, until the prospect model supplies a stronger prior. No-history players must not be valued as established stars or silently disappear. Goalies have a separate ability/exposure model and a simple historical benchmark.

Add in-season updating here, before the market refit. Begin with components that can be measured reliably before the trade date. Calibrate game-level signals to the same target using past data only; weak defensive signals can receive little or no weight. Update expected remaining games and role. Actual pre-trade production is already delivered and must not be included in the acquired asset's remaining contribution.

Gate: same-row comparison of the two models and a separate pre-trade-information ablation. Retain the component model only if it earns the improvement. If some components improve and others do not, retain the simpler specification for those components.

## 6. Phase D - Aging, opportunity and participation

Estimate additive smooth age effects using the selected ability model, with position and a restrained estimated-level interaction. Include experience only if it adds predictive value. Avoid treating regression from an extreme observed season as accelerated biological aging. Refit anchor and aging together where their shrinkage overlaps.

Compare the additive model with the historical-cutoff version of the existing comparables method, including its best documented top-50 variant. Both use the same inputs and evaluation windows. Lower games thresholds alone do not remove selection from disappearance; evaluate rates conditional on participation and totals for everyone.

Model forecast states: NHL participation, temporary no-NHL participation, return and long-term/permanent departure where labels support it. Do not mark recent absences permanent using future returns not yet observed. Censor unresolved future outcomes. Use current contract status and known expiry, not eventual re-signing, as inputs. Explicitly test the contracted-population correction, first-season non-participation and stale-history cases.

Link participation to games and deployment. Exit implies no NHL games; injury and reduced role can persist; draws cannot be independent by default. A conditional forecast times participation and an unconditional forecast are alternative constructions, not two discounts to stack.

Gate: calibrated games, zero-season and return probabilities; better total production prediction across horizons; smooth behaviour around zero ability and sparse history. Remove ratio guards and negative-anchor rules only when the replacement forecast is fully wired and tested.

## 7. Phase E - Market rates and the currency decision

### Contract-price output

Fit salary from forecasts available at signing, including the forecast production/workload path over the whole deal. Translate the contract stream and predicted contribution stream into aligned cap-share summaries using the cap path known at signing. Explain the alignment; do not compare one season's wins to an unexplained multiyear average.

Begin with the existing censored straight model and position slope. Candidates include term, restricted rights, experience/history reliability, games, age and a limited set of justified interactions. RFA years bought versus UFA years bought must be distinguishable where control dates are known. Start with a small registered set rather than a new unrestricted search. Use the reported clean-signing subset as a sensitivity, not the primary population: excluding early extensions changes the market being studied.

Score actual salary outcomes on signing-date folds. Report error, bias and coverage. Re-estimate all coefficients; neither the old 39% gain nor the exploratory star-RFA discount is a target the rebuild must reproduce.

### Primary production currency

Use a declared common annual production mapping for expected and realized contribution. Estimate its production coefficient(s) from the richer market model with term and rights accounted for, but do not pass the asset's own term or bargaining restrictions through as a gross-value premium. State the chosen common reference level/intercept and the support for it; report uncertainty and sensitivity. These coefficients are conditional market valuations, not identified causal willingness-to-pay.

Retain one consistent convention across rostered players, draft yields and prospects. Rights alter costs, control length, renewal choices and market-contract predictions. They do not automatically alter the gross dollar value of the same annual production. Show how much surplus is ordinary control-rights value before interpreting a trade residual as mispricing.

Required sensitivity: a term-inclusive reference valuation. Validate its transfer from original signing term to residual term; prevent repeatedly counting a commitment premium as years elapse. Show whether trade-category conclusions change. A conclusion that depends on this choice is labelled definition-sensitive, not robust evidence of inefficiency.

Gate: coherent units and horizon, historical price errors, same-map projected/realized scoring, and a valuation bridge separating performance changes from currency changes. Retest the floor only as a bounded sensitivity unless effects warrant redesign.

## 8. Phase F - Career simulation and control costs

Draw connected paths of ability, aging, participation, games and deployment from the fitted forecast. Include uncertainty from the first predicted period and estimate horizon behaviour rather than holding the three-year spread flat indefinitely. Include parameter uncertainty or report it separately from player-outcome uncertainty.

At each future renewal date, simulate the club's decision from the information that would be available then, not from knowledge of the later simulated performance. Qualification, negotiation, participation and return are different events. Model negotiated renewal costs where data support them; qualifying offers alone are not automatically expected signed salaries. Propagate pre-expiry participation into control years and address the documented skater/goalie gate omissions without multiplying overlapping events twice.

Track cap costs under the actual contractual state, including available retention, termination, buyout and relief rules. Missing participation does not automatically erase a signed contract's cap obligation. Where source data cannot support a mechanism, declare a bounded scenario rather than invent precision.

Price each path and average. Report expected NPV, outcome ranges and probability of negative surplus. Check simulation against analytically simple cases and convergence of reported values. A simulation is acceptable only if its inputs and interval coverage are calibrated; complexity is not validation.

## 9. Phase G - Integration, acceptance and handoff

Rebuild the player panel, draft yield curve and any built prospect valuation on the chosen currency. Do not let this phase silently expand into building the entire unbuilt prospect pillar; specify its future interface. Keep unresolved coverage visible. Re-run mixed-asset consistency and historical trade scoring with actual decision dates.

Game Value remains secondary triangulation, with its own historical training boundaries and position-specific measurement limitations. If used as an input to the in-season updater, acknowledge that it is no longer fully separate evidence for that part of the forecast.

Deliver a bridge from old to new outputs separating date corrections, ability, aging, participation, market mapping and control-cost changes. Component-by-component attribution is order-dependent, so also report the full joint change. Include stars, ordinary regulars, rookies, stale histories and goalies rather than only prominent examples.

Acceptance package: baseline reproduction; data/date audit; forecast comparison; market report; participation/interval calibration; currency sensitivities; representative contract paths; coverage table; full rerun instructions; updated state and manifest. No vendor data or generated outputs committed. Archive superseded material under existing rules, keep live filenames, and finish with the project's commit/push ritual.

## 10. Instructions to the builder after selection

Work through the phases in order. Make routine implementation decisions without seeking repeated permission. Keep unselected experiments separate from live outputs and make the selected specification reproducible. At each phase, report what changed, which evidence passed, what remains uncertain and the next dependency. Return to Thomas only for a material scope change or an unresolved economic definition that this plan does not settle. Do not change the primary currency after seeing which trade categories become significant.

First delivery: Phase A audit plus Phase B test specification, followed by a matched benchmark/component comparison. Do not start by changing the price coefficients or regenerating production NPVs.
