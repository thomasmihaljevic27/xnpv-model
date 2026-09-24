# Player model scorecard: the current model against the rebuilt candidates

Run 2026-09-24 in `50_REBUILD/` (`run_model_scorecard.py` v1.0), with the skater dollar scoring
(`Skater_Dollar_Scoring.md`) and the production reconciliation (`Production_Reconciliation.md`
run log, rebuilt 2026-09-23). Development pages 2015–2021 and development start years only; the
confirmatory pages 2022–2025 are untouched. Nothing is adopted by this document; it is the basis for
the decision of which player model to carry forward.

## What is being compared

| | what it is |
|---|---|
| **Current** | the production skater chain: a 60/40 trailing WAR total carried along the locked aging path (`skater_forward_projection.py`), exit-hazard survival (`exit_hazard.py`, `contract_npv.py`), no separate games forecast. Scored through `production_adapter.ProductionChain`, which imports production's own code rather than reimplementing it. |
| **Candidate A (adopted)** | the rebuilt skater leader: a three-season shrunk ability forecast with hinge and evidence terms, an additive aging walk with the survivorship correction, separate games-share and participation models, participation reading visible contract status (adopted provisionally 2026-09-23); a simulated distribution for every contract. |
| **Candidate B (previous)** | Candidate A without contract data in participation. |

Scope: skaters. The goalie branch is a separate, frozen baseline (`Goalie_Branch_Baseline.md`) that
keeps production's goalie projector for ability, so a goalie choice is not on this card. Draft picks
and prospects are separate, unfinished models and are not part of this rebuild.

**One tilt in the current model's favour:** its aging curve is fitted on the whole panel, including
seasons after some of the pages it is scored on (`production_adapter.py`, "What it inherits"). The
candidates see only what each page could see. The comparison is with production as it is.

## The scorecard

| criterion | Current | Candidate A | Candidate B | reading |
|---|---:|---:|---:|---|
| **Season WAR, squared error (RMSE)** | 0.868 | **0.815** | 0.816 | both candidates better in 2,000 of 2,000 player-resamples; 6.1% lower |
| Season WAR, absolute error | 0.516 | **0.457** | 0.457 | 11.5% lower |
| Season WAR, bias | +0.056 | −0.067 | −0.068 | current over-forecasts on average, candidates under-forecast |
| Better at every horizon? | — | yes | yes | 10.3% lower RMSE at the valuation season, narrowing to 2.4% five seasons out |
| **Chance of playing (Brier)** | 0.231 | **0.133** | 0.134 | current's most confident fifth over-predicts by 25 points (+0.247); candidates' by −0.010 and −0.015 |
| Star tier (3+) bias, valuation season → five out | +0.99 → +0.53 | −0.17 → −0.87 | −0.17 → −0.87 | opposite directions; see below |
| **Contract dollars, squared error** (one line) | $3.548M | **$3.513M** | $3.529M | A lower in 1,237 of 2,000 against current: **not decisive** |
| Contract dollars, absolute error | $1.771M | **$1.675M** | $1.674M | A lower in 1,962 of 2,000; B in 1,961 |
| Contract dollars, bias | **−$0.14M** | −$0.55M | −$0.59M | current is closer on average |
| A contract value as a distribution | none | calibrated in pooled tests | too narrow in the middle | A passes every pooled PIT and coverage test; B's 50% band misses by 5.4 points |
| Information dated at the decision | aging fitted on the full panel; market sample dated by contract start | page / signing dated, rolling fits | same as A | four look-ahead tests pass at exactly zero change for the candidates |
| Uses the vendor contract export in the forecast | no | yes (visible status from 2018; completeness assumed) | no | A's one extra identifying assumption |
| Known open limitation | over-forecasts good players | under-forecasts stars at long horizons | same | both quantified below |

Candidate A against Candidate B directly: season WAR squared error lower in 1,998 of 2,000, Brier in
2,000; contract dollars squared error lower in 1,999 of 2,000 (point) and 1,985 (simulated); absolute
dollar error slightly worse on the simulated mean. The differences are real and small.

## 1. Season forecasts

Harness, 1 July of each development page, zero to five seasons ahead, 40,510 forecasts each.

| model | participation Brier | season WAR RMSE | lower than current | MAE | bias |
|---|---:|---:|---:|---:|---:|
| current | 0.2306 | 0.8683 | — | 0.5160 | +0.0564 |
| Candidate A | 0.1328 | 0.8151 | 2000/2000 | 0.4565 | −0.0666 |
| Candidate B | 0.1340 | 0.8155 | 2000/2000 | 0.4565 | −0.0681 |

RMSE by seasons ahead:

| model | valuation | one | two | three | four | five |
|---|---:|---:|---:|---:|---:|---:|
| current | 0.8759 | 0.8859 | 0.8860 | 0.8832 | 0.8520 | 0.8178 |
| Candidate A | 0.7857 | 0.8230 | 0.8309 | 0.8351 | 0.8140 | 0.7981 |
| Candidate B | 0.7861 | 0.8236 | 0.8314 | 0.8355 | 0.8146 | 0.7983 |

**Where each model misses**, season WAR bias over every forecast by trailing tier (the harness's
60/40 two-season total):

| tier | current, valuation → five out | Candidate A, valuation → five out |
|---|---|---|
| below 0 | −0.32 → −0.05 | −0.00 → −0.04 |
| 0 to 1 | +0.09 → −0.06 | +0.04 → −0.07 |
| 1 to 2 | +0.37 → +0.14 | −0.00 → −0.21 |
| 2 to 3 | +0.45 → +0.40 | −0.23 → −0.37 |
| 3+ | +0.99 → +0.53 | −0.17 → −0.87 |

The current model over-forecasts every tier from one win up at every horizon, most at the top: a
three-win player is forecast about a win too high the season he is valued. The
candidates are close for the lower tiers early and under-forecast the top, increasingly with the
horizon (`Star_Residual.md`, retained as a stated limitation). Through two seasons out the current
model's star bias is the larger in size; from three seasons out the candidates' is.

## 2. Contract dollars

Every model's valuation and the realised production priced on ONE line (the adopted candidate's),
realised target asserted identical across models, 1,176 ended terms, 767 players. The current model
has no simulated distribution and is scored on its point valuation. Shares are player-resamples in
which the candidate's error is lower than the current model's.

| model | valuation | RMSE | MAE | bias | squared error lower than current | absolute lower than current |
|---|---|---:|---:|---:|---:|---:|
| current | point | 3.548 | 1.771 | −0.143 | — | — |
| Candidate A | point | 3.513 | 1.675 | −0.549 | 1237/2000 | 1962/2000 |
| Candidate A | simulated | 3.513 | 1.758 | −0.335 | | |
| Candidate B | point | 3.529 | 1.674 | −0.594 | 1162/2000 | 1961/2000 |
| Candidate B | simulated | 3.526 | 1.743 | −0.406 | | |

On the current model's line (the sensitivity) the pattern repeats: squared error lower in 1,137 (A)
and 1,047 (B) of 2,000, absolute error in 1,969 and 1,973. The two lines give different realised
targets, so their levels are not compared with each other.

- **In dollars, the candidates' forecast advantage mostly survives on absolute error and not on
  squared error.** A contract's dollars are a sum over its term, priced through a line with a floor,
  and a few large misses on long, expensive deals dominate squared error.
- **The current model is less biased on average** because its over-forecast of good players and its
  under-forecast elsewhere partly cancel in dollars; the candidates' under-forecast of stars does not
  cancel.
- This scores the current model's **forecast** on the rebuild's price line. It is not a score of
  production's full chain in its own currency; each chain's own line gives a different realised
  target, and scores against different targets are not comparable.

## 3. How different the full chains' valuations are

Production's own contract NPVs against the rebuild's point surplus on 1,141 contracts both value
(`run_production_reconciliation.py`, adopted candidate, rebuilt 2026-09-23). Mean per contract, $M;
"gap" is the rebuild's surplus minus production's NPV:

| term | contracts | production NPV | gap |
|---|---:|---:|---:|
| 1 year | 551 | +0.30 | −0.39 |
| 2 years | 304 | +0.51 | −0.62 |
| 3 years | 108 | −1.08 | +1.24 |
| 4 years | 66 | −4.49 | +5.13 |
| 5 years | 31 | −9.09 | +8.71 |
| 6 years | 33 | −14.32 | +15.97 |
| 7 years | 26 | −21.23 | +24.80 |
| 8 years | 22 | −28.19 | +33.82 |

Production values long deals as heavily negative; the rebuild does not. Term groups account for 85%
of the squared variation in the gap. The exit hazard alone does not explain it (removing it moves
production's eight-year figure from −28.19 to −25.90). The rebuild prices term as part of what a club
buys (the term-in price line, `Phase4_Decisions.md`, decision A), which is a framing choice as much
as an accuracy one; the reconciliation does not identify how much of the gap is framing and how much
is forecast. Comparability caveats (different valuation dates, 185 contracts where production carries
terminal control value, 46 cost disagreements) are in the reconciliation log.

## What the scorecard does not settle

- **The confirmatory pages.** Everything here is on development pages; 2022–2025 have not been
  scored for any model. The rebuild's lead over the flat benchmark narrowed from 38% on the 2015 page
  to 22% on 2021 (`Phase5_StressTests.md`), so a smaller lead on later pages is expected.
- **The price line and term framing** as a separate decision from the forecast.
- **The star bias** of the candidates and the good-player over-forecast of the current model: both
  are known, quantified, and unrepaired.
- **Goalies, picks and prospects**, outside this card.

## Recommendation

**Carry Candidate A forward as the player model.**

1. **It is the better forecaster by a clear margin**: 6% lower squared error and 11.5% lower absolute
   error on season WAR, better at every horizon, in every resample, and with far better calibrated
   participation. That holds although the current model's aging curve has seen seasons the
   candidates have not.
2. **It dates every input at the decision**, which the current model does not (full-panel aging fit;
   a market sample dated by contract start). For a thesis judged on look-ahead and selection, that is
   the stronger reason.
3. **It gives each contract a calibrated distribution**, which the current model cannot, and which
   the back-test's risk statements need.
4. **Its dollar advantage is modest and honest to state that way:** decisive on absolute error, not
   on squared error, and more negatively biased than the current model on average.
5. **Against Candidate B** it is better on every primary score by small, consistent margins, and its
   contract distribution is calibrated where B's is too narrow; the cost is one extra assumption (the
   vendor snapshot is complete for contracts ending from 2018). B is the natural sensitivity if that
   assumption is challenged.

This is a recommendation; the choice is Thomas's.

## Files

- `50_REBUILD/code/run_model_scorecard.py` v1.0 (new)
- output (ignored): `model_scorecard_run_log.txt`, `model_scorecard_seasons.csv`,
  `model_scorecard_dollars.csv`
