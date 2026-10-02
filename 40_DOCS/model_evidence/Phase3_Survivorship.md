# Survivorship: the prediction I wrote down was wrong, and why

Run 2026-09-15 in `50_REBUILD/`. Experimental. Development seasons 2015–2021 only.

## The problem

A year-over-year change can only be measured on a player who played both seasons. The players
who decline hardest stop playing, so their worst year is never in the sample. The aging curve is
fitted on survivors.

The scale of it, at 33 and over: 64% of qualifying player-seasons are followed by another one.
The ones who continue averaged **+0.862** WAR per 82 in the season before; the ones who stopped
averaged **+0.092**. Splitting by quality, 84% of the top quartile play on and 49% of the bottom
quartile do.

## The prediction, and what happened

Written into the code before anything was run: *the correction should produce a steeper decline
after about 33; if it does not, the correction is wrong rather than the expectation.*

**The first correction made the decline shallower, and the expectation as I stated it was wrong
too.** Both halves are worth keeping.

## Why inverse-probability weighting does not work here

The standard fix is to weight each observed change by one over the probability it would have
been observed, so a 35-year-old whose decline we did see stands in for the ones who never got a
next season. It moved the curve the wrong way at every age — a 1.5-win 38-year-old went from
−0.485 to −0.378.

The reason is the kind of missingness. Reweighting corrects selection **on observables**: it
assumes that once you condition on age, level, games and position, whether a player is observed
is unrelated to what he would have done. That is not this situation. A player retires *because
of the season we do not get to see*. The outcome causes the missingness, and no amount of
reweighting the survivors recovers information about people who are absent for a reason
correlated with the thing being measured.

Worse, it has a perverse edge. The players given the largest weights are the ones least likely
to survive — and among players unlikely to survive, the ones who did are positively selected.
Up-weighting them flattens the curve rather than steepening it. That is exactly what happened.

IPW stays in the register with a number against it. An approach that was tried and does not work
is evidence; an approach quietly dropped because it disagreed with expectation is not.

## What does work: stating the assumption

The alternative puts the missing seasons back explicitly. A player who played season *t* and
could not hold an NHL job at *t+1* is assumed to have been at about replacement level, which is
zero on this scale by construction. 1,695 missing seasons re-enter a panel of 7,764 observed
pairs.

That is not a measurement. It is an identifying assumption, and it is the thing that makes
missing data informative. It is deliberately a hard case — some of those players were injured
and would have been fine — so the result is better read as a bound on decline than as a point
estimate of it.

## The correction is about level, not age

This is the part I had not anticipated, and it is more useful than what I predicted. Yearly
change in WAR per 82:

| | age 30 | age 34 | age 38 |
|---|---:|---:|---:|
| **fringe player (0.5 wins)** | | | |
| survivors only | −0.110 | −0.194 | −0.381 |
| imputed | −0.087 | −0.119 | **−0.212** |
| **average player (1.5 wins)** | | | |
| survivors only | −0.158 | −0.269 | −0.485 |
| imputed | −0.169 | −0.249 | −0.391 |
| **star (3.0 wins)** | | | |
| survivors only | −0.229 | −0.382 | −0.640 |
| imputed | **−0.292** | **−0.445** | **−0.659** |

The correction **steepens decline for good players and flattens it for marginal ones.**

The mechanism is in the data. The players who vanish are overwhelmingly marginal — at 33 and
over, their last season averaged +0.060 wins per 82, so putting them back at replacement is a
change of −0.060, far shallower than the −0.30 the survivors of the same age show. Fringe players
do not fall off a cliff when they leave; they were already at the floor and there was nowhere to
fall. Correcting for their absence therefore tells the model that old marginal players decline
*less* than the survivor sample implied, and the level interaction absorbs the difference by
making stars decline *more*.

So my prediction of "a steeper decline after 33" was right about the players it matters for and
wrong as a general statement. The survivorship bias in this curve was never a missing cliff for
everyone. It was concentrated in the level dimension, and it was making the model too gentle
with exactly the players who carry the money.

## Does it forecast better

| seasons ahead | valuation | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| effect of the correction | 0.00% | **−0.08%** | **−0.27%** | **−0.57%** | **−1.10%** | **−1.11%** |

Negative is better, and every interval from one season out excludes zero. The gain grows with
horizon, which is the right shape: the further ahead you look, the more of the forecast is
carried by the aging curve, and the more a biased curve costs.

The reweighting approach is worse than doing nothing at all, at every horizon.

Star bias moves from −0.393 to −0.418 — slightly further from zero, and consistent with the
curve now declining faster for the players in that tier. Whether that is a cost or a correction
cannot be settled on wins; it is a dollars question.

## Standing

**New leader: the calibrated total, three-season window, additive aging with the survivorship
imputation, and participation without contract data.** Against the pre-participation leader it
is 3.7% better at the valuation season and **26.9%** better five seasons out.

## The sensitivity: how much rests on the assumption

The replacement-level assumption is doing real work, so it is a dial with a sweep behind it
rather than a constant buried in the fit.

**On the curve, it matters enormously for fringe players and barely for stars.** Yearly change:

| assumed level of a departing player | 3-win at 34 | 1.5-win at 34 | 0.5-win at 38 |
|---|---:|---:|---:|
| −0.75 | −0.516 | −0.400 | −0.594 |
| −0.50 | −0.493 | −0.350 | −0.466 |
| −0.25 | −0.469 | −0.300 | −0.339 |
| **0.00 (replacement)** | **−0.445** | **−0.249** | **−0.212** |
| +0.25 | −0.422 | −0.199 | −0.084 |

The star curve moves across a range of 0.094 wins over the whole sweep; the fringe curve moves
across 0.510. That asymmetry is the right way round for this project: the assumption is weakest
exactly where the money is not.

**On the forecast, it barely matters, and the natural anchor is also the best one.** Average miss
five seasons out: 0.4338 at −0.50, 0.4221 at −0.25, **0.4171 at replacement**, 0.4200 at +0.25.
Replacement level was chosen because a player who cannot hold an NHL job is worth about what a
free replacement is worth — an argument made before any of this was run — and it turns out to be
the shallow optimum. The whole sweep spans 4% of the forecast at the longest horizon.

**Returners are now handled with data instead of an assumption.** A player absent at *t+1* who
plays again at *t+2* or *t+3* was usually hurt rather than finished, and his rate on return is
observed. Using that where it exists leaves the assumption carrying only the players who never
appeared again — 291 of 1,695 absences are returners. It forecasts identically (0.4171) and
carries a slightly better star bias (−0.412 against −0.418), so it is adopted: same accuracy,
one less thing assumed.

## What this does not settle

- Everything here is skaters.
- The correction is a bound, not a point estimate, and should be reported as one.
