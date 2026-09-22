# Will he play, and how much? The goalie participation model

Run 2026-09-22 in `50_REBUILD/` (v2, after an independent review). The goalie branch of the plan's Phase 5, third step. Development
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

## Why an independent rerun disagreed, and what fixed it

The first version reported a Brier score of 0.2075 and a season-WAR error of 1.437. An independent
rerun got 0.2101 and 1.446, concentrated at two seasons out (predicted participation 0.633 against
0.577). Both runs were deterministic on their own machines, so the difference was between machines.

**The cause is a singular design that the machine, not the data, resolved.** When every goaltender
the contract export knows about is also under contract for the season, `under_contract` is exactly
`1 - contract_unknown` and the logistic design loses a rank. On this machine the regularised fit
reported convergence with an arbitrary split between the two columns on one such fit (+6.88 against
−3.99, 2018 page, one season out) and raised a singular-Hessian error on another (2019 page, two
seasons out), falling back to fewer features. Which of those happens depends on floating-point
details that differ between platforms — so on a different machine the same rows can take the other
branch, and the difference lands exactly at the horizons where the columns collide. That this is what
happened on the reviewer's machine is inferred from where the difference sits; it could not be
observed directly.

`participation_model` v1.5 no longer lets a singular design reach the optimiser: redundant columns
are dropped in a fixed order until the design has full rank, so every machine makes the same choice.
Three goalie fits collide (2018 one out, 2019 one and two out) and now resolve identically every time.
The corrected figures above are the ones from full-rank designs.

**The same defect was in the skater model, and it changes a recorded result.** Fifteen skater fits in
the contract-using variants were singular. There the arbitrary split reproduced the training rows and
over-predicted participation on the page by up to fifteen points — 0.556 against an observed 0.406 on
the 2019 page five seasons out. The standing leader fits participation without contract data and has
no singular fits, so it is unaffected. But the Phase 2 finding that contract data *hurts* the forecast
by about 0.9% was measured with this defect, and re-measured after the fix it is close to a tie on
season WAR (+0.03% to +0.27%) with contract data better on participation itself. See the correction in
`Phase2_Participation.md`.

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
| **participation model** | **0.575** | 0.553 | **0.2056** |

| horizon | observed | flat | model | Brier flat | Brier model |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.723 | 0.815 | 0.782 | 0.2084 | **0.1488** |
| 1 | 0.663 | 0.747 | 0.654 | 0.2306 | **0.1549** |
| 2 | 0.585 | 0.657 | 0.578 | 0.2480 | **0.1919** |
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
| **participation model, trailing share** | **1.432** | +0.096 | **100%** |
| flat survival, share model | 1.581 | +0.234 | 0% |
| participation model and share model | 1.492 | +0.183 | 36% |

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

> **Tested since (`Goalie_Rate_Forecast.md`).** A per-82 rate forecast was built. With it, the share
> model no longer worsens squared error (−0.020 to −0.027) and the combined forecast is the best
> calibrated of every arm, overall and by role. But it still worsens mean absolute error, and
> production's season total remains the more accurate season forecast on both scores. The diagnosis
> above holds in part, not in full.

## The pooled bias is not eliminated, and its causes are unresolved

The participation model improves accuracy and brings predicted participation much closer to the
observed rate, but it **does not eliminate the pooled WAR bias**. The first version of this report
went further and said that, since participation was now roughly right, the remaining bias "comes
from somewhere other than participation". That does not follow. Average participation can improve
while errors for high-production and low-production goaltenders offset differently once they are
weighted by WAR — a model that lowers the chance of playing for backups and raises it for starters
can move the pooled bias in either direction or not at all. **What causes the remaining bias is not
established here.**

## The price line, refitted on the updated forecast

`run_goalie_price_line.py` refits every line with the participation model in the goalie forecast
(production's projector for ability, trailing share for role).

**Contract state is now read at the signing.** The first version read it at 1 July of the page, so a
deal signed later in the summer was priced by a model that could not see it. Dated at the signing,
participation changes on **95 of 205** contracts. Jon Gillies, signed 16 July 2018: first season
44.4% → 92.7%, second 41.2% → 99.5%.

**Correctly dated is not the same as calibrated**, so the priced contracts' own seasons are scored
against whether he actually played them:

| season | contracts | played | flat rate | read at 1 July | read at the signing |
|---|---:|---:|---:|---:|---:|
| first | 205 | 0.761 | 0.803 | 0.749 | 0.822 |
| second | 107 | 0.794 | 0.721 | 0.710 | **0.797** |

Read at the signing, the second season is calibrated almost exactly; the first runs about six points
high. A plausible reason, not tested here: the model was fitted on contract state as known at 1 July
of each training page, and "under contract" for a deal known on 1 July is a different population
from "just signed this contract". It is recorded as a known calibration gap rather than corrected.

**The forecast moves materially, not slightly.** Against the flat-survival forecast the season
average moves by +0.111 WAR on average, **0.223 WAR on average in absolute terms, and up to 1.235**.
The first version quoted only the mean move (−0.003 at the time) and called the price-ratio change a
response to a tiny perturbation; the mean hid the movement.

On the same 174 contracts:

| line | flat survival forecast | participation model, dated at the signing |
|---|---:|---:|
| no goaltender terms | 0.010318 | 0.010001 |
| goaltender level only | 0.007457 | **0.007017** |
| goaltender level and slope | 0.007489 | 0.007153 |
| level and slope beats level only in | 10% of resamples | 22% of resamples |

**The level still carries the improvement**, in 100% of resamples either way, and the slope still
has not earned its place.

| one more win every season, last fit | skater $M | goalie $M | ratio |
|---|---:|---:|---:|
| UFA, flat survival forecast | 2.022 | 2.167 | 1.07 |
| UFA, participation model dated at the signing | 2.079 | 1.642 | **0.79** |
| RFA, participation model dated at the signing | 1.949 | 1.512 | 0.78 |

The goaltender slope changes a great deal under a materially different forecast, which is one more
reason it is not identified on 174 contracts. **The goaltender specification stays provisional.
Nothing here settles D7.**

## What is checked

- **Every goaltender, not the survivors.** With age excluded the fit keeps every anchor, so its base
  rate equals the anchors' own played rate at every horizon; putting age back opens a 0.53 gap.
- **The future is ignored when it is handed over.** The whole table, future seasons included, goes
  into the participation fit clean and scrambled, and the coefficients agree with each other and with
  a fit on the truncated table. (The first version of this check removed the future before fitting,
  so both fits saw identical inputs.) The share model refuses a table that reaches the page.
- **The predictions are a fitted model.** In-sample they reproduce the base rate and they separate
  goaltenders; a constant 99.9% predictor, which passed the first version, now fails.
- **Contract state is read at the date asked for.** A deal signed 16 July is visible on 16 July and
  not on 1 July; and the price runner asks at the signing — Gillies prices his first season higher
  dated at the signing than at 1 July.
- **No fit is handed a singular design.** The redundant column is dropped in a fixed order, a
  full-rank design is left alone, and the colliding goalie fits resolve identically on every run.
- The anchor builder's `cols` option leaves the skater anchors byte-identical.

## What this does not establish

- **Not a rate forecast.** Ability is production's season-total projector, which is why the share
  model cannot yet be used.
- **Not the one-game participation event** the skater side scores; the source floors at about 100
  minutes.
- **No ageing term.** Age is excluded because its availability is selected on the outcome. That is a
  limit on what this panel can say about goalie ageing.
- **The first season of a signing-dated forecast runs about six points high** on the priced contracts.
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
