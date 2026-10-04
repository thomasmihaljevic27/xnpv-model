# MODEL DIRECTIVES — what Thomas has explicitly directed

This is Thomas's own record of how the model is meant to work. Each entry is a decision he made
explicitly, in his words, with what it means exactly and whether the code does it yet. The model
must match these entries. Nothing enters this list unless Thomas states it; nothing is
implemented from it without his go-ahead.

Status values: **directed** (decided, code not changed yet), **implemented** (code matches, with
the commit), **superseded** (replaced by a later entry).

---

## 1. The starting level: 50/30/20, pulled 65/35 toward comparable players

- **Date:** 2026-10-04, while reading the xNPV 1 documents line by line.
- **Thomas's words:** "50/30/20 previous season weighting pulled towards player comparables. 65% is
  50/30/20 of the players per 82 game WAR from the three previous seasons, 35% is comparable
  players."
- **What it means:**
  - Take the player's WAR per 82 games in each of the three seasons before the valuation season,
    and weight them 50% (last season), 30% (the season before) and 20% (the one before that).
  - Starting level = 65% × that weighted rate + 35% × the comparable players' level.
  - No weights chosen from the data. No league average in the blend.
- **What the code does now (not yet changed):** `skater_forecast.py` builds the starting level from
  an eight-term regression on a trailing total whose weights' decay is chosen from the data on each
  valuation date (47/32/21 from 2016). The games-share and chance-of-playing regressions read the
  same trailing total.
- **Evidence:** `25_TESTS/starting_level_simple_test.py` v1.1, valuation dates 2015-2021:
  - 50/30/20 was the best of nine simple three-season weightings.
  - 65/35 toward comparable players was the best pull. A three-way blend put 0% on the league
    average.
  - It is 0.9% higher in error than the current start (1.1502 against 1.1398).
- **Details not yet settled by Thomas** (the test used the first option in each):
  1. *Seasons with different games played:* the test weighted each season by 50/30/20 times its
     games played, so a 20-game season counts for less than a full one. The alternative is plain
     50/30/20 on the three per-82 rates. The test found the games-weighted version slightly better
     (1.1683 against 1.1708).
  2. *Which comparable-player level:* the aging curve's existing estimate (the comparables blended
     with the league average for his position and age at a weight of ten comparables), or the
     comparables alone. They tied in the test (1.1502 against 1.1497).
  3. *The step to the valuation season:* the test added the comparables' one-year change from the
     player's last season's age to the valuation season. Without it, the error was 1.1599 against
     1.1502.
  4. *Fewer than three seasons:* the test renormalized over the seasons a player has (a missing
     season is not a zero), so two seasons are weighted 50/30 and one season stands alone.
- **Status:** directed. Code unchanged.
