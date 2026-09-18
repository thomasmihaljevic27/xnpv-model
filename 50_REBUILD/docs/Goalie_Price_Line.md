# Is a goalie win priced like a skater win?

Run 2026-09-18 in `50_REBUILD/`. The goalie branch of the plan's Phase 5, second step. Development
start years only. **Nothing adopted, and no production file changed.**

## Why this question

The contribution of this project is putting three asset classes on **one** scale, and that scale is
dollars per forecast win. So before a goaltender can be valued beside a skater, one thing has to be
settled: does the market pay the same for a win from a goaltender as it pays for a win from a
skater?

It has a testable answer. Fit one censored price line over skaters and goaltenders together with a
goaltender indicator and an interaction, refitted at each signing quarter on contracts signed
before it, and read the interaction — it **is** the difference in dollars per forecast win.

## What feeds it

The forecast chosen in the bake-off: **production's own goalie projector**, imported and called at
each signing's page. It was the best of the seven candidates scored there and nothing beat it.

Its pooled mean error of +0.101 WAR is **not corrected here and no price is moved to cancel it**.
That number's career-bootstrap interval spans zero, and the participation estimator it was measured
with over-predicts playing by nearly nine points — a gap worth more than the whole observed bias. It
is a diagnostic for the participation model to take up, not a defect to price around.

## What the market pays

| fitted on contracts signed before | contracts | $ per skater win | $ per goalie win | ratio |
|---|---:|---:|---:|---:|
| 2017-10 | 272 | 0.266 | 0.367 | 1.38 |
| 2018-07 | 365 | 0.212 | 0.264 | 1.25 |
| 2018-10 | 601 | 0.535 | 0.395 | 0.74 |
| 2019-07 | 713 | 1.326 | 1.212 | 0.91 |
| 2019-10 | 947 | 1.316 | 1.321 | 1.00 |
| 2020-07 | 1,004 | 1.195 | 1.256 | 1.05 |
| 2021-01 | 1,270 | 0.899 | 1.047 | 1.16 |
| 2021-10 | 1,638 | 0.652 | 0.794 | 1.22 |
| **2022-01** | **1,657** | **0.820** | **0.965** | **1.18** |

On the last fit a forecast win from a goaltender prices at **$0.96M** against **$0.82M** from a
skater. Across the window the ratio runs 0.74 to 1.57, and **the spread is almost entirely in the
early fits**: under about 600 contracts the interaction is not pinned down at all, and from 900
contracts on it settles between 0.87 and 1.22.

**This is a conditional association, not the price of a win.** Nobody randomised which players got
which contracts. And a goaltender's forecast is built by a different rule from a skater's — flat
where the skater ages, shrunk far harder, measured on 82 seasons a year — so a difference in the
fitted slope is a difference between **two priced objects**, not proof that clubs value a
goaltender's win differently. The forecast's own scale is part of what is being compared. Anything
downstream that reads this as "clubs underpay goaltenders" is reading it wrong.

## Does a goaltender belong on the skaters' line?

Held-out error on goaltender contracts, in cap share, each line fitted only on contracts signed
before the one it prices.

| line | goalie contracts priced | mean absolute error | bias |
|---|---:|---:|---:|
| one line, no goaltender terms | 174 | 0.0103 | +0.0066 |
| **one line with goaltender terms** | **174** | **0.0075** | **+0.0001** |
| a goalie-only line | 5 | 0.0056 | +0.0056 |

Cap share, not dollars: 0.01 is a percentage point of the ceiling, about $0.9M on a 2021 cap.

**The goalie-only line never gets off the ground.** It needs 200 contracts signed before the
decision and the development sample holds 266 in total, so it first becomes fittable in the last
quarter of the window and prices five contracts. Its error is not a result; it is printed to show
the option is unavailable rather than unattractive.

**What is a result: a goaltender does not belong on the skaters' line unchanged.** Adding the two
goaltender terms cuts held-out error on goalie contracts by **more than a quarter** and takes the
bias from +0.0066 to nothing. Both the level and the slope differ, and one line with goaltender
terms is the only one of the three this sample can both fit and defend.

That is an answer to the open question behind D7's single market, for goaltenders specifically:
**one market, two terms** — not one line for everybody, and not a separate market.

## What this does not establish

- **Not a causal price.** See above; it is a conditional association between a forecast and a cap
  share in an unrandomised market.
- **The two forecasts are not on the same footing.** The skater side is the rebuild's own leader
  with an aging path; the goalie side is production's flat, heavily-shrunk projector. Part of any
  slope difference is that difference.
- **266 development goalie contracts**, of which 174 are priced out of sample here. The early fits
  are unusable and the late ones rest on a few hundred goalie contracts inside a pooled sample.
- **No participation model yet**, so a goaltender's forecast carries the shared flat survival rate
  rather than a modelled one. That is the next step and it moves this input.
- **Development starts only**; the confirmatory cohorts are sealed.

## What is checked

- The pooled line **recovers a goalie slope it was given**: on synthetic contracts built with a
  known interaction, the fitted coefficient comes back at 0.0049 against 0.0050 given, first-year
  production priced at nothing comes back at nothing, and the dollars helper adds the interaction to
  the base slope rather than replacing it.
- The fit **cannot see a contract signed after the decision**: adding a later cohort at a wildly
  different price leaves every coefficient unmoved.

Both verified by breaking them — reading the interaction as the whole goalie slope, and removing the
signing-date filter.

Suite: **33 passed, 0 skipped, 0 failed.**

## Files

    50_REBUILD/code/run_goalie_price_line.py

Writes `goalie_price_line.csv`: one row per signing quarter with the fitted dollars per win for each
side and the goaltender level term. Outputs ignored under `50_REBUILD/output/`.

`contract_price_model.contract_sample` now takes a position group rather than assuming skaters, so
the two samples come off one census with one set of rules for the cap-share denominator, the
league-minimum floor and the signing date.

## Next in the goalie branch

The participation model — a goaltender's share of the schedule is a depth-chart question, and both
the forecast and this price line currently carry a flat survival rate in its place. The control-year
gate the plan asks for comes after that, because a goaltender's tender decision is a depth-chart
decision as much as a value one.
