# What the repaired chain does, against a comparator that is actually production

Run 2026-09-15 on development pages 2015 to 2021, horizons zero to five. Both reserved samples
are untouched.

> **This table was published once with the wrong numbers.** The first version used a production
> adapter that reimplemented two of production's rules instead of calling them, and got both
> wrong: it multiplied negative anchors along a decay path where the locked rule projects them to
> replacement, and it took the two most recent qualifying seasons anywhere before the valuation
> instead of exactly the two preceding ones. The adapter now calls production's own `anchor()`
> and `multiplier()`. The corrected figures are roughly half the size of the published ones, and
> one subgroup claim reverses outright. The superseded numbers were -16.5% to -13.3% overall and
> -28.6% for below-replacement players.

Three forecasts are scored on identical rows. The **flat benchmark** carries the locked 60/40
trailing blend forward unchanged, with availability and participation both at one. The **live
chain** is production's own forecast, running production's aging curve, decay path, negative
anchor rule and exit-hazard survival through `production_adapter.py`. The **rebuilt chain** is
the adopted candidate from the variant register.

## The comparison, on rows production can answer

Production declines to answer for a player with no qualifying season at either of the two
preceding years. There are 120 such subjects on the 2021 page. The adapter supplies a
carried-flat fallback for them so that the harness has an answer on every row, but those rows
are tagged and excluded here, because a comparison against production on rows production cannot
price is not a comparison against production.

| horizon | live chain | rebuilt | improvement | n |
|---|---|---|---|---|
| 0 | 0.6534 | 0.5595 | **-14.4%** | 6,124 |
| 1 | 0.6077 | 0.5598 | -7.9% | 6,124 |
| 2 | 0.5815 | 0.5321 | -8.5% | 6,124 |
| 3 | 0.5542 | 0.5038 | -9.1% | 6,124 |
| 4 | 0.5065 | 0.4638 | -8.4% | 6,124 |
| 5 | 0.4575 | 0.4179 | -8.6% | 5,258 |

Mean absolute error in season WAR. The rebuilt chain is better than the live chain by about 8%
to 9% from one season out, and by 14% in the valuation season itself. Including the 120 rows per
page that production cannot price raises this to 17.6% at the valuation season and 10.3% at five
seasons out, but that number is measuring the rebuilt chain against a fallback rather than
against production, and it should not be quoted as a comparison with the live chain.

## Where the gain comes from, and where it does not

| age band | n | improvement | live bias | rebuilt bias |
|---|---|---|---|---|
| 22 and under | 3,197 | **+0.4%** | -0.336 | -0.251 |
| 23 to 26 | 12,227 | -2.9% | +0.002 | -0.099 |
| 27 to 30 | 10,549 | -11.0% | +0.123 | -0.054 |
| 31 to 33 | 5,154 | -20.2% | +0.158 | -0.036 |
| 34 and over | 4,497 | **-43.1%** | +0.170 | -0.010 |

| trailing level | n | improvement | live bias | rebuilt bias |
|---|---|---|---|---|
| below replacement | 11,254 | **-2.6%** | -0.113 | -0.039 |
| 0 to 1 wins | 15,542 | -7.6% | -0.024 | -0.043 |
| 1 to 2 | 5,553 | -14.6% | +0.292 | -0.086 |
| 2 to 3 | 2,355 | -12.3% | +0.485 | -0.235 |
| 3 or more | 1,174 | -10.4% | +0.666 | -0.565 |

Bias is mean predicted minus actual, so a positive number is over-projection.

**The rebuild is an old-player fix.** That is the whole of it. Above 30 it removes between a
fifth and nearly half of production's error, and the 34-and-over band is where the aging path
and the survival weighting have the most to correct. Below 27 it does nothing: the 23-to-26 band
improves by 2.9%, and on players 22 and under the rebuilt chain is **slightly worse than
production**.

**The below-replacement claim does not survive the corrected comparator.** The superseded
version of this table reported a 28.6% improvement on below-replacement players, and that figure
was almost entirely the adapter's own defect. Production projects a below-replacement player to
replacement in every season after the valuation, which is decision D12 and is a good rule; the
broken adapter instead carried his negative anchor forward along a decay path, which is a bad
forecast that the rebuilt chain beat easily. Against the real rule the improvement is 2.6%.

## The two residuals

**The star residual is inverted, not repaired.** The live chain over-projects a three-win player
by 0.67 wins a season and the rebuilt chain under-projects him by 0.57. Under-projection is the
safer direction for a surplus estimate on an expensive player, but a forecast wrong by more than
half a win a season is what every claim about star contracts rests on.

**Young players are where the rebuild does least, and now slightly worse than nothing.** Both
chains under-project players 22 and under, production by 0.34 wins and the rebuilt chain by 0.25,
and on mean absolute error the rebuilt chain is 0.4% behind. The smaller bias with the larger
error means the rebuilt chain is closer on average and less accurate case by case on exactly the
population the negative-NPV finding on early extensions lives in.

## What this does not settle

These are forecast figures. The dollar side runs, on signing-dated market fits with a
signing-dated cap-share denominator and discounting from the signing, but no dollar total has
been reconciled against production's contract net present values and none should be quoted until
it has. The forecast holdout is unspent; the market holdout is spent and recorded separately.
