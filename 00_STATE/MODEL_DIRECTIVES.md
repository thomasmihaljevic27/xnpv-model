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
- **Also directed (Thomas, 2026-10-04): "We are not using fitted decay."** This applies to every
  trailing total in the model. The games-share and chance-of-playing regressions, which read the
  same trailing total, therefore move to 50/30/20 too. Their other terms, including the trailing
  total above one win, are not covered by this entry and stay unless Thomas directs otherwise.
- **What this overrides in `Data, Production, and Aging.docx`, Section 3** (confirmed by Thomas):
  - Step 1's decay chosen from the data;
  - Step 2's eight-term regression, its coefficient table, and its worked numbers (the 27-year-old
    examples and Marchessault's 2.37).
  - Kept: Step 2's opening paragraph on why a pull is needed.
  - To re-measure after the switch: the evidence paragraph (2.3%) and the star paragraph (-0.26).
- **Status:** directed. Code unchanged.

---

## 2. The aging curve measures each player's level with 50/30/20 over three seasons

- **Date:** 2026-10-04, while reading the xNPV 1 documents line by line.
- **Thomas's words:** "Add to the ledger", directing the result below after asking why the curve
  averages two seasons equally when weighting improves other parts of the model.
- **What it means:**
  - The comparable-player curve measures each player's level at each age as 50% × his rate per 82
    at that age + 30% × the age before + 20% × the age before that. Only seasons of 20 games or
    more count. The weights are rescaled over the seasons he has, so a missing season is not a
    zero. The weights are plain: no games weighting.
  - This one measure is used everywhere the curve uses a level:
    - the "recent rate" measure in the profile that finds comparable players;
    - the year-to-year changes the forecast adds (a comparable's level at the next age minus his
      level at this age);
    - the comparable players' level that makes up entry 1's 35%.
  - Departed players: a player with no NHL season the next year is entered with that season at
    replacement level (rate 0), averaged by the same 50/30/20 rule.
  - Unchanged: the comparables pool rule (two consecutive 20-game seasons), the other profile
    measures (style, ice time, trend), the yardstick, the weighting formula, and the league weight
    of ten.
- **What the code does now (not yet changed):** `aging_curve.py` uses the equal average of the last
  two consecutive 20-game seasons (`WIN = 2`), and `skater_forecast.imputed_aging_model` enters a
  departure as (last rate + 0) / 2.
- **Evidence:** `25_TESTS/aging_level_weights_test.py` v1.0, valuation dates 2015-2021:
  - The starting level is unaffected: all four versions tie (1.1501-1.1506).
  - Aging only, one to five seasons out: 1.3610, against 1.3642 for the equal two-season average,
    lower in 1,999 of 2,000 resamples. Whole forecast: 1.3596 against 1.3642, lower in 2,000.
  - Slightly worse one season out (1.2620 against 1.2603); better from two seasons on.
  - 60/40 over two seasons was worse than the equal average. Games weighting added nothing.
- **Status:** directed. Code unchanged.

---

# To investigate (Thomas's list; nothing here is directed)

Questions Thomas wants looked into before he decides. An item moves to the directives above only
when he directs it.

## A. The yardstick: one per position, and no self-pairs

- **Raised:** 2026-10-04, reading the yardstick sentence in `Data, Production, and Aging.docx`.
- **Background:** the meeting with Karl (aging review, 2026-10-02) agreed to two changes:
  - a separate yardstick for forwards (2.48) and defencemen (2.56), instead of the pooled 2.53;
  - no self-pairs, so a player is never measured against his own other seasons when the yardstick
    is built.
  Neither was made, and no decision was recorded.
- **Already known:** both were tested on 2026-09-28 (`Model_Changes_September_2026.md` §3), and
  each moved forecast error by under 0.01% (the "about 1%" said in the meeting was wrong). That
  test ran on the old model, before entries 1 and 2.
- **Thomas's view:** "sounds like a lot of hoopla for nothing."
- **To investigate:** re-score both changes on the curve as entries 1 and 2 define it. If they
  still move nothing, close the item and report the test in the paper as a robustness check. If
  Thomas directs either change, it rides on the same rebuild as entries 1 and 2 (the price line is
  re-locked once).
- **Until then:** the code and the model keep one pooled yardstick, self-pairs included.

## B. The league average inside the comparables' estimate: who needs it, and can it go?

- **Raised:** 2026-10-04, reading "Stabilizing the estimate with the league average" in
  `Data, Production, and Aging.docx`.
- **Background:** the curve mixes the comparables' average with the league average for the same
  position and age, at a fixed weight of ten (`aging_curve.SHRINK_K`). It does so for the
  comparables' level (entry 1's 35%) and for each year-to-year change.
- **Already known** (2026-09-28 test, old model, held-out careers; change in error against ten):
  0.01 (effectively removed) +0.02%; 5 -0.02%; 20 +0.04%; 50 +0.16%; a fixed 5% share +0.04%; a
  fixed 10% share +0.07%. Increasing it never helped. On the directed starting level, comparables
  alone were slightly better than with the league blend (1.1497 against 1.1502, lower in 1,770 of
  2,000; `starting_level_simple_test.py` v1.1). On curves refitted per valuation date, the league
  average carries a median 11-14% of the estimate at the start of the walk and 17-23% at its end.
- **Thomas's questions:** are there players it is genuinely useful for? Would more of it help?
  Would anything be lost by removing it?
- **To investigate:** on the curve as entries 1 and 2 define it, compare today's weight of ten
  with "comparables only, and the league average only where no comparable has a value at that age"
  (a fallback is needed there, because the average does not exist). Score the starting level and the
  rate one to five seasons out, broken out by the league average's share of the estimate, by age
  band (under 22, 22-34, 35 and over), and by seasons ahead.
- **Until then:** the code and the model keep the weight of ten.
