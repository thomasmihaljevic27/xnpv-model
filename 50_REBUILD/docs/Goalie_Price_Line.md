# How the market prices a goaltender's forecast

Run 2026-09-22 in `50_REBUILD/` (v2.0, after an independent review). The goalie branch of the
plan's Phase 5, second step. Development start years only. **Nothing adopted, and no production
file changed. The goaltender price specification is provisional.**

The first version of this report (2026-09-18) made two claims that are withdrawn: that a goaltender
needs both its own price level **and** its own win slope, "settling" the single-market question for
goaltenders; and that a goalie win prices at 1.18 times a skater win. The first compared the wrong
alternatives; the second quoted a partial slope as though it were the whole response. What survives
is narrower and set out below. The corrections are listed at the end.

## Why this question

The project puts three asset classes on one scale, and that scale runs through a forecast win. So
before a goaltender can be valued beside a skater, the market's treatment of a goaltender's forecast
has to be measured: does the price line that fits skaters fit goaltenders, and if not, how does it
differ?

One censored price line over skaters and goaltenders together, refitted at each signing quarter on
the contracts signed before it. The forecast feeding the goalie side is production's own projector,
the bake-off's winner. Its pooled mean error of +0.101 WAR is not corrected and no price is moved to
cancel it — that is a diagnostic for the participation model, not a defect to price around.

## The sample, stage by stage

| development goaltender contracts | |
|---|---:|
| eligible in the census | 263 |
| with a forecast from production's projector | 205 |
| priced out of sample on the pooled line | 174 |

Against 1,458 development skater contracts with a forecast. The first version quoted 266, a count
taken before the census applies its signing-date rule.

## Which goaltender adjustment the evidence supports

Held-out error on the **same 174 goaltender contracts**, in cap share. Every line is refitted at each
quarterly cutoff on an expanding sample of the contracts signed before it — the same scheme for all
four. (The first version said the goalie-only line used a different window. It did not.)

| line | goalie contracts | mean absolute error | bias |
|---|---:|---:|---:|
| no goaltender terms | 174 | 0.010318 | +0.006627 |
| **goaltender level only** | **174** | **0.007457** | **+0.000145** |
| goaltender level and slope | 174 | 0.007489 | +0.000140 |
| a goalie-only line | 5 | — | too few to read |

Resampling the 102 goaltenders rather than the contracts:

| comparison | change in mean absolute error | better in |
|---|---:|---:|
| level only, against no goaltender terms | −0.002861 | **100%** of resamples |
| level and slope, against level only | +0.000032 | **10%** of resamples |

**What this supports: goaltenders need an adjustment on the shared line, and a different price
level on the same win slope delivers all of the improvement.** Adding a goaltender slope on top has
not earned its place — it is marginally worse and wins a tenth of resamples.

**What it does not support.** It is not evidence that the two slopes are equal: 174 contracts cannot
tell a small slope difference from none. And it does not settle the single-market question for
goaltenders, which the first version claimed. The specification stays provisional while the goalie
participation model is built, because that model changes the forecast this line prices.

The goalie-only line needs 200 contracts signed before each decision and the development sample
holds 205 with a forecast in total, so it becomes fittable only at the very end of the window and
prices five contracts. Unavailable rather than unattractive.

Cap share, not dollars: 0.01 is a percentage point of the ceiling, about $0.8M on a 2021 cap.

## What the line says about a goalie win — and what that number means

The coefficient first reported as "dollars per win" is a **partial slope**: the change in the fitted
annual price when the season-average forecast rises by one win with **first-year production held
fixed**, for an **unrestricted** player. That is not what a better player is worth, because a better
player's first year moves too.

On the last fit (contracts signed before January 2022, 1,657 of them), defining the change
explicitly:

| the change in expected production | skater $M | goalie $M | ratio |
|---|---:|---:|---:|
| partial slope, first year held fixed (UFA) | 0.820 | 0.965 | 1.18 |
| **one more win in every season, UFA** | **2.022** | **2.167** | **1.07** |
| one more win in every season, RFA | 1.928 | 2.073 | 1.08 |

These are changes in the fitted **annual price, before the league-minimum floor**. They are not
contract values and must not be quoted as NPVs.

The goaltender gap is the same $0.145M in every row, because it is one coefficient — so the *ratio*
depends entirely on which change is being priced. Against the whole-path response it is about
**1.07**, not the 1.18 first reported.

Over the window the partial-slope ratio runs 0.74 to 1.57, with the spread almost entirely in fits
under about 600 contracts:

| fitted on contracts signed before | contracts | skater, partial | goalie, partial | ratio |
|---|---:|---:|---:|---:|
| 2018-07 | 365 | 0.212 | 0.264 | 1.25 |
| 2019-10 | 947 | 1.316 | 1.321 | 1.00 |
| 2021-01 | 1,270 | 0.899 | 1.047 | 1.16 |
| 2022-01 | 1,657 | 0.820 | 0.965 | 1.18 |

And given the level-only result above, the goaltender slope term these rows read is itself one the
evidence has not asked for.

**A conditional association between matched cases, not the price of a win.** Nobody randomised which
players got which contracts. And a goaltender's forecast is built by a different rule from a
skater's — flat where the skater ages, shrunk far harder, measured on 82 seasons a year — so part of
any difference between the two is the difference between two priced objects.

## What is checked

- The pooled line **recovers a goalie slope it was given** on synthetic contracts (0.0049 against
  0.0050), and first-year production priced at nothing comes back at nothing.
- The **whole-path response moves every term the forecast enters** — the season average, the first
  year, the restricted interaction for a restricted player, the goaltender interaction for a
  goaltender — and the partial slope is not passed off as it. Verified by substituting the partial
  slope, which the check catches.
- The **level-only specification is a separate line**: goaltender level, no goaltender slope.
- The fit **cannot see a contract signed after the decision**.

Suite: **33 passed, 0 skipped, 0 failed.**

## What this does not establish

- **Not a causal price**, and not the value of a win.
- **Not an equal-slopes result.** The slope term did not earn its place; that is different from
  being shown to be zero.
- **Not the single-market question settled**, for goaltenders or anyone.
- **The two forecasts are on different footings**, so part of every goalie-skater comparison is the
  forecasts.
- **No goalie participation model yet.** The forecast carries a flat survival rate, and the model
  that replaces it moves the input this line prices.
- **Development starts only**; the confirmatory cohorts are sealed.

## Files

    50_REBUILD/code/run_goalie_price_line.py

Writes `goalie_price_line.csv`: one row per signing quarter with the partial slopes and the
goaltender level term. `contract_price_model.contract_sample` takes a position group, so both
samples come off one census with one set of rules.

## What the first version got wrong

1. **It compared the wrong alternatives.** No goaltender terms against level *and* slope left out
   level alone — which, on the same contracts, delivers all of the improvement. The claim that both
   terms are needed, and that this settled the single-market question for goaltenders, is withdrawn.
2. **It quoted a partial slope as "dollars per win".** The coefficient on the season average holds
   first-year production fixed and omits the restricted interaction. The whole-path response is
   $2.022M against $2.167M for unrestricted players, a ratio of 1.07 rather than 1.18.
3. **Smaller:** the sample was quoted at 266 rather than 263 → 205 → 174; the goalie-only line was
   said to use a different window when every line uses the same expanding quarterly scheme; and the
   +0.167 WAR participation figure in the forecast report was read as a decomposition of the bias
   when it is an illustration of the participation term's scale.

## Next in the goalie branch

The participation model. Both the forecast and this price line currently carry a flat survival rate
where a goaltender's share of the schedule — a depth-chart question — should be.
