# Forecasting a goaltender, and whether production's rule holds up

Run 2026-09-18 in `50_REBUILD/` (v2.0, after an independent review). The goalie branch of the
plan's Phase 5, first step. Development pages only. **Nothing adopted, and no production file
changed.**

**The first version of this report claimed a candidate beat production's rule. It is withdrawn.**
The thing it beat was not production's rule — it was a reimplementation of it, missing three
mechanisms, built from a partial reading of the code. Against production's own projector, imported
and called, **nothing here beats it**. What survives is a narrower and still useful result about
bias. The corrections are listed at the end.

## Why this before anything else

The rebuild has no goaltenders in it. Before a goalie control-year gate, a price line or a
participation model can be built, one question has to be answered: does forecasting a goaltender
work at all on this evidence, and does the rule production already uses survive being scored the
way every skater candidate has been scored?

## The panel

`goalie_season_table.py` builds the goalie panel in the skater table's schema, so the information
set, the harness and the scoring all work on it unchanged. It reuses the skater table's rules
rather than restating them: name normalisation, the career key, D20 proration, the games share
against the schedule the season actually had, the per-82 rate built from the raw total so the two
schedule adjustments cancel, experience with its left-censoring flag, and the birthdate join.

**1,560 goaltender-seasons, 280 goaltenders, 2007–2025** — 82 a season against roughly 700
skater-seasons.

Three things are genuinely different and are not style choices:

- **One number, not six.** No component split, so the component-wise forecast that won the skater
  bake-off has nothing to work on.
- **Games are a role, not only availability.** The median qualifying goaltender plays **0.44** of
  the schedule; among those playing 40 games or more it is **0.67**. A team carries two
  goaltenders, so a low share can be a backup role, a tandem, or an injury, and the source cannot
  tell them apart. Anything that later reads `gp_share` as availability has to say so first.
- **No goaltender in this panel has ever played 82 games.** The busiest season is 77.

Age coverage is **76%**, not the skater table's 98%, because the birthdate table was built for
skaters. That is a limitation of this run.

## The benchmark is production's own projector, imported

Not a reimplementation. The first version rebuilt the cascade from a reading of
`contract_npv.py` that stopped halfway through the method, and three mechanisms were missing:

1. production's lookup table has **no games filter** — a two-game season is a prior like any other,
   where the rebuilt one dropped anything under ten games;
2. the cascade fills the t−1, t−2, t−3 slots **strictly**. A goaltender with no t−1 season does not
   fall to a 60/40 of whatever else exists; he goes to a **stale anchor** computed at an earlier
   standpoint, bounded three seasons back;
3. a stale-anchor goaltender shrinks toward **0.650**, the conditional mean of goaltenders who came
   back, not toward the league average.

The third I had never read. The candidate now imports the class and calls it, the same way the
qualifying-offer bands are checked against production's implementation rather than re-derived. The
reimplementation is kept in the bake-off as "a simplified cascade", because the gap between it and
the real thing is itself worth seeing: up to **2.28 WAR** on a single goaltender.

## What was scored

The same harness, the same development pages, the same frozen information set. Every candidate
answers the same grid of (goaltender, horizon) cells, and **every candidate shares one participation
estimator** fitted before each page — the question here is ability, and letting candidates differ on
who is still in the league would mix the two. 3,683 forecasts per candidate.

Mean absolute error in season WAR. Lower is better.

| rule | all | h0 | h1 | h2 | h3 | h4 | h5 | bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| the league average | 1.634 | 1.899 | 1.863 | 1.694 | 1.565 | 1.394 | 1.351 | +0.092 |
| **production's own projector** | **1.488** | 1.628 | 1.662 | 1.555 | 1.455 | 1.304 | 1.295 | +0.101 |
| a simplified cascade, keep 0.35 | 1.582 | 1.757 | 1.771 | 1.648 | 1.540 | 1.378 | 1.367 | +0.218 |
| the same on the page's own average | 1.511 | 1.696 | 1.706 | 1.579 | 1.468 | 1.308 | 1.273 | +0.045 |
| the same, with the kept weight fitted | 1.491 | 1.662 | 1.681 | 1.561 | 1.452 | 1.295 | 1.262 | **+0.036** |
| shrunk by the games behind it | 1.585 | 1.788 | 1.796 | 1.658 | 1.530 | 1.367 | 1.337 | +0.164 |
| with a fitted age slope | 1.552 | 1.788 | 1.764 | 1.603 | 1.467 | 1.335 | 1.325 | +0.034 |

Against production's own projector, resampling **goaltenders** rather than rows, pairing on
(page, goaltender, horizon):

| rule | MAE gap | share of resamples it wins |
|---|---:|---:|
| the league average | +0.147 | 0% |
| a simplified cascade, keep 0.35 | +0.094 | 0% |
| the same on the page's own average | +0.023 | 1% |
| the same, with the kept weight fitted | **+0.003** | **34%** |
| shrunk by the games behind it | +0.097 | 0% |
| with a fitted age slope | +0.065 | 0% |

## What this says

**Production's goalie projector is the best forecast here, and nothing in this bake-off beats it.**
The closest candidate is 0.003 WAR worse and wins a third of resamples, which is a tie and not a
loss for production. The claim in the first version of this report — that a fitted kept weight
improved on production — was an artifact of comparing against a lookalike that was 0.094 WAR worse
than the real thing.

**The bias is a diagnostic, not an established defect.** Production's projector runs **+0.101 WAR**
high over these 3,683 forecasts and the fitted-weight candidate **+0.036**, and an earlier version of
this report called that a defect for the price line to correct. It is not established, for two
reasons.

Resampling whole careers puts production's mean error between **−0.129 and +0.315**. That interval
contains zero, so this run does not establish that the forecast runs high at all.

And the bias is not only the forecast's. Every candidate shares one participation estimator by
design, and that estimator says **64.1%** of these goaltender-seasons are played where **55.3%**
were. Priced at a flat 1.89 WAR for every season actually played, that gap comes to **+0.167 WAR** —
an **illustration of the participation term's scale, not a decomposition of the observed bias**. It
gives every played season the same production, so it does not say how much of the +0.101
participation caused; it says only that the term is large enough that the bias cannot be read as the
ability forecast's alone. Every candidate carries it.

So the pooled mean error cannot be attributed to anybody's ability forecast, and the only part of it
this run can speak to is the *difference* between two candidates' biases. **Nothing downstream
should move a dollar price to cancel it.** The place to take it up is the goalie participation
model, where the larger term lives.

**The shrinkage reads something real.** Every cascade-based rule beats the flat league average
comfortably (0% of resamples for the average), so a goaltender's trailing record is informative even
after two thirds of it is shrunk away.

**Weighting by workload does not help** (+0.097, 0% of resamples), which is the clearest negative
result here: the fitted half-point sits at 220 games, and using it costs as much as the simplified
cascade's other differences.

## How goaltenders age: the earlier claim is withdrawn

The first version reported that the fitted season-to-season change flips sign across pages and
concluded that goalie ageing "is not identified on this panel". **That conclusion is withdrawn,
because the candidate it rested on never used age.** It took the intercept of its own regression —
the average change at the pivot age — and applied it to every goaltender alike. Adding twenty years
to every subject moved the forecast by exactly zero.

Fitted properly, the two coefficients behave differently and only one of them is about age:

| page | change per year of age | the common drift at the pivot |
|---|---:|---:|
| 2015 | −0.0479 | +0.1167 |
| 2016 | −0.0050 | +0.1467 |
| 2017 | −0.0260 | +0.0792 |
| 2018 | −0.0081 | +0.1167 |
| 2019 | −0.0711 | −0.0019 |
| 2020 | −0.0884 | −0.0574 |
| 2021 | −0.0722 | −0.1057 |

**The age slope is negative on every page.** An older goaltender's season-to-season change is worse
than a younger one's, on every window this run has. What swings is the **drift** — the level the
whole population moves by — from +0.117 WAR a season in 2015 to −0.106 in 2021, and that is not an
age effect at all.

So the honest statement is narrower in one direction and stronger in the other: this run gives no
reason to say ageing is unidentified, and a stable negative age slope is what it actually found.
Using it still does not beat production (+0.065, 0% of resamples), which is a statement about this
implementation on 82 seasons a year, not about whether goaltenders age. The slope is fitted on
within-goaltender changes, so it is measured only on goaltenders who played both seasons and the
ones who fall out are the ones who declined — the same selection the skater aging curve carries,
and untested here.

## What this does not establish

- **Nothing here is a valuation.** No price line, no dollars, no contracts.
- **The role forecast is held fixed across candidates**, so this says nothing about forecasting a
  goaltender's share of the schedule — which is a depth-chart question as much as a skill one.
- **The participation estimator is a flat survival rate by horizon**, shared so the comparison is
  clean. It is not a participation model, and it over-predicts playing by nearly nine points, which
  is the larger part of every candidate's pooled bias.
- **Production's projector declines to price some goaltenders** (prospect-pillar territory there);
  here the grid must be answered, so they take the page's average. That is a small courtesy to the
  benchmark, not a handicap.
- **82 seasons a year.** Every margin in the table is small against that.
- **Development pages only**, and the confirmatory pages are sealed.

## What is checked

- The panel is the skater panel's schema with one row per goaltender-season and proration applied
  exactly once — verified by prorating the rate a second time.
- Every candidate answers the same grid, cannot fit on the page it stands on, and shares one
  participation estimator — verified by removing the page guard and by giving one candidate its own
  survival numbers.
- **The benchmark is production's own class**, it differs from the simplified cascade, and it
  ignores every season from the page onward — verified by putting a lookalike in its place, by
  making the two coincide, and by scrambling the future in its lookup table.
- **One forecast is one (page, goaltender, horizon)**, and a candidate that says it uses age moves
  when age moves and leaves h0 alone — verified by dropping the page from the pairing and by
  reverting the age term to the intercept.

Suite: **32 passed, 0 skipped, 0 failed.**

## Files

    50_REBUILD/code/goalie_season_table.py   the panel
    50_REBUILD/code/run_goalie_bakeoff.py    the seven candidates and the scoring

Writes `goalie_bakeoff.csv`: every scored (rule, goaltender, page, horizon) cell with its error.
Outputs ignored under `50_REBUILD/output/`.

## What the first version got wrong

1. **The benchmark was not production.** A reimplementation missing the games filter, the strict
   slot rule and the 0.650 stale-anchor target. The claimed improvement over production is
   withdrawn.
2. **The bootstrap paired across years.** Joining on goaltender and horizon without the page turned
   3,683 intended pairs into 19,853 rows and reweighted the comparison toward goaltenders who
   appear on many pages. Workload weighting was reported at 78% of resamples; correctly paired
   against the real benchmark it is 0%.
3. **The ageing candidate never used age.** It applied one common drift to everyone, so the sign
   flip it produced was in the drift, not in ageing. The "not identified" conclusion is withdrawn.

## Next in the goalie branch

A price line and a participation model, in that order — the control-year gate the plan asks for
needs both, and a goaltender's tender decision is a depth-chart decision as much as a value one. On
this evidence the forecast to carry forward is **production's own projector**. Its +0.101 mean error
is recorded as a diagnostic to re-examine alongside the participation model — not as a defect for
the price line to correct, and not as a reason to replace the rule.
