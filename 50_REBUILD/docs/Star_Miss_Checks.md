# What causes the star under-forecast in Model 3: every listed cause, checked

Run 2026-09-30. Test only: nothing adopted, no production file changed.

**Sources:**
- Read-only checks on Model 3's saved forecasts (`run_star_late_test.py` output, rows the current
  model answers) and on the season table.
- One harness run, `50_REBUILD/code/run_participation_drift_test.py` v1.0, with
  `star_candidates.py` v1.5.
- Models are numbered as in `Dollar_Rescore.md`. Model 3 is the current model with every listed fix,
  comparable-player aging, and the games-share forecast reading the player's level.

## The list, item by item

| # | Possible cause | What the check shows | Verdict |
|---|---|---|---|
| 1-2 | Stars' starting level too low (before aging) | Valuation-season rate 3.23 against 3.26; young stars (24 or under) 0.47 too low, and all of that is five players (below) | not a general cause |
| 3 | Too few comparables, too much pull to the league or to weaker players | Comparables carry 61%-84% of the step; the league-average step is shallower. Comparables average 1.7 wins per 82 against the star's 4.1, but among them the better ones decline more | not the cause |
| 4 | Games played under-forecast | Fixed by the games-share change (valuation-season miss -0.19 to -0.06) | fixed |
| 5 | Growth and consistency in stars not seen | Real, and confined to five players (below) | a stated limitation |
| 6 | Chance of playing too low late | Good players stay in the league longer now than in the training seasons (below). Fitting on recent seasons moves it most of the way for stars | one candidate, borderline |
| 7 | Young stars pulled back harder for thin history | Of 47 young-star valuation-season rows, 35 have three seasons behind them and those miss by -0.66; the 1-2 season rows miss by -0.42 and +0.56 | not the cause |
| 8 | Noise | The 88-player tier's mean miss over seasons 1-5 is -0.30 [-0.60, +0.02]; five players carry it | the main finding |
| 9 | The league changed | At a fixed horizon, stars are over-forecast on the 2015-2016 pages and under-forecast on 2019-2021. The top 30 skaters' rate rose from 4.1-4.5 (2014-2019) to 5.3 (2021, 2022). The league-wide rate did not move | real, overlaps with 8 |
| 10 | Who is still around to measure | Three to five seasons out the stars' season-WAR miss is -0.31: -0.06 from the chance of playing, -0.24 from rate x games in seasons played | not the cause |
| 11 | Mean reversion counted twice | Comparables' changes measured after the match made the walk steeper (`Star_Bias_Test.md`) | not supported |
| 12 | Departures entered at replacement | The star bias is identical with and without it (`Obvious_Fixes_Test.md`) | not the cause |

## The five players (items 5, 8 and 9)

The 3+ tier's miss over seasons 1-5, by player (sum over forecasts):

| Player | Total miss | Forecasts | Average miss |
|---|---:|---:|---:|
| Connor McDavid | -67.3 | 24 | -2.80 |
| Leon Draisaitl | -57.2 | 19 | -3.01 |
| Nathan MacKinnon | -56.7 | 19 | -2.98 |
| Auston Matthews | -56.3 | 24 | -2.35 |
| Sidney Crosby | -49.8 | 34 | -1.46 |

- **Without these five the rest of the tier is unbiased.** The mean miss is 0.000, and 83 players
  remain.
  - Season WAR by seasons ahead: valuation +0.12, one +0.03, two -0.06, three +0.04, four +0.09, five
    -0.12.
  - Rate: +0.16 to -0.05.
- **Most stars are not under-forecast.** Only 44% of the 88 have a negative average miss.
  Over-forecasts include Tarasenko, Laine, Seguin and Kane.
- **Young stars without the five** (23 players) miss by -0.30 per 82 three to five seasons out,
  against -1.08 with them.

The calendar pattern (item 9) and the five may be the same thing: the stars' miss is concentrated on
the later pages, whose outcome seasons are where the top 30's rate rose. With 88 players the two
cannot be separated by this check.

## Good players' chance of playing (item 6)

From the season table: 2+ win players (60/40 trailing) still playing three seasons later.

| Valued in | 24 or under | 25-28 | 29-31 | 32+ |
|---|---:|---:|---:|---:|
| 2009-2014 (the training seasons) | 0.970 | 0.945 | 0.901 | 0.645 |
| 2015-2021 (the development pages) | 0.993 | 0.987 | 0.976 | 0.691 |

Model 3 under-predicts good players three seasons out on every page, by 0.03 to 0.06. Those who did
not play mostly left for good: 7% of the 187 missed forecasts played again later.

**Two candidates, each one change to Model 3's chance of playing.** The rule was declared in the runner
before the run: an improvement needs lower squared error AND lower Brier, each in 1,950 of 2,000.
- **T:** a linear trend in the season.
- **W:** fitted only on anchors valued in the last nine seasons. The width was declared, not
  searched.

| Model | RMSE | Lower in | Brier | Lower in | 3+ bias, seasons 1-5 [95%] |
|---|---:|---:|---:|---:|---|
| Model 3 | 0.8584 | | 0.1359 | | -0.30 [-0.61, +0.04] |
| T: season trend | 0.8697 | 0 | 0.1657 | 0 | -0.39 [-0.69, -0.07] |
| **W: last nine seasons** | **0.8575** | **2,000** | **0.1356** | **1,445** | **-0.27 [-0.58, +0.06]** |

W's chance of playing three to five seasons out (predicted / observed) against Model 3's:

| Tier | Age | Model 3 | W | Observed |
|---|---|---:|---:|---:|
| 3+ | 32+ | 0.59 | 0.68 | 0.67 |
| 3+ | 29-31 | 0.84 | 0.86 | 0.95 |
| 2-3 | 29-31 | 0.73 | 0.78 | 0.89 |
| 2-3 | 32+ | 0.38 | 0.44 | 0.49 |
| 1-2 | 32+ | 0.28 | 0.32 | 0.27 |

- **W is clearly better on season error** (2,000 of 2,000), but not clearly on Brier (1,445). By the
  declared rule it does not improve Model 3.
- **What W does:** it moves good players' late chance of playing most of the way at 32+ and a little
  at 29-31. It slightly over-shoots the 1-2 tier at 32+.
- **T extrapolates the wrong way.** Its fitted trend lowers everyone's chance of playing (predicted
  minus observed -0.22 five seasons out). It is not a fix in this form.

## Reading

- **The "star under-forecast" is mostly five generational players.** Without McDavid, Draisaitl,
  MacKinnon, Matthews and Crosby, the rest of Model 3's star tier is unbiased at every horizon. They
  are the players a forecast built from earlier players has the fewest close matches for. This is a stated limitation, not a defect to repair. Trades involving those five
  should be read with that in mind.
- **The one systematic piece left is good players' late chance of playing.** Players now stay in the
  league longer than the training seasons taught. Fitting participation on recent seasons (W) is a
  simple, dated fix that lowers season error in every resample. It fails the declared bar on Brier,
  so it would need a deliberate choice, not a pass.
