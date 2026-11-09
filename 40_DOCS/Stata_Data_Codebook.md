# The model's regressions in Stata

Build the CSVs first, from the repo root (about 3 minutes):

```
python 20_CODE/stata_refresh.py
```

Then in Stata, work from the folder the CSVs are in:

```
cd "C:\Users\thoma\Desktop\xNPV\30_OUTPUT\stata"
```

Each section starts by importing its CSV. The line above each command (starting with `*`) says what it does; Stata
skips those lines, so a block can be pasted in whole. `30_OUTPUT/stata/xnpv_walkthrough.do` has the same commands, with
the figure each one should print.

The same option words recur:

| In the command | What it means |
|---|---|
| `noconstant` | No constant (intercept): the line goes through zero, so a player with a zero input is worth zero |
| `vce(robust)` | Robust standard errors: the size of the misses may differ from player to player |
| `vce(cluster x)` | Clustered standard errors: one player's (or trade's) misses may be related across his rows |
| `if ...` | Use only the rows where the condition holds |
| `ibn.g#c.x` | A separate coefficient on x for each value of g |
| `c.x#c.z` | x times z |
| `testparm`, `test` | Test that the named coefficients are zero (or equal to each other); read the p-value |
| `tobit ..., ll(m)` | A regression where the outcome cannot go below m (the league minimum): a contract at the minimum says only that his price was at or below it |
| `logit` | A regression for a yes/no outcome: the chance of a yes |
| `estimates store n`, `lrtest` | Save a fit under a name; compare two nested fits (does the bigger one fit significantly better?) |
| `quietly` | Fit without printing the table |

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
* Regress career NPV on star probability, leaving out deceased players; no constant, robust standard errors.
* The coefficient on p_star is the star value: what a 100% star chance is worth.
regress career_npv_m p_star if excluded_deceased == 0, noconstant vce(robust)
```

### 2. Without the 2015 and 2016 drafts

```stata
* The same regression, also leaving out the 2015 and 2016 drafts (the sensitivity).
regress career_npv_m p_star if excluded_deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

### 3. Each term added to the pick curve

```stata
* Add a constant: regress career NPV on star probability with an intercept; robust standard errors.
regress career_npv_m p_star if excluded_deceased == 0, vce(robust)

* Add an intercept for each draft year: star probability plus a dummy per draft, no overall constant.
regress career_npv_m p_star ibn.draft_year if excluded_deceased == 0, noconstant vce(robust)
* Test that all eleven draft intercepts are zero.
testparm ibn.draft_year

* Add the overall pick number and a constant.
regress career_npv_m p_star pick if excluded_deceased == 0, vce(robust)

* Add the chance of becoming an NHL player; no constant.
regress career_npv_m p_star p_nhler if excluded_deceased == 0, noconstant vce(robust)
```

### 4. One star value for every draft

```stata
* Regress career NPV on star probability with a separate star value for each draft year; no constant.
regress career_npv_m ibn.draft_year#c.p_star if excluded_deceased == 0, noconstant vce(robust)
* Test that the eleven star values are all equal.
testparm ibn.draft_year#c.p_star, equal

* Regress career NPV on star probability and its trend across draft years: does the star value drift over time?
regress career_npv_m p_star p_star_trend if excluded_deceased == 0, noconstant vce(robust)
* The same trend, leaving out the 2015 and 2016 drafts.
regress career_npv_m p_star p_star_trend if excluded_deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

### 5. A star value for defencemen

```stata
* Regress career NPV on star probability and on star probability for defencemen; no constant.
* p_star's coefficient is forwards' and goaltenders' star value; p_star_x_d_draft's is what defencemen's differs by.
regress career_npv_m p_star p_star_x_d_draft if excluded_deceased == 0, noconstant vce(robust)
* Add the two coefficients: defencemen's star value.
lincom p_star + p_star_x_d_draft
```

### 6. Other shapes

```stata
* Career NPV on the overall pick number: a straight line with a constant.
regress career_npv_m pick if excluded_deceased == 0, vce(robust)
* Career NPV on the log of the pick, with a constant.
regress career_npv_m log_pick if excluded_deceased == 0, vce(robust)
* Career NPV on the log of the pick and its square, with a constant.
regress career_npv_m log_pick log_pick_sq if excluded_deceased == 0, vce(robust)
* Career NPV on star probability and its square, no constant.
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

Every regression below has a separate coefficient on each term for each season after the draft (D+1, D+2, D+3, D+4,
D+5 and later), no constant, and standard errors clustered by player.

### 7. The star value in each season after the draft

```stata
* Regress remaining NPV on star probability, a separate star value for each season after the draft; all prospects.
regress remaining_npv_m ibn.season_group#c.p_star if sample_star == 1, noconstant vce(cluster player_id)
```

### 8. How the star value fades

These tests use the regression in step 7.

```stata
* Test that the star value is the same in all five seasons.
test 1.season_group#c.p_star = 2.season_group#c.p_star = 3.season_group#c.p_star = 4.season_group#c.p_star = 5.season_group#c.p_star

* Test that it falls by the same amount each season from D+1 to D+4 (a straight line).
test (2.season_group#c.p_star - 1.season_group#c.p_star = 3.season_group#c.p_star - 2.season_group#c.p_star) ///
     (3.season_group#c.p_star - 2.season_group#c.p_star = 4.season_group#c.p_star - 3.season_group#c.p_star)

* Test that it falls by the same percentage each season from D+1 to D+4.
testnl (_b[2.season_group#c.p_star]^2 = _b[1.season_group#c.p_star]*_b[3.season_group#c.p_star]) ///
       (_b[3.season_group#c.p_star]^2 = _b[2.season_group#c.p_star]*_b[4.season_group#c.p_star])
```

### 9. Production

```stata
* Regress remaining NPV on star probability and production; skater prospects.
regress remaining_npv_m ibn.season_group#c.(p_star nhle82) if sample_production == 1, noconstant vce(cluster player_id)
* Test that production adds nothing (its five coefficients are zero).
testparm ibn.season_group#c.nhle82

* Add production squared.
regress remaining_npv_m ibn.season_group#c.(p_star nhle82 nhle82_sq) if sample_production == 1, noconstant vce(cluster player_id)
* Test that production and its square together add nothing.
testparm ibn.season_group#c.nhle82 ibn.season_group#c.nhle82_sq
* Test that production squared adds nothing beyond linear production.
testparm ibn.season_group#c.nhle82_sq
* Test that star probability adds nothing in D+4 and from D+5 on.
test 4.season_group#c.p_star 5.season_group#c.p_star

* Keep star probability only in D+1 to D+3 (s_early), with production and its square.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq) if sample_production == 1, noconstant vce(cluster player_id)
* Test that linear production adds nothing beside its square.
testparm ibn.season_group#c.nhle82
```

### 10. Age

```stata
* Add age on its own (age - 18, D+1 to D+4) to draft position and production.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq flat_term) if sample_production == 1, noconstant vce(cluster player_id)
* Test that age on its own adds nothing.
testparm ibn.season_group#c.flat_term

* Instead add production x (age - 18), D+1 to D+4: each point worth less the older he is when he scores it.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term) if sample_production == 1, noconstant vce(cluster player_id)
* Test that production x age adds nothing.
testparm ibn.season_group#c.age_term

* Add both.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq flat_term age_term) if sample_production == 1, noconstant vce(cluster player_id)
* Test age on its own, given production x age.
testparm ibn.season_group#c.flat_term
* Test production x age, given age on its own.
testparm ibn.season_group#c.age_term

* Production x (age - 18) in every season, including D+5 and later.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq prod_x_age_m18) if sample_production == 1, noconstant vce(cluster player_id)
* Test that it adds nothing from D+5 on.
test 5.season_group#c.prod_x_age_m18
```

### 11. The adopted prospect model, and the defenceman tests

```stata
* The adopted model: remaining NPV on star probability (D+1 to D+3), production, its square, production x (age - 18)
* (D+1 to D+4) and production for defencemen; skater prospects.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
* Test that the defenceman terms add nothing.
testparm ibn.season_group#c.prod_x_defence
* Test that production and its square add nothing from D+5 on.
test 5.season_group#c.nhle82 5.season_group#c.nhle82_sq

* Add production squared for defencemen.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence prod_sq_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
* Test that it adds nothing.
testparm ibn.season_group#c.prod_sq_x_defence

* Add star probability for defencemen.
regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq age_term prod_x_defence s_early_x_defence) if sample_production == 1, noconstant vce(cluster player_id)
* Test that it adds nothing.
testparm ibn.season_group#c.s_early_x_defence
```

### 12. Linear production, with age measured from 18, 19 and 20

```stata
* For age measured from 18, then 19, then 20: fit the adopted model (without printing it), then test that linear
* production adds nothing. The three fits give the same values; only this test changes.
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

### 13. The skater price line

```stata
* Tobit of cap hit on forecast WAR, a defenceman's extra per forecast win, and years of term; floor at the league minimum.
tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m)
* The same, with standard errors clustered by player.
tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m) vce(cluster player_num)
```

### 14. The price line built up

```stata
* Cap hit on forecast WAR only; save as "wins".
quietly tobit cap_m xwar, ll(min_m)
estimates store wins
* Add a defenceman's extra per win; save as "defence".
quietly tobit cap_m xwar c.xwar#c.is_d, ll(min_m)
estimates store defence
* Add years of term (the adopted line); save as "adopted".
quietly tobit cap_m xwar c.xwar#c.is_d term_years, ll(min_m)
estimates store adopted
* Does the defence term improve on wins only?
lrtest wins defence
* Does term improve on wins and defence?
lrtest defence adopted
```

### 15. Other forms of the price line

Each fits the adopted line plus one change, then tests whether the change improves the fit.

```stata
* A separate line for RFA signings: their own intercept, price per win, defence extra and term premium.
quietly tobit cap_m xwar c.xwar#c.is_d term_years is_rfa c.is_rfa#c.xwar c.is_rfa#c.xwar#c.is_d c.is_rfa#c.term_years, ll(min_m)
lrtest adopted .

* A term premium that changes with the forecast (term x forecast WAR).
quietly tobit cap_m xwar c.xwar#c.is_d term_years c.term_years#c.xwar, ll(min_m)
lrtest adopted .

* A term premium for each forecast group (below 0, 0 to 1, 1 to 2, 2 or more wins); save as "groups".
quietly tobit cap_m xwar c.xwar#c.is_d term_years term_x_0to1 term_x_1to2 term_x_2plus, ll(min_m)
estimates store groups
lrtest adopted groups

* One premium below replacement level (forecast under 0) and another above; save as "onestep".
quietly tobit cap_m xwar c.xwar#c.is_d term_years term_x_0plus, ll(min_m)
estimates store onestep
lrtest adopted onestep
* Do the groups improve on the one step?
lrtest onestep groups

* Forecast WAR squared.
quietly tobit cap_m xwar c.xwar#c.is_d term_years c.xwar#c.xwar, ll(min_m)
lrtest adopted .

* A different price per win above one forecast win.
quietly tobit cap_m xwar c.xwar#c.is_d term_years xwar_over1, ll(min_m)
lrtest adopted .

* A separate line for contracts starting 2022-23 to 2025-26.
quietly tobit cap_m xwar c.xwar#c.is_d term_years start_2022_on c.start_2022_on#c.xwar c.start_2022_on#c.xwar#c.is_d c.start_2022_on#c.term_years, ll(min_m)
lrtest adopted .
```

### 16. Pricing on the forecast over the whole term

Not nested in the adopted line, so compare the log likelihood each prints with the adopted line's (higher fits better).

```stata
* The price line with forecast WAR averaged over the contract's term in place of the first season's.
tobit cap_m xwar_term_avg c.xwar_term_avg#c.is_d term_years, ll(min_m)
* The same, with each season's forecast times his chance of playing.
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
* Tobit of goaltender cap hit on forecast WAR and years of term; floor at the league minimum. Save as "g_adopted".
tobit cap_m xwar term_years, ll(min_m)
estimates store g_adopted
* Without term (not printed).
quietly tobit cap_m xwar, ll(min_m)
* Does term improve the fit?
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

These are fitted as the 2025-26 valuation fits them: on seasons before 2025-26 (`season < 2025`), standard errors
clustered by player. `h == 0` is the valuation season itself.

### 18. The games share

```stata
* Games share on trailing games share; print its R-squared.
quietly regress y_gp_share tr_gp_share if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
* Add seasons since debut; print R-squared.
quietly regress y_gp_share tr_gp_share exp_seasons if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
* Add age and age squared; print R-squared.
quietly regress y_gp_share tr_gp_share exp_seasons age_c age_c2 if h == 0 & season < 2025, vce(cluster career_num)
display e(r2)
* Add trailing WAR: the adopted games-share regression.
regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war if h == 0 & season < 2025, vce(cluster career_num)

* The adopted regression for each season ahead, 0 to 5.
forvalues s = 0/5 {
    regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war if h == `s' & season < 2025, vce(cluster career_num)
}

* The same with the defenceman dummy added, for each season ahead (read is_d's p-value; it was dropped).
forvalues s = 0/5 {
    regress y_gp_share tr_gp_share exp_seasons age_c age_c2 tw_war is_d if h == `s' & season < 2025, vce(cluster career_num)
}
```

### 19. The chance of playing

```stata
* Logit of whether he played on his age that season; print the pseudo R-squared.
quietly logit y_played p_age_c if h == 0 & season < 2025, vce(cluster career_num)
display e(r2_p)
* Add trailing WAR, trailing games share and the defenceman dummy; print the pseudo R-squared.
quietly logit y_played p_age_c tw_war tr_gp_share is_d if h == 0 & season < 2025, vce(cluster career_num)
display e(r2_p)
* Add contract status: the adopted chance-of-playing regression.
logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown if h == 0 & season < 2025, vce(cluster career_num)

* The adopted regression for each season ahead, 0 to 5.
forvalues s = 0/5 {
    logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown if h == `s' & season < 2025, vce(cluster career_num)
}

* The same with age squared and seasons since debut added, for each season ahead (read their p-values; both dropped).
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
* Regress how far a goaltender's WAR beat his track-record forecast on his age, seasons before 2025-26, with a constant.
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
* Logit of whether a goaltender played, on his age, his forecast WAR and his most recent season's games; valuation season.
logit played age_c pulled gp_share_last if h == 0 & season < 2025

* The same with age squared added, for each season ahead 0 to 12 (read age_c2's p-value; it was dropped).
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
* Regress each club's outcome on its forecast, no constant, complete trades: a slope of 1 means the forecast's gaps come true.
regress outcome_net_m forecast_net_m if complete == 1, noconstant
* The correlation between forecast and outcome.
correlate forecast_net_m outcome_net_m if complete == 1
* The share of trades in which the club the forecast favoured came out ahead (0.5 would be a coin flip).
mean ahead if complete == 1 & favoured == 1
```

### 23. Test A: realised seasons only, and without conditional picks

```stata
* The same slope with the outcome counted on realised seasons only.
regress realised_net_m forecast_net_m if complete == 1, noconstant
* The same slope leaving out trades with a conditional pick.
regress outcome_net_m forecast_net_m if complete == 1 & has_conditional_pick == 0, noconstant
```

### 24. Test A: in-season and off-season trades

```stata
* The slope for trades made during the regular season.
regress outcome_net_m forecast_net_m if complete == 1 & during_regular_season == 1, noconstant
* The slope for trades made outside it.
regress outcome_net_m forecast_net_m if complete == 1 & during_regular_season == 0, noconstant
```

### 25. Test C: the groups

```stata
* For each group, the mean forecast, mean outcome and mean miss (outcome less forecast) of its club sides.
* C1: clubs that received picks and prospects for players.
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_futures == 1
* C2: the club higher in the standings, in-season two-team trades.
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_buyer == 1
* C4: clubs in trades with retained salary.
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_retained == 1
* C5: clubs that received nothing recorded.
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_nothing_back == 1
* C6: clubs that received a player with a no-trade or no-move clause.
mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_clause == 1
```

### 26. Test A on Game Value

```stata
* Test A's slope, correlation and share ahead with the outcome measured on Game Value (adjusted).
regress outcome_net_m_gv_adj forecast_net_m if complete == 1, noconstant
correlate forecast_net_m outcome_net_m_gv_adj if complete == 1
mean ahead_gv_adj if complete == 1 & favoured == 1
* The same on Game Value (raw).
regress outcome_net_m_gv_raw forecast_net_m if complete == 1, noconstant
correlate forecast_net_m outcome_net_m_gv_raw if complete == 1
mean ahead_gv_raw if complete == 1 & favoured == 1
```

### 27. Test A's interval

```stata
* Refit Test A's slope on 2,000 resamples of whole trades (both sides of a trade together) for its interval.
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
* The mean miss (outcome less forecast) per traded asset, for each asset class.
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
* Regress each team's goal differential in a game on its skaters' summed Game Value, with a constant.
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
* Regress each team's season goal differential on its skaters' summed Game Value, with a constant.
regress gv_goal_diff game_value_sum
```

### 31. Goals per win

```stata
* Regress team wins on goal differential, all seasons together; goals per win is one over the slope.
regress wins goal_diff_in_play
display "goals per win: " 1/_b[goal_diff_in_play]

* For each season: the same regression (not printed), then that season's goals per win.
levelsof season, local(ss)
foreach s of local ss {
    quietly regress wins goal_diff_in_play if season == `s'
    display "`s'  goals per win " %6.3f 1/_b[goal_diff_in_play]
}
```
