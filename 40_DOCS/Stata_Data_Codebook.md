# Stata data: every regression in the model

Fourteen CSV files in `30_OUTPUT/stata/` hold the rows and variables of every regression the model runs. Three
scripts write them, each after the step it reads:

    python 20_CODE/stata_export.py            # draft picks and prospects (after prospect_values.py; ~2 minutes)
    python 20_CODE/stata_export_players.py    # the player model (after the dashboard chain; ~2 minutes)
    python 20_CODE/stata_export_backtest.py   # the back-test and Game Value (after backtest.py and its Game Value runs)

The scripts build no data of their own: each row comes from the functions the model runs, or, for the back-test, from
its own output files. Before it finishes, each script reads its files back from disk, refits every regression from
them, and stops unless the result equals the model's (the tolerance of each check is in its log). The logs,
`stata_export_log.txt`, `stata_export_players_log.txt` and `stata_export_backtest_log.txt`, print the refitted
figures, so a Stata run can be compared with them line by line.

The files are in `30_OUTPUT/`, so they are not committed: they regenerate from the code. **Two files carry PuckPedia's
confidential contract data** (`price_line_skaters.csv` and `price_line_goalies.csv`: each contract's AAV, signing
date and term). Check PuckPedia's terms before giving them to anyone.

| Regression | Files | Section |
|---|---|---|
| The draft pick curve | draft_players.csv | 1 |
| The prospect model (Valuing Prospects Tables 2, 6, 9 and 10) | prospect_seasons.csv, production_seasons.csv | 1 |
| The skater and goalie price lines | price_line_skaters.csv, price_line_goalies.csv | 2 |
| The skater games share and chance of playing, every page | skater_forecast_pairs.csv, forecast_fits.csv | 2 |
| The goalie age term and chance of playing, every page | goalie_age_rows.csv, goalie_play_rows.csv, forecast_fits.csv | 2 |
| The back-test's tests A, B and C (WAR and both Game Value runs) | backtest_club_sides.csv, backtest_assets.csv | 3 |
| Game Value's validation regressions and goals per win | gv_team_games.csv, gv_team_seasons.csv | 4 |

**Not covered, because they are not regressions:** the comparable-player aging curve (a weighted average over
similar players), the 65/35 and 35/65 blends (fixed weights), the qualifying rates for control seasons (shares of
observed decisions), Game Value's penalty value and replacement level (averages), and the expected-goals model behind
Game Value (a machine-learning model, which Stata cannot refit as a regression). The goaltenders' exit-risk table is
still built, but nothing has been priced on it since the chance of playing replaced it (2026-10-21).

**The Stata commands below were written from the model's code but have not been run in Stata** (this desktop's
Stata licence expired on 2026-09-08). They use standard syntax. Every money figure is in millions of dollars at the
2025-26 cap.

The first runs (2026-10-23) passed every check. Each gave back the model's figures:
- "Valuing Prospects" v3.0 Table 2: star values of $18.29M, $18.16M, $16.53M, $9.65M and $2.68M from D+1 to D+5 and
  later.
- Table 9: every coefficient, standard error, row count and R-squared.
- The locked skater and goalie price lines, to 1e-8.
- Every page's games share, chance of playing and goalie age term.
- The back-test's 29 estimates for each of its three runs.
- Game Value's goals per win of 5.903.

# 1. Draft picks and prospects

## The outcome

The outcome is a drafted player's net present value (NPV) to the club that drafted him, from his draft to the end
of club control (CBA Group 3: 27 as of June 30, or seven Accrued Seasons), cut at 2025-26 (`pick_curve.py`):

    NPV = sum over seasons t of (V_t - C_t) / (1.03)^t

- V_t is what his season t delivered, priced on the contract line: the price of his WAR at one year of term
  (skaters: `XNPV1_RATE`, with the defence slope for a defenceman; goaltenders: the goalie line), floored at the
  league minimum. A season under 10 NHL games is scaled by games/82; a season with no NHL game is worth zero and
  costs zero.
- C_t is his cost: the entry-level maximum for his draft class while his entry-level deal runs, then the
  qualifying offer, or the arbitration price once he is eligible for arbitration, whichever is higher.
- Each season's value and cost are in that season's dollars: its share of that season's cap times the 2025-26 cap
  grown at 3% a year. The 3% cap growth and the 3% discount cancel (D11), so the code adds up cap shares and states
  the total at the 2025-26 cap.
- A player whose rights lapsed (his first NHL season was for another club with no trade of him in between, or the
  earlier pick of a player drafted twice) is worth zero to the pick. A negative NPV counts as negative.

**Career NPV** (`career_npv_m`, draft_players.csv) is that sum over every season. **Remaining NPV**
(`remaining_npv_m`, prospect_seasons.csv) is the same sum from the valuation season on, that season included.

## Files

### draft_players.csv: one row per drafted player, 2007-2017

| Column | Meaning |
|---|---|
| `player_id` | draft year x 1000 + overall pick (2017013 = 2017, 13th overall). The cluster for standard errors. |
| `draft_year`, `pick`, `round` | his draft |
| `player_name`, `position`, `team` | from the NHL draft records; `team` is the drafting club |
| `position_ep`, `is_defence` | Elite Prospects' position; `is_defence` = 1 when it starts with D |
| `is_goalie` | 1 for a goaltender |
| `birth_date`, `ep_player_id` | his birthdate; his Elite Prospects id |
| `p_star` | Bacon's star probability for his draft position (`draft_slot_baseline.csv`) |
| `control_ends` | end year of his last season of club control (2021 = the season ending in 2021) |
| `nhl_seasons`, `career_war` | NHL seasons and WAR inside club control |
| `route` | never played, same team, traded first, lapsed (or signed by the drafting club) |
| `career_npv_m` | career NPV, $M at the 2025-26 cap (the outcome above) |
| `excluded_deceased` | 1 for the six players who died before reaching the NHL; left out of every fit |

### prospect_seasons.csv: one row per drafted player and season, D+1 to D+8

D0 is the draft season; D+1 is the season after the draft. Seasons run to 2025-26.

| Column | Meaning |
|---|---|
| `player_id` ... `p_star` | as in draft_players.csv |
| `k`, `dplus` | seasons after the draft season: `k` = 0 for D+1; `dplus` = k + 1 |
| `season`, `season_label` | the valuation season (2018 = 2018-19) |
| `season_group`, `season_group_label` | 1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later |
| `in_control` | 1 when the season is inside his club control |
| `prospect` | 1 when he is a prospect that season and inside club control. A skater is a prospect with no NHL season of 10+ games in the three seasons before; a goaltender with no NHL game in the six before. |
| `sample_star` | rows of the star-value regressions (Section 1): `prospect` = 1, every position |
| `sample_production` | rows of the production and age regressions (Sections 2 and 3): `prospect` = 1, skaters only |
| `remaining_npv_m` | remaining NPV from this season on, $M at the 2025-26 cap (the dependent variable) |
| `nhle82` | production: NHLe points per 82 games, weighted 50/30/20 over the three seasons before this one (most recent first), rescaled over the seasons he has; 0 with no record. Skaters only. |
| `nhle82_sq` | `nhle82` squared (15 points enter as 225) |
| `n_prod_seasons`, `no_record` | how many of the three seasons have a record; 1 when none does |
| `age`, `age_m18` | his age on September 15 of the valuation season; that age less 18 |
| `prod_x_age_m18` | `nhle82` x (`age` - 18): the age term as the document writes it |
| `years_past_elig`, `prod_x_years_past_elig` | `age` - `k` - 18, and `nhle82` times it: the age term as `prospect_values.py` stores it |
| `prod_x_defence` | `nhle82` x `is_defence`: the defenceman term (in the model since 2026-10-24) |

The two age terms give the same fitted values and the same age coefficient. Within one season group every row has
the same `k`, so the difference between them is `k` x production, and production's coefficient absorbs it:
production's coefficient with `prod_x_age_m18` equals its coefficient with `prod_x_years_past_elig` minus `k` times
the age coefficient. The document uses `prod_x_age_m18`.

### production_seasons.csv: one row per Elite Prospects season line, 2007-2017 skater draftees

| Column | Meaning |
|---|---|
| `player_id`, `ep_player_id` | as above |
| `season_start`, `season_ep` | the season (2015 = 2015-16) and Elite Prospects' label |
| `league`, `gp`, `points` | one line of his Elite Prospects record (one team, league and season) |
| `nhle_factor` | Bacon's NHLe factor for that league and season (`nhle_temporal.csv`); blank where Bacon has none |
| `factor_imputed_2012` | 1 where 2012-13's factor is the mean of the league's 2011-12 and 2013-14 factors |
| `nhle_points` | `points` x `nhle_factor` |

Five players were drafted twice (Teigan Zahn, Alan Quine, Brenden Kichton, Lukas Sutter, Conner Bleackley). Each has
one Elite Prospects record, listed under both of his `player_id`s, so add up by `player_id`, not by `ep_player_id`.

To rebuild `nhle82`: keep the lines with a factor; for each `player_id` and season, add up `gp` and `nhle_points`; keep
seasons of 10+ games (counting only games in leagues with a factor); the season's rate is nhle_points / gp x 82.
`nhle82` for valuation season y weights the rates of y-1, y-2 and y-3 by 0.5, 0.3 and 0.2, over the seasons that
exist, divided by the sum of the weights used.

## The regressions

Every regression is ordinary least squares through zero (no constant). With more than one season, it is one
regression on every season's rows, with each term multiplied by an indicator for each season group (a full set of
interaction terms), so each season gets its own coefficients. Standard errors are clustered by player
(`player_id`), since one player appears in several seasons. The pick curve has one row per player, so its errors
are robust (heteroskedasticity-consistent, Stata's `vce(robust)`).

R-squared: a regression without a constant reports the uncentered R-squared (the share of the sum of squared
outcomes, not of the variance about the mean). The document's R-squared is each season's own regression run alone,
uncentered.

Below, 1[D+n] is 1 for a row in that season group and 0 otherwise; S is `p_star`, P is `nhle82`, A is `age`.

In the commands, `ibn.` gives one indicator per season with no base season left out, and `noconstant` matches the
through-zero form.

### 1. The pick curve (Valuing Draft Picks; the D+1 star value in Valuing Prospects)

    career NPV = a x S + error

    import delimited using "draft_players.csv", clear
    regress career_npv_m p_star if excluded_deceased == 0, noconstant vce(robust)

### 2. The star value by season (Valuing Prospects, Table 2)

    remaining NPV = sum over n of a_n x S x 1[D+n] + error,    n = 1, 2, 3, 4, and 5 and later

    import delimited using "prospect_seasons.csv", clear
    regress remaining_npv_m ibn.season_group#c.p_star if sample_star == 1, noconstant vce(cluster player_id)

### 3. Draft position and linear and squared production, before age (Table 6)

    remaining NPV = sum over n of (a_n x S + b_n x P + c_n x P^2) x 1[D+n] + error

    regress remaining_npv_m ibn.season_group#c.(p_star nhle82 nhle82_sq) if sample_production == 1, ///
        noconstant vce(cluster player_id)

### 4. The adopted model (Table 9)

Draft position in D+1 to D+3, the age term in D+1 to D+4, and production for defencemen (D = `is_defence`) in every
season (added 2026-10-24):

    remaining NPV = sum over n = 1..3 of a_n x S x 1[D+n]
                  + sum over all n of (b_n x P + c_n x P^2 + f_n x D x P) x 1[D+n]
                  + sum over n = 1..4 of e_n x P x (A - 18) x 1[D+n] + error

    generate s_early  = p_star * (season_group <= 3)
    generate age_term = prod_x_age_m18 * (season_group <= 4)
    regress remaining_npv_m ibn.season_group#c.(s_early nhle82 nhle82_sq prod_x_defence age_term) ///
        if sample_production == 1, noconstant vce(cluster player_id)

Stata lists the zero columns (`s_early` from D+4, `age_term` from D+5 on) as omitted; they are not estimated.
The defenceman terms together (five coefficients):

    testparm ibn.season_group#c.prod_x_defence

Each season's own R-squared, for example D+2:

    regress remaining_npv_m p_star nhle82 nhle82_sq prod_x_defence prod_x_age_m18 ///
        if sample_production == 1 & season_group == 2, noconstant vce(robust)

### 5. The D+2 build-up (Table 10, Appendix B)

Each column adds one term to the regression in section 3 or 4, fitted on every season at once. Its D+2
coefficients are the table's column; its standard errors are clustered by player across all seasons:

    regress remaining_npv_m ibn.season_group#c.p_star if sample_production == 1, noconstant vce(cluster player_id)
    regress remaining_npv_m ibn.season_group#c.(p_star nhle82) if sample_production == 1, noconstant vce(cluster player_id)
    regress remaining_npv_m ibn.season_group#c.(p_star nhle82 nhle82_sq) if sample_production == 1, noconstant vce(cluster player_id)

Column (4) adds the age term. The adopted model (section 4) adds production for defencemen to it.

### 6. A defenceman dummy interacted with production

Since 2026-10-24 the adopted model includes it (section 4; `25_TESTS/defence_terms_look.py`: the five terms jointly
p = 0.033). The form below is the earlier test, on draft position and linear production only, with one production
coefficient for forwards and another for defencemen, in each season (D is `is_defence`):

    remaining NPV = sum over n of (a_n x S + f_n x P x (1 - D) + d_n x P x D) x 1[D+n] + error

    regress remaining_npv_m ibn.season_group#c.p_star ibn.season_group#ibn.is_defence#c.nhle82 ///
        if sample_production == 1, noconstant vce(cluster player_id)

The same model written as production plus a defenceman dummy interacted with production has b_n = f_n and an
interaction coefficient d_n - f_n; testing that coefficient against zero tests whether defencemen need their own
rate.

### 7. The age forms tested (supervisor meeting, 2026-10-23)

The meeting raised two alternatives to production x (age - 18); both were tested on 2026-10-23
(`25_TESTS/prospect_age_discount_look.py`) and production x (age - 18) was kept (Thomas, 2026-10-24). The data for
both is in the file:

- Age on its own, moving the whole value line up or down: replace `age_term` with `age_m18` (by season group).
- Age-adjusted production and its square: `prod_x_age_m18` and either its square, or `nhle82_sq` x `age_m18`.
  These are two different variables, and they mean different things.

# 2. The player model

## The price lines (price_line_skaters.csv, price_line_goalies.csv)

One row per contract in each line's sample:
- **Skaters (2,336 contracts):** standard-level UFA and RFA contracts whose first season is 2018-19 to 2025-26, with a
  10+ game season in one of the two seasons before.
- **Goaltenders (333):** standard-level contracts whose first season is 2015-16 to 2025-26, with a season in the year
  before the signing.

Each contract's forecast is dated at its signing: it is the forecast from the valuation page whose 1 July information
matches what was known on the signing date (`signing_page`), `seasons_ahead` seasons before the contract's first
season.

| Column | Meaning |
|---|---|
| `contract_id`, `pp_player_id`, `player_name`, `player_key` | PuckPedia's ids; the name; the model's player key |
| `position_group`, `is_d` | skaters: F or D; `is_d` = 1 for a defenceman |
| `signing_status`, `signing_date`, `first_season`, `term_years` | the contract (first season 2018 = 2018-19) |
| `aav`, `cap_ceiling` | average annual value; the cap ceiling of the first season |
| `cap_share` | AAV / cap ceiling: the dependent variable |
| `min_share` | the league minimum salary / cap ceiling, the same season: the censoring point |
| `at_minimum` | 1 when `cap_share` is at the minimum (censored) |
| `xwar` | the regressor. Skaters: the forecast's WAR if he plays, in the contract's first season, dated at the signing. Goaltenders: the track-record forecast (35% of his 50/30/20 trailing WAR plus 65% of the league average of 2.189), dated at the signing, before the age term. |
| `xwar_start_dated` | skaters only: the same forecast dated at the first season (the price line script's comparison) |

The line is a regression censored at the league minimum (a tobit). A contract at the minimum says only that his
market price was at or below it.

    cap share = alpha + (beta + beta_D x D) x xwar + gamma x term + error,  observed as max(that, min_share)

    import delimited using "price_line_skaters.csv", clear
    tobit cap_share c.xwar c.xwar#c.is_d term_years, ll(min_share)      // the term-in line (XNPV1_RATE)
    tobit cap_share c.xwar c.xwar#c.is_d, ll(min_share)                 // the term-free line (XNPV1_RATE_TERM_FREE)

    import delimited using "price_line_goalies.csv", clear
    tobit cap_share xwar term_years, ll(min_share)                      // GOALIE_RATE
    tobit cap_share xwar, ll(min_share)                                 // GOALIE_RATE_TERM_FREE

The model fits the same likelihood in percentage points of the cap (cap share x 100) and reports it in shares. The
coefficients are the same either way. If Stata's optimiser struggles with shares this small, run it on
`100 * cap_share` and `100 * min_share` and divide the coefficients by 100.

## The forecast pieces, every page

Each piece is refitted on every valuation page P (1 July of the season starting in year P; pages 2010 to 2026), on
the rows whose outcome season is before P. The CSVs hold every row any page uses, so a page's fit is the condition
`season < P`. `forecast_fits.csv` lists the model's own coefficients for each regression, page and season ahead
(`b0` is the constant; `columns` names the variable each `b` belongs to, in order).

### skater_forecast_pairs.csv: one row per skater, valuation season and season ahead (0 to 12)

The inputs are from the seasons before the valuation season `page_season` (his 10+ game seasons, weighted 50/30/20,
most recent first, rescaled over those he has). The outcome is in `season` = `page_season` + `h`.

| Column | Meaning |
|---|---|
| `career_key`, `player_key`, `position`, `is_d` | who he is |
| `page_season`, `h`, `season` | valuation season; seasons ahead (0 = the valuation season); outcome season |
| `tr_gp_share` | his trailing share of his team's games, 50/30/20 |
| `exp_seasons` | seasons since his NHL debut, counted at his most recent counted season (0 in his debut season) |
| `age_c`, `age_c2` | his age in the valuation season less 27.22, and its square |
| `tw_war` | his trailing WAR total, 50/30/20 |
| `y_gp_share` | the games share's outcome: his share of his team's games in `season` (blank when he played no NHL game) |
| `p_age_c` | the chance of playing's age: his age in the outcome season less 27.22 |
| `under_contract` | 1 when a contract signed by 1 July of `page_season` covers `season` |
| `contract_unknown` | 1 for outcome seasons before 2018-19, which the contract export cannot see |
| `y_gp`, `y_played` | NHL games in `season`; the chance of playing's outcome, 1 for one game or more |

The games share, page P, season ahead H (a straight-line fit with a constant):

    import delimited using "skater_forecast_pairs.csv", clear
    regress y_gp_share tr_gp_share exp_seasons age_c tw_war age_c2 if h == H & season < P

The chance of playing, page P, season ahead H (a logit):

    logit y_played p_age_c tw_war tr_gp_share is_d under_contract contract_unknown if h == H & season < P

On some pages a column cannot carry a coefficient: on early pages the contract columns are nearly constant, or they
duplicate each other. The model then drops that column, and `forecast_fits.csv` lists the columns it kept; use those.
The model's logit is very lightly penalised (an L1 penalty of 0.0001), so a coefficient cannot run off to infinity
where a contract column almost perfectly predicts playing. Stata's plain `logit` differs from it by at most 0.00018
in any coefficient on any page (the export log).

### goalie_age_rows.csv: one row per goaltender-season of 20+ games with a trailing value and an age

| Column | Meaning |
|---|---|
| `player_key`, `season`, `gp`, `war` | the goaltender-season (WAR with 2019-20 and 2020-21 scaled to 82 games) |
| `trailing_war` | his 50/30/20 trailing WAR (62.5/37.5 with two seasons; the most recent alone with one) |
| `pulled` | 0.35 x `trailing_war` + 0.65 x 2.189 (the league average): the track-record forecast |
| `war_less_pulled` | `war` - `pulled`: the age term's outcome |
| `age`, `age_c` | his age on September 15 of `season`; less 27.22 |

    import delimited using "goalie_age_rows.csv", clear
    regress war_less_pulled age_c if season < P

### goalie_play_rows.csv: one row per goaltender, valuation season and season ahead

A goaltender enters at valuation season `page_season` when he has a season in the year before it.

| Column | Meaning |
|---|---|
| `player_key`, `page_season`, `h`, `season` | as in skater_forecast_pairs.csv |
| `age_c` | his age in the outcome season less 27.22 |
| `pulled` | his track-record forecast at `page_season` (as above) |
| `gp_share_last` | his games in the season before `page_season`, divided by 82 |
| `played` | 1 when he played one NHL game or more in `season` |

    import delimited using "goalie_play_rows.csv", clear
    logit played age_c pulled gp_share_last if h == H & season < P

A season ahead is fitted only with 200 rows or more and both outcomes present. Page 2010 has none, so no goalie
chance of playing is fitted there (as in the model).

# 3. The back-test

From `backtest.py`'s own outputs. The protocol is `40_DOCS/Backtest_Protocol.md`.

### backtest_club_sides.csv: one row per club side of each trade

| Column | Meaning |
|---|---|
| `trade_id`, `trade_date`, `valuation_page`, `club`, `n_clubs` | the trade and the club |
| `during_regular_season`, `has_conditional_pick` | 1 for an in-season trade; 1 when the trade has a conditional pick |
| `complete` | 1 when every asset in the trade has an outcome: the tests' sample |
| `forecast_net_m` | the forecast's net for the club: what it received less what it gave ($M) |
| `outcome_net_m`, `realised_net_m` | the outcome's net (realised through 2025-26 plus the rest revalued at 2026-27); realised only |
| `outcome_net_m_gv_adj`, `outcome_net_m_gv_raw` (and `realised_...`) | the same on Game Value (the protocol's check) |
| `recv_*_m`, `gave_*_m`, `received_m`, `given_m`, `miss_m`, `out_wins` | the forecast by asset class; outcome less forecast; wins delivered |
| `g_futures`, `g_buyer`, `g_star`, `g_retained`, `g_nothing_back`, `g_clause`, `standing` | the protocol's groups C1 to C6 |

Test A's slope is a regression through zero of the outcome net on the forecast net (1 means the forecast's gaps come
true):

    import delimited using "backtest_club_sides.csv", clear
    regress outcome_net_m forecast_net_m if complete == 1, noconstant
    correlate forecast_net_m outcome_net_m if complete == 1

The model's intervals and p-values come from 2,000 resamples of trades (a trade's club sides move together; seed
20261020). Stata can resample the same way, but its draws differ, so its intervals will be close to the model's, not
equal:

    bootstrap _b, reps(2000) seed(20261020) cluster(trade_id): regress outcome_net_m forecast_net_m if complete == 1, noconstant

Test C is each group's mean, for example C1: `mean forecast_net_m outcome_net_m miss_m if complete == 1 & g_futures == 1`.

### backtest_assets.csv: one row per traded asset (test B)

The columns are `asset_class` (players, picks, prospects, retained), `forecast_m`, `outcome_m` and `realised_m` (with
the Game Value runs' outcomes beside them), and `complete_trade` (1 when the asset's trade is in the tests' sample).
Test B is the mean of outcome less forecast in each class:

    import delimited using "backtest_assets.csv", clear
    generate miss = outcome_m - forecast_m
    mean miss if complete_trade == 1, over(asset_class)

# 4. Game Value

From the game-log database (regular-season games, 2017-18 to 2025-26), with `metric_assembly.py`'s own queries. A
shootout winner's extra goal is taken off (in-play goal differential).

| File | Columns |
|---|---|
| gv_team_games.csv | `game_id`, `season`, `team`, `game_value_sum` (the team's skaters' Game Value that game), `goal_diff_in_play` |
| gv_team_seasons.csv | `season`, `team`, `wins`, `goal_diff_in_play`, `game_value_sum`, `gv_goal_diff` (the goal differential of the games with Game Value) |

    import delimited using "gv_team_games.csv", clear
    regress goal_diff_in_play game_value_sum                  // team-game validation: slope 0.3595, R-squared 0.0332

    import delimited using "gv_team_seasons.csv", clear
    regress gv_goal_diff game_value_sum                       // team-season validation: slope 1.1321, R-squared 0.5833
    regress wins goal_diff_in_play                            // goals per win = 1 / slope = 5.903 (pooled)
    statsby _b, by(season): regress wins goal_diff_in_play    // each season's goals per win
