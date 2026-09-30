# 50_REBUILD/code — what each file is

Index written 2026-09-30 from each file's docstring and its imports. When a file is added, add
its line here.

## The player model going forward: xNPV 1 (decision D33)

xNPV 1 is `star_candidates.XNPV1`. These files build it:

| File | What it does for xNPV 1 |
|---|---|
| `star_candidates.py` | `XNPV1 = candidate(gp=True, contracts=True)`. Adds two things to `ObviousFixes`: the games-share forecast that reads the player's level, and the contract-status switch |
| `obvious_fixes.py` | `ObviousFixes`: the fitted three-season start, the rebuilt games share and chance of playing, and the comparable-player aging with its fixes. The fixes are fitting on earlier seasons only, adding the yearly changes instead of multiplying, and entering departures at replacement |
| `ability_forecast.py` | The rebuilt model classes that `ObviousFixes` builds on (`A1HingeExposure`), and the anchors |
| `participation_model.py` | The chance of playing, which reads contract status when switched on |
| `contract_source.py` | Reads the PuckPedia exports (contract status, signing dates). Needs the export, so xNPV 1 runs in full only on the laptop |
| `production_adapter.py` | xNPV 0, the model running today in `20_CODE/`, on the harness (`ProductionChain`). It also puts `20_CODE/` on the path, where xNPV 1's aging curve (`aging_curve.py`) lives |

## Shared machinery (every runner uses some of it)

| File | What it is |
|---|---|
| `rebuild_config.py` | Paths, constants and guard rails. Every write goes through `out_path()`, which refuses anything outside `50_REBUILD/output/` |
| `player_season_table.py` | The one season table every rebuild script reads |
| `information_set.py` | What was knowable on a given date |
| `forecast_harness.py` | The scoreboard: valuation pages, horizons, realised outcomes |
| `aging_additive.py` | The fitted aging equation (the rebuilt model's aging; xNPV 1 does not use it) |
| `contract_price_model.py`, `production_currency.py` | What a player signs for, and forecast production in dollars |
| `npv_simulation.py`, `predictive_interval.py` | A contract's value as a distribution; point forecast to distribution |
| `control_years.py` | What a club still owns when the contract ends |
| `dollar_scoring.py` | Scoring contract valuations against realised outcomes, with player resampling |
| `goalie_season_table.py` | The goaltender panel |
| `repair_checks.py` | The standing guards, run as tests |

## Runners (`run_*.py`), by topic

Several runners are also imported as libraries, so none is moved. `run_skater_contract_test.Boot`
(the player resampler) and `run_npv_simulation` (the dollar machinery and `LEADER`) are the main
ones.

- **Harness and acceptance:** `run_phase0_acceptance`, `run_bakeoff`, `run_leakage_tests`,
  `run_uncertainty`, `run_coverage_decomposition`, `run_stress_tests`, `run_model_scorecard`.
- **Market and dollars:** `run_phase4_decisions`, `run_curvature_test`, `run_surplus`,
  `run_npv_simulation`, `run_control_years`, `run_valuation_integration`,
  `run_valuation_sensitivity`, `run_player_comparison`, `run_production_reconciliation`,
  `run_skater_dollar_scoring`, `run_dollar_rescore`.
- **Skater participation and contracts:** `run_contract_ablation`, `run_skater_contract_test`,
  `run_status_carry_sensitivity`, `run_contract_status_test` (laptop; the xNPV 1 evidence),
  `run_participation_drift_test`.
- **Aging:** `run_aging_choices_test`, `run_aging_method_test`, `run_exit_hazard_window_test`,
  `run_step_attribution`, `run_obvious_fixes_test`.
- **Stars:** `run_star_definition`, `run_star_residual`, `run_star_walk_diagnostic`,
  `run_star_bias_test`, `run_star_late_test`.
- **Goalies:** `run_goalie_bakeoff`, `run_goalie_rate`, `run_goalie_participation`,
  `run_goalie_participation_top`, `run_goalie_price_line`, `run_goalie_control_years`.
- **xNPV 1 follow-ups:** `run_xnpv1_holdout` (laptop; a single confirmation score on the 2022-2025
  pages).

## `reviews/`

These are the independent reviews' one-shot audit scripts (`review_*.py`). Each is paired with a
report in `../docs/reviews/`. Most run against an isolated checkout under `50_REBUILD/output/`. The
repo root is `Path(__file__).parents[3]`.
