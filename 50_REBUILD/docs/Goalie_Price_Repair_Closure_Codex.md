# Goalie price-line repair review

Reviewed 2026-09-22. Candidate: `af61f6c` on
`claude/amazing-johnson-cllbgl`, tested in an isolated worktree.

## Decision

The preceding price-line findings are closed. Proceed to the goalie participation
model with the price specification provisional. This closes the repair review;
it does not adopt a goalie model or settle D7. No new blocking finding.

## Results reproduced

The candidate runner reproduces the comparison on the same 174 contracts,
representing 102 goaltenders. Errors are annual salary cap shares.

| Specification | Mean absolute error | Bias |
| --- | ---: | ---: |
| No goalie terms | 0.010318 | +0.006627 |
| Goalie level only | 0.007457 | +0.000145 |
| Goalie level and slope | 0.007489 | +0.000141 |

The runner reports level-only beating no goalie terms in 100% of resamples,
and level-and-slope beating level-only in 10%. Independent reconstruction gives
0.0074561 for level-only, a negligible optimizer difference from the runner.
An independent bootstrap that resamples whole goalie careers gives a 95% interval
of [-0.0000161, +0.0000824] for the additional slope's change in absolute error.
This supports retaining the simpler specification as the development comparator;
it establishes neither equal slopes nor a necessary separate goalie slope.

The final fit's response to one additional expected win in every contract season
is $2.022M for an unrestricted skater and $2.167M for an unrestricted goalie
(ratio 1.07). Restricted-player responses are $1.928M and $2.073M (ratio 1.08).
These are changes in fitted annual price before the salary floor, not contract
NPV. The earlier first-year-fixed partial slopes are approximately $0.819M and
$0.964M in this rerun. The corrected definition includes first-year production
and the applicable rights and goalie interactions.

The sample counts reproduce: 263 eligible development goalie contracts, 205 with
forecasts, 174 priced by the pooled specifications. All specifications use
expanding samples at quarterly cutoffs. The goalie-only specification prices five
contracts under its 200-row training minimum, insufficient for a comparison.
The +0.167 WAR calculation is now explicitly a constant-production illustration,
not an identified decomposition of forecast bias.

## Verification beyond running the suite

- Full review suite: **33 passed, 0 skipped, 0 failed**.
- All 68 executed price fits report convergence; the assembled sample has no
  duplicate contract IDs. Comparisons use matching contracts.
- Direct changes to the fitted equation agree with the whole-path response
  within $1.2e-9 across both positions and both rights categories.
- Additional synthetic checks give first-year, RFA and goalie coefficients
  distinct nonzero values. All eight combinations of position, rights and
  level-only/level-and-slope specification return the expected response.
- Check 33 rejects each deliberate defect: using the goalie interaction alone,
  admitting future signings, and substituting a partial slope for the whole-path
  response. These mutations are temporary, in memory only.

## Scope of the next item

Participation means the probability of playing any NHL games in the season.
Workload means how much a goalie plays conditional on appearing. They are distinct
quantities: a flat probability of participation is not a model of depth-chart
share. The next design should state which quantity it estimates and how it enters
the season forecast. Revisit the provisional price comparison after changing the
forecast input; this review does not establish that its result survives that change.

Earlier forecast, RFA, simulator and reconciliation closures stand. Joint paths,
goalie control years, development dollar scoring and the declared back-test remain
outside this review. No model adoption, candidate merge or production changes.

## Evidence

Reproduction entry point: `50_REBUILD/code/review_goalie_price_repairs.py`.
Modes: `setup`, `run`, `checks`, `audit`, `mutations`, `qualification`.
It uses the detached candidate worktree under
`50_REBUILD/output/goalie_price_repair_review`. Logs, captured coefficients and
independent scores use the `goalie_price_repair_` prefix in `50_REBUILD/output/`
and remain ignored. Vendor files and canonical production outputs were untouched.
