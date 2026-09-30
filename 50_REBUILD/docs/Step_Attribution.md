# The current and rebuilt skater forecasts, piece by piece

**Correction, 2026-09-30.** The current model's exit risk on the 2015 and 2016 pages rested on a
star cell near zero. The pre-valuation window for those pages holds no star exit, and the fit
stopped at a star exit risk of about 1e-5. `exit_hazard.py` v1.3 fits such windows with Firth's
penalty. Rerun on the same rows, the current model's figures become:
- **Answerable rows:** RMSE 0.9033 (was 0.9036), MAE 0.5430, Brier 0.1917 (was 0.1918).
- **Full grid:** RMSE 0.8589 (was 0.8591).
- **Chance of playing alone swapped in:** -1.5% (was -1.6%).

The rebuilt model's margin stays -4.4%, and no reading below changes. The tables below keep the
v1.0 figures.

Run 2026-09-28. Test only: nothing adopted, no production file changed.
Script: `50_REBUILD/code/run_step_attribution.py` v1.0, on the forecast harness (development pages
2015-2021, valuation season to five seasons out, 40,510 forecasts from 1,609 players).

## The question

The scorecard (`Model_Scorecard.md`, 2026-09-24) compared the two whole forecasts before the current
model's two 2026-09-28 revisions: the aging curve and the exit hazard now use only seasons before each
valuation date, and the age table has the older careers restored. This run compares the rebuilt
forecast with the current model as it now runs, and splits the gap into its pieces.

In both models a season forecast is the chance he plays times his production if he plays
(`forecast_harness.py`: `p_play * rate_82 * gp_share`).
- **Current:** production if he plays is the 60/40 trailing total walked along the aging path, with a
  games share of one (`production_adapter.py`, "THE MAPPING"). The chance he plays is the exit-hazard
  survival factor, one in the valuation season.
- **Rebuilt:** production if he plays is the shrunk rate per 82 walked by the fitted aging equation,
  times its games-share forecast. The chance he plays comes from its participation model (at least one
  NHL game, `rebuild_config.PARTICIPATION_GP`).

So each piece can be swapped into the current model on its own and scored.

The rebuilt model is `A1HingeExposure`, the adopted leader's twin without contract data, because the
contract export is not in this container. On production's answerable rows the scorecard measured the
two at 0.8640 and 0.8645 season-WAR RMSE.

Guards:
- both models answer the same rows with the same realised targets;
- the current arm reproduces the harness's forecast for `ProductionChain` (v1.3), and the rebuilt arm
  reproduces it for `A1HingeExposure`;
- the current survival factor is exactly one in the valuation season;
- the age table production reads is logged by its real path.

The current arm reproduces the exit-hazard test's adopted figures: season-WAR RMSE 0.8591 (full grid)
and 0.9036 (answerable rows), Brier 0.2143 and 0.1918.

## Results, rows the current model answers (35,878 forecasts, 1,516 players)

"Lower in" counts the player resamples, of 2,000, in which the arm's error is below the current
model's.

| Season forecast | RMSE | Change | Lower in | MAE | Bias |
|---|---:|---:|---:|---:|---:|
| current | 0.9036 | | | 0.5431 | +0.0077 |
| current, rebuilt production if he plays | 0.8657 | -4.2% | 2000 | 0.5236 | -0.0687 |
| current, rebuilt chance of playing | 0.8895 | -1.6% | 2000 | 0.5229 | -0.0093 |
| rebuilt | 0.8634 | -4.4% | 2000 | 0.5081 | -0.0756 |

- The two swaps overlap. Taking production if he plays first gives -0.0379 RMSE, and the chance of
  playing then adds -0.0023. In the other order they give -0.0141, then -0.0261.
- The full grid (40,510, production plus its fallback): 0.8591 against 0.8144, -5.2%, 2,000 of 2,000.

Season-WAR RMSE by seasons ahead:

| | valuation | one | two | three | four | five |
|---|---:|---:|---:|---:|---:|---:|
| current | 0.9140 | 0.9216 | 0.9202 | 0.9175 | 0.8861 | 0.8532 |
| rebuilt | 0.8320 | 0.8728 | 0.8805 | 0.8849 | 0.8626 | 0.8434 |

**Production if he plays** (seasons played, predicted minus actual season WAR):
- **Valuation season** (starting points only, no aging applied): average miss 0.7401 current, 0.6816
  rebuilt, -7.9%, 2,000 of 2,000.
- **One to five seasons out:** 0.8556 and 0.8210, -4.0%, 2,000 of 2,000. The gap narrows from -5.1% one
  season out to -2.9% five out (1,982 of 2,000).

Production if he plays, valuation season, by the trailing-total tier:

| tier | seasons | current bias | rebuilt bias | current MAE | rebuilt MAE |
|---|---:|---:|---:|---:|---:|
| below 0 | 1,198 | -0.351 | +0.011 | 0.531 | 0.451 |
| 0 to 1 | 2,114 | +0.019 | +0.033 | 0.619 | 0.602 |
| 1 to 2 | 919 | +0.320 | -0.001 | 0.949 | 0.871 |
| 2 to 3 | 396 | +0.398 | -0.233 | 1.169 | 1.097 |
| 3+ | 198 | +0.920 | -0.207 | 1.471 | 1.218 |

**Chance he plays:** Brier 0.1918 current, 0.1359 rebuilt (-29.2%, 2,000 of 2,000). Mean predicted
against observed:

| | valuation | one | two | three | four | five |
|---|---:|---:|---:|---:|---:|---:|
| observed | 0.788 | 0.700 | 0.622 | 0.555 | 0.493 | 0.429 |
| current | 1.000 | 0.858 | 0.760 | 0.667 | 0.578 | 0.495 |
| rebuilt | 0.795 | 0.712 | 0.626 | 0.542 | 0.471 | 0.391 |

**Season-WAR bias for 3+ players, valuation season to five out:** current +0.96 to +0.22, rebuilt
-0.19 to -0.88.

## Reading

- The rebuilt forecast is more accurate than the current model as it now runs, at every horizon and
  in all 2,000 resamples. The margin is smaller than the scorecard's 5.4% mainly because the current
  model improved (0.9129 to 0.9036 with its revisions and the restored age table), while the rebuilt
  model barely moved (0.8645 to 0.8634).
- Most of the gap is production if he plays. Aging alone does not carry it: with the starting point
  held fixed, the two aging methods are within 0.2% on season WAR (`Aging_Method_Test.md`). So the gain
  sits mainly in the starting level and the games forecast.
- The chance of playing is much better calibrated. The current model treats the valuation season as
  certain, and 21% of these players did not play in it. But once production if he plays is swapped,
  the chance of playing adds little to season-WAR RMSE.
- Not scored here: dollars (which need the contract export) and the version that reads contract data.

## Error found in an earlier page

`Skater_Model_Decision.html` (2026-09-24) describes the rebuilt participation model as "Chance of a
10+ GP season". The code forecasts at least one game (`rebuild_config.PARTICIPATION_GP = 1`, set so that
participation and production condition on the same event). The HTML page is not edited here.
