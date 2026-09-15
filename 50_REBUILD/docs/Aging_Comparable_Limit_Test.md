# Limiting the comparables blend in the aging curve

Test date: 2026-09-13. Production model unchanged. Script: `20_CODE/aging_comp_limit_test.py`
v1.0, seed 20260913.

## Summary

1. **The comparables blend is close to an age-group average.** Nearly every same-age,
   same-position player in the pool receives a substantial similarity weight. The effective
   number of comparables is about 92% of everyone eligible. For a player at 3+ WAR per 82 games,
   the 17 comparables within half a win of his level carry 8% of the weight.
2. **The fixed pooled weight of ten is not the cause.** It takes 5% to 6% of the estimate for
   every tier of player, and slightly less for the best players than for middle ones. Removing
   it changes held-out error by less than 0.05% in every comparison.
3. **Concentrating the blend on the closest comparables helps, modestly.** Keeping only the 50
   most similar comparables lowers average error by 0.3% to 0.8% across all four held-out
   comparisons, and the uncertainty interval excludes zero in each. Halving the similarity
   bandwidth and dropping comparables below a similarity of 0.5 give similar gains. For players
   at 3+ WAR per 82, the top-50 rule lowers season-total error by 2.1% under full-era training
   and 1.3% under historical training.
4. **Limiting the blend makes the pooled weight matter, and it should stay.** Once the blend is
   limited, the ten carries 20% of the estimate at 50 comparables and 52% at ten. Every limited
   rule gets worse when the ten is removed as well. Top 10 without it raises error by 1.6% to
   3.9%.
5. **Two other ideas lose.** Letting the kept share of a player's own form rise with career
   length raises error in three of four comparisons. Removing the shrinkage altogether raises it
   in all four.
6. **Most of the error for the best players is not about comparables.** Held-out season-total
   projections for 3+ players run 0.62 WAR per season above what they went on to produce (0.46
   under historical training). The best-performing blend removes about 0.1 of that.

## How the blend works

The curve projects a player from a starting point, called the anchor, and then walks it forward
one year at a time.

- **The anchor** keeps 55% of the player's own smoothed level (a two-season per-82 average) and
  takes 45% from where comparable players his age sit. This pull toward comparables is mean
  reversion: an unusually high or low level tends to drift back toward typical.
- **The yearly steps** are the average year-over-year change of the same comparables at each
  later age.
- **The comparables** are every pool entry at the same age and position. Each gets a similarity
  weight `exp(-d² / 2h²)`, where `d` is the distance between the two players' profiles (style
  shares, ice time, level, trend) and `h` = 2.526 is the bandwidth, the scale that sets how
  quickly weight falls off with distance. `h` is the median distance between pairs of profiles.
  So a typical pair of players sits at `d ≈ h` and receives a weight of about 0.61 out of a
  maximum of 1.
- **The pooled weight** adds the plain league average for that age and position at a fixed
  weight of 10 (`SHRINK_K`), so an estimate built from few comparables leans toward the league
  curve.

The valuation does not use the curve's levels directly. `skater_forward_projection.ratio_path()`
divides each future level by the curve's own level in the valuation season and multiplies the
player's raw trailing WAR by that ratio. The anchor's pull toward comparables therefore reaches
the dollar value only by changing that denominator. A lower starting level turns the same yearly
decline in wins into a larger percentage decline.

## Part 1: what the blend does, measured

The production curve was fitted to every career (1,478 careers, 7,531 pool entries, `h` = 2.526,
matching the figures in the `aging_curve.py` docstring). Every pool entry was then scored the way
the projection scores it, with the player excluded from his own comparables. The table shows
medians by the player's smoothed level.

| | below 0 | 0 to 1.5 | 1.5 to 3 | 3+ |
|---|---:|---:|---:|---:|
| Pool entries scored | 1,517 | 3,634 | 1,715 | 660 |
| Eligible comparables | 248 | 250 | 294 | 399 |
| Sum of similarity weights | 134 | 159 | 189 | 175 |
| League average's share of the comparable estimate | 7.0% | 5.9% | 5.0% | 5.4% |
| Effective comparables, as a share of the pool | 90% | 94% | 92% | 83% |
| Comparables within 0.5 WAR/82 of the player's level | 49 | 90 | 56 | 17 |
| Their share of the weight | 25% | 34% | 21% | 8% |
| Share of the player's gap from the age-position average kept by the comparable estimate | 16% | 16% | 21% | 19% |
| Same, with the pooled weight removed | 18% | 17% | 22% | 20% |
| Share of the gap kept by the anchor (55% own + 45% comparable) | 62% | 62% | 64% | 64% |

The effective number of comparables is `(Σw)² / Σw²`. It equals the pool size when every weight
is equal and falls toward one as the weight concentrates on a single player.

For a 3+ player the comparable estimate is built mostly from ordinary players, so it keeps about
a fifth of his edge over the age-position average. Removing the pooled weight lifts that to about
a fifth plus one point. The anchor keeps 64% of the edge either way.

The percentage conversion runs the other direction. The table below takes the same yearly steps
and applies them once from the anchor (production) and once from the player's unshrunk level.
It shows the median share of the valuation-season level that remains.

| Years after valuation | 3+, from anchor | 3+, from own level | 1.5 to 3, from anchor | 1.5 to 3, from own level |
|---:|---:|---:|---:|---:|
| 2 | 0.89 | 0.92 | 0.85 | 0.88 |
| 4 | 0.79 | 0.84 | 0.68 | 0.74 |
| 6 | 0.66 | 0.75 | 0.48 | 0.56 |

The shrinkage makes the valuation's percentage decline steeper for above-average players. Part 2
tests whether that steeper decline is closer to what happened.

## Part 2: held-out test

### Design

The design is the one used in `Aging_Yardstick_Comparison.md`, with the same guards.

- **Folds.** Careers are split into five groups, stratified by position. Each group is predicted
  from a curve fitted to the other four. A target sees only his own seasons up to the forecast
  date.
- **Two training windows.** Full-era training predicts one to six years ahead and allows other
  players' later seasons into the fit. Historical training keeps only seasons up to the forecast
  year, for forecast years 2017 to 2022, and predicts one to three years ahead.
- **Two outcomes.** The first is future WAR per 82 in seasons of 20+ games, which tests the curve
  as a level. The second is future season-total WAR, predicted by applying the curve's ratio to a
  60/40 trailing season-total baseline. That uses the production rules: a negative baseline goes
  to zero, a curve base at or below 0.25 is held flat, and ratios are clipped to between 0 and 3.
  This second outcome is the one that carries through to dollars.
- **Paired scoring.** Every rule is scored on the same forecast-outcome pairs.
- **Uncertainty.** Intervals come from resampling whole careers 2,000 times. They condition on
  the fitted folds.
- **Reproduction guard.** The production rule was recomputed inside the script and also run
  through `AgingModel.project()`. The two agreed to 1e-10 on every forecast. Source and
  production-code hashes are unchanged after the run.

Scale: 26,251 rate pairs from 1,056 players and 19,794 season-total pairs from 939 players under
full-era training; 8,303 and 5,258 under historical training.

### Rules tested

Each rule changes only what it names. Everything else stays at production settings.

| Rule | Change |
|---|---|
| pool off | pooled weight 10 → 0.01 (exactly 0 divides by zero when no comparable has a value at an age) |
| h × ½, h × ¼ | bandwidth halved or quartered: weight falls off faster with distance |
| top 50 / 25 / 10 | only the N most similar comparables keep their weight |
| cutoff 0.5 / 0.8 | comparables with similarity weight below the cutoff get zero |
| + pool off | the rule above, with the pooled weight also removed |
| evidence λ | kept share of own form = n / (n + n₀), where n is qualifying seasons to date and n₀ = 4.09, set so the median forecast (5 qualifying seasons) keeps 0.55. n₀ was fixed from the distribution of career lengths before any error was computed |
| no shrink | kept share of own form = 1 |

### All players

Change in average absolute error relative to production. Negative is better. † marks a 95%
interval that excludes zero.

| Rule | Rate, full era | Rate, historical | Season total, full era | Season total, historical |
|---|---:|---:|---:|---:|
| production MAE | 1.0017 | 1.0047 | 0.9362 | 0.9312 |
| pool off | +0.02% | +0.04% | −0.00% | +0.01% |
| h × ½ | −0.43% † | −0.60% † | −0.44% † | −0.19% † |
| h × ¼ | +0.11% | +0.12% | −0.06% | +0.11% |
| h × ½ + pool off | −0.39% † | −0.69% † | −0.65% † | −0.17% |
| **top 50** | **−0.50% †** | **−0.83% †** | **−0.58% †** | **−0.32% †** |
| top 25 | −0.26% | −0.88% † | −0.50% † | −0.32% † |
| top 10 | −0.05% | −0.47% † | −0.30% † | −0.09% |
| top 25 + pool off | +0.85% † | −0.61% | +0.03% | −0.00% |
| top 10 + pool off | +3.86% † | +1.64% † | +1.73% † | +1.71% † |
| cutoff 0.5 | −0.42% † | −0.61% † | −0.37% † | −0.17% |
| cutoff 0.8 | −0.10% | −0.59% † | −0.42% † | −0.23% |
| cutoff 0.8 + pool off | +2.25% † | +1.48% † | +0.47% | +1.14% † |
| evidence λ | +0.70% † | +0.58% † | +0.18% † | +0.09% |
| no shrink | +6.84% † | +4.35% † | +1.25% † | +0.40% † |

### Players at 3+ WAR per 82 at the forecast date

180 players under full-era training, 100 under historical.

| Rule | Rate, full era | Rate, historical | Season total, full era | Season total, historical | Season-total bias, full era |
|---|---:|---:|---:|---:|---:|
| production MAE / bias | 1.342 | 1.495 | 1.466 | 1.562 | +0.62 |
| pool off | −0.08% | +0.00% | −0.29% † | +0.04% | +0.61 |
| h × ½ | −0.31% | −0.88% | −1.19% † | −0.46% | +0.57 |
| h × ½ + pool off | −0.23% | −1.65% | −2.84% † | −0.79% | +0.49 |
| **top 50** | **−0.42%** | **−1.55% †** | **−2.11% †** | **−1.26% †** | **+0.53** |
| top 25 | −0.18% | −1.65% | −1.97% † | −0.71% | +0.53 |
| top 10 | +0.10% | −0.58% | −1.42% † | +0.37% | +0.55 |
| top 25 + pool off | +1.12% | −2.14% | −2.98% † | −1.44% | +0.44 |
| cutoff 0.5 | −0.53% | −1.37% † | −1.35% † | −0.74% † | +0.56 |
| cutoff 0.8 | +0.20% | −0.75% | −1.61% † | −0.85% | +0.54 |
| evidence λ | +0.82% | −0.79% | +0.19% | −0.01% | +0.64 |
| no shrink | +14.10% † | +0.85% | +3.31% † | +0.97% † | +0.74 |

Bias is the average of forecast minus outcome, in season-total WAR. Positive means the forecast
was too high. Almost all of these players are forwards: 23 defencemen under full-era training and
11 under historical. The defence-only results are large in both directions and are not reported
as findings.

### How much the league average carries under each rule

Median share of the comparable estimate from the league average, full-era forecasts:

| Rule | below 0 | 0 to 1.5 | 1.5 to 3 | 3+ |
|---|---:|---:|---:|---:|
| production | 8% | 7% | 6% | 7% |
| h × ½ | 24% | 18% | 16% | 22% |
| top 50 | 20% | 20% | 19% | 20% |
| top 25 | 33% | 32% | 31% | 32% |
| top 10 | 53% | 53% | 52% | 52% |
| cutoff 0.8 (comparables kept: 17 / 33 / 41 / 25) | 41% | 26% | 22% | 31% |

## What the results show

**Tighter comparables help, and the direction is consistent.** Three differently built rules
concentrate weight on the nearest players: top 50, halving the bandwidth, and a 0.5 cutoff. All
three improve on production in all four all-player comparisons. That agreement is stronger
evidence than any single rule's margin, because fourteen rules were compared and the best of
fourteen will look good partly by chance. Going tighter stops helping. A quarter bandwidth, top
10, and a 0.8 cutoff give up most of the gain.

**For the best players, the gain comes through the yearly steps.** Compared with production, the
top-50 rule raises a 3+ player's projected rate by 0.28 WAR per 82 at one year and by 0.14 to 0.17
from year three on. So its projection starts higher and declines faster. In the dollar-relevant
season-total outcome it lowers the projection by about 0.1 WAR per season. A blend built mostly
from ordinary players gives the best players ordinary yearly declines, and the best players
decline faster than that in wins.

**The pooled weight becomes load-bearing once the blend is limited.** Under production it barely
matters because the comparables' weights add to 130 to 190. Under top 10 they add to about 9, and
the league average carries half the estimate. Removing it at that point leaves ten players to set
both the level and every later step, and error rises in every comparison. A limited blend needs
the pooled weight.

**The steeper percentage decline is closer to the truth, not further.** Removing the shrinkage
makes the valuation's percentage path shallower for above-average players. It raises error in
every comparison and raises the 3+ season-total bias from +0.62 to +0.74. The best players are
already over-projected in season totals, so a steeper decline moves the forecast toward the
outcome.

**The largest remaining error for the best players is the starting level.** The valuation
multiplies the ratio path by raw trailing WAR, not by the mean-reverted anchor, so a player
selected for a high recent level keeps all of it at the valuation season. Held-out outcomes for
3+ players come in 0.54 to 0.66 WAR per season below the production projection at every horizon.
Changing the comparables removes about 0.1 of that. The evidence is conditional on players who
kept playing 10+ games, and players who exited would not raise the realized figure.

## Follow-up in the production chain

The season-total outcome above mirrors the valuation path but does not run it.
`20_CODE/npv_realized_by_tier.py` runs it. For all 2,591 skater contracts in the NPV spine, every
contract season already played was priced two ways: as the engine prices it (survival times
projected value), and at what the player produced, using the same price per win, the same
forecast cap ceiling and the same league-minimum floor, with $0 if he had left the league.

| Level at valuation (season-total WAR) | Contract seasons | Over (+) or under (−) per season | Share of realized value |
|---|---:|---:|---:|
| below 0 | 1,227 | −$0.32M | −25% |
| 0 to 1 | 2,073 | −$0.13M | −7% |
| 1 to 2 | 874 | +$0.49M | +16% |
| 2 to 3 | 322 | +$0.68M | +15% |
| 3+ | 181 | +$0.98M | +14% |
| all | 4,677 | +$0.04M | +1% |

The engine is not too generous overall; it spreads value too widely. Players valued after strong
seasons are priced too high, and players valued after weak ones too low. At 3+, the 95% interval
is +$0.24M to +$1.74M per season, and the result holds without Johnny Gaudreau's 2022 contract
(+$0.82M, 11%). Players at 3+ in both of the two prior seasons are over-priced more (+$1.49M, 21%)
than players who reached 3+ on one strong season (+$0.38M, 5%, interval including zero), so the
tilt is not only short hot streaks fading. Their WAR miss is +0.43 in the valuation season and
+0.56 after it: most of it is the unadjusted starting level, with faster decline on top. The aging
curve and exit table were fitted on these same seasons, so this check is in-sample and favours
the model. It covers the contract seasons only, not RFA control years.

## Limits

- The data are contemporary reconstructions, not vintage snapshots. Outcomes are observed
  surviving seasons only. The test does not model exits, dollars or the full contract chain.
- Feature weights, the bandwidth rule, the 55% kept share and the pooled weight of ten were
  selected earlier on the same data. The top-N and cutoff values were chosen before the run, not
  tuned, but only three values of each were tried.
- Fourteen rules were compared. A single rule's interval does not account for that.
- A rule like top 50 changes nothing where fewer than 50 comparables are eligible (ages 19 to 20
  and 37+), so it does not address the thin-pool findings in `Aging_Curve_Coverage_Audit.md`.
- The curve, its pooled weight and the 55% kept share are locked. Adopting any rule here needs a
  re-run of the kept-share selection test and the full-chain valuation movement before it ships.

## Data note

`Aging_Yardstick_Comparison.md` excluded Erik Gustafsson as a career-key collision. This run found
no collision. `skater_value_engine.norm_name` keeps digits, so "Erik Gustafsson 88" stays a
separate career. The standalone fallback cleaner inside `aging_curve.py` strips digits, and it is
used only when `skater_value_engine` cannot be imported. The earlier collision came from that
fallback. Production is unaffected, but the two cleaners disagree.

## Reproduction

`python 20_CODE/aging_comp_limit_test.py` from the repository root runs in about 70 seconds.
Outputs in `30_OUTPUT/` begin with `aging_comp_limit_test_`: `design.json` (written before
fitting), `audit.csv` and `audit_rows.csv` (Part 1), `predictions.csv`, `origins.csv`,
`summary.csv`, and `run.json` (hashes and completion). Generated outputs stay outside Git.
