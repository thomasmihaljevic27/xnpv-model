# Moving xNPV 1 into production: the plan

Version 2, 2026-10-02. It replaces the 2026-09-30 version and folds in Thomas's three answers.
Nothing in this plan is built yet. Every mechanism below was read from the script named beside
it.

## Thomas's decisions (2026-10-02)

1. **Production keeps its own copy.** xNPV 1's code is promoted into the existing folders. xNPV 0's
   superseded code and the whole `50_REBUILD/` tree go to `90_ARCHIVE/`.
2. **The current season's chance of playing comes from xNPV 1's forecast.** Production's current
   rule, S_0 = 1, is dropped. This is what was tested:
   - **Season scores.** The harness scores the valuation season with each model's own chance of
     playing. xNPV 0's fixed 1 gives Brier 0.212 in that season against 78.8% who actually played.
     xNPV 1's version without contract status predicts 0.795 for that season (cloud, development
     pages).
   - **Dollar scores.** Every season of a contract's term, the first included, was priced on
     chance of playing x rate x games share, with the chance of playing read at the signing
     (`contract_price_model.attach_forecasts`).
   - **What 1 would mean.** Setting the first season's chance to 1 would be an untested change.
3. **The spread behind the league-minimum floor:** explained below. **Decision still owed.**

## What changes and what does not

**Changes: the skater forecast only.** Production values a skater contract in
`20_CODE/contract_npv.py` (`NPVEngine._npv_skater`). For each season k of the contract it computes:

- **value.** The projected WAR comes from `skater_forward_projection.SkaterProjector.project_contract`.
  That WAR is priced at the Stage 3 rate on the ex-ante cap path, and its expectation is floored at
  the league minimum (`expected_floored_value`).
- **survival.** A chained factor, S_k = S_{k-1} x (1 - h). The hazard h is read from this page's
  exit-hazard table, indexed at k-1. S_0 = 1.
- **present value.** (S_k x value − cap hit) / 1.03^k.

The RFA terminal value (`rfa_terminal_value.py`) is added to this. It takes its expiry-year WAR from
the same projector.

Under xNPV 1, value uses the WAR the player produces if he plays (rate per 82 x games share), and
survival is xNPV 1's chance of playing that season, read directly rather than chained.

**Unchanged:**
- the Stage 3 price per win;
- the 3% cap path and discount (D11, D17);
- the league-minimum floor rule (D10);
- the cap hit charged whether or not the player plays (D16(i));
- the extension chain (D28);
- the RFA terminal value's qualify-rate chain (D13, D14(c));
- the whole goalie branch, including its exit-risk table in `exit_hazard.py`;
- the draft pillar.

## The floor spread, in detail (decision 3)

**The rule (D10).** A season is never priced below the league minimum: a club can always replace a
player for that. On the Stage 3 line a forward's value reaches the minimum at about −0.21 WAR. For
2027-28 on the 2025 page, the cap is $101.3M, the minimum $900,000, and a 0-WAR forward is worth
$1.34M.

**Why the spread matters.** The projection is a best guess, not a certainty.
- Below the floor, the value is held at the minimum. Above it, it rises one-for-one.
- So averaging over the possible outcomes gives more than pricing the best guess: the bad outcomes
  are cut off at the floor and the good ones are not.
- Production adds that difference (`expected_floored_value`, a closed form). How big it is depends on
  how wide the range of outcomes is, the "spread".
- Measured before it was wired in, on the retired price line: +$68,200 per contract on average, concentrated at zero projected
  wins and close to nil above two.

**Where the spread comes from today.**
- `_BACKCAST_MAE_36` in `skater_forward_projection.py`: xNPV 0's own backcast errors of 0.522 /
  0.735 / 0.803 WAR one, two and three seasons out, converted to a spread (x 1.2533).
- From four seasons on, the three-season figure is held flat. The code calls that a placeholder.
- In the valuation season the spread is **zero**, because production treats that season as observed.

**Why it should change under xNPV 1.**
- **The figures belong to xNPV 0.** They measure how wrong xNPV 0's projections are, on its own
  backcast sample.
- **The valuation season is a forecast too.** On 1 July the season has not been played. On the
  harness, xNPV 1's error in that season, among players who played, is 0.68 WAR, not zero.
- **Same sample for both models** (cloud, development pages, rows xNPV 0 answers, seasons played),
  mean absolute error of the WAR-if-plays:

  | Seasons ahead | 0 | 1 | 2 | 3 | 4 | 5 |
  |---|---:|---:|---:|---:|---:|---:|
  | xNPV 1 (its rate and games share) | 0.680 | 0.756 | 0.805 | 0.857 | 0.884 | 0.895 |
  | xNPV 0 | 0.740 | 0.796 | 0.840 | 0.880 | 0.892 | 0.912 |

  The constants in use (0.522 / 0.735 / 0.803) are smaller than xNPV 0's own errors on this sample,
  because they were measured on a different one.

**What it does to a value.** Worked from production's own functions, for a forward two seasons out
on the 2025 page. Each figure is the floor's addition per season.

| Projected WAR | Today's constant (0.735) | xNPV 1's harness error (0.805) |
|---:|---:|---:|
| −0.5 | +$513,902 | +$585,762 |
| 0.0 | +$589,042 | +$662,639 |
| +0.5 | +$252,836 | +$310,441 |
| +1.0 | +$88,557 | +$123,033 |
| +2.0 | +$5,484 | +$11,033 |

**The options:**
- **(a) Recommended.** Re-derive the spread from xNPV 1's harness errors among seasons played, one
  figure per season ahead from 0 to 5, then held flat. That gives the valuation season a spread too.
  It is consistent with decision 2: both treat the valuation season as forecast.
- **(b)** The same, but keep the valuation season at zero.
- **(c)** Keep today's constants as a stated placeholder.

Every option moves only the floor term. Players projected well above replacement barely change; low
projections move by tens of thousands of dollars per season.

## The layout after the move

**Promoted into `20_CODE/`** (xNPV 1 and what it needs to run). These come from `50_REBUILD/code/`.
Each is renamed for what it is and stripped of the candidate classes xNPV 1 does not use.

| Now | Role in production |
|---|---|
| `star_candidates.py` + `obvious_fixes.py` | xNPV 1 itself: the start, the games share that reads level, the comparable-player walk added on, departures at replacement |
| `ability_forecast.py` (only the classes xNPV 1 inherits) | the fitted start and games share |
| `participation_model.py` | the chance of playing, reading contract status |
| `aging_additive.py` | imported by the classes above, so it is needed at import even though xNPV 1's aging is `aging_curve.py`; dropped if the prune shows it unused |
| `player_season_table.py`, `information_set.py`, `contract_source.py` | the season table, the what-was-known-when rules, the contract-status reader |
| `forecast_harness.py` + the player resampler | the scoreboard every future model change is checked on |
| `rebuild_config.py` | folded into the above; outputs go to `30_OUTPUT/` |

New in `20_CODE/`: `xnpv1_forecast.py`. It fits xNPV 1 page by page and writes
`30_OUTPUT/xnpv1_forecasts.csv`, every row tagged with the model and the code versions.
`contract_npv.py` and `rfa_terminal_value.py` read it in place of `SkaterProjector` and the skater
exit hazard. `dashboard_refresh.py`'s `CHAIN` runs it before `contract_npv.py`.

**Archived to `90_ARCHIVE/<date>/` under the original names:**
- xNPV 0's skater code: the pre-migration copies of `skater_forward_projection.py`,
  `contract_npv.py`, `rfa_terminal_value.py` and `exit_hazard.py`. The live files are edited, not
  removed: they also hold the price, cap path, extension chain, goalie branch and goalie exit risk,
  which stay.
- The last xNPV 0 spine and panel, so the switch can be compared contract by contract
  (`npv_spine_compare.py`).
- Everything in `50_REBUILD/` that is not promoted: the runners, review scripts, the alternative
  valuation machinery (market price line, simulation, control years), and the output folder.

**Two conflicts with "archive 50_REBUILD", and the recommendation for each:**
1. **`90_ARCHIVE/` is gitignored, so it exists only on the laptop.**
   - A file retired by a cloud commit is deleted from the laptop when the commit is pulled, and
     nothing lands in the archive.
   - `25_TESTS/archive_from_git.py` writes the archive copies from git history. It works before or
     after the pull and never overwrites.
   - Archived files also leave GitHub's current tree. Git history keeps them.
2. **`50_REBUILD/docs/` holds the evidence the model rests on, and the inspection ledger.** That is
   D33's test reports, the review reports, and the ledger: the committed record of which reserved
   seasons were scored.
   - Archiving them takes them out of the repository's tree. Every state-file reference to them
     would then point at a laptop-only folder.
   - **Recommended:** keep the documents tracked in `40_DOCS/model_evidence/`, with the reviews
     under it, and move the ledger to `00_STATE/`. Archive only the code and the outputs.

## Order of work

0. **Gate: fix the laptop's production age table first.**
   - `30_OUTPUT/WAR_with_age.csv` on the laptop has birthdates on 70.9% of rows. The cloud copy,
     the one uploaded after the 2026-09-28 fix, has 99.94%.
   - xNPV 1's comparable-player curve and xNPV 0's exit risk are both fitted on that table. So
     every laptop run since it reverted used a thinner comparables pool and exit tables missing
     exits.
   - Re-run `age_join.py`, then re-run the contract-status test and the confirmation (see the
     session log, 2026-10-02).
1. Promote the code. It is done when the new forecast file equals the harness's xNPV 1 forecasts on
   pages 2015-2021 to 1e-12.
2. Point `contract_npv.py` and `rfa_terminal_value.py` at it. Apply decision 2 (the first season
   uses xNPV 1's chance of playing) and decision 3 (the spread).
3. Run the dashboard refresh on the laptop. Compare the new spine with the archived xNPV 0 spine,
   contract by contract.
4. Move the documents and the ledger. Archive the rest of `50_REBUILD/` and xNPV 0's copies with
   `archive_from_git.py`.
5. Update CLAUDE.md (run order, folder map), the READMEs and MANIFEST. Grep for every old name:
   `SkaterProjector`, `project_contract`, `h_sk_for`, `ProductionChain`, `A1HingeExposureStatus`,
   `LEADER`, `50_REBUILD`. Every hit is either gone or points at the archive.

## Checks before calling it done

- **Bridge reproduces the harness.** The bridge's rate, games share and chance of playing equal the
  harness's xNPV 1 forecasts on the same rows.
- **Goalies unchanged.** Goalie values are byte-identical to the last xNPV 0 run (compare hashes, not
  sizes).
- **Spine comparison.** The count moved each way, the largest moves, and the totals.
- **Every artifact names its model.** The spine, panel and dashboard each record which model built
  them.
- **Run on the laptop**, the only machine with the contract export. `SCRIPT_VERSION` is printed on
  every run.
