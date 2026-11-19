# Back-test protocol, declared before the run (2026-10-20)

Committed before any outcome was computed, so that the groups and tests cannot be chosen after seeing results. Every
choice marked **Thomas** was his on 2026-10-20 (or earlier, as dated); every choice marked **built** is how Claude
implemented a decided rule, listed so it can be checked. Nothing here may change after the run without a dated note
saying what changed and why.

## What is compared

For each club in each traded deal from 2017-07-01 to 2022-03-28 (567 trades, trades.db):

- **Forecast (ex-ante) net:** the value of what the club received minus the value of what it gave up, every asset
  valued by the three models at the trade, in $M at the 2025-26 cap (`trade_sides.py`). Each trade is zero-sum among
  its clubs. The retained part of a player's cap hit is charged to the retaining club (Thomas, 2026-10-19).
- **Outcome (realised) net:** the same sum with each asset's value replaced by what it delivered over the same span.

## How an asset's outcome is measured

1. **Span.** The same span its forecast covers: a player's contract as traded plus his control seasons to his UFA
   year; a pick's or prospect's draftee from the draft (or the trade) to the end of club control (CBA Group 3, as the
   pick curve). **Thomas:** a contract signed with the acquirer on the trade date is not part of the trade (13 in
   2018-19 on, 2 on the 2017 page), in the forecast and the outcome alike.
2. **Seasons played, through 2025-26** (Thomas: "Played + rest re-valued"). Value: the contract line with the wins he
   delivered (open decision 3, 2026-10-05): max(alpha + beta x WAR + gamma_term x term, league minimum) x that
   season's actual cap; a season with no NHL game is worth zero. Short seasons' WAR scaled to 82 games and seasons of
   under 10 games scaled by games/82, as the pick curve (**built**: the pick curve's rules). Goalies on the goalie line.
   The term premium of a contract season is the one its forecast used (**built**); a control or draftee season is
   priced as a one-year deal.
3. **Cost of a contract season:** the cap hit charged (PuckPedia's, `model_cap_hit`), paid whether or not he played,
   the acquirer's share net of retention and the retained part to the retaining club. A contract season the contract
   no longer has (bought out or ended) is charged what the forecast charged (**built**: buyouts are not in the data).
4. **Cost of a control or draftee season** (Thomas: "The model's rule"): entry-level maximum, then the qualifying
   offer, then the higher of it and the arbitration price once eligible, exactly as the pick curve; a season with no
   NHL game costs zero. For traded players, the chain starts from the expiring contract's final salary
   (`rfa_terminal_value.final_year_salary`) and eligibility follows PuckPedia's flag, as the forecast does. A player
   not qualified at his contract's end ("UFA no QO") has no control seasons.
5. **The season of an in-season trade:** the share of the season's days left (Thomas, 2026-10-19) for the intercept,
   the floor and the cap hit, and the wins he delivered after the trade = season WAR x his games after the trade /
   his games that season, from the game logs (**built**; the record's Game Value split is on hold and needs a rule for
   seasons whose total is near zero).
6. **Seasons from 2026-27 on** (Thomas: "the rest re-valued"): valued by the same models at the 2026-27 page,
   knowing everything through 2025-26: a draftee still a prospect by the prospect model at season 2026; a draftee or
   traded player in the NHL by the forecast at page 2026 (value x chance of playing, the control-year weights as in
   the forecast) with the cost of rule 3 or 4.
7. **Rights that lapsed** (the pick curve's rule) are worth zero. A pick is followed to the player drafted with it
   (trades.db `pick_number`, the linkage); conditional picks as conveyed in the record.
8. All seasons in cap shares, stated at the 2025-26 cap (3% growth and 3% discounting cancel, D11; realised seasons
   at each season's actual cap). Each asset is followed whoever holds it later: the outcome is the asset's, not the
   club's (**built**).

## The statistic (Thomas: "Dollar gap per club")

Per club side: forecast net and outcome net in $M at the 2025-26 cap. Intervals: 2,000 resamples of trades (a trade's
club sides move together), seed 20261020, 95% percentile intervals; a p-value is the share of resamples on the other
side of zero, doubled.

## Tests, all reported, none dropped

**A. Does the model's verdict predict the outcome?** Over all club sides of complete trades: the slope of outcome net
on forecast net (one would mean the forecast's gaps come true on average, zero that they carry no information), the
correlation, and the share of trades whose favoured club (forecast net > 0) also came out ahead. Each with its
interval.

**B. Asset-class calibration.** For players, picks and prospects separately: the sum and mean of (outcome - forecast)
per asset. A pillar whose outcomes fall short of its forecasts on average will show here before it shows in any group.

**C. Groups of clubs** (from the record's named categories; the mean forecast net, mean outcome net and their
difference for the group's club, each with its interval):
1. **Futures for players:** two-team trades where one club received only players and gave at least one pick or
   prospect. The group is the club that received the picks and prospects.
2. **Buyers at the trade date:** two-team trades during the regular season. The group is the club higher in the
   standings (points percentage, games before the trade date).
3. **Stars:** the club that received a skater whose 50/30/20 trailing WAR total before the trade's page is 3 or more
   (the harness's 3+ tier, where the star over-forecast was measured: STANDING_FLAGS 2026-09-13b).
4. **Retained salary:** the club that retained salary.
5. **Nothing back:** trades where one club received no recorded asset. The group is that club.
6. **No-trade or no-move clause:** the club that received a player whose contract carried such a clause in the trade
   season (the clause scrape). Not a forced-trade test: the detection rule is not built (STANDING_FLAGS).
7. **Deadline versus off-season:** in-season trades and off-season trades, each scored by test A's slope.

## Sensitivities, all reported

- Trades with a conditional pick left out.
- Outcome through 2025-26 only (the 2026-27 re-valuation set to zero), and the share of the outcome that is re-valued.
- The pick curve's sensitivity star value for picks (without 2015-2016).

## Amendments after the first run (2026-10-20)

The first run (`backtest.py` v1.0) was read in full, group results included, before these were made. Each corrects how
an outcome was measured; none changes a group, a test or a sensitivity. The first run's log is kept beside the final one
(`30_OUTPUT/backtest_log_v1.0.txt`).

1. **Seasons after a buyout** (replaces the last sentence of rule 3). v1.0 charged a bought-out contract's remaining
   seasons at the full cap hit and credited the value of seasons he played afterwards on other clubs' contracts
   (Ekman-Larsson's Florida and Toronto seasons against Vancouver's deal). From v1.2: after a contract's last season in
   force (the export's 38 deals that ended early), its seasons credit no value and charge the CBA buyout share of the
   cap hit, two thirds (one third under 26). A mutual termination is charged the same, an overstatement.
2. **Spellings** (v1.1, v1.2). A player whose spine spelling has no WAR rows is read under the trade ledger's spelling
   (Alex Petrovic), then under the short or long form of the first name (Alex Nylander, Alex Kerfoot); every
   player-model asset with no WAR row under any of them is listed in the log. In v1.0 these four players' delivered
   value read as zero.

3. **Long-term injured reserve** (v1.4; Thomas, 2026-10-20: "All of it", "Outcome + known at trade", "Fetch a real
   LTIR log"). Rule 3's cost of a contract season is charged only for the days he was not on LTIR (Spotrac's
   injured-reserve pages, `ltir.py`); the retained part is never relieved. From 2026-27, a player on LTIR at that page
   is charged his cap hit times the forecast's chance he plays. The forecast side changes too: a player on LTIR when
   traded is charged, season by season, his cap hit times the chance he plays (`traded_player_values.py` v1.5,
   `page_2017_values.py` v1.8), or nothing where there is no forecast (`buried_contract_values.py` v1.8). Which spells
   count is Thomas's choice between Spotrac's "Long-Term IR" label alone and the label plus any IR spell meeting the
   CBA's test (24+ days, 10+ games); both are run.
4. **The qualifying-offer look-ahead** (v1.3; Thomas: "Fix the QO look ahead"). The forecast reads "UFA no QO" only
   once the club's decision is known; the outcome reads the label itself (no control seasons for a player the club
   did not qualify).
5. **The star group set aside** (2026-10-23; Thomas: "don't include the star line at all in the back test but we can
   revisit that later"). Group C3 (the club that received a skater with a 3+ trailing WAR total) holds one club side
   in the run, too few to test. It is left out of the reported results; no lower line is substituted. `backtest.py`
   v1.6 still computes it. Changes a group, unlike amendments 1 to 4.

6. **Draftees traded after March 2022** (2026-11-11; Thomas: "Yes, switch"). The pick curve's rule for rights that
   lapsed (rule 7 above) read `trades.db`, which ends 2022-03-28, so a draftee traded after that date who debuted for
   his new club counted as lost for nothing and his pick's outcome as zero. From `pick_curve.py` v1.12 the rule reads
   the ledger carried to March 2026 (`trade_ledger_extend.py`). Measured before the switch, in a scratch run: the
   forecast side barely moves (one player in the fit, the star value down $200, no traded pick's value by more than
   $56); eleven draftees of 2018-2023 change from lapsed to traded (Brock Faber +$4.29M, Cutter Gauthier +$6.65M),
   four of them drafted with a pick traded in the declared window (five assets, +$8.4M of outcome). Corrects how an
   outcome is measured; changes no group, test or sensitivity. The results before it are kept in
   `30_OUTPUT/_before_switch/`.

## The Game Value check (declared 2026-10-20, before it was run; Thomas: "Run the Game Value check on the back-test's outcomes, as the protocol says")

The locked validators (DECISIONS, 2026-07-04 and 2026-07-14): Game Value adjusted (GV-adj) primary, Game Value raw
(GV-raw) as robustness, goals to wins at 5.903, zero Bacon inputs. This is the trade-level check deferred in July
"until draft/prospect components exist".

1. **What changes.** Only the measure of what a skater delivered in a realised season, 2017-18 to 2025-26: his Bacon WAR
   is replaced by his Game Value. Everything else is the v1.4 outcome unchanged: the same assets and spans, games
   played, cap hits, the rule's costs, LTIR, buyouts, the 2026-27 revaluation (a forecast, not an outcome) and the
   forecast side. Goaltenders keep Bacon's goalie WAR (Game Value has no goaltender measure). Drafted players' realised
   seasons are re-priced the same way (their costs unchanged).
2. **Baseline.** GV-adj is centred on the league average; Bacon's WAR and the contract line count from replacement. GV-adj
   is put on a replacement baseline with Game Value's own per-game rebase (`player_game_value_repl`: gv_repl minus
   game_value, summed over his regular-season games). GV-raw uses gv_repl directly.
3. **Units.** The rebased Game Value runs about 200 wins a league season against Bacon's 470-570, with a narrower
   spread, so priced as it stands it would mark every player down for its units alone. Each season and position (F, D),
   it is mapped to Bacon's scale by matching the league's mean and standard deviation of season totals (all skaters in
   each table; two numbers per cell from Bacon, none from any one player). Who delivered how much stays Bacon-free.
   A skater-season with games and no Game Value row keeps Bacon's figure; the count is logged.
4. **Rate-free leg.** Each club side's net wins delivered in realised seasons (received minus given), on Bacon and on
   each Game Value measure, compared by correlation, with no dollar rate on either side.
5. **What is reported.** Tests A, B and C re-run on GV-adj and GV-raw beside the WAR run. A result **holds on Game
   Value** when, on GV-adj, its estimate keeps the WAR run's sign and its 95% interval still excludes zero; otherwise
   it is **not confirmed**. GV-raw is reported beside, not decisive. As in July, Game Value is strong for forwards and
   weak for defencemen (r 0.65 against 0.30); the asset-level agreement is reported by position.

## Limits stated in advance

- The outcome uses Bacon's WAR, the same source as the forecast. The Game Value check (the locked circularity
  validators) is the next step; no group finding is called systematic before it.
- The 2026-27 re-valuation is itself a forecast; it is largest for the 2022-2025 picks.
- A club's own gains (fit, playoffs, a Cup) are outside the currency: regular-season wins only.
- Multiple groups: seven groups and two class tests; a single p below 0.05 among them is weak evidence alone.

## Exploratory cuts (declared 2026-11-11, before any of them was computed; Thomas: "Time to look into findings")

These cuts were chosen after the protocol's results (tests A, B, C and the Game Value check) had been read. They are
exploratory: none replaces a protocol test, and with this many groups a single p below 0.05 is weak evidence.
Script: `25_TESTS/backtest_cuts.py`, reading the 2026-10-24 run's files (`backtest_sides*.csv`, `backtest_assets*.csv`).

**The measure** (Thomas, 2026-11-11: "Yes, dollar gap"). Per club side, in $M at the 2025-26 cap: the forecast net (what
the models valued the club's side at on the trade date: below zero means the club paid more than the models' value),
the outcome net on Bacon's WAR, and the outcome net on Game Value adjusted (skaters' realised seasons Bacon-free;
goaltenders keep Bacon's WAR). Each group: club sides, trades, median and interquartile range of the forecast net, and
the mean of each of the three with a 95% interval from 2,000 resamples of trades (seed 20261111). The ratio of value
sent to value received is not used: it is defined for 429 of 1,135 club sides. Asset-level rows (outcome minus forecast
per asset) follow test B.

**A club side's main player** is the player it received with the highest cap hit in the trade ledger (a fact of the
contract, not a model value, so group membership does not select on the forecast). Players are the assets the player
model values (contracts, rights, buried contracts, the 2017 page), not prospects.

1. **Position:** the main player's position (F, D, G). Asset-level: players by position.
2. **Age:** the main player's age on the trade date: 23 and under, 24 to 27, 28 to 31, 32 and over.
3. **Asset class:** two-team trades by what changed hands: players for players, players for picks and prospects (C1),
   picks and prospects both ways, mixed (a side received both).
4. **Contract status** of the main player at the trade: entry-level contract; final season, restricted at expiry;
   final season, unrestricted at expiry (a rental when traded in-season); two seasons left; three or more; rights only.
5. **Former top prospects not broken out (5b only):** a player drafted in the top 15, traded in his D+5 season or later
   (the page at least four years after his draft), whose 50/30/20 trailing WAR total before the page is below the mean
   season WAR per 82 of top-15 picks in D+5 and later, measured on the 2005-2012 drafts' seasons through 2016-17
   (before every trade here). Group: the club that received him.
6. **Timing:** off-season; deadline window (the 14 days up to and including the deadline: 2018-02-26, 2019-02-25,
   2020-02-24, 2021-04-12, 2022-03-21); rest of the regular season. Test A's slope and the buyer's side in each.
7. **Buyers:** C2's club higher in the standings, split by the gap in points percentage (above or below the median gap),
   and crossed with 4 (received a rental) and 6 (deadline window).
9. **Retention:** C4 by timing; three-team trades counted.
10. **Clauses:** C6's club against clubs whose main player had no clause, both restricted to main players with a cap
    hit of $3M or more.
11. **Cap era:** trades before 2020-03-12 (the pause) against after. Tests A and C1 in each.
12. **Over time:** by trade season 2017-18 to 2021-22: the mean absolute forecast net per trade and C1's forecast net.
13. **Quantity for quality:** two-team trades where one club received one asset and the other two or more (retained
    salary not counted). Group: the club that received the single asset.
14. **Future picks:** by years between the trade's next draft and the pick's draft (0, 1, 2+). (a) asset-level outcome
    minus forecast; (b) for picks valued at the round average, the actual selection number minus the round's middle
    selection; (c) trades with a conditional pick against without (conditions are not modelled).
15. **Late picks:** asset-level outcome minus forecast by round (1, 2, 3-4, 5, 6-7), and picks forecast or selected
    at 151 or later.

Not run, and why: 5a (untraded players are not valued at each date), 8 (no club cap payroll by date), 9's amendment
split and 11's post-flat era (the trades end 2022-03-28), 16 (offer sheets: not built), GM tenure and injury status
(no data).

**Rows added when the script was written (2026-11-11, before any result was read; none replaces a declared row):** the
buyer's side (C2) by cap era; buyers who received no rental; final-season unrestricted players by when traded; the
single asset in cut 13 split into a player or a pick or prospect; cut 14a's club side by its most distant pick; cut
14b's rows by round; the club whose whole return was round 6-7 picks. Main players of unknown position or age are
reported as their own rows (the 2017 page's players with no NHL id).

## The extended trades (declared 2026-11-11, before any group was computed on them; Thomas: "Extend", "Yes, build it")

The trades after 2022-03-28 come from PuckPedia's trades export (`trade_ledger_extend.py`, rules in its docstring;
`trades_extended.db`), valued by the same chain into `30_OUTPUT/_extended_run/`. The confirmatory run stays the declared
window, 2017-07-01 to 2022-03-28; its 1,648 asset values are unchanged in the extended run. Read before this note was
written: the extended run's tests A and B and one line of C6.

- **Complete trades only, as before.** A trade with a pick for a draft not yet held has no outcome and is out (927 of
  1,085 trades are in). The outcome of a recent trade is mostly the models' re-valuation at 2026-27, so for trades from
  2022-23 on the forecast net is the firmer column.
- **Replication.** Each result the exploratory cuts found on 2017-22 is recomputed on the trades after 2022-03-28 alone,
  which played no part in finding it: the club higher in the standings in the deadline window and in the rest of the
  season, with and without a rental; picks and prospects for players (C1); retained salary (C4); the main player aged
  28 to 31, and 23 and under; the main player a defenceman, a forward; clause and no clause at $3M or more; one asset for
  two or more; picks by round (asset level); contracts with three or more seasons left (asset level); picks valued at
  the round average, one draft later. A result replicates when the new trades give the same sign with a 95% interval
  excluding zero.
- **Cuts that were blocked.** Cap era in three parts: before 2020-03-12, 2020-03-12 to 2022-06-30 (flat cap), from
  2022-07-01. Trend by trade season 2017-18 to 2025-26. Retained salary by period: to 2021-22, 2022-23 to 2024-25,
  2025-26 (the season of the retention rule change; its date is not verified here).
- **Deadlines added:** 2023-03-03, 2024-03-08, 2025-03-07, 2026-03-06 (each the busiest trade date of its season in
  the ledger).

## Four more exploratory cuts (declared 2026-11-12, before any was computed; Thomas: "continue with 5a, 8, 16, and GM tenure")

Script: `25_TESTS/backtest_cuts_more.py`, reading the extended run (`30_OUTPUT/_extended_run/`, every complete trade
2017-07-01 to 2026-03-13), with the declared window (to 2022-03-28) shown beside each main row. Measures and intervals
as the exploratory cuts above (2,000 resamples of trades, seed 20261112). All four are exploratory.

**5a. Former top-15 picks who have not broken out: are they held too long?** Not a trade test: every skater drafted in
the top 15 from 2009 to 2020, at every July 1 page from 2018 to 2025 on which the player model values a contract of
his (the contract panel) and which is his D+5 season or later, traded or not. Below the benchmark as in 5b (50/30/20
trailing WAR total before the page under 1.078). By season since the draft: players; mean and median model value
($M at the 2025-26 cap); the share traded in the next twelve months (the ledger carried to 2026); the share at or above
the benchmark at any later page (a later break-out); and, for those not traded, the change in model value to the next
page. Limit: the model's value stands in for what he would have fetched, which no data records for a player who was
not traded; cut 5b gives what the market paid for the traded ones.

**8. Cap pressure.** (i) Paying to move a contract, by the trade's structure alone (no model value picks the group):
two-team trades in which one club sent a player with a cap hit of $2.5M or more together with a pick or prospect, and
received no player with a cap hit of $1M or more. Reported: trades; the cap dollars cleared (cap hit times the seasons
left, the trade season by its share left; $M at the 2025-26 cap); the models' value of the picks and prospects sent
with him; that value per $1M of cap cleared; the receiving club's forecast net and outcome. (ii) Club payroll on the
trade date, an estimate: the cap hits (`model_cap_hit`, the page's season) of every player whose most recent NHL
regular-season game in the 365 days before the trade was for that club, as a share of that season's cap. In-season
two-team trades at least 20 days after the season's first game. Clubs in the top third of payroll share against the
rest: forecast net and outcome. The estimate leaves out long-term injured reserve, players buried in the minors,
retained salary and bonus overages.

**16. Offer sheets (a what-if, not a back-test).** Every standard contract in the PuckPedia export signed from 2018 on
by a restricted free agent (signing status RFA) that the contract panel values at its first season. Value to a club
that had signed him to the same term by offer sheet at his actual average annual value plus 0%, 10% and 20%: the
panel's value of the contract (control seasons after it included) less the extra cap hit each season, discounted at 3%,
less the compensation picks at the pick curve's round-average values (the offering club's own picks; a first-round
pick in each of the next two or four drafts where the tier asks for them). The tier is read on total value divided by
the lesser of the term and five, as the CBA. Thresholds: the 2005 base ($660,000, $1M, $2M, $3M, $4M, $5M) times a
yearly factor. The factors for 2019, 2021 and 2024 are confirmed by the sheets tendered (Aho $8,454,000 a year, the top
of its tier; Kotkaniemi; Broberg $4,580,917 and Holloway $2,290,457, each the top of its tier); those for 2018, 2020,
2022, 2023 and 2025 are recalled, not read from a printed source (each consistent across two tiers to six digits).
Reported by tier and premium: contracts, the share with a positive payoff, the mean and median payoff; and the four
sheets tendered 2018 to 2025 priced at their own terms. (Dated note, 2026-11-12, after the run: Thomas supplied the printed thresholds for every year 2018 to 2025; each
equals the build above to within $3 and no contract changed tier. The script now reads the printed table.)
An upper bound: the original club's right to match, players
ineligible for a sheet, the offering club's need to hold its own picks, and league norms are not modelled, and a
contract signed under a club's exclusive rights understates what a sheet would have had to pay.

**GM tenure.** General managers and their dates from each club's Wikipedia list (86 tenures, read 2026-11-12). A new
general manager: the first 365 days of a person's time in the job at a club (an interim spell that becomes permanent
counts from its first day). Group: a club that sent a player whose contract was signed before that person took the
job, in that first year; against clubs sending a player under a general manager past his first year. The player is the
one with the highest cap hit the club sent. Forecast net and outcome for the sending club.

## Sensitivity: each contract season priced on its contract's original term (declared 2026-11-12, before it was run; Thomas: "Yes, run it")

Why: `25_TESTS/contract_value_by_age.py` showed that the level of every traded contract's value follows from pricing a
contract season on the term left at the valuation date while its cap hit was set on the whole term (STANDING_FLAGS,
"The remaining-term rule"). The model as decided is unchanged. This run changes one thing: with the environment
variable `XNPV_TERM_BASIS=original`, a contract season is priced on the signed length of the contract it belongs to
(a bought-out deal at its full signed term), in the forecast and in the outcome alike. Control seasons, draftees'
seasons, picks and prospects stay at one year of term; goaltenders' contract seasons follow the same switch on their
own line; the price lines are not re-fitted. Read before this note: the approximate adjustment of four groups in the
check above.

Run on the ledger carried to 2026 into `30_OUTPUT/_original_term_run/`. Reported beside the run as decided: tests A and
B; the protocol's groups; every exploratory cut on the declared window, the trades after 2022-03-28 and all trades
(`backtest_cuts.py`, whose check against the recorded group means is skipped under the switch and says so). A finding is
called robust to the term rule when it keeps its sign with a 95% interval excluding zero under both.

## Test: does a longer contract predict out-performing the forecast? (declared 2026-11-13, before it was built or run; Thomas: "Yes, run it")

Decides between the two ways of pricing a mid-contract season (STANDING_FLAGS, "The remaining-term rule"). Sample: the
price line's 2,336 skater contracts (`30_OUTPUT/term_average_price_line_rows.csv`: standard UFA and RFA contracts
starting 2018-2025, forecast dated at the signing). For each contract season through 2025-26: the forecast's expected
season WAR from the signing page (chance of playing x WAR if he plays, `xnpv1_forecasts.csv`, the career key from
`player_season_table`), against the delivered season WAR (the harness's target, `forecast_harness.outcomes`: a season
not played is zero, short seasons on 82 games). The miss, delivered minus expected, is converted to dollars with the
price line's slope (forwards and defencemen apart) at the 2025-26 cap. Regressed on the contract's length in years, for
the first, second and third season of the contract separately (so the forecast horizon is the same within each fit),
controlling for the forecast and defence; a second fit adds signing status and age; a third puts the forecast in
fifths. Intervals: 2,000 resamples of players. Benchmark: a coefficient of $0.851M a season per year of term would
mean the whole term premium is quality the forecast misses (original term); zero would mean it buys length alone
(remaining term). Script to be written: `25_TESTS/term_quality_test.py`.

## Which findings survive each other (declared 2026-11-15, before it was built; Thomas: "Yes, run it")

The exploratory cuts are largely the same trades seen from different sides. One regression, `25_TESTS/joint_regression.py`,
puts the characteristics together. Two-team complete trades; one row a trade; the outcome is one club's net (club A, the
first in alphabetical order); each characteristic enters as club A's indicator minus club B's (+1, 0 or -1), with no
constant, so a coefficient is what having the characteristic, rather than the other club having it, does to a club's net,
the others held. Outcomes: the forecast net (priced), the outcome net on WAR, on Game Value. Characteristics, each as
defined in its cut: took picks and prospects for players (C1); higher in the standings in the deadline window; higher in
the standings in the rest of the regular season; received a rental (main player in his final season, unrestricted at
expiry, traded in-season); retained salary; main player aged 28 to 31; 32 or over; a defenceman; carrying a no-trade or
no-move clause; a former top-15 pick below the benchmark; received one asset for two or more; took a contract another
club paid to move (cut 8(i)); sent a player under a new general manager on his predecessor's contract. Scopes: all trades
2017-2026 (the extended run) and the declared window. Intervals: 2,000 resamples of trades, seed 20261115. Each
characteristic's coefficient alone is reported beside its coefficient with the others, so a reader sees which shrink.
The model as decided (the term left).

## The seasons played only (declared 2026-11-15, before it was run; Thomas: "Yes, run it")

For recent trades most of the outcome is the models' re-valuation at 2026-27, so an outcome finding may rest on the model
agreeing with itself. With `XNPV_OUTCOME_PART=played`, `backtest_cuts.py` v1.5 and `joint_regression.py` v1.2 read each
club side's outcome through 2025-26 only (the back-test's existing "realised only" column; the re-valued seasons set to
zero) and each asset's realised part; the forecast is unchanged, so outcome minus forecast is not read under it. Run on
the declared window, the trades after 2022-03-28 and all trades, and the joint regression on all trades and the declared
window. An outcome finding is called independent of the re-valuation when it keeps its sign with a 95% interval
excluding zero on the seasons played. Expected in advance: recent trades' outcomes shrink toward zero (few seasons
played), so the trades after 2022-03-28 have the least power under it.

## Standard errors clustered by trade, and outcome on price by group (declared 2026-11-15, before it was built; Thomas: "Yes, re-run them")

Why: the group results were averages with intervals from 2,000 resamples of trades. The same problem (a trade's two
sides are mirror images, so club sides are not independent) is solved in the standard way by robust standard errors
clustered by trade. Script: `25_TESTS/groups_clustered.py`, on the extended run's club sides (the model as decided; all
trades, the declared window and the trades after 2022-03-28 as subsets).

Groups: the joint regression's thirteen characteristics, each as a club-side indicator, and the club that received
nothing recorded (C5). For each group and each outcome (priced net, outcome net on WAR, on Game Value):
1. The group's mean, with a standard error clustered by trade, beside the resampled interval it replaces.
2. Thomas's regression, on every club side: outcome net = a + b x priced net + c x (in the group) + d x (in the group x
   priced net), clustered by trade. c is the group's outcome beyond what its price predicts (the mispricing reading);
   d is whether the models' verdict comes true differently in the group. Run on the outcome on WAR and on Game Value.
3. Holm's adjustment of the p-values across the fourteen groups, separately for each outcome and each scope; the
   declared window is the primary scope, the trades after 2022-03-28 the replication.
The joint regression is re-fitted with robust standard errors (its rows are trades, so clustering by trade is the
plain robust error), and once more with the priced net added as a regressor (Thomas's form, all traits together).
No group, outcome or rule changes; the resampled intervals stay beside each new one.

## Is the defenceman result the measures' weakness on defence? (declared 2026-11-15, before it was built; Thomas: "Yes, run them")

The finding: clubs acquiring a defenceman come out worse than even their price predicts (joint regression, price held),
on WAR and on Game Value, and both measures are built from shot-and-shift data, weak on defence. Script
`25_TESTS/defence_checks.py`, report only, the model as decided.
0. The loose end: per asset, traded defencemen delivered about what was forecast (test B by position), yet the club sides
   fall short. For club sides whose main player is a defenceman (and, beside, a forward), the side's outcome minus its
   priced net is split into the main player's own miss, the other assets received, and the assets given.
1. Games against quality per game. For every skater the forecast covers, at every July 1 page 2018-2025, seasons one to
   three ahead through 2025-26: delivered minus expected season WAR is split exactly into a games part ((games share
   delivered - expected) x forecast rate per 82) and a per-game part (games share delivered x (rate delivered - forecast
   rate)). Defencemen against forwards; players traded in the twelve months after the page against not traded.
2. Ice time. Each such season's ice time per game against the player's own 50/30/20 trailing ice time per game before
   the page (seasons of 10+ games): traded against not, within each position. Ice time is the coaches' choice and uses
   no WAR model.
3. Bacon's WAR by part. The same seasons' per-82 rates of even-strength offence, even-strength defence, power play,
   penalty kill, penalties and shooting, each against the player's own 50/30/20 trailing rate: traded defencemen
   against untraded.
Intervals: 2,000 resamples of players, seed 20261115. Reading declared in advance: a shortfall carried by games (1), by
ice time (2), or by parts other than even-strength defence (3) is not the measures' weakness on defence; a shortfall
carried by the per-game part and by even-strength defence alone, with ice time held up, points at the measures.

## Why do clubs overpay for clause players? (declared 2026-11-17, before it was built; Thomas: "Yes, run them")

The clause result holds with the age bands held (joint regression). Three explanations are tested, report only, script
`25_TESTS/clause_checks.py`, all trades and the declared window, the model as decided:
1. A marker of a free-agent contract. The joint regression is re-fitted with two more differences between the clubs:
   the main player's contract signed as an unrestricted free agent (PuckPedia's signing status; unknown counts 0, the
   count printed), and his cap hit ($M). If the clause coefficient falls to zero and the free-agent coefficient takes
   its place, the clause marks a free-agent contract.
2. Reputation. For main players with a cap hit of $3M or more: his 50/30/20 trailing WAR total before the trade's page
   less the forecast's expected WAR for the first season (chance of playing x WAR if he plays), clause against no
   clause; and whether the club's priced net falls as that gap grows, with and without the clause held.
3. The season. The clause group's means, off-season against in-season trades, standard errors clustered by trade.
Each answers its own question; none excludes the others.

## What the cap hit explains, and who clubs pay more than they are worth (declared 2026-11-17, before it was built; Thomas: "the more interesting finding is to follow the pattern of who is overpaid")

The clause checks found the main player's cap hit carries the clause result. A contract's xNPV is its forecasted
performance value less its cap hit, so "clubs overpay for expensive contracts" is partly the model's own definition.
Script `25_TESTS/who_overpaid.py`, report only, all trades and the declared window, standard errors clustered by trade.
A. What else the cap hit explains: the joint regression's thirteen coefficients with and without the main player's cap
   hit; and the cap hit's coefficient on the trades after 2022-03-28 alone (its replication).
B. How prices follow a contract's value. For club sides with a main player: the price paid for him is what the club gave
   up less everything else it received, at the models' values. It is regressed on his contract's two parts: the value of
   his forecasted performance (with his control seasons) and the present value of his cap hit over the seasons left
   (cap hit x the share of the season left, then each further season, each divided by 1.03^k, stated at the 2025-26 cap;
   retention and injured-reserve relief left out, so approximate). A price that follows each part in full has both
   coefficients at 1 (the cost with a minus sign). Outcome beside: the same with the assets' delivered values.
C. Who clubs pay more than they are worth, with the cap hit left out: the club's overpay (minus its priced net) and its
   realised loss (minus its outcome net), on club sides with a main player, regressed on his characteristics measured
   before the trade: age band (27 and under the base), defenceman, a clause, signed as an unrestricted free agent,
   seasons left (one the base), his production (50/30/20 trailing WAR total), his record above the forecast (trailing
   total less expected first-season WAR), his games share in the most recent season, and a former top-15 pick. All
   together, then each alone.
Exploratory: each term was chosen after the earlier results were read.

## Two checks on who is overpaid and on how prices follow a contract (declared 2026-11-17, before they were built; Thomas: "Yes, run both")

Script `25_TESTS/who_overpaid_checks.py`, report only, building its rows with `who_overpaid.build()`.
1. Immature outcomes. The "who" regression (part C of who_overpaid.py) on the trades after 2022-03-28 alone, and on all
   trades and the declared window with each club's result counted on the seasons played through 2025-26 only (the
   re-valuation at 2026-27 set to zero). The overpay (the trade-day grade) is unchanged by either; only the loss moves.
2. Model error or the market. Part B's price paid for the main player regressed on the value of his performance as
   delivered (his asset's outcome plus the same cost), and on the seasons played only; then the price regressed on the
   model's performance value with that value instrumented by the delivered value (two-stage least squares), which
   removes the pull toward zero from error in the model's value if that error is unrelated to the luck in what was
   delivered. Standard errors clustered by trade (the instrumented fit's by 2,000 resamples of trades, seed 20261117).

## Amendment, 2026-11-18: the headline on trades fully played out (requested after a first look)

Thomas, commenting on the writeup: "I still think it may be best to not include any of the models own valuations when
doing this comparison ... but I want to know how much it shrinks the sample size". A first count was run before this entry
was written, so this check is declared after its result was seen. Script `25_TESTS/played_out_trades.py`, report only. A
trade is fully played out when no asset in it carries any value re-assigned by the models at 2026-27 (each asset's
`revalued_M` zero to $1e-6). On those trades, beside all complete trades, Test A as `backtest.py` computes it: the favoured
club ahead (also with sides whose realized value is exactly zero set aside, since many played-out trades are minor-league
swaps in which nothing ever played), the slope through zero, the correlation and its square, with 95% intervals from
2,000 resamples of trades (seed 20261118); declared window, after 2022-03-28, and all trades. No test or group in this
protocol changes; whether the main test should move to played-out trades is Thomas's decision.

## Who is overpaid, with each characteristic taken from any player received (declared 2026-11-18, before it was built; Thomas: "I would be interested in seeing the results done without this rule and just if they got that type of asset at all")

Script `25_TESTS/who_overpaid_any.py`, report only, on the same club sides as `who_overpaid.py` part C (735, all trades;
the same overpay, loss on WAR and loss on Game Value). One change: each yes-or-no characteristic is 1 when ANY player the
club received has it, not only the main player (the highest cap hit). The players counted are the same pool the main
player is chosen from (`backtest_assets` player rows valued by the player model or as buried contracts). The yes-or-no
characteristics: aged 28 to 31, aged 32 or over, a defenceman, a no-trade or no-move clause, signed as an unrestricted free
agent, two seasons left, three or more seasons left, a former top-15 pick. Each player's fact is built by the rule the
main player's uses (age from the birthdate at the trade date; clause and seasons left from the contract running at the
page; position from the asset; draft position from the prospect inventory). The three measured characteristics
(production, record above the forecast, games share) stay the main player's, as they measure an amount, not a type of
player. Guard: on clubs that received one player, each any-player flag equals the main player's. Reported beside the
main-player figures: all trades; the declared window on the seasons played only; the trades after 2022-03-28; and how
many clubs each characteristic adds. Standard errors clustered by trade. Exploratory, as part C.

Amendment, 2026-11-18 (after the first run of `who_overpaid_any.py`): Thomas made the any-player rule the main one for the
"who is overpaid" regression ("I thought we agreed to switch to just yes or no on the trade types, not by if it's the player
with the highest cap"). v1.1 adds the columns the writeup reports as replications under the main-player rule: the
trade-day grade after 2022-03-28, the loss on WAR in the declared window, and the loss on the seasons played across all
trades. Nothing else changes.

## The categories built from one player, with each taken from any player (declared 2026-11-18, before it was built; Thomas: "yes check all other categories for the any player version")

Script `25_TESTS/groups_any.py`, report only, on `groups_clustered.py`'s club sides (the extended run). Of its fourteen
categories, two are already built from any player received (a no-trade or no-move clause, backtest.py's C6; a former
top-15 pick below the top-15 benchmark, backtest_cuts.py cut 5b) and seven are not about a player. Five are built from
one player, and each gets an any-player version: received a rental (any player received in his final season,
unrestricted at expiry, traded in-season); aged 28 to 31 and aged 32 or over (any player received); a defenceman (any
player received); sold under a new general manager (any player sent whose contract was signed before that manager's first
day, in his first 365 days; the main-player version uses the highest-paid player sent). Each player's facts follow the
rule the one-player version uses (backtest_cuts.py's contract status, ages from the birthdate at the trade date,
backtest_cuts_more.py's general managers). Reported beside the existing figures, standard errors clustered by trade:
(1) each group's mean trade-day grade and realized value (WAR, Game Value), declared window; (2) the outcome-on-price
coefficient c for each group (beyond its price), declared window, WAR and Game Value; (3) the joint regression on all
trades with the five replaced together, robust standard errors. Guards: the one-player figures reproduce
groups_clustered.py's; on sides with one player received (or sent, for the manager), each any-player flag equals the
one-player flag. No other group, test or rule changes.

## Every category and characteristic under both rules, and the change over time on both values (declared 2026-11-18, before it was built; Thomas's notes on the findings document: "Why not just actually do the analysis under both methods?", "You could ask 'did any player have salary retained' or 'did the main player have salary retained'", "Why not use both? Why be inconsistent with how we're measuring this")

Report only; no test or group above changes. Three parts.

1. `25_TESTS/who_overpaid_any.py` v1.2, the "who is overpaid" regression with each rule applied to every characteristic
(Thomas: "In the main player model it should look at the production and etc of the main player acquired, and in the any
player model it should be your recommended option"). Main player rule: every characteristic is the main player's,
including the clause (the main player's contract at the page has a no-trade or no-move clause, backtest.py's rule applied
to him alone). Any player rule: the eight yes-or-no characteristics are 1 when any player received has them (v1.1's
flags); production and the record above the forecast are the totals over every player received; the games share is the
average over the players received, weighted by cap hit. A player's missing production, forecast or games count counts as
zero; the rows are v1.1's 735 club sides. Guards: v1.1's two fits reproduce first; on sides with one player received, the
any-player totals equal the main player's figures and the main-player clause equals the any-player clause. The same eight
columns as v1.1.

2. `25_TESTS/groups_any.py` v1.1, Section 5's categories under both rules. New versions: retained salary (main player rule:
the club kept part of the salary of the highest-paid player it sent; any player rule: of any player sent, backtest.py's
g_retained); a former top-15 pick below the top-15 benchmark (main player rule: the main player received is one, by
backtest_cuts.py cut 5b's rule and benchmark; any player rule: cut 5b's flag); a restricted free agent in his final contract
season (main player received, backtest_cuts.py's status; any player received). One category not about a player is added
to the table: the club whose whole return was picks in rounds 6 and 7 (backtest_cuts.py cut 15's rule). Reported, declared
window, clustered by trade: each group's mean trade-day grade and realized value (WAR, Game Value) and the
outcome-on-price coefficient c. And the joint regression on all trades (groups_clustered.py part 4's design) run twice,
once with every player category on the main player rule (the clause and retained salary included) and once with every
one on the any player rule; the two new groups are not added to it. Guards: v1.0's checks; the any-player retained and
top-15 flags equal groups_clustered.py's; on sides with one player received (sent, for retention), each pair of flags
agrees.

3. `25_TESTS/trend_both.py` v1.0, the change over time: backtest_cuts.py cut 12's trend (per trade, the larger absolute
club net, regressed on the trade's season, 2017-18 to 2025-26) on the trade-day grade and on the realized value (WAR),
with robust standard errors and p-values beside cut 12's resampled interval. Guard: the trade-day slope reproduces cut
12's -0.019. Expected, and stated with the result: realized values of recent trades are partly forecast and have had
fewer seasons to spread out, so the realized trend leans downward by construction.

Amendment, 2026-11-18 (Thomas: "Cap-weighted"): under the any player rule, production, the record above the forecast and the
games share are each the average over the players received, weighted by cap hit, so each describes the type of player
received, as the yes-or-no characteristics do. A player's missing figure still counts as zero; a club whose players
received carry no cap hit takes the plain average. `who_overpaid_any.py` v1.3. The guard on one-player sides is unchanged
(the average of one player is his own figure). Nothing else changes.

## The findings document on the declared window, the price-response correction on the seasons played, and two groups added to the joint regression (declared 2026-11-18, before any new figure was built; Thomas's fourth round of notes on the findings document)

Amendment to what the findings document reports. No test, group or rule above changes; the figures already run stay in
their logs.

1. The declared window throughout (Thomas: "I think it hurts the models credibility to include these trades because
temporally a larger share of trades post 2022 rely on the models projections standing in for realized results"; "I would
do 2017-22 for both trade day and realized value"). Every trade-day grade and realized value the document reports is on
the declared window, 2017-07-01 to 2022-03-28, the window committed before the first run. The trades after 2022-03-28,
and the "fresh trades" check that used them, leave the document. The checks that stay: Game Value in place of WAR, and the
seasons played only.

2. The exception: how prices follow a contract's two parts (`who_overpaid_checks.py`; Thomas: "the finding about how the
trades respond to contract value shouldn't be changed", then "All trades, played seasons"). It keeps all trades. The price
is set on trade day; its correction for error in the models' value is the two-stage fit instrumented by the performance
value over the seasons played only (no forecast enters it), already run (v1.1). That fit becomes the headline in place of
the one instrumented by the delivered value, which counts the forecast seasons of recent trades.

3. New figures, all on the declared window, report only:
   a. `who_overpaid_any.py` v1.4: two more columns under both rules, the trade-day grade and the realized value on Game
      Value in the declared window; and the number of clubs there with two or more players received. Guards unchanged.
   b. `groups_any.py` v1.2: the joint regression with one rule throughout (part 4's design) on the declared window, with
      two groups added (Thomas, on "Not in the regression": "Well it really should be added to the regression"): a
      restricted free agent in his final contract season (main player rule: the main player received; any player rule:
      any player received; v1.1's flags) and the club whose whole return was picks in rounds 6 and 7 (v1.1's flag, the
      same under both rules). A group with fewer than five non-zero differences drops out, as in part 4. Guard: the same
      code on all trades without the two groups reproduces part 4's fits.
   c. `trend_both.py` v1.1: the change over time on both values, also on the declared window's seasons (2017-18 to
      2021-22). Guard unchanged (the all-trades trade-day slope, -0.019).
   d. `who_overpaid.py` v1.1: part A's joint regression with the main player's cap hit, the futures-for-players
      coefficient on the declared window (it already logs the cap hit's coefficient there). Guard: the all-trades figures
      (-0.14 trade-day, -0.10 realized WAR) reproduce.
   The cap-dump figures are read from `backtest_cuts_more.py`'s existing declared-window line.
   Added the same day, before these were run: to read the declared-window joint regression, `groups_any.py` v1.2 also logs,
   under each rule, (i) how many late-picks-only clubs are also futures-for-players clubs, and the sum of the two groups'
   coefficients with its robust 95% interval; (ii) joint_regression.py's "deadline rental for picks and prospects" profile
   (rental + deadline buyer - futures for players) on this fit, with its robust 95% interval.

## Handedness, size, playoff performance and birthplace (declared 2026-11-18, before it was built; Thomas: "I want to see handedness, size, playoff performance, and European or not"; "Both terms", "Height and weight", "Fetch spring 2017")

Script `25_TESTS/traits_test.py`, report only, on `who_overpaid_any.py` v1.4's club sides in the declared window (431),
both rules, standard errors clustered by trade. Outcomes: the trade-day grade, the realized value on WAR, on Game Value,
and on the seasons played only. Each player's facts, by his NHL id (PuckPedia's contract export, the model's own contract
provider; one row a player):
- right shot: PuckPedia `shoots` is "right" (a goalie, or a player with no recorded side, counts as no);
- right-shot defenceman: right shot and the asset's position D;
- height (inches) and weight (per 10 lb), PuckPedia `height` and `weight`;
- born in Europe: PuckPedia `country` (birth country) is neither Canada nor the USA; unknown counts as no;
- playoff points: his points in the most recent NHL playoffs completed before the trade date (zero if he played no game
  in them). The 2018-2022 playoffs from the game logs (`skater_games`, game type 3); the 2017 playoffs from the NHL's
  public stats API (skater summary, 2016-17, game type 3), fetched once and saved under `10_SOURCE/raw/`. Guard: the API's
  2017-18 playoff points equal the game logs' for every player.
Main player rule: the main player's facts. Any player rule: the yes-or-no facts are 1 when any player received has them;
height, weight and playoff points are averages over the players received weighted by cap hit (as the other measured
characteristics, v1.3), over the players whose figure is known.
Reported: (1) each new term alone (the outcome on that term alone); (2) all of them added together to the Section 3
regression, with every existing characteristic held; the clause, age 28 to 31 and defenceman coefficients in that
extended fit beside v1.4's. Guard: on the same rows, the fit without the new terms reproduces v1.4's declared-window
coefficients. A new term is a finding by the document's rule (statistically significant at the 5% level, same sign, on
the trade-day grade and the realized value); Game Value and the seasons played are its checks.

## Age 28 and over in place of the two age bands (declared 2026-11-18, before it was built; Thomas: "Replace 28-31 and 32+ with just 28+, I'm mostly just curious if the way you define the age bands affects anything")

Report only, a sensitivity of the age bands; nothing reported changes. One yes-or-no term, aged 28 or over at the trade
date (the main player's, or any player received), replaces the two terms aged 28 to 31 and aged 32 or over; every other
term, row, rule and standard error unchanged. Run in both regressions on the declared window: (1) the who-is-overpaid
regression (`25_TESTS/age_band_test.py`, on `traits_test.py`'s rebuilt rows; guard: the two-band fit reproduces
`who_overpaid_any.py` v1.4), outcomes the trade-day grade and the realized value on WAR, Game Value and the seasons played;
(2) the joint regression (`groups_any.py` v1.3, part 6, on part 5's design; guard: part 5's fit reproduces), the trade-day
grade and the realized value on WAR and Game Value. Reported: the 28-and-over coefficient beside the two bands', and the
clause and defenceman coefficients in each fit. A player whose age is unknown counts as no, as in the two-band flags.

## One regression in place of two (declared 2026-11-19, before it was built; Thomas: "It seems strange to have a section 3 regression and a section 4 regression, especially when the two regressions share a variable which turns out to be a finding in one but not the other"; "let's see the results of this change")

Report only until Thomas decides whether it replaces the two; nothing reported changes yet. Script
`25_TESTS/one_regression.py`. Design: `groups_any.py` part 5's (each two-team trade once, the first club's value on the
differences between the two clubs, no constant, robust standard errors), on the declared window, under each rule, with
every Section 3 player characteristic added to every type of trade.
- Types of trade (part 5's, by the rule): selling a player for picks and prospects, the deadline buyer, the other in-season
  buyer, rental, retained salary, a former top-15 pick below the top-15 average, one asset for two or more, taking a
  contract to clear cap, a new general manager selling his predecessor's player, a restricted free agent in his final
  season, only picks in rounds 6 and 7.
- Player characteristics (who_overpaid_any.py v1.4's, by the rule): aged 28 to 31, aged 32 or over, defenceman, clause,
  signed as an unrestricted free agent, two seasons left, three or more seasons left, former top-15 pick, production, record
  above the forecast, games share. Each appears once (part 5's age, defenceman and clause flags are the same
  characteristics and are not entered twice; guard: they equal who_overpaid's on every side with a player).
- A club that received no player valued by the player model: every player characteristic 0, and a "received a player"
  indicator (0 or 1) enters. A club that received such a player with any characteristic unknown: the trade is dropped
  (counted and reported).
- Outcomes: the trade-day grade, the realized value on WAR, on Game Value, and on the seasons played only.
- Guard: the same code with the player characteristics removed and no trade dropped reproduces part 5's coefficients.
- `groups_any.py` v1.4 writes each side's flags (`groups_any_sides.csv`) for this script; no figure of its own changes.
Reported: every coefficient under both rules, and which meet the document's finding rule (the trade-day grade and the
realized value statistically significant at the 5% level, same sign), with Game Value and the seasons played as checks.
Amendment, 2026-11-19 (Thomas: "there's probably a lot of multicolinearity going on with the two different top 15 pick
variables, so one of them has to be dropped. Drop the below average one"): `one_regression.py` v1.1 drops the former top-15
pick below the top-15 average from the merged regression under both rules; the former top-15 pick stays. v1.1 also logs the
correlation between the two terms' differences in v1.0's rows. Nothing else changes; guard 2 still reproduces part 5 with
all its terms.
Decided, 2026-11-19 (Thomas: "Yes, rewrite"): the merged regression (`one_regression.py` v1.1, without the below-average
top-15 term) replaces the two regressions in the findings document. Its rows, terms and finding rule are as declared above;
the document's player-characteristic and types-of-trade tables both come from it. The categories' averages on their own
(Step 4) are unchanged.

## Recovering the trades the one regression left out (declared 2026-11-19, before it was built; Thomas: "Go and try to reconcile this. I want as many usable trades in the sample as possible")

`one_regression.py` v1.1 left out 125 of 556 trades: 154 club sides whose main player had an age, recent WAR, record above
the forecast or games share missing. The causes, counted: goalies (54 sides; the back-test leaves their recent WAR blank
by design and the skater forecast has none); players traded as rights or on buried contracts (24; the back-test fills no
recent WAR for those asset types); players on the 2017 page (84; the saved forecasts start at 2018, and most of these
players have no NHL id in prospect_values, so no birthdate or games share was looked up). v2.0 fills each fact from data
the model already holds, in this order, and only where it was missing; every fact already known stays as it was.
- Name: backtest_assets' WAR spelling, else page_2017_values' war_name, else the asset's name. NHL id: prospect_values,
  else traded_player_values, else page_2017_values.
- Birthdate: by NHL id (contract_level_spine, WAR_with_age, goalie_birthdates), else by name (WAR_with_age for skaters,
  goalie_birthdates for goalies), one value required. Age at the trade date as before.
- Recent WAR: the back-test's own rule (backtest.trailing_total: 50/30/20 over the three seasons before the page, seasons
  of 10+ games, rescaled), on the WAR table found by name (backtest.seasons_for's spelling rule); goalies on the goalie WAR
  table, the same rule. No qualifying season: 0.
- Forecast for the season of the trade: skaters, the player model's at the page (xnpv1_forecasts.csv; for the 2017 page,
  skater_forecast.ContractForecaster's page 2017, fitted here and written to 30_OUTPUT/xnpv1_forecasts_2017.csv); goalies,
  the goalie model's forecast_war at the page (goalie_value_spine_v2.csv). No forecast: 0 (v1.3's rule for the any player
  rule's measures). Record above the forecast = recent WAR - forecast.
- Games share: the season before the page, as now (by NHL id in WAR_with_age), else from the WAR table by name; goalies
  from the goalie WAR table. No games: 0.
- Seasons left, 2017 page, where the contract spine has no 2017 row: page_2017_values' contract_last_season - 2017 + 1.
The any player rule's per-player facts are filled the same way. A trade is still left out only when a main player's
birthdate cannot be found. Guards: on every fact already known, the filling rule reproduces it (recent WAR, forecast,
games share, age bands); the guards of v1.1 stay. Reported as v1.1 was, beside v1.1's figures.
Amendment, 2026-11-19, before the regression was run with the filled facts: building the fill showed that every goalie's
games share was 0 in who_overpaid and player_facts (both read WAR_with_age, a skater table). Goalies were never main players
in the fits run so far (their recent WAR was blank), but under the any player rule a goalie received beside a skater
pulled the club's cap-weighted games share down. facts_fill.py v1.1: a goalie's games share is read from the goalie WAR
table, by name, the same season and rule, replacing the 0; a skater's missing games share is read by NHL id where one was
recovered (who_overpaid's rule), and by name only where none was.

## Is the clause finding another finding in disguise? (declared 2026-11-19, before it was built; Thomas: "What are the chances that the clause finding is a different finding in disguise? ... clause players are players who are of a higher reputation in the league, they may carry higher cap hits, they may be more likely to become cap dumps")

Report only. Script `25_TESTS/clause_disguise.py`, on `one_regression.py` v2.0's 556 two-team trades in the declared window,
both rules, the same design, outcomes and robust standard errors.
1. Profile: clubs whose main player has a clause against those whose main player has none (main player rule): mean cap hit,
   age, seasons left, recent WAR, record above the forecast, share signed as an unrestricted free agent, share former
   top-15 picks, share of the clubs that took the contract to clear cap, share at the deadline.
2. The regression with the contract's cost added, each alone, then together, as separate fits: (a) the cap hit ($M;
   main player rule: the main player's; any player rule: the total over the players received); (b) the present value of
   the cap hit over the seasons left ($M at the 2025-26 cap, who_overpaid.build's `cost`; any player rule: the total);
   (c) both. Reported: the clause, age 28 to 31 and cost coefficients in each fit, beside the fit without them.
3. Cap dumps: the regression without the trades where a club took a contract to clear cap; the clause coefficient.
A clause "in disguise" is read as: its coefficient on the trade-day grade and on realized value is no longer
statistically significant at the 5% level once a cost term is held. The cost term was left out of the main regression on
purpose (a contract's value is its performance less its cost, so holding cost constant asks a different question); this is
a reading of the finding, not a change to the specification.
Added the same day, before anything was built (Thomas: "Maybe a clause is indicitive of a reputation, so teams overpay for
reputation and that appears in the form of a trade clause"): 4. Reputation. Two measures of a player's track record, from the
WAR table by name (backtest.seasons_for, goalies on the goalie table), every season before the page: career WAR (the sum),
and his best single season's WAR. Under the any player rule each is the cap-weighted average over the players received, as
the other measures. Each is added to the regression alone, then the two together, then with the cap hit; the clause, age
28 to 31 and reputation coefficients reported. Read with 2: if the clause stops being statistically significant once
reputation is held, it is a marker of reputation; if only once the cap hit is held, a marker of an expensive contract.

## A goalie indicator in the one regression (declared 2026-11-19, before it was built; Thomas: "the only positional dummy variable is Defence. So the state is: Defenceman, or Forward or Goalie. That probably isn't correct"; "yes add the goalie indicator and rerun")

Since the facts were filled (facts_fill.py), 54 clubs' main players are goalies, and 32 main players have no position in
backtest_assets, so both were compared as forwards. `facts_fill.py` v1.2 fills a missing position, in order: page_2017_values'
position, PuckPedia's position by NHL id, WAR_with_age's position by name, and goalie when the name is found in the goalie WAR
table only; each mapped to forward, defenceman or goalie. `one_regression.py` v2.2 adds a goalie indicator beside the
defenceman one under each rule (main player rule: the main player is a goalie; any player rule: any player received is), so
each position is compared with forwards. Guard: positions already known are unchanged. Everything else as v2.0. Reported
beside v2.0; `clause_disguise.py` rerun on it (v1.1, reading the same frame). The findings document is not changed until
Thomas has seen the result.
