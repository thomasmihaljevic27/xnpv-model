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

## 4. What is established, and what is only demonstrated

**This machine has no birthdate table.** The join that supplies ages needs a file the
repository does not carry, so age coverage here is zero, the aging walk degenerates to a flat
carry-forward and the participation fits collapse to a constant one-in-two. The code paths all
run. **Every figure the run produced about hockey is about a crippled model and is not
evidence.** The run log says so on its first line and again on its last.

What that leaves is still substantial, because the checks that matter here do not depend on the
model being good.

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

## 5. Two things the run measured that are worth recording anyway

Both are properties of the machinery rather than claims about hockey, and both would need
rerunning with ages before they are quoted as findings.

**Being fitted in sample flatters the band by about 3%.** The spread is learned by replaying
the model on pages inside its own training window, so the misses it learns from are slightly
smaller than the misses it will make. That gap is measured rather than assumed small: the
model's real misses, each divided by the band it was given, against the same figure for the
misses the band was fitted on. The middle 80% of the real misses is 3.3% wider than the middle
80% of the fitted ones. Small, in the direction expected, and worth re-measuring on a full
table before deciding whether to correct for it.

**About 30% of a one-season shock survives into the forecast.** Raising every player's most
recent per-82 rate by half a win moves the forecast by 0.148. That number is the shrinkage the
entire rebuild rests on, stated for the first time as a single figure: one season is weak
evidence and the model treats it as such. A pass-through above one would mean the model
amplifies a single noisy season, which is the defect the rebuild set out to remove.

## 6. What this does not establish

- **Nothing about the calibration of the real model.** Coverage, width and the subgroup tables
  all ran, and all of them describe a model with no ages and a constant participation
  probability. They show the report's shape. They are not results.
- **Nothing about dollars.** The band is on a season's win total. Turning it into a band on a
  contract's value is the joint simulation, which is the next piece and is not built.
- **Nothing about the market side.** The contract export is not on this machine either, so
  eight of the twenty checks in the review suite skip here rather than pass.
- **The interval is on the season total only.** The rate, the games share and the participation
  probability do not carry separate bands, and the simulation will need the first two to be
  drawn jointly rather than through their product.

## 7. What comes next

The band is the input the joint simulation needs. The order that follows from this run:

1. rerun everything here on a machine with the birthdate join, and read the coverage and
   subgroup tables as results rather than as a demonstration
2. build the path simulation on the fitted spread, with the zero-uncertainty identity it
   already has to satisfy one layer down
3. separate bands for the rate and the games share, drawn jointly, so an exit implies zero
   games on the path rather than a product of averages

## Files

    50_REBUILD/code/predictive_interval.py     the mixture, the calibrator, the wrapper
    50_REBUILD/code/run_uncertainty.py         coverage and width by horizon and subgroup
    50_REBUILD/code/run_leakage_tests.py       the five-part battery
    50_REBUILD/code/repair_checks.py           three new guards (18-20) in the reviewer's suite

Outputs, all ignored under `50_REBUILD/output/`: `uncertainty_run_log.txt`,
`uncertainty_coverage_by_horizon.csv`, `uncertainty_coverage_by_subgroup.csv`,
`leakage_tests_run_log.txt`, `leakage_sensitivity.csv`.
