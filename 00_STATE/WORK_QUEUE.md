# WORK QUEUE — NHL Trade Market Efficiency

<!-- Extracted from PROJECT_STATE.md on 2026-09-09 (v3.2 restructure). Pure move, no content change. -->
<!-- The full list of yet-to-do work, phase-sequenced. Changes almost every session.
     Detailed sequences for individual pillars live in 01_Draft_Model_Sequence.md,
     02_Prospect_Model_Sequence.md, 03_Player_Market_Model_Sequence.md. -->

---

## Work queue

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
   variant recovered a fifth). It is also **most of why the 80% band delivers 60% for the 3+ tier
   five seasons out** — the middle of the star misses sits at +0.44 where the band expects -0.11.
   Widening the band would hide it. **Fixing the centre is the prerequisite for reading the
   tails**, so this comes before any further interval work.
2. **The joint simulation** on the fitted spread, with the zero-uncertainty identity it already
   satisfies one layer down.
3. **Separate bands for the rate and the games share, drawn jointly**, so an exit implies zero
   games on the path rather than a product of averages.
4. **Only then** re-measure whether the shape of a miss needs a tier or age term of its own. The
   star and young-player right tails reach +3.41 and +3.65 against a pooled +2.56, which is real,
   but fitting a fatter tail around a biased centre is fitting the wrong thing.
5. Then the rest of the named milestone: trade-date updates, control-year and goalie treatment,
   contract-by-contract dollar reconciliation, and the holdout policy.

**Open question raised by the sensitivity test, not answered.** A shock to last season survives
into the forecast at 0.45 at the valuation season and **0.65 five seasons out** — the share RISES
with distance, when a distant season should revert further toward the league. Removing the oldest
season in the window shows the same from the other side (-0.013 at the valuation season, -0.321
five out). The long horizons lean harder on the trailing anchor than the short ones. A question
for the forecast, recorded rather than guessed at.

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
