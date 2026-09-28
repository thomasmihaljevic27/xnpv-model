# One fitted equation against comparable players, aging alone

Run 2026-09-28. Test only: nothing adopted, no production file changed.
Script: `50_REBUILD/code/run_aging_method_test.py` v1.0, on the forecast harness (development
pages 2015-2021).

## The question

Two ways of carrying a player's level forward in age.

- Comparable players, the current model. For each player, the yearly changes of same-age,
  same-position players are averaged, the most similar weighted most, and blended with the league
  average.
- One fitted equation, the rebuilt model. A regression predicts next season's change in wins per 82
  from a cubic in age, a defence shift, and the player's level in the season before, with an
  age interaction. It is fitted on each pair of consecutive seasons by the same player.

Earlier comparisons scored the two whole forecasts, which also differ in their starting level and
participation. This test holds everything except the yearly changes fixed.

## Design

Each arm uses the rebuilt forecast without contract data: the same starting level at the valuation
season, the same games share, the same chance of playing, and the same rows. Only the change added
to reach seasons 1 to 5 differs, and each arm's aging is fitted on seasons that finished before the
page.

| Arm | Yearly changes from |
|---|---|
| regression | the fitted equation, with departing players entered at replacement level (as adopted) |
| regression, survivors only | the same equation on players who played both seasons, which is also how the comparables curve is built |
| comparables | the current model's curve (fitted per page), its change from the valuation age to each later age; where it has no profile for a player (1,359 of 6,916 player-pages), its own league-average curve |
| no aging | none: the starting level carried flat |

Scores, declared before the run:
- the rate per 82 games in seasons played, absolute error, which is what aging predicts;
- season WAR, squared error, the harness's primary score.

Both are scored on the full grid and on the rows where the comparables arm used the player's own
comparables. The declared rule: a method is better only if it is lower on both scores, on both
samples, in at least 1,950 of 2,000 player resamples.

## Results

Seasons 1 to 5, full grid: 33,594 forecasts, 16,975 of them in seasons played, 1,609 players.
"Lower" counts the resamples, of 2,000, in which the arm's error is below the regression's.

| Arm | Rate error | Lower | Season-WAR RMSE | Lower |
|---|---:|---:|---:|---:|
| regression | 1.0499 | | 0.8201 | |
| regression, survivors only | 1.0514 | 306 | 0.8195 | 1,686 |
| comparables | 1.0604 | 1 | 0.8189 | 1,423 |
| no aging | 1.0840 | 0 | 0.8203 | 959 |

On the rows with the player's own comparables (27,016 forecasts, 1,377 players), rate error is
1.0541 regression against 1.0659 comparables (0 of 2,000 lower). Season-WAR RMSE is 0.9004 against
0.8987 (1,509 of 2,000).

By the declared rule, **no method is a clear winner**. The two scores disagree.

- The rate per 82. The regression is more accurate than the comparables by 1.0% (1 of 2,000
  resamples favour the comparables). It is more accurate at each horizon, from one to five seasons
  out, and in each tier of player below three wins.
- Season WAR. The four arms are within 0.2% of one another, and not aging at all scores the same as
  aging. Season WAR here is dominated by whether and how much a player plays, which every arm shares,
  so it cannot tell aging methods apart. It was a poor choice of deciding score for this question.

## The split by player tier

Rate error in seasons played, seasons 1 to 5, by the player's trailing total:

| Arm | below 0 | 0 to 1 | 1 to 2 | 2 to 3 | 3+ (910 rows) |
|---|---:|---:|---:|---:|---:|
| regression | 0.927 | 0.968 | 1.118 | 1.231 | 1.548 |
| regression, survivors only | 0.931 | 0.970 | 1.120 | 1.231 | 1.533 |
| comparables | 0.944 | 0.976 | 1.130 | 1.249 | 1.523 |
| no aging | 0.936 | 0.989 | 1.189 | 1.318 | 1.528 |

Rate bias five seasons out (predicted minus actual, seasons played):

| Arm | below 0 | 0 to 1 | 1 to 2 | 2 to 3 | 3+ |
|---|---:|---:|---:|---:|---:|
| regression | -0.05 | -0.12 | -0.23 | -0.28 | -0.93 |
| comparables | -0.19 | -0.18 | -0.15 | -0.03 | -0.43 |

- For most players the regression is more accurate.
- For three-win-and-up players the comparables are more accurate, and their under-forecast five
  seasons out is less than half the regression's. For those players the regression is worse than
  carrying the level flat (1.548 against 1.528), and the comparables are only slightly better than
  flat (1.523).
- The survivorship correction (regression against regression on survivors) changes little overall.
  Without it the regression is slightly better for stars, slightly worse in three of the other four
  tiers, and level in the fourth.

## Reading

- The fitted equation predicts a typical player's future rate better than the comparables do.
- The comparables do better for the best players, where the equation's decline is too steep. This
  is the rebuilt model's recorded star under-forecast, now shown to come from the aging step:
  everything else is held fixed here.
- Season WAR cannot separate the two, and dollars were not scored. Because stars carry the largest
  contracts, a dollar-weighted score could favour the comparables even though the rate score
  favours the regression. That test needs the contract export.
- One construction of each method was tested. The comparables arm used the current model's
  settings; the regression used the adopted formula.
