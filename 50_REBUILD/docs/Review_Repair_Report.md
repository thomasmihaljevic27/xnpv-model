# Repairing the player rebuild: what the review found, and what was done

Written 2026-09-15, closing the independent review of the experimental player rebuild. The
review raised nine findings against commit `beb69a1`. Seven were accepted as written, two were
accepted in substance with the framing disputed, and none was found to be wrong. All nine have
now been worked. This report records what was done for each, what the repairs changed in the
results, what they turned up that nobody was looking for, and what is still open.

No production file was changed and no locked decision was reopened. The confirmatory forecast
pages remain unspent.

## Verdict, in One Paragraph

The rebuilt chain is better than the live chain by 13% to 17% of mean absolute error on season
WAR, at every horizon, on development pages. That improvement is real, it survives the repairs,
and it is the first figure in this project measured against production rather than against a
simplified stand-in. Two things the earlier reports claimed do not survive. The improvement does
not grow with the forecast horizon; that growth was an artifact of the comparator. And the star
over-projection the rebuild was said to fix has been inverted rather than removed. The dollar
side now runs on signing-dated market fits and a discounted, date-aware cap path, but no dollar
total has been reconciled against production's contract net present values, and none should be
quoted until it has.

## The Nine Findings, One by One

**1. The comparator was a flat-anchor baseline, not production.** Accepted in substance. The
comparator holds the trailing anchor flat with availability and participation both at one, while
the live chain projects through the locked aging curve and carries exit-hazard survival. Where I
disagreed was on where the misstatement lived: the class names itself the chain's starting point
and its own comment says it conflates level with availability, so the claim was being made in
the write-ups rather than by the code.

That turned out to be half right. The review then pointed out that the false attribution also
reaches executable output, in the Phase 0 acceptance runner's log line, and I had missed it. The
repair therefore covers four surfaces: `production_adapter.py` puts the live chain on the
harness; the benchmark class is renamed to the flat benchmark; the acceptance runner's log line
and the module docstring are corrected; and both affected reports carry a dated correction
stating what their comparator actually was. A rerun no longer regenerates the claim.

The adapter imports production's locked aging curve, its decay path with the age-1 basing, its
hazard table, and its survival convention rather than restating any of them, because a second
copy of a rule drifting from the first has already cost this project twice. Production's own
documented limitations travel with it, including the curve being fitted on the whole panel,
because repairing them would stop it being production.

**2. Shortened-season rates and games did not reconstruct the target.** Accepted. The season
total was scaled to an 82-game basis under decision D20 and the per-82 rate was then built by
dividing that already-scaled total by the player's own games, so the schedule adjustment was
applied twice. The rate is now built from the raw total with D20 applied after the aggregation.
Since D20 scales by 82 over the schedule and the games share divides by the same schedule, the
two cancel exactly, and the identity holds on all 17,050 played rows. The 61 rows whose merged
trade halves carry more games than the schedule are excluded by the games-share clip and
counted rather than hidden. D20 is unchanged in substance.

I had judged this defect narrower than it was, on the reasoning that a rate error is scored
against a target on the same inflated scale. That was wrong and the review's wider claim was
right. The trailing anchors blend two seasons, so a 2021 valuation was averaging a 2020 rate
inflated by 1.464 with a 2019 rate inflated by 1.171, and each fit pooled across seasons trained
on a target that changed scale partway through the sample. The 2020-21 median rate falls from
0.9319 to 0.6364 against a full-length-season range of 0.4485 to 0.6282.

Separately, predicted games were converted on a flat 82-game basis and scored against raw games
in a shortened season, which charged a player available for all 56 games of 2020-21 a 26-game
error. Games are now converted on the outcome season's own schedule.

**3. Years seven onward silently used an unfitted 60% participation.** Accepted, and the repair
went further than refusing. The six-horizon limit turned out not to be a choice: a training pair
at horizon h needs an outcome completed before the valuation season, so at the 2015 page horizon
6 has 270 pairs and horizon 7 has none at all, while at 2021 horizon 7 has 1,246 and the range
reaches 11. Each model now records what its own page supported and refuses past it. Horizons 7
and 8 at the 2018 page carry 176 distinct fitted probabilities spanning 0.005 to 0.95, where
each player used to receive exactly 0.6.

The review was right that refusing is the first repair and not the whole one. 28 of 1,927
development contracts, which is 1.5%, still need a horizon their page cannot reach, and each of
them is a long deal. Those use a declared extrapolation, described under finding 8 below,
through a separate explicitly-called method so that nothing extrapolates silently. The
named-player runner no longer reprices a ten-year contract as an eight-year one.

**4. Market training windows were not frozen at the signing.** Accepted. `ProductionCurrency.fit`
now takes a date, refuses a season outright, and asserts that the latest training signing
precedes the decision date. The two rolling evaluations and the surplus runner all train on
contracts signed before the test contract's own signing quarter rather than before its start
year. The module docstring claimed signing-dated fits before this was true of the fit.

The review's coverage figure was verified independently rather than taken on trust: 3,550
eligible standard-level skater contracts starting 2015 to 2025, 3,550 parseable signing dates,
none missing, so no fallback rule is needed. The exposure reproduces as well, with 354 training
contracts in the 2022 pool signed after the earliest 2022 signing.

**5. Dollar outputs used future actual caps without discounting.** Accepted. `cap_path()` uses a
ceiling only once announced, normally the June before the season and 2025-01-31 for the three
seasons published together, and grows at 3% beyond. Seen from 2017 the 2020 ceiling is 82.0M
against the 81.5M it turned out to be, so a historical valuation no longer knows the flat cap
before it was announced. Value and cost are discounted on the same schedule. Under locked
decision D24 the 3% growth and the 3% discount cancel in cap-share terms, and the check suite
demonstrates that identity rather than assuming it.

One gap is left open deliberately. The announced 2026-27 and 2027-28 ceilings are public but are
not in this repository's source data, so those seasons extrapolate at 3% and are understated.
Entering a figure from memory into a thesis model is not a trade worth making, so it is recorded
in the config where it will be found.

**6. Participation and production conditioned on different events.** Accepted. One games
threshold was answering three questions. Ten games still decides whether a past season is usable
evidence. The event the participation model predicts is now the plan's one game, and the rate
and games targets condition on the same event. On the preceding commit the new check fails and
names the damage: 2,170 training pairs carried a rate target while being classified as not
played.

One game admits 2,918 cameo seasons, which are 17.1% of rows and -0.10% of total WAR, and whose
per-82 rates run from -8.4 to +41.5 because dividing by one to nine games and multiplying by 82
amplifies noise up to eighty times. Rate fits are therefore weighted by games played, which is
the precision weight rather than a convenience, since a rate's sampling variance scales as one
over the games behind it. The review left this open between weighting and modelling short
appearances as their own state; Thomas took the weighting.

**7. The harness permitted silent sample changes and dropped return candidates.** Accepted,
including the adversarial demonstration. The harness validated the contents of whatever frame
came back and never that the frame answered the question, so a model returning one player for a
page of 866 passed each assertion and was scored on the sample it chose. It now validates the
exact requested player-by-horizon grid, and the one-row model is refused.

The eligibility window said three seasons and the trailing level stopped at two, so a player
whose only qualifying season was the oldest in the window was dropped. On the 2021 page that is
120 careers, exactly the count the review predicted, and the drop fell entirely on players who
missed a season and came back. They are admitted with a history tier recorded on each row and an
anchor from their most recent qualifying season, added only where the window had nothing. The
three-season models are unaffected by construction and the check confirms it at 8.9e-16. Age
bands are now defined at the valuation season, so the subgroup populations are defined at the
forecast date.

**8. The stress tests did not establish the claims made about them.** Partly addressed, and this
is the finding with the most left on it. The battery selected the earlier leader while the
register recorded the hinge-and-evidence variant as adopted, so the six-part suite was testing a
model nobody had chosen. It is now wired to the adopted candidate. My own first rerun made the
same mistake and has been redone; the two models agree to the third decimal at every horizon, so
no conclusion turned on it.

The extrapolation the review asked for is declared and tested. The first rule tried was to hold
the last fitted season flat. Measured against pages where those horizons are genuinely fitted,
that overstates production by 36%, 88%, and 170% at one, two, and three seasons past the range,
so it was discarded. The rule that ships continues the decay observed at the end of the fitted
range, measured league-wide on the product and split so that participation keeps its own rate.
That leaves +3.0%, +10.0%, and +19.8% on average and +32% on the worst page tested. Measuring a
ratio per component and applying both was also tried and undershoots by 21% to 45%, because it
decays the product twice. Each extrapolated row is tagged. The residual bias is upward and is
not corrected, because dividing it out would mean three tuned constants repairing 1.5% of the
sample.

Not addressed: subgroup results are still pooled across horizons, no candidate supplies
predictive intervals so the harness still reports missing coverage rather than failing, the
export-break test still runs on outcome eras rather than synthetic input perturbations, and the
full-chain leakage test still compares rates only. These remain open.

**9. The confirmatory protection covered one entry point.** Accepted. Reserved market start
cohorts are now enforced alongside the forecast page seal, the page seal requires a written
reason instead of accepting an empty one, and each inspection appends to a committed ledger.
`Holdout_Inventory.md` records the state of both reserved samples and is blunt about it: the
forecast holdout is intact, and the market holdout is spent, because both market runners swept
start years through 2025 and selected on each year they touched. No market result on a 2022 to
2025 start cohort can be presented as out-of-sample. The policy question the review asked for,
which is what the market holdout should now be, is set out there as three routes and is a
decision still owed.

## What Changed in the Results

Mean absolute error in season WAR on development pages 2015 to 2021, three forecasts scored on
identical rows.

| horizon | flat benchmark | live chain | rebuilt | against flat | against live |
|---|---|---|---|---|---|
| 0 | 0.6160 | 0.6078 | 0.5073 | -17.7% | -16.5% |
| 3 | 0.6935 | 0.5310 | 0.4505 | -35.0% | -15.2% |
| 5 | 0.6931 | 0.4304 | 0.3733 | -46.2% | **-13.3%** |

The improvement is real and worth having. Its shape is not. Against the flat benchmark the
advantage grows with the horizon, which reads as a model that gets relatively better the further
out it forecasts; against production it narrows. The growth was the benchmark's missing aging
path, since the further out a model without aging projects the more it loses, and none of that
was the rebuild's doing.

The gain is concentrated rather than general. Against the live chain it runs from -2.4% for
players 22 and under to -53.9% for players 34 and over, and from -28.6% below replacement to
-11.1% for three-win players. The rebuild is an old-player and a below-replacement-player fix.
On players 26 and under it is barely better than production.

On the repairs themselves, holding the model and the harness fixed, the published -43.5%
improvement at five seasons out against the flat benchmark moves to -43.4%. The units, guard,
event, and weighting work leaves the case essentially where it was. What moved the headline was
not the repairs but the comparator.

## What the Repairs Turned Up That the Review Did Not Name

**The star residual is inverted, not repaired.** Production over-projects a three-win player by
0.68 wins a season; the rebuilt chain under-projects him by 0.55. The magnitude is 19% smaller
and the sign has flipped. Under-projection is the safer direction for a surplus estimate on an
expensive player, but any claim about star contracts rests on a forecast wrong by more than half
a win a season, and the earlier reports describe this residual as an over-projection. The
review's instruction to reassess it before adding more flexibility looks right, since chasing it
now would be chasing an under-projection.

**Young players are where the rebuild does least.** Both chains under-project players 22 and
under, production by 0.39 wins and the rebuilt chain by 0.25, with an error advantage of 2.4%.
The negative net-present-value finding on early extensions lives in exactly that population, and
the direction of the error pushes against that finding rather than supporting it.

**A source file the tree depended on silently.** The birthdate join takes PuckPedia plus an
Elite Prospects file that is not in the repository. Without it, coverage falls from 98.3% of
season rows to 69.2%, nothing fails, and the rebuild's improvement at five seasons out reads
23.6% instead of 43.5%. A missing input that shrinks a headline result without raising anything
is worse than one that stops the run, because the shrunken number looks like a finding. I raised
it as a flag, and it resolved the same day when the file arrived: at full coverage the published
figures reproduce to the decimal. The season table now refuses below 95% coverage, naming the
file and what its absence costs.

**An adapter bug that would have hidden the whole of finding 1.** Production's aging curve
indexes an age array, so passing 27.0 instead of 27 raised inside it, `ratio_path` swallowed the
error as "no qualifying season", and each player came back on a flat path. The adapter would
have looked exactly like the benchmark it exists to replace, and the comparison would have shown
production and the flat benchmark as the same thing.

## What Remains Open

Nothing on the dollar side has been reconciled. The chain runs and prices 1,226 development
contracts, but no total from it has been checked against production's contract net present
values, and no such comparison should be quoted until it has.

The market holdout is spent and what replaces it is a decision owed. The four unaddressed parts
of finding 8 are listed above. The announced 2026-27 and 2027-28 cap ceilings are absent from
source. The plan's joint simulation, the trade-date forecast update, the control-year
integration, and the goalie branch are all still unbuilt, as the review's adherence table says.

## How to Reproduce This

    python 50_REBUILD/code/repair_checks.py

Twelve checks, each corresponding to a defect above. The first eight were demonstrated failing
against the commits that preceded them, by copying the suite into a checkout of the earlier code
and running it there; against the original commit none of the first six passes. The last four
guard code that did not exist before. All twelve pass on the current tree.

The suite builds its table with the coverage guard disabled and reports the coverage instead.
That is deliberate: the guard exists to stop a silent degraded run, and this suite is the tool
you reach for to find out what state the tree is in, so letting the guard abort it would mean
the diagnostic refused to start on exactly the checkout most in need of one. Writing this
section is what surfaced the problem, since the first draft claimed a graceful skip that the
code did not do.

On a checkout missing the Elite Prospects birthdate file the suite reports 11 passed and 1
skipped: the extrapolation check measures a decay rate produced by the aging model, and at 69%
coverage that rate is noise, so it skips with the coverage named rather than failing on the
environment. Check 12 needs `.env` and `30_OUTPUT/WAR_with_age.csv`, which is built by
`20_CODE/age_join.py`, and skips without them rather than substituting anything for the live
chain. It reads production's own age file, so it is unaffected by the rebuild-side join.
