# The aging curve: what is being changed, and why

Written 2026-09-15 for `50_REBUILD/`. **A design for approval. Nothing here has been run.**
It is written from `20_CODE/aging_curve.py` as it stands, not from a summary of it.

## What the production curve does now

Given a player and the age you are valuing him from, it projects his WAR per 82 across the
future years of a contract, in three steps:

1. **Anchor** on a two-season average of his WAR per 82 (`WIN = 2`, seasons of 20+ games only).
2. **Pull that anchor toward a norm** for comparable players at his age — 55% his own form, 45%
   the norm (`LAMBDA = 0.55`). Comparables are found by kernel-weighted matching on a
   standardised style profile (the five WAR components bar penalties, ice time, level, and a
   trend term), with thin comparison groups shrunk toward a global position curve.
3. **Walk it forward** one year at a time by adding an age-conditional step, where the step is
   the average year-over-year change in WAR per 82 among comparable players at that age.

Its validation reports 0.898 and 1.034 wins per 82 of error at one and six years, against 1.048
and 1.264 for the older global curve.

## The five things being changed

### 1. Additive on the shrunk rate, not a ratio on a raw total

**Now:** the forward projection in the value chain multiplies a raw trailing WAR total by an
aging *ratio*. That needs four guards to stay sane — a floor on the base, a cap on the ratio, a
floor on the ratio, and a flat fallback — because a ratio applied to a number near zero or
below zero does something meaningless.

**Change:** the curve becomes a *difference* in WAR per 82, added to the shrunk rate from the
forecast. Under a straight-line price on wins, adding is exactly right, and **all four guards
disappear** rather than being retuned. A negative anchor stops being a special case.

### 2. The double-shrink comes out — this is the important one

The production curve does its own mean reversion at `LAMBDA = 0.55`, pulling a player 45% of
the way to a comparables norm before any aging is applied. The rebuilt forecast already does
that job, per component, with the amount fitted from evidence rather than set at 0.55.

**Running both would shrink every player twice**, once by a fitted amount and once by a fixed
45%, and the second pull is invisible inside something labelled "aging". So in the rebuild the
aging curve is *pure aging*: the expected change in rate from one age to the next, and nothing
else. Mean reversion stays where it is measured and can be audited.

This is the single biggest structural change, and it is the reason the rebuild's curve cannot
be a drop-in swap for the production one.

### 3. What the curve is fitted on

A smooth function of age, fitted on within-player year-over-year changes, refitted on each
decision date so it never sees the future, with:

- **age**, smoothly — a low-order polynomial or spline rather than a separate number per age,
  so the curve cannot wiggle on the 40-year-olds;
- **a level-by-age term**, because better players decline faster *in wins* — a 3-win player
  losing 10% of his ability loses more wins than a 1-win player losing 10%;
- **experience alongside age as a candidate**, kept only if it earns its place. A 24-year-old in
  his sixth season is not the same prospect as a 24-year-old rookie.

Fitted per position. Goalies keep their own branch.

### 4. Survivorship — the part a supervisor will press on

**The problem.** A year-over-year change can only be measured when the player plays both
seasons. The players who decline hardest are exactly the ones who stop playing, so their worst
year is never in the sample. The observed changes are therefore a *selected* sample and the
curve understates decline, most at the ages where it matters most. The production curve inherits
this: its delta series requires two consecutive qualifying seasons, and it drops non-adjacent
pairs outright.

Lowering the 20-game bar admits short seasons but does not touch this — a player who is gone
has no season to admit.

**Two fixes, run as competitors:**

- **Inverse-probability weighting.** Weight each observed change by one over the modelled
  probability that it would be observed at all. A 35-year-old's observed decline then stands in
  for all the 35-year-olds like him, including those who did not get a next season. The
  probabilities come from the participation model.
- **Imputation**, following Schuckers, Lopez and Macdonald: estimate what the missing seasons
  would have looked like and fit on the completed panel.

Both are scored on the same harness. The expected direction is a **steeper decline after about
33**, and if the correction does not move it that way, something is wrong with the correction
rather than with the expectation.

### 5. The comparables curve stays as a challenger

Not retired. The plan keeps it as a competitor, and it only goes if the additive curve beats it
on the held-back seasons. Its machinery is the most complex thing in the player pillar and it
may still be earning that complexity at long horizons.

## The sequencing problem, and what I propose

The survivorship correction needs a probability that a player is observed, and that is the
participation model — the plan's Phase 2, which is not built. Three ways to handle it:

| option | what it gives |
|---|---|
| Build participation first, then aging with the correction | One clean answer, but the additive change and the survivorship change land together and cannot be told apart. |
| Build a small hazard inside the aging work, for weighting only | Fast, but a second participation model in the codebase that will disagree with the real one. |
| **Uncorrected additive curve first, then participation, then the correction** | **Three measurable steps.** The additive-versus-ratio change is isolated, then participation is built once and used properly, then the correction is measured against a curve we already understand. |

**I propose the third.** It costs one extra run and it is the only order where, if the answer
moves, we can say which change moved it.

## What this opens

Locked decisions that a rebuilt curve reopens, all deliberately and inside `50_REBUILD/` only:
**D3** (the aging curve itself), **lambda** (the 0.55 mean-reversion split, which change 2
removes from the curve entirely), and **the comparables pool**. Production keeps running on
them untouched.

## What both anchors get

The star-bias tension from the anchor bake-off is unresolved: the two-season models are the most
accurate on 3+ win players and the three-season models are the most accurate overall. **Both
carry forward into aging.** Aging is the layer most likely to settle that disagreement, because
it is what governs the seasons where the two differ most.

## The acceptance test

The additive curve on the shrunk anchor must beat both the flat carry-forward and the
production-style ratio path, at horizons two through six, on the development seasons. Separately,
the survivorship correction must move the decline after 33 in the direction the participation
model implies. Neither is scored on whether total NPV rises or falls.
