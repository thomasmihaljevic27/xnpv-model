# What the repaired chain does, against the right comparator

Run 2026-09-15 on development pages 2015 to 2021, horizons zero to five. Both reserved samples
are untouched. This is the rerun the repair sequence was building toward, and it is the first
set of figures in this project measured against the live chain rather than against a flat
benchmark.

Three forecasts are scored on identical rows. The **flat benchmark** carries the locked 60/40
trailing blend forward unchanged, with availability and participation both at one. The **live
chain** is production's own forecast, running production's locked aging curve, its decay path
and its exit-hazard survival through `production_adapter.py`. The **rebuilt chain** is the
adopted candidate, the calibrated total with the survivorship-corrected aging curve and the
participation model.

## The headline, and what happens to its shape

Mean absolute error in season WAR, and the rebuilt chain's improvement over each comparator.

| horizon | flat benchmark | live chain | rebuilt | against flat | against live |
|---|---|---|---|---|---|
| 0 | 0.6160 | 0.6078 | 0.5079 | -17.6% | -16.4% |
| 1 | 0.6627 | 0.6027 | 0.5049 | -23.8% | -16.2% |
| 2 | 0.6795 | 0.5670 | 0.4781 | -29.6% | -15.7% |
| 3 | 0.6935 | 0.5310 | 0.4508 | -35.0% | -15.1% |
| 4 | 0.6959 | 0.4795 | 0.4141 | -40.5% | -13.6% |
| 5 | 0.6931 | 0.4304 | 0.3734 | -46.1% | **-13.2%** |

The improvement is real and it is worth having: 13% to 16% of the error, on every horizon. What
does not survive the correct comparator is the shape. Against the flat benchmark the advantage
grows steadily with the horizon, which reads as a model that gets relatively better the further
out it forecasts. Against production it narrows. The growth was the benchmark's missing aging
path: the further out you go, the more a model without aging loses, and none of that was the
rebuild's doing.

## Where the gain actually comes from

Improvement in mean absolute error against the live chain, by the player's age at the valuation
date and by his trailing level.

| age band | n | against live chain |
|---|---|---|
| 22 and under | 3,209 | -2.6% |
| 23 to 26 | 12,871 | -5.9% |
| 27 to 30 | 11,890 | -16.6% |
| 31 to 33 | 6,020 | -27.5% |
| 34 and over | 6,176 | **-53.8%** |

| trailing level | n | against live chain |
|---|---|---|
| below replacement | 13,902 | -28.7% |
| 0 to 1 wins | 17,384 | -10.3% |
| 1 to 2 | 5,654 | -14.8% |
| 2 to 3 | 2,384 | -13.2% |
| 3 or more | 1,186 | -10.9% |

The rebuild is an old-player and a below-replacement-player fix. Those two groups are where the
live chain's missing aging path and its survivorship blind spot bite, and they are where more
than half the error disappears. On players 26 and under the rebuilt chain is barely better than
production at all.

## The two residuals the review said to revisit after the repairs

Bias here is mean predicted minus actual season WAR, so a positive number is over-projection.

| trailing level | live chain bias | rebuilt bias |
|---|---|---|
| below replacement | -0.190 | -0.037 |
| 0 to 1 wins | -0.006 | -0.032 |
| 1 to 2 | +0.290 | -0.081 |
| 2 to 3 | +0.494 | -0.238 |
| 3 or more | **+0.680** | **-0.572** |

**The star residual has not been fixed. It has been inverted.** The live chain over-projects a
three-win player by 0.68 wins a season; the rebuilt chain under-projects him by 0.57. The sign
is better in the sense that a conservative error on an expensive player is the safer direction
for a surplus estimate, and the magnitude is only 16% smaller. Anything the project says about
star contracts rests on a forecast that is wrong by more than half a win a season, in the
opposite direction from before. This is the single largest open weakness in the rebuilt chain.

| age band | live chain bias | rebuilt bias |
|---|---|---|
| 22 and under | -0.390 | -0.252 |
| 23 to 26 | -0.032 | -0.093 |
| 27 to 30 | +0.079 | -0.047 |
| 31 to 33 | +0.115 | -0.030 |
| 34 and over | +0.137 | -0.006 |

The young-player residual is improved and still the worst age band in the table. Both chains
under-project players 22 and under, production by 0.39 wins and the rebuild by 0.25, and the
rebuild's error advantage on that group is 2.6%, which is close to nothing. Young players are
the population the negative-NPV finding on early extensions lives in, so an under-projection
there pushes directly against that finding.

## What this rerun does not settle

These are forecast figures, not dollar figures. The dollar side runs, on signing-dated market
fits and a date-aware cap path with discounting, but no dollar total from the rebuilt chain has
been reconciled against production's contract NPVs, and no such comparison should be quoted
until it has. The confirmatory samples remain unspent on the forecast side and spent on the
market side, which is recorded separately.

The two residuals above are the reason the review asked for this rerun before more model
variants were tried. Adding flexibility to chase the star residual would now be chasing an
under-projection rather than the over-projection the earlier reports described.
