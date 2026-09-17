# What a club still owns when the contract ends

Run 2026-09-17 in `50_REBUILD/`. The plan's Phase 5 item on the restricted-free-agency walk-away
and the control years. Development start years only. **Nothing adopted, and no production file
changed.**

## The asset the simulator was leaving out

A contract that expires into unrestricted free agency ends the relationship: the player walks and
the club keeps nothing. A contract that expires with the player still **restricted** does not. The
club holds his rights for every season until he becomes unrestricted, and it can keep him by
tabling a **qualifying offer** — a one-year offer whose size the CBA fixes off his last salary, and
which for a good young player sits far below what he is worth.

Those seasons are an asset, and the path simulator has been valuing them at zero.

| expiry | development contracts |
|---|---:|
| still restricted, so the club holds rights | 254 |
| unrestricted | 862 |
| already declined to qualify | 101 |

**252 of the 1,217 development contracts own at least one control year** — 88 own one, 93 two, 55
three, 14 four, 2 five. They are overwhelmingly short deals: 133 one-year contracts, 86 two-year,
31 three-year, 2 four-year. That is exactly the population where the rebuild sits *below* the
production chain in the reconciliation, and production's own terminal value appears on 185 rows,
all one- to three-year contracts.

## It is an option, and an option is not a stream

Control is a right, not an obligation. The club tables an offer while the player is worth more than
the offer and walks away when he is not — and once it walks away the remaining control years are
gone. There is no skipping a year and re-qualifying later.

So the value of the control years is the value of a **stopping rule**, and a stopping rule is worth
more than the stream it stops. That is a quantity a point valuation cannot reach, because a point
valuation has one path and nothing to decide. Production prices the same right (D13) by walking its
single projected path and truncating at the first control year whose projected surplus goes
negative, which is the best a single path can do.

## What the club is allowed to know — the whole identification question

A stopping rule is only as honest as the information it stands on, and it is easy to write one that
quietly reads the future. So four rules are priced **on the same draws**, differing only in what the
club knows when it decides:

- **committed** — the club takes every control year, good or bad. Not a right at all.
- **declared** — the club fixes the whole schedule in advance off the point projection, before a
  single path is drawn. This is production's rule, and it uses no path information whatsoever.
- **informed** — at each control year the club decides on what it knows *then*: the forecast,
  updated by how wrong the forecast has turned out so far on this path, and whether the player is
  still in the league. It cannot see the season it is deciding about.
- **hindsight** — the club knew the whole path and could only choose when to stop. The ceiling.

The update is the simulation's own dependence, not a new model. The miss in each season is a
standard normal before the empirical shape is applied, the fitted persistence gives their
correlation matrix, so the club's expectation of next season is the linear projection of that
normal onto the misses already seen, pushed through the shape. Nothing is fitted here that was not
already fitted for the paths. The expectation is **integrated** through the shape on a
Gauss–Hermite grid rather than substituted into it, which would be the club expecting the median.

Whether he plays is conditioned too. A club standing at a control year knows whether the player is
in the league, so the chance he plays next season is the participation chain's own transition — one
minus the exit probability if he is in it, the return rate if he is not — rather than the
unconditional marginal a point valuation uses.

**The ceiling is not "take every year that turns out positive."** Because walking away is final, a
club that wants a good third year must sit through a bad second one: on a path worth +5, −1, +10
the myopic rule collects 5 and taking all three collects 14. The first version of this module used
the myopic rule as its ceiling; it is not one. The ceiling is the best prefix, including the empty
one, so it is never below zero and never below any other rule here — and that is asserted, not
argued.

## What the right is worth

Dollars a contract, discounted to the signing, 2,000 paths.

| control years | n | committed | declared | informed | hindsight | deciding as you go is worth |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 88 | −0.556 | 0.079 | **0.190** | 0.367 | +0.111 |
| 2 | 93 | −0.038 | 0.317 | **0.614** | 0.934 | +0.297 |
| 3 | 55 | 1.117 | 1.111 | **1.453** | 1.628 | +0.343 |
| 4 | 14 | 1.538 | 1.063 | **1.635** | 1.852 | +0.572 |
| 5 | 2 | 1.851 | 0.583 | **1.932** | 2.373 | +1.349 |
| all | 252 | 0.136 | 0.451 | **0.716** | 0.950 | **+0.266** |

Three things in that table.

**The obligation is worth less than the right, and sometimes less than nothing.** A club forced to
take every control year loses money on the deals with one or two of them (−$0.56M, −$0.04M). The
same seasons, with the right to decline, are worth +$0.19M and +$0.61M.

**Deciding as you go is worth $0.27M a contract over deciding in advance**, and the gap widens with
the number of control years, because there are more decisions to get right. This is the part of the
asset that only exists over paths.

**It does not beat hindsight**, and it must not: the informed rule sits between the declared
schedule and the ceiling everywhere. Deciding on an expectation is not the same as not losing —
the informed rule ends up under water on 2 of the 252 contracts, which is what tendering on an
expectation means, not a defect.

The club tables an offer in **1.18 of its 2.00 control years** on average, deciding as it goes.

## What it does to the contract

Reported beside the contract's surplus, not folded into it. Every comparison already run in this
tree values a contract to its expiry, and moving the headline would silently re-date all of them.

| term | n | surplus $M | control years $M | together | control ÷ together |
|---|---:|---:|---:|---:|---:|
| 1 yr | 133 | −0.108 | +0.942 | +0.834 | 1.13 |
| 2 yr | 86 | −0.012 | +0.547 | +0.535 | 1.02 |
| 3 yr | 31 | +0.120 | +0.303 | +0.422 | 0.72 |
| 4 yr | 2 | +2.327 | +0.086 | +2.413 | 0.04 |

The last column is above one wherever the contract itself loses money: **on a one-year deal the
right to keep the player afterwards is worth more than the season the club just bought.** A ratio
above one is a statement about the contract being under water, not about the right being worth more
than everything.

## Against production's own terminal value

Production prices the same right by truncating one projected path, which is the declared rule here
and nothing else. The two are **not on the same information date** — production discounts to 1 July
of the first contract season, this discounts to the signing — so the levels are not expected to
agree and the comparison is about who carries the right and how they rank.

| | |
|---|---:|
| contracts in both | 241 of 252 |
| production's terminal value, mean | $0.894M |
| the declared rule here, mean | $0.409M |
| deciding as it goes, mean | $0.684M |
| rank correlation, production vs declared | 0.547 |
| rank correlation, production vs informed | 0.759 |

Production prices **57** of these contracts at exactly zero where this tree finds a right worth
$0.13M on average — and the reason is the truncation itself, not a disagreement about who owns the
right. Checked rather than assumed: the declared rule here gives **zero on all 57 of them too**,
and on 56 of the 57 this tree's own point projection also has the first control year under water.
Where the two rules both decide in advance, they decide the same way. The $0.13M is what the same
57 rights are worth once the club is allowed to decide as it goes instead.

The reverse case is larger and is a value-side disagreement rather than a rule one: on 127
contracts production carries a terminal value while this tree's point projection puts the first
control year below zero.

The rank correlation being *higher* against the informed rule than against the declared one is
worth stating and not over-reading. It is one ordering comparison on 241 contracts between two
models with different value sides, not evidence that clubs behave like the informed rule.

## The weak point: the offer's base salary

The CBA formula runs off the final year's **base salary**. The PuckPedia contract export this tree
reads carries one row per contract with an average annual value and no salary schedule, so the
average is used. That is measurable rather than arguable, against the per-season salaries
production joins from the clause feed:

| | contracts |
|---|---:|
| final-year salary equals the average within 1% | 421 |
| final salary **above** the average, so the offer is understated | 155 |
| final salary below the average | 17 |

Median ratio 1.000, 90th percentile 1.100. A front-loaded deal's last salary sits above its
average, so the average makes the offer too cheap and the control year too valuable. **That is the
direction of this approximation**, and it is why the qualifying-offer rule's 120%-of-cap-hit clause
— which exists precisely to catch front-loading — bites less here than it should.

## What is checked

- The qualifying-offer bands are reimplemented in this tree rather than imported from production,
  then **checked against production's implementation on 4,000 random cases: largest difference
  $0.00.** The two cannot drift apart unnoticed.
- The span: unrestricted or already-declined expiries own nothing; a restricted expiry runs from
  the season after the contract to the season before eligibility; an export whose eligibility year
  has already passed owns nothing.
- The ceiling sits through a bad year to reach a good one, is never below zero, and nothing beats
  it — on the worked case and on 500 random paths.
- **The informed rule cannot see the season it is deciding about.** Every season from the decision
  onward is redrawn and the club's expectation comes back bit for bit, at four horizons; scrambling
  the *past* moves it at all four, so the rule is not vacuously ignoring everything.

All four were tested by deliberately breaking them: reverting the ceiling to the myopic rule,
letting the club peek one season ahead, handing control years to unrestricted players, and freezing
the offer schedule. Each break is caught.

Suite: **28 passed, 0 skipped, 0 failed.**

## What this does not establish

- **Nothing here is scored against an outcome.** Whether clubs actually exercise the right this
  well is a back-test question, and the back-test has not run.
- **The informed rule is a model of a club, not a measurement of one.** It brackets the answer
  between deciding in advance and knowing the future; where real clubs sit in that range is not
  tested.
- **The forecast is extrapolated further here than anywhere else in the tree.** A control year sits
  past the contract's own term, so the longest horizons lean on the declared extrapolation past the
  fitted range.
- **Goalies are not here.** This is the skater branch; the goalie control-year gate is still open.
- The 2026 CBA's offer bands and league-minimum schedule were not public before the summer of 2025,
  so a valuation dated earlier could not have known them. The league minimum is now dated the way
  the cap ceiling already was — only figures published before the signing are used, and later
  seasons grow at 3% from the last one the date could see.

## Files

    50_REBUILD/code/control_years.py        the offer, the span, the four rules
    50_REBUILD/code/run_control_years.py    the run, the checks, the report

Writes `control_years.csv`: one row per contract with control years, carrying the number of them,
the offer schedule, the point projection's first-year surplus, the mean and spread under each rule,
and how many years the club tables an offer in when it decides as it goes. Outputs ignored under
`50_REBUILD/output/`.
