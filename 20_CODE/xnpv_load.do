* =====================================================================================================================
* xnpv_load.do -- loads every data file the walkthrough uses, once, each into its own frame (v1.0, 2026-11-08)
*
* Run it with one command, from the folder that holds it and the CSVs (30_OUTPUT/stata/):
*     do xnpv_load.do
* xnpv_walkthrough.do runs it as its first line. stata_refresh.py copies this file next to the CSVs it writes.
*
* A frame is a dataset held in memory beside the others (Stata 16 or later). After this file runs, every dataset is
* loaded; "frame change picks" makes the draft-pick data the one the next command uses, and so on. Nothing here
* changes the data: each file is read exactly as the Python export wrote it.
* =====================================================================================================================

version 16
clear all
set more off

* ---- Draft picks and prospects (stata_export.py) ----------------------------------------------------------------------
frame create picks
frame picks:       import delimited using "draft_players.csv", clear            // one row per drafted player, 2007-2017
frame create prospects
frame prospects:   import delimited using "prospect_seasons.csv", clear         // one row per drafted player and season
frame create production
frame production:  import delimited using "production_seasons.csv", clear       // one row per Elite Prospects season line

* ---- The player model (stata_export_players.py) -----------------------------------------------------------------------
frame create skater_lines
frame skater_lines: import delimited using "price_line_skaters.csv", clear      // one row per skater contract
frame create goalie_lines
frame goalie_lines: import delimited using "price_line_goalies.csv", clear      // one row per goaltender contract
frame create skater_pairs
frame skater_pairs: import delimited using "skater_forecast_pairs.csv", clear   // skater x valuation season x season ahead
frame create goalie_age
frame goalie_age:  import delimited using "goalie_age_rows.csv", clear          // one row per goaltender-season, 20+ games
frame create goalie_play
frame goalie_play: import delimited using "goalie_play_rows.csv", clear         // goaltender x valuation season x season ahead
frame create fits
frame fits:        import delimited using "forecast_fits.csv", clear            // the model's own coefficients, every page

* ---- The back-test and Game Value (stata_export_backtest.py) ----------------------------------------------------------
frame create sides
frame sides:       import delimited using "backtest_club_sides.csv", clear      // one row per club side of each trade
frame create assets
frame assets:      import delimited using "backtest_assets.csv", clear          // one row per traded asset
frame create gv_games
frame gv_games:    import delimited using "gv_team_games.csv", clear            // one row per team and game
frame create gv_seasons
frame gv_seasons:  import delimited using "gv_team_seasons.csv", clear          // one row per team-season

frames dir
* Should list 13 frames (plus "default"), each with its rows and variables.
