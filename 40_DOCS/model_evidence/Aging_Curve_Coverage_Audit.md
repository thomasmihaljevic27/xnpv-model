# Aging Curve Coverage Audit

2026-09-13. Written from `aging_curve.py` and `skater_forward_projection.ratio_path()` as they
stand, and from a read-only run against the 2018-2025 contract NPV panel as it stood before
`skater_forward_projection.py` v1.3. Audit script: session scratch (`audit.py`), logic summarised
in each section below.

## What the curve does, in one paragraph

A skater's future seasons are projected by multiplying his trailing-WAR anchor by a ratio path
taken from the aging curve. The curve is built from a comparables pool. Each entry in the pool is
one player at one age, described by a two-season profile: style shares, ice time per game, a
smoothed per-82 level, and a trend (the change between the two seasons). A target player is
compared only against pool entries at the same age and position, weighted by similarity. Those
weighted comparables set both where he should regress toward and how he should change from year
to year, and a fixed pooled weight of 10 pulls thin estimates toward the league-wide curve for his
position. The valuation bases the curve at age−1, falling back to age−2 (D21), so it only ever
reads completed seasons.

## Finding 1: most "no curve" tags were a labelling bug (fixed, no value change)

Of 1,976 skater pages tagged `flat_no_curve`, 1,765 had the curve available. They were pages with
one contract season left. The contract projection asked the curve for zero future years, and the
lag guard in `ratio_path()` (the walk must reach at least one future season) skipped both bases,
so the tag fell through to `flat_no_curve`. The value was never affected: the only season on such
a page is the valuation season itself, whose ratio is exactly 1.0 on every path, and the RFA
control years were projected by a separate call with a longer horizon that did use the curve.

Of the 1,765, 1,694 would have been tagged `curve` and 71 `flat_low_curve_base`. Fixed in v1.3 by
probing the curve at horizon 1 for the tag only. The path-mix figures recorded under D21 counted
these pages as curve misses and overstate the miss rate.

## Finding 2: the real misses are 211 pages, about 3% of skater pages

| Cause | Pages | Players |
|---|---:|---:|
| First 20+ GP season comes after the base age (rookie cameo) | 99 | 82 |
| Never a 20+ GP season at all (the curve's own games filter) | 68 | 41 |
| No 20+ GP season at age−1 or age−2 (injury or demotion gap) | 44 | 37 |

Valuation ages cluster at 21-25. The first row is the standing short-first-season flag, now
counted: the `MIN_GP = 20` filter drops a short rookie cameo, so a player valued one year into his
career has no curve base and is held flat. Direction is conservative for young players, since the
curve generally projects them upward.

## Finding 3: first seasons can never be comparables, which empties the young end of the pool

A pool entry needs two consecutive qualifying seasons ending at that age (review item 1.7). A
player's first qualifying season therefore never enters the pool. At the older ages this costs
little. At the young ages it removes most of the league:

| Age | D with a 20+ GP season | D in pool | F with a 20+ GP season | F in pool |
|---:|---:|---:|---:|---:|
| 19 | 43 | 6 | 101 | 22 |
| 20 | 87 | 34 | 220 | 86 |
| 21 | 160 | 72 | 349 | 186 |
| 22 | 230 | 129 | 480 | 295 |
| 23 | 285 | 197 | 576 | 409 |
| 25 | 301 | 251 | 585 | 510 |

At ages 19 and 20 every exclusion is a first season. Two consequences follow.

1. **The young pool is selected on early arrival.** At age 20 the pool holds only defencemen who
   were already NHL regulars at 19. Quinn Hughes, Moritz Seider, Jake Sanderson and Kris Letang
   (first qualifying season at 20) are absent from it; Cale Makar, Adam Fox, Roman Josi and P.K.
   Subban (first at 21) are absent from the age-21 pool. A college-route defenceman valued at 20
   or 21 is matched against players who took a different development path. Lane Hutson's
   closest age-20 matches are Trouba, Werenski, Heiskanen, Dahlin and Maatta. The direction of the
   resulting bias is not measured.
2. **The pool is thin exactly where young contracts are priced.** Median total similarity weight
   against the fixed pooled weight of 10 gives the league-wide curve's share of each estimate:

| Age | D pool | D league-curve share | F pool | F league-curve share |
|---:|---:|---:|---:|---:|
| 19 | 6 | 78% | 22 | 42% |
| 20 | 34 | 31% | 86 | 15% |
| 21 | 72 | 18% | 186 | 8% |
| 22 | 129 | 11% | 295 | 5% |
| 25 | 251 | 6% | 510 | 3% |
| 34 | 74 | 19% | 126 | 12% |
| 37 | 18 | 49% | 37 | 32% |

Below 21 for defencemen, and at the oldest ages for both positions, the comparable-specific curve
is substantially the league-wide position curve.

## Items already logged elsewhere, still open

- Self-exclusion is incomplete at the league-wide layer (STANDING_FLAGS, 2026-09-09).
- The Erik Gustafsson / Erik Gustafsson 88 career-key collision (STANDING_FLAGS, 2026-09-10).
- Whether the mean-reversion weight (λ = 0.55) should vary by player type (STANDING_FLAGS,
  2026-08-28).

## Options, not implemented

The curve, its pool rule and λ are locked. Each option below changes them, so each needs the same
evidence the item 1.6/1.7 rebuild produced: held-out error against the current curve, a re-run of
the λ selection test, and the full-chain valuation movement.

1. **Admit single-season entries to the pool** with the trend attribute treated as missing, so the
   distance is computed over the remaining attributes. Item 1.7 rejected keeping single-season
   entries with a trend of zero because zero is a value, not an absence; treating it as missing
   answers that objection. Addresses Finding 3 directly.
2. **Base a first-year player on his first qualifying season** when the age−1 and age−2 bases are
   both missing, instead of holding flat. Addresses the first row of Finding 2.
3. **Pool adjacent ages at the thin ends** (age ±1 at 19-20 and 35+), with the age difference as a
   distance term. Addresses Finding 3's second consequence without touching the rule for
   mid-career ages.
