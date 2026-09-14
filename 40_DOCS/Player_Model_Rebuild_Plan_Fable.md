# Player model rebuild plan

Written 2026-09-14 (session 2026-09-14d). Status: a proposal for decision, not an adopted change. Production code and every locked decision are unchanged. A competing plan from the 2026-09-14c session sits at `Player_Model_Rebuild_Plan.md`; the two are meant to be read side by side. The plan draws on the code as it stands, the September 13 and 14 experiment reports (`Anchor_Shrink_Test.md`, `Aging_Comparable_Limit_Test.md`, `Aging_Curve_Coverage_Audit.md`, `Pipeline_Experiment.md`), the ground-up review in `Ground_Up_Player_Model_Review.md`, and two new test scripts written for this plan, `component_persistence_test.py` and `signing_date_audit.py`, whose figures are quoted in section 6.

## 1. What the rebuild is for

The model values a player by taking his raw two-season WAR total as his level, pricing that number on a market line, and projecting it forward by multiplying by an aging ratio. The defects found this month share that root: value is tilted by the player's level at valuation, stars are over-projected, negative anchors need a special rule, the ratio path needs four guards, the exit hazard was quietly offsetting over-projection, and the back-test has no settled currency for a realized win.

The rebuild replaces that chain with three connected pieces.

1. **A forecast.** For every player at every decision date, a distribution over future per-82 rate, games played and NHL participation, one season at a time, built only from information available on that date.
2. **Two market models.** A contract-price model that predicts what a player signs for, and a production currency that prices forecast production under a declared reference market. They answer different questions and are kept apart.
3. **A valuation by simulation.** Career paths drawn from the forecast, priced per path, averaged. The league-minimum floor, the RFA walk-away option and forecast uncertainty are all handled by the paths rather than by separate rules.

The cross-asset currency is untouched in spirit: picks and prospects are priced in the same production dollars with their own cost schedules.

## 2. Decisions required before the market phase

These are design choices, not tunings. Each is listed with the recommendation this plan carries. None is needed before Phase 3, so the forecast work can start now.

| Decision | Options | Recommendation |
|---|---|---|
| A. Term in the production currency | Term-free (one-year replacement each season; the term premium is a mispricing to measure) or term-in (one replacement for the remaining term; the premium is fair value) | Term-in as the declared currency, term-free reported as the sensitivity. The one-year counterfactual does not exist for the players who carry the money: 94% of stars re-sign with their own club. |
| B. Reference market for production dollars | Pooled RFA and UFA line, or a standardized UFA reference with rights on the cost side | Shared estimation across rights groups, rights entering as a cost feature through the qualifying-offer machinery and as a labelled back-test category. An open-market star price is extrapolation from two signings and must be labelled as such. |
| C. Second value provider | Keep single-provider discipline, or test a blended input | Test as a candidate in the harness. Circularity lives on the outcome side, which stays Game Value. Shared errors and vintage need checking before any blend ships. |
| D. Holdout policy | Which pages are development and which are confirmatory | Development on 2015-2021 pages; 2022-2025 pages touched once, at the end of Phase 5, with the roughly thirty variants already inspected on them recorded as prior selection. |
| E. Locked decisions opened | The k=0 identity, D3, D10, D11, D12, D16 and D18 population, D6 to D9, lambda and the comparables pool | All of them, deliberately, each with full-chain movement recorded. The plan lists which phase opens which. |
| F. Comparables curve | Retire, or keep as a challenger | Keep as a challenger in the harness; retire only if the additive curve beats it on the confirmatory pages. |

## 3. Principles that hold in every phase

- **Frozen information.** Every quantity used at a decision date is computed from data available on that date. Fits are rolling. Signing dates, not contract starts, date the market sample.
- **One forecast object.** Rate, games and participation are forecast jointly and consumed once. A season with no participation is a zero in the production target, and no second survival haircut is applied on top of it.
- **Complexity earns its place.** Every model change is scored against the simple benchmark on the harness before it enters the chain.
- **Nothing ships on aggregate NPV.** Whether total NPV rises, falls or holds is recorded, never used as the criterion.
- **Existing files are never renamed.** New scripts get new names. Production scripts keep running until the switch, then move to `90_ARCHIVE/`.

## 4. Phases

Effort is in working sessions of the kind logged in `00_STATE/sessions/`.

### Phase 0. Dates, identities and the evaluation harness (2 to 3 sessions)

Both reviews put this first. Improvements measured on a leaky harness are artifacts.

1. **Signing-date audit, done.** `signing_date_audit.py` shows 30% of the locked rate sample was signed before its trailing seasons were complete, rising to 58% at 3+ WAR. The market sample builder must date regressors at the signing. See section 6.
2. **Shared season table.** A new module, `player_season_table.py`, that builds one table of cleaned name key, season, position, components, games, ice time, per-82 rates, games share, birthdate, age and NHL experience, with the D20 proration applied once. Every new script reads it. The duplicated loaders in `skater_value_engine.py` and `skater_forward_projection.py` stay untouched until the switch. The standalone name-cleaner fallback in `aging_curve.py` is reconciled with the engine's here.
3. **Information-set builder.** For a date d: seasons complete before d, contracts signed on or before d (the D28 rule generalised), the player's contract state for the coming season as known on d, and, in Phase 1, Game Value through d for in-season use.
4. **Birthdates.** Finish the Elite Prospects birthdate pull so the aging panel is not selected on recent careers. Currently 40% of careers have no age.
5. **Harness.** `forecast_harness.py`. Inputs: a decision date, a model, an eligible sample rule. A model is a function from the information set to a per-season distribution over rate, games and participation for horizons one to six. Outputs, always by horizon, level tier, age band, position and experience: mean error and mean absolute error in per-82 rate, in season-total WAR with zeros for non-participation, in games; participation accuracy as a Brier score (the mean squared distance between a predicted probability and what happened); and interval coverage (how often the stated 80% range contained the outcome). Rolling fits only. The development and confirmatory split from decision D is enforced in code.

Acceptance: the production chain's own forecast, re-expressed as a model, scores on the harness and reproduces the tilt already measured (+24% at 3+ on 2020-25 pages). That is the reproduction guard for the harness itself.

### Phase 1. Current form: the ability forecast (2 to 3 sessions)

The single largest lever. Opens the k=0 identity between Layer 1 and Layer 2.

Models, all in `ability_forecast.py` as options:

- **A0** the raw 60/40 blend, the production rule, as the baseline.
- **A1** the age-aware three-season rule from the September 14 sweep (LB3A). The benchmark: 6.4% less WAR error on 2020-25 pages there, and 50/30/20 beat 60/40 in 1,000 of 1,000 resamples in July.
- **A2** component-wise: for each of the six WAR components, a per-82 rate shrunk toward the age-and-position norm by its own reliability. Shrinkage means pulling a noisy number toward what is typical by an amount that depends on how much evidence there is; here that amount is fitted per component, so a season of finishing luck is trusted less than a season of even-strength play. Games are the exposure, so a nine-game season is weak evidence rather than missing. Weights over three or more seasons are fitted, not fixed. Age and experience enter. Games share is forecast separately from the rate.
- **A3** A2 plus an in-season update from Game Value with its own fitted reliability, for trade-date valuations. Defensive weakness in Game Value shows up as low reliability for defencemen rather than as a rule.

What goes: the negative-anchor rule (D12 v3), because shrinkage handles it. The 93% bounce-back is regression to the mean.

Acceptance: A2 beats A1 on the development pages at every horizon with the tilt within 5% at every tier; A3 beats A2 at trade dates on the same pages. One confirmatory run at the end of Phase 5.

### Phase 2. Participation and exit (1 to 2 sessions)

Opens D16 and D18's population.

`participation_model.py`. Three states for each future season: played (one or more NHL games), absent but returned later, gone. Hazards by age, forecast level and contract state as known on the decision date. Returns are allowed: 18% of exiters come back within two seasons. The contracted-population finding from September 14 is the starting point (5.3% a year against 10.6% on all seasons).

Control years get the same treatment: probability of a tender times probability of playing given a tender, which the July test put at 13% exit conditional on tender, currently uncounted. Goalie control years get the gate the code says is missing.

Integration rule, written once and asserted: the production forecast is conditional on playing; participation multiplies it exactly once; a season scored as zero in the harness is a season the model must have given a participation probability to.

### Phase 3. Aging (2 sessions)

Opens D3, lambda and the comparables pool.

`aging_additive.py`. The yearly change in per-82 rate as a smooth function of age, by position, with a level-by-age term because the best players decline faster in wins, and NHL experience as a candidate alongside age. Fitted on within-player changes, rolling. Applied additively to the shrunk rate from Phase 1, never as a ratio on a raw total. With a linear price line, additive is exact, and the base floor, ratio cap, ratio floor and flat fallback all disappear.

Selection: a within-player change requires two observed seasons, so players who fall out are missing from the changes and old-age decline is understated. Lowering the games bar admits short seasons but does not fix that. The fix is joint with Phase 2: weight the observed changes by the inverse of the modelled probability of being observed, and test the imputation approach of Schuckers, Lopez and Macdonald as a challenger. The comparables curve stays in the harness as a challenger under decision F.

Acceptance: additive curve on the shrunk anchor beats A2-with-flat and A2-with-the-current-ratio-path on the development pages at horizons two to six; the selection correction changes the 33+ decline in the direction the participation model implies.

### Phase 4. The two market models (2 sessions)

Opens D6 to D9 and D7's single market. Requires decisions A and B.

`contract_price_model.py`. Dependent variable: cap share at signing. Regressors dated at the signing: the Phase 1 forecast over the contract's term, term, restricted status and its interaction with level, games share, a one-season-record flag, age. Left-censored at the league minimum as now. Rolling. Term and restricted status are reported as conditional associations, not causal prices. The star-RFA discount from the July exploration is re-estimated here on prorated, signing-dated data with a swept threshold; until then it is a candidate, not a finding.

`production_currency.py`. The declared reference market from decision B, fitted on the forecast so that its slope is the price of a forecast win. Under decision A the currency prices the remaining term. Realized wins in the back-test are priced on the same line, so both sides of every comparison sit in the same units. This does not prove the slope is the economically correct price of a win; it makes the currency internally consistent, and the reference market is what carries the economic claim.

Acceptance: held-out cap-hit error on the 1,648 contracts signed after their trailing seasons ended, against the $1.235M production line and the $0.755M term line from the September 14 search; the two figures are not comparable until both are rerun on signing-dated regressors.

### Phase 5. Valuation by simulation (2 to 3 sessions)

Opens D10 and D11. Replaces item 3.6's spread and the D13 point-path truncation.

`npv_simulation.py`. For each player and date: draw true talent from the Phase 1 posterior, walk it forward with the Phase 3 curve and its year-to-year shocks, draw games and participation jointly from Phase 2 so that an exit implies zero games, price each path on the Phase 4 currency against the known cost, apply the league-minimum floor and the RFA walk-away on the path, discount, average. Cap path: the published ceilings where they were announced before the decision date (the NHL and NHLPA published the 2025-26 to 2027-28 ranges on 2025-01-31, so pages from July 2025 may use them and earlier pages may not), 3% growth beyond. Goalies keep their own branch with the tender gate from Phase 2. The back-test statistic becomes a dollar difference scaled by a declared positive gross-value measure, not a surplus ratio.

Acceptance: the harness's dollar scoring on development pages; the k=0 identity is retired and replaced by a guard that the simulation mean equals the analytic forecast when uncertainty is set to zero. Full-chain movement against the production spine recorded contract by contract.

### Phase 6. Rebuild, confirm, lock (1 to 2 sessions)

Rebuild the draft yield curve and the prospect layer on the new currency. Run the confirmatory pages once. Re-run the power analysis. Write the change set as one robustness section with its net effect stated. Lock, then open the back-test.

Total: roughly 12 to 17 sessions.

## 5. The first decisive comparison

Agreed in both reviews and run inside Phase 1 on the Phase 0 harness.

1. One information set per decision date, one eligible sample rule, applied identically to every model.
2. A1 against A2, then A3 at trade dates.
3. Scored on the same future seasons at horizons one to three, including short histories and non-participation.
4. The additive curve and the games forecast added on the winner.
5. The market models fitted on the winner's forecasts, and valuations compared on the declared currency.

## 6. Evidence now in the repository

**Signing-date exposure** (`signing_date_audit.py`, locked sample of 2,349 contracts, every one with a signing date on file). The t-1 season is Oct 1 of the year before the contract start to Jun 30 of the start year.

| Signed | Contracts | Share |
|---|---:|---:|
| Before the t-1 season began | 85 | 3.6% |
| During the t-1 season | 616 | 26.2% |
| After it ended | 1,648 | 70.2% |

| Trailing-WAR tier | n | Share signed before t-1 began | Share signed before or during |
|---|---:|---:|---:|
| below 0 | 763 | 1.3% | 23.6% |
| 0 to 1 | 1,097 | 1.8% | 29.4% |
| 1 to 2 | 335 | 9.9% | 35.8% |
| 2 to 3 | 102 | 11.8% | 47.1% |
| 3+ | 52 | 19.2% | 57.7% |

Early signers are paid more at the same trailing WAR in every tier (for example 12.2% of the cap against 9.2% at 3+), which is what selection on private information looks like and is why the sample must be dated at the signing before any line is read.

**Component persistence** (`component_persistence_test.py`, 10,047 consecutive 20+ game season pairs). The share column is each component's covariance with total WAR per 82 divided by the total's variance, so the six shares sum to one.

| Component | Year-to-year correlation | Share of WAR per 82 | Carried into the next season |
|---|---:|---:|---:|
| Even-strength offence | 0.66 | 24% | 0.90 |
| Even-strength defence | 0.51 | 6% | 0.54 |
| Power play | 0.58 | 9% | 1.09 |
| Penalty kill | 0.20 | 2% | 0.44 |
| Penalties | 0.49 | 10% | 0.96 |
| Shooting | 0.35 | 49% | 0.44 |
| Games share | 0.29 | | |

Rolling out of sample, valuation seasons 2016 to 2025, outcome seasons with 10+ games, mean absolute error of season-total WAR:

| Horizon | n | Raw 60/40 blend | Pull-back L | Component-wise | 3+ bias, raw | 3+ bias, component |
|---|---:|---:|---:|---:|---:|---:|
| Valuation season | 6,296 | 0.810 | 0.764 (−5.7%) | 0.753 (−7.0%) | +0.87 | −0.21 |
| One season on | 5,085 | 0.902 | 0.837 (−7.2%) | 0.829 (−8.1%) | +0.97 | −0.42 |
| Two seasons on | 4,029 | 0.971 | 0.894 (−7.9%) | 0.884 (−8.9%) | +1.03 | −0.61 |

Limits: no aging applied at the longer horizons, so the growing negative bias for 3+ players there is partly the missing curve; outcomes are conditional on playing 10+ games; the rules are pooled least squares, not the per-component reliability shrinkage Phase 1 will fit. The component rule's gain over the pull-back is about a point at every horizon, consistent and modest. Its case is that it is the right structure for reliability-based shrinkage, not this margin.

## 7. What stays

The censored fit at the league minimum, the position slope with a common intercept, cap-share units with growth and discount cancelling, the exit hazard as a margin separate from aging, D28 on extensions, Game Value as the outcome yardstick, the reproduction guards and the file discipline. A rebuild that touches these is wasted work.

## 8. Identification notes

- Circularity: the production currency is the market's own price. The back-test measures deviation from the average market, not from an absolute value of a win, and says so.
- Selection: contracts are observed only for players who signed, and stars sign with their own club after seeing part of the season. Dating at the signing removes the look-ahead; it does not remove the selection, which is stated.
- Look-ahead: every phase's fits are rolling and the harness enforces frozen information. Bacon's WAR is a current-vintage export; that remains a documented limitation.
- Survivorship: handled jointly by the participation model and the aging weights, and scored on zeros in the harness rather than assumed away.
- Multiple inspection: the 2022-2025 pages have been examined by about thirty variants; decision D records that, and the confirmatory run is once.
