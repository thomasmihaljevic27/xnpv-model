# Review of the experimental player rebuild

Reviewed 2026-09-15 against commit `beb69a1` and `Player_Model_Rebuild_Plan_Fable.md`. Scope: `50_REBUILD/`, its reports and session record, with production code checked where the candidate claims to reproduce it. No candidate or production implementation was changed.

## Verdict

The experiment contains useful work and reproducible results, but its testing is not comprehensive enough to support the claims that it beats the live chain, that the whole chain is free of look-ahead, or that its dollar values are ready for use. Several concrete errors sit underneath the reported model comparisons. Correct those before choosing more variants or spending the forecast confirmatory run.

The original six-part stress-test runner executes successfully and reproduces the published subgroup, calibration and per-page figures. Reproducibility is established for that runner; the interpretation of those figures is not. The most important discoveries are the incorrect production comparator, inconsistent rate/total units, unfitted long-contract horizons, and market fits dated by starts rather than signings.

Priority P1 means fix before relying on the affected result. P2 means a material coverage or implementation defect that should be resolved before adoption.

## Findings

### 1. P1: the claimed production comparator is a flat-anchor baseline

`50_REBUILD/code/ability_forecast.py:273-294` returns the same trailing total at every horizon, with games share and participation both one. The live chain has an aging projection and survival weighting: see `20_CODE/contract_npv.py:402-425` and `skater_forward_projection.py`. Consequently, “43.6% better five seasons out” and the dramatic older-player improvements are comparisons with a simpler rule, not measured improvements against production.

The same substitution drives `run_player_comparison.py`: its `prod_value()` carries the anchor flat over the term. The report's claim that today's chain carries Mark Stone flat in perfect health for eight years does not describe the live code. This can exaggerate the rebuild's advantage precisely where aging and exits matter most.

Phase 0 required the production chain's own forecast on the harness. `run_phase0_acceptance.py` instead accepts a top-tier bias greater than 0.3 wins. That only establishes that a simpler baseline overpredicts; it does not reproduce the specified production forecast or the original tilt measurement.

**Required:** retain A0 as a simple benchmark, add a faithful production adapter, and reproduce forecast rows before recomputing all claims about improvement over production and the named-player dollar differences.

### 2. P1: shortened-season rates and games shares do not reconstruct the target

`player_season_table.py:151-155` applies D20 to WAR. At line 186 it then divides that already-prorated total by actual GP and multiplies by 82. Lines 193-194 define games share as GP divided by the shortened schedule. The harness multiplies the two.

For a 56-game full-season player with raw WAR of 1, prorated WAR is 1.464. The table calls his per-82 rate 2.144 and his games share 1. Their product is 2.144, not the target 1.464. The rate has acquired an extra schedule adjustment.

**Executed reproduction:** the median ratio `WAR_82 * gp_share / WAR` is 1.1714286 in 2019 and 1.4642857 in 2020. These are 17.1% and 46.4% discrepancies in the accounting identity, not estimates of the final fitted forecast bias. They contaminate rate targets, component persistence, aging changes and the rate-times-games integration. Games error has the related problem: predictions multiply games share by 82 while outcomes are raw GP in a shortened season.

**Required:** define raw per-82 rate, schedule share and standardized season total coherently, and assert their identity before fitting. Score games in a common unit. Refit the affected chain; a final dollar adjustment cannot repair this upstream error.

### 3. P1: years seven onward silently use an unfitted 60% participation probability

`ParticipationModel.fit()` defaults to `range(6)`; `A1Calibrated.fit()` also fits games only for horizons 0-5. `ParticipationModel.predict()` at line 297 returns 0.6 when a horizon is missing. The ability models fall back to trailing games share when that horizon has no games fit.

Market forecasts nevertheless request horizons through 8, and named-player comparisons request 0-7. **Executed reproduction with the actual leader on the 2021 page:** horizon 5 has 840 distinct probabilities spanning 0.005-0.995; horizons 6, 7 and 8 give every one of the 866 subjects exactly 0.6. Only horizons 0-5 have fitted participation coefficients. An old player near retirement can abruptly become much more likely to play when the forecast crosses this boundary.

These tails enter long-contract production averages and therefore also the fitted price line. The six-horizon stress tests cannot catch them. Separately, the ten remaining years specified for Shea Weber are truncated to eight in `run_player_comparison.py`.

**Required:** support every horizon used by an actual contract, or stop explicitly. Any extrapolation must be declared and tested. Assert that forecasted contract years equal the requested term; never silently discard years.

### 4. P1: market training windows are not frozen at the signing

`ProductionCurrency.fit()` at line 66 filters `start_yr < before`, despite promising contracts signed before the valuation. `run_phase4_decisions.py:rolling_price_eval()` and `run_curvature_test.py:rolling()` use the same start-year split. A 2019-start extension signed in 2017 can therefore be priced with contracts signed in 2018. Dating the player's regressors at his signing does not make those later market observations available in 2017.

**Executed sample audit:** 1,424 rows in the raw eligible contract sample have at least one later-signed contract in their start-year training pool; the largest such pool contains 354 later signings. This count is before forecast attachment and minimum-training-size restrictions, so it is an exposure count, not the exact final evaluated sample count.

The named-player runner is more explicit: it fits its currency on the entire contract sample and applies it to 2015-2021 valuations. That may illustrate a retrospective reference currency, but cannot establish an ex-ante valuation or support a clean historical back-test.

**Required:** date each market fit at the decision/signing date and assert that the maximum training signing date precedes it. Re-evaluate pooled versus split markets and curvature on identical date-valid rows.

Follow-up after Claude's response, 2026-09-15: all 3,550 contracts meeting the standard-level,
RFA/UFA, skater, 2015-2025-start filters have parseable signing dates before the date-validity
filter is applied. Missing dates therefore do not require a fallback in this sample. This
checks presence and parsing, not independent historical accuracy of the vendor dates.

### 5. P1: dollar outputs use future actual caps without present-value discounting

`production_currency.py:95-96` sums historical realized cap ceilings across the future contract and substitutes the 2025 cap for later years. There is no decision date, announcement cutoff, 3% extrapolation, or discount factor. `run_player_comparison.py` does the same.

Thus a historical valuation knows the future cap path, including the flat-cap years, while years beyond the dictionary remain at $95.5M. Calling the sum a cap-share convention does not make discounting cancel: if future nominal dollars are first reconstructed using future ceilings, they still need the specified present-value treatment. Value and cost must use the same declared date and units.

**Required:** a date-aware cap path and explicit discounted value/cost schedules. Treat existing totals as experimental nominal illustrations, not contract NPV. No corrected dollar totals were estimated in this review.

### 6. P1: participation and production condition on different events

The participation model predicts GP >= 10. But `_training_pairs()` attaches rates and games for all source rows, and the A1/A2 fits retain any nonmissing rate/games target, including 1-9 game seasons. The harness also retains their WAR and GP while classifying them as not played. The documented claim that both halves use the same ten-game event is false.

**Executed reproduction:** the 2021 leader's horizon-zero training pairs include 723 nonmissing rate outcomes classified as not played. The source table contains 2,918 rows with 1-9 games. The plan explicitly specified participation at one or more games and weak evidence, rather than exclusion, for nine-game histories.

**Required:** use the planned one-game participation event, or model short appearances as a separate nonzero-production state. Make the rate and games condition match the participation event. Even after that, multiplying separate conditional means is a modeling approximation unless their dependence is modeled; the planned joint simulation is still needed.

### 7. P2: the harness permits silent sample changes and drops return candidates

`forecast_harness.py` validates columns and missing values inside the returned prediction frame, but never checks that the complete requested career-by-horizon grid was returned. A model can omit difficult players entirely and pass. `compare()` then inner-joins the surviving rows, hiding the omission.

**Executed adversarial check:** a model returning only one subject was accepted and scored on the 2021 page, which requested 866 subjects. This demonstrates a missing guard; it does not establish that the current leader deliberately omits rows.

`subjects_at()` additionally declares a three-season eligibility window but drops subjects without a two-season trailing tier. On the 2021 page, 120 careers with qualifying 2018 history and no qualifying more recent history disappear. These are exactly the missed-season/return cases the wider eligibility rule was intended to admit.

**Required:** validate exact keys, uniqueness, finite outputs and equal samples before scoring and comparison. Keep eligible return candidates with an explicit stale-history tier or fallback. Age groups also use the last observed season's age rather than valuation-season age, so the reported “20 and under” population is not defined at the forecast date; correct and relabel subgroup reports.

### 8. P2: the stress tests do not establish the claims made about them

- The “full-chain” test fits on two already-truncated, effectively identical season tables, compares only `rate_82`, and examines horizons 0 and 3 on two July pages. It does not compare games, participation, market prices, costs, cap paths or signing-date contract state. A rate-only invariant cannot establish no leakage anywhere in the chain.
- The export-break test runs the total-WAR leader, not the component challenger. It splits outcomes before/after 2023; the development-page inputs do not include the new 2023 component residual. Similar error across those outcome eras does not establish that carrying the seventh component works.
- The runner still selects `A1AgingParticipationImputedNC`, while the later adopted experimental leader is `A1HingeExposure`. The latter has bake-off evidence, but the six-part stress battery is not wired to test it.
- Subgroup results pool horizons within each age/position group. Winning each marginal grouping does not establish winning every subgroup at every horizon.
- No candidate supplies the required predictive intervals. The harness silently reports missing coverage rather than failing the distribution requirement.

**Required:** targeted future-data perturbation tests covering the full forecast and market outputs, correct export-break tests using synthetic input perturbations, the final selected candidate in the stress runner, subgroup-by-horizon results, and actual interval calibration.

### 9. P2: the confirmatory protection only covers one entry point

`Harness._check_pages()` blocks default forecast-page scoring, but `unseal=True` accepts an empty reason and there is no persistent once-only record. Market selection bypasses this entirely: both the market comparison and curvature runners score 2018-2025 start cohorts, including the nominally reserved years, repeatedly during development.

Development pages forecasting outcomes in later years are not themselves a breach of the plan's page-based split. The separate problem is model selection on later market cohorts and the resulting broad assertion that those years are untouched.

**Required:** inventory market and forecast inspections separately, define which future tests remain confirmatory, and enforce that policy in every evaluation runner. Do not describe the whole rebuild as sealed because one harness method refuses a page.

## Adherence to the Fable plan

| Phase | What exists | What is missing or differs materially |
|---|---|---|
| 0: dates and harness | Shared table, age join, source checks, frozen season inputs, subgroup scores | Production forecast reproduction; consistent units; complete-sample enforcement; contract information-set method still raises `NotImplementedError`; interval output. |
| 1: ability | Extensive A1/A2 variants, rolling fits, reliability and window experiments | A3 trade-date Game Value update is absent. Nine-game histories are excluded. The every-tier 5% gate remains unmet; the simpler leader is a documented experimental choice, not passage of the specified A2 gate. |
| 2: participation | Per-horizon logistic probabilities; contract-feature ablation; returns possible in marginal probabilities | No played/absent/gone career-state process, tender/control-year integration, or goalie gate. Ten-game definition differs from plan and implementation is internally inconsistent. |
| 3: aging | Additive curve; naive/lagged level comparisons; IPW and imputation sensitivity | The current comparables ratio path is absent from the harness. No faithful A2-with-current-ratio acceptance comparison. Missing-lag rows are dropped by the finite-design filter, despite comments promising an age-and-position fallback. |
| 4: markets | Censored fits, contract regressors, currency experiments | Signing-date market windows; declared common production reference; comparable rerun of planned benchmarks. The production currency retains RFA features instead of isolating rights on costs; position enters as an intercept shift instead of the retained position slope/common intercept. Games share, age and short-history regressors specified for contract pricing are absent (`one_year` is contract length, not one-season history). These require explicit reconciliation. |
| 5: simulation | Deterministic dollar illustrations and forecast stress tests | No `npv_simulation.py`, talent posterior paths, joint games/participation shocks, per-path floor and RFA option, zero-uncertainty analytic guard, discounting, dollar harness, or full contract-by-contract production-spine reconciliation. |
| 6: confirm and integrate | Deferred | Draft/prospect currency rebuild, power rerun, final confirmation and lock are not done. Goalies remain outside the rebuild. |

The narrower choice of the total model, contract-feature ablation, and sensitivity work on survivor assumptions are documented and reasonable experiments. They do not require forcing the plan's preferred component model to win. They do require keeping the unmet acceptance conditions visible.

There is also configuration/report drift: the README still marks participation and aging unstarted; all versions remain 1.0 through substantial changes; the named-player executable still uses the log line after its rejection for valuation in the state record. ProductionCurrency and the named-player runner implement different term conventions. A single explicit candidate configuration and accurate entry-point instructions are needed for a reproducible final rebuild.

## What I executed, and the limits

1. Built an ignored review environment with Python 3.12.14, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, statsmodels 0.15.0 and python-dotenv 1.2.3. No system environment or model constants changed.
2. Rebuilt birthdates with the existing PuckPedia-plus-EP merger: 98.346% season-row age coverage, matching the reported coverage.
3. Ran the original `run_stress_tests.py` successfully: 35,878 scored rows, 1,516 careers; the published 0.279 top-decile miss, subgroup improvements, seven page wins and 0.504/0.499 era errors reproduce.
4. Ran the new `50_REBUILD/code/review_candidate_checks.py`: units identity, raw market-date exposure, horizon support, participation/production conditioning, omitted-subject behavior, and an arbitrary-date API check. Its aggregate results are saved under `50_REBUILD/output/review_candidate_checks.json`.
5. The arbitrary-date check also reproduces an assertion on 2025-06-01 with default `t0`: the completed 2024 season is selected while inferred `t0` is still 2024. The date API needs explicit valuation-season semantics before A3 use. Participation's optional `as_of` argument is currently ignored in favor of July 1 dates; this matters if contract features are enabled for trade-date forecasts.

I did not rerun all 30 variants and their bootstraps, the market model-selection runners on reserved cohorts, or the live production NPV pipeline. I did not produce repaired forecasts or quantify the net NPV effect of these bugs. The market-date count uses the eligible pre-attachment sample; all numerical reproductions above identify their actual scope. Generated data, installed dependencies and run logs remain ignored.

## Recommended order

1. Correct rate/games units and the participation event; add identities that fail on the present code.
2. Repair eligibility, prediction completeness and long-horizon handling.
3. Add the real production comparator and frozen signing-date market fits; unify the production currency and cap/discount conventions.
4. Refit and rerun development comparisons. Reassess the star and young-player residuals after these corrections before adding more flexibility.
5. Complete the omitted distribution, trade-date, control-year and simulation work; reconcile the plan gates explicitly.
6. Record which confirmatory evidence remains available, then run it after the final candidate is frozen.

The useful conclusion today is that the experimental forecast beats its simple flat benchmark reproducibly. It is not yet established that the rebuilt valuation beats production or follows the whole agreed plan.
