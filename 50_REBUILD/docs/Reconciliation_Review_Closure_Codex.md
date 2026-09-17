# Reconciliation review closure

Verified `76730b6` on 2026-09-16 in an isolated checkout.

## Decision

Both findings in the preceding reconciliation repair review are closed. Proceed with
the remaining valuation work. No new blocking defect was found in the changed code.

This closes the review of the integration/reconciliation diagnostic. It does not make
the two models comparable at the same information date, validate either model against
realized outcomes, or complete Phase 5. The disclosed date differences, production input
exceptions and other machine's unexplained goalie-file hash remain limitations.

## What was verified

The actual reconciliation runner queried production's engine for all 1,141 contracts.
Its total and terminal NPV now come from the same engine call as the season details;
the saved total is retained only for a consistency check. The terminal flag also uses
the fresh summary. Minimum season value and nonnegative hazard effects are asserted.

| Test | Result |
|---|---|
| Normal reconciliation | Pass, 1,141 contracts |
| Hazard effects versus the independent per-season audit | Exact agreement on all rows |
| Saved spine versus fresh engine totals | Largest difference $0.00 |
| Add $1M only to saved spine totals | Rejected; all 1,141 offenders identified in the count |
| Halve contract 3702's season values in detail only | Rejected by hazard assertion, naming 3702 |
| Asset screen | 912 |
| Asset-screen rows failing date flag | 217 |
| Asset and date flags both pass | 695 |
| Eight-year contracts passing both flags | 5; explicitly reported below the table threshold |

The two mutation tests replayed the engine details and summaries captured during the
real normal run, changing only the intended input. They did not modify source files,
production artifacts or candidate code. Output writes were intercepted for these tests.

The old `clean` flag is absent. `asset_ok`, `date_ok` and `asset_and_date_ok` are
present and reproduce the stated counts. The report now explains that agreement on
valuation season is not agreement on the exact information date. The four-test asset
screen includes a declared cost tolerance, rather than requiring identical cash flows.
The corrected six-year retention is 33 to 31.

The integration runner is unchanged from the preceding pass, in which all three
original bad-input tests were rejected. The unchanged 25-check model suite and unchanged
production chain were not rerun. This pass exercised the changed reconciliation runner
and its two new rejection paths directly, using the previously regenerated production
outputs and verified integrated input.

## Next work

Continue the already declared valuation work: RFA walk-away/control years, goalies,
the remaining joint rate/games/participation design, development dollar scoring and
the back-test with its grouping rule and protocol declared before evaluation. Carry the
reconciliation's date and input limitations into that work; do not turn the raw model
comparison into evidence about which model predicts outcomes better.

## Evidence

The candidate is `50_REBUILD/output/reconciliation_closure_review`. The extended audit
driver runs the real reconciler, records engine answers, checks the resulting artifact,
and proves both rejection paths:

```powershell
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_integration.py closure-audit --candidate-root 50_REBUILD/output/reconciliation_closure_review
```

Local inputs are the verified integrated CSV from the preceding pass and unchanged
production outputs under `50_REBUILD/output/integration_production`. Evidence stays
ignored in `reconciliation_closure_audit.log`, `reconciliation_closure_audit.json`, and
the candidate's `production_reconciliation.csv`.

No candidate implementation was edited or merged. No production/source inputs or
unrelated user documents were modified. Only the review, audit and state records are
included in this review's commit.
