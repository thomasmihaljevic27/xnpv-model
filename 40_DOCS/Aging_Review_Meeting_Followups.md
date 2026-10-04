# Aging review meeting: questions, requests and follow-ups

**What this is.** A working note for preparing the next supervisor meetings (Tuesday 2026-10-06 at 1:00 PM
for one hour, Wednesday 2026-10-07 at 10:00 AM). It is not a reader-facing document.

**Source.** Thomas's meeting notes and the transcript of the meeting held the week of 2026-09-28. The
meeting walked through `40_DOCS/Supervisor_Drafts/Data, Production, and Aging.docx` and its Excel
walkthrough (Ryan O'Reilly example).

**Checked against** (2026-10-03, branch at `3c21f39`):

- `20_CODE/aging_curve.py`, `20_CODE/skater_forecast.py` and `20_CODE/participation_model.py`;
- `40_DOCS/Model_Changes_September_2026.md` §3, which reports the settings tests;
- `00_STATE/STANDING_FLAGS.md` (the aging choices entries of 2026-09-28).

---

## 1. Settle this first: the document under review describes the archived model

The aging document and the spreadsheet both describe **xNPV 0**, the anchor-and-ratio model that was
archived on 2026-10-02. Since then contracts are priced on **xNPV 1** (D33). Several things the
meeting treated as planned changes are already in the live model. Other topics the meeting spent time
on no longer affect any price.

| Topic | The document under review says | xNPV 1 (live) does | Where to read it |
|---|---|---|---|
| Starting estimate | 60% last season, 40% the season before | Three seasons, with the weights' decay fitted on earlier seasons, then pulled toward the league by a fitted line | `skater_forecast.py` docstring, step 1 |
| How aging is applied | The curve's % change multiplies the baseline (1.6 → 1.36) | The curve's yearly changes in wins are **added** to the start | step 2; `_walk`, `_changes` |
| Ratio guard rules (Section 4: 0.25 cutoff, cap of 3, floor at 0, negative → replacement) | Live | Gone. There is no ratio, and a negative start gets no floor (D12 v3 superseded for skaters) | step 2 |
| 55/45 own form vs comparables | Sets the curve's starting point | **Has no effect on xNPV 1's forecast.** xNPV 1 reads only the curve's year-to-year *changes* (level at age+k minus level at age). The 55/45 blend sets only the curve's starting level, so it cancels out. The pull toward the league comes from the fitted start line instead | `_changes`: `lv[age + k] - lv[age]` |
| Seasons the aging curve is fitted on | The whole file, including seasons after the valuation date | Only seasons that started before each valuation page (D3 revision, 2026-09-28) | `AgingModel(before=t0)`; `imputed_aging_model` |
| Leaving the NHL | A logistic exit table (4 quality × 5 age groups, 2018-2024), compounded into survival | For skaters: a chance of playing **for each future season**, with contract status as an input. It is not compounded, so a player can be absent one season and back the next. Goalies keep the exit table | `participation_model.py` docstring; D18 superseded for skaters |
| Games played | Not modelled (per-82 rate, total baseline) | Forecast: a games share per horizon, fitted on trailing share, position, experience, age **and the player's level** | step 3, `GP_FEATURES` |

The 55/45 point comes from reading the code: in `_changes` the curve's anchor drops out of every
difference. No run has tested it. A one-line check on the laptop would confirm it: set
`aging_curve.LAMBDA` to 0.3 and to 0.8, refit one page, and compare the forecasts.

**Consequence for the meeting record.** Thomas committed to four things that are already done in
xNPV 1: remove future data, switch to additive changes, move to three seasons, and treat games played
as possible future work. The agenda item already in `WORK_QUEUE.md` (item 2) covers the right
material: xNPV 1's changes and the revised locks D3, D12 v3, D18 and the price line. **Suggest opening
Tuesday with it**, before going on to the next document. Otherwise the review keeps spending time on
mechanics that no longer price anything.

---

## 2. The supervisor's questions, and their status

### Settled or answered in the meeting

**1. Who is in the yardstick pool? Can a player be paired with himself?**
- *In the meeting:* the pool is every pair of qualifying profiles. Both agreed to remove self-pairs.
  Thomas said removing them made predictions "about 1% worse".
- *Records:* the yardstick is the median distance over every pair in a random sample of up to
  1,200 profiles per position. A player's own pairs are included (`_build_bank`). The comparables
  themselves already exclude the target player (`_weights(..., exclude=player)`).
- **Removing self-pairs changed forecast error by less than 0.01%, not about 1%**
  (`Model_Changes_September_2026.md` §3). Redrawing the random sample moves the yardstick more than
  removing them does.
- *Bring:* the corrected figure, and see §3 on whether to implement it.

**2. Why multiply by the square root of the weights?**
- *Answered:* it is arithmetic only. (√w·z_a − √w·z_b)² = w·(z_a − z_b)², so scaling each measure by
  √w gives the same result as weighting the squared difference. This is recorded in §3 of the same
  document. Settled.

**3. The O'Reilly profile tab's column I (weighted scores) is computed but never used.**
- *Agreed in the meeting.* This is spreadsheet housekeeping: remove the column or label it. The
  spreadsheet is the xNPV 0 walkthrough in any case (see §4, request 2).

**4. The comparable weights stay fixed as the projection moves forward. What should the reader take
away from that paragraph?**
- *Answered aloud, and the supervisor agreed.* The code confirms it: `project()` computes the
  candidates and weights once, at the profile age, and reuses them at every later age.
- *To do:* rewrite the paragraph. The worked rewrite in the writing skill is built from Thomas's
  spoken explanation.

**5. How are there players with unknown age?**
- *Fixed.* The rebuilt age table has birthdates on 99.9% of skaters (STANDING_FLAGS, 2026-09-28b), and
  the runners refuse a table under 99%.

### Open: an answer to correct or complete before Tuesday

**6. Forwards and defencemen share one yardstick. Should they have separate ones?**
- *In the meeting:* "a simple fix", to be made.
- *Records:* already tested. Separate yardsticks (2.49 for forwards, 2.57 for defence, against 2.53
  pooled) changed error by **less than 0.01%** (§3). The code still pools them.
- *Bring:* the test result, and a decision (see §3).

**7. Does the aging curve use future data?**
- *In the meeting:* "Yes, and that'll get fixed."
- *Records:* **fixed on 2026-09-28** (D3 revision). The curve, the z-score scales, the yardstick and
  the league-average curves are all fitted on seasons before each valuation page. In xNPV 0's chain
  the fix cost 1.73% in season-WAR RMSE (root mean squared error). xNPV 1 is fitted the same way.
- *Bring:* this is done. The supervisor said he is sympathetic to both arguments (aging as a fixed
  natural pattern, or only what clubs could know at the time). The model takes the stricter one.

**8. Why does the league average get a weight of 10?**
- *In the meeting:* "basically arbitrary". Thomas said it exists to protect the ratio arithmetic, and
  that adding changes instead of multiplying makes it unnecessary.
- **The code says otherwise.** `SHRINK_K = 10` is a pseudo-count, "pull thin comp estimates toward the
  global curve". In `_shrunk` the comparable average is (Σ w·v + 10·league) / (Σ w + 10). It applies
  to the curve's starting level **and to every yearly change**. It has nothing to do with ratios, and
  the additive switch does not remove it.
- It matters most at older ages, where fewer comparables have an observed change and their weights
  sum to less. O'Reilly's 95.9% from comparables is one player at one age.
- *Records:* any value from 0.01 to 20 gives the same error to within 0.06% (STANDING_FLAGS
  2026-09-28; §3). That is exactly the defence the supervisor asked for ("I tried these different
  values and nothing really changed").
- *Bring:* the correction and the test.

**9. Why a Gaussian (bell-curve) weighting function?**
- *In the meeting:* Thomas did not know. The supervisor accepts it if the paper justifies it with
  **academic references**.
- *Evidence already on record* (§3), scored on held-out careers on the aging curve itself before
  xNPV 1 was adopted:
  - weighting every same-age player equally was worse on each of four comparisons, by 0.5% to 0.9%;
  - a narrower weighting (half the yardstick) was better on each, by 0.2% to 0.6%. It was not adopted
    because it was one of many settings tried on the same data.
- *The argument, in plain terms:* this is kernel-weighted matching. Every comparable gets a positive
  weight that falls smoothly with distance, so there is no hard cutoff at a fixed number of
  neighbours. A standard result in kernel smoothing is that the shape of the kernel matters much less
  than its width (the yardstick). The yardstick here is the median pairwise distance, a known rule of
  thumb (the "median heuristic").
- *Candidate references.* Check each one before citing it:
  - Nadaraya (1964), "On Estimating Regression", *Theory of Probability and Its Applications*;
    Watson (1964), "Smooth Regression Analysis", *Sankhyā A*. These are the kernel-weighted average.
  - Heckman, Ichimura and Todd (1998), "Matching as an Econometric Evaluation Estimator", *Review of
    Economic Studies*. This is kernel matching in econometrics and probably the strongest fit for an
    econometrics reader.
  - Abadie and Imbens (2006), "Large Sample Properties of Matching Estimators for Average Treatment
    Effects", *Econometrica*. This is nearest-neighbour matching, the hard-cutoff alternative.
  - Silverman (1986), *Density Estimation for Statistics and Data Analysis*; Wand and Jones (1995),
    *Kernel Smoothing*. These cover kernel shape against bandwidth.
  - Hastie, Tibshirani and Friedman (2009), *The Elements of Statistical Learning*, ch. 6. This is a
    textbook treatment.
  - Garreau, Jitkrittum and Kanagawa (2017), "Large sample analysis of the median heuristic", arXiv.
    This covers the median-distance yardstick.
  - Silver's PECOTA comparables (Baseball Prospectus, 2003). This is a practitioner precedent for
    similarity-weighted player aging, not peer-reviewed.

**10. Leaving the NHL: how was the 1.2% computed? What does the logistic-model paragraph mean? He wants
to see the regression.**
- *In the meeting:* Thomas said he can lay out the table.
- *Records:* for skaters, that exit table no longer prices anything. The relevant fitted model is now
  the chance of playing (`participation_model.py`): one probability per future season, with contract
  status as an input. Goalies still use the exit table.
- *Bring:* the participation model's fitted coefficients for each horizon, as a regression table with
  standard errors, plus the goalie exit table. Neither table exists as a document yet. Producing them
  is a laptop task, since the fits need the vendor export.

**11. Is games played random, or does it depend on the player's quality? What is the average?**
- *In the meeting:* Thomas said the average is "about 48 of 82, according to the database". The
  supervisor's two reasons for missing games were injury or rest, and not being dressed by the coach.
  The agreed note: possible future work.
- *Records:* xNPV 1 already forecasts games share, fitted on trailing share, position, experience, age
  and the player's level. So its answer to "a function of quality?" is yes: level is an input.
- The 48 figure was not checked in this session; the season table is not in the cloud clone. It
  probably counts every player-season, call-ups included. Bring a computed figure for all
  player-seasons and for seasons of 10 or more games, and the games-share coefficients.

### Information requests

1. **A worked contract table** (O'Reilly, five-year deal). For each season: projected WAR, the chance
   he reaches that season, and the expected WAR that results.
   - For xNPV 1 the columns are: the rate per 82 games, the games share, the chance of playing,
     expected WAR (the product of those three), the price per win, the discount factor, and the value.
   - `valuation_walkthrough.py` was archived with xNPV 0, so an xNPV 1 walkthrough has to be built.
     It can be built from `30_OUTPUT/xnpv1_forecasts.csv` on the laptop.
2. **Talk through the spreadsheet's formulas in the rewrite** ("these are the formulas used"). The
   spreadsheet needs an xNPV 1 version first. Otherwise the document will explain formulas that no
   longer run.
3. **Are draft-pick values inflation-adjusted?**
   - *In the meeting:* "they should be. They're discounted."
   - *More precise answer:* `draft_yield_curve.py` values picks in **cap shares** (the price of one
     win is stated as a share of the cap), so cap growth is handled by construction. Discounting is a
     separate step.
4. **Have you started pricing trades in dollars?** Status given: players yes; draft picks started (a
   banded yield curve over 2007-2018 drafts); prospects not started. Pricing the trade ledger has not
   started.
5. **The summer question: a contender trades a pick at the deadline, gets better, and so the pick
   falls in value.** Thomas's answer: freeze the pick at its projected slot when it was traded, and
   apply the same rule to next-year picks. A dynamic version is out of scope. *To do:* state it as an
   assumption in the draft document, after checking what `draft_pick_linkage.py` does for future-year
   picks. This session did not check it.

### Points raised that need no action beyond the write-up

- **Survivorship at older ages.** The comparables thin out with age and come to look like elite
  survivors. This is already a stated limitation. The star under-forecast is concentrated in five
  generational players (`Star_Miss_Checks.md`).
- **Scope.** "At some point you just have to say this is as far as I can go." That applies to
  alternative aging methods, and to the dynamic pick question above.

---

## 3. Decisions for Thomas before anything is implemented

The meeting agreed to two code changes: remove self-pairs from the yardstick, and split the yardstick
by position. **Both are cheap to write and expensive to ship.**

1. They change `aging_curve.py`, which D3 governs. That makes them a deliberate revisit of a locked
   decision.
2. They change xNPV 1's forecasts. `XNPV1_RATE` is locked, and its reproduction guard requires each
   re-run of `xnpv1_price_line.py` to give the lock back. Any change to the curve therefore means
   re-fitting and re-locking the price line, then re-running the valuations.
3. Both were tested, and each moved error by less than 0.01%.

**Recommendation:** do not implement either. Report the two tests in the paper as robustness checks.
They answer the supervisor's concern ("is this choice arbitrary?") without moving a locked number. If
the supervisor still prefers the cleaner construction, batch both into one revisit with a
fingerprinted before/after (rule: check 46).

The other meeting decisions need no code:

| Agreed in the meeting | Status |
|---|---|
| Keep 55/45 | It stays in the curve, but it does not move xNPV 1's forecast (§1). Say so before the supervisor spends more time on it |
| Move to 50/30/20 | xNPV 1 uses three seasons with a fitted decay, not a fixed 50/30/20. Bring the fitted weights |
| Hold comparable weights fixed from the start | Already how the code works |
| Remove future data | Done 2026-09-28 |
| Games played as future work | Already modelled in xNPV 1 |

---

## 4. Timeline agreed

- Finish going through the documents before **reading week**, two weeks after the meeting. That ends
  with a list of what to change or investigate.
- Implement over reading week, since this month has a light course load.
- November: final model and results.
- **Before the end of November:** the paper goes to the second reader, a department member chosen
  because he knows hockey and is a tough critic. The deadline is set because December is busy for
  readers.
- Thomas prefers to finish the model before writing, to avoid revising text after model changes.

---

## 5. Corrections to the AI-generated meeting summary

- **"50/30/20 (most recent season / prior season / league average)"** is wrong. 50/30/20 is three
  seasons (last, the one before, and the one before that). The league average is not one of the
  three.
- **Games played "could matter for older players where the comparable pool shrinks"** joins two
  separate topics. Neither speaker linked them.
- **"Implement before reading week: yardstick split, remove future data, additive changes,
  50/30/20".** Three of the four are already in xNPV 1. The fourth was tested at under 0.01% (§3).
- **The exit-model section** describes the skater exit table as current. For skaters it no longer
  prices anything.
- **"Removing self-comparisons: accuracy drops about 1%".** This repeats the figure said in the
  meeting. The recorded effect is under 0.01%.
- **"Forward the aging walkthrough"** is listed as an action item. The supervisor forwarded it during
  the meeting.
- **The answer to the square-root question** is missing from the summary. It was answered: arithmetic
  only.
- **The writing feedback** is reduced to "glossary, subheadings, tell a story". The full points are in
  `.claude/skills/writing-style/SKILL.md` Part 1.
