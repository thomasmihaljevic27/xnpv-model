# Third repair verification

Reviewed 2026-09-15 at `54b6253`, branch `claude/loving-maxwell-rd3w5v`.
Updates the preceding assessment in `Latest_Repair_Verification_Codex.md`.
Candidate code was run in an isolated checkout and was not merged into main.

## Assessment

The remaining extrapolation and long-term request defects are closed on the tested cases.
The named-player runner now uses dated market fits, the production forecast adapter, known-at-
signing cap paths and discounting. However, it fits a different price equation for each forecast
while claiming to hold the equation fixed. Its dollar comparison still cannot support the
interpretation printed above the table. A smaller failure remains in empty attachment results.

All 15 repair checks passed with zero skips. This closes more of the repair work but does not
complete the Fable plan. The simulation, trade-date update and valuation validation remain
substantial unfinished work, acknowledged in Claude's own report.

## Findings

### 1. P1: the named-player columns do not share the claimed price equation

`run_player_comparison.py:136-149` loops over the rebuilt and live forecast tables and fits
`ProductionCurrency` separately on each table for each quarter. These tables contain different
forecast regressors. Calling the same class with the same term mode does not hold its estimated
coefficients fixed. Nevertheless, lines 195-198 tell the reader the difference is the forecast
rather than the price line. The repair report repeats that claim.

I ran the actual named-player entry point with wrappers that recorded its fitted coefficients
and valuation calls without changing them. All **18 quarters** with both fits have different
coefficient vectors. The largest absolute coefficient difference is **0.0117093** in the
model's cap-share regression units.

Then I held each live forecast, contract and valuation date fixed and repriced it using the
rebuilt equation for the same quarter. Across the **12 displayed named contracts**, the live
column changes by **$8,259,504 on average in absolute terms**, and by as much as **$19,194,961**.
These measure the effect of changing the pricing equation, not an error against a known true
player value. The original run prices 12 cases and lists 20 omissions.

Required repair: for each quarter, fit one declared reference currency once, then apply that
same fitted object to both forecast tables on matched contracts. Add a test that verifies the
coefficients are identical across the two valuation calls. If a separately refitted currency is
also useful, report it as a distinct whole-model sensitivity; it cannot isolate the forecast
change. The existing 15 checks do not execute or verify this comparison.

### 2. P2: an all-rejected attachment batch crashes before publishing its reasons

`contract_price_model.py:183` creates `pd.DataFrame(out).set_index("idx")` before publishing
the rejection records at lines 185-191. When every requested contract is rejected, `out` is
empty and has no `idx` column. The result is:

    KeyError: "None of ['idx'] are in the columns"

Executed with a single contract for a subject absent from the eligible population and a
deterministic model that answers every requested eligible subject/year. This is an ordinary
no-history outcome. The caller gets neither an empty result nor the newly promised rejection
report. The same construction also cannot return an empty input cleanly.

Build the empty output with its expected schema and publish rejection information before
joining. Verify all-rejected and empty requests, as well as the existing successful long-term
case. Early batch skips also need explicit reasons if the interface promises an accounting of
every submitted contract. This finding concerns failure handling; it does not invalidate the
successful named-player run or the forecast headline.

## Repairs verified

- All **15 checks passed**, with **98.346% season-row age coverage** and production inputs
  present. The production adapter still agrees with the production rate and survival methods
  across 5,196 rows; the 663-row cap-target perturbation test and actual discounted-cost test
  still pass.
- Independent requests `[4,5,6]`, `[3,4,6]`, subject subsets and reversed row ordering produce
  identical horizon-six WAR. Requesting `[6]` alone succeeds. The final fitted endpoint is now
  computed internally.
- The complete-forecast stub retains both the two-year and ten-year contracts. The upstream
  horizon-eight request ceiling is removed.
- The actual named-player runner completes. It uses the live production forecast, filters to
  development start cohorts, fits only before each signing quarter, and calls the shared cap
  and discount APIs. The whole-sample pricing and flat-comparator paths are removed from its
  executable calculation, although its opening docstring still describes the old method.

## How close is the rebuild to finished?

The narrow review of the existing forecast candidate is much closer to closure. The remaining
material issue in this pass is the named-player currency comparison, plus attachment failure
handling. This pass changes no fitted forecast specification or underlying production methods,
so I did not repeat the development leaderboard reproduced in the preceding review.

Completion against `Player_Model_Rebuild_Plan_Fable.md` remains a different acceptance test:

| Work | Status |
|---|---|
| Forecast comparator, rate/game units, participation event and query repairs | Tested repairs now pass |
| Named-player dollar comparison | Runs, but mixes forecast and price-equation changes |
| Predictive distributions and 80% interval coverage | Still incomplete |
| Subgroup results by horizon and full-chain/input-perturbation tests | Still incomplete |
| A3 in-season trade-date forecast update | Still unbuilt |
| Joint career-path simulation and zero-uncertainty identity | Still unbuilt |
| Control-year and goalie tender treatment | Still incomplete |
| Contract-by-contract dollar reconciliation and development dollar scoring | Still incomplete |
| Market holdout policy and final confirmatory run | Unresolved/not completed |

The plan also requires the missing announced later cap ceilings. The forecast improvement
verified in the previous pass is useful evidence; it cannot substitute for these remaining
valuation requirements. I would close the two concrete findings, then make the next milestone
the missing end-to-end valuation work with explicit acceptance checks.

## Reproduction and limits

Executed the candidate's `repair_checks.main()`, the existing `review_latest_pass.py` against
this checkout, and the new `review_named_currency.py --candidate-root <checkout>`. The new
script captures the real runner's pricing calls, restores the wrapped methods, and then
recalculates only the comparison needed to isolate the currency effect. It also reproduces
the all-rejected failure. No model source files were patched during execution.

Aggregate logs and JSON are ignored under `50_REBUILD/output/`, including
`current_repair_checks.log`, `current_independent.log`, and `current_named_review.json`.
No reserved evaluation was unsealed, no production outputs were rewritten, and no vendor rows
were committed. No full NPV correctness, final model adoption or complete plan validation is
claimed.
