# Participation: the biggest single gain in the rebuild

Run 2026-09-15 in `50_REBUILD/`. Experimental. No production file changed, no locked decision
opened. Development seasons 2015–2021 only; the held-back seasons are untouched.

## The prediction this tests

The aging work ended with a diagnosis and a prediction committed in writing before anything was
built. The diagnosis: the aging walk's long-horizon deficit was not a curve problem but a
participation deficit — at five seasons out among players 34 and over it predicted below zero
for 99% of them while 98% had already stopped playing. The prediction: **participation closes
most of that gap.**

It closed all of it and reversed the ordering.

## What the model is

For a player and a future season, the probability he plays a meaningful NHL season. Meaningful
is the same ten-game bar the rate forecast is estimated on and the harness scores against —
deliberately, because the rate is conditional on playing, so the probability multiplying it has
to be the probability of the same event or the product is of two different things.

Each future season gets its own probability rather than a survival chain that ends a career at
the first absence. A player can be absent at +2 and back at +3, which is what actually happens.

Fitted per horizon, rolling, on age in the target season, trailing level, trailing games share,
experience, position, and **contract state** — whether he is under contract for that season,
counting only deals signed on or before the decision date.

## The result

Average miss in wins, on identical rows:

| model | valuation | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| previous leader (no participation) | 0.5714 | 0.5954 | 0.5887 | 0.5884 | 0.5861 | 0.5705 |
| aging walk, no participation | 0.5714 | 0.5909 | 0.5886 | 0.6025 | 0.6287 | 0.5893 |
| aging walk + participation (with contracts) | 0.5508 | 0.5539 | 0.5311 | 0.5089 | 0.4861 | 0.4392 |
| **aging walk + participation (no contracts)** | **0.5501** | **0.5524** | **0.5274** | **0.5030** | **0.4668** | **0.4218** |
| component model, aging + participation | 0.5490 | 0.5559 | 0.5333 | 0.5116 | 0.4901 | 0.4401 |
| six regressions + participation | 0.5508 | 0.5580 | 0.5382 | 0.5160 | **0.4857** | 0.4502 |

Against the previous leader that is **3.7% better at the valuation season and 26.1% better five
seasons out** — the largest single improvement anything in this rebuild has produced, larger
than the three-season window, the shrinkage, and the aging curve combined.

How well each model knows whether a player will be on the ice at all, scored as a Brier score
(0 is perfect):

| | valuation | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| placeholder (everyone plays) | 0.278 | 0.355 | 0.424 | 0.483 | 0.538 | 0.595 |
| participation model | **0.131** | **0.146** | **0.151** | **0.152** | **0.165** | **0.164** |

The placeholder got steadily worse the further out it looked, because it kept insisting that
everyone was still playing. The participation model is roughly flat, which is the shape it
should be: uncertainty about a player's future stops growing once you are honestly modelling
the thing that actually happens to careers.

## The aging walk, judged again

With participation underneath both, the explicit aging walk now beats the six independent
per-horizon regressions it replaces:

| seasons ahead | aging walk vs six regressions | verdict |
|---|---:|---|
| valuation | +0.00% | identical by construction |
| +1 | −0.73% | aging better |
| +2 | −1.32% | aging better |
| +3 | −1.38% | aging better |
| +4 | +0.09% | tie |
| +5 | −2.44% | aging better |

Before participation the same comparison had aging losing by 2.4%, 7.3% and 3.3% at three, four
and five seasons out. **The reversal is complete, and it is the diagnosis being confirmed rather
than a new model being found.** The curve was always fine; it was being scored without the layer
it was designed to sit on.

This matters beyond the accuracy number. The walk is the form Phase 5's simulation needs — a
career path drawn one step at a time — and it no longer costs anything to use it.

## The contract data does not help. It hurts.

**This section replaces an earlier version of it that said the opposite. The earlier claim —
that contract state was worth 5% to 13% — was wrong, and the error is worth recording because
of how it hid.**

With no contract data, both contract columns become constants: zero for `under_contract` and one
for `contract_unknown` on every row. A constant column is collinear with the intercept, so the
logistic design was singular, **every fit failed on every horizon, and the model fell back to a
single base rate for everyone.** The ablation was therefore not comparing "participation with
contracts" against "participation without contracts". It was comparing participation against no
participation model at all, and reporting the difference as the value of the contract feature.

The fallback was silent. A model returning one flat probability looks like a working model with
no strong opinion, which is exactly what a participation model might legitimately be. What gave
it away was the probability by tier: a flat 59% for every level of player, when in truth 44% of
below-replacement players and 97% of 3+ win players go on to play. No fitted model produces
that.

Fixing it took three passes, and the first two were not enough — recorded because each pass
changed the number and the last one changed it by a factor of four.

1. **Drop the contract columns when there is no contract data**, so the ablation removes the
   feature instead of the model.
2. **Log a failed fit loudly** instead of falling back in silence.
3. **Require a feature to have real support before it earns a coefficient.** A variance test was
   not enough: a binary column that is true for 2% of rows has a healthy standard deviation and
   still cannot carry a coefficient. With only a variance test, the WITH-contract model was
   still failing at four and five seasons out — precisely the horizons where the contract
   feature was being judged worst — so the first re-measurement was comparing a working model
   against a crippled one in the other direction. A binary feature now needs at least fifty rows
   on its rarer side, and a fit that still fails retries on the base features alone before
   giving up on the horizon. Zero fits now fail on any development page.

Re-measured with every fit converged, on identical rows:

| seasons ahead | valuation | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| effect of adding contract data | −0.12% | **−0.26%** | **−0.68%** | **−0.91%** | **−0.90%** | **−0.87%** |

Negative means the contract feature makes the forecast **worse**, and every interval past the
valuation season excludes zero. The direction is robust across all three passes; the magnitude
was not — an intermediate version of this document reported −3.98% at four seasons out, which
was the broken fit rather than the feature. The honest number is about nine tenths of one
percent. The best participation model in the register is still the one that never sees a
contract, but it wins by a hair rather than by a mile.

Where the feature survives the support test is itself informative: on the 2015 page it earns a
coefficient only at the valuation season and one season out, on 2017 out to three seasons, and
only from 2019 does it earn one at every horizon. That is the coverage table below, showing up
as the model declining to use a feature it cannot support.

The probability of playing by tier says why the feature has so little to add:

| tier | with contracts | without | actually played |
|---|---:|---:|---:|
| below 0 | 53% | 48% | 44% |
| 0 to 1 | 70% | 66% | 63% |
| 1 to 2 | 92% | 89% | 91% |
| 2 to 3 | 96% | 95% | 97% |
| 3+ | 98% | 97% | 97% |

Trailing level, age, games played and experience already carry almost all the signal about
whether a player will be on the ice. Being good and being available are close to the same
question, and the contract is largely a consequence of the first rather than independent
evidence about the second.

**Why it actively hurts is the coverage asymmetry.** The share of players being valued whom the
export knows, as of 1 July each year:

| 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022–2025 (sealed) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 11% | 18% | 34% | 64% | 87% | 94% | 99% | 97% |

This is decision D8's thin-early-coverage finding in a new place. On the early pages
`contract_unknown` is true for most players, so it functions as an era indicator rather than as
a fact about a player, and the model learns a relationship from those pages that does not hold
on the later ones. A feature whose availability is correlated with the calendar is a feature
that teaches the model about the calendar.

**What this does not say.** It does not say contract state is irrelevant to hockey, or that it
will be irrelevant in Phase 4, where the contract IS the object being priced. It says that for
predicting whether a player suits up, on this panel, with this coverage, it adds nothing and
costs a little. If the export is ever backfilled to cover the early 2010s evenly, this is worth
retesting.

## One bug caught on the way

The first version dated contract state once for a training set drawn from a decade of valuation
seasons, which handed a 2010 row the contract knowledge of 2015 — a look-ahead leak of exactly
the kind the rest of this tree is built to make impossible. The information-set object that
prevents this for season data does not yet cover the contract side, which is how it got through.
Contract state is now dated from each row's own valuation season. Every figure here was measured
after the fix.

## Where it stands

- **New leader: the calibrated total with a three-season window, the additive aging walk, and
  participation fitted WITHOUT contract data.**
- The component model with the same layers is within 0.4% of it, ahead at the valuation season,
  behind from +1 out — still the closest it has been, and still the best on stars (−0.333
  against −0.385).
- The star-bias tension is unresolved and is now the main open question on the anchor.

## What is still missing

- **The survivorship correction** (step three of aging). The aging curve is still fitted only on
  players who played both seasons, so it understates decline. Now that participation exists, the
  inverse-probability weights it needs exist too. This is the next step.
- Goalies. Everything here is skaters.
- The market models, Phase 4.
