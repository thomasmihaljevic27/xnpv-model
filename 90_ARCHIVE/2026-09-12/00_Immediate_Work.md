# 00. Immediate Work

Generated 2026-07-29, revised the same evening after the goalie stale-anchor fix shipped. Scope: everything that does **not** change a model's structure. Verification, housekeeping, materiality counts, decisions with no downstream propagation, and documentation debt.

Nothing in this document refits the market rate, alters an anchor, or changes how any asset class is priced. Those items live in documents 01, 02, and 03. The dividing test I applied is whether an item, once actioned, forces any other artifact to be rebuilt. If it does, it is a structural change and it is not here.

---

## 1. Blocking Verification

These gate the three structural documents. Nothing in 01, 02, or 03 should start until this section closes, because each of the three consumes an artifact that is currently unverified or stale.

**Close the two remaining Stage 2-5 verification items.** The 2026-07-28 local runs confirmed the Stage 3 rate, the Stage 4 retention gate, item 1.10, and the 1b counter. Two items were not covered because they live in scripts that were not run in that pass. First, the Stage 2 length-term null test, which sits in the price-equation work rather than the terminal-value chain. Second, the rebuilt draft curve, which was recomputed in a sandbox at review item 4.3 and has never been reproduced on my machine. Until the second closes, `draft_yield_curve.csv` on disk is the pre-rebuild version, so any pick pricing that reads it is using the shallower curve. This one gates document 01 directly.

**DONE the same evening: the downstream spines were regenerated.** `contract_npv_spine.csv` and `contract_npv_panel.csv` both rebuilt after the goalie fix, the panel at 6,939 rows against 6,829. Median contract NPV now +0.29M, p10 −7.80. The original wording of this item follows, retained because the Phase 4b claim inside it was wrong and is corrected above.

**Regenerate the downstream spines on the corrected engine.** The 2026-07-28 run rewrote `contract_npv_spine.csv` on the Stage 3 position-split rate and the Stage 4 gate. The median NPV moved from +0.76M to +0.32M and the distribution tightened at both ends, p10 from -8.15 to -7.97 and p90 from +2.97 to +2.52. Every artifact built off the old spine is stale, including `contract_npv_panel.csv` and anything in the Phase 4b circularity outputs keyed on contract-level NPV. Audit what consumes the spine before assuming the list is short.

**CLOSED the same evening: the goalie stale-anchor fix.** Applied and verified. 107 rows now carry a real anchor. `patch_goalie_stale_anchor.py` was **not** what did it: its anchors were cut against the 409-line project mirror while the local file is 641 lines and already carried review item 1.1, so three anchors missed and it refused to write. Superseded by `patch_goalie_stale_anchor_v2.py` plus a runner carrying the `contract_npv.py` edits. Do not run the original. Stage P parity passed with zero `weight_scheme` mismatches, item 1.1 unchanged at 98 rows, and `contract_npv.py` imported cleanly, which is what confirms the spine's recovered rate and target survived.

**CLOSED as not needed: the Phase 4b regeneration.** The item below in section 1 claimed those outputs are keyed on contract-level NPV. They are not. `gv_4b_inventory.py`, `gv_4b_circularity_check.py` and `gv_4b_robustness_check.py` correlate skater trailing projections against the GV yardstick at player-season level, n=6,027, and never read contract-level NPV. The goalie fix touched only goalie rows.

**Confirm whether `age_join.py` was re-run after Stage 1.** The split-sample run reproduced the sandbox figures digit for digit under a seeded bootstrap, which means `WAR_with_age.csv` is byte-identical to the two-session-old mirror. Stage 1 changed `age_join.py`. Either it was never re-run, or the fix touched no row feeding that test. The answer determines whether the identifier and birthdate pollution audit in section 3 is still measuring the pre-fix file.

**Note the one verification caveat already on record.** `rfa_terminal_value.py` was rebuilt from the verified 2026-07-06 Drive copy after the local file was damaged mid-session. Its Stage 4 fix reproduces the documented behaviour exactly, 21.3% on n=1,231 moving to 27.0% on n=2,270 with star, regular, and fringe rates unmoved, which is strong evidence it is functionally identical. It is not guaranteed byte-identical to what was originally written.

**RESOLVED 2026-07-30 by the Dropbox migration: this item is obsolete.** The Claude project no longer holds scripts or run logs at all, only decision-cadence files, and Google Drive is retired. Scripts live in Dropbox `20_CODE/`, one current copy each, and are attached per message when worked on. The original item follows, retained for context.

**Sync scripts and run logs to Drive and to the Claude project.** Both copies are two full sessions behind, missing the 2026-07-27 Stage 1 fixes and the 2026-07-28 Stage 2-5 rebuild. A future session reading project files by default picks up the pre-review price equation and the pre-rebuild draft curve without knowing it. This already produced a wrong read in the 2026-07-29 session, where `skater_value_engine.py` returned the superseded OLS constants. Do this immediately after the verification runs above.

---

## 2. Conflict, Resolved 2026-07-29

**The aging-curve split-sample stability check ran and passed.** It was recorded as complete in PROJECT_STATE.md v2.7 while the Craft Work Queue still carried it open. The Work Queue was the stale record and has been corrected. Result, for the limitations section: within-player age deltas, early era 2007-2015 against late 2016-2025, player-clustered bootstrap, 7,530 usable deltas across 1,479 players. Forwards differ at 0 of 16 ages, defence at 1 of 16, against roughly 1.6 false positives expected by chance across 32 tests. Thomas's local run reproduced every figure. Script `aging_split_sample.py`. The stable-parameter defence is now tested rather than asserted.

---

## 3. Decisions Owed, No Propagation

Each of these is a call with a bounded blast radius. None refits anything.

**The 93 cascade-gap goalie rows.** This is the live remainder of what used to be called the 83 never-played rows, and it is the oldest open decision in the project. The 83 figure could not be reproduced: the `no_observed_war_history` tag covers 748 rows and 286 players. The real defect was a missing cascade branch, not a pricing choice, since a goaltender with no t-1 season but a usable t-2 or t-3 fell through to the no-history branch. Carey Price, Corey Crawford, Ben Bishop, Spencer Knight, and Carter Hart were all caught by it. Two constants were measured on the 93 affected rows: `STALE_TARGET` 0.650, the conditional mean WAR of that population given the goaltender plays (n=29), and `STALE_GATE` 0.312, which is 29 of 93. The gate does most of the work, because the goalie rate carries a 1.391% of cap intercept, so an ungated goaltender who never plays still books roughly $1.3M of modelled value. Note the direction: shrinking this population toward the league average of 2.189 pushes value up, which is wrong, because it is the mean of a population he is not in. **The decision on these 93 rows was never answered and is still owed.**

**The WAR_with_age identifier and birthdate audit.** 23 identifiers carry more than one name, covering 217 rows and 47 players, and some carry wrong birthdates into the locked aging curve and the exit hazard. Spot checks show both kinds of error, genuinely mis-aged (Jeff Schultz enters the panel at 17 against a true age of 21) and identifier-wrong but age-correct (Michael Peca). Lambda 0.55 was re-tested on the corrected data and held, so the likely verdict is immaterial. The options remain a documented limitation with a materiality note or a targeted `age_join.py` audit pass. Open since 2026-07-19 and recorded as my call.

**Short first seasons losing the age-1 curve base.** The 20-game panel filter excludes a short rookie season, so a player with a cameo first year has no age-21 observation and any valuation whose age-1 base lands on 21 falls through to flat. The direction is conservative, since flat understates a player the curve would project upward, but it hits precisely the population the young-extension negative-NPV finding lives in. That makes it a Karl question rather than a curiosity. What is needed first is a materiality count: how many contracts in the NPV sweep route to `flat_no_curve` for this reason, and what the aggregate value at stake is.

---

## 4. Analysis Owed, Small

**Stress-test how floored seasons compound across a full contract.** D10 fires correctly inside the engine, confirmed incidentally on Tyler Myers 2023 where a raw -1.22M floored to 775K. How floors stack across a multi-season NPV has never been checked on purpose. Do it before the back-test leans on floor-heavy contracts.

**Complete the mid-season allocation application, Phase 4a-ii.** Split each back-test trade season's value around the trade date using the `player_game_value` table. Its per-game team column makes the split mechanical. The engine exists and was validated end to end on 2026-07-03, so this is application rather than construction.

**Watch the negative-anchor k=1 backcast slip.** After the aging-curve rebuild the curve trails hold-flat by 1.4% at one year out for negative anchors, n=233, where it previously led by 0.2%. It still wins clearly at k=2 (+5.2%) and k=3 (+8.0%), and the D12 v3 evidence base is unaffected. No action now. Revisit if the affected population grows.

---

## 5. Documentation Debt

**Write WAR_AAV_Regression_Report v3.** The v2 report is superseded twice over, first by the skater-only re-derivation under D6 through D9, and again by the Stage 3 censored position-interaction rate. v3 should restate the current rate, the one-market finding, and the regime finding, so nothing is left citing v2's F=3.63 distinctness figure or its flat-cap-break numbers as current.

**Purge the position-blind language.** Several documents in the workspace still describe the dollars-per-win conversion as position-blind with positional effects emerging as residuals. Stage 3 replaced that. One intercept is shared across positions, because at zero measured wins forwards and defencemen are paid alike, but defencemen carry a higher slope above that. Anything citing the position-blind convention as current is stale.

**Record the clause measurement-error lines.** Two lines are owed when the clause section is written. First, the CapWages adjudication workflow was superseded by the direct join, so the empty decision columns in `clause_disagreements.csv` are an abandoned path rather than unfinished work. Second, the most-restrictive tie-break on duplicate cap-space season rows affects 35 of 15,124 season-rows, 0.2%, and shifts clause prevalence by roughly 0.8% against a cap-hit-nearest rule, so the dedup choice is not load-bearing.

---

## 6. Standing Traps to Re-Read Before Any Structural Work

Not tasks. These are the failure modes that have already cost this project time, and each of the three structural documents can trip one.

**Duplicated loader logic across two files.** `skater_value_engine.py` and `skater_forward_projection.py` each build their own copy of the season-WAR lookup. Fixing only the value engine changes nothing downstream, because the projection file is what actually prices contracts. Any change to how season data is loaded, filtered, or de-duplicated must be applied in both, or it silently does nothing. `draft_yield_curve.py` holds a third copy of the trailing-window constants. This trap is live for document 03.

**Same-name collisions.** Disambiguate Sebastian Aho, Elias Pettersson, Connor Murphy, and Josh Anderson to an identifier before production. Separately, WAR.csv merges two different players under one name for Ryan Johnson, Nathan Smith, and Erik Gustafsson. Exclude rather than disambiguate until they can be split by identifier.

**Goalies_WAR splits traded goalies into one row per team per season**, 78 duplicate name-season pairs, so any consumer must sum within name-season. WAR.csv does the opposite and combines multi-team seasons into a single row.

**PuckPedia `overall_position` is back-filled for future picks.** A 2020 third traded in June 2019 carries its realized slot 70, a number nobody knew on the day. It must never be read for an ex-ante price. This trap is live for document 01.

**Reproduce before extending.** The locked v2 regression pooled goaltenders into what was presented as a skater-only sample, with no mention in its methods section. It surfaced only because a reproduction guard was built and run before the numbers were trusted for new work. Any inherited regression or metric gets a reproduction attempt before being extended.

---

## 7. Parallel Track, Not Sequenced Here

The Retention and Clauses pillar is self-contained and can run alongside any of the three structural documents. It is listed here so it does not fall out of view, not because it belongs with the small items.

**Find a data path for the NTC and NMC friction-cost discount.** This is headline contribution one and the only one still data-blocked. The cap-space.com scrape produced clause coverage, but nothing yet supports a revealed-preference estimate of what a clause costs an asset.

**Build standalone cap-retention pricing from the roughly 51 three-team deals.** Headline contribution two. Self-contained and parallelisable from here on.

**Implement the forced-trade detection rule.** An upper bound exists, 53 of 205 clean trades carry a clause-holder flag, but the presence of a clause is not proof it caused the move. Needed before monopsony trades can be split out as their own back-test category rather than sitting in the residual.
