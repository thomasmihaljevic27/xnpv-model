# The current model with every listed fix, and nothing else

Run 2026-09-30. Test only: nothing adopted, no production file changed.
Scripts: `50_REBUILD/code/obvious_fixes.py` v1.0 (the model), `run_obvious_fixes_test.py` v1.0 (the
season forecasts), and `run_dollar_rescore.py` v1.0 (contract dollars, to run on the laptop).

## The question

Suppose the current model took every fix with an obvious case and kept everything else, most visibly
its comparable-player aging. How would it score against the current model and the rebuilt one?

The fixes, as built (`obvious_fixes.py` docstring):

- **Starting level:** a three-season rate per 82 games, pulled toward the league average by the
  rebuilt model's fitted rule. Thomas added the pull to the list during the run. The plain 50/30/20
  rate without the pull is kept as a lower rung. That rate is games-weighted: weighted WAR per
  weighted game, seasons of 10+ games.
- **Games share and chance of playing:** the rebuilt model's own forecasts, without contract data.
  Reading contract status was not on the list.
- **Aging:** the current model's comparable-player curve, with these changes:
  - fitted per valuation page on earlier seasons and on the corrected age table;
  - each year's change added to the rate, not multiplied;
  - players who left the league entered at replacement level. A pool season whose player has no NHL
    row the next year, with that season over before the page, gets an imputed next rate of 0, smoothed
    the pool's own way. The league-average changes are recomputed with those rows included. That
    enters 495 departures on the 2015 page and 900 on the 2021 page.
- **Not changed:** the comparable-player method itself (pool rule, eight measures, group weights,
  yardstick, weighting formula, league weight of ten, 55/45 pull inside the curve, basing one or two
  ages back).

Guards:
- one row set and target for every arm;
- games share and chance of playing identical across the fixed arms and the rebuilt model;
- the fitted start identical to the rebuilt model's in the valuation season;
- the survivors-only arm reproduces the aging-method test's comparables arm on all 40,510 rows
  (largest gap 8.9e-16);
- the current arm reproduces the recorded 0.9036.

## Results, rows the current model answers (35,878 forecasts, 1,516 players)

"Lower in" counts player resamples, of 2,000, in which the arm's squared error is below the named
model's.

| Season forecast | RMSE | vs current | Lower in | vs rebuilt | Lower in | MAE | Bias |
|---|---:|---:|---:|---:|---:|---:|---:|
| current, as it runs | 0.9036 | | | +4.7% | 0 | 0.5431 | +0.008 |
| fixes, plain 50/30/20 start | 0.8822 | -2.4% | 2000 | +2.2% | 13 | 0.5458 | -0.059 |
| **fixes, fitted start** | **0.8619** | -4.6% | 2000 | -0.2% | 1529 | 0.5151 | -0.067 |
| fixes, survivors-only pool | 0.8621 | -4.6% | 2000 | -0.1% | 1470 | 0.5166 | -0.069 |
| rebuilt | 0.8634 | -4.4% | 2000 | | | 0.5081 | -0.076 |

The full grid (40,510) gives the same ordering: 0.8591 current, 0.8340 plain start, 0.8132 fixed,
0.8144 rebuilt.

Season-WAR RMSE by seasons ahead:

| | valuation | one | two | three | four | five |
|---|---:|---:|---:|---:|---:|---:|
| current | 0.9140 | 0.9216 | 0.9202 | 0.9175 | 0.8861 | 0.8532 |
| fixes, plain start | 0.8514 | 0.8927 | 0.8973 | 0.9041 | 0.8921 | 0.8496 |
| fixes, fitted start | 0.8320 | 0.8733 | 0.8802 | 0.8837 | 0.8622 | 0.8348 |
| rebuilt | 0.8320 | 0.8728 | 0.8805 | 0.8849 | 0.8626 | 0.8434 |

Season-WAR bias by trailing tier, valuation season to five out:

| | below 0 | 0 to 1 | 1 to 2 | 2 to 3 | 3+ |
|---|---|---|---|---|---|
| current | -0.33 to -0.06 | +0.07 to -0.10 | +0.35 to -0.08 | +0.43 to +0.08 | +0.96 to +0.22 |
| fixes, plain start | -0.18 to -0.18 | +0.03 to -0.11 | +0.15 to -0.10 | +0.09 to -0.01 | +0.43 to -0.07 |
| fixes, fitted start | +0.01 to -0.07 | +0.03 to -0.09 | -0.02 to -0.17 | -0.24 to -0.21 | -0.19 to -0.54 |
| rebuilt | +0.01 to -0.05 | +0.03 to -0.07 | -0.02 to -0.21 | -0.24 to -0.37 | -0.19 to -0.88 |

The rate per 82, one to five seasons out, in seasons played (16,771), average miss:

| | all | 3+ |
|---|---:|---:|
| fixes, plain start | 1.1301 | 1.579 |
| fixes, fitted start | 1.0590 | 1.517 |
| fixes, survivors-only pool | 1.0619 | 1.523 |
| rebuilt | 1.0512 | 1.548 |

The rebuilt model's rate error is lower than the fixed model's in 1,983 of 2,000 resamples (the fixed
model lower in 17).

## Reading

- **The listed fixes close the whole gap on season error.** The fixed current model and the rebuilt
  model are within 0.2% on squared error, and the fixed one is lower in 1,529 of 2,000 resamples, which
  is not decisive. On absolute error the rebuilt model is lower (0.5081 against 0.5151).
- **The starting level carries about half the gain on its own.** The plain 50/30/20 rate gives -2.4%.
  The fitted pull toward the league adds another 2.2 points and removes the tilt by quality in the
  valuation season.
- **Aging now splits by player.** With every other piece shared, the fitted equation is still slightly
  more accurate on the typical player's rate. The comparables are better for stars, and the fixed
  model's star under-forecast five seasons out is -0.54 against the rebuilt model's -0.88. Five
  seasons out its season error is 1.0% lower.
- **The survivorship fix matters little for comparables** (0.8621 to 0.8619 RMSE; 1.0619 to 1.0590 in
  rate). Why it matters less here than in the equation has not been tested.
- **What this does not show:** dollars, where stars on long deals carry the most weight
  (`run_dollar_rescore.py` needs the contract export), and the version that reads contract status.
  One construction of each fix was built; other constructions of the survivorship fix for comparables
  are possible.
