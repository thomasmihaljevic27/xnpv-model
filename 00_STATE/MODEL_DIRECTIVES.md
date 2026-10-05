# MODEL DIRECTIVES — what Thomas has explicitly directed

This is Thomas's own record of how the model is meant to work. Each entry is a decision he made
explicitly, in his words, with what it means exactly and whether the code does it yet. The model
must match these entries. Nothing enters this list unless Thomas states it; nothing is
implemented from it without his go-ahead.

Status values: **directed** (decided, code not changed yet), **implemented** (code matches, with
the commit), **superseded** (replaced by a later entry).

## Summary (2026-10-04)

| # | Directive | Status |
|---|---|---|
| 1 | Starting level: 50/30/20 per-82 WAR over three seasons, pulled 65/35 toward comparable players; no fitted decay anywhere | directed |
| 2 | The aging curve measures each player's level with 50/30/20 over three seasons, games-weighted (changed from plain 2026-10-04c) | directed |
| 3 | One own-versus-comparables blend: 65/35 replaces the curve's 55/45 | directed |
| 4 | Contract length in the price line (term-in), term-free reported as the sensitivity | directed |
| 5 | Price-line forecasts dated at each contract's signing | directed |
| 6 | Draft and prospect models restart from scratch with Karl; the data is kept | directed |

| | To investigate (closed list) | Status |
|---|---|---|
| A | The yardstick: one per position, and no self-pairs | open |
| B | The league average inside the comparables' estimate | open |
| C | Departed players in the aging curve: the assumed zero and its gaps | open |
| D | The games-share equation's form | open |
| E | The chance of playing for players under contract | open |
| F | Re-run the Game Value checks on the model as directed | after directives 1-5 are built |

The plan of record (order of work) follows this summary. Open decisions (Thomas's to make; listed at the end): the control-year weight; when contract status
is read for a contract valuation; the price of a delivered win. Unsettled details sit inside
directives 1 and 4.


## Plan of record: the order of work (Thomas, 2026-10-04)

Several items cannot be settled until some directives exist in code, so the work runs in this
order. The price line (the expensive step: re-fit, re-lock, re-run the valuations) is built once,
at step 6.

1. **Build the forecast directives (1, 2, 3) in code, on a branch.** First settle directive 1's
   details 1, 3 and 4 (games weighting of seasons, the one-year step to the valuation season,
   players with fewer than three seasons), one at a time with Thomas. Do not re-fit the price line
   yet; values stay provisional on the branch. Every later test runs on this real code, not on a
   separate test copy.
2. **Investigations A, B and C on that branch, as one script** (all three change the same curve).
   B also settles directive 1's detail 2 (which comparable-player level).
3. **Investigation D, and investigation E together with open decision 2.** Independent of A-C (both
   need only directive 1's 50/30/20 trailing total); can run alongside step 2.
4. **Open decision 1 (the control-year weight)**, after E's result.
5. **Fix the forecast:** add whatever Thomas adopts from steps 2-4 to the directives and the branch.
6. **Pricing:** settle directive 4's details; directives 4 and 5 as one price-line re-fit and
   re-lock; re-measure the qualify rates and control-year weights on the final forecast; re-run the
   valuations and the dashboard; update the documents.
7. **Checks:** investigation F, and the price-line specification tests on the new line (straight
   line, contract length, RFA/UFA, stability). Decide how the changed model is validated: the
   2022-2025 confirmation was a one-time run on the old forecast and cannot simply be repeated.
8. **Open decision 3 (the price of a delivered win)**, which unlocks directive 6 (the draft and
   prospect restart with Karl).

**Next step:** step 1, the build: directives 1-3 in code on a branch. Details 1, 3 and 4 settled
(2026-10-04c/2026-10-05: games-weighted on both sides; the step to the valuation season; rescale over
the seasons he has). Detail 2 waits on investigation B (step 2), which was widened with C to cover the
comparables' level for thin histories.

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
     - *Thomas, 2026-10-04 (session 2026-10-04c):* "if this is going to be games weighted then the
       comparable's level should be as well. i want them to be the same. create a test script for
       that." The own rate and the comparables' level use one weighting, plain or games-weighted,
       chosen on `25_TESTS/level_games_weighting_test.py` v1.0.
     - **Settled (Thomas, 2026-10-04c): games-weighted on both sides.** Each season's weight is
       50/30/20 times its games played, for the player's own rate and for the curve's level
       (directive 2 changed with it). Evidence (laptop, development pages 2015-2021, 6,916
       player-pages by 1,609 players; with the step to the valuation season): start RMSE 1.1506
       against plain's 1.1526, whole forecast one to five seasons out 1.3598 against 1.3618;
       games-weighted lower in 1,827 and 1,802 of 2,000 career resamples (under the 1,950 bar).
       Lower on 7 of 8 RMSE/MAE cells (without the step, whole MAE is 0.0001 higher). The gain
       comes from the own side: games-weighting the curve alone is slightly worse than plain
       (1.3621 against 1.3618), and costs 0.0002 against weighting the own side alone (1.3598
       against 1.3596). It sits in players with a recent season under 41 games (start 1.1382
       against 1.1469; elsewhere 1.1558 against 1.1550).
     - *Minimum games (Thomas, 2026-10-04):* a season counts toward the player's own 50/30/20 rate
       at 10 games or more ("10 games, as tested"; `forecast_config.MIN_GP`). The curve keeps its
       20 (directive 2).
  2. *Which comparable-player level:* the aging curve's existing estimate (the comparables blended
     with the league average for his position and age at a weight of ten comparables), or the
     comparables alone. They tied in the test (1.1502 against 1.1497).
  3. *The step to the valuation season:* the test added the comparables' one-year change from the
     player's last season's age to the valuation season. Without it, the error was 1.1599 against
     1.1502.
     - **Settled (Thomas, 2026-10-04c): take the step.** The start (65% own + 35% comparables) is
       moved from his last counted season's age to the valuation season by the curve's own changes
       over that gap (one year, or more after missed seasons): the comparables' changes blended with
       the league average at weight ten, or the league-average change for his position and age where
       he has no 20-game profile. Evidence (`level_games_weighting_test.py` v1.0, laptop, games-
       weighted both sides): start RMSE 1.1506 with the step against 1.1611 without; whole forecast
       1.3598 against 1.3689; the step lower on 36 of 36 RMSE/MAE cells across the four arms. No
       resample count for this pair. Under directive 1 nothing else ages the start (the fitted
       start's age terms go).
  4. *Fewer than three seasons:* the test renormalized over the seasons a player has (a missing
     season is not a zero), so two seasons are weighted 50/30 and one season stands alone.
     - *Thomas, 2026-10-05 (session 2026-10-04c): check first.* On the development pages 1,881 of
       6,916 valuation rows (27%) have one counted season (median 29 games; 948 under 30 games),
       1,409 two, 3,626 three. The 2026-10-04 run found the start running high (+0.110 per 82) where
       the shortest counted season is under 41 games, a group mixing thin histories with three-season
       players. `25_TESTS/thin_history_check.py` v1.0 (laptop run owed) scores the directed start's
       error and high/low bias by seasons counted, by games in a lone season, by total trailing games
       and by seasons since the last counted one, with the own-alone and comparables-alone biases.
       Missing = zero was put to Thomas and not chosen (it scores junior, AHL and injury years as
       replacement-level NHL play).
     - **Settled (Thomas, 2026-10-05): rescale, as tested.** Result (laptop, reproduction PASS):
       the own rate is not what runs high for thin histories (own rate alone, start bias: one season
       +0.053, a lone 10-19-game season +0.000, all rows +0.054). The directed start does run high
       for them (one season +0.166 [+0.069, +0.257]; two seasons +0.100; three seasons -0.008),
       and the excess comes from the comparables' level (alone: one season +0.374, a lone 10-19-game
       season +0.561, trailing games under 41 +0.581). That problem went to investigations B and C
       (widened 2026-10-05), not to this detail.
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
    zero. Each weight is multiplied by that season's games played (Thomas, 2026-10-04c, so the
    curve's level matches the own rate in directive 1; this replaces "plain: no games weighting").
  - This one measure is used everywhere the curve uses a level:
    - the "recent rate" measure in the profile that finds comparable players;
    - the year-to-year changes the forecast adds (a comparable's level at the next age minus his
      level at this age);
    - the comparable players' level that makes up entry 1's 35%.
  - Departed players: a player with no NHL season the next year is entered with that season at
    replacement level (rate 0), averaged by the same 50/30/20 rule. Under games weighting that
    filled-in season counts as 82 games (as tested; `aging_level_weights_test.build_curve`), so the
    zero weighs as a full season. A setting carried in by the test, not chosen by Thomas;
    investigation C examines departures.
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

## 5. The price line is fitted on forecasts dated at each contract's signing

- **Date:** 2026-10-04, reading the dating paragraph in `Pricing, Control Years, and Contract
  Value.docx`. This carries out what Thomas approved on 2026-10-02.
- **Thomas's words:** "Did we not fix this?"; then "Add it to the ledger as a directive." On
  2026-10-02 he approved the recommendation to re-fit the line "with xNPV 1's signing-dated
  WAR-if-plays forecast as the input" (`sessions/2026-10-02.md`; `DECISIONS.md` change log
  2026-10-02f).
- **What it means:** each contract in the price-line sample is paired with the forecast that could
  have been made on its signing date, from seasons whose numbers were available by then, as the
  rebuild did on 2026-09-15 ("each with a forecast frozen at its own signing date"). A contract
  signed during a season is priced on a forecast that does not read that season.
- **How it was lost:** the script built the same day, `xnpv1_price_line.py` v1.0, used the start
  year's page ("the information set Stage 3 already used") instead, and nothing flagged the change.
  `XNPV1_RATE` is locked on that start-dated line.
- **What the code does now (not yet changed):** `xnpv1_price_line.py` takes each contract's
  forecast from the page of its start year.
- **Scale of the problem:** in the 2026-09-14 audit of this sample, 30% of contracts were signed
  before the production they are priced on was complete (58% for players with three or more
  trailing wins); the rebuild found 596 of 3,550 deals signed before the prior season was readable.
- **Rides with entry 4:** both change the price line, so they go into one re-fit and one re-lock.
- **Related, for Thomas to decide alongside (not part of this directive):** the chance of playing
  in a contract valuation reads contract status at July 1, so a contract signed after July 1 cannot
  see itself (open decision 2 below; `25_TESTS/late_signing_status_check.py`). Same root:
  valuing a contract as of its start rather than its signing.
- **Status:** directed. Code unchanged.

---

## 6. Draft and prospect models restart from scratch, with Karl in the development; the data is kept

- **Date:** 2026-10-04, while reading `Draft Picks, Prospects, and the Remaining Trade Model.docx`.
- **Thomas's words:** "we should scrap all draft and prospect modelling decisions, keep the data
  obviously. starting from scratch allows us to have Karl in the development process, which I think
  will help the development process and remove explanation pains and further backtracking."
- **What it means:**
  - Every draft and prospect modelling decision is retired: D22-D27 (harvest window, cost rules,
    units, fitting cohorts, one fixed curve, goalies) and D29-D32 (break-test bands, own-slot for
    unknown picks, conditional picks, the widened prospect pull). Each may come back, but only as a
    fresh decision taken with Karl.
  - The models are rebuilt from a plain-English specification agreed step by step (with Karl)
    before any code, each step entered in this ledger.
  - **Kept, as data:** the cached NHL draft records; the Elite Prospects draft pages (4,765 picks)
    and the EP-to-NHL id bridge (`ep_nhl_bridge.py`, 2,232 of 2,233 agreeing); the scraper
    (`ep_extract.py`) and the NHLe table (`nhle_temporal.csv`); the trade inventory; and the old
    linkage's output (`draft_pick_linkage.csv`) as the check any new linkage is compared against
    pick by pick, with its hand-verified cases (aliases, spelling unions, merged-name exclusions).
  - **Retired, as models:** `draft_yield_curve.py`, `slot_curve.py`, `future_pick_premium.py`, and
    the plans `01_Draft_Model_Sequence.md` and `02_Prospect_Model_Sequence.md`. They stay in the tree
    until the restart begins (archived then, under their original names).
- **Order:** after directives 1-5 are in the code and the price of a delivered win is decided,
  because the draft curve prices in the player model's currency. Consistent with the 2026-10-04
  triage (draft and prospect pillars on hold until Karl is up to speed).
- **Status:** directed. Nothing archived or changed yet.

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
- **Widened (Thomas, 2026-10-05): thin histories.** `thin_history_check.py` v1.0 found the
  comparables' level runs high for players with little NHL history (comparables alone, start bias:
  one counted season +0.374, a lone 10-19-game season +0.561, trailing games under 41 +0.581; three
  seasons -0.140). A reading of the code, to test: a lone season under 20 games has no profile on
  the curve, so his comparables' level is the league average for his position and age, built only
  from 20-game seasons. B therefore also reports every arm by seasons counted (1, 2, 3) and tests,
  for thin histories, a fallback that does not stand on regulars' seasons alone.
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
- **Widened (Thomas, 2026-10-05): thin histories.** The comparables come from a pool that needs two
  consecutive 20-game seasons, i.e. players who stuck; for a player with one or two counted seasons
  that pool may sit above him (see B's widening; comparables alone run +0.374 for one-season players,
  +0.488 and +0.803 for players whose last counted season was two and three years back). C therefore
  also tests, for thin histories, comparables drawn without the two-consecutive-season requirement
  (or with short seasons measured, gap 3 above), reported by seasons counted.
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

## E. The chance of playing for players under contract: is it lowered by other players' walk-aways?

- **Raised:** 2026-10-04, from the control-years passage in `Pricing, Control Years, and Contract
  Value.docx`.
- **Thomas's point:** the chance of playing is estimated on all player-seasons, including players
  who left because their club did not qualify them or nobody signed them. A player with years left
  on his deal should not have his chance lowered by club decisions that do not apply to him.
- **What the model does:** each season's chance of playing reads whether the player is under
  contract for that season (deals signed by the valuation date), which raises the odds of playing
  about 3.5 times (2024 fit, valuation season). That should put most walk-away departures in the
  "not under contract" group.
- **Three leaks, none measured:**
  1. Seasons before 2018-19 are all coded "not under contract" (the export cannot show them), so
     contracted players from those seasons sit in the free-agent group in training. That shrinks the
     measured benefit of a contract and may set a contracted player's chance too low. A
     before/after-2018 indicator would separate them; D33 left it out (for goalies it carried the
     gain credited to contract status, corrected 2026-09-23).
  2. Contracts signed after July 1 are treated as not under contract for their own seasons (1,533 of
     2,759 priced; open decision 2 below).
  3. The contract effect is one shift in the odds, the same for every player and quality.
- **To investigate:** for players under contract for the season (2018-19 onward), compare the
  forecast chance of playing with how often they played, by quality and by seasons ahead. Score
  each fix the same way: the before/after-2018 indicator; status read at the signing; a contract
  effect that varies by quality.
- **Separate from** the control-year weighting (P(qualified) x P(plays, given qualified)), which
  awaits Thomas's choice of method and is not affected by this pool question.
- **Until then:** the code and the model keep the current chance of playing.

## F. Re-run the Game Value circularity checks on the model as directed (final item)

- **Raised:** 2026-10-04, reading `Circularity and Game Value.docx`. Thomas: these tests need to be
  re-run on the new model specifications once the directives above are fully implemented; this is
  the final to-investigate item.
- **Why:** the checks in that document were run on the 60/40 two-season trailing total. Under
  directives 1 and 2 the production measure becomes 50/30/20 over three seasons, pulled 65/35
  toward comparable players, and none of the checks has been run on the forecast itself.
- **To re-run, after directives 1-5 are implemented:**
  1. The main check: each player's trailing measure (now 50/30/20) against his GV-adj performance
     that season, overall, by season, by position, and one season further ahead (previously 0.576
     across 6,027 player-seasons; 0.648 forwards, 0.302 defence; 0.538 one season further).
  2. The two raw Game Value variants (against replacement, and zero-sum).
  3. The same checks with the model's starting level and its forecast WAR if he plays in place of
     the trailing measure.
  4. The contract-status channel (the chance of playing reads club decisions): report how much of
     the forecast's agreement with Game Value survives without contract status.
- **Related, already carried elsewhere:** the price-line specification tests (straight line,
  contract length, RFA/UFA, stability over time) are not repeated on xNPV 1's line (WORK_QUEUE,
  2026-10-04 block, item 3); directives 4 and 5 change that line again.
- **Status:** to run once directives 1-5 are implemented.

---

**The to-investigate list is closed (Thomas, 2026-10-04): F is the final item.** New questions go to
WORK_QUEUE unless Thomas adds them here.

---

# Open decisions (raised 2026-10-04, not yet made)

These are choices put to Thomas during the read-through. They are not investigations; each needs
his decision before the code it touches is changed.

1. **The control-year weight.** Today each RFA control year is weighted only by the rate at which
   clubs qualified players of his forecast level; a qualifying offer does not mean he plays. The
   July test (`DECISIONS.md`, "Control-year departure... TESTED, both fixes PARKED") found a
   qualified skater still leaves the league at 13.1% a year, uncounted, and that goalie control
   years carry no weight at all. Choose how "he plays" enters:
   - the July method: P(qualified) x P(plays, given he was qualified), measured only among
     qualified players (each departure counted once); or
   - reuse xNPV 1's chance of playing (simpler, but it includes walk-aways, so part of them is
     charged twice).
   Also: start the control-year chain from his chance of playing the contract's final season, not
   from 1. Goalies: Thomas's July sub-decisions stand (one pooled rate, a one-game bar).
2. **When contract status is read for a contract valuation.** Contracts are valued at July 1 of
   their first season, so a contract signed after July 1 cannot see itself in its own chance of
   playing (1,533 of 2,759 priced skater contracts). Reading it at the signing raises 1,351 of 1,530
   re-datable values, median +$0.33M, total +$622M (`25_TESTS/late_signing_status_check.py`).
   Options: read status at each contract's signing (a code change), or keep July 1 and correct
   `skater_forecast.py`'s docstring. Same root as directive 5.
3. **The price of a delivered win.** The draft curve and any back-test outcome price realized
   wins; player contracts price forecast wins on their own line. Which price a delivered win
   carries must be decided once, for both sides of each trade. On hold under the 2026-10-04 triage;
   directive 6's restart waits on it.
