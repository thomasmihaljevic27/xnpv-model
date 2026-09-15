# Verification of Claude's second repair pass

Reviewed 2026-09-15 at commit `0e70d4b` on `claude/loving-maxwell-rd3w5v`.
This updates the assessment of `d651998` in `Repair_Verification_Codex.md`.
The implementation was tested in an isolated checkout and remains separate from main.

## Assessment

The production anchor and negative-anchor repairs work. The revised development headline
reproduces. Signing-date cap normalization and the annual discount origin also pass independent
checks. These findings close the four P1 defects in the preceding verification on the tested
paths. They do not establish contract-dollar correctness or completion of the rebuild plan.

Three implementation issues remain below. The repair report's statement that all six prior
findings are repaired is too broad. Fourteen passing checks are useful evidence, but the suite
still misses variations of the interfaces it claims to cover.

## Remaining findings

### 1. P1: the named-player dollar comparison still uses the withdrawn valuation method

`run_player_comparison.py:127-135,179-241` still fits its log currency on the whole contract
sample, including signings after the illustrated valuation dates. Its comparator is
`A0Production`, the flat benchmark, and its dollar loops use realized ceilings without
discounting. It does not call `ProductionChain` or the repaired `ProductionCurrency`.
The output continues to label this comparator TODAY and describe it as today's chain.

The latest change repairs the horizon guard only. Making the runner reach its dollar calculation
does not make that calculation a valid historical production comparison. Route it through the
repaired APIs with dated training data, or withdraw the dollar illustration until that work is
done. This is established by source inspection; I did not execute the full-sample fit or inspect
reserved cohorts to demonstrate an already-visible timing violation.

### 2. P2: extrapolation remains dependent on the requested endpoint

`ability_forecast.py:162-170` now measures decay on a fixed population, which repairs subject
batching. However, it still applies that decay to `max(inside)`, the last fitted horizon the
caller requested, rather than the last horizon the model fitted.

On the 2021 page, with the model's exposed fitted range restricted to 0-5 to exercise its tail:

- `[4,5,6]` versus `[3,5,6]`: identical horizon-six forecasts, as Claude's check 13 reports.
- `[4,5,6]` versus `[3,4,6]`: maximum difference **0.504879883 WAR** at horizon six.
- A player alone versus in the population, and reversed subject ordering: zero difference.
- `[6]` alone raises an error, despite a fitted model capable of deriving its year-six tail.

Check 13 keeps horizon five in both requests, so it cannot catch the remaining endpoint error.
Always obtain the player's final fitted forecast internally, extrapolate from that fixed
endpoint, and return only the requested rows. The test should vary the endpoint and request an
extrapolated year alone. Current full-range caller requests are not evidence of a current
headline error: the defect concerns other valid ways to query the same model.

### 3. P2: the horizon-eight attachment limit remains upstream

`contract_price_model.py:133-135` still filters requested seasons to `0 <= s-t0 <= 8`.
The later loop now requires every contract season to have a forecast, so it no longer returns
a shortened contract. Instead, a term needing horizon nine is dropped at lines 155-161.
The inner join at lines 174-175 removes it without a rejection record.

Executed a deterministic forecast stub that answers every requested year. Given two contracts
for the same eligible subject, of lengths two and ten, attachment returns only the two-year
contract. This isolates the interface from statistical fit support. No current eligible source
contract reaches beyond horizon eight, so this is a demonstrated latent coverage defect, not a
claim that the current headline sample loses ten-year contracts.

Remove the request ceiling and record explicit rejection reasons where a model cannot cover a
term. Carrying `n_years_extrapolated` into accepted contracts is a useful repair already present.

## What I verified successfully

All **14 repair checks passed, with zero skips**, using merged birthdates and the production
age output. Season-row age coverage was **98.346%**.

Independent checks went beyond the repair suite:

- **Production method parity:** zero rate or survival discrepancy across **5,196 rows**,
  covering 866 answerable subjects on the 2021 page at horizons 0-5. The sample includes 266
  negative anchors, 599 curve paths, 106 no-curve fallbacks and 161 low-base fallbacks. The 120
  subjects production cannot anchor are explicitly tagged. This compares the imported anchor,
  curve, multiplier and hazard methods on the adapter's inputs; it is not a complete contract
  spine or dollar reconciliation.
- **Cap-target timing:** doubling every 2019-and-later ceiling leaves cap shares and floor
  shares unchanged for all **663 sample contracts signed before 2019-01-01**. This checks
  information isolation under the candidate's announcement policy, not historical accuracy of
  the announcement dates themselves. The earlier 31-row exclusion is counted by the loader.
- **Actual discounted costs:** a one-year $1M contract starting in 2019 costs **$942,595.91**
  when signed in July 2017 and **$970,873.79** when signed in July 2018, matching two and one
  annual periods at 3%. The value method uses the same offset helper by inspection.
- **Runner selection:** both rolling market runners now request development start cohorts
  only, and the market seal now requires a reason to unseal. These wiring changes were read;
  their full market fits were not rerun in this review.

## Reproduced development comparison

Ran the production adapter and adopted `A1HingeExposure` through the harness on pages
2015-2021, horizons 0-5, matching rows and excluding the tagged outside-production subjects.
The complete six-horizon table reproduces Claude's report to its displayed precision.

| Horizon | Production MAE | Rebuild MAE | Error reduction | Rows |
|---|---:|---:|---:|---:|
| 0 | 0.6534 | 0.5595 | 14.4% | 6,124 |
| 3 | 0.5542 | 0.5038 | 9.1% | 6,124 |
| 5 | 0.4575 | 0.4179 | 8.6% | 5,258 |

MAE is the mean absolute difference between forecast and realized season WAR. These are
development results on data used during model selection, not confirmatory estimates. The
production comparator retains its documented full-panel parameter vintage. I did not
separately reproduce the pooled age and level subgroup tables. A smaller aggregate forecast
error does not settle whether the contract dollar estimates or trade rankings are right.

## Plan and testing gaps still open

The Fable plan requires distributions and 80% interval coverage, subgroup reporting by horizon,
the A3 trade-date update, joint rate/games/participation simulation, control-year treatment and
the goalie tender gate. Those are still incomplete. The full-chain leakage test remains
rate-only, the export-break test still does not perturb inputs, dollar outputs remain
unreconciled, and the market holdout policy remains unresolved after prior inspection.
Once-only ledger enforcement and the missing announced later cap ceilings also remain open.

This pass improves the candidate materially. It does not complete the plan or establish that
testing is comprehensive. The next review should cover the three remaining interface/reporting
defects above and the missing end-to-end valuation checks, rather than infer completion from
the repair suite count.

## Reproduction

`50_REBUILD/code/review_latest_pass.py --candidate-root <checkout> --development` reproduces
the independent probes and development table. Use the review environment, shared source paths,
production `WAR_with_age.csv`, and the checkout's merged `output/birthdates.csv`.
The suite was run separately as `repair_checks.main()` with the same inputs. Aggregate logs
and JSON are in ignored `50_REBUILD/output/`; no vendor rows are included in this report.
No candidate implementation, production code, locked decision, or reserved evaluation changed.
