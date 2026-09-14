# Which forecast is best, and why nothing has been retired

Run 2026-09-14 in `50_REBUILD/`. Experimental. No production file changed, no locked decision
opened. Every figure is from the development seasons 2015–2021; the seasons held back for the
final confirmatory run have not been touched.

Reproduce with `python 50_REBUILD/code/run_bakeoff.py`. Thirteen variants are registered in
`variant_register.csv` beside this file.

## The rule this document follows

**Nothing is retired on forecast accuracy alone.** What decides the rebuild is the error in the
*dollar value of a contract*, and that is not the same quantity as the error in a season's
wins. Surplus value is concentrated in a small number of expensive players, so a model that is
slightly worse on the average skater but better on the ones carrying the money wins the thing
that actually matters. Participation, aging and pricing are all still to be built underneath
these forecasts, and each can change the ranking. Every candidate stays in.

The cost of that patience is honesty about how many times the same seasons have been looked at.
The register is the running tally, so the final run can say how many variants preceded it
rather than implying the winner was the first idea.

## The models

| name | what it does |
|---|---|
| today's model | Blend the last two seasons of WAR 60/40, assume that is the player every year, assume he plays all 82. No aging. |
| calibrated total | Same starting number, pulled toward league average by an amount fitted from history. Knows age and position. Forecasts games played rather than assuming a full season. |
| component model | Splits WAR into even-strength offence and defence, power play, penalty kill, penalties, shooting, and an unallocated remainder. Trusts each part by how much it repeats. Adds the parts back up. |
| component split, no shrinking | The split with the trusting step removed. A diagnostic — it shows which half of the idea does the work. |

## Standing, best first

Average miss in wins. Lower is better. Columns are how far ahead the forecast reaches; a
six-year contract needs all six.

| model | valuation | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| **calibrated total, three-season window** | **0.571** | **0.595** | **0.589** | **0.588** | **0.586** | **0.571** |
| calibrated total, window fitted per horizon | 0.571 | 0.596 | 0.589 | 0.589 | 0.586 | 0.571 |
| calibrated total (two seasons) | 0.576 | 0.604 | 0.598 | 0.597 | 0.607 | 0.570 |
| component model, per-horizon trust, four-season window | 0.577 | 0.602 | 0.595 | 0.605 | 0.632 | 0.617 |
| component model, trust and window per horizon | 0.577 | 0.605 | 0.596 | 0.604 | 0.634 | 0.615 |
| component model, per-horizon trust, three-season window | 0.577 | 0.604 | 0.596 | 0.604 | 0.634 | 0.615 |
| component model, per-horizon trust (two seasons) | 0.575 | 0.606 | 0.597 | 0.601 | 0.638 | 0.606 |
| component model (two seasons) | 0.575 | 0.607 | 0.602 | 0.610 | 0.656 | 0.614 |
| component split, no shrinking | 0.592 | 0.623 | 0.626 | 0.622 | 0.661 | 0.592 |
| today's model | 0.654 | 0.706 | 0.724 | 0.741 | 0.744 | 0.739 |

Everything beats today's model by a wide margin. Against the best model here it is 14.4% worse
at the valuation season and 29.4% worse five seasons out. That gap is the rebuild's whole case
and it is not in doubt.

## What worked

**A third season is the biggest single win found so far — and the locked recency weighting was
already right.** Both models had been reading only the last two seasons through the locked
60/40 blend. Reading three, with the decay rate fitted rather than assumed, improves the
calibrated total at every horizon: −0.8%, −1.4%, −1.6%, −1.4%, −3.4% and level at five, with
five of those six differences real rather than noise.

The fitted decay rate is the striking part. It lands on **0.667 on every page but the
earliest** — which is exactly the locked 60/40 ratio. Weighted across three seasons that gives
**47% / 32% / 21%**. The project's recency weighting was never the problem. The window was one
season too short.

**Letting the model decide how far to trust a player separately for each season it forecasts.**
The trust setting answers "how many games of evidence before this player's own rate outweighs
the league norm?" The component model fitted it once, against next season, then reused it for
all six contract years. Fitted per season the constants rise monotonically for every component
and never fall — even-strength offence 40 to 80 games, power play 40 to 160, penalty kill 320
to 2560. The model discovers unprompted that recent form says less the further out you look,
and says it separately for each skill, which a blended total cannot. It closed the gap at three
seasons out from +2.2% to a tie and cut it at four from +8.2% to +5.1%.

## What did not

**Carrying age only through the shrinkage target.** The thought was that the component model
knew a player's age twice and the duplicate was letting it overfit. Removing it made things
worse at +2, +3 and +4. The two are not redundant, and the control arm confirms it is not a
general effect.

**Fitting the window shape per horizon.** The symmetric completion of the per-horizon trust
idea: let how fast older seasons are discounted also vary by how far ahead the forecast
reaches. It changes nothing — the calibrated total moves by 0.0005 wins, in the wrong
direction. A clean null. One decay rate is enough.

**A fourth season.** Essentially identical to three (0.632 against 0.634 at +4, 0.617 against
0.615 at +5). The window has all the evidence it can use by three seasons.

**A ceiling I had set was binding, and lifting it changed nothing.** The list of candidate trust
settings topped out at 1280 games with 9 of 42 cells pinned there — the fit asking to shrink
harder than an array literal allowed. Extended to mean "use the norm, ignore the player". Only
the no-signal components moved. Worth fixing, recorded as a null.

## The tension that keeps the component model alive

The three-season window improves average accuracy and **makes the treatment of stars worse**.

Bias in wins, valuation season through +2. Negative means the model says he is worse than he
turns out to be.

| model | below 0 | 0 to 1 | 1 to 2 | 2 to 3 | 3+ |
|---|---:|---:|---:|---:|---:|
| today's model | −0.37 | +0.09 | +0.48 | +0.65 | **+1.00** |
| calibrated total, two seasons | −0.12 | +0.03 | +0.05 | −0.14 | **−0.31** |
| component model, two seasons | −0.12 | +0.02 | +0.07 | −0.08 | **−0.30** |
| calibrated total, three seasons | −0.10 | +0.03 | +0.03 | −0.17 | −0.37 |
| component model, three seasons | −0.10 | +0.01 | +0.02 | −0.16 | −0.43 |

A longer window is more regression toward the mean, so it pulls the best players down harder.
That is right on average and wrong where the money is: the two-season models are the most
accurate on 3+ win players, and the three-season models are the most accurate overall. **These
are different models winning on different criteria**, and the criterion that decides the
rebuild — dollar error on a contract — has not been built yet.

This is the concrete reason not to retire anything now. Today's model over-rates a 3+ win
player by a full win a year and every calibrated model removes that; what remains is a
half-win-scale disagreement about how far to push the correction, and it will be settled by
pricing, not by average wins.

## Where it stands

- **Leader: the calibrated total on a three-season window**, ahead at every horizon.
- The component model's best form trails it by 1.0% to 8.2%, widest at the back end of a long
  contract.
- The longer window costs accuracy on stars, where the surplus value is.
- **Aging is still not built.** Both models carry a player forward flat. The horizons where the
  component model loses are the ones aging governs, and this is the plan's Phase 3.

## What has not been tried

- **Aging** (Phase 3), **participation** (Phase 2), **pricing** (Phase 4). All three sit under
  these forecasts and all three can change the ranking.
- **A window that differs by component.** Shooting is the noisiest part and should want the
  longest window; even-strength offence the shortest. The window is currently shared, which is
  the one place the component idea has not yet been allowed to express itself.
- **Goalies.** Everything here is skaters.
