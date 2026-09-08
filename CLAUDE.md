# CLAUDE.md — xNPV Model

## What this is

A Master's economics thesis building a net-present-value framework that prices three NHL
trade-asset classes (rostered players, draft picks, non-roster prospects) on one common scale,
projected surplus value in dollars, then back-tests historical trades against realized outcomes
to find categories of systematic mispricing. The cross-asset integration onto a single currency
is the contribution. Audience is an econometrics supervisor who weighs identification issues
(circularity, look-ahead bias, selection bias) above all other concerns.

## Current state, and how stale it is

`00_STATE/PROJECT_STATE.md` is the current-state anchor. It was generated 2026-07-29 with a
7-day refresh cadence and has not been refreshed since the 2026-07-30 file migration.
**Treat it as unverified beyond 2026-07-30.** Refreshing it is the first task in this repo.
Known open items as of that date: regenerate the downstream spines after the 2026-07-28
rebuild, and close two remaining verification items (Stage 2 length-term null test, rebuilt
draft curve).

Detail beyond the state file lives in the Craft "xNPV" workspace. Precedence when sources
conflict: PROJECT_STATE.md and Craft > the scoping document > the Research Brief.
There is no paper manuscript. Writing begins once the model is built.

## Stack

Python 3, SQLite. pandas, numpy, statsmodels, scipy, requests, TopDownHockey_Scraper.
No virtualenv convention is established yet. Stata or R on request only.

## Folder map

    00_STATE/     PROJECT_STATE.md, four sequence docs, MANIFEST.csv
    10_SOURCE/    vendor and scraped source data. Code reads it, never writes it
    20_CODE/      flat. Every script, current version only
    30_OUTPUT/    flat. Every spine, panel, curve, diagnostic, run log. Gitignored
    40_DOCS/      reports, reviews, briefs
    90_ARCHIVE/   YYYY-MM-DD/ superseded material under original names. Gitignored

`20_CODE` and `30_OUTPUT` are flat deliberately. Per-pillar subfolders were tried, sat empty
for a month, then filled with duplicates and sync-conflict copies while real work happened in
one flat directory.

## How to run it

Paths come from `.env` (copy `.env.example`). Run from the repo root.

Player pillar, in order:

    python 20_CODE/skater_value_engine.py        # Layer 1, observed-season value
    python 20_CODE/skater_forward_projection.py  # Layer 2, forward projection
    python 20_CODE/rfa_terminal_value.py         # terminal value at expiry
    python 20_CODE/exit_hazard.py                # survival weights
    python 20_CODE/contract_npv.py               # summation, writes contract_npv_spine.csv
    python 20_CODE/contract_npv_panel.py         # panel build

Game-level chain, in order:

    python 20_CODE/nhl_gamelog_scraper.py
    python 20_CODE/on_ice_reconstruction.py
    python 20_CODE/xg_model.py
    python 20_CODE/score_state.py
    python 20_CODE/metric_assembly.py

Draft pillar:

    python 20_CODE/draft_pick_linkage.py
    python 20_CODE/draft_yield_curve.py

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
- **Don't reopen locked decisions** (D1 through D27 in PROJECT_STATE.md) without a deliberate
  revisit. The locked skater rate is alpha=0.0184516, beta=0.0202139.
- **Don't trust file size as an integrity check.** Pre-rebuild and post-rebuild
  `draft_yield_curve.csv` are both exactly 845 bytes with different contents. Compare hashes.
- **Don't trust an output because a script ran.** Several scripts carry reproduction guards that
  must pass first. Three stale-file incidents have already cost round trips, which is why
  scripts print SCRIPT_VERSION on every run.
- **Don't commit anything from `30_OUTPUT/`.** It regenerates and would drift by construction.
- **Don't commit the PuckPedia exports.** They are confidential vendor data, gitignored by name.
- **Don't read or write Google Drive.** Retired. Local is source of truth, OneDrive backs it up,
  Dropbox is the sync channel.

## Working style

Plain English. High hockey fluency, no assumed statistics or econometrics vocabulary. Name a
technical term once, then explain it plainly and say why it matters. Numbered steps with the
reasoning behind them. For code, explain each block in prose before or alongside it, with heavy
inline comments flagging every baked-in assumption: join keys, dedupe rules, which coefficient
vintage is in use, how a curve is applied.

Every time I get corrected on something, add a rule here so it doesn't repeat.
