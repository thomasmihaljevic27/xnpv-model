# Hand-set choices in the aging curves, scored

Run 2026-09-28. The tests change no production file. Two results were adopted the same day (see "Adopted 2026-09-28").
Scripts: `25_TESTS/aging_arbitrary_choices_test.py` v1.0 (the current curve on held-out careers),
`25_TESTS/aging_ep_pool_test.py` v1.0 (the missing older careers, held out),
`25_TESTS/aging_weight_sweep_test.py` v1.0 (the four group weights, swept) and
`50_REBUILD/code/run_aging_choices_test.py` v1.2 (both models on the rebuild's forecast harness).
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
6. **The current curve's pool is missing about 1,276 older careers, and that matters more than any
   hand-set choice.** `age_join.py` reads the Elite Prospects birthdates from
   `OUTPUT_DIR/ep_out/ep_birthdates.csv`, but the file sits in `10_SOURCE/`, so the step that ages
   pre-2018 retirees is skipped without a warning. With those careers added, the live chain's
   season-WAR RMSE falls **1.4%**. With the careers added AND the pool limited to seasons before
   each valuation date, it is **0.6% below the current chain as it runs**. That is the
   look-ahead-free version, and it beats today's figure.
7. **Across models,** on the 35,878 rows the current chain answers itself, the rebuilt model's
   season-WAR RMSE is:
   - 5.2% below the current chain as it runs;
   - 6.8% below it with the look-ahead removed;
   - 4.6% below it with the older careers added and the look-ahead removed.
8. **Equal group weights are neither best nor beaten.** Across 65 proportions of the four group
   weights, equal weights rank 28th to 32nd on each comparison. No proportion moves error by more
   than 0.4%, and the best set on the primary comparison fails on the season totals.

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
the years the contract export covers.** That is a selection on survival; it is scored below
("The missing older careers").

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
| older careers added to the pool | 0.8554 | -1.39% | 2000 | 0.8990 | -1.42% | 2000 |
| older careers added, pool from seasons finished before the page | 0.8626 | -0.56% | 1972 | 0.9068 | -0.58% | 1966 |

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
| current chain, older careers added | 0.8990 | -1.4% |
| current chain, older careers added, pool from seasons before the page | 0.9068 | -0.6% |
| rebuilt model (no contract data) | 0.8647 | -5.2% (2,000 of 2,000 lower) |

## The missing older careers

**Why they are missing.**
- `age_join.py` Pass 4 fills the players the contract export never had (mostly pre-2018 retirees)
  from the Elite Prospects scrape.
- It reads that scrape from `OUTPUT_DIR/ep_out/ep_birthdates.csv` (`EP_BIRTHDATES_PATH`).
  `10_SOURCE/ep_birthdates.csv` exists; that path does not, in this container or in the synced
  Dropbox copy.
- The pass checks `os.path.exists()` and skips. The live table carries no "ep" match type.
- The 26 hand corrections (`EP_BIRTHDATE_OVERRIDES`) are hard-coded, so they were still applied,
  which is why the table looks partly Elite-Prospects-aware.

**The table, rebuilt by rule.** `aging_ep_pool_test.py` applies Pass 4 and the override pass to the
live table. It does not re-run `age_join.py`, which needs the confidential contract export.
- Every row that already had an age keeps it exactly (asserted).
- 1,276 players gain a birthdate and 2 remain unmatched.
- Season-row coverage rises from 70.9% to 99.9%.

| | Live table | Older careers added |
|---|---:|---:|
| Pool profiles, forwards / defence | 4,950 / 2,581 | 6,600 / 3,457 |
| Careers in the pool | 1,172 | 1,813 |
| Yardstick (pooled; forwards / defence) | 2.5264 (2.4852 / 2.5651) | 2.5253 (2.4986 / 2.5512) |

**Held out.** The same forecast-outcome pairs and folds as the hand-set-choices test. Its saved
production forecasts are reproduced on all 59,606 rows. The added careers are never forecast; they
only join every fold's training pool. Change in mean absolute error ("better in" = resamples of
2,000 with lower error):

| | Full era, WAR/82 | Full era, season total | Historical, WAR/82 | Historical, season total |
|---|---:|---:|---:|---:|
| all players | +0.14% (333) | -0.36% (2000) | -0.33% (1847) | -0.64% (1999) |
| 3+ WAR per 82 | +0.37% (383) | -1.34% (2000) | +1.12% (79) | -1.74% (2000) |

The season total improves in both modes. The rate is mixed and neither rate result is decisive.
With the older careers in, projected WAR per 82 runs lower: bias falls from -0.07 to -0.14 in the
full-era mode. The average forecast moves 0.07-0.11 WAR per 82, more than any hand-set choice
moves it.

**In the live chain** (tables above), the added careers lower season-WAR RMSE by 1.39% (2,000 of
2,000), and the rate error among seasons played by 0.10%.
- With the pool also limited to pre-valuation seasons, the look-ahead costs 0.84%, where it cost
  1.73% on the live table.
- The combination is 0.56% below the current chain (1,972 of 2,000), with a rate error 0.38% above
  it (25 of 2,000 lower).
- The three-win-and-up tier's over-forecast five seasons out falls from +0.484 to +0.219 on the rows
  production answers.
- The exit hazard also reads the age table and was not refitted.

## Group weights, swept (2026-09-28)

The distance gives each of four groups equal weight: style (five WAR-component shares, a fifth
each), ice time, level and trend. That is equal weight, not equal contribution: what a group adds
to a given distance depends on how far apart two players are on it. The removals above do not show
whether equal proportions are best. `25_TESTS/aging_weight_sweep_test.py` v1.0 sweeps them:
- **One group at a time:** one group at 0.25, 0.5, 2 or 4 times the others.
- **Joint grid:** every group at 0.5, 1 or 2.

That makes 65 distinct weight sets. Only proportions matter, because the yardstick is rebuilt on
each scale (checked: all weights times 3 leaves every similarity weight unchanged). The sweep runs on
the age table with the older careers added. Its primary mode is the pre-valuation one, the adopted
specification.

| Comparison | Forecast pairs | Players | Equal weights rank (of 65) | Range across the 65 sets |
|---|---:|---:|---:|---|
| Pre-valuation, WAR/82 (primary) | 8,311 | 843 | 32 | -0.32% to +0.24% |
| Pre-valuation, season total | 5,263 | 752 | 28 | -0.22% to +0.22% |
| Full era, WAR/82 | 32,263 | 1,583 | 29 | -0.29% to +0.22% |
| Full era, season total | 23,893 | 1,369 | 29 | -0.40% to +0.40% |

One group at a time, change in mean absolute error against equal weights. The four columns are the
same four comparisons, in the same order:

| Group, times the others | Pre-val. WAR/82 | Pre-val. season total | Full era WAR/82 | Full era season total |
|---|---:|---:|---:|---:|
| style x0.25 | -0.12 | -0.01 | -0.08 | +0.03 |
| style x4 | +0.24 | +0.04 | +0.18 | -0.01 |
| ice time x0.25 | +0.18 | -0.08 | +0.19 | -0.12 |
| ice time x4 | -0.32 | +0.17 | -0.29 | +0.24 |
| level x0.25 | -0.00 | +0.18 | -0.02 | +0.26 |
| level x4 | +0.02 | -0.22 | +0.07 | -0.40 |
| trend x0.25 | -0.04 | -0.01 | -0.05 | -0.12 |
| trend x4 | +0.10 | +0.13 | +0.13 | +0.30 |

- **The declared rule.** Written before the run: choose the best set on the primary comparison, then
  require it to win the other three. The chosen set is ice time x4: -0.32% (2,000 of 2,000) on the
  primary comparison, but +0.17% and +0.24% on the two season totals (0 of 2,000 lower). It
  **fails**.
- **What moves error.** Ice-time weight trades the rate against the season total. Level weight helps
  the season total and does nothing for the rate. Less style and less trend help slightly.
- **Found after the run, not declared.** Eight sets are lower on all four comparisons. In all eight,
  neither style nor trend carries more weight than ice time or level, and at least one of the two
  carries less. The largest gain on any one comparison is 0.30%. None has an interval excluding zero
  on all four; four of the eight exclude zero on three.
- **Reading.** Equal weights are not shown to be the best proportions, and none of the 65 is shown
  to be better. With 65 sets tried on the same data, an edge of 0.1%-0.3% is the size selection alone
  produces. The weights matter little: no proportion moves error by more than 0.4%.

## Adopted 2026-09-28

- **The aging curve is fitted per valuation page.** Production's aging pool, z-score scale,
  yardstick and league curves now use only seasons that started before the page
  (`AgingModel(before=t0)`; `skater_forward_projection.py` v1.4, `curve_for`). This revises locked
  decision D3.
  - The rebuild's adapter follows (`production_adapter.py` v1.2).
  - The harness runner v1.2 asserts that production as adopted equals the pre-valuation arm scored
    above, on all 40,510 forecasts, largest gap 0.
- **The Elite Prospects path is fixed.** `age_join.py` reads `SOURCE_DIR/ep_birthdates.csv` and stops
  if the file is missing; it no longer skips silently.
  - It needs the contract export, so the re-run of `age_join.py` and the chain happens on the laptop.
  - Once re-run, production is the "older careers added, pool from seasons before the page" arm
    above.
- **Not changed:**
  - The exit hazard, still fitted on every season.
  - The walkthrough workbook. It stops with an explanation rather than show the retired curve.

## Limits

- Development pages 2015-2021 only. About thirty earlier variants inspected these pages, so they
  are reused, not fresh. The held-back pages 2022-2025 were not scored.
- The held-out test has no exit hazard and no dollars. The harness has no dollars. Nothing here
  prices a contract.
- Each change is scored alone, apart from the one combination above (older careers plus the
  pre-valuation pool). A setting that loses alone could still help in combination, and none was
  searched.
- The older-careers table is rebuilt by rule, not by running `age_join.py` with the contract
  export.

## Files

Generated and gitignored:
- `30_OUTPUT/aging_arbitrary_choices_test_{design,run}.json`
- `_predictions.csv`, `_origins.csv`, `_summary.csv`, `_fold_yardsticks.csv`, `_league_share.csv`
  (same prefix)
- `50_REBUILD/output/aging_choices_{summary,forecasts}.csv`
- `aging_choices_run_log.txt` and `aging_choices_birthdates.csv` (same folder)
- `30_OUTPUT/aging_ep_pool_test_{war_with_age,predictions,summary}.csv` and `_run.json`
