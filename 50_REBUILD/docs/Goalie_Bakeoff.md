# Forecasting a goaltender, and whether production's rule holds up

Run 2026-09-17 in `50_REBUILD/`. The goalie branch of the plan's Phase 5, first step. Development
pages only. **Nothing adopted, and no production file changed.**

## Why this before anything else

The rebuild has no goaltenders in it. Before a goalie control-year gate, a goalie price line or a
goalie participation model can be built, one question has to be answered: does forecasting a
goaltender work at all on this evidence, and does the rule production already uses survive being
scored the way every skater candidate has been scored?

Production's rule, read from `20_CODE/contract_npv.py` rather than from any summary: a trailing
**50/30/20** blend of the last three seasons' WAR, falling back to 60/40 with two seasons and to
last season alone with one; shrunk by **keeping 35%** of it and putting 65% on a league average of
**2.189**; then held **flat** across the whole contract, with no aging curve. That is a strong pair
of claims — that two thirds of what a goaltender just did is noise, and that he then never ages —
and neither had been scored on held-out pages in this tree.

## The panel, and what is different about it

`goalie_season_table.py` builds the goalie panel in the skater table's schema, so the information
set, the harness and the scoring all work on it unchanged. It reuses the skater table's rules
rather than restating them: name normalisation, the career key, D20 proration, the games share
against the schedule the season actually had, the per-82 rate built from the raw total so the two
schedule adjustments cancel, experience with its left-censoring flag, and the birthdate join.

**1,560 goaltender-seasons, 280 goaltenders, 2007–2025** — 82 a season against roughly 700
skater-seasons. Everything below has to be read against that.

Three things are genuinely different and are not style choices:

- **One number, not six.** The source carries a single WAR with no component split, so the
  component-wise forecast that won the skater bake-off has nothing to work on. Every candidate here
  is a total-WAR rule.
- **Games are a role, not only availability.** A skater who plays 40 of 82 was hurt. A goaltender
  who plays 40 of 82 may be a healthy starter in a tandem, a backup, or a starter who missed a
  month, and the source cannot tell them apart. The median qualifying goaltender plays **0.44** of
  the schedule; among those playing 40 games or more it is **0.67**. Anything that reads `gp_share`
  as availability — the participation model, when it comes — has to say so first.
- **No goaltender in this panel has ever played 82 games.** The busiest season on record is 77. The
  schema's identity is therefore asserted on the rate itself rather than on a full season, and that
  absence is the point.

**Age coverage is 76%, not the skater table's 98%.** The birthdate table was built for skaters and
its goalie keys are thinner. The age candidate below is fitted on three quarters of the panel; that
is a limitation of this run, not a finding about goaltenders.

## What was scored

The same harness, the same development pages, the same frozen information set. Every candidate
answers the same grid of (goaltender, horizon) cells, so none can win by declining the hard ones,
and **every candidate shares one participation estimator** fitted before each page — the question
here is ability, and letting candidates differ on who is still in the league would mix the two.

Mean absolute error in season WAR. Lower is better.

| rule | all | h0 | h1 | h2 | h3 | h4 | h5 | bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| the league average | 1.634 | 1.899 | 1.863 | 1.694 | 1.565 | 1.394 | 1.351 | +0.092 |
| **production's rule** (keep 0.35, flat) | 1.582 | 1.757 | 1.771 | 1.648 | 1.540 | 1.378 | 1.367 | **+0.218** |
| the same, on the page's own average | 1.511 | 1.696 | 1.706 | 1.579 | 1.468 | 1.308 | 1.273 | +0.045 |
| **the same, with the kept weight fitted** | **1.491** | 1.662 | 1.681 | 1.561 | 1.452 | 1.295 | 1.262 | **+0.036** |
| shrunk by the games behind it | 1.585 | 1.788 | 1.796 | 1.658 | 1.530 | 1.367 | 1.337 | +0.164 |
| the same, with a fitted age change | 1.624 | 1.788 | 1.806 | 1.684 | 1.563 | 1.413 | 1.468 | +0.232 |

Against production's rule, resampling **goaltenders** rather than rows — there are 280 of them and
a goaltender's seasons are not independent draws:

| rule | MAE gap | share of resamples it wins |
|---|---:|---:|
| the league average | +0.052 | 3% |
| the same, on the page's own average | **−0.071** | **100%** |
| the same, with the kept weight fitted | **−0.091** | **100%** |
| shrunk by the games behind it | +0.003 | 78% |
| the same, with a fitted age change | +0.042 | 0% |

## What this says

**The shrinkage is sound. The constant is not.** Production's rule beats the flat league average,
so the trailing blend is reading something real (3% of resamples say otherwise). But it carries a
**+0.218 WAR bias** — it says goaltenders will be better than they turn out to be, at every horizon
— and simply measuring the league average on what each page could see removes most of it (+0.045)
and takes 0.071 WAR off the error, in 100% of resamples. The 2.189 constant is higher than the mean
of the development window, so every goaltender is being pulled up toward a league that no longer
exists.

**The kept weight is nearer 0.43 than 0.35.** Fitted as the slope of next season's WAR on the
trailing blend — the reliability the shrinkage is supposed to be — on 679 pairs the last
development page could see. Worth another 0.020 WAR of error on top of the constant, 100% of
resamples. That is in the same direction as the correction already recorded in production's own
docstring, which established that the locked λ is the weight on the league average and not on
trailing.

**Weighting by workload does not help.** A goaltender with 150 games behind him has told you more
than one with 40, and the fitted half-point sits at 220 games, but the candidate lands on
production's rule (+0.003, 78% of resamples — which is not a result).

**Production's flat carry survives, and the reason is worth more than the result.** The age
candidate loses (0% of resamples). But the interesting part is that the quantity it is built on is
**not identified on this panel**:

| page | fitted average change in WAR a season |
|---|---:|
| 2015 | +0.117 |
| 2016 | +0.147 |
| 2017 | +0.079 |
| 2018 | +0.117 |
| 2019 | −0.002 |
| 2020 | −0.057 |
| 2021 | −0.106 |

It flips sign as the window moves, so the early pages walk a goaltender **up** and the late ones
walk him down. A within-player change can only be measured on goaltenders who played both seasons,
and the ones who fall out are the ones who declined — the same selection the skater side documents
in Phase 3, on a twelfth of the sample. So this is not evidence that goaltenders do not age. It is
evidence that **this panel cannot tell you how they age**, and that production's flat carry is
defensible for that reason rather than because ageing has been ruled out.

## What this does not establish

- **Nothing here is a valuation.** No price line, no dollars, no contracts. This is the ability
  forecast alone, and it is the input the rest of the goalie branch needs.
- **The role forecast is held fixed across candidates**, deliberately, so this says nothing about
  how well a goaltender's share of the schedule can be forecast — which for a goaltender is a
  depth-chart question as much as a skill one.
- **The participation estimator is a flat survival rate by horizon**, shared so the comparison is
  clean. It is not a participation model and does not have the two-state structure the skater side
  uses.
- **82 seasons a year.** The two winning margins are 100% of resamples, but they are margins of
  0.07 and 0.09 WAR on a 1.5 WAR error.
- **Development pages only**, and the confirmatory pages are sealed.

## What is checked

- The panel is the skater panel's schema, one row per goaltender-season after a traded goaltender's
  halves are summed, with the rate built from the raw total so proration is applied exactly once.
  Verified by prorating the rate a second time, which the check catches.
- Every candidate answers the same grid, cannot fit on the page it stands on, and **shares one
  participation estimator** — each verified by breaking it: removing the page guard, and giving one
  candidate its own survival numbers.
- The participation estimator is unmoved when every season at or after the page is scrambled.

Suite: **30 passed, 0 skipped, 0 failed.**

## Files

    50_REBUILD/code/goalie_season_table.py   the panel
    50_REBUILD/code/run_goalie_bakeoff.py    the six candidates and the scoring

Writes `goalie_bakeoff.csv`: every scored (rule, goaltender, page, horizon) cell with its error.
Outputs ignored under `50_REBUILD/output/`.

## Next in the goalie branch

A price line and a participation model, in that order — the control-year gate the plan asks for
needs both, and the tender decision for a goaltender is a depth-chart decision as much as a value
one. On this evidence the ability forecast to carry forward is the trailing blend with the league
average measured at the page and the kept weight fitted, not the locked constants.
