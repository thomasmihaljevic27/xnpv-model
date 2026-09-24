# Player Model acceptance review

Candidate `01e78a9`, reviewed 2026-09-24.

## Decision and scope

The acceptance work supplies the missing comparison of simulated skater contract
values on a common price line. Two narrow scoring repairs remain before final
sign-off. These do not call for another forecast candidate or a reopened star
investigation.

Closure here means a reviewed, reproducible Player Model candidate with stated
limitations. It does not adopt the rebuild for the thesis or production. Picks
and prospects are separate model work; the decision to adopt or drop the rebuilt
Player Model will be made when that work resumes, as the user clarified.

## Reproduced acceptance evidence

- The unmodified repair suite completes: **47 passed, zero skipped, zero failed**.
- Both skater forecasts price and simulate 1,217 contracts, with none skipped for
  an incomplete band. Scoring covers 1,176 ended contracts and 767 players.
- The selected forecast's point values agree with the previously reviewed
  integration artifact on all 1,176 scored contracts, with a maximum difference
  of $1.49e-08. The reconciliation implementation is unchanged in this update;
  the production engine itself was not rerun for this review.
- The point-valuation extraction is equivalent to the previous statements in
  `main`. Five moved helper functions have identical executable syntax, and
  the shared scorer matches the former inline scorer on the real-row fixture.
- The full goalie runner completes. On its 133 scored contracts, the shared
  scorer and the previous inline implementation return exactly equal targets,
  point values, simulated means, and draw arrays on both price lines when given
  the same current inputs. This verifies the refactor independently of a saved
  historical table that may have used a different currency fit.

Primary line, millions of dollars:

| Forecast | Valuation | RMSE | Mean absolute error | Bias |
|---|---|---:|---:|---:|
| Selected | Point | 3.513 | 1.675 | -0.549 |
| Selected | Simulated mean | 3.513 | 1.758 | -0.335 |
| Previous | Point | 3.529 | 1.674 | -0.594 |
| Previous | Simulated mean | 3.526 | 1.743 | -0.406 |

All comparison counts reproduce exactly. The previous forecast has lower
squared error in 15/2,000 resamples for simulated values and 1/2,000 for point
values on the primary line; the sensitivity counts are 12/2,000 and 1/2,000.
Its simulated mean has lower absolute error in 2,000/2,000 on both lines.
Point absolute-error counts are 1,056/2,000 and 1,423/2,000. Some sensitivity-line
RMSE cells differ from the report by $0.001M at its printed precision; the
primary table and all comparison counts above reproduce as printed. Calibration
is not bit-for-bit reproducible under its current tie rule, as detailed below.

For the full skater rerun, the reviewer replaced repeated DataFrame concatenation
inside resampling with group sums and counts using the same player draws and
seeds. Forecast fitting, simulation, and pricing are unchanged. This calculation
was checked against the original resampler before use; it avoids rebuilding
hundreds of player tables for each draw. The initial unmodified run was stopped
during resampling after reproducing the primary error table. Additional checks
on the real scoring sample reproduce the original resampler's results too.

Reproduction helper: `50_REBUILD/code/review_acceptance.py`. Generated logs and
captured scoring arrays remain in ignored `50_REBUILD/output/`. No candidate
implementation, production code, or vendor input was changed in this review.

## Finding: the shared-target guard does not check identity and dates

`dollar_scoring.score_on_line`, lines 117-135, takes the first forecast's player,
season range, signing-date dollar factor, and price-line cut before entering the
loop over forecasts. It then uses those same inputs to build each realised
target. Consequently, target equality cannot detect a disagreement in those
inputs, despite the docstring claiming that it covers them. Point valuation uses
each row's own dates, while the simulated valuation uses the first row's factor.

Two independent mutations of check 47's contract fixture were accepted:

| Mutation to the second forecast's row | Difference in a target computed from that row |
|---|---:|
| Different player, with different realised production | $2,475,000 |
| Different signing date | $26,000 |

These are deliberately corrupted comparisons, not measured errors in the current
contract results. The existing check catches its RFA-status mutation, but misses
these identity and date changes.

Repair: before reusing common inputs, assert the same player, signing date,
start/end seasons, term, and pricing cut, together with the invariant pricing
features and floor. Forecast production fields may differ. Alternatively,
compute the realised path and discount factor independently from each arm's row
and also assert the identity/date fields explicitly, since equal dollar targets
can occur by coincidence or through the floor. Extend check 47 with player,
signing-date, season-range, and pricing-cut mutations. Matching rows must retain
the current scores. The error should name the contract and mismatched field.

The reviewer helper prototypes the identity/date assertions separately from the
candidate. Valid fixture values remain exactly equal, and mutations to the
player, signing date, starting season, ending season, and pricing cut are all
refused. The candidate implementation itself was left unchanged for Claude's
repair.

## Finding: monetary ties are unstable in the calibration calculation

The dollar scorer passes unrounded monetary values into `randomized_pit`, whose
strict `<` and `<=` comparisons require exact equality at a point mass. Values
that should be tied can differ at floating-point precision. The interval
coverage calculations also compare the unrounded amounts directly.

In the fresh primary-line results, 17 contracts in each arm have draws within
$0.000001 of the realised amount but unequal under the exact comparison. For
contract 4127, 1,254 of 2,000 draws are only $2.33e-10 away, and recognising the
tie moves its randomized percentile by 0.544. This is numerical precision being
read as a position above or below a probability mass. The affected cases are
not just the minimum-salary floor, so a floor-only adjustment is insufficient.

The reviewer recomputed calibration after rounding dollar draws and outcomes to
six decimal places. This leaves valuation scores economically unchanged and
gives:

| Statistic | Selected forecast | Previous forecast |
|---|---:|---:|
| Randomized percentile mean | 0.501 [0.484, 0.518] | 0.512 [0.495, 0.529] |
| Central 50% percentile share | 0.488 [0.459, 0.516] | 0.448 [0.419, 0.477] |
| 50% interval coverage minus own-draw coverage | -1.6 points [-4.4, +1.1] | -5.4 points [-8.2, -2.6] |

The qualitative conclusion survives: the selected forecast's pooled tests do
not reject their reference values, while the previous forecast still misses
too often in the middle. The exact calibration figures need refreshing after
the repair. Use a declared monetary precision consistently for ties and interval
membership. Keep that unit-specific convention in dollar scoring rather than
silently imposing a dollar tolerance on WAR-based calibration. Test scalar and
batched pricing of an identical path and perturbations below the declared
monetary precision.

## Interpretation and remaining scope

The two forecasts use common random numbers, with bands and dependence refitted
for each forecast. This compares their full distributions; it does not isolate
participation while holding the uncertainty model fixed.

Pooled calibration statistics that do not reject their reference values support
the stated limited conclusion: these tests did not detect pooled miscalibration.
They do not establish calibration within each subgroup. The star limitation
remains recorded. Rounded equality of two RMSE figures means approximately equal
error at that reporting precision, not an exact identity.

The scorer covers contracts' signed terms. Control-year values remain separately
reported, and goalies retain their frozen branch and its stated scope. Reserved
cohorts and a thesis back-test are not part of this review. Those limits should
remain explicit when the Player Model candidate is frozen.

## Required next action

Repair the identity/date guard and monetary tie handling. Demonstrate that the
additional mutations fail, valid valuations stay unchanged, and calibration is
stable at the declared monetary precision. Then record the candidate's
closure with its version, run commands, artifacts, and limitations. The evidence
does not call for another round of aging experiments.
