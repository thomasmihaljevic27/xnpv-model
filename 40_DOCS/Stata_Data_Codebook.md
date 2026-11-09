# The model's regressions in Stata

Build the CSVs first, from the repo root (about 3 minutes):

```
python 20_CODE/stata_refresh.py
```

Then in Stata, work from the folder the CSVs are in:

```
cd "C:\Users\thoma\Desktop\xNPV\30_OUTPUT\stata"
```

Each section starts by importing its CSV. `30_OUTPUT/stata/xnpv_walkthrough.do` has the same commands, with the
figure each one should print.

---

## Draft picks

### Load

```stata
import delimited using "draft_players.csv", clear
```

| Variable | What it is |
|---|---|
| `career_npv_m` | Career NPV to the club that drafted him, $M (the outcome) |
| `p_star` | Chance a pick at his draft position becomes a star (Bacon) |
| `excluded_deceased` | 1 for the six players who died before reaching the NHL |
| `draft_year` | Draft year |
| `pick` | Overall pick number |
| `p_nhler` | Chance a pick at his draft position becomes an NHL player (Bacon) |
| `p_star_trend` | p_star x (draft year - 2012): lets the star value drift by draft |
| `p_star_x_d_draft` | p_star if he was drafted as a defenceman, else 0 |
| `log_pick` | Log of the overall pick |
| `log_pick_sq` | log_pick squared |
| `p_star_sq` | p_star squared |

### 1. The pick curve

```stata
regress career_npv_m p_star if excluded_deceased == 0, noconstant vce(robust)
```

### 2. Without the 2015 and 2016 drafts

```stata
regress career_npv_m p_star if excluded_deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

### 3. Each term added to the pick curve

```stata
* An intercept
regress career_npv_m p_star if excluded_deceased == 0, vce(robust)

* An intercept for each draft
regress career_npv_m p_star ibn.draft_year if excluded_deceased == 0, noconstant vce(robust)
testparm ibn.draft_year

* Draft position and an intercept
regress career_npv_m p_star pick if excluded_deceased == 0, vce(robust)

* NHL-player probability
regress career_npv_m p_star p_nhler if excluded_deceased == 0, noconstant vce(robust)
```

### 4. One star value for every draft

```stata
* A star value for each draft, and the test that they are equal
regress career_npv_m ibn.draft_year#c.p_star if excluded_deceased == 0, noconstant vce(robust)
testparm ibn.draft_year#c.p_star, equal

* A trend across drafts, with and without 2015 and 2016
regress career_npv_m p_star p_star_trend if excluded_deceased == 0, noconstant vce(robust)
regress career_npv_m p_star p_star_trend if excluded_deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

### 5. A star value for defencemen

```stata
regress career_npv_m p_star p_star_x_d_draft if excluded_deceased == 0, noconstant vce(robust)
lincom p_star + p_star_x_d_draft
```

### 6. Other shapes

```stata
regress career_npv_m pick if excluded_deceased == 0, vce(robust)
regress career_npv_m log_pick if excluded_deceased == 0, vce(robust)
regress career_npv_m log_pick log_pick_sq if excluded_deceased == 0, vce(robust)
regress career_npv_m p_star p_star_sq if excluded_deceased == 0, noconstant vce(robust)
```

---

## Prospects

### Load

```stata
import delimited using "prospect_seasons.csv", clear
```

| Variable | What it is |
|---|---|
| `remaining_npv_m` | His NPV from this season to the end of club control, $M (the outcome) |
| `season_group` | Season after the draft: 1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later |
| `sample_star` | 1 for a prospect-season (every position) |
| `sample_production` | 1 for a skater prospect-season |
| `player_id` | The player (draft year x 1000 + pick): standard errors clustered on it |
| `p_star` | Chance a pick at his draft position becomes a star (Bacon) |
| `s_early` | p_star in D+1 to D+3, 0 later |
| `nhle82` | Production: NHLe points per 82 games, 50/30/20 over the 3 seasons before |
| `nhle82_sq` | nhle82 squared |
| `age_term` | nhle82 x (age - 18) in D+1 to D+4, 0 later |
| `prod_x_age_m18` | nhle82 x (age - 18) in every season |
| `flat_term` | Age - 18 in D+1 to D+4, 0 later (age on its own; tested, not adopted) |
| `prod_x_defence` | nhle82 for a defenceman, else 0 |
| `prod_sq_x_defence` | nhle82_sq for a defenceman, else 0 |
| `s_early_x_defence` | s_early for a defenceman, else 0 |
| `age_term_19` | nhle82 x (age - 19) in D+1 to D+4, 0 later |
| `age_term_20` | nhle82 x (age - 20) in D+1 to D+4, 0 later |

`ibn.season_group#c.(x y)` gives x and y a separate coefficient in each season after the draft (D+1 to D+5 and later).

### 7. The star value in each season after the draft

```stata
regress remaining_npv_m ibn.season_group#c.p_star if sample_star == 1, noconstant vce(cluster player_id)
```

### 8. How the star value fades

```stata
* One value for every season
test 1.season_group#c.p_star = 2.season_group#c.p_star = 3.season_group#c.p_star = 4.season_group#c.p_star = 5.season_group#c.p_star

* A straight-line decline
test (2.season_group#c.p_star - 1.season_group#c.p_star = 3.season_group#c.p_star - 2.season_group#c.p_star) ///
     (3.season_group#c.p_star - 2.season_group#c.p_star = 4.season_group#c.p_star - 3.season_group#c.p_star)

* The same percentage decline
testnl (_b[2.season_group#c.p_star]^2 = _b[1.season_group#c.p_star]*_b[3.season_group#c.p_star]) ///
       (_b[3.season_group#c.p_star]^2 = _b[2.season_group#c.p_star]*_b[4.season_group#c.p_star])
```

### 9. Production

```stata
* Linear production
regress remaining_npv_m ibn.season_group#c.(p_star nhle82) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.nhle82

* Linear and squared production
regress remaining_npv_m ibn.season_group#c.(p_star nhle82 nhle82_sq) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.nhle82 ibn.season_group#c.nhle82_sq
testparm ibn.season_group#c.nhle82_sq
test 4.season_group#c.p_star 5.season_group#c.p_star

* Draft position in D+1 to D+3 only
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.nhle82
```

### 10. Age

```stata
* Age on its own
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq flat_term) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.flat_term

* Production x (age - 18)
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.age_term

* Both together
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq flat_term age_term) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.flat_term
testparm ibn.season_group#c.age_term

* Production x (age - 18) from D+5 on as well
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq prod_x_age_m18) if sample_production == 1, noconstant vce(cluster player_id)
test 5.season_group#c.prod_x_age_m18
```

### 11. The adopted prospect model, and the defenceman tests

```stata
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.prod_x_defence
test 5.season_group#c.nhle82 5.season_group#c.nhle82_sq

* Defenceman x production squared
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence prod_sq_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.prod_sq_x_defence

* Defenceman x draft position
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence s_early_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
testparm ibn.season_group#c.s_early_x_defence
```

### 12. Linear production, with age measured from 18, 19 and 20

```stata
foreach v in age_term age_term_19 age_term_20 {
    quietly regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq `v' prod_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
    testparm ibn.season_group#c.nhle82
}
```

---

## Players

### Load: skater contracts

```stata
import delimited using "price_line_skaters.csv", clear
```

| Variable | What it is |
|---|---|
| `cap_m` | Cap hit, $M at the 2025-26 cap (the outcome) |
| `min_m` | League minimum, $M at the 2025-26 cap (the tobit's lower limit) |
| `xwar` | Forecast WAR if he plays in the contract's first season, at the signing |
| `is_d` | 1 for a defenceman |
| `term_years` | Years of term |
| `player_num` | The player: standard errors clustered on it |
| `is_rfa` | 1 for an RFA signing |
| `term_x_0to1` | term_years if xwar is 0 to 1, else 0 |
| `term_x_1to2` | term_years if xwar is 1 to 2, else 0 |
| `term_x_2plus` | term_years if xwar is 2 or more, else 0 |
| `term_x_0plus` | term_years if xwar is 0 or more, else 0 |
| `xwar_over1` | xwar above 1 (xwar - 1), 0 below |
| `start_2022_on` | 1 if the contract starts in 2022-23 or later |
| `xwar_term_avg` | Forecast WAR if he plays, averaged over the contract's term |
| `xwar_term_avg_exp` | xwar_term_avg with each season x his chance of playing |

`c.xwar#c.is_d` is xwar x is_d: a defenceman's extra price per win.

### 13. The skater price line

```stata
tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m)
tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m) vce(cluster player_num)
```

### 14. The price line built up

```stata
quietly tobit cap_m xwar, ll(min_m)
estimates store wins
quietly tobit cap_m xwar c.xwar#c.is_d, ll(min_m)
estimates store defence
quietly tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m)
estimates store adopted
lrtest wins defence
lrtest defence adopted
```

### 15. Other forms of the price line

```stata
* A separate line for RFAs
quietly tobit cap_m xwar c.xwar#c.is_d term_years is_rfa c.is_rfa#c.xwar c.is_rfa#c.xwar#c.is_d c.is_rfa#c.term_years, ll(min_m)
lrtest adopted .

* The term premium times the forecast
quietly tobit cap_m xwar c.xwar#c.is_d term_years c.term_years#c.xwar, ll(min_m)
lrtest adopted .

* A term premium by forecast group
quietly tobit cap_m xwar c.xwar#c.is_d term_years term_x_0to1 term_x_1to2 term_x_2plus, ll(min_m)
estimates store groups
lrtest adopted groups

* A different term premium below replacement level
quietly tobit cap_m xwar c.xwar#c.is_d term_years term_x_0plus, ll(min_m)
estimates store onestep
lrtest adopted onestep
lrtest onestep groups

* A squared forecast
quietly tobit cap_m xwar c.xwar#c.is_d term_years c.xwar#c.xwar, ll(min_m)
lrtest adopted .

* A bend at one forecast win
quietly tobit cap_m xwar c.xwar#c.is_d term_years xwar_over1, ll(min_m)
lrtest adopted .

* A separate line for 2022-23 to 2025-26
quietly tobit cap_m xwar c.xwar#c.is_d term_years start_2022_on c.start_2022_on#c.xwar c.start_2022_on#c.xwar#c.is_d c.start_2022_on#c.term_years, ll(min_m)
lrtest adopted .
```

### 16. Pricing on the forecast over the whole term

```stata
tobit cap_m xwar_term_avg c.xwar_term_avg#c.is_d term_years, ll(min_m)
tobit cap_m xwar_term_avg_exp c.xwar_term_avg_exp#c.is_d term_years, ll(min_m)
```

### Load: goaltender contracts

```stata
import delimited using "price_line_goalies.csv", clear
```

| Variable | What it is |
|---|---|
| `cap_m` | Cap hit, $M at the 2025-26 cap (the outcome) |
| `min_m` | League minimum, $M at the 2025-26 cap (the tobit's lower limit) |
| `xwar` | Forecast WAR at the signing: 35% his 50/30/20 WAR, 65% league average |
| `term_years` | Years of term |

### 17. The goaltender price line

```stata
tobit cap_m xwar term_years, ll(min_m)
estimates store g_adopted
quietly tobit cap_m xwar, ll(min_m)
lrtest . g_adopted
```

### Load: skater forecast

```stata
import delimited using "skater_forecast_pairs.csv", clear
```

| Variable | What it is |
|---|---|
| `h` | Seasons ahead of the valuation season (0 = the valuation season) |
| `season` | The season forecast; season < 2025 = the rows the 2025-26 valuation uses |
| `career_num` | The player: standard errors clustered on it |
| `y_gp_share` | Share of his team's games he played that season (outcome) |
| `tr_gp_share` | His share of team games, 50/30/20 over the 3 seasons before |
| `exp_seasons` | Seasons since his NHL debut |
| `age_c` | Age at the valuation season - 27.22 |
| `age_c2` | age_c squared |
| `tw_war` | His WAR, 50/30/20 over the 3 seasons before |
| `is_d` | 1 for a defenceman |
| `y_played` | 1 if he played an NHL game that season (outcome) |
| `p_age_c` | Age in the season forecast - 27.22 |
| `p_age_c2` | p_age_c squared |
| `under_contract` | 1 if a contract signed by July 1 covers that season |
| `contract_unknown` | 1 for seasons before 2018-19, which the contract data cannot see |

### 18. The games share

```stata
* Built up
quietly regress y_gp_share tr_gp_share if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
quietly regress y_gp_share tr_gp_share exp_seasons if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
quietly regress y_gp_share tr_gp_share exp_seasons age_c age_c2 if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war if h == 0 & season < 2025, vce(cluster career_num)

* Each season ahead
forvalues s = 0/5 {
    regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war if h == `s' & season < 2025, vce(cluster career_num)
}

* The dropped defenceman term
forvalues s = 0/5 {
    regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war is_d if h == `s' & season < 2025, vce(cluster career_num)
}
```

### 19. The chance of playing

```stata
* Built up
quietly logit y_played p_age_c if h == 0 & season < 2025, vce(cluster career_num)
display e(r2_p)
quietly logit y_played p_age_c tw_war tr_gp_share is_d if h == 0 & season < 2025, vce(cluster career_num)
display e(r2_p)
logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown if h == 0 & season < 2025, vce(cluster career_num)

* Each season ahead
forvalues s = 0/5 {
    logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown if h == `s' & season < 2025, vce(cluster career_num)
}

* The dropped age squared and seasons since debut
forvalues s = 0/5 {
    logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown p_age_c2 exp_seasons if h == `s' & season < 2025, vce(cluster career_num)
}
```

### Load: goaltender age

```stata
import delimited using "goalie_age_rows.csv", clear
```

| Variable | What it is |
|---|---|
| `war_less_pulled` | Goaltender's WAR less his track-record forecast (outcome) |
| `age_c` | Age - 27.22 |
| `season` | Season; season < 2025 = the rows the 2025-26 valuation uses |

### 20. The goaltender age term

```stata
regress war_less_pulled age_c if season < 2025
```

### Load: goaltender chance of playing

```stata
import delimited using "goalie_play_rows.csv", clear
```

| Variable | What it is |
|---|---|
| `played` | 1 if he played an NHL game that season (outcome) |
| `h` | Seasons ahead of the valuation season (0 = the valuation season) |
| `season` | The season forecast; season < 2025 = the rows the 2025-26 valuation uses |
| `age_c` | Age in the season forecast - 27.22 |
| `age_c2` | age_c squared |
| `pulled` | His track-record forecast WAR |
| `gp_share_last` | His games in the season before the valuation season / 82 |

### 21. The goaltender chance of playing

```stata
logit played age_c pulled gp_share_last if h == 0 & season < 2025

* The dropped age squared
forvalues s = 0/12 {
    logit played age_c pulled gp_share_last age_c2 if h == `s' & season < 2025
}
```

---

## Back-test

### Load: club sides

```stata
import delimited using "backtest_club_sides.csv", clear
```

| Variable | What it is |
|---|---|
| `forecast_net_m` | Forecast: what the club received less what it gave up, $M |
| `outcome_net_m` | Outcome on WAR: realised through 2025-26, the rest revalued, $M |
| `realised_net_m` | Outcome on WAR, realised seasons only, $M |
| `complete` | 1 if every asset in the trade has an outcome (the tests' sample) |
| `favoured` | 1 for the club the forecast favoured in the trade |
| `ahead` | 1 if outcome_net_m is above zero |
| `has_conditional_pick` | 1 if the trade includes a conditional pick |
| `during_regular_season` | 1 for an in-season trade |
| `miss_m` | outcome_net_m - forecast_net_m |
| `g_futures` | Group C1: received picks and prospects for players |
| `g_buyer` | Group C2: higher in the standings, in-season two-team trade |
| `g_retained` | Group C4: retained salary in the trade |
| `g_nothing_back` | Group C5: received nothing recorded |
| `g_clause` | Group C6: received a player with a no-trade or no-move clause |
| `outcome_net_m_gv_adj` | Outcome on Game Value (adjusted), $M |
| `outcome_net_m_gv_raw` | Outcome on Game Value (raw), $M |
| `ahead_gv_adj` | 1 if outcome_net_m_gv_adj is above zero |
| `ahead_gv_raw` | 1 if outcome_net_m_gv_raw is above zero |
| `trade_id` | The trade: resampled as a unit |

### 22. Test A: outcome on forecast

```stata
regress outcome_net_m forecast_net_m if complete == 1, noconstant
correlate forecast_net_m outcome_net_m if complete == 1
mean ahead if complete == 1 & favoured == 1
```

### 23. Test A: realised seasons only, and without conditional picks

```stata
regress realised_net_m forecast_net_m if complete == 1, noconstant
regress outcome_net_m forecast_net_m if complete == 1 & has_conditional_pick == 0, noconstant
```

### 24. Test A: in-season and off-season trades

```stata
regress outcome_net_m forecast_net_m if complete == 1 & during_regular_season == 1, noconstant
regress outcome_net_m forecast_net_m if complete == 1 & during_regular_season == 0, noconstant
```

### 25. Test C: the groups

```stata
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_futures == 1
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_buyer == 1
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_retained == 1
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_nothing_back == 1
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_clause == 1
```

### 26. Test A on Game Value

```stata
regress outcome_net_m_gv_adj forecast_net_m if complete == 1, noconstant
correlate forecast_net_m outcome_net_m_gv_adj if complete == 1
mean ahead_gv_adj if complete == 1 & favoured == 1
regress outcome_net_m_gv_raw forecast_net_m if complete == 1, noconstant
correlate forecast_net_m outcome_net_m_gv_raw if complete == 1
mean ahead_gv_raw if complete == 1 & favoured == 1
```

### 27. Test A's interval

```stata
bootstrap _b, reps(2000) seed(20261020) cluster(trade_id): regress outcome_net_m forecast_net_m if complete == 1, noconstant
```

### Load: traded assets

```stata
import delimited using "backtest_assets.csv", clear
```

| Variable | What it is |
|---|---|
| `miss_m` | The asset's outcome less its forecast, $M |
| `complete_trade` | 1 if the asset's trade is in the tests' sample |
| `asset_class` | players, picks, prospects or retained salary |

### 28. Test B: by asset class

```stata
mean miss_m if complete_trade == 1, over(asset_class)
```

---

## Game Value

### Load: team-games

```stata
import delimited using "gv_team_games.csv", clear
```

| Variable | What it is |
|---|---|
| `goal_diff_in_play` | Team's goal differential in the game, shootout goal removed |
| `game_value_sum` | Team's skaters' Game Value in the game, summed |

### 29. Goal differential on Game Value, by game

```stata
regress goal_diff_in_play game_value_sum
```

### Load: team-seasons

```stata
import delimited using "gv_team_seasons.csv", clear
```

| Variable | What it is |
|---|---|
| `gv_goal_diff` | Goal differential in the games with Game Value |
| `game_value_sum` | Team's skaters' Game Value over the season, summed |
| `wins` | Team wins |
| `goal_diff_in_play` | Team's goal differential, shootout goals removed |
| `season` | Season (20172018 = 2017-18) |

### 30. Goal differential on Game Value, by season

```stata
regress gv_goal_diff game_value_sum
```

### 31. Goals per win

```stata
regress wins goal_diff_in_play
display "goals per win: " 1/_b[goal_diff_in_play]

levelsof season, local(ss)
foreach s of local ss {
    quietly regress wins goal_diff_in_play if season == `s'
    display "`s'  goals per win " %6.3f 1/_b[goal_diff_in_play]
}
```
