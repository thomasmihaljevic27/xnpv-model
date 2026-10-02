# The late star miss in Model 3: two quality-by-age terms

Run 2026-09-30. Test only: nothing adopted, no production file changed.
Scripts: `50_REBUILD/code/star_candidates.py` v1.3 and `run_star_late_test.py` v1.0, on the forecast
harness (development pages 2015-2021).

The models are numbered as in `Dollar_Rescore.md`.
- **Model 1** is the current model.
- **Model 3** is the current model with every listed fix, its comparable-player aging, and the
  games-share forecast reading the player's level. It is the base here.

## What the split showed

Model 3's 3+ win players (88), three to five seasons out, split by age at valuation. Before the run,
comparables were checked as the source of the star rate miss:
- **Comparables carry most of the star's step.** They hold 61%-84% of the weight in each yearly step,
  against the league average's pseudo-weight of ten, and the league-average step is the shallower
  of the two.
- **They are much weaker players.** Their average level is about 1.7 wins per 82 against the
  star's 4.1.
- **A matching correction would make it worse.** Among them the better players decline slightly
  more, also on raw post-match changes (about -0.06 per 82 per win of level). So a correction toward
  the star's own level would steepen his decline.

The miss by age:
- **Chance of playing** is too low for good players past about 29. For 3+ win players aged 29-31 it
  is 0.84 predicted against 0.96 observed. For 2-3 win players it is 0.74 against 0.89 (29-31) and
  0.38 against 0.49 (32+). The 1-2 tier aged 32+ is right.
- **Rate:** the largest star miss is young stars. Aged 24 or under, 27 players are forecast 3.28 per
  82 against 4.36 in seasons played, and their valuation-season rate is already 0.47 too low.

## The candidates and the rule

Each is one added term on Model 3:
- **A:** the chance-of-playing model reads level x age.
- **S:** the fitted starting rate reads level x age.

The rule, declared in the runner before the run: a candidate improves Model 3 only if its
season-WAR squared error is lower in 1,950 of 2,000 player resamples, with neither rate error nor
Brier higher in 1,950 or more.

The guards passed:
- the base reproduces the saved Model 3 forecasts on all 40,510 rows;
- A moved only the chance of playing, and S only the rate.

## Results, rows the current model answers (35,878 forecasts)

| Model | RMSE | Lower than Model 3 in | 3+ tier RMSE | Lower in | 3+ bias, mean of seasons 1-5 [95%] |
|---|---:|---:|---:|---:|---|
| Model 3 | 0.8584 | | 1.792 | | -0.30 [-0.61, +0.04] |
| A: participation level x age | 0.8589 | 120 | 1.792 | 983 | -0.29 [-0.60, +0.04] |
| S: start level x age | 0.8580 | 1,628 | 1.786 | 1,749 | -0.29 [-0.59, +0.04] |
| A + S | 0.8584 | 1,137 | 1.785 | 1,911 | -0.29 [-0.59, +0.04] |

By the declared rule, none improves Model 3.

Three to five seasons out, the pieces each term was aimed at (predicted / observed):
- **A:** 3+ aged 32+ chance of playing 0.59 to 0.65 (observed 0.67). Aged 29-31, 0.84 to 0.86
  (observed 0.95). Young stars slip from 0.98 to 0.97, and overall squared error is slightly worse.
- **S:** 3+ aged 24 or under, rate 3.28 to 3.36 (observed 4.36). Aged 32+, 1.75 to 1.67 (observed
  2.24).

## Reading

- **Neither simple term fixes the late star miss.** A term that lets age cost a good player less
  moves old stars' chance of playing about half the way at 32+ and barely at 29-31. A term that lets
  the starting pull differ by age moves young stars' rate by 0.08 of a 1.08 miss.
- **The young-star miss is a small group with no close matches.** The 27 young stars improved far
  beyond what their comparables (weaker young players) or a pull toward the league can see. More
  flexible terms fitted on so few players risk chasing noise.
- **The late chance-of-playing miss for good players runs across ages, not only past 29.** The 2-3
  tier is also low at 25-28 (0.88 against 0.96). Neither a level slope above two wins (earlier test)
  nor level x age captures it. One input the model does not use is a live candidate: whether the
  player is under contract for that season. A star three years into an eight-year deal is on a
  roster. The adopted rebuilt model reads contract status in its participation; Model 3 does not.
  That test needs the contract export, so it runs on the laptop.
- The star bias in Model 3 stays about -0.30 over seasons 1-5 (-0.44 five out). The rebuilt model
  sits at -0.64, and the current model is +0.46 the other way.
