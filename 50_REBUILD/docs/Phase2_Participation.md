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
| **aging walk + participation** | **0.5508** | **0.5539** | **0.5311** | **0.5089** | 0.4861 | **0.4392** |
| component model, aging + participation | 0.5490 | 0.5559 | 0.5333 | 0.5116 | 0.4901 | 0.4401 |
| six regressions + participation | 0.5508 | 0.5580 | 0.5382 | 0.5160 | **0.4857** | 0.4502 |

Against the previous leader that is **3.6% better at the valuation season and 23.0% better five
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

## What rests on the contract data, and the risk in that

Dropping the contract export and refitting on everything else:

| seasons ahead | valuation | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| worse without contracts | 5.1% | 6.0% | 8.8% | 11.0% | 12.0% | 12.9% |

Contract state is carrying a large share of the gain, and rightly — a player under contract for
a season is far more likely to play it, and that is knowable in advance.

**But its coverage is not uniform, and the asymmetry runs the wrong way for honest testing.**
The share of players being valued whom the export knows, as of 1 July each year:

| 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022–2025 (sealed) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 11% | 18% | 34% | 64% | 87% | 94% | 99% | 97% |

This is decision D8's finding — the vendor's coverage of earlier years is thin and selected —
showing up in a new place. Two consequences, both stated rather than managed away:

1. **The development pages are the badly-covered ones.** Most of the measured contract gain
   comes from 2019–2021, so the figures above rest on three pages rather than seven.
2. **The confirmatory pages are well covered.** A model leaning on contract state should
   therefore do *better* on the held-back seasons than on the development seasons. That is the
   opposite of the usual direction, and it means a good confirmatory result would be partly a
   data-coverage artifact rather than evidence the model generalises. It has to be reported that
   way when the time comes.

The no-contract variant stays in the register permanently for this reason: it is the floor the
model is worth if the contract feature is judged unusable.

## One bug caught on the way

The first version dated contract state once for a training set drawn from a decade of valuation
seasons, which handed a 2010 row the contract knowledge of 2015 — a look-ahead leak of exactly
the kind the rest of this tree is built to make impossible. The information-set object that
prevents this for season data does not yet cover the contract side, which is how it got through.
Contract state is now dated from each row's own valuation season. Every figure here was measured
after the fix.

## Where it stands

- **New leader: the calibrated total with a three-season window, the additive aging walk, and
  participation.**
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
