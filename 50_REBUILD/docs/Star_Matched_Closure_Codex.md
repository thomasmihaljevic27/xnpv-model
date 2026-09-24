# Matched aging comparison: closure review

Reviewed candidate `670b614` in an isolated checkout on 2026-09-23; reproduction
and closure completed 2026-09-24.

## Decision

The training-sample repair is closed. Keep the adopted forecast and proceed to
the proposed multi-season-level candidate as an experiment. The explanation
that the current formula pulls players toward average twice remains a hypothesis.
Neither tested candidate earns adoption, and Phase 5 remains open.

## Repair verified

The matched no-level model now preserves the adopted curve's training rows and
weights. The old unmatched model remains explicitly labelled as changing both
the formula and sample. The hinge model uses the adopted rows too.

Independent checks:

- Actual fit fingerprints match on all seven development pages. The adopted
  sample grows from 3,494 rows in 2015 to 7,164 in 2021.
- Restoring the matched model's old sample makes check 46 fail: 7,212 rows
  versus the adopted 5,299 on its 2018 test page.
- Changing the matched fit's game weights by 1% also makes check 46 fail,
  with 5,299 rows on both sides. The guard checks more than counts.
- The adopted aging coefficients are bit-identical to the previous `477316d`
  implementation on every development page.

Check 46's own coefficient comparison calls the current implementation twice;
it tests consistency between entry points, not historical parity. The independent
cross-version comparison above establishes parity for this change.

## Interpretation for the next experiment

### The failed hinge is one tested specification

The hinge leaves the five-year star rate bias essentially unchanged, at -0.925
versus -0.921. It does make a small improvement in star season WAR RMSE, from
1.8591 to 1.8547, lower in 1,962/2,000 resamples. Its pooled squared error and
dollar scores do not justify adoption.

Describe this as a failure of the specified hinge at 2 wins to repair the
long-horizon bias. It does not establish that differing level effects cannot
explain the miss. That broader conclusion would repeat the earlier mistake of
letting one unsuccessful candidate stand for an entire idea.

### The double-pull explanation is plausible but unmeasured

The diagnostic reproduces when the training changes are weighted by the smaller
game count in the two seasons. Among 594 observed training pairs whose lagged
rate is at least three, observed change is -0.226 and fitted change is -0.270.
Grouping by the season the change starts from instead gives -1.149 observed.
These are weighted training-sample summaries; they do not demonstrate which
mechanism causes errors on later forecast pages.

The proposed interpretation is that the regression learned partly from temporary
good seasons, then applies that adjustment to a more stable forecast that has
already discounted temporary performance. That is a reasonable motivation for
testing a multi-season level input. It is not established by matching a mean in
the data used to fit the curve. A weighted multi-season rate is also not
automatically identical to the calibrated forecast level used during prediction.
Specify the season alignment too: the training level ends before the change's
starting season, while the walk supplies its current projected level.

Keep the proposed input dated before the change being predicted, hold training
rows and weights fixed, and preserve the adopted currency as the primary dollar
comparison. Check 46 should cover the actual new class once it exists. Score
the new candidate before attributing a gain to the proposed mechanism.

## Remaining documentation cleanup

These items do not block the next experiment:

- The inline missing-lag explanation is corrected, but the aging module's opening
  docstring still claims those rows receive an age/position fallback. Remove it.
- That docstring also says lagged noise is independent by construction. Using a
  different season removes the shared-variable arithmetic; it does not guarantee
  independence across seasons, which the new hypothesis itself questions.
- The star runner still quotes a 1.06 season WAR miss where the current result is
  0.866. The report's file list still gives old versions and calls each old variant
  a single change. Update those descriptions alongside the next experiment.

## Reproduction scope

The complete suite passes **46 checks, zero skipped, zero failed**, including
all 41 registered forecast variants. The star runner completes on 40,510
forecasts per variant, 1,217 priced contracts and 1,176 ended terms scored.

| Version | Season WAR RMSE | Season squared-error wins /2,000 | Primary dollar RMSE | Primary dollar wins /2,000 |
|---|---:|---:|---:|---:|
| Adopted | 0.8151 | -- | $3.513M | -- |
| No level terms, matched rows | 0.8133 | 1,610 | $3.487M | 1,531 |
| Second level slope above 2 | 0.8154 | 263 | $3.519M | 180 |

These reported comparisons reproduce exactly. On the hinge currency, the
unmatched, matched and hinge versions win in 1,117, 1,474 and 200 resamples,
versus the published 1,118, 1,473 and 203. Those differences do not change the
decision; their numerical cause was not isolated.

The final row-level audit confirms that participation, games share and
horizon-zero rates remain exactly equal across all four variants. The adopted
forecast matches the preceding candidate exactly on all 40,510 rows, and the
matched variant reproduces the independent review's implementation within
1e-12. The training diagnostic and both deliberate guard failures are also
recorded by the helper.

Reproduction helper: `50_REBUILD/code/review_star_matched.py`. Generated logs and
tables are ignored review outputs. No candidate was merged or adopted by this
review. Full simulation distributions, control years, production reconciliation
and confirmatory cohorts are outside this rerun.
