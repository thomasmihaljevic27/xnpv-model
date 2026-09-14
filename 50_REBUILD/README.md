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

- **Birthdates.** They come from the PuckPedia export via `20_CODE/age_join.py`. Age
  coverage in this checkout is 0%, so the aging work in Phase 3 and the age-and-position
  norm in Phase 1 are running on position alone. The season table takes a birthdate CSV
  through `REBUILD_BIRTHDATES` when one is available.
- **Contracts.** Phase 4 needs signing dates, cap hits and contract state.
  `information_set.contracts_known_at()` raises rather than returning an empty frame.
