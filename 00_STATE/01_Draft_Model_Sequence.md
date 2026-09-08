# 01. Draft Pick Model, Sequenced

Generated 2026-07-29. Position in the overall order: **first of the three structural documents.**

## Why This Pillar Goes First

Three reasons, in order of weight.

**It is closest to finished.** The linkage and the yield curve are built, locked, and confirmed on my machine under D22 through D27. Two steps remain, and both are already scoped. No other pillar is this far along.

**It has been shown empirically to survive a rate change.** This is the argument that decides the ordering. Every asset class is denominated in the currency set by the skater price equation, so any change to that equation propagates outward. The Stage 3 rate change was a real test of how much that matters here, and it moved the implied future-pick discount only from 0.486 to 0.503. The curve shape steepened, the pick-1-to-tail ratio going from roughly 16.9 to 22.4, and the downstream estimate barely moved. Finishing this pillar before the player-model batch therefore carries a measured, small risk of rework rather than an assumed one.

**Nothing else is waiting on it, but it is waiting on very little.** Only the repeat-sales estimator in step 5 needs another pillar, and that is why it sits last.

## Entry Gate

Do not start until the rebuilt curve has been reproduced locally. This is the second item in document 00, section 1. Until it closes, `draft_yield_curve.csv` on disk is the pre-rebuild version and every number computed from it is computed on the shallower curve. The 2026-07-28 future-pick work was explicitly told not to re-run against the stale mirror, and that instruction still stands.

---

## Step 1. Rule On the Band Boundaries Before Touching Them

**Check whether the current bands sit inside D22 through D27 or were an unlogged implementation choice.** The bands are 1, 2, 3-5, 6-10, 11-20, 21-32, 33-50, 51-100, 101-150, and 151-224. If they are inside a locked decision, replacing them is a reopen and needs an explicit call from me. If they were an implementation convenience that never got logged, step 2 proceeds without ceremony. This is a five-minute check that determines whether the next step is a decision or a build.

---

## Step 2. Rebuild the Curve Without Bands

Raised 2026-07-28. This gates step 3 and it is not optional, because the current bands caused a live failure rather than a theoretical one.

**The failure.** The 51-100 band carries one value across fifty slots, so trade-downs inside it priced at exactly zero and drove the discount estimate to nonsense. The 151 boundary also cuts round 5 in half, splitting a 1.27M round across two bands, and rounds 5, 6, and 7 at 1.27M, 0.81M, and 0.75M are pooled into a single tail value.

**The fix.** Drop bands in favour of a shape-constrained monotone fit, either isotonic regression or a monotone spline. Both pool noise locally and continuously instead of in blocks, and neither leaves a boundary to argue about. A monotone fit is a fitting method that is only allowed to move one direction as the pick number rises, which encodes the thing we already know to be true, that an earlier pick is not worth less than a later one, without imposing any particular curve shape.

**What will not work, and why it was already tried.** A global parametric form overstated pick 1 by 112%, because the real curve is far flatter across the top of round 1 than any such form permits. Do not revisit this.

**Attach three things to the rebuild.** First, bootstrapped intervals, because the reported analytic standard errors assume a far less skewed distribution than the data has. Second, a winsorized robustness leg, reported as a sensitivity and never as the headline. Third, a hit-rate times conditional-value decomposition, so the probability a pick produces anything and the value it produces conditional on producing can move separately. The outlier problem is severe enough to require all three: the top 5% of picks hold 42% of the tail band total across only 11 cohorts.

---

## Step 3. Price Actual Traded Picks

Shelved 2026-07-28 mid-investigation, with the design batch now partly answered. Resume here once step 2 closes.

**Decisions still owed before any pricing runs.**

**Unknown slots.** A future second traded before its number exists needs a convention. The candidates are a round-mean slot and a standings-conditioned expectation. Note that the back-filled `overall_position` field must never be used for this, since it carries a number nobody knew on the day.

**Conditional and protected picks.** Protection ladders and round-upgrade conditions need a decided rule. Currently there is none.

**The deferred future-pick premium, now scoped as bounds rather than a point.** The Pillar 2 specification says future picks discount at a higher rate than players, but the locked curve already prices bust probability per slot, so any premium may cover only arrival delay and team-identity uncertainty. It must never charge bust risk twice. This is Karl-sensitive on double-count identification.

**Why a point estimate is not available, and this is the substantive finding from 2026-07-28.** The pure pick-for-pick sample is 119 trades, 56 of them cross-year, of which 39 are one-for-one and 35 of those are same-round swaps carrying almost no information. That leaves 17 bundle trades as the entire estimation sample. A single fitted discount factor gives 0.486 under a round-mean convention and 0.510 under a team-own-slot convention, but per-trade implied values run from 0.015 to 0.689, ordered almost perfectly by how large the future sweetener is relative to the slot gap it buys. The parameter is not stable and the pooled figure is a least-squares compromise between trades that disagree.

**The mechanism, which is why bounds are the correct target.** Clubs cannot trade cash, so the smallest unit of consideration available is a late-round pick, which the curve prices near 0.81M. Any trade closing a gap smaller than that is a corner solution rather than an equilibrium price, and equality-based estimation applied to a corner is misspecified. Clubs are floored, not confused: sweetener size does scale with the gap, Spearman 0.735. Each corner trade therefore yields an inequality restriction rather than an equality, and the set of inequalities identifies bounds.

**Existing artifacts.** `slot_curve.py`, `future_pick_premium.py`, `future_pick_premium_diagnostics.csv`.

---

## Step 4. Resolve the Tail Versus the Minimum Tradeable Unit

Raised 2026-07-28 as a Standing Flag. This affects every back-test trade containing a small makeweight, which is most of them, so it cannot be left open.

The curve prices a pick in the 151-224 band at 0.00853 of the cap, roughly 0.81M, but that figure is the mean of a lottery. The median outcome is zero and 74.5% of those picks produce nothing. Because a late-round pick is also the smallest unit of consideration available, it is the standard makeweight in trades closing gaps far smaller than 0.81M.

**Two readings are observationally equivalent in the pure-pick sample.** Either the tail is overvalued relative to what clubs treat it as worth, or the curve is right and clubs systematically undervalue late picks. Staleness is not the explanation, since approximating the rebuilt steeper curve moved the implied discount only from 0.486 to 0.503.

Step 2's hit-rate times conditional-value decomposition is the natural instrument here, because it separates the probability from the conditional payout and lets the makeweight question be asked about the right component. Sequence it accordingly.

---

## Step 5. Repeat-Sales Estimation of the Future-Pick Discount

Raised 2026-07-28 and deliberately deferred. **Do not attempt this before document 02 closes.**

**The design.** The same pick is often traded more than once. 811 distinct picks appear in the PuckPedia trade file, 241 traded more than once, and 163 traded at two or more different horizons: 113 one year apart, 42 two, 7 three, and 1 four. Observing one identical asset priced twice, once when it was three drafts out and once when it was one, gives the discount factor from the ratio of the two prices. This is the Case-Shiller repeat-sales design applied to picks.

**Why it is strictly stronger than step 3's approach.** The underlying asset is held fixed, so the unknown-slot convention drops out of the comparison entirely and the minimum-denomination corner problem shrinks rather than dominating.

**Why it is deferred.** Only 4 of the 163 have all legs inside pure pick-for-pick trades, and 84 have at least one pure leg. The rest need the other side of each trade priced, which requires the player model verified and the prospect pillar built. That is a reason to sequence, not a blocker.

---

## Identification Notes for This Pillar

**Look-ahead.** The back-filled `overall_position` field is the live threat and it is specific to this pillar. Any ex-ante pick price that reads it is using a number that did not exist on the trade date.

**Left-truncation, resolved.** D25 set fitting cohorts to 2007-2017, complete D+9 windows only, dropping the truncated 2005-06 cohorts rather than backfilling. Settled, recorded here so it is not reopened by accident.

**Name-match exposure.** 16.3% of curve value rests on a name match rather than an identifier. Computed and locked at the 2026-07-28 rebuild. State it wherever the curve is cited.

**Double-counting bust risk.** The single most likely place Karl finds a problem in this pillar. The curve already prices bust probability per slot. Any deferral premium that also charges bust risk is charging it twice.
