# WORK QUEUE — NHL Trade Market Efficiency

<!-- Extracted from PROJECT_STATE.md on 2026-09-09 (v3.2 restructure). Pure move, no content change. -->
<!-- The full list of yet-to-do work, phase-sequenced. Changes almost every session.
     Detailed sequences for individual pillars live in 01_Draft_Model_Sequence.md,
     02_Prospect_Model_Sequence.md, 03_Player_Market_Model_Sequence.md. -->

---

## Work queue


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
