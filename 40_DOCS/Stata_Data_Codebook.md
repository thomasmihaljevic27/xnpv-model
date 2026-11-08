# Running the model's regressions in Stata

This guide covers every regression the xNPV model runs, across the three asset classes (draft picks, prospects and
players), plus the back-test and Game Value. It also covers every significance test the documents report. Each one
can be run by hand in Stata, step by step. There are three parts:

1. **One command builds everything**, before you open Stata (below).
2. **One command in Stata loads every data file** (Step 0).
3. **A do-file runs each regression in order.** Each command is followed by the figure Stata should print.

The do-file is `xnpv_walkthrough.do`. Its step numbers are the ones in this guide. "Valuing Players" below is
"Valuing Players, Draft Picks, and Prospects" v4.3; "Valuing Prospects" is v4.3. Every money figure is in millions of
dollars at the 2025-26 cap ($95.5M). D+1 is the season after the draft.

## Before Stata: build the data (one command)

From the repo root, on the laptop:

    python 20_CODE/stata_refresh.py

It takes about two minutes and writes everything into `30_OUTPUT/stata/`:

- **13 CSV files:** every row and variable of every regression, plus the variables the tests use. Nothing has to be
  generated in Stata.
- **`xnpv_load.do`:** loads all 13 files.
- **`xnpv_walkthrough.do`:** the steps. Each one has the figure it should print, computed from these CSVs when the
  command ran.

The command runs three exports in order (`stata_export.py`, `stata_export_players.py`, `stata_export_backtest.py`). Each
export refits every regression from the CSVs it has just written and stops if any result differs from the model's. A run
that finishes therefore means the CSVs reproduce the model.

**Run it after the model is current.** That means after the dashboard chain (`dashboard_refresh.py`), the trade chain
(`trade_refresh.py`) and the back-test with its two Game Value runs (`backtest.py`). It does not run any of those itself.

**Two files carry PuckPedia's confidential contract data:** `price_line_skaters.csv` and `price_line_goalies.csv`. Each
holds every contract's AAV, signing date and term. Check PuckPedia's terms before giving them to anyone.

## In Stata

1. **File > Change Working Directory**, and choose `30_OUTPUT/stata/`.
2. Open `xnpv_walkthrough.do` in the Do-file Editor.
3. **Step 0:** run its first line, `do xnpv_load.do`. This loads all 13 files, each into its own *frame*: a dataset
   held in memory beside the others (Stata 16 or later). Each part of the do-file begins with `frame change`, which
   makes that part's dataset the active one.
4. Run one step at a time: select its lines and press Ctrl+D. Compare what Stata prints with the "Should print" comment
   under each command.

Differences in the last digit shown can come from rounding or from the optimiser, in a tobit or a logit. Anything larger
is a real difference. **These commands were written from the model's code and have not yet been run in Stata.**

## Reading the commands

Five conventions recur throughout:

- **`noconstant`:** the regression goes through zero, with no intercept. The pick curve and the prospect model are
  fitted this way. Without a constant, Stata's R-squared is measured from zero. It is the share of the sum of squared
  outcomes the regression explains, not the share of their variance.
- **`vce(robust)` and `vce(cluster id)`:** the standard errors.
  - Robust errors allow the size of the misses to differ from row to row. They are used where each player appears once
    (the pick curve).
  - Clustered errors also allow one player's misses to be related across his rows. They are used where a player
    appears several times (the prospect seasons, the forecast's player-seasons, the price line's contracts).
- **`ibn.season_group#c.x`:** gives x its own coefficient in each season group (D+1, D+2, D+3, D+4, and D+5 and later).
  `ibn.season_group` is a set of five dummy variables, one per group, and exactly one of them is 1 on each row.
  Interacting them with x gives x a separate, estimated coefficient in each group, all within one regression.
- **`test` and `testparm`:** test that coefficients are zero, or equal to each other. After `regress` Stata reports
  an F statistic. After `tobit` or `logit` it reports a chi-squared, and `lrtest` compares the log-likelihoods of two
  nested fits.
- **p-values against the documents:** the documents report chi-squared versions of the same Wald tests. Stata's F
  version of a test can differ from the document's p-value in the third or fourth decimal. The do-file's "Should print"
  figures are Stata's.

## The steps

| Step | What it asks | Where it is reported |
|---|---|---|
| **Part 1: draft picks** | outcome: career NPV, one row per drafted player 2007-2017 | |
| 1 | The pick curve: what a 100% star chance is worth (the star value) | Valuing Players, Section 6 |
| 2 | The same, without the 2015 and 2016 drafts (the sensitivity) | Section 6 |
| 3 | Each term the curve leaves out, added in turn: an intercept, one for each draft, draft position, the NHL-player chance | Section 6, "The star value, with each term added" |
| 4 | Whether the star value differs by draft, and whether it trends over time | Section 6, "One star value for every draft" |
| 5 | A separate star value for defencemen (tested, not adopted) | Section 6; Valuing Prospects, Section 4 |
| 6 | The other shapes for the curve (compared on held-out drafts) | Section 6, "Six shapes of value" |
| **Part 2: prospects** | outcome: remaining NPV in each season after the draft | |
| 7 | The star value in each season after the draft | Valuing Prospects, Table 1 (Valuing Players, Section 7) |
| 8 | Whether it fades by one value, a straight line, or the same percentage | Table 2 |
| 9 | Production: linear, squared, and draft position from D+4 on | Table 3 |
| 10 | Age as a flat amount, or as a discount on production | Table 5 |
| 11 | Defencemen: production, its square, draft position | Table 6 |
| 12 | The adopted prospect model, every coefficient | Table 7 |
| 13 | Why linear production stays in the model | Valuing Prospects, "Why linear production stays" |
| **Part 3: players** | | |
| 14 | The skater price line: cap hit on forecast WAR, defence and term | Valuing Players, Section 3, "The price line, built up" |
| 15 | The price line built up, with each step's likelihood-ratio test | the same table |
| 16 | Seven other forms of the price line, each against the adopted one | Section 3, "Other forms of the price line" |
| 17 | Pricing on the forecast over the whole term (tested, not adopted) | Section 3, the first season against the term average |
| 18 | The goaltender price line | Section 4, "Goaltenders" |
| 19 | The skater games share on the 2025-26 page: built up, each season ahead, and the dropped defenceman term | Section 2 and Appendix A |
| 20 | The skater chance of playing: built up, each season ahead, and its two dropped terms | Section 2 and Appendix A |
| 21 | The goaltender age term | Section 4, "Goaltenders" |
| 22 | The goaltender chance of playing, with its dropped age squared | Section 4, "Goaltenders" |
| **Part 4: the back-test** | each club's side of each trade: what it received less what it gave up | Backtest_Protocol.md |
| 23 | Test A: do the forecast's verdicts come true? (slope, correlation, share of favoured clubs ahead) | |
| 24 | Test A on realised seasons only, and without conditional picks | |
| 25 | Test A for in-season and off-season trades | |
| 26 | Test B: outcome less forecast per asset, by class | |
| 27 | Test C: the protocol's groups (the star group is left out, amendment 5) | |
| 28 | Test A with Game Value as the outcome, adjusted and raw | |
| 29 | Test A's interval, by resampling trades | |
| **Part 5: Game Value** | | |
| 30 | Goal differential on Game Value, team by game | |
| 31 | The same, team by season | |
| 32 | Goals per win, pooled and each season | |

**Steps 19 to 22 are fitted on one valuation page.** The model refits the games share, the chance of playing and the
goaltender age term on every page from 2010-11 to 2026-27. Each fit uses only seasons before that page, so on page P
the rows are the ones with `season < P`. The do-file fits the 2025-26 page, which is the page the documents' tables
show. Change 2025 to any other page to fit that page. `forecast_fits.csv` (frame `fits`) lists the model's own
coefficients for every page and season ahead, to compare with.

**Not in Stata, and why:**

- **Held-out comparisons.** Each draft, contract group or page is predicted from a fit on the others, then the errors
  are compared. The documents report these only where a significance test is inconclusive, and each is a loop of
  refits. The scripts that run them are named in the documents.
- **The comparable-player aging curve.** It is a weighted average over similar players, not a regression.
- **The 65/35 and 35/65 blends and the 50/30/20 weights.** These are fixed weights.
- **The expected-goals model behind Game Value.** It is a machine-learning model.
- **The goaltenders' season-to-season correlations.** These are correlations, and their data is not exported.

## Why the do-file needs no `generate` lines

Every derived variable a test uses is already a column, built in Python and checked there. Each one is listed in the
file tables below. The pick curve's defenceman test uses the NHL draft record's position (`is_d_draft`). The prospect
model uses Elite Prospects' position (`is_defence`), as the model does.

---

# The outcomes

**Career NPV** (`career_npv_m`, draft_players.csv) is a drafted player's net present value to the club that drafted
him. It runs from his draft to the end of club control (CBA Group 3: age 27 as of June 30, or seven Accrued Seasons),
cut at 2025-26 (`pick_curve.py`):

    NPV = sum over seasons t of (V_t - C_t) / (1.03)^t

- **V_t** is what his season t delivered, priced on the contract line. Skaters' WAR is priced on `XNPV1_RATE` at one
  year of term, with the defence slope for a defenceman; goaltenders' on the goalie line. The price is floored at the
  league minimum. A season under 10 NHL games is scaled by games / 82. A season with no NHL game is worth zero and costs
  zero.
- **C_t** is his cost. It is the entry-level maximum for his draft class while his entry-level deal runs. After that it
  is the qualifying offer, or the arbitration price once he is eligible for arbitration, whichever is higher.
- **Each season is in that season's dollars:** its share of that season's cap, times the 2025-26 cap grown at 3% a
  year. The 3% cap growth and the 3% discount cancel (D11), so the code adds up cap shares and states the total at the
  2025-26 cap.
- **Lapsed rights:** a player whose rights lapsed is worth zero to the pick. That is the case when his first NHL season
  was for another club with no trade of him in between, or when it is the earlier pick of a player drafted twice.
- **A negative NPV counts as negative.**

**Remaining NPV** (`remaining_npv_m`, prospect_seasons.csv) is the same sum from the valuation season on, that season
included.

**The price lines' outcome** (`cap_m`) is the contract's cap share times the 2025-26 cap, in $M. Its floor is the
league minimum's share of the same season's cap, times the same (`min_m`). A tobit is censored at that floor: a contract
at the minimum says only that his market price was at or below it.

---

# The data files

## draft_players.csv (frame `picks`): one row per drafted player, 2007-2017

| Column | Meaning |
|---|---|
| `player_id` | draft year x 1000 + overall pick (2017013 = 2017, 13th overall) |
| `draft_year`, `pick`, `round` | his draft |
| `player_name`, `position`, `team` | from the NHL draft records; `team` is the drafting club |
| `position_ep`, `is_defence` | Elite Prospects' position; `is_defence` = 1 when it starts with D |
| `is_goalie` | 1 for a goaltender |
| `birth_date`, `ep_player_id` | his birthdate; his Elite Prospects id |
| `p_star` | Bacon's star probability for his draft position (`draft_slot_baseline.csv`) |
| `p_nhler` | Bacon's NHL-player probability for his draft position (step 3d) |
| `log_pick`, `log_pick_sq` | the log of the overall pick, and its square (step 6) |
| `p_star_sq` | `p_star` squared (step 6) |
| `is_d_draft`, `p_star_x_d_draft` | 1 when the draft record lists him at D; `p_star` x that (step 5) |
| `p_star_trend` | `p_star` x (draft year - 2012): a star value that changes by draft (step 4) |
| `control_ends` | end year of his last season of club control (2021 = the season ending in 2021) |
| `nhl_seasons`, `career_war` | NHL seasons and WAR inside club control |
| `route` | never played, same team, traded first, lapsed (or signed by the drafting club) |
| `career_npv_m` | career NPV, $M (the outcome) |
| `excluded_deceased` | 1 for the six players who died before reaching the NHL; left out of every fit |

## prospect_seasons.csv (frame `prospects`): one row per drafted player and season, D+1 to D+8

D0 is the draft season, and D+1 the season after it. Seasons run to 2025-26.

| Column | Meaning |
|---|---|
| `player_id` ... `p_star` | as in draft_players.csv; `player_id` is the cluster |
| `k`, `dplus` | seasons after the draft season: `k` = 0 for D+1; `dplus` = k + 1 |
| `season`, `season_label` | the valuation season (2018 = 2018-19) |
| `season_group`, `season_group_label` | 1 = D+1, 2 = D+2, 3 = D+3, 4 = D+4, 5 = D+5 and later |
| `in_control` | 1 when the season is inside his club control |
| `prospect` | 1 when he is a prospect that season and inside club control. A skater is a prospect with no NHL season of 10+ games in the three before; a goaltender with no NHL game in the six before. |
| `sample_star` | the rows of steps 7 and 8: `prospect` = 1, every position |
| `sample_production` | the rows of steps 9 to 13: `prospect` = 1, skaters only |
| `remaining_npv_m` | remaining NPV from this season on, $M (the outcome) |
| `nhle82` | production: NHLe points per 82 games, weighted 50/30/20 over the three seasons before this one (most recent first), rescaled over the seasons he has; 0 with no record |
| `nhle82_sq` | `nhle82` squared (15 points enter as 225) |
| `n_prod_seasons`, `no_record` | how many of the three seasons have a record; 1 when none does |
| `age`, `age_m18` | his age on September 15 of the valuation season; that age less 18 |
| `prod_x_age_m18` | `nhle82` x (`age` - 18): the age term, in every season |
| `s_early` | `p_star` in D+1 to D+3, zero later: draft position where the model keeps it |
| `age_term` | `prod_x_age_m18` in D+1 to D+4, zero later: the age term where the model keeps it |
| `flat_term` | `age_m18` in D+1 to D+4: age on its own, the rejected alternative (step 10) |
| `prod_x_defence` | `nhle82` x `is_defence`: the defenceman term (in the model since 2026-10-24) |
| `prod_sq_x_defence`, `s_early_x_defence` | `nhle82_sq` and `s_early` times `is_defence` (step 11) |
| `age_term_19`, `age_term_20` | `nhle82` x (`age` - 19), and (`age` - 20), in D+1 to D+4 (step 13) |
| `years_past_elig`, `prod_x_years_past_elig` | `age` - `k` - 18, and `nhle82` times it: the age term as `prospect_values.py` stores it |

`prod_x_age_m18` and `prod_x_years_past_elig` give the same fitted values and the same age coefficient. Within one
season group every row has the same `k`, so the two differ by `k` x production, and production's coefficient absorbs
the difference. The documents use age less 18.

## production_seasons.csv (frame `production`): one row per Elite Prospects season line, 2007-2017 skater draftees

| Column | Meaning |
|---|---|
| `player_id`, `ep_player_id` | as above |
| `season_start`, `season_ep` | the season (2015 = 2015-16) and Elite Prospects' label |
| `league`, `gp`, `points` | one line of his record (one team, league and season) |
| `nhle_factor` | Bacon's NHLe factor for that league and season (`nhle_temporal.csv`); blank where Bacon has none |
| `factor_imputed_2012` | 1 where 2012-13's factor is the mean of the league's 2011-12 and 2013-14 factors |
| `nhle_points` | `points` x `nhle_factor` |

This file is how `nhle82` is built:

1. Keep the lines with a factor.
2. For each `player_id` and season, add up `gp` and `nhle_points`.
3. Keep seasons of 10 or more games, counting only games in leagues with a factor.
4. Each season's rate is `nhle_points / gp x 82`.
5. `nhle82` for valuation season y weights the rates of y-1, y-2 and y-3 by 0.5, 0.3 and 0.2, over the seasons that
   exist, divided by the sum of the weights used.

Five players were drafted twice, so add up by `player_id`, not by `ep_player_id`.

## price_line_skaters.csv (frame `skater_lines`): one row per contract in the price line's sample (2,336)

The sample is standard-level UFA and RFA contracts whose first season is 2018-19 to 2025-26, with a 10+ game season in
one of the two seasons before. Each contract's forecast is dated at its signing. It comes from the valuation page whose
July 1 information matches what was known on the signing date (`signing_page`), `seasons_ahead` seasons before the
contract's first season.

| Column | Meaning |
|---|---|
| `contract_id`, `pp_player_id`, `player_name`, `player_key` | PuckPedia's ids; the name; the model's player key |
| `player_num` | one number per player: the cluster (step 14) |
| `position_group`, `is_d` | F or D; `is_d` = 1 for a defenceman |
| `signing_status`, `signing_date`, `first_season`, `term_years` | the contract (first season 2018 = 2018-19) |
| `aav`, `cap_ceiling`, `cap_share` | average annual value; the cap ceiling of the first season; AAV / cap |
| `cap_m`, `min_m` | `cap_share` and the league minimum's share, times the 2025-26 cap, $M: the outcome and its floor |
| `min_share`, `at_minimum` | the league minimum's share of the cap; 1 when the contract is at it |
| `xwar` | the forecast's WAR if he plays, in the contract's first season, dated at the signing |
| `xwar_start_dated` | the same forecast dated at the first season (the price line script's comparison) |
| `is_rfa`, `start_2022_on` | 1 for an RFA signing; 1 for a first season from 2022-23 (step 16) |
| `xwar_over1` | forecast WAR above one win, zero below (the bend, step 16) |
| `term_x_0to1`, `term_x_1to2`, `term_x_2plus` | years of term for a forecast of 0 to 1, 1 to 2, 2 or more wins (step 16) |
| `term_x_0plus` | years of term for a forecast of 0 or more (the one step at replacement level, step 16) |
| `xwar_term_avg`, `xwar_term_avg_exp` | the forecast of WAR if he plays averaged over the contract's term; the same times the chance of playing (step 17) |

`xwar_term_avg` and `xwar_term_avg_exp` come from `25_TESTS/term_average_price_line.py`'s rows. They are filled only
when that run used today's forecast; otherwise they are blank, and step 17 says to re-run it (about 20 minutes).

## price_line_goalies.csv (frame `goalie_lines`): one row per goaltender contract (333)

These are standard-level contracts whose first season is 2015-16 to 2025-26, with a season in the year before the
signing. The columns are as for skaters. `xwar` is the track-record forecast: 35% of his 50/30/20 trailing WAR plus
65% of the league average of 2.189, dated at the signing, before the age term.

## skater_forecast_pairs.csv (frame `skater_pairs`): one row per skater, valuation season and season ahead (0 to 12)

The inputs come from the seasons before the valuation season `page_season`: his 10+ game seasons, weighted 50/30/20,
most recent first, rescaled over those he has. The outcome is in `season` = `page_season` + `h`.

| Column | Meaning |
|---|---|
| `career_key`, `player_key`, `position`, `is_d` | who he is |
| `career_num` | one number per career: the cluster |
| `page_season`, `h`, `season` | valuation season; seasons ahead (0 = the valuation season); outcome season |
| `tr_gp_share` | his trailing share of his team's games, 50/30/20 |
| `exp_seasons` | seasons since his NHL debut, counted at his most recent counted season |
| `age_c`, `age_c2` | his age in the valuation season less 27.22, and its square |
| `tw_war` | his trailing WAR total, 50/30/20 |
| `y_gp_share` | the games share's outcome: his share of his team's games in `season` (blank when he played none) |
| `p_age_c`, `p_age_c2` | the chance of playing's age: his age in the outcome season less 27.22; its square (dropped, step 20) |
| `under_contract` | 1 when a contract signed by July 1 of `page_season` covers `season` |
| `contract_unknown` | 1 for outcome seasons before 2018-19, which the contract export cannot see |
| `y_gp`, `y_played` | NHL games in `season`; the chance of playing's outcome, 1 for one game or more |

On early pages a column may not be able to carry a coefficient. The model then drops it, and `forecast_fits.csv`
lists the columns it kept. On the 2025-26 page every column is kept. The model's chance-of-playing logit is very lightly
penalised (an L1 penalty of 0.0001), which keeps a coefficient finite where contract status almost perfectly predicts
playing. Stata's plain `logit` differs from it by at most 0.0002 in any coefficient on any page.

## goalie_age_rows.csv (frame `goalie_age`): one row per goaltender-season of 20+ games with a trailing value and an age

| Column | Meaning |
|---|---|
| `player_key`, `season`, `gp`, `war` | the goaltender-season (2019-20 and 2020-21 WAR scaled to 82 games) |
| `trailing_war` | his 50/30/20 trailing WAR (62.5/37.5 with two seasons; the most recent alone with one) |
| `pulled` | 0.35 x `trailing_war` + 0.65 x 2.189: the track-record forecast |
| `war_less_pulled` | `war` - `pulled`: the age term's outcome |
| `age`, `age_c` | his age on September 15 of `season`; less 27.22 |

## goalie_play_rows.csv (frame `goalie_play`): one row per goaltender, valuation season and season ahead

A goaltender enters at valuation season `page_season` when he has a season in the year before it. A season ahead is
fitted only with 200 rows or more and both outcomes present.

| Column | Meaning |
|---|---|
| `player_key`, `page_season`, `h`, `season` | as for skaters |
| `age_c`, `age_c2` | his age in the outcome season less 27.22; its square (dropped, step 22) |
| `pulled` | his track-record forecast at `page_season` |
| `gp_share_last` | his games in the season before `page_season`, divided by 82 |
| `played` | 1 when he played one NHL game or more in `season` |

## forecast_fits.csv (frame `fits`)

This file holds the model's own coefficients for each regression, page and season ahead. `b0` is the constant, and
`columns` names the variable each `b` belongs to, in order.

## backtest_club_sides.csv (frame `sides`): one row per club side of each trade

These rows come from `backtest.py`'s own outputs. The protocol is `40_DOCS/Backtest_Protocol.md`.

| Column | Meaning |
|---|---|
| `trade_id`, `trade_date`, `valuation_page`, `club`, `n_clubs` | the trade and the club |
| `complete` | 1 when every asset in the trade has an outcome: the tests' sample |
| `forecast_net_m` | the forecast's net for the club: what it received less what it gave up ($M) |
| `outcome_net_m`, `realised_net_m` | the outcome's net (realised through 2025-26, the rest revalued at 2026-27); realised only |
| `outcome_net_m_gv_adj`, `outcome_net_m_gv_raw` (and `realised_...`) | the same on Game Value |
| `miss_m` | outcome net less forecast net |
| `favoured` | 1 for the club the forecast favoured in its trade (the largest positive forecast net) |
| `ahead`, `ahead_gv_adj`, `ahead_gv_raw` | 1 when the outcome net is above zero |
| `during_regular_season`, `has_conditional_pick` | 1 for an in-season trade; 1 when the trade includes a conditional pick (the same on every side) |
| `g_futures`, `g_buyer`, `g_star`, `g_retained`, `g_nothing_back`, `g_clause` | the protocol's groups C1 to C6 (C3, the star group, is not in the walkthrough) |
| `recv_*_m`, `gave_*_m`, `received_m`, `given_m`, `out_wins`, `standing` | the forecast by asset class; wins delivered; standings |

## backtest_assets.csv (frame `assets`): one row per traded asset

The columns are `asset_class` (players, picks, prospects, retained); `forecast_m`, `outcome_m` and `realised_m`, with
the Game Value runs' outcomes beside them; `miss_m` (outcome less forecast, and its Game Value versions); and
`complete_trade` (1 when the asset's trade is in the tests' sample).

## gv_team_games.csv and gv_team_seasons.csv (frames `gv_games`, `gv_seasons`)

These come from the game-log database: regular-season games, 2017-18 to 2025-26, using `metric_assembly.py`'s own
queries. A shootout winner's extra goal is taken off, which gives the in-play goal differential.

| File | Columns |
|---|---|
| gv_team_games.csv | `game_id`, `season`, `team`, `game_value_sum` (the team's skaters' Game Value that game), `goal_diff_in_play` |
| gv_team_seasons.csv | `season`, `team`, `wins`, `goal_diff_in_play`, `game_value_sum`, `gv_goal_diff` (the goal differential of the games with Game Value) |
