# Contract-status adoption review

Reviewed 2026-09-23. Candidate `7fee59b`, tested in an isolated checkout.

## Decision

The provisional model and its signing-date simulation caller are connected
correctly. The downstream adoption is not complete: the integrated valuation
table cannot be rebuilt from the candidate's own freshly regenerated artifacts.
Keep the provisional status-only model while repairing that connection and the
missing-history diagnostic. The earlier signing-date closure remains closed.

For the long-contract cliff, carry the last supported status effect forward as
a separately named, scored sensitivity before changing the baseline. The
current point-score win does not establish that the cliff is a good forecast;
it also does not establish that smoothing it will improve the result.

## 1. The valuation comparison still calls the old model adopted

`run_valuation_sensitivity.py:106` maps `the adopted candidate` to
`A1HingeExposure`. The simulator now uses `A1HingeExposureStatus`. The comparison
also groups contracts using that stale adopted column.

I regenerated both `valuation_sensitivity.csv` and `npv_simulation.csv` with this
checkout, then ran `run_valuation_integration.py`. Its existing consistency guard
fails:

> The two artifacts disagree about the adopted point surplus by up to
> $1,060,704.07 on 948 contracts; they are not from the same run.

These are fresh artifacts. Re-running the unchanged sensitivity script does not
fix the model mismatch. Therefore, "every downstream runner imports the leader"
and "everything downstream was rerun" are too broad. This consumer is part of
the valuation chain, not just an old diagnostic. Production reconciliation reads
the integrated artifact and inherits its stale state if the file is left in place.

Use the shared adopted model in the comparison, retain the old leader as an
explicit sensitivity, and rerun comparison, integration, and reconciliation.
Declare whether category membership stays frozen at the previous grouping or is
rebuilt from the new baseline. Do not silently treat different memberships as
the same category comparison. Require the integration consistency guard to pass.

## 2. The stated clipping effect includes simulation noise

The 15 affected contracts reproduce. The reported average discrepancy of 0.014
WAR per season comes from comparing 2,000 simulated paths with the point forecast.
That difference includes random participation and performance draws. It does not
isolate the effect of clipping a transition probability.

The transition routine supplies an exact calculation. Starting at the first
forecast probability, propagate the actual chain using its clipped exit rate:

    actual[h] = actual[h-1] * (1 - exit[h])
                + (1 - actual[h-1]) * return_rate

Multiply the probability discrepancy by conditional production and average over
each contract. On the same 15 contracts:

| Quantity | Mean absolute difference, WAR/season | Largest absolute difference |
| --- | ---: | ---: |
| Exact expected effect of clipping | 0.000415 | 0.000937 |
| Simulation-minus-point difference | 0.014198 | 0.030939 |

The exact signed average is -0.000290 WAR/season. Report this separately from
Monte Carlo variation. These are production effects, not a dollar decomposition
through the valuation floor.

The cliff and clipping are also distinct. Contract 6500 falls from participation
0.9250 to 0.4493 at the last season; an earlier rise clips, with a maximum
probability discrepancy of 0.002224. Contract 6587 falls from 0.8793 to 0.3228
without any clipping. A sharp fall can be represented by the chain; a rise faster
than its allowed return rate cannot. Smoothing the fall is not automatically a
repair for the clipped rises.

## 3. The deferred diagnostic fails on missing history

I ran `run_leakage_tests.py` with its leader replaced by the adopted class.
All four leakage checks pass: the three future-data checks have exactly zero
change on all seven development pages, and the shuffled-player placebo worsens
error at each horizon.

The script then crashes in its fifth section, input sensitivity. Removing the
last season while retaining the original subject list creates an anchor with
missing `t0`. `participation_model.py:262` attempts `int(NaN)` when constructing
the date. It raises `ValueError: cannot convert float NaN to integer` before
the runner can report its unanswered subjects.

A separate 2015-page probe reproduces this with both `A1HingeExposure` and
`A1HingeExposureStatus`. It is a pre-existing missing-history defect, not evidence
that the newly adopted model leaks. Restore explicit missing-anchor handling and
run the complete diagnostic to its end, keeping the requested subjects and
unanswered counts visible. Add this case to the checks. Updating and running
the adopted model's verification does not require another user decision.

## Verification completed

- Full repair suite: **43 passed, 0 skipped, 0 failed**.
- Check 43 compares eight contracts through both real callers. Forcing only the
  simulator back to July dating makes it fail on contract 7041.
- Full NPV simulation: **1,217 contracts**, mean point surplus **$0.23M**, mean
  simulated surplus **$0.43M**, **226** point-versus-simulation sign changes, and
  **15** clipped terms. The 300-contract zero-spread identity passes, with maximum
  difference **$1.49e-08** in this environment.
- Fresh valuation-sensitivity run completed; fresh integration failed as above.
- Exact marginal recursion evaluated on all 15 clipped terms. A separate 2021
  page audit reproduces the eight-year cliff.
- The adopted model's four leakage checks pass, with the later sensitivity
  section failure reported separately.
- Changing future-signed vendor contracts through the new simulator caller
  leaves Chara's conditional mean, scale, participation, and residual shape
  exactly unchanged after refitting.

The zero-spread test sets participation to one; it does not verify the actual
participation chain. Check 43 verifies inputs supplied to the chain. Neither
proves that clipped paths preserve the requested marginals.

This review did not independently rerun the skater control-year valuation or the
two goalie downstream reports. Their reported means are not certified by this
review. The old and new own-currency means are descriptive movements; the fixed
currency point-score comparison remains the adoption evidence. A matched
simulation-score comparison is still outstanding.

## Artifacts and next step

The reproduction helper is `50_REBUILD/code/review_status_adoption.py`; evidence
is ignored under `50_REBUILD/output`. Repair the shared leader reference, rebuild
the integration and reconciliation, restore the missing-history check, and score
the named cliff sensitivity. Then return to the star-residual work. No new model,
default, or sensitivity was adopted by this review; no candidate merge, vendor
write, or canonical production-output write was made.
