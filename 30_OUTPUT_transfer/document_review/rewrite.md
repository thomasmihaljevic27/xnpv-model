# Valuing Players, Draft Picks, and Prospects

An NHL club can acquire a player, a draft pick, or a prospect in the same trade. Comparing those assets requires a common measure of what each is expected to contribute and what the club must pay to obtain that contribution. I measure each asset by its surplus value, which is the market price of its performance less its cap cost over the seasons under club control.

The distinction between performance and surplus matters. A productive player can have negative surplus if his contract costs more than comparable performance would cost in the market. A less productive player can have positive surplus at a sufficiently low cap hit. Draft picks and prospects have value because they may provide future NHL performance at a cost below its market price.

The September 10, 2018 trade between Montreal and Vegas provides an example of all three assets. Vegas acquired Max Pacioretty. Montreal received Tomas Tatar, Nick Suzuki, and a 2019 second-round pick originally belonging to Columbus. Pacioretty and Tatar require contract valuations, Suzuki requires a prospect valuation, and the pick requires an estimate before a player has been selected.

## 1. A Common Measure of Value

Performance is measured in wins above replacement (WAR), an estimate of the wins a player contributes relative to replacement-level performance. Season WAR measures the contribution over the games played. WAR per 82 games measures the player's rate of contribution. Keeping these quantities separate is necessary: a good rate over a short season need not produce a large contribution.

The performance data come from Patrick Bacon's TopDownHockey models. Bacon publishes the construction of WAR, including its offensive, defensive, special-teams, penalty, and shooting components. This provides a documented measure across positions and seasons. WAR remains an estimate of individual contribution; agreement with team results does not establish that credit is allocated correctly among teammates. [1]

PuckPedia supplies the contract terms, cap hits, and trade records. CapWages supplements contracts outside the PuckPedia export's historical coverage. Elite Prospects supplies scoring outside the NHL, and Bacon's NHL equivalency factors convert that scoring to a common unit. NHL draft records link selections to careers. Spotrac's saved injured-reserve records support the long-term injured reserve adjustment. These sources supply different inputs; the performance valuations use one WAR provider throughout.

### Surplus, cap growth, and discounting

A season contributes the market price of its performance less its cap cost. Contributions in later seasons are discounted because they occur later. With k counting seasons from the valuation season, the general calculation is:

@eq general

Vₖ is the value of performance in season k, and Cₖ is its cap cost, both in that season's dollars. The discount rate is 3% a year. The current season has k = 0 and receives no annual discount.

The price of performance is estimated as a share of the salary cap. This permits comparisons across seasons in which the league could spend different amounts. For a forward, for example, the same forecasted performance is worth more dollars when the cap is higher. Future caps are projected to grow by 3% a year from the valuation season's cap.

Equal cap growth and discount rates keep the present value of a fixed cap share constant. The assumed growth in the dollar price of performance cancels its annual discount. A fixed-dollar cap hit still declines in present value: $5 million due four seasons ahead counts as $4.44 million at the valuation date. The cancellation is therefore not a reason to omit discounting from the calculation.

Three percent is a modeling assumption, not an estimate of clubs' impatience. It avoids building a penalty for waiting into a study that will examine how clubs value future assets. It also means that a later pick does not lose value solely because its draft is further away. Whether that assumption matches clubs' preferences remains a limitation. A different relationship between cap growth and discounting would alter that result.

The player calculation starts in the dollars of the valuation season. Pick and prospect values are estimated at the 2025-26 cap of $95.5 million. Before assets are added together, player values are restated at that same cap. Historical trade values are consequently comparable in cap purchasing power.

## 2. Forecasting a Skater's Performance

Each future season requires a performance rate, a games share conditional on appearing, and a probability of appearing at all. The performance rate is WAR per 82 games. Multiplying it by games share gives WAR conditional on playing; multiplying again by the probability of appearing gives expected WAR.

@eq performance

rₖ is WAR per 82 games, gₖ is games share, and pₖ is the chance of playing at least one NHL game. Separating the three distinguishes a decline in performance from a shorter season or an absence from the NHL. Pricing uses WAR conditional on playing, wₖ. The probability of playing is applied to the dollar value afterwards.

The skater forecast is fitted separately for each valuation season using completed earlier seasons. Recent performance generally uses the three preceding seasons with weights of 50%, 30%, and 20%, most recent first. Missing seasons are omitted and the available weights are rescaled. A season needs at least ten games to enter the player's recent record.

### The starting performance rate

One season can be affected by injuries, shooting results, or other short-lived changes. I therefore combine the player's recent record with the level of comparable players. The starting rate retains 65% of his own rate and places 35% on the comparable players' level. The expected change between his most recent qualifying season and the valuation season is then added.

@eq own

@eq start

G₁ and r₁ are games and WAR per 82 in the most recent qualifying season; the subscripts 2 and 3 refer to the preceding seasons. Multiplying each recency weight by games prevents a short season from counting as much as a full season with the same recency. L is the comparable players' level at the player's most recent qualifying age, and Δ is their estimated change to his age in the valuation season.

Pacioretty's recent rates were 2.312, 3.721, and 0.035 WAR per 82 in 2015-16, 2016-17, and 2017-18, over 82, 81, and 64 games. The games-weighted average is 1.781 WAR per 82. His comparable players' level is 1.328, and their estimated change to the valuation season is −0.124. His starting rate is therefore 0.65 × 1.781 + 0.35 × 1.328 − 0.124 = 1.498 WAR per 82, using unrounded inputs in the calculation.

@table start_tests

The tests support using several seasons, accounting for games, and combining the player's record with comparable players. They do not establish that each chosen setting is uniquely best. In particular, a five-game threshold reduced error on the evaluated rows, but would also change which players receive prospect rather than player valuations. That wider change was not tested. Ten games remains a boundary between the two valuation methods.

### Selecting comparable players

Comparables are other players of the same position at the same age. Similarity is measured across four groups of attributes: the distribution of WAR across five performance components, ice time per game, performance level, and recent trend. Each group receives the same weight in the distance calculation; the five performance components share one group's weight. This does not imply that each group contributes exactly one quarter of the distance for a particular pair of players.

The attributes are standardized within position so that differences in their units do not determine similarity. Closer comparables receive greater weight, using Gaussian kernel weights. [3] For distance d and a distance scale h, the weight is exp(−d² / 2h²). A comparable one distance scale away receives weight 0.61, and one twice as far away receives 0.14. The distance scale is the median distance within position, 2.52 for forwards and 2.56 for defencemen in the 2025-26 fit. A player's own career is excluded from his comparables.

To limit the influence of a small or distant group, the league-average level for the same position and age receives weight ten alongside the comparables. Pacioretty's comparable weights sum to 131.99, so the league average supplies 10 / 141.99 = 7.0% of the combined level. The same blending rule is used for changes with age. Ten is a judgment call. In the October 5 comparison, removing this weight raised one-to-five-season rate RMSE from 1.3598 to 1.3678 WAR per 82. That supports retaining some blending; it does not establish ten as uniquely optimal.

@table comparables

### Projecting changes with age

The comparable players remain fixed throughout a projection. At each later age, their observed changes from that age to the next are averaged and blended with the corresponding league-average change. Those changes are added to the starting rate. Holding the comparables fixed keeps the projection tied to observed players rather than selecting a new group from a previously forecasted version of the player.

Departures require an additional assumption. A player who disappears from the NHL has no subsequent performance observation. Ignoring those players would estimate older-age changes only from players who remained. For an apparent departure, one replacement-level season is inserted, using the player's most recent games as its weight. Players observed returning before the valuation date are not treated as departures. This adjustment cannot identify permanent retirement with certainty at the valuation date.

@table aging_tests

Replacement level is retained as an interpretable assumption about the alternative player available to the club. It is not the error-minimizing departure value among the values tested: assigning 0.25 WAR per 82 above replacement performed better at longer horizons in that diagnostic. The comparison makes the cost of the assumption visible.

@figure aging

### Games share and the chance of playing

The performance rate must next be converted to a season contribution. Games share is estimated from the player's recent games share, recent season WAR, seasons since NHL debut, age, and age squared. Each future season has a separate regression. Predictions are restricted to the interval from zero to one. Age squared permits the association between age and games share to bend rather than imposing one constant change per year.

The chance of playing at least one game is estimated separately by logistic regression. It uses age, recent season WAR, recent games share, position, whether a signed contract covers the season, and an indicator for unavailable contract coverage. The indicator separates missing historical contract records from an observed absence of a contract. Contract status is taken at the valuation's information date.

@eq participation

In the games-share equation, G is recent games share, W is recent season WAR, E is seasons since debut, and A is age minus 27.22. The fitted value is limited to zero through one. In the probability equation, z is the intercept plus the coefficient-weighted inputs in the table. The logistic transformation puts p between zero and one. Each horizon has its own coefficients.

@table participation

In the valuation-season fit, a contract is associated with much higher odds of appearing: exp(2.088) is about 8.1. This is an association conditional on the other inputs, not evidence that signing a contract causes an eightfold increase in the probability of playing. Odds and probabilities are different quantities.

@table participation_tests

The preferred games-share specification is judged partly by the resulting season WAR, not only by its fit to games. A fractional logit improved games-share error in the October 5 test but worsened season-WAR error, from 0.8088 to 0.8108 wins. Adding age squared to the linear regression reduced season-WAR error to 0.8078 wins. Those are comparisons within that dated test, not a new evaluation of the current forecast.

A separate probability is fitted for each horizon, so absence in one season does not force absence in all subsequent seasons. Beyond the skater model's fitted range, the aggregate decline in expected WAR between the final two fitted horizons is extended. Forecasts at those distant horizons therefore rely more heavily on extrapolation.

## 3. Pricing Forecasted Performance

Forecasted wins must be converted to dollars before they can be compared with a cap hit. I estimate the price of performance from contracts signed by players beyond their entry-level contracts. The dependent variable is cap hit divided by the cap in the contract's first season. The explanatory variables are forecasted WAR conditional on playing in that season, an additional per-win coefficient for defencemen, and contract length.

@eq price

D is one for a defenceman and zero for a forward, and T is contract length in years. The forecast is dated at signing, so a contract agreed before the preceding season ended does not use that season's eventual performance. The current fitted sample contains 2,336 contracts by 1,167 players, starting from 2018-19 through 2025-26.

Of those contracts, 521 are at the league minimum. Those observations reveal that the negotiated price could have been at or below the minimum, rather than identifying an unrestricted market price. The regression accounts for that floor through a censored normal likelihood, commonly called a Tobit model. [2]

@table price

At the 2025-26 cap, the fitted price before the minimum floor is −$0.412 million, plus $1.672 million per forecasted win for a forward, plus $0.389 million per win for a defenceman, plus $0.851 million per year of term. A forward forecast at one win on a one-year contract has a point price of $2.112 million.

### Why the first season and contract length enter

A longer contract commits both parties beyond the first season. It is therefore reasonable to ask whether its average forecasted performance prices the contract better than the first season's forecast. Both the conditional average and an average weighted by the chance of playing were tested on the same contracts.

@table term_average

The first-season forecast predicts cap hits more accurately in these comparisons. The contract-length term is also useful: without it, average one-year cap hits are overpredicted by $0.78 million, while eight-year cap hits are underpredicted by $2.87 million. Adding term reduces those differences to approximately +$0.09 million and +$0.19 million. The term coefficient describes the price association with longer commitments; the regression alone does not prove that security is its cause.

In a valuation, the remaining term at the valuation date is used for each remaining contract season. For Tatar, three seasons remain, so each is priced with three years of term. A terminal season or a historical drafted-player season is priced with one year. A complete valuation without the term coefficient is retained as a sensitivity because this convention materially affects dollar values.

@table price_alternatives

The flat term coefficient is a simplification. An earlier comparison found a small predictive gain from a higher coefficient below replacement-level performance. It also found that a separate restricted-free-agent specification improved prediction slightly. These alternatives were not adopted. A nonsignificant test for a later-period price line is insufficient to establish that market prices are stable across periods.

### The minimum floor and forecast uncertainty

For contract seasons, the price is the expected value of the higher of the uncertain market price and the league minimum. This differs from applying the floor only to the point forecast. If some possible outcomes fall below the minimum, those prices are raised to the minimum while higher outcomes remain unchanged.

The spread is estimated from the forecast's mean absolute errors conditional on playing, converted to a normal standard deviation. The current errors range from 0.6766 WAR in the valuation season to 0.8975 five seasons ahead. Beyond five seasons, the latter error is held constant. Pacioretty's point price of $2.103 million increases by $0.062 million to $2.165 million after this adjustment.

Terminal seasons and delivered historical seasons use a simple maximum of their point price and the minimum. They do not receive this contract-season uncertainty adjustment. That distinction is part of the current implementation.

## 4. From Seasons to Contract Value

A signed contract creates a cap cost even in seasons when the player does not appear. The expected performance value is therefore multiplied by the probability of playing, while the contractual cap cost is subtracted in full. For a contract valued today:

@eq contract

The first sum covers signed contract seasons. Terminal value covers additional seasons of restricted-free-agent control after the signed contract ends. For a trade during the regular season, the current season's value and cost are both multiplied by the share of scheduled regular-season days remaining.

### The two contracts in the example

Pacioretty had one season remaining at a $4.50 million cap hit. Montreal retained $0.45 million, leaving Vegas a $4.05 million charge. His probability of playing is 0.9664, so his expected performance value is 0.9664 × $2.165 million = $2.092 million. Subtracting Vegas's cost gives −$1.958 million at the 2018-19 cap.

Tatar had three seasons remaining at $5.30 million. Vegas retained $0.50 million per season, leaving Montreal $4.80 million. His forecasted performance price is below that cost in each remaining season.

@table contracts

Neither player has terminal value in this example. Pacioretty's extension signed on the trade date is excluded under the study's information convention: same-day agreements are treated as occurring after the asset exchange. This is a consistent dating rule where intraday ordering is not observed. It should not be read as proof that negotiations or an agreement were unknown to the clubs.

### Terminal value

Restricted-free-agent rights give a club an opportunity to retain a player after his current contract. Those additional seasons can have surplus, but only if the club retains him and he plays. Terminal value is calculated season by season:

@eq terminal

j counts the terminal season's distance from the valuation season. Vⱼ is the simple-floored price of forecasted performance at one year of term. Cⱼ is the modeled cost of retaining the player. Wⱼ is the cumulative probability weight for retaining him and receiving performance through that season.

The cost starts with the qualifying offer computed from the preceding salary. Once arbitration applies, cost is the higher of that offer and the one-year market price of the arbitration forecast. That forecast is rebuilt using the preceding seasons; future observations are replaced by forecasts where necessary. Each subsequent qualifying offer uses the cost assigned to the preceding season.

For existing contracts, arbitration timing generally follows PuckPedia's flag at expiry: eligibility begins in the first terminal season when flagged eligible and in the second when flagged ineligible. A professional-season-count proxy is used where the flag is unavailable. Because an expiry flag can be recorded after an earlier valuation date, this input is a source of hindsight.

@table control

The cumulative weight begins with the probability of playing in the contract's final season, then multiplies the annual retention-and-playing weight for each terminal season. For example, a final-season playing probability of 0.90 followed by two annual weights of 0.687 gives weights of about 0.618 and 0.425. These are illustrative weights, not a new player valuation.

Terminal value stops at the first season with negative modeled surplus. This represents a club declining to retain an unprofitable player. It prevents a cost for an optional future season from being treated as an unavoidable contractual liability. It also rules out retaining a player through an unprofitable season to obtain a later profitable one.

Long-term injured reserve receives a separate treatment in traded-player valuations. For a player already identified as on LTIR at the trade, expected cap cost is relieved in proportion to the chance of not playing. Full relief in the model's cap currency is an assumption; it is not a complete simulation of a club's actual cap-management decisions.

### Goaltenders

Goaltender performance is forecast separately. Consecutive-season WAR has a correlation of 0.209 among goaltenders and 0.586 among skaters in the recorded comparison. This establishes weaker persistence for goaltenders in that sample. It does not, by itself, establish a larger variance of their year-to-year changes.

The goaltender forecast retains 35% of recent season WAR and combines it with 65% of the league average, approximately 2.19 WAR. A fitted linear age adjustment is then applied. The recent record uses 50/30/20 weights where all three seasons are available. A separate logistic regression estimates the chance of appearing, using age, the forecast before the age adjustment, and the most recent games share.

@table goalies

The goaltender price line is fitted on the forecast before its age adjustment, but future seasons are valued using the age-adjusted forecast. The current coefficients, at the 2025-26 cap, are −$3.028 million plus $2.042 million per win plus $0.775 million per year of term, before the floor. This fit uses 333 contracts. The different forecast used for estimation and valuation is a modeling choice supported by the cap-hit prediction comparison; it does not establish that clubs ignore aging.

## 5. Valuing Draft Picks

A draft pick has no player-specific NHL record. Its value is estimated from what earlier selections delivered during club control. Historical careers are first converted to surplus, and that surplus is then related to draft position. This order preserves the effects of the minimum price, cost rules, and uneven outcomes before averaging across players.

### Measuring the surplus of a drafted player

The fit includes 2,316 selections from the 2007 through 2017 drafts after exclusions. Performance is observed through 2025-26 in the saved dataset. Each played season is priced using delivered season WAR, with shortened league seasons normalized to 82 scheduled games. This normalization is different from dividing a player's WAR by his own games and multiplying by 82.

The control window ends at the earlier of age-based unrestricted free agency or seven accrued seasons. The age cutoff is 27 by June 30. The code approximates accrued seasons using at least 40 NHL games for skaters and 30 for goaltenders, adjusted for shortened seasons. Games played substitute for roster time, so the window is an approximation rather than a complete reconstruction of contractual eligibility.

Costs begin at the entry-level maximum for the draft class. Entry-level duration is assigned using signing age, with the first NHL season substituted where the signing year is unavailable. The contract then advances by calendar year from the first NHL season; entry-level slides are not modeled. Subsequent seasons use qualifying offers and, once eligible under the NHL-games proxy for professional experience, the higher arbitration-based cost.

A season with no NHL games contributes zero value and zero cost. Seasons under ten games receive an additional games-over-82 scaling of both price and cost. Rights that lapsed without the drafting club first signing or trading the player contribute zero. Negative career surplus is retained. Six draftees who died before reaching the NHL are excluded from the fits.

Historical value and cost are converted to a common cap using the actual cap in each season. Writing the conversion as a discount makes its connection to the forward calculation explicit:

@eq historical

Vₛ and Cₛ are historical dollars, capₛ is that season's cap, and cap* is $95.5 million. The denominator is the cumulative change in the cap relative to the reference cap. The code sums the resulting cap shares and multiplies by cap*. It does not apply an additional 3% annual discount after this conversion. For future projections, 3% cap growth and 3% discounting give the analogous cancellation.

@table sissons

Sissons illustrates why an NHL career and a valuable draft pick are different outcomes. His seven observed seasons inside the modeled control window produce $9.84 million of performance value and $9.09 million of cost, for $0.743 million of surplus. Seasons with no NHL appearance contribute zero and are omitted from the table. The modeled control window ends before 2021-22.

### Relating surplus to draft position

Draft outcomes are concentrated: the highest-surplus 5% of selections account for about 80% of total surplus in this sample. The average at one exact draft position is therefore sensitive to a few careers. I use Bacon's star probability by draft position as the explanatory variable in a regression of career surplus, with no intercept:

@eq pick

S is star probability and θ is the fitted coefficient, called star value. The estimate is $18.289 million, with a heteroskedasticity-robust standard error of $1.74 million. Star value is the fitted surplus at S = 1. It is an extrapolation of a regression across draft positions, not an estimate of the average surplus conditional on a player actually becoming a star. Regular NHL players' surplus also contributes to the fitted coefficient.

@table pick_tests

The star-probability specification has the lowest held-out root mean squared error among these shapes. The advantage over the logarithm and its square is small; the latter also turns upward at late draft positions. An intercept does not improve held-out error: $3.659 million against $3.658 million without it. Its estimated $0.097 million intercept has p = 0.314. The no-intercept restriction keeps predicted value proportional to star probability, including at late positions where a small fixed addition would be substantial.

@figure picks

One coefficient is used across draft years. Removing the 2015 and 2016 drafts reduces star value to $15.99 million, about 13% below the main fit. This sensitivity matters because a few exceptional drafts can change the valuation of every pick. It is not proof that the remaining drafts form an unbiased historical expectation.

### Assigning a position before the draft

A pick traded during its own draft receives its known position. For the coming draft after the regular season has begun, position is approximated from the original team's standings at the trade date. Before that season begins, or for a later draft, the average star probability across the round is used. Lottery outcomes and playoff reordering are not forecast, and conditional picks are treated as unconditional while flagged.

The second-round pick in the Pacioretty trade falls in the round-average category. Its average star probability is 0.052838, giving 0.052838 × $18.2886 million = $0.966 million. Its eventual position, 50th overall, is not used at the trade date. The value of a known 50th pick is $0.877 million, which explains why that value differs from the traded pick's value.

The cost rule remains an important limitation. In the saved comparison of first-round skaters who reached the NHL for their drafting club, modeled costs are only about 51% to 64% of observed cap costs across the reported draft-position groups. Understated costs would overstate the value of picks relative to existing contracts. Neither the choice of regression shape nor a precise star-value estimate resolves that problem.

## 6. Valuing Prospects

A prospect has a draft position and a developing record, but insufficient recent NHL experience for the player forecast. Skaters remain in the prospect category when none of their three preceding seasons contains ten NHL games. The goalie boundary uses an NHL appearance within the preceding six seasons. Prospect value is the surplus still to come before club control ends.

Seasons are named relative to the draft. D0 is the season ending with the draft, D+1 is the following season, and D+2 is the next. A prospect in D+2 has been selected, but his value may differ from his original pick because a year has passed and more performance is observed.

### Draft position after time has passed

The first comparison relates remaining surplus to draft-position star probability separately for each season since the draft. D+1 through D+4 each receive a coefficient, and D+5 through D+8 share one coefficient. The regression uses a full set of season interactions, with standard errors clustered by player because a career can contribute several prospect-seasons.

@table prospect_fade

These are values conditional on still being a prospect. They are not depreciation rates for the same unchanged group of players. Many successful early selections have already entered the NHL by D+3. Those still outside it in later seasons are a different group, and draft position distinguishes their remaining outcomes less well.

The separate-season specification has held-out root mean squared error of $2.6242 million per prospect-season, compared with $2.6440 million for one common coefficient, $2.6246 million for a straight-line decline, and $2.6268 million for a constant percentage decline. The common coefficient performs worse (reported one-sided p < 0.001). The two declining alternatives are not distinguishable at the 5% level in the reported comparisons. Separate coefficients are retained to avoid imposing a shape, rather than because prediction decisively favors them.

### Adding scoring and age

Scoring provides information beyond draft position. Each season's points per game are multiplied by its league-season NHL equivalency factor and by 82. This yields NHLe points per 82 games. Production P is the 50/30/20 average across the three preceding seasons with at least ten games, rescaled over available seasons. At D+1 those are D0, D−1, and D−2. No counted scoring record is represented by P = 0.

Adding production gives the specification aS + bP + cP². Draft position is included only through D+3; from D+4 it is omitted. The squared term allows additional scoring to have a different value for an already high scorer. Age is then included through an interaction with production: equally productive prospects are compared at the same time since the draft, but at different ages.

@eq prospect

A is age in years on September 15 of the valuation season. Coefficients differ by season group. The age interaction is present through D+4; from D+5 onward only linear and squared production remain. In code, the age measure subtracts seasons since the draft as well as 18. The coefficients shown here are transformed to age minus 18, with exactly the same fitted values. This distinction matters when interpreting an individual coefficient's significance.

@table prospect_tests

These comparisons show modest improvements relative to the large uncertainty of individual prospect outcomes. Root mean squared error declines from $2.2615 million on draft position alone to $2.1995 million with the adopted production and age terms. Those errors are measured across prospect-seasons, not as confidence intervals for a particular prospect's value.

@table prospect_coefficients

For D+2, each additional year of age reduces value by $0.0621 million per NHLe point, holding production and draft position fixed. At ten NHLe points, the difference between otherwise equal prospects one year apart is about $0.621 million. The squared term means that the marginal value of another point also depends on existing production.

The linear production term is retained even though its coefficient in this parameterization is not individually significant at the 5% level. With a production-by-age interaction, that coefficient describes the linear production effect at the chosen reference age. Changing the reference age changes its coefficient and p-value without changing predictions. Removing it would impose a different substantive restriction at each chosen reference age. This is a reason to assess the specification jointly rather than remove the term solely from one displayed p-value.

From D+5 onward, the two production terms are also jointly nonsignificant at the 5% level (p = 0.085). Removing both raises held-out error from $0.7567 million to $0.7621 million per late prospect-season, a difference that is not statistically significant in the reported comparison (one-sided p = 0.27). The retained values for late prospects therefore rest on weak evidence. Keeping them avoids forcing all such players to zero; that is a modeling judgment, not a significant test result.

### Suzuki at the trade date

Suzuki was a D+2 prospect with a star probability of 0.169956 from his 13th draft position. His production was 15.3659 NHLe points per 82, and his age was 19.0992. Applying the D+2 coefficients gives:

@table suzuki

His $4.242 million valuation exceeds the $3.087 million from the draft-position-only specification. The difference is not simply the production terms added to $3.087 million: adding production and age also changes the fitted coefficient on draft position. In the full specification, the draft-position contribution is $1.776 million.

@figure prospect

Goalie prospects remain on draft position alone because NHLe scoring does not measure goaltending. Undrafted skaters on NHL contracts receive the production-based valuation with star probability set to zero and time measured from first draft eligibility. Applying a model estimated on drafted players to this selected group of undrafted signees is an extrapolation. Missing scoring data and the weak late-season fit are especially consequential for these players.

## 7. Adding the Trade and Interpreting the Result

The player values are restated from the 2018-19 cap to the 2025-26 cap by multiplying by 95.5 / 79.5. Suzuki and the pick are already expressed at the latter cap. Retained salary is charged to the retaining club, and the acquiring club pays only the unretained part.

@table trade

Montreal receives Tatar, Suzuki, and the pick, and remains responsible for $0.541 million of Pacioretty's cap cost in common-cap dollars. Its received value after that liability is −$0.205 million. Montreal gives up Pacioretty at his pre-trade value of −$2.892 million, when it carried his full cap hit. The difference is +$2.687 million. Vegas's net is −$2.687 million, so the trade reconciles to zero across the clubs.

Negative contract surplus explains the result. Montreal takes on a larger contract deficit through Tatar than it gives up through Pacioretty, but Suzuki and the pick more than offset that difference. This is an estimate based on the model's forecasts and valuation rules. It is not a measure of how the players subsequently performed, nor does it include team-specific needs or playoff utility.

### What the evidence establishes

The forecast is checked against Game Value, a separately constructed performance measure using NHL expected goals and penalties, with an adjusted version that accounts for five-on-five teammates and opponents. It does not use Bacon's WAR as an input. In the saved October 5 comparison of 6,027 player-seasons by 1,319 players, conditional forecast WAR correlates 0.624 with adjusted Game Value, against 0.588 for trailing WAR. The analogous comparison one season further ahead is 0.602 against 0.552.

This is supporting evidence that the forecast contains information about subsequent performance. It does not eliminate shared measurement error, because both measures describe the same underlying NHL games. Nor does it validate the dollar price line or the cost assigned to prospects.

The historical values are not fully restricted to information available to clubs at each trade. Player forecasts use earlier completed seasons, but price coefficients use contracts through 2025-26. Pick and prospect fits use later career outcomes from the 2007-2017 drafts, and some valued prospects are themselves in those fits. Qualifying rates, expiry flags, and the downloaded NHLe factors also contain later information. Leaving a prospect's own draft out is reported as a sensitivity; for Suzuki it reduces value from $4.242 million to $4.023 million. It does not remove all later information.

The framework therefore provides a common surplus benchmark under explicit assumptions. Claims about historical market mispricing must also account for the use of later information, understated control costs, uncertainty in prospect outcomes, and the simplifications for conditional picks and LTIR. These limitations affect the interpretation of the trade result even when the arithmetic reconciles exactly.

## References and Implementation Sources

[1] Patrick Bacon, “NHL WAR (Wins Above Replacement) Explained,” HockeyStats.com, https://hockeystats.com/methodology/war. The provider's team-level validation is descriptive and does not independently validate individual player attribution.

[2] James Tobin (1958), “Estimation of Relationships for Limited Dependent Variables,” Econometrica, 26(1), 24–36. The implementation uses a league-minimum-censored normal likelihood.

[3] E. A. Nadaraya (1964), “On Estimating Regression,” Theory of Probability and Its Applications, 9(1), 141–142; G. S. Watson (1964), “Smooth Regression Analysis,” Sankhyā, Series A, 26(4), 359–372. These are references for kernel regression; they do not validate the particular hockey attributes or distance scale chosen here.

Implementation sources are in 20_CODE. Current versions include skater_forecast.py v2.4, contract_npv.py v3.4, pick_curve.py v1.11, and prospect_values.py v1.12. Table notes identify the supporting outputs and dated tests.
