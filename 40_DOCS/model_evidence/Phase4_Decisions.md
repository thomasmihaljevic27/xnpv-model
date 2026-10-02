# The two market decisions: one is answered, one is yours

Run 2026-09-15 in `50_REBUILD/`. Experimental. No production file changed, no locked decision
opened. 2,580 skater standard-level contracts with 2015–2025 starts, each carrying a forecast
built from information frozen at **its own signing date**.

## The signing-date problem this is built around

The locked market sample dates contracts by start season and reads the two prior seasons. The
audit found 30% of it was signed before those seasons had finished — 58% at 3+ wins, because
the best players re-sign early. On this sample, **596 of 3,550 deals (16.8%) were signed before
the prior season was readable.**

Dating by contract start hands those deals an anchor built from games that had not been played
when the pen moved, and it flatters exactly the expensive contracts. Here each contract's
forecast comes from an information set frozen at its signing date, through the same machinery
every other forecast in this tree uses. Contracts are batched by which seasons were readable
when they were signed, since that is the only thing that varies.

## Decision B: one price line or two — answered, and the locked answer holds

Each season's contracts are priced using only contracts signed before it. Error is in cap share,
so 0.010 is one percent of the cap, about $0.9M in 2024.

| season | n | one line | two lines | better |
|---|---:|---:|---:|---|
| 2018 | 280 | 0.00862 | 0.00811 | two lines |
| 2019 | 292 | 0.00856 | 0.00837 | two lines |
| 2020 | 287 | 0.00731 | 0.00732 | one line |
| 2021 | 299 | 0.00766 | 0.00767 | one line |
| 2022 | 324 | 0.00766 | 0.00759 | two lines |
| 2023 | 270 | 0.00855 | 0.00863 | one line |
| 2024 | 285 | 0.00893 | 0.00884 | two lines |
| 2025 | 272 | 0.00850 | 0.00861 | one line |
| **weighted** | **2,309** | **0.00821** | **0.00813** | two lines |

Two lines win by 1.00%, which is **$7,203 on the average contract** — and they win in four
seasons out of eight. A method that were genuinely better would not be splitting seasons
evenly, and the weighted gap is smaller than the year-to-year variation within either method.

**The data does not distinguish them.** That is a finding rather than a failure: the locked
single line (D7, which rested on F=0.12, p=0.887) survives a test built on signing-dated
forecasts rather than start-dated ones, and the rebuild has no cause to reopen it. Restricted
status still enters the price model as a feature — it is worth −0.0036 of cap share directly and
−0.0043 more per forecast win — it just does not need a line of its own.

## Decision A: term as value or as mispricing — not a horse race

A held-out test cannot settle this and a horse race between the two would be theatre. They price
different things and would need different targets. Term-in says the security of a long deal is
part of what the team bought; term-free says it is a premium to be measured against a one-year
price. Both are internally consistent. What can be done is to build both and show where they
disagree, so the choice is made with the disagreement in view.

The fitted price line, in cap share per unit:

| | coefficient |
|---|---:|
| forecast wins per season | +0.02914 |
| **years of term** | **+0.00986** |
| restricted status | −0.00363 |
| restricted × forecast wins | −0.00425 |
| defenceman | +0.00540 |
| one-year deal | +0.00148 |
| first-season forecast | −0.00204 |

A year of term carries about **$0.87M a season** at the 2024 ceiling.

**Read that as an association, not a price.** Long deals go to better players, and the forecast
controls for production only as well as the forecast does. Whatever quality the forecast misses,
term will carry, because term is assigned on exactly the information teams have and models do
not. Stripping term out therefore strips some genuine quality with it. This cuts directly
against reading the whole gap below as a premium, and it is the main reason decision A cannot be
settled by fitting harder.

Where the two currencies disagree — total cap share consumed across the whole deal, and the
whole-contract dollar gap at the 2024 ceiling:

| term | n | term-in | term-free | gap |
|---|---:|---:|---:|---:|
| 1 | 1,040 | 0.0117 | 0.0117 | $0.0M |
| 2 | 732 | 0.0391 | 0.0261 | $1.2M |
| 3 | 248 | 0.1071 | 0.0557 | $4.5M |
| 4 | 172 | 0.1877 | 0.0786 | $9.6M |
| 5 | 96 | 0.3033 | 0.1159 | $16.5M |
| 6 | 107 | 0.4156 | 0.1304 | $25.1M |
| 7 | 72 | 0.5720 | 0.1698 | $35.4M |
| 8 | 113 | 0.7868 | 0.2469 | $47.5M |

And by forecast production, which is what makes this consequential:

| forecast wins/season | n | mean term | gap per contract | gap, total |
|---|---:|---:|---:|---:|
| below 0 | 507 | 1.71 | $1.5M | $774M |
| 0 to 0.5 | 1,385 | 2.12 | $3.9M | $5,389M |
| 0.5 to 1 | 401 | 3.47 | $11.2M | $4,504M |
| 1 to 2 | 244 | 4.35 | $17.4M | $4,235M |
| 2+ | 43 | 4.88 | $20.8M | $896M |

**The choice is worth $15.8 billion across 2,580 contracts, and it is concentrated exactly where
the thesis lives** — the good players on long deals, who are also the players who get traded and
whose surplus the back-test is trying to measure. A one-year deal is unaffected either way.

## What I would choose, and why it is still yours

**Term-in**, with term-free reported as the sensitivity, for one reason that is about the data
rather than about theory: the one-year counterfactual does not exist for the players who carry
the money. 94% of 3.5-win contracts are signed with the player's own club. Pricing a star's
production at a one-year rate compares him to a market that never had the chance to bid, and
then calls the difference mispricing.

But this is an economics decision about what the thesis claims, not a fit statistic, and the
confounding above means term-free is not simply "the same value with a premium removed" — it is
a different quantity with some real quality removed too. Both belong in the paper; which one is
primary determines what the back-test is measuring.

## What is not built

- The production currency proper. This prices contracts; converting forecast production into
  dollars on a declared reference market is the other half of Phase 4 and waits on decision A.
- Goalies, and the 970 contracts whose players have no usable forecast (mostly players with too
  little NHL history at signing — an entry-level population the prospect pillar covers).

---

# The production currency, and the first dollar values

Decision A settled **term-in** (Thomas, 2026-09-15), decision B settled **one line** by the test
above. Both are now built. 2,309 contracts with 2018–2025 starts, each priced on a line fitted
only to deals signed before its own start season.

## What surplus means here

The currency is the market's own price for forecast production. Because the line is fitted to
observed contracts, the average contract prices at roughly zero surplus **by construction**, and
a positive number means "this club paid less than the average club paid for a comparable
forecast". It is deviation from the market, not profit. That is the circularity this project has
always known about; it is bounded here, not removed, and every claim built on it inherits it.

## Surplus by forecast production

Over the whole deal, in millions:

| forecast wins/season | n | mean | median | sd | share positive |
|---|---:|---:|---:|---:|---:|
| below 0 | 481 | −0.39 | 0.00 | 2.51 | 40% |
| 0 to 0.5 | 1,267 | +0.35 | 0.00 | 3.48 | 52% |
| 0.5 to 1 | 333 | +0.93 | +0.38 | 6.15 | 59% |
| 1 to 2 | 191 | **+3.05** | +1.52 | 8.11 | **65%** |
| 2+ | 37 | +3.00 | +1.28 | 11.50 | 57% |
| all | 2,309 | +0.54 | 0.00 | 4.66 | 51% |

**Surplus rises with forecast production.** Good players are systematically cheaper relative to
what the average club pays for a comparable forecast. That is the shape the thesis went looking
for, and it is the first time the rebuilt chain has produced it end to end.

## The honest question about that gradient

A rising residual against the very variable the line is fitted on is what you would also see if
the price function were curved and the line were straight. The actual price paid:

| forecast wins/season | n | mean forecast | mean cap share paid | implied share per win |
|---|---:|---:|---:|---:|
| 0 to 0.5 | 1,267 | 0.17 | 0.0203 | 0.1203 |
| 0.5 to 1 | 333 | 0.72 | 0.0441 | 0.0609 |
| 1 to 1.5 | 143 | 1.21 | 0.0585 | 0.0485 |
| 1.5 to 2 | 48 | 1.71 | 0.0777 | 0.0454 |
| 2 to 3 | 31 | 2.28 | 0.0963 | 0.0422 |
| 3+ | 6 | 3.57 | 0.1085 | **0.0304** |

If the market paid a constant price per forecast win the last column would be flat. It falls by
a factor of four. **Clubs pay progressively less per win as production rises**, which is exactly
what "stars are underpaid" means in this market — and it is also exactly what curvature in the
price function looks like. The two are the same arithmetic described from different ends.

The locked record already tested a curved price line and rejected it out of sample at Stage 3.
That test was run on start-dated anchors. **It should be rerun on signing-dated forecasts before
this gradient is presented as mispricing**, because the retest is cheap and the claim is the
thesis's central one. Recorded as the next thing to do rather than assumed either way.

Note also the 3+ cell is six contracts. Nothing at the very top of this market is estimated on
enough data to carry a claim on its own.

## Where the term decision does its work

Mean surplus over the deal, in millions:

| term | n | term-in (adopted) | term-free (sensitivity) | difference |
|---|---:|---:|---:|---:|
| 1 | 1,040 | −0.20 | −0.20 | 0.00 |
| 2 | 652 | −0.07 | −1.15 | 1.08 |
| 4 | 133 | +0.40 | −9.16 | 9.56 |
| 6 | 64 | +4.11 | −21.79 | 25.91 |
| 8 | 93 | **+8.32** | **−42.02** | 50.34 |

Under term-free every long deal in the league is a large loss, because the production is priced
at a one-year rate while the cost is the real multi-year commitment. Under term-in long deals for
good players are the best value in the market. **The two currencies do not disagree about
magnitude; they disagree about sign.** The sensitivity is reported in the paper, not discarded.
