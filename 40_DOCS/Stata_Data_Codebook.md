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

### 20. The goaltender age term

```stata
regress war_less_pulled age_c if season < 2025
```

### Load: goaltender chance of playing

```stata
import delimited using "goalie_play_rows.csv", clear
```

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

### 29. Goal differential on Game Value, by game

```stata
regress goal_diff_in_play game_value_sum
```

### Load: team-seasons

```stata
import delimited using "gv_team_seasons.csv", clear
```

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
