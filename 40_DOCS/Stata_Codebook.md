# xNPV: the regressions in Stata

The regressions reported in the four documents, in the order they appear: Valuing Players, Valuing Draft Picks, Valuing
Prospects, then the Findings. Each block imports the CSV it needs, so any section can be run on its own. Put the CSVs in
one folder and start Stata there:

```stata
cd "C:\path\to\the\csv\folder"
```

Money is in $ millions at the 2025-26 salary cap ($95.5 million); the documents state it as a share of that cap (divide
by 95.5 and multiply by 100). Stata's p-values use the t distribution and the documents' use the normal, so a third
decimal can differ. The forecast's accuracy tests (out-of-sample RMSE comparisons) and the cross-validation in the
goaltender section are computed in Python and have no Stata block.

---

## 1. Valuing Players

### Data: the skater forecast

```stata
import delimited using "skater_forecast_pairs.csv", clear
```

| Variable | What it is |
|---|---|
| `seasons_ahead` | Seasons ahead of the valuation season (0 = the valuation season) |
| `season` | The season forecast; `season < 2025` keeps the rows the 2025-26 valuation uses |
| `player_id` | The player; standard errors are clustered on it |
| `gp_share` | Share of his team's 82 games he played that season (outcome) |
| `gp_share_trail` | His games share, 50/30/20 over the three seasons before |
| `seasons_since_debut` | NHL seasons since his debut |
| `age_minus27`, `age_minus27_sq` | Age at the valuation season less 27.22, and its square |
| `war_trail` | His WAR, 50/30/20 over the three seasons before |
| `defence` | 1 for a defenceman |
| `played` | 1 if he played an NHL game that season (outcome) |
| `age_minus27_season`, `age_minus27_season_sq` | Age in the season forecast less 27.22, and its square |
| `under_contract` | 1 if a contract signed by the valuation date covers that season |
| `pre_2018` | 1 for a season before 2018-19, which the contract records do not cover |

### How much does a player play, given his recent games, experience, age and quality? (Table 6, built up)

```stata
regress gp_share gp_share_trail if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
regress gp_share gp_share_trail seasons_since_debut if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
```

### Does he play at least one NHL game, given his age, quality, recent games, position and contract? (Table 7, built up)

```stata
logit played age_minus27_season if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
logit played age_minus27_season war_trail gp_share_trail defence if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 if seasons_ahead == 0 & season < 2025, vce(cluster player_id)
```

### Data: team Game Value

```stata
import delimited using "gv_team_seasons.csv", clear
```

| Variable | What it is |
|---|---|
| `goal_diff_gv_games` | Team's goal differential in the games with Game Value (outcome) |
| `game_value` | Team's skaters' Game Value over the season, summed |

### Does team Game Value explain team goal differential? (Checking the forecast with Game Value)

```stata
regress goal_diff_gv_games game_value
```

### Data: skater contracts

```stata
import delimited using "price_line_skaters.csv", clear
```

| Variable | What it is |
|---|---|
| `cap_hit` | Cap hit (outcome) |
| `league_min` | League minimum, the lower limit of the Tobit regression |
| `war_fcst` | Forecasted WAR in the contract's first season, dated at the signing |
| `defence` | 1 for a defenceman |
| `term` | Contract length in years |
| `player_id` | The player; standard errors are clustered on it |
| `war_fcst_term_avg` | Forecasted WAR averaged over the contract's term |
| `war_exp_term_avg` | The same, each season times his chance of playing |
| `rfa` | 1 for a restricted free agent's contract |
| `term_war0plus` | `term` when `war_fcst` is 0 or more, else 0 |
| `term_war0to1`, `term_war1to2`, `term_war2plus` | `term` when `war_fcst` is in that range, else 0 |
| `war_fcst_over1` | `war_fcst` less 1 above one forecasted win, else 0 |
| `start_2022plus` | 1 for a contract starting in 2022-23 or later |

### What do clubs pay for a forecasted win, for a defenceman, and for each year of term? (Table 10, the price line)

Stata's log-likelihoods are in $ millions rather than shares of the cap, so they differ from Table 10's by a constant;
the likelihood-ratio tests are the same.

```stata
tobit cap_hit war_fcst, ll(league_min) vce(cluster player_id)
tobit cap_hit war_fcst c.war_fcst#c.defence, ll(league_min) vce(cluster player_id)
tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min) vce(cluster player_id)
```

### Do the defenceman term and the term premium each improve the fit? (Table 10, likelihood-ratio tests)

```stata
quietly tobit cap_hit war_fcst, ll(league_min)
estimates store wins
quietly tobit cap_hit war_fcst c.war_fcst#c.defence, ll(league_min)
estimates store defence
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
estimates store adopted
lrtest wins defence
lrtest defence adopted
```

### Do clubs price the forecast over the whole contract instead of its first season? (Table 12, last two rows)

```stata
tobit cap_hit war_fcst_term_avg c.war_fcst_term_avg#c.defence term, ll(league_min)
tobit cap_hit war_exp_term_avg c.war_exp_term_avg#c.defence term, ll(league_min)
```

### Does any other form of the price line fit better? (Table 12)

```stata
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term, ll(league_min)
estimates store adopted
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term term_war0plus, ll(league_min)
estimates store onestep
lrtest adopted onestep
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term term_war0to1 term_war1to2 term_war2plus, ll(league_min)
estimates store groups
lrtest adopted groups
lrtest onestep groups
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term c.term#c.war_fcst, ll(league_min)
lrtest adopted .
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term rfa c.rfa#c.war_fcst c.rfa#c.war_fcst#c.defence c.rfa#c.term, ll(league_min)
lrtest adopted .
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term c.war_fcst#c.war_fcst, ll(league_min)
lrtest adopted .
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term war_fcst_over1, ll(league_min)
lrtest adopted .
quietly tobit cap_hit war_fcst c.war_fcst#c.defence term start_2022plus c.start_2022plus#c.war_fcst c.start_2022plus#c.war_fcst#c.defence c.start_2022plus#c.term, ll(league_min)
lrtest adopted .
```

### Data: goaltender age

```stata
import delimited using "goalie_age_rows.csv", clear
```

| Variable | What it is |
|---|---|
| `war_minus_fcst` | A goaltender's WAR less his track-record forecast (outcome) |
| `age_minus27` | Age less 27.22 |
| `season` | Season; `season < 2025` keeps the rows the 2025-26 valuation uses |

### Does a goaltender fall short of his record as he ages? (Goaltenders, the age term)

```stata
regress war_minus_fcst age_minus27 if season < 2025
```

### Data: goaltender chance of playing

```stata
import delimited using "goalie_play_rows.csv", clear
```

| Variable | What it is |
|---|---|
| `played` | 1 if he played an NHL game that season (outcome) |
| `seasons_ahead` | Seasons ahead of the valuation season (0 = the valuation season) |
| `season` | The season forecast; `season < 2025` keeps the rows the 2025-26 valuation uses |
| `age_minus27_season`, `age_minus27_season_sq` | Age in the season forecast less 27.22, and its square |
| `war_fcst` | His track-record forecast WAR |
| `gp_share_recent` | His games in the most recent season, over 82 |

### Does a goaltender play, given his age, forecast and recent games? (Goaltenders, the chance of playing)

```stata
logit played age_minus27_season war_fcst gp_share_recent if seasons_ahead == 0 & season < 2025
```

### Does age squared belong in a goaltender's chance of playing? (Goaltenders; read the squared term's p-value)

```stata
forvalues s = 0/12 {
    logit played age_minus27_season war_fcst gp_share_recent age_minus27_season_sq if seasons_ahead == `s' & season < 2025
}
```

### Data: goaltender contracts

```stata
import delimited using "price_line_goalies.csv", clear
```

| Variable | What it is |
|---|---|
| `cap_hit` | Cap hit (outcome) |
| `league_min` | League minimum, the lower limit of the Tobit regression |
| `war_fcst` | Forecast WAR at the signing: 35% his 50/30/20 WAR, 65% the league average |
| `term` | Contract length in years |

### What do clubs pay a goaltender for a forecasted win and for each year of term? (Goaltenders, the price line)

```stata
tobit cap_hit war_fcst term, ll(league_min)
estimates store g_adopted
quietly tobit cap_hit war_fcst, ll(league_min)
lrtest . g_adopted
```

### Data: the skater forecast, again (Appendix A)

```stata
import delimited using "skater_forecast_pairs.csv", clear
```

### The games-share regression for each season ahead (Table A1)

```stata
forvalues s = 0/5 {
    regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
```

### The chance-of-playing regression for each season ahead (Table A2)

```stata
forvalues s = 0/5 {
    logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
```

### Do the three dropped terms belong? (Appendix A; read the added terms' p-values)

A defenceman dummy in the games share; age squared and seasons since debut in the chance of playing.

```stata
forvalues s = 0/5 {
    regress gp_share gp_share_trail seasons_since_debut age_minus27 age_minus27_sq war_trail defence if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
forvalues s = 0/5 {
    logit played age_minus27_season war_trail gp_share_trail defence under_contract pre_2018 age_minus27_season_sq seasons_since_debut if seasons_ahead == `s' & season < 2025, vce(cluster player_id)
}
```

---

## 2. Valuing Draft Picks

### Data: drafted players, 2007 to 2017

```stata
import delimited using "draft_players.csv", clear
```

| Variable | What it is |
|---|---|
| `career_npv` | His NPV over club control (outcome) |
| `star_prob` | Bacon's probability that a player taken at his draft position becomes a star |
| `nhl_prob` | Bacon's probability that a player taken at his draft position plays 200 NHL games |
| `deceased` | 1 for the six drafted players who died before reaching the NHL (left out) |
| `draft_year`, `pick` | Draft year and overall pick |
| `log_pick`, `log_pick_sq` | Log of the overall pick, and its square |
| `star_prob_sq` | `star_prob` squared |
| `star_prob_x_year` | `star_prob` times (draft year less 2012) |

### Which shape of value across draft positions fits? (Table 3)

```stata
regress career_npv pick if deceased == 0, vce(robust)
regress career_npv log_pick if deceased == 0, vce(robust)
regress career_npv log_pick log_pick_sq if deceased == 0, vce(robust)
regress career_npv star_prob if deceased == 0, noconstant vce(robust)
regress career_npv star_prob star_prob_sq if deceased == 0, noconstant vce(robust)
regress career_npv star_prob nhl_prob if deceased == 0, noconstant vce(robust)
```

### What is a pick worth per unit of star probability, and does anything else add to it? (Table 4, the star value built up)

```stata
regress career_npv star_prob if deceased == 0, noconstant vce(robust)
regress career_npv star_prob if deceased == 0, vce(robust)
regress career_npv star_prob ibn.draft_year if deceased == 0, noconstant vce(robust)
testparm ibn.draft_year
regress career_npv star_prob pick if deceased == 0, vce(robust)
regress career_npv star_prob nhl_prob if deceased == 0, noconstant vce(robust)
```

### Does the star value differ from draft to draft? (One star value for every draft)

```stata
regress career_npv ibn.draft_year#c.star_prob if deceased == 0, noconstant vce(robust)
testparm ibn.draft_year#c.star_prob, equal
```

### Does the star value drift across draft years, with and without 2015 and 2016? (One star value for every draft)

```stata
regress career_npv star_prob star_prob_x_year if deceased == 0, noconstant vce(robust)
regress career_npv star_prob star_prob_x_year if deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

### The star value without the 2015 and 2016 drafts (the sensitivity in Table 5)

```stata
regress career_npv star_prob if deceased == 0 & !inlist(draft_year, 2015, 2016), noconstant vce(robust)
```

---

## 3. Valuing Prospects

### Data: prospect-seasons

```stata
import delimited using "prospect_seasons.csv", clear
```

| Variable | What it is |
|---|---|
| `remaining_npv` | His NPV from this season to the end of club control (outcome) |
| `dplus` | Season after the draft: 1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later |
| `prospect`, `skater_prospect` | 1 for a prospect-season; 1 for a skater prospect-season |
| `player_id` | The player; standard errors are clustered on it |
| `star_prob` | Bacon's probability that a player taken at his draft position becomes a star |
| `star_prob_d1to3` | `star_prob` in D+1 to D+3, else 0 |
| `nhle_pts`, `nhle_pts_sq` | Production level: NHLe points per 82 games, 50/30/20 over the three seasons before; and its square |
| `age_minus18` | Age less 18 in D+1 to D+4, else 0 |
| `nhle_x_age18` | `nhle_pts` times (age less 18) in D+1 to D+4, else 0 |
| `nhle_x_age18_all` | `nhle_pts` times (age less 18) in every season |
| `nhle_x_age19`, `nhle_x_age20` | `nhle_pts` times (age less 19, or 20) in D+1 to D+4, else 0 |
| `nhle_pts_def`, `nhle_pts_sq_def` | `nhle_pts`, `nhle_pts_sq` for a defenceman, else 0 |
| `star_prob_d1to3_def` | `star_prob_d1to3` for a defenceman, else 0 |

Each regression gives every term a separate coefficient in each season after the draft (`ibn.dplus#c.`), has no
constant, and clusters standard errors by player.

### How much of his pick's value does a prospect keep in each season after the draft? (Table 1)

```stata
regress remaining_npv ibn.dplus#c.star_prob if prospect == 1, noconstant vce(cluster player_id)
```

### Does the star value stay the same, fall in a straight line, or fall by the same percentage? (Table 2)

```stata
quietly regress remaining_npv ibn.dplus#c.star_prob if prospect == 1, noconstant vce(cluster player_id)
test 1.dplus#c.star_prob = 2.dplus#c.star_prob = 3.dplus#c.star_prob = 4.dplus#c.star_prob = 5.dplus#c.star_prob
test (2.dplus#c.star_prob - 1.dplus#c.star_prob = 3.dplus#c.star_prob - 2.dplus#c.star_prob) (3.dplus#c.star_prob - 2.dplus#c.star_prob = 4.dplus#c.star_prob - 3.dplus#c.star_prob)
testnl (_b[2.dplus#c.star_prob]^2 = _b[1.dplus#c.star_prob]*_b[3.dplus#c.star_prob]) (_b[3.dplus#c.star_prob]^2 = _b[2.dplus#c.star_prob]*_b[4.dplus#c.star_prob])
```

### Does scoring after the draft add to draft position? (Table 3)

```stata
regress remaining_npv ibn.dplus#c.star_prob if skater_prospect == 1, noconstant vce(cluster player_id)
regress remaining_npv ibn.dplus#c.nhle_pts if skater_prospect == 1, noconstant vce(cluster player_id)
regress remaining_npv ibn.dplus#c.(star_prob nhle_pts) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts
regress remaining_npv ibn.dplus#c.(star_prob nhle_pts nhle_pts_sq) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts_sq
test 4.dplus#c.star_prob 5.dplus#c.star_prob
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts
```

### Is a point scored younger worth more? (Table 4)

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq age_minus18) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.age_minus18
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_x_age18
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq age_minus18 nhle_x_age18) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.age_minus18
testparm ibn.dplus#c.nhle_x_age18
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18_all) if skater_prospect == 1, noconstant vce(cluster player_id)
test 5.dplus#c.nhle_x_age18_all
```

### Is a defenceman's point worth more than a forward's? (Table 5, and the adopted model in Table 6)

```stata
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts_def
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def nhle_pts_sq_def) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.nhle_pts_sq_def
regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def star_prob_d1to3_def) if skater_prospect == 1, noconstant vce(cluster player_id)
testparm ibn.dplus#c.star_prob_d1to3_def
```

### Does production still matter from D+5 on? (The adopted model)

```stata
quietly regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq nhle_x_age18 nhle_pts_def) if skater_prospect == 1, noconstant vce(cluster player_id)
test 5.dplus#c.nhle_pts 5.dplus#c.nhle_pts_sq
```

### Does linear production's p-value depend on where age is measured from? (The adopted model)

The three regressions give the same fitted values; only the test of linear production changes.

```stata
foreach v in nhle_x_age18 nhle_x_age19 nhle_x_age20 {
    quietly regress remaining_npv ibn.dplus#c.(star_prob_d1to3 nhle_pts nhle_pts_sq `v' nhle_pts_def) if skater_prospect == 1, noconstant vce(cluster player_id)
    testparm ibn.dplus#c.nhle_pts
}
```

---

## 4. Findings

### Data: club sides of each trade

```stata
import delimited using "findings_data.csv", clear
```

One row for each club in each complete trade, July 2017 to March 2026. Each section picks its rows with a yes/no column.

| Variable | What it is |
|---|---|
| `trade_id`, `club`, `trade_date` | The trade, the club, the date |
| `tradeday_grade` | Trade-day xNPV: what the club received less what it gave up, at the models' values |
| `realized_war` | Realized NPV on WAR |
| `realized_gamevalue` | Realized NPV on Game Value |
| `realized_war_played_only` | Realized NPV on WAR, seasons played through 2025-26 only |
| `in_2017_22` | 1 for a trade from July 1, 2017 to March 28, 2022 |
| `favoured_by_grade` | 1 for the club the trade-day xNPV favoured |
| `came_out_ahead_war`, `came_out_ahead_gamevalue` | 1 when the club's realized NPV is above zero |
| `in_main_regression` | 1 for both clubs of the two-team trades in the main regression |
| `one_row_per_trade` | 1 for the first club (alphabetically) of a two-team trade, so each trade appears once |
| `main_` + characteristic | Main player rule: the club's side less the other club's (+1, 0 or -1 for a yes/no characteristic; the difference for a measure) |
| `any_` + characteristic | The same under the any player rule |
| `main_cap_hit`, `main_career_war`, `main_best_season_war` | The main player's cap hit, career WAR and best single-season WAR, the club's side less the other's |
| `trade_had_cap_dump` | 1 when either club was paid to take on a contract |
| `own_sold_for_just_picks` | 1 for a club that sold a player for just picks and prospects (its own yes/no) |
| `grp_` + group | The first club's group less the second's, for the sellers regression; `grp_cap_hit` the main players' cap hits |
| `in_price_regression` | 1 for the clubs whose main player has a model value and a cap cost |
| `price_paid_main_player` | Everything the club gave up less everything else it received |
| `performance_value` | The models' value of the main player's forecasted performance over the rest of his contract |
| `cap_hit_cost` | The present value of his cap hit over the seasons left |
| `performance_delivered` | What his performance delivered, seasons played through 2025-26 only |

### Do the models predict how trades turn out? (Section 2)

```stata
regress realized_war tradeday_grade if in_2017_22 == 1, noconstant
regress realized_gamevalue tradeday_grade if in_2017_22 == 1, noconstant
mean came_out_ahead_war came_out_ahead_gamevalue if in_2017_22 == 1 & favoured_by_grade == 1
```

### What do clubs overpay for, under the main player rule? (Section 3)

```stata
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_gamevalue main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_war_played_only main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
```

### What do clubs overpay for, under the any player rule? (Section 3)

```stata
regress tradeday_grade any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_war any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_gamevalue any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_war_played_only any_sold_for_just_picks any_deadline_buyer any_buyer_earlier_in_season any_got_rental any_retained_salary any_got_one_for_two_or_more any_took_cap_dump any_new_gm_sold_old_contract any_got_final_year_rfa any_got_only_late_picks any_age_28_31 any_age_32_plus any_defenceman any_clause any_signed_as_ufa any_two_seasons_left any_three_plus_seasons_left any_former_top15_pick any_recent_war any_war_above_forecast any_games_played_share any_goalie any_got_a_player if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
```

### Is the clause a stand-in for cap hit, reputation, or cap dumps? (Section 3, players with a clause)

```stata
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_cap_hit if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_cap_hit if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_career_war main_best_season_war if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_took_cap_dump main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player main_career_war main_best_season_war if in_main_regression == 1 & one_row_per_trade == 1, noconstant vce(robust)
regress tradeday_grade main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & one_row_per_trade == 1 & trade_had_cap_dump == 0, noconstant vce(robust)
regress realized_war main_sold_for_just_picks main_deadline_buyer main_buyer_earlier_in_season main_got_rental main_retained_salary main_got_one_for_two_or_more main_new_gm_sold_old_contract main_got_final_year_rfa main_got_only_late_picks main_age_28_31 main_age_32_plus main_defenceman main_clause main_signed_as_ufa main_two_seasons_left main_three_plus_seasons_left main_former_top15_pick main_recent_war main_war_above_forecast main_games_played_share main_goalie main_got_a_player if in_main_regression == 1 & one_row_per_trade == 1 & trade_had_cap_dump == 0, noconstant vce(robust)
```

### How much of a contract's value do clubs price? (Section 4)

The last two lines are the two-stage least squares estimate and its first stage. The document's two-stage standard
errors come from resampling trades, so Stata's clustered ones differ.

```stata
regress price_paid_main_player performance_value cap_hit_cost if in_price_regression == 1, vce(cluster trade_id)
regress price_paid_main_player performance_delivered cap_hit_cost if in_price_regression == 1, vce(cluster trade_id)
ivregress 2sls price_paid_main_player cap_hit_cost (performance_value = performance_delivered) if in_price_regression == 1, vce(cluster trade_id)
regress performance_value performance_delivered cap_hit_cost if in_price_regression == 1
```

### How did clubs that sold a player for just picks and prospects do on average? (Section 4, clubs selling players for picks and prospects)

```stata
mean tradeday_grade realized_war if in_2017_22 == 1 & own_sold_for_just_picks == 1, vce(cluster trade_id)
```

### Do sellers gain with the cap hit of the player sold held fixed? (Section 4, clubs selling players for picks and prospects)

```stata
regress tradeday_grade grp_sold_for_just_picks grp_deadline_buyer grp_buyer_earlier_in_season grp_got_rental grp_retained_salary grp_age_28_31 grp_age_32_plus grp_defenceman grp_clause grp_top15_below_average grp_got_one_for_two_or_more grp_took_cap_dump grp_new_gm_sold_old_contract grp_cap_hit if one_row_per_trade == 1 & in_2017_22 == 1, noconstant vce(robust)
regress realized_war grp_sold_for_just_picks grp_deadline_buyer grp_buyer_earlier_in_season grp_got_rental grp_retained_salary grp_age_28_31 grp_age_32_plus grp_defenceman grp_clause grp_top15_below_average grp_got_one_for_two_or_more grp_took_cap_dump grp_new_gm_sold_old_contract grp_cap_hit if one_row_per_trade == 1 & in_2017_22 == 1, noconstant vce(robust)
regress realized_gamevalue grp_sold_for_just_picks grp_deadline_buyer grp_buyer_earlier_in_season grp_got_rental grp_retained_salary grp_age_28_31 grp_age_32_plus grp_defenceman grp_clause grp_top15_below_average grp_got_one_for_two_or_more grp_took_cap_dump grp_new_gm_sold_old_contract grp_cap_hit if one_row_per_trade == 1 & in_2017_22 == 1, noconstant vce(robust)
```
