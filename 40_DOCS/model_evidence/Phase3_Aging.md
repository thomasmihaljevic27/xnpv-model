# Aging, step one: the curve, and why its result is provisional

Run 2026-09-15 in `50_REBUILD/`. Experimental. No production file changed, no locked decision
opened. Development seasons 2015–2021 only; the held-back seasons are untouched.

Step one of three. The survivorship correction needs participation probabilities, so the order
agreed was: uncorrected curve first, then participation, then the correction — the only order
in which a moving answer says which change moved it.

## What the curve is

The expected **change** in a player's WAR per 82 over the next season, as a smooth function of
age, fitted on within-player consecutive-season changes, refitted at each decision date,
weighted by the smaller of the two seasons' games, by position, with a level term. A projection
walks it forward a year at a time.

Two deliberate departures from `20_CODE/aging_curve.py`:

**A difference, not a ratio.** The production chain multiplies a raw trailing WAR total by an
aging ratio, which needs four guards — a floor on the base, a cap on the ratio, a floor on the
ratio, a flat fallback — because a ratio applied to a number near or below zero is meaningless.
Under a straight-line price on wins a difference is exactly right and **all four guards
disappear** rather than being retuned.

**No mean reversion inside it.** The production curve pulls a player 45% toward a comparables
norm (`LAMBDA = 0.55`) before aging is applied, inside the thing called the aging curve. The
rebuilt forecast already does that job by a fitted amount. Running both would shrink every
player twice, once visibly and once hidden inside "aging".

## The level term was 89% measurement error

The plan asks for a level-by-age term because better players decline faster *in wins*. Fitted
the obvious way it produced a 3-win 27-year-old losing **0.8 wins a year**, which is not a
finding about hockey.

The change from season *t* to *t+1* is (rate at *t+1*) minus (rate at *t*). Regress it on the
rate at *t* and the same noise sits on both sides — positively in the regressor, negatively in
the outcome — so the coefficient collects regression to the mean and reports it as aging.
Measured on the panel rather than argued about:

| level regressor | correlation with the yearly change |
|---|---:|
| the season the change starts from | **−0.447** |
| one season earlier | **−0.052** |

**The fix is the lagged level**, whose noise is independent of the change by construction. What
survives is small and plausible:

| age | 0.5-win player | 1.5-win | 3.0-win |
|---:|---:|---:|---:|
| 20 | +0.26 | +0.29 | +0.32 |
| 23 | +0.07 | +0.07 | +0.07 |
| 26 | −0.04 | −0.06 | −0.09 |
| 29 | −0.10 | −0.14 | −0.20 |
| 32 | −0.15 | −0.21 | −0.30 |
| 35 | −0.23 | −0.31 | −0.43 |
| 38 | −0.38 | −0.49 | −0.64 |

Gains through about 24, crossing over near 25, decline steepening after 30. The "more to lose"
effect is real — a 3-win player at 35 declines nearly twice as fast as a 0.5-win player — it was
just buried under arithmetic.

The naive version is kept as a registered candidate rather than deleted, so its cost appears in
forecast error and not only in a correlation. It costs a great deal — measured on identical
rows, paired, clustered by career:

| seasons ahead | valuation | +1 | +2 | +3 | +4 | +5 |
|---|---:|---:|---:|---:|---:|---:|
| naive curve, worse by | 0.0% | 5.5% | 11.3% | 11.7% | 7.8% | 6.1% |

The two are identical at the valuation season by construction — the curve only starts mattering
once you walk forward. Its star bias is **−0.859** against **−0.344** for the lagged fit, the
worst of any calibrated model in the register. An identification error that would have been
invisible in a coefficient table costs up to a ninth of the forecast.

## The structural change, and what it costs today

Until now every model reached each future season through **six independent regressions** — a
reduced form that can imitate aging but never states one, cannot be audited as one, and cannot
be walked forward a year at a time. Phase 5's simulation needs exactly that walk, because a
career path is drawn step by step.

The aging variants replace it: map the anchor to the valuation season once, then walk that level
forward on the explicit curve. Against the six free regressions it replaces:

| seasons ahead | aging walk vs reduced form | verdict |
|---|---:|---|
| valuation | +0.00% | identical by construction |
| +1 | −0.76% | aging walk better |
| +2 | −0.00% | tie |
| +3 | +2.40% | reduced form better |
| +4 | +7.27% | reduced form better |
| +5 | +3.29% | reduced form better |

**Read on its own that says the structure costs accuracy at long horizons. That reading is
wrong, and the diagnosis says why.**

## Why the long-horizon loss is not the curve's fault

What the two models predict for players aged 31 and over:

| seasons ahead | reduced form | aging walk | actual | share who played |
|---|---:|---:|---:|---:|
| valuation | +0.24 | +0.24 | +0.27 | 57% |
| +1 | +0.15 | +0.09 | +0.20 | 41% |
| +2 | +0.14 | −0.06 | +0.13 | 29% |
| +3 | +0.08 | −0.25 | +0.11 | 20% |
| +4 | −0.02 | −0.51 | +0.08 | 13% |
| +5 | +0.10 | −0.54 | +0.05 | **8%** |

At five seasons out, among players 34 and over, **the walk predicts below zero for 99% of them
and 98% of them did not play at all.**

The walk is answering the wrong question. It says "this 39-year-old will be half a win below
replacement"; the truth is he is not in the league. Because participation is still a placeholder
that has everyone playing forever, that deep-negative number is taken at face value and scored
against an outcome that is almost always a zero.

The reduced form is not modelling retirement either. It wins here **by accident**: fitting a
separate regression at each horizon lets it shrink toward a number that happens to sit near the
mostly-zero observed mean, which looks like accuracy and is not a statement about anything.

So the honest summary is that **the explicit aging curve is currently being scored without the
layer it was designed to sit on top of.** Its long-horizon deficit is a participation deficit.

## One bug worth recording

The first aging walk returned no prediction at all for the 0.6% of rows with no birthdate — an
aging curve cannot age a player whose age is unknown. Every mean taken downstream silently
skipped those rows, so the aging variants were scored on 210 fewer rows than their rivals and
the paired comparison returned nothing.

**The harness should have caught that and did not.** It now refuses any model that returns a
missing forecast, with the reason stated: a model that declines to predict the players it finds
hard is scored on an easier sample than its rivals and wins by forfeit. The walk now carries a
level flat where the age is unknown, which is the status quo before the curve existed, rather
than guessing an age.

## Where this leaves the standing

- **Leader on raw forecast accuracy remains the calibrated total on a three-season window**,
  without the explicit aging walk.
- The aging walk is better one season out, level at two, behind at three to five — and that
  deficit is diagnosed, not mysterious.
- On the star problem the aging walk is **better**: −0.344 against −0.370 for the same model
  without it, and the component model with aging is the best of any calibrated variant.
- **The result is provisional and should not be used to choose an anchor.** Participation comes
  next, and the prediction this document commits to in advance is that it closes most of the
  long-horizon gap, because it is the missing term the diagnosis identifies.

## Next

1. **Participation** (Phase 2): played, absent but returned, gone. Then rerun everything above.
2. **The survivorship correction** (step three of aging): the curve is fitted only on players
   who played both seasons, so it understates decline. Inverse-probability weighting against an
   imputation challenger, both scored on the harness.
3. Only then is the anchor question worth reopening.
