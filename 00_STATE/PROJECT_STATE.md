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

- `40_DOCS/Doc_1_Circularity_and_Game_Value.docx` — edited copy of the supplied explainer, 2026-09-09. Prose and structure checked; visual pagination QA pending renderer availability. See `sessions/2026-09-09b.md`.
- **There is no paper manuscript.** The file labelled `NHL_..._Paper_v6.docx` is the model **overview / scoping document** — it states what the model will do and what the back-test looks for, not written-up findings. It is out of date and slated for replacement. **No paper is written until the model is built.**
- The `Model_Open_Questions_v3` doc has been **removed from the project** (canonical open questions live in `00_STATE/STANDING_FLAGS.md`).
- `NHL_Trade_Model_Build_Roadmap.docx` — **CORRECTION (2026-07-03): located.** It sat in the cloud root (created 2026-07-02); v1.5 wrongly recorded it as not locatable. Content is superseded by the re-sequenced Work Queue and by the four sequence documents. DELETED 2026-07-30 during the file-system migration; recoverable from Dropbox trash.

**Scripts built (reconciled against what is locatable)**
- `skater_value_engine.py` — **UPDATED 2026-07-27 (item 1.5: sums a traded player's team-halves instead of discarding one, before the games filter, with an 82-game guard against merging two same-named players). NEW 2026-07-05.** Phase 1b Layer 1: builds `skater_value_spine.csv` from trailing WAR + the new locked skater-only rate + the D10 league-minimum floor. Two-stage reproduction guard baked in (must pass before any output is trusted). Excludes the merged-name rows (Ryan Johnson, Nathan Smith); resolves the Sebastian Aho (D) / WAR.csv "Sebastian Aho Swe" alias explicitly. (In the project; local parity confirmed 2026-07-05.)
- `skater_forward_projection.py` — **v1.2, UPDATED 2026-07-27 (item 1.3: RATIO_FLOOR=0.0 plus a `ratio_floored` flag column; item 1.5: its OWN copy of the WAR loader fixed — this is the copy that prices contracts; item 1.6: curve lookup now goes through `career_key`). NEW 2026-07-05.** Phase 1b Layer 2: `SkaterProjector.project_contract(player_id, valuation_season)` projects each remaining contract season via the D3 decay path (aging curve as ratio path on the raw-WAR anchor), D12 v3 negative-anchor replacement-reversion, D11 ex-ante ceilings, D10 floor. Imports Layer 1 constants; requires `aging_curve.py` + `WAR_with_age.csv`. Boundary guard added for panel-edge ages (the locked aging engine IndexErrors past its max age — left untouched, wrapped instead).
- `rfa_terminal_value.py` — **UPDATED 2026-07-27 (item 1.10: max-salary fallback where available, `qo_salary_source` tag, guard against substituting while a real salary is on file, source split reported in the run log). NEW 2026-07-05.** Phase 1c: `TerminalValuer.terminal_value(...)`. UFA/"no QO" → 0; RFA → Layer 2 walk through control years vs iterated era-aware QOs (D13 truncation, D14(c) empirical qualify-gate calibration re-estimated each run). QO mechanics assert-self-test on import.
- `exit_hazard.py` — **v1.2, UPDATED 2026-07-27 (item 1.4: cells come from a fitted additive model, not raw cell means; `(bucket,"ALL")` marginals stay raw; `unknown`-age cells no longer emitted; four guards including a calibration check. NEW DEPENDENCY: statsmodels + scipy — this file used to run on numpy and pandas alone).** NEW 2026-07-05. Phase 1a (D18): estimates the exit hazard (P(no NHL season at t+1)) by quality×age from the panel. Exposes `build_transitions` / `build_hazard_table` as importable functions so `contract_npv.py` shares one code path (no drift). Skater table; goalie table built by the same functions inside the NPV engine.
- `contract_npv.py` — **v1.3, UPDATED 2026-07-27 (item 1.2: hazard indices read at k−1 on BOTH axes, with a `legacy_hazard_index` audit switch that re-measures the correction into the run log every run; item 1.4: goalie-table audit reported here since the goalie panel is built here). NEW 2026-07-05.** Phase 1d: `NPVEngine.npv(player_id, valuation_season)` stacks Layer 2 + terminal value + survival weights + 3% denominator into one discounted contract NPV, both positions. Contains the goalie mini-engine (`GoalieProjector`, flat projection, self-calibrating goalie rate recovered from the spine). Writes `contract_npv_spine.csv`. Has a diagnostic k=0 consistency check that prints the offending player/season before failing (added after a stale-spine mismatch was traced this way on Thomas's machine).
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

- **CURRENT LOCKED SKATER RATE (2026-07-28, review Stage 3 — supersedes both entries above):** left-censored (Tobit) maximum-likelihood fit, same n=2,349 sample, no contract-length term (Stage 2 found none belongs — see the Player Model Review Stages 2-5 block in Resolved Decisions). **Intercept alpha=0.0132478230 (1.325% cap, $1.265M at the 2025-26 ceiling) shared by both positions. Slope beta=0.0212322891 (2.123% cap/win, $2.028M/win) for forwards; defencemen carry an additional beta_d_add=0.0028702824 (0.287% cap/win), for a combined 2.410% cap/win ($2.302M/win).** Residual scale sigma=0.02276380 (Tobit reports this in place of an OLS R²). The straight-line, censored, position-interaction specification beat a nonlinear (bent) curve on out-of-sample prediction despite the bent curve fitting better in-sample — bent curve rejected. **This is the rate now in force for every skater valuation, and the one the draft-pick curve was rebuilt against (see D22-D27 above).** Not yet locally re-run/confirmed by Thomas — see the open verification gap flagged in Resolved Decisions.

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
