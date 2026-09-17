# STANDING FLAGS & OPEN QUESTIONS — NHL Trade Market Efficiency

## Independent rebuild review (2026-09-15)

**RFA control-year review, 2026-09-17:** reviewed `61c62bc` in isolation.
Full suite passes 28/28 and main values reproduce on 252 contracts (declared $0.451M,
informed $0.716M, oracle $0.950M). Item remains open: signing-date ownership excludes
101 later no-QO outcomes; informed policy reads latent performance shocks during missed
seasons (hidden-history intervention changes decisions in 188/252 contracts); future
QO bands enter contract 6876's 2021 valuation; and the myopic stopping/point-price
baseline comparison does not isolate information value or optimal continuation.
Repair dated eligibility, observation conditioning and QO vintage; implement continuation
or label a myopic policy, and compare like valuation rules before claiming an information
premium. Correct salary-approximation direction language (155 above, 17 below; broader
593-record sample). See `50_REBUILD/docs/Control_Years_Review_Codex.md`. Previous
simulation/reconciliation closures remain in scope. No production/candidate model
patch, adoption or merge; sources untouched and generated evidence ignored.

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

**Fourth repair verification, 2026-09-15:** reviewed `4b9723a` in isolation. All 17 repair
checks pass with no skips. Independent full-run audit confirms identical coefficients across
18 comparable quarters and zero shared-currency repricing differences for all 12 named cases.
The all-rejected request returns zero rows and one rejection record; empty input also passes.
The two preceding findings are closed. See `50_REBUILD/docs/Fourth_Repair_Verification_Codex.md`.
No new blocking defect found in the changed paths. Next milestone is the remaining simulation,
A3, control/goalie, uncertainty, dollar reconciliation and final-validation work. Rejection
CSV reporting still is not a complete per-run sample audit. Candidate implementation remains
unmerged; production code and the previously verified forecast specification are unchanged.

The earlier rebuild claims of improvement against the live chain and no leakage anywhere are
superseded by `50_REBUILD/docs/Player_Rebuild_Candidate_Review_Codex.md`. The original stress runner
reproduces its results, but it uses a flat comparator and a rate-only look-ahead check. Confirmed
defects include rate/games unit mismatch in shortened seasons, a 60% participation fallback after
the sixth forecast year, market windows dated by starts instead of signings, inconsistent
participation conditioning, and missing sample-completeness enforcement. Dollar illustrations
read future actual caps without discounting. Forecast-page protection does not seal market
selection. These issues affect the basis for interpreting the previously reported star/young
residuals and currency comparisons; fix and rerun development work before further selection.

## Ground-up review follow-ups (2026-09-14b; recommendations only)

- Market experiment samples use contract start year rather than signing date (`anchor_shrink_test.rate_sample`, inherited by `market_line_search`). Early extensions can expose unavailable performance. **QUANTIFIED 2026-09-14d (`signing_date_audit.py`):** of the locked 2,349 contracts, 85 (3.6%) were signed before the t-1 season began and 616 (26.2%) during it, so 30% read some production the signing team had not seen. Concentrated at the top: 19.2% of 3+ contracts and 11.8% of 2-3 signed before t-1 began, against 1-2% below 1 WAR; early signers are paid more at the same trailing WAR in every tier. The production rate itself (`skater_value_engine.stage0`) is built the same way. Until the sample is dated at the signing, the September 14 market-line figures are not signing-date out-of-sample evidence.
- **Component persistence (2026-09-14d, `component_persistence_test.py`).** Shooting WAR is 49% of the covariance of WAR/82 with year-to-year r 0.35 and 44% carried into the next season; even-strength offence r 0.66, 90% carried. A component-wise rolling anchor cuts next-season error 7.0% (8.1% and 8.9% at horizons 1 and 2) against 5.7% (7.2%, 7.9%) for the pull-back L, and removes the 3+ over-projection. Test only; the structure for reliability-based shrinkage in `50_REBUILD/docs/Player_Model_Rebuild_Plan_Fable.md` Phase 1.
- Full rebuild plan with phases, acceptance tests and the decisions it needs: `50_REBUILD/docs/Player_Model_Rebuild_Plan_Fable.md` (2026-09-14d). Proposal only; the competing plan from the 09-14c session is `50_REBUILD/docs/Player_Model_Rebuild_Plan.md`.
- First forecast-season uncertainty is zero in `_proj_sd_war(0)`; later uncertainty is held flat beyond year three. Both need recalibration for a forecasting model.
- Applying a new-signing term-price equation to remaining years on existing contracts requires separate validation.
- The salary-informed forecast diagnostic is not an accuracy ceiling for statistics-only models or an identified private-information estimate. Recent rolling experiments retain full-history aging fits.
- Full proposed architecture and qualifications: `50_REBUILD/docs/Ground_Up_Player_Model_Review.md`. No production decision changed.

<!-- Extracted from PROJECT_STATE.md on 2026-09-09 (v3.2 restructure). Pure move, no content change. -->
<!-- Karl's identification axes to watch on every design choice, the triaged open
     questions, and the original-conflicts resolution record. A flag is a standing
     watch-item on a design axis; an open question is a specific undecided thing. -->

---

## Standing flags (Karl's identification axes — watch on every design choice)

- **NEW 2026-09-15 — the elite tier is not identified, and the currency choice decides the
  headline.** Surplus at 2+ forecast wins a season is +$3.00M under a straight price line and
  −$0.78M under a log line, on 37 contracts (six above three wins). The log line beat the straight
  line out of sample by 0.81%, about $6,000 a contract, so the data marginally prefers the
  specification that reverses the finding. A named-player check makes the consequence concrete:
  under the log currency Connor McDavid at $12.5M is overpaid by $51M, and Kucherov, Marchand and
  MacKinnon are all bad contracts. **The straight line is primary for valuation on face-validity
  grounds and the log line is retained for price prediction, and that reversal is domain evidence
  overriding a marginal statistical preference, not a statistical result.** What can be claimed is
  that clubs get more surplus from good-but-not-elite players (half a win to two wins a season, 524
  contracts, holding under both currencies). What cannot is that elite production is underpaid.
- **NEW 2026-09-15 — the Stage 3 rejection of a curved price line was right for the wrong reason.**
  Curvature does appear once the market sample is dated at the signing rather than the contract
  start, which is exactly where the signing-date audit found the sample worst (58% of 3+ contracts
  signed before their trailing seasons finished). Any future curvature claim must use signing-dated
  forecasts.
- **NEW 2026-09-15 — inverse-probability weighting cannot fix the aging curve's survivorship.**
  A player retires because of the season we never observe, so the outcome causes the missingness
  and reweighting the survivors corrects the wrong thing; it moved the curve the wrong way at every
  age. The imputation approach states the assumption instead (a departing player was at about
  replacement) and works, but the result is a **bound on decline, not a point estimate**, and
  should be reported as one. The assumption matters enormously for fringe players (0.51 wins of
  curve movement across the sweep) and barely for stars (0.094), which is the right way round.
- **NEW 2026-09-15 — the aging level term is 89% measurement error if fitted naively.** Regressing
  the change from t to t+1 on the rate at t puts the same noise on both sides; the yearly change
  correlates −0.447 with the same-season level and −0.052 with the level one season earlier. Fitted
  naively the curve claims a 3-win 27-year-old loses 0.8 wins a year. The lagged level identifies
  it, and the effect that survives is real: a 3-win player at 35 declines nearly twice as fast as a
  0.5-win player. **Any level term in any curve in this project needs the same check.**
- **NEW 2026-09-15 — contract-export coverage tracks the calendar, and using it as a predictor
  teaches the model about the era.** Coverage of the players being valued runs 11% (2015) to 99%
  (2021) and 97% on the sealed pages. In the participation model the contract feature costs
  0.26%-0.91% rather than helping, because on early pages the unknown flag is an era indicator. It
  also means **a model leaning on contract state would do better on the confirmatory pages than the
  development ones**, the opposite of the usual direction, so a good confirmatory result would be
  partly a coverage artifact. Does not bear on Phase 4, where the contract is the object priced.
- **NEW 2026-09-15 — the WAR export's six components stop summing to the total from 2023-24.**
  Exact through 2022-23; from 2023-24, 97.9% of rows carry a residual that grows with the player's
  WAR (r = 0.79 forwards), about 2% of WAR at the median, largest 0.332 wins. Cause is vendor-side
  and unknown. The rebuild carries it as a seventh unallocated component, which the fit then shrinks
  entirely to the norm as carrying no signal. **Production reads the total so its levels are
  unaffected, but `component_persistence_test.py`'s covariance shares are computed over pairs
  including 2023-24 onward and carry the residual inside them; effect unquantified.** Not taken back
  to the vendor.

- **NEW 2026-09-13 — aging-curve coverage audit.** Full write-up: `50_REBUILD/docs/Aging_Curve_Coverage_Audit.md`. (1) 1,765 of 1,976 `flat_no_curve` skater pages were a labelling bug on one-season-left pages, value-neutral, fixed in `skater_forward_projection.py` v1.3; the D21 path-mix figures overstate curve misses. (2) Real misses are 211 pages (about 3%): 99 pages / 82 players rookie cameo (the short-first-season flag below, now counted), 68 / 41 never a 20+ GP season, 44 / 37 injury or demotion gap. (3) **Selection issue:** a player's first qualifying season never enters the comparables pool, so at age 20 only 34 of 87 defencemen with a 20+ GP season are eligible comparables (Q. Hughes, Seider, Sanderson, Letang absent), and at 21 Makar, Fox, Josi, Subban are absent. The young pool is selected on early arrival; direction of bias unmeasured. (4) The pool is thin where young contracts are priced: the league-wide position curve carries 78% of a 19-year-old defenceman's estimate, 31% at 20, 49% at 37. Three options listed in the doc; each changes the locked curve and needs a deliberate revisit with held-out error, a λ re-test and full-chain movement.
- **NEW 2026-09-14 — whole-chain sweep (`50_REBUILD/docs/Pipeline_Experiment.md`).** (1) A rolling pull-back of the starting point (fitted on seasons before each valuation) removes the level tilt on 2020-25 pages: bias +3.5% → −2.9% overall, +24% → −4% at 3+, WAR error −5.7%. The 09-13b star overshoot was the 2018-19 pages, where stars held their level. (2) **The exit hazard is estimated on the wrong population**: 10.6%/yr on all 10+ GP seasons against 5.3% among players holding a contract for next season, and the chain prices only the latter; it over-predicts exits at k≥1 (11.7% vs 7.0%). Fixing it alone worsens error because it had been offsetting over-projection; with the pull-back (L+H) every level is within 5% of unbiased and net NPV moves −$645M instead of −$1.2B. (3) Games played carry their own market price (~$2.1M for a full vs half season at the same WAR); with games in the line the price per win falls from $2.03M to ~$0.8M, so the production line charges wins for availability. A games-aware value line cuts relative error 6-12 points above 1 WAR but redefines value (D6-D9). (4) The market line is not tilted by level; contract length predicts cap hit strongly (−31% error alone, −39% in the best line with term, games, one-season flag and RFA; `market_line_search.py`). **Whether term enters the value line is a framing decision (corrected 2026-09-14):** one-year replacements each season (term-free; the term premium is a mispricing to measure) or one replacement for the remaining term (term in the line; the premium becomes fair value and aggregate NPV rises $3.3-4.1B). (5) Age in the starting-point pull-back (LB3A) keeps the tilt at zero and makes the package near NPV-neutral. All locked; nothing adopted.
- **NEW 2026-09-13b — the comparables blend is nearly an age-group average, and the best players are over-projected in season totals.** Effective comparables are ~92% of the eligible pool; a 3+ WAR/82 player's at-level comparables carry 8% of the weight. The pooled weight of 10 is not the cause (~5% share, every tier). Top 50 comparables with the pooled weight kept improved held-out error modestly and consistently; locked, so a candidate for the curve revisit only. On held-out careers, 3+ players' season-total projections run +0.46 to +0.62 WAR per season high (conditional on survival); the curve explains ~0.1 of it, the raw trailing valuation anchor the rest. **Confirmed in dollars in the production chain** (`npv_realized_by_tier.py`, in-sample, contract part only): no overall bias (+$0.04M per season), but value is over-projected for players valued at 1+ WAR and under-projected below 1, rising to +$0.98M per season (13.9%) for 3+ and +$1.49M (20.9%) for sustained stars; +$0.82M / +$1.21M without Gaudreau 2022. This is the production (value) side of NPV, not the salary regression: it overstates the best players' NPV. Back-test consequence: a trade of a star for lesser assets would be scored in the star side's favour by construction. **Fix test (same session, `50_REBUILD/docs/Anchor_Shrink_Test.md`):** pulling the starting point back (calibrated 2009-2017) removes the tilt and helps the middle of the league but overshoots stars, because forwards and newly signed stars have held their level better since 2018 (contract-start stars kept 89% vs 72% in 2009-17). Refitting the market line on pulled-back WAR changes nothing (the market already discounts recent runs) and together with the pull-back returns today's NPVs. **The star over-valuation is currency-dependent:** it holds when realized wins are priced at today's line, and largely disappears if they are priced per delivered win. The back-test's realized-value currency must be decided first. `50_REBUILD/docs/Aging_Comparable_Limit_Test.md`, `sessions/2026-09-13b.md`.
- **NEW 2026-09-13 — D11 grows the cap 3% from t0 even where the future ceilings were already published.** For the 2025-26 page the path is $98.4M / $101.3M for 2026-27 / 2027-28 against the published $104.0M / $113.5M; the 2026-27 page projects 2027-28 at $107.1M against $113.5M. League minimums already use the published schedule, so the two sides of the floor treatment are inconsistent for t0 ≥ 2025. Context: ceiling growth averaged 3.4%/yr from 2015-16 to 2019-20, 0.6%/yr through the escrow-repayment years to 2023-24, and 7.6%/yr from 2023-24 to 2026-27. The level is back on the pre-COVID trend in 2026-27 (+1.2%) and only 2027-28 is clearly above it (+6.9%), so most of the post-escrow surge is catch-up. D11/D17 are locked, and g is also the discount rate, so any change is a deliberate revisit.
- **NEW 2026-09-13 — the contract being played is not gated on its signing date.** D28 gates extensions only. A contract signed after July 1 for the season about to start (late RFA deals, in-season signings) is on that season's page from July 1. Look-ahead on the cost side, small in days; unmeasured.
- **NEW 2026-09-13 — the 2026-27 page is built on the May 21, 2026 PuckPedia export.** Every July 2026 signing is missing, so the page holds 626 contracts against 850-900 on the others. Refresh the export and re-run `contract_npv_panel.py` and `player_dashboard.py` before reading that page as a league view.

- **Aging identity and yardstick test (2026-09-10).** The target-specific median-distance experiment found a career-key collision between Erik Gustafsson and Erik Gustafsson 88, including two qualifying seasons at age 23. Test-only exclusion from training and evaluation; production identity handling still needs review. The alternative slightly worsened errors. This is exploratory evidence from current reconstructed data and existing settings, with evaluation conditional on observed >=20-GP seasons. The full-era test admits other players' future seasons; a historical-window check removes those and reaches the same direction. It does not validate survival, dollar values, or the complete contract pipeline. Details: `40_DOCS/Aging_Yardstick_Comparison.md`. **Update 2026-09-13b:** production has no Gustafsson collision; `skater_value_engine.norm_name` keeps digits, so "Erik Gustafsson 88" is its own career. The 09-10 run used the standalone fallback cleaner in `aging_curve.py`, which strips digits. Open item is now the fallback's disagreement with the engine's cleaner, not the production identity.


- **VERIFICATION GAP, NOW COMPOUNDED (updated 2026-09-08).** The Stage 2-5 changes were never run
  locally or cross-checked the way Stage 1 was, and that gap is still open. It is now compounded:
  every script had its paths replaced on 2026-09-08 and nothing has been run end to end since. The
  2026-07-28 figures are carried on the reasoning that only paths changed, which is exactly the
  class of reasoning the reproduce-before-extending rule exists to reject. Until the player chain
  is re-run, treat every figure in this file as unverified on the current codebase.
- **Scripts wrote to the current working directory (found and fixed 2026-09-08).** Six scripts
  resolved paths relative to wherever they were launched, two of them writing load-bearing
  artifacts. This is the mechanism behind the stale duplicates found on disk, some predating the
  2026-07-28 rebuild by three weeks. Standing lesson: a stale duplicate is usually created by a
  script with a relative path, not by a person copying a file.
- **This file now lives on three surfaces (new 2026-09-08).** Local working folder (git-tracked),
  Dropbox `00_STATE`, and the Claude project. Local is authoritative and is now the git copy, so an
  edit made anywhere else is lost on the next pull. Update local first, refresh Dropbox from it,
  then replace the Claude project copy by hand. The project copy does not update itself and has
  already been found serving stale files twice.

- **NEW 2026-07-28 — the yield-curve tail versus the minimum tradeable unit.** The curve prices a pick in the 151-224 band at 0.00853 of the cap, roughly $0.81M. That number is the mean of a lottery: **the median outcome is zero, 74.5% of those picks produce nothing, and the top 5% hold 42% of the band's entire value across eleven cohorts** (round 1, for contrast: median $4.74M, 7.1% produce nothing, top 5% hold 16.3%). The same pick is also the *smallest unit of consideration a club can add to a trade*, since cash cannot be traded. Two readings are observationally equivalent in the pure-pick sample: either the tail is overvalued relative to what clubs treat it as worth, or the curve is right and clubs systematically undervalue late picks. Approximating the rebuilt steeper curve moves the implied discount only from 0.486 to 0.503, so **staleness is not the explanation**. This touches every back-test trade containing a small makeweight, which is most of them.
- **NEW 2026-07-28 — short first seasons lose the age−1 curve base.** Supersedes the Samoskevich note. The MIN_GP=20 panel filter excludes a short rookie cameo, so a player whose first season was (say) 7 games has no age-21 observation and any valuation basing at 21 falls through to flat. Direction is conservative, but it hits precisely the population the young-extension negative-NPV finding lives in. Needs a materiality count before the paper. **COUNTED 2026-09-13:** 99 panel pages, 82 players (see the coverage audit above).
- **UPDATED 2026-07-28 — the one-directional-corrections flag is now PARTLY ANSWERED.** The flag recorded that six of ten Stage 1 fixes moved values up and none moved them down, which is the kind of uniform sign a supervisor is right to be suspicious of. **The 2026-07-28 evening run is the first change set to move values DOWN:** median contract NPV fell from +$0.76M to +$0.32M and the distribution tightened at both ends (p10 −8.15→−7.97, p90 +2.97→+2.52), driven by the lower intercept and the tighter retention gate. Forwards fell, defencemen rose on the higher defence slope, and fringe terminal values fell hardest. Visible in named players rather than only in constants: Sandin (D) $12.67M→$14.22M, Samoskevich (F) $14.43M→$13.51M with terminal $11.12M→$10.44M, Rantanen (D) −$73.97M→−$73.18M. **This is direct evidence the corrections are not uniformly signed by construction, and belongs in the robustness section.**

- **Discount rate r — RESOLVED (estimated and locked 2026-07-05, D15-D18; stale flag text corrected 2026-07-14 on Thomas's confirmation).** Structure: survival-weighted value side (exit hazard from the panel by quality × age) + 3% cap-growth denominator, fundamentals-only — GM impatience deliberately excluded (D15) so the back-test can still detect over-discounting as a finding. Kept in this list as a closed record because every pillar's NPV depends on it; see Resolved Decisions D15-D19.
- **Value_t circularity** — the dollars-per-win rate is Bacon-derived, so the risk was "testing" the model against a yardstick made of the same vendor's material. **RESOLVED WITH STATED LIMITATIONS (primary validator run 2026-07-14; was Fatal → Important 2026-07-04).** The Phase 4b primary check executed: the Bacon-derived trailing projection correlates r=0.576 (n=6,027, stable across all nine seasons) with GV-adj, a metric with zero Bacon inputs, in win units with no dollar conversion on the outcome side. Three limitations are load-bearing for how this is cited: (1) it is **convergent validity, not proof the dollar level of a win is correct** — the test runs in win units by design and can only show the projection tracks an independent measure; (2) validation is **strong for forwards (r=0.648), partial for defencemen (r=0.302)** — the known structural weakness of shot-and-shift data on defensive value, to be stated wherever this result appears; (3) the claim is **no shared model or vendor, not no shared reality** — both metrics describe the same underlying games, and the paper must say so before a referee does. **Robustness leg RUN 2026-07-14 — Phase 4b is now FULLY CLOSED.** GV-raw confirms rather than merely fails to contradict: rebased r=0.609, zero-sum r=0.564, bracketing the GV-adj primary (0.576); all three validators land in a tight 0.56-0.61 band across all nine seasons, and the t+1 horizon degrades gently in all three. One honest note preserved: GV-raw correlates as well as or slightly better than GV-adj — explained by GV-raw retaining team-context signal that the RAPM adjustment strips and that Bacon WAR also carries; a finding about what each metric measures, not grounds to revisit the locked primary choice. Rebased-D at 0.442 is treated with caution (the rebase's documented offensive-D inflation plus deployment correlation), not cited as the best defence number. Still flag anything that would re-entangle the input rate and the outcome measure.
- **Look-ahead bias** — enforce the trailing-season rule (t-1, t-2) everywhere; flag any trade-season-row or current-vintage leak.
- **Selection bias** — trades happen only on mutual agreement, inflating apparent mispricing; no-trade counterfactual unobserved. Structural limitation (to be documented in the model overview).
- **Goalie playing-time endogeneity** — goaltender starts are allocated on perceived quality (weaker goalies get benched, stronger ones start more), which inflates naive season-to-season WAR correlations computed on the full population. Confirmed 2026-06-30: restricting to GP>=20 drops the goalie persistence correlation materially, and restricting further to contract-signing-anchored established goalies drops it further still, from r=0.30 down to r=0.08-0.09. Any goalie predictability/persistence statistic must state its population (full league, GP-filtered, or contract-signing-anchored) before being compared to another figure or cited in the paper.
- **Monopsony events** — NTC/NMC-forced trades are a separate back-test category, never residual mispricing. An UPPER BOUND was established 2026-06-30 (53 of 205 clean trades carry a clause-holder flag), but the **forced-trade detection rule is not yet implemented** — presence of a clause is not proof it caused the move.
- **Cap regime breaks** — flag long-term contracts from the 2020-2022 flat-cap window; they need the regime indicator.
- **Retention amendment (2025-26)** — the 75-day re-retention restriction changes third-party-broker strategy; flag any pre/post bridge.
- **Same-name collisions** — flag name-based joins touching Aho / Pettersson / Murphy / Anderson. Separately, WAR.csv merges two different players each under **Ryan Johnson** and **Nathan Smith** — left unmatched in the age join; exclude (don't disambiguate) until split by ID.
- **WAR_with_age.csv nhl_id pollution (2026-07-19)** — the age join's fuzzy/EP-fixed stages stamped **33 NHL IDs onto the wrong lookalike's rows** (Rick Nash carries Riley Nash's ID; Todd Bertuzzi carries Tyler's; Jeff Schultz carries Justin's). Any ID join through this file must require **name agreement** (the 3a linkage does). **COUNTS CORRECTED 2026-07-27 (item 1.8):** measured directly on the file, **23 identifiers carry more than one name, covering 217 rows and 47 players** — not the 33 / 322 / 69 the review recorded, nor the 113 / 36 recorded here previously. All three figures were in circulation; the measured pair is the one to cite. The guard is now built (`join_on_id_and_name()` in `age_join.py`, with a self-test that fires every run), so an ID-only join through this file raises instead of attaching the wrong player. Spillover: wrong birthdates on some of those rows feeding the locked aging curve and exit hazard — some genuinely mis-aged (Schultz aged 17, true 21), some age-correct. Likely immaterial to λ=0.55; audit of age_join.py is **Thomas's open call**.
- **Duplicated loader logic across two files (NEW 2026-07-27, found during item 1.5)** — `skater_value_engine.py` and `skater_forward_projection.py` each build their OWN copy of the season-WAR lookup rather than sharing one. Fixing only the value engine changed nothing downstream, because the projection is the file that actually prices contracts. Any future change to how season data is loaded, filtered, or de-duplicated MUST be applied in both, or it will appear to work and quietly do nothing. Same class of trap as the three historical stale-file incidents.
- **Corrections have run one way (NEW 2026-07-27)** — six of the Stage 1 fixes moved contract values upward and none moved them systematically down. Each is defensible alone; the pattern is what invites a question. Present Stage 1 as a set with a stated net effect in the robustness section rather than as separate corrections scattered through the methodology.
- **Qualifying-offer salary substitute (NEW 2026-07-27, item 1.10)** — ~25% of qualifying offers are computed from average annual value because no final-year salary exists, which switches off the CBA's 120%-of-cap-hit ceiling in exactly the cases it was written for. Direction: offer understated → control-year cost understated → **surplus overstated**. Now tagged in the output (`qo_salary_source`) and counted in the run log. Not fixable with current data; needs per-season salary coverage extended.
- ~~**Stage 2-5 review changes not locally verified (NEW 2026-07-28)**~~ — **CLOSED 2026-09-09.** All four are now run locally and reproduce: the new skater price equation (Stage 3 rate, in force through `skater_forward_projection.py`), the retention-calibration fix (Stage 4, 21.3%→27.0% buckets unmoved), the rebuilt draft curve (to the cent), and the Stage 2 length-term null test (`term_premium_test.py` — decisive null, every spec constant exact, value-side share 0.000). Not provisional any more. GV-raw robustness legs of the Stage 2 test remain an optional, un-run extension.
- **Erik Gustafsson = third WAR.csv merged name (2026-07-19)** — joins Ryan Johnson and Nathan Smith (13-14 PHI row is the undrafted b.1988 player; 15-16+ is the 2012-drafted b.1992 player). Standing rule applied: 2012 #93 pick excluded from the curve. Also: **Goalies_WAR splits traded goalies into one row per team per season** (78 duplicate name-seasons) — always SUM within name-season.

---

## Open questions (triaged)


**IMPORTANT — should the mean-reversion blend weight vary by player type? (new 2026-08-28.)**
Lambda is locked at 0.55 and applied universally to every skater. It was recovered by player-split
cross-validation on the pooled panel, so it is the single weight minimising average held-out error,
not a weight tested for whether it should differ by quality tier, position, age, or career stage.
Raised verbally in the supervisor meeting and previously unlogged anywhere. The question has real
content: a star with a long stable record arguably warrants less shrinkage toward the comparable
norm than a fringe player with two noisy seasons, and the current design gives them the same.
Resolving it means re-running the cross-validation within strata rather than pooled. Any change is
rate-adjacent, since the anchor feeds the projection that feeds the price equation. Not started.


**Fatal**
- *(none open)* — the discount rate r, the sole Fatal item since 2026-06-30, was **estimated and locked 2026-07-05** (Phase 1a; D15-D18). Structure: survival-weighted value + 3% cap-growth denominator, fundamentals-only, exit hazard estimated from the panel. See Resolved Decisions D15-D19 and the Work Queue Phase 1 block. No Fatal-tier open questions remain.

**Important (new 2026-07-28)**
- ~~**Stage 2-5 review changes not yet locally verified.**~~ **CLOSED 2026-09-09** — all four ran locally and reproduced (Stage 3 rate, Stage 4 retention, rebuilt draft curve, Stage 2 `term_premium_test.py` decisive null). See the DECISIONS.md verification-gap entry and the v3.3 change-log line.
- ~~**Scripts and run logs stale relative to two full sessions of changes**~~ — **CLOSED 2026-07-30.** The risk was real and it fired at least twice: a chat read the superseded OLS constants out of the project mirror during the Lane Hutson session, and the project was still serving the pre-rebuild draft curve plus output from a rejected goalie patch. The Claude project no longer holds model outputs or scripts at all; it holds only decision-cadence files. Scripts live in Dropbox `20_CODE/` and are attached per message when worked on.

**Important**
- Value_t circularity — **FULLY RESOLVED 2026-07-14** (primary + robustness legs both run; see Standing Flags for results and the three citation guardrails). The paired validator design executed in full: GV-adj 0.576, GV-raw rebased 0.609, GV-raw zero-sum 0.564 — three affirmative answers in a tight band. Moves to the Decision Log; kept here one cycle as a closed record.
- League-average vs team-specific value: the residual blends mispricing with team-fit premiums, private-information rents, and monopsony. Empirical separation is an open back-test design problem.
- Forced-trade detection rule not yet implemented. UPPER BOUND established 2026-06-30: 53 of 205 clean trades carry a clause-holder flag, but presence of a clause is not proof it caused the move.
- **No data path yet for the NTC/NMC friction-cost discount** (carried forward from the retired `00_Immediate_Work.md`, 2026-07-29). This is headline contribution one and the only one still data-blocked: the cap-space.com scrape produced clause *coverage* but nothing yet supports a revealed-preference estimate of what a no-trade/no-move clause costs an asset. Distinct from the forced-trade detection rule above — that's about identifying which trades a clause caused; this is about pricing the clause itself. Self-contained, parallelisable with Phase 4c retention pricing.
- **In-season production is not used before a trade (NEW 2026-09-13).** The model re-values once per season, so a trade in game 81 is valued on the page built before that season began. Phase 4a-ii splits realized season value around the trade date; it does not update the forecast. The obstacle is identification, not effort: Bacon WAR exists only as season totals, and scaling the finished total by pre-trade game shares uses post-trade games (look-ahead). An in-season update would have to come from Game Value alone, which needs a scoped exception to single-provider discipline and is weak for defencemen. Proposed, not decided: keep the annual clock as the main specification and run a GV-based in-season anchor as a robustness leg.
- Point-in-time metric availability: single current-vintage export, no archived season snapshots. The 2018 window limits but does not remove look-ahead. The constraint Karl is most likely to press; mitigated, not solved.
- Long-term deals crossing UFA eligibility need separate terminal-value handling.
- Outcome-measurement design: the realized-outcome window and playoff-vs-regular-season weighting are not fixed (a Cup rental != a seven-year accumulator).
- Efficient-market null not yet stated as a possible finding (Work Queue Phase 6).
- Trade-data completeness: the PuckPedia trades export has only one 2017-18 trade (earliest 2018-06-23); realized sample effectively runs 2018-19 -> 2025-26. Intended window is 2017-18 — verify against PuckPedia and re-pull the early window before finalizing the sample (low priority).

**Important (new 2026-07-05)**
- **`WAR_AAV_Regression_Report_v2` is superseded** (see Phase 1b decisions D6-D9): its headline numbers pooled goalies into the skater sample, undocumented. A v3 report restating the skater-only rate, the market-distinctness result, and the regime finding is owed but not yet written — flag if anyone (including future Claude sessions) cites v2's RFA/UFA-distinctness or flat-cap-break figures as current.
- **Value_t floor at league minimum (D10) is implemented but not yet stress-tested** against the back-test: whether floored seasons behave sensibly inside a multi-season NPV (once Layer 2/1d exist) hasn't been checked.

**Important (new 2026-07-27, from the Stage 1 work)**
- ~~**The 83 never-played goalie rows**~~ — **CLOSED 2026-07-29 (evening).** The fix is applied and verified; see the v2.9 changelog entry. What follows is the history, retained because the attribution was wrong twice and should not be re-derived. **SUPERSEDED first on 2026-07-29 (afternoon):** The figure of 83 could not be reproduced from the files: the `no_observed_war_history` tag covers **748 rows and 286 players**, with 203 rows carrying a blank trailing figure. Re-derived, and the underlying defect turned out to be a **missing cascade branch** rather than a pricing choice — a goaltender with no t−1 season but a usable t−2 or t−3 fell through to the no-history branch, which is how Carey Price, Corey Crawford, Ben Bishop, Spencer Knight, and Carter Hart were all tagged as never having played. `patch_goalie_stale_anchor.py` was written to fix it and **has not been run.** It hard-codes `GOALIE_LEAGUE_AVG = 2.189172466` first (the constant had to be broken loose before the rows it reads from could be repriced; alpha/beta are NOT hard-coded and refit identically to twelve decimal places), then adds `STALE_TARGET = 0.650` and `STALE_GATE = 0.312`, then the cascade branch, then the target routing. **Two live items replace this one:** run the patch, and decide the 93 cascade-gap rows (the session that produced the script ended waiting on that decision). Nothing downstream of the goalie branch should be regenerated until the patch runs.
- **Negative-anchor backcast at k=1 slipped after the curve rebuild** — the curve now trails hold-flat by 1.4% at one year out for negative anchors (n=233), where it previously led by 0.2%. It still wins clearly at k=2 (+5.2%) and k=3 (+8.0%), and D12 v3's evidence base is unaffected, so no action taken. Watch it if the population grows.
- **Review Stages 2-5 — RESOLVED 2026-07-28, moved to Resolved Decisions.** All items closed; see the "Player Model Review — Stages 2-5" block. Kept here one cycle as a closed record, per the project's convention for recently-resolved Important items.

**Optional**
- Single discount rate vs player-specific risk (does a 36-year-old carry the same r as a 24-year-old?). NOTE: assumed a baseline r already existed -- see the new Fatal item, r has never actually been estimated at all yet.
- Cap-inflation shock handling beyond the flat-cap regime indicator.
- Contender vs rebuilder marginal-win value.
- Signing-bonus structure / front-back-loading (absent from data; equal-AAV contracts valued identically).
- LTIR as a strategic asset (currently only a dead-cap accounting effect).
- ELC slide rule (extra team control not cleanly captured by the 3+4 window).
- Replacement-level variance by position (position-blind intercept may understate a #1 goaltender).
- Slug normalization pre-flight feasibility.
- Left-truncation — **RESOLVED 2026-07-19 (D25):** fitting cohorts 2007-2017, complete D+9 windows only; 2005-06 dropped rather than backfilled.

---

## Resolution record & remaining housekeeping


*Conflicts raised 2026-06-30 were resolved by Thomas the same day:*

1. **Back-test window** — intended **2017-18 onward** (Thomas to verify and, if needed, re-pull the missing early window; low priority). Data currently effectively begins 2018-19.
2. **ELC valuation** — resolved: **only RFA and UFA regressions exist.** ELC value = project production, price it at the RFA rate (what they would earn as an RFA), then subtract the slotted ELC cost. ELC is folded into the RFA regression; no separate ELC rate. (Reverses an early, abandoned line of thinking.)
3. **The `..._Paper_v6` file** — it is the model **overview / scoping document**, not a manuscript. Out of date and being replaced. No paper is written until the model is built.

*Remaining housekeeping (refreshed 2026-07-28):*
- The items (a)-(d) below this line as of v2.5 were all applied to Craft successfully on 2026-07-27 (the "Craft connection issue" session reconnected and pushed the full Stage 1 update set across seven hubs). That entry is now historical.
- **Craft is unreachable again this session (2026-07-28)** — same intermittent failure mode noted in at least three prior sessions (2026-07-03, 2026-07-05, 2026-07-27 before reconnecting). Craft therefore does not yet carry the Stages 2-5 closure (new rate, retention fix, rebuilt draft curve) documented in this file's v2.6 update. A paste-ready `CRAFT_UPDATE_2026-07-28.md` has been prepared covering: Decision Log (Stages 2-5 close-out entry), Player Model Progress Log (item-by-item narrative), Standing Flags (local-verification-gap flag), Open Questions (verification gap + script staleness, both new Important items), Work Queue (review roadmap fully closed), Regression Results (new skater rate), and the Draft Picks Progress Log (rebuilt curve). Apply next time the connector is reachable.


## Repository review follow-ups recorded 2026-09-09

- **Qualifying-offer effective-date mismatch (supervisor-detail pass):** the official 2025 NHL/NHLPA MOU item 1 starts September 16, 2026; item 32's revised QO bands state no earlier start. `rfa_terminal_value.py:qualifying_offer()` switches on `offseason_year >= 2026`, i.e. summer 2026, before that date. Review/correct the timing or document a transitional basis before describing it as verified legal implementation. Fuller Doc 3 records the discrepancy; no code or locked decision changed. Primary source and checks in `sessions/2026-09-09g.md`.

These are newly identified review items, not changes to locked decisions. Detailed evidence and proposed document language are in `40_DOCS/Repository_Review_and_Doc_1_Edits.md`; scope and checks are in `sessions/2026-09-09c.md`.

- **Draft Rule B position mismatch:** `draft_yield_curve.py` uses the position-specific slope for value but the forward slope for trailing cost. Source mismatch confirmed; aggregate effect unmeasured. The primary Rule A curve is separate. Review and rerun the sensitivity comparison before citing its small difference as settled.
- **Aging self-exclusion is incomplete at the global layer:** target-player direct comparable weights are zero, but global levels/deltas include all careers and enter shrinkage. Actual-method synthetic check confirms the dependency. Real-panel materiality is unmeasured; Docs 2/5 should not claim no own-future contribution anywhere.
- **Surplus ratios and the null need deliberate review:** common gross-value changes do not generally cancel after subtracting fixed costs; near-zero/negative denominators are problematic; exchangeable positive sides do not imply ratios average 1. The locked comparison statistic remains unchanged pending a deliberate decision.
- **Game Value validation wording:** construction without Bacon differs from validation on unseen games. Final xG refits on all regular seasons. Raw and adjusted validators share source data. Midseason allocation remains unimplemented and needs a signed/near-zero-total rule.
- **Docs 2-5 rewrite completed 2026-09-09:** these qualifications now appear in the explainers; model fixes remain open. Additional code-grounded checks surfaced in the rewrite: draft cameo costs and floors scale by GP/82 but the value intercept does not; skater projected contract years receive an expected-floor uncertainty correction that terminal and goalie years do not; qualifying-offer costs use timing proxies and salary fallbacks rather than reconstructing actual negotiated renewals. Effects are unmeasured. See `sessions/2026-09-09f.md`; no locked decision reopened.

**Stability-test scope clarified (2026-09-10d):** The 0/16 forward and 1/16 defence era counts come only from observed within-player WAR/82 changes. aging_split_sample.py's docstring also describes comparing fitted pooled profiles, but that leg is unimplemented. Supervisor Docs 2 and 5 now state the implemented scope; the results do not measure the effect of full-panel estimation on historical valuations.

- **2026-09-10f:** Control-year qualification survival starts at one in rfa_terminal_value.py; contract_npv.py adds discounted adjusted terminal surplus without multiplying by signed-contract survival. D14(c) deliberately avoids using both annual gates in control years, but the effect of departure before expiry has not been isolated. Docs 3 and 5 now explain this behavior; no model change. The pooled term-test null also coexists with a small positive forward-subgroup coefficient, now preserved in both explainers.
