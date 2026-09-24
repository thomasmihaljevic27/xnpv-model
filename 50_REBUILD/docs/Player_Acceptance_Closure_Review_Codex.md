# Player Model acceptance closure review

Reviewed 2026-09-24, candidate `7b046a3`, in an isolated checkout. This closes
the two scoring findings from `Player_Acceptance_Review_Codex.md`. It does not
adopt the rebuild into production. Thomas will make that choice when work on
the separate Picks and Prospects Models resumes.

## Verdict

The Player Model candidate can close at Phase 5 with its recorded limitations.
No further forecast candidate or star-residual experiment is requested. The new
scorecard needs the reporting corrections below before it is used to support
the later adoption decision. They do not reopen the repaired acceptance scorer.

## Verified repairs

- The unmodified full suite passes: **48 passed, none skipped or failed**.
- The shared scorer checks player identity, signing date, contract seasons,
  length, pricing quarter, RFA status, position, one-year flag and floor share.
  Independently changing each of these ten fields is rejected by name. The
  preceding scorer still accepts a changed player on the same fixture.
- Each arm now computes its realised target using its own inputs before the
  target-equality check. The guard no longer manufactures equality by reusing
  the first arm's identity and dates.
- Monetary calibration uses six decimal dollar places. Restoring effectively
  exact comparisons makes check 48 fail; a cent remains a distinct amount.
- On all 1,176 ended contracts, both rebuilt point values, simulated means,
  and realised targets are exactly unchanged from the preceding independent
  acceptance run. Corrected pooled PIT means are 0.501049 for Candidate A and
  0.511792 for B; central-50% shares are 0.488095 and 0.448129 respectively.

## Scorecard rerun

All three models produce 40,510 development forecasts. Both rebuilds simulate
1,217 contracts without a missing-band rejection; 1,176 ended contracts from
767 players enter dollar scoring. The primary printed RMSE/MAE/bias table
reproduces. Candidate A's season RMSE is 0.8151 against the adapter's 0.8683.
Primary point-dollar RMSE is $3.513M against $3.548M, MAE $1.675M against
$1.771M, and bias -$0.549M against -$0.143M.

Primary squared-error bootstrap counts are 1,236/2,000 for A and 1,161 for B
against current, one below the reported 1,237 and 1,162. Absolute-error counts
are the reported 1,962 and 1,961. On the current-line sensitivity, squared-error
counts are 1,137 and 1,045 (reported 1,137 and 1,047), and absolute-error counts
are 1,969 and 1,973. These small differences do not change the conclusions;
the rerun is not claimed bit-identical in every statistic.

The dollar bootstrap uses equivalent player-group sums and the same seeded
resampling, validated against the original routine. Forecasts, paths and prices
are unchanged. The full check suite is unmodified. This turn did not rerun the
production NPV reconciliation or the entire goalie pipeline, which were not
changed by these repairs.

## 1. Report production's answerable sample separately

`run_model_scorecard.py` scores all adapter rows and calls them production.
But `ProductionChain.predict` tags an explicit fallback when production has no
anchor: the harness's trailing value is carried forward instead. Its own code
says this extends production and requires a separate answerable-sample result.

There are **4,632 fallback rows (11.4%)** in the reported 40,510. Restricting all
three arms to the same **35,878 production-answerable rows** gives:

| forecast | season RMSE | season MAE | bias | Brier |
|---|---:|---:|---:|---:|
| production | 0.9129 | 0.5626 | +0.0532 | 0.2052 |
| Candidate A | 0.8640 | 0.5082 | -0.0765 | 0.1358 |
| Candidate B | 0.8645 | 0.5083 | -0.0781 | 0.1370 |

Both candidates still have lower squared error in **2,000/2,000** player
resamples. Retain the full-sample result as production plus its declared
fallback, and add this common answerable-sample result. Importing production's
class does not make every row it returns a production forecast.

The same issue reaches **65 of 1,176 dollar-scored contracts**: production has
no anchor on their signing page. On the other 1,111 contracts, retaining the
already fitted primary price line, A's point RMSE is $3.614M against $3.648M
and MAE $1.761M against $1.854M. Squared-error wins are 1,245/2,000 and absolute-
error wins 1,934/2,000. This preserves the qualitative dollar result too. It is
an answerable-sample scoring sensitivity, not a price line refitted without
fallback contracts. Preserve and report that distinction in the runner.

Production's `p_play` is the adapter's mapping of its accumulated survival
weight, starting at one. Describe the Brier comparison in those terms rather
than implying production has a separately fitted first-season participation
model. Future-panel estimation is a dating problem; it is not a demonstrated
accuracy advantage without a comparison to a dated fit.

## 2. Preserve the actual limits of the adoption evidence

- **The later pages are not historically sealed.** Plan decision D and its
  multiple-inspection warning explicitly record about thirty variants already
  inspected on 2022-2025. This run does not score them; that does not restore
  pristine holdout status. Correct the runner, scorecard and chat summary.
- **Pooled calibration is not calibration for each contract or subgroup.**
  State that the corrected pooled tests do not detect miscalibration for A.
  Keep the known star limitation beside the result. Passing those tests does
  not establish a reliable distribution for every individual contract.
- **6.1% is the reduction in RMSE**, not mean squared error. The corresponding
  mean-squared-error reduction is about 11.9% on the reported full sample.
- **A does not win every error metric against B.** The displayed dollar MAE
  is slightly lower for B, especially on simulated means. A's advantage is
  in the declared squared-error criterion; the report partly states this
  already, but the blanket recommendation wording contradicts it.
- The chat attributes much of the long-term valuation gap to term pricing.
  The document correctly says the reconciliation has not separated forecast
  and pricing effects. Retain that qualification. The eight-year comparison
  also carries the earlier asset/date comparability limits.

These changes narrow claims, not the completed implementation. Keep adoption
deferred as Thomas requested; no new model search is required to close this
candidate.

## Reproduction

`50_REBUILD/code/review_acceptance_closure.py` provides `setup`, `checks`,
`repairs`, `scorecard`, and `audit` modes. Evidence is ignored under
`50_REBUILD/output/acceptance_closure_*.txt` and the isolated checkout's output.
Vendor inputs were read only. No production code or model default was changed.
