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
its rows with a yes/no column (`declared`, `in_reg`, `in_price`, `first_club`). Above each block: what it does and its
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
| `grade` | Trade-day grade: what the club received less what it gave up, at the models' values (xNPV), $M at the 2025-26 cap |
| `real_war` | Realized value on WAR: what the assets delivered less what was given up, $M |
| `real_gv` | Realized value on Game Value, $M |
| `real_played` | Realized value on WAR, the seasons played through 2025-26 only, $M |
| `declared` | 1 for a trade from July 1, 2017 to March 28, 2022 |
| `favoured` | 1 for the club the trade-day grade favoured in its trade |
| `ahead_war`, `ahead_gv` | 1 when the club's realized value is above zero (WAR, Game Value) |
| `in_reg` | 1 for both clubs of the 556 two-team trades in Section 3's regression |
| `m_` + characteristic | Main player rule: the club's side less the other club's side (what it received less what it sent away): +1, 0 or -1 for a yes/no characteristic; the difference in WAR or games share for a measure. Blank outside `in_reg` |
| `a_` + characteristic | The same under the any player rule |
| `..._sold_picks` | Sold a player for just picks and prospects |
| `..._deadline_buyer` | Team higher in the standings, last 14 days before the deadline |
| `..._earlier_buyer` | Team higher in the standings, earlier in the season |
| `..._rental` | Received a rental (final contract season, unrestricted, in season) |
| `..._retained` | Retained salary on the player sent |
| `..._one_for_many` | Received one asset for two or more |
| `..._took_dump` | Took on a contract to clear cap |
| `..._new_gm` | Sold under a new general manager, his predecessor's contract |
| `..._rfa_final` | Received a restricted free agent in his final contract season |
| `..._late_picks` | Received only picks in rounds 6 and 7 |
| `..._age28_31`, `..._age32_plus` | Received a player aged 28 to 31, aged 32 or over (each against 27 or under) |
| `..._defence`, `..._goalie` | Received a defenceman, a goalie (each against a forward) |
| `..._clause` | Received a player with a no-trade or no-move clause |
| `..._ufa_signed` | Received a player signed as an unrestricted free agent |
| `..._left2`, `..._left3_plus` | Received a player with two, three or more seasons left (each against one) |
| `..._top15` | Received a former top-15 draft pick |
| `..._production` | Recent production: WAR weighted 50/30/20 over the three most recent seasons |
| `..._above_fcst` | That production less the models' forecast for the season of the trade, WAR |
| `..._games_share` | Share of games played in the most recent season |
| `..._got_player` | Received a player at all |
| `cd_cap`, `cd_career`, `cd_best` | Main player rule: the main player's cap hit ($M), career WAR and best single-season WAR, club's side less the other's |
| `dump_trade` | 1 when either club in the trade took on a contract to clear cap |
| `own_clause_main`, `own_clause_any` | 1 for a club that received a player with a clause: its main player, any player |
| `own_seller` | 1 for a club that sold a player for just picks and prospects |
| `in_price` | 1 for the 886 clubs, all trades, whose main player has a model value and a cap cost |
| `price` | The price the club paid for its main player: everything it gave up less everything else it received, $M |
| `perf_value` | The models' value of the main player's forecasted performance over the rest of his contract (control seasons included), $M |
| `cap_cost` | The present value of his cap hit over the seasons left, $M |
| `perf_played` | What his performance delivered, the seasons played through 2025-26 only, $M |
| `first_club` | 1 for the first club (alphabetically) of a two-team trade: one row a trade |
| `j_` + group | On the first club's row: the first club's group less the second's (+1, 0 or -1); `j_cap` the main players' cap hits, $M |

### 1. The models predict how trades turn out

Each club's realized value on its trade-day grade, no constant, the declared window: a slope of 1 means the gap
predicted on trade day all shows up. Then the same on Game Value, and the share of trades the favoured club came out of
ahead (0.5 would be a coin flip).

Equation: `real_war = b*grade + e`

```stata
regress real_war grade if declared == 1, noconstant
regress real_gv grade if declared == 1, noconstant
mean ahead_war ahead_gv if declared == 1 & favoured == 1
```

### 2. The one regression, both rules

Each trade twice, once for each club: the club's value on what it received less what it sent away in each of the 23
variables, no constant, standard errors clustered by trade. A finding is a variable statistically significant at the 5%
level on both `grade` and `real_war`, with the same sign; `real_gv` and `real_played` are the checks.

Equation: `grade = sum over k of b_k * m_k + e` (the same for each outcome; `a_k` under the any player rule)

Main player rule:

```stata
regress grade m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player if in_reg == 1, noconstant vce(cluster trade_id)
regress real_war m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player if in_reg == 1, noconstant vce(cluster trade_id)
regress real_gv m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player if in_reg == 1, noconstant vce(cluster trade_id)
regress real_played m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player if in_reg == 1, noconstant vce(cluster trade_id)
```

Any player rule:

```stata
regress grade a_sold_picks a_deadline_buyer a_earlier_buyer a_rental a_retained a_one_for_many a_took_dump a_new_gm a_rfa_final a_late_picks a_age28_31 a_age32_plus a_defence a_clause a_ufa_signed a_left2 a_left3_plus a_top15 a_production a_above_fcst a_games_share a_goalie a_got_player if in_reg == 1, noconstant vce(cluster trade_id)
regress real_war a_sold_picks a_deadline_buyer a_earlier_buyer a_rental a_retained a_one_for_many a_took_dump a_new_gm a_rfa_final a_late_picks a_age28_31 a_age32_plus a_defence a_clause a_ufa_signed a_left2 a_left3_plus a_top15 a_production a_above_fcst a_games_share a_goalie a_got_player if in_reg == 1, noconstant vce(cluster trade_id)
regress real_gv a_sold_picks a_deadline_buyer a_earlier_buyer a_rental a_retained a_one_for_many a_took_dump a_new_gm a_rfa_final a_late_picks a_age28_31 a_age32_plus a_defence a_clause a_ufa_signed a_left2 a_left3_plus a_top15 a_production a_above_fcst a_games_share a_goalie a_got_player if in_reg == 1, noconstant vce(cluster trade_id)
regress real_played a_sold_picks a_deadline_buyer a_earlier_buyer a_rental a_retained a_one_for_many a_took_dump a_new_gm a_rfa_final a_late_picks a_age28_31 a_age32_plus a_defence a_clause a_ufa_signed a_left2 a_left3_plus a_top15 a_production a_above_fcst a_games_share a_goalie a_got_player if in_reg == 1, noconstant vce(cluster trade_id)
```

### 3. Is the clause a stand-in for something else?

The main player rule's regression with the main player's cap hit added; then with his reputation (career WAR, best
season) added; then without the trades in which a club took on a contract to clear cap (the cap-dump column is all zero
there, so it is left out). Read `m_clause` in each.

Equation: `grade = sum over k of b_k * m_k + c*cd_cap + e`

```stata
regress grade m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player cd_cap if in_reg == 1, noconstant vce(cluster trade_id)
regress real_war m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player cd_cap if in_reg == 1, noconstant vce(cluster trade_id)
regress grade m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player cd_career cd_best if in_reg == 1, noconstant vce(cluster trade_id)
regress real_war m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_took_dump m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player cd_career cd_best if in_reg == 1, noconstant vce(cluster trade_id)
regress grade m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player if in_reg == 1 & dump_trade == 0, noconstant vce(cluster trade_id)
regress real_war m_sold_picks m_deadline_buyer m_earlier_buyer m_rental m_retained m_one_for_many m_new_gm m_rfa_final m_late_picks m_age28_31 m_age32_plus m_defence m_clause m_ufa_signed m_left2 m_left3_plus m_top15 m_production m_above_fcst m_games_share m_goalie m_got_player if in_reg == 1 & dump_trade == 0, noconstant vce(cluster trade_id)
```

### 4. The averages on their own (Step 4)

The average trade-day grade and realized value of the clubs in a group, the declared window, standard errors clustered
by trade: clubs that received a player with a clause (main player, then any player), and clubs that sold a player for
just picks and prospects. A mean below zero: the group came out behind.

Equation: `grade = a + e` over the group's clubs (a is the group's average)

```stata
mean grade real_war if declared == 1 & own_clause_main == 1, vce(cluster trade_id)
mean grade real_war if declared == 1 & own_clause_any == 1, vce(cluster trade_id)
mean grade real_war if declared == 1 & own_seller == 1, vce(cluster trade_id)
```

### 5. The sellers with the cap hit held fixed

One row a trade (the first club's), the declared window: the first club's value on its groups less the second club's,
with the main players' cap hits added, robust standard errors. Read `j_sold_picks`: with the cap hit of the player sold
held fixed, does selling for just picks and prospects still gain?

Equation: `grade = sum over k of b_k * j_k + c*j_cap + e`

```stata
regress grade j_sold_picks j_deadline_buyer j_earlier_buyer j_rental j_retained j_age28_31 j_age32_plus j_defence j_clause j_top15_below j_one_for_many j_took_dump j_new_gm j_cap if first_club == 1 & declared == 1, noconstant vce(robust)
regress real_war j_sold_picks j_deadline_buyer j_earlier_buyer j_rental j_retained j_age28_31 j_age32_plus j_defence j_clause j_top15_below j_one_for_many j_took_dump j_new_gm j_cap if first_club == 1 & declared == 1, noconstant vce(robust)
regress real_gv j_sold_picks j_deadline_buyer j_earlier_buyer j_rental j_retained j_age28_31 j_age32_plus j_defence j_clause j_top15_below j_one_for_many j_took_dump j_new_gm j_cap if first_club == 1 & declared == 1, noconstant vce(robust)
```

### 6. How the price follows a contract's two parts

All trades to March 2026, the main player rule: the price paid for the main player on the value of his forecasted
performance and on his cap cost, with a constant, standard errors clustered by trade. A price that followed the contract
in full would give +1 on the performance value and -1 on the cost. Then the same on what his performance delivered in the
seasons played. Then two-stage least squares: the models' performance value predicted first from what the seasons played
delivered (the first stage), so the part of the models' value that is error drops out. The document's two-stage
standard errors (0.19, 0.16) come from 2,000 resamples of trades; Stata's clustered ones differ.

Equation: `price = a + b*perf_value + c*cap_cost + e` (b = 1 and c = -1: the price follows the contract in full)

```stata
regress price perf_value cap_cost if in_price == 1, vce(cluster trade_id)
regress price perf_played cap_cost if in_price == 1, vce(cluster trade_id)
ivregress 2sls price cap_cost (perf_value = perf_played) if in_price == 1, vce(cluster trade_id)
regress perf_value perf_played cap_cost if in_price == 1
```
