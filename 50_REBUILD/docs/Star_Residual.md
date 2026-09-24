# The star residual: located in the aging walk, retained as a stated limitation

**Updated 2026-09-24 (v1.1):** the no-level result below changed the curve's sample as well as its formula. The matched comparison and the next aging candidate are in "The matched comparison, and a second level slope".

Run 2026-09-24 in `50_REBUILD/` (`run_star_residual.py` v1.0–v1.4; `ability_forecast.py` v2.6; `aging_additive.py` v1.4; diagnostic `run_star_walk_diagnostic.py` v1.0).
Development pages and development start years only. **Nothing adopted.**

## Where the miss is

The adopted skater leader (visible contract status in participation, adopted provisionally
2026-09-23) under-rates its best players. For players whose trailing total is three wins or more,
split into the two halves of a season forecast (rate per 82 games among seasons played, and season
WAR over every forecast):

| seasons ahead | predicted rate | actual rate (played) | rate miss | season WAR miss |
|---|---:|---:|---:|---:|
| valuation season | 3.24 | 3.26 | −0.03 | −0.17 |
| one | 2.99 | 3.26 | −0.27 | −0.42 |
| three | 2.47 | 3.10 | −0.63 | −0.64 |
| five | 1.90 | 2.82 | −0.92 | −0.87 |

**The starting point is right; the path forward is too steep.** The forecast walks a star's rate
down about 0.27 wins per 82 games a season. The stars who kept playing lost about 0.09. Every
trailing tier shows the same too-steep walk, smaller (five seasons out: −0.07 below replacement,
−0.13 for 0–1, −0.23 for 1–2, −0.29 for 2–3).

That is why the earlier repair recovered only a fifth of the gap: the hinge and evidence terms
changed the valuation-season fit, where the stars' rate was already about right.

**A caution on the rate column.** It is measured on seasons played, and the stars who played five
seasons later are a selected group. The season WAR column counts every forecast, played or not,
and shows the same growing miss, so selection does not explain it away. It could still inflate the
rate column's size.

## Three changes, scored

**Correction (after review): only two of the three were single changes.** Removing the aging
curve's level terms also changed the curve's training sample. The lagged-level fit drops every pair
with no season before the change (its level is missing), and the no-level fit kept them: 7,164 rows
against 9,459 on the 2021 page. So the "no level terms" row below changed the formula and the
sample together. The matched comparison, same rows and weights, is in the next section. (The code
comment that said such rows were "fitted on age and position alone rather than dropped" was wrong
and is corrected.)

Each is the adopted leader with the stated change; participation, games share and the
valuation-season rate are identical (Brier and first-season participation are unchanged to four
decimals in every version, which checks that).

| version | what changes |
|---|---|
| survivors-only curve | the aging curve fitted without the replacement-level seasons imputed for departing players. The forecast rate is conditional on playing, and leaving the league is priced by the participation model, so the imputed curve may count an exit twice. |
| no level terms | the aging curve on age and position alone, so a star is not walked down faster for being a star; **also admits 2,295 more training rows (2021 page)** |
| per-season regression | the rate at each horizon from that horizon's own regression on the anchor (fitted on seasons played), instead of walking the valuation-season rate forward |

The scores were declared in the runner before it ran. Shares are exact counts of 2,000
player-resamples in which the version's error is lower than the adopted leader's.

**Season WAR, every player (primary):**

| version | RMSE | lower than adopted | MAE | bias |
|---|---:|---:|---:|---:|
| adopted | 0.8151 | — | 0.4565 | −0.067 |
| survivors-only curve | 0.8146 | 1601/2000 | 0.4584 | −0.076 |
| no level terms | 0.8147 | 1130/2000 | 0.4619 | −0.073 |
| per-season regression | 0.8144 | 1288/2000 | 0.4676 | −0.037 |

None separates from the adopted leader on squared error, and all three are worse on absolute error.

**The residual itself, three-win-and-up tier:**

| seasons ahead | adopted | survivors-only | no level terms | per-season regression |
|---|---:|---:|---:|---:|
| rate miss, one | −0.27 | −0.23 | −0.13 | −0.29 |
| rate miss, three | −0.63 | −0.55 | −0.22 | −0.60 |
| rate miss, five | −0.92 | −0.83 | −0.26 | −0.68 |
| season WAR miss, five | −0.87 | −0.80 | −0.45 | −0.74 |

| version | tier RMSE | tier bias | tier error lower than adopted |
|---|---:|---:|---:|
| adopted | 1.859 | −0.549 | — |
| survivors-only curve | 1.844 | −0.503 | 1998/2000 |
| no level terms | 1.801 | −0.298 | 1975/2000 |
| per-season regression | 1.873 | −0.529 | 546/2000 |

The top tenth of each version's own predictions misses by −0.30 (adopted), −0.29, −0.21 and −0.31.

**What the level terms do to everyone else**, rate miss five seasons out:

| tier | adopted | survivors-only | no level terms | per-season regression |
|---|---:|---:|---:|---:|
| below 0 | −0.07 | −0.17 | −0.36 | +0.18 |
| 0 to 1 | −0.13 | −0.20 | −0.29 | +0.10 |
| 1 to 2 | −0.23 | −0.26 | −0.17 | −0.03 |
| 2 to 3 | −0.29 | −0.27 | +0.02 | −0.08 |
| 3+ | −0.92 | −0.83 | −0.26 | −0.68 |

**Contract dollars** (1,176 ended terms, realised target asserted identical across versions):

| line | adopted RMSE | survivors-only | no level terms | per-season regression |
|---|---:|---:|---:|---:|
| adopted's (primary) | $3.513M | $3.512M, 1065/2000 | $3.500M, 1183/2000 | $3.507M, 1212/2000 |
| per-season regression's (sensitivity) | $3.758M | $3.760M, 537/2000 | $3.767M, 449/2000 | $3.765M, 734/2000 |

Nothing separates in dollars either, and the direction flips between the two lines.

## What this says

- **The star residual is the aging walk, and mostly its level terms.** Removing the level terms
  (with the sample change; see the matched comparison) takes the stars' five-season rate miss from
  −0.92 to −0.26 and their season WAR bias from −0.55
  to −0.30, with the tier's squared error lower in 1,975 of 2,000 resamples. Fitting the curve on
  survivors helps a little (−0.83); the per-season regression does not help stars.
- **The level terms are also what keeps the lower tiers right.** Without them the two lowest tiers
  are walked down too fast (below replacement −0.07 to −0.36). One version of the reading that one
  slope was doing two jobs (a second slope above 2 wins, v1.1) did not help: see below.
- **No candidate improves the declared primary scores.** Pooled season WAR squared error and
  contract dollars do not separate from the adopted leader, and absolute error is worse for all
  three. By the rule declared before the run, none is adopted, and no combination is scored
  (neither single improves a primary score).
- **For the thesis the star tier is where the money is**, so a repair that fixes it without
  breaking the lower tiers is worth designing. The first shape tried (a second slope above 2 wins,
  v1.1) did nothing; the next follows from the diagnostic below.

## The matched comparison, and a second level slope (v1.1)

`run_star_residual.py` v1.1. Two new versions, each fitted on the adopted curve's rows and weights
(check 46 asserts the fingerprint): the curve without level terms, matched; and the adopted curve
with a second level slope (and its age interaction) above a lagged 2.0 wins per 82, the knot
declared before the run and not searched.

| version | pooled WAR RMSE | lower than adopted | WAR MAE | stars' five-season rate miss | lowest tier's | star tier error lower than adopted | dollars, adopted line | dollars, hinge line |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adopted | 0.8151 | — | 0.4565 | −0.921 | −0.068 | — | — | — |
| no level terms, unmatched (v1.0) | 0.8147 | 1130/2000 | 0.4619 | −0.261 | −0.364 | 1975/2000 | 1183/2000 | 1118/2000 |
| no level terms, same rows | 0.8133 | 1610/2000 | 0.4628 | −0.328 | −0.351 | 1993/2000 | 1531/2000 | 1473/2000 |
| second level slope above 2 | 0.8154 | 263/2000 | 0.4562 | −0.925 | −0.065 | 1962/2000 | 180/2000 | 203/2000 |

(The lowest tier is the below-replacement trailing tier. The hinge row's star-tier share is on a
0.004 RMSE difference.)

- **The finding survives the matched comparison.** On the same rows, dropping the level terms still
  takes most of the stars' miss away (−0.92 to −0.33) and still walks the lowest tier down too fast
  (−0.07 to −0.35). The sample change accounted for part of the star gain (−0.26 unmatched).
- **It is still not an improvement on the declared primary scores.** Pooled squared error is lower in
  1,610 of 2,000 resamples, dollars in 1,531 (adopted line) and 1,473 (hinge line); absolute error is
  worse. Not adopted.
- **A second level slope above 2 wins barely moves the stars' five-season miss** (−0.925 against
  −0.921) and is worse overall (263 of 2,000; dollars 180 and 203). It slightly improves the stars'
  pooled season error (1.8591 to 1.8547, lower in 1,962 of 2,000), which is not a repair of the
  long-horizon bias. Not adopted. This rejects that construction, a hinge at 2 wins; it does not
  show that no level effect differing by tier could explain the miss.

**Why the curve and the forecast disagree (diagnostic, 2021 page).** On its own training pairs the
curve matches what happened: grouped by the previous season's rate, players at 3+ lost 0.23 per 82
the next season against 0.27 fitted (the fit is steeper by design, since it includes the imputed
departures). Grouped by the rate the change starts from, the same pairs show the full regression to
the mean (−1.15 for a 3+ starting season), which the lagged level exists to keep out.

So the curve describes single-season numbers faithfully, and the forecast applies it to something
different: a multi-season, shrunk rating, where a star's 3.24 is mostly ability. A level slope
measured against one noisy season still carries the fading of the part of a good season that
persists for a year or two (role, linemates, luck that lasts), which the shrunk rating has already
removed. Applied to that rating, the curve pulls stars back a second time. This is a hypothesis
consistent with the numbers, not a measurement of it.

**The next candidate that followed from it:** fit the curve's level on a multi-season weighted rate
ending the season before the change, on the same rows. Scored in v1.2 below: it did not help, and
its fitted slope moved the opposite way to the hypothesis.

## The multi-season level (v1.2)

`run_star_residual.py` v1.2; `A1StatusAgingMultiLevel`. The aging curve's level is a weighted rate
over the three seasons before the change (weights 1, 0.667, 0.444, renormalised over the seasons
played; the season just before is required, so the rows and weights are the adopted curve's, check
46). It is still dated before the change it predicts. Season alignment, stated: the training level
ends the season before the change starts, while the walk supplies the projected level of the season
the change starts from, as it does for the adopted curve; a projected level and a weighted past
rate are not the same quantity.

**Recorded before the run:** on the 2021 page the multi-season level makes the curve's level slope
steeper, not flatter (−0.071 against −0.062 per win; a 3.2-win 27-year-old's yearly step −0.265
against −0.251). The "pulled back twice" reading predicted a flatter slope, so the prediction was
no gain for stars.

| version | pooled WAR RMSE | lower than adopted | stars' five-season rate miss | lowest tier's | star tier error lower than adopted | dollars, adopted line | dollars, multi-level line |
|---|---:|---:|---:|---:|---:|---:|---:|
| adopted | 0.8151 | — | −0.921 | −0.068 | — | — | — |
| no level terms, same rows (reference) | 0.8133 | 1610/2000 | −0.328 | −0.351 | 1993/2000 | 1531/2000 | 1588/2000 |
| multi-season level | 0.8153 | 234/2000 | −0.956 | −0.025 | 1/2000 | 826/2000 | 778/2000 |

**The prediction held: no gain, and slightly worse for stars.** Not adopted.

**What it rules out, and what it does not.** This substitution did not help, and it moved the
fitted level slope the opposite way to what the "pulled back twice" reading expected. That rejects
this particular repair. It does not reject double shrinkage as a mechanism: the substituted input
is still a weighted history, while the walk still passes a projected current-season level to a
relationship fitted on a level ending one season earlier (corrected after review; the first version
of this paragraph said the result "rejects this explanation").

Why the forecast walks stars down about 0.27 a season while the stars it forecast lost about 0.09
is still not located. The two describe different populations. The curve's training pairs are
grouped by one or three past seasons' rates among players who played consecutive seasons. The
forecast's star tier is the harness's reporting group: a 60/40 total over the two latest qualifying
seasons, falling back to the latest, then the second, then the third when seasons are missing
(`forecast_harness.subjects_at`). The first version of this paragraph called it a three-season
weighted total, which is the forecast's own anchor, not the reporting group (corrected after
review). Its outcomes are the seasons those players went on to play.

## Where the walk and the stars part company (hindsight diagnostic)

`run_star_walk_diagnostic.py` v1.0. A localisation exercise, not a candidate and not a two-way test.
For each development page the adopted leader is fitted once on what the page could see and frozen.
The group is the harness's own "3+" tier (`forecast_harness.subjects_at`), fixed per player and
page. A transition is season t to t+1 for t from the page season to four seasons later, kept only
where the player played t−1, t and t+1, so every arm is scored on the same 876 rows with the same
weights (the smaller of the two seasons' games, as the curve is fitted). **Arms 1 and 2 use realised
seasons after the page and are hindsight.**

Change in rate per 82 from t to t+1, weighted:

| transition | rows | observed | arm 1: curve on the realised rate at t−1 | arm 2: on the realised rate at t | arm 3: the forecast's own path | projected level minus realised, at t | arm 1 on a survivors-only curve |
|---|---:|---:|---:|---:|---:|---:|---:|
| page season to next | 190 | +0.003 | −0.322 | −0.246 | −0.250 | −0.039 | −0.269 |
| one to two | 188 | −0.045 | −0.300 | −0.294 | −0.275 | −0.288 | −0.262 |
| two to three | 182 | −0.119 | −0.345 | −0.340 | −0.288 | −0.583 | −0.301 |
| three to four | 175 | −0.209 | −0.394 | −0.380 | −0.294 | −0.837 | −0.346 |
| four to five | 141 | −0.228 | −0.421 | −0.405 | −0.290 | −1.055 | −0.377 |
| all | 876 | −0.112 | −0.352 | −0.328 | −0.279 | −0.527 | −0.307 |

Counts: 27 to 32 tier members a page; 113 to 134 transition rows a page.

Comparison groups, arm 1 only, same pages, dates and weights:

| group | rows | observed | arm 1 | survivors-only curve |
|---|---:|---:|---:|---:|
| the harness "3+" tier | 876 | −0.112 | −0.352 | −0.307 |
| the harness "2 to 3" tier | 1,750 | −0.189 | −0.226 | −0.212 |
| every subject whose realised rate at t−1 was 3 or more | 1,563 | −0.216 | −0.344 | −0.288 |

The full cohort, season WAR from the adopted leader's harness rows, absences counted: the tier is
0.17 low at the valuation season, 0.63 two seasons out and 0.87 five out; 0.23, 0.72 and 1.06 low
among the seasons played. Predicted participation is close through four seasons out (0.87 against
0.90 played at four) and low at five (0.78 against 0.88).

**What it localises:**
- **Excess predicted decline appears before repeated forecasting is involved.** On the same rows
  the curve predicts −0.33 to −0.35 a season from realised, correctly dated inputs of either
  timing, against −0.11 observed. That does not clear the rest of the forecast; it says the curve's
  own step is already too steep on these rows.
  The forecast's own path steps less steeply (−0.28), because its projected level falls as it goes;
  feeding forecasts back does not add to the decline. The starting level is close (−0.04), and the
  level error then accumulates step by step.
- **The imputed departures are a small part of it.** A survivors-only curve still predicts −0.31.
- **The stars in this tier barely decline for two seasons** (+0.003, then −0.045), then by 0.12 to
  0.23 a season.
- **Membership matters, and is not the whole story.** Players picked by one season's rate at t−1
  (the curve's own kind of group) are also over-predicted out of sample, by 0.13; the harness stars,
  picked on a two-season total, by 0.24; the 2-to-3 tier by 0.04.

**How much evidence this is.** The 876 rows are 492 distinct player-season transitions by 84
players, many appearing on several pages. Resampling whole careers (the independent review's
calculation), the training-aligned arm's error is −0.240 a season with a 95% interval of −0.347 to
−0.130, so the excess is not an artefact of counting one career many times. The rows are also a
selected set: of 983 transitions observable by calendar, 894 have the player in all three seasons,
883 at the qualifying games in each, and 876 with an age.

**What it does not show.** The diagnostic localises; it does not identify the cause. These are survivors: every row played three consecutive seasons, and a
star who declined sharply may be the one who did not. A survivors-only curve fitted on history does not
make later surviving stars representative of the whole starting cohort, so it reduces the
survivorship concern without removing it. Nor does it show why a curve that matches its training pairs
(3+ at t−1: −0.23 observed against −0.27 fitted on the 2021 page's history) over-predicts the same
kind of group after the page (−0.22 against −0.34 here): the training pairs and these transitions
are different seasons.

## A sustained-quality level (v1.3)

`run_star_residual.py` v1.3; `A1StatusAgingSustained`. The aging curve gets a second level beside
the one-season lagged level: the lower of the player's rates at t−1 and t−2 (t−1 alone where t−2
was not played), with its age interaction, so its slope can separate a player who was high in both
seasons from a one-season spike. Same rows and weights (check 46). The walk passes the projected
level as both. A proposed forecasting change, not an identified cause.

**Recorded before the run:** on the 2021 page the sustained level's slope is negative (−0.034 per
win): in the training pairs, players high in both seasons declined more, not less. A 3.2-win
27-year-old's yearly step becomes −0.280 against −0.251. The prediction was no gain for stars.

| version | pooled WAR RMSE | lower than adopted | stars' five-season rate miss | star tier error lower than adopted | dollars, adopted line | dollars, sustained line |
|---|---:|---:|---:|---:|---:|---:|
| adopted | 0.8151 | — | −0.921 | — | — | — |
| sustained level | 0.8170 | 0/2000 | −1.017 | 0/2000 | 42/2000 | 85/2000 |

Worse on the declared primary scores (squared error in season WAR and in dollars, pooled and for the
star tier), and more negative in every tier five seasons out (below replacement −0.085 against
−0.068; 0 to 1 −0.159 against −0.129; 1 to 2 −0.274 against −0.227; 2 to 3 −0.356 against −0.290).
**Not worse on every score**, as the first version of this paragraph said: season WAR absolute
error improves slightly (0.456457 to 0.456009; the independent review's interval includes zero), and
participation is unchanged by construction. Not adopted.

This rejects this construction of sustained quality, not every one. In the forecast both level
inputs receive the same projected rate, so the model never carries a player's observed consistency
forward; a construction that did would be a different candidate.

**Every tier, every horizon (the adopted leader).** Rate miss among seasons played:

| tier | valuation season | one | two | three | four | five |
|---|---:|---:|---:|---:|---:|---:|
| below 0 | +0.123 | +0.056 | −0.001 | −0.005 | −0.060 | −0.068 |
| 0 to 1 | +0.213 | +0.150 | +0.097 | −0.024 | −0.083 | −0.129 |
| 1 to 2 | +0.112 | +0.106 | +0.102 | +0.014 | −0.122 | −0.227 |
| 2 to 3 | −0.079 | +0.023 | −0.146 | −0.095 | −0.165 | −0.290 |
| 3+ | −0.027 | −0.265 | −0.427 | −0.632 | −0.800 | −0.921 |

**Every tier's miss is lower five seasons out than at the valuation season**, by 0.19 to 0.34 below
the top tier and by 0.89 in it, but not step by step: the 2-to-3 tier rises from the valuation
season to one season out, and several tiers are flat for a step. The lower tiers start too high at
the valuation season and end too low. Four constructions that change the curve's level input (none, a hinge, a multi-season level, a
sustained level) either break the lower tiers or leave the stars no better; the two that use a steadier
level found a steeper level effect in the training pairs, not a flatter one.

**What that points to, not what it shows.** The curve's training pairs repeatedly say high-level
players decline steeply; the seasons after each page say they decline much less. One reading is that
the older seasons the rolling curve is fitted on differ from the later seasons it is applied to. The
horizon pattern does not establish that: a longer horizon also changes the players' ages and which
players are still observable. A curve weighted toward the seasons nearest each page tests one version
of the reading (next section).

## One recency-weighted curve (v1.4), and where this leaves the residual

`run_star_residual.py` v1.4; `A1StatusAgingRecency`. One predeclared sensitivity: the adopted aging
curve with every training row kept and its weight halved for every five seasons it lies before the
most recent starting season the page can use. Five is a chosen value, not an estimated optimum, and
no other value was tried. Rows unchanged, weights changed exactly as declared (check 46); forecast
formula, participation and primary price line fixed.

**Recorded before the run, and wrong:** on the 2021 page the weighted curve is slightly gentler (a
3.2-win 27-year-old's step −0.230 against −0.251; at 31, −0.362 against −0.403), and the prediction
was a small star gain. The stars came out slightly worse. One page's curve did not stand for the
others.

| version | pooled WAR RMSE | lower than adopted | WAR MAE | stars' five-season rate miss | star tier error lower than adopted | dollars, adopted line | dollars, recency line |
|---|---:|---:|---:|---:|---:|---:|---:|
| adopted | 0.8151 | — | 0.4565 | −0.921 | — | — | — |
| recency, half-life 5 | 0.8156 | 69/2000 | 0.4570 | −0.947 | 463/2000 | 155/2000 | 116/2000 |

Five seasons out the recency curve is slightly better for the below-replacement tier (−0.065 against
−0.068) and slightly worse for the other four (0 to 1 −0.134 against −0.129; 1 to 2 −0.244 against
−0.227; 2 to 3 −0.308 against −0.290; 3+ −0.947 against −0.921). Participation is unchanged by
construction. Not adopted. This tests one weighting; it does not show that the age of the training
seasons plays no part.

**The residual is retained as a stated limitation of the adopted leader.** Eight constructions have
been scored on one declared currency (survivors-only curve; no level terms, unmatched and matched; a
per-season regression; a second level slope; a multi-season level; a sustained level; recency
weighting), the later ones on matched rows. None separates from the adopted leader on the declared
primary scores: the best, no level terms on matched rows, is lower on pooled squared error in 1,610 of
2,000 resamples and in dollars in 1,531, with worse absolute error and a broken lower tier. The limitation, as measured on
the development pages:
- for the three-win-and-up tier (the harness's 60/40 two-season total, 27 to 32 players a page), the
  rate per 82 is right at the valuation season (−0.03) and under-forecast by 0.27 one season out,
  0.63 three out and 0.92 five out among the seasons played; season WAR over every forecast is 0.17,
  0.64 and 0.87 low;
- a hindsight diagnostic puts the excess in the aging curve's step for these players, on realised
  and correctly dated inputs (about −0.35 a season predicted against −0.11 observed; career-resampled
  excess −0.240, interval −0.347 to −0.130, 84 players), with survivor selection not removed;
- in dollars, the star tier is where the thesis's surplus claims concentrate, so any result about
  star contracts carries this bias with it, in the direction of under-valuing the players.

Reopening it needs new evidence pointing at a more specific repair, not another variation on the
curve's level input.

## What is not settled

- Why the fitted curve walks stars down so much faster than the stars actually declined. The level
  term is measured against the rate one season before the change starts, which removes the obvious
  regression-to-the-mean artefact; whether a residual version of it remains, or whether one level
  slope simply averages over tiers that age differently, is not established.
- Whether the stars' observed slow decline is partly selection: stars who declined sharply may be
  the ones not playing five seasons later. The season WAR column argues against this being the
  whole story.

## Files

- `50_REBUILD/code/ability_forecast.py` v2.6: `A1StatusSurvivorAging`, `A1StatusReducedForm` (one
  change each); `A1StatusNoLevelAging` (formula and sample changed together; reference only);
  `A1StatusNoLevelAgingMatched`, `A1StatusAgingLevelHinge`, `A1StatusAgingMultiLevel`,
  `A1StatusAgingSustained` (one change each, rows and weights asserted identical by check 46);
  `A1StatusAgingRecency` (rows identical, weights changed as declared, check 46). None adopted.
- `50_REBUILD/code/aging_additive.py` v1.4: the `sample` option, the level knot, the multi-season
  level, the sustained level, recency weighting, the fit fingerprints
- `50_REBUILD/code/run_star_residual.py` v1.0 to v1.4 (the candidates scored in each are listed in
  its docstring); `run_star_walk_diagnostic.py` v1.0
- `50_REBUILD/code/repair_checks.py` v3.7: check 46
- output (ignored): `star_residual_run_log.txt` / `.csv` (v1.0), `star_residual_v11_*` (v1.1),
  `star_residual_v12_*` (v1.2), `star_residual_v13_*` (v1.3), `star_residual_v14_*` (v1.4), `star_walk_diagnostic_*`
