# Reconciliation repair verification

Reviewed `1a6ba0d` on 2026-09-16 in an isolated checkout.

## Decision

The corrected survival arithmetic reproduces, the contract exceptions are now exposed,
and all three originally demonstrated integration mutations are rejected. Those are
substantive repairs. Two narrow corrections remain before closing this pass: use one
consistent production result throughout the hazard calculation, and stop describing the
912-row screen as passing every comparability test.

The available comparison remains a diagnostic across different information dates.
It is not a same-date validation, an outcome back-test, or a completed Phase 5 sign-off.
Other development can proceed while these corrections are made. No simulator redesign
or reopening of the previously closed simulation repairs is warranted.

## Verified repairs

Reran the actual integration and new production-reconciliation runners against the
production outputs regenerated in the preceding review. Production code and the upstream
forecast/simulation algorithms have not changed, so those outputs were reused.

| Check | Result |
|---|---|
| Integrated table | 1,217 contracts, 31 columns |
| Reconciliation table | 1,141 contracts, all answered by the engine |
| Hazard effect compared contract by contract with the independent audit | Maximum difference $3.85e-09 |
| Hazard removal at 4 / 6 / 7 / 8 years | +$0.86M / +$1.69M / +$1.67M / +$2.29M |
| Negative effects on the unmodified inputs, below -$1 tolerance | 0 |
| Wrong-contract IDs / different season counts | 10 / 3, matching the audit |
| Terminal-value rows / cost differences above 10% | 185 / 46 |
| Date flag failures | 240 |
| Restore $1M simulation point-baseline mismatch | Rejected |
| Duplicate a matched production ID | Rejected by merge cardinality validation |
| Inject reserved 2022 cohorts | Rejected |

The nominal no-survival column has been renamed, and the false decomposition has been
removed from the integration runner. The revised report appropriately withdraws the
claim that the remaining gap is identified as aging or the price line.

The 240 date failures compare the signing's July-to-June season with the production
valuation season. This differs from the preceding audit's count of 77 calendar-year
differences; the counts measure different things. Neither test establishes exact-date
equivalence when it passes.

## 1. The new runner mixes fresh season details with saved NPV totals [P2]

`run_production_reconciliation.py:94-128` calls the engine and gets fresh detail plus
summary `s`. It calculates contract value without hazard from the fresh detail, but
adds `r.npv_terminal` and subtracts `r.npv_total`, both read separately from the saved
production spine. It does not compare those saved totals with the fresh summary.

This produces the correct answer for the current consistent files. It is not a safe
calculation if the spine is stale relative to the engine, its inputs or its settings.

I changed only the saved spine's `npv_total` by +$1M in memory and reran the actual
reconciliation consumer. The engine and all season details were unchanged. The runner
accepted the input, shifted every hazard effect by -$1M and wrote a result containing
**1,043 negative hazard effects**. Its check merely prints the count; it does not fail.
The mutation did not overwrite any real input or output file.

Required correction:

1. Use `s['npv_total']` and `s['npv_terminal']` from the same engine call as the details.
   Use that same terminal result for the terminal-value flag.
2. If the saved spine remains part of the comparison, assert agreement with the fresh
   summary within a declared numerical tolerance, or label discrepancies explicitly.
3. Assert that removing the contract hazard cannot lower value beyond numerical
   tolerance. Keep the mutation as a regression test.

This is a data-consistency safeguard and a small code correction, not evidence that
the reproduced +$0.86M/+1.69M/+1.67M/+2.29M figures are wrong.

## 2. “912 comparable on every test” excludes the date test [P2]

At lines 141-142, `clean` requires the requested identity, season count, cost tolerance
and absence of terminal value. It deliberately omits dates. The later `date_ok` column
is separate, and date differences are absent from `exclusion_reasons`.

The report discloses this in a paragraph, but its headline, table label and “comparable
rows” description contradict that qualification:

- **912** pass the structural/cost screen.
- **217 of those 912** fail the signing-season date flag.
- **695** pass that screen and the date flag. They still do not necessarily share an
  exact information date.
- **17 of the 22 eight-year contracts** fail the date flag. Retaining every eight-year
  row in the structural screen does not establish same-date comparability.

The user's pasted summary also says the four-to-eight-year cells are untouched. The
actual report and output are more precise: the six-year cell falls from 33 to 31.
Four, five, seven and eight years are unchanged by this structural screen only.

Required correction: name the flag and row group for the tests they actually apply,
such as “passes identity, season-count, cost and terminal-value screen.” Describe
dates as a separate unresolved limitation. If a downstream consumer needs a same-date
comparison, provide explicit harmonization rather than treating either 912 or 695 as
proof that it has one. Dropping 217 rows by itself would not solve the dating issue.

## Limits and evidence

The candidate's 25-check suite and model algorithms are unchanged from the prior
verification; the suite was not rerun in this pass. Those 25 checks do not exercise
these new integration/reconciliation consumers. The actual runners, independent
row-level arithmetic comparison and targeted mutation tests above are this review's
validation evidence.

The existing audit driver now accepts `--candidate-root` and has `reconciliation`
and `repair-audit` modes. Commands, after upstream CSVs and the previously regenerated
production output are available:

```powershell
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_integration.py integration --candidate-root 50_REBUILD/output/integration_repair_review
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_integration.py reconciliation --candidate-root 50_REBUILD/output/integration_repair_review
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_integration.py guards --candidate-root 50_REBUILD/output/integration_repair_review
.\50_REBUILD\output\review_venv\Scripts\python.exe 50_REBUILD/code/review_integration.py repair-audit --candidate-root 50_REBUILD/output/integration_repair_review
```

Run dependent commands to completion in order. An initial reconciliation invocation
preceded integration completion and refused its missing input; the subsequent run
completed successfully. Evidence is ignored under `50_REBUILD/output/`, including
`integration_repair_run.log`, `integration_repair_guards.log`,
`reconciliation_repair_run.log` and `reconciliation_repair_audit.json`.

The other machine's differently hashed goalie file remains unavailable, so its hash
difference is not newly resolved here. No production input or model implementation
was changed, and no candidate changes were merged into main by this review.
