# Why the band misses the stars, and why it misses the young for a different reason

Run 2026-09-16 in `50_REBUILD/`. Experimental. Development pages only; the confirmatory seal was
not touched. **Nothing here is a candidate model and nothing is adopted.**

## The question

The stated 80% band holds 82–84% of seasons overall, 61% for players with 3+ trailing wins five
seasons out, and 66% for players aged 22 and under. Two independent reviews have now put the same
question to that gap, and neither the coverage table nor the residual diagnostic could answer it:
how much of it is the forecast sitting too low, how much is the band being too narrow, and how
much is the probability of playing being wrong?

It matters because the three are repaired in different places. A low centre is fixed in the
ability forecast, which moves every score on record. A narrow band is fixed in the interval
layer. A wrong probability of playing is fixed in the participation model. Guessing wrong means
spending a phase of work on the wrong half of the model.

## The method, and what it can and cannot say

**Three oracle levers.** Each is set to the value the outcomes say it should have had, for that
subgroup at that horizon, and coverage is recomputed. That uses the answer to grade the question,
deliberately. It measures the **ceiling** each repair could reach with hindsight on this sample —
an upper bound on what the lever can buy, not a prediction of what a real repair would buy. A
lever that cannot close the gap even with hindsight certainly cannot close it without.

- **the centre** — shift the group's forecast until its standardised misses sit where the band's
  own shape says they should
- **the spread** — stretch the group's band until its realized middle-90 span matches the shape's
- **participation** — replace the predicted probability of playing with the share who did

**Two measurements with no hindsight in them at all**, because an oracle says how much a lever
could buy and not what is wrong with it: the participation probability against the realized play
rate, and the season-total bias split into its rate, games and participation parts.

**The levers can substitute for each other.** Shifting a centre and widening a band both raise
coverage, and on a subgroup whose misses are skewed either can absorb the other's defect. The
tell is which tail each one repairs, so both tails are reported throughout. The three also do not
add up — the interval is a nonlinear function of all three — and the overshoot is reported rather
than hidden.

## Result 1: no single lever closes the star gap

Share of the distance from base coverage to the stated 80% that each lever closes, for players
with 3+ trailing wins:

| horizon | base | centre | spread | participation | **all three** |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.739 | 73% | −24% | 48% | 73% |
| 3 | 0.729 | 63% | −14% | 42% | **146%** |
| 4 | 0.759 | 12% | 48% | 48% | **179%** |
| 5 | 0.602 | 24% | 36% | 12% | **112%** |

Five seasons out, the best any single lever manages is 36% of the gap. All three together
overshoot it. **The star gap is a three-way defect, not one defect**, and the story changes with
distance: near the valuation season the centre carries it, further out the spread and
participation do.

The oracle shift for the stars is large and grows with horizon (+0.37 at the valuation season to
+0.72 five out, in units of the band). The forecast really is low for them. It is just not, on
its own, enough.

## Result 2: for the young, the centre is the wrong lever

| horizon | base | centre | spread | participation | all three |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.761 | **−5%** | 110% | 62% | 129% |
| 1 | 0.758 | 9% | 96% | 48% | 148% |
| 2 | 0.714 | **−11%** | 85% | 38% | 109% |
| 3 | 0.659 | **−12%** | 51% | 31% | 88% |
| 4 | 0.692 | **−29%** | 47% | 51% | 95% |
| 5 | 0.663 | **−9%** | 68% | 54% | 106% |

**Correcting the centre makes coverage worse at five of six horizons.** The spread carries most
of it and participation carries the rest. The oracle shift is near zero at the short horizons
(−0.05, −0.03, +0.07) — the forecast is not systematically low for these players where it
matters most — while the stretch is 1.12 to 1.23 at every horizon, so the band is 12 to 23% too
narrow for them throughout.

This contradicts the working assumption carried in the queue, which treated the young-player
weakness as a forecast bias needing a prior from the prospect pillar. On coverage it is not a
centre problem.

## Result 3: participation is squeezed toward the middle, and the aggregate hides it

No hindsight in this table. Predicted probability of playing against the share who actually
played:

| trailing level | h0 | h3 | h5 |
|---|---|---|---|
| 3+ | 0.987 / 0.975 | 0.923 / 0.921 | **0.781 / 0.883** |
| 2 to 3 | 0.976 / 0.973 | 0.859 / 0.931 | **0.682 / 0.799** |
| 1 to 2 | 0.947 / 0.952 | 0.753 / 0.774 | 0.559 / 0.626 |
| 0 to 1 | 0.765 / 0.724 | 0.485 / 0.469 | 0.333 / 0.348 |
| below 0 | **0.598 / 0.524** | 0.306 / 0.308 | 0.200 / 0.216 |

| age band | h0 | h3 | h5 |
|---|---|---|---|
| 22 and under | **0.922 / 0.954** | **0.782 / 0.895** | **0.677 / 0.804** |
| 23–26 | 0.849 / 0.838 | 0.666 / 0.670 | 0.531 / 0.563 |
| 27–30 | 0.772 / 0.730 | 0.521 / 0.513 | 0.345 / 0.385 |
| 31–33 | 0.684 / 0.628 | 0.325 / 0.318 | 0.142 / 0.155 |
| 34 and over | **0.491 / 0.373** | 0.111 / 0.085 | 0.027 / 0.023 |

The pattern is one-directional and it runs the length of both tables. **The groups that survive
best are under-predicted and the groups that survive worst are over-predicted.** Players aged 22
and under are under-predicted at every horizon, by 3 points at the valuation season and 13 five
seasons out. Players 34 and over are over-predicted by 12 points at the valuation season. That is
under-dispersion: the model shrinks every group toward the league and the spread of predicted
survival is too narrow.

**The harness never showed it**, and the reason is worth recording. In aggregate the errors
cancel — predicted 0.752 against 0.710 actual at the valuation season, 0.352 against 0.383 five
out — and the Brier score sits at 0.126 to 0.138 at every horizon with no trend. A single
calibration number over a population containing both halves of a compensating error is blind to
it by construction.

## Result 4: the point bias says the same thing, from the other side

The season total is the probability of playing times the rate times the share of the schedule, so
a biased total has three places to come from. Measured separately, with no hindsight:

| group | horizon | total bias | rate bias | games-share bias | participation error |
|---|---:|---:|---:|---:|---:|
| 3+ | 3 | −0.647 | **−0.632** | −0.024 | +0.002 |
| 3+ | 5 | −0.866 | **−0.921** | −0.032 | −0.102 |
| 22 and under | 3 | −0.340 | **−0.072** | −0.053 | **−0.114** |
| 22 and under | 5 | −0.407 | −0.369 | +0.027 | −0.126 |
| 2 to 3 | 5 | −0.366 | −0.290 | +0.006 | −0.118 |

**The star residual is a rate problem.** Nearly the whole of the stars' point bias is in the rate,
at both horizons, with participation contributing almost nothing at three seasons out.

**The young players' bias at three seasons out is not a rate problem.** The rate is off by 0.072
wins per 82, which is small; the total is off by 0.340. The participation probability is off by
0.114. A group whose total is badly biased while its rate is not has a participation problem
wearing a forecasting problem's clothes.

## What this changes

1. **Participation is promoted.** It was Phase 2 work with no known defect beyond the population
   question. It now has a specific, measured, one-directional defect that reaches both of the
   populations the model is worst at, and it is the only lever that helps every under-covered
   group. The compression is the thing to fix: whatever separates a 22-year-old's survival from a
   34-year-old's is under-weighted.
2. **The star residual keeps its place, and its scope narrows.** It is a rate defect, it is
   confirmed twice here, and it is worth roughly 0.9 wins a season five years out for the players
   who carry the money. But fixing it closes at most a quarter of the star coverage gap at that
   horizon, so it is not the whole of the star problem and should not be sold as such.
3. **The young-player item in the queue needs rewriting.** Its stated fix — a prior from the
   prospect pillar — addresses a centre that the decomposition says is not the problem at the
   horizons where the gap opens.
4. **The band's own spread does need a tier or age term.** It was previously the item to defer
   until the centre was fixed. For the young it is the largest single lever at every horizon, and
   waiting on a centre repair that would not help them is waiting for nothing.

## Limits

- **Every lever is an oracle.** These are ceilings on one sample, not achievable gains.
- **The star subgroup is small**: 203 scored rows a horizon, 171 at five out, and far fewer
  careers than rows, so the star figures are the least stable in the table.
- **Levers substitute.** The tails table separates them where it can, but a decomposition of a
  nonlinear interval into three overlapping causes cannot be exact, and the overshoot column
  shows how much they overlap.
- **Coverage is not accuracy.** A perfectly calibrated band around a biased forecast is still a
  band around a biased forecast, which is why result 4 is reported beside the oracle and not
  instead of it.
- **Nothing here is fitted for use.** No adjustment in this document is in the chain.

## Files

    50_REBUILD/code/run_coverage_decomposition.py

Outputs, ignored under `50_REBUILD/output/`: `coverage_decomposition_run_log.txt`,
`coverage_decomposition.csv`.
