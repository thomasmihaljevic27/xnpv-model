# Valuation review closure

Verified 2026-09-16. Candidate: `e14e873`, tested in isolated checkout
`50_REBUILD/output/valuation_repair_review`.

## Decision

Ready to close this diagnostic/review stage and continue the remaining rebuild work.
The valuation comparison corrections are implemented and reproduce. No new blocking
defect was found in the revised comparison on the tested data.

This is approval to proceed with development, not a declaration that the complete model
is validated or ready for final thesis conclusions. Candidate implementation remains unmerged
into the local main branch.

## Verification

Ran the revised `run_valuation_sensitivity.py` from source with the local workbook,
existing production age output and merged birthdates. Independently checked the generated
CSV against the previous independent valuation audit.

- Every column contains the same 1,217 unique contract IDs.
- Every contract has the same fixed group and cost across columns.
- Fixed group counts are 174, 735, 199, 91 and 18, from lowest to highest forecast tier.
- All five sets of group means reproduce the prior independent audit within 1e-8 million
  dollars. Every group retains its sign; group-average ordering is identical.
- Top-group means are -$3.933583M (production forecast), -$4.552236M (flat blend),
  -$1.736439M (baseline), -$1.909668M (participation alternative) and -$1.804376M (candidate).
- The held-currency participation result reproduces -$1.592M at the top.
- Retention reproduces: 1,896 eligible, 438 lost at attachment, 241 lost at price fitting,
  and 1,217 priced.
- Fixed-top-group term contrasts range from $8.765077M to $9.701655M.
- The report now distinguishes production's forecast repriced in the rebuild from the
  complete production NPV chain and acknowledges the inherited full-panel aging fit.

The runner uses the same aging configuration for the participation alternative.
As in the preceding independent audit, the model's extrapolation rules can respond to
the changed participation predictions; this is not a claim that every other extrapolated
quantity is numerically fixed.

No forecast or currency implementation changed between the reviewed valuation candidates.
The 22-check suite passed in the preceding review of `5e019ad`; it was not rerun here.
This pass targeted the changed runner, its output and the revised claims.

## Scope of the result

The agreement concerns signs and rankings of group-average model valuations. Individual
contract rankings need not be identical. The grouping was fixed for this corrected
development comparison; it was not independently preregistered before the earlier results
were inspected.

The report's withdrawals appropriately narrow the interpretation. This is a robustness
check on one development sample, not a realized-outcome back-test or evidence of systematic
trade mispricing. Uncertain magnitudes, the small top group, subgroup miscalibration and
selective coverage remain stated limitations.

## Next work

1. Close the repeated coverage/valuation diagnostic review. Keep the limitations on record.
2. Repair the known component variant's missing `fitted_horizons_` initialization and
   verify that variant before including it in further comparisons.
3. Continue the planned joint simulation, remaining valuation integration and reconciliation,
   and back-test work. Declare the category rule and evaluation protocol before the next
   substantive evaluation; keep the final reserved evaluation sealed until choices are fixed.
4. Evaluate all predefined categories and report sensitivity, rather than selecting categories
   according to their development-sample signs.

No new forecast tuning cycle is required by the results of this closure check.

## Evidence

Ignored local logs:

- `50_REBUILD/output/valuation_repair_review.log`: full revised runner.
- `50_REBUILD/output/valuation_repair_independent_check.log`: contract identity, group,
  cost, mean reproduction, sign and ordering assertions.

Preceding evidence and methods:
[Valuation sensitivity review](Valuation_Sensitivity_Review_Codex.md).

No production code or vendor records changed. No candidate implementation was merged and
no reserved-cohort valuation result was scored.

