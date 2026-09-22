# PROJECT STATE — NHL Trade Market Efficiency

<!-- Canonical default-context anchor. Source of truth is this file plus its three siblings in
     00_STATE/ (WORK_QUEUE.md, DECISIONS.md, STANDING_FLAGS.md) and the per-session log in
     00_STATE/sessions/, all version-controlled in git. Craft is retired as a canonical surface.
     This file holds: objective, model spec, current build state, the data/scripts inventory,
     locked regression results, per-pillar status, and the file-management protocol. -->

**Generated:** 2026-09-08
**Refresh due:** 2026-09-15 (7-day cadence)
**Maintained by:** Claude, at session close (see the DECISIONS.md change log)
**File version:** 3.2 (v3.2 restructure 2026-09-09: PROJECT_STATE.md split into four state files + a per-session log; see DECISIONS.md change log. Not a weekly refresh — Generated / Refresh-due unchanged.)

> **Refresh note (2026-09-08).** The previous snapshot was v2.9, generated 2026-07-29 and due
> 2026-08-05. It ran six weeks stale. Two sessions in that window went unrecorded on every
> surface: the 2026-08-28 supervisor meeting and the 2026-09-08 repository migration. Both are
> written up in the new section below and applied to Craft in the same pass. **Every model
> figure in this file still dates from the 2026-07-28 runs and has not been reproduced since
> the migration.** See the compounded verification flag before citing any of them.

---

## STALENESS TRIGGER — READ THIS FIRST (instruction to Claude)

Before doing substantive work in any chat, check today's date against **Refresh due** above.

- **If today is on or after the Refresh due date:** this snapshot is stale. Do **not** silently rely on it. First tell Thomas: *"The PROJECT_STATE snapshot was generated on [Generated date] and is now past its weekly refresh. Want me to run the refresh before we proceed?"* Then, on his go-ahead, run the **Refresh protocol** below.
- **If today is before the Refresh due date:** treat this file as current. Where it conflicts with older project-instruction text or dated project files, this file wins — it is the more recent snapshot.

This is a soft trigger: it works only because this file sits in context each chat and the above is a standing instruction. Honour it. The same staleness caveat covers the sibling files (WORK_QUEUE.md, DECISIONS.md, STANDING_FLAGS.md) — they share this file's Generated / Refresh-due dates.

---
## Refresh protocol (run when stale, or whenever Thomas asks)

1. **Confirm the date** and state how stale the snapshot is.
2. **Read the session log** — every `00_STATE/sessions/*.md` written since the Generated date. That is the primary record of what changed: decisions made, work done, artifacts touched, threads left open.
3. **Cross-check against `git log --stat 00_STATE/ 20_CODE/`** for the same window — commits are the mechanical second copy; anything in a commit but not in a session file is a gap to close.
4. **Reconcile.** Edit whichever of the four state files each change touches: PROJECT_STATE.md (build state, inventory, regression results, pillar status), WORK_QUEUE.md, DECISIONS.md (locked decisions + change log), STANDING_FLAGS.md.
5. **Compile conflicts and questions** — anything where the session files, the commits, or the state files disagree, or where a decision is ambiguous.
6. **Bring the conflicts to Thomas** and let him resolve them. Do not guess on load-bearing items.
7. **Re-stamp** the Generated date, advance the Refresh due date by 7 days, bump the File version, and append an entry to the **DECISIONS.md change log**.

---
## Precedence & layers

- **Order of authority:** the four `00_STATE/` files (PROJECT_STATE.md, WORK_QUEUE.md, DECISIONS.md, STANDING_FLAGS.md) + the `sessions/` log, all in git — these ARE the source of truth; then the model overview / scoping doc; then the Research Brief. **There is no paper manuscript** — writing begins only after the model is built.
- **Craft is retired as a canonical surface (2026-09-09).** It may survive as a personal reading/scratch space, but Claude does not read, reconcile against, or sync to it. "How it works" explainers now live in `40_DOCS/`. Historical note kept for the lesson (2026-07-28): Craft received a full content overhaul at 17:09 on 2026-07-28, AFTER the v2.6 snapshot of this file was taken at 11:26. For roughly six hours Craft was the more current surface and this file was the stale one. v2.7 reconciles them. The lesson is recorded because it recurred twice in one session: read the live hub before asserting anything about its contents, rather than trusting a snapshot that sits in context.
- **SQLite + local files** are the heavy data store (source of truth for data). Only summaries, schemas, diagnostics, and small aggregates travel into chats.
- **This file** is the lightweight current-state anchor that seeds default context.

---
## Objective

Put all three trade-asset classes — rostered players, draft picks, non-roster prospects — on one common scale: projected surplus value in dollars over a defined horizon, risk- and time-adjusted. Then back-test historical trades against realized outcomes to find categories of systematic mispricing. The cross-asset integration is the central contribution. Audience: economics faculty (supervisor **Karl**, econometrics) and sports-analytics practitioners. Karl weighs identification (circularity, look-ahead, selection) most heavily.

---
## Model spec

**Proposed rebuild plan (2026-09-14c; not adopted):** `50_REBUILD/docs/Player_Model_Rebuild_Plan.md` gives the staged plan requested for comparison, with Claude as intended builder. Thomas has not selected a plan. Existing production specification and work-queue order remain in force. See `sessions/2026-09-14c.md`.

**Core NPV:** `NPV = sum_t (Value_t - Cost_t) / (1+r)^t + Terminal Value`

- **Value_t** — projected production in dollars: a comparable-based aging curve x the cap-inflation-indexed dollars-per-win rate. Fit only on player-seasons observable at the valuation date.
- **Cost_t** — cap hit in dollars, prorated for mid-season acquisitions.
- **r** — discount rate: injury risk + opportunity cost of cap space.
- **Terminal Value** — zero if the contract expires into UFA; for RFA-expiring contracts, re-run the player model over the expected RFA-control years at projected qualifying-offer cost, using the WAR-only coefficient.

**Pillar 1 — Player asset model.** Surplus = production value minus prorated cap cost over the contract life. Production -> wins currency -> dollars at the market-derived rate (regress contract cost as cap-share on projected wins; slope = price of a win, intercept = replacement cost). **UPDATED 2026-07-28 (review Stage 3):** the rate is now fit by **left-censored regression** (a Tobit model), because 529 of 2,349 contracts sit exactly at the league-minimum salary and are not freely negotiated prices — treating them as observed prices dragged the fitted line up. The line is **straight in production, no contract-length term** (a pre-registered Stage 2 test found length carries no genuine outcome signal beyond what production already predicts, so its omission is not model error). **Position enters as a slope difference, not a separate intercept** — at zero measured wins forwards and defencemen are paid alike, so one intercept covers both, but defencemen are paid more per win above that. Two market regressions only — RFA and UFA (unchanged; the censored refit did not need separate lines for the two, same as before). ELC players are valued through the RFA regression: project their production, price it at the RFA rate (what they would command as an RFA), then subtract their slotted ELC cost. ELC salaries are CBA-set, not market-negotiated, so no separate ELC rate is estimated. Goaltenders handled separately on measurement grounds, rate unchanged by this update.

**Cap-share is the treatment of cap opportunity cost (review item 5.3, resolved 2026-07-28).** The spec previously implied a separate charge for tied-up cap space beyond the 3% denominator; that 3% is cap growth (dollar-year conversion), not an opportunity charge. Corrected: expressing value and cost as shares of the cap **is** the opportunity-cost treatment (a player consuming 10% of the cap is already charged 10% of the scarce resource, whatever the dollar level). No separate component added — one would double-count the cap-share framing and would barely move surplus **ratios** in any case (a uniform charge largely cancels across both sides of a trade). Documented limitation: the model does not price the optionality forgone by locking up cap space for many years; adding that charge would make long contracts look **worse**, so its omission is conservative relative to the project's headline long-contract finding, not flattering to it.

**Pillar 2 — Draft pick model.** A pick is a call option on an unknown player. Value via a bucketed yield curve (coarser buckets where the curve flattens), in the same dollar-surplus currency. Future picks: expected value over the standings-outcome distribution, discounted at a higher rate than players.

**Pillar 3 — Non-roster prospect model.** Project future surplus for unestablished players. NHLe (era-varying) translates junior/college/European production; a Bayesian pedigree update blends draft-slot prior with D+1/D+2 performance; risk-adjusted by a bust rate. Window up to seven years (3 ELC + up to 4 RFA), terminating at UFA eligibility.

**Back-test logic.** Per trade, compute NPV of assets sent vs received using only point-in-time information; the differential is the ex-ante prediction. Express each trade as a **surplus ratio (NPV sent / NPV received)** — robust to level errors in the dollars-per-win rate. Compare to realized on-ice outcomes measured by the **non-Bacon** game-level metric (the yardstick that breaks circularity for systematic claims). Decompose residuals: genuine mispricing vs team-fit premiums, private-information rents, monopsony pricing under trade-protection clauses.

---
## Resolved decisions & change log → DECISIONS.md

**Aging yardstick test (2026-09-10):** `20_CODE/aging_bandwidth_test.py` compared the shared scale with each target's median distance to eligible comparables. Whole-career holdout and historical training windows both gave slightly larger errors for the target-specific alternative (about 0.10%-0.18% across rate and season-total proxy outcomes). Production unchanged. Report: `40_DOCS/Aging_Yardstick_Comparison.md`; five generated `30_OUTPUT/aging_bandwidth_test_*` artifacts. Test-only exclusion of the merged Erik Gustafsson career needs a separate identity review. See `sessions/2026-09-10c.md` for scope and limitations.

**Aging comparables-limit test (2026-09-13):** `20_CODE/aging_comp_limit_test.py` v1.0 audited the production blend on real ages (effective comparables ~92% of the eligible pool; the pooled weight of 10 takes ~5% for every tier) and scored 14 rules on held-out careers. Keeping only the 50 most similar comparables, pooled weight retained, lowered error 0.3%-0.8% in all four all-player comparisons and 1.3%-2.1% in season totals for 3+ WAR/82 players; removing the pooled weight alone did nothing, and removing it from a limited blend made things worse. Evidence-weighted lambda and no shrinkage both lost. Production unchanged (locked). Report: `50_REBUILD/docs/Aging_Comparable_Limit_Test.md`; generated `30_OUTPUT/aging_comp_limit_test_*` artifacts. See `sessions/2026-09-13b.md`.

**Realized-vs-projected NPV by tier (2026-09-13b):** `20_CODE/npv_realized_by_tier.py` v1.0 compared the production chain's priced contract value with realized value on 4,677 played contract seasons. No overall bias, but a monotone tilt: under-projected below 1 WAR, over-projected above, +$0.98M per season (13.9%) at 3+ and +$1.49M (20.9%) for sustained stars. In-sample, contract part only. Generated `30_OUTPUT/npv_realized_by_tier_*` artifacts.

**Starting-point and market-line fix test (2026-09-13b):** `20_CODE/anchor_shrink_test.py` v1.1. A 2009-2017 starting-point pull-back improves forecasts for most contracts but overshoots stars; refitting the market line on pulled-back WAR changes no prices and with the pull-back returns production NPVs. Whether stars are over-valued depends on the back-test's undecided realized-value currency. Production unchanged. Report `50_REBUILD/docs/Anchor_Shrink_Test.md`; generated `30_OUTPUT/anchor_shrink_test_*` artifacts.

**Whole-chain sweep (2026-09-14):** `20_CODE/pipeline_experiment.py`, `market_line_experiment.py`, `games_line_experiment.py` v1.0. Rolling (pre-valuation) calibrations throughout. A rolling starting-point pull-back removes the level tilt on 2020-25 pages; the exit hazard is estimated on the wrong population (all seasons, not contracted ones) and over-predicts exits; the two together (L+H) are within 5% of unbiased at every level. Games played carry their own market price; a games-aware value line is a D6-D9 design question. Second pass (`market_line_search.py`, `pipeline_experiment2.py`, `games_line_experiment.py` v1.1): age in the pull-back makes the package near NPV-neutral; term in the value line cuts held-out cap-hit error 39% and adds $3.3-4.1B of NPV, a framing decision. Production unchanged. Report `50_REBUILD/docs/Pipeline_Experiment.md`; generated `30_OUTPUT/pipeline_experiment_*`, `market_line_experiment_*`, `games_line_experiment_*` artifacts.

**Rebuild plan, Fable version, and diagnostics (2026-09-14d):** `50_REBUILD/docs/Player_Model_Rebuild_Plan_Fable.md` is a proposal for rebuilding the player forecasting chain in six phases (frozen-information harness; component-wise shrunk ability forecast with rate and games separate; participation with returns; additive aging on the shrunk rate; contract-price model and production currency dated at the signing; valuation by simulation). Two test scripts carry its evidence: `signing_date_audit.py` v1.0 (the locked rate sample reads trailing seasons that 30% of contracts were signed before, 58% at 3+ WAR) and `component_persistence_test.py` v1.0 (shooting is 49% of WAR/82 covariance at year-to-year r 0.35; a component-wise rolling anchor cuts error 7-9% across horizons 0-2). Competing plan (09-14c): `50_REBUILD/docs/Player_Model_Rebuild_Plan.md`. Production unchanged. See `sessions/2026-09-14d.md`.

Moved 2026-09-09 (v3.2). The locked decision record (D1-D27, the Phase-1b/1c/1d blocks, the Phase 3a D22-D27 draft-curve block, and the Player Model Review Stages 2-5 item-by-item record) and the running change log for the state files now live in **`00_STATE/DECISIONS.md`**. `git log 00_STATE/` is the second, mechanical copy of that history. Per-session detail is in `00_STATE/sessions/`.

---

## Data & scripts inventory

**Data in hand (local source of truth; subset mirrored into the project)**
- `WAR.csv` — Bacon skater WAR, component-decomposed. 17,123 rows, seasons **2007-08 -> 2025-26** (regressions use 2015+; pre-2015 vintage excluded).
- `Goalies_WAR.csv` — Bacon goalie WAR. 1,639 rows. (The "not yet integrated" note was stale: the goalie pillar has been wired since 2026-06-30 and `goalie_value_spine_v2.csv` is live.)
- `nhle_temporal.csv` — era-varying NHLe. 2,196 rows, 142 leagues, 2006-07 -> 2025-26 (lockout year absent by design).
- `draft_slot_baseline.csv` — per-slot NHLer/Star probabilities. 225 rows, monotone decreasing.
- PuckPedia player-contract export + trades export (CONFIDENTIAL xlsx). Trades export: **980 trades, 2018-2026**, one row per asset per trade.
- `capspace_clauses.csv` / `capspace_clauses.db` — NTC/NMC scrape, 15,261 contract-season rows.
- `capspace_targets.csv` (1,672), `capspace_misses.csv` (30), `clause_disagreements.csv`, `capwages_per_season.csv` (14,720) — clause validation set.
- **NHL API game-log store (local `new_scrape/nhl_gamelogs.sqlite`, mirrored to Dropbox `10_SOURCE/`)** — scraper v2.4 full run: 11,870 games (2017-18 -> 2025-26), 427,241 skater-games, 8 raw tables (incl. 1.39M shot events, 8.67M+ shift rows; 582 games recovered via the HTML shift-report fallback). Model output tables now include `shot_xg` (1,019,261 scored shots), `shot_score_state` + `score_state_factors`, and **`player_game_value` (427,241 rows — one goal-denominated value per skater per game, with team)**. Only summaries travel into chats; the in-project `games.csv`/`goalie_games.csv`/`goal_events.csv` copies are stale v1-era subsets slated for removal.
- **`contract_season_spine.csv` (15,918 contract-seasons)** and **`contract_level_spine.csv` (6,851 contracts)** — join outputs; the model's cost backbone. (In the project.)
- **`skater_value_spine.csv` (11,821 rows, 6,892 priced) — NEW 2026-07-05.** Layer 1 output of Phase 1b: skater Value_t/Cost_t/Surplus_t per contract-season, 2015-2025. Local parity confirmed. (In the project.)
- **`contract_npv_spine.csv` (2,909 contracts) — NEW 2026-07-05.** Phase 1d output: one discounted NPV per contract (contract + terminal components), both positions, valued from each contract's first 2018-2025 season. The first artifact in the project that is a real, summed, discounted NPV. (In the project.)
- **Draft-pick pillar artifacts — NEW 2026-07-19:** `draft_pick_linkage.py` v1.1 (NHL Records pull + guarded resolution: ID-with-name-agreement, 19 aliases, collision blocklist, temporal guard, 12 variant unions) → `draft_pick_linkage.csv` (4,765 picks 2005-2026, war_names pipe-separated); `draft_yield_curve.py` v1.1 (D22-D27, verified CBA constants embedded) → `draft_pick_outcomes.csv` (2,324-pick audit panel) + `draft_yield_curve.csv` (the locked curve, Rules A and B). RESOLVED 2026-07-30: `draft_pick_linkage.py` and `draft_yield_curve.py` are in Dropbox `20_CODE/`; the three CSV outputs are in `30_OUTPUT/`.
- **`WAR_with_age.csv` — regenerated 2026-07-05** via `age_join.py` (60.1% player match, 70.9% of season-rows aged; age = Feb 1 of the season's ending year). Feeds the aging curve and the exit-hazard age join.
- Research Brief (PDF); `WAR_AAV_Regression_Report` **v2** (v1 superseded and removed from the project).

**Document framing (read carefully)**

- **Doc 2 follow-up (2026-09-10b):** current supervisor copy clarifies the evidential status of projection safeguards, negative-baseline math, and exit-model pooling. The similarity-weight passage remains for the user's own rewrite after an explanation in chat. Other edits preserved; no model changes. See `sessions/2026-09-10b.md`.

- **Doc 2 aging revision (2026-09-10):** `40_DOCS/Supervisor_Drafts/Doc_2_Player_Pillar_I.docx` incorporates the user's edited Downloads copy and replaces only Section 3 with a calculation-ordered explanation addressing four annotations. Other user edits preserved exactly. Text/core schema and worked examples checked; Word pagination remains unavailable. See `sessions/2026-09-10.md`.

- **Current supervisor review copies:** `40_DOCS/Supervisor_Drafts/Doc_2_Player_Pillar_I.docx`, `Doc_3_Player_Pillar_II.docx`, `Doc_4_Drafting_Prospects_Unbuilt.docx`, and `Doc_5_Cross_Cutting.docx`. Created 2026-09-09 after the user found the earlier rewrite too compressed. Restore explanatory depth, evidence, and examples while retaining factual qualifications; parent-directory shorter copies left unchanged. Text/core schema checked, Word pagination unverified. See `sessions/2026-09-09g.md`.

- Docs 2-5 in `40_DOCS/` were rewritten against implementing code on 2026-09-09. They distinguish built components from plans, qualify retrospective information exposure, and correct surplus-ratio and bias interpretations. Text, ZIP/XML, and core WordprocessingML schema checks pass; visual pagination remains unverified because the bundled renderer is unavailable. See `sessions/2026-09-09f.md`. No model specification or locked result changed.

- `40_DOCS/Repository_Review_and_Doc_1_Edits.md` — GitHub/source review dated 2026-09-09, with proposed Doc 1 passages and newly recorded follow-ups. Does not revise locked model results; see STANDING_FLAGS and `sessions/2026-09-09c.md`.

- `40_DOCS/Doc_1_Circularity_and_Game_Value.docx` — new 1370-word draft incorporating user-provided editorial feedback, 2026-09-09. Text and XML checked; schema and visual pagination QA unavailable in the current runtime. See `sessions/2026-09-09e.md`.
- **There is no paper manuscript.** The file labelled `NHL_..._Paper_v6.docx` is the model **overview / scoping document** — it states what the model will do and what the back-test looks for, not written-up findings. It is out of date and slated for replacement. **No paper is written until the model is built.**
- The `Model_Open_Questions_v3` doc has been **removed from the project** (canonical open questions live in `00_STATE/STANDING_FLAGS.md`).
- `NHL_Trade_Model_Build_Roadmap.docx` — **CORRECTION (2026-07-03): located.** It sat in the cloud root (created 2026-07-02); v1.5 wrongly recorded it as not locatable. Content is superseded by the re-sequenced Work Queue and by the four sequence documents. DELETED 2026-07-30 during the file-system migration; recoverable from Dropbox trash.

**Scripts built (reconciled against what is locatable)**
- `skater_value_engine.py` — **UPDATED 2026-07-27 (item 1.5: sums a traded player's team-halves instead of discarding one, before the games filter, with an 82-game guard against merging two same-named players). NEW 2026-07-05.** Phase 1b Layer 1: builds `skater_value_spine.csv` from trailing WAR + the new locked skater-only rate + the D10 league-minimum floor. Two-stage reproduction guard baked in (must pass before any output is trusted). Excludes the merged-name rows (Ryan Johnson, Nathan Smith); resolves the Sebastian Aho (D) / WAR.csv "Sebastian Aho Swe" alias explicitly. (In the project; local parity confirmed 2026-07-05.)
- `skater_forward_projection.py` — **v1.3, UPDATED 2026-09-13 (D28: `contract_chain()` / `check_as_of()` / `page_date()` / `load_signing_dates()`, `project_contract(player_id, valuation_season, as_of=None)` now includes extensions signed by the as-of date; CAP_CEILING gains 2026 $104.0M and 2027 $113.5M; one-season-left path label fixed, value-neutral).** v1.2, UPDATED 2026-07-27 (item 1.3: RATIO_FLOOR=0.0 plus a `ratio_floored` flag column; item 1.5: its OWN copy of the WAR loader fixed — this is the copy that prices contracts; item 1.6: curve lookup now goes through `career_key`). NEW 2026-07-05.** Phase 1b Layer 2: `SkaterProjector.project_contract(player_id, valuation_season)` projects each remaining contract season via the D3 decay path (aging curve as ratio path on the raw-WAR anchor), D12 v3 negative-anchor replacement-reversion, D11 ex-ante ceilings, D10 floor. Imports Layer 1 constants; requires `aging_curve.py` + `WAR_with_age.csv`. Boundary guard added for panel-edge ages (the locked aging engine IndexErrors past its max age — left untouched, wrapped instead).
- `rfa_terminal_value.py` — **v1.3, UPDATED 2026-09-13 (D28: control years attach to the end of the contract chain; `terminal_value(..., as_of=None)`).** UPDATED 2026-07-27 (item 1.10: max-salary fallback where available, `qo_salary_source` tag, guard against substituting while a real salary is on file, source split reported in the run log). NEW 2026-07-05.** Phase 1c: `TerminalValuer.terminal_value(...)`. UFA/"no QO" → 0; RFA → Layer 2 walk through control years vs iterated era-aware QOs (D13 truncation, D14(c) empirical qualify-gate calibration re-estimated each run). QO mechanics assert-self-test on import.
- `exit_hazard.py` — **v1.2, UPDATED 2026-07-27 (item 1.4: cells come from a fitted additive model, not raw cell means; `(bucket,"ALL")` marginals stay raw; `unknown`-age cells no longer emitted; four guards including a calibration check. NEW DEPENDENCY: statsmodels + scipy — this file used to run on numpy and pandas alone).** NEW 2026-07-05. Phase 1a (D18): estimates the exit hazard (P(no NHL season at t+1)) by quality×age from the panel. Exposes `build_transitions` / `build_hazard_table` as importable functions so `contract_npv.py` shares one code path (no drift). Skater table; goalie table built by the same functions inside the NPV engine.
- `contract_npv.py` — **v1.4, UPDATED 2026-09-13 (D28: `npv(player_id, valuation_season, as_of=None)`, same chain in the goalie branch; summary carries `as_of` and `chain`).** v1.3, UPDATED 2026-07-27 (item 1.2: hazard indices read at k−1 on BOTH axes, with a `legacy_hazard_index` audit switch that re-measures the correction into the run log every run; item 1.4: goalie-table audit reported here since the goalie panel is built here). NEW 2026-07-05.** Phase 1d: `NPVEngine.npv(player_id, valuation_season)` stacks Layer 2 + terminal value + survival weights + 3% denominator into one discounted contract NPV, both positions. Contains the goalie mini-engine (`GoalieProjector`, flat projection, self-calibrating goalie rate recovered from the spine). Writes `contract_npv_spine.csv`. Has a diagnostic k=0 consistency check that prints the offending player/season before failing (added after a stale-spine mismatch was traced this way on Thomas's machine).
- `contract_npv_panel.py` — **v1.1, UPDATED 2026-09-13.** Validation panel (never a back-test input), now 2018-2026: 7,565 rows, 626 on the 2026-27 page (May 2026 export; summer-2026 signings missing). Each page valued as of July 1 of its season; new columns `as_of_date`, `n_extension_contracts`, `extension_contract_ids`.
- `player_dashboard.py` + `player_dashboard_template.html` — **v1.1, 2026-09-13.** Local viewer (`30_OUTPUT/player_dashboard.html`, embeds confidential PuckPedia data, never shared). Pick a player and a date; shows the page in force, with in-season extension variants from their signing dates (D28). Re-runs the engine for every page and variant and refuses to write unless it matches the panel within $1.
- `aging_curve.py` + `age_join.py` — **BOTH UPDATED 2026-07-27.** `aging_curve.py`: item 1.6 (careers keyed on the cleaned name via `career_key`, `CURVE_NAME_SPLITS` for the two Elias Petterssons, team-halves summed) and item 1.7 (adjacency required for the two-season window, non-adjacent entries dropped from the comparables pool, trend divides by the real age gap). `age_join.py`: item 1.8 (`join_on_id_and_name()` + `id_name_conflicts()` + a guard self-test + `age_join_id_conflicts.csv`). Previously described as **finalized** mean-reversion aging engine (lambda=0.55, player-split cross-validated) and hardened age join. (In the project.)
- `join_clauses_to_spine.py` + `join_clauses_runlog.txt` — clause-to-spine join and validation log. (In the project.)
- **Game-level model chain (built + validated end-to-end 2026-07-03; Phase 4a):**
  - `nhl_gamelog_scraper.py` **v2.4** — JSON API scraper + legacy HTML shift-report fallback (recovered all 582 gap games; 0.00 min TOI reconciliation) + foreign-team shift filter. Prints SCRIPT_VERSION on every run (stale-file guard — three stale-run incidents this project).
  - `on_ice_reconstruction.py` **v1.3** — matches shifts to shot events (99.72% headline code-match; 117 suspect-code games flagged); **roster-truth rule** (box score is roster truth) neutralizes three NHL-feed corruption modes found in exactly 3 games league-wide.
  - `xg_model.py` — logistic xG on distance/angle/type/strength/rebound; holdout AUC 0.739; xG/goals ratio 1.000; three label-leak bugs caught pre-ship via coefficient sanity checks.
  - `score_state.py` — goal replay -> leading/tied/trailing tags (11,870/11,870 games reconcile exactly); EV factors 1.046/1.000/0.958 (trailing share 52.2% on xG).
  - `metric_assembly.py` — combines score-adjusted on-ice xG (equal split by actual on-ice counts — accounting identity exact at +0.000000), penalty component (v=0.2097 goals/drawn penalty), ixg stored separately. Orphan tripwire guards the roster join. **Headline validation: season-level R²=0.583 vs team goal differential, fitted to nothing; goals-per-win = 5.90.**
- `ep_extract.py` — Elite Prospects extraction (TopDownHockey_Scraper; cached, rate-limited, SQLite). (In the project.)
- `capspace_scraper.py` + `capspace_capwages_compare.py` — clause scrape + CapWages comparison. (In the project.)
- `capspace_capwages_finalize.py` — **built (2026-06-11), tested on a 48-player subset only, never run to completion.** This was Phase 2 of a two-stage CapWages-adjudicated workflow (compare -> manual XLSX review -> finalize) intended to produce `capspace_clauses_final.csv`. The full CapWages scrape + manual adjudication step was never launched. **Superseded** by the direct join script below — do not revive unless a more rigorous clause cross-validation pass is explicitly requested later.
- `capspace_validator.py` — **built and run (2026-06-11)**, not located as a standalone file in the project. Surfaced 4 WARN cases (data-quality disagreements, not parser bugs), resolved manually. Validation work is done; the file's absence from the project is not a gap.
- `parse_capfriendly_trades.py` — **not located.** Contingency parser feeding `trades.db`, off the critical path; do not block on it.

**External sources:** hockeystats.com/TopDownHockey (all player value + NHLe); cap-space.com (clauses, MIT GitLab, ID-keyed URLs); CapWages (clause cross-check); Elite Prospects (via TopDownHockey_Scraper); NHL JSON API (game-level); CapFriendly via Wayback (contingency -> trades.db).

**Pending / missing**
- ~~**`Reevaluation.pdf`**~~ — **RESOLVED 2026-07-28.** Thomas confirmed it has already been fully actioned outside the project record. Removed from the cloud root before the 2026-07-30 migration. No further action.
- **`Model_Review_Resolution_July_2026.md`** — the plain-language Stage-2-5 resolution document generated 2026-07-28 as a chat deliverable. **RESOLVED 2026-07-30.** Uploaded to Dropbox `40_DOCS/` during the file-system migration, and retained in the Claude project.
- ~~**Script and run-log staleness**~~ — **RESOLVED 2026-07-30 by the Dropbox migration.** The 2026-07-28 Drive survey found no `draft_yield_curve.py`/`.csv` newer than 2026-07-20, and no updated `skater_value_engine.py` / `rfa_terminal_value.py` reflecting either the 2026-07-27 Stage 1 fixes or the 2026-07-28 Stage 2-5 rebuild; both the cloud copies and the Claude-project mirror were two full review sessions behind. The migration resolved this by consolidating a single live copy of each script into `20_CODE/` and archiving the superseded duplicates. The audit was also more serious than the survey showed: the cloud held two competing script sets, and the stale set contained Dropbox conflict copies (`aging_curve (1).py`, `age_join (2).py`, and nine others). Six files in the Claude project were stale, four of them wrong rather than merely old, and all six were removed. **Standing replacement for this item:** run the `audit files` protocol in Section 12 rather than an ad hoc survey.
- ~~`capspace_clauses_final.csv`~~ — **abandoned, not pending.** Was the output of the two-phase CapWages-adjudicated finalize workflow (never run to completion); superseded by the direct join script, which produces `contract_season_spine.csv` / `contract_level_spine.csv` straight from `capspace_clauses.csv` via most-restrictive-clause collapse. P1 is effectively **closed** — the clause data is already joined and live in the spine.
- Goaltender WAR integrated into the spine (P2).
- Elite Prospects production pull — prospect-pillar data not yet extracted (P3).
- Mid-season allocation model — **model chain BUILT and validated (2026-07-03); the allocation *application* (splitting back-test trades around trade dates using `player_game_value`) is the remaining step (Phase 4a-ii).**
- A saved file of the three notes-only regression findings (RESET floor, goalie slope + low YoY correlation, defence weakest fit).
- NHLe slug crosswalk — generated, not yet verified.
- `trades.db` 2018-2022 spot-validation (contingency).
- ~~Data-quality note: `puckpedia_player_id` 17422~~ — **RESOLVED 2026-07-28.** It is **Stanislav Demin**, age 19, traded Vegas to Chicago on 2020-02-24 in the three-way Robin Lehner deal with Toronto. He is a non-roster prospect with no PuckPedia contract, which is why a contract-keyed export carries no name or EP id for him. Genuinely a one-off: of 1,503 trade rows carrying a `player_id`, exactly one has no name. Not a data defect — the prospect pillar showing up before the prospect pillar exists. Resolves itself at Phase 3b.

---
## Experimental player-model rebuild → `50_REBUILD/` (2026-09-14/15)

**Status: experimental, isolated, nothing adopted into production.** The live chain in `20_CODE/`
is untouched and every locked decision stands. The rebuild lives in its own tree with its own
output and its own gitignore; writes are refused outside it by a path guard, so the separation is
enforced rather than promised.

**Built and guarded.** A frozen-information harness (`forecast_harness.py`, `information_set.py`),
one shared season table with a reproduction guard that matches the production loader on all 14,193
keys at zero difference (`player_season_table.py`), an ability forecast with a three-season window
and fitted decay (`ability_forecast.py`), an additive aging curve with a survivorship correction
(`aging_additive.py`), a participation model (`participation_model.py`), a signing-dated contract
price model and production currency (`contract_price_model.py`, `production_currency.py`), a
predictive-interval layer that turns any of those forecasts into a distribution over a season
(`predictive_interval.py`), and the runners that produced the reports in `50_REBUILD/docs/`.

**Review correction, 2026-09-15:** the reported 16.0%/43.6% error improvements and +0.999 to
-0.365 star-bias comparison use a flat 60/40 benchmark, not the live chain's aging and survival.
The original stress runner reproduces, but the independent review confirmed inconsistent
shortened-season rate/games units, unfitted participation horizons after year six, market fits
split by contract starts rather than signings, and incomplete harness sample guards. Historical
dollar illustrations also use future actual caps without discounting. The forecast-page seal
does not cover the market-selection runners. See `50_REBUILD/docs/Player_Rebuild_Candidate_Review_Codex.md`.
These findings take precedence over the earlier broad validation claims. No implementation was
changed; repaired development comparisons and the unbuilt simulation work must precede adoption.
Thirty variants remain registered in `50_REBUILD/docs/variant_register.csv`.

**Goalie price line corrected after review, 2026-09-22.** `run_goalie_price_line.py` v2.0. Two
conclusions withdrawn. (1) The first pass compared no goaltender terms against a goaltender level AND
slope; on the same 174 contracts a **level alone** gives 0.007457 mean absolute error against 0.007489
with the slope as well, better than no terms in 100% of goaltender-resamples, while adding the slope
wins only 10%. So goaltenders need a price adjustment, a different level delivers all of it, the
slope has not earned its place -- which is not evidence the slopes are equal -- and **D7 is not
settled**. (2) What was reported as dollars per win was the partial slope on the season average with
first-year production held fixed; defined as one more expected win in every season it is **$2.022M
for a skater against $2.167M for a goaltender** (UFA; $1.928M/$2.073M RFA), a ratio of 1.07 rather than
1.18, as changes in the fitted annual price before the floor and not contract values. Sample
corrected to 263 eligible -> 205 with a forecast -> 174 priced; every line uses the same expanding
quarterly scheme; and the +0.167 WAR participation figure is re-labelled an illustration of scale,
not a decomposition. Suite 33/33. **Goaltender price specification provisional**; participation next.
See `50_REBUILD/docs/Goalie_Price_Line.md`.

**The goalie price line, 2026-09-18b.** `run_goalie_price_line.py` v1.0 answers whether a goalie
win prices like a skater win, which decides whether goaltenders can sit on the project's single
scale. One censored line over both populations with a goaltender indicator and an interaction,
refitted at each signing quarter on contracts signed before it. On the last fit **a forecast win
from a goaltender prices at $0.96M against $0.82M from a skater, a ratio of 1.18**; across the
window 0.74 to 1.57, with the spread almost entirely in fits under 600 contracts and the ratio
settling between 0.87 and 1.22 from 900 on. Reported as a conditional association, never as the
price of a win: the two forecasts are built by different rules, so part of any slope difference is
that difference. **Held-out error on goaltender contracts says a goaltender does not belong on the
skaters' line unchanged** -- 0.0103 cap share with no goaltender terms against 0.0075 with them.
**[CORRECTED 2026-09-22]** A goaltender LEVEL alone achieves the same (0.007457 against 0.007489 with
the slope too), so the two-term claim and "one market with two terms" are withdrawn; D7 is not
settled; the sample is 263 -> 205 -> 174, not 266; and the $0.96M/$0.82M figures are partial slopes,
not dollars per win.
`contract_price_model.contract_sample` now takes a position group so both samples come off one
census. Suite 33/33, the new check verified by breaking it. Nothing adopted. See
`50_REBUILD/docs/Goalie_Price_Line.md`.

**Goalie comparison corrected after review, 2026-09-18.** Three findings, all fixed.
`run_goalie_bakeoff.py` v2.0 now **imports production's own `GoalieProjector`** rather than a
reimplementation of it: the first pass was built from a partial reading of the method and missed
production's absent games filter, its strict slot rule with a stale anchor for a goaltender with no
t-1 season, and the **0.650** shrinkage target for that returning population -- up to 2.28 WAR away
on a single goaltender. The paired bootstrap now keys on (page, goaltender, horizon); joining on
goaltender and horizon alone turned 3,683 intended pairs into 19,853 rows. And the ageing candidate
now uses age: it had taken the intercept of its own regression and applied one drift to everyone,
so adding twenty years to every subject moved nothing. **Corrected: production's projector is the
best forecast at 1.488 MAE and nothing beats it** -- the closest candidate is +0.003 and wins 34% of
resamples, so the earlier improvement claim is withdrawn. **The bias is a diagnostic and not an established defect**
[qualified after review]: production's +0.101 mean error carries a career-bootstrap interval of
-0.129 to +0.315 that contains zero, and the shared participation estimator predicts 64.1% of these
seasons played against 55.3% observed, a gap illustrated at +0.167 WAR (an illustration of scale,
not a decomposition) and carried by every candidate -- so the pooled error cannot be attributed to an ability forecast and no dollar price
should be moved to cancel it. Weighting by workload is the clear negative (+0.097, 0%). On ageing, the
"not identified" claim is **withdrawn**: fitted properly the age slope is negative on every page
(-0.005 to -0.088 per year of age) and it is the common DRIFT that flips sign (+0.117 to -0.106);
the slope still does not beat production (+0.065, 0%). Suite 32/32 with four reintroduced defects
caught. Nothing adopted. See `50_REBUILD/docs/Goalie_Bakeoff.md`.

**The goalie branch opens, 2026-09-17f.** `goalie_season_table.py` and `run_goalie_bakeoff.py`
v1.0. The goalie panel is built in the skater table's schema so the harness, information set and
scoring work on it unchanged: **1,560 goaltender-seasons, 280 goaltenders**, 82 a season against
roughly 700 skater-seasons, one WAR number with no component split, and a games share that measures
ROLE rather than availability (median 0.44; no goaltender in the panel has played 82 games, the
busiest being 77). Six candidates scored on the same grid with one shared participation estimator.
**Production's locked rule (50/30/20, keep 0.35, league average 2.189, flat) carries a +0.218 WAR
bias at every horizon**: the constant sits above the development window's own mean. Measuring the
average at the page removes most of it and 0.071 of the error (100% of goaltender-resamples);
fitting the kept weight gives 0.43 rather than 0.35 and another 0.020. Workload weighting does
nothing (78%). The flat carry survives, but the age term it would replace is **not identified** --
the fitted average change flips sign from +0.117 on the 2015 page to -0.106 on 2021, which is the
Phase 3 survivorship problem on a twelfth of the sample, so flat is defensible because ageing
cannot be measured here rather than because it was ruled out. Suite 30/30 with both new checks
verified by deliberate breakage. Nothing adopted; no price, no dollars. See
`50_REBUILD/docs/Goalie_Bakeoff.md`.

**Control-year repair after review, 2026-09-17d.** Four findings, all fixed. Ownership now rests
on **eligibility alone** rather than the export's realised expiry label, which records a club
declining to qualify a player years after the signing being valued; the sample goes from 252
contracts to **398**, and the eligibility year is audited against the age-27 rule (89.3% exact, 130
earlier via accrued seasons, none later) and bounded by pricing the whole sample again on the age
rule alone (+$0.026M a contract). The informed rule now conditions only on the misses of seasons the
player actually **played**, integrating the unobserved ones out; conditioning on all of them had
moved the first control year's decision on 188 of 252 contracts. The qualifying-offer BANDS are now
dated like the floor, so a 2021 signing pricing a 2026 control year sees the pre-2026 regime. And
the rule set is now six rules differing one change at a time, so **the value of information is
$0.066M a contract**, not the $0.266M first reported -- that figure compared pricing the mean
against averaging the price, deciding in advance against deciding on the path, and stopping at the
first loss against counting later years, all at once, and is withdrawn. Being able to walk away at
all is worth **$0.422M**, six times the information. Production's own terminal value reads the same
expiry label (130 of the 187 zero-terminal contracts carry one of the two labels it zeroes outright: 97 "UFA no QO", 33 plain "UFA"), which is flagged as a finding about
production. Suite 28/28 with each defect reintroduced and caught. See
`50_REBUILD/docs/Control_Years.md`.

**The RFA walk-away and the control years, 2026-09-17.** `control_years.py` and
`run_control_years.py` v1.0 price the seasons a club holds after a contract expires with the player
still restricted: 252 of 1,217 development contracts, mostly one- and two-year deals. Control is a
right, so it is priced as a stopping rule on drawn paths under four rules differing only in what the
club may know -- take every year (-$0.556M on one control year), decide the whole schedule in
advance off the point projection as production does (+$0.079M), decide each year on what the path
has shown so far (+$0.190M), or know the whole path (+$0.367M). Across all 252: 0.136 / 0.451 /
**0.716** / 0.950 $M. **Deciding as you go is worth $0.266M a contract over deciding in advance**,
which is the part of the asset a point valuation cannot reach. The informed rule uses the
simulation's own fitted persistence to update the forecast on realised misses, integrated through
the empirical shape, and conditions participation on the current state; it is asserted to move not
at all when every season from the decision onward is redrawn. The ceiling is the best prefix, not
stopping at the first loss, because walking away is final. Offer bands reimplemented in this tree
and checked against production's at $0.00 on 4,000 cases; the league minimum is now dated like the
cap ceiling and carries the published 2026-29 schedule. Known approximation: the offer's base
salary is the contract average rather than the final year's salary (155 of 593 measurable contracts
have a higher final salary, 90th percentile 1.10), which makes the offer too cheap and the right too
valuable. Suite 28/28, the three new checks each verified by deliberate breakage. Nothing adopted;
the control value sits beside the contract's surplus rather than inside it. See
`50_REBUILD/docs/Control_Years.md`.

**Valuation integration and production reconciliation review, 2026-09-16 (repaired
2026-09-17):** reviewed `bc724e5` in isolation. The integration table builds and the raw
cross-model comparison reproduces; the reconciliation was not ready to close. Three findings,
all now repaired. (1) The reported "survival effect" also removed discounting, because
production's `surplus_no_survival` is undiscounted surplus plus terminal value at its own
reference date; the negative effects it produced were the warning. Rebuilt from production's
per-season detail with cost, discounting and terminal value held, the hazard is worth +$0.86M at
four years, +$1.69M at six, +$1.67M at seven and +$2.29M at eight, against gaps of $5.03M,
$15.86M, $24.61M and $33.63M. **The supported claim is only that the exit hazard alone does not
explain the long-contract gap**; the earlier claim that the gap lives on the value side is
withdrawn. (2) Contract IDs alone do not establish the same asset at the same date: production's
sweep labels output with the ID it requested and its engine can value another (10 rows), and the
two sides also differ on season count (3), terminal control value (185), cost by more than 10%
(46) and valuation versus signing year (240); 912 of 1,141 pass the four asset tests, of which
217 have a valuation year away from the signing year, leaving 695 -- not "comparable on every
test", and 17 of the 22 eight-year contracts carry the date flag. Flags and reasons are written
per row. (3) The integration's guards accepted mutated inputs: a $1M
shift in every simulated point surplus, a duplicated production contract, and reserved start
years all passed. `run_valuation_integration.py` v1.2 and the new
`run_production_reconciliation.py` close all three. A second review pass (`f452cd7`) confirmed
the corrected hazard effects contract by contract to within $4e-09 and found two residual items,
both now fixed in v1.2 of the reconciler: the hazard arithmetic mixed fresh engine details with
saved spine totals (a $1M shift in the saved totals alone produced 1,043 negative effects, printed
as a count and not failed), and the 912-row group was labelled "comparable on every test" when it
does not include the date flag. Term-group means account for 84.8% of
the squared variation in the dollar gap. The independently regenerated `goalie_value_spine_v2.csv`
hashes to the locked `55c935dd...` in the reviewer's checkout, so the container-local
`7e481bf4...` is unexplained and the float-formatting guess is withdrawn. See
`50_REBUILD/docs/Valuation_Integration_Review_Codex.md` and
`50_REBUILD/docs/Production_Reconciliation.md`. No production code or source input was changed.

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

**RFA control-year repair review, 2026-09-17:** verified `fc4190d` in isolation.
Reproduced 28/28 checks and 398 contracts; declared/informed/oracle means
$0.636647M/$0.704391M/$0.903579M. All four old-defect mutations are caught;
hidden missed-season interventions now move nothing. Targeted filter, observation,
historical-QO, and matched-pricing repairs are verified. Proceed with further
prototype development, with scope corrected: the policy counts expected later
profits but omits the option to learn and stop later. A Gaussian two-season example
returns zero under the implemented rule versus 0.12336 under a feasible informed
rule. The $67,745 gain is specific to these policies; $838 does not measure the
full continuation option. Age-only sensitivity is $25,867 on common draws, close
to the reported $26,318; 356 unchanged windows are now identical. It is not a bound
on historical eligibility bias. Correct stale salary/front-loading prose and
production-zero counts (97 no-QO plus 33 plain UFA, not 130 no-QO). Before adoption,
resolve historically admissible eligibility, offer costs, and policy scope; retain
remaining goalie/joint-path/dollar-scoring/back-test work. See
`50_REBUILD/docs/Control_Years_Repair_Review_Codex.md`. No candidate merge,
production edits or adoption. Earlier simulator/reconciliation closures stand.

---

**Goalie branch review, 2026-09-17:** reviewed `08731eb`, including `b36a738`.
RFA corrections verified: 356 unchanged windows exactly equal; salary coverage
339 with 221/110/8; approximate-policy and sensitivity limits disclosed. Prior
RFA prototype clearance stands. Goalie panel and table reproduce: 1,560 seasons,
280 goalies, six rules with 3,683 cells each, full suite 30/30. Three corrections
precede forecast selection: the production-labelled rule excludes low-GP priors,
changes gap handling, and omits the 0.650 stale-history target; bootstrap omits
page and expands 3,683 pairs to 19,853; the aging challenger applies a common
intercept drift and discards the age slope. Actual production projector through
the shared participation estimator has MAE 1.48784 versus fitted candidate
1.49123; difference +0.00339, goalie-cluster 95% interval [-0.01516,+0.02206].
No decisive improvement over production. Corrected workload bootstrap win share
37.5%, not 78%. Adding 20 years to subjects changes the age candidate by zero.
Retain panel; correct benchmark/pairing and narrow aging claims before choosing
what enters the goalie price line. See `50_REBUILD/docs/Goalie_Branch_Review_Codex.md`.
No candidate merge, adoption, production edit, or confirmatory-page access. Earlier
simulation/reconciliation closures and remaining Phase 5 limitations stand.

---

**Goalie price-line review, 2026-09-22:** reviewed `16d1d5f` in isolation.
Original run and 33/33 checks reproduce; all 52 captured executed fits converge,
and both check-33 mutations are caught. Two corrections precede price-specification
closure: the missing level-only challenger matches the gain on the same 174 goalie
contracts (MAE .007456 versus .007489 with both terms), so a separate goalie slope
is not established; reported dollar-per-win levels omit first-year and RFA effects.
Last-fit UFA +1 expected win in each season changes latent annual price by
$2.022M/$2.167M for skaters/goalies, versus the reported first-year-fixed partial
slopes $.819M/$.964M. Interaction remains a conditional contrast; table levels and
ratios need the forecast-change definition. Development goalie sample is 263
eligible, 205 forecast-attached, 174 pooled-priced. All fits use expanding samples
at quarterly cutoffs; goalie-only prices five under the chosen 200-row minimum.
See `50_REBUILD/docs/Goalie_Price_Line_Review_Codex.md`. Participation work may
proceed with price specification provisional; do not treat two terms as settled D7.
Bias diagnostic is qualified, but its +.167 calculation is illustrative, not an
identified decomposition. Prior forecast/RFA/simulator/reconciliation closures stand.
No model edits, candidate merge, adoption, or confirmatory market scoring.

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

**Fourth repair verification, 2026-09-15:** reviewed `4b9723a` in isolation. All 17 repair
checks pass with no skips. Independent full-run audit confirms identical coefficients across
18 comparable quarters and zero shared-currency repricing differences for all 12 named cases.
The all-rejected request returns zero rows and one rejection record; empty input also passes.
The two preceding findings are closed. See `50_REBUILD/docs/Fourth_Repair_Verification_Codex.md`.
No new blocking defect found in the changed paths. Next milestone is the remaining simulation,
A3, control/goalie, uncertainty, dollar reconciliation and final-validation work. Rejection
CSV reporting still is not a complete per-run sample audit. Candidate implementation remains
unmerged; production code and the previously verified forecast specification are unchanged.

**Predictive uncertainty and the leakage battery, 2026-09-15c.** The forecast now states a
range, which the harness has been scoring since it was written and finding empty every run. The
distribution is a mixture: a lump of probability on exactly zero for the seasons a player spends
out of the league, and a fitted spread around the conditional forecast for the seasons he plays.
The spread is fitted rolling, by replaying the model on pages whose outcome seasons had all
finished before the decision date; scale is a line in the size of the forecast fitted per season
ahead, shape is the empirical distribution of the scaled misses. `run_uncertainty.py` reports
coverage and width by horizon and by subgroup within horizon; `run_leakage_tests.py` runs five
tests, four of them about look-ahead. The new tests all pass with the largest change to any
forecast or band exactly zero, including the one the previous spot check could not do: handing
the model the whole source and relying on its own outcome-window rule rather than on the
harness's filter. Three guards (18-20) are added to the reviewer's suite, one of them on the
interval layer itself, because it is the first component in the tree that reads outcomes at fit
time. **Run on the full table** (98.3% age coverage, 32,946 replayed misses, 40,510 scored rows), then
**revised after independent review**. The aggregate calibration is good: the 80% band holds 82-84%
of seasons at every horizon and the 90% band holds 91-92%, both erring slightly wide. **The
subgroups are where the work is, and they fail on the two populations the project already knows
are weakest.** At the stated 80% the 3+ tier falls from 0.847 at the valuation season to 0.608
five seasons out and the 22-and-under band runs 0.761 to 0.663, while the 34-and-over band
over-covers to 0.977; 18.5% of played star seasons at five out finish above their own page's 95th
percentile, where 5% is intended. Two causes are visible in the misses -- a star middle at +0.51
against the band's own -0.11, which points at the star residual, and star and young right tails at
+3.64 and +3.55 against a pooled +2.56, which points at the band -- and **the share carried by
each is not established**, because the diagnostic conditions on playing while coverage includes
non-participation. **The band was not widened**: that would hide a known bias behind a bigger
interval. The review also found and this branch fixed a sensitivity test that refitted while
claiming not to (reversing its headline), a residual diagnostic that used the last page's
calibrator for every page, and a predictive distribution whose mean sat up to 0.23 wins above the
point forecast because the shape was never centred -- the last of these passed every existing
guard. Report:
`50_REBUILD/docs/Predictive_Uncertainty_and_Leakage.md`; review:
`50_REBUILD/docs/Uncertainty_Implementation_Review_Codex.md`.

**An aggregate contract simulator (2026-09-16d, revised after review). Phase 5 is NOT closed.**
`npv_simulation.py` draws career paths: participation as a two-state chain that allows a return and
reproduces the model's marginals exactly, and the forecast's miss correlated across seasons through
a Gaussian copula that leaves each season's fitted shape untouched. The review found the runner
using a 2025 calibration -- holding outcomes through 2024 -- for all 1,217 earlier contracts, a
look-ahead in the only part of the chain that reads outcomes; each contract now uses its own page
and **check 25** enforces it by corrupting the future and requiring every calibrated quantity to be
bit-identical. It also found rank correlations handed to the normal draws without the
rank-to-Gaussian conversion (0.427 asked, 0.410 delivered), now inverted and tested analytically
rather than by Monte Carlo. Returns are modelled rather than excluded on a non-sequitur. Holding
after the fixes: the identity at $1.49e-08 against `ProductionCurrency.value` on 300 contracts;
averaging path values worth +$0.19M on the average contract, concentrated where the league minimum
binds; an eight-year cohort averaging $11.0M of within-contract sd around $5.5M with a 38% chance
of losing money. **228 of 1,217 contracts change sign**; the fixed-tier means do not. Still absent:
RFA walk-away and control years, goalies, dollar reconciliation. Report:
`50_REBUILD/docs/NPV_Simulation.md`; review: `50_REBUILD/docs/NPV_Simulation_Review_Codex.md`.
Suite 25/0/0. Nothing adopted.

**Review stage closed, component variant repaired (2026-09-16c).** The independent reviewer closed
the coverage-and-valuation review at `e14e873`. The first item on its next-work list is done:
`A2AgingParticipationImputed` raised `AttributeError` because the component model's overriding
training-pair builder was a copy of the base one with the three lines recording the fitted
horizons dropped. Those lines now live in one `_record_fitted_horizons` that both builders call,
and `BaseModel.fit` initialises `fitted_horizons_ = None` -- the convention `_guard_horizons`
already read -- so an unrecorded range fails visibly instead of downstream. New check 23 fits and
queries **all 34 registered variants**; suite is **23 passed, 0 skipped, 0 failed**. Remaining
work: the joint simulation, valuation integration and dollar reconciliation, then the back-test
with its grouping rule and protocol declared in advance.

**Valuation sensitivity on a declared fixed grouping (2026-09-16, revised after review).** Same
1,217 development contracts under five forecasts, from production's own projection and survival
(imported through the adapter and priced through THIS tree's currency, which is not the production
contract-NPV chain's output) to the adopted candidate. Groups cut once on the candidate's forecast
and applied to every column. **Every group keeps its sign in all five columns and the ordering is
identical in all five**; contract by contract the models correlate 0.974-0.988 and agree on sign
for 88-97%. The earlier report's "top tier flips sign" was an artifact of per-column tier
membership (51, 68, 18, 19, 18 contracts) and is withdrawn. **The magnitude is still unsettled**:
the top group runs -1.74 to -4.55 $M on 18 contracts with no uncertainty estimate. Participation,
tested properly by pinning the probability of playing to one while holding the imputed aging,
moves the top group to -1.910 or -1.592; signs and ordering survive, but "calibration is
immaterial" is withdrawn. Sample loss is at the **price fit**, not the forecast horizon (438 at
attachment, 241 at the price fit). Report: `50_REBUILD/docs/Valuation_Sensitivity.md`; review:
`50_REBUILD/docs/Valuation_Sensitivity_Review_Codex.md`. Nothing adopted.

**Subgroup miscalibration: measured, causes unresolved (2026-09-16, revised after fact check).**
Nominal 80% ranges hold 82-84% of outcomes overall, **61% for the 3+ tier five seasons out and 66%
for players 22 and under**; 18.5% of played star seasons five out exceed their own page's 95th
percentile against an intended 5%; participation probabilities are miscalibrated for those groups.
A common-unit accounting that closes puts the stars' bias mostly in the **rate** (-0.680 of -0.866
five out) and identifies **games played** as a substantial error source nothing had remarked on
(the largest single component of the young players' bias three seasons out). **The respective
roles of participation, games, rate and selection are unresolved**, and the diagnostic's earlier
causal reading was fact-checked and largely withdrawn -- nine claims, listed in the report's
section 5, including the "ceiling" framing that the rest rested on. The loop is closed
deliberately: repeated adjustments to one development sample cannot separate these causes. Report:
`50_REBUILD/docs/Coverage_Decomposition.md`; review:
`50_REBUILD/docs/Coverage_Decomposition_Review_Codex.md`. Nothing adopted.

**The cap path, 2026-09-15c.** The rebuild's ceiling table gains 2026-27 at $104.0M, confirmed,
with the 2025-01-31 announcement date enforced in both directions. 2027-28 stays out because the
figure in circulation is an estimate; production carries it as $113.5M and the discrepancy is in
the flags, inert under D11 until a 2027-28 page exists.

**Decisions taken inside the tree only.** Term-in for the production currency (Thomas,
2026-09-15). One shared price line for restricted and unrestricted free agents — D7's locked answer
survived a test on signing-dated forecasts. Neither is adopted into production.

**The two candidate anchors have not been separated.** The calibrated total and the component model
are within 1.1% at every horizon, tie at the valuation season, and are within 0.002 wins of each
other on the star tier. The criterion that would separate them is dollar error on a contract, which
needs the back-test.

## Work queue → WORK_QUEUE.md

Moved 2026-09-09 (v3.2). The phase-sequenced list of yet-to-do work now lives in **`00_STATE/WORK_QUEUE.md`**. Pillar-level detail stays in `01_Draft_Model_Sequence.md`, `02_Prospect_Model_Sequence.md`, `03_Player_Market_Model_Sequence.md`.

---

## Regression results (locked — build on these, do not re-derive)

- **SUPERSEDED 2026-07-05 — see Phase 1b decisions D6-D9 above.** The items below marked *(superseded)* came from a regression that, undocumented, pooled goalies into the skater sample. They are kept for audit trail, not for use.

- **THE 2026-07-05 RATE BELOW IS ITSELF SUPERSEDED, TWICE OVER — see the current rate at the bottom of this section.** It was first refit under D20 (COVID proration, alpha=0.01831864/beta=0.01924854, same n=2,349), then replaced entirely 2026-07-28 by the review Stage 3 rate (left-censored, position-interaction, no length term). Kept here for audit-trail continuity only.

- **NEW LOCKED skater rate (2026-07-05, SUPERSEDED — see above):** one pooled market (RFA+UFA skaters, no split — see D7), estimated on 2018-2025 contract starts (D8), no era regime (D9). **alpha = 0.0184516 (1.845% cap), beta = 0.0202139 (2.0214% cap per WAR) — ≈$1.93M per WAR at the 2025-26 ceiling. R-squared = 0.4638, n = 2,349.** Refit under D20 to alpha=0.01831864/beta=0.01924854 (COVID proration; same n and R² order of magnitude). **Both figures are now historical — see the current rate below.**
- **RFA vs UFA distinct *(superseded)*:** baseline **F=3.63, p=0.0266** — did NOT survive goalie removal. Skater-only: **F=0.12, p=0.887** — not statistically distinct. See D7.
- **Headline R-squared (WAR-only): 0.39-0.43** *(superseded, goalie-pooled)*. Skater-only headline is now **R-squared = 0.4638** (see NEW LOCKED rate above). Full-controls R-squared of 0.74 remains suspect for the same reason flagged previously — largely contract length acting as a quality proxy (length alone ~66% of cap-share variance; length-WAR r~0.49-0.51) — not re-tested on the skater-only sample yet.
- **Data correction:** `true_start_year = end_year - length + 1` (PuckPedia stores first season for completed contracts, last season for active long-term deals). Fixed ~433 active contracts; narrowed the RFA/UFA slope gap 18% -> 11% *(pre-goalie-removal finding; gap is now ~0% per D7)*.
- **Regimes *(superseded)*:** flat-cap era (2020-2022) previously read as the only structural break (Chow). On the skater-only, 2018+ sample this mostly does not hold: 2018-19 vs flat-cap p=0.75 (no break); only a marginal post-2023 cheapening survives (p=0.044), treated as noise (D9). The old finding was partly an artifact of the thin, selected 2015-2017 tail (see D8).
- **Form:** Ramsey RESET rejects linearity, but it traces to a **floor effect below WAR ~0.1-0.3**, not a WAR-squared term. *[notes-only, not re-tested on the new sample]*
- **RFA extensions** command lower cap-share — a certainty discount, not a growth premium. *[notes-only, not re-tested on the new sample]*
- **Goalies:** near-zero YoY WAR correlation **among established goalies at contract signing** (**r=0.079**, GP>=10 in both lookback seasons, n=220, contracts 2015-2026) vs 0.557 for skaters in the same contract-anchored comparison; goalie WAR slope ~half the skater slope (superseded — see re-derived rate below). *[notes-only]* Goalie baseline R-squared=0.456 vs skater 0.480 (a different spec from the 0.39-0.43 UFA/RFA split, and using the OLD 60/40 weighting — see re-derived rate below) — goalies are not dragging the fit; the issue is **predictability, not fit**.
- **Defence** contracts have the weakest fit (baseline R-squared=0.295). *[notes-only]*
- **RFA terminal value:** use the WAR-only coefficient (remaining RFA years are not expected contract length, so the length coefficient would mechanically inflate cost).
- **Goalie trailing-WAR weighting for the NPV projection (resolved 2026-06-30):** the r=0.079 figure above is contract-signing-anchored and answers a different question than "how should the model weight trailing seasons for any goaltender that shows up in a trade." Full-panel test (every consecutive goalie-season pair, 2007-08 to 2025-26): t-1 alone gives r=0.303 unfiltered (n=1200), r=0.209 at GP>=20 (n=776). Tested 12 weighting schemes across t-1/t-2/t-3; **50/30/20 (t-1/t-2/t-3) wins** (r=0.335 unfiltered n=783, r=0.257 at GP>=20 n=458), best under both sample restrictions, though all multi-season blends cluster within a few thousandths of each other so the exact split is not sharply identified. **Locked weighting: 50/30/20**, with a fallback cascade — 60/40 t-1/t-2 with two consecutive priors, t-1 alone (flagged low-confidence) with one, league-replacement level for rookies with no NHL history. Reconstructed the original r=0.079 methodology independently (n=220, r=0.093) — confirms this is not a bug; the gap is sample selection (contract-signing-anchored, established-only vs the full career panel), driven by goalie playing time being endogenous to perceived quality (weaker goalies get benched, stronger ones start more), which inflates the naive full-panel correlation.
- **Goalie shrinkage lambda (resolved 2026-06-30):** estimated via 5-fold player-split cross-validation (mirrors the skater aging-curve lock), blending the trailing-WAR projection with league-average goalie WAR (2.19). Result: lambda=0.55 unfiltered, **lambda=0.65 at GP>=20 (LOCKED, stable across 6 random seeds)**. **LABEL CORRECTION (2026-07-05, D19):** lambda here is the weight on the LEAGUE AVERAGE, not on trailing WAR — goalies KEEP 0.35 of trailing (shrink 0.65 toward the mean), which is HARDER shrinkage than skaters' kept-0.55, not "surprisingly close to" it. The original "close to the skater 0.55, explained by goalie WAR's ~2x spread" gloss inverted the comparison; the true a-priori-expected story is that goalies' weaker year-to-year signal earns heavier shrinkage. The locked NUMBER (0.65 toward the mean) is unchanged and the shipped `goalie_value_spine.csv` was always correct — only the narrative wording was wrong. Verified: spine `shrunk_projection` backs out kept=0.35 exactly; head-to-head on 645 goalie-seasons, kept-0.35 beats kept-0.65 (MAE 2.084 vs 2.131). Uses a flat league-average target, not age-conditioned (goalie birthdate coverage 64%).
- **Goalie dollar rate, re-derived 2026-06-30:** the old ~half-skater-slope/R-squared=0.456 figures used the flat 60/40 skater weighting, predating the goalie-specific finding above. Re-estimated using the SAME 50/30/20 cascade as input: n=350 (goaltender contracts 2015-2026), intercept=1.398% cap-share (replacement cost, ~$1.34M at 2025-26 cap), slope=1.097% cap-share per WAR (~$1.05M per WAR), **R-squared=0.526** (up from 0.456). Confirmed the gain is from the weighting scheme, not sample composition, by testing both schemes on the identical n=350 sample (old 60/40: R-squared=0.488; new: 0.526). **Unaffected by the 2026-07-28 skater rate rebuild — goalies keep their own rate throughout.**

- **CURRENT LOCKED SKATER RATE (2026-07-28, review Stage 3 — supersedes both entries above):** left-censored (Tobit) maximum-likelihood fit, same n=2,349 sample, no contract-length term (Stage 2 found none belongs — see the Player Model Review Stages 2-5 block in Resolved Decisions). **Intercept alpha=0.0132478230 (1.325% cap, $1.265M at the 2025-26 ceiling) shared by both positions. Slope beta=0.0212322891 (2.123% cap/win, $2.028M/win) for forwards; defencemen carry an additional beta_d_add=0.0028702824 (0.287% cap/win), for a combined 2.410% cap/win ($2.302M/win).** Residual scale sigma=0.02276380 (Tobit reports this in place of an OLS R²). The straight-line, censored, position-interaction specification beat a nonlinear (bent) curve on out-of-sample prediction despite the bent curve fitting better in-sample — bent curve rejected. **This is the rate now in force for every skater valuation, and the one the draft-pick curve was rebuilt against (see D22-D27 above).** Locally re-run and confirmed 2026-09-09 — the verification gap this line used to flag is closed; see the Resolved Decisions verification-gap entry.

---
## Player pillar — goaltender wiring CLOSED for observed seasons (P2, 2026-06-30)

Full chain wired: trailing weight (50/30/20 cascade) → shrinkage (lambda=0.65) → dollar conversion (rate above) → Value_t, joined to existing Cost_t (`cs_cap_hit`/`pp_cap_hit`) → Surplus_t. Output: `goalie_value_spine.csv`, 1,730 of 1,752 goalie contract-seasons valued (2015-2025 observed range). 22 pre-2015 rows excluded (outside the regression sample window); 71 rows use an extrapolated cap ceiling beyond 2027-28 (flat 3%/yr placeholder).

**Bug caught and fixed mid-build:** a naive exact-name join initially mislabeled 54% of rows as "rookie." Verified root cause: 748 genuinely have no NHL WAR record (true rookies + never-played-meaningfully depth goalies — correct fallback to league average), and 181 are FUTURE contract years (2026-2032) beyond any actual WAR data — now separately flagged as `future_season_static_placeholder`, not conflated with rookies. Name normalization only recovered 2 additional matches (180→182); spot-checked 12 known starters (Shesterkin, Hellebuyck, Vasilevskiy, etc.), all matched cleanly.

**Known limitation, not fixed:** the 181 future-season rows use a static league-average placeholder, not a real forward projection — no aging-curve-based decay model exists for goalies (or skaters — same project-wide gap, see Phase 1). Low priority since the back-test window (2018-present) sits entirely within observed WAR data.

---
## Power analysis (Phase 2, first run 2026-06-30)

946 trade groups (2018-2026, multi-team collapsed via `linked_trade_id`). 69.1% involve a draft pick (unpriceable until Phase 3). Cleanest current category (player-only, no pick, no prospect-proxy) = **205 trades (21.7%)**. Of those: only **14 all-goalie** (fully priceable today), **154 all-skater** (blocked on Phase 1), 153 need Phase 4a (mid-season allocation), 53 carry an NTC/NMC clause-holder flag (upper bound, not a confirmed forced trade). Era split (flat-cap 91 / post-flat 88 / pre-flat 26) confirms the regime indicator is load-bearing. Fixed a boolean-comparison bug mid-run that had silently zeroed out the monopsony count (`== 'True'` string compare against actual Python bools). Output: `power_analysis_trade_groups.csv`.

**Key finding:** the real bottleneck is Phase 1 (skater NPV engine + discount rate), not the back-test items the old queue prioritized — triggered the full re-sequencing above.

**Framing caveat, raised directly by Thomas:** running this against an almost-entirely-unbuilt model meant near-total blockage was the expected floor, not a genuine discovery — should have stated that expectation before running, not after. The category-size breakdown and the bottleneck-identification are the real value; the raw pass/fail count itself wasn't news. **Must re-run after Phase 3 closes.**

---
## Game-level model — Phase 4a-i CLOSED (2026-07-03)

The non-Bacon, goal-denominated per-skater-per-game metric is built and validated end-to-end on 11,870 games (2017-18 -> 2025-26). Four-script chain (see Scripts inventory). Purposes: (a) mid-season trade allocation via the per-game `team` column; (b) the designated non-Bacon outcome yardstick for the circularity fix. **Zero Bacon inputs anywhere in the chain** — weights come from a fixed accounting identity (equal split among skaters actually on ice) plus league-estimated factors, never fitted to Bacon.

**Validation (both machines, matching to 3+ decimals):** accounting identity exact (+0.000000); orphan tripwire 0; **season-level regression: metric explains 58.3% of team-season goal differential (R²=0.583, slope 1.085), fitted to nothing**; game-level R²=0.034 — honestly benchmarked against MoneyPuck's public model (R²≈0.07 per game with richer features; single games are mostly luck for every model); goals-per-win = 5.90; penalty value v = 0.2097; eyeball test passes (2023-24 leaders: McDavid, MacKinnon, Tkachuk...).

**Documented limitations:** equal split cannot separate a player from his linemates (teammate confound — why the metric is scoped to allocation + validation, not standalone player valuation); xG top-decile overpredicts (~21.8% vs 17.0%, partly era drift; log-distance and slot-indicator fixes tested and rejected on evidence); 2,629 bench/team penalties credited to no individual (correct per feed).

**NHL feed corruption found and neutralized (exactly 3 games league-wide):** 2025020565 (another game's shifts misfiled under its id), 2021020513 (every shift triplicated, one copy with corrupted team label), 2024030116 (shift-chart player absent from the official box score). Fix: the roster-truth rule (Script 1 v1.3) + scraper v2.4's foreign-team filter. Also: the 2019-20 COVID round-robin contains the only two playoff-type shootout games in nine seasons (2019030002, 2019030016) — shootout detection now keys on the game's recorded final period, not game type.

**Provider-discipline note:** MoneyPuck's public shot file was downloaded once, solely to benchmark validation *expectations* (what game-level R² a richer public model achieves). It is not an input to any model component and does not touch the single-provider rule.

**GV-adj + architecture decision (2026-07-04).** A WAR-like adjusted version — GV-adj — was built (RAPM teammate/competition separation, shrunken finishing talent, deployment controls). A pre-registered battery testing GV as a full replacement for Bacon skater WAR was run and closed: Bacon is retained for skater value; the defensive-value gap is structural, not a tuning problem (see Resolved Decisions). GV now has three scoped roles — mid-season allocation (GV-raw), and the paired Phase 4b circularity validators (GV-adj + GV-raw). Backward scraping of the game-log store to 2006-07 was confirmed available via live URL tests (not yet run) — relevant to the left-truncation open question.

**Phase 4b primary validator — RUN 2026-07-14.** Tier 1 player-level: `trailing_war(t)` (the exact ex-ante quantity priced into Value_t) vs same-season GV-adj in win units. Headline: r=0.576 / Spearman 0.460 / OLS R²=0.331 on 6,027 player-seasons; per-season r=0.55–0.61 across all nine seasons (no season carries the result, no era break); t+1 horizon r=0.538. Forward/defence split mirrors the known GV defensive gap (F 0.648 vs D 0.302) — same wall from the replacement battery, seen from the outcome side. Framing: descriptive convergent validity, no pass/fail bar (none was pre-registered; retrofitting one post-hoc was explicitly rejected). Run mechanics worth preserving: the join is spine `nhl_id` ↔ GV `player_id` (the GV tables carry NHL ids, NOT PuckPedia ids — a zero-match tripwire now guards this); 47 duplicate player-seasons in the skater spine turned out to be retention-split contract legs (mid-season trade + salary retention, identical projection across legs) — collapsed with a projection-agreement guard, and independently a small structural confirmation of the retention mechanism. **Canonical game-log DB declared: the `Desktop\test` copy** (`C:\Users\thoma\OneDrive\Desktop\test\nhl_gamelogs.sqlite`) — the only copy holding `gv_adjusted` + `player_game_value_repl`; the old `new_scrape` path is superseded. **Robustness leg RUN 2026-07-14 — 4b closed in full.** GV-raw aggregated to player-seasons (regular season only, both the zero-sum `game_value` and replacement-rebased `gv_repl` columns): rebased r=0.609, zero-sum r=0.564 vs the GV-adj primary 0.576 — a tight three-validator band, stable in every season, gentle t+1 decay in all three. Two interpretive notes: (a) GV-raw matching/exceeding GV-adj is consistent with the earlier persistence finding (raw 0.809 vs adj 0.779) — the RAPM adjustment strips team-context signal that Bacon WAR also carries; a finding about metric content, not a reason to reopen the locked primary designation. (b) Rebased-D (0.442) is not cited as the defence headline — the rebase's known offensive-D inflation plus shared deployment correlation likely contributes; the honest defence range is 0.28-0.30 across the other two validators.

---
## Player-model review — STAGE 1 CLOSED (2026-07-27)

An external review of the player pillar (`player_model_review.md`) listed ten Stage 1 items:
corrections that bring the code into line with rules the project had already adopted. All ten are
now closed. Every fix was built, run locally by Thomas, and cross-checked against an independent
run before being accepted. Seven scripts changed.

**What each item was, and what it did**

| item | file(s) | outcome |
|---|---|---|
| 1.1 goalie out-year projections | `goalie_value_engine.py` v1.1 | 98 rows / 38 goalies now carry the goalie's own projection instead of the league average; 83 never-played rows retagged only. Net +$36.9M on the goalie panel. Parity gate still passes. |
| 1.2 retirement-risk lookup | `contract_npv.py` v1.2 | Both lookup axes (age AND quality) were read one season too late. Corrected to k−1. 922 contracts move, +$137.1M. |
| 1.3 projection multiplier floor | `skater_forward_projection.py` v1.2 | `RATIO_FLOOR = 0.0` added. 67 rows across 39 contracts had wanted a NEGATIVE multiplier (worst −2.86). 41 contracts move, all upward, +$8.4M. |
| 1.4 thin cells in the risk table | `exit_hazard.py` v1.2 | Cell means replaced by a fitted additive model (quality + age, main effects). Two skater cells and FOUR goalie cells had read exactly 0.0% — i.e. asserted certainty. 1,450 contracts move, +$16.6M. |
| 1.5 traded player's lost half-season | `skater_value_engine.py`, `skater_forward_projection.py` | Team-halves are now summed, not discarded. One live case (Nick Paul 2022), +$2.30M — he had been routed onto the wrong projection branch entirely. |
| 1.6 name cleaning in the aging curve | `aging_curve.py`, `skater_forward_projection.py` | Careers keyed on the cleaned name; five split careers reunited; the two Elias Petterssons kept apart by explicit rule. |
| 1.7 non-consecutive season windows | `aging_curve.py` | 338 windows had paired non-consecutive seasons (worst: ages 21 and 30 treated as consecutive). Dropped from the comparables pool; level falls back to the single season; trend divides by the real age gap. |
| 1.8 identifier / name join guard | `age_join.py` | `join_on_id_and_name()` added, with a self-test that fires on a known conflict every run. No behavioural change; forward-looking guard. |
| 1.9 goalie column type | `goalie_value_engine.py` | `trailing_war` is numeric again (748 rows had carried text, re-typing the column). Was a regression against the locked v1 file, not the original design. |
| 1.10 qualifying-offer salary substitute | `rfa_terminal_value.py` | **RECLASSIFIED: limitation, not correction.** See below. |

**1.6 + 1.7 combined effect on the curve and the valuations**
Careers 1,479 → 1,478; comparables pool 7,869 → 7,531; bandwidth 2.555 → 2.526. Downstream:
1,011 contracts move (34.8%), +$30.5M in total, but the median move is $5k and 90% are under
$167k; largest single move $1.33M. Nine contracts switch projection track, eight of them off the
flat fallback and onto the curve because their careers are now whole. **λ = 0.55 was re-tested,
not assumed** — sampled-career error 1.0226 / 1.0110 / **1.0068** / 1.0095 / 1.0192 at λ = 0.35 /
0.45 / 0.55 / 0.65 / 0.75. 0.55 still wins; the locked value stands and is now re-earned on
corrected inputs.

**1.10 is a limitation, not a fix.** The review proposed falling back to the contract's highest
observed salary when the final year's salary is missing. Of the 1,689 affected contracts, only
**11** have a salary recorded on any season — the salary feed covers a whole contract or none of
it — and the PuckPedia export holds a contract total, not a per-season breakdown, so there is no
alternative source in the current data. Implemented: max-salary fallback where it exists, explicit
tagging (`qo_salary_source`) everywhere else, a guard against substituting while a real salary is
on file, and reporting in the run log (**1,083 real salaries vs 356 substitutes, 25%**; priced
population 411 vs 133). Downstream effect: zero contracts. **Paper statement:** roughly a quarter
of qualifying offers rest on a figure that switches off the CBA's 120%-of-cap-hit ceiling; the
bias runs one way (offer understated → control-year cost understated → surplus overstated); about
2.8% of contracts would have had the ceiling bind, judged from the contracts where the real salary
IS visible. Closing it needs per-season salary coverage extended — the cap-space.com feed is the
natural place to look.

**The review's own reliability — record this before Stages 2-5.** It identified a real problem in
all ten items, but was wrong on mechanism or magnitude in five: 1.1 (row count and population
split), 1.2 (35.8% figure requires five transitions, not the four its worked example implies;
7.5% on that path), 1.3 (attributed the cause to small curve bases — only 18 of 75 rows;
its proposed threshold change would have left 57 pathological rows and re-routed 197 healthy
ones), 1.8 (23 IDs / 217 rows / 47 players, not 33 / 322 / 69), and 1.10 (proposed remedy not
implementable). Treat every Stage 2-5 claim as a hypothesis to verify, not a finding to act on.

**Direction-of-effect pattern (belongs in the robustness section).** Items 1.1, 1.2, 1.3, and 1.5
all moved values UPWARD, and 1.6/1.7 net upward as well. Each is independently defensible, but the
common direction is what a skeptical reader will notice, so it should be presented as a set with
the total effect stated, not as six unrelated corrections.

**No accuracy gain claimed.** The projection's own backcast barely moved (+1.5% over hold-flat at
k=1 before and after; +8.3% vs +8.4% at k=3). Stage 1 bought defensibility, not predictive
performance. One small honest note: for negative anchors at k=1 the curve now trails hold-flat by
1.4% where it previously led by 0.2% (n=233); it still wins clearly at k=2 and k=3.

---
## Sessions log → 00_STATE/sessions/

Moved 2026-09-09 (v3.2). Each working session writes a dated file to **`00_STATE/sessions/`** (`YYYY-MM-DD[letter].md`) summarising that session beat-by-beat: what was discussed, what was decided or done, which artifacts were touched, and — mandatory — any thread left without a follow-up. The two pre-split write-ups (2026-08-28 supervisor meeting, 2026-09-08 repository migration) were migrated there verbatim. The curated arc lives in the DECISIONS.md change log; the session files are the granular substrate you grep.

---

## Standing flags & open questions → STANDING_FLAGS.md

Moved 2026-09-09 (v3.2). Karl's identification axes, the triaged open questions, and the original-conflicts resolution record now live in **`00_STATE/STANDING_FLAGS.md`**.

---

## File management protocol (adopted 2026-07-30)

### Amendment (2026-09-08): git is now the code channel

The tree below is unchanged and still governs. What changed is how code and state move between
machines. `20_CODE`, `00_STATE`, `40_DOCS`, and the four small vendor CSVs travel through the
GitHub repo. `10_SOURCE` heavy data and all of `30_OUTPUT` do not, because GitHub caps files at
100 MB and the game-log database alone is 2.3 GB. **Dropbox is therefore no longer the working
channel for code, but remains the only channel for data.** Local stays authoritative throughout.
The practical trap: generate a spine on one machine and the other goes stale silently, because git
will not tell you. Either re-run the chain or sync `30_OUTPUT` through Dropbox, and treat the most
recent run as canonical.

### Amendment (2026-09-11): the sync is scripted, and it refuses to run on a broken repo

Two machines now sync through one script, `sync.ps1` at the repo root, launched by
`Sync-Desktop.cmd` or `Sync-Laptop.cmd`. The script commits every local change, pulls whatever is
on GitHub and not local, and pushes, in that order. It takes the repo location from its own folder
rather than a hardcoded user path, because the two Windows accounts differ (`Thomas` on the
desktop, `thoma` on the laptop); the two `.cmd` launchers carry the machine-specific path so they
can be pinned outside the folder, and fall back to their own directory if that path is wrong.

Two design points are load-bearing, both of them consequences of a real stall on 2026-09-11 that
left the desktop in detached HEAD with an interactive rebase half-applied. **The pull is
`--no-rebase`, deliberately.** Rebase rewrites local commits onto the remote's and strands you off
the branch when it stops partway, which is what happened; a merge pull leaves you on the branch
whatever else goes wrong, and a merge commit costs nothing on a single-author repo. **The script
refuses to run at all** when `rebase-merge`, `rebase-apply`, `MERGE_HEAD`, or `CHERRY_PICK_HEAD`
exists, or when HEAD is detached: in those states an `add`/`commit`/`pull` sequence compounds the
problem rather than fixing it, so it prints the resolving commands and exits without touching
anything.

The sync moves tracked files only. `30_OUTPUT` is gitignored and does not travel, so the stale-spine
trap above is unchanged: a spine generated on one machine still goes silently stale on the other.

### Where things live, and which copy is authoritative

The local working folder on Thomas's machine is the source of truth. OneDrive backs it up continuously at no effort. Dropbox is the working channel, which is the only cloud surface Claude can read and write. Google Drive is retired. When Dropbox and local disagree, local wins and Dropbox is refreshed from it; a stale Dropbox never means work was lost.

### The tree

- `00_STATE/`, holding the four state files (`PROJECT_STATE.md`, `WORK_QUEUE.md`, `DECISIONS.md`, `STANDING_FLAGS.md`), the `sessions/` per-session log, the four sequence documents, and `MANIFEST.csv`.
- `10_SOURCE/`, vendor and scraped source data. Our code reads it and never writes it.
- `20_CODE/`, flat. Every script, current version only.
- `30_OUTPUT/`, flat. Every spine, panel, curve, diagnostic, and run log.
- `40_DOCS/`, reports, reviews, briefs, and assets.
- `90_ARCHIVE/YYYY-MM-DD/`, superseded material under its original name.

`20_CODE` and `30_OUTPUT` are flat deliberately. The previous per-pillar folders sat empty for a month, then filled with duplicates and Dropbox conflict copies while the real work happened in one flat directory. A structure that contradicts how the code actually runs will keep losing.

### Naming

Filenames in Dropbox are byte-identical to filenames locally. There is no version suffix on a live file; the file in `20_CODE` is current, and superseded copies move to `90_ARCHIVE/YYYY-MM-DD/` under their original name, with the date carried by the folder.

A `<pillar>_<name>` convention was considered and **rejected for code and outputs**. Six scripts are imported as modules by others, so renaming them is a code change requiring an import rewrite and a local re-run; output filenames are equally exposed because scripts read and write them by hardcoded name. More importantly, a file named one thing locally and another in Dropbox breaks the manifest check and licenses the two surfaces to disagree, which is the failure this system exists to prevent. Browsability is recovered through the manifest's `pillar` column instead.

### MANIFEST.csv

One row per file, in `00_STATE/`. Columns: `path`, `filename`, `pillar`, `class`, `session_id`, `dbx_content_hash`, `size_bytes`, `handoff_date`, `verified_locally`, `channel`, `note`. **Reconciled 2026-09-09 (v3.2) into a complete inventory** — 77 rows: every git-tracked file under `20_CODE` / `00_STATE` / `10_SOURCE` / `40_DOCS`, plus the load-bearing `30_OUTPUT` working set and the game-log DB. Before then it listed only the 2026-07-30 handoff set (~13 scripts + spines) and was never complete.

`channel` (new 2026-09-09) says how the file moves and therefore how it is audited:
- **`git`** — the `dbx_content_hash` column holds the **git blob SHA** (from `git ls-files -s`), not a Dropbox hash. The audit for these files is `git status` (clean tree = every row verified) and `git log`. `verified_locally` is `yes` whenever the working tree is clean.
- **`dropbox`** — `30_OUTPUT` outputs and the 2.3 GB `nhl_gamelogs.sqlite`, which do not travel through git. `dbx_content_hash` is `LOCAL_RUN` (they regenerate; the most recent local run is canonical) or an actual Dropbox content hash after a handoff. These are the only rows the Dropbox-hash audit still applies to.

`class` governs how a file is compared when it IS hash-audited. `hashable` covers csv, md, txt, py, and xlsx. `rendition` covers pdf and docx, which the Claude project stores as page-image/markdown extractions, not as files — comparing a rendition to its source produces a guaranteed false mismatch (this caused two spurious conflicts in the 2026-07-30 audit). `binary` covers png and sqlite.

`session_id` is `YYYY-MM-DD` plus a letter where a date carries more than one session.

### The audit, on the trigger phrase "audit files"

Scope is now `channel = dropbox` rows only — `channel = git` files are audited by `git status` / `git log`, not by hash comparison against a listing.

Direction one asks whether a handoff landed: compare the Dropbox content hash, which any listing returns at no cost, against the manifest row. Match means fine, differ means Thomas edited or reran it and Claude asks which, absent means the handoff never arrived.

Direction two asks whether the Claude project is serving stale files: the same comparison against the project copies, restricted to `class = hashable`. (Largely moot since 2026-07-30 — the Claude project no longer holds scripts or outputs.)

Both report exceptions only. Two operational notes from the migration. Dropbox move jobs can report `internal_error` on every entry while having actually succeeded, so completion is confirmed by listing the destination rather than by trusting the job result. And file size alone is not an integrity check: the pre-rebuild and post-rebuild `draft_yield_curve.csv` are both exactly 845 bytes with different contents.

### What the Claude project holds

Only files that change on a decision cadence: `PROJECT_STATE.md`, the four sequence documents, the two review documents, the Research Brief, the WAR/AAV regression report, and the frozen vendor sources. No scripts, no spines, no panels, no curves, no run logs. Outputs change every run while project files change only when Thomas clicks, so any output kept there drifts by construction. Scripts and outputs are attached per message when being worked on, or read from Dropbox.

**Supervisor review applied (2026-09-10d):** Doc 2 and Doc 5 in `40_DOCS/Supervisor_Drafts/` incorporate the agreed factual and prose corrections. Doc 5 now distinguishes the completed raw within-player era comparison from the unimplemented fitted-profile leg described in the source docstring. Doc 2 retains full explanations and adds the yardstick test. ZIP/XML and core WML checks pass; visual pagination remains unverified. See `sessions/2026-09-10d.md`.

- **2026-09-10e Doc 2 formatting:** User-edited Downloads copy incorporated into Supervisor_Drafts with consistent fonts, heading hierarchy, and spacing. Text preserved exactly; core checks pass; visual pagination remains unverified. See `sessions/2026-09-10e.md`.

- **2026-09-10f:** Supervisor Docs 3-5 reviewed against code and run logs. Clarified tests and calculations; restored the forward term-test result and separate draft intervals, and documented terminal qualification survival starting a new chain. Production unchanged. Report: `40_DOCS/Docs_3_4_5_Review_Notes.md`.

- **2026-09-11b formatting:** Applied Data, Production, and Aging's formatting to the four other user-named explainers in place. Text preserved exactly; XML checks pass. Visual pagination remains unverified because the packaged renderer lacks LibreOffice. See sessions/2026-09-11b.md.

**2026-09-11c document update:** Current user-supplied pricing draft is 40_DOCS/Doc_3_Player_Pillar_II_2.docx, edited for flow and consistent formatting. Numerical results and model settings unchanged. Visual pagination unverified because the bundled renderer lacks LibreOffice.

**2026-09-11d document update:** 40_DOCS/Doc_4_Drafting_Prospects_Unbuilt.docx rewritten for comprehension and matched to the preceding explainer's formatting. Built/proposed distinctions and numerical findings retained. Structural checks pass; visual pagination remains unverified.

**SUPERSEDED by the entry appended at the end of this file on 2026-09-15 after the repair verification: the improvement figures below are measured against a faulty adapter and are corrected there.** **2026-09-15b rebuild status, and what may be quoted from it.** The experimental player rebuild
in `50_REBUILD/` was independently reviewed, answered, and has had its first repair pass. What
is established today: the experimental forecast beats a flat-carry benchmark reproducibly. What
is not established: that it beats the live chain, that the chain is clean of look-ahead through
the market stage, or that any of its dollar figures can be used. **Each dollar figure in the
candidate reports is withdrawn** until the participation event, the market dating and the cap
path with discounting are repaired and the chain is refit. The comparator those reports call
the production chain is a flat trailing anchor with no aging path and no survival weighting, so
each improvement quoted against production is an improvement against a simpler rule; the
attribution appears in report prose, model labels and log output, and is corrected in none of
them yet. Two defects are repaired and asserted: the shortened-season units, and four silent
defaults that returned fabricated numbers rather than refusing. The market holdout is spent
(see STANDING_FLAGS and `50_REBUILD/docs/Holdout_Inventory.md`); the forecast holdout is
believed intact and is now recorded rather than reconstructed. Nothing in production changed
and no locked decision was reopened. Repair sequence and the two decisions owed are in
WORK_QUEUE.

**2026-09-15b rebuild status, CORRECTED after the repair verification.** The comparator used in
the earlier entry was a production adapter that reimplemented two of production's rules and got
both wrong. Corrected, on rows production can price: **the rebuilt chain beats the live chain by
14.4% in the valuation season and by 8% to 9% from one season out.** The gain is an old-player
gain and should be described as one: 43.1% at 34 and over, 20.2% at 31 to 33, 11.0% at 27 to 30,
2.9% at 23 to 26, and a 0.4% loss at 22 and under. **The previously reported 28.6% improvement on
below-replacement players is withdrawn; correctly measured it is 2.6%.** The star residual is
inverted rather than repaired, at -0.57 wins against production's +0.67. Each dollar figure
remains withdrawn pending reconciliation against production's contract NPVs. Repair items 1 to 7
and all six verification findings are complete; the check suite is at 14 of 14. No production
file changed and no locked decision was reopened.
