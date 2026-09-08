# 02. Prospect Model, Sequenced

Generated 2026-07-29. Position in the overall order: **second of the three structural documents.**

## Why This Pillar Goes Second

**It is the last unbuilt pillar, and the largest remaining structural risk.** The paper's central contribution is that three asset classes price onto one common currency. Two of the three now do. Whether the third can is an open structural question, and it is a bigger risk than whether the market rate is a few percent off. Structural risk before calibration risk.

**It unblocks two things that are otherwise stuck.** The repeat-sales future-pick estimator in document 01 step 5 needs the other side of mixed trades priced, which needs prospects. The power-analysis re-run is meaningless until picks and prospects are both priced, since the 2026-06-30 run was taken against an almost-unbuilt model and near-total blockage was the expected floor rather than a finding.

**It goes after the draft model because it borrows from it.** Draft-slot baseline probabilities are the natural prior for a prospect with little professional evidence, and the yield curve's hit-rate times conditional-value decomposition is the same decomposition a prospect model needs. Building the draft side first means the prospect model inherits a settled structure rather than inventing a parallel one.

---

## Design Constraint, Read Before Anything Else

**Apply the market rate. Do not fit against it.**

This is the single decision that determines whether the overall ordering in these documents holds or inverts. Document 03 refits the market rate, and everything denominated in that currency has to be rebuilt afterwards. For the draft curve that rebuild was a one-line re-point, because Rule A makes post-ELC surplus zero by construction and the curve is a mechanical application of the rate rather than a fit against it.

If the prospect model has parameters estimated against rate-derived dollar values, then a later rate change means a refit rather than a re-point, and this pillar should have been built after document 03 instead of before it.

**So: estimate everything in win units or probability units, and convert to dollars only at the final step.** NHLe coefficients, transition probabilities, and shrinkage weights should all be recoverable without any dollar figure entering the estimation. If a design choice cannot be made without a dollar value in the loss function, stop and flag it, because it changes the sequencing of all three documents.

---

## Step 1. Verify the NHLe Slug Crosswalk

Generated but never verified. Everything downstream reads through it, so it goes first.

**Pre-flight question, still open.** Does the Bacon `get_player_information` endpoint expose full career league history, or only biographical data? The answer determines whether a cheap distinct-league check is feasible or whether verification has to be done the expensive way.

---

## Step 2. Build the Elite Prospects Production Pull

Phase 3b in the Work Queue. `ep_extract.py` exists as an extraction harness with caching, rate limiting, and SQLite storage.

**Single-provider discipline applies here in a form worth restating.** NHLe and all player-side value come from one provider precisely so that skater WAR, goaltender value, and junior or European production sit on internally consistent scales. Do not blend a second provider's junior scoring into this pull without an explicitly scoped and documented exception.

---

## Step 3. Apply Era-Varying NHLe Coefficients

`nhle_temporal.csv` holds 2,196 league-season rows with per-season NHLe factors.

**Use the season-specific coefficient, never a pooled one.** The file exists in temporal form for a reason. A pooled coefficient applied to a 2012 CHL season imports the scoring environment of the whole panel into a single observation.

**Look-ahead check.** The coefficients themselves are estimated on the full panel, so valuing a 2019 prospect uses NHLe factors partly estimated from post-2019 seasons. This is the same class of exposure as the aging-curve estimation window and the Bacon vintage issue, and it should be grouped with them in one limitations paragraph rather than defended separately. Consider whether a split-sample stability check is feasible here the way it was for the aging curve, since that is what turns the stable-parameter defence from asserted into tested.

---

## Step 4. Establish the Draft-Slot Prior

`draft_slot_baseline.csv` holds 225 rows of per-slot probabilities for reaching the league and for reaching star level.

**This is the prior, and it is already recovered.** A prospect with no professional record is valued at his slot's baseline. A prospect with a long professional record should be valued almost entirely on that record. The whole modelling problem is what happens in between, which is step 5.

**Consistency check owed.** The draft yield curve correlates at r = 0.893 against these same per-slot probabilities. That correlation was computed as an external validation of the curve. Using the probabilities directly in the prospect model means the two pillars now share an input, so state the shared dependency rather than presenting them as independent.

---

## Step 5. Design the Fading Prior

This is the item flagged as a major player-model consideration, and it belongs here rather than in document 03 because it is this pillar's core machinery rather than an adjustment to an existing one.

**The mechanism.** A weight moving from the draft-slot prior toward observed production as professional evidence accumulates. The project already has a working instance of exactly this pattern in the shrinkage applied to skater and goaltender WAR, where lambda controls how far a small sample is pulled back toward a league baseline. The prospect version is the same idea with a slot-specific rather than league-average target.

**What has to be decided.**

**The evidence unit.** Games, seasons, or NHLe-adjusted production volume. Games is the most defensible, since the concern is sample size rather than calendar time, and a player who spent three years injured has not generated three years of evidence.

**The fade rate.** Estimate it, do not assume it. The precedent here is strong: lambda 0.55 for skaters and 0.35 for goaltenders were both recovered by player-split cross-validation rather than picked, and lambda 0.55 was re-tested and re-confirmed after the curve rebuild rather than carried forward on trust. Match that standard.

**Whether the prior fades to zero.** A tenth-overall pick who has produced nothing across four professional seasons is not the same asset as an undrafted player with the same record. Whether draft position retains residual signal after production is observed is an empirical question and should be answered as one.

**The identification risk, stated plainly.** If the fade rate is estimated on outcomes that also feed the valuation, this becomes circular in the same way Value_t was before Phase 4b. Design the estimation so the parameter is recovered from prediction accuracy on held-out players, not from fit to valuations the model itself produces.

---

## Step 6. Convert to Surplus Dollars

Only here does a dollar figure enter, per the design constraint above.

**Mirror the draft curve's Rule A.** Value is projected production over the ELC window, priced at the market rate, less the slotted ELC cost, with post-ELC surplus zero by construction. Rule B exists as a robustness column on the draft side and the same pairing should carry over, so the two pillars remain comparable rather than each inventing its own convention.

**This is the step that gets rebuilt after document 03 changes the rate.** Keep it isolated in its own module so the rebuild is a re-point rather than a refit.

---

## Step 7. Absorb the Populations Currently Routed Here

Two groups are already pointed at this pillar and are being mispriced until it exists.

**Goaltender rookies.** D19 routed them here after the old league-average fallback wrongly topped the NPV list with unknown ELC goaltenders. They are unpriced by design pending this build.

**The 83 never-played goalie rows.** Currently priced at the goalie league average, with `contract_npv.py` recovering its league-average constant at import time from exactly those rows. The decision on how to handle them sits in document 00, section 3, because it can be taken independently, but the honest repricing lands here.

**One prospect already appears in the trade data with no contract.** PuckPedia identifier 17422 is Stanislav Demin, traded Vegas to Chicago on 2020-02-24 in the three-way Robin Lehner deal. He carries no name or Elite Prospects identifier in a contract-keyed export because he has no contract. Of 1,503 trade rows carrying a player identifier, exactly one has this problem, and it resolves itself when this pillar exists.

---

## Step 8. Re-Run the Power Analysis

The 2026-06-30 run found 946 trade groups, a cleanest category of 205 player-only trades, and only 14 fully priceable. That was taken against an almost-unbuilt model, so it measured the state of the build rather than the state of the data.

Re-running once picks and prospects are both priced is what makes the number mean anything. It is also a precondition for reading any null result as evidence of market efficiency, since failing to reject is weaker evidence than rejecting and the realized trade sample runs only 2018-19 to 2025-26.

---

## Identification Notes for This Pillar

**Circularity in the fade rate.** The specific risk called out in step 5. Recover the parameter from held-out prediction, not from fit to model-produced valuations.

**Look-ahead in the NHLe coefficients and the slot baselines.** Both are current-vintage estimates applied to historical decisions. Group with the aging-curve window and the Bacon vintage in one limitations paragraph.

**Selection.** Which prospects have professional records at all is not random. Players who never leave junior, or who go to Europe and stop being tracked, drop out of the evidence base in a way correlated with quality. This is the version of selection bias specific to this pillar and it has no analogue in the other two.

**Shared input with the draft pillar.** The slot baselines feed both. Say so once, explicitly, rather than letting the r = 0.893 validation and the prospect prior look independent when they are not.
