# Does the valuation hold when the forecast changes?

Run 2026-09-16 in `50_REBUILD/`. Experimental. Development start years only; the reserved market
cohorts are refused by the guard. **Nothing adopted, and no production file changed.**

**Revised after independent review** (`Valuation_Sensitivity_Review_Codex.md`, reviewing
`5e019ad`). Three findings, all accepted. One of them reverses this report's headline, and the
corrected answer is the stronger one. The withdrawals are in section 6.

## 1. Why this and not more diagnostics

The forecast has measured errors concentrated on stars and on young players at long horizons, and
three rounds of diagnostics could not separate their causes. That leaves one question worth
asking: **does any of it change the answer?**

The thesis does not claim to forecast a player. It claims certain categories of asset are
systematically mispriced. So the test is whether the valuation of **a fixed set of contracts**
holds when the forecast under it is replaced.

## 2. The grouping is declared once, and the first version got that wrong

Every column used to cut its tiers from its own forecast. That answers a real question — what does
each model say about the players *it* calls stars — but it is not a robustness test, because the
columns then describe different populations. The top tiers held **51, 68, 18, 19 and 18**
contracts, the report printed a single n row, and the spread across them was read as the same
contracts changing sign. They are not the same contracts.

The declared rule now: tiers are cut once on the adopted candidate's forecast production per
season, fixed before any column is priced, and joined to every column by contract id. Any rule
would do as long as it is one rule; this one is named so it can be objected to. The own-tier table
is still reported, second, labelled as the descriptive question it answers, with its own n.

## 3. Where the sample goes, and the first version blamed the wrong stage

| | contracts |
|---|---:|
| eligible on development cohorts | 1,896 |
| lost at forecast attachment | 438 |
| lost because the price line could not be fitted | 241 |
| **priced** | **1,217** |

The earlier report attributed the losses to the forecast not reaching far enough for a long deal,
and proposed extending its reach. **That is the wrong remedy.** The attachment path already
extrapolates past its fitted horizons. The binding constraint is downstream: a contract is priced
only if its signing quarter has enough *earlier* signings to fit a price line, and the early
quarters do not. The independent audit traced it contract by contract — of 35 excluded six-year
deals, **34 are lost at the price-fit threshold**, and 18 of 20 eight-year deals. Extending the
forecast would restore none of them.

The 842 rejections in the run log are against the full 3,519-contract input including reserved
cohorts. Only 438 belong to the development sample. The earlier report conflated the two.

## 4. The result, on the declared fixed groups

Mean surplus, $M over the whole deal, term-in currency, same 1,217 contracts, same membership in
every column:

| forecast | below 0 | 0 to 0.5 | 0.5 to 1 | 1 to 2 | 2+ |
|---|---:|---:|---:|---:|---:|
| production's forecast, priced here | −0.30 | +0.21 | +0.36 | +1.21 | −3.93 |
| trailing blend, carried flat | −0.49 | +0.25 | +0.50 | +0.84 | −4.55 |
| calibrated total + aging + participation | −0.42 | +0.10 | +0.63 | +1.76 | −1.74 |
| the same, participation pinned to one | −0.51 | +0.13 | +0.57 | +1.53 | −1.91 |
| the adopted candidate | −0.41 | +0.10 | +0.56 | +1.66 | −1.80 |
| **n** | 174 | 735 | 199 | 91 | **18** |

**Every group keeps its sign in all five columns, and the ordering is identical in all five.**
Worst to best: 2+ < below 0 < 0 to 0.5 < 0.5 to 1 < 1 to 2.

There is no sign reversal anywhere. The earlier report's headline — that the top tier flipped
between bargain and overpay — was an artifact of letting each column choose its own membership.

**What does not follow from this.** The top group's *magnitude* still ranges from −1.74 to −4.55,
so how overpaid is not settled even though the direction is. It is 18 contracts, on a development
sample, with no uncertainty estimate attached and no realised outcome scored. Stable signs on
model-generated valuations are a robustness check and nothing more.

At the contract level the models agree closely with production's forecast: correlation 0.974 to
0.988, the same sign on 88 to 97%, mean absolute gap $0.24M to $0.47M on deals worth millions.

### What each model says about its own stars, which is a different question

| forecast | 2+ | top-tier n |
|---|---:|---:|
| production's forecast, priced here | −0.19 | 51 |
| trailing blend, carried flat | +1.05 | 68 |
| calibrated total + aging + participation | −1.74 | 18 |
| the adopted candidate | −1.80 | 18 |

The models disagree about **who the stars are** far more than about what a given contract is
worth. That is worth knowing and it is not robustness.

## 5. What the participation half is worth

The earlier comparison swapped `A1AgingParticipationImputedNC` for `A1Calibrated3Aging`, which
also swaps the imputed survivorship aging for the uncorrected curve. Two things changed and the
result was read as one.

Corrected: the baseline against itself with the probability of playing pinned to one, everything
else held including the imputed aging. Run twice, because refitting the currency lets the market
slope absorb part of the change:

| fixed group | baseline | pinned, currency refitted | pinned, currency held |
|---|---:|---:|---:|
| below 0 | −0.422 | −0.512 | −0.526 |
| 0 to 0.5 | +0.101 | +0.132 | +0.266 |
| 0.5 to 1 | +0.627 | +0.573 | +0.979 |
| 1 to 2 | +1.756 | +1.531 | +2.053 |
| 2+ | −1.736 | −1.910 | −1.592 |

**Signs and ordering survive both.** The movement is larger than the earlier report's −1.74 to
−1.68, which came from the confounded pair.

The defensible statement: *these valuation patterns survive the participation alternatives
tested.* Not that calibration is immaterial. Pinning everyone to play is not a calibrated repair,
and this says nothing about individual contracts, a path simulation, or a realised trade result.

## 6. Claims withdrawn

1. **"The top tier flips sign across forecasts."** An artifact of per-column tier membership. On
   one declared grouping every column is negative. Withdrawn, and with it "a second independent
   reversal of the headline" and "two design choices each flip it".
2. **"Removing participation barely matters."** The pair used also changed the aging curve. The
   corrected test moves the top group −1.736 → −1.910 or −1.592. Restated as: the patterns survive
   the alternatives tested.
3. **"The forecast's calibration errors are not what threatens the conclusion."** Too strong on
   this evidence. Withdrawn.
4. **"Extending the forecast's reach is the cheapest real gain."** Wrong stage: 34 of 35 excluded
   six-year deals are lost at the price-fit threshold, not the horizon. Withdrawn.
5. **"A framing judgement is worth three to five times any modelling difference."** The
   denominator was the spread across own-tier columns, which was itself a change of population.
   On the fixed top group the term contrast runs $8.76M to $9.70M across all five forecasts — it
   is large and it reproduces, but it is a contrast between two declared framings on one group,
   not a general measure of relative model uncertainty.
6. **"Cite the three robust categories; do not cite the elite one."** Selecting categories by
   their current development-sample signs is the selection problem this project exists to avoid.
   The back-test should evaluate the predefined categories and report where conclusions are
   sensitive.
7. **"How does the live chain compare."** The production column is production's projection and
   exit-survival imported through the adapter and then priced through **this tree's** currency. It
   is not the production contract-NPV chain's output, and agreement with it is not parity with the
   production spine. The adapter also inherits production's full-panel aging fit, so it carries a
   parameter look-ahead the rolling price fits here do not remove.

## 7. Limits

- Not a back-test. Nothing scored against a realised outcome, no trade priced.
- Development-sample means with no uncertainty estimates attached.
- Each column refits its own currency, so levels are not comparable across columns.
- 18 contracts in the top group.
- The component-model variant is absent because it raises an `AttributeError` inside its own fit.
  The 22 repair checks pass despite this, so they do not establish that every registered variant
  runs.

## 8. What follows

Finish the planned valuation and back-test work **with a declared grouping rule stated in
advance**, evaluate the predefined categories, and report where conclusions are sensitive rather
than dropping categories that look unstable. Agreement among model valuations is a robustness
check; a back-test against realised outcomes is evidence about performance; systematic trade
mispricing is the claim that still needs testing. Those three are different and the write-up
should keep them apart.

## Files

    50_REBUILD/code/run_valuation_sensitivity.py

Outputs, ignored under `50_REBUILD/output/`: `valuation_sensitivity_run_log.txt`,
`valuation_sensitivity.csv`. The reviewer's reproduction is
`50_REBUILD/code/review_valuation_sensitivity.py`.
