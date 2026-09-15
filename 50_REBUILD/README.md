# 50_REBUILD — the experimental player-model rebuild

**Status: experimental. Nothing here is production, and nothing here is locked.**

This tree is the build of the player-model rebuild proposed in
`50_REBUILD/docs/Player_Model_Rebuild_Plan_Fable.md`. It is deliberately separate from the live
model so the rebuild can be wrong, restarted, or abandoned without touching anything that
currently works.

## What separate means, concretely

- **Its own code and output.** Scripts live in `50_REBUILD/code/`, outputs in
  `50_REBUILD/output/`. Nothing here writes to `20_CODE/`, `30_OUTPUT/`, `10_SOURCE/` or
  `90_ARCHIVE/`. That is enforced, not promised: every write goes through
  `rebuild_config.out_path()`, which raises on any path resolving outside this tree.
- **No production file is edited.** The live pipeline runs exactly as it did before this
  tree existed. `git log 20_CODE/` shows no change from the rebuild.
- **Read-only on source.** The rebuild reads the same vendor CSVs the production chain
  reads, through `assert_read_only_source()`, which refuses anything outside `SOURCE_DIR`.
  Both chains therefore see identical source bytes, and neither can write them.
- **Its own gitignore.** `output/.gitignore` ignores this tree's output locally, so the
  repo-root `.gitignore` did not need editing either.
- **No locked decision opened.** D1–D27 stand. Where the rebuild's design departs from a
  locked decision, it does so *inside this tree only*, and the departure is named in the
  phase report rather than adopted.

## Layout

All player-model rebuild documentation belongs in `50_REBUILD/docs/`, including the plans,
reviews, supporting diagnostics, and phase reports. Project-wide state and session history
link here from `00_STATE/`.

- [Fable rebuild plan](docs/Player_Model_Rebuild_Plan_Fable.md)
- [Alternative rebuild plan](docs/Player_Model_Rebuild_Plan.md)
- [Ground-up review](docs/Ground_Up_Player_Model_Review.md)
- [Independent candidate review](docs/Player_Rebuild_Candidate_Review_Codex.md)
- Supporting diagnostics: [anchor shrinkage](docs/Anchor_Shrink_Test.md),
  [comparables limit](docs/Aging_Comparable_Limit_Test.md),
  [aging coverage](docs/Aging_Curve_Coverage_Audit.md), and
  [pipeline experiment](docs/Pipeline_Experiment.md).

    code/     the rebuild's scripts, flat, current version only (repo convention)
    output/   everything generated; gitignored, regenerable
    docs/     per-phase reports: what was run, what it found, what it did not settle

## How to run it

No `.env` is required — paths fall back to the repo layout. From the repo root:

    python 50_REBUILD/code/player_season_table.py       # the shared season table + guards
    python 50_REBUILD/code/information_set.py           # frozen-information self test
    python 50_REBUILD/code/run_phase0_acceptance.py     # the Phase 0 gate + first comparison

`run_phase0_acceptance.py` runs the whole chain and is the one to run if you only run one.

## Where the build has got to

| Phase | What it is | State |
|---|---|---|
| 0 | dates, identities, the scoreboard | **built, acceptance PASS**; item 4 (ages) closed at 98.3% coverage |
| 1 | how good will he be | run with ages. **The component model fails the plan's gate; the simpler calibrated total is ahead** |
| 2 | will he be playing at all | not started — placeholder in the harness |
| 3 | aging | not started — flat carry-forward in the harness |
| 4 | what the market pays, and what production is worth | **unblocked** — contracts CSV validated against the locked regression |
| 5 | put a dollar value on the whole contract | not started |
| 6 | rebuild the other pillars, confirm once, lock | not started |

See `docs/Phase0_Harness_Report.md` for the findings, including two that were not expected:
an undocumented break in the WAR export from 2023-24, and a first comparison that does not
yet meet the plan's Phase 1 acceptance test.

## The holdout seal

Development pages are 2015–2021. Pages 2022–2025 are confirmatory and are scored **once**,
at the end of Phase 5. `forecast_harness.Harness.run()` refuses a confirmatory page unless
the caller explicitly unseals with a written reason, which is logged. Every number in this
tree so far comes from development pages.

## What this tree needs that it does not have

The vendor inputs are present. `10_SOURCE/` carries the two PuckPedia exports as CSV and
`ep_birthdates.csv`, all three gitignored as confidential and none committed.

Two notes for anyone re-running this elsewhere:

- **The CSVs must be CSVs.** An `.xlsx` moved through a text extraction loses interior empty
  cells and its columns shift per row; `contract_source.validate()` would catch that, but the
  cheaper fix is to keep the CSV exports.
- **Encodings differ per file** (contracts cp1252, trades UTF-8) and are detected, not
  assumed. Never read them with `errors='replace'` — it corrupts the accented surnames that
  are the join key to `WAR.csv`, and a failed name match drops a contract silently.

Still missing: nothing that blocks Phases 1 through 4. The game-level SQLite store
(`nhl_gamelogs.sqlite`, 2.3 GB) is needed only for the in-season update that revalues a
player at a trade deadline rather than at a season start.
