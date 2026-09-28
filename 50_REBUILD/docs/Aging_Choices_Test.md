# Hand-set choices in the aging curves, scored

Run 2026-09-28. Test only: no production file changed, no locked decision opened, nothing adopted.
Scripts: `20_CODE/aging_arbitrary_choices_test.py` v1.0 (the current curve on held-out careers) and
`50_REBUILD/code/run_aging_choices_test.py` v1.0 (both models on the rebuild's forecast harness).
`50_REBUILD/code/aging_additive.py` v1.5 exposes three options for the second script; at their
defaults it fits exactly the committed curve on every development page (asserted).

## Summary

The current aging curve (`20_CODE/aging_curve.py`) finds comparable players by a weighted
distance, turns distance into a weight with a bell-shaped formula whose width is "one yardstick",
and blends the comparables with a league average carried as ten units of weight. Most of those
settings were chosen by hand. The rebuilt model's aging curve (`50_REBUILD/code/aging_additive.py`)
has none of that machinery and already refits at each valuation date, but it has three hand-set
choices of its own. Each was changed one at a time and scored against the same outcomes.

1. **Almost none of the hand-set choices matters.** Of the current curve's nineteen single changes
   (the look-ahead aside), none moves average error by more than 1% on any of the four held-out comparisons. The
   rebuilt curve's five changes all stay within 0.17% on its primary score.
2. **The one choice that does matter is the look-ahead.** The current curve builds its comparables,
   its z-score means and SDs, its yardstick and its league-average curves from every season in the
   file, including seasons played after the valuation date. Rebuilt from only the seasons finished
   before each valuation date, the live chain's season-WAR error rises by **1.7% in RMSE**. That
   1.7% is accuracy the current model gets from information no team had.
3. **Similarity weighting earns its place, and a narrower weighting would do slightly better.**
   Weighting every same-age player equally is worse in all four held-out comparisons (0.47%-0.94%).
   Halving the yardstick is better in all four (0.19%-0.60%), which agrees with the 2026-09-13
   comparables-limit test.
4. **The weight of ten on the league average is arbitrary but harmless.** Any value from near zero
   to twenty gives the same error to within 0.06%. A fixed 5% league share instead is no better
   (within 0.07% held out) and slightly worse in the live chain (0.20% in RMSE).
5. **The rebuilt model's recorded choices hold up.** The recorded settings are a cubic in age,
   ages 19-39, and season pairs weighted by games. No alternative beats them on the primary score
   by more than 0.013%.
6. **Across models,** on the 35,878 rows the current chain answers itself, the rebuilt model's
   season-WAR RMSE is 5.2% below the current chain as it runs, and 6.8% below the current chain
   with its look-ahead removed.

## What the current curve's comparables pool is

Read from the production fit (`AgingModel` on `30_OUTPUT/WAR_with_age.csv`, which reproduces the
recorded yardstick of 2.5264 and pool of 7,531 exactly):

| | Forwards | Defence |
|---|---:|---:|
| Profiles in the pool (two consecutive 20+ game seasons, one entry per such window) | 4,950 | 2,581 |
| Distinct careers behind them | 766 | 406 |
| Profiles drawn at random for the yardstick (seed 0) | 1,200 | 1,200 |
| Pairs measured | 719,400 | 719,400 |
| Pairs that are one player's own two seasons | 1,280 | 2,362 |
| Median distance, all sampled pairs | 2.4852 | 2.5651 |
| Median distance, a player's own two seasons | 1.9100 | 2.0539 |

The yardstick is the median of the two positions' distances pooled: **2.5264**. Every pair in the
pool, with no sampling, gives 2.5339; removing a player's pairs with himself gives 2.5277. Twenty
different random draws give 2.5039 to 2.5693, so the sampling itself moves the yardstick more than
either change does.

A player appears once for every qualifying two-season window he has: 6.4 times on average and up
to 18 times. The pool holds only players with a birthdate in the age table, and that table has no
match from the Elite Prospects file (every one of its match types is exact, fuzzy, manual or
hand-fixed): 1,278 of 3,199 skaters have no age. Coverage is 17% of 2007-08 season rows, 60% of
2014-15 and 100% from 2018-19. **The pool is therefore weighted toward careers that lasted into
the years the contract export covers.** That is a selection on survival, and it was not scored here.

## The current curve on held-out careers

Five whole-career folds (the comparables-limit test's seed and folds). The player being forecast is
never in his own training pool and sees only his own seasons up to the forecast age. Two modes:

- **Full-era training**: the training careers' every season. Forecasts one to six seasons ahead;
  26,251 forecast-outcome pairs from 1,056 players.
- **Historical training**: only seasons up to the forecast year, forecast years 2017-2022. Forecasts
  one to three seasons ahead; 8,303 pairs from 841 players.

Two outcomes:
- **WAR per 82**: the rate the curve predicts.
- **Season total**: production's ratio applied to a 60/40 trailing season total. 19,794 and 5,258
  pairs.

The score is mean absolute error, as in the two earlier aging tests. The interval resamples
careers, 2,000 draws.

Each cell is the **change in mean absolute error against the current curve, in percent**, negative
meaning lower error. "Better in" counts the resamples, of 2,000, in which the change has lower
error, in the full-era WAR-per-82 comparison.

| Change | Full era, WAR/82 | Full era, season total | Historical, WAR/82 | Historical, season total | Better in |
|---|---:|---:|---:|---:|---:|
| **Yardstick pool** | | | | | |
| every pair, no sampling | -0.004 | -0.003 | -0.006 | -0.001 | 2000 |
| a player's own pairs removed | +0.001 | +0.001 | +0.001 | +0.000 | 0 |
| **Forward and defence yardstick** | | | | | |
| one yardstick per position (forwards 2.485, defence 2.565) | -0.008 | -0.003 | -0.008 | -0.001 | 2000 |
| **Feature weights** (yardstick rebuilt on each scale) | | | | | |
| all eight measures weight 1 | +0.22 | +0.01 | +0.36 | +0.01 | 0 |
| style shares removed | -0.11 | +0.02 | -0.22 | +0.05 | 2000 |
| trend removed | -0.06 | -0.17 | -0.07 | -0.04 | 1871 |
| level alone | +0.41 | -0.85 | +0.17 | -0.28 | 0 |
| **Weight formula** (u = distance in yardsticks) | | | | | |
| every same-age comparable weight 1 | +0.75 | +0.61 | +0.94 | +0.47 | 0 |
| 1 - (u/2)^2, zero beyond two yardsticks | +0.04 | +0.04 | +0.01 | +0.02 | 54 |
| (1 - (u/2)^3)^3, zero beyond two yardsticks | -0.23 | -0.19 | -0.34 | -0.09 | 2000 |
| 1 / (1 + u^2), heavier tails | +0.08 | +0.06 | +0.13 | +0.05 | 0 |
| bell curve, yardstick doubled | +0.49 | +0.42 | +0.63 | +0.30 | 0 |
| bell curve, yardstick halved | -0.43 | -0.44 | -0.60 | -0.19 | 2000 |
| **League-average weight** (production 10) | | | | | |
| 0.01 | +0.02 | -0.00 | +0.04 | +0.01 | 559 |
| 5 | -0.02 | -0.03 | -0.02 | -0.02 | 1752 |
| 20 | +0.04 | +0.05 | +0.06 | +0.05 | 26 |
| 50 | +0.16 | +0.16 | +0.20 | +0.16 | 2 |
| a fixed 5% share | +0.04 | +0.01 | +0.07 | +0.01 | 189 |
| a fixed 10% share | +0.07 | +0.03 | +0.10 | +0.02 | 19 |

What the table does and does not show:

- **Square roots of the weights** are not scored because they are not a choice. Scaling each z-score
  by the square root of its weight before squaring gives exactly the weighted squared difference.
  The weights themselves are the choice, and no alternative set wins on both outcomes. Removing the
  style shares helps the rate slightly and hurts the season total slightly. Level alone does the
  reverse, by more. The equal-per-group weights are not beaten across the board.
- **The formula's width matters more than its shape.** The two narrower versions are better in all
  four comparisons (the halved bell curve, and the one that drops to zero at two yardsticks). The
  two wider versions are worse in all four (the doubled bell curve, and the heavy-tailed one). The
  production yardstick is the median distance between ALL pairs of profiles, so almost every
  same-age player carries real weight. In the full-era fit, the median effective number of comparables at the
  start of the walk is about 80%-95% of the median number eligible, by tier.
- **The league average's share grows along the walk.** Its median share of the comparable estimate is
  6%-8% at the start and 12%-14% at the last projected season (full-era training). Under historical
  training it is 11%-14% at the start and 17%-23% at the end, because fewer comparables have both
  seasons of each later step. Its size is set in weight units, so any change to the yardstick or
  the pool changes its share silently. A fixed share avoids that, but scored no better.
- Nineteen changes are compared, plus the look-ahead. Each is one change, none is tuned and no combination is scored, so a
  small gain by one of them is weak evidence on its own. The 55% kept share of own form was chosen
  with the production comparables and is held fixed. A loss rules out the construction tried, not
  the idea behind it.

### The look-ahead, held out

In the historical mode, the current rule with the full-era pool (other players' later seasons
included) is compared with the same rule on seasons finished by the forecast year. The full-era
version has lower error by **0.57% on WAR per 82** (2,000 of 2,000 resamples) and **0.28% on the
season total** (1,748 of 2,000; the interval includes zero). By seasons ahead, on WAR per 82:
0.57%, 0.46% and 0.70% at one, two and three seasons. It moves the average forecast by 0.067 WAR per
82. One change here moves four things, because production builds all four from the whole file:
the comparables, the z-score means and SDs, the yardstick, and the league-average curves.

## Both models on the forecast harness

Development pages 2015-2021, horizons from the valuation season to five seasons out. 40,510
forecasts from 1,609 players. The score is season WAR (rate x games share x participation), with
squared error primary. "Lower" is the share of 2,000 player-resamples in which the change's error
is lower.

**Ages.** Both models take ages from one birthdate table: production's age join first, then the
Elite Prospects file for the 1,276 keys it lacks, by the rule the rebuild's own merged table uses.
That covers 99.9% of season rows. The current chain's aging curve is fitted on production's own age
file, as production runs it.

### The rebuilt model's hand-set choices

The rebuilt model here is the adopted leader without contract data. The adopted leader differs
from it only in participation, which reads the confidential contract export; ability, aging, rate
and games share are identical. Every change below shares that participation exactly.

| Change | Season WAR RMSE | Change | Lower | MAE change | Lower | Stars' WAR bias, five out |
|---|---:|---:|---:|---:|---:|---:|
| recorded: cubic in age, ages 19-39, pairs weighted by games | 0.8157 | | | | | -0.882 |
| quadratic in age | 0.8155 | -0.013% | 1268 | +0.15% | 2 | -0.887 |
| quartic in age | 0.8165 | +0.10% | 14 | +0.13% | 7 | -0.872 |
| ages 20-38 | 0.8156 | -0.008% | 1758 | -0.014% | 1983 | -0.882 |
| ages 18-40 | 0.8156 | -0.002% | 1424 | 0.000% | 953 | -0.883 |
| every season pair weighted equally | 0.8170 | +0.17% | 0 | -0.06% | 1942 | -0.899 |

On every page, the degree and age-band changes fit the recorded curve's exact rows and weights,
and the equal-weight change fits the same rows with every weight one (asserted). None of them
touches the stars' under-forecast. Not scored, and why:
- **The age centring at 27** is a change of basis in a fit that has every power of age and the
  level-by-age term, so it cannot move a forecast.
- **The level terms, the survivorship imputation, the imputed level and recency weighting** were
  each scored in earlier runs.
- **The 20-game qualifying rule** belongs to the whole chain, not to aging.

### The current model in the live chain

The current chain is production's own forecast (aging path and survival) run through the adapter.
Where production has no anchor, the adapter carries the trailing total flat. The table shows both
the full grid and the 35,878 rows production answers itself, same rows for every change.

| Change | RMSE, full grid | Change | Lower | RMSE, rows production answers | Change | Lower |
|---|---:|---:|---:|---:|---:|---:|
| current, as it runs | 0.8675 | | | 0.9120 | | |
| aging pool from seasons finished before the page | 0.8825 | +1.73% | 0 | 0.9281 | +1.77% | 0 |
| one yardstick per position | 0.8675 | -0.001% | 1295 | 0.9120 | -0.001% | 1273 |
| yardstick from every pair | 0.8675 | +0.002% | 0 | 0.9120 | +0.002% | 0 |
| league average a fixed 5% share | 0.8692 | +0.20% | 0 | 0.9139 | +0.20% | 0 |
| every same-age comparable weight 1 | 0.8714 | +0.45% | 0 | 0.9162 | +0.46% | 0 |

The wrapper with no change reproduces the live chain's forecasts exactly on all 40,510 rows
(asserted). The pre-valuation change refits only the aging curve. The exit-hazard table the chain
multiplies by is still production's full-era one. Removing the look-ahead also shrinks the chain's
over-forecast of three-win-and-up players five seasons out, from +0.484 to +0.426 WAR on the rows
production answers.

### Across models, rows production answers (35,878)

| | Season WAR RMSE | Against the current chain |
|---|---:|---:|
| current chain, as it runs | 0.9120 | |
| current chain, aging pool from seasons before the page | 0.9281 | +1.8% |
| rebuilt model (no contract data) | 0.8647 | -5.2% (2,000 of 2,000 lower) |

## Limits

- Development pages 2015-2021 only. About thirty earlier variants inspected these pages, so they
  are reused, not fresh. The held-back pages 2022-2025 were not scored.
- The held-out test has no exit hazard and no dollars. The harness has no dollars. Nothing here
  prices a contract.
- Each change is scored alone. A setting that loses alone could still help in combination, and
  none was searched.
- The age table's missing Elite Prospects matches bias the current pool toward long careers, and
  that was not scored.

## Files

Generated and gitignored:
- `30_OUTPUT/aging_arbitrary_choices_test_{design,run}.json`
- `_predictions.csv`, `_origins.csv`, `_summary.csv`, `_fold_yardsticks.csv`, `_league_share.csv`
  (same prefix)
- `50_REBUILD/output/aging_choices_{summary,forecasts}.csv`
- `aging_choices_run_log.txt` and `aging_choices_birthdates.csv` (same folder)
