# Does the conclusion move when the forecast does, and how does the live chain compare?

Run 2026-09-16 in `50_REBUILD/`. Experimental. Development start years only; the reserved market
cohorts are refused by the guard. **Nothing adopted, and no production file changed.**

## Why this and not more diagnostics

The forecast has measured errors concentrated on stars and on young players at long horizons, and
three rounds of diagnostics could not separate their causes. That leaves one question worth
asking, and it is not another diagnostic: **does any of it change the answer?**

The thesis does not claim to forecast a player. It claims that certain categories of asset are
systematically mispriced. If that claim holds under every forecast a reasonable person would
accept — including the one the live model uses today — the forecast's errors are a limitation to
state and the argument survives them. If it does not, that is a finding about the thesis.

## What was held fixed and what varied

Fixed: the contracts, the cost side, the signing-dated rolling protocol, the discounting, the cap
path, the development seal. Varied: the forecast, across five, and the term framing.

Each forecast gets **its own price line**, because the currency is fitted on the forecast and a
world with a different forecast has a different price of a forecast win. That makes each column a
complete alternative model rather than one model's forecast priced on another's market. It also
means the **level is not comparable across columns** — the line is fitted to observed contracts,
so the average contract prices near zero surplus in every column by construction. The **gradient**
is comparable, and the gradient is what the thesis rests on.

This is not a back-test. Nothing is scored against a realised outcome and no trade is priced.

## Sample, and a caveat that is part of the result

1,896 contracts eligible on the development cohorts, **1,217 priced (64%)**. A contract is priced
only if the forecast reaches every season of its term, and the early pages do not reach as far as
a long deal needs. The loss is not uniform:

| term | eligible | priced | kept |
|---|---:|---:|---:|
| 1 yr | 885 | 605 | 68% |
| 2 yr | 548 | 324 | 59% |
| 5 yr | 56 | 31 | 55% |
| 6 yr | 68 | 33 | 49% |
| 8 yr | 42 | 22 | 52% |

Long contracts are under-represented by about a quarter relative to short ones, and **long
contracts are where the top tier lives.** Every figure below inherits that.

## The result

Mean surplus, $M over the whole deal, term-in currency, same 1,217 contracts in every column:

| forecast | below 0 | 0 to 0.5 | 0.5 to 1 | 1 to 2 | 2+ |
|---|---:|---:|---:|---:|---:|
| today's live chain | −0.19 | +0.29 | −0.07 | +1.52 | **−0.19** |
| trailing blend, carried flat | −0.31 | +0.25 | +0.21 | +0.75 | **+1.05** |
| calibrated total + aging + participation | −0.42 | +0.11 | +0.60 | +1.76 | **−1.74** |
| calibrated total + aging, no participation | −0.33 | +0.12 | +0.39 | +1.45 | **−1.68** |
| the adopted candidate | −0.41 | +0.10 | +0.56 | +1.66 | **−1.80** |
| **n (adopted candidate)** | 174 | 735 | 199 | 91 | **18** |

### What holds

**Three of the five tiers keep their sign under every forecast**, including the live chain:

- below replacement is **always negative**, −0.19 to −0.42
- 0 to 0.5 wins is **always positive**, +0.10 to +0.29
- 1 to 2 wins is **always positive and the largest robust category**, +0.75 to +1.76

At the level of individual contracts the models agree closely with the live chain: correlation
0.974 to 0.988, the same sign on 88 to 97% of contracts, mean absolute gap $0.24M to $0.47M on
deals worth millions.

### What does not hold

**The top tier flips sign, and the flip is the thesis's headline.** The live chain says −0.19,
the trailing blend says +1.05, the three rebuilt forecasts say −1.7 to −1.8. Range: −1.80 to
+1.05. Whether elite contracts are bargains or overpays depends on which forecast is used.

**It rests on 18 contracts**, after a term-selective loss that removes about half of the long
deals. This is the same conclusion the queue already carries from the currency-shape work —
surplus at the top flipped between a straight and a log price line there — reached independently
down a second road. Two different design choices, each defensible, each reversing the sign of the
headline on a sample this thin.

The 0.5-to-1 tier also flips (−0.07 to +0.60) but the magnitudes are small and the live chain is
the only column below zero.

### What barely matters

**Dropping the participation model changes almost nothing.** The column without it sits at −1.68
against −1.74 with it at the top, −0.33 against −0.42 at the bottom, and correlates 0.977 with
the live chain against 0.974. The participation miscalibration that took up most of the last two
days does **not** move the valuation ordering. That is worth knowing before spending a phase on
it.

### What matters far more than the forecast

**The term framing.** Top-tier surplus, same contracts, same forecasts:

| forecast | term-in | term-free | difference |
|---|---:|---:|---:|
| today's live chain | −0.19 | −13.77 | 13.58 |
| the adopted candidate | −1.80 | −10.82 | 9.02 |

A $9M to $14M swing per contract, against a $2.9M spread across all five forecasts. The decision
about whether the security of a long deal is something the club bought dominates every forecast
choice here, and it is a judgement rather than an estimate.

## What this means for the thesis

**Three of five categories are robust to the forecast, and the live chain agrees with the rebuild
about them.** A back-test result built on the below-replacement, the cheap-regular and the
one-to-two-win categories rests on ground that does not move when the forecast is varied across
everything from the production chain to the adopted candidate.

**The elite category is not identified and should not be cited.** It fails on two independent
axes — the price line's shape and the choice of forecast — on 18 contracts, drawn from a sample
that keeps only half the long deals. The queue already said no back-test result about stars
should be cited until this is settled. This run says the same thing more strongly: it is not a
matter of settling one design choice, because two separate ones each flip it.

**The forecast's calibration errors are not what threatens the conclusion.** The participation
half can be removed entirely and the ordering survives. What threatens the conclusion is thin
data at the top and two framing choices that move it further than any modelling difference does.

## Limits

- Not a back-test, and no realised outcome is scored.
- Each column refits its own currency, so levels are not comparable across columns by
  construction; only the gradient is.
- The 18-contract top tier is the binding constraint on everything said about it.
- Term coverage is selective against long deals, as above.
- The component-model variant is absent because it raises an `AttributeError` inside its own fit
  before any contract is priced. That is a defect in a registered candidate, found here and
  recorded rather than repaired in a runner about something else.

## Files

    50_REBUILD/code/run_valuation_sensitivity.py

Outputs, ignored under `50_REBUILD/output/`: `valuation_sensitivity_run_log.txt`,
`valuation_sensitivity.csv`.
