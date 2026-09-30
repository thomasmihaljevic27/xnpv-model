# The star under-forecast in the fixed current model: four single changes

**Correction, 2026-09-30.** The current model's figures here (RMSE 0.9036 on the answerable rows,
0.8591 on the full grid) used an exit-risk star cell near zero on the 2015 and 2016 pages. With
`exit_hazard.py` v1.3 they are 0.9033 and 0.8589 (`Step_Attribution.md`, correction). No other arm
uses that table, and no reading changes.

Run 2026-09-30. Test only: nothing adopted, no production file changed.
Scripts: `50_REBUILD/code/star_candidates.py` v1.2 and `run_star_bias_test.py` v1.2, on the forecast
harness (development pages 2015-2021). The base is `obvious_fixes.ObviousFixes`, the current model
with every listed fix and its comparable-player aging (`Obvious_Fixes_Test.md`).

## Where the miss is

Players with a trailing total of 3+ wins, on the rows the current model answers. There are 1,174
forecasts, but only 88 players stand behind them.

| seasons ahead | season WAR, predicted | actual | bias |
|---|---:|---:|---:|
| valuation | 2.70 | 2.89 | -0.19 |
| one | 2.48 | 2.86 | -0.38 |
| three | 2.21 | 2.63 | -0.42 |
| five | 1.68 | 2.22 | -0.54 |

Split into the forecast's three pieces:
- **Games share** is too low from the start (0.84 against 0.89 in the valuation season). That is the
  whole valuation-season miss, since the rate (3.23 against 3.26) and the chance of playing (0.99
  against 0.99) are right there.
- **The rate** is walked down about 0.17 per 82 a season (3.23 to 2.40 in five). The stars who kept
  playing fell about 0.09 a season (3.26 to 2.82). That is measured on seasons played, a selected
  group.
- **The chance of playing** is right through three seasons out, then low (0.80 against 0.89 five out).

## The candidates

Each is one change to the base (`star_candidates.py` docstring):

| | change | aimed at |
|---|---|---|
| G | the games-share forecast also reads the player's level (trailing total, second slope above one win) | games share |
| P | the chance of playing gets a second level slope above two wins | chance of playing |
| R | comparables' yearly changes measured on raw seasons after the match, not on the two-season smoothed level | rate walk |
| H | comparables' similarity window at half the yardstick (added after G, P and R were scored) | rate walk |

The rule was declared before the run, on the rows the current model answers:
- **Improves the base** only if season-WAR squared error is lower in 1,950 of 2,000 player resamples,
  with neither rate error nor Brier higher in 1,950 or more.
- **Star bias removed** if the 3+ tier's mean season-WAR bias over seasons 1-5 has a 95%
  player-resampled interval that includes zero.

The guards passed:
- the base reproduces the saved fixed-model forecasts on all 40,510 rows;
- G moved only games share, P only the chance of playing, R and H only the rate past the valuation
  season.

## Results, rows the current model answers (35,878 forecasts)

"Lower" counts resamples, of 2,000, in which the arm's squared error is below the base's.

| arm | RMSE | lower | 3+ tier RMSE | lower | 3+ bias, mean of seasons 1-5 [95%] | 3+ bias five out |
|---|---:|---:|---:|---:|---|---:|
| base (fixed current model) | 0.8619 | | 1.828 | | -0.42 [-0.74, -0.08] | -0.54 |
| **G: games share reads level** | **0.8584** | **1995** | **1.792** | **1963** | **-0.30 [-0.61, +0.04]** | **-0.44** |
| P: participation hinge | 0.8620 | 2 | 1.829 | 12 | -0.42 [-0.74, -0.08] | -0.53 |
| R: raw comparables steps | 0.8671 | 0 | 1.833 | 327 | -0.43 [-0.75, -0.09] | -0.59 |
| H: half-width comparables | 0.8624 | 450 | 1.840 | 18 | -0.48 [-0.79, -0.14] | -0.58 |
| G + R | 0.8636 | 235 | 1.798 | 1968 | -0.30 [-0.61, +0.03] | -0.49 |
| G + H | 0.8586 | 2000 | 1.802 | 1910 | -0.35 [-0.66, -0.02] | -0.48 |
| rebuilt model | 0.8634 | 471 | 1.866 | 66 | -0.64 [-0.95, -0.31] | -0.88 |
| rebuilt model + G | 0.8591 | 1895 | 1.822 | 1264 | -0.53 [-0.84, -0.21] | -0.80 |

- G + P + R matches G + R to within 0.0001 on RMSE, with a slightly higher Brier.
- The full grid (40,510) gives the same ordering: base 0.8132, G 0.8100 (1,987), rebuilt 0.8144,
  rebuilt + G 0.8104.

Other tiers' bias five seasons out:
- **G** changes the other tiers by 0.02 or less.
- **R** moves each lower tier down by about 0.02 to 0.05.

## Reading

- **One change helps, and it helps both models.** Letting the games-share forecast read the player's
  level lowers season error in 1,995 of 2,000 resamples. The current games-share line reads only
  trailing share, position, experience and age, so it gives a star and a depth player with the same
  recent share the same forecast. The same change lowers the rebuilt model's error in 2,000 of 2,000.
  With G in both, the comparables version is lower in 1,230 of 2,000, which is not decisive. The
  rebuilt version has the lower absolute error (0.5067 against 0.5136).
- **It removes the valuation-season part of the star miss and shrinks the rest.** The miss goes from
  -0.19 to -0.06 in the valuation season, and from -0.42 to -0.30 averaged over seasons 1 to 5. The
  declared test calls the bias removed, because the 95% interval now reaches +0.04. That is the width
  of an interval resting on 88 players, not a bias of zero: the point estimate is still -0.30 and
  -0.44 five seasons out.
- **What is left is the rate walk and late participation.** Five seasons out the stars' rate is
  2.40 against 2.82 among seasons played, and their chance of playing 0.80 against 0.89. Neither
  targeted change moved them.
  - **P** barely changes the stars' chance of playing (0.795 to 0.797).
  - **R** makes the walk steeper, not flatter (2.34 five out). The reading behind it was that the
    smoothed changes count the matched season's luck twice. That reading is not supported in this
    construction. It does not rule out other ways the walk might double-count reversion.
  - **H**, a narrower window, also makes stars worse, although it was slightly better overall in the
    held-out test of 2026-09-28.
- **Caution on selection.** G was one of four candidates, and H was added after the first three were
  read. G's margin (1,995 of 2,000 against a 1,950 bar) is the result most exposed to that.

## Not tested

- dollars, where stars on long deals weigh most: `run_dollar_rescore.py` v1.1 (laptop) scores the
  base and G beside the current and rebuilt models, but has not been run;
- a fix aimed at the stars' late-horizon participation from a different angle, for example contract
  status (the adopted rebuilt model reads it);
- the 2022-2025 pages.
