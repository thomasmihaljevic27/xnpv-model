# The findings document's regressions in Stata

Build the CSV first, from the repo root, after the back-test and the findings scripts (about 2 minutes):

```
python 20_CODE/stata_export_findings.py
```

Then in Stata, work from the folder the CSV is in:

```
cd "C:\Users\thoma\Desktop\xNPV\30_OUTPUT\stata"
```

One CSV holds everything: one row for each club in each complete trade, July 2017 to March 2026. Each section picks
its rows with a yes/no column (`in_2017_22`, `in_main_regression`, `in_price_regression`, `one_row_per_trade`). Above each block: what it does and its
equation. Each block is only Stata commands, one per line, so it can be pasted straight into the Command window.
`30_OUTPUT/stata/findings_walkthrough.do` has the same commands, with the figure each one should print.

The same option words recur:

| In the command | What it means |
|---|---|
| `noconstant` | No constant (intercept): one club's gain is the other's loss, so a trade with no difference between the clubs predicts zero |
| `vce(robust)` | Robust standard errors: the size of the misses may differ from trade to trade |
| `vce(cluster trade_id)` | Clustered standard errors: the two clubs in a trade are mirror images, so the trade counts once |
| `if ...` | Use only the rows where the condition holds |
| `mean ..., vce(cluster trade_id)` | The average of each variable over the rows, with clustered standard errors |
| `ivregress 2sls y w (x = z)` | Two-stage least squares: x is first predicted from z and w, then y is regressed on that prediction and w |
| Equation | The regression written out: a, b, c ... are the coefficients Stata estimates; e is the error; sum over k means one coefficient for each variable in the list |

Stata's p-values for clustered errors use the t distribution on (trades - 1) degrees of freedom; the document's use the
normal distribution, so a third decimal can differ.

---

## Findings

### Load

```stata
import delimited using "findings_data.csv", clear
```

| Variable | What it is |
|---|---|
| `trade_id`, `club`, `trade_date` | The trade, the club, the date |
| `tradeday_grade` | Trade-day grade: what the club received less what it gave up, at the models' values (xNPV), $M at the 2025-26 cap |
| `realized_war` | Realized value on WAR: what the assets delivered less what was given up, $M |
| `realized_gamevalue` | Realized value on Game Value, $M |
| `realized_war_played_only` | Realized value on WAR, the seasons played through 2025-26 only, $M |
| `in_2017_22` | 1 for a trade from July 1, 2017 to March 28, 2022 (Sections 2 and 3) |
| `favoured_by_grade` | 1 for the club the trade-day grade favoured in its trade |
| `came_out_ahead_war`, `came_out_ahead_gamevalue` | 1 when the club's realized value is above zero (WAR, Game Value) |
| `in_main_regression` | 1 for both clubs of the 556 two-team trades in Section 3's regression |
| `main_` + characteristic | Main player rule (the player with the highest cap hit received): the club's side less the other club's side, what it received less what it sent away. +1, 0 or -1 for a yes/no characteristic; the difference for a measure. Blank outside `in_main_regression` |
| `any_` + characteristic | The same under the any player rule (any player received) |
| `..._sold_for_just_picks` | Sold a player for just picks and prospects |
| `..._deadline_buyer` | Team higher in the standings, last 14 days before the deadline |
| `..._buyer_earlier_in_season` | Team higher in the standings, earlier in the season |
| `..._got_rental` | Received a rental (final contract season, unrestricted, in season) |
| `..._retained_salary` | Retained salary on the player sent |
| `..._got_one_for_two_or_more` | Received one asset for two or more |
| `..._took_cap_dump` | Took on a contract to clear cap |
| `..._new_gm_sold_old_contract` | A new general manager selling a contract signed by his predecessor |
| `..._got_final_year_rfa` | Received a restricted free agent in his final contract season |
| `..._got_only_late_picks` | Received only picks in rounds 6 and 7 |
| `..._age_28_31`, `..._age_32_plus` | Received a player aged 28 to 31, aged 32 or over (each against 27 or under) |
| `..._defenceman`, `..._goalie` | Received a defenceman, a goalie (each against a forward) |
| `..._clause` | Received a player with a no-trade or no-move clause |
| `..._signed_as_ufa` | Received a player signed as an unrestricted free agent |
| `..._two_seasons_left`, `..._three_plus_seasons_left` | Received a player with two, three or more seasons left on his contract (each against one) |
| `..._former_top15_pick` | Received a former top-15 draft pick |
| `..._recent_war` | Recent production: WAR weighted 50/30/20 over the three most recent seasons |
| `..._war_above_forecast` | That production less the models' forecast for the season of the trade, WAR |
| `..._games_played_share` | Share of games played in the most recent season |
| `..._got_a_player` | Received a player at all |
| `main_cap_hit`, `main_career_war`, `main_best_season_war` | The main player's cap hit ($M), career WAR and best single-season WAR, the club's side less the other's |
| `trade_had_cap_dump` | 1 when either club in the trade took on a contract to clear cap |
| `own_main_player_has_clause`, `own_any_player_has_clause` | 1 for a club that received a player with a clause: its main player, any player (the club's own yes/no, not a difference) |
| `own_sold_for_just_picks` | 1 for a club that sold a player for just picks and prospects (its own yes/no) |
| `in_price_regression` | 1 for the 886 clubs, all trades, whose main player has a model value and a cap cost (Section 4) |
| `price_paid_main_player` | The price the club paid for its main player: everything it gave up less everything else it received, $M |
| `performance_value` | The models' value of the main player's forecasted performance over the rest of his contract (control seasons included), $M |
| `cap_hit_cost` | The present value of his cap hit over the seasons left, $M |
| `performance_delivered` | What his performance delivered, the seasons played through 2025-26 only, $M |
| `one_row_per_trade` | 1 for the first club (alphabetically) of a two-team trade, so each trade appears once |
| `grp_` + group | On that row: the first club's group less the second's (+1, 0 or -1), for Section 4's sellers regression; `grp_cap_hit` the main players' cap hits, $M; `grp_top15_below_average` a former top-15 pick below the top-15 average |

### 1. The models predict how trades turn out

Each club's realized value on its trade-day grade, no constant, the declared window: a slope of 1 means the gap
predicted on trade day all shows up. Then the same on Game Value, and the share of trades the favoured club came out of
ahead (0.5 would be a coin flip).

Equation: `realized_war = b*tradeday_grade + e`

```stata
regress realized_war tradeday_grade if in_2017_22 == 1, noconstant
regress realized_gamevalue tradeday_grade if in_2017_22 == 1, noconstant
mean came_out_ahead_war came_out_ahead_gamevalue if in_2017_22 == 1 & favoured_by_grade == 1
```

### 2. The one regression, both rules

Each trade twice, once for each club: the club's value on what it received less what it sent away in each of the 23
variables, no constant, standard errors clustered by trade. A finding is a variable statistically significant at the 5%
level on both `tradeday_grade` and `realized_war`, with the same sign; `realized_gamevalue` and `realized_war_played_only` are the checks.

Equation: `tradeday_grade = sum over k of b_k * main_k + e` (the same for each outcome; `any_k` under the any player rule)

Main player rule:

```stata
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_gamevalue main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_war_played_only main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
```

Any player rule:

```stata
regress tradeday_grade any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_war any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_gamevalue any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_war_played_only any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1, noconstant vce(cluster trade_id)
```

### 3. Is the clause a stand-in for something else?

The main player rule's regression with the main player's cap hit added; then with his reputation (career WAR, best
season) added; then without the trades in which a club took on a contract to clear cap (the cap-dump column is all zero
there, so it is left out). Read `main_clause` in each.

Equation: `tradeday_grade = sum over k of b_k * main_k + c*main_cap_hit + e`

```stata
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_cap_hit if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_cap_hit if in_main_regression == 1, noconstant vce(cluster trade_id)
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_career_war main_best_season_war if in_main_regression == 1, noconstant vce(cluster trade_id)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_career_war main_best_season_war if in_main_regression == 1, noconstant vce(cluster trade_id)
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & trade_had_cap_dump == 0, noconstant vce(cluster trade_id)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & trade_had_cap_dump == 0, noconstant vce(cluster trade_id)
```

### 4. The averages on their own (Step 4)

The average trade-day grade and realized value of the clubs in a group, the declared window, standard errors clustered
by trade: clubs that received a player with a clause (main player, then any player), and clubs that sold a player for
just picks and prospects. A mean below zero: the group came out behind.

Equation: `tradeday_grade = a + e` over the group's clubs (a is the group's average)

```stata
mean tradeday_grade realized_war if in_2017_22 == 1 & own_main_player_has_clause == 1, vce(cluster trade_id)
mean tradeday_grade realized_war if in_2017_22 == 1 & own_any_player_has_clause == 1, vce(cluster trade_id)
mean tradeday_grade realized_war if in_2017_22 == 1 & own_sold_for_just_picks == 1, vce(cluster trade_id)
```

### 5. The sellers with the cap hit held fixed

One row a trade (the first club's), the declared window: the first club's value on its groups less the second club's,
with the main players' cap hits added, robust standard errors. Read `grp_sold_for_just_picks`: with the cap hit of the player sold
held fixed, does selling for just picks and prospects still gain?

Equation: `tradeday_grade = sum over k of b_k * grp_k + c*grp_cap_hit + e`

```stata
regress tradeday_grade grp_sold_for_just_picks grp_deadline_buyer grp_buyer_earlier_in_season grp_got_rental grp_retained_salary grp_age_28_31 grp_age_32_plus grp_defenceman grp_clause grp_top15_below_average grp_got_one_for_two_or_more grp_took_cap_dump grp_new_gm_sold_old_contract grp_cap_hit if one_row_per_trade == 1 & in_2017_22 == 1, noconstant vce(robust)
regress realized_war grp_sold_for_just_picks grp_deadline_buyer grp_buyer_earlier_in_season grp_got_rental grp_retained_salary grp_age_28_31 grp_age_32_plus grp_defenceman grp_clause grp_top15_below_average grp_got_one_for_two_or_more grp_took_cap_dump grp_new_gm_sold_old_contract grp_cap_hit if one_row_per_trade == 1 & in_2017_22 == 1, noconstant vce(robust)
regress realized_gamevalue grp_sold_for_just_picks grp_deadline_buyer grp_buyer_earlier_in_season grp_got_rental grp_retained_salary grp_age_28_31 grp_age_32_plus grp_defenceman grp_clause grp_top15_below_average grp_got_one_for_two_or_more grp_took_cap_dump grp_new_gm_sold_old_contract grp_cap_hit if one_row_per_trade == 1 & in_2017_22 == 1, noconstant vce(robust)
```

### 6. How the price follows a contract's two parts

All trades to March 2026, the main player rule: the price paid for the main player on the value of his forecasted
performance and on his cap cost, with a constant, standard errors clustered by trade. A price that followed the contract
in full would give +1 on the performance value and -1 on the cost. Then the same on what his performance delivered in the
seasons played. Then two-stage least squares: the models' performance value predicted first from what the seasons played
delivered (the first stage), so the part of the models' value that is error drops out. The document's two-stage
standard errors (0.19, 0.16) come from 2,000 resamples of trades; Stata's clustered ones differ.

Equation: `price_paid_main_player = a + b*performance_value + c*cap_hit_cost + e` (b = 1 and c = -1: the price follows the contract in full)

```stata
regress price_paid_main_player performance_value cap_hit_cost if in_price_regression == 1, vce(cluster trade_id)
regress price_paid_main_player performance_delivered cap_hit_cost if in_price_regression == 1, vce(cluster trade_id)
ivregress 2sls price_paid_main_player cap_hit_cost (performance_value = performance_delivered) if in_price_regression == 1, vce(cluster trade_id)
regress performance_value performance_delivered cap_hit_cost if in_price_regression == 1
```
