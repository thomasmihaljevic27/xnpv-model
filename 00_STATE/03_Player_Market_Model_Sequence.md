# 03. Player and Market Model Changes, Sequenced

Generated 2026-07-29. Position in the overall order: **third and last of the three structural documents, immediately before the back-test engine.**

## Why This Pillar Goes Last

**Every change in this document propagates to the other two pillars.** All three asset classes are denominated in the currency set by the skater price equation. Two of the five changes below refit that equation, and one changes the anchor the equation is fit on. Each such change forces a rebuild of the draft yield curve, the prospect pricing layer, and every NPV artifact. Doing them piecemeal means one rebuild of everything per change. Doing them in a single batch after the other two pillars exist means exactly one rebuild each.

**The back-test is the one thing that must not be re-run repeatedly.** That is where the findings live, and where pre-registration matters to Karl. The efficient-market null has already been stated in advance for exactly this reason. Locking the currency immediately before the back-test opens is the clean cut.

**The honest counter-argument.** Building the prospect pillar against a rate that will change is a real cost. The mitigation is the design constraint at the top of document 02: apply the rate, do not fit against it. If that constraint cannot be met, this document should move ahead of 02 instead.

---

## Ordering Within This Document

The five items split on one axis: whether they touch the rate.

**Downstream-only** items change terminal value and NPV but leave the price equation alone. They force no curve rebuild and can be pulled forward at any time, including now. Items 1, 2, and 3.

**Rate-touching** items refit the price equation or the anchor it is fit on. These are the batch. Items 4, 5, and 6.

One addition since this document was first written: **the skater cascade acquires a third rung when the window changes**, and that rewrite is precisely where the goalie stale-anchor bug got introduced. The replacement ladder needs a branch for every non-empty subset of the three seasons, not a sequence that short-circuits when t−1 is missing. Item 4 carries that warning.

Within the rate-touching group the order is forced: the anchor change must precede the price-equation change, or the star correction gets fitted on anchors that then move underneath it.

---

## Item 1. Goaltender Control Years

Downstream-only. **This is the cheapest item in the document and I recommend pulling it forward immediately, ahead of documents 01 and 02.**

**The gap.** Goaltender control years are weighted by nothing. The goalie branch of `contract_npv.py` writes survival 1.0 on every terminal row, and its own comment records the absence of the tender gate as a known gap. A goaltender with three control years is currently valued as though he is certain to still be there.

**Why it should not wait.** This is an unimplemented feature that the code itself documents as unimplemented, not a modelling refinement under debate. It is inflating every goaltender with control years in the current NPV spine, and that spine is what the other two pillars will price mixed trades against.

**The numbers, already tested 2026-07-28.** A single pooled rate rather than buckets, since the goalie cells are too thin to support four, with fringe at n=5 and regular at n=8. Pooled at a one-game bar, P(tendered) is 0.909 and the corrected weight is 0.788 on n=99. Applied and compounded that gives 0.788, 0.621, and 0.489 across three years, against 1.0, 1.0, and 1.0 today.

**Status.** A new decision rather than a reopen, because the gap is already documented as a gap.

**Two sub-decisions are already settled and do not need revisiting.** First, a pooled goalie rate rather than four talent buckets, since the goalie cells cannot support buckets (fringe n=5, regular n=8) while the pooled n=99 supports one number. Second, the one-game materialisation bar rather than the 20-game bar the exit hazard uses. Both were decided 2026-07-28 and are recorded in the Decision Log. Only implementation remains.

---

## Item 2. Skater Control Years

Downstream-only. A D14(c) reopen.

**The gap.** The model asks whether a club will tender a restricted free agent but never whether he then plays. Those are different events. The correct weight on a control year is P(tendered) times P(plays given tendered), and only the first term is in. Conditional on being tendered, a player still exits at 13.1% a year, and none of it is counted.

**The evidence that the two events are distinct.** Of players a club walked away from, 41.9% of skaters and 42.9% of goaltenders also left the league. The tender gate therefore measures club retention rather than league exit, and the two only partly overlap. Skaters and goaltenders are statistically indistinguishable on this, which removes any basis for treating the positions differently and is the reason items 1 and 2 belong together.

**Corrected weights at a one-game bar.** Below-replacement 0.694 to 0.619, fringe 0.795 to 0.753, regular 0.888 to 0.877, star unchanged. Compounded over three control years for a below-replacement player that is 0.334 today against 0.237 corrected, a factor of 1.41.

**Why the one-game bar and not a higher one.** The gate asks whether the control year materialised. A player who survives but plays five games is overvalued through the projection rather than through the gate, so charging him again at the gate double-counts. At a 20-game bar the same bottom-bucket figure reads 29.5% rather than 12.2%, meaning more than half the naive correction at that threshold is an artifact of where the line was drawn.

**Direction note for the robustness section.** Both control-year items move values down. That matters, because the one-directional-corrections flag records that six of ten Stage 1 fixes moved values up and none moved them down. The 2026-07-28 run was the first change set to move values down, and these two continue that. This is direct evidence the corrections are not uniformly signed by construction.

---

## Item 3. Skater Stale-Anchor Materialisation Gate

Downstream-only. Found and measured 2026-07-29 while checking whether the goalie cascade defect had a skater equivalent. **The cascade defect does not exist on the skater side**, but a related valuation gap does.

**The population.** 457 skater contract-season rows from 2018 carry a `t2_only` anchor, meaning no t−1 season but a usable t−2. The cascade handles them correctly, so they are priced rather than misclassified. What is missing is any accounting for whether the season happens.

**The size.** They materialise at **61.7%** against 96.1% for rows with both trailing seasons. So 38.3% are valued for a season that never occurs, and at a $1.265M intercept that is roughly **$220M of phantom value** across the panel.

**The instrument is a gate, not a discount, and this is the part that matters.** The anchor in use is 0.069 while these players produce 0.140 when they do play. The trailing figure is therefore if anything slightly pessimistic, and a staleness discount would correct in the wrong direction. This is the **mirror image of the goalie case**, where the 2.189 default sat far above that population's true 0.650, which is what made a discount right there. Do not carry the goalie reasoning across by analogy.

**It must be applied per season, not seeded into `S`.** The goalie fix seeds the gate, making it permanent across the contract, justified because only 9.3% of non-materialising goaltenders return at k=1. For skaters that figure is **26.0%**, so the state is not absorbing and seeding would understate value badly.

**Why it is downstream-only.** 287 of the 2,591 rate-fitting rows carry a `t2_only` anchor, which is 11%, so touching the *anchor* would refit the market rate and cascade to every pillar. A gate leaves `trailing_war` and `cap_pct` both untouched, so the rate does not move.

**Why it is here and not shipped.** It is the third of three changes governing how survival weight compounds. Items 1 and 2 are the others. Shipping them separately in different styles is how two competing conventions end up in one file, which is exactly what the goalie work spent a session untangling.

---

## Item 4. Trailing Window, With Joint Lambda Refit

Rate-touching. **First of the batch, because it changes the anchor everything else is fit on.**

**The test is already run and it is decisive.** `trailing_window_test.py`, 2026-07-28. 50/30/20 on seasons t-1, t-2, and t-3 beat the current 60/40 blend in 1,000 of 1,000 player-clustered bootstrap resamples, with a 95% interval on the mean-absolute-error gain of 0.021 to 0.030 WAR, excluding zero. It holds at games-played thresholds of 10 and 20, on season totals and on a per-82 basis. Every three-season scheme beat every two-season scheme. Every scheme was scored on identical rows, because a three-season blend requires three trailing seasons and the players who have them are disproportionately established survivors, so scoring a deep scheme on deep rows compares two populations rather than two schemes. The continuity guard passed, so the test reproduced the locked D20 rate before comparing anything.

**Two caveats that must survive into the adoption decision.**

**The pricing-side leg is confounded and must not be leaned on.** A three-season average is a less noisy regressor, and classical measurement error biases a slope toward zero, so smoothing the regressor mechanically raises both beta and R-squared. Beta moving from 1.78M to 1.97M per win is the signature of attenuation correction rather than evidence that the market was looking at three seasons. The prediction leg is the clean result and the pricing leg is corroboration at best. Karl will find this if it is not stated first.

**The test's coverage loss is an artifact of the test.** The strict no-fallback rule drops 296 contracts, 17.2% of currently-anchored rows, disproportionately young players. That rule exists so schemes are measured rather than cascades. Production would use a fallback ladder in the goaltender style, so real coverage loss on adoption is close to zero.

**What adoption requires, and why it is expensive.**

A fallback ladder, specified in the goaltender style.

**A joint re-cross-validation of the aging-curve lambda.** Window length and mean reversion are partial substitutes, since both smooth. Lambda 0.55 was cross-validated against the two-season window. Adopting a three-season window without refitting lambda over-smooths the projection. This is not optional and it is the item most likely to be forgotten.

A full inventory of the downstream constants to be refit, including the hardcoded rate constants and the duplicated trailing-window copy inside `draft_yield_curve.py`. Re-read the duplicated-loader flag in document 00 section 6 before starting: `skater_value_engine.py` and `skater_forward_projection.py` each hold their own copy of the season-WAR loader, and fixing one has no downstream effect.

---

## Item 5. Star and Restricted-Free-Agent Price Suppression

Rate-touching. **Second of the batch, because it must be fitted on the anchors item 3 produces.**

**Origin.** Reading a modelled valuation above the league maximum and asking whether the model could produce one. Under the Stage 3 rate exactly one row in 6,892 crosses 20% of the cap: McDavid 2023-24 at 9.31 trailing WAR, 21.1%, 17.62M against a 16.70M maximum. The thresholds are 8.80 WAR for a forward and 7.75 for a defenceman.

**A dead end to record so it is not re-attempted.** The 20% maximum has never bound in the contract sample. The highest skater deal since 2018 is 15.7% of the cap and none exceed 17%. A right-censored correction at the maximum is unidentified.

**The scarcity fact.** Of skater contracts starting 2018 to 2025 with a trailing anchor of 3.5 WAR or more, 94% were signed with the player's own club and none came through a trade and re-sign. At 4.0 WAR or more it is 96% own club. The only two open-market star signings in the window are Gaudreau in 2022 and Panarin in 2019. Both priced above the own-club star mean, 11.8% and 14.3% of cap against 10.6% at an identical mean anchor, but n = 2 and no estimate can rest on it.

**The identifiable version.** Left-censored maximum likelihood on 2,468 contracts, censoring at the CBA minimum as a cap share, with position slope, own-club route, and a star by RFA interaction. The baseline specification reproduces the locked Stage 3 rate closely, at a 1.21M intercept and 2.01M per win against locked figures of 1.265M and 2.028M. In the full specification the RFA main effect is zero at z = 0.5, the star main effect is zero at z = 0.3, and only the interaction fires, at minus 0.01789 cap share, z = minus 4.4, or minus 1.71M at the 2025-26 ceiling. A 4.5 WAR forward re-signing with his own club prices at 11.07M as a UFA against 9.43M as an RFA, roughly 14%, or about 13M of cap across an eight-year term. A star UFA sits on the same straight line as everyone else, so the entire top-end distortion is star RFAs.

**A second, separate effect from the same fit.** Own-club re-signing carries a level premium of 0.00603 cap share, z = 5.1, or 0.58M, with no slope component. Because it is a level shift it is 19% on a 3M player and 6% on a 10M star, so it lands hardest in the middle of the market. This is a candidate mechanism for clubs getting into cap trouble on mid-tier players, and it is a distinct finding rather than the same one.

**The interpretive split that must survive into any adoption decision.** The intuition that suppressed star pay creates surplus divides into two claims that are not equally testable. That star RFAs are underpaid relative to star UFAs is a within-market differential, so the pooled line sits between the two and star RFA contracts already show positive surplus under the current specification. That claim is measurable from inside the data. That stars league-wide are underpaid relative to true value is a level claim, and the value side and the cost side move together, since value is a market prediction and a market-wide depression depresses the prediction too. That claim is not measurable from inside the market. Do not conflate them.

**What closing this requires, in order.** A star-threshold sensitivity sweep from 3.0 to 4.5, since the 3.5 cutoff is arbitrary and unswept. A refit on the locked 2,349 sample with the prorated anchors, which by then are item 3's anchors. A decision on whether the interaction enters the production rate or is documented as a limitation. If it enters, the full downstream rebuild.

**Caveats carried from the exploratory fit.** 2,468 contracts rather than the locked 2,349, unprorated anchors, 34 stars in total. Signing team is the club that signed the paper, so a sign and trade counts as an own-club re-sign, with Marner 2025 counting as Toronto and Rantanen 2025 as Dallas. Arizona and Utah are collapsed to one code. Selection is the obvious objection: stars who re-sign early may differ systematically from those who do not, and nothing here addresses that.

---

## Item 6. Long-Term Deals Crossing UFA Eligibility

Rate-touching in effect, since it changes terminal value for exactly the population item 4 concerns. **Take it with item 4, not separately.**

**The gap.** The terminal-value model assumes UFA years revert to market. Deals that purchase UFA years need separate handling, and none exists. Open since the start of the project and never actioned.

**Why it belongs with item 4.** These are the same phenomenon seen from opposite ends. A star restricted free agent signing a long extension is buying UFA years at RFA-discounted prices. That is very likely the mechanism behind the young-star extension negative NPVs, which five independent mechanical corrections failed to explain away under held-out validation. Item 4 measures the discount at the signing moment. Item 5 governs what the purchased years are worth. Resolving one without the other leaves the finding half-explained.

**Related open thread.** The ELC slide rule currently sits in the Optional tier, on the grounds that extra team control is not captured cleanly by the three-plus-four valuation window. It is the same class of question about how control years are counted and should be looked at in this pass rather than left in Optional.

---

## Closing Sequence, After All Five Items

**Rebuild everything denominated in the rate.** The draft yield curve, the prospect pricing layer, `contract_npv_spine.csv`, `contract_npv_panel.csv`, and any Phase 4b circularity output keyed on contract-level NPV. Audit what consumes each artifact rather than assuming the list is short.

**Re-run the local verification discipline in full.** Each change built, run on my machine, and reconciled line by line against an independent run before acceptance. The Stage 2-5 departure from this is already a Standing Flag and should not be repeated.

**Re-run the power analysis.** Prerequisite to reading any null as evidence of efficiency.

**Then lock the currency and open the back-test.**

---

## Identification Notes for This Pillar

**One-directional corrections.** Karl's likely first objection to the Stage 1 set. Items 1 and 2 both move values down, which strengthens the answer. Present the batch as a set with the net effect stated once in the robustness section, rather than as five unrelated fixes scattered through the methodology.

**Selection in item 4.** Stars who re-sign early differ from those who do not, and the exploratory fit does not address it. This is the identification hole in the headline finding of this document.

**Attenuation in item 3.** The pricing-side R-squared improvement is a mechanical consequence of smoothing the regressor. State it before the result, not after.

**Circularity, closed but adjacent.** Value_t circularity was fully resolved at Phase 4b with three validators in a 0.56 to 0.61 band. Any design in this document that would re-entangle the input rate and the outcome measure reopens it. Item 4's efficient-price extension, if pursued, is the one most likely to touch this, since a normative benchmark built from the same market data is circular by construction. That extension is a separate contribution and is not part of this batch.
