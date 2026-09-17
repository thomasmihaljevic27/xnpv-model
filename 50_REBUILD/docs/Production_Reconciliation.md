# Full-chain movement against the production spine, contract by contract

Run 2026-09-17 in `50_REBUILD/`. The plan's Phase 5 acceptance item. Development start years only.
**Nothing adopted, and no production file changed.**

An earlier version of this report (2026-09-16) claimed the exit hazard had been ruled out as the
source of the long-contract disagreement. It had not been. What that version subtracted was an
undiscounted column, so it removed the discounting along with the hazard. The corrected
arithmetic is below, and the claim it supports is narrower.

## The production chain runs here, and reproduces its locked record

Thomas supplied `contract_season_spine.csv` and `goalie_value_spine.csv`, so production's own
chain ran in this container for the first time. Every guard on record reproduces:

| guard | locked | this run |
|---|---|---|
| Stage 0a, regression reproduction | PASS | **PASS** |
| Stage 0b, censored rate | alpha 0.01324782 | **0.01324290**, PASS |
| priced skater-seasons | 6,892 | **6,892** |
| skater k=0 vs Layer 1 | $0.00 | **$0.00** |
| goalie parity gate | $0.000284 | **$0.000284** |
| contracts priced | 2,981 (2,591 skater, 390 goalie) | **2,981 (2,591 / 390)** |
| NPV distribution | median +0.29, p10 −7.80 | **median +0.29, p10 −7.80** |

One thing does **not** match: the `goalie_value_spine_v2.csv` regenerated here hashes to
`7e481bf4…` where the record says `55c935dd…`. Every content check on that file passes, including
the parity gate against the locked v1 at $0.000284 and the 1,730 priced rows. An independent
rerun in a separate checkout regenerated the file and got `55c935dd…` exactly, with parsed values
and missingness matching. So the difference is specific to this container and **unexplained**. An
earlier version of this report guessed float formatting under a different pandas version; that was
never tested and is withdrawn. It stays open until the two files are compared directly.

## What is and is not comparable

Both sides are a dollar surplus over a contract. They are **not the same construct, and they are
not even dated alike.**

- Production prices on the locked censored regression, carries survival weights on top, and values
  from **1 July of the first contract season**. The rebuild prices a **signing-dated** forecast on
  a rolling currency, with participation inside the forecast rather than as a weight over it.
- Production carries **terminal control value** past expiry on some contracts. The rebuild's
  simulator stops at expiry by construction.
- Production's cost is the cap hit in the supplied season spine. The rebuild's cost is the
  contract's own AAV. On most contracts those agree; on a few dozen they do not.

So the levels are two different definitions of surplus, on two different information dates, and
their difference is not an error in either. What is comparable is the **movement**: whether the
two order the same contracts the same way.

1,141 contracts are in both before any check.

## Who survives a like-for-like test, and who does not

Production's sweep calls its engine with a player and a season and then labels the result with the
contract ID it *asked* about. The engine follows a chain and can value a different contract. So
matching on contract ID alone does not establish that the two sides priced the same asset. Each
test below is reported separately, because they overlap and the reasons matter more than the count.

| test | rows failing |
|---|---:|
| production valued a **different contract** than the one requested | 10 |
| production covers a different number of seasons | 3 |
| production carries terminal control value the rebuild excludes | 185 |
| the two sides disagree about cost by more than 10% | 46 |
| the valuation year differs from the signing year | 240 |
| **comparable on every test** | **912 of 1,141** |

The ten mislabelled contracts are 4334, 4336, 4453, 4547, 4798, 5598, 5627, 6364, 7010 and 7108.
Nate Schmidt's requested 4798 is priced as 3632, one season against a six-year deal; Evander
Kane's 7108 is priced as 4118. A unique exported ID does not repair this.

**The date test is reported and not used to exclude.** Production values from 1 July of the first
contract season and the rebuild values at the signing, so the two sit on different information
dates even when the calendar years agree. Equal years would not make them the same date. That is a
limitation of the whole comparison, not a property of 240 particular rows.

The largest cost disagreements are a source inconsistency rather than anything this comparison
introduced: the supplied season spine carries a cap hit an order of magnitude away from the
contract's own AAV, and production prices the cap hit.

| contract | production cost $M | rebuild cost $M | ratio | also a wrong contract? |
|---|---:|---:|---:|---|
| 5598 | 12.318 | 0.700 | 17.6 | yes |
| 7108 | 26.800 | 2.109 | 12.7 | yes |
| 6216 | 8.625 | 0.750 | 11.5 | no |
| 5606 | 19.216 | 1.866 | 10.3 | no |

No production input was changed, and no problem row was dropped silently: every contract keeps its
row in `production_reconciliation.csv` with the flags and a written reason.

**The attrition falls almost entirely on short contracts.** All 185 terminal-value rows are one-
to three-year deals. Four, five, seven and eight years lose nobody at all; six years loses two
contracts on a cost disagreement, three years eleven, and one and two years together 216.

## They agree about ranking and disagree about long contracts

| | vs production NPV |
|---|---:|
| rank correlation | 0.418 |
| linear correlation | 0.290 |
| agree on sign | 66% |

Moderate overall — and the aggregate hides the story, because the disagreement runs with term.
Term-group means account for **84.8%** of the squared variation in the dollar gap. That is strong;
it is not literally all of the disagreement, and the definitional differences above can themselves
vary with term.

| term | n | rebuild $M | production $M | mean gap | rank correlation within term |
|---|---:|---:|---:|---:|---:|
| 1 yr | 551 | −0.10 | +0.30 | −0.39 | 0.506 |
| 2 yr | 304 | −0.15 | +0.51 | −0.66 | 0.746 |
| 3 yr | 108 | +0.13 | −1.08 | +1.21 | 0.804 |
| 4 yr | 66 | +0.54 | −4.49 | +5.03 | 0.827 |
| 5 yr | 31 | −0.55 | −9.09 | +8.54 | 0.797 |
| 6 yr | 33 | +1.53 | −14.32 | **+15.86** | 0.688 |
| 7 yr | 26 | +3.38 | −21.23 | **+24.61** | 0.889 |
| 8 yr | 22 | +5.44 | −28.19 | **+33.63** | 0.759 |

The gap is monotone in term and reaches **$33.6M a contract** at eight years, where production says
the average deal destroys $28M of value and the rebuild says it creates $5M.

**Within each term the two systems still agree substantially about ordering** — rank correlation
0.69 to 0.89 across three to eight years. That is substantial ranking agreement, not identical
ordering, and it is not proof that what remains is a value-side issue.

Every one of the ten largest individual disagreements is an eight-year deal:

| player | start | term | rebuild $M | production $M | gap |
|---|---:|---:|---:|---:|---:|
| Drew Doughty | 2019 | 8 | −18.89 | −70.56 | 51.66 |
| Clayton Keller | 2020 | 8 | +6.62 | −40.73 | 47.35 |
| Josh Morrissey | 2020 | 8 | +9.91 | −37.24 | 47.15 |
| Erik Karlsson | 2019 | 8 | −25.73 | −70.23 | 44.50 |
| John Carlson | 2018 | 8 | −6.26 | −47.26 | 41.00 |

## The exit hazard, isolated — and what that does and does not settle

The obvious suspect is production's survival weighting: multiply eight seasons by a compounding
hazard and a long deal loses most of its value. The rebuild's own premise says as much — the
standing note that "the exit hazard was quietly offsetting over-projection".

Isolating it means holding everything else. The production spine carries a column called
`surplus_no_survival`, but that column is **undiscounted contract surplus plus terminal value at
production's own reference date**. Subtracting production's NPV from it removes the discounting
along with the hazard, and the earlier version of this report did exactly that. The tell was that
it produced *negative* hazard effects: removing a survival haircut cannot lower a value when the
value is nonnegative and everything else is fixed.

The correct comparison is rebuilt from production's own per-season detail, setting the survival
multiplier to one and holding cost, the discount factor and terminal value:

    no-hazard NPV = sum over seasons of (value − cost) × discount  +  the original terminal NPV

| term | n | production $M | no hazard $M | **the hazard is worth** | gap to rebuild | what the earlier report claimed |
|---|---:|---:|---:|---:|---:|---:|
| 4 yr | 66 | −4.49 | −3.63 | **+0.86** | +5.03 | +0.70 |
| 6 yr | 33 | −14.32 | −12.64 | **+1.69** | +15.86 | +0.76 |
| 7 yr | 26 | −21.23 | −19.56 | **+1.67** | +24.61 | −0.17 |
| 8 yr | 22 | −28.19 | −25.90 | **+2.29** | +33.63 | −0.58 |

Every effect is now positive, as it must be, and zero of the 1,141 rows have removing the hazard
lower the value. The comparable-only subsample is identical at four, five, seven and eight years,
because those cells lose nobody; at six years its 31 contracts give +1.76 against a gap of +16.96.

**What this supports, and only this: the exit hazard alone does not explain the long-contract
gap.** At eight years it is worth $2.29M against a gap of $33.63M; at six years, $1.69M against
$15.86M. Roughly nine-tenths of the long-term disagreement survives removing it.

It does **not** identify the aging path or the price line as the cause — nothing here tests those.
It does **not** show that the two systems' remaining difference is a value-side issue rather than
the definitional and dating differences catalogued above. And it does **not** test whether the
hazard historically offset over-projection against realised outcomes, which is the claim the
standing note actually makes. That test needs outcomes, and there are none in this comparison.

## What this does not establish

- **Neither side is scored against an outcome here.** This is two models disagreeing, not evidence
  that one is right. A long deal looking better under the rebuild is not a finding that long deals
  are good.
- **The level difference is definitional in part.** Different information dates, different
  treatment of control years, different cost inputs on some rows, participation in different
  places. Some of the gradient in term may be definitional too.
- **22 eight-year contracts.** The largest gaps sit on the smallest cells.
- **Development sample only**, and the reserved cohorts are refused by the guard.
- The rebuild's own long-horizon forecasts lean on the declared extrapolation past the fitted
  range, which is flattered upward by a stated amount. Some of the eight-year gap is that.

## Files

    50_REBUILD/code/run_valuation_integration.py
    50_REBUILD/code/run_production_reconciliation.py

The first writes `contract_valuation.csv`: one row per contract, 1,217 contracts and 31 columns,
carrying cost, the adopted forecast's value and surplus, the surplus under all five forecasts, the
simulated distribution, the declared sensitivities, and production's NPV. It carries production's
nominal column under its honest name, `production_surplus_nominal_no_survival`, and decomposes
nothing out of it.

The second imports production's own engine, prices each contract through it for the per-season
detail and the chain of contract IDs actually valued, and writes `production_reconciliation.csv`:
identity, season coverage, dates, costs, terminal-value flag, the isolated hazard, and a written
reason for every row that fails a comparability test. Outputs ignored under `50_REBUILD/output/`.
