# The forecast states a range, and four attempts to make it see the future

Run 2026-09-15 in `50_REBUILD/`. Experimental. Development pages only; the confirmatory seal
was not touched and nothing was adopted into production.

**Revised after independent review** (`Uncertainty_Implementation_Review_Codex.md`, reviewing
`73b77ee`). Three findings were accepted in full and one figure of this report was simply
stale. The revisions are listed in section 8; two of them reverse a claim the first version
made.

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
| the placebo | every forecast paired with a different player's season | error rises 44–68% |

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
| 50% | 0.566 | 0.585 | 0.611 | 0.637 | 0.666 | 0.690 |
| **80%** | **0.836** | **0.832** | **0.827** | **0.822** | **0.843** | **0.836** |
| 90% | 0.919 | 0.916 | 0.917 | 0.911 | 0.921 | 0.913 |

The 80% band holds 82–84% of seasons at every horizon and the 90% band holds 92%. Both err
slightly wide, which is the cheaper direction. The 50% band is the exception and the reason is
structural rather than a defect: at long horizons a large share of players have a real chance of
not playing at all, the lump on zero is wide enough to swallow the middle half of the
distribution, and a band whose ends both sit on zero necessarily holds more than half the
outcomes.

**Pooling the shape across horizons is not contradicted by the horizons themselves.** The 5th
and 95th percentiles of a scaled miss move from −1.85/+2.46 at the valuation season to
−1.55/+2.75 nine seasons out: the right tail lengthens slightly with distance and the left one
shortens, and the pooled figure (−1.72/+2.56) sits inside the range at every horizon. That is a
description of one sample, not a test of the pooling, and it is reported here as the former. It
was the assumption most likely to fail and this is the evidence available on it.

**Pooling it across tiers and ages does not.** Coverage at the stated 80%:

| trailing level | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| below 0 | 0.877 | 0.871 | 0.869 | 0.862 | 0.877 | 0.887 |
| 0 to 1 | 0.829 | 0.835 | 0.832 | 0.822 | 0.849 | 0.844 |
| 1 to 2 | 0.770 | 0.774 | 0.762 | 0.762 | 0.787 | 0.766 |
| 2 to 3 | 0.796 | 0.735 | 0.752 | 0.762 | 0.769 | 0.754 |
| **3+** | 0.847 | 0.818 | 0.739 | 0.739 | 0.759 | **0.608** |

| age band | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| **22 and under** | 0.761 | 0.760 | 0.714 | 0.661 | 0.690 | **0.663** |
| 23–26 | 0.821 | 0.810 | 0.810 | 0.796 | 0.816 | 0.794 |
| 27–30 | 0.842 | 0.829 | 0.814 | 0.816 | 0.833 | 0.830 |
| 31–33 | 0.844 | 0.857 | 0.862 | 0.845 | 0.868 | 0.878 |
| 34 and over | 0.875 | 0.890 | 0.908 | 0.939 | 0.967 | 0.977 |

A band that claims 80% and delivers 61% five seasons out, for the players who carry the money,
is not a detail. It lands on the two populations the project already knows are its weakest: the
stars and the twenty-and-unders.

## 4b. Which half is wrong, and why the obvious fix is the wrong one

A band can miss too often for two different reasons and the repair is opposite in the two cases.
If the forecast is centred too low for a group, a correctly sized band around it misses high. If
the group's outcomes are genuinely more spread out than the pooled shape allows, the band itself
is too narrow. Coverage alone cannot tell them apart, so the runner divides each miss by the band
**its own page** gave it and reports the middle and the ends separately, for players who played.

| group, five seasons out | n | middle | 5th | 95th | above its own 95th |
|---|---:|---:|---:|---:|---:|
| the band, as fitted | 32,946 | −0.11 | −1.72 | +2.56 | 5% by construction |
| 3+ trailing wins | 151 | **+0.51** | −1.68 | **+3.64** | **18.5%** |
| aged 22 and under | 389 | +0.17 | −1.73 | **+3.55** | **11.6%** |
| 1 to 2 wins | 516 | +0.20 | −1.81 | +2.79 | 7.9% |

The last column is the sharpest number here, because it does not require reading a median and a
quantile together: it is the share of played seasons finishing above the 95th percentile of the
shape their own page was fitted with, which should be 5%. For the stars five seasons out it is
**18.5%**, nearly four times what the band allows.

**The star misses sit high, and that points at the forecast.** Their middle is +0.51 where the
band's own middle is −0.11, which is the star residual already on the queue as an open item and
already measured in wins (top decile predicted at 2.360 against 2.698 actual). A band centred on
a number that is too low misses high, and **widening it would hide a known bias behind a bigger
interval rather than fix it.** That repair was available, would have made the coverage table look
considerably better, and is not made here.

**The star and young right tails are also genuinely longer** — +3.64 and +3.55 against a pooled
+2.56 — and that is not a shift, because their left tails sit almost exactly where the pooled one
does. So the shape is not one shape across tiers and ages.

**How much of the coverage gap each accounts for is not established, and the first version of
this report overstated it.** It said most of the gap was the forecast. That does not follow from
a median and a tail quantile: this diagnostic conditions on the player having played, while the
coverage table includes non-participation and the probability attached to it, so a whole
component of the gap is outside what is measured here. Settling the split needs the
participation half assessed on the same footing and a controlled comparison of moving the centre
against widening the band. What the evidence supports is that **both** a low centre and a thin
upper tail are present for these groups and both are worth investigating, with the centre first
because fitting a fatter tail around a biased centre is fitting the wrong thing.

## 5. Two things the run measured

Both are properties of the machinery rather than claims about hockey.

**The realized spread runs between 0.94 and 1.11 times the fitted one, and that is a
description rather than an estimate.** The band is fitted by replaying the model on pages inside
its own training window, so its misses should be a little smaller than the misses it goes on to
make. Page by page, the middle 80% of the realized misses against the middle 80% of the fitted
ones: 1.011, 0.942, 1.000, 1.049, 1.044, 1.095, 1.114 for 2015 through 2021.

**The first version of this report called the pooled figure, 1.045, a measured 4.5% of in-sample
optimism. It is not.** Each page's fitted misses and its realized ones are different mixtures of
seasons and players, so the ratio carries that difference as well as any optimism, and looking at
the ratio cannot separate them. The pooled version also used the last page's calibrator for
every page, which is the reporting bug described in section 8. No inflation is applied on this
evidence, and none should be until an experiment that isolates overfitting is run.

**About a fifth of a one-season shock survives into the forecast, and the share falls with
distance.** Raising every player's most recent per-82 rate by half a win moves the
valuation-season forecast by 0.116 and the five-seasons-out forecast by 0.073 — a pass-through
of 0.23 falling to 0.15. That is the shrinkage the whole rebuild rests on, stated for the first
time as a single number: one season is weak evidence, the model treats it as such, and it
discounts it further the further ahead it is asked to look. A pass-through above one would be
the amplification the rebuild set out to remove.

**The first version of this report said the opposite, and was wrong.** It reported a
pass-through rising from 0.45 to 0.65 and flagged the rise as an unexplained anomaly, because a
distant forecast should revert further toward the league rather than lean harder on the trailing
anchor. The anomaly was an artifact of the test. `run_leakage_tests._predict_at()` fitted a fresh
model on every call, so perturbing the table also **retrained** the regression, the aging walk
and the participation model on the perturbed data, while the test's own text said the fit was
held fixed. What it measured was retraining and input response mixed together.

With one fitted object per page and only the inputs changed:

| response to +0.5 wins per 82 in the last season | h0 | h1 | h2 | h3 | h4 | h5 |
|---|---:|---:|---:|---:|---:|---:|
| **frozen fit — the input response** | +0.116 | +0.108 | +0.099 | +0.090 | +0.081 | +0.073 |
| refitted as well — the old number | +0.226 | +0.260 | +0.287 | +0.306 | +0.319 | +0.325 |

Both are now run and both are reported, the second named as what it is. The gap between the two
rows is the model's own retraining response, which is a real quantity and a different one.

**The deletion cases do not answer for everybody.** Removing the most recent season, or the
oldest in the window, leaves 4,764 and 4,752 of 41,496 requested subject-horizons without a
finite answer, because a player whose only qualifying season was the one deleted has no anchor
left. The counts are printed beside each case and those rows are not a complete same-population
response.

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

## 8. What the independent review changed

Reviewed at `73b77ee`. The reviewer reproduced the coverage tables, the export guard, 21 of 21
repair checks with the production workbook, and the three zero-change leakage results. Four
things were wrong and all four are corrected above.

**1. The sensitivity test refitted the model while saying it did not.** `_predict_at()` built
and fitted a fresh model on every call, so perturbing the table retrained on the perturbed data.
The test now takes an already-fitted model and changes only what `predict()` sees, and it forces
the unperturbed subject list so a deletion cannot quietly change the population. **This reverses
the reported result**: pass-through falls with distance (0.23 to 0.15) rather than rising, and
the "unexplained backwards pattern" this report previously flagged was an artifact of the bug.
The refit response is still computed and reported under its own name.

**2. The residual diagnostics used the last page's calibrator for every page.** After a harness
run, `spread_` holds the 2021 fit, and reports 5 and 6 divided a 2015 miss by a 2021 band while
describing it as the band that miss was given. Every page's calibrator is now kept and each miss
is scaled by its own. The star figures move from +0.44/+3.41 to **+0.51/+3.64**, so the concern
survives the correction and strengthens slightly.

**3. The distribution's mean was not the point forecast.** The scaled misses were kept
uncentred, and they average about +0.10 because the shape is right-skewed. The conditional
distribution was therefore `mu + sigma*E[Z]`, not `mu` — its mean sat up to 0.23 wins above the
forecast column printed beside it. This is the exact failure this wrapper exists to prevent,
arriving by a route none of the existing guards could see: the forecast **columns** were
untouched, so the "moves nothing" check passed, and the zero-spread identity passed because an
absent shape cannot be off centre. The simulation reads the mean, not the column, so every drawn
path would have been shifted upward by an amount nobody put there.

The shape is now centred, on the mean of the piecewise-linear quantile function that is actually
interpolated rather than the plain sample mean of the misses, and the amount removed (+0.0968 on
the last development page) is reported as what it is: the average miss the forecast makes on
seasons that happened. Centring rather than moving the point forecast is a choice — treating the
residual mean as a bias correction would change the forecast, move every score in the variant
register, and belongs in the forecast's own phase with its own test. A new check integrates the
returned quantile function and requires its mean to equal the expectation the harness scores;
it is written to fail both ways, so a version that stopped centring fails it and a shape that
was already centred cannot pass it by luck.

**4. A stale figure.** The placebo was quoted at 29–39% from the earlier run that had no ages.
On the full table it is **44–68%**, which is the reviewer's figure.

Two claims were also softened rather than corrected: that pooling the shape across horizons
"holds", which is one sample's description and not a test, and that 1.045 was measured in-sample
optimism, which it is not, because fitted and realized misses are different mixtures of seasons
and players. No inflation is applied.

The reviewer's reproduction script is `50_REBUILD/code/review_uncertainty.py`.

## Files

    50_REBUILD/code/predictive_interval.py     the mixture, the calibrator, the wrapper
    50_REBUILD/code/run_uncertainty.py         coverage and width by horizon and subgroup
    50_REBUILD/code/run_leakage_tests.py       the five-part battery
    50_REBUILD/code/repair_checks.py           four new guards (18-21) in the reviewer's suite

Outputs, all ignored under `50_REBUILD/output/`: `uncertainty_run_log.txt`,
`uncertainty_coverage_by_horizon.csv`, `uncertainty_coverage_by_subgroup.csv`,
`uncertainty_shape_by_subgroup.csv`,
`leakage_tests_run_log.txt`, `leakage_sensitivity.csv`.

