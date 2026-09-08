\# Review of the Player Valuation Model

\## Findings on Specification, Implementation, and Data Handling

Prepared 24 July 2026

\---

\## 1. Summary

I re-examined the code and the statistical work behind the player pillar of the valuation model. Before making any criticism, I reproduced the current market rate from the raw inputs and recovered the stored coefficients to eight decimal places, so each finding below is a property of the live model rather than of my reconstruction.

The review covers the skater pillar, the goaltender pillar, the restricted free-agent terminal value, and the draft pick curve. It found one specification problem large enough to change how the project's current headline result should be read, three further problems with the price equation that bias the model differently for different categories of player, two errors in pillars outside the skater chain that each move valuations by more than a million dollars per season, four implementation errors in the projection and risk machinery, and several data-handling errors.

The central finding is this. The price equation that converts projected production into dollars does not include contract length. Contract length is the strongest single predictor of what a contract costs, worth roughly $0.82 million per season for each additional year of term. Because the equation omits it, the estimated price of one win is overstated by 86%, and the estimated value of a replacement-level player is overstated by a factor of nearly seven. The correlation between contract length and the model's final valuation is −0.750, meaning contract length alone accounts for approximately 56% of the variation in the model's headline output. The finding that long contracts signed by young players carry negative net present value is, in substantial part, a mechanical consequence of this omission rather than a discovery about how teams behave.

This does not mean the finding is wrong. It means the model cannot presently tell the difference between the two explanations, and an external reader will identify this quickly. Section 3 sets out a test that separates them.

Two further findings sit close behind it in size. In the goaltender pillar, 181 contract-seasons covering 38 goaltenders are priced using the league-average goaltender rather than the goaltender under valuation, which contradicts the flat-projection rule the project has already adopted and undervalues elite goaltenders on long contracts by $1.1 million to $1.6 million in each affected season. In the restricted free-agent terminal value, the retention rates that are used in place of the exit hazard are estimated on a sample that excludes 1,039 of 2,270 observable decisions, and the excluded group is walked away from 1.6 times as often as the group the rates are fitted on, so control years currently carry neither the exit hazard nor the departure risk the rates are assumed to cover.

The draft pick curve survived review in shape and construction. Its point estimates at the top of the draft rest on eleven cohorts and should carry intervals, and its assumption that post-entry-level seasons generate no surplus is not independent of the price-equation problem above.

Section 13 sets out a staged roadmap ordered by dependency, with a status column so this document can serve as the working tracker.

\---

\## 2. How the Player Model Values a Contract

The rest of this document assumes the following four steps, so I set them out plainly here.

Step one, the price equation. I take each contract signed between 2018 and 2025, measure what the player produced in the two seasons before he signed, and fit a line relating production to price. Production is measured in wins above replacement, which is an estimate of how many wins a player added compared to a freely available substitute. Price is measured as a share of the salary cap, so that contracts from different years are comparable. The fitted line has a slope, which is the price of one win, and an intercept, which is what a player producing nothing is worth.

Step two, the anchor. For any player at any point in time, I take a weighted average of his production in the two preceding seasons, weighted 60% to the more recent one. Nothing from the current season enters. This is the model's defence against using information that was not available at the decision date.

Step three, the forward projection. An aging curve estimates how a player's production changes as he gets older. The curve is used as a percentage path rather than a level, so that a player's own anchor is multiplied by the shape the curve implies.

Step four, discounting and summation. Each future season's projected value is multiplied by the probability the player is still playing, the cost is subtracted, and the result is converted into present-day terms. The total is the contract's net present value.

\---

\## 3. The Central Finding: Contract Length Is Priced by the Market and Absent from the Model

\### The evidence

The price equation currently relates price to production and nothing else. When I add contract length to it, the results move a long way.

| specification | price of one win | value of a zero-win player | share of price variation explained |

|---|---|---|---|

| production only (current model) | $1.84M | $1.75M | 46.5% |

| production and contract length | $0.99M | $0.26M | 72.7% |

The coefficient on contract length is $0.82 million per season for each additional contract year, with a t-statistic of 34.5. For context, a t-statistic above roughly 2 is conventionally treated as evidence that a relationship is real. A value of 34.5 is far outside the range where sampling noise is a plausible explanation.

I checked the obvious alternative explanations.

Length is not standing in for quality. Length and production are correlated at 0.522, which is the condition under which omitting length biases the production coefficient, but the length effect survives controlling for production.

Length is not standing in for age. Length and age at signing are correlated at −0.120, and adding age to the equation leaves the length coefficient at $0.83 million per year with a t-statistic of 34.9.

Length is not an artifact of the straight-line form. In a fuller specification that also allows the price of a win to bend at different production levels and allows defencemen to price differently, length still carries $0.78 million per season per year of term, with a t-statistic of 31.7.

\### Why the effect is so large

Contract length is bought and sold. A team taking a player for eight years is buying cost certainty and the player's unrestricted free-agent seasons; the player is selling flexibility and buying security. Both sides of that exchange appear in the annual cap hit. The current model treats the annual cap hit as if it were a payment for expected production only, so the entire term premium lands on the cost side of the surplus calculation with nothing corresponding on the value side.

The math follows directly. Consider a player whose trailing production is 3.0 wins above replacement.

The current model prices him at 0.018319 + 0.019249 × 3.0 = 7.61% of the cap, which is $7.27 million at the 2025-26 ceiling, and it prices him at that figure regardless of how long the contract runs.

The term-aware equation prices the same player at $9.81 million per season on an eight-year deal and at $4.06 million per season on a one-year deal.

The current model, therefore, undervalues an eight-year contract for that player by $2.55 million per season and overvalues a one-year contract for the same player by $3.20 million per season. Across eight seasons, the eight-year error alone is roughly $18 million to $20 million in present-value terms.

\### What this does to the model's output

The finished valuations show the pattern the math predicts.

| contract length | mean net present value | median | number of contracts |

|---|---|---|---|

| 1 year | +$0.90M | +$0.93M | 1,370 |

| 2 years | +$1.27M | +$1.40M | 838 |

| 3 years | −$0.59M | −$0.31M | 254 |

| 4 years | −$5.59M | −$4.81M | 141 |

| 5 years | −$8.15M | −$7.73M | 74 |

| 6 years | −$13.54M | −$14.32M | 70 |

| 7 years | −$22.80M | −$21.44M | 61 |

| 8 years | −$27.48M | −$27.07M | 101 |

The correlation between contract length and net present value is −0.750. Squaring that gives 0.5625, so contract length by itself accounts for about 56% of the variation in the model's central output. The observed −$27.48 million average on eight-year deals is of the same order as the $18 million to $20 million the omission mechanically generates, with the aging decline and the composition of players on long deals accounting for the remainder.

\### What this does and does not imply

I want to be careful here, because there is a real finding buried in this and I do not want to argue it away.

Two competing explanations exist for the term premium, and I cannot separate them with the data currently assembled.

The first is that term has a genuine market price. Teams pay more per season to lock a player in, or players accept less for security. Under this reading, the premium is a legitimate component of what a contract is worth, the value side of the model should carry it, and the current negative valuations on long deals are largely an artifact.

The second is that the premium reflects private information. Teams give eight-year contracts to players they believe in beyond what two seasons of production data show, and the length coefficient is absorbing that belief. Under this reading, the negative valuations on long deals are a real finding, because the model is measuring how often those beliefs failed to pay off.

The problem with the model as it stands is not that it picks the wrong explanation. It is that it picks the second one silently, by construction, without ever testing it. An equation with no term variable in it assigns 100% of the term gap to team error. This is an assumption presented as a result.

\### The test that separates the two explanations

The two stories make opposite predictions about realized outcomes, and the project already has the data to check.

Take the residual term premium on each contract, meaning the part of the annual cap hit that contract length explains and production does not. Then ask whether that premium predicts realized production over the life of the contract, measured against the independently built game-level metric rather than the same wins-above-replacement source that produced the projection.

If the premium predicts nothing, teams were paying for term as such, and the value side of the model should include it. If the premium predicts realized production, teams were paying for private information, that information was correct on average, and the current negative-valuation finding survives with a much stronger defence than it has now.

Either outcome is useful. The first catches a specification error before it reaches a thesis. The second eliminates the first objection any reader would raise, and turns a result that is currently vulnerable into one that is difficult to dismiss.

\### A note on the surplus-ratio defence

The project expresses back-test results as ratios of value sent to value received, on the grounds that ratios are robust to errors in the level of the price of a win. That defence holds against errors that scale both sides of a trade by the same factor. It does not hold here. A trade of a player on an eight-year contract for a player on a one-year contract carries a systematic, mechanical gap of several million dollars per season that does not cancel, because the two sides differ in the omitted variable.

\---

\## 4. Three Further Problems with the Price Equation

\### The price of one win is not constant

The current equation assumes each win costs the same amount, whether it is a fourth-line forward's first win or a first-line centre's fifth. I tested this by allowing the price to bend at production levels of 0, 1, and 2 wins, which correspond to roughly replacement level, an established roster player, and a top-six forward or top-four defenceman.

The formal test for whether a straight line is adequate rejects it. The Ramsey specification test returns F(2, 2345) = 62.78 with a p-value indistinguishable from zero. Allowing the bends raises the share of price variation explained from 46.5% to 50.6%, and the standard model-selection criterion prefers the bent version by a margin of 180 points, which is well beyond the threshold at which the added complexity is considered worthwhile.

The shape the market actually pays is as follows.

| trailing production | price per win at the 2025-26 ceiling |

|---|---|

| below 0 wins | −$0.74M |

| 0 to 1 wins | $2.28M |

| 1 to 2 wins | $2.42M |

| 2 wins and above | $1.77M |

| \*current single slope\* | \*$1.84M\* |

The negative segment at the bottom is not teams behaving irrationally. It is composed of 134 declining veterans, averaging 1.7 contract years at $1.61 million, whose contracts were signed against what they used to produce. The flattening at the top reflects the collective agreement's ceiling on individual contracts, which caps what an elite player can be paid regardless of how much better he is than the next tier.

The consequence for the model is not a uniform shift. I re-priced the full set of observed-season valuations using the bent equation with a position control, and the average change across 6,892 player-seasons was $39,263. That is close to nothing. Underneath that average:

Defencemen move by +$321,248 per season and forwards by −$114,306 per season.

Players in the 2 to 3 win range move by +$454,949 per season; those in the 0 to 1 win range move by −$249,046.

This is the pattern that matters. The errors cancel in aggregate and do not cancel by category. The project's stated purpose is to identify categories of systematic mispricing, and a valuation model whose own errors are category-correlated will generate categories of apparent mispricing on its own, with no team behaviour involved.

\### The position-blind design is not delivering what it assumes

The model prices a win identically regardless of position, on the stated reasoning that any positional difference in how the market pays will appear afterwards as leftover error and can be studied then.

That reasoning requires the leftover error to average to zero within each position. It does not. Regressing the model's errors on a defenceman indicator returns a coefficient of +0.597 percentage points of the cap, which is $570,000 per season, with a t-statistic of 6.80 and a p-value of approximately one in one hundred billion. Forwards average −$204,000 and defencemen +$389,000 in the raw split.

A leftover error with a non-zero average for a whole position is not a positional effect waiting to be studied. It is a variable the valuation is missing, and each trade that exchanges forwards for defencemen inherits it.

A further difficulty exists that is specific to this project. The independent validation work already established that the wins-above-replacement measure tracks an external benchmark well for forwards and poorly for defencemen, with correlations of roughly 0.65 and 0.28 to 0.30 respectively. So when the market pays a defenceman more than his measured production justifies, two explanations exist, which are that teams overpay defencemen and that the measure does not capture what defencemen do. The model currently assumes the first. Given the project's own validation evidence, the second is at least as likely, and probably more so.

\### A quarter of the estimation sample is not made of market prices

Of the 2,349 contracts used to fit the price equation, 571, or 24.3%, are at or within 2% of the league minimum salary. Those figures are set by the collective agreement. They are the lowest amount a team is permitted to pay rather than an amount anyone negotiated, and in many cases the team would pay less if it were allowed to.

Fitting a price curve through them is comparable to estimating what used cars are worth from a lot where a quarter of the windscreen stickers read "$500" because that is the dealer's legal floor rather than an assessment of the vehicle.

This has a concrete consequence the project has already paid for. Because the fitted line has to pass through a mass of contracts pinned at the floor along with the declining veterans described above, the intercept is pulled up to 1.83% of the cap, or $1.75 million. That figure is the model's estimate of what a player producing zero wins is worth, and it is 2.3 times the actual league minimum of $775,000. It is also the number that made nearly each fringe restricted free agent look worth retaining, which is what required a separate calibration step using observed retention decisions to correct.

Allowing the price curve to bend drops the intercept to $1.26 million on its own. Adding contract length drops it to $0.26 million. A meaningful share of the calibration step is repairing damage the price equation created.

The standard treatment for a dependent variable with a floor of this kind is a censored regression, which estimates the line the underlying prices would trace if the floor were not there. Dropping the floored observations entirely, which is a cruder approach, moves the price of a win by −5.9%.

\---

\## 5. The Model Prices Its Best Guess Rather Than the Range of Outcomes

For each future season, the model takes one number, which is its single best estimate of the player's production, and runs that number through the price equation.

The future is not one number. It is a distribution. When the price equation is curved, running the average outcome through the equation gives a different answer from averaging what each outcome would be worth.

Consider a player projected at replacement level three years out. In roughly half his possible futures he stays there and produces nothing of value above a freely available substitute. In the other half he re-establishes himself as a roster regular, and that half is worth a great deal, because the price curve is steep immediately above zero. Averaging what the outcomes are worth gives a larger figure than pricing the average outcome. The model does only the second, which is comparable to valuing a lottery ticket at its most likely payout.

Using the project's own documented forecast accuracy to set the width of the distribution, the size of the gap is as follows.

| projected production | one year out | three years out | five years out |

|---|---|---|---|

| 0.0 wins | +$0.71M | +$1.19M | +$1.36M |

| 0.5 wins | +$0.20M | +$0.58M | +$0.73M |

| 1.0 wins | +$0.06M | +$0.23M | +$0.34M |

| 2.0 wins | −$0.15M | −$0.23M | −$0.22M |

| 3.0 wins | −$0.01M | −$0.05M | −$0.07M |

The understatement is concentrated on low-projection players and grows with horizon, which is the population where the option-like character of a contract matters most.

There exist two qualifications with this. The size of the gap depends on the shape of the price curve below zero, which the previous section shows is contaminated by the censoring and by the declining-veteran contracts. The direction is reliable; the magnitude should be treated as indicative until the price equation is settled.

\---

\## 6. Goaltender Valuation: Contract Seasons Past the Observed Window Are Priced at the League Average

\### What the rule says and what the code does

The goaltender pillar deliberately holds a goaltender's projection flat across the length of his contract. Goaltenders receive no aging curve and no comparable search, on the reasoning that goaltender performance is volatile enough that a flat carry-forward beats any curve the data would support. The projection is shrunk heavily toward the league mean, at 65% against 45% for skaters, for the same reason.

That is the rule. It is not what happens for seasons beyond the observed production window.

181 contract-seasons, covering 38 goaltenders, carry a projection of exactly 2.189172466 wins. That figure is not any individual goaltender's projection. It is the league average, applied identically to each of the 181 rows. Nothing in the recorded decisions calls for a switch to the league average in out-years, and the flat-carry rule specifies the opposite, so this reads as an implementation error rather than a design choice.

The discontinuity is visible inside a single contract. Andrei Vasilevskiy's rows are as follows.

| season | projection used | source | value | cost | surplus |

|---|---|---|---|---|---|

| 2024-25 | 2.662 | his own record | $3.71M | $9.50M | −$5.79M |

| 2025-26 | 3.167 | his own record | $4.53M | $9.50M | −$4.97M |

| 2026-27 | 3.419 | his own record | $5.21M | $9.50M | −$4.29M |

| 2027-28 | \*\*2.189\*\* | \*\*league average\*\* | $4.21M | $9.50M | −$5.29M |

The flat-carry rule requires 3.419 in the final row. The switch to 2.189 reverses the direction of the value path in the one season where nothing about the goaltender changed.

\### The error is directional and concentrated in the assets that matter

Because the placeholder is a single number applied to each goaltender, the error is proportional to how far a goaltender sits from average, and it is signed by whether he is better or worse than average.

| goaltender | own projection | placeholder seasons | error per season |

|---|---|---|---|

| Logan Thompson | 3.79 | 4 | −$1.62M |

| Ilya Sorokin | 3.52 | 5 | −$1.35M |

| Igor Shesterkin | 3.44 | 6 | −$1.27M |

| Andrei Vasilevskiy | 3.42 | 1 | −$1.24M |

| Connor Hellebuyck | 3.29 | 4 | −$1.11M |

| Spencer Knight | 2.99 | 2 | −$0.81M |

| Matt Tomkins | 1.37 | 1 | +$0.83M |

| Joonas Korpisalo | 1.41 | 1 | +$0.79M |

Elite goaltenders on long contracts are undervalued by $1.1 million to $1.6 million in each affected season. Weak goaltenders on long contracts are overvalued by a similar margin. The mean absolute error across the 181 rows is $529,000 per season. Shesterkin carries six affected seasons, so his contract's total error approaches $7.6 million in present-value terms.

This matters more than the row count suggests because starting goaltenders on long contracts are among the highest-value and least frequently traded assets in the league. A back-test that mis-prices them by more than a million dollars per season in a predictable direction will read goaltender trades wrongly and will read them wrongly in a consistent way.

\### This failure has occurred once before under a different name

The project record already contains one instance of a league-average fallback producing exactly this kind of distortion. Goaltenders on entry-level contracts with no production history were assigned the league mean, which placed unknown prospects at the top of the surplus list, and the fallback was removed once identified. The same mechanism is present here, applied to out-years rather than to unknown players, and labelled differently.

The lesson worth recording is that a league-average fill is never neutral. It is a strong assertion that a specific player is exactly average, and in a model built to detect mispricing it manufactures mispricing wherever it appears.

\### Two smaller items in the same pillar

The trailing production column in the rebuilt goaltender value file contains the text \`no\_observed\_war\_history\` in 748 of 1,752 rows. The earlier version of the same file left the field blank. The column therefore loads as numeric in one file and as text in the other under the same name, which will silently break any arithmetic performed on it. Nothing downstream currently fails, because the self-calibration step reads a different column and recovers the stored coefficients exactly, but the inconsistency should be removed before another script reads that file.

The per-team split rows are handled correctly. Goaltenders traded mid-season appear as separate rows for each team, and the engine sums within goaltender-season before applying anything else. I verified this against the standing flag and found it clean.

\---

\## 7. Terminal Value: The Retention Gates Exclude the Departures They Are Assumed to Cover

\### The reasoning and where it breaks

Restricted free-agent control years are valued using observed retention rates rather than the exit hazard applied elsewhere in the model. The reasoning is sound as stated: a team declining to tender a player is itself a departure, so the observed retention rate already captures the risk that he is gone, and applying the exit hazard on top of it would charge the same risk twice.

The reasoning depends on the retention rates being estimated from each observable decision. They are not.

The calibration requires a production anchor at the decision point in order to sort the player into a talent bucket. A player with no recent NHL games has no anchor, so he is skipped. Players with no recent NHL games are precisely the players teams walk away from.

| group | number of decisions | share the team walked away from |

|---|---|---|

| used in the calibration | 1,231 | 21.3% |

| dropped for having no anchor | 1,039 | 33.9% |

| \*\*all eligible decisions\*\* | \*\*2,270\*\* | \*\*27.0%\*\* |

Nearly half of the observable decisions are dropped, and the dropped group is walked away from 1.6 times as often as the group the rates are fitted on. The true walk-away rate is 27.0% and the model uses 21.3%.

\### Why the gap matters more than its size suggests

The 5.7 percentage point gap is close to the departure margin the retention gates are assumed to absorb. So the current treatment leaves control years carrying neither risk properly. The exit hazard is switched off on the reasoning that the retention rates cover departure. The retention rates are estimated on a sample that excludes the departures.

The consequence compounds, because the gates are applied multiplicatively across each control year. For a player with three control years in a bucket where the true rate is understated, the overstatement of terminal value runs to roughly 20% to 25%. The affected buckets are the fringe and below-replacement groups, which is the population the calibration was built to correct in the first place.

The fix does not require a new decision. Each of the 1,039 dropped cases has an observable outcome, and having no recent NHL games is itself informative rather than missing. Treating those cases as observed decisions, with a separate bucket for players with no anchor, uses each of the 2,270 decisions and removes the selection.

\### A related item in the same calculation

The qualifying offer is computed from the final contract year's base salary, with average annual value used as a fallback when salary is unavailable. The collective agreement caps a qualifying offer at 120% of the contract's cap hit, a rule that exists specifically to limit what a front-loaded contract can generate at the tender.

Average annual value is the figure that erases front-loading by construction. Using it as the fallback therefore disables the 120% rule in exactly the cases the rule was written for, since a front-loaded contract is one whose final-year salary sits far above its average. The fallback should either take the contract's highest observed salary or flag the row rather than substitute the one figure that neutralizes the constraint.

\---

\## 8. The Draft Pick Curve: Sound in Shape, Thinner at the Top Than the Point Estimates Suggest

The draft curve survived my reading. It is monotone across each bucket without imposed smoothing, the bucket boundaries follow sensible breaks in the underlying distribution, and the construction is documented and reproducible. Three items belong in the write-up as stated uncertainty rather than as corrections, and one connects back to section 3.

\### Precision at the top of the draft is weak

The fitting sample uses eleven cohorts, so it contains eleven first-overall picks. Bootstrapping the top buckets, meaning resampling the observed picks with replacement several thousand times to see how far the average moves, gives the following.

| bucket | picks | mean value | 95% interval |

|---|---|---|---|

| pick 1 | 11 | $13.7M | $9.7M to $18.2M |

| pick 2 | 11 | $8.9M | $6.5M to $11.3M |

| picks 3-5 | 33 | $7.3M | $5.5M to $9.4M |

The first-overall estimate spans an 88% range from the bottom to the top of its interval. The gap between the first and second pick is $4.8 million with an interval running from $0.2 million to $9.9 million, which clears zero but only just, at a 1.9% chance the ordering reverses on resampling.

The estimates are usable. What should not be presented without the interval attached is any claim that the first pick is worth substantially more than the second, because that claim rests on eleven observations per side.

\### The mean is a thin-tail estimate in the later rounds

Draft outcomes are severely skewed, and the skew worsens as the draft proceeds.

| pick range | picks | mean | median | produced nothing | top 10% share of all value |

|---|---|---|---|---|---|

| 1-32 | 352 | 0.0593 | 0.0496 | 7.1% | 28.9% |

| 33-100 | 747 | 0.0242 | 0.0134 | 43.1% | 41.3% |

| 101-224 | 1,225 | 0.0113 | 0.0000 | 69.6% | 62.0% |

For picks past 100, seven in ten produce nothing and the best 10% of picks carry 62% of the value in the range. The mean remains the correct quantity for pricing a pick, since a team acquiring one is buying the whole distribution. The reported standard error, however, assumes a symmetry the data does not have, and it will understate the uncertainty on the late buckets. Bootstrap intervals should replace it.

\### Name matching carries more weight than the coverage rate implies

Of 1,167 picks linked to a professional record, 299, or 25.6%, resolved by name or alias rather than by a shared identifier. Those picks account for 17.2% of the total value in the curve. The linkage chain is well guarded and I found no incorrect match, but a sixth of the curve resting on name agreement should be stated rather than left implicit.

\### The curve inherits the price-equation problem from section 3

The curve values entry-level seasons only. I verified this directly: entry-level surplus equals total surplus on each row, so the entire restricted free-agent window is priced at zero surplus.

That follows from a defensible rule, which is that players past their entry-level contract are paid the market rate for realized production and therefore generate no surplus by construction. But the market rate in question is the same equation section 3 shows undervalues long contracts by roughly $2.55 million per season for a three-win player. Second contracts for successful draft picks are long contracts, frequently the longest a player will sign.

So the zero-surplus assumption for post-entry-level seasons is not independent of the misspecification. If contract length turns out to carry genuine market value, then successful draft picks generate surplus in their second contracts that the curve currently sets to zero, and the top of the curve is understated. The draft pillar cannot be treated as settled until the price equation is, and the two should be resequenced accordingly.

\---

\## 9. Implementation Errors in the Projection and Risk Machinery

\### A guard rail exists on one side only

The aging curve does not hand the projection a production number. It hands over a percentage path, for example a decline of 15% in the first year and a further 12% in the second, and the projection multiplies the player's anchor by that path.

A cap prevents that percentage from exceeding +200%. No corresponding lower bound exists. When the curve's own starting level sits near zero, dividing by it produces multipliers that go negative; in synthetic testing across 1,097 players, 418 produced a negative multiplier and the most extreme was −5.98. A multiplier of −5.98 means the model is asserting that a player will produce nearly six times his current output in the opposite direction, which is not a physically possible outcome.

Live exposure is smaller than the synthetic test suggests, at 67 contract-seasons across 41 contracts, with the most extreme real multiplier being −1.61. The affected contracts are, however, concentrated in the population the back-test depends on. They include Kris Letang in 2022, Drew Doughty in 2019, John Carlson in 2018, Morgan Rielly in 2022, Hampus Lindholm in 2022, and Colton Parayko in 2022, which is to say expensive long-term defencemen.

The league-minimum floor on value hides part of this, because a value computed from an impossible production figure is floored before it is reported. The impossible figure still propagates, because it is used to select the player's retirement-risk category and to price his restricted free-agent years. The floor is, therefore, doing load-bearing work it was not designed for.

The threshold intended to prevent this is set at a starting level of 0.25 wins per 82 games. The pathology occurs for starting levels between roughly 0.25 and 0.40, so the threshold is set too low. The cap is also asymmetric, permitting a threefold increase but an unbounded decrease, which biases projections downward on its own.

\### The retirement-risk lookup is off by one year

Each future season is multiplied by the probability the player is still in the league. The probability comes from a table built by asking, of players who were a given age in a given season, what share did not appear the following season. The entry for age 30, therefore, describes the odds of getting from 30 to 31.

The code looks up the wrong entry. To decide whether a player survives into the next season, it looks up the age he will be in that next season rather than the age he is now. Because risk rises steeply with age, this makes each player look more fragile than the data supports.

For players who remain inside one age bracket for the whole contract the effect is zero. It matters when a player crosses one of the bracket boundaries at 23, 27, 31, or 35. For a 30-year-old fringe player on a five-year contract, the model as written gives a 33.5% probability that he is still playing in the fifth season; the corrected lookup gives 45.5%. This is a 35.8% understatement of that season's value, and it arises from a one-character error.

\### Two cells in the risk table read zero and the model treats them as certainty

The risk table has twenty cells, being four quality tiers by five age groups. Cell sizes vary from 743 players down to 15. Two cells contain no observed departures.

Star players aged 22 and under, with 26 observations, return 0.0%.

Star players aged 31 to 34, with 40 observations, return 0.0%.

The model, therefore, treats a 32-year-old star as certain to play each remaining season of an eight-year contract. Not merely likely. Certain. That is the tier holding the largest concentration of trade value in the league.

The table is also internally inconsistent, since star players aged 27 to 30 return 1.2%, which is higher than the zero recorded for the older group. Risk does not fall as players enter their thirties.

The remedy is one the project already uses elsewhere. The aging curve pulls thinly populated comparable estimates partway toward a global average using a fixed pseudo-count. The same device applied to the risk table, or a simple parametric model of risk on quality and age, would remove the zero cells and restore the expected ordering. No minimum-sample guard of any kind exists in the table's construction.

\### Two decisions interact in a way that is nowhere recorded

A decision was made that a player whose trailing production is negative should have each future season projected at exactly replacement level, on the empirical finding that below-replacement players who keep playing overwhelmingly recover. That decision is well supported and I am not questioning it.

The risk table sorts players into quality tiers by their production figure. A projected figure of exactly zero falls into the tier for players between zero and one win, not the tier for players below zero. So the instant the replacement-reversion rule is applied, the player quietly receives materially better survival odds: 33.3% annual risk instead of 51.6% for a player aged 35 or over, and 15.8% instead of 22.2% for a player aged 31 to 34.

This may well be the correct treatment, since the rule does assert that the player reverts to replacement level and replacement-level players carry replacement-level risk. My point is that it is currently an unnoticed consequence of two separate decisions meeting rather than a decision anyone made, and it should be recorded either way.

\---

\## 10. Data-Handling Errors

\### One player loses half a season

The wins-above-replacement source records Nick Paul under two spellings, being "Nick Paul" for his Ottawa half of the 2021-22 season and "Nicholas Paul" for his Tampa Bay half after the trade deadline. This is not the same as the deliberate per-team splitting applied to goaltenders, which the project already handles. It is an inconsistency in the source file.

The name-cleaning code correctly recognizes both spellings as the same player. A de-duplication step then discards one of them, removing 21 games and 0.44 wins. His 2022 anchor is short by 0.26 wins, which is approximately $418,000 per season, and 2022 is the season he signed a seven-year contract, so the error rides through the whole agreement.

A safety check is written into the code for precisely this situation. It can never trigger, because the de-duplication step runs first and removes the condition the check looks for.

Four other players are affected by the same spelling inconsistency, being Matěj Blümel, Max Lajoie, Nick Abruzzese, and Nick Merkley. All four are marginal players and the valuation consequence is negligible.

\### The aging curve does not clean names

Each other script in the chain normalizes player names before matching. The aging curve groups players by their raw name string with no cleaning applied.

Two consequences follow. The five players above become ten separate careers, each holding a fragment of its true history. And the project's standing exclusions for players whose records are merged in the source file, together with its flagged same-name collisions, are enforced in the valuation engine and not enforced here.

\### "Last season" sometimes means several years ago

The aging curve smooths a player's production level using a two-season average. It takes the previous entry in the player's list of qualifying seasons. If the player missed a year through injury, or had a season below the twenty-game threshold that was filtered out, the previous entry is not last season.

Of 7,869 two-season windows used to build the curve, 339, or 4.3%, pair non-consecutive seasons. The largest gap being treated as consecutive is nine years.

The same routine also computes a trend feature describing how quickly a player is improving or declining, and it divides the change by one year regardless of the true gap. A nine-year change is, therefore, recorded as a one-year trend, and that inflated figure is one of the standardized inputs used to select the player's comparables.

\### One identifier can carry several players

The file that attaches ages to production records was built by matching players across sources. 33 identifiers in that file each carry more than one player name, covering 322 rows and 69 distinct players. The pairs are lookalike names, and the examples make the mechanism obvious.

One identifier carries both Mark Cullen and Matt Cullen. Another carries Marcel Hossa and Marian Hossa. Others pair Taylor and Tom Pyatt, Jared and Jordan Staal, Rick and Riley Nash, and Jeff and Justin Schultz. One identifier carries three players, being Brandon, Brett, and Brody Sutter.

The consequence for the aging curve is small. 237 of the polluted rows are curve-eligible, which is 2.54% of the curve's input, and because lookalike pairs are usually close in age, most polluted rows happen to carry a correct age anyway. Only one player shows a detectably impossible age, that being a first qualifying season at age 17.

The exposure is not the ages. It is that the file is now a permanent part of the project's data and any future join through it on identifier alone will silently attach the wrong player, with no error raised. The remedy is to require name agreement alongside identifier agreement on each join through this file, which is the guard the draft linkage already applies. The recorded count for this issue should be corrected from 113 rows across 36 players to 322 rows across 69 players.

\---

\## 11. Identification and Documentation Points

\### Three components use the whole sample to value the past

The aging curve, the price equation, and the retirement-risk table are each estimated on the full 2018 to 2025 window and then applied backwards to value trades from the start of that window. A valuation dated 2018 is, therefore, built partly from information generated in 2024.

The project documents this for the aging curve and describes the intended defence. The price equation and the risk table carry identical exposure and are not flagged anywhere. A reader is likely to notice the inconsistency in treatment before noticing the underlying issue.

My recommendation is to present all three together under one defence, which is that these are structural market parameters rather than player-specific information, together with one stability check showing how far the estimates move when fitted on the first half of the sample only. The project has already written this defence for the draft-pick curve; the same argument extends here with no modification.

\### One documented claim is not true as implemented

The aging curve's documentation states that no look-ahead is present and that each input is trailing. This is true for the player being projected, whose own future seasons are excluded. It is not true for his comparables, whose profiles are drawn from the entire panel including seasons after the valuation date. The wording should be corrected to match the implementation.

\### The discount structure is missing a component the specification promises

The project's model specification defines the discount rate as injury risk plus the opportunity cost of cap space. Injury risk is present, as the survival probability. The 3% figure in the denominator is the assumed rate of salary cap growth, which performs a different function, being the conversion of dollars across years rather than a charge for tying up cap space.

Either the specification should be rewritten to state that expressing value in cap-share terms is the treatment of cap opportunity cost, which is a defensible position, or the component should be added.

\### The league-minimum floor is applied at the wrong point in the calculation

The floor exists on the reasoning that a replacement player can always be signed at the league minimum, so a roster spot is never worth less than that amount. The code applies the floor to the projected value and then multiplies by the survival probability. A player with a 50% chance of still playing, therefore, contributes $388,000 against a $775,000 floor.

If the reasoning behind the floor is that the roster spot retains its minimum value regardless of what happens to the individual, the floor belongs after the survival adjustment rather than before it.

\### Value and cost are measured on slightly different instruments

The price equation is fitted on average annual value. The costs used in the valuation are cap hits. These are identical for most contracts and differ for those carrying performance bonuses and for contracts signed at age 35 or older. The effect is small and belongs in the limitations rather than in a revision.

\---

\## 12. Where These Recommendations Conflict with Decisions Already Made

Several recommendations above cut against decisions the project has already taken and recorded. I set out each conflict and my reasoning below.

\### Adding contract length conflicts with valuing production alone

The decision. The model values production. Contract characteristics belong on the cost side, and any gap between what production is worth and what the contract costs is the surplus the project exists to measure.

Why I am recommending a change anyway. The conflict dissolves once the two distinct uses of the price equation are separated. Contract length does not have to enter the value calculation for it to belong in the estimation. Including length as a control changes the estimated price of one win, from $1.84 million to $0.99 million, and the estimated value of a zero-win player, from $1.75 million to $0.26 million. Those two figures are then applied to each player. The recommendation is not that long contracts should be valued more highly. It is that the price of a win is currently mis-estimated by 86% because a variable correlated with production at 0.522 was left out of the regression that produces it.

Once the price of a win is estimated correctly, the project retains complete freedom to evaluate each player at a common reference term, which preserves the production-only value concept while removing the bias from the coefficient. This is the standard treatment of an omitted variable correlated with the regressor of interest, and it does not require conceding that term has value.

\### Allowing the price of a win to bend conflicts with a single flat rate

The decision. One rate prices the whole market, on the finding that restricted and unrestricted free agents are statistically indistinguishable once goaltenders are removed from the sample, and on the reasoning that expressing results as ratios protects against errors in the level of the rate.

Why I am recommending a change anyway. The earlier finding tested whether two groups of players face different rates. It did not test whether the relationship between production and price is a straight line, which is a separate question, and the answer is no with F = 62.78. The ratio defence protects against errors that scale the whole rate up or down. It does not protect against a shape error, because a shape error moves the two sides of a trade by different amounts. The re-pricing exercise in section 4 makes this concrete: the average change is $39,263 and the change for defencemen is $321,248, so the error is invisible in aggregate and material by category.

\### Adding a position control conflicts with the position-blind design

The decision. The rate is fitted without regard to position, and positional effects are recovered afterwards as residuals.

Why I am recommending a change anyway. The design as stated is coherent and I would keep it if it were working. It is not working, because the residuals do not average to zero within position; they average +$570,000 per season for defencemen with a t-statistic of 6.80. A residual with a non-zero mean is a variable the valuation is missing, and it enters each valuation of each defenceman rather than sitting in a residual file waiting to be analysed.

I want to flag one qualification against my own recommendation. Adding a position control assumes the gap reflects how the market prices, when the project's own validation work suggests it may instead reflect how the production measure performs. If defensive value is systematically under-measured, then a position control is partly correcting a measurement failure rather than capturing a market behaviour, and the paper should say so rather than presenting the control as a clean market finding. Either way the current design conflates the two, and adding the control at least makes the choice explicit.

\### Estimating with a censored regression conflicts with the fitted intercept as replacement cost

The decision. Replacement cost is the regression intercept rather than the league minimum, on the reasoning that the intercept is what the market actually pays a player producing nothing.

Why I am recommending a change anyway. The intercept is not currently measuring what the market pays a zero-production player. It is measuring where a straight line lands when it is forced through 571 contracts pinned at a legislated floor together with 134 declining veterans paid on reputation. The evidence that the intercept is an artifact rather than an estimate is that it moves to $1.26 million when the line is allowed to bend and to $0.26 million when contract length is included, without any change to the underlying data. A stable parameter does not move that far under specification changes that leave the sample untouched.

A second piece of evidence exists internal to the project. The intercept implied that nearly each fringe restricted free agent was worth retaining, which contradicted the observed record of retention decisions and required a separate calibration step to repair. That mismatch is a symptom, and treating the censoring addresses the cause.

\### Applying the floor after survival conflicts with the recorded discount structure

The decision. Survival probability multiplies the value side while the cost side is left unconditional, on the reasoning that a player who leaves stops producing while his cap charge may persist.

Why I am recommending a change anyway. I agree with the decision as it applies to a player's production above replacement. The conflict is narrower than it appears and concerns only the floor. The floor's stated reasoning is that the roster spot is always worth at least the league minimum, because a substitute can always be signed at that price. That reasoning does not depend on the original player being present. If it did, the floor would not be justified in the first place. Applying the survival probability to a quantity defined as being available regardless of survival is internally inconsistent, and the fix affects only the floored rows.

\### Re-estimating the retention gates conflicts with leaving the exit hazard off control years

The decision. Restricted free-agent control years carry observed retention rates instead of the exit hazard, because a team declining to tender a player is itself a departure and applying both would double-count the same risk.

Why I am recommending a change anyway. I agree with the decision entirely, and my recommendation does not overturn it. The double-counting argument is correct and the retention rates are the right instrument. My point is narrower: the rates as currently estimated do not contain the departures the argument credits them with, because the players who were walked away from most often are the ones excluded from the estimation for lacking a production anchor. Restoring those 1,039 cases makes the decision work as intended rather than replacing it. If anything, the recommendation defends the original reasoning, since a retention rate that genuinely captures departure is what makes switching off the exit hazard legitimate.

\### Carrying a goaltender's own projection into out-years conflicts with nothing

I include this for completeness rather than because a conflict exists. The flat-carry rule already requires a goaltender's own shrunken projection to be held constant across the contract. The league-average placeholder contradicts that rule rather than implementing any alternative to it, and no recorded decision supports the substitution. This is a correction to bring the code into line with a decision already taken, not a proposal to change one.

\---

\## 13. Roadmap

The ordering below is driven by dependency rather than by severity. Several items look independent and are not: the price equation feeds the draft curve, the terminal value, and the retention calibration, so correcting it after those are rebuilt means rebuilding them twice.

Each item carries a status column so this document can serve as the working tracker. Statuses are \`open\`, \`in progress\`, and \`done\`.

\### Stage 1: Corrections that require no decision

These bring the code into line with rules the project has already adopted. None of them changes the intent of a recorded decision, so none of them needs to wait on anything else. They can proceed in parallel with stage 2.

| # | item | section | effect | status |

|---|---|---|---|---|

| 1.1 | Carry each goaltender's own projection into out-years, removing the league-average placeholder | 6 | corrects 181 contract-seasons; up to $1.6M per season per goaltender | open |

| 1.2 | Correct the retirement-risk lookup to use the current age rather than next season's | 9 | up to 35.8% understatement on late contract seasons | open |

| 1.3 | Add a lower bound on the projection multiplier and raise the starting-level threshold | 9 | removes impossible values on 67 contract-seasons | open |

| 1.4 | Apply shrinkage to thinly populated cells in the risk table | 9 | removes two cells asserting certainty | open |

| 1.5 | Repair the de-duplication step that discards a traded player's second team-half | 10 | one material case, four minor | open |

| 1.6 | Normalize player names in the aging curve and apply the standing exclusions there | 10 | five split careers; enforces existing exclusions | open |

| 1.7 | Require age adjacency in the aging curve's two-season window and its trend feature | 10 | 339 of 7,869 windows | open |

| 1.8 | Require name agreement on each join through the age file | 10 | permanent guard; corrects recorded counts to 322 rows, 69 players | open |

| 1.9 | Make the trailing-production column numerically typed in the goaltender value file | 6 | prevents a silent type failure downstream | open |

| 1.10 | Replace the average-annual-value fallback in the qualifying-offer calculation | 7 | restores the 120% rule where it was written to apply | open |

\### Stage 2: The test that determines what the price equation should be

This is the highest-value item in the review and it gates stage 3. Nothing in stages 3 through 5 should be rebuilt before it is answered, because the answer determines the specification everything else consumes.

| # | item | section | why it gates the rest | status |

|---|---|---|---|---|

| 2.1 | Test whether the residual term premium predicts realized production, measured against the independent game-level metric | 3 | decides whether contract length carries genuine market value or reflects private information; determines whether the long-contract result is a finding or an artifact | open |

The test should be specified before it is run, including which side counts as which outcome, so the result cannot be read after the fact to suit whichever conclusion is preferred. Both outcomes are useful and neither is a failure.

One constraint on the measurement. The independent metric must not be tuned toward better agreement with the production source while this test is pending, or the test loses its meaning.

\### Stage 3: The price equation

Once stage 2 resolves, the price equation can be settled. The candidate specification raises the share of contract price explained from 46.5% to 74.5%.

| # | item | section | status |

|---|---|---|---|

| 3.1 | Include contract length as a control and evaluate each player at a common reference term | 3, 12 | open |

| 3.2 | Allow the price of a win to bend, with breaks at replacement, one win, and two wins | 4, 12 | open |

| 3.3 | Treat the league-minimum floor as censoring rather than as observed prices | 4, 12 | open |

| 3.4 | Add a position control, with the measurement qualification stated in the write-up | 4, 12 | open |

| 3.5 | Re-derive replacement cost from the corrected intercept | 4, 12 | open |

| 3.6 | Price the range of outcomes rather than the single best estimate, once the curve shape is settled | 5 | open |

Item 3.6 depends on 3.2 and 3.3, since the size of the effect is a function of the curve's shape below zero, which those two items determine.

\### Stage 4: Everything the price equation feeds

Each of these consumes the price equation and should be rebuilt only after stage 3 is locked.

| # | item | section | dependency | status |

|---|---|---|---|---|

| 4.1 | Re-estimate the retention gates on each of the 2,270 observable decisions, with a separate bucket for players lacking an anchor | 7 | independent of stage 3, but pairs naturally with 4.2 | open |

| 4.2 | Revisit the fringe-retention calibration against the corrected intercept | 4, 7 | requires 3.5 | open |

| 4.3 | Re-examine the zero-surplus assumption for post-entry-level seasons in the draft curve | 8 | requires 3.1 | open |

| 4.4 | Move the league-minimum floor to after the survival adjustment | 11, 12 | requires 3.5 | open |

| 4.5 | Re-run the full valuation chain and record how far each output moves | all | requires stages 3 and 4 | open |

Item 4.3 is the one most likely to be overlooked. The draft curve currently reads as finished work, and it is not independent of the price equation.

\### Stage 5: Documentation and identification

These require no rebuilding and can be written at any point. They are placed last only because several of them describe the corrected model rather than the current one.

| # | item | section | status |

|---|---|---|---|

| 5.1 | Consolidate the three retrospective-estimation exposures into one documented position with one stability check | 11 | open |

| 5.2 | Correct the aging curve's claim that no look-ahead is present | 11 | open |

| 5.3 | Resolve whether cap-share conversion is the treatment of cap opportunity cost or whether the component is missing | 11 | open |

| 5.4 | Record the interaction between replacement-reversion and the risk tiers as a decision either way | 9 | open |

| 5.5 | Replace point estimates with bootstrap intervals on the draft curve buckets | 8 | open |

| 5.6 | State the name-match exposure in the draft curve and the value share resting on it | 8 | open |

| 5.7 | Note the average-annual-value against cap-hit mismatch in the limitations | 11 | open |

\### What is not yet reviewed

For completeness, the following have not been examined and may contain further items.

Three of the five scripts behind the game-level metric, being the on-ice reconstruction, the score-state estimation, and the game-log retrieval. The clause join that builds the cost backbone. The validation panel. The prospect extraction script, which has not been run, so there is no output to check against.

The game-level metric carries one finding from a partial review that belongs in this list: the headline validation confirms the chance model and the score-state layer but cannot test the credit-allocation rule, because team sums are identical under any allocation. That should be resolved before the metric is used for mid-season allocation.

\---

\## Appendix: Where Each Item Lives in the Code

| item | file | location |

|---|---|---|

| price equation and fitted coefficients | \`skater\_value\_engine.py\` | \`NEW\_LOCKED\`, stage 0b |

| missing lower bound on the decay ratio | \`skater\_forward\_projection.py\` | \`ratio\_path\`, ratio construction |

| retirement-risk lookup off by one year | \`contract\_npv.py\` | \`\_npv\_skater\`, hazard call |

| zero cells in the risk table | \`exit\_hazard.py\` | \`build\_hazard\_table\` |

| replacement-reversion and risk-tier interaction | \`contract\_npv.py\`, \`skater\_forward\_projection.py\` | quality-tier boundary at zero |

| de-duplication discarding a season | \`skater\_value\_engine.py\`, \`skater\_forward\_projection.py\` | production lookup construction |

| raw-name grouping | \`aging\_curve.py\` | model initialization |

| non-consecutive seasons treated as consecutive | \`aging\_curve.py\` | smoothed-level and profile construction |

| league-minimum floor ordering | \`contract\_npv.py\` | present-value line |

| league-average projection in goaltender out-years | \`goalie\_value\_engine.py\` | forward-carry of the shrunken projection |

| retention-rate estimation sample | \`rfa\_terminal\_value.py\` | qualify-rate calibration |

| qualifying-offer salary fallback | \`rfa\_terminal\_value.py\` | qualifying-offer inputs |

| draft curve interval reporting | \`draft\_yield\_curve.py\` | bucket aggregation |

| identifier-only join through the age file | \`age\_join.py\` | match construction |