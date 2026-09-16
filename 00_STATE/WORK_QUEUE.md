# WORK QUEUE — NHL Trade Market Efficiency

<!-- Extracted from PROJECT_STATE.md on 2026-09-09 (v3.2 restructure). Pure move, no content change. -->
<!-- The full list of yet-to-do work, phase-sequenced. Changes almost every session.
     Detailed sequences for individual pillars live in 01_Draft_Model_Sequence.md,
     02_Prospect_Model_Sequence.md, 03_Player_Market_Model_Sequence.md. -->

---

## Work queue

**Phase 5 simulation review, 2026-09-16:** reviewed `95750f5` in isolation.
Standard suite passes 24/24, including all 34 variants on page 2018; independent
300-contract deterministic currency comparison agrees within $7.45e-09. Phase 5 is
not closed: all 1,217 historical simulations use the 2025 residual shape/persistence
fit (outcomes through 2024), rank correlations are used as Gaussian correlations
and the larger-sample self-test fails, and absorbing exits omit the plan's returns.
Zero rising marginal probabilities does not establish zero returns. See
`50_REBUILD/docs/NPV_Simulation_Review_Codex.md`. Correct dated calibration and
copula mapping, resolve the return-capable path scope, then continue integration.
RFA/control-year, goalie, joint-path design and dollar reconciliation remain open.
The preceding valuation review stays closed; no model changes or merge in this review.

**Valuation review closed, 2026-09-16:** verified `e14e873` by rerunning the corrected
comparison and independently checking its CSV. All 1,217 contract IDs, costs and fixed
groups match across columns; all five group means reproduce the prior audit and retain
their signs and ordering. Corrected retention and framing figures reproduce. The preceding
valuation-comparison findings are resolved on tested paths. See
`50_REBUILD/docs/Valuation_Review_Closure_Codex.md`. Ready to continue development:
repair the known component-variant failure before using it, then continue simulation,
valuation integration/reconciliation and the predefined back-test. Subgroup limitations,
small samples and final-validation work remain; this is not a completed-model sign-off.
Candidate implementation remains unmerged on main.

**Valuation sensitivity review, 2026-09-15:** reproduced `5e019ad` and 22/22 checks;
also reproduced the component variant's missing-`fitted_horizons_` error. The reported
top-tier reversal changes membership (18-68 contracts). On the candidate's same 18,
all five means are negative. Reported participation removal also changes aging; a
same-aging comparison retains fixed-group signs but does not establish calibration is
irrelevant. Development attrition is 423 unmatched subjects, 241 insufficient earlier
pricing contracts and 15 pre-forecast-term cases, leaving 1,217 of 1,896 priced.
Extending horizons does not recover these losses. The production forecast is repriced
with rebuild currency, not a full production-NPV comparison. See
`50_REBUILD/docs/Valuation_Sensitivity_Review_Codex.md`. Continue planned evaluation
with fixed groups and these limits; no model change or new thesis claim adopted.

**Coverage diagnostic fact check, 2026-09-15:** reproduced `c4c41f4` in isolation.
The participation discrepancies reproduce, but the report's oracle ceilings and causal
attributions do not follow. Alternative one-parameter adjustments exceed its claimed
ceilings. A common-unit accounting assigns young h3 error mainly to games in one stated
replacement order, not almost exclusively participation. The new diagnostic substitutes
the final year's residual shape, changing star h5 baseline from 60.8% to 60.2%.
Prior uncertainty fixes remain closed. See
`50_REBUILD/docs/Coverage_Decomposition_Review_Codex.md`. Record subgroup miscalibration
as a limitation with unresolved causes; selection bias is plausible, not established.
Recommendation is to continue remaining build and assess valuation robustness, without
adopting the new queue priorities as proven diagnoses. No model changed or merged.

**Uncertainty repair verification, 2026-09-15:** tested `9c27042` in isolation and
closed all three findings from the preceding uncertainty review. All 22 repair checks pass
with no skips, including production comparisons. Frozen-model sensitivity reproduces
+0.116 at h0 and +0.073 at h5; reports now use each evaluation year's calibrator.
Distribution and point expectations agree within 2.60e-16 WAR across 40,510 rows.
Disabling centring makes the new guard fail, detecting a 0.2228-win mismatch.
Revised 80% coverage is 82.2-84.3% overall, but only 60.8% for stars and 66.3% for young
players at h5; 28/151 played star seasons exceed their fitted 95th percentile.
These remain model limitations, not unresolved instances of the three repaired bugs.
See `50_REBUILD/docs/Uncertainty_Repair_Verification_Codex.md`. No new blocking defect found
in these repairs; candidate remains unmerged and remaining plan work is incomplete.
The preceding review paragraph records the superseded candidate's findings.

**Uncertainty implementation review, 2026-09-15:** reviewed `73b77ee` on
`claude/amazing-johnson-cllbgl` in isolation. All 21 repair checks pass, including local
production comparisons. Export guards and published interval coverage reproduce: overall 80%
ranges cover 82-84%, but h5 star/young coverage is 59.6%/66.3%. The reported rising recent-season
sensitivity is a diagnostic error: it refits on altered data. Holding parameters fixed changes
the +0.5 rate shock response from +0.116 at h0 to +0.073 at h5, declining with distance.
Residual-shape and optimism diagnostics also use the last page's calibrator across all pages.
The predictive distribution has a positive mean offset from the reported point expectation
(mean 0.0374 WAR, maximum 0.2265); reconcile before simulation. See
`50_REBUILD/docs/Uncertainty_Implementation_Review_Codex.md`. Coverage and future-data checks
are reproduced evidence; attribution to bias versus spread remains unresolved. Implementation
is unmerged, and simulation/A3/control/goalie/dollar-validation work remains incomplete.

**2026-09-15c — predictive uncertainty and the leakage battery, built.** The forecast states a
range (`predictive_interval.py`), the harness's coverage column is no longer empty, and the
look-ahead spot check is now a five-part battery (`run_leakage_tests.py`). All four leakage tests
pass at exactly zero change. Report: `50_REBUILD/docs/Predictive_Uncertainty_and_Leakage.md`.
**Run on the full table once Thomas supplied the vendor exports:** 98.3% age coverage, review
suite 19 passed / 2 skipped / 0 failed (the two skips need the PuckPedia **.xlsx**, which the
production loader opens with `read_excel`; the CSV will not substitute). The aggregate
calibration is good — 80% band holds 82-84%, 90% band holds 91% — and the subgroups are where
the work is. Next, in order:
1. **The star residual, promoted: it now blocks two things rather than one.** It was already the
   forecast's largest known defect (top decile predicted 2.360 against 2.698 actual, hinge
   variant recovered a fifth). It is also visible in why the 80% band delivers 61% for the 3+ tier
   five seasons out: the middle of the star misses sits at +0.51 where the band's own middle is
   −0.11, and 18.5% of played star seasons finish above their own page's 95th percentile where 5%
   is intended. **How much of the coverage gap is the centre and how much is the tail is not
   established** — the diagnostic conditions on playing while coverage includes non-participation.
   Widening the band would hide the bias, so it was not widened. **Fixing the centre is the
   prerequisite for reading the tails**, and it comes before any further interval work.
2. **The joint simulation** on the fitted spread, with the zero-uncertainty identity it already
   satisfies one layer down.
3. **Separate bands for the rate and the games share, drawn jointly**, so an exit implies zero
   games on the path rather than a product of averages.
4. **Only then** re-measure whether the shape of a miss needs a tier or age term of its own. The
   star and young-player right tails reach +3.64 and +3.55 against a pooled +2.56, which is real,
   but fitting a fatter tail around a biased centre is fitting the wrong thing. Settling the split
   also needs the participation half assessed on the same footing, and a controlled comparison of
   moving the centre against widening the band.
5. Then the rest of the named milestone: trade-date updates, control-year and goalie treatment,
   contract-by-contract dollar reconciliation, and the holdout policy.

**2026-09-16d, revised after review — an aggregate contract simulator, and Phase 5 is NOT
closed.** The review found two implementation defects and one scope claim; all three are fixed and
the reporting is corrected. Report: `50_REBUILD/docs/NPV_Simulation.md`. Suite: **25 passed, 0
skipped, 0 failed**.

**The blocker was a look-ahead of exactly the kind the leakage battery exists to catch.** The
runner fitted one calibrator on the latest page in the whole contract input -- 2025, whose replay
holds outcomes through 2024 -- and used its shape and persistence for all 1,217 earlier contracts.
Forecasts and price lines were rolling; the uncertainty around them, the only part that reads
outcomes, was not. Each contract now uses its own page. **New check 25** corrupts every season at
or after the decision date and requires the shape, scale, persistence and return rate to be
identical to the last digit. The existing battery could not have caught this -- it tests the
forecast and the band, and the defect was in the runner consuming them.

**The copula imposed the wrong correlation.** Rank correlations were handed straight to the normal
draws; a Gaussian copula with latent r delivers (6/pi)*arcsin(r/2). Asking for 0.427 delivered
0.410. Fixed by inverting, and **the test is now analytic** rather than Monte Carlo, because three
thousand paths could not see the error and six hundred thousand could.

**Returns were excluded, not shown absent.** "No term has rising marginals" is a non-sequitur -- a
marginal can fall from 90% to 70% with one path in ten a return. Now a two-state chain with a
return rate estimated before each decision date (~0.10); absorbing kept as the sensitivity, and it
costs little ($11.02M against $11.09M of within-contract sd on the eight-year cohort).

**Reporting corrected:** 228 of 1,217 contracts change sign (the "none" was read off tier means);
the dependence counterfactual keeps participation correlated in both arms and isolates the
conditional performance error only; a point valuation does NOT assume independent errors; the
floor is the convexity, not a bending tobit; the one-year 0% now runs on common draws; and every
figure comes from one run.

**What holds after the fixes:** the identity, now checked against `ProductionCurrency.value`
independently, at $1.49e-08 on 300 contracts. The gap between averaging path values and valuing
the average path, +$0.19M on the average contract, concentrated where the floor binds and
vanishing for stars. The spread: an eight-year cohort averaging $11.0M of within-contract sd
around a $5.5M mean with a 38% chance of losing money, and the miss's cross-season dependence
widening a seven-year deal by 41%.

**Phase 5 remains open.** Still absent against the written plan: the RFA walk-away and control
years (their absence makes the lower tails too heavy, and does not mean every downside was
unavoidable), goalies, contract-by-contract dollar reconciliation, and development dollar scoring.
The aggregate draw does not retire the plan's joint rate/games/participation design for later
consumers.

**2026-09-16c — the review stage is closed and the first item after it is done.** The component
variant's `AttributeError` is repaired and the suite now covers every registered variant:
**23 passed, 0 skipped, 0 failed**, including all 34 variants fitting and answering the grid.

**The cause was a second copy of a rule.** `A2PerComponentWindow` has to override the training-pair
builder to construct its anchors differently, and it was written by copying the base builder and
dropping the three lines that record which horizons the fit managed. The class then read
`fitted_horizons_` a moment later and raised. That is the failure this codebase warns about in two
other files, so the fix takes the lines out of both builders into one `_record_fitted_horizons`
that each calls, rather than making a third copy.

`BaseModel.fit` now also sets `fitted_horizons_ = None` up front. None already meant "fitted
nothing, so no horizon is out of range" wherever `_guard_horizons` read it through a getattr
default; making it explicit means a model that SHOULD have recorded a range fails where it can be
seen rather than with an AttributeError somewhere downstream. No behaviour changes: the two
unrestricted models already resolved to None.

**Next, in the order the reviewer set:**
1. **The joint simulation**, on the fitted spread, with the zero-uncertainty identity it already
   satisfies one layer down and the distribution-mean guard it now has.
2. **Remaining valuation integration and contract-by-contract dollar reconciliation.**
3. **The back-test, with the grouping rule and evaluation protocol declared in advance**, all
   predefined categories evaluated and sensitivity reported. Keep the reserved evaluation sealed
   until those choices are fixed.

**A wording distinction to preserve** (the reviewer's, and it is right): the ranking of GROUP
AVERAGES is stable across forecasts. Individual contract rankings are not necessarily identical,
and nothing here tested them.

**2026-09-16b, revised after review — the valuation sensitivity, on a declared fixed grouping.**
Same 1,217 development contracts, five forecasts from production's own through the adopted
candidate, groups cut ONCE on the candidate's forecast and applied to every column. Report:
`50_REBUILD/docs/Valuation_Sensitivity.md`.

**Every group keeps its sign in all five columns and the ordering is identical in all five.**
Worst to best: 2+ < below 0 < 0-to-0.5 < 0.5-to-1 < 1-to-2. Contract by contract the models
correlate 0.974-0.988 with production's forecast, same sign on 88-97%, mean gap $0.24-0.47M.
**The earlier report's "top tier flips sign" was an artifact** of letting each column cut its own
tiers, which gave them 51, 68, 18, 19 and 18 contracts -- different populations, not the same
contracts changing sign. Withdrawn, along with "a second independent reversal".

**The magnitude is still unsettled** even though the direction is not: the top group runs -1.74 to
-4.55 $M across forecasts, on 18 contracts, with no uncertainty estimate and no realised outcome.

**Participation, tested properly:** pinning the probability of playing to one while holding the
imputed aging moves the top group -1.736 to -1.910 (currency refitted) or -1.592 (held). Signs and
ordering survive. The earlier "-1.74 to -1.68, barely matters" came from a pair that also swapped
the aging curve; that claim and "calibration errors are not what threatens the conclusion" are
both withdrawn.

**The sample loss is at the price fit, not the forecast horizon.** 1,896 eligible, 438 lost at
attachment, 241 lost because the signing quarter had too few earlier signings to fit a line, 1,217
priced. Of 35 excluded six-year deals, 34 are lost at the price-fit threshold. **"Extending the
forecast's reach is the cheapest gain" is withdrawn** -- it is the wrong stage.

**What follows, and it replaces the instruction in the previous version of this entry:**
1. **Finish the valuation and back-test work with a declared grouping rule stated in advance.**
   Evaluate the predefined categories and report where conclusions are sensitive. **Do not select
   or drop thesis categories on the strength of their current development-sample signs** -- that
   is the selection problem this project exists to avoid, and the earlier "cite three, drop the
   elite" instruction is withdrawn.
2. Keep three things apart in the write-up: agreement among model valuations is a robustness
   check, a back-test against realised outcomes is evidence about performance, and systematic
   trade mispricing is the claim that still needs testing.
3. The term framing contrast is large and real ($8.76M to $9.70M on the fixed top group across all
   five forecasts) and remains an open judgement. It is a contrast between two declared framings,
   not a measure of model uncertainty.
4. **Open defect:** `A2AgingParticipationImputed` raises `AttributeError` on `fitted_horizons_` in
   its own fit, so a registered candidate cannot run through the contract path. The 22 checks pass
   despite it, so they do not establish that every registered variant runs.

**2026-09-16 — the diagnostic loop is closed. The limitation is measured; its causes are not.**
The coverage decomposition was fact-checked and its tables reproduce, but most of the causal
reading did not survive and is withdrawn (nine items, listed in
`50_REBUILD/docs/Coverage_Decomposition.md` section 5). **Do not start another tuning cycle on
this sample.** Repeated adjustments to a development sample that has already been inspected many
times cannot separate these causes, and each pass spends credibility on a question the exercise
is not built to answer.

**What is established and goes in the write-up as stated:**
- Nominal 80% ranges hold 82-84% of outcomes overall, **61% for the 3+ tier five seasons out** and
  **66% for players 22 and under**; 18.5% of played star seasons five out finish above their own
  page's 95th percentile, where 5% is intended.
- Participation probabilities are miscalibrated for those groups: 22-and-unders under-predicted at
  every horizon (0.677 against 0.804 five out), 3+ at 0.781 against 0.883, 34-and-overs
  over-predicted at 0.491 against 0.373 at the valuation season.
- In a common-unit accounting that closes, the stars' bias is mostly **rate** (-0.680 of -0.866
  five out) and **games played is a substantial error source nothing had remarked on** -- the
  largest single component of the young players' bias three seasons out (-0.207 of -0.340) and the
  whole of the stars' bias at the valuation season (-0.178 of -0.172).
- **The respective roles of participation, games, rate and selection are unresolved.** Say that.

**Next, and it is the question that decides whether any of this matters:** does the thesis's own
conclusion move? Run the valuations and the trade-mispricing categories across reasonable
forecast alternatives. If the categories survive, an imperfect forecast still supports the
argument and the paragraph above is a limitation. If they do not, that is a finding about the
thesis, not about calibration. Then the rest of the milestone: the joint simulation, separate rate
and games bands, trade-date updates, control-year and goalie treatment, contract-by-contract
dollar reconciliation, and the holdout policy.

**Carried forward from the withdrawn reordering, because it is measured rather than inferred:**
the games forecast deserves attention it has not had, and the star residual remains a rate defect.
Neither is a ranking of causes.

**WITHDRAWN, same day — the "rising sensitivity" open question.** It was raised on a test whose
helper refitted the model on the perturbed data while claiming the fit was held fixed. With the
fit frozen the pass-through **falls** with distance, 0.23 at the valuation season to 0.15 five
seasons out, which is what theory expects. Corrected in `run_leakage_tests.py`; both the frozen
and the refit responses are now reported, the second named as what it is.

**2026-09-15c, after review — three fixes landed and one is worth carrying forward.** The
independent review of `73b77ee` found the refitting sensitivity test above, a residual diagnostic
that used the last page's calibrator for every page, and a predictive distribution whose mean sat
up to 0.23 wins above the point forecast it surrounded because the shape was never centred. All
three are fixed; the third is the one to remember, because **every existing guard passed while it
was wrong** — the forecast columns were untouched and the zero-spread identity removes the shape
it would have had to inspect. A simulation reads the distribution's mean, not the column. Check
22 now integrates the returned quantile function and requires the two to agree, and it fails both
ways so a version that stopped centring fails it.

**2026-09-15c — the 2026-27 ceiling is entered, 2027-28 is not, and production disagrees.**
`rebuild_config.CAP_CEILING` gains 2026 = $104.0M (Thomas, confirmed), announced 2025-01-31 and
enforced as such: a valuation dated the day before still extrapolates it, one dated the
following July uses it exactly. Before this the rebuild grew it from the 2025-26 ceiling to
$98.4M, understating the denominator of every 2026-27 cap share by 5.4%. 2027-28 stays out —
the $113M in circulation is an estimate, not a set ceiling. **Production carries 2027 =
$113.5M** in `skater_forward_projection.py` and `goalie_value_engine.py`, commented as a
published 2025 MOU figure. Under D11 only the valuation season's own ceiling is read and there
is no 2027-28 page, so nothing priced today depends on it; it stops being inert the day one is
built. **Thomas's call**, in the flags. Production was not edited.
**Fourth repair verification, 2026-09-15:** reviewed `4b9723a` in isolation. All 17 repair
checks pass with no skips. Independent full-run audit confirms identical coefficients across
18 comparable quarters and zero shared-currency repricing differences for all 12 named cases.
The all-rejected request returns zero rows and one rejection record; empty input also passes.
The two preceding findings are closed. See `50_REBUILD/docs/Fourth_Repair_Verification_Codex.md`.
No new blocking defect found in the changed paths. Next milestone is the remaining simulation,
A3, control/goalie, uncertainty, dollar reconciliation and final-validation work. Rejection
CSV reporting still is not a complete per-run sample audit. Candidate implementation remains
unmerged; production code and the previously verified forecast specification are unchanged.

**2026-09-15 independent rebuild review: prerequisite before the experimental next steps below.**
See `50_REBUILD/docs/Player_Rebuild_Candidate_Review_Codex.md`. Correct shortened-season rate/games units
and the participation event; enforce eligible samples and fitted contract horizons; add the real
production comparator; date market fits at signings; implement consistent ex-ante caps and
discounting. Then rerun development comparisons before tuning the remaining star residual.
Complete the missing predictive distributions, A3 update, control-year/goalie gates and simulation;
record market versus forecast holdout exposure before final confirmation. Review only: no fixes
adopted and no locked decision reopened.

**2026-09-15 — experimental rebuild (`50_REBUILD/`), next steps in order.** Phases 0-4 are built
and reported; nothing is adopted into production. In priority order:
1. **The elite tier is not identified, and it is the thesis's headline.** Surplus at 2+ forecast
   wins a season flips sign between the straight and log currencies (+$3.00M against −$0.78M) on
   37 contracts, and the named-player check makes it concrete: the log currency says McDavid at
   $12.5M was overpaid by $51M. Options: pool the goalie and prospect pillars to widen the top of
   the sample, extend the panel back, or state in the paper that the top is not identified. **No
   back-test result about stars should be cited until this is settled.**
2. **The star residual in the forecast.** The model still under-rates its best players by about a
   third of a win over the first three seasons, located in the rate rather than participation
   (top decile predicts 2.360 against 2.698 actual). The hinge variant recovered a fifth of it.
3. **Young players** (aged 20 and under: error 1.034, bias −0.346, the worst population in the
   model by a factor of two). The fix is probably a prior from the prospect pillar rather than
   more machinery in the player chain.
4. **Draft and prospect pillars onto the rebuilt currency**, then the back-test.
5. **The confirmatory run**, once and once only, at the end. Prediction on record: the advantage
   will be nearer 20% than 40%, because it narrows monotonically across the development window
   (−38.1% in 2015 to −22.3% in 2021).
6. **Goalies are untouched** by the rebuild.


**2026-09-14d — player model rebuild plan, Fable version (proposal, awaiting Thomas's choice).** `50_REBUILD/docs/Player_Model_Rebuild_Plan_Fable.md`: Phase 0 dates, identities and a frozen-information harness; Phase 1 the ability forecast (component-wise reliability shrinkage, rate and games separate, in-season update at trade dates); Phase 2 participation with returns and control-year gates; Phase 3 additive aging on the shrunk rate with selection weights; Phase 4 a contract-price model and a production currency, both dated at the signing; Phase 5 valuation by simulation; Phase 6 rebuild, one confirmatory run, lock. Six decisions (term framing, reference market, second provider, holdout policy, locks opened, comparables fate) are needed before Phase 4, none before. Two test scripts now carry the evidence: `signing_date_audit.py` (30% of the rate sample signed before its trailing seasons were complete, 58% at 3+) and `component_persistence_test.py`. Nothing adopted; the competing plan (09-14c) is `50_REBUILD/docs/Player_Model_Rebuild_Plan.md` and its review `50_REBUILD/docs/Ground_Up_Player_Model_Review.md`.

**2026-09-13 — 2026-27 page, D28 extensions, aging-curve audit.** Done: the 2026-27 page is live in the panel and dashboard ($104.0M ceiling, reads 2025-26); signed extensions count from their signing date (D28), including in-season dashboard variants; the one-season-left curve label is fixed. Follow-ups, in order:
1. **Refresh the PuckPedia contract export** (current one ends 2026-05-21) and re-run `contract_npv_panel.py` → `player_dashboard.py`. The 2026-27 page is missing all summer-2026 signings until then.
2. **Aging-curve pool decision** (deliberate revisit of the locked curve): whether to admit first seasons to the comparables pool, base first-year players on their first qualifying season, and/or pool adjacent ages at the thin ends. Options and evidence required: `50_REBUILD/docs/Aging_Curve_Coverage_Audit.md`. **Added 2026-09-13b:** a fourth candidate, limiting the blend to the 50 most similar comparables with the pooled weight kept (held-out gains 0.3%-0.8% overall, 1.3%-2.1% for 3+ players' season totals; `50_REBUILD/docs/Aging_Comparable_Limit_Test.md`). Separately, examine the +0.5-0.6 WAR/season held-out over-projection of 3+ players' season totals, which comes mostly from the unshrunk valuation anchor rather than the curve. Confirmed in dollars in the production chain the same session (`npv_realized_by_tier.py`: +$0.98M per season for 3+, under-projection below 1 WAR, no overall bias). Tested the same session (`anchor_shrink_test.py`, `50_REBUILD/docs/Anchor_Shrink_Test.md`): a 2009-2017 pull-back fixes the middle tiers but overshoots stars; refitting the market line on pulled-back WAR does nothing. Next, in order: (a) decide the back-test's realized-value currency (price per recent win vs per delivered win), which decides whether stars are over-valued at all; (b) if the pull-back is pursued, calibrate it on a rolling recent window at valuation dates (not contract starts) and test it out of sample. Both must precede any back-test result comparing star and non-star sides of a trade. **2026-09-14 sweep (`50_REBUILD/docs/Pipeline_Experiment.md`):** the recommended package is a rolling starting-point pull-back plus the contracted-population exit hazard (L+H), with top-50 comparables; (a) above still comes first, then a deliberate revisit of the k=0 identity and the hazard population in `exit_hazard.py` with full-chain movement recorded. Second pass the same day: age in the pull-back (LB3A+H, +top50) is the lowest-error production rule and near NPV-neutral; the value line is a framing decision (term-free −19% or with term −39% on held-out cap hits; term adds $3.3-4.1B of NPV). Decide the framing (possibly after the draft and prospect pillars), then which locked rules to open: k=0 identity, D6-D9, hazard population, comparables.
3. **D11 vs the published cap schedule** for t0 ≥ 2025 (STANDING_FLAGS). Decide before any 2025-26 or 2026-27 valuation is cited.
4. **Phase 4 trade scoring** must call `npv(pid, t0, as_of=trade_date)` so extensions signed before a trade are in the asset.

**Target-specific aging yardstick comparison completed (2026-09-10).** The tested median-target-distance rule slightly increased errors in whole-career holdout and historical training windows. Retain the shared production scale; no broader claim that it is optimal. See `40_DOCS/Aging_Yardstick_Comparison.md`. New follow-up: review the Erik Gustafsson / Erik Gustafsson 88 career-key collision in the aging input and implement an identity correction only after checking downstream effects. The comparison excluded that career equally from both alternatives; production remains unchanged.


**TOP OF QUEUE (2026-09-08) — DONE 2026-09-09. Migration verified clean.** The full player chain
(`skater_value_engine` → `skater_forward_projection` → `rfa_terminal_value` → `exit_hazard` →
`contract_npv` → `contract_npv_panel`) plus `goalie_value_engine` all re-run on the desktop
machine post-migration. Every recorded figure reproduced: `[1a]` skater k=0 max diff $0.00,
6,892 priced skater-seasons, median contract NPV +0.29M, p10 -7.80, NPV panel 6,939 rows,
`[1b]` 776 goalie k=0 rows / 13 divergences (< 19 assert), goalie parity gate $0.000284,
`goalie_value_spine_v2.csv` byte-identical (MD5 `55c935dd…`). **One target figure in the old
version of this line was stale and is now corrected: the sweep prices 2,981 contracts (2,591
skater + 390 goalie), not 2,909.** The 2,909 was a 2026-07-05 number; the 2026-07-29 goalie
stale-anchor / flat-carry fix (v2.9 change log) made ~72 more goalie contracts priceable and
v2.9 updated the median/p10/panel figures but not the contract total. Inputs all byte-identical,
git tree clean, so the pipeline is sound. Rebuilt draft curve also reproduced this session
(matches to the cent). See the Change log v3.1 entry.

**Editorial update (2026-09-09).** Doc 1 has a new 1370-word draft incorporating the user-provided editorial feedback at `40_DOCS/Doc_1_Circularity_and_Game_Value.docx`. User reading and visual pagination verification remain; broader repository-review work is deferred for now.

**SECOND (2026-08-28, consolidated 2026-09-09) — DONE 2026-09-09.** Write the five explainer
documents per `Explainer_Document_Plan.docx`. All five drafted and placed in `40_DOCS/`:
`Doc_1_Circularity_and_Game_Value.docx`, `Doc_2_Player_Pillar_I.docx`,
`Doc_3_Player_Pillar_II.docx`, `Doc_4_Drafting_Prospects_Unbuilt.docx`,
`Doc_5_Cross_Cutting.docx`. Written in the humanizer voice, each section carrying its four
required elements (how it works, why built that way, what it doesn't do, what's untested).
See the Change log v3.5 entry for sourcing and the open items each document surfaced.
Docs 2-5 were rewritten and checked against implementing code on 2026-09-09 at the user's request (see `sessions/2026-09-09f.md`). Text and core WordprocessingML schema checks pass. User reading and visual pagination verification remain; rendering is unavailable in the current runtime. No model changes or queue reordering resulted.

**Subsequent user correction:** that pass cut too much explanation for the supervisor. Fuller review copies now live in `40_DOCS/Supervisor_Drafts/` under the same filenames. These are the Docs 2-5 versions for the next read-through; see `sessions/2026-09-09g.md`. Preserve full explanations when removing AI prose. Qualifying-offer effective-date review added to flags, without changing the model or queue order.

**Doc 2 annotations addressed 2026-09-10:** Section 3 now explains the aging calculation step by step with defined inputs and one worked example; other edits in the user's Downloads copy are preserved. Latest review copy remains in `Supervisor_Drafts`. User read-through and unavailable visual pagination check remain. See `sessions/2026-09-10.md`.

**Second annotation pass (2026-09-10b):** comments 2-6 edited; similarity weighting explained in chat for the user's own rewrite, with that paragraph unchanged. Projection safeguards and exit-model explanation clarified. See `sessions/2026-09-10b.md`.

**Rationale:** the first power analysis (below) showed the real bottleneck is the unwired skater NPV engine and the never-estimated discount rate — not the back-test items (old P4-P6) the queue previously prioritized. Phase 1 now sits ahead of everything else.

**Phase 0 — closed items**
- [x] Clause join finalized. CLOSED 2026-06-19. (Fixed pre-existing Craft drift 2026-06-30: Craft still showed this in-progress.)
- [x] Goaltender WAR wired into the model, observed seasons (2015-2025). CLOSED 2026-06-30. See Player Model section below.

**Phase 1 — model spine [CLOSED 2026-07-05, all four sub-phases]**
Reproducible on both machines (Thomas's local run matches: `[1a] max diff $0.00`, full sweep 2,909 contracts). The model now produces real, discounted, contract-level NPVs for both positions.
1. **1a — discount rate r: CLOSED.** Structure locked (D15-D18): survival-weighted value side + 3% cap-growth denominator, fundamentals-only (GM impatience excluded, D15). Exit hazard h estimated from the panel (`exit_hazard.py`): established players barely exit (star 1.1%, regular 0.9%/yr), fringe/negative much higher (10.3%/19.4%), compounding with age. Goalie hazard estimated separately (11.55%/yr overall). No behavioral discounting — GM over-discounting is a back-test FINDING, not an input.
2. **1b — skater Value_t: CLOSED (both layers).** Layer 1 (`skater_value_engine.py`) → `skater_value_spine.csv`, 6,892 priced skater-seasons. Layer 2 (`skater_forward_projection.py`) → forward projection from any valuation season via the D3 decay path, D12 v3 negative-anchor handling, D11 ex-ante ceilings, D10 floor. k=0 reproduces Layer 1 exactly ($0.00).
3. **1c — RFA terminal value: CLOSED.** `rfa_terminal_value.py` → UFA expiry TV=0; RFA expiry walks the Layer 2 projection through control years vs iterated CBA qualifying offers (era-aware bands, D13 truncation, D14(c) empirical qualify-gate calibration). QO mechanics assert-self-test on import.
4. **1d — contract NPV summation: CLOSED.** `contract_npv.py` stacks Layer 2 + terminal value + survival weights + 3% denominator into one NPV per contract, both positions. Output: `contract_npv_spine.csv`, 2,909 contracts priced (2,591 skater, 318 goalie). Smell tests pass emphatically — bottom 5 by NPV are the consensus albatrosses (Karlsson/Doughty/Huberdeau/Price + Rantanen-2025 on an honest single-provider −0.76 WAR read); top contracts are cheap ELC/bridge deals. Goalie engine (`GoalieProjector` inside `contract_npv.py`): flat projection, self-calibrated goalie rate recovered from the spine at startup, λ convention corrected (D19).

**Phase 2 — power analysis (first run done, must re-run later)**
- [x] First run DONE 2026-06-30. See Power Analysis section below. **Must re-run after Phase 3 closes** — today's count was taken against an almost-unbuilt model.

**Phase 3 — remaining pillars, re-ordered**
- 3a (steps 1-2). Draft-pick yield curve — **CLOSED 2026-07-19 (D22-D27).** Linkage (draft_pick_linkage.py v1.1: 4,765 picks, guarded ID+name resolution) and curve (draft_yield_curve.py v1.1: cap-share surplus over D+1..D+9, cohorts 2007-2017, Rule A canonical) built and reproduced locally. Outputs: draft_pick_linkage.csv, draft_pick_outcomes.csv, draft_yield_curve.csv.
- 3a (step 3). **Price actual traded picks through the locked curve — NEXT.** Design batch owed before build: (1) future-pick discount premium (deferred flag comes due — premium may cover only arrival delay + team-identity uncertainty, never bust risk twice, Karl-sensitive), (2) unknown-slot convention, (3) conditional/protected picks. Also closed en route: the old 4d linkage task (done as step 1; raw ID coverage 99.9%, the recorded 94% was the spine-join rate).
- 3b. Elite Prospects production pull (verify slug crosswalk first). Now SECOND.

**Phase 4 — back-test engine (folds in old P4, P5, P7)**
- 4a-i. Game-level model chain (scraper -> on-ice -> xG -> score state -> metric assembly). **[CLOSED 2026-07-03]** — see Game-Level Model section below.
- 4a-ii. Mid-season allocation application: split each back-test trade's season value around the trade date using `player_game_value`. [NEXT within Phase 4 — small, engine exists]
- 4b. Circularity fix: validate the model's projections vs the non-Bacon game-level metric. **[PRIMARY VALIDATOR RUN — CLOSED 2026-07-14.** Tier 1 player-level design (Thomas's call; trade-level Tier 2 deferred until draft/prospect components exist). trailing_war(t) vs GV-adj wins(t), win units only (goals ÷ pooled 5.903 — no dollars on the outcome side, so the Bacon-derived rate never touches the benchmark). n=6,027 player-seasons (88% ID-to-ID join via spine nhl_id ↔ GV player_id), Pearson r=0.576, Spearman 0.460, OLS R²=0.331; stable r=0.55–0.61 in every one of nine seasons; secondary t+1 horizon r=0.538 (n=4,988). Forwards r=0.648/R²=0.421 vs defencemen r=0.302/R²=0.091 — the same structural defensive-measurement gap from the 2026-07-04 battery, expected and documented, not new. **Framing locked (Thomas): descriptive convergent validity, NO post-hoc pass/fail threshold** — no bar was pre-registered for this run, so none is retrofitted. Script: `gv_4b_circularity_check.py`; outputs in `gv_4b_outputs/`. **Robustness leg RUN 2026-07-14 — 4b FULLY CLOSED.** GV-raw (both variants, regular season only, `gv_4b_robustness_check.py`): rebased r=0.609/R²=0.371, zero-sum r=0.564/R²=0.318 — bracketing the primary; F/D split replicates (F 0.663/0.642 vs D 0.442/0.277, rebased-D flagged as inflated by the documented rebase mechanism); t+1 degrades gently in all variants (0.565/0.530). Three independent validators now agree in a 0.56-0.61 band.]
- 4c. Standalone cap-retention pricing (~51 three-team deals). Self-contained — can run in parallel with any phase from here on.
- 4d. Draft-pick-to-player linkage via the NHL Records API (`records.nhl.com/site/api/draft`; 13,152 picks 1963-2026, 94% carry an nhl playerId joining the PuckPedia spine ID-to-ID, zero name matching). **Approved 2026-07-03** for the prospect/draft pillars — a factual historical record, distinct from Bacon's locked valuation curve; feeds Phase 3.

**Player-model review — Stages 1-5 [ALL CLOSED 2026-07-28]**
- Stage 1: **CLOSED 2026-07-27** (all ten items; see the Stage 1 section above).
- Stages 2-5: **CLOSED 2026-07-28** (every numbered item across all four remaining stages; see the "Player Model Review — Stages 2-5" block in Resolved Decisions for the full item-by-item record — the price equation rebuilt (censored, position-interaction, no length term), the retention calibration's selection bias fixed, the draft curve rebuilt on the new rate, and all seven Stage 5 documentation items closed).
- **Verification gap — CLOSED 2026-09-09.** All Stage 1-5 changes now run locally and reproduced: the rebuilt draft curve (to the cent), the goalie spine (byte-identical), and the Stage 2 length-term null test (`term_premium_test.py`, decisive null confirmed — every spec constant reproduces, main-spec f = −0.0135 CI contains zero, value-side share 0.000). GV-raw robustness legs of the Stage 2 test are an optional extension, not run. See the DECISIONS.md verification-gap entry.
- **Regenerate the downstream spines — DONE 2026-09-09.** `contract_npv_spine.csv` (2,981 contracts) and `contract_npv_panel.csv` (6,939 rows) rebuilt on the desktop machine after the path migration; both are current. The Phase 4b circularity outputs are NOT keyed on contract-level NPV (v2.9 change-log correction) — they correlate skater trailing projections against the GV yardstick at player-season level and did not need regeneration.
- Review roadmap is now fully worked. Next substantive work reverts to the Work Queue's Phase 3b/4 items below (Elite Prospects pull, mid-season allocation application, standalone retention pricing, traded-pick pricing).

**Phase 6 — documentation**
- [x] Efficient-market null stated in Open Questions as a possible finding. **DONE 2026-07-28.** Written out in full: the null itself (the market prices all three asset classes correctly on average, so measured surplus differences are noise around zero with no systematic pattern by asset class, contract length, player age, or team competitive position), the conditions under which it holds (surplus ratios averaging 1.0 with no category deviation surviving correction for the number of categories tested), why a null result stays publishable (the contribution is the common surplus-dollar currency across three asset classes, which stands either way), and the power caveat (failing to reject is weaker evidence than rejecting, and the power analysis has not been re-run since Phase 3 opened).


**Review follow-ups (2026-09-09, not a queue reorder).** Assess the Rule B defence-cost slope mismatch and aging global self-inclusion described in `40_DOCS/Repository_Review_and_Doc_1_Edits.md`; review the proposed Doc 1 passages and the signed allocation rule. A change to the locked surplus-ratio statistic requires a deliberate revisit. No code or model changes made in this review.

**Doc 2/5 review completed (2026-09-10d):** Agreed corrections applied to supervisor copies; user read-through and visual pagination remain. Source-description follow-up: aging_split_sample.py advertises a fitted-profile comparison that main() does not implement. Its published 0/16 and 1/16 counts concern observed within-player deltas only. No new test or production change in this session.

- **2026-09-10e Doc 2 formatting:** User-edited Downloads copy incorporated into Supervisor_Drafts with consistent fonts, heading hierarchy, and spacing. Text preserved exactly; core checks pass; visual pagination remains unverified. See `sessions/2026-09-10e.md`.

- **2026-09-10f:** Supervisor Docs 3-5 edits complete; user read-through and visual pagination remain. Review the effect of terminal qualification probabilities restarting at one without signed-contract survival carried into control years. Existing QO timing and Rule B slope issues remain open.

**Rebuild repair sequence (opened 2026-09-15b, after the independent review and the response to it).**
Agreed order, with the holdout item pulled forward at the reviewer's request. Items 1 and 2 are
done and demonstrated by `50_REBUILD/code/repair_checks.py`, which fails on the pre-repair code
and passes on the repaired tree. Each dollar figure in the candidate reports stays withdrawn
until items 3 to 5 land and the chain is refit.
1. **Units — DONE.** Per-82 rates now built from the raw total with D20 applied after the
   aggregation, so the season identity holds on all 17,050 played rows; games scored on the
   outcome season's own schedule.
2. **Guards — DONE.** Unfitted horizons refused, the fitted range named once, the harness
   validates the exact requested grid, the named-player runner requests the whole term.
3. **Holdout inventory and enforcement — DONE.** See `50_REBUILD/docs/Holdout_Inventory.md`.
   Forecast holdout intact; market holdout spent. **Decision owed:** what the market holdout
   should be, given that the obvious candidate has already been consumed. Three routes are set
   out in that file. The enforced boundary mirrors the forecast pages as a proposal, not a lock.
4. **Eligibility and the participation event — DONE 2026-09-15b.** Decision owed: games
   weighting of cameo rates versus a separate low-production state. Was: Move participation to the plan's
   one-game event, make the rate and games targets condition on the same event, keep returning
   players with an explicit stale-history tier, and define the age bands at the valuation date
   rather than the last observed season.
5. **Market dating and dollars — DONE 2026-09-15b.** Signing-date coverage verified independently at
   3,550 of 3,550, so no fallback rule is needed. Date each market fit at the signing date and assert the
   latest training signing precedes the valuation; signing-date coverage is confirmed at 3,550
   of 3,550 on the eligible sample, so no fallback rule is needed. Build the date-aware cap
   path with the announcement cutoff, 3% extrapolation and the discount schedule.
6. **The production adapter, and the corrections — DONE 2026-09-15b.** The false
   attribution appears in the reports, in model labels, and in executable log output, so a
   rerun regenerates it. The adapter is validated by agreement with production's individual
   forecast rows under the same settings, not by reproducing 24% on a different population.
7. **Refit and rerun the development comparisons — DONE 2026-09-15b.** Star residual is
   inverted, not fixed; young-player residual improved and still worst. Was:, then revisit the star and young-player
   residuals. The stress battery and the confirmatory work follow the refit.
**Coverage decision owed alongside item 4:** the fitted range is six seasons and real contracts
run longer. The guards refuse the gap rather than filling it, so pricing a seven- or eight-year
deal needs either fits extended to those horizons or a declared and tested extrapolation.

**Rebuild repair, second verification closed (2026-09-15b).** Named-player runner routed through
the repaired valuation path; extrapolation made endpoint-invariant; attachment horizon ceiling
removed with rejections recorded. Suite at 15. Still open and unchanged: predictive distributions
and interval coverage, subgroup reporting by horizon, the trade-date update, joint simulation,
control-year treatment, goalies, end-to-end dollar reconciliation, the full-chain leakage and
export-break tests, once-only ledger enforcement, the announced later cap ceilings, and the market
holdout policy.
