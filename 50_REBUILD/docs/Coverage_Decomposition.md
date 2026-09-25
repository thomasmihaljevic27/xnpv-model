# Subgroup miscalibration: what is measured, and what was claimed and withdrawn

Run 2026-09-16 in `50_REBUILD/`. Experimental. Development pages only; the confirmatory seal was
not touched. **Nothing here is a candidate model and nothing is adopted.**

**Revised after independent fact check** (`Coverage_Decomposition_Review_Codex.md`, reviewing
`c4c41f4`). The tables reproduced. Several conclusions drawn from them did not, and they are
withdrawn in section 5 rather than quietly edited. Two of them were contradicted by this file's
own printed output.

## 1. The question, and why it stays open

The stated 80% band holds 82–84% of seasons overall, 61% for players with 3+ trailing wins five
seasons out, and 66% for players aged 22 and under. Two reviews asked the same thing of that gap:
how much is the forecast sitting too low, how much is the band too narrow, and how much is the
probability of playing wrong?

**It is still open, and this document does not close it.** What follows is what can be measured
on a development sample that has now been looked at many times, separated carefully from what
cannot.

## 2. What is established

### Subgroup miscalibration is real and reproduces

| group | h0 | h3 | h5 |
|---|---:|---:|---:|
| all scored rows | 0.836 | 0.822 | 0.836 |
| 3+ trailing wins | 0.847 | 0.739 | **0.608** |
| aged 22 and under | 0.761 | 0.661 | **0.663** |
| aged 34 and over | 0.875 | 0.939 | 0.977 |

Of 151 played star seasons five out, 28 (**18.5%**) finish above the 95th percentile of the shape
their own page was fitted with, where 5% is intended.

### Participation probabilities are wrong for specific subgroups

Predicted against the share who played:

| group | h0 | h3 | h5 |
|---|---|---|---|
| aged 22 and under | 0.922 / 0.954 | 0.782 / **0.895** | 0.677 / **0.804** |
| 3+ trailing wins | 0.987 / 0.975 | 0.923 / 0.921 | 0.781 / **0.883** |
| 2 to 3 | 0.976 / 0.973 | 0.859 / 0.931 | 0.682 / **0.799** |
| aged 34 and over | **0.491** / 0.373 | 0.111 / 0.085 | 0.027 / 0.023 |

Players aged 22 and under are under-predicted at every horizon. The oldest players are
over-predicted at the short ones. These are observed subgroup calibration errors and they matter
beyond the interval, because the same probability multiplies the expected production.

### The point bias, in wins, by an accounting that adds up

The forecast is the probability of playing times the rate per 82 times the share of the schedule.
Substituting the realized value of each in turn gives contributions in one unit:

| group | horizon | total | participation | rate | games |
|---|---:|---:|---:|---:|---:|
| 3+ | 0 | −0.172 | +0.023 | −0.017 | **−0.178** |
| 3+ | 3 | −0.647 | −0.004 | **−0.507** | −0.135 |
| 3+ | 5 | −0.866 | −0.101 | **−0.680** | −0.086 |
| 22 and under | 0 | −0.035 | −0.008 | +0.100 | **−0.127** |
| 22 and under | 3 | −0.340 | −0.061 | −0.072 | **−0.207** |
| 22 and under | 5 | −0.407 | −0.075 | **−0.256** | −0.076 |

Two things follow, and only two.

**The stars' bias at the longer horizons is mostly rate.** −0.507 of −0.647 at three seasons out,
−0.680 of −0.866 at five. The star residual is a rate defect, which is what the earlier work said
and what survives here.

**Games played is a substantial error source that nothing had remarked on.** It is the largest
single component of the young players' bias at three seasons out (−0.207 of −0.340) and the whole
of the stars' bias at the valuation season (−0.178 of −0.172). The games forecast has been
treated throughout this rebuild as the quiet half of the pair, and on this evidence it is not.

**This is an accounting, not a causal split.** The order of substitution decides where the
interactions land and a different order moves them. It is reported because it is in one unit and
it closes, which the version it replaces was not and did not.

## 3. Three adjustments, and what they are worth

Each lever is set to a value read off the outcomes and coverage is recomputed. Share of the
distance from base coverage to the stated 80% that each closes:

| group | h | base | centre | spread | participation | all three |
|---|---:|---:|---:|---:|---:|---:|
| 3+ | 3 | 0.739 | 65% | −40% | 32% | 153% |
| 3+ | 5 | 0.608 | 24% | 34% | 9% | 113% |
| 22 and under | 3 | 0.661 | −17% | 47% | 34% | 84% |
| 22 and under | 5 | 0.663 | −9% | 66% | 54% | 100% |

**These are the effect of three particular changes, not bounds on anything.** Each is arbitrary —
align a median, match a middle-90 span, substitute a group mean — and none maximises coverage.
Doubling the spread alone takes star coverage five seasons out from 60.8% to **88.3%**, past
everything in the table. That is not a proposal, since coverage alone always rewards a wider
band; it is the counterexample that shows these numbers bound nothing.

Read as sensitivity: coverage responds strongly to the spread for the young at every horizon, and
to the centre for the stars at the middle horizons. That is all it says.

## 4. What is not established

- **Which cause dominates.** The relative roles of participation, games, the rate forecast and
  selection are unresolved. Nothing here identifies them.
- **That it is selection bias.** Plausible, and the intuition is sound — the players whose later
  seasons are observed are the ones still in the league. But the harness already keeps departed
  players as zero-production seasons rather than dropping them, and the aging curve already
  attempts a selection correction. Identifying the mechanism needs assumptions about who becomes
  observable and how that relates to performance. A calibration table cannot do it.
- **That any repair would achieve what the levers show.** See section 3.
- **That the star figures are firm.** 203 scored rows a horizon and 171 five out, but only **88
  and 81 distinct careers**. A player contributes many rows.

## 5. Claims this document made and has withdrawn

1. **"Oracle ceilings" and "the most a perfect repair could buy".** The adjustments are arbitrary,
   not optimal. Withdrawn.
2. **"Therefore it is three defects, not one."** It rested entirely on the false ceiling. Withdrawn.
3. **"Fixing the centre closes at most a quarter of the star gap."** Same. Withdrawn.
4. **"For the young the centre is the wrong lever."** One median-aligning adjustment lowering
   coverage does not rule out a better ability forecast or a prospect prior. Median alignment
   among played seasons, unconditional coverage, and mean accuracy are three different
   objectives. Withdrawn as a claim about the forecast; what remains is that this particular
   adjustment does not help.
5. **"The young players' bias is almost entirely participation."** In common units it is mostly
   **games** (−0.207) against participation (−0.061) and rate (−0.072). Withdrawn — and the error
   was reading four quantities in four different units as contributions to one total.
6. **"One-directional down the whole length of both tables."** Stars are slightly over-predicted
   at the short horizons and below-zero players under-predicted at the long ones. Withdrawn.
7. **"Participation is the only lever that helps every under-covered group."** This file's own
   output printed −16% and −4% for the 1-to-2 tier while the sentence was written. Withdrawn.
8. **"The aggregate Brier score cannot see it because the errors cancel."** Opposite-signed errors
   do not cancel inside a squared-error score. What cancels is the comparison of mean predicted
   against mean actual. A Brier score mixes calibration with discrimination and outcome
   uncertainty, so a flat one neither demonstrates nor refutes subgroup calibration. Corrected.
9. **A comment claiming the per-page residual shapes differed by less than a hundredth at every
   quantile.** It was never measured. The largest difference is 0.030, and using the last page's
   shape for every page moved the star five-seasons-out baseline from 60.8% to 60.2%. The
   diagnostic now uses each page's own shape and the tables above are on the corrected baseline.

## 6. The measured limitation, for the record

> The model has systematic forecast and interval errors for some age and ability groups,
> concentrated at longer horizons. Nominal 80% ranges hold 82–84% of outcomes overall but 61% for
> the highest trailing-ability group five seasons out and 66% for players aged 22 and under.
> Participation probabilities are miscalibrated for those same groups. The respective roles of
> participation, games played, the rate forecast and selection are unresolved.

That paragraph is the honest statement of where the forecast stands, and it is what belongs in
the write-up.

## 7. What comes next, and it is not more of this

The diagnostic loop stops here. Repeated adjustments to one development sample that has already
been inspected many times cannot separate these causes, and each pass spends holdout credibility
on a question it is not built to answer.

The question that decides whether any of this matters is whether these errors change the thesis's
own conclusions: **do valuations and the trade-mispricing categories move when the forecast is
varied across reasonable alternatives?** If the conclusions survive, an imperfect forecast still
supports the argument and this is a limitations paragraph. If they do not, that is a finding about
the thesis and not about calibration.

## Files

    50_REBUILD/code/run_coverage_decomposition.py

Outputs, ignored under `50_REBUILD/output/`: `coverage_decomposition_run_log.txt`,
`coverage_decomposition.csv`, `point_bias_accounting.csv`. The reviewer's reproduction is
`50_REBUILD/code/review_coverage_decomposition.py`.
