# 50_REBUILD — the experimental player-model rebuild

**Status: experimental. Nothing here is production, and nothing here is locked.**

This tree is the build of the player-model rebuild proposed in
`40_DOCS/Player_Model_Rebuild_Plan_Fable.md`. It is deliberately separate from the live
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
| 0 | dates, identities, harness | **built, acceptance PASS** |
| 1 | ability forecast (A0/A1/A2) | first comparison run; not settled |
| 2 | participation and exit | not started — placeholder in the harness |
| 3 | aging | not started — flat carry-forward in the harness |
| 4 | contract price and production currency | blocked: needs the PuckPedia export |
| 5 | valuation by simulation | not started |
| 6 | rebuild, confirm, lock | not started |

See `docs/Phase0_Harness_Report.md` for the findings, including two that were not expected:
an undocumented break in the WAR export from 2023-24, and a first comparison that does not
yet meet the plan's Phase 1 acceptance test.

## The holdout seal

Development pages are 2015–2021. Pages 2022–2025 are confirmatory and are scored **once**,
at the end of Phase 5. `forecast_harness.Harness.run()` refuses a confirmatory page unless
the caller explicitly unseals with a written reason, which is logged. Every number in this
tree so far comes from development pages.

## What this tree needs that it does not have

The vendor inputs all exist in the Dropbox sync channel. The obstacle is transport: the
direct download host is refused by this environment's egress policy, and the connector's
text extraction of an `.xlsx` collapses interior empty cells, so columns shift per row and
the result cannot be realigned honestly. A real `.csv` crosses that path losslessly.

- **Birthdates.** `10_SOURCE/ep_birthdates.csv` is recovered and wired in
  (`REBUILD_BIRTHDATES=10_SOURCE/ep_birthdates.csv`), joining on name + position. It raises
  coverage to 29.1% of season rows but is **not usable for aging**: Elite Prospects was the
  second source, scraped for the players PuckPedia could not match, so coverage runs 83.5%
  in 2007 down to 0.0% from 2018 onward and falls with player quality. No model uses an age.
  Needs the PuckPedia birthdates or a completed EP pull.
- **Contracts.** Phase 4 needs signing dates, cap hits and contract state — the workbook as
  bytes, not as extracted text. `information_set.contracts_known_at()` raises rather than
  returning an empty frame.

**Cheapest unblock for both: a CSV export of the PuckPedia workbook in the Dropbox
`10_SOURCE/` folder.**
