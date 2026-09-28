# The exit hazard fitted only on what each valuation date could know

Run 2026-09-28. Test only: no production file changed, nothing adopted.
Script: `50_REBUILD/code/run_exit_hazard_window_test.py` v1.0, on the rebuild's forecast harness
(development pages 2015-2021, valuation season to five seasons out, 40,510 forecasts from 1,609
players).

## The question

The pricing chain multiplies each future season by the chance the player is still in the league.
That chance comes from one exit-hazard table, `20_CODE/exit_hazard.py`. It is estimated on every
transition from 2018 to 2024 (a player "exits" when he has no NHL game the next season) and applied
to every valuation date. So a 2018 valuation reads exits that happened in 2019-2025, the same
look-ahead the aging curve's revision removed on the same day.

`exit_hazard.py` starts its window at 2018 on purpose. The age table was essentially complete only
from 2018, and the players it missed were the pre-2018 retirees, so older years would undercount
exits. Since 2026-09-28 the age table carries the Elite Prospects ages (99.9% of season rows), and
that reason no longer holds.

## What was compared

Every arm is the live chain as now adopted (aging curve fitted per valuation page, corrected age
table). Only the hazard table changes.

| Arm | Transitions the hazard is fitted on |
|---|---|
| current | 2018-2024, for every page |
| pre-valuation, expanding | 2007 up to two seasons before the page (the exit season finished before the page) |
| pre-valuation, rolling | the seven transition years ending two seasons before the page, production's own window width |
| all seasons | 2007-2024 for every page. It still sees the future, but separates "more history" from "no future" |

Guards:
- An arm set to 2018-2024 reproduces the live chain exactly on all 40,510 forecasts.
- Every arm has the live chain's rate and games share on every row, so any change in season WAR
  comes from the hazard alone.
- The hazard's own checks (no cell at exactly 0 or 1, calibration to the observed exit rate) ran on
  every fit.

Exit rates in the windows:
- **The 2007-2013 to 2007-2019 windows:** 12.7%-13.1% a year.
- **The rolling windows:** 12.3%-12.8%.
- **Production's 2018-2024 window:** 10.6%.

## Results

The Brier score is the squared error of the predicted chance of playing, and lower is better.
"Lower in" counts the resamples of 2,000 players in which the arm's error is lower than the current
chain's.

**Full grid (40,510 forecasts):**

| Arm | Brier | Lower in | Season-WAR RMSE | Lower in | WAR bias | Mean predicted chance of playing |
|---|---:|---:|---:|---:|---:|---:|
| current | 0.2275 | | 0.8619 | | +0.025 | 0.745 |
| pre-valuation, expanding | 0.2143 | 2000 | 0.8591 | 2000 | +0.015 | 0.715 |
| pre-valuation, rolling | 0.2156 | 2000 | 0.8593 | 2000 | +0.017 | 0.720 |
| all seasons | 0.2181 | 2000 | 0.8599 | 2000 | +0.019 | 0.726 |

**Rows the chain answers itself (35,878):**
- Brier: 0.2019 current, 0.1918 expanding, 0.1927 rolling, 0.1945 all seasons.
- Season-WAR RMSE: 0.9061, 0.9036, 0.9038, 0.9043.
- Every arm is lower than current in 2,000 of 2,000 resamples on both scores.

**The chance of playing, predicted minus observed, full grid:**

| Arm | 1 season out | 3 seasons out | 5 seasons out |
|---|---:|---:|---:|
| current | +0.232 | +0.187 | +0.140 |
| pre-valuation, expanding | +0.214 | +0.148 | +0.088 |

Every arm over-predicts playing at every horizon; the pre-valuation hazard over-predicts least.

## Reading

- **Removing the look-ahead does not cost accuracy here; it gains it.** The expanding pre-valuation
  hazard cuts the Brier score 5.8% and season-WAR RMSE 0.32% on the full grid, and both hold in
  every resample.
- **Two things change at once, and the all-seasons arm helps split them.**
  - Adding 2007-2017 while keeping the future: Brier from 0.2275 to 0.2181.
  - Then removing the future: from 0.2181 to 0.2143.
  - Both steps lower the error. This does not show why. Older windows have higher exit rates, and
    the chain over-predicts playing, so a higher exit rate would help whether or not it is the
    reason.
- **Expanding against rolling.** The two pre-valuation windows are close: expanding is lower on both
  scores and on both samples, by 0.0013 Brier and 0.0002 RMSE on the full grid.
- **Scope.** This tests the participation piece only. No dollars were priced, and the goalie hazard
  is not tested.

## Adopted 2026-09-28

Thomas adopted the expanding window.
- **Production.** `contract_npv.py` v1.5 fits the skater table per valuation page on transitions
  2007 to two seasons before the page (`exit_hazard.pre_valuation_window`). `h_sk_for(None)` keeps
  the 2018-2024 table for recorded experiments only.
- **Harness.** `production_adapter.py` v1.3 follows production. The runner v1.1 asserts that
  production as adopted equals the pre-valuation arm on all 40,510 forecasts, and the old table,
  now an arm, reproduces v1.0's figures.
- **Checked.** The method was lifted from `contract_npv.py` and checked alone: for every page from
  2018 to 2026 it builds exactly the table the shared rule builds.
- **Not changed.** The goalie table (still 2018-2024; untested) and the control-year chain, which
  never used the hazard.
- **Not yet run.** `contract_npv.py` and the panel need the contract export, so the re-run is owed
  on the laptop.
