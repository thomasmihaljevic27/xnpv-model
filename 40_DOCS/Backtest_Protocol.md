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

## Limits stated in advance

- The outcome uses Bacon's WAR, the same source as the forecast. The Game Value check (the locked circularity
  validators) is the next step; no group finding is called systematic before it.
- The 2026-27 re-valuation is itself a forecast; it is largest for the 2022-2025 picks.
- A club's own gains (fit, playoffs, a Cup) are outside the currency: regular-season wins only.
- Multiple groups: seven groups and two class tests; a single p below 0.05 among them is weak evidence alone.
