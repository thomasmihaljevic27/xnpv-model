# Valuation sensitivity review

Reviewed 2026-09-15. Candidate `5e019ad`, isolated under
`50_REBUILD/output/valuation_review`.

## Verdict

The five published valuation columns, correlations, mean absolute differences, term
framing contrasts, and 22/22 repair checks reproduce using the local production workbook.
The component variant's AttributeError also reproduces.

This is useful evidence about model-generated contract valuations. It does not establish
that calibration is immaterial to the thesis or that three trade categories are validated.
The report changes the membership of its tiers between columns, changes aging alongside
participation, and attributes missing contracts to the wrong stage of the pipeline.

The remaining work can proceed. Correct the interpretation and preserve these limitations;
there is no reason to restart an open-ended forecast tuning exercise on this evidence.

## 1. The top-tier sign reversal compares different contracts

`run_valuation_sensitivity.py:197-211` creates a new tier from each forecast's own
`war_per_season`. All columns contain the same 1,217 contracts overall, but their
top tiers contain 51, 68, 18, 19 and 18 contracts respectively. The single n row in the
report applies only to the candidate.

Holding membership fixed to the candidate's 18 top-tier contracts gives:

| Forecast | Its own top-tier n | Its own top-tier mean surplus ($M) | Same candidate 18 contracts ($M) |
| --- | ---: | ---: | ---: |
| Production forecast | 51 | -0.19 | -3.93 |
| Flat trailing blend | 68 | +1.05 | -4.55 |
| Calibrated + aging + participation | 18 | -1.74 | -1.74 |
| Reported no-participation variant | 19 | -1.68 | -1.64 |
| Candidate | 18 | -1.80 | -1.80 |

The sign reversal disappears for these same contracts. This does not establish that elite
players generally are overpaid. It shows that the reported reversal is not evidence that
the same elite contracts switch from bargains to overpayments when forecasts change.
Different model-defined populations can answer a legitimate descriptive question, but
that question must be distinguished from valuation robustness for a fixed group.

Using candidate-defined tiers throughout, all five models give a negative mean below zero,
positive means in all three middle tiers, and a negative mean for the top tier. Even the
reported 0.5-to-1 sign reversal disappears. These remain development-sample averages,
without uncertainty estimates or a realized trade back-test.

## 2. The participation comparison changes aging as well

The reported pair is `A1AgingParticipationImputedNC` versus `A1Calibrated3Aging`.
The former uses the imputed survivorship adjustment in its aging curve; the latter uses
the default uncorrected aging curve. See `ability_forecast.py:1245-1252` and
`1469-1478`. The pair does not isolate removing participation.

I repeated the comparison retaining the imputed aging configuration and setting the
participation prediction to one. With the candidate's fixed groups and a newly fitted
currency, the top 18 change from -$1.736M to -$1.910M, rather than the report's -$1.74M
to -$1.68M. This diagnostic retains the model's extrapolation rules, which respond to
the changed participation predictions; it is not a claim that every extrapolated rate
remains fixed.

Refitting the price equation is a defensible comparison of complete pipelines, but it
allows the market slope to absorb forecast changes. Holding the baseline currency fixed
by signing quarter gives a top-tier mean of -$1.592M. Other tier means also move:

| Fixed candidate tier | Baseline ($M) | Participation set to one; currency refitted ($M) | Participation set to one; currency held fixed ($M) |
| --- | ---: | ---: | ---: |
| Below 0 | -0.422 | -0.512 | -0.526 |
| 0 to 0.5 | +0.101 | +0.132 | +0.266 |
| 0.5 to 1 | +0.627 | +0.573 | +0.979 |
| 1 to 2 | +1.756 | +1.531 | +2.053 |
| 2+ | -1.736 | -1.910 | -1.592 |

Signs and the order of these fixed-group means survive this additional check. That is
positive evidence for this sample. It does not prove that correcting miscalibration has
no effect on individual values, other populations, uncertainty-sensitive simulation,
or realized trade-category conclusions. Setting everyone to play is not a calibrated
repair, and neither column is adopted.

## 3. The retention rate is real; the explanation is wrong

The development sample has 1,896 contracts; 1,458 receive forecasts; 1,217 receive prices.
Tracing exclusions by unique contract ID gives this complete accounting:

| Outcome | Contracts |
| --- | ---: |
| Priced | 1,217 |
| No matching eligible forecast subject | 423 |
| Fewer than 200 earlier attached development contracts for the price fit | 241 |
| Contract term includes a season before the forecast starts | 15 |
| **Total** | **1,896** |

No remaining development loss is attributable to an unsupported distant horizon in this
run. The attachment path already invokes `predict_beyond_fit`. Even the unrestricted
flat blend loses the same contracts.

Of the 35 excluded six-year deals, 34 are lost at the price-fitting threshold and one
includes a pre-forecast season. Of the 20 excluded eight-year deals, 18 are lost at the
price-fitting threshold and two include pre-forecast seasons. Increasing the forecast's
reach will not restore these contracts.

The logged 842 forecast rejections refer to the full 3,519-contract input, which includes
reserved start cohorts; only 438 belong to the 1,896 development contracts.
Forecasts are attached before the runner restricts the pricing sample to development years.
No reserved-cohort valuation result is scored in this review.

The initial audit used player/start-year keys and counted one excluded second contract as
priced because it shared those keys with a retained deal. The final accounting uses unique
contract IDs, reconciles exactly, and is saved separately in `valuation_attrition.json`.

## 4. Clarify the production comparison and framing claim

The production column imports the live projection and exit-survival calculations through
`ProductionChain`, then prices them with the rebuild's `ProductionCurrency`. It is not
the output of the complete production contract-NPV chain. It therefore does not establish
parity with the production spine, including its other valuation rules.

The adapter also explicitly inherits production's full-panel aging fit. Historical
production forecasts are a current-production benchmark, not a fully rolling
information-clean alternative. The runner's common protocol freezes its price fits;
that does not remove the inherited parameter look-ahead.

The term-in/term-free contrast is large and reproduces. For the same candidate 18
contracts, the production-forecast contrast is $9.70M and the candidate contrast is $9.02M.
The headline $13.58M production contrast uses its different 51-contract top tier.
Report the framing sensitivity directly and specify the population. The ratio to a
range across selected forecast variants is not a general estimate of relative model
uncertainty, and it does not resolve the preferred framing.

## 5. The component failure is confirmed; passing checks are not exhaustive

`A2AgingParticipationImputed.fit(..., before=2015)` raises AttributeError at
`ability_forecast.py:868` because `fitted_horizons_` has not been set by the component
fit before `A2PerHorizonTrust.fit` reads it. This is pre-existing and was independently
reproduced. The 22 repair checks pass despite it, so they do not establish that every
registered variant runs. The variant remains excluded from this comparison and needs a
targeted repair/check before it can be evaluated.

## What the results support

Several fixed-group mean signs and rankings survive the five reported alternatives and
an additional participation comparison. The tested price-framing choice moves top-group
levels substantially. Both are useful development findings.

The report itself correctly states that no realized outcomes or trades are scored.
Maintain that distinction in the conclusion. A reasonable next step is to finish the
planned valuation/back-test work with a declared grouping rule and report robustness on
the same assets. Avoid selecting or excluding thesis categories based only on their
current development-sample signs.

## Reproduction record

Added `50_REBUILD/code/review_valuation_sensitivity.py`, with valuation, checks,
component and attrition modes. The valuation mode runs the actual candidate entry point,
captures attachment results and then performs fixed-group and participation comparisons.
The attrition mode reconciles the cached candidate attachment against the priced output
using contract IDs. All generated records remain ignored.

Logs:
- `50_REBUILD/output/valuation_review.log`
- `50_REBUILD/output/valuation_repair_checks.log`
- `50_REBUILD/output/valuation_component_check.log`
- `50_REBUILD/output/valuation_attrition.log`

Aggregate results:
- `50_REBUILD/output/review_valuation_sensitivity.json`
- `50_REBUILD/output/valuation_attrition.json`

The local canonical workbook and existing production age output were used. Claude's
separate CSV-to-XLSX conversion and its 40-column identity claim were not independently
audited here. No vendor data, model implementation or production output was changed.
No candidate implementation was merged.

