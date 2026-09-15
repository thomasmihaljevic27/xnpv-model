# What the rebuild has already looked at

Written 2026-09-15, before the repaired chain is refit, so that the record of what has been
consumed is taken while it can still be reconstructed rather than after another evaluation
round has been added to it. Two reserved samples exist and they are in different states. The
forecast holdout is intact. The market holdout is spent.

## The forecast pages

Development pages are the 2015 to 2021 valuation seasons. Confirmatory pages are 2022 to 2025.

Every variant comparison, bake-off, aging test, survivorship sensitivity, and stress test to
date has run on the development pages. No caller anywhere in the tree passes `unseal=True`, and
the harness refuses a confirmatory page by default, so on the evidence of the code and the
session record no confirmatory forecast page has been scored.

One exception, recorded because the standard this file sets is worth nothing if an
inconvenient inspection goes unrecorded. On 2026-09-15, while testing the guards described
below, the flat-carry benchmark was scored on confirmatory page 2022 at horizon zero. It ran
in a throwaway copy of the pre-repair code in a scratch directory, to demonstrate that the old
seal accepted an unsealed run with no reason, which it did. No variant was compared, no
candidate was selected, and the output was discarded unread beyond the row count. The page is
not spent in any sense that affects selection, and it is written down anyway.

That statement rests on the reports and the session log rather than on a record, because until
today no record existed. The seal refused a page and logged nothing, so an unsealed run would
have left a line in a run log that is gitignored and regenerates. This is the weaker of the two
things that could be said, and it is the honest one: the forecast holdout is believed intact,
and from now on it is auditable.

## The market cohorts

Contract start years 2018 to 2025 have each been evaluated repeatedly during development, the
reserved years included. Both the rolling price evaluation and the curvature test swept
`range(2018, 2026)`, fitting on earlier start years and scoring the next, once per development
run, across the pooled-versus-split market question, the term convention, the contract-feature
ablation, and the curvature retest.

There was no market seal. The page seal covered forecast scoring only, so sealing the pages and
not the cohorts was never a split sample: a price specification chosen on cohorts through 2025
has been selected on the same years the forecast side was reserving.

The practical consequence is that no market result on a 2022 to 2025 start cohort can be
presented as out-of-sample. Those cohorts have been used for selection. This does not
invalidate the development work, and it is not a reason to discard the market experiments; it
means the market side currently has no untouched sample, and a confirmatory market claim needs
one that has been defined and then left alone.

## Where the line now sits, and who owns it

The reserved market cohorts are set to 2022 through 2025, mirroring the forecast pages, and
`check_market_cohorts()` enforces it in both market runners with the same written-reason
unseal the harness uses. The boundary mirrors the pages because that is the conservative
reading of the existing split. It is not a decision that has been taken.

The decision owed is what the market holdout should be, given that the obvious candidate has
already been consumed. Three routes, and the choice belongs to the project rather than to this
file.

1. Accept that the market side has no holdout, and present each market result as in-sample
   development evidence. Honest, costs nothing, and gives up the confirmatory market claim.
2. Reserve a different sample that selection has not touched. The candidates are a forward
   window of signings after the rebuild is frozen, or a held-out slice of the existing sample
   drawn on something other than start year, which is only worth doing if the slice was never
   an evaluation unit.
3. Re-derive the market specification on development cohorts alone, then spend the reserved
   years once. This is only available if the specification is genuinely rechosen without
   reference to what the reserved cohorts already showed, which is a claim about what the
   analyst knows, not about what the code does.

Until that is decided the enforced boundary above stands, so that nothing further is consumed
while the question is open.

## The ledger

`inspection_ledger.csv` in this folder records one line for each evaluation that consumes a
forecast page or a market cohort: the timestamp, the runner, what was consumed, which of those
keys are reserved, and the reason given for any unsealing. It is committed rather than
generated, because a record that regenerates is not a record.

It starts empty today. It is not a reconstruction of the history above, which is written from
the reports and the code and is stated as such. From here the two are meant to converge: the
narrative covers what happened before the ledger existed, and the ledger covers everything
after.
