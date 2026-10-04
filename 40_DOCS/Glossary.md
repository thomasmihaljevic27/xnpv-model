# Glossary

One name per concept, defined once. Reader-facing documents use these words and no synonyms for them.
Each entry is written from the code that implements it. Entries marked **xNPV 0** describe the first
skater model, archived on 2026-10-02. Its code is in git at `7f91f0e` (`20_CODE/` paths below refer to
that commit when so marked). Created 2026-10-04 for the rewrite of the three `Supervisor_Drafts`
documents on xNPV 0.

## Production

- **Bacon WAR.** The vendor's wins above replacement for each skater-season (`10_SOURCE/WAR.csv`) and
  goaltender-season (`10_SOURCE/Goalies_WAR.csv`). The only source of player value levels.
- **Trailing production** (xNPV 0). A weighted average of a skater's Bacon WAR in the two seasons
  before the valuation season: 60% on the more recent, 40% on the one before. With one usable season,
  that season alone. Seasons need at least ten games, and 2019-20 and 2020-21 are scaled to 82 games
  first. `skater_forward_projection.SkaterProjector.anchor`. The price line is fitted on it.
- **Valuation season, valuation date.** The season from whose start a contract is valued, and the date
  the valuation stands on: July 1 of that season by default, any date to the following June 30
  allowed. `skater_forward_projection.page_date`, `check_as_of`.

## Pricing

- **Cap share.** A salary or value divided by that season's salary cap ceiling.
- **Price line.** The fitted relationship between production and cap share. Skaters (the line xNPV 0
  prices on): 0.0132478 + 0.0212323 × WAR for forwards, + 0.0241026 × WAR for defencemen, fitted by a
  censored (Tobit) regression on 2,349 contracts starting 2018-2025. `skater_rate_cap_pct`.
  Goaltenders: 0.01391356 + 0.01059314 × WAR, ordinary least squares.
- **Cap path.** Future ceilings: the ceiling known on the valuation date grown 3% a year.
  `skater_forward_projection.cap_path`.
- **League-minimum floor.** No season is valued below that season's league minimum.
  `league_min_path`.
- **Range of outcomes** (xNPV 0). Each future season is valued as the average over a bell-shaped range
  of outcomes around the projection, with the floor applied to each outcome.
  `expected_floored_value`, spread from `_proj_sd_war`.
- **Surplus.** Value of production minus cap cost, for one season or summed.

## Survival and summation

- **Exit hazard** (xNPV 0 skaters; goaltenders today). The yearly chance a player with at least ten
  games has no NHL season the next year, from a logistic regression on four quality groups and five
  age groups. `exit_hazard.build_hazard_table`, window `pre_valuation_window`.
- **Survival** (xNPV 0). The chance the player is still in the NHL in season k: the product of one minus
  the exit hazard over earlier seasons, read at season k − 1. Multiplies value only.
  `contract_npv.NPVEngine._npv_skater`.
- **Quality groups.** Below replacement (below 0 WAR), fringe (0 to 1), regular (1 to 3), star (3 or
  more). `exit_hazard.bucket`, `rfa_terminal_value._anchor_bucket`.
- **Present value.** A season's surplus divided by 1.03^k, k years after the valuation season.
- **Extension.** A contract that starts the season after the current one ends, counted once its
  signing date is on or before the valuation date. `skater_forward_projection.contract_chain`.

## Control years

- **Control years.** The seasons after a restricted expiry until the player is eligible for
  unrestricted free agency.
- **Terminal value.** The discounted surplus from control years. Zero for an unrestricted expiry.
  `rfa_terminal_value.TerminalValuer.terminal_value`.
- **Qualifying offer.** The one-year offer set by the collective agreement's formula, iterated year on
  year. `rfa_terminal_value.qualifying_offer`.
- **Qualification rate.** The observed share of restricted expiries a club qualified, by quality
  group, on contracts ending 2018-2024. Weights each control year in place of the exit hazard.
  `TerminalValuer._calibrate_qualify_rates`.

## Game Value

- **Expected goals (xG).** A shot's estimated probability of becoming a goal. `xg_model.py`.
- **Score adjustment.** The weight on an even-strength chance by game state (leading, tied,
  trailing). `score_state.py`.
- **Game Value.** A skater's score-adjusted on-ice expected goals for minus against, split equally
  among the skaters on the ice, plus 0.2097 goals per penalty drawn minus per penalty taken.
  `metric_assembly.py`, table `player_game_value`.
- **GV-adj.** Game Value with five-on-five play estimated by ridge regression on shifts, plus
  penalties and shrunk finishing. `gv_adjusted_build.py`.
- **Circularity check.** Trailing production against GV-adj in the same season, in wins.
  `25_TESTS/gv_4b_circularity_check.py`.

## Draft picks

- **Draft curve.** Mean surplus per pick by draft-position band, 2007-2017 drafts, nine seasons from
  the draft. `draft_yield_curve.py`.
- **Entry-level years.** Three, two, or one year by age at the first season with ten NHL games
  (21 or younger, 22-23, 24 or older). `draft_yield_curve.py`, `elc_len`.
- **Rule A.** Surplus counted only in entry-level years; zero afterward by construction.
- **Rule B.** After entry-level years, cost priced on trailing production. A robustness check, with a
  known defence slope mismatch.
- **Original-team slot.** A pick whose number is unknown on the trade date is placed where its
  original team picked in the last draft. `slot_curve.own_slot_overall`.
