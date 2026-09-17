# What a club still owns when the contract ends

Run 2026-09-17 in `50_REBUILD/` (v2.1, after two rounds of independent review). The plan's Phase 5 item on the
restricted-free-agency walk-away and the control years. Development start years only. **Nothing
adopted, and no production file changed.**

The first version of this report (v1.0) put the value of deciding as you go at $0.27M a contract.
**That figure is withdrawn.** It compared two rules that differed in three things at once, and the
comparison that isolates information gives **$0.066M**. The corrections are listed at the end; the
body below is the repaired work.

**Two limitations stay attached to this result.** The stopping policy is an approximation to
optimal stopping and not the option value, and the eligibility comparison is a sensitivity and not
a bound on bias. Both are set out below where they arise. This is a prototype, not a solved
component.

## The asset the simulator was leaving out

A contract that expires into unrestricted free agency ends the relationship: the player walks and
the club keeps nothing. A contract that expires with the player still **restricted** does not. The
club holds his rights until he becomes unrestricted, and can keep him by tabling a **qualifying
offer** — a one-year offer the CBA sizes off his last salary, which for a good young player sits
far below what he is worth.

**398 of the 1,217 development contracts own at least one control year** — 148 own one, 153 two, 79
three, 16 four, 2 five. They are short deals: 219 one-year contracts, 138 two-year, 39 three-year.

### Ownership is eligibility, and nothing else

A club holds the rights from the season after the contract until the season before the player is
unrestricted. That is all this reads.

It is not what the export records as the contract's expiry. That column is an **outcome**: of the
398, it eventually recorded 252 as restricted expiries, **101 as "UFA no QO"** — a club that
declined to qualify the player — and 45 as plain unrestricted. Declining to qualify happens years
after the signing being valued, and it is *the very decision the stopping rule exists to make*.
Reading it back into the setup tells the model the answer. `control_span` no longer takes the label
as an argument at all, and the suite asserts that it cannot.

**Where eligibility comes from.** A player is unrestricted at 27 on the age rule alone, which his
birthdate fixes and a club knows the day it signs him. Seven accrued seasons can get him there
sooner, and a season accrues by being played.

| | contracts | |
|---|---:|---|
| the export's eligibility year matches the age rule exactly | 1,087 | 89.3% |
| earlier than the age rule (the accrued-seasons route) | 130 | |
| later than the age rule | 0 | |

Never later, which is what the rule says: eligibility is the earlier of the two routes. The 130 are
the exposure — for a player short of seven accrued seasons at the signing, that route runs partly
through seasons not yet played. **So the whole sample is priced again on the age rule alone**, which
needs nothing but a birthdate:

| | eligibility | age rule alone |
|---|---:|---:|
| contracts owning control years | 398 | 405 |
| control years each | 1.92 | 2.03 |
| deciding as you go, $M | 0.703 | 0.717 |

On the contracts in both, the difference is **+$0.026M a contract**, about 4% of the answer. The
356 contracts whose control window is the same under both rules come back **identical to the cent**,
because the draws are seeded per contract rather than taken from one stream in loop order — before
that fix they were being re-rolled and the wobble was reported as part of the difference.

**This is a sensitivity, not a bound on bias.** It says what changes when one eligibility
assumption is swapped for another. It does not establish that using the export's eligibility year
costs less than 4% against the truth, which would be each player's accrued seasons as they stood on
his signing date — something this tree does not hold. The age rule also never brings eligibility
forward, so it is not a neutral alternative.

## It is an option, and the walk-away is final

Control is a right, not an obligation, and once the club declines the remaining years are gone —
there is no skipping a year and re-qualifying later. So the value is the value of a **stopping
rule**.

And because the walk-away is final, "worth keeping" is not "does next season pay". A year that
loses money is worth taking when the years behind it more than pay for it: on a path worth +5, −1,
+10, a club that stops at the first loss leaves 9 behind. That is true of the ceiling **and of the
policy**. The first version fixed only the ceiling.

## Six rules, each differing from its neighbour in one thing

Priced on the same draws. Dollars a contract, discounted to the signing, 2,000 paths.

| control yrs | n | take every year | production's rule | decide in advance | myopic, informed | decide as you go | knew the path |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 148 | −0.221 | 0.143 | 0.224 | 0.267 | **0.267** | 0.410 |
| 2 | 153 | 0.235 | 0.424 | 0.615 | 0.709 | **0.709** | 0.967 |
| 3 | 79 | 1.037 | 0.933 | 1.249 | 1.303 | **1.305** | 1.485 |
| 4 | 16 | 1.472 | 0.949 | 1.498 | 1.561 | **1.565** | 1.787 |
| all | 398 | 0.281 | 0.442 | 0.637 | 0.702 | **0.703** | 0.901 |

- **take every year** — the obligation, not the right.
- **production's rule** — prices the mean projection and stops at the first loss. Production's D13.
- **decide in advance** — expected price, no path seen, later years counted.
- **myopic, informed** — the path's *observed* history, stop at the first expected loss.
- **decide as you go** — the same history, with the later years' *expected* payoffs counted.
- **knew the path** — the ceiling: best stopping point in hindsight.

### Two differences that mean something

**The value of information is $0.066M a contract** — deciding as you go ($0.703M) against a
baseline that prices the same way and uses the same policy ($0.637M), so that only the conditioning
differs. That is a quarter of the way from deciding in advance to knowing the whole path ($0.901M).

### The policy is an approximation, and the second difference is narrower than it looks

Counting the later years' expected payoffs is worth **+$0.001M** against the myopic version — it
changes 142 of the 398 contracts, by $2,722 where it does.

**That is the gap between two specified policies. It is not the value of the continuation option,
and a small number there is no evidence the option is small.** Neither rule values the decision the
club will get to make next year. A club that keeps a player through a disappointing season partly
to *see another season of him* and then decide is doing something neither rule can express, because
both price the future as though the club had to commit to the whole run now. A feasible policy
using only information available at each decision can therefore beat the one implemented here,
which the review demonstrated on this module's own setup.

Pricing that properly means backward induction over the conditional law with the later decisions
valued as decisions. It is not built. **So the informed rule is a declared approximation to optimal
stopping, and the figures here are a lower bound on what an optimally-stopping club would get.**

### And one that does not

**Deciding as you go against production's rule is +$0.261M** — the figure the first version
reported as the value of deciding as you go. It is a mixture of three changes: pricing the
mean versus averaging the price, deciding in advance versus on the path, and stopping at the first
loss versus counting the later years. It is not an option premium and should not be quoted as one.

### What the right is worth against the obligation

The largest single number here is not about information at all. A club **forced** to take every
control year loses money on the deals with one of them (−$0.221M); with the right to decline the
same seasons are worth +$0.267M. **Being able to walk away is worth $0.422M a contract** across the
398 — six times the value of the information the club brings to the decision, and the one figure
here that does not rest on the stopping policy being the right one, since an approximate policy can
only understate it.

Deciding on an expectation is not the same as not losing: the declared rule ends under water on 1
of the 398 contracts. That is what tendering on an expectation means, not a defect.

The club tables an offer in **1.25 of its 1.92 control years** on average.

## What it does to the contract

Reported beside the contract's surplus, not folded into it. Every comparison already run in this
tree values a contract to its expiry, and moving the headline would silently re-date all of them.

| term | n | surplus $M | control years $M | together |
|---|---:|---:|---:|---:|
| 1 yr | 219 | +0.015 | +0.850 | +0.865 |
| 2 yr | 138 | +0.175 | +0.599 | +0.774 |
| 3 yr | 39 | +0.543 | +0.285 | +0.828 |

On a one-year deal the right to keep the player afterwards ($0.850M) dwarfs the surplus on the
season the club just bought ($0.015M). The ratio is not worth quoting — the denominator is a mean
near zero — but the ordering is the point: for these contracts the asset is mostly the right.

## Against production's own terminal value

Production prices the same right by truncating one projected path, which is the `production_point`
rule here. The two are **not on the same information date** — production discounts to 1 July of the
first contract season, this to the signing — so levels are not expected to agree.

| | |
|---|---:|
| contracts in both | 372 of 398 |
| production's terminal value, mean | $0.580M |
| production's own rule, rebuilt here | $0.423M |
| deciding in advance, priced alike | $0.620M |
| deciding as it goes | $0.690M |
| rank correlation, production vs its own rule | 0.234 |
| rank correlation, production vs deciding as you go | 0.382 |

**Production prices 187 of them at zero**, where this tree finds a right worth $0.528M on average.
Broken down by the label production reads: **97 are "UFA no QO"**, 33 plain "UFA", and 57 restricted
expiries. Production's own code sets terminal value to zero for the first two outright — the
docstring says so, "team already declined to qualify" — so **130 of the 187 are the same future
decision this version stopped reading**. The remaining 57 are the D13 truncation, and this tree's
rebuild of production's rule gives zero on 147 of the 187, which is those 57 plus the cases where
both rules truncate anyway.

That is a finding about production's terminal value and not only about this module: **production's
control-year value uses the outcome of the decision it is pricing.** The rank correlations falling
from the first version (0.547 → 0.234 on the matched rule) is the same thing seen from the other
side — the two now disagree about who owns a right at all. The docstring is production's own: it sets
terminal value to zero for both "UFA" and "UFA no QO" expiries, and 97 + 33 = 130 of the 187 carry
one of those two labels.

## The weak point: the offer's base salary

The CBA formula runs off the final year's **base salary**. This tree's source carries one row per
contract with an average annual value, so the average is used. Measured against the per-season
salaries production joins from the clause feed, on the 339 of these 398 contracts the feed covers:
221 agree within 1%, **110 have a final salary above the average**, 8 below; median ratio 1.000,
90th percentile 1.160.

A **back**-loaded deal pays most at the end, so its final salary sits above its average: the
average understates the offer and makes the control year look too valuable. A front-loaded deal
runs the other way. (An earlier version of this section had those two reversed.) The
120%-of-cap-hit clause caps the offer on exactly the back-loaded deals where the gap runs the first
way, so substituting the average switches it off where it was meant to bind.

## What is checked

- **The expiry label cannot reach the span.** Asserted on the function's signature, so it cannot
  come back quietly.
- **The offer is dated twice over** — the league minimum it floors at, and the bands themselves. A
  2021 signing pricing a 2026 control year sees $1.00M on a $1M salary; a 2025 signing sees $1.10M.
- The bands are reimplemented in this tree and **checked against production's implementation on
  4,000 random cases: largest difference $0.00.**
- **Ceiling and policy both sit through a bad year to reach a good one**, on the worked case and on
  500 random paths, where nothing beats the ceiling.
- **The club sees what it was shown and only that.** Every season from the decision onward is
  redrawn: the expectation comes back bit for bit. The misses of seasons he did not play are
  redrawn: unmoved. The seasons he *did* play are redrawn: it moves at every horizon.

Each was verified by reintroducing the defect it guards — the label back in the span, conditioning
on unseen misses, undated bands, and a myopic policy. All four breaks are caught.

Suite: **28 passed, 0 skipped, 0 failed.**

## Open limitations to carry into any adoption

Three, and none of them is fixed by rerunning this:

1. **The stopping policy is an approximation to optimal stopping**, so every informed figure is a
   lower bound on what an optimally-stopping club would get. The $0.001M continuation difference
   bounds two specified policies, not the option.
2. **Eligibility is dated only as far as the export allows.** The age-rule comparison is a
   sensitivity, not a bound on bias; the accrued-seasons route as it stood at each signing is not
   held in this tree.
3. **The offer's base salary is the contract average**, which understates the offer on back-loaded
   deals and switches off the 120%-of-cap-hit clause where it was meant to bind.

## What this does not establish

- **Nothing here is scored against an outcome.** Whether clubs exercise the right this well is a
  back-test question.
- **The informed rule is a model of a club, not a measurement of one.** It brackets the answer
  between deciding in advance and knowing the future; where real clubs sit is not tested. The
  realised expiry label is now available for exactly that test, having been removed from the setup.
- **The forecast is extrapolated further here than anywhere else in the tree**, because a control
  year sits past the contract's own term.
- **Goalies are not here.** The goalie control-year gate is still open.
- The $0.066M value of information is a sample mean over 398 contracts, and the rules it compares
  share draws, so it is a paired difference — but it is still one sample and one dependence model.

## What the first version got wrong

Four things, all found by review:

1. **It used a future decision to remove the right.** 101 contracts marked "UFA no QO" were given no
   control years because the club had declined to qualify the player — years after the signing being
   valued. 45 more were dropped on a plain "UFA" label despite listing a later eligibility year. The
   sample was 252 contracts; on eligibility it is 398.
2. **The club saw shocks from seasons the player missed.** Conditioning ran over every earlier
   season's miss, including ones nobody observed. Changing only those hidden shocks moved the first
   control year's decision on 188 of 252 contracts and flipped 26,519 path decisions. The
   future-scramble test could not catch it, because those seasons are in the past.
3. **A historical valuation used future qualifying-offer bands.** The floor was dated; the regime
   switch at 2026 was not. Contract 6876, signed in 2021, was handed a $1.10M offer in 2026 where
   the rules it could see gave $1.00M.
4. **The headline compared three changes at once.** The informed rule stopped at the first expected
   loss, ignoring the later years it would also lose; and it averaged prices across uncertain
   production while the rule it was compared against priced the mean. With the floor bending the
   price, those two calculations differ even when no information has arrived.

The first three are corrected in the model. The fourth is corrected by adding the matched baseline,
which is what moves the headline from $0.266M to $0.066M.

## Files

    50_REBUILD/code/control_years.py        the offer, the span, the six rules
    50_REBUILD/code/run_control_years.py    the run, the audit, the checks

Writes `control_years.csv`: one row per contract with control years, carrying the number of them,
the offer schedule, the point and unconditional first-year surpluses, the mean under each rule, the
spread under the informed one, and how many years the club tables an offer in. Outputs ignored under
`50_REBUILD/output/`.
