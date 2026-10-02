# Repairing the player rebuild: what the review found, and what was done

> **Corrected 2026-09-15, after this report was itself reviewed.** The verification found six
> further defects, four of them P1, and two of those invalidate figures this report published.
> The production adapter reimplemented two of production's rules instead of calling them, and got
> both wrong: it multiplied a negative anchor along a decay path where locked decision D12
> projects it to replacement, and it read the two most recent qualifying seasons anywhere before
> the valuation instead of exactly the two preceding ones. **The improvement over the live chain
> is 8% to 9% from one season out and 14.4% in the valuation season, not the 13% to 17% reported
> below, and the 28.6% gain on below-replacement players was almost entirely the adapter's own
> defect and is 2.6% against the corrected comparator.** Each figure in this report has been
> brought into line; the superseded ones are named where they mattered. All six new findings are
> repaired and the check suite is at 14. The full corrected tables are in
> `Repaired_Chain_Development_Results.md`, and the verification itself is
> `Repair_Verification_Codex.md`.
>
> **Second correction, same day.** A further verification found three more issues and judged the
> claim that all six earlier findings were repaired too broad, which it was: the named-player
> dollar table still ran on the withdrawn valuation method, the extrapolation still depended on
> which horizons were requested, and the horizon-eight ceiling was still in the attachment
> interface. All three are now repaired and the suite is at 15. The forecast figures in this
> report are unaffected and were independently reproduced. See the closing section.
>
> **Third correction, same day.** A third verification closed two of those three and found that
> the rewritten named-player table fitted a SEPARATE price line to each forecast while its own
> heading claimed one line served both. It did, in all 18 comparable quarters. One reference
> currency is now fitted per signing quarter and applied to both columns; this moves the live
> column by $8.26M on average and $19.18M at most, and leaves the rebuilt column unchanged to the
> cent. An all-rejected attachment batch also crashed before publishing its rejection report, and
> now returns cleanly. Suite at 17.

Written 2026-09-15, closing the independent review of the experimental player rebuild. The
review raised nine findings against commit `beb69a1`. Seven were accepted as written, two were
accepted in substance with the framing disputed, and none was found to be wrong. All nine have
now been worked. This report records what was done for each, what the repairs changed in the
results, what they turned up that nobody was looking for, and what is still open.

No production file was changed and no locked decision was reopened. The confirmatory forecast
pages remain unspent.

## Verdict, in One Paragraph

The rebuilt chain is better than the live chain by 8% to 9% of mean absolute error on season
WAR from one season out, and by 14.4% in the valuation season itself, on the development pages
and on the rows production can price. That improvement is real, it survives the repairs,
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
hazard table, its anchor, its negative-anchor multiplier, and its survival convention, because a
second copy of a rule drifting from the first has already cost this project twice. The first
version of this paragraph claimed the adapter restated none of them, and that was not true: it
restated the anchor and the multiplier, and got both wrong. That is the substance of the
verification's first two findings, and it is why the parity check now compares the adapter
against production's methods rather than against a description of them. Production's own
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
named-player runner no longer reprices a ten-year contract as an eight-year one, and is now
routed through the repaired valuation path entirely.

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

| horizon | live chain | rebuilt | against live |
|---|---|---|---|
| 0 | 0.6534 | 0.5595 | **-14.4%** |
| 3 | 0.5542 | 0.5038 | -9.1% |
| 5 | 0.4575 | 0.4179 | -8.6% |

Measured on the rows production can answer, which excludes the 120 subjects a page holds that
production declines to anchor. The superseded version of this table read -16.5% to -13.3% and
was measured against an adapter that was not production.

The improvement is real and worth having. Its shape is not. Against the flat benchmark the
advantage grows with the horizon, which reads as a model that gets relatively better the further
out it forecasts; against production it narrows. The growth was the benchmark's missing aging
path, since the further out a model without aging projects the more it loses, and none of that
was the rebuild's doing.

The gain is concentrated rather than general, and the corrected comparator narrows where it
comes from. Against the live chain it runs from +0.4% for players 22 and under, where the
rebuilt chain is slightly worse, to -43.1% for players 34 and over. By trailing level it runs
from -2.6% below replacement to -10.4% for three-win players. The rebuild is an old-player fix.
The below-replacement gain reported earlier was the adapter's defect rather than the rebuild's
doing, since production projects those players to replacement and the broken adapter carried
their negative anchors along a decay path instead.

On the repairs themselves, holding the model and the harness fixed, the published -43.5%
improvement at five seasons out against the flat benchmark moves to -43.4%. The units, guard,
event, and weighting work leaves the case essentially where it was. What moved the headline was
not the repairs but the comparator.

## What the Repairs Turned Up That the Review Did Not Name

**The star residual is inverted, not repaired.** Production over-projects a three-win player by
0.67 wins a season; the rebuilt chain under-projects him by 0.57. The magnitude is 15% smaller
and the sign has flipped. Under-projection is the safer direction for a surplus estimate on an
expensive player, but any claim about star contracts rests on a forecast wrong by more than half
a win a season, and the earlier reports describe this residual as an over-projection. The
review's instruction to reassess it before adding more flexibility looks right, since chasing it
now would be chasing an under-projection.

**Young players are where the rebuild does least, and against the corrected comparator it is
slightly worse than nothing.** Both chains under-project players 22 and under, production by 0.34
wins and the rebuilt chain by 0.25, and on mean absolute error the rebuilt chain is 0.4% behind.
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

## The Verification, and What It Found

This report was itself reviewed. The verification ran the check suite, reproduced the reported
figures, and found six further defects, four of them P1. All six are repaired.

**The adapter omitted production's negative-anchor rule.** Locked decision D12 projects a
below-replacement player to replacement in each season after the valuation; the adapter
multiplied his negative anchor along the decay path instead. 266 subjects on the 2021 page
received a nonzero forecast where production requires zero, and the wrong level fed the hazard
lookup as well. This is the finding that reversed a headline claim, since the 28.6% gain on
below-replacement players was measuring the rebuilt chain against a bad forecast rather than
against production's rule.

**The adapter read different trailing seasons from production.** Production reads exactly the
two preceding seasons and declines when neither exists. The adapter took the two most recent
qualifying seasons anywhere before the valuation, which moved 142 anchors by up to 1.022 WAR and
invented an answer for the 120 subjects production declines. Both now call production's own
method. The 120 are still answered, because the harness requires an answer on every row, but
they are tagged and excluded from the comparison, and reported separately.

**Signing-date filtering still admitted future cap information through the target.** The fit was
dated at the signing while the cap share was divided by the realised start-year ceiling, so an
early-signed extension entered training with a denominator not yet announced. The denominator is
now the start-year ceiling as knowable at the signing. 31 contracts signed before the cap table
opens are dropped and counted, because inventing a pre-2015 ceiling would be inventing the
number the constraint is about.

**Discounting started at the contract start rather than the valuation date.** A one-year
contract starting in 2019 cost the same whether signed in 2017 or 2018, so the wait between
signing and start was free. Value and cost now discount from the signing, which is where the
market and cap information are already dated.

**Extrapolated forecasts depended on the question.** The tail decay was measured between the
last two requested horizons on the mean of the requested subjects, so asking for horizons 3, 5,
and 6 gave a different horizon-six answer than asking for 4, 5, and 6, by up to 0.52 WAR, and
asking about one player alone differed from asking about him inside the population. The rate is
now measured between the two highest fitted horizons on a fixed reference population and cached
per page. Both invariances are now exactly zero. The extrapolation tag is also carried through
to the contract table, which can now report how many of a contract's seasons came from beyond
the fitted range.

**Repaired entry points were not runnable.** The named-player runner checked the global
six-horizon constant before fitting, so it refused a seven-year term on a page that supports
nine and never reached the extrapolation path. The two rolling runners handed the cohort guard a
range it had to refuse. The forecast attachment clipped at horizon eight and dropped missing
years instead of asserting full-term coverage. Each is fixed, and the market seal now requires a
written reason for an unseal, as the page seal already did.

The verification also notes that the ledger records inspections without enforcing once-only use.
That is correct and is not repaired here: enforcement needs the holdout policy decided first,
which is the open decision recorded in `Holdout_Inventory.md`.

## The Second Verification, and the Three Issues It Found

The repair report was reviewed again at commit `0e70d4b`. The forecast results reproduced, the
production parity held across 5,196 rows, and the cap-timing and discount repairs passed
independent tests. Three implementation issues remained, and the judgement that "all six prior
findings are repaired" was too broad. It was.

**The named-player dollar table still used the withdrawn method.** The earlier pass repaired its
horizon guard and stopped there, which made the runner reach a dollar calculation without making
that calculation valid. It still fitted its price line on the whole contract sample, still
compared against the flat benchmark while calling it today's chain, and still summed realised
ceilings without discounting. It is now routed through the same API as the surplus runner: a
currency fitted only on deals signed before each contract's own signing quarter, a cap path known
at the signing, discounting from the signing, and the live chain as the comparator. Both columns
are priced on the same currency, so the difference between them is the forecast rather than the
price line.

That rewrite costs most of the table, and the reason is worth stating rather than hiding. Dating
the price line at the signing means the earliest contracts have no market to have learned from:
the first signing this tree can price is 2017-10-02, because before that there are fewer than 200
prior signings to fit on. **20 of the 32 named cases are therefore no longer showable, including
the whole 2016 group**, which holds the most familiar names in the list. Each absent case is
listed with its reason. This is the price of removing the look-ahead, and widening the training
window to get those cases back would be reintroducing exactly what was removed.

**The extrapolation still depended on the requested endpoint.** The decay rate was measured on a
fixed population, which fixed the subject-batching half, but it was applied from the last fitted
horizon the CALLER requested rather than the last the model fitted. Asking for horizons 3, 4, and
6 therefore differed from 4, 5, and 6. My own check could not see it, because both of its
requests kept horizon five. The final fitted season is now always computed internally, every
extrapolation runs from it, and only the requested rows are returned, so a request for an
extrapolated year alone works where it used to raise. The check now varies the endpoint and asks
for a lone extrapolated year, and it fails on the previous commit.

**The horizon-eight ceiling was still in the attachment interface.** The full-term requirement
added in the previous pass stopped the interface shortening a contract silently, but the request
itself was still clipped at eight, so a longer term was never asked about and then dropped in the
join with no record. The ceiling is gone, and contracts the forecast cannot cover are written to
a rejection file with a reason rather than disappearing. A stub that answers every requested
season now returns a ten-year contract; on the previous commit it does not.

## The Third Verification

Two of the three issues from the second pass closed on the tested cases: the extrapolation is
invariant to the requested horizons, subjects and row order, and a ten-year term survives
attachment. One material issue remained, and it was in something I had written two passes
earlier and repeated since.

**The named table fitted two price lines while saying it fitted one.** The rewritten runner
looped over the two forecast tables and called `ProductionCurrency` on each. Those tables carry
different forecast regressors, so the two fits returned different coefficients, in all 18
comparable quarters. The printed difference between the columns was therefore a forecast change
and a price change added together, while the line above the table said it was the forecast alone.
The claim was mine and it was wrong in the same way twice: the code changed underneath a sentence
that did not.

One currency is now fitted per signing quarter, on the rebuilt forecasts as the declared
reference, and the same fitted object prices both columns. The effect is not small. The live
column moves by $8.26M on average and by $19.18M at most, and the rebuilt column does not move at
all, which is what fitting on the rebuilt table should do. Substantively the correction runs
against the rebuild: priced on one line, the live chain values these players higher than the
rebuilt chain does, so the rebuilt chain is the more conservative of the two and its surpluses are
smaller. Nikita Kucherov's live surplus goes from $8.8M to $27.7M while his rebuilt surplus stays
at $6.0M.

Fitting a separate line to each forecast is a legitimate whole-model sensitivity, and it is a
different question from the one this table asks. It is not reported here.

**An all-rejected batch crashed before publishing its reasons.** The attachment built its result
frame from rows that did not exist when every contract had been rejected, so the caller got a
`KeyError` instead of either an empty result or the rejection report the function had just
promised. An empty batch is an ordinary no-history outcome. Both cases now return cleanly, and
the rejection report is published before the join rather than after it.

The runner's opening docstring also still described the withdrawn method, and now describes the
one the code runs.

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

Seventeen checks, each corresponding to a defect above. The first eight were demonstrated
failing against the commits that preceded them, by copying the suite into a checkout of the
earlier code and running it there; against the original commit none of the first six passes. The
rest guard code that did not exist before. Check 12 was rewritten after the verification pointed
out that its original form, which asserted only that rates move with the horizon and survival
falls below one, was true of an adapter wrong in two ways at once; it now compares the adapter
against production's own methods row by row. All seventeen pass on the current tree. Each pair of checks added in a later pass fails on the commit that preceded it, which is the only evidence that a check is worth having.

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
