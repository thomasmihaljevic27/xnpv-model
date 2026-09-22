# WORK QUEUE — NHL Trade Market Efficiency

<!-- Extracted from PROJECT_STATE.md on 2026-09-09 (v3.2 restructure). Pure move, no content change. -->
<!-- The full list of yet-to-do work, phase-sequenced. Changes almost every session.
     Detailed sequences for individual pillars live in 01_Draft_Model_Sequence.md,
     02_Prospect_Model_Sequence.md, 03_Player_Market_Model_Sequence.md. -->

---

## Work queue

**Goalie rate review open, 2026-09-22:** reviewed `0bec937` in isolation.
36/36 passes and published rate/season/price comparisons reproduce. One P2 repair:
price consumer and scored FlatShare arm use different trailing-share fallbacks
when a horizon has no share fit. 435 conditional forecast cells differ; aligning
paths changes 8/165 contract forecasts, maximum .00760 WAR per season. Price
level-only MAE .008503 becomes .008504 on the same 137 contracts; conclusion holds.
Share a conditional-forecast rule and add consumer parity guard before closure.
Production remains the stronger season point benchmark (RMSE 2.073 vs 2.099 for
rate/share); carry rate as sensitivity. Squared error primary for means, alongside
MAE, subgroup bias and dollar/distribution validation. Weighted rate targets and
joint rate/workload assumptions need explicit definition. Pricing and D7 provisional.
See `50_REBUILD/docs/Goalie_Rate_Review_Codex.md`. Prior closures stand; no adoption,
model changes or candidate merge.

**Goalie participation review closed, 2026-09-22:** verified `8d1efc6` in isolation.
35/35 passes; Brier .2056 and WAR MAE 1.432 reproduce. Signing dates flow through
per-row prediction; reordered duplicate-player batches and future-contract tests
pass. Three deliberate defects caught. All 32 goalie optimizer inputs full rank;
three goalie and fifteen contract-using skater fits drop redundant columns, none
without contracts. Corrected price level-only MAE .007017; extra slope wins 22%.
Bias claim corrected. Close preceding findings; proceed to goalie rate experiment.
Skater contract-data decision stays open: corrected Brier .1326 vs .1340 without,
WAR gaps +.03% to +.27%, only h2 interval excludes zero. Keep current leader until
its exact configuration is compared with/without contracts and valued downstream.
Dropping unknown status imposes an extrapolation assumption on absent training
categories; it does not identify their separate effects. Pricing and D7 provisional.
See `50_REBUILD/docs/Goalie_Participation_Repair_Closure_Codex.md`. Earlier closures
stand. No model edits, candidate merge or adoption.

**Goalie price-line review closed, 2026-09-22:** verified `af61f6c` in isolation.
Full suite 33/33; all 68 executed fits converge. Same 174 goalie contracts:
no terms MAE .010318, level-only .007457, level-and-slope .007489. Additional
slope wins only 10% of career resamples; equality of slopes and D7 remain unsettled.
Whole-path annual price responses reproduce ($2.022M/$2.167M UFA,
$1.928M/$2.073M RFA), checked against direct equation changes and nonzero
synthetic coefficients. Three check-33 mutations caught. Counts 263 eligible,
205 forecast-attached, 174 priced; expanding quarterly fits verified. Bias
illustration correctly qualified. All preceding price-line findings closed;
proceed to participation with provisional price specification. Distinguish any-NHL
participation from workload conditional on playing, and reassess pricing when the
forecast changes. See `50_REBUILD/docs/Goalie_Price_Repair_Closure_Codex.md`.
Earlier closures stand. No model edits, candidate merge, adoption or back-test.

**Goalie forecast review closed, 2026-09-17:** verified `e42f57c` in isolation.
Full suite 32/32; seven candidates, 3,683 cells each. Imported projector agrees
with the independent source-class calculation within 1.78e-15 WAR; replacing future
WAR changes none of 629 goalie/page forecasts. Correct page pairing and responsive
age term verified; all four reintroduced defects are caught. The preceding three
findings are closed. Proceed to the goalie price-line prototype using production's
projector provisionally. Its MAE is 1.48784 versus fitted weight 1.49123; the paired
interval spans zero. Observed +.10062 WAR bias is a diagnostic, not an established
price adjustment: goalie-cluster mean-error interval [-.12155,+.31314], and shared
participation averages .64098 predicted versus .55254 observed. Assess any correction
with participation and development scoring. Seasonal lookup dating does not date the
locked production calibration constants for historical valuation. See
`50_REBUILD/docs/Goalie_Repair_Closure_Codex.md`. RFA/simulator/reconciliation closures
stand; goalie participation, control gate, dollars, and back-test remain open. No
production/model edits, candidate merge, adoption, or confirmatory-page access.

**Reconciliation review closed, 2026-09-16:** verified `76730b6` in isolation.
Actual runner prices 1,141 contracts; all hazard effects agree exactly with the
independent per-season audit. Fresh engine summary now supplies total/terminal NPV.
Both negative tests fail: +$1M saved totals rejected on all 1,141; detail-only season
value corruption rejected naming contract 3702. Revised asset/date flags reproduce
912/217/695; strict eight-year cell has five and is explicitly flagged too small.
Both preceding findings are closed. Proceed with remaining valuation development.
This diagnostic still compares different information dates and does not validate
outcomes or complete Phase 5. Input exceptions and remote goalie hash remain disclosed.
See `50_REBUILD/docs/Reconciliation_Review_Closure_Codex.md`. No candidate merge,
model edits or source changes; unrelated files preserved.

**Reconciliation repair verification, 2026-09-16:** reviewed `1a6ba0d` in isolation.
Corrected hazard effects reproduce within $3.85e-09 per contract; wrong-ID, season,
terminal and cost flags reproduce. All three prior integration mutations now fail.
Two narrow items remain: the new reconciliation combines fresh engine detail with
saved-spine total/terminal values; a +$1M saved-total mutation is accepted and produces
1,043 negative hazard effects. Use the same call's summary and assert invariants.
Also, 912 means passes the structural/cost screen, not every test: 217 fail the date
flag; 695 pass both, still without proving same information dates. Rename the screen
and retain the date limitation explicitly. Six-year screening loses two contracts;
other four-to-eight-year cells survive the structural screen, not a same-date test.
See `50_REBUILD/docs/Reconciliation_Repair_Verification_Codex.md`. Prior simulation
closure remains valid. Further development can proceed; no model redesign requested.
No candidate merge, implementation edit, or production/source changes.

**Valuation integration review, 2026-09-16:** reviewed `bc724e5` including `1752a0e`.
Production chain reproduces in isolated output: regression guards, 6,892 skater rows,
$0.000284 goalie parity, 2,981 contracts and the recorded NPV distribution. Local
regenerated goalie v2 matches the locked MD5 exactly. Integration writes 1,217 x 31,
with 1,141 production matches. Reconciliation is not closed. The claimed survival
effect also removes discounting; holding discounting fixed gives +$1.69M at six years
and +$2.29M at eight, not +$0.76M/-$0.58M. Ten joined production rows actually value
another contract, 185 include terminal control value absent from the rebuild, dates
differ, and cost-input discrepancies need explicit reconciliation. Consumer guards
accept a mismatched simulation baseline, duplicate production IDs and reserved cohorts.
See `50_REBUILD/docs/Valuation_Integration_Review_Codex.md`. Correct decomposition,
reconcile identities/dates/costs/terminal scope and enforce artifact invariants before
closing this acceptance item. Prior simulation repairs remain closed. No model patch,
candidate merge or source changes; only isolated generated outputs and review records.

**Simulation repair review closed, 2026-09-16:** verified `db0c6b2` in isolation.
Full suite passes 25/25. All 605 one-year contracts now have exact path/SD equality;
shared participation uniforms reach all three arms. Check 25 passes normally and
fails both with page_dependence disabled and with latest-page selection restored.
Both preceding findings are closed; proceed with valuation integration. Full run:
1,217 contracts, 223 sign changes, $182,944 mean uplift; eight-year average within-
contract SD $11.012715M with returns versus $11.074470M absorbing. Shared draws reduce
comparison noise but do not eliminate multi-year Monte Carlo error. Phase 5 remains
open for RFA/control years, goalies, joint-path scope, dollar scoring and reconciliation.
See `50_REBUILD/docs/Simulation_Review_Closure_Codex.md`. No model patch or merge;
unrelated files preserved.

**Simulation repair verification, 2026-09-16:** reviewed `8239d29` in isolation.
Reproduced 25/25 checks, 1,217 simulations, 228 contract sign changes and the
$11.02M/$11.09M eight-year return/absorbing spread comparison. Dated calibration
selection, rank-to-Gaussian conversion and return-capable participation are repaired.
The 600,000-path self-test passes and restoring the conversion bug fails analytically.
Two narrow items remain: participation draws are not shared between comparison arms
(the one-year contrast is -0.1057%, not exactly zero), and check 25 bypasses the
runner whose date selection caused the original leakage. Correct those and regenerate
sensitivities; remaining valuation integration can proceed. Clipping affects two
contracts by at most 0.381 percentage points of playing probability, documented as a
small exception. Phase 5 remains an aggregate prototype with RFA/control-year, goalie,
joint-path, dollar-scoring and reconciliation gates open. See
`50_REBUILD/docs/NPV_Simulation_Repair_Verification_Codex.md`.
No candidate implementation changed or merged; unrelated files preserved.

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

**2026-09-22f — the goalie rate forecast: a better rate, not a better season.** Built
`run_goalie_rate.py` (report `50_REBUILD/docs/Goalie_Rate_Forecast.md`). A per-82 rate, pooled by
games over three seasons and shrunk toward a norm, beats production's implied rate as a per-game
forecast (100%). Production's shrunk **season total is still the more accurate season forecast**
(MAE 1.432 against 1.439 or more; RMSE 2.073 against 2.098 or more, rate arms losing in 98-99%) and
ranks goaltenders better at every horizon. The **decomposition (rate x share x participation) is
better calibrated**: bias +0.030 against +0.096, and flatter by role. With a real rate the share model
helps squared error (lower in 66-70%) and still hurts absolute error. The role term in the norm
earns nothing. The price line with the decomposed forecast: level-only error 0.008503 against
0.008635 on 137 common contracts (68%); the slope still fails (28%); the UFA ratio moves again
(0.73 -> 0.81 on the subset). Suite 36/36. Nothing adopted.

**DECIDED 2026-09-22 -- which goalie forecast, and on what score.**
- **Default:** production's season total, which is more accurate on both scores and ranks better.
- **Sensitivity:** rate x share x participation, carried into the control-year work.
- **Scoring hierarchy, declared before the next comparison:**
  1. squared error is primary for forecasts of expected values;
  2. mean absolute error is reported alongside;
  3. so is bias by horizon and by role or tier.
- **WAR accuracy is not dollar accuracy.** The floor and control options are nonlinear, so the
  eventual choice is tested on expected dollars and simulated outcome distributions.

**2026-09-22g -- repair.** The price runner and the scored arm now share one conditional forecast
(`ConditionalSeason`). Check 37 asserts they agree on every page and horizon. 8 contracts moved by at
most 0.0076 WAR per season, and no conclusion changed. Suite 37/37.

**Next (unchanged sequence):** the goalie control-year gate. It needs a goalie forecast per
contract-season, so it runs on production's total (the default) and on the decomposition (the
sensitivity), scored by the hierarchy above. It reports expected dollars, not only WAR. Any joint
rate-and-workload path defines its target first: rate times share is the expected season only if the
two are uncorrelated given the record.

**2026-09-22d — repairs for the goalie participation review (closed by review, `e8bedb4`).** All four
requested items are done; the review stays open until it is independently re-checked.

1. **The numerical discrepancy is reconciled.** Singular participation designs (the two contract
   columns exact mirror images whenever every known player is under contract) were being resolved by
   the optimiser in a platform-dependent way. `participation_model.py` v1.5 drops redundant columns in
   a fixed order. Corrected goalie figures: Brier **0.2056** (flat 0.2470), season WAR error **1.432**
   (stand-ins 1.488), pooled bias +0.096. The reviewer's machine is inferred, not observed, to have
   taken the other branch.
2. **Signing-date contract state** in the goalie price runner (v2.2): 95 of 205 contracts move;
   Gillies 44.4% -> 92.7% and 41.2% -> 99.5%. **Known gap:** first season predicted 0.822 against
   0.761 played (second season 0.797 against 0.794). Refitted: level only 0.007017 (beats none 100%),
   slope 22%, whole-path UFA ratio **0.79**. Specification provisional; D7 not settled.
3. **Checks 34 (rewritten) and 35 (new)**, each mutation-tested. Suite 35/35.
4. **Bias claim corrected** in the 22b entries below.

**OPEN DECISION (Thomas) -- should the skater leader fit participation with contract data?** The same
rank defect sat in fifteen skater fits of the contract-using variants and is where Phase 2's "contract
data hurts" came from. Re-measured (`run_contract_ablation.py`): before the fix +0.45% to +0.98% worse
WAR error at one to five seasons out; after it +0.03% to +0.27%, with only two seasons out clear of
zero, and participation Brier better with contracts (0.1326 against 0.1340). The finding is withdrawn
in conclusion. The leader fits without contracts, partly on that finding; with contracts is now a near
tie on WAR and better on participation. Not changed here -- a leader change is a deliberate decision,
and it would move every downstream skater number. **Review recommendation (2026-09-22, closure of `8d1efc6`):** keep the
current leader, and test an otherwise identical leader with contract data, including downstream
dollar values, before any switch. The ablation used a different ability configuration from the
leader, so it corrects the historical evidence without choosing between versions of today's leader.

**Next after verification:** the goalie rate forecast (per-82 shrunk toward a rate norm) so rate x
share x participation decomposes, then the price comparison again, then the control-year gate.

**2026-09-22b — the goalie participation model, and a birthdate that encodes the future.** The
next item. Whether a goaltender plays at all and how much he plays if he does are built and scored
as separate problems, with ability held at production's projector throughout.

**The main finding came from the first version failing.** Reused unchanged, the skater
participation model drops rows with no age. A goaltender's birthdate comes mostly from the contract
export, so having one means he was still playing in the contract era: on the 2019 page, goalie
anchors WITH a birthdate play at **0.908 / 0.902 / 0.894** zero, three and five seasons out, those
WITHOUT at **0.557 / 0.257 / 0.119**. The fit learned only from survivors, predicted about 0.87 at
every horizon against 0.72 falling to 0.37, and lost badly to the flat rate. The first share model
also carried a has-a-birthdate flag -- the future as a column. **Age is now excluded from both goalie
models** (`ParticipationModel(exclude=...)`), experience from the panel stands in, and check 34
asserts the fit keeps every anchor: its base rate equals the anchors' own played rate, which opens a
0.53 gap if age goes back in. Skaters have 98% coverage and are barely affected.

**Whether he plays:** predicted **0.580** against 0.553 observed (flat rate 0.641), Brier **0.2075**
against 0.2470, lower in 100% of goaltender-resamples; almost all the gain is in the first three
horizons. **How much, if he plays:** the share model beats the flat carry on the 2,035 played seasons
(0.1686 against 0.1801, 100%). **The season:** participation model with trailing share improves WAR
error from 1.488 to **1.437** (100%). **The share model makes season WAR worse** (1.581, 0%), and
the reason is structural: production's projector gives a SEASON TOTAL shrunk toward a starter-level
2.19, so dividing by a backup's small trailing share inflates his implied rate, and a correctly
higher share forecast (0.22 -> 0.34 for backups) multiplies the inflation -- backup bias +0.13 ->
+0.54. **Production's number cannot be split into rate x share; using the share model needs a goalie
RATE forecast**, which is next.

**The pooled bias did not move** (+0.100 -> +0.104). [CORRECTED after review: the entry said this
showed the bias sits outside participation, which does not follow -- average participation can
improve while errors for high- and low-production goaltenders offset differently in WAR. Supported:
the participation model improves accuracy but does not eliminate the pooled bias; its causes are
unresolved.]

**Price line refitted on the updated forecast:** every line more accurate; the level still carries
the improvement (100%); the slope is a coin flip (58%); and **the goaltender slope is unstable** --
the average goalie forecast moved -0.003 WAR yet the whole-path UFA ratio went from 1.07 to **0.75**
($2.128M skater, $1.603M goalie). Specification provisional; D7 not settled.

Suite **34 passed, 0 skipped, 0 failed**. Nothing adopted. Report: `50_REBUILD/docs/Goalie_Participation.md`.
**Next: a goalie rate forecast**, so rate x share x participation is a real decomposition.

**2026-09-22 — the goalie price line, corrected: a level, not a slope, and a defined response.**
Two conclusions from the 09-18b pass were ahead of the evidence, and the review was right about both.

**(1) The comparison left out the simpler answer.** It set no goaltender terms against a goaltender
level AND slope, and credited the gain to both. On the same 174 contracts:

| line | mean abs error | bias | better than the line above it |
|---|---:|---:|---:|
| no goaltender terms | 0.010318 | +0.006627 | -- |
| **goaltender level only** | **0.007457** | +0.000145 | **100%** of goaltender-resamples |
| goaltender level and slope | 0.007489 | +0.000140 | 10% |

**A different goaltender price level on the same win slope delivers all of the improvement; a
goaltender slope on top has not earned its place.** That is not evidence the slopes are equal -- 174
contracts cannot tell a small difference from none -- and **it does not settle D7**. The goaltender
specification is provisional while the participation model is built.

**(2) "Dollars per win" was a partial slope.** The coefficient on the season average holds first-year
production fixed and omits the restricted interaction. Defined explicitly on the last fit, as the
change in fitted annual price before the league-minimum floor (not a contract value):

| the change | skater $M | goalie $M | ratio |
|---|---:|---:|---:|
| partial slope, first year held (UFA) | 0.820 | 0.965 | 1.18 |
| **one more win every season, UFA** | **2.022** | **2.167** | **1.07** |
| one more win every season, RFA | 1.928 | 2.073 | 1.08 |

The goaltender gap is one coefficient ($0.145M) in every row, so the ratio depends on which change is
priced.

**Smaller:** the sample is **263 eligible -> 205 with a forecast -> 174 priced**, not 266; every line
uses the same expanding quarterly scheme, including the goalie-only one; and the +0.167 WAR
participation figure is an **illustration** of that term's scale, not a decomposition of the bias --
corrected in the forecast runner and its report.

Suite **33 passed, 0 skipped, 0 failed**; check 33 now also tests that the whole-path response moves
every term the forecast enters and that the level-only specification is its own line, verified by
substituting the partial slope. Nothing adopted. Report rewritten: `50_REBUILD/docs/Goalie_Price_Line.md`.
**Next: the goalie participation model**, with the price specification provisional.

**2026-09-18b — the first goalie price-line pass. ITS TWO-TERM AND 1.18 CLAIMS ARE WITHDRAWN;
see the 2026-09-22 entry above.** The goalie branch's second step, and the question that decides whether
goaltenders can sit on the project's single scale at all.

One censored line over skaters and goaltenders together, with a goaltender indicator and an
interaction, refitted at each signing quarter on contracts signed before it. **The interaction IS
the difference in dollars per forecast win.** The forecast feeding it is production's own projector,
the bake-off's winner; its +0.101 mean error is NOT corrected and no price is moved to cancel it.

| fitted on contracts signed before | n | $ per skater win | $ per goalie win | ratio |
|---|---:|---:|---:|---:|
| 2018-07 | 365 | 0.212 | 0.264 | 1.25 |
| 2019-10 | 947 | 1.316 | 1.321 | 1.00 |
| 2021-01 | 1,270 | 0.899 | 1.047 | 1.16 |
| **2022-01** | **1,657** | **0.820** | **0.965** | **1.18** |

**[CORRECTED 2026-09-22: these are partial slopes with first-year production held fixed, not
dollars per win; the whole-path ratio is 1.07]** A forecast win from a goaltender prices at $0.96M
against $0.82M from a skater on the last fit.
The ratio runs 0.74 to 1.57 across the window, but the spread is almost all in the early fits: under
about 600 contracts the interaction is not pinned down, and from 900 on it settles between 0.87 and
1.22. **A conditional association and not the price of a win** -- nobody randomised who got which
contract, and a goaltender's forecast is built by a different rule from a skater's (flat where the
skater ages, shrunk far harder, 82 seasons a year), so part of any slope difference is that
difference.

**Held-out error on goaltender contracts, in cap share:**

| line | goalie contracts | mean abs error | bias |
|---|---:|---:|---:|
| one line, no goaltender terms | 174 | 0.0103 | +0.0066 |
| **one line with goaltender terms** | **174** | **0.0075** | **+0.0001** |
| a goalie-only line | 5 | -- | never fittable |

**[WITHDRAWN 2026-09-22]** This entry credited the gain to both goaltender terms and called the
result "one market with two terms". The comparison left out a goaltender LEVEL alone, which on the
same 174 contracts delivers all of the improvement; the slope has not earned its place and D7 is not
settled. The sample figure of 266 is also wrong (263 eligible, 205 with a forecast, 174 priced).

`contract_price_model.contract_sample` now takes a position group rather than assuming skaters, so
both samples come off one census with one set of rules for the denominator, the floor and the
signing date. Suite **33 passed, 0 skipped, 0 failed**; the new check recovers a synthetic goalie
slope (0.0049 against 0.0050 given) and refuses a contract signed after the decision, both verified
by breaking them. Nothing adopted. Report: `50_REBUILD/docs/Goalie_Price_Line.md`. Next: the goalie
participation model -- a goaltender's share of the schedule is a depth-chart question and both the
forecast and this price line carry a flat survival rate in its place.

**2026-09-18 — the goalie comparison is corrected, and production's own projector wins.** Three
findings from review, all real.

**(1) The benchmark was not production.** The first pass rebuilt production's cascade from a
reading of `contract_npv.py` that stopped halfway through the method, and it was missing three
mechanisms: production's lookup table has **no games filter**, its cascade fills the t-1/t-2/t-3
slots **strictly** and sends a goaltender with no t-1 season to a **stale anchor** computed at an
earlier standpoint, and that stale-anchor population shrinks toward **0.650** rather than the league
average. The reimplementation is up to **2.28 WAR** away from the real thing on a single goaltender.
The candidate now imports the class and calls it, as the qualifying-offer bands already do.

**(2) The bootstrap paired across years.** Joining on goaltender and horizon without the page
matched a 2015 forecast to a 2021 one: 3,683 intended pairs became 19,853 rows, reweighting toward
goaltenders who appear on many pages.

**(3) The ageing candidate never used age.** It took the INTERCEPT of its own regression -- the
average change at the pivot age -- and applied it to everyone; adding twenty years to every subject
moved nothing.

**Corrected, mean absolute error in season WAR over 3,683 forecasts:**

| rule | MAE | bias | beats production |
|---|---:|---:|---:|
| the league average | 1.634 | +0.092 | 0% |
| **production's own projector (imported)** | **1.488** | +0.101 | -- |
| a simplified cascade, keep 0.35 (the old "production") | 1.582 | +0.218 | 0% |
| the same on the page's own average | 1.511 | +0.045 | 1% |
| the same, kept weight fitted (0.43) | 1.491 | **+0.036** | 34% |
| shrunk by the games behind it | 1.585 | +0.164 | 0% |
| with a fitted age slope | 1.552 | +0.034 | 0% |

**Nothing beats production's projector**, and the claimed improvement is withdrawn: the closest
candidate is 0.003 WAR worse and wins a third of resamples, which is a tie. **The bias is a
DIAGNOSTIC, not an established defect** [qualified 2026-09-18 after review]: production's +0.101
mean error has a career-bootstrap interval of **-0.129 to +0.315**, which contains zero, and the
shared participation estimator predicts **64.1%** of these seasons played against **55.3%**
observed -- a gap that, priced at a flat 1.89 WAR per played season, comes to **+0.167 WAR**: an
ILLUSTRATION of the participation term's scale and not a decomposition of the bias [qualified
2026-09-22] -- carried by every candidate. So the pooled error cannot be attributed to any ability forecast, only the
difference between two candidates' biases can, and **nothing downstream should move a dollar price
to cancel it**; it belongs with the participation model. Weighting by workload is the clear negative
result (+0.097, 0%).

**On ageing, the earlier claim is withdrawn and replaced.** Fitted properly there are two
coefficients and only one is about age. **The age slope is negative on every page** (-0.005 to
-0.088 WAR a season per year of age): older goaltenders decline faster, on every window this run
has. What flips sign is the **drift**, the level the whole population moves by, from +0.117 in 2015
to -0.106 in 2021 -- not an age effect. So there is no basis for saying ageing is unidentified here.
Using the slope still does not beat production (+0.065, 0%), which is a statement about this
implementation on 82 seasons a year.

Suite **32 passed, 0 skipped, 0 failed**; two new checks, and all four reintroduced defects caught
(a lookalike in production's place, the two rules coinciding, the pairing dropping the page, and the
age term reverted to the intercept). Report rewritten: `50_REBUILD/docs/Goalie_Bakeoff.md`. The
forecast to carry into the price line is **production's own projector**, with its +0.101 mean error
recorded as a diagnostic to re-examine alongside the participation model.

**2026-09-17f — the first goalie pass. ITS COMPARISON WAS AGAINST A LOOKALIKE AND ITS
IMPROVEMENT CLAIM IS WITHDRAWN; see the 2026-09-18 entry above.** The
next declared item. The rebuild had no goaltenders in it at all, so the first question is whether
forecasting one works on this evidence and whether the rule production uses survives being scored
the way every skater candidate has been.

**The panel.** `goalie_season_table.py` (new) builds the goalie season table in the skater table's
schema, so the information set, the harness and the scoring work on it unchanged, reusing the
skater rules rather than restating them. **1,560 goaltender-seasons, 280 goaltenders, 2007-2025 --
82 a season against roughly 700 skater-seasons.** Three real differences: one WAR number and no
component split, so the component forecast that won the skater bake-off has nothing to work on; a
goaltender's games are a ROLE and not availability (median share 0.44, and 0.67 among 40-game
goaltenders), which anything reading `gp_share` later has to say first; and **no goaltender in this
panel has ever played 82 games**, the busiest season being 77.

**The bake-off.** Six candidates on the same grid, sharing one participation estimator so the
comparison is about ability, mean absolute error in season WAR on development pages:

| rule | MAE | bias | beats production |
|---|---:|---:|---:|
| the league average | 1.634 | +0.092 | 3% |
| production's rule (keep 0.35, flat, avg 2.189) | 1.582 | **+0.218** | -- |
| the same, on the page's own average | 1.511 | +0.045 | **100%** |
| the same, with the kept weight fitted (0.43) | **1.491** | +0.036 | **100%** |
| shrunk by the games behind it | 1.585 | +0.164 | 78% |
| the same, with a fitted age change | 1.624 | +0.232 | 0% |

**[WITHDRAWN 2026-09-18]** The rule labelled "production's" in this table is a reimplementation
missing three of production's mechanisms, and it is 0.094 WAR worse than the real projector. The
improvement claimed here is against the lookalike, not against production. See the 2026-09-18
entry for the corrected comparison.

**[WITHDRAWN 2026-09-18]** The age candidate never used age -- it applied one common drift to
everyone -- so the sign flip reported here is in the drift and says nothing about ageing. Fitted
properly the age slope is negative on every page.

Suite **30 passed, 0 skipped, 0 failed**; the two new checks each verified by breaking the rule they
guard. Nothing adopted. Report: `50_REBUILD/docs/Goalie_Bakeoff.md`. Next in the branch: a goalie
price line and a participation model, in that order, before the control-year gate the plan asks for.

**2026-09-17d — the control-year pass is repaired; the information premium is $0.066M, not
$0.27M.** Four findings from an independent review, all real, all now fixed.

**(1) A future decision was removing the right.** The export's expiry status records what the club
eventually did: "UFA no QO" is a club that declined to qualify the player, YEARS after the signing
being valued, and it is the very decision the stopping rule exists to make. 101 contracts were
dropped on that label and 45 more on a plain "UFA" label despite listing a later eligibility year.
Ownership is now **eligibility alone**; `control_span` cannot see the label and the suite asserts
it. The sample goes from 252 contracts to **398**. Eligibility itself is audited: the export's year
matches the age-27 rule exactly on 89.3%, is earlier on 130 (the accrued-seasons route, which for a
player short of seven runs partly through seasons not yet played), and is never later. The whole
sample is priced again on the age rule alone, which needs only a birthdate: **+$0.026M a contract**,
so that exposure is bounded at under 4%.

**(2) The club was seeing shocks from seasons the player missed.** Those misses exist in the
simulator and nobody ever observed them. The review measured it: changing only the hidden shocks
moved the first control year's decision on 188 of 252 contracts and flipped 26,519 path decisions.
The rule now conditions on the misses of **played** seasons and integrates the rest out, which is
exact rather than approximate because the joint law is Gaussian and participation is independent of
it. Seeing a played season's production is the same as seeing its miss because the shape is
monotone, now asserted.

**(3) A historical valuation was using future offer bands.** The floor was dated; the 2026 regime
switch was not. The agreement was ratified in the summer of 2025, so a 2021 signing pricing a 2026
control year sees $1.00M on a $1M salary, not $1.10M.

**(4) The headline compared three changes at once.** The informed rule stopped at the first
expected loss while the ceiling counted later years, and it averaged prices while its baseline
priced the mean -- and the league-minimum floor makes those differ even with no information. Six
rules now sit on the same draws, each differing from its neighbour in ONE thing, $M a contract over
398: take every year 0.281, production's rule 0.442, decide in advance 0.637, myopic informed
0.702, decide as you go 0.703, knew the path 0.901.

| the comparison | what changes | $M |
|---|---|---:|
| decide as you go vs decide in advance | the information only | **+0.066** |
| decide as you go vs myopic informed | two specified policies, NOT the option | +0.001 |
| the right vs the obligation | being able to walk away | **+0.422** |
| decide as you go vs production's rule | all three at once, NOT an option premium | +0.261 |

**The largest number is not about information at all**: being able to walk away is worth $0.422M a
contract, six times what the club's information is worth.

**A finding about production, not only about this module.** Production's `rfa_terminal_value.py`
reads the same expiry column the same way -- its docstring states that "UFA no QO (team already
declined to qualify) -> terminal value = 0". Of the 187 contracts where production carries no
terminal value while this tree finds a right, **130 carry a label production zeroes outright: 97 "UFA no QO" and 33 plain "UFA"**. Flagged.

Suite **28 passed, 0 skipped, 0 failed**, with each of the four defects reintroduced and caught.
Report rewritten: `50_REBUILD/docs/Control_Years.md`.

**2026-09-17c — the first control-year pass. ITS $0.27M HEADLINE IS WITHDRAWN; see the
2026-09-17d entry above.** The first item of the remaining valuation work. `control_years.py` and
`run_control_years.py` (new) price the seasons a club still owns when a contract expires with the
player still restricted. **252 of the 1,217 development contracts own at least one** -- 133 of them
one-year deals, 86 two-year -- which is exactly the population where the rebuild sits below
production in the reconciliation.

**Control is a right, not an obligation, so it is a stopping rule and not a stream.** Four rules on
the same draws, differing only in what the club knows when it decides, $M a contract:

| control yrs | n | take every year | decide in advance | decide as you go | knew the path |
|---|---:|---:|---:|---:|---:|
| 1 | 88 | -0.556 | 0.079 | **0.190** | 0.367 |
| 2 | 93 | -0.038 | 0.317 | **0.614** | 0.934 |
| 3 | 55 | 1.117 | 1.111 | **1.453** | 1.628 |
| all | 252 | 0.136 | 0.451 | **0.716** | 0.950 |

A club **forced** to take every control year loses money on the deals with one or two of them. The
same seasons with the right to decline are worth +$0.19M and +$0.61M. **[WITHDRAWN 2026-09-17d]** This entry called $0.27M the value of deciding as you go. It is the
gap against production's rule, which differs in three things at once -- pricing the mean rather
than averaging the price, deciding in advance, and stopping at the first loss. Against a baseline
that changes only the information, the answer is **$0.066M**.

**The club's decision cannot see the season it is deciding about.** It updates the forecast by the
misses already realised on the path, through the persistence the simulator already fitted,
integrated through the empirical shape rather than substituted into it, and it conditions the
chance he plays on whether he is in the league now. Scrambling every season from the decision
onward moves nothing, bit for bit; scrambling the past moves it at every horizon.

**The ceiling was wrong in the first draft and is fixed.** Stopping at the first bad year is not
what a club with perfect foresight would do, because the right dies when it walks away: on a path
worth +5, -1, +10 it sits through the bad year. The ceiling is the best prefix, which is never
below zero and never below any other rule.

**Against production:** 241 in both; production's terminal value means $0.894M against $0.409M for
the same declared rule here, on different information dates, rank correlation 0.547 declared and
0.759 informed. The 57 contracts production prices at zero are the D13 truncation and not a
disagreement about ownership -- the declared rule here gives zero on all 57 too.

**The weak point is the offer's base salary.** The formula runs off the final year's base salary
and this tree's source carries an average; measured against the season spine, 155 of 593 have a
final salary above the average, 90th percentile ratio 1.10. The average makes the offer too cheap
and the control year too valuable, and that is the direction.

Also: the league minimum is now dated the way the cap ceiling already was (only figures published
before the signing, 3% beyond), the published 2026-29 schedule is in the table, and the offer bands
are checked against production's implementation on 4,000 random cases at $0.00. Suite: **28 passed,
0 skipped, 0 failed**, the three new checks each verified by deliberately breaking them. Nothing
adopted: the control value is written beside the contract's surplus, never folded into it. Report:
`50_REBUILD/docs/Control_Years.md`.

**2026-09-17 — the reconciliation is corrected, and the claim it supports is much narrower.**
An independent review found the survival decomposition in the 2026-09-16h pass was not a
decomposition at all. `contract_npv.py` builds `surplus_no_survival` as **undiscounted** contract
surplus plus terminal value at its own reference date, so subtracting production's NPV from it
removes the discounting along with the hazard. The tell was in the output and was missed: it
produced **negative** hazard effects, and removing a survival haircut cannot lower a value when
the value is nonnegative and everything else is held.

**`run_production_reconciliation.py` (new)** imports production's own engine, prices each contract
through it, and rebuilds the no-hazard value from the per-season detail with cost, the discount
factor and terminal value all held:

    no-hazard NPV = sum over seasons of (value - cost) x discount + the original terminal NPV

| term | n | production $M | no hazard $M | the hazard is worth | gap to rebuild | claimed 09-16h |
|---|---:|---:|---:|---:|---:|---:|
| 4 yr | 66 | -4.49 | -3.63 | **+0.86** | +5.03 | +0.70 |
| 6 yr | 33 | -14.32 | -12.64 | **+1.69** | +15.86 | +0.76 |
| 7 yr | 26 | -21.23 | -19.56 | **+1.67** | +24.61 | -0.17 |
| 8 yr | 22 | -28.19 | -25.90 | **+2.29** | +33.63 | -0.58 |

Every effect is positive, as it must be, and **v1.2 asserts it** rather than printing a count.
It also computes every figure from the engine's own summary and asserts the saved spine still
agrees: the first version took details from the engine and totals from the spine, which agree
only while the spine is current -- adding $1M to the saved totals alone produced 1,043 negative
hazard effects and the runner printed the count without failing. Both assertions were tested by
deliberately breaking them. **The
supported statement is only that the exit hazard alone does not explain the long-contract gap** --
roughly nine-tenths of it survives removing the hazard. It does **not** locate the disagreement on
the value side, and the 09-16h entry saying it did is withdrawn.

**Matching on contract ID does not establish that the two sides priced the same asset.**
Production's sweep labels its output with the ID it asked about; the engine follows a chain and
can value another. Of 1,141 joined rows: **10** value a different contract, **3** cover a different
number of seasons, **185** carry terminal control value the rebuild excludes, **46** disagree
about cost by more than 10%, and **240** have a valuation year different from the signing year.
**912 pass the four asset tests** -- the same asset, whatever the date. **[CORRECTED after a
second review pass]** That is not "comparable on every test": **217 of those 912 have a valuation
year away from the signing year**, leaving 695 that pass the asset tests and the date flag
together, and even those are not on the same information date. The date flag falls hardest where
the disagreement is largest -- **17 of the 22 eight-year contracts** -- so the strictest screen
leaves five eight-year deals, too few to report. Excluding on the date would hide the dating
difference rather than fix it. Every row keeps its place in `production_reconciliation.csv` with
flags and a written reason; nothing was dropped silently and no production input was changed. The attrition is almost all short contracts -- all 185
terminal-value rows are one- to three-year deals -- so four, five, seven and eight years lose
nobody and the term gradient is unaffected. The largest cost disagreements are a **source
inconsistency**: the supplied season spine carries a cap hit an order of magnitude from the
contract's own AAV (5606 at $19.216M against $1.866M; 6216 at $8.625M against $0.750M) and
production prices the cap hit.

**Two framings corrected.** The two sides are not both discounted from the signing: production
values from **1 July of the first contract season**. And term-group means account for **84.8%** of
the squared variation in the dollar gap -- strong, but not literally all of the disagreement, and
the definitional differences above can themselves vary with term.

**`run_valuation_integration.py` v1.2** drops the false decomposition, renames the column honestly
to `production_surplus_nominal_no_survival`, and gains the guards that in-memory input mutations
defeated: required-column schema checks, duplicate-key checks before every join, explicit merge
cardinalities with a final uniqueness assertion, a reserved-cohort refusal in this consumer, a
cross-artifact check that the simulation's point surplus equals the market comparison's adopted
surplus to within $1, and named missing IDs instead of `min(n_sens, n_sim)` as evidence the two
populations agree.

**2026-09-16h — the first reconciliation pass. ITS SURVIVAL DECOMPOSITION IS WITHDRAWN; see the
2026-09-17 entry above for the corrected arithmetic and the narrower claim it supports.**
`goalie_value_spine.csv` arrived, the goalie engine's parity gate passes at **$0.000284** (the
locked figure), and `contract_npv.py` prices **2,981 contracts (2,591 skater, 390 goalie)** with
**median +0.29, p10 -7.80** -- every locked figure exactly. Report:
`50_REBUILD/docs/Production_Reconciliation.md`.

**The two systems agree about ranking and disagree about long contracts.** 1,141 contracts in
both. Rank correlation 0.418 overall, but that hides everything: the gap is **monotone in term**,
from -$0.39M on one-year deals to **+$33.63M on eight-year deals**, where production says the
average contract destroys $28M and the rebuild says it creates $5M. **Within each term the two
still agree about ordering** (rank correlation 0.69-0.89 from three to eight years). They agree
which long contracts are better than which; they disagree about whether long contracts are worth
signing.

**[WITHDRAWN 2026-09-17]** This entry claimed the exit hazard had been ruled out and the
disagreement located on the value side, on a decomposition that subtracted an undiscounted column
and so removed the discounting along with the hazard. Its figures (-$0.58M at eight years, $0.76M
at six) are wrong and its conclusion was not earned. The corrected figures are +$2.29M and +$1.69M
and they support only that the hazard alone does not explain the gap. See the 2026-09-17 entry.

**One thing does not reproduce:** `goalie_value_spine_v2.csv` hashes to `7e481bf4...` against the
record's `55c935dd...`. Every content check on it passes, including the parity gate and the 1,730
priced rows. **[CORRECTED 2026-09-17]** The float-formatting explanation offered here was a guess
and it is withdrawn: an independent rerun in a separate checkout regenerated the file and got
`55c935dd...` exactly, with parsed values and missingness matching, so the difference is specific
to this container and remains unexplained.

**Caveats that stand:** neither side is scored against an outcome, so this is two models
disagreeing and not evidence that either is right; part of the level difference is definitional
because the two put participation in different places; 22 eight-year contracts carry the largest
gaps; and the rebuild's long-horizon forecasts lean on a declared extrapolation that is flattered
upward by a stated amount.

**2026-09-16g — the production chain runs here, and valuation integration is built.** Thomas
supplied `contract_season_spine.csv`, so production's own chain runs in this container for the
first time. Its guards reproduce the locked record exactly: **Stage 0a and 0b PASS** against the
locked regression, **6,892 priced skater rows**, and the **k=0 identity at $0.00** on 397 shared
rows. `skater_value_engine`, `skater_forward_projection`, `rfa_terminal_value` and `exit_hazard`
all complete.

**`run_valuation_integration.py` writes `contract_valuation.csv`** -- one row per contract, 1,217
contracts and 29 columns, with the join asserted rather than assumed: what the club committed
(aav, length, discounted cost), what the adopted forecast says (production per season, value,
surplus), the same surplus under all five forecasts, the distribution around the adopted one
(mean, sd, 10th, 90th, chance of a loss), and the declared sensitivities (term-free, the miss's
cross-season dependence, absorbing participation). Everything downstream should read this rather
than joining the three runners' CSVs by hand.

**ONE FILE STILL BLOCKS THE RECONCILIATION: `goalie_value_spine_v2.csv`.** `contract_npv.py` prices
both positions and reads the goalie spine at startup, so the skater half cannot run without it.
Running `goalie_value_engine.py` to produce it does not help: its Stage P parity gate reads a
previously locked `goalie_value_spine.csv`, which is also absent. Either file unblocks it --
`goalie_value_spine_v2.csv` directly, or `goalie_value_spine.csv` which lets the engine run and
its parity gate be verified (the locked record puts that gate at $0.000284 and the v2 file's MD5
at 55c935dd...). Every other production input is present and reproduces.

**2026-09-16f — simulation review CLOSED; next is valuation integration, and reconciliation is
blocked on one file.** Three qualifications from the closure folded in: the average-production
sentence still carried 0.3495 against this run's 0.3487; the returns-against-absorbing pair is an
**estimate, not an identity** (shared draws remove the difference between two independently drawn
participation samples, not the Monte Carlo error of a comparison whose transition rules differ --
an independent rerun gives $11.0127M against $11.0745M, which is the sampling wobble on a
22-contract cohort at 2,000 paths); and check 25's docstring used pricing language for something
that compares drawn production on a held forecast and does not reconcile dollars.

**CONTRACT-BY-CONTRACT DOLLAR RECONCILIATION NEEDS `capspace_clauses.csv`.** The plan asks for
full-chain movement against the production spine. `30_OUTPUT/contract_npv_spine.csv` is not in this
container and building it means running the production chain, which reads
`contract_season_spine.csv`, which `join_clauses_to_spine.py` builds by annotating the PuckPedia
contracts with the cap-space.com clause scrape. That scrape is not in the repository and the
builder hard-fails without it.

**Verified, so the ask is precise:** the valuation path reads **no clause column at all** --
nothing in `skater_value_engine.py`, `skater_forward_projection.py` or `contract_npv.py` touches
`ntc_full`, `nmc_full`, `clause_*`, `has_any_clause` or the bonus fields. So a spine built with
empty clause columns would be identical for the NPV path's purposes, and the locked figures on
record (k=0 max diff $0.00, 6,892 priced skater-seasons, median NPV +0.29M, p10 -7.80, 2,981
contracts) would confirm it. **That synthesis was not done**: fabricating an input to a production
chain whose output is meant to BE the reconciliation reference is the wrong risk to take quietly,
and a subtly wrong spine would be hard to detect from the reconciliation itself. Either
`capspace_clauses.csv` or an already-built `contract_season_spine.csv` unblocks it; alternatively,
an explicit decision to reconcile against a clause-free spine with the locked figures as the
acceptance test.

**Not blocked, and next:** valuation integration itself -- carrying the point valuation, the
simulated distribution and the surplus through one contract-level artifact -- needs nothing that
is missing.

**2026-09-16e — the two corrections from the repair verification are in.** Suite: **25 passed, 0
skipped, 0 failed**.

**The common draws were half common.** The runner built shared participation uniforms and never
passed them, so performance draws were shared and participation was redrawn per arm. The one-season
contrast printed as 0% while all 605 one-season contracts actually differed, by -0.106% on the
cohort. Participation uniforms are now passed to every arm, and **the one-season identity is
asserted path by path rather than reported**: 605 of 605 identical, contrast 0.00000000%. The
returns-against-absorbing pair reads $11.01M against $11.08M on shared draws, where it previously
read $11.02M against $11.09M without the noise removed.

**The leakage guard did not test the runner.** Check 25 built its own correctly-dated calibrator,
so it tested the calibration and not the SELECTION -- and selection was where the defect was. The
reviewer proved it by stubbing the runner's functions out entirely; the check still passed. It now
drives `per_season`, `page_dependence` and a named `calibration_for` that the runner itself calls,
on a sample spanning two pages, and asserts that the two pages give DIFFERENT answers so a revert
to latest-page selection cannot pass unnoticed. Verified by reverting: stubbing `page_dependence`
fails it, and restoring `max(spreads)` selection fails it.

**Source comments brought into line with the corrected report** -- absorbing exits, a bending
tobit prediction and point valuations assuming independent errors were still described in
`npv_simulation.py` after the report had withdrawn all three.

**Carried as prototype limitations, not defects:** the return rate is estimated from recent
absences and applied to every absent state regardless of age or how long the player has been out;
two contracts (4921, 6809) need an exit probability clipped, missing their target playing
probability by 0.045 and 0.381 percentage points.

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
