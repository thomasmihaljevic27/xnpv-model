# 01. Draft Pick Model, Sequenced

Generated 2026-07-29. **Rewritten 2026-09-28** against the current tree, with the design
decisions Thomas made that day so work can resume without a decision round first. Position in
the overall order: first of the three structural documents.

## Where it stands

**Built and reproducible.** The pick linkage (`draft_pick_linkage.py` v1.1, 4,765 picks
2005-2026) and the yield curve (`draft_yield_curve.py` v1.1, 2007-2017 classes, Rule A) were
re-run on 2026-09-28 into a scratch folder and all three outputs matched the live files by
hash. The curve is priced on the same Stage 3 rate as the player chain (checked in the code:
intercept 0.0132478, 0.0212323 per win for forwards, 0.0241026 for defencemen).

**The entry gate is met.** The July version of this document said not to start until the
rebuilt curve had been reproduced locally. That happened on 2026-09-09 and again on
2026-09-28.

**Recreated 2026-09-28.** The July investigation's `slot_curve.py`, `future_pick_premium.py`
and `future_pick_premium_diagnostics.csv` could not be found in git (any branch), the local
tree, Dropbox (archive included) or any local transcript. They were rebuilt from the recorded
findings. `slot_curve.py` v2.0 prices a pick number off the curve and holds both unknown-slot
conventions. `future_pick_premium.py` v2.0 must reproduce the recorded sample before it prints
anything. It does: 119 pick-only trades, 56 across drafts, 39 one-for-one, 35 same-round, 17
bundles. What does not reproduce is recorded under step 3.

**The player-model choice is still deferred.** The rebuilt skater model or the current chain
has not been chosen. That waits for the next supervisor meeting, which will cover further
tweaks and whether to pursue the player-comparables model or the regression approach. The
draft curve only needs the price per win, which it reads mechanically (Rule A), so whichever
model wins, the curve is a re-point and not a refit.

---

## Step 1. Band boundaries: settled, not a reopen

The bands (1, 2, 3-5, 6-10, 11-20, 21-32, 33-50, 51-100, 101-150, 151-224) are a code
constant, `BUCKETS` at line 192 of `draft_yield_curve.py`. None of D22-D27 fixes them; they
appear only in the reported results. Replacing them is a build step.

## Step 2. Set the bands with a break test (decided 2026-09-28, D29)

**Decision.** Where the curve's value level genuinely changes is to be found from the data,
by a structural-break (change-point) test on the per-pick surplus, and the bands placed there.
A structural-break test asks where a sequence's average steps from one level to another. Here,
it asks at which pick numbers the expected surplus drops enough to call it a new tier.

**Why this matters.** The current bands caused a live failure: the 51-100 band gives fifty
slots one value, so a trade-down inside it priced at exactly zero and pushed the discount
estimate to nonsense. The 151 boundary also splits round 5 in two.

**Design points to settle when it is built.**
1. **The unit of evidence is the draft class, not the pick.** Each pick number has 11
   observations (one per class 2007-2017). Choose the number of breaks by leave-one-class-out
   prediction, and put intervals on the break locations by resampling whole classes.
2. **Keep the curve decreasing.** An earlier pick is never worth less than a later one. Impose
   it on the fitted levels.
3. **What bands still cannot do.** Any step curve prices a trade-down inside one band at zero,
   whatever the break test says. If the break test finds wide bands in the middle rounds, the
   zero-gap problem comes back. The earlier plan's alternative (a smooth fit that only
   decreases, such as isotonic regression or a monotone spline) avoids that. Compare the two
   on the same held-out classes before choosing, rather than assuming the breaks settle it.
4. **Do not use a single global formula.** One was tried and overstated pick 1 by 112%.
5. Carry the three attachments the July plan listed: intervals by resampling classes (the
   code's current bootstrap is 2,000 resamples); a winsorized robustness leg, never the
   headline; and a split into the chance a pick produces anything times the value it produces
   when it does. The top 5% of picks hold 42% of the tail band's total.

## Step 3. Price actual traded picks

**Decisions taken 2026-09-28.**

- **Unknown slots (D30).** A pick whose number is not known on the trade date is assumed to
  land where its original team picked in the most recent draft held before the trade. If a
  team picked 20th in 2025 and trades its 2026 first, the pick is priced as 20th. The team's
  first-round position is applied to every round. Implemented as
  `slot_curve.own_slot_overall`; the original team comes from the NHL record's pick-ownership
  chain. It matters mostly in the first round, where the curve is steep. **Open detail for
  Thomas:** for a trade in mid-season, "where the team is that day" could instead mean its
  position in the standings on the trade date. The implementation uses the last completed
  draft, which matches the worked example. Say if in-season standings were meant; the game-log
  store (2017-18 onward) would supply them.
- **A pick's number counts as known** from three days before its draft. The order is set once
  the Stanley Cup Final ends; from the Final's end dates (recalled, not taken from project
  data) that is at least four days before the draft in every year 2018-2025. 2026 is unchecked,
  and no 2026-draft pick trade falls in that window in the May export anyway. Only inside that window is the trade export's
  `overall_position` read. Outside it, that field is never used: it is back-filled with a
  number nobody knew on the day.
- **Conditional picks (D31).** Assume the conditions are met: the pick conveys as described
  in its conditional form. 161 of 1,112 pick rows carry condition text, which will need coding
  by hand into round and year. The export's condition flags are as of the export date and are
  not read.

**The future-pick premium: still open.** Nothing was decided. The choices, when this resumes:
(a) no premium: a later pick is discounted only by the model's own discounting, which under
D24 cancels, so next year's first equals this year's first at the same slot; (b) a premium
estimated as bounds from the corner-solution trades (below); (c) the repeat-sales estimate in
step 5, once prospects are priced. Any premium must cover only arrival delay and uncertainty
about the slot, never bust risk, which the curve already prices.

**Why a point estimate is not available.** The 17 bundle trades are the whole estimation
sample. Clubs cannot trade cash, so the smallest unit of consideration is a late pick; a trade
closing a smaller gap is a corner solution, not an equilibrium price, and gives an inequality
rather than an equality. The set of inequalities identifies bounds.

**What the recreated script shows (2026-09-28, current banded curve).** Pooled discount per
draft 0.459 under round-mean slots and 0.512 under the own-slot rule (recorded in July on the
pre-rebuild curve: 0.486 and 0.510, with a criterion that was not written down). **Not
reproduced:** only 8 of the 17 bundles can be balanced by any discount between 0 and 1 (July
recorded a per-trade range of 0.015 to 0.689), and the sweetener-size-to-slot-gap correlation
is 0.02 (round-mean) and 0.24 (own-slot) against a recorded 0.735. 3 of the 9 unbalanced
trades have a current-year gap of exactly zero because both current picks sit in the same
band; the other 6 are unexplained. Re-examine on the break-test curve before reading anything
into either set of numbers.

## Step 4. The tail against the smallest tradeable unit

Unchanged from July. The curve prices a pick in the last band at about $0.61M at the 2025-26
cap (rebuilt curve), but that is the mean of a lottery: the median outcome is zero, and a late
pick is also the standard makeweight in trades closing much smaller gaps. Either the tail is
overvalued relative to how clubs treat it, or clubs undervalue late picks, and the pick-only
sample cannot tell these apart. Step 2's split into hit chance times conditional value is the
instrument, because it lets the makeweight question be asked of the right piece.

## Step 5. Repeat-sales estimate of the future-pick discount

Deferred until the prospect pillar prices the other side of mixed trades. 811 distinct picks
appear in the trade export, 241 traded more than once, 163 at two or more different horizons.
Pricing one identical pick at two horizons gives the discount from the ratio, with the slot
convention dropping out. Only 4 of the 163 have every leg inside pick-only trades.

---

## Data in hand for this pillar (checked 2026-09-28)

| Need | Where | State |
|---|---|---|
| Pick-to-player linkage | `30_OUTPUT/draft_pick_linkage.csv` | 4,765 picks; reproduces |
| Curve | `30_OUTPUT/draft_yield_curve.csv` | reproduces by hash |
| Original team of every held pick | `30_OUTPUT/draft_raw/*.json`, field `teamPickHistory` | all 22 drafts, none missing |
| Traded picks | PuckPedia trade export (May 2026) | 1,112 pick rows, 811 distinct picks; round and original team on every row |
| Picks traded before their draft | same | 820 of 1,112 need the slot convention |
| Conditions | same, `draft_pick_conditions` | 161 rows, free text; to be hand-coded |
| Standings on a trade date | game-log store, 2017-18 onward | only needed if in-season standings are chosen for D30 |

## Identification notes

- **Look-ahead.** The back-filled `overall_position` is the live threat. It is read only
  inside the three-day window before a draft.
- **Left-truncation.** Settled by D25 (2007-2017 classes, complete windows only).
- **Name-match exposure.** 16.3% of curve value rests on a name match rather than an
  identifier (2026-07-28 rebuild). State it wherever the curve is cited.
- **Charging bust risk twice.** The curve already prices bust probability per slot. Any
  future-pick premium that also charges it double-counts.
- **Shared input with the prospect pillar.** The curve's check against the draft-slot
  probabilities (`draft_slot_baseline.csv`) now prints r = 0.866 on the rebuilt curve (0.893
  was the original build). If the prospect model uses those probabilities as its prior, the two
  pillars share an input; say so rather than presenting the correlation as independent support.
