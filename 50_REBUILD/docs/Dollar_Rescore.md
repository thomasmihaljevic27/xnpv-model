# Contract dollars re-scored after the 28 September fixes

Run 2026-09-30 on Thomas's laptop (`50_REBUILD/code/run_dollar_rescore.py` v1.1, Python 3.14.3,
`exit_hazard.py` v1.3). Test only: nothing adopted. Figures are copied from the run log
(`50_REBUILD/output/dollar_rescore_run_log.txt`, gitignored).

## What was scored

Five forecasts, each priced over each contract's term on one price line, against the realised
production priced on the same line. The realised target is asserted identical across forecasts.
The sample is development start years: 1,176 contracts that have ended, 767 players; 1,111 of them
are contracts the current model answers itself.

| Forecast | What it is |
|---|---|
| current | the live chain as it now runs: aging curve and exit risk fitted on seasons before each valuation, corrected age table |
| obvious fixes | the current model's comparable-player aging with every listed fix (`Obvious_Fixes_Test.md`) |
| fixes + games | obvious fixes with the games-share forecast reading the player's level (`Star_Bias_Test.md`, change G) |
| adopted | the rebuilt model reading contract status |
| previous | the rebuilt model without contract data |

**Guard: the adopted and previous rebuilt models reproduce their 2026-09-24 figures exactly.** On the
answerable contracts, adopted line, point valuation, they are 3.614 / 1.761 / -0.581 and 3.630 /
1.762 / -0.628. Only the current model moved, and the two new forecasts are new.

## Results

Primary: the adopted model's line, the 1,111 contracts the current model answers, point valuations,
$M per contract. "Lower in" counts player resamples, of 2,000, with lower error.

| Forecast | RMSE | MAE | Bias | vs current: squared / absolute lower in | vs adopted: squared / absolute lower in |
|---|---:|---:|---:|---|---|
| current | 3.681 | 1.865 | -0.179 | | |
| obvious fixes | 3.616 | 1.764 | -0.614 | 1,437 / 1,972 | 888 / 774 |
| **fixes + games** | **3.555** | **1.753** | -0.571 | 1,749 / 1,991 | 1,870 / 1,563 |
| adopted | 3.614 | 1.761 | -0.581 | 1,429 / 1,969 | |
| previous | 3.630 | 1.762 | -0.628 | 1,347 / 1,960 | |

The other three tables give the same ordering.
- **All 1,176 contracts, adopted line:** current 3.580, obvious fixes 3.515, fixes + games 3.456,
  adopted 3.513. Fixes + games against adopted: 1,869 / 1,620.
- **The current model's line (the sensitivity):** fixes + games has the lowest squared error. Against
  adopted it is lower in 1,914 (all contracts) and 1,917 (answerable). Against current it is lower in
  1,949 and 1,958. It has the lowest absolute error in every table (against current 2,000 of 2,000 on
  that line).

By term, adopted line, all contracts (RMSE / bias, $M):

| Term | Contracts | current | obvious fixes | fixes + games | adopted |
|---|---:|---|---|---|---|
| 1-2 years | 929 | 1.56 / -0.08 | 1.47 / -0.20 | 1.47 / -0.19 | 1.47 / -0.17 |
| 3-5 years | 206 | 6.31 / +0.22 | 6.06 / -1.22 | 5.94 / -1.07 | 6.06 / -1.15 |
| 6-8 years | 41 | 10.62 / -4.09 | 10.98 / -6.00 | 10.78 / -5.81 | 11.00 / -6.01 |

## Reading

- **The current model's revisions cost it a little in dollars.** On the answerable contracts its
  squared error went from 3.648 (2026-09-24) to 3.681, and its absolute error from 1.854 to 1.865.
  The revisions change three things at once (the aging window, the age table, the exit-risk window),
  and this run does not split them. As with the aging look-ahead in season WAR, part of the old
  accuracy may have come from seasons no team had seen; this run cannot show how much.
- **Comparable-player aging and the fitted equation do not separate in dollars.** Obvious fixes
  against adopted: 3.616 against 3.614, obvious fixes lower in 888 of 2,000. So the season-level tie
  holds in dollars too. The obvious-fixes model reads no contract data; adopted does.
- **The games-share change carries into dollars.** Fixes + games has the lowest squared and absolute
  error of the five on every table. Against adopted it is lower in 1,869-1,917 of 2,000. That is
  short of the 1,950 used for the season-level rule, so not decisive, but it is consistent across
  lines and samples.
  - **It is not a comparables-against-equation result.** The games change was not added to the
    adopted rebuilt model here, and on season WAR it helped the rebuilt model just as much. Fixes +
    games against obvious fixes (3.555 against 3.616) is the games change's own dollar effect.
- **Long deals are where every new forecast is weakest.** On the 41 contracts of six to eight years,
  the current model has the lowest error (10.62) and the smallest under-valuation (-4.09 over the
  term). The new forecasts under-value them by $5.8M-6.1M. This is the star under-forecast showing in
  dollars. With 41 contracts it is thin evidence, but it is the direction the star tests predicted.
- **Every forecast under-values on average.** The current model is closest (-0.18) because its high
  forecasts for good players offset its low ones elsewhere. The new forecasts sit at -0.57 to -0.63.

## Not done

- The rebuilt model with the games change (`star_candidates.RebuiltGamesLevel`) in dollars, which is
  the fair test of comparables against the equation once both carry it.
- Splitting the current model's dollar change into its three revisions.
- The 2022-2025 pages.
