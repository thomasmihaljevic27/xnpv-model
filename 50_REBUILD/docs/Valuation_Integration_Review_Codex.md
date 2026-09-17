# Valuation integration and production reconciliation review

Reviewed `bc724e5` (including `1752a0e`) on 2026-09-16 in an isolated checkout.

## Decision

The integration table is built and the reported raw comparison broadly reproduces.
The reconciliation is not ready to close: its survival decomposition changes both
survival and discounting, some joined rows value different contracts, and the new
integration runner does not enforce key input and output invariants. These findings
do not reopen the closed simulation repairs.

## 1. The reported survival effect also removes discounting [P1]

At `run_valuation_integration.py:213`, the runner subtracts `npv_total` from
`surplus_no_survival` and calls the result the survival weight. The production
implementation at `20_CODE/contract_npv.py:461-463` defines the latter as the sum
of undiscounted contract surplus plus terminal value at its own reference date.
It is not an otherwise-identical NPV with the exit hazard disabled.

I recomputed all 1,141 matched production valuations from their season details.
The correct isolated comparison preserves costs, discount factors and terminal
value and changes only the contract-season survival multiplier to one:

    no-hazard NPV = sum((value - cost) * discount) + original terminal NPV

| Term | Production NPV $M | NPV without exit hazard $M | Effect of removing hazard $M | Effect claimed in report $M |
|---|---:|---:|---:|---:|
| 4 years | -4.49 | -3.63 | +0.86 | +0.70 |
| 6 years | -14.32 | -12.64 | +1.69 | +0.76 |
| 7 years | -21.23 | -19.56 | +1.67 | -0.17 |
| 8 years | -28.19 | -25.90 | +2.29 | -0.58 |

These retain the original matched sample, including the identity exceptions below,
to make the arithmetic correction comparable to Claude's table. The eight-year
cohort is unaffected by the ten wrong-contract cases.

Removing a survival haircut cannot lower value when value is nonnegative and
everything else is fixed. The negative reported effects were a warning that another
part of the calculation was changing. At eight years the residual gap is about
$31.34M, not $34.21M; at six years it is $14.17M, not $15.09M.

Most of the raw long-term gap survives this correction. That supports a narrower
statement: exit hazard alone does not explain the gap. It does not identify aging
or the price line as the cause, and it does not test whether survival historically
offset over-projection against actual outcomes.

Required: recompute a discounted no-hazard value from production season details;
rename the existing nominal column honestly; replace the decomposition and its
interpretation in the report and state files.

## 2. Contract IDs alone do not establish equivalent assets or dates [P1]

The integration joins the exported production ID without checking the underlying
valuation. Production's sweep calls `engine.npv(player_id, valuation_season)` and
then labels its output with the loop's requested contract ID
(`20_CODE/contract_npv.py:671-684`). The engine can select a different contract.

Across the 1,141 joined rows, **10 have no occurrence of the requested contract ID
in their actual production contract-season details**. Examples:

| Requested contract ID | Actual valued ID | Rebuild term | Production seasons |
|---|---:|---:|---:|
| 4798, Nate Schmidt | 3632 | 6 | 1 |
| 5598, Ilya Kovalchuk | 4277 | 1 | 2 |
| 7108, Evander Kane | 4118 | 1 | 4 |

All ten requested IDs: 4334, 4336, 4453, 4547, 4798, 5598, 5627, 6364,
7010 and 7108. A unique exported ID does not repair this mislabelling.

Additional differences need to be carried in the reconciliation:

- Production is valued from the first season's July 1 page; rebuild values are
  dated at signing. The report says both are discounted from signing, which is
  false. Signing calendar year differs from production valuation year in 77 rows;
  calendar-year equality itself would not establish matching information dates.
- Production includes nonzero terminal control value in 185 matched rows. The
  rebuild simulator explicitly excludes control years. The compared assets differ.
- Cost inputs differ beyond discount timing. The supplied production season spine
  puts Eric Robinson's contract 5606 at `pp_aav=975000` but `cs_cap_hit=9750000`
  in both seasons. Production uses the latter: present-value cost is $19.216M
  versus rebuild's $1.866M. Corey Perry's 6216 similarly carries $8.625M in
  `cs_cap_hit` against $0.750M AAV. These are existing source/spine inconsistencies,
  not defects introduced by this integration.

Required: reconcile requested versus actually valued contract IDs, season coverage,
valuation/information dates, cost schedules and terminal value. Flag or quarantine
exceptions with reasons, and report attrition. Keep the raw cross-model comparison
if useful, but separate it from a comparison of the same asset at the same date.
Do not silently drop the problem rows or change production inputs without an audit.

The strong term gradient is real in the raw table. Term-group means account for
about 84.8% of squared variation in the dollar gap in this sample; it is not literally
all disagreement. Differences in cost and valuation definitions can themselves vary
with term. Correlations of 0.69-0.89 indicate substantial ranking agreement, not
identical ordering or proof that the remaining difference is solely a value-side issue.

## 3. The integration's guards accept inconsistent inputs [P2]

The first uniqueness check precedes the production merge, and that merge has no
cardinality validation. The runner also discards the simulator's `surplus_point`
rather than comparing it with the adopted point surplus. It calls no reserved-cohort
guard despite describing itself as development-only.

I drove the actual runner with in-memory input mutations, intercepting output writes:

| Mutation | Result |
|---|---|
| Add $1M to every simulation `surplus_point` | Accepted; writes 1,217 rows |
| Duplicate one matched production contract | Accepted; writes 1,218 rows with a duplicate ID |
| Set sensitivity input start years to reserved 2022 | Accepted; writes 1,217 rows |

Required: validate required schemas and one-row-per-contract/forecast keys before
joins; use explicit merge cardinalities and final uniqueness checks; compare shared
point values, forecast quantities, terms and cohorts across source artifacts; enforce
the development cohort rule in this consumer. If partial coverage is allowed, declare
it and record exact missing IDs instead of treating `min(n_sens,n_sim)` as proof that
the two input populations agree. Guard against stale artifacts with unchanged IDs.

## What reproduced

Reran production in a separate ignored output directory. Original `30_OUTPUT` files
were not overwritten. All six commands completed: skater value, forward projection,
RFA terminal value, exit hazard, goalie value and contract NPV.

| Check | Result |
|---|---|
| Stage 0a/0b regression guards | Pass |
| Priced skater rows | 6,892 |
| Forward projection k=0 | $0.00 across 397 shared rows |
| Goalie Stage P | $0.000284 across 1,730 priced rows |
| Contract NPV sweep | 2,981: 2,591 skaters / 390 goalies |
| NPV distribution | Median +$0.29M, p10 -$7.80M |
| Integrated output | 1,217 rows, 31 columns |
| Production intersection | 1,141 rows |

The goalie NPV k=0 diagnostic also prints 13 documented join-recovery divergences;
it is not a blanket zero-difference gate for both positions.

Both the existing local goalie v2 and the newly regenerated v2 hash to
`55c935dd47627517c0b32c30f4771e11`. Parsed values and missingness match as well.
This verifies local reproduction. Claude's `7e481bf4...` file is not present here,
so its difference cannot be attributed to formatting without comparing that file.

The candidate sensitivity runner completed and wrote its output; an older reviewer
wrapper then failed in an obsolete supplementary diagnostic because `price()` now
returns a tuple. That wrapper error did not interrupt the candidate runner or its
written comparison. The simulation CSV was reused from the immediately preceding
verified `db0c6b2` run; simulator code is unchanged in this candidate. The full 25-test
suite was not repeated because the changes under review are in this new integration
consumer. Its targeted guard tests exposed the failures above.

## Evidence and scope

`50_REBUILD/code/review_integration.py` reproduces the isolated production chain,
integration, per-season survival calculation and consumer mutation tests. Modes:
`production`, `integration`, `audit`, `guards`, with integration requiring the two
upstream rebuild CSVs. The bundled Excel reader supplements the review environment.
The first production attempt stopped at the missing reader before generation;
the configured rerun completed all stages.

Evidence remains ignored under `50_REBUILD/output/`: `integration_production/`,
`integration_run_review.log`, `integration_definition_audit.csv`,
`integration_definition_audit.json` and `integration_guard_audit.json`.
No production code, source inputs or candidate implementation was edited or merged.
Only review records and the audit script are committed.
