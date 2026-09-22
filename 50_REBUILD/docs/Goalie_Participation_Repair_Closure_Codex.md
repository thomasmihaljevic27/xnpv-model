# Goalie participation repair review closed

Reviewed 2026-09-22. Candidate `8d1efc6`, tested in an isolated worktree.

## Decision

Close the preceding goalie participation review. The signing-date error, incomplete
checks and unsupported bias claim are repaired. Corrected goalie results reproduce
in the independent environment. Proceed to the goalie rate forecast as a development
experiment. Pricing remains provisional; this is not adoption or D7 closure.

The skater contract-data choice remains a separate open decision. Keep the current
leader until a matched comparison changes only contract information in that leader's
own configuration and measures downstream dollars.

## What reproduced

| Result | Independent run |
| --- | ---: |
| Full review suite | 35 passed, 0 skipped, 0 failed |
| Goalie participation Brier, baseline / model | 0.2470 / 0.2056 |
| Season-WAR mean absolute error, baseline / participation model | 1.488 / 1.432 |
| Conditional share error, trailing / model | 0.1801 / 0.1686 |
| Price error, no goalie terms | 0.010000 |
| Price error, goalie level only | 0.007017 |
| Price error, goalie level and slope | 0.007153 |
| Extra slope beats level-only | 22% of career resamples |
| UFA whole-path goalie/skater annual price response ratio | 0.79 |

Price errors compare the same 174 contracts across 102 goalies. Minor last-digit
optimizer differences remain in dollar responses and the no-terms error; the
material discrepancy in the participation forecast is resolved. The participation
and season-WAR improvements win in 100% of the runner's career resamples.

## Repairs verified

### Contract status is read at signing

The price consumer now supplies one actual signing date per contract to
`ParticipationModel.predict`. The fitted model still uses historical training-row
dates. Vectorized prediction preserves duplicate player keys with different dates;
reversing a batch reverses its results exactly. Adding a future contract leaves the
real price consumer's fitted and predicted participation unchanged.

Gillies's 2018 deal reproduces: first-season probability 0.4443 at July 1 versus
0.9272 at signing; second season 0.4117 versus 0.9950. The current runner finds
95 of 205 contracts changing in their first or second season between July and
signing-date status. Both sides use the same repaired fit. Thus 95 is a date-only
comparison under the new fit, not a combined refit-and-date intervention. The
previous 92 count used the old fit and checked the entire contract horizon. Those
counts should not be described as identical measurements.

Calibration figures also reproduce: first-season prediction 0.822 versus 0.761
observed on 205 contracts; second-season 0.797 versus 0.794 on 107. These are
aggregate frequencies, not proof of calibration within subgroups. The first-season
gap is openly retained. Forecast changes versus flat participation average +0.111
WAR, 0.223 in absolute terms, with maximum absolute change 1.235.

### The rank check resolves the duplicated-column problem

I instrumented every executed goalie logistic fit: all 32 optimizer inputs have
full column rank, and all report convergence. Three page/horizon fits drop
`contract_unknown`. Independent skater inspection finds fifteen affected fits with
contract data and no rank drops without it. This matches the reported exposure.

The prior singular fits were not guaranteed to fail: they could return different
coefficient splits or fall back to fewer inputs. The rank repair makes the current
reported forecasts reproduce across the two reviewed environments. This supports
the explanation; it does not prove universal cross-platform bit equality.

One modeling qualification remains: dropping `contract_unknown` is an explicit
restriction on predictions. Where training has only unknown-status players and
known under-contract players, it cannot separately identify a known-but-expired
category. Omitting the unknown flag makes that absent category share the baseline
of players without known coverage, holding other predictors fixed. Record that
choice as an extrapolation assumption, rather than implying full rank creates
information that the training data lacks. This does not block the prototype.

### The guards catch the repaired defects

Check 34 now compares participation fits with future rows present, absent and
scrambled, and exercises predictions and the signing-date consumer. The share
model's refusal of future rows is tested directly. Check 35 tests the rank rule.

Independent mutations all fail as intended: constant 99.9% participation, ignored
prediction date, and disabled rank repair. Additional audit checks confirm ordered
per-row dates, future-contract invariance and full-rank optimizer inputs.

### The bias claim is corrected

The report now says participation improves accuracy without eliminating pooled
WAR bias, whose causes remain unresolved. It no longer treats better average
participation as proof that residual bias originates elsewhere.

## The skater finding and the decision it supports

The original ablation runner and an independent implementation of its whole-career
bootstrap give the same displayed corrected results:

| Horizon | WAR error change from adding contracts after repair |
| --- | ---: |
| 1 | +0.08% [-0.05%, +0.21%] |
| 2 | +0.27% [+0.13%, +0.42%] |
| 3 | +0.06% [-0.09%, +0.22%] |
| 4 | +0.12% [-0.01%, +0.25%] |
| 5 | +0.03% [-0.06%, +0.12%] |

Positive means larger mean absolute WAR error. Participation Brier improves from
0.1340 without contracts to 0.1326 with contracts. The old uncorrected version is
still machine-sensitive: my h4 deterioration is 1.36%, rather than the reported
upper range of 0.98%. Its unreliability is precisely why that comparison is retired.
The corrected results agree.

The broad claim that contract data hurts is properly withdrawn. There is a small
tradeoff across metrics, not a demonstrated winner on every outcome. Also,
`run_contract_ablation.py` compares `A1AgingParticipation` and its no-contract
counterpart. The current downstream leader is `A1HingeExposure`, with additional
performance/aging choices. Do not replace it based on a different configuration's
comparison. Its no-contract participation path is unaffected by the redundant
contract-column repair. Retain it while evaluating an otherwise identical
with-contract challenger and subsequent valuation effects on development data.

## Evidence and scope

Audit: `50_REBUILD/code/review_goalie_participation_repairs.py`. It includes full
runner, suite, price and ablation modes, independent date/mutation/design checks,
and an equivalent career bootstrap based on grouped error sums. Both bootstrap
implementations completed and their displayed results match. Generated evidence
uses `goalie_participation_repair_` under `50_REBUILD/output/` and remains ignored.

No candidate merge, implementation edits, source writes, canonical production
writes or model adoption. Earlier closures stand. Goalies' rate and joint path
models, control years and downstream scoring remain development work.
