# Full-chain movement against the production spine, contract by contract

Run 2026-09-16 in `50_REBUILD/`. The plan's Phase 5 acceptance item. Development start years only.
**Nothing adopted, and no production file changed.**

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

One thing does **not** match: `goalie_value_spine_v2.csv` hashes to `7e481bf4…` where the record
says `55c935dd…`. Every content check on that file passes, including the parity gate against the
locked v1 at $0.000284 and the 1,730 priced rows, so the likeliest cause is float formatting under
a different pandas version. **That is a guess and it is not verified** — the locked v2 is not here
to compare against.

## What is and is not comparable

Both sides are a dollar surplus over the contract, discounted from the signing. They are **not the
same construct**. Production prices production on the locked censored regression and carries it
with survival weights on top. The rebuild prices a signing-dated forecast on a rolling currency,
with participation inside the forecast rather than as a weight over it.

So the levels are two different definitions of surplus and their difference is not an error in
either. What is comparable is the **movement**: whether the two order the same contracts the same
way.

1,141 contracts are in both.

## They agree about ranking and disagree about long contracts

| | vs production NPV | vs production, no survival |
|---|---:|---:|
| rank correlation | 0.418 | 0.453 |
| linear correlation | 0.290 | 0.304 |
| agree on sign | 66% | 68% |

Moderate overall — and the aggregate hides the whole of the story, because **the disagreement is
almost entirely a function of term**:

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

The gap is monotone in term and reaches **$33.6M a contract** at eight years, where production
says the average deal destroys $28M of value and the rebuild says it creates $5M.

**Within each term the two systems still agree about ordering** — rank correlation 0.69 to 0.89
across three to eight years. They agree about which long contracts are better than which. They
disagree, enormously, about whether long contracts are worth signing at all.

Every one of the ten largest individual disagreements is an eight-year deal:

| player | start | term | rebuild $M | production $M | gap |
|---|---:|---:|---:|---:|---:|
| Drew Doughty | 2019 | 8 | −18.89 | −70.56 | 51.66 |
| Clayton Keller | 2020 | 8 | +6.62 | −40.73 | 47.35 |
| Josh Morrissey | 2020 | 8 | +9.91 | −37.24 | 47.15 |
| Erik Karlsson | 2019 | 8 | −25.73 | −70.23 | 44.50 |
| John Carlson | 2018 | 8 | −6.26 | −47.26 | 41.00 |

## It is not the exit hazard, and the project has been assuming it was

The obvious suspect is production's survival weighting: multiply eight seasons by a compounding
hazard and a long deal loses most of its value. The rebuild's own premise says as much — the
standing note that "the exit hazard was quietly offsetting over-projection".

The spine carries production's surplus with that weighting removed, so the two candidates can be
separated rather than argued about:

| term | production | no survival | **the weight** | the rest of the gap |
|---|---:|---:|---:|---:|
| 4 yr | −4.49 | −3.79 | +0.70 | **+4.33** |
| 6 yr | −14.32 | −13.56 | +0.76 | **+15.09** |
| 7 yr | −21.23 | −21.40 | −0.17 | **+24.78** |
| 8 yr | −28.19 | −28.77 | **−0.58** | **+34.21** |

**The survival weight accounts for essentially none of it.** At eight years it is worth −$0.58M
against a gap of $34.21M; at six years, $0.76M against $15.09M. Removing production's exit hazard
entirely would leave the disagreement almost exactly where it is.

So production's long-contract pessimism lives on the **value side** — the aging path applied
season by season across a long term, and the value line it is priced on — not in the survival
margin. That is a different repair from the one the standing note implies, and it relocates the
largest full-chain movement in this project.

## What this does not establish

- **Neither side is scored against an outcome here.** This is two models disagreeing, not evidence
  that one is right. A long deal looking better under the rebuild is not a finding that long deals
  are good.
- **The level difference is definitional in part.** The two put participation in different places,
  so some constant offset is expected. What is not definitional is the *gradient in term*, and the
  survival decomposition above is what separates them.
- **22 eight-year contracts.** The largest gaps sit on the smallest cells, as they have all week.
- **Development sample only**, and the reserved cohorts are refused by the guard.
- The rebuild's own long-horizon forecasts lean on the declared extrapolation past the fitted
  range, which is flattered upward by a stated amount. Some of the eight-year gap is that.

## Files

    50_REBUILD/code/run_valuation_integration.py

Writes `contract_valuation.csv`: one row per contract, 1,217 contracts and 31 columns, carrying
cost, the adopted forecast's value and surplus, the surplus under all five forecasts, the
simulated distribution, the declared sensitivities, and production's NPV with and without
survival. Outputs ignored under `50_REBUILD/output/`.
