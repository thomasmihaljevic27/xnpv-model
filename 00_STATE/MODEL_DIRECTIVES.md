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
| 1 | Starting level: 50/30/20 per-82 WAR over three seasons, pulled 65/35 toward comparable players; no fitted decay anywhere | implemented (branch, `64ab8bf`) |
| 2 | The aging curve measures each player's level with 50/30/20 over three seasons, games-weighted (changed from plain 2026-10-04c) | implemented (branch, `64ab8bf`) |
| 3 | One own-versus-comparables blend: 65/35 replaces the curve's 55/45 | implemented (branch, `64ab8bf`) |
| 4 | Contract length in the price line (term-in), term-free reported as the sensitivity | implemented and validated (branch, 2026-10-05) |
| 5 | Price-line forecasts dated at each contract's signing | implemented and validated (branch, 2026-10-05) |
| 6 | Draft and prospect models restart from scratch with Karl; the data is kept | pick curve built 2026-10-09 (`pick_curve.py`, `traded_pick_values.py`); prospects not started |

| | To investigate (closed list) | Status |
|---|---|---|
| A | The yardstick: one per position, and no self-pairs | closed: A1 implemented (v2.1), A2 dropped |
| B | The league average inside the comparables' estimate | closed: weight of ten kept (2026-10-05) |
| C | Departed players in the aging curve: the assumed zero and its gaps | closed: C2, C6 implemented (v2.1); C5 dropped |
| D | The games-share equation's form | closed: D2 implemented (v2.2) |
| E | The chance of playing for players under contract | closed: E1 implemented (v2.2); E3, contracted-seasons fit dropped |
| F | Re-run the Game Value checks on the model as directed | closed: run 2026-10-05; the forecast agrees with Game Value more than the trailing totals |

The plan of record (order of work) follows this summary. Open decisions (Thomas's to make; listed at the end): the price of a delivered win. (Decided
2026-10-05: the control-year weight, the July method from his chance of playing; when contract status
is read for a contract valuation, at the signing.) Unsettled details sit inside
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
   line, contract length, RFA/UFA, stability). **Carried to it (Thomas, 2026-10-05):** term-in puts long
   cheap deals for mid-level players at the top of the values (a 7-8-year deal carries about
   $6.0-6.8M a season of term premium at the 2025-26 cap whatever he produces; the rebuild warned that
   term carries quality the forecast misses); the contract-length test examines whether the term
   premium should scale with player quality. Values are provisional until then. Decide how the changed model is validated: the
   2022-2025 confirmation was a one-time run on the old forecast and cannot simply be repeated.
8. **Open decision 3 (the price of a delivered win)**, which unlocks directive 6 (the draft and
   prospect restart with Karl).

**Step 1 build (2026-10-05):** directives 1-3 and the build rules are in `20_CODE/skater_forecast.py`
v2.0 and `20_CODE/aging_curve.py` on `claude/amazing-einstein-tk4b08`. One fix beyond the tested
design: the walk now stops at the curve's oldest age and holds (the tested code fell back to the
league path for a player walked past it). `25_TESTS/directed_build_check.py` v1.0 holds the build to
the tested design row by row (passed in the cloud on fake data) and to the recorded figures (laptop).

Laptop check passed 2026-10-05: production equals the tested design row by row and reproduces every
recorded figure; the walk fix moves 42 of 41,496 rates (7 player-pages) and no figure at four decimals.

**Step 2 closed (2026-10-05):** A1, C2, C6 adopted and built (`skater_forecast.py` v2.1); A2, B1, B2,
C1, C3, C4 and C5 not adopted. `25_TESTS/abc_build_check.py` v1.0 passed on the laptop (gaps 0; 1.1506 / 1.3587 / 0.8088 / 0.4673). Directive 1's
detail 2 (which comparable-player level): **settled (Thomas, 2026-10-05)** by B's outcome: the curve's
comparables estimate, blended with the league average at weight ten.

**Step 3 closed (2026-10-05):** D2 and E1 built (`skater_forecast.py` v2.2); D1, D3, E3 and the
contracted-seasons fit not adopted; open decision 2 decided (at the signing; built at step 6).

`25_TESTS/de_build_check.py` passed on the laptop (2026-10-05): gaps 0; figures reproduced.

**Step 4 closed (2026-10-05):** open decision 1 decided (the July method; the chain starts from his
chance of playing the final contract season; goalies weighted, pooled, one-game bar). Built at step 6.

**Step 5 (fix the forecast) is done in code:** everything adopted from steps 2-3 is in
`skater_forecast.py` v2.2 and `aging_curve.py` on the branch, each held by a build check that passed
on the laptop (A1, C2, C6: `abc_build_check.py`; D2, E1: `de_build_check.py`).

Directive 4's three details settled (2026-10-05): one linear term for years; each season uses the term
remaining at the valuation date; a control year is priced as a one-year signing.

**Step 6 so far (2026-10-05):** the price line re-fitted (`xnpv1_price_line.py` v2.0) and both lines
locked by Thomas (term-in `XNPV1_RATE`: $1.67M per forecast win, D $2.01M, + $0.853M a season per
year of term; term-free `XNPV1_RATE_TERM_FREE` beside it). Term built into pricing
(`skater_forward_projection.py`, `rfa_terminal_value.py`, `contract_npv.py` v2.1). Directive 4
implemented in code; directive 5 implemented in the price line (and in valuations with open decision 2).

Open decision 1 (the control-year weight, skaters and goalies) and open decision 2 (status read at
the signing for a contract's first season) built 2026-10-05 (`rfa_terminal_value.py`, `contract_npv.py`,
`skater_forward_projection.valuation_as_of`, `contract_npv_panel.py` v1.3).

Floor spread re-measured and locked (2026-10-05). The first dashboard refresh stopped on a bug in the
signing-date change (fixed) and showed the control-year weights missing the NHL-regular condition
(fixed, Thomas's definition).

The refresh at `dca0831` passed (2026-10-05): every step, the dashboard re-pricing 7,771 pages within
$1 of the panel. Directives 4 and 5 and open decisions 1 and 2 are validated.

Documents updated (2026-10-05): `Data, Production, and Aging.docx` and `Pricing, Control Years, and
Contract Value.docx` describe the model as now built, figures from `25_TESTS/document_figures.py`.
**Step 6 is complete.**

**Step 7 is complete (2026-10-05).** The revalidation: the built forecast, scored once on 2022-2025, is
CONFIRMED against xNPV 0 under the declared rule (RMSE 0.8932 against 0.9724, lower squared error in
2,000 of 2,000 player resamples). Against the 10-02 forecast (reported): RMSE 0.8932 against 0.9001,
lower squared error in 1,954 of 2,000, lower absolute error in 546 of 2,000 (MAE 0.5823 against 0.5809),
lower Brier in 1,991 of 2,000.

**Step 8 is complete (2026-10-05):** open decision 3 decided, delivered wins on the contract line.
The plan of record is done. **Next:** directive 6, the draft and prospect restart, specified step by
step with the supervisor (each step states its trailing weighting, 50/30/20 unless decided otherwise).

**Next step (was):** step 8, open decision 3 (the price of a delivered win), which unlocks directive 6.

**Next step (was):** step 7, remaining: the revalidation run. Thomas chose (2026-10-05) one more scored run on
2022-2025, reported as a second use of seasons already seen: `25_TESTS/run_revalidation_2022_2025.py`
v1.0, the built forecast against the 10-02 confirmed forecast and xNPV 0, both read from the
confirmation's saved forecasts. Rule declared in the script: confirmed if lower squared error than
xNPV 0 in at least 1,950 of 2,000 player resamples; the comparison with the 10-02 forecast is reported,
not decided. Thomas runs `--code-test` first, then the run once. Then step 8.

**Next step (was):** step 7, remaining: how the changed model is validated. Done in step 7: investigation F
(closed); the price-line specification tests (closed 2026-10-05): straight line and stability hold;
one line for RFA and UFA; the length premium kept flat; `XNPV1_RATE` unchanged.

**Next step (was):** step 7, remaining: Thomas runs `25_TESTS/price_line_spec_tests.py` v1.1 (the
one-step length premium; the hidden-quality legs), then decides the length premium's shape; then how
the changed model is validated. Done in step 7: investigation F (closed); the specification tests v1.0
(straight line and stability hold; one line for RFA and UFA, Thomas 2026-10-05).

**Next step (was):** step 7: investigation F, the price-line specification tests (straight line, contract
length including whether the premium should scale with quality, RFA/UFA, stability), and how the
changed model is validated.

**Next step (was):** step 6, (a) Thomas runs `20_CODE/xnpv1_price_line.py` v2.0 on the laptop (built
2026-10-05: signing-dated forecasts matched to the page with the identical information set; one linear
term for years; four fits on the same rows, so directive 5 alone, directive 4 alone and both are each
shown; the term-free and term-in lines printed for locking) and locks the two lines; then (b) the pricing code: term in each season's value, status read at the signing (open decision
2), the control-year weight (open decision 1), the qualify rates and floor spread re-measured, the
valuations and dashboard re-run, the documents updated. Do not run the dashboard or `xnpv1_price_line.py` on the branch: the price line is not re-fitted
until step 6, so any valuation there is provisional. Details 1, 3 and 4 settled
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
- **What the code did before `64ab8bf`:** `skater_forecast.py` builds the starting level from
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
- **Build rules (Thomas, 2026-10-05, before step 1's build):**
  - *Where the aging comes from:* the tested rule. The step to the valuation season and every later
    season's change come from one match at the player's last counted season's age; where he has no
    20-game season at that age, the league-average changes for his position and age. (Today's code
    reads his profile one season before the valuation season, else two.)
  - *The trailing WAR input to the games-share and chance-of-playing equations:* Thomas asked why a
    rate per 82 is not used. It is inherited from the rebuild and was never tested against a rate.
    Thomas: "any time a players WAR is being considered in a calculation, I want them to be as
    uniformly inputted as possible. Test first, sure, but I will lean to have things as uniform as
    possible when possible." Stated preference, not yet a directive: decided on
    `25_TESTS/war_input_uniformity_test.py` v1.0 (laptop run owed), which scores the trailing total
    (plain 50/30/20) against the games-weighted 50/30/20 rate per 82, each with and without the
    level-above-1.0 term (cut-off 1.0 in its own units, a carried setting). The trailing games share
    stays plain 50/30/20 (a share already counts games).
  - **Settled (Thomas, 2026-10-05): the trailing total, and the level-above-1.0 term dropped.** Both
    equations read the plain 50/30/20 trailing WAR total; the games-share equation loses its
    total-above-one-win term. Evidence (laptop, development pages, 40,510 player-seasons, 1,609
    players; checks passed): season-WAR RMSE 0.8093 total without the term, 0.8107 with it, 0.8108
    rate without, 0.8111 rate with; the rate lower than the total in 10 of 2,000 career resamples;
    the total without the term lowest at all six seasons ahead. Chance of playing: the rate's log
    loss lower in 0 of 2,000 (0.4089 against 0.4044). Games share: the rate slightly better (0.2645
    against 0.2657, 2,000 of 2,000). The term helps the share but costs season WAR (total without it
    lower in 1,979 of 2,000; rate 1,931). The rate is the input wherever a player's quality is
    measured (the start, the aging curve); the total where the question is whether he plays and how
    much. Not scored: a mixed version (rate in one equation, total in the other).
- **What this overrides in `Data, Production, and Aging.docx`, Section 3** (confirmed by Thomas):
  - Step 1's decay chosen from the data;
  - Step 2's eight-term regression, its coefficient table, and its worked numbers (the 27-year-old
    examples and Marchessault's 2.37).
  - Kept: Step 2's opening paragraph on why a pull is needed.
  - To re-measure after the switch: the evidence paragraph (2.3%) and the star paragraph (-0.26).
- **Status:** implemented on `claude/amazing-einstein-tk4b08` at `64ab8bf` (`skater_forecast.py` v2.0, `aging_curve.py`); `25_TESTS/directed_build_check.py` passed on the laptop 2026-10-05 (production equals the tested design row by row and reproduces every recorded figure; the walk fix moves 42 of 41,496 rates, 7 player-pages). Not yet on `main`.

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
- **What the code did before `64ab8bf`:** `aging_curve.py` uses the equal average of the last
  two consecutive 20-game seasons (`WIN = 2`), and `skater_forecast.imputed_aging_model` enters a
  departure as (last rate + 0) / 2.
- **Evidence:** `25_TESTS/aging_level_weights_test.py` v1.0, valuation dates 2015-2021:
  - The starting level is unaffected: all four versions tie (1.1501-1.1506).
  - Aging only, one to five seasons out: 1.3610, against 1.3642 for the equal two-season average,
    lower in 1,999 of 2,000 resamples. Whole forecast: 1.3596 against 1.3642, lower in 2,000.
  - Slightly worse one season out (1.2620 against 1.2603); better from two seasons on.
  - 60/40 over two seasons was worse than the equal average. Games weighting added nothing.
- **Status:** implemented on `claude/amazing-einstein-tk4b08` at `64ab8bf` (`skater_forecast.py` v2.0, `aging_curve.py`); `25_TESTS/directed_build_check.py` passed on the laptop 2026-10-05 (production equals the tested design row by row and reproduces every recorded figure; the walk fix moves 42 of 41,496 rates, 7 player-pages). Not yet on `main`.

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
- **What the code did before `64ab8bf`:** `aging_curve.py` blends 55% own and 45% comparables
  in `AgingModel.project`; xNPV 1 reads only the curve's changes, so that blend has no effect on any
  value today.
- **What this overrides in `Data, Production, and Aging.docx`, Section 4:** the paragraph saying the
  curve computes a 55/45 starting level that the model does not use. Under entries 1 and 3 the
  starting-level section states the single 65/35 blend once. Marchessault's 2.37 and his forecast
  rates (2.00, 1.76, 1.56, 1.12) change once the code is changed.
- **Note:** with the curve's 55/45 replaced, the curve's own starting level becomes the model's
  starting level before the one-year step to the valuation season (entry 1, open detail 3).
  *Correction (2026-10-05):* not exactly. The curve measures a player from 20-game seasons by age;
  the start's own rate uses 10-game seasons by calendar season (Thomas's 10-game minimum, directive
  1). The two blends use the same weights (65/35) and the same games-weighted 50/30/20 rule, but the
  start is built as tested (`level_games_weighting_test.py`), not read off the curve's anchor.
- **Status:** implemented on `claude/amazing-einstein-tk4b08` at `64ab8bf` (`skater_forecast.py` v2.0, `aging_curve.py`); `25_TESTS/directed_build_check.py` passed on the laptop 2026-10-05 (production equals the tested design row by row and reproduces every recorded figure; the walk fix moves 42 of 41,496 rates, 7 player-pages). Not yet on `main`.

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
     - **Settled (Thomas, 2026-10-05): years of term, one linear term,** added to today's line (cap
       share = intercept + price per forecast win, defence slope, + a fixed share per year of term),
       nothing else. RFA status and interactions stay out; the RFA/UFA question is the step 7
       specification test. The rebuild's form (term, RFA, RFA x wins, one-year marker, defence
       intercept, first-season forecast) was put to Thomas and not chosen.
     - **RFA/UFA settled (Thomas, 2026-10-05): one price line for both,** on the step 7 test (a
       separate RFA line: four terms, 0.17% lower held-out RMSE, only RFA defence clearly non-zero).
       **Length premium settled (Thomas, 2026-10-05): kept flat,** the locked line unchanged, after the
       one-step test (v1.1): a separate premium below replacement would have cut held-out RMSE by about
       $9k a contract (0.7%) and moved the price per win; the falling premium is a known limit.
  2. *How term enters each season's value:* term-in must not add the term premium to each season
     whatever the player produces (the rebuild's first attempt priced Brent Seabrook's 0.20
     forecast wins at $47.2M). The rebuild's resolution: the replacement a contract is compared
     against is a player signed for the remaining term. The exact rule for this model is to be
     set before any code changes.
     - **Settled (Thomas, 2026-10-05): the remaining term at the valuation date,** the same for every
       remaining season of the contract (the comparison is a replacement signed today for the rest of
       the deal; at signing, the full length). Each season's value = chance he plays x E[max(intercept
       + price per forecast win x WAR if he plays + term coefficient x remaining term, league
       minimum)] - cap hit, discounted. The term premium is reported in its own column beside
       production value, and the term-free value beside the term-in value. Not chosen: the original
       length at every valuation; a term shrinking season by season.
  3. *Control years:* whether the RFA control years are priced term-in, and at what term.
     - **Settled (Thomas, 2026-10-05): one year.** Each control year is a one-year qualifying offer, so
       its market price is a one-year signing's (term = 1): cost and value describe the same deal.
       Not chosen: the control years remaining; the expired contract's remaining term.
- **Knock-ons once implemented:** the price line is re-fitted and re-locked; aggregate value moves
  by billions (term-in added $3.3-4.1B across 2,591 contracts in the 2026-09-14 test); the
  defence-premium question (WORK_QUEUE) is re-read on the new line (the rebuild's term-in line put
  the defence premium in an intercept, not the slope).
- **Status:** implemented on `claude/amazing-einstein-tk4b08` (`xnpv1_price_line.py` v2.0; term-in `XNPV1_RATE` locked by Thomas 2026-10-05; `skater_forward_projection.py` v2.1, `rfa_terminal_value.py`, `contract_npv.py`); validated on the laptop 2026-10-05: the full dashboard refresh at `dca0831` passed (the dashboard re-priced 7,771 pages, each matching the panel within $1). The step 7 contract-length test (2026-10-05) kept the line as locked: the values stand.

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
- **Status:** implemented on `claude/amazing-einstein-tk4b08`: the price line is fitted on forecasts dated at each signing (`xnpv1_price_line.py` v2.0), and valuations read status at the signing (open decision 2); validated on the laptop 2026-10-05: the full dashboard refresh at `dca0831` passed (the dashboard re-priced 7,771 pages, each matching the panel within $1). The step 7 contract-length test (2026-10-05) kept the line as locked: the values stand.

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
  because the draft curve prices in the player model's currency. Both done 2026-10-05: delivered
  wins are priced on the contract line (`XNPV1_RATE`), not Stage 3. Consistent with the 2026-10-04
  triage (draft and prospect pillars on hold until Karl is up to speed).
- **50/30/20 (Thomas, 2026-10-05):** "when the draft and prospect work starts you need to be 100% certain
  that you are using 50/30/20 when needed." Binding on the restart: each step of the specification
  that reads a player's recent seasons states its weighting, 50/30/20 unless Thomas decides otherwise,
  and the restart's first check lists every trailing weighting in the code it calls. 60/40 is still in
  `draft_yield_curve.py` (`W_T1, W_T2`, the cost anchor, lines 165 and 351) and in
  `skater_value_engine.py` (`W_T1, W_T2`, line 217: the observed-season value and the older price line
  the draft curve reads); neither is reused without that decision.
- **Archived (Thomas, 2026-10-09):** `draft_yield_curve.py`, `slot_curve.py`, `future_pick_premium.py`,
  `01_Draft_Model_Sequence.md` and `02_Prospect_Model_Sequence.md` moved to `90_ARCHIVE/2026-10-09/`
  under their original names (in git up to `de67144`), with the old curve's outputs
  (`draft_yield_curve.csv`, `draft_pick_outcomes.csv`) copied beside them as the reference the new curve
  is compared against. Nothing live imported them. `draft_pick_linkage.py` stays (kept data and check).
- **Status:** directed; restarted 2026-10-09. The specification so far follows. Nothing built yet.

### The specification so far (2026-10-09)

Agreed in the meeting with the supervisor on 2026-10-09 (read from the transcript), then decided by
Thomas the same day. Each item may change only by Thomas's decision.

**Draft picks: agreed in the meeting**
- *One regression on draft slot.* A pick's value comes from one regression on draft slot across all
  picks, not from bands of picks (about 2,200 picks over ten-plus classes is enough). It is noisy by
  design: at the draft, the slot is the only information. Draft-year indicators control for unusually
  deep or shallow drafts; a pick is valued from the slope, without a year's effect. Thomas expects the
  slope, more than the level, to change by year: tested (below), and accepted as uncertainty.
- *A pick a year or more ahead is valued at the average for its round.* Last draft's slot is not used
  to predict it: the slot-persistence chart showed no usable signal. Thomas: "the draft slot is
  uncertain one year out. We will just take the average value of a draft pick in that round." The
  supervisor: "I think that's exactly what you do."
- *A pick for the coming draft, traded in-season, is valued at its projected slot on the trade date*
  (decided earlier; confirmed in the meeting).
- *Cost after the entry-level deal: a chain of one-year qualifying offers,* as in the player model.
  Not chosen: surplus counted only during the entry-level deal (it understates: clubs control a player
  past three years); cost set from his earlier production (set aside).
- *Top picks get a separate look:* what control over a top prospect is worth in the data, against the
  qualifying-offer chain (a top pick is likelier to sign a long deal than to take one-year offers).
- *Every selection enters,* picks that never play included (read in the meeting and agreed).
- *Read and accepted:* the classes the old document used (2007-2017). The curve's classes overlap the
  traded picks (a 2017 pick traded from 2017-18 has its outcome inside the curve that values it).
  Accepted as how the draft works; to be stated as a limitation, with a check that refits the curve
  without the class being valued.

**Draft picks: decided by Thomas after the meeting (2026-10-09)**
- *Order: price each player, then regress.* Each drafted player's seasons are priced in dollars (value
  minus cost, as below), and the dollars are regressed on slot. The regression of WAR on slot is
  reported beside it. Not chosen: regress WAR on slot, then price the predicted WAR (it treats every
  player at a slot as the average one and blurs the stars, who carry a pick's value).
- *Window: from the draft to where the qualifying-offer chain ends,* not a fixed nine seasons. The
  chain ends at unrestricted free agency, simplified to age 27 or seven NHL seasons, whichever comes
  first. **Settled (Thomas, 2026-10-09): both from the CBA.** "lets keep the age cutoff consistent, it
  may be subject to change throughout the whole project as I want the age rules to be based off the
  CBA. What counts as a season I suppose is also based off the CBA." The age date and the definition
  of a season counted toward free agency are taken from the CBA text (cited in the code, not from
  memory). The player model does not compute this: it reads each contract's UFA year from PuckPedia
  (`rfa_terminal_value.py`, `ufa_year`). Drafted players before 2018-19 have no PuckPedia record, so the
  rule is built from the CBA and checked against PuckPedia's UFA year wherever a player has one.
- *Entry-level seasons are priced as one-year deals* (term = 1 in the contract line), like the control
  years. Not chosen: the entry-level deal's remaining term (3, 2, 1), which at $0.853M a season per
  year of term (2025-26 cap) adds $1.7M and $0.85M to the first two seasons beyond one-year pricing,
  about $2.6M over the deal, where the price is above the league minimum. (The chat on 2026-10-09 put
  it at about $5M, measuring against no premium at all; corrected here.) This settles,
  for drafted players' entry-level seasons, open decision 3's "term premium of the contract he was on".
- *A season outside the NHL is worth zero and costs zero* (a minor-league salary is off the cap).
- *Partial NHL seasons are scaled (Thomas, 2026-10-09):* a season under 10 NHL games has its priced value
  and its cost scaled by games/82 (a callup is on the cap only for his days on the roster). Seasons of
  10+ games are priced in full: games played under-count roster days for injured regulars, whose cap
  hit counted all year. The 10-game cut is carried from the archived curve (and is the CBA's 9.1(d)
  slide line). Effect on the first look: mean surplus a pick $1.50M -> $1.68M (655 picks change).
- *2012-13 WAR is scaled to 82 games (x82/48) (Thomas, 2026-10-09),* extending D20 (82/70, 82/56) to
  the lockout season.
- *Classes whose window runs past 2025-26:* count the players affected first, then decide between
  dropping the class and cutting the window at 2025-26.
  - **Count (2026-10-09, `25_TESTS/draft_window_count.py` v1.0):** CBA Group 3 (Section 10.1(a): seven
    Accrued Seasons, or 27 as of June 30; an Accrued Season is 40 active-roster games, 30 for a goalie,
    with NHL games played standing in for roster games). Every window in the 2007-2016 classes ends by
    2025-26. In the 2017 class, 29 of 217 run past it, each by exactly one season (control through
    2026-27, all from the age rule: born after June 30, 1999): 15 have played in the NHL (among them
    Jason Robertson, Gabriel Vilardi, Filip Chytil), 14 have not. If Group 6 (25 or older, three
    professional seasons, under 80 NHL games) is assumed met for everyone, 12 remain, all NHL
    players. 3 picks have no window (two forfeited picks without a player; Erik Gustafsson 2012, the
    merged-name exclusion). Against PuckPedia's UFA year: 1,151 of 1,183 drafted players with a contract
    agree; PuckPedia is earlier for 19 (games played under-count roster games: injured players and
    backup goalies) and later for 13 (11 where the seven-season count decides, cause not found; debut
    age does not explain it, since 76 of the 89 who debuted at 18 or 19 agree; and Conner Bleackley,
    drafted twice). Of the 29, PuckPedia has Chytil free after 2024-25; 8 have no PuckPedia contract.
  - **Settled (Thomas, 2026-10-09): keep the 2017 class as it is; no decision owed unless its refit
    moves the curve.** The 29 short windows (one season each, mostly late-birthday players) are stated
    as a limitation. The draft-year indicators absorb most of a class-wide shortfall, and the
    leave-one-class-out scoring already refits without 2017, which is the "drop" option; if that refit
    moves the curve materially, the question comes back to Thomas with the figures.

**Draft picks: to test (Thomas, 2026-10-09)**
- the slope's form (widened, Thomas 2026-10-09: "test all but I agree I favour a simpler solution"):
  a straight line in pick number; the log of the pick; a bendable curve (a + b x pick^c, one extra
  number); a two-part model (chance he plays in the NHL x value if he does, each on log of the pick);
  a curve on the log of the pick (adds log squared); Bacon's NHL and star probabilities by pick as the
  inputs (caution recorded: fitted on largely the same drafts); and, as a benchmark never adopted, the
  smoothed average at each pick forced to fall with the pick number. Simpler wins unless a more complex
  form clearly beats it (the bar is set before the run);
  - **Result and decision (2026-10-09).** Bar 1,950 of 2,000 (Thomas). `25_TESTS/pick_curve_shape_test.py`
    v1.0: the declared rule's verdict was log + log-squared (held-out RMSE $5.213M a pick against log's
    $5.384M), but that curve rises from pick 138 on; Bacon's probabilities also cleared the bar ($5.224M);
    the bendable curve missed it by four redraws. **Thomas: "I think we should probably just go with
    bacon's probabilities, but maybe this regression can be used to validate that his approximation is
    backed up."** The pick curve is surplus = a + b x P(NHL player) + d x P(star) by slot (Bacon's
    `draft_slot_baseline.csv`), with draft-year indicators, read at the average year.
  - **Validation** (`25_TESTS/pick_bacon_validation.py` v1.0, report only): adding log(pick) to his
    probabilities adds nothing (coefficient +0.14, se 1.21, p 0.91; held-out RMSE 5.228 against 5.224).
    Our own slot-only curves give nearly the same dollars: mean gap per pick $0.15M (bendable) and
    $0.24M (log + log-squared), largest at #1 (bendable $27.1M against his curve's $23.4M; raw $28.6M).
    In dollars his NHL-player probability carries nothing once his star probability is in (coefficient
    -0.05, se 2.15; star +31.3, se 6.9). Caveat: his probabilities are fitted on largely the same
    drafts, so agreement is not independent confirmation.
  - **Star chance only (Thomas, 2026-10-09):** "this seems simple enough to go with his star
    probabilities." Options put: both of his chances (held-out RMSE 5.224), the star chance only
    (5.215, same dollars to $0.03M a pick), the NHL chance only (5.410; #1 at $10.3M). His NHL chance
    carried nothing once the star chance was in (-0.05, se 2.15); the two correlate 0.87 across picks.
  - **His definitions** (hockeystats.com/draft/guide, read 2026-10-09): a star has career WAR per 82
    games of 1.8+ (forwards) or 1.23+ (defencemen), described as the top 20% / 15%; an NHLer has 200+
    NHL games; players are labelled only if drafted 2021 or earlier; the slot baseline is a logistic
    regression on pick number with a kink at pick 150. The curve's shape across picks is therefore his
    logistic; our regression sets its dollar scale.
  - **Form on the star chance** (`25_TESTS/pick_star_form_test.py` v1.0, same rule and bar): through
    zero (surplus = b x P(star), b = $31.37M) RMSE 5.214; with an intercept 5.215 (a = $0.04M); with a
    squared term 5.232; a power curve 5.227 (k = 1.03). No version with more numbers beat the
    through-zero line in more than 30 of 2,000 redraws. Verdict under the rule: through zero. Values
    at an average year: #1 $23.5M, #10 $6.7M, #32 $2.3M, #100 $0.75M, #200 $0.12M. The $31.37M is not
    the value of a star: it also carries the surplus of non-star regulars, which rises with the star
    chance.
  - **ADOPTED (Thomas, 2026-10-09): "yes adopt".** The pick curve: surplus = $31.37M x Bacon's star
    chance for the slot, through zero, at the average draft year (2025-26 cap). Bacon's logistic gives
    the shape across picks; our regression gives only the dollar scale. Explained before adoption: the
    line is straight in the star chance, not in pick number (#1 to #2 falls $5.0M, #20 to #32 $1.3M).
    Provisional on the remaining tests (year slopes, negative careers, top 10/15, slides, goalies),
    which may change the scale.
  - **Top picks: cost stays the qualifying-offer chain (Thomas, 2026-10-09: "I think it should then work
    this way").** `25_TESTS/top_pick_control_look.py` v1.1 (report only) found clubs actually paid 3.2x
    the chain over the control window for picks 1-10, 2.3x for 11-15, 2.1x for 16-32. Not adopted:
    actual contracts add hindsight on the cost side (Thomas's concern) and their averaged cap hits
    include the price of UFA years outside the window. Recorded as a stated limitation with its size
    (salary arbitration, CBA Article 12, and early long deals push RFA pay toward market). Optional
    later, a sensitivity only: from arbitration eligibility, control years costed at the market price
    of delivered wins (rule-based, no actual contracts).
  - **Keep the cost side's alternatives (Thomas, 2026-10-09):** "I think keeping alternative ways to
    design the cost side of picks is going to be needed." The qualifying-offer chain stays the main
    cost; alternatives are kept and reported beside it: the arbitration-eligibility version; the
    entry-level slide variants; actual cap hits (hindsight, reference only). A cost alternative changes
    each pick's surplus, so it is compared by how much it moves the curve, never by held-out miss
    against the main version (different targets).
  - **Skater tests run (`25_TESTS/pick_cost_and_year_tests.py` v1.0, 2026-10-09; main reproduces the
    first look for all 2,089 picks).** Scale ($M per 100% star chance; main 31.37): CBA-only slides
    31.27 (-0.3%), no slides 31.21 (-0.5%); each player's total floored at zero 32.64 (+4.1%);
    arbitration (control seasons from eligibility carry no surplus) 14.06 (-55%; #1 $10.5M against
    $23.5M). By class (Wald test that all eleven scales are equal: chi2 27.3, 10 df, p 0.002): 2012
    8.6 (se 4.9) to 2015 56.4 (se 10.1); the spread beyond sampling noise is about 9.1, 29% of the
    pooled scale; 2014-2017 all above the pooled scale (a pattern, cause not examined). Open for
    Thomas: slides (modelled, CBA-only, or none); careers floored at zero or not.
  - **Goalie test (`25_TESTS/pick_goalie_test.py` v1.0, report only; no bar declared):** 233 goalie
    picks priced on the goalie line (82 played; mean surplus $2.40M against skaters' $1.68M; best:
    Holtby #93, Vasilevskiy #19, Gibson #39, Saros #99, Oettinger #26, Shesterkin #118). Scale:
    skaters 31.37, pooled 32.00 (+2%), goalies alone 84.33 (goalie value does not follow the slot;
    applied to Bacon's skater star chance it would put a #1 goalie pick near $63M). Held-out miss on
    goalie picks: skater scale 5.889, pooled 5.891, apart 5.707; skater picks 5.2155 in all three.
    At a trade the pick's position is unknown. Open for Thomas: skaters only, pooled, or apart.
  - **Decided (Thomas, 2026-10-09): "no slides, keep negatives, pool goalies."** The entry-level deal
    runs by calendar from his first NHL season (3 / 2 / 1 years by age), with no slide; a player's
    negative total surplus counts as negative; goalie picks are priced on the goalie line and pooled
    with skaters in one scale. The scale is to be re-fitted once on this package.
  - **The scale is the one knowable at each trade (Thomas, 2026-10-09: "go with the knowable scale,
    pooled as sensitivity").** A pick traded in season T is priced with the scale fitted only on classes
    drafted in T-9 or earlier (their control windows had largely run out by then); the shape stays
    Bacon's star chance, which fits early and late drafts alike (`25_TESTS/pick_lookahead_check.py`).
    The pooled scale (all classes 2007-2017) is reported beside it as the sensitivity. Reason: the
    value at a trade must use only what was knowable then; realised careers belong to the back-test's
    outcome side. The scale is not stable across classes (p 0.002), unlike the player price line.
    Cost, accepted: the early trade seasons rest on two or three classes (2017-18 se $6.2M).
  - **SUPERSEDED (Thomas, 2026-10-09, reviewing the document): one fixed star value for every year.** Thomas's
    comments asked whether a year-specific scale was justified at all ("What if teams simply value draft picks
    consistently over time?"). The test behind the trade-season scale showed only that drafts differ; the
    test that matters is a drift over time. `25_TESTS/pick_review_checks.py` v1.0: the scale rises +2.08 a
    draft year (robust p 0.046), but without 2015 and 2016 +0.84 (p 0.435). Decided: "go with (a)": the
    **star value** (renamed from "dollar scale"; Thomas: "star value works"), the surplus a pick would be worth
    if its player were certain to become a star, is one number fitted on all eleven drafts (31.66); the same
    fit without 2015 and 2016 (27.58) is the sensitivity. The trade-season scale is retired.
  - **Future picks: the round average stays (Thomas, 2026-10-09: "keep round average").** Final standings
    2017-18 to 2025-26: a team's place correlates 0.54 with the next season's and 0.44 two seasons on; median
    move 6 places. The persistence data is rebuilt from the draft records (Thomas: "im sure you can recreate
    the data") for the document, with what the round average costs.
    Rebuilt (`25_TESTS/pick_slot_persistence.py` v1.0, draft records 2005-2026, each team's own first-round
    slot): correlation 0.44 with the next draft, 0.34 two drafts on; median move 6 slots. Valued at the slots
    teams went on to pick, a future first of a team that just picked 1-5 was worth $9.5M against the round
    average of $6.6M; of a team that just picked 25-32, $4.35M. Stated in the document as a limitation.
  - **Built (2026-10-09):** `pick_curve.py` v1.2 (star value 31.66, sensitivity 27.58) and
    `traded_pick_values.py` v1.2 (634 traded picks: $704.8M; sensitivity $614.0M).
  - **Later work (Thomas, 2026-10-09):** the conditional picks are back-test work, for when the full model is
    complete; the arbitration cost alternative for picks is folded into the RFA arbitration idea (WORK_QUEUE),
    and probably the prospect model, and goes to Karl at the next meeting.
  - **Checks (`25_TESTS/pick_star_and_rights_checks.py` v1.1, 2026-10-09, report only).** (1) Bacon's
    star rates against ours (his definition; our reading: a star is also a 200+ game NHLer), classes
    2007-2015, 1,700 skater picks: 5.9% stars against his 5.3%; every pick range within two standard
    errors (#1 67% against 75%; 2-3 56% / 54%; 4-10 29% / 29%; 11-20 22% / 15%; 21-32 8% / 9%). NHLers
    run above his (27.8% / 23.0%), most in late picks. Not independent (same drafts, same WAR). (2) Who
    collected the surplus (1,080 drafted skaters who played; $3,517.7M): the drafting club 92.1%,
    rights traded before his first NHL season ended 5.7%, rights lapsed and signed elsewhere 2.2% (55
    players; Spurgeon, Hagel, Muzzin, Hayes). Zeroing the lapsed group moves the pooled scale -0.5%.
    **Decided (Thomas, 2026-10-09): zero them.**
  - **Built (2026-10-09).** `20_CODE/pick_curve.py` v1.0 prices every drafted player 2007-2017 under all of
    the above (2,322 picks, 233 goalies; guards: windows equal the window count for 2,322 of 2,322,
    skater surplus equals the tested no-slides version for 2,089 of 2,089) and fits the scales: pooled
    31.66 (se 2.74); knowable 25.56 (2017-18), 27.45, 27.19, 26.40, 24.16 (2021-22), 24.62, 26.19, 29.62,
    30.95 (2025-26). 68 lapsed-rights picks zeroed ($104.6M of $4,022.2M). `20_CODE/traded_pick_values.py`
    v1.1 values every traded pick: during its own draft, its actual slot (188); the next draft's pick
    after that season's first game, the slot its original team's standings on the trade date give
    (156; median miss against the actual slot 2, largest in round 1 10, lottery not modelled); before
    that season's first game or a later draft, the round average for that draft's team count (51 + 239).
    634 picks from 2017-07-01 to 2022-03-28 (where trades.db ends): $575.4M knowable, $704.8M pooled.
    Conditional picks (113 here) valued as unconditional until resolved.
  - **Status:** the pick curve is built; the prospect model is not started.
- a slope that varies by draft year;
- negative careers counted as negative, or floored at zero (this matters only for the WAR version;
  in dollars, a season is already priced no lower than the league minimum);
- the separate look at top picks: the top 10, with the top 15 as the test;
- entry-level cost: the old way (the entry-level maximum for his class, with slides modelled, where a
  season sent back to junior does not count toward the deal) against no slides.
- *How a test is won (Thomas, 2026-10-09):* prediction error in dollars on draft classes left out of
  the fit, one class at a time, resampling classes rather than players. The bar is declared in the
  test script before it runs.

- *Goalies (Thomas, 2026-10-09): test all three* (one curve with skaters, goalies priced on the goalie
  line; a separate goalie curve; goalies left out). His first guess: "its best to go assuming only
  players are drafted", read as skaters only.

**Cap growth (Thomas, 2026-10-09):** "lets just keep the 3% for now." No 4-5% sensitivity for now.

**Prospects**
- *Outline (Thomas, in the meeting):* the draft slot as the starting estimate, plus the prospect's own
  information: production history (Elite Prospects, adjusted to NHL terms) and physical traits such as
  size. Any step that reads his recent seasons uses 50/30/20 unless Thomas decides otherwise.
- *Undrafted prospects (Thomas, 2026-10-09):* the same model as drafted prospects, without the
  draft-slot starting estimate.

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
- **Result** (`25_TESTS/aging_investigations_abc.py` v1.0 (laptop, 2026-10-05; baseline 1.1506 / 1.3598 / 0.8093
  on 40,510 player-seasons, PASS; each version one change against the build; start / whole one to five
  seasons out / season WAR; "lower in" of 2,000 career resamples)): A1 (by position) 1.1505 / 1.3598 / 0.8093, lower in 1,990 / 1,996 / 2,000;
  A2 (no self-pairs) unchanged at four decimals, lower in 0 / 23 / 0. Pooled yardsticks 2.527-2.565;
  forwards 2.492-2.562, defence 2.536-2.575.
- **Decided (Thomas, 2026-10-05): adopt A1, drop A2.**
- **Combined run:** `25_TESTS/aging_abc_followup.py` v1.0 (laptop 2026-10-05; v1.0 figures reproduced): A1 + C2 + C6 together
  1.1506 / 1.3587 / 0.8088 (MAE 0.4673) against the build's 1.1506 / 1.3598 / 0.8093; whole and season
  WAR lower in 2,000 and 2,000 of 2,000, start in 517; costs, counted: MAE +0.0002, one season out
  +0.0002, age 35+ +0.0010 (C6), one-season start bias +0.166 to +0.171 (C2); the gain is mostly C2's.
- **Implemented** in `aging_curve.py` (`h_by_pos`, used by `_weights`; the pooled `h` kept for
  reporting) with C2 and C6, `skater_forecast.py` v2.1; `25_TESTS/abc_build_check.py` v1.0 holds it to
  the tested version (passed on the laptop 2026-10-05: gaps 0, figures reproduced).

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
- **Result** (`aging_investigations_abc.py` v1.0, laptop): B1 (comparables only) 1.1505 / 1.3678 /
  0.8120, worse on the walk in 2,000 of 2,000, most for under-22s (1.8119 against 1.7384) and where the
  league carries 25%+ of the estimate (1.6444 against 1.5586). B2 (thin histories: a 10-game league
  fallback) improves the start of no-profile players (1.1203 against 1.1271; start lower in 1,999)
  and nothing after (whole 1.3599, season WAR 0.8094).
- **Decided (Thomas, 2026-10-05): keep the weight of ten.** B closed; B2 not adopted.

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
- **Result** (`aging_investigations_abc.py` v1.0, laptop; start / whole / season WAR, base 1.1506 /
  1.3598 / 0.8093): C1 level -0.50 1.1494 / 1.3767 / 0.8139, -0.25 1.1499 / 1.3670 / 0.8113, +0.25
  1.1515 / 1.3552 / 0.8080 (worse at the start and one out, better from two out; no turning point
  reached); C2 returners not filled 1.1507 / 1.3588 / 0.8089 (whole and WAR lower in 1,999 and 2,000);
  C3a 1.1505 / 1.3671 / 0.8123 and C3b 1.1506 / 1.3610 / 0.8100 (worse); C4 no filled-in seasons
  1.1509 / 1.3612 / 0.8092 (WAR lower in 1,463, a wash; 35+ whole 1.0541 against 1.0066), so filling
  in departures does not double-count in a way that costs season WAR; C5 relaxed pool for thin
  histories 1.1488 / 1.3607 / 0.8098, start bias one season +0.166 to +0.104, two seasons +0.100 to
  +0.039, but the two-season walk worse (1.3939 against 1.3802); C6 departed games = his own 1.1506 /
  1.3596 / 0.8092 (lower in 1,193 / 1,934 / 1,965).
- **Decided (Thomas, 2026-10-05): adopt C2 and C6;** keep the zero, keep filling in, keep short next
  seasons dropped.
- **C5 on the comparables' level only** (`aging_abc_followup.py` v1.0): start bias down (on the
  combination: one season +0.171 to +0.136, two seasons +0.105 to +0.067; start lower in 1,990), but the
  walk and season WAR worse (lower than the combination in 46 and 97 of 2,000); C5 in full on the
  combination also worse (510 and 565). The thin-history start runs high while the walk after it runs
  low, and the two partly cancel; fixing the start alone breaks that. **Decided (Thomas, 2026-10-05):
  C5 dropped** in both forms; the offsetting-bias finding is in WORK_QUEUE with the long-horizon
  under-forecast.
- **Implemented** with A1: `skater_forecast.imputed_aging_model` (v2.1) skips a player who appears
  again at a later age before the page (C2) and enters a departed season at his own games (C6);
  `aging_curve.DEPARTED_GP` removed. Combined run: `25_TESTS/aging_abc_followup.py` v1.0 (laptop 2026-10-05; v1.0 figures reproduced): A1 + C2 + C6 together
  1.1506 / 1.3587 / 0.8088 (MAE 0.4673) against the build's 1.1506 / 1.3598 / 0.8093; whole and season
  WAR lower in 2,000 and 2,000 of 2,000, start in 517; costs, counted: MAE +0.0002, one season out
  +0.0002, age 35+ +0.0010 (C6), one-season start bias +0.166 to +0.171 (C2); the gain is mostly C2's.

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
- **Update (2026-10-05):** since v2.0 the line no longer has the above-one-win term (build rule,
  Thomas); its inputs are the trailing share, defence, experience, age - 27 and the trailing total.
- **Versions approved (Thomas, 2026-10-05):** D1 fractional logit, D2 the line plus age squared, D3
  both; `25_TESTS/games_and_playing_de.py` v1.0.
- **Result** (`25_TESTS/games_and_playing_de.py` v1.0 (laptop 2026-10-05; baseline PASS; 40,510 player-seasons; 2,000 career resamples); games-share RMSE / season-WAR RMSE, build 0.2657 / 0.8088): D1 fractional logit
  0.2636 / 0.8108 (share better in 2,000; season WAR lower in only 3); D2 line + age squared 0.2654 /
  0.8078 (1,825 / 1,982); D3 both 0.2628 / 0.8100 (2,000 / 65). The logistic curve fits the share
  better but worsens season WAR, and is worse where he really played 90%+ (0.2087 against 0.2068); D3
  shows the logit, not the age term, costs WAR. Today's cap binds on 0.10-0.48% of forecasts at every
  season ahead except four out, where it binds on 19.55% (a quirk of that season's fitted line; no
  version changes it).
- **Decided (Thomas, 2026-10-05): adopt D2;** cap and floor kept.
- **Combined run:** `25_TESTS/games_playing_followup.py` v1.0 (laptop 2026-10-05; v1.0 figures reproduced): D2 + E1 together
  games share 0.2654, log loss 0.4047, Brier 0.1313, season WAR 0.8075 / MAE 0.4656 against the build's
  0.2657 / 0.4044 / 0.1313 / 0.8088 / 0.4673; season WAR lower in 1,998 of 2,000 and better or equal at
  every season ahead; counted cost: log loss +0.0003 (lower in 780).
- **Implemented:** `skater_forecast.py` v2.2 (`GP_FEATURES` gains `age_c2`); `25_TESTS/de_build_check.py`
  v1.0 holds it to the tested version (passed on the laptop 2026-10-05: gaps 0, figures reproduced).

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
- **Versions approved (Thomas, 2026-10-05):** E0 a diagnostic for players under contract (forecast
  against played, by quality and season ahead); E1 the before-2018 marker put back
  (`contract_unknown`, excluded by the build); E2, which answers open decision 2: contracts signed
  after 1 July of their first season, the chance of playing read at 1 July against at the signing, on
  the seasons each covers; E3 a contract effect by quality (under contract x trailing total).
  `25_TESTS/games_and_playing_de.py` v1.0.
- **Result** (`25_TESTS/games_and_playing_de.py` v1.0 (laptop 2026-10-05; baseline PASS; 40,510 player-seasons; 2,000 career resamples)). E1 entered the fit only on pages 2019-2021 (earlier pages have no training season
  from 2018 on). E1: log loss 0.4047 against 0.4044 (lower in 744), Brier equal (970), season WAR
  0.8085 against 0.8088 (1,979), MAE 0.4653 against 0.4673. E3: no gain (season WAR 255). E2 (open
  decision 2): 884 late-signed contracts, 1,561 contract-seasons, played 0.916; read at 1 July mean
  chance 0.785, log loss 0.3309, Brier 0.1037; read at the signing 0.877, 0.2632, 0.0772; signing lower
  in 2,000 of 2,000 on both.
- **E0 (diagnostic): Thomas's concern confirmed.** Players under contract for the season (2018 on) are
  under-forecast, the gap growing with the seasons ahead: forecast against played 0.893 / 0.916 in the
  valuation season, 0.882 / 0.915, 0.876 / 0.912, 0.826 / 0.887, 0.786 / 0.877, 0.687 / 0.858 five out;
  worst for low-quality players (below 0 WAR two out: 0.647 against 0.820); even 2+ WAR five out
  0.779 against 0.910. Neither E1 (0.690 five out) nor E3 (0.719) fixes it.
- **Decided (Thomas, 2026-10-05): adopt E1, drop E3; test a fix for E0:** for seasons a player is
  under contract, a chance of playing estimated only on player-seasons under contract
  (`25_TESTS/games_playing_followup.py` v1.0, with D2 + E1 combined).
- **Follow-up result:** `25_TESTS/games_playing_followup.py` v1.0 (laptop 2026-10-05; v1.0 figures reproduced): D2 + E1 together
  games share 0.2654, log loss 0.4047, Brier 0.1313, season WAR 0.8075 / MAE 0.4656 against the build's
  0.2657 / 0.4044 / 0.1313 / 0.8088 / 0.4673; season WAR lower in 1,998 of 2,000 and better or equal at
  every season ahead; counted cost: log loss +0.0003 (lower in 780).
  The build's chance of playing carries NO contract information on pages 2015-2018 (no training season
  there has a visible contract; the export starts in 2018); from 2019 the contract column is in the fit
  at every season ahead. E0's under-forecast comes mostly from those pages: on 2019-2021 contracted
  players are close to calibrated (forecast / played 0.916 / 0.920, 0.920 / 0.920, 0.911 / 0.928,
  0.899 / 0.893, 0.875 / 0.898, 0.797 / 0.875 for zero to five seasons out; 1,622 to 80 rows). The
  contracted-seasons fit could be trained only from the 2019 page and over-forecast there (three out
  0.944 against 0.893; log loss on contracted rows 0.2304 against 0.2200; worse than D2 + E1 in 1,907 of
  2,000), season WAR unchanged. (Corrects the earlier reading that the contract effect drops out at
  longer horizons: it is absent at every horizon before 2019 and present at every one after.)
- **Decided (Thomas, 2026-10-05): build D2 + E1; the contracted-seasons fit dropped.** Implemented in
  `skater_forecast.py` v2.2 (`PART_EXCLUDE` emptied); `25_TESTS/de_build_check.py` v1.0. The pre-2019
  finding and the 2018 page (contracts starting 2018 are valued where contracts are invisible) are in
  WORK_QUEUE for step 6.

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
- **Status:** run 2026-10-05 (`25_TESTS/gv_investigation_f.py` v1.2, laptop; the recorded 60/40 checks
  reproduced first). On the same 6,027 player-seasons, r against GV-adj: 60/40 0.576; 50/30/20 0.588;
  starting level 0.604; WAR if he plays 0.624; expected WAR 0.623, 0.624 without contract status (none of
  the agreement comes through contract status). Forwards 0.649 -> 0.681, defence 0.302 -> 0.330; next
  season 0.538 -> 0.602. Paired career resample (2,000 draws, v1.3): the forecast beats the 60/40 total
  in 2,000 of 2,000 in each comparison (each Game Value version, forwards, defence, next season).
  `Circularity and Game Value.docx` updated. **Closed 2026-10-05.** Details: session 2026-10-04c.

---

**The to-investigate list is closed (Thomas, 2026-10-04): F is the final item.** New questions go to
WORK_QUEUE unless Thomas adds them here.

---

# Open decisions (raised 2026-10-04, not yet made)

These are choices put to Thomas during the read-through. They are not investigations; each needs
his decision before the code it touches is changed.

1. **DECIDED (Thomas, 2026-10-05): the July method, chain started from his chance of playing.**
   Built 2026-10-05 (`rfa_terminal_value.TerminalValuer.control_weight`; goalies
   `contract_npv.NPVEngine._calibrate_goalie_control`). **Who counts at the decision (Thomas,
   2026-10-05): a player who played one NHL game or more in the contract's final season.**
   P(plays | qualified) is measured on those players; for goalies both numbers are, as in July. It is
   the event the chain starts from, so an absence is charged once. The first build had no condition
   (goalies 0.348 a year against July's 0.788); the second used 10+ games in one of the three seasons
   before (goalies 0.726; skater fringe 83.9%, below replacement 74.9%), which charged a final-season
   absence twice (`25_TESTS/control_weight_check.py`: July's figures come back with 20+ games in the
   final season). Validated on the laptop 2026-10-05 (refresh at `dca0831`): goalies 0.902 x 0.859 =
   0.775 a year; skaters 100% / 100% / 88.2% / 67.8% by bucket. Each
   RFA control year is weighted by P(the club qualifies him) x P(he plays, given he was qualified),
   measured among qualified players, so each departure is counted once; the chain starts from his
   forecast chance of playing the contract's final season instead of 1.0. Goalies get a weight for the
   first time: Thomas's July sub-decisions stand (one pooled rate, a one-game bar). Built and measured at
   step 6, on the final forecast, with the qualify rates. Original entry:
   **The control-year weight.** Today each RFA control year is weighted only by the rate at which
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
2. **DECIDED (Thomas, 2026-10-05): at the contract's signing.** Built 2026-10-05
   (`skater_forward_projection.valuation_as_of`); validated on the laptop 2026-10-05 (refresh at `dca0831`). Built at step 6 with directive 5 (both
   date a contract's forecast at its signing). Evidence: investigation E2 above (log loss 0.2632
   against 0.3309, 2,000 of 2,000). Original entry:
   **When contract status is read for a contract valuation.** Contracts are valued at July 1 of
   their first season, so a contract signed after July 1 cannot see itself in its own chance of
   playing (1,533 of 2,759 priced skater contracts). Reading it at the signing raises 1,351 of 1,530
   re-datable values, median +$0.33M, total +$622M (`25_TESTS/late_signing_status_check.py`).
   Options: read status at each contract's signing (a code change), or keep July 1 and correct
   `skater_forecast.py`'s docstring. Same root as directive 5.
3. **The price of a delivered win.** The draft curve and any back-test outcome price realized
   wins; player contracts price forecast wins on their own line. Which price a delivered win
   carries must be decided once, for both sides of each trade. On hold under the 2026-10-04 triage;
   directive 6's restart waits on it.
   - **Decided (Thomas, 2026-10-05): the contract line.** A delivered season is priced by the same
     formula as a forecast season (`skater_forward_projection.price_constants()`, `XNPV1_RATE`), with
     the wins actually delivered in place of the forecast: intercept + price per win x wins + the term
     premium of the contract he was on, floored at the league minimum; a season not played is worth
     zero (its cap hit still paid). One currency for players and drafted picks on both sides of every
     trade. Because the line is straight, the average delivered value equals the forecast value when
     the forecast is right on average, so a back-test gap is mispricing or forecast error, not a
     currency difference. It rests on calibration: on 2022-2025 the built forecast's average miss by
     trailing tier runs -0.24 to +0.09 wins a season (2-3 wins under-forecast by 0.24); a calibration
     check measures it before the back-test is read. Options not chosen: a line fitted on delivered
     wins (two currencies for one player, the 10-02 tilt); the Stage 3 line (60/40 trailing wins).
     Left to the restart with the supervisor: how a drafted player's entry-level seasons are costed.
