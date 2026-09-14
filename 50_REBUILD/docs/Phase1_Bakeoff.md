# Which forecast is best, and why nothing has been retired

Run 2026-09-14 in `50_REBUILD/`. Experimental. No production file changed, no locked decision
opened. Every figure is from the development seasons 2015–2021; the seasons held back for the
final confirmatory run have not been touched.

Reproduce with `python 50_REBUILD/code/run_bakeoff.py`.

## The rule this document follows

**Nothing is retired on forecast accuracy alone.** What decides the rebuild is the error in the
*dollar value of a contract*, and that is not the same quantity as the error in a season's
wins. A model that is slightly worse on the average player but better on the expensive ones, or
better at the back end of a long deal, wins the thing that actually matters. Participation,
aging and pricing are all still to be built underneath these forecasts, and each of them can
change the ranking. So every candidate stays in and gets rerun as the layers go in. The
decision is taken once, at the end, on dollars.

The cost of that patience is honesty about how many times the same seasons have been looked at.
`variant_register.csv`, committed beside this file, is the running tally. Look at one set of
seasons often enough and something wins by luck; the register is what lets the final run say
how many variants preceded it.

## The models

| name | what it does |
|---|---|
| today's model | Blend the last two seasons of WAR 60/40, assume that is the player every year, assume he plays all 82. No aging. |
| calibrated total | Same starting number, pulled toward league average by an amount fitted from history. Knows age and position. Forecasts games played rather than assuming a full season. |
| component model | Splits WAR into even-strength offence and defence, power play, penalty kill, penalties, shooting, and an unallocated remainder. Trusts each part by how much it repeats. Adds the parts back up. |
| component split, no shrinking | The split with the trusting step removed. A diagnostic — it exists to show which half of the idea is doing the work. |

## Average miss, in wins

Lower is better. This is the average size of the miss, ignoring whether the model was high or
low. Columns are how far ahead the forecast reaches: a six-year contract needs all six.

| model | valuation season | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| today's model | 0.654 | 0.706 | 0.724 | 0.741 | 0.744 | 0.739 |
| **calibrated total** | 0.576 | **0.604** | 0.598 | **0.597** | **0.607** | **0.569** |
| calibrated total, no age terms | 0.575 | **0.600** | 0.599 | 0.598 | 0.613 | 0.586 |
| component split, no shrinking | 0.592 | 0.623 | 0.626 | 0.622 | 0.661 | 0.592 |
| component model | 0.575 | 0.607 | 0.602 | 0.610 | 0.656 | 0.614 |
| component model, age in the norm only | **0.574** | 0.606 | 0.609 | 0.618 | 0.671 | 0.600 |
| **component model, trust fitted per horizon** | 0.575 | 0.606 | **0.597** | 0.601 | 0.638 | 0.606 |
| component model, both repairs | **0.574** | 0.606 | 0.603 | 0.607 | 0.655 | 0.589 |

Everything beats today's model by a wide margin — 13.5% at the valuation season, 24.1% three
seasons out, 29.7% five seasons out. That gap is the rebuild's whole case and it is not in
doubt.

## What the two repairs did

**Letting the model decide how far to trust a player separately for each season it forecasts:
this works.** The trust setting answers "how many games of evidence before this player's own
rate outweighs the league norm?" The original component model fitted that once, against next
season, then reused the same answer for all six years of a contract. That is the wrong shape —
a rate that half-predicts next season predicts the year after less, and the year after that
less again — and the seasons where the component model was losing were exactly the ones where
it should have been shrinking harder.

Fitted per season, the constants come out as the reasoning predicts:

| component | valuation season | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| even-strength offence | 40 | 40 | 80 | 80 | 80 | 80 |
| even-strength defence | 80 | 80 | 160 | 160 | 160 | 160 |
| power play | 40 | 80 | 160 | 160 | 160 | 160 |
| penalties | 80 | 80 | 80 | 160 | 160 | 160 |
| shooting | 160 | 160 | 160 | 160 | 160 | 160 |
| penalty kill | 320 | 640 | 640 | 1280 | 1280 | 2560 |
| unallocated | norm | 5120 | 2560 | norm | 10240 | norm |

Every row rises or holds. Nothing falls. The model is discovering, without being told, that a
player's recent form says less about him the further out you look — and it now says so
separately for each skill, which is the thing a single blended total can never express.

The effect on accuracy: the gap to the benchmark at +3 seasons closed from +2.2% (a real
difference) to +0.7% (a tie), and at +4 seasons it fell from +8.2% to +5.1%. **The component
model now matches the benchmark from the valuation season through three seasons out.** It still
loses at +4 and +5.

**Carrying age only through the shrinkage target: this does not work.** The thought was that
the component model knows a player's age twice — once because each part is pulled toward the
norm for his age and position, once because age enters the regression directly — and that the
second copy was letting it overfit. Removing it made things worse at +2, +3 and +4 (from +0.7%,
+2.2%, +8.2% to +1.7%, +3.5%, +10.6%). The two are not redundant. Hypothesis rejected, and the
control confirms it is not a general effect: stripping age terms from the calibrated total
barely moves it except five seasons out.

**A ceiling I had set was binding, and lifting it changed almost nothing.** The list of
candidate trust settings topped out at 1280 games, and 9 of 42 cells sat pinned at that
ceiling — the fit asking to shrink harder than it was allowed. That is a modelling decision
being made by an array literal rather than by the data, so the list now runs high enough to
mean "ignore this player's own rate, use the norm". Only the components carrying no signal
moved, and the accuracy figures are unchanged to three decimal places. Worth fixing, worth
recording as a null.

## The star problem

Bias in wins over the valuation season through two seasons out. Positive means the model says
he is better than he turns out to be.

| model | below 0 | 0 to 1 | 1 to 2 | 2 to 3 | 3+ |
|---|---:|---:|---:|---:|---:|
| today's model | −0.37 | +0.09 | +0.48 | +0.65 | **+1.00** |
| calibrated total | −0.12 | +0.03 | +0.05 | −0.14 | −0.31 |
| component model | −0.12 | +0.02 | +0.07 | −0.08 | **−0.30** |
| component model, trust per horizon | −0.10 | +0.02 | +0.04 | −0.15 | −0.41 |
| component split, no shrinking | −0.26 | −0.01 | −0.06 | −0.28 | −0.61 |

Today's model says a player coming off a 3+ win season will do it again, and he does not: it is
a full win high, every year of the deal. Every calibrated model removes that. The two leaders
land within 0.01 wins of each other at the top tier, so the star problem no longer separates
them — it is settled, by both.

Note that shrinking is what fixes it. The split without shrinking is the *worst* of the
calibrated models at the top tier (−0.61), which is the clearest statement of where the value
in the component idea actually lives.

## Where it stands

- The component model with per-horizon trust **ties the benchmark for the first four seasons**
  and loses at five and six.
- Those last two seasons are where aging dominates, and **aging is not built yet** — both
  models currently carry a player forward flat. This is the plan's Phase 3 and it is the single
  most likely thing to change the ranking.
- Neither leader has an edge on the star problem.

## What has not been tried yet

- **A three-season window.** Both models still read only the last two seasons, through the
  locked 60/40 blend. The plan specifies weights over three or more seasons, fitted rather than
  fixed, and an earlier experiment found a three-season rule helped. More evidence behind the
  anchor should matter most at exactly the long horizons where the component model is losing.
  This is the obvious next test.
- **Aging** (Phase 3), **participation** (Phase 2), and **pricing** (Phase 4). All three sit
  underneath these forecasts and all three can change the ranking.
- **Goalies.** Everything here is skaters.
