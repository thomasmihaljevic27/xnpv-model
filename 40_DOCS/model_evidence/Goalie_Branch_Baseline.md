# The goalie branch: adopted baseline, frozen as a sensitivity

Recorded 2026-09-23 in `50_REBUILD/`. This closes the goalie branch of the plan's Phase 5. The
branch is **frozen as a sensitivity**: goaltenders are about 12% of the contract census (494 of 4,013), and the questions left
open below are not expected to move thesis-level results. Development pages and development start
years only. No production file is changed.

## What the baseline is

A goaltender's expected season is three things multiplied together: how good he is, how much of the
schedule he plays if he plays, and whether he plays at all. The adopted choice for each:

| part | adopted | where it was decided |
|---|---|---|
| how good (season total) | production's own goalie projector, imported and called | `Goalie_Bakeoff.md`, `Goalie_Rate_Forecast.md` |
| how much of the schedule | his trailing share, carried flat | `Goalie_Participation.md` |
| whether he plays | the goalie participation model with **no contract inputs** | `Goalie_Participation_Top.md` |
| the price of a forecast win | the pooled skater-and-goaltender line with a goaltender price **level** | `Goalie_Price_Line.md` |
| control years and dollar distributions | the shared control-year and simulation code | `Goalie_Control_Years.md` |

**No contract inputs was adopted on 2026-09-23.** The contract export is a snapshot of contracts
ending in 2018 or later, so its fields carried survival on early pages, and that led the old model
to predict retired goaltenders near-certain to play. Dropping contract inputs removes that signal. It
does so without a vendor-specific 2018 boundary and without assuming the export is complete. It is
**not** the winner on the declared dollar-accuracy score: on one fixed price line its squared dollar
error is slightly worse than the old model's (beats it in 32% of goaltender-resamples), while its
average dollar error is about zero. That trade-off is recorded, not hidden.

In code, the choice is one line: `run_goalie_participation.PART_VARIANT = "none"`. The scored arms
and the price runner both read it. The other specifications stay runnable by name (`--participation
as_known | observable | period_only | contract_only` on the control-year runner).

## The goalie results on the baseline

Every goalie runner was rerun on the baseline. Figures inside one run can be compared with each
other. **Dollar errors from different runs cannot**, because each run fits its own price lines and
so prices its realised target differently. Cross-specification dollar comparisons are made only on
one fixed line (the last table).

**Whether he plays** (`run_goalie_participation.py`):
- Brier 0.1958, against 0.2470 for the flat survival rate the bake-off used (lower in 100% of
  goaltender-resamples);
- predicted 0.538 against 0.553 observed;
- the confident fifth predicts 0.90 against 0.90 observed.

With production's projector and trailing share, season WAR error is 1.410 (bias +0.037), against
1.488 for the stand-ins.

**How good, per game or per season** (`run_goalie_rate.py`, participation now on the baseline):
- Production's season total remains the more accurate season forecast: RMSE 2.065, against
  2.091–2.098 for the rate arms, which beat it in 1% of resamples.
- With the share model, the rate decomposition has smaller biases across the role thirds (average
  0.065 against 0.118) and a pooled bias of about the same size (−0.03 against +0.04), but it ranks
  goaltenders less well.

The rate forecast stays a sensitivity.

**The price line** (`run_goalie_price_line.py`, 174 goaltender contracts):
- No goaltender terms: 0.009127 mean absolute error in cap share.
- A goaltender level: **0.006882**, better than no terms in 100% of resamples.
- A separate goaltender slope on top: 0.006954, better than the level alone in only 33%.

The level carries it and the slope has not earned its place. The goaltender-to-skater ratio for one
more expected win every season, unrestricted, is 0.77 (restricted 0.76). Across the forecast versions
tried it has read between 0.71 and 1.07, so the slope stays unstable and D7 (whether skaters and
goaltenders share one market) is not settled.

With no contract inputs, participation no longer depends on the signing date (it moves on 0 of 205
contracts). Scored on the priced contracts' own seasons, participation now runs low: the first
season is predicted 0.712 against 0.761 played (about five points low), and the second 0.687 against
0.794 (about eleven points low).

**Control years and dollars** (`run_goalie_control_years.py`, on its own lines):
- Deciding as you go, the control years of the 21 contracts that own them and reach the simulation
  are worth $1.051M on production's forecast and $1.091M on the rate forecast (rank correlation
  0.938). Production's rule gives $0.118M, and seeing the path adds $0.05M.
- The 21 are selected toward goaltenders with an NHL record: 74 development contracts own control
  years.
- Against realised dollars, on this run's production line, 133 ended terms: production's simulated
  value has RMSE $7.111M and bias +$0.082M. The rate forecast's has lower squared error in 30% of
  resamples and lower absolute error in 99%.

Calibration, allowing for the floor's lump (randomized PIT):

| | production | rate |
|---|---:|---:|
| PIT mean (0.5 if calibrated) | 0.486 [0.439, 0.531] | 0.512 [0.464, 0.560] |
| PIT variance (0.083 if calibrated) | 0.082 [0.071, 0.091] | 0.087 [0.076, 0.097] |
| excess of floor-level outcomes over the model's own share | +5.0 [−2.3, +12.9] | +2.2 [−5.3, +10.1] |

The pooled diagnostics did not detect miscalibration in these statistics. That is weaker than
"calibrated": subgroups can still be off.

**Contract dollars across participation specifications, on one fixed line** (the old specification's
production line; realised target asserted identical across runs; 133 ended contracts; production
forecast):

| participation | RMSE | MAE | bias | beats the old specification on squared error |
|---|---:|---:|---:|---:|
| old: export membership | 6.882 | 3.985 | +0.566 | — |
| observable (period + contract status) | 6.880 | 3.849 | +0.187 | 51% |
| period only | 6.932 | 3.766 | −0.064 | 33% |
| **none (adopted)** | 6.932 | 3.808 | **−0.007** | 32% |

For the rate forecast, the adopted baseline's squared dollar error is also worse than the old
specification's (7.035 against 6.923; 10%).

The adopted baseline removes the average dollar error and lowers absolute error, at a small cost in
squared dollar error, which is the declared primary score. The independent closure review reported
the same row (6.931, −0.006); the last-digit differences are rounding.

## Kept as sensitivities

- **The rate decomposition** (per-82 rate × share model × participation): better calibrated, less
  sharp.
- **The share model** for the share of the schedule: it improves squared error only with the rate
  forecast.
- **Participation with contract inputs:** export membership (the old model), observable, period only
  and contract only.
- **Each forecast on its own price line**, beside the common-currency comparison.

## Deferred, and why they need not hold the branch open

- **A time adjustment not tied to the vendor's coverage year** (recency weighting of the training
  rows). The period indicator's gain is real on participation but did not carry into dollars.
- **Goalie participation on the priced contracts' own seasons**, now about five points low in the
  first season and eleven in the second. These are goaltenders who have just signed, a group the
  pooled harness does not isolate.
- **The joint distribution of rate and workload** for paths through the floor or a control option.
  The games-weighted rate times the mean share is the expected season; the distribution around it is
  not specified.
- **Control values for goaltenders without an NHL record**, outside the simulated sample by
  construction.
- **D7**, whether skaters and goaltenders share one market: the level is established, the slope is
  not.
- **Stated limits carried forward:**
  - forecasts beyond five seasons hold the last fitted horizon;
  - the qualifying offer runs off the average annual value;
  - eligibility is the export's year (8 of 174 priced contracts go early, through accrued seasons or
    Group VI);
  - the vendor snapshot's coverage is assumed.

## What is checked

The suite covers the goalie branch in:
- **checks 29–41:** the panel, the page guards, production's projector, the pooled price line,
  participation, the rank rule, the rate forecast, forecast-to-price parity, replay dating, the
  persistence fit, calibration with lumps, and the observable definition;
- **the runner's own assertions:** the folded price line, the simulated forecast equal to the priced
  one, the realised target identical across forecasts, and nothing beating hindsight.

Check 34's signing-date test is pinned to a specification that reads contract state, because the
baseline no longer does.

Suite: **41 passed, 0 skipped, 0 failed**.
