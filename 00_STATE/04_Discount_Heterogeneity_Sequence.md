# 04. Discount-Rate Heterogeneity, Sequenced

Generated 2026-09-14. Position in the overall order: **fourth structural document, downstream of 01 and 02.**

## What This Estimates

The model's discount rate is normative. Under D15 the rate carries no behavioural component, so GM impatience is a quantity the back-test measures rather than a parameter it assumes. This document sequences the measurement: whether clubs' revealed rate of trade between near-dated and far-dated assets differs by cap era, and whether it differs with a club's competitive position at the trade date.

The estimand is a revealed rate of substitution, not a preference parameter recovered from a structural model of club behaviour. Each recovered figure is a residual against the model's own pricing, so the interpretation is conditional on the value side being right. Step 1 and step 7 exist because that condition is not free.

## Why This Sits After the Other Three

**The identifying variation is in the pick trades.** A discount rate is identified from differences in the time profile of the two sides of a trade. Of 946 trade groups, 654 involve a draft pick, which is 69.1%. The cleanest current category, 205 player-only trades with no pick or prospect proxy, is the sample with the least time-profile spread and therefore the least useful for this question. The ordering here is the reverse of the ordering that governs the main efficiency test.

**It is gated on two pillars, not one.** Pricing the far-dated side needs document 01's traded-pick pricing, and pricing the other side of a mixed trade needs document 02's prospect layer. The repeat-sales design in 01 step 5 has the same dependency and for the same reason: 4 of the 163 candidate picks have all legs inside pure-pick trades, and 84 have at least one.

**It is a back-test extension, not a model change.** Nothing here touches the price equation, the aging curve, the hazard table, or the NPV engine. D15 stays as locked. The heterogeneity is measured in the back-test, and r stays normative inside the model.

## Entry Gate

Two items, both hard.

**The cap-growth assumption must be settled first.** See step 1. Until it is, a recovered discount rate is not separately identified from D11's 3% path, and any era result is uninterpretable.

**Picks and prospects must be priced.** Documents 01 and 02 in full. Attempting this on the 205 clean player-only trades would produce a number, and the number would be measuring almost nothing.

---

## Step 1. Settle g Before Estimating rho

This is the confound that decides whether anything downstream is readable, and it is new as of this session.

**The mechanism.** In `contract_npv.py` the discount rate and the cap-growth rate are one constant. `G = CAP_GROWTH` at line 197, and `CAP_GROWTH = 0.03` in `skater_forward_projection.py` at line 225. Because the value side is grown at g through `cap_path()` and then discounted at g, the two cancel on the value term and what survives is the cost term divided by (1+g)^k. That surviving term is the whole of the model's credit for a flat cap hit becoming cheaper in cap-share terms as the ceiling rises.

**Why that collides with this measurement.** The size of the credit is set by g. An eight-year contract at a flat cap hit equal to its t0 value carries +$6.16M of NPV at g=3%, +$9.71M at 5%, and +$13.77M at 7.6%, holding survival and aging aside. Realized ceiling growth from 2023-24 to 2026-27 was 7.6% per year. A g set below the realized path therefore understates the value of far-dated cap relief, and a club that trades for far-dated assets at a price the model calls expensive looks like a club with a low discount rate when the model may simply be underpricing what it bought. Under-crediting far-dated cap relief and clubs over-discounting the future produce the same residual, in the same direction, and the current specification cannot tell them apart.

**What closing this requires.** Either a deliberate revisit of D11 and D17, or an explicit sensitivity. The revisit is the larger job because g is also the discount rate, so changing it moves each NPV artifact. The sensitivity is the cheaper route and is sufficient for this document's purposes: re-run the back-test surplus differentials at g in {3%, 5%, 7.6%} and report the recovered rate at each. If the era ordering is stable across the sweep, the result survives the assumption. If it inverts, the result is an artifact of g and must be reported as one.

**A smaller inconsistency to resolve at the same time.** League minimums already use the CBA's published forward schedule while ceilings use flat 3%, so for t0 >= 2025 the two sides of the D10 floor are built on different conventions. This is already a standing flag. It bears on floor-bound fringe rows rather than on the term gradient, so it is a tidiness item here, not a blocker.

---

## Step 2. Decide What Is Being Estimated

**Levels are already known to be unavailable, and the reason is recorded.** The pure pick-for-pick attempt was investigated and shelved: 119 pure pick trades, 56 cross-year, 39 one-for-one, 35 of those same-round swaps carrying almost no information, leaving 17 bundle trades. A single fitted factor gives 0.486 on the round-mean slot convention or 0.510 on team-own-slot, but the per-trade implied values run 0.015 to 0.689 and order almost perfectly by the size of the future sweetener relative to the slot gap it buys. The driver is a minimum-denomination floor. Clubs cannot trade cash, so the smallest unit of consideration is a late pick priced near $0.81M, and any trade closing a gap smaller than that is a corner solution rather than an equilibrium price. Equality-based estimation applied to a corner is misspecified.

**Differences survive that finding, and this is the argument for the whole document.** A corner solution still yields an inequality restriction, which carries information. If the censoring is common across eras and across team states, it differences out of a comparison even where it destroys a level. The forward path already recorded with the shelved item is the right one: estimate bounds rather than a point, since each corner trade yields an inequality. Interval-censored estimation on grouped data is the tool, and the grouping is by era and by team state.

**The evidence that the bounds will be informative rather than vacuous.** Sweetener size scales with the gap at Spearman 0.735. Clubs are pricing directionally and are floored, not pricing at random. A floored but monotone response is exactly the case where bounds are narrow enough to compare.

**What to state in the write-up.** The deliverable is a ranking and a set of bounds, not a point estimate of any club's discount rate. Write the claim that way from the start, because a bound reported once as a point will be quoted as a point.

---

## Step 3. Fix the Bargaining Restriction Before Any Estimation

One trade is one price and two discount rates. The observed exchange reflects both parties' preferences together with whatever bargaining power each held, so the two rates are not separately identified from a single transaction without a restriction. This is the step most likely to be skipped and the one a supervisor will find first.

**Option A, the directional restriction.** The club acquiring the far-dated asset is revealed to hold the lower discount rate. This yields an ordering rather than a level, and it aggregates across repeated appearances into a club's revealed position relative to the league. It is the weaker assumption and the one I would default to.

**Option B, the symmetric-split restriction.** Assume the price sits at the midpoint of the two reservation values, as under Nash bargaining with equal weights. The differential between the two clubs' rates is then identified from the measured NPV gap, though the level still is not. It buys a differential at the cost of an assumption about surplus division that the data cannot check.

**Pick one, in writing, before the estimation runs.** Both are defensible and they answer slightly different questions. Choosing after seeing the results is the failure mode the Stage 2 specification document existed to prevent, and the same discipline applies here.

---

## Step 4. Build the Team-State Covariate Ex Ante

**It is constructible from data already held.** `nhl_gamelog_scraper.py` builds a `games` table carrying `game_date`, `away_team`, and `home_team` with scores, across 11,870 games from 2017-18 to 2025-26. Standings at an arbitrary date reconstruct from that directly, and the coverage window contains the full trade window.

**The variable must be dated at the trade, not at the end of the season.** Points percentage and games remaining as of the trade date are permissible. Final standing position, playoff qualification, and playoff result are not: each is realized after the decision and using any of them is the look-ahead violation the project's trailing-season rule exists to reject. This is the one place in this design where the tempting variable is the forbidden one, because "rebuilding" is most cleanly labelled after the fact.

**A deadline indicator is worth carrying separately.** Trade-deadline trades and draft-week trades are different decisions taken under different information, and pooling them puts two populations into one coefficient. The date is already on each trade row.

---

## Step 5. The Repeat-Sales Leg, Split by Era

This is the cleanest identification available for this question, because pricing the same pick at two horizons differences the asset's own value out of the comparison. It does not require the value model to be right, only stable.

**The sample.** 811 distinct picks appear in the PuckPedia trade file, 241 traded more than once, and 163 traded at two or more different horizons: 113 one year apart, 42 two, 7 three, and 1 four. Split across the three cap regimes that is roughly 54 per era, which is thin for a point estimate and workable for a bound.

**The dependency.** 4 of the 163 have all legs inside pure-pick trades and 84 have at least one, so the rest need the other side priced. That is the same dependency 01 step 5 carries, and the two legs should be built as one job rather than twice.

**The caveat to carry.** PuckPedia's `overall_position` is back-filled for future picks, so a 2020 third traded in June 2019 carries its realized slot. It must never be read for an ex-ante price, and a repeat-sales design is the place that mistake would be invisible, because both observations would carry the same back-filled number and the ratio would look clean.

---

## Step 6. The Full-Population Leg, and What It Cannot Support

**Specification.** Model the discount rate as a function of state rather than as a set of club parameters:

    rho(i,t) = rho_0 + gamma * (points percentage at trade date) + delta * (games remaining) + era effects

Three to five parameters. Add the deadline indicator from step 4 and the monopsony flag already carried on the trade rows, since an NTC or NMC forced move is a separate category under the standing flag and must not enter as ordinary revealed preference.

**Club-specific rates are out of scope, and this is a decision rather than an omission.** The right design for club effects is a two-sided fixed-effects decomposition over the transaction network, in the manner of the worker-firm wage literature. The NHL trade network is densely connected, so the connected set is probably the full league and the effects would be estimable in principle. They are not estimable in practice here. All 946 groups give roughly 59 trade-sides per club, the clean 205 give roughly 13, and the dependent variable is itself a modelled quantity with substantial error. At that ratio the estimated club effects would be dominated by limited-mobility bias. If it is attempted later it needs shrinkage or a leave-out correction and it is labelled exploratory. Do not put club-level discount rates in the paper off this sample.

---

## Step 7. Validate the Long-Horizon Projection Before Reading Any Result

The template is Stage 2, and it should be followed closely because the failure mode is the same one.

**The problem.** The regressor of interest is horizon. The model's own projection error also grows with horizon, and beyond k=3 the spread is a placeholder rather than an estimate: `_proj_sd_war` holds the k=3 figure flat, covering about 13% of projected seasons, all on long contracts. Error whose variance moves with the regressor gives heteroskedasticity at a minimum. If the long-horizon projection is biased rather than only noisy, the bias is not separable from a discount rate, because "clubs discount the future" and "the model is wrong about the future" leave the same residual.

**Why this is a live risk rather than a hypothetical.** The 2026-09-13b work found the best players over-projected in season totals, by +$0.98M per season at 1+ WAR rising to +$1.49M for sustained stars, and traced most of it to the unshrunk starting level rather than to the curve. That is a horizon-correlated bias in the value side, already measured, in the population that long contracts are drawn from.

**What to run.** Realized Game Value against projected value at k=4 through k=8, on the same design logic as `term_premium_test.py`. Game Value carries no Bacon inputs, so the outcome side is independent of the vendor that produced the projection being tested. Report the bias by horizon before any discount-rate figure is quoted, and if it is material, either correct it or state the recovered rate as an upper or lower bound with the direction named.

---

## Step 8. Power and the Reading Rule, Pre-Registered

**Fold this into the power-analysis re-run rather than bolting it on.** The re-run is already owed after Phase 3 and is currently specified against the headline efficiency null. It needs a second arm: the minimum detectable difference in the recovered rate by era and by team state, given the dispersion of the measured surplus differential. Without that arm a null here reads as homogeneous preferences when it may be low power, which is the same error the 2026-06-30 run was criticised for.

**Write the reading rule before the estimation.** What counts as a difference, how many era and state contrasts are being tested, and how the multiplicity is handled. The Stage 2 specification is the precedent and it worked: the reading rule was fixed and signed before the script existed, which is why its null is quotable.

---

## What This Document Does Not Do

It does not reopen D15. The model's rate stays normative and fundamentals-only; the heterogeneity is measured against it, never substituted into it. Calibrating r to observed behaviour would assume the conclusion, which is the reason D15 exists.

It does not deliver club-level discount rates. See step 6.

It does not resolve whether a measured difference is mispricing or efficient gains from trade. Two clubs with different time preferences trading to mutual advantage is not an error, and the model scores it against one league-average yardstick regardless. The standing flag on league-average versus club-specific value already records this as an open back-test design problem, and this document narrows it rather than closing it: a recovered difference in revealed rates is evidence about preferences, and reading it as mispricing needs a separate argument.
