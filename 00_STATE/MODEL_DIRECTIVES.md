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

## 3. One own-versus-comparables blend: 65/35 replaces the aging curve's 55/45

- **Date:** 2026-10-04, while reading the xNPV 1 documents line by line.
- **Thomas's words:** "Add it to the ledger as a directive", directing that the curve's 55/45 be
  replaced by his 65/35 so the model has one blend.
- **What it means:**
  - The model has exactly one weighting of a player's own level against his comparables' level:
    65% own, 35% comparables, as entry 1 defines it.
  - The aging curve's own 55/45 starting level (`aging_curve.LAMBDA = 0.55`) is replaced by that
    65/35, so the curve and the starting level use the same weights and the same measure (entry 2:
    50/30/20).
  - The forecast still adds the curve's year-to-year changes to the starting rate (unchanged: the
    changes are added in rate units, not applied as percentages).
- **What the code does now (not yet changed):** `aging_curve.py` blends 55% own and 45% comparables
  in `AgingModel.project`; xNPV 1 reads only the curve's changes, so that blend has no effect on any
  value today.
- **What this overrides in `Data, Production, and Aging.docx`, Section 4:** the paragraph saying the
  curve computes a 55/45 starting level that the model does not use. Under entries 1 and 3 the
  starting-level section states the single 65/35 blend once. Marchessault's 2.37 and his forecast
  rates (2.00, 1.76, 1.56, 1.12) change once the code is changed.
- **Note:** with the curve's 55/45 replaced, the curve's own starting level becomes the model's
  starting level before the one-year step to the valuation season (entry 1, open detail 3).
- **Status:** directed. Code unchanged.

---

## 4. Contract length (term) is in the price line: term-in, with term-free as the sensitivity

- **Date:** 2026-10-04, reading the price-line equation in `Pricing, Control Years, and Contract
  Value.docx`. This restores Decision A, which Thomas locked on 2026-09-15.
- **Thomas's words (2026-10-04):** "I swear to god we agreed that term needed to be in this
  equation"; then "Add it to the ledger as a directive."
- **The 2026-09-15 decision, as recorded:** "Decision A locked by Thomas: term-in (the security of a
  long deal is part of what the club bought; term-free retained as the required sensitivity)"
  (`DECISIONS.md`, change log 2026-09-15k; `40_DOCS/model_evidence/Phase4_Decisions.md`).
- **What it means:**
  - The price line includes contract length: a club pays for the security of a long deal, so the
    line prices production signed for a given term.
  - Contract values are reported term-in. Term-free values (no length in the line) are reported
    beside them as the required sensitivity.
  - Term is not production. This is consistent with the July Stage 2 null (length did not predict
    later production): term-in prices the security, not more wins.
- **How it was lost:** the term-in line was built in the rebuild (`production_currency.py`) and
  recorded as "taken inside the tree only... not adopted into production" (`PROJECT_STATE.md`).
  D33 kept "the Stage 3 price per win", and the 2026-10-02 re-fit used the Stage 3 specification,
  which has no term. Neither step flagged that this overrode Decision A.
- **What the code does now (not yet changed):** `xnpv1_price_line.py` fits cap share = alpha +
  (beta + beta_D x defence) x forecast WAR, with no term, and `XNPV1_RATE` is locked on that line.
- **Details not yet settled by Thomas:**
  1. *How term enters the line:* for example a linear term in years, as the July Stage 2
     specification had ($0.82M a year at the 2025-26 cap on the trailing total), or the rebuild's
     form; and whether term interacts with the defence slope or the RFA status.
  2. *How term enters each season's value:* term-in must not add the term premium to each season
     whatever the player produces (the rebuild's first attempt priced Brent Seabrook's 0.20
     forecast wins at $47.2M). The rebuild's resolution: the replacement a contract is compared
     against is a player signed for the remaining term. The exact rule for this model is to be
     set before any code changes.
  3. *Control years:* whether the RFA control years are priced term-in, and at what term.
- **Knock-ons once implemented:** the price line is re-fitted and re-locked; aggregate value moves
  by billions (term-in added $3.3-4.1B across 2,591 contracts in the 2026-09-14 test); the
  defence-premium question (WORK_QUEUE) is re-read on the new line (the rebuild's term-in line put
  the defence premium in an intercept, not the slope).
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

## C. Departed players in the aging curve: the assumed zero and its gaps

- **Raised:** 2026-10-04, reading the departures paragraph in `Data, Production, and Aging.docx`.
- **Background:** a comparable with no NHL record the next season is filled in as if he had played
  it at replacement level (rate 0 per 82), smoothed like any other season, and the league-average
  changes are recomputed with these filled-in seasons (`skater_forecast.imputed_aging_model`; 1,071
  on the 2024 valuation). Under entry 2 the zero would carry 50% of the 50/30/20 level.
- **Already known:**
  - On the comparable-player curve (the one in use), only on/off was tested: season-WAR RMSE 0.8621
    without, 0.8619 with (`Obvious_Fixes_Test.md`, 2026-09-30). The value zero was never varied.
  - On the rebuild's fitted aging equation (not in use), zero was argued before the run and then
    swept: error five seasons out 0.4338 at -0.50, 0.4221 at -0.25, 0.4171 at 0, 0.4200 at +0.25
    (`Phase3_Survivorship.md`, 2026-09-15). Reweighting the survivors instead made the curve worse.
- **Gaps to investigate**, on the curve as entries 1 and 2 define it:
  1. Sweep the assumed level (for example -0.50, -0.25, 0, +0.25) on the comparable-player curve.
  2. Returning players: a player absent one season who returns is filled in at zero today. The
     rebuild used his real return instead (291 of 1,695 absences there); test that here.
  3. Short seasons: a player with 1-19 games the next season is neither filled in nor measured
     (the curve needs 20 games), so he drops out, a milder form of the survivor bias this rule
     exists to fix. Test filling him in, or measuring him on his short season.
  4. A possible double count: the rate is "if he plays", and the chance of playing already lowers
     each season for the risk he leaves. Filling departures in at zero also lowers the "if he
     plays" rate for that same risk. Examine whether leaving is counted twice, and score the
     forecast with and without the filled-in seasons under the full model.
- **Until then:** the code and the model keep today's rule.

## D. The games-share equation's form

- **Raised:** 2026-10-04, reading the games-share equation in `Data, Production, and Aging.docx`.
- **Background:** for each season ahead, the games share is a straight-line regression on the
  trailing games share, defence, experience, age - 27, the trailing total, and the trailing total
  above one win (`skater_forecast.GP_FEATURES`). The prediction is then capped at 1.0 (a full
  season) and floored at 0.05. Age - 27 is centering only: it moves a constant into the intercept and
  changes no forecast.
- **Already known:** the form was never tested; the only test added the two level terms (season-WAR
  RMSE 0.8640 to 0.8596, in a version with the fitted aging equation). In the current run the cap
  binds on 0.26% of 47,940 forecasts zero to five seasons ahead (1.5% four seasons out); the floor
  never binds (lowest forecast 0.23); the mean share is 0.68 (about 56 games).
- **Thomas's point:** a share should approach a full season, not be able to exceed it.
- **To investigate:**
  1. A fractional logit (a logistic curve fitted to the share, so predictions stay between 0 and 1
     without a cap; Papke and Wooldridge, 1996) against the straight line plus cap.
  2. A curved age effect against the straight line.
  Score the games share and season WAR on development pages; the cap binds rarely, so expect a
  small effect.
- **Until then:** the code and the model keep the straight line with the cap and floor.
