# Goalie rate repair review closed

Reviewed 2026-09-22. Candidate `f90e6fe`, independently tested in an isolated
worktree. The preceding fallback finding is closed. Proceed to the goalie
control-year comparison, retaining production's total as the default benchmark
and the rate forecast as a sensitivity. No new blocking implementation finding.

## Evidence

- **37 passed, 0 skipped, 0 failed.** Check 37 compares 4,759 scored cells with
  zero difference, including 1,235 fallback cells, 1,235 borrowed-fit cells and
  1,076 clamped cells.
- An additional direct prediction comparison covers **5,032 cells**, every
  requested horizon 0-7 on each development page, including forecasts whose
  outcomes are not yet available for scoring. The maximum difference is **zero**.
- Restoring only the consumer's old fallback makes check 37 fail at page 2015,
  horizon 4, with a **0.5776 WAR** gap. Capping only the consumer's long horizons
  incorrectly makes it fail at page 2017, horizon 6, with a **1.9398 WAR** gap.
- Independent regression comparisons preserve all scored columns across the
  bake-off (25,781 rows), participation runner (14,732) and rate runner (22,098).
  Numeric agreement is within 1e-12; this verifies data values, not Claude's
  separate claim about byte-identical CSV serialization.

The code now shares `ConditionalSeason`, `trailing_share` and `role_share` between
the rate arm and price consumer. The new test exercises the consumer's pkey join,
fallback and horizon cap against the scored forecast rather than testing only
helper arithmetic. Earlier date and participation protections remain in the suite.

## Price rerun

Comparing the repaired contract forecasts against the prior candidate changes
**8 of 165** attached goalie contracts. The largest change is **0.00760086 WAR per
season**, matching the preceding independent correction.

On the same 137 priced contracts across 82 goalies:

| Result | Independent rerun |
| --- | ---: |
| Rate forecast, goalie level-only price MAE | 0.008503 |
| Rate forecast beats production, level-only | 67% of career resamples |
| Extra goalie slope beats level-only | 28% |
| UFA whole-path goalie/skater price response ratio | 0.81 |

The conclusion is unchanged. The separate slope has not earned its place, and the
rate forecast's price advantage is inconclusive. Price specification and D7 remain
provisional. This review does not adopt a final goalie model.

## Clarification for the joint rate/workload design

One qualification in the new prose needs precision. My earlier warning concerned
multiplying two separately estimated ordinary conditional means. That warning
should not be applied unchanged to an exposure-weighted rate.

For a fixed season length L, let R be the per-82 rate and G the games played,
conditioning throughout on the known history and playing that season. The target
of games-weighted squared loss is:

    r_weighted = E[G * R] / E[G]

With share S = G / L:

    r_weighted * E[S] = E[R * S]

That relationship does not require zero correlation between rate and workload.
The usual covariance term applies to E[R] * E[S], where E[R] is the unweighted
mean. Thus the new report's statement that this weighted-rate product works
"only if" rate and share are uncorrelated is too strong.

This identity does not prove the fitted forecast is correct. It requires compatible
conditioning and target definitions, correct component estimates, and care with
mixed schedule lengths. Joint paths still need a defined rate/workload distribution,
particularly for nonlinear floors and control options. Preserve that requirement,
without treating zero covariance as universally necessary. This is a documentation
qualification for remaining design work, not a reopening of the repaired fallback.

## Next step and scope

Proceed with goalie control years using production's total first and the rate
forecast as a declared sensitivity. Squared error remains the recommended primary
point-forecast score for expected quantities; report MAE and bias by subgroup too.
Expected-dollar and distribution checks remain necessary because nonlinear pricing
need not preserve rankings from WAR error. These are prototype defaults and review
recommendations, not authorization to reopen or adopt a final locked model.

Audit: `50_REBUILD/code/review_goalie_rate_repairs.py`; modes setup, run, checks,
price, regression, audit and parity. Evidence uses `goalie_rate_repair_` under
`50_REBUILD/output/` and remains ignored. Earlier closures and the open skater
contract-data comparison stand. No model implementation edits, candidate merge,
vendor writes or canonical production output writes in this review.
