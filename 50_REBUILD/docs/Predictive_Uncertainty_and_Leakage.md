# The forecast states a range, and four attempts to make it see the future

Run 2026-09-15 in `50_REBUILD/`. Experimental. Development pages only; the confirmatory seal
was not touched and nothing was adopted into production.

Two pieces of the remaining plan work are built here. The forecast now produces a distribution
over a future season rather than a single number, and the look-ahead check that existed as a
two-page spot test is now a five-part battery. They shipped together because the second one is
what makes the first one trustworthy: the uncertainty layer is the first thing in this tree
that reads **outcomes** at fit time, so it is the most likely place in the rebuild for a leak.

## 1. What was missing

Every score this project has published for a forecast is an error — how far the number was from
what happened. That answers one question and hides another. A model that says "1.2 wins" and is
off by 0.6 is doing well if 0.6 is the kind of miss it warned about, and badly if it claimed to
be sure. The second question is whether the model knows how wrong it is, and until this run
nothing in the tree could answer it, because no model stated a range.

The harness has scored interval coverage since the day it was written. The column has been
empty in every run.

It is not a reporting nicety. The valuation in the next phase walks career paths and averages
them, so it needs to know how widely the paths spread. A contract is worth more when the same
expected production carries a chance of being much better, because the club keeps the upside
and the cap hit does not move. Two models that agree on the expectation and disagree on the
spread price a seven-year deal differently, and only the one that states a spread can be
checked against what actually happened.

## 2. The shape of the answer, and why it is not a bell curve

A season's win total is not a smooth spread around a central value. It has a lump of
probability sitting **exactly on zero** — the seasons a player spends out of the league, hurt,
in the minors or retired — and a continuous spread for the seasons he plays.

A normal curve around the expectation gets the middle roughly right and the edges badly wrong.
For a fringe player with a 50% chance of playing at all, the honest tenth percentile *is* zero,
and no bell curve centred on 0.4 wins will ever say so.

So the distribution is written as a mixture, in the same three pieces every model already
produces:

- with probability (1 − p\_play), the season is exactly 0
- with probability p\_play, the season is drawn from a spread around rate × games share

The participation probability enters once, in the same place and with the same meaning it has
in the harness's integration rule. Nothing is counted twice.

One detail decides whether the arithmetic is right: **the lump sits in the middle of the
spread, not at its edge.** A player who does play can still finish below zero wins, so the
quantile function has a flat step at exactly zero, and the players whose stated percentile
lands inside that step have zero as their honest answer. That is why the inversion is written
out by hand in `predictive_interval.mixture_quantile()` rather than borrowed from a standard
formula.

## 3. Where the spread comes from

Fitted, not assumed, and fitted rolling like everything else in the tree.

At a decision date the calibrator replays the model on earlier pages — pages whose outcome
seasons had all finished before that date — and collects what it got wrong. Two things are read
off those misses.

**Scale, per season ahead.** Misses are bigger for better players and bigger further out, so
the scale is fitted as a straight line in the size of the forecast itself, separately for each
horizon. A player forecast at three wins gets a wider band than one forecast at 0.3, because he
has earned one. The line is floored at a share of the typical miss, so a player forecast at
nothing still gets a band; without that floor the fourth-liners, who are most of the rows,
would be scored against a band of almost no width and the coverage figure would be about them
rather than about the model.

**Shape, pooled across horizons.** After dividing each miss by its own scale, what is left is
the character of the error — how fat the tails are, how lopsided it is. That is taken as the
empirical distribution of the scaled misses rather than as a formula, which is the whole point:
a season's misses have a long right tail (a career year) and a short left one (there is a floor
on how bad a player can be before he stops playing), and no two-parameter curve carries that.

Pooling is an assumption, so it is checked rather than trusted: `run_uncertainty.py` prints the
shape at every horizon beside the pooled one.

**A horizon with too little evidence of its own** has its scale continued at the growth rate
already visible across the horizons that were fitted. At the earliest development page the
replay cannot reach the longest horizons — seeing a five-season miss there would have meant
asking the model in 2009 and grading it in 2014 — and leaving those horizons without a band
would silently drop the longest contracts, the population the thesis cares most about, out of
every coverage figure. This is the same device the forecast itself already uses to price an
eight-year deal from a page that reaches five, with the same caveat: every row produced by it
is tagged, so a coverage figure that leans on one can say so.

## 4. What the checks establish

Three of these do not depend on the model being any good, which is why they were written first
and run on a machine that at the time had no ages at all.

### The arithmetic, against an answer known by construction

Seasons are drawn from a mixture whose parameters the test chose; the same parameters go into
the quantile function; the stated ends are compared against the simulated ones. Nothing about
hockey is involved, so a disagreement would be an error in the arithmetic and could not be
anything else. Five player types at three stated levels, including the fringe player whose
honest tenth percentile is exactly zero and a forecast that is negative. Stated and simulated
ends agree to within Monte Carlo error at every one.

### The band collapses when the uncertainty is removed

Set the spread to nothing and make participation certain, and every quantile lands **exactly**
on the point forecast — largest gap 0 across five quantiles and 5,000 rows. A distribution that
does not collapse onto its own mean when the uncertainty is switched off is not a distribution
around that mean. The plan asks the Phase 5 simulation to satisfy the same identity; this is
that check one layer down, where it is cheap to run.

### The band is added beside the forecast, never instead of it

40,510 scored rows, largest change to any point forecast **exactly zero**. No score already on
record for this model moves.

### Four attempts to make the chain see the future, all failed

| test | what it does | result |
|---|---|---|
| the model's own discipline | fits on the whole source, 2007–2025, telling it only which year it stands in | no change, every page |
| deleting the future | every season at or after the decision date removed | no change, every page |
| corrupting the future | the same rows kept, contents shuffled between players | no change, every page |
| the placebo | every forecast paired with a different player's season | error rises 29–39% |

Largest change to any forecast or band in the first three: **0.00e+00**, on all seven
development pages, at every horizon, for the rate, the games share, the participation
probability and both ends of the band.

The first of those is new and is the one that matters. The existing spot check hands the model
a table the harness has already filtered and then filters it again, so it can only catch a
model reaching for data it was never given. This one hands over the unfiltered source and
relies on the model's own rule — that a training pair counts only if its **outcome** season
finished before the decision date. A model that filtered its inputs and not its outcomes passes
the old test and fails this one, and that is a real bug with a real history: a pair whose inputs
end three seasons back still has an outcome that lands next year. It matters beyond tidiness,
because the trade-date valuation in the next phase builds its own information sets at arbitrary
dates rather than taking the harness's, so the model's own discipline is what will carry the
weight there.

The placebo is about the scoring join rather than the model. Pair every forecast with a
different player's season and the skill should disappear; if the error barely moves, the join is
not joining a player to his own outcome and every figure in the tree measures something else.
It moves, in the right direction, at every horizon.

### The spread itself cannot see the future

Fitted on the whole source and fitted on a source truncated at the decision date, the replayed
misses are **identical to the last digit** and so is every fitted scale. This is checked in the
suite a reviewer runs, not only in the battery, because the interval layer is the one component
here that reads outcomes at fit time.

## 4a. What the band is actually worth

Run on the full table: 98.3% age coverage, 98.4% on the pages that are scored, 32,946 replayed
misses across calibration pages 2009–2020, 40,510 scored rows on the seven development pages.

**The aggregate is good and the subgroups are where the work is.**

| stated | horizon 0 | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|---:|
| 50% | 0.563 | 0.580 | 0.610 | 0.637 | 0.667 | 0.693 |
| **80%** | **0.829** | **0.828** | **0.825** | **0.816** | **0.836** | **0.832** |
| 90% | 0.915 | 0.913 | 0.914 | 0.909 | 0.921 | 0.913 |

The 80% band holds 82–84% of seasons at every horizon and the 90% band holds 91%. Both err
slightly wide, which is the cheaper direction. The 50% band is the exception and the reason is
structural rather than a defect: at long horizons a large share of players have a real chance of
not playing at all, the lump on zero is wide enough to swallow the middle half of the
distribution, and a band whose ends both sit on zero necessarily holds more than half the
outcomes.

**Pooling the shape across horizons holds.** The 5th and 95th percentiles of a scaled miss move
from −1.85/+2.46 at the valuation season to −1.55/+2.75 nine seasons out — the right tail
lengthens slightly with distance and the left one shortens, but the shape is recognisably one
shape, and the pooled figure (−1.72/+2.56) sits inside the range at every horizon. That was the
assumption most likely to be wrong and it survives.

**Pooling it across tiers and ages does not.** Coverage at the stated 80%:

| trailing level | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| below 0 | 0.875 | 0.870 | 0.864 | 0.858 | 0.874 | 0.882 |
| 0 to 1 | 0.817 | 0.826 | 0.831 | 0.816 | 0.841 | 0.841 |
| 1 to 2 | 0.764 | 0.771 | 0.751 | 0.757 | 0.775 | 0.761 |
| 2 to 3 | 0.794 | 0.735 | 0.762 | 0.744 | 0.757 | 0.751 |
| **3+** | 0.852 | 0.823 | 0.768 | 0.734 | 0.764 | **0.596** |

| age band | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| **22 and under** | 0.754 | 0.747 | 0.705 | 0.653 | 0.677 | **0.663** |
| 23–26 | 0.816 | 0.806 | 0.805 | 0.790 | 0.807 | 0.784 |
| 27–30 | 0.833 | 0.826 | 0.817 | 0.809 | 0.824 | 0.825 |
| 31–33 | 0.836 | 0.856 | 0.855 | 0.838 | 0.865 | 0.882 |
| 34 and over | 0.873 | 0.887 | 0.910 | 0.938 | 0.966 | 0.977 |

A band that claims 80% and delivers 60% five seasons out, for the players who carry the money,
is not a detail. It lands on the two populations the project already knows are its weakest: the
stars and the twenty-and-unders.

## 4b. Which half is wrong, and why the obvious fix is the wrong one

A band can miss too often for two different reasons and the repair is opposite in the two cases.
If the forecast is centred too low for a group, a correctly sized band around it misses high. If
the group's outcomes are genuinely more spread out than the pooled shape allows, the band itself
is too narrow. Coverage alone cannot tell them apart, so the runner now divides each miss by the
band it was given and reports the middle and the ends separately, for players who played.

| group, five seasons out | n | middle | 5th | 95th | 5–95 span |
|---|---:|---:|---:|---:|---:|
| the band, as fitted | 32,946 | −0.11 | −1.72 | +2.56 | 4.28 |
| 3+ trailing wins | 151 | **+0.44** | −1.62 | **+3.41** | 5.03 |
| aged 22 and under | 389 | +0.18 | −1.72 | **+3.65** | 5.37 |
| 1 to 2 wins | 516 | +0.20 | −1.80 | +2.84 | 4.64 |

**Most of the star under-coverage is the forecast, not the band.** The middle of the star misses
sits at +0.44 where the band expects −0.11: the model is centred too low for them, which is the
star residual already on the queue as an open item and already measured in wins (top decile
predicted at 2.360 against 2.698 actual). A band centred on a number that is too low misses high,
and **widening it would hide a known bias behind a bigger interval rather than fix it.** That is
the wrong repair and it is not made here.

**Some of it is the band.** The star and young-player right tails are genuinely longer than the
pooled shape — +3.41 and +3.65 against +2.56 — and that is not a shift, because their left tails
sit almost exactly where the pooled one does. So the shape is not one shape across tiers and
ages, whatever it is across horizons. That is the interval layer's own limitation and it is
recorded as one.

The order that follows is: fix the centre first, then re-measure the tails. Fitting a fatter
tail for stars while the forecast for stars is biased would be fitting the wrong thing.

## 5. Two things the run measured that are worth recording anyway

Both are properties of the machinery rather than claims about hockey.

**Being fitted in sample flatters the band by about 4.5%.** The spread is learned by replaying
the model on pages inside its own training window, so the misses it learns from are slightly
smaller than the misses it will make. That gap is measured rather than assumed small: the
model's real misses, each divided by the band it was given, against the same figure for the
misses the band was fitted on. The middle 80% of the real misses is 4.5% wider than the middle
80% of the fitted ones (3.32 against 3.18 in units of the band). Small, in the direction
expected, and **not corrected for** -- a 4.5% inflation would raise the aggregate 80% coverage
from 0.83 to a little over 0.84, which is further from the stated level, not closer. The band is
already slightly wide in aggregate; correcting the optimism on top of that would make it wider
still. Recorded as measured rather than applied.

**Between 45% and 65% of a one-season shock survives into the forecast, and the share RISES
with distance.** Raising every player's most recent per-82 rate by half a win moves the
valuation-season forecast by 0.226 and the five-seasons-out forecast by 0.325 — a pass-through
of 0.45 climbing to 0.65. The level is the shrinkage the whole rebuild rests on, stated for the
first time as a single figure: one season is weak evidence and the model treats it as such, and
a pass-through above one would be the amplification the rebuild set out to remove.

**The slope is the surprising part and it is not explained here.** A shock to last season ought
to matter less the further out the forecast reaches, not more, because a distant season should
revert further toward the league. It does the opposite. Removing the oldest season in the window
shows the same pattern from the other side: it moves the valuation season by −0.013 and the
fifth season out by −0.321. The long horizons lean harder on the trailing anchor than the short
ones do. That is a question for the forecast, not for the interval layer, and it is recorded as
one rather than guessed at.

## 6. What this does not establish

- **Nothing about dollars.** The band is on a season's win total. Turning it into a band on a
  contract's value is the joint simulation, which is the next piece and is not built.
- **The interval is on the season total only.** The rate, the games share and the participation
  probability do not carry separate bands, and the simulation will need the first two to be
  drawn jointly rather than through their product.

## 7. What comes next

The band is the input the joint simulation needs. The order that follows from this run:

1. **the star residual, which is now blocking two things rather than one.** It was already the
   forecast's largest known defect; it is also most of why the band under-covers the players who
   carry the money. Fixing the centre is the prerequisite for reading the tails.
2. build the path simulation on the fitted spread, with the zero-uncertainty identity it
   already has to satisfy one layer down
3. separate bands for the rate and the games share, drawn jointly, so an exit implies zero
   games on the path rather than a product of averages
4. then, and only then, re-measure whether the shape needs a tier or age term of its own

## Files

    50_REBUILD/code/predictive_interval.py     the mixture, the calibrator, the wrapper
    50_REBUILD/code/run_uncertainty.py         coverage and width by horizon and subgroup
    50_REBUILD/code/run_leakage_tests.py       the five-part battery
    50_REBUILD/code/repair_checks.py           four new guards (18-21) in the reviewer's suite

Outputs, all ignored under `50_REBUILD/output/`: `uncertainty_run_log.txt`,
`uncertainty_coverage_by_horizon.csv`, `uncertainty_coverage_by_subgroup.csv`,
`uncertainty_shape_by_subgroup.csv`,
`leakage_tests_run_log.txt`, `leakage_sensitivity.csv`.
