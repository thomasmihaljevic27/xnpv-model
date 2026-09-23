# Skater signing-date repair review

Reviewed 2026-09-23. Candidate `d2be5b0` in an isolated checkout.

## Decision

The signing-date implementation finding is closed. The contract attachment caller
now passes each contract's signing date into participation, while retaining the
same completed-season history and fitted model. The existing no-contract leader
is unchanged. No new implementation blocker was found in this repair.

The corrected point-dollar result supports contract status only as a provisional
skater choice. Simulation and control-year integration must then be re-scored.
Adoption and that integration are separate from this review; the
review does not change the leader or merge the candidate into main.

## What was verified

The full suite returns **42 passed, 0 skipped, 0 failed**. Check 42 runs through
`attach_forecasts`, including two contracts for the same player in one batch with
different signing dates. It reproduces Chara's participation at 0.336686 using
July information and 0.589150 using signing information. A July-dated copy
reproduces the previous calculation, and the leader remains unchanged.

The seven-year example tests an extrapolated tail. The new participation method
uses the last fitted horizon and the existing cached participation decay, while
retaining the page forecast's conditional production. Historical forecasts used
in the alternative price fits use the same attachment function.

Independent deliberate breaks establish that the new check is active:

| Change introduced for testing | Result |
| --- | --- |
| Force the attachment caller back to page dating | Check 42 fails |
| Remove the participation decay beyond the fitted range | Check 42 fails on long-contract production parity |

An additional test changed the coverage of 3,184 contracts signed after Chara's
decision date. His forecast remained exactly unchanged through the attachment
caller, including a refit: first-season participation 0.5891498849763103 and
expected production 0.05896016531592401 WAR. The vendor source was not modified.

## Reproduced results

The five season-score rows reproduce with 40,510 unique, matching forecast cells
per variant. Ability and games share are exactly unchanged across variants.
The first-season calibration table also reproduces: leader 0.782, status only
0.845, and actual participation 0.900, including the reported intervals.

On the leader's common currency, the independent dollar rerun gives:

| Specification | RMSE, $M | MAE, $M | Bias, $M | Lower squared error in career resamples |
| --- | ---: | ---: | ---: | ---: |
| Leader | 3.534 | 1.679 | -0.597 | Reference |
| Old contract definition | 3.500 | 1.686 | -0.515 | 2,000 / 2,000 |
| Period and status | 3.517 | 1.681 | -0.550 | 1,999 / 2,000 |
| Period only | 3.537 | 1.678 | -0.612 | 1 / 2,000 |
| Status only | 3.518 | 1.681 | -0.549 | 1,999 / 2,000 |

The displayed RMSEs differ from Claude's by at most $0.001M. The substantive
comparison reproduces: about $16,000 lower RMSE and $48,000 less negative bias.
MAE is slightly worse, so the recommendation depends on the declared squared-error
primary score. On the alternative currency, status only wins 2,000 / 2,000.

The runner rounds resample shares to whole percentages. In this independent run,
"100%" on the primary line is 99.95%, and "0%" is 0.05%. Write "almost all"
rather than "every" for the primary status-only result. This qualification does
not change the recommendation. No explanation for the small cross-run numerical
differences is established here.

## Interpretation and reporting qualifications

1. The first-season calibration table covers **1,458 contracts with attached
   forecasts**, before the price-fit availability filter. Dollar valuation covers
   **1,217**, and dollar scoring covers **1,176 completed terms**. Calling all
   1,458 contracts "priced" conflates these stages. This does not invalidate
   either calculation.
2. Adding contract status reduces the measured first-season gap by about 6.3
   percentage points. It does not establish that omitting status caused the
   entire 11.8-point gap. The remaining underprediction and the difference
   between July training dates and signing application dates remain unresolved.
3. A strong paired bootstrap result describes these development contracts under
   the chosen currency. It does not establish a large economic effect, remove
   the vendor-coverage assumption, or provide confirmatory evidence. Path
   simulation, control years, and the affected price lines still need integration
   and scoring before their conclusions are carried forward.
4. The cited goalie dollar comparison was already part of the recorded trade-off
   when adopting its no-contract baseline. It is not new evidence from this
   skater repair. The goalie choice can remain closed unless the user deliberately
   revisits that trade-off; this review does not reopen it.

These are reporting and adoption qualifications, not requests for another
implementation repair cycle.

## Reproduction and scope

`50_REBUILD/code/review_skater_signing.py` supplies setup, full-suite, skater-run,
artifact-audit, deliberate-break, future-contract, and exact-bootstrap modes.
It uses candidate `d2be5b0`; raw evidence remains in ignored `50_REBUILD/output`.
No production implementation, source data, or canonical production output was
changed. Phase 5 and the trade back-test remain open.
