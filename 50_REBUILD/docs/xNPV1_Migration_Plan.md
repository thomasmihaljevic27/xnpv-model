# Moving xNPV 1 into production: the plan and the decisions it needs

Written 2026-09-30, after decision D33. Nothing in this plan is built yet. Every mechanism below was
read from the script named beside it.

## What changes and what does not

**Changes: the skater forecast only.** Production values a skater contract in
`20_CODE/contract_npv.py` (`NPVEngine._npv_skater`). For each season k of the contract it computes:

- **value.** The projected WAR comes from `skater_forward_projection.SkaterProjector.project_contract`.
  That WAR is priced at the Stage 3 rate on the ex-ante cap path, and its expectation is floored at
  the league minimum (`expected_floored_value`).
- **survival.** A chained factor, S_k = S_{k-1} x (1 - h). The hazard h is read from this page's
  exit-hazard table (`h_sk_for(t0)`), indexed at k-1. S_0 = 1.
- **present value.** (S_k x value − cap hit) / 1.03^k.

The RFA terminal value (`rfa_terminal_value.py`) is added to this. It takes its expiry-year WAR from
the same `SkaterProjector`.

xNPV 1 replaces two inputs:
1. **The projected WAR** becomes xNPV 1's rate per 82 games x its games share: the WAR the player
   produces if he plays.
2. **The survival factor** becomes xNPV 1's chance of playing that season, p_play(k). This is one
   probability per season, read directly, not chained (`participation_model.py`: "each future season
   gets its own probability rather than a survival chain"). Its product with (1) is exactly the
   harness's expected WAR, `p_play x rate_82 x gp_share`, so production would price the quantity
   that was scored.

**Unchanged:**
- the Stage 3 price per win;
- the 3% cap path and discount (D11, D17);
- the league-minimum floor (D10);
- the cap hit charged whether or not the player plays (D16(i));
- the extension chain (D28);
- the RFA terminal value's qualify-rate chain (D13, D14(c));
- the whole goalie branch;
- the draft pillar.

The dashboard and the panel follow automatically, because both call `NPVEngine.npv`
(`player_dashboard.py`, `contract_npv_panel.py`).

## The recommended route

1. **Add a bridge script, `20_CODE/xnpv1_forecast.py`.**
   - It fits xNPV 1 (`star_candidates.XNPV1`) once per valuation page, on seasons before the page:
     the same rolling fit the harness uses.
   - For every skater it writes `30_OUTPUT/xnpv1_forecasts.csv`: player, page, as-of date, season
     ahead k (0-12), rate per 82, games share, chance of playing, and the WAR-if-plays.
   - Every row carries `model = "xNPV 1"` and the code versions that built it.
   - For in-season as-of dates it uses the signing-dated chance of playing (`p_play_signed`), which
     the dollar scoring already uses.
2. **Add a switch to `contract_npv.py`**, `SKATER_MODEL = "xNPV 1"` or `"xNPV 0"`.
   - Under xNPV 1 the skater branch reads WAR and survival from the bridge file instead of from
     `SkaterProjector` and the exit hazard.
   - The RFA terminal value reads its expiry-year WAR from the same file.
   - xNPV 0 stays selectable as the reported sensitivity.
   - `contract_npv_spine.csv`, the panel and the dashboard gain a `model` column.
3. **Add the bridge to the dashboard launcher.** `dashboard_refresh.py`'s `CHAIN` needs the bridge
   before `contract_npv.py`, or the launcher will not run it.
4. **Switch the rebuild's simulation leader** (`run_npv_simulation.LEADER`) to `XNPV1` as a
   **separate** step. 18 other runners and `repair_checks.py` read `LEADER`, so every result they report
   would move. The xNPV 1 class already supports the calls the simulation makes: `predict_beyond_fit`
   and `p_play_signed` to nine seasons ahead were checked on four pages on 2026-09-30.

The bridge writes a file, rather than having `contract_npv.py` import the rebuild code, for three
reasons:
- production stays readable on its own;
- the forecasts can be hashed and checked;
- a failed bridge run leaves the last good file in place instead of half a chain.

## Decisions needed before building

1. **Where xNPV 1's code lives.**
   - **(a) Recommended for now:** the bridge imports it from `50_REBUILD/code/`. This is quick, and
     it means the rebuild tree is no longer experimental. The README and CLAUDE.md would say so.
   - **(b)** Copy the modules into `20_CODE/`. That is `star_candidates`, `obvious_fixes`,
     `ability_forecast`, `participation_model`, `player_season_table`, `information_set`,
     `contract_source`, `rebuild_config` and `forecast_harness`: about 5,000 lines. It is cleaner,
     but two copies can drift apart.
2. **The valuation season's survival.**
   - Production sets S_0 = 1: the current season is not discounted for exit.
   - xNPV 1 gives a chance of playing for the current season, p_play(0), which the harness scores.
   - Using p_play(0) is consistent with what was scored. Keeping 1 is consistent with the "he is on
     the roster on 1 July" convention.
   - This changes every contract's first season a little.
3. **The spread behind the league-minimum floor.** The floor's expected value uses a projection
   spread taken from xNPV 0's own backcast (`_BACKCAST_MAE_36`: 0.522 / 0.735 / 0.803 WAR at
   k = 1 / 2 / 3, held flat after 3). Options:
   - re-derive it from xNPV 1's harness errors among seasons played (recommended);
   - use the rebuild's predictive interval;
   - keep xNPV 0's figures as a stated placeholder.
4. **The contract export.** xNPV 1 reads contract status, so the bridge runs only where the
   PuckPedia export is (the laptop). Production already needs the export for signing dates, so this
   adds no new dependency. It does mean the cloud can never rebuild the spine.

## Checks before calling it done

- **Bridge reproduces the harness.** For pages 2015-2021, the bridge's rate, games share and chance
  of playing equal the harness's xNPV 1 forecasts on the same rows, to 1e-12.
- **xNPV 0 is untouched.** With the switch on xNPV 0, `contract_npv_spine.csv` hashes identical to
  the current file (compare hashes, not sizes).
- **Dollar agreement.** With the switch on xNPV 1, compare the spine against the xNPV 0 spine
  contract by contract (`npv_spine_compare.py`). Report the count moved each way and the largest
  moves.
- **Nothing still reads the old model.** Search by name for the old model classes and functions:
  `SkaterProjector`, `project_contract`, `h_sk_for`, `A1HingeExposureStatus` and `LEADER`. Every
  hit is either behind the switch or labelled as the xNPV 0 sensitivity. Don't search only for
  the switch.
- **Every artifact names its model.** The spine, panel, dashboard and simulation outputs each
  record which model built them, and the integration step refuses to join two artifacts that name
  different models.
- **Run the standing guards.** `repair_checks.py` and each production script's reproduction guards
  pass. `SCRIPT_VERSION` is printed on every run.
- **Test on the laptop.** Run the dashboard refresh there, since it is the only machine with the
  export.
