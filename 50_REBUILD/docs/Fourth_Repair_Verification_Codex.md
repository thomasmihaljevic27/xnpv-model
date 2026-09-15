# Fourth repair verification

Reviewed 2026-09-15 at `4b9723a` on `claude/loving-maxwell-rd3w5v`.
Supersedes the two outstanding findings in `Third_Repair_Verification_Codex.md`.

## Result

Both findings from the preceding pass are closed on the tested paths. All **17 repair checks
passed with zero skips**, using merged birthdates and production inputs. The independent
named-player audit also passed across the full development comparison. I found no new blocking
defect in the changed calculation paths.

This closes the current repair findings. It does not establish completion of the Fable rebuild
plan, full contract NPV correctness, or final model adoption.

## Shared price equation: verified

`run_player_comparison.price_on_one_currency()` now fits once per signing quarter on the rebuilt
forecast table, the explicitly declared reference. It applies that same fitted currency to
both forecast tables. The executable named-player entry point calls this helper.

Ran the actual entry point with the existing independent `review_named_currency.py` audit.
Its wrappers recorded the coefficient vectors actually used in valuation calls without changing
the calculation. Across **18 comparable quarters**, the two columns now have **zero coefficient
differences**. Holding the live forecasts fixed and repricing them on the rebuilt equation
changes all **12 displayed named values by exactly zero**. The preceding commit differed in
all 18 quarters, with a maximum named-value difference of $19.19M under that same audit.

The runner completes and lists the 20 omitted named cases. This validates the shared-equation
comparison, not the economic accuracy of the estimated currency or the completeness of contract
NPV. The live forecast is being priced on the rebuilt reference equation; it is not production's
own contract-dollar result.

## Empty and rejected batches: verified

Attachment now constructs an empty output with the required schema instead of inferring columns
from an empty list. The independent missing-subject reproduction returns **zero forecast rows
and one rejection record**. It no longer raises the missing-`idx` error. The new candidate check
also exercises an empty input and an all-rejected model response; both return cleanly.

The in-memory rejection record is available before the join. The CSV is still written only
when there are rejections, and early batch skips are not comprehensively recorded. Consequently,
the CSV alone should not be treated as a complete per-run sample reconciliation. This is a
remaining reporting limitation, not a recurrence of the repaired crash.

## Testing scope

Executed in isolated checkout `50_REBUILD/output/repair_review_fourth`:

- Candidate `repair_checks.main()`: **17 passed, 0 skipped, 0 failed**.
- Independent `review_named_currency.py --candidate-root <checkout>`: full named-player run,
  actual coefficient capture across 18 quarters, repricing of 12 displayed contracts, and the
  missing-subject rejection reproduction.

The suite also rechecks the earlier unit, participation, prediction-grid, horizon, production
anchor, timing and extrapolation repairs. No fitted forecast specification changed in this
pass, so the development leaderboard already reproduced in the second verification was not
rerun. No reserved evaluation was unsealed and no candidate implementation was merged.

Aggregate evidence remains ignored under `50_REBUILD/output/`: `fourth_repair_checks.log`,
`fourth_named_review.log`, and the audit's `current_named_review.json`, which identifies this
checkout. No new test implementation was needed; the prior independent audit reproduces the
failure on `54b6253` and its closure on `4b9723a`.

## Next acceptance milestone

The next milestone should be end-to-end valuation validation and completion of the remaining
plan work: predictive distributions and interval coverage; subgroup reporting by horizon;
full-chain leakage and input-perturbation tests; A3 trade-date updates; joint simulation and its
zero-uncertainty identity; control-year and goalie treatment; announced cap inputs;
contract-by-contract dollar reconciliation; and a resolved market holdout policy before final
confirmation. Claude's report continues to acknowledge these gaps.

The present repairs are ready to move out of repeated defect review. The full rebuild still
needs those implementation and acceptance results before it can be called finished.
