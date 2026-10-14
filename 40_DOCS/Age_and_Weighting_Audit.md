# Age and season-weighting audit (2026-10-14)

Two audits Thomas asked for before the prospect model (WORK_QUEUE reading-week items 7 and 9; directive 6's
first check). Each row was read from the code that runs, at the line given. Nothing was changed. Every
"Decide" is Thomas's.

## 1. Ages: where the model reads one, and the date it uses

### What the CBA says (2013 CBA text, read 2026-10-13/14)

| CBA clause | Rule | Age date |
|---|---|---|
| 9.2 | Entry-level deal length (9.1(b): 3 / 2 / 1 seasons by signing age 18-21 / 22-23 / 24+) | September 15 of the calendar year he **signs** the contract |
| 10.1(a) | Unrestricted free agent (Group 3): 27 or older, or seven Accrued Seasons | June 30 at the end of a League Year |
| 10.1(c) | Unrestricted free agent (Group 6): 25 or older, three professional seasons, under 80 NHL games (goalies 28) | the clause states no date |
| 10.2 | Restricted free agency (Group 2) | September 15 of the calendar year he signs |
| 12.1(c) | Salary arbitration eligibility (12.1(a): 4 / 3 / 2 / 1 years of experience by first-signing age 18-20 / 21 / 22-23 / 24+) | September 15 of the calendar year he **first signs** |

The CBA has no rule for how old a player is "during a season" for measuring performance. That age is a
measurement, not a contract rule.

### Where the model reads an age

| # | Where (code) | What the age does | Date used | CBA date | Same? |
|---|---|---|---|---|---|
| 1 | `age_join.py` `compute_age` (REFERENCE_MONTH/DAY = 2/1) -> `WAR_with_age.csv` | Skater exit-risk age groups (reported only; skater exit risk no longer prices) | February 1 of the season's ending year | none (measurement) | n/a |
| 2 | `player_season_table._attach_age` | The forecast's age: the aging curve, the chance of playing, the games share; stepped forward one year a season | February 1 of the ending year | none (measurement) | n/a |
| 3 | `skater_forward_projection.age_at` | `age_at_valuation`, shown on each priced row and the dashboard; prices nothing | February 1 of the ending year | none | n/a |
| 4 | `contract_npv.py` `g_age` | Goalie exit-risk age groups, which set goalies' survival weights (prices goalies) | February 1 of the ending year | none (measurement) | n/a |
| 5 | `rfa_terminal_value._arb_inputs` | Arbitration need for a player **without** PuckPedia's eligibility flag (players with the flag use the flag) | September 15 of his **first NHL season** (Feb 1 age minus 139 days) | September 15 of the year he first signs (12.1(c)) | Date yes, **year no** |
| 6 | `pick_curve.price` | Entry-level deal length for drafted players | September 15 of his **first NHL season** | September 15 of the year he signs (9.2) | Date yes, **year no** |
| 7 | `pick_curve.price` (`ARB_NEED`) | Arbitration need for drafted players | September 15 of his **first NHL season** | September 15 of the year he first signs (12.1(c)) | Date yes, **year no** |
| 8 | `pick_curve.year_reaching` / `window_end` | End of club control at 27 | June 30 | June 30 (10.1(a)) | **Yes** |
| 9 | Player contracts' UFA year (`rfa_terminal_value`, `ufa_year`) | End of club control for contract valuations | read from PuckPedia, not computed | PuckPedia applies the CBA | n/a |
| 10 | Group 6 (age 25, few NHL games) | Not built in `pick_curve.py`; `25_TESTS/draft_window_count.py` reports it as a bound | none | 10.1(c) | **Not modelled** |

### Findings for Thomas

1. **The performance age (rows 1-4) uses February 1.** The CBA has no rule for it. February 1 sits
   mid-season, so consecutive seasons differ by exactly one year of age. Moving it to a CBA date
   (September 15) would make about four and a half months of birthdays a year younger in every season.
   It would also mean re-fitting the aging curve, the chance of playing and the price line. **Decide:**
   keep February 1 as a measurement convention and state it, or move it.
2. **The signing year in rows 5-7 is a stand-in.** The CBA reads the age on September 15 of the year he
   signs. The code uses the year of his first NHL season, because no signing date is held for most
   drafted players before 2018-19. Of the 1,157 drafted players (2007-2017) who played, the median is
   three years from draft to first NHL season. Signing usually comes earlier, so the stand-in makes him
   older at signing. An older signing age gives a shorter entry-level deal and an earlier arbitration
   date, and both raise his cost. Counted against the earliest possible signing year (his draft year), 437
   of the 1,157 would get a different entry-level length and 683 a different arbitration need. The true
   signing year lies between the two, so these counts are the upper bound. An offsetting stand-in already
   exists: experience counts only seasons of 10+ NHL games (no AHL games in the data), which makes
   arbitration later. On the player side this applies only to contracts without PuckPedia's flag.
   **Decide:** keep the stand-in and state it, or find signing dates (PuckPedia's export for contracts
   active from 2018-19; the cached CapWages pages for first-round picks) and measure the change.
3. **Group 6 is not modelled** (row 10). It applies to a player who reaches 25 with under 80 NHL games
   (goalies 28) and three professional seasons. The window count's bound assumes every such player has the
   three professional seasons. Under it, 1,656 of 2,325 drafted players (2007-2017) would reach free agency
   earlier. 1,156 of those never played an NHL game, so their seasons are worth zero and cost zero either
   way. The other 500 played; for them, any NHL seasons after 25 would leave the window. The bound
   overstates, because the data holds no minor-league games to test the three seasons. **Decide:** leave it
   out and state it, or build it and measure the change in the star value.
4. **The 35-plus contract rule** (age as of June 30 before the League Year) is not modelled. The model
   already keeps a departed player's full cap hit, so it does not change a value.

## 2. Season weighting and pulls toward the league or comparable players

Thomas's rule: 50/30/20, most recent season first, rescaled over the seasons he has (two seasons are
62.5/37.5); goalies are the exception on the pull (35% own, 65% league).

| # | Where (code) | What it weights | Weighting | Pull | Prices anything? |
|---|---|---|---|---|---|
| 1 | `skater_forecast._anchors` `own_82` | The start of the skater forecast: his rate per 82 | 50/30/20, each season's weight times its games | 65% own, 35% comparable players' level (`K_OWN`) | Yes (every skater contract) |
| 2 | `skater_forecast._anchors` `tw_WAR`, `tr_gp_share` | The level the chance of playing and the games share read | 50/30/20, plain | none | Yes |
| 3 | `aging_curve.level_at` (`LEVEL_WEIGHTS`) | Each player's level in the aging curve | 50/30/20 over ages a, a-1, a-2, games-weighted | 65% own, 35% type-and-age norm (`LAMBDA`); thin comparable estimates pulled to the league curve at weight ten (`SHRINK_K`) | Yes (through the forecast's changes) |
| 4 | `contract_npv.py` goalie cascade (`LAMBDA_G`) | The goalie forecast, held flat | 50/30/20; 62.5/37.5 with two seasons; last season alone with one | 35% own, 65% league | Yes (every goalie contract) |
| 5 | `goalie_value_engine.py` live regime | The goalie spine | as row 4 | 35% own, 65% league | Yes |
| 6 | `rfa_terminal_value.arb_trailing` | The arbitration price of a player's control season | 50/30/20 of season WAR totals, plain, rescaled; seasons after the valuation date at the forecast's WAR | none | Yes (control years) |
| 7 | `pick_curve.price` (`W_TRAIL`) | The arbitration price of a drafted player's control season | 50/30/20 of season WAR totals (short seasons to 82 games), plain, rescaled, seasons with an NHL game | none | Yes (the star value) |
| 8 | `exit_hazard.bucket` | Quality bucket for exit risk | the one season's WAR | none | Goalies only |
| 9 | `forecast_harness.subjects_at` | The star tier in test reports | 50/30/20 trailing total | none | No (tests) |
| 10 | `skater_value_engine.py` (`W_T1, W_T2`) | Observed-season value; the Stage 3 price line | **60/40** | none | No. Its spine is read only by `contract_npv.validate()` to choose rows to check; Stage 3 survives as `xnpv1_price_line.py`'s reproduction guard |
| 11 | `goalie_value_engine.py` RAW regime (`TWO_SEASON[False]`) | Rebuilds the locked goalie spine for its comparison guard | **60/40** | 65% league | No (guard only) |

### Findings for Thomas

1. **No 60/40 prices anything.** The two remaining (rows 10-11) feed only checks.
2. **The prospect model will call rows 1-7 and nothing else from this table.** These are the contract
   line (fitted on forecasts built with rows 1-3), the pick curve (row 7) and the qualifying offer.
   Every one of them is 50/30/20.
3. **One difference to rule on: the arbitration price (rows 6-7) has no pull and no games weighting.**
   The forecast's start is a games-weighted rate pulled 65/35 toward comparable players. The
   arbitration price reads his raw 50/30/20 season totals. This matches your rule ("the market price
   of his 3-season weighted WAR (50/30/20)"), and an arbitrator reads a player's recent seasons, not a
   model's estimate. **Decide:** keep it raw (recorded as deliberate), or pull it like the forecast.
4. **Pick side and player side agree** on rows 6-7 except where the data forces a difference: the player
   side counts future seasons at the forecast's WAR, and the pick side counts only seasons he played.
5. **Rows 10-11:** the 60/40 code could be retired, but each row is a guard on a locked figure. Leave
   them unless you want the guards rebuilt.
