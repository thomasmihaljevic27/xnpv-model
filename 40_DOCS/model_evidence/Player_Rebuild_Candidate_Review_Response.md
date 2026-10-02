# Response to the review of the player rebuild candidate

Written 2026-09-15 against the same commit the review read (`beb69a1`). Each finding was
checked against the candidate code before being accepted, rather than accepted as written.
No candidate file, production file, or locked decision changed in producing this response.

## Summary

I accept seven of the nine findings as written. I accept two in substance and dispute the
framing, which matters because the framing decides which artifact has to be repaired. One
accepted finding is worse than the review describes, and one is narrower. I did not find a
finding I believe is wrong.

The central conclusion holds. The candidate has been shown to beat a flat-carry baseline
reproducibly. It has not been shown to beat the live chain, to be clean of look-ahead through
the market stage, or to produce dollar figures that can be quoted. I am treating each dollar
figure in the candidate reports as withdrawn until items 2, 4, and 5 below are repaired.

## Findings accepted as written

Shortened-season units (finding 2). Confirmed, and the accounting is exactly as reported.
`player_season_table.py` multiplies the total by the decision D20 proration factor, which is
82/70 in 2019 and 82/56 in 2020, and then divides that already-prorated total by the player's
own games and multiplies by 82. The games share on the next lines divides by the shortened
schedule. `forecast_harness.py:161` then reconstructs the season total as the product of
participation, rate, and games share, so the reconstruction overshoots the target by the
proration factor in those two seasons. The reported median ratios of 1.171 and 1.464 are the
two factors themselves. The companion problem on line 162 is real as well: predicted games
are the games share on an 82-game scale while the scored outcome is raw games in a 56-game
season, so a player who was available for the whole of 2020-21 is charged a 26-game error.

Unfitted long horizons (finding 3). Confirmed. Participation and games are fitted over
horizons zero to five, and `ParticipationModel.predict()` falls back to `base_.get(h, 0.6)`
when a horizon was never fitted, which returns a flat 0.6 because no base rate was stored for
those horizons either. One qualification that does not reduce the severity: the rebuild plan
specified a harness over horizons one to six, so the models are not off-spec. The market and
named-player runners are the code that asks for horizons outside the fitted range, and they
do it with no guard. The repair belongs in both places. The forecast has to refuse a horizon
it cannot serve, and the callers have to stop requesting one silently.

Market windows dated by contract start (finding 4). Confirmed. `ProductionCurrency.fit()`
filters on `start_yr < before`, and the rolling evaluations in the Phase 4 decision runner and
the curvature runner split on the same field. A contract that starts in 2019 and was signed in
2017 is therefore priced on contracts signed in 2018. I note one fact that strengthens the
finding rather than softening it. A `signing_date` field exists in the contract source and is
parsed and coverage-logged by `contract_source.py` at load. This is a code choice, not a data
limitation, and the repair is available today subject to confirming the coverage rate on the
eligible sample.

Cap path and discounting (finding 5). Confirmed. `production_currency.py` sums the realized
ceiling for each contract season and substitutes the 2025 ceiling beyond the dictionary, with
no decision date, no announcement cutoff, no 3% extrapolation, and no discount factor. The
rebuild plan specified each of those four. A historical valuation therefore knows the flat-cap
years before they were announced. The cap-share convention does not rescue this, because the
share is converted back into nominal dollars using ceilings the valuation date could not have
known, and those nominal dollars are then summed undiscounted.

Participation and production condition on different events (finding 6). Confirmed. The
participation event is ten or more games, through the shared minimum-games constant. The rate
and games targets in `_training_pairs()` are read from the full season table, so a season of
one to nine games supplies a rate target while being labelled as not played. The rebuild plan
specified participation at one or more games. The in-code comment at that point says a season
that never happened is not a rate training row but is a participation row, which is correct
for a season with no games and silent about the one-to-nine band that is the actual problem.

Harness completeness (finding 7). Confirmed, including the adversarial demonstration. The
harness asserts the required columns, the probability bounds, and the absence of missing
values inside whatever frame the model returns, and the missing-value assertion carries a
comment describing a real past incident. None of that checks the returned frame against the
requested career-by-horizon grid, and the subsequent join is a left join on the prediction, so
a model that returns one row is scored on one row. The second half of the finding is also
correct. `subjects_at()` advertises a three-season activity window, then requires a trailing
level built from the two most recent seasons and drops each row where that is missing, which
removes the returning players the wider window was written to admit. Age is taken from the
last observed season rather than the valuation season, so the age bands are not defined at the
forecast date and the subgroup tables are mislabelled.

Stress tests and confirmatory coverage (findings 8 and 9). Accepted. The stress runner still
imports the older total-WAR model as its leader while the adopted candidate is the hinge
exposure model, so the six-part battery does not test the model that was selected. Subgroup
results pool horizons within each group, which does not establish a win at each horizon within
the group. No candidate returns predictive intervals, and the harness reports the missing
coverage rather than failing on it. On confirmatory coverage, the point that the seal covers
one entry point is correct, and I accept the distinction the review draws between forecasting
later outcomes on a development page, which the plan allows, and selecting a market model on
later signing cohorts, which is what the market runners do.

## Accepted in substance, disputed in framing

The comparator (finding 1). The substance is right and it is the most consequential finding in
the review. The comparator is not the live chain. The live chain projects through the locked
aging path in `skater_forward_projection.py` and carries exit-hazard survival weights in
`contract_npv.py`, while the baseline in the candidate holds the trailing anchor flat with
games share and participation both set to one. Each improvement figure quoted against
"production" is therefore an improvement against a simpler rule, and the gap is widest exactly
where aging and exits do the most work, which is the old and the long-contracted.

Where I disagree is on where the misrepresentation lives. The baseline class names itself as
the production chain's starting point, and its own comment states that it conflates level with
availability and calls that the conflation the rebuild separates. The code is not claiming to
be the live chain. The claim is made in the write-ups, and `Phase0_Harness_Report.md:252`
attributes a +35% star over-projection to "the production chain" when +35% is the flat
baseline's bias. That same report quotes the project's own measured production tilt of +24% at
three wins and above, eleven points lower, which is the figure a faithful adapter would have to
reproduce. So the repair is two separate items rather than one: build the production adapter
the plan's Phase 0 required, and correct each report sentence that attributes a baseline number
to the live chain. The second is owed whether or not the first lands quickly, and I am not
waiting on the adapter to do it.

Named-player truncation (part of finding 3). The review says the ten years specified for Shea
Weber are truncated to eight. That is true, at `run_player_comparison.py:147`, which takes the
smaller of the term and eight. Two corrections in opposite directions. It is not asymmetric
between the two sides, because the flat baseline is priced over the same truncated count, so
the difference column is a like-for-like comparison over eight seasons rather than a distorted
one. It is worse in a different respect than truncation alone: the truncation is to eight
horizons while the fitted range ends at five, so each named player on a term of seven or more
has his final one or two seasons priced on the unfitted 0.6 participation, and the reported
term column says eight without recording that a ten-year contract was silently redefined.

## Where my own earlier reading was wrong

On first reading I judged the units error to be confined to the total-WAR reconstruction, the
games metric, and the dollar conversion, on the reasoning that a rate error is measured against
a target on the same inflated scale and therefore cancels within a page. That is too
generous, and the review's wider claim is the correct one.

The cancellation fails in two places. The anchors carry both season totals and per-82 rates
across lags and blend them with geometric decay across two seasons, so a valuation dated 2021
blends a 2020 rate inflated by 1.464 with a 2019 rate inflated by 1.171, and the blend mixes
three scales. Persistence, the aging deltas, and each year-over-year change that crosses a
shortened season inherit that mixture. Separately, each model that pools training pairs across
seasons fits coefficients on a target that is on one scale for two seasons and another scale
for the rest, so the fit is pulled even where the scoring is self-consistent. The scope
qualification I would still make is about concentration rather than about which quantities are
affected: two of the nineteen source seasons are shortened, but they are the two that sit
under the anchors of the 2019, 2020, and 2021 development pages, which is the end of the
development window and the part of it the candidate leans on hardest.

## Repair order

I depart from the review's order in one place, by pulling the assertion work forward ahead of
the modelling work, because each assertion is a small diff that fails on today's code and
protects each later refit.

1. Units. Define the raw per-82 rate, the schedule share, and the standardized season total as
   three coherent quantities, and assert the identity between them before any fit runs. Score
   predicted and actual games in one unit. This is the smallest diff in the list and each
   later item inherits it.
2. Guards. Make the forecast refuse a horizon it has not fitted, make the callers stop
   requesting one, assert that forecasted contract seasons equal the requested term, and make
   the harness validate the exact requested career-by-horizon grid before scoring. These are
   assertions rather than modelling decisions, and each should fail on the current code, which
   is the point of writing them before the refit.
3. Eligibility and the participation event. Move participation to the one-game event the plan
   specified, make the rate and games targets condition on the same event, and keep returning
   players with an explicit stale-history tier. Redefine the age bands at the valuation date
   and relabel the subgroup tables.
4. Market dating and dollars. Date each market fit at the signing date and assert that the
   latest training signing precedes the valuation. Build the date-aware cap path with the
   announcement cutoff, the 3% extrapolation beyond it, and the discount schedule.
5. The production adapter, and the report corrections that do not wait for it.
6. Refit, then rerun the development comparisons on identical date-valid rows. Only then
   revisit the star and young-player residuals, which are the two places the candidate was
   about to add flexibility and are the two most likely to move once items 1 through 4 land.

Items 8 and 9 in the review, which are the stress battery and the confirmatory inventory,
follow the refit rather than precede it, because a battery wired to the pre-repair leader
would have to be rerun in any case.

## What this response does not settle

I have not quantified the net effect of any of these on a contract NPV, and neither has the
review. Until items 1 through 5 are repaired and the chain is refit, the honest statement of
where the rebuild stands is the review's: the experimental forecast beats its flat benchmark
reproducibly, and nothing further is established. Two questions I would want answered before
the refit rather than after. First, whether the signing-date field's coverage on the eligible
contract sample is high enough to date each market fit without dropping a material share of
the sample, or whether a fallback rule is needed and has to be declared. Second, whether the
one-game participation event leaves enough separation in the logistic fits at the long
horizons, given that the ten-game event was chosen partly for fit stability, or whether the
short-appearance seasons are better modelled as their own low-production state as the review
suggests in its finding on conditioning.
