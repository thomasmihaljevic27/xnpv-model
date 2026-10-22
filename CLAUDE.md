# CLAUDE.md — xNPV Model

## What this is

A Master's economics thesis building a net-present-value framework that prices three NHL
trade-asset classes (rostered players, draft picks, non-roster prospects) on one common scale,
projected surplus value in dollars, then back-tests historical trades against realized outcomes
to find categories of systematic mispricing. The cross-asset integration onto a single currency
is the contribution. Audience is an econometrics supervisor who weighs identification issues
(circularity, look-ahead bias, selection bias) above all other concerns.

## Current state, and how stale it is

State lives in four version-controlled files in `00_STATE/`, plus a per-session log:

- **`PROJECT_STATE.md`** — the anchor: objective, model spec, current build state, the
  data/scripts inventory, locked regression results, per-pillar status, file-management protocol.
- **`WORK_QUEUE.md`** — the phase-sequenced list of yet-to-do work.
- **`DECISIONS.md`** — the locked decision record (D1–D27 and the review-stage items) and the
  running change log for all four state files.
- **`STANDING_FLAGS.md`** — Karl's identification axes, the triaged open questions, the
  original-conflicts resolution record.
- **`MODEL_DIRECTIVES.md`** (new 2026-10-04) — Thomas's explicit model directives, the investigate list,
  the open decisions, and the plan of record (the order of work). The model must match it; read it
  before changing any model code, and change nothing in it without Thomas's say.
- **`sessions/YYYY-MM-DD[letter].md`** — one file per working session, beat-by-beat: what was
  discussed, decided, done, which artifacts were touched, and any thread left without a
  follow-up. `git log 00_STATE/ 20_CODE/` is the mechanical second copy of that history.

All four share `PROJECT_STATE.md`'s Generated / Refresh-due dates and its staleness trigger.
As of the 2026-10-14 refresh (PROJECT_STATE v3.4, "Current state" and "Model as built"): skater and goalie
contracts are priced on xNPV 1 with the five player directives built; the draft pick curve and the traded-pick
values are built, with the arbitration cost for control seasons adopted on both sides (2026-10-13); the
prospect model is built (2026-10-14: slot, production adjusted to NHL terms and age, undrafted players on NHL
contracts with the slot at zero, `prospect_values.py`), each addition Thomas's; the back-test has not started.
Built 2026-10-15: drafted players who died before reaching the NHL are left out of every fit (`deceased_draftees.py`), and
the prospect model has no age-removed version (age centred at 18; `prospect_values.py` v1.7).
Built 2026-10-14: every age the model reads follows the CBA (September 15; drafted players' signing ages in the
year they signed), the arbitration price is consistent with the forecast, and the 60/40 checks are retired.
Built 2026-10-20: every script dates a contract by one rule (`contract_source.contract_terms`: a bought-out deal at its
own first season, its full signed term counted until the buyout is known); the model charges PuckPedia's cap hit
(`model_cap_hit`); the price line is re-locked; the back-test's three rules are in (the 2025-26 cap, retained salary
charged to the retaining club, the season left on in-season trades).
Run 2026-10-20: the back-test (`trade_sides.py`, `backtest.py`; protocol `40_DOCS/Backtest_Protocol.md`, committed
before the run). Its Game Value check was run the same day (9 results hold, 1 not confirmed). LTIR relief (2026-10-20): `ltir.py` reads
Spotrac's injured-reserve pages saved by Thomas in `10_SOURCE/ltir/` ("Label + CBA test"); the trade valuations and the
back-test import it.

**Craft is retired as a canonical surface (2026-09-09).** Do not read it, reconcile against it,
or sync to it. "How it works" explainers live in `40_DOCS/`. Precedence when sources conflict:
the four `00_STATE/` files + the `sessions/` log > the scoping document > the Research Brief.
There is no paper manuscript. Writing begins once the model is built.

**Session-close ritual.** When a session has changed state or run work: write/append the
`sessions/` file for today, update whichever of the four state files each change touches, append
a `DECISIONS.md` change-log entry, and commit + push it all in one commit. The session is not
done until that commit exists.

## Stack

Python 3, SQLite. pandas, numpy, statsmodels, scipy, requests, TopDownHockey_Scraper.
No virtualenv convention is established yet. Stata or R on request only.

## Folder map

    00_STATE/     PROJECT_STATE.md + WORK_QUEUE.md + DECISIONS.md + STANDING_FLAGS.md,
                  sessions/ (per-session log), two sequence docs, 03 and 04 (the draft and prospect plans
                  were archived 2026-10-09), MANIFEST.csv,
                  inspection_ledger.csv (which seasons each evaluation scored; committed, union-merged)
    10_SOURCE/    vendor and scraped source data. Code reads it, never writes it
    20_CODE/      flat. The live pipeline and its tools, current version only
    25_TESTS/     flat. Finished one-off tests and diagnostics; each puts 20_CODE/ on its path
    30_OUTPUT/    flat. Every spine, panel, curve, diagnostic, run log. Gitignored
    40_DOCS/      reports, reviews, briefs; model_evidence/ holds the player-model test reports
                  and independent reviews behind D33 (moved from 50_REBUILD/docs/ 2026-10-02)
    90_ARCHIVE/   YYYY-MM-DD/ superseded material under original names. Gitignored
    (50_REBUILD/  the player-model rebuild, retired 2026-10-02: code in git at 7f91f0e and in
                  90_ARCHIVE/2026-10-02/ on the laptop; the folder name is gitignored)

A test or diagnostic goes in `25_TESTS/` once its result is recorded (moved there 2026-09-30); a new
one may start in `25_TESTS/` directly. `40_DOCS/model_evidence/reviews/` holds the independent reviews'
reports; their scripts went to the archive with `50_REBUILD/`. `20_CODE` and `30_OUTPUT` are flat deliberately. Per-pillar subfolders were tried, sat empty
for a month, then filled with duplicates and sync-conflict copies while real work happened in
one flat directory.

## How to run it

Paths come from `.env` (copy `.env.example`). Run from the repo root.

Player pillar, in order:

    python 20_CODE/war_name_crosswalk.py         # each contracted player's WAR spelling (before age_join; 2026-10-14)
    python 20_CODE/elc_signing_dates.py          # entry-level signing years (CBA arbitration and entry-level ages)
    python 20_CODE/skater_forward_projection.py  # Layer 2, forward projection
    python 20_CODE/rfa_terminal_value.py         # terminal value at expiry
    python 20_CODE/exit_hazard.py                # exit-risk report; goalies' survival weights
    python 20_CODE/contract_npv.py               # summation, writes contract_npv_spine.csv
    python 20_CODE/contract_npv_panel.py         # panel build

Skater contracts are priced on xNPV 1 (D33), the only skater model since 2026-10-02. The forecast is
`20_CODE/skater_forecast.py` (with `forecast_config.py`, `player_season_table.py`, `information_set.py`,
`contract_source.py`, `participation_model.py`, `forecast_harness.py`); `contract_npv.py` fits it in-process,
one fit per valuation page, and writes `30_OUTPUT/xnpv1_forecasts.csv`. It needs the contract export as CSV
in SOURCE_DIR and an age table at 99%+ birthdates. Survival is xNPV 1's chance of playing; the skater exit
hazard no longer prices anything (goalies still use theirs).

xNPV 0, the old anchor-and-ratio projection, was archived on 2026-10-02 after the switch comparison was
accepted (git 7f91f0e is the last commit that has it). `XNPV_SKATER_MODEL` set to anything but `xNPV 1` now
stops the run. Finished tests in `25_TESTS/` that build `NPVEngine` on xNPV 0, or that import from
`50_REBUILD/`, reproduce their recorded results only from a checkout of 7f91f0e.

xNPV 1's seasons and control years are priced by `skater_forward_projection.price_constants()`. It returns
`XNPV1_RATE` (the term-in line, re-locked 2026-10-20 on contracts dated one way; `XNPV1_RATE_TERM_FREE` beside it as the sensitivity); set to
None, it falls back to Stage 3, and every row's `price_line` column says which line priced it ("provisional"
means Stage 3). Both come from `python 20_CODE/xnpv1_price_line.py` v2.3: the Stage 3 specification re-fitted
on xNPV 1's forecast dated at each contract's signing (directive 5), with a linear term for contract length
(directive 4). Each re-run must give the lock back (its reproduction guard). The pick curve (`pick_curve.py`)
prices delivered wins on `XNPV1_RATE` at one year of term (open decision 3). The D14(c) qualify rates are
bucketed on xNPV 1's forecast. (Corrected 2026-10-14: this said the 2026-10-02 lock and that the draft curve
stays on Stage 3; both were stale.)

Player dashboard: double-click `Update-Dashboard.cmd` (or `python 20_CODE/dashboard_refresh.py`) to rebuild;
`Open-Dashboard.cmd` only reopens the last build and shows when it was made.
It re-runs everything the dashboard reads, from `join_clauses_to_spine.py` and `age_join.py`
through the chain above plus `goalie_value_engine.py`, then builds and opens
`30_OUTPUT/player_dashboard.html` (about 7 minutes). The step list lives in `dashboard_refresh.py`'s
`CHAIN`; a new script the dashboard depends on must be added there, or the launcher will not run it.

Game-level chain, in order:

    python 20_CODE/nhl_gamelog_scraper.py
    python 20_CODE/on_ice_reconstruction.py
    python 20_CODE/xg_model.py
    python 20_CODE/score_state.py
    python 20_CODE/metric_assembly.py

Draft pillar (restarted 2026-10-09 with the supervisor; the specification is `00_STATE/MODEL_DIRECTIVES.md`
directive 6). The old models (`draft_yield_curve.py`, `slot_curve.py`, `future_pick_premium.py`) and plans are in
`90_ARCHIVE/2026-10-09/`, with the old curve's output as a reference. In order:

    python 20_CODE/draft_pick_linkage.py     # picks linked to careers (also the kept check)
    python 20_CODE/elc_signing_dates.py      # entry-level signing years (the CBA ages)
    python 20_CODE/pick_curve.py             # each drafted player priced; the star value (its sensitivity; the qualifying-offer chain beside)
    python 20_CODE/traded_pick_values.py     # every traded pick valued at its trade
    python 20_CODE/prospect_values.py        # prospects: every traded prospect valued (slot, production, age)
    python 20_CODE/traded_player_values.py   # traded players valued at their trade's page (2018-19 on; trade_page.py)
    python 20_CODE/rights_values.py          # rights: a player traded before he signed his page contract; written into traded_player_values
    python 20_CODE/buried_contract_values.py # traded veterans with no recent NHL season: cost above burial
    python 20_CODE/contracts_2017.py         # 2017-18 traded players' contracts from CapWages (--fetch [--only NAME ...] for pages)
    python 20_CODE/page_2017_values.py       # the player model's 2017 page for them
    python 20_CODE/trade_asset_values.py     # every traded asset once: one value, its source, at the page's and the 2025-26 cap

One command runs that whole list in order (2026-10-18): `python 20_CODE/trade_refresh.py`, about 8 minutes. It also runs
the five checks those scripts guard against: `25_TESTS/draft_window_count.py` before the pick curve;
`prospect_slot_years_check.py`, `prospect_nhle_look.py` and `prospect_age_look.py` before the prospects;
`uncovered_assets_audit.py` before the 2017 contracts and again after the 2017 page. It stops at the first step that
exits with an error, prints a guard failure, prints no version line, or leaves an output unwritten, and records each
output's hash in `30_OUTPUT/trade_refresh_manifest.json`. `--output-dir DIR` runs it into a copy of 30_OUTPUT. Run
`dashboard_refresh.py` first whenever the contract side changed (the PuckPedia export, WAR, the ages, the price line or
any script in its chain): this chain reads its outputs. It fetches no CapWages page (`contracts_2017.py --fetch` stays a
step run by hand, with Thomas's approval each time); the draft linkage pulls a draft year from records.nhl.com only if
its cached file in `30_OUTPUT/draft_raw/` is missing.

The back-test, after `trade_refresh.py` (both by hand; not in its chain):

    python 20_CODE/trade_sides.py   # each club's side of each trade, zero-sum
    python 20_CODE/backtest.py      # outcomes, club sides, the protocol's tests (about 10 minutes)

The Game Value check (2026-10-20): the same script with XNPV_OUTCOME_METRIC=gv_adj, then gv_raw (outputs carry the
metric's suffix), then `python 25_TESTS/backtest_gv_compare.py` for the protocol's verdicts. In PowerShell set the variable
first: `$env:XNPV_OUTCOME_METRIC = "gv_adj"`, and remove it afterwards (`Remove-Item Env:XNPV_OUTCOME_METRIC`).

Its rules, tests and groups are in `40_DOCS/Backtest_Protocol.md`, committed before the first run; a change to any of
them after a run goes in as a dated amendment saying what changed and why.

To answer questions about the curve on the spot: `python 25_TESTS/pick_lookup.py --help`. Each finding in
`Valuing Draft Picks.docx`, with its command and expected value: `40_DOCS/Valuing_Draft_Picks_Reproduction.md`.
`draft_pick_linkage.py` v1.2 (2026-10-18, commit bc8db88) added sixteen hand-verified WAR spellings; the four finished
tests pinned to the old prospect rows (`prospect_curve_vs_line.py`, `prospect_production_form.py`,
`prospect_term_combinations.py`, `prospect_age_correlation.py`) reproduce their recorded results only from git before it.

## Don't

- **Don't rename anything in `20_CODE/` or `30_OUTPUT/`.** Six scripts import each other as
  modules and outputs are read and written by hardcoded filename. A rename is a code change,
  not a filing decision, and it breaks MANIFEST.csv.
- **Don't add version suffixes to live files.** The file in `20_CODE/` is current. Superseded
  copies move to `90_ARCHIVE/YYYY-MM-DD/` under their original name.
- **Don't blend a second value provider.** Single-provider discipline holds for all player-value
  inputs. MoneyPuck has been used once as a validation benchmark only. Any exception must be
  scoped and documented before it ships.
- **Don't let a valuation see its own season.** A player's value at a decision point draws only
  on information available before that date. Check every new join or metric against this.
- **Don't reopen locked decisions** (D1 through D33 in `00_STATE/DECISIONS.md`, except D22-D27 and D29-D32,
  the draft and prospect decisions retired on 2026-10-04) without a
  deliberate revisit. The skater price per win in force is the Stage 3 rate (locked 2026-07-28):
  left-censored at the league minimum, one intercept, a separate defence slope.
  alpha=0.0132478230, beta=0.0212322891 per win for forwards, plus 0.0028702824 for defencemen
  (0.0241025715), all as cap shares. The retired draft curve and xNPV 0 used it; it now survives as guards.
  xNPV 1 prices on its own line, with term in (directives 4 and 5), re-locked 2026-10-21 on skater_forecast v2.4
  (the forecast audit's decisions; read the value the code assigns in `skater_forward_projection.py`): `XNPV1_RATE`,
  alpha=-0.0043092485, beta=0.0175092736 per forecast win for forwards, plus 0.0040764912 for defencemen, plus
  gamma_term=0.0089103033 a season per year of term; `XNPV1_RATE_TERM_FREE` (0.0081682729 / 0.0311829464 /
  +0.0143706284) is the sensitivity. Goaltenders have their own locked line since 2026-10-21 (`contract_npv.GOALIE_RATE`:
  alpha=-0.0317074413, beta=0.0213830910 per track-record forecast win, gamma_term=0.0081170278; fitted by
  `goalie_value_engine.py` Stage G on the forecast without the age term, applied to the forecast with it). The
  2026-10-20 line (-0.0043026112 / 0.0175297693 / +0.0039447231, term 0.0089105379) is superseded. The 2026-10-14
  crosswalk line (-0.0043651624 / 0.0175356938 / +0.0037579369, term 0.0089300596) and the earlier 2026-10-14
  line (-0.0043530319 / 0.0175137032 / +0.0038753270, term 0.0089195167) are superseded. The 2026-10-05 line (-0.0043574069 / 0.0174691916 / +0.0035971954, term
  0.0089321965) and the 2026-10-02 line (0.0076921739 / 0.0308904772 / +0.0146619104) are superseded. The
  pre-D20 rate (0.0184516 / 0.0202139) and the D20 rate (0.01831864 / 0.01924854) are retired; their
  reproduction guards were removed with the 60/40 checks on 2026-10-14 (Thomas). The Stage 3 constants stay
  in `skater_value_engine.NEW_LOCKED` as the fallback line, no longer re-fitted.
- **Don't trust file size as an integrity check.** Pre-rebuild and post-rebuild
  `draft_yield_curve.csv` are both exactly 845 bytes with different contents. Compare hashes.
- **Don't trust an output because a script ran.** Several scripts carry reproduction guards that
  must pass first. Three stale-file incidents have already cost round trips, which is why
  scripts print SCRIPT_VERSION on every run.
- **Don't commit anything from `30_OUTPUT/`.** It regenerates and would drift by construction.
- **Don't commit the PuckPedia exports.** They are confidential vendor data, gitignored by name.
- **Don't read or write Google Drive.** Retired. Local is source of truth, OneDrive backs it up,
  Dropbox is the sync channel.
- **Don't describe a mechanism you haven't read the code for.** Any document explaining how a
  component works is written from the script that implements it, not from `00_STATE/`, the
  Status Report, or a prior explainer. Those summaries are lossy and they go stale: the first
  pass of the `40_DOCS/` explainer set was written from summaries and got Game Value's inputs
  wrong (expected goals, not actual goals), quoted the aging curve's validation against the
  wrong baseline, reported the draft bootstrap at 10,000 resamples when the code runs 2,000,
  and described a fixed defect (the projection ratio floor) as live and unfixed. Read the
  script's docstring and the constants it actually uses. Where a figure is a run output rather
  than a code constant, cite it from the locked decision record and say so. The same goes for a
  reporting group: the harness's star tier was a 60/40 two-season total with fallbacks
  (`forecast_harness.subjects_at`), and it was described from memory as a three-season weighted
  total (corrected 2026-09-24); since 2026-10-05 (harness v1.4) it is the forecast's 50/30/20
  trailing WAR total. Quote the function that assigns the label.
- **Don't credit a multi-part change to one of its parts.** When a candidate adds more than one
  input or term, score each alone and in combination before saying which one carries the gain. This
  was corrected twice: the goalie price line credited a level-and-slope pair when the level alone
  carried it (2026-09-22), and the goalie participation replacement credited contract status when its
  before/after-2018 period indicator carried it (2026-09-23).
- **Don't compare scores whose targets differ.** Before comparing two forecasts, or two runs of one,
  price both and the outcome on one declared currency and assert that the target is identical. Each
  run's own price line gives a different realised target (corrected 2026-09-22i and caught again
  2026-09-23 before it was reported).
- **Don't say "everything downstream was rerun" after changing a shared default until you have
  searched for the old value by name.** A switch variable only moves the consumers that read it; a
  script that imports the old class directly, or labels it "adopted", stays behind silently. When the
  skater leader changed (2026-09-23), the market comparison still valued on the old class and the
  integration refused the two artifacts ($1.06M apart). Grep for the old class name, not just the
  switch, and make artifacts record which model built them.
- **Don't report a simulated-minus-expected difference as a mechanism's effect.** A gap between 2,000
  draws and the point forecast is mostly sampling noise. Where the mechanism has an exact form (the
  participation chain's recursion), compute its effect exactly: clipping cost 0.000415 WAR a season,
  not the 0.014 first reported (corrected 2026-09-23).
- **Don't summarise a table with "all", "every" or "none" until you have checked every cell.** A
  universal word is a claim about each row. It was wrong three times in one review cycle: "every
  resample" was 1,999 of 2,000, "better on every measure" hid a worse absolute error, and "all
  upward" hid one contract that moved down (2026-09-23). It recurred: "worse on every declared
  score" hid a slightly better absolute error (2026-09-24). Count, then write the count.
- **Don't let a failed variant stand for the whole idea.** A candidate that loses rules out that
  construction. Say what it actually changed (the carry-forward sensitivity moved the whole last
  supported fit, not just the contract-status effect) and what its loss does not rule out.
- **Don't call a formula change "one change" until the fit's rows and weights are shown identical.**
  Dropping a term changes which rows have complete inputs, and a finite-value filter then changes the
  sample silently. Removing the aging curve's level terms admitted 2,295 extra rows (7,164 against
  9,459) and was reported as a single change (corrected 2026-09-24). Fingerprint the fitted rows and
  assert equality (check 46).
- **Don't frame a diagnostic as a two-way verdict.** "If it predicts the first step, the walk is
  the problem; if not, the group is" overstates both branches: a first-step success does not show
  that repeated application causes the later miss, and a failure does not show membership does. Say
  what each arm localises, compare arms on the same rows and weights, and label any arm that uses
  realised future seasons as hindsight (corrected 2026-09-24).
- **Don't report a row count as the amount of evidence.** Say how many independent units stand
  behind it and resample those units. The star diagnostic's 876 rows were 492 distinct transitions by
  84 players, repeated across forecast pages (corrected 2026-09-24); resampling careers is the honest
  interval.
- **Don't read a cause off a horizon pattern.** A bias that grows with the horizon moves with age,
  with who is still observable, and with how old the training seasons are, all at once. "The older
  training seasons differ" was offered from such a pattern (2026-09-24); it is a reading to test,
  not something the pattern shows.
- **Don't copy a figure into a summary without its row label from the source table.** A closing
  summary gave season-WAR misses of 0.17 / 0.64 / 0.87 "one, three and five seasons out"; 0.17 was
  the valuation-season figure and one season out was 0.42 (corrected 2026-09-24). Read each figure
  off its labelled row, not from memory of the table.
- **Don't build an equality guard from inputs both sides share.** A check that prices every
  forecast's realised target from the FIRST forecast's player, dates and discount factor cannot see
  a mismatch in them: a different player ($2.475M) and a different signing date ($26,000) passed
  (corrected 2026-09-24). Compare the identity fields explicitly, and compute each side from its own
  inputs.
- **Don't compare money with exact equality.** Values that should tie (a floor, one path priced two
  ways) differ at $1e-10, and a percentile reads that as above or below a lump: one contract moved by
  0.544 (corrected 2026-09-24). Round to a declared monetary precision before ties and interval
  membership (check 48).
- **Don't take a runner's label for its comparator on trust.** The stress tests print "what the
  chain does today" over a comparison with the flat benchmark (`A0Production`), and a summary repeated
  it as "beats production's forecast" (corrected 2026-09-24). Check which class the comparison
  actually runs before naming it; the live chain is `production_adapter.ProductionChain`.
- **Don't credit a comparator with rows it did not answer.** An adapter that imports production's
  code still fills gaps: where production has no anchor, `ProductionChain` carries the harness's
  trailing total flat and tags the row `outside_production`. The scorecard called all 40,510 rows
  "production" when 4,632 were that fallback (corrected 2026-09-24). Report the full sample as
  "production plus its fallback" and the answerable sample, same rows for every arm, beside it.
- **Don't call a reused holdout sealed, or a pooled pass per-contract calibration.** The 2022-2025
  pages were examined by about thirty variants before the rebuild (plan decision D); "not scored by
  this run" is true, "sealed" is not. Passing pooled PIT and coverage tests means those tests did
  not detect miscalibration, not that each contract or subgroup is calibrated. And name the metric
  a percentage is on: a 6.1% cut in RMSE is an 11.9% cut in mean squared error (corrected
  2026-09-24).
- **Don't say something doesn't exist until you have fetched.** A session clone can be several
  commits behind. On 2026-09-11 a review reported that the target-specific aging-yardstick test
  had "no source anywhere in `20_CODE/`, `00_STATE/` or `40_DOCS/`" and recommended cutting the
  sentence that cited it. The test was real: `aging_bandwidth_test.py` and
  `40_DOCS/Aging_Yardstick_Comparison.md`, committed as `4e708ae` the previous afternoon, three
  commits ahead of the branch being searched. Before reporting a file, test, result or commit as
  missing, run `git fetch origin` and search the current tree. "I could not find it" and "it is
  not there" are different claims. (Ported 2026-09-25 from the retired branch
  `claude/wizardly-goodall-25okn3`, which never reached main.)
- **Don't trust a docstring's account of what a script does; read what actually runs.**
  `aging_split_sample.py`'s docstring says the split-sample check compares two things, the raw
  within-player age-delta curve and "the model's own global age profile," via "two era-specific
  AgingModel instances." Its `main()` builds the panel, computes deltas, and prints the era
  comparison. `aging_curve` is never imported anywhere in the file, so the second comparison
  does not exist, and the 0-of-16 / 1-of-16 result covers the raw deltas only. Read the entry
  point and the call path, not the prose above them. (Ported 2026-09-25, same branch.)
- **Don't sharpen vague wording into a claim the code doesn't support.** Tightening is an edit
  like any other and needs the same check. "The five style measures together receive the same
  total importance as ice time, production level, or trend" is vague; the proposed replacement,
  that each group contributes a quarter of the distance, is false. `_attr_weights()` assigns the
  four groups equal *weights*; what each contributes to a given distance depends on how far apart
  the two players are on it. When a sentence is imprecise but true, the replacement must be
  checkable against the code the same way the original was. (Ported 2026-09-25, same branch.)

- **Don't drop a step from a simplified walkthrough.** A plain-language or high-level
  description of how a value is built still names every operation the code applies to that
  number, in order. The first draft of the two-page overview (2026-09-24) listed the player
  path's steps but left out discounting, although `contract_npv.py` shrinks each future
  season by (1.03)^k. Simplify the wording, not the pipeline: walk the summation in the
  implementing script and check each operation has a place in the text.

- **Don't run a test under a practice environment and report it.** The session's practice `.env`
  points OUTPUT_DIR at a scratch folder holding an older `WAR_with_age.csv`. A harness run under it
  gave a current-model RMSE of 0.9529 against the recorded 0.9036, and the runner's own log still
  named `30_OUTPUT/WAR_with_age.csv`, because that label is hard-coded (caught 2026-09-28 before it was
  reported). Before reading a result, check that its log shows the real path of every input and that
  a reference arm reproduces a recorded figure.
- **Don't shorten an estimation window without checking that every category still has both
  outcomes.** The skater exit risk was moved to windows ending before each valuation date
  (2026-09-28). Those windows hold no star exit for pages 2010-2016, so the star effect's best fit
  is minus infinity. The fallback optimizer "converged" at a star exit risk of 1e-5, which passed the
  table's "no cell at exactly 0 or 1" guard, and the laptop's run of the same fit raised a singular
  matrix (2026-09-30). Count each level's outcomes in every window a fit will see, not only the
  windows the first test used.
- **Don't hand over a command for the Windows laptop without checking it there.** Thomas runs
  commands in Windows PowerShell 5.1 inside a working folder that `sync.ps1` stages wholesale
  (`git add -A`). Three round trips on 2026-09-25 came from ignoring that: a script that required a
  clean tree failed on its own untracked copy; `git show ... > file` wrote UTF-16, which Python cannot
  read (use `cmd /c "... > file"`); and a sync run between a check and a push committed a stray `.env`
  backup and moved a pinned branch. Test on a CRLF clone with the same untracked files, keep
  generated or copied files out of the repo folder, and say plainly when not to run the sync.
- **Don't ask for a decision on something by its name alone.** "Decide whether to keep
  `claude/nifty-euler-u5c5vm`" meant nothing to Thomas (2026-09-25): a branch name, like a model
  label, says nothing about what it is. Say what it does and what keeping or dropping it changes,
  then ask.
- **Don't put a decision to Thomas as a list of version labels.** Script labels for test versions
  (A1, C2, K) are filing labels like model codes. In the question itself, say in hockey terms what each
  option changes and what it costs; a table of labels from an earlier message is not enough. Twice in
  one session he could not decide: the departure-rule choices had to be re-explained, and a question
  offered to "drop K" without saying K was the chance of playing fitted only on contracted seasons
  (2026-10-05).
- **Don't put an item to Thomas without saying what he is asked to do.** A to-do list read back
  to him had an entry that was only a list of meeting topics, with no verb; he could not tell
  whether it was a task, a decision or an agenda (2026-10-04). Each item says do, decide, read or
  bring, and an agenda is labelled as an agenda.
- **Don't add your own angles to an item Thomas asks to queue.** Asked to queue "look into offer sheets with the
  model", the entry added two suggested angles (offer-sheet players against their compensation picks; a cap on
  control-year value). His question was only whether offer sheets are under-used (2026-10-14). Record the item in
  his words, with what the record shows about it; suggest angles in chat, if at all, not in the queue.
- **Don't turn Thomas's own answer, or a settled choice, into a check owed.** A list asked him to
  verify a games-played average he had read off the data himself, to decide yardstick changes that
  had already been tested, and to check a script's handling of future picks after he had decided
  the rule (2026-10-04). If he stated it or the record shows it decided, it is not open. Doubt about
  it is a question to ask once, not a queue item.
- **Don't report a remote branch as still there from an unpruned fetch.** `git fetch` without
  `--prune` keeps deleted branches as remote-tracking refs. Three branches Thomas had already merged
  or deleted were listed as his to deal with (2026-10-04). Run `git fetch --prune origin` before
  saying a branch exists.
- **Don't list a dated to-do from the state files as still pending without checking it still
  stands.** A 2026-09-28 stock-take reported "read through Docs 1-5 and check their page layout"
  as open because the queue still said so; the item was weeks old and long overtaken. When an
  open item is more than a couple of weeks old and nothing has touched it since, say its date
  and ask whether it still applies rather than listing it as live work.
- **Don't quote a constant from a rules file or a docstring; read the value the code assigns.**
  This file quoted a skater rate retired twice over, and `skater_forward_projection.py` still
  labels a superseded rate "locked" at the top of the file before overwriting it further down
  (corrected 2026-09-28). The last assignment is the one that runs.
- **Don't weigh a player's recent seasons any way but 50/30/20 without saying so first.** The model
  reads a player's recent seasons 50/30/20 (last season first; rescaled over the seasons he has, so two
  seasons are 62.5/37.5, not 60/40). The pricing document compared the forecast against a 60/40 total
  the forecast does not use, and Thomas caught it (2026-10-05). His instruction: "when the draft and
  prospect work starts you need to be 100% certain that you are using 50/30/20 when needed." No live code
  reads a 60/40 total since 2026-10-14: the last two places, both checks that priced nothing
  (`skater_value_engine.py`'s July guards and observed-season spine, the goalie engine's RAW regime), were
  retired (Thomas; `skater_value_engine` v2.0, `goalie_value_engine` v1.3). Finished tests in `25_TESTS/`
  that import `trailing_weighted_war` or `W_T1` reproduce only from git before commit 35cbb62.
  Before any code, figure or document reads a trailing total, grep for `0.6`, `0.4`, `W_T1` and
  "60/40" in what it calls, and state which weighting each step uses; a figure stated against another
  weighting says so and why.
- **Don't hand over a scraper after checking only that its pages load.** `ep_extract.py` v3.0 went
  to Thomas with every league slug checked for a 200 response and the draft pass run, but no
  league-season pulled through the package end to end. On the laptop every pull failed: the
  package's clean-up writes "FW" into a true/false column, which pandas 3 rejects (2026-09-28).
  Before handing over any data-pull script, run one real unit of work through the whole path
  (request, parse, cache, database) on the same library versions.
- **Don't test a runner that spends reserved pages by running it.** A confirmation runner scores
  real forecasts on the pages it unseals, whatever the test fakes around it. `run_xnpv1_holdout.py`
  v1.0 was checked in the cloud with synthetic contracts. The fake contracts made the xNPV 1 figures
  meaningless, but xNPV 0 and the no-contract twin were scored for real on 2022-2025 and read
  (2026-09-30; ledger lines labelled CLOUD CODE TEST). Give such a runner a development-page test
  mode first, and test only through it.
- **Don't write that a change reopens no locked decision until each one it touches is checked
  against the code.** D33's first draft said xNPV 1 left D3 and D18 standing. In fact it adds the
  aging changes to a fitted start instead of multiplying the anchor (D3), drops the replacement
  floor for negative anchors (D12 v3), and replaces the exit hazard with the chance of playing
  (D18) (corrected 2026-09-30). List the decisions governing each step the model changes, and read
  what the new code does at that step.
- **Don't build a decided method from its headline; build it from the record's full method.** The
  control-year weight Thomas chose was "the July method", and the decision record says that method
  measures plays-given-qualified only on NHL regulars at the decision. The first build left that
  condition out and gave goalies 0.348 a year against July's recorded 0.788 (2026-10-05). Before
  handing over a build of a recorded method, list every condition the record states, and compare
  the first run's figures with the recorded ones; a large gap is a build error until shown otherwise.
- **Don't add a per-page input to one valuation caller without checking every caller that prices
  the same page.** The sweep, the panel and the dashboard each value a player-season, and the
  dashboard refuses a page whose re-price differs from the panel's by more than $1. A signing date
  keyed on the panel job's own contract gave two values for one page when a player had two contracts
  in a season, and the dashboard's July 1 re-price would have failed every late-signed page
  (2026-10-05). Key the input on what the engine values (`NPVEngine.first_season_as_of`) and route
  every caller through it.
- **Don't let borrowed code bring in settings nobody named.** When a test arm or a promoted model
  reuses code from another model, list every setting that code carries and how each is chosen, and
  check the description of the result against the code, before Thomas is asked to approve it. The
  2026-09-30 "starting rate fix" reused the rebuild's trailing-total builder, which picks its weights'
  decay from the data (47/32/21). D33 described the adopted model as 50/30/20, Thomas approved that
  description, and the fitted decay ran unapproved until he found it on 2026-10-04. Thomas wants
  fewer moving parts, not more: an added parameter is a decision for him, never a side effect.
- **Don't name how an input went wrong until you have its write date.** The laptop's
  `WAR_with_age.csv` was diagnosed as having "reverted" to 70.9% birthdates. Its timestamp showed it
  had never been rebuilt there after 2026-07-28 (corrected 2026-10-02). A machine-specific result
  starts with the date, coverage and hash of every input table on that machine; the rebuild runners
  now refuse an age table under 99% coverage (`production_adapter._check_age_coverage`).
- **Don't explain a gap between two counts until you have counted the starting point.** The bio pass
  printed 4,853 needed, then 4,004; with 949 bios stored, the 100 "extra" bios were read as the old
  run still saving while the new one ran, and the 403 blamed on two runs at once. Thomas had stopped
  the old run first; 100 bios were already stored before the first count (2026-10-05). Recompute
  wanted, stored and needed from the code's own functions before naming a cause.
- **Don't take a scraper's error message as the cause; send the request yourself.** The package
  printed "403 Error" and two sessions treated it as Elite Prospects blocking the laptop, slowed the
  pass twice and sent Thomas to wait three days. The page was loading with status 200: the package's
  block test matched "evil" inside "Belleville" (2026-10-08). Before diagnosing a block, request the
  exact page the run is stuck on and read its status code and body, and note which player it is.
- **Don't hand Thomas a reader-facing document without an agreed spine and the writing-style skill's 1.6 review
  pass.** "Valuing Draft Picks" ran 11 pages as "an info dump, and a long one at that", and its rewrite still drew 38
  comments, nearly all one of six failures: vague phrases for plain claims, coined labels ("dollar scale", "the
  chain"), claims without their number, results described instead of shown, numbers without their meaning, and
  choices without their reason (2026-10-09). Agree three to five take-aways first, then check each sentence against
  skill section 1.6 before handing it over. Then run the checks at the end of `40_DOCS/Valuing_Prospects_Feedback.md`, his
  five rounds of notes on "Valuing Prospects" sorted into themes (2026-10-16).
- **Don't state what an option costs against a baseline nobody chose.** Asked how pricing a rookie's
  entry-level seasons at the deal's remaining term compares with pricing them as one-year deals, a
  reply put the difference at "roughly $5M", the whole term premium, when one-year pricing carries a
  year of premium too: the difference is about $2.6M (corrected 2026-10-09). Price each option on the
  table and subtract them; never one option against zero.
- **Don't queue updates to the supervisor documents.** The documents in `40_DOCS/Supervisor_Drafts/`
  ("Valuing Draft Picks" and the four main documents) are point-in-time snapshots of progress. A work
  queue listed a new version of "Valuing Draft Picks" because its figures had moved, and Thomas dropped
  it: "Those are meant to be point in time snapshots of progress, not anything we need to continuously
  update" (2026-10-14). When the model changes, record it in the state files; write a new short note only
  if Thomas asks for one.
- **Don't number seasons after the draft from zero in anything Thomas reads.** Hockey names them from the draft: D0
  is the draft season, D+1 the season after it. "Valuing Prospects" called the season after the draft "season 0", and
  Thomas had to translate it (2026-10-15). The code's k = 0 can stay; in prose, tables and figures write D+(k+1), and
  say once which seasons a measure reads (a prospect valued in D+1 is measured on D0, D-1 and D-2).
- **Don't report a redraw count beside the p-value it makes.** "Lower in 1,997 of 2,000 redraws (p = 0.0015)" says one
  number twice. Thomas: "if the whole redraw thing is really just the p value, you should just state the p value"
  (2026-10-15). Define the p-value once, in a caption, and report it alone.
- **Don't show a model's formula once and then add its terms in prose.** "Valuing Prospects" showed the formula for
  the slot alone, then added production, its square and age in words. Thomas: "you should definitely show the adopted
  formula each time you add a variable to the model" (2026-10-15).
- **Don't write one model's formula with discounting and another's without.** Every model discounts at 3% a year, but
  only the contract formula showed it: `contract_npv.py` divides each season by (1.03)^k, while the pick curve and the
  prospect model add up cap shares, where 3% cap growth and 3% discounting cancel (D11, D17), so their formulas showed
  no discount at all. Thomas asked why picks and prospects were not discounted, and: "when writing out the formulas you
  should just do the full form because it helps to see that there is still discounting in all models" (2026-10-19).
  Write every value formula in full, the same way for each model: each season's value and cost in that season's
  dollars, divided by (1.03)^k (a realised career's seasons multiplied by the stated cap over that season's cap, the
  same discount at the cap's actual growth), then say in one line where the growth and the discount cancel. Never
  present the cancelled cap-share sum as the formula.
- **Don't explain a regression by its specification, or an interaction by its arithmetic.** "It regresses each
  prospect's remaining surplus on his slot's star probability, through zero, with draft-year indicators that sum to
  zero" and "star value for his seasons since the draft" meant nothing to Thomas, and "multiplies production by years
  past eligibility" read as doubling a player's scoring two years on (2026-10-15). Say what is compared with what,
  what the coefficient measures in hockey terms ("each year older lowers the value of each point by $0.064 million"),
  and give one worked number. A negative coefficient beside its square needs the same: say where the curve turns.
- **Don't say the data rejects a form until the test is the right one and does not hang on an arbitrary choice.** Twice in
  one session (2026-10-15): a reply said "the data rejects" a straight-line decline of the slot's value from the shape
  of the estimates, when the held-out test could not tell the two apart (p = 0.33); and it said the data rejects
  production squared alone in every sample, when that test's verdict flipped with where age was centred (p = 0.0027 at
  18.5, 0.063 at 18). Run the held-out comparison before calling a form worse, and check that the verdict survives a
  change of centre or scale that leaves the adopted model's values unchanged.
- **Don't attribute a line in a meeting transcript by its speaker label.** The transcription's "Speaker A" and
  "Speaker B" swap between Thomas and Karl mid-meeting. A reply credited Karl's guess (half of the players who
  reach the NHL do it in their first season) to Thomas; Thomas's guess was about 10% of first-rounders
  (2026-10-15). Before saying who said something, check it against what each person would say (Karl asks about
  method, Thomas explains hockey), and when it is still unclear, say so instead of naming either.
- **Don't name a model version by its shape; name it by its terms.** "The curve" and "the full curve" in "Valuing
  Prospects" left Thomas asking how they differed: "The whole thing is a curve" (2026-10-15). Write "linear production",
  "linear and squared production", "production squared alone", and use the same name for one version everywhere.
- **Don't call a draft position "the slot".** The slot is an area of the ice; "slot" for a pick's position read as
  non-specific to Thomas (2026-10-15). Write "draft position".
- **Don't draw a cumulative share without saying what it is a share of.** "When drafted players reach the NHL" plotted
  shares of the players who arrived, so every line reached 100%, and Thomas read it as everyone reaching the NHL
  (2026-10-15). A cumulative curve of an outcome some never reach is drawn as a share of the whole group, so the
  never-reached share shows.
- **Don't argue from a part of the model the reader has not reached.** Section 2 rejected production squared alone
  on how age is centred, before Section 3 introduces age; Thomas: "Why are we talking about age here at all?"
  (2026-10-15). Give the reason that stands where it is, or move the argument after what it rests on.
- **Don't describe a measure by how it is built when the reader asks what it means.** "Years past first eligibility
  ... the age the autumn after his draft, less 18" read to Thomas as valuing a player by his draft age, when within a
  season it also measures the age at which he scored, which is what matters (2026-10-15). Say what the measure
  compares in hockey terms first.
- **Don't describe an equivalent of the method Thomas asked for; build the one he asked for.** Asked to use a full
  set of interaction terms, the document said the season-by-season fits "give exactly the same coefficients" while
  the code kept fitting each season alone. Thomas: "Just make the regression actually be the interaction terms. I
  feel like I've said this multiple times" (2026-10-16). Change the code to run the asked-for method, keep the old
  route only as a guard, and describe what runs.
- **Don't write "reliable" for a test result.** Thomas: "Be specific. You mean statistically significant"
  (2026-10-16). Say "statistically significant at the 5% level", with the p-value.
- **Don't introduce rejected alternatives as if the model used them.** "Three simpler rules each restrict how the
  value may change" read as rules in the model (2026-10-16). Say they were tested and rejected before describing
  them.
- **Don't let a table's baseline go by a shorthand name.** Table 8's "production model without age" was the Section 2
  model, and Thomas asked why the age candidates were not compared with it (2026-10-16). Name the baseline by its terms
  in the title, the row and the column.
- **Don't quote a pooled estimate for a subgroup it doesn't describe.** Asked about valuing D+5-and-later skater
  prospects without production, a reply offered draft position alone as significant there ($2.01M, p = 0.002). That
  star value pools skaters and goaltenders: skaters alone give $0.16M (p = 0.64), goaltenders $19.35M (2026-10-16).
  Before quoting a fit's estimate for a group, check it was fitted on that group's rows.
- **Don't rebuild a document Thomas has annotated without carrying his own edits into the builder.** He edits the text
  in Word as well as commenting (not as tracked changes). v3 of "Valuing Players, Draft Picks, and Prospects" was rebuilt
  from the builder after only his comments were read, and his rewording of five paragraphs, the overview paragraph he
  deleted, the statistical-terms table he deleted and his new Section 2 title were lost. Thomas: "If I made a change to
  the document you should honour that change" (2026-10-21). Before each rebuild, diff the text of his copy against the
  copy he was sent, paragraph by paragraph (deletions included, not only `w:ins`/`w:del`), carry each edit into the
  builder verbatim, and check after the build that each is present. Never write over a file he has open or has saved
  edits into.
- **Don't personify the model or its parts.** "On the cost side only the discount acts" drew: "The Discount is not a
  noun and it cannot act. This is a MAJOR tell of AI writing. Do not personify things in the model" (2026-10-21). A
  discount, forecast, regression or price line does not act, know, ask, see, read or learn; say what is done to what:
  "A cap hit is in fixed dollars, so on the cost side discounting is present."
- **Don't open a document with detail that only a later section explains.** Section 1 of "Valuing Players, Draft
  Picks, and Prospects" gave the realised-career cap formula before picks were introduced: "indecipherable unless
  you've already read the document ... The entire document needs to be cleared of writing continuity errors like this"
  (2026-10-21). An opening section introduces the concept, why it matters and how it works in general; each detail goes
  where its context is.
- **Don't write "play" for what a player delivers.** Thomas: "Important to use 'performance' rather than 'play'"; a
  forecast of it is "forecasted performance" (2026-10-21). And a pick or prospect delivers no performance until its
  player reaches the NHL.
- **Don't call the value of the control seasons anything but the terminal value** (Thomas, 2026-10-21;
  `rfa_terminal_value.py`).
- **Don't define a symbol by apposition.** "and C his cap hit" reads as if C were a verb; write "C is his cap hit"
  (2026-10-21).
- **Don't use "Decision:" headings.** Thomas: "I am not a fan of these" (2026-10-21). Keep the options and reasons;
  name the topic in the heading.
- **Don't name a data source without saying who it is and why it is credible.** WAR, Patrick Bacon, PuckPedia and
  the trade ledger were named without either (2026-10-21). His notes are in `40_DOCS/Valuing_Players_Feedback.md`.
- **Don't describe what an earlier version of the model did in a reader-facing document.** v3 of "Valuing Players, Draft
  Picks, and Prospects" explained the forecast, the chance of playing, the price line, term and the control-season cost
  against the model's earlier projection, its trailing-WAR price line and the qualifying-offer chain. Thomas: "If you were
  someone reading this paper, would you give a shit what a model that doesn't exist did? No"; "What's important is
  defending the parameters used in the model as it exists and describing how and why they are used" (2026-10-21).
  Defend each choice shortly by why it is right; an alternative tested against the model as it is may stay, briefly; a
  superseded version, and anything no longer in any part of the model (the qualifying-offer chain), is not mentioned.
- **Don't write a number without saying what it is.** "Start 1.1506 against 1.1611; one to five seasons ahead 1.3598
  against 1.3689" drew: "I can just say random numbers too if I wanted to and act like they mean anything" (2026-10-21).
  Name the measure and its unit each time a figure appears (the forecast's root mean squared error, in WAR per 82), and
  say what a difference of that size means. "Best in the same test" is shown, not asserted.
- **Don't leave a term in an adopted model that is not statistically significant without a reason Thomas has
  accepted.** Position at p = 0.404 in the games share, age squared at p = 0.111 in the chance of playing and linear
  production at p = 0.113 in the prospect model drew: "I'm getting tired of seeing things that aren't statistically
  significant in these results" (2026-10-21). Before a table of an adopted regression goes to him, list each term with
  p above 0.05 and either test dropping it or state why it stays; never show one in silence.
- **Don't give a circular reason.** "The threshold used throughout the model" as the reason for a threshold, and "a
  club holds an asset for the seasons it controls it", drew "Horribly circular reasoning" (2026-10-21). The reason is
  what makes the choice right, not that the model makes it.
- **Don't state a claim the document does not show.** "Goaltenders' WAR varies far more from season to season" and
  "the signal was judged too weak": "You cannot simply state that, you need to show proof" (2026-10-21). Give the
  figure, or a table, that shows it.
- **Don't write "last" for the most recent season.** Thomas: "Most recent ... to avoid confusion between last meaning
  previous and last meaning final" (2026-10-21).
- **Don't run several tested figures through a paragraph.** Four errors and two p-values in prose drew "Shit like this
  is where a table is helpful" (2026-10-21); so did a list of five comparable players with their weights.
- **Don't let a document address its own reader.** Anything going to Karl (the `40_DOCS/`
  explainer set, status reports, review write-ups) must not name him, reference "the meeting,"
  or frame itself as a response to specific feedback ("this document answers...," "raised
  twice"). Session logs and meeting notes are source material for facts, not for framing. Write
  every reader-facing document as if it stood on its own, explaining how the model works, not
  as a reply to a conversation the reader was already in.

## Working style

Plain English. High hockey fluency, no assumed statistics or econometrics vocabulary. Name a
technical term once, then explain it plainly and say why it matters. Numbered steps with the
reasoning behind them. For code, explain each block in prose before or alongside it, with heavy
inline comments flagging every baked-in assumption: join keys, dedupe rules, which coefficient
vintage is in use, how a curve is applied.

**Never use a codename as if it were a name.** Model labels (A0, A1, A2), horizon codes
(h0-h5), phase numbers, decision IDs (D6, D20) and file prefixes are filing labels. They are
useful for pointing at a row in a table; they carry no meaning on their own, and a sentence
built out of them is unreadable. Lead with what the thing IS, in hockey English, and put the
label in parentheses afterwards if it earns its place. "A2 loses to A1 at h4" says nothing;
"the component model is 8% worse four seasons out" is the same sentence with the meaning left
in. This applies to chat, commit messages, session logs and every document. A table may use
short labels in its cells only if the column or a line above it says what each one means.

Every time I get corrected on something, add a rule here so it doesn't repeat.
