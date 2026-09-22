# Will he play, and how much? The goalie participation model

Run 2026-09-22 in `50_REBUILD/`. The goalie branch of the plan's Phase 5, third step. Development
pages only. **Nothing adopted, and no production file changed. The goaltender price specification
stays provisional.**

## Two questions, not one

A goaltender's expected season is three numbers multiplied together: the chance he plays in the NHL
at all, the share of the schedule he plays if he does, and how good he is per game. The bake-off
settled the third — production's own projector, which nothing beat. The first two had been stood in
for by a flat survival rate and his trailing share, carried forward unchanged, and the flat rate
predicted **64.1%** of goaltender-seasons played where **55.3%** were.

They are different forecasting problems, so they are built and scored separately.

- **Whether he plays** — the skater participation model, reused rather than copied: one rolling
  logistic fit per horizon on trailing level, trailing share of the schedule, experience, and
  contract state as known on the decision date. **Not age**, for the reason below.
- **How much, if he plays** — a rolling linear fit per horizon of next season's share of the schedule
  on trailing share, trailing level and experience, fitted only on seasons he actually played.

The ability forecast is held at production's projector in every arm, so each comparison is about
participation and role and nothing else.

## Why there is no age in either model — a selection on the outcome

**This is the main finding of the run.** It was found by the first version getting it badly wrong.

A goaltender's birthdate comes mostly from the contract export. So having one means he was still in
the league in the contract era, which is exactly the outcome the model predicts. On the 2019 page:

| goalie anchors | played 0 seasons out | 3 seasons out | 5 seasons out |
|---|---:|---:|---:|
| with a birthdate | 0.908 | 0.902 | 0.894 |
| without one | 0.557 | 0.257 | 0.119 |

A goalie with a birthdate is almost certain to keep playing, and one without is likely to leave. The
skater participation model drops rows with no age, and run on goaltenders that rule fitted **only
survivors**. It predicted about 0.87 at every horizon against an observed rate falling from 0.72 to
0.37, and scored far worse than the flat rate it was meant to beat. The first share model also
carried a has-a-birthdate flag as a feature, which amounts to a column recording who was still
playing years later.

Skaters have 98% birthdate coverage, so the same rule barely bites there. For goaltenders about half
of the anchor rows have a birthdate, and that half is mostly the survivors. Experience, counted from
the panel itself, stands in for age. `ParticipationModel` now takes an `exclude` argument, and the
goalie branch uses it to drop age.

**This also qualifies the bake-off's ageing result.** The age slope reported there, negative on
every page, was fitted on within-goaltender changes among goaltenders **with** a birthdate. That is
the survivor subsample just described. The standing flag on goalie ageing is updated to say so.

## What the source cannot see

The goalie source floors at about 100 minutes in net; the lightest season on record is two games.
A goaltender who dressed for one game, or relieved for a period, is absent, and absent is scored as
not having played. So the participation event here is "played a season the source records", which
for a goaltender means roughly two games or more. That is narrower than the one-game event the
skater side scores. The fit and the scoring use the same event, so the two halves agree.

## Whether he plays

| | predicted | observed | Brier score (lower is better) |
|---|---:|---:|---:|
| flat survival rate | 0.641 | 0.553 | 0.2470 |
| **participation model** | **0.580** | 0.553 | **0.2075** |

| horizon | observed | flat | model | Brier flat | Brier model |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.723 | 0.815 | 0.782 | 0.2084 | **0.1488** |
| 1 | 0.663 | 0.747 | 0.686 | 0.2306 | **0.1681** |
| 2 | 0.585 | 0.657 | 0.577 | 0.2480 | **0.1897** |
| 3 | 0.512 | 0.577 | 0.564 | 0.2544 | 0.2570 |
| 4 | 0.437 | 0.506 | 0.475 | 0.2511 | 0.2494 |
| 5 | 0.368 | 0.525 | 0.368 | 0.2965 | **0.2359** |

The model's Brier score is lower in **100%** of goaltender-resamples. Almost all of the gain is in the
first three horizons, where contract state and role are known. From three seasons out it roughly
ties the flat rate. The fits there rest on fewer pages and the contract export knows little that
far ahead.

## How much, if he plays

Scored only on the 2,035 seasons he actually played; the other seasons belong to the first question.

| share of the schedule | mean absolute error | bias |
|---|---:|---:|
| trailing share, carried flat | 0.1801 | +0.0129 |
| **share model** | **0.1686** | +0.0243 |

**The share model forecasts share better**, lower in 100% of goaltender-resamples.

## The season — and why the share model cannot be used yet

Season WAR, with ability held at production's projector in every arm:

| arm | mean abs error | bias | beats the stand-ins |
|---|---:|---:|---:|
| flat survival, trailing share (the stand-ins) | 1.488 | +0.100 | — |
| **participation model, trailing share** | **1.437** | +0.104 | **100%** |
| flat survival, share model | 1.581 | +0.234 | 0% |
| participation model and share model | 1.499 | +0.192 | 16% |

**The participation model improves the season forecast.** The share model forecasts share better and
still makes season WAR worse. The reason is how production's number is split up, and it shows up
tercile by tercile:

| trailing role | trailing share | modelled share | bias, flat share | bias, share model |
|---|---:|---:|---:|---:|
| backup-ish | 0.221 | 0.341 | +0.128 | **+0.543** |
| middle | 0.409 | 0.445 | +0.238 | +0.359 |
| starter-ish | 0.635 | 0.571 | −0.065 | −0.203 |

Production's projector gives a **season total** shrunk toward a league average of 2.19 WAR, which is
starter-level. To use it in rate × share × participation, the season total is divided by the
goalie's trailing share. For a backup that division inflates the implied rate, because his season
total has been pulled toward a starter's. With the flat share the harness multiplies the inflation
straight back out. With a modelled share that rises for backups (0.22 → 0.34, which is correct for
share), the inflated rate is multiplied by more, and backup bias rises from +0.13 to +0.54.

So **production's number cannot be split into a rate and a share**, and a better share forecast
cannot be plugged into it. Using the share model needs a goalie **rate** forecast, a per-82 number
shrunk toward a rate norm. That is the next thing to build.

## The pooled bias did not move

Fixing participation brought predicted play from 64.1% to 58.0% against 55.3% observed, and
**the pooled WAR bias stayed where it was** (+0.100 → +0.104). The model mostly lowers participation
for goaltenders who contribute little WAR anyway. That settles the earlier question empirically:
the +0.167 WAR figure in the bake-off report was an illustration of the participation term's size,
not a breakdown of the bias, and the remaining +0.10 comes from somewhere other than participation.

## The price line, refitted on the updated forecast

`run_goalie_price_line.py` now refits every line with the participation model in the goalie forecast
(production's projector for ability, trailing share for role). On the same 174 contracts:

| line | flat survival forecast | participation model forecast |
|---|---:|---:|
| no goaltender terms | 0.010318 | 0.009398 |
| goaltender level only | 0.007457 | 0.007292 |
| goaltender level and slope | 0.007489 | 0.007256 |
| level and slope beats level only in | 10% of resamples | 58% of resamples |

Every line is more accurate on the updated forecast, and **the level still carries the
improvement**: level-only beats no goaltender terms in 100% of resamples either way. The slope moves
from a clear loss to a coin flip, which is still not a result.

**The goaltender slope is not stable.** The whole-path response on the last fit:

| one more win every season | skater $M | goalie $M | ratio |
|---|---:|---:|---:|
| UFA, flat survival forecast | 2.022 | 2.167 | 1.07 |
| **UFA, participation model forecast** | **2.128** | **1.603** | **0.75** |
| RFA, participation model forecast | 1.955 | 1.429 | 0.73 |

The average goalie forecast moved by only −0.003 WAR (1.203 → 1.199), yet the goalie/skater ratio
went from 1.07 to 0.75. The participation model reorders goaltenders — starters up, backups down —
without moving the mean, and the goaltender slope estimate is sensitive to that reordering. That is
a second reason the slope has not earned its place. It is not identified robustly on 174 contracts,
and it will move again when the rate forecast is built. The skater response also moves slightly
(2.022 → 2.128), because the first-year and restricted terms are shared between the two positions.

**The goaltender specification stays provisional. Nothing here settles D7.**

## What is checked

- **The fit learns from every goaltender, not only the survivors.** With age excluded, the fit keeps
  every anchor it is given, so its base rate at each horizon equals those anchors' own played rate,
  to the digit. Putting age back opens a **0.53** gap, which the check catches.
- The participation fit and the share fit **ignore every season from the page onward**.
- The anchor builder's new `cols` option leaves the skater anchors **byte-identical**.

Suite: **34 passed, 0 skipped, 0 failed.**

## What this does not establish

- **Not a rate forecast.** Ability is production's season-total projector, which is why the share
  model cannot yet be used.
- **Not the one-game participation event** the skater side scores; the source floors at about 100
  minutes.
- **No ageing term.** Age is excluded because its availability is selected on the outcome. That is a
  limit on what this panel can say about goalie ageing.
- **Horizons three to five are thin.** Fits there rest on fewer pages, and the model roughly ties the
  flat rate.
- **Development pages only.**

## Files

    50_REBUILD/code/run_goalie_participation.py   the two models, the four arms, the scoring
    50_REBUILD/code/participation_model.py        v1.4: `exclude`
    50_REBUILD/code/ability_forecast.py           `_anchors(cols=...)`
    50_REBUILD/code/run_goalie_price_line.py      v2.1: refitted on the updated forecast

Writes `goalie_participation.csv`: every scored (arm, goaltender, page, horizon) cell.

## Next in the goalie branch

A goalie **rate** forecast: per-82 production shrunk toward a rate norm, so that rate × share ×
participation is a real decomposition and the share model can be used. Then the price comparison
again, and after that the control-year gate.
