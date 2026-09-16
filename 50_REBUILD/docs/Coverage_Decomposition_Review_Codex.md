# Coverage diagnostic fact check

Reviewed 2026-09-15. Candidate commit: `c4c41f4`.
Isolated checkout: `50_REBUILD/output/coverage_review`.

## Conclusion

Claude's numerical tables reproduce. The participation errors are useful evidence of
subgroup miscalibration. The diagnostic does not establish three distinct causes, an upper
bound on any repair's benefit, or that young-player error is mainly participation.
The three previously repaired implementation findings remain closed.

Recommendation: record the measured limitations and continue the remaining rebuild work.
Do not start another open-ended tuning cycle on the strength of these causal claims.
The final valuation assessment must still test whether errors concentrated among stars and
young players change the thesis's trade-category results. That check is part of assessing
the model's usefulness, not a requirement to eliminate every prediction error.

## What the report means in ordinary language

The model estimates whether a player will play, how much of the schedule he will play,
his production rate, and the range around the resulting season total. Claude changed some
of those estimates after seeing the answers and counted how often the resulting ranges
contained the outcomes. The exercise shows sensitivity to those particular adjustments.

At h5, the reported star interval covers 60.2% rather than the intended 80%. The reported
36% gain from stretching the distribution closes 36% of that 19.8-percentage-point gap:
coverage becomes 67.3%. It does not mean 36 percentage points of improvement.
The joint 112% closes slightly more than the gap, producing 82.5% coverage; coverage
itself never exceeds 100%.

## Finding 1: the adjustments are not oracle ceilings

In `run_coverage_decomposition.py:105-145`, the centre matches a median of standardized
played-season errors, the scale matches a middle-90% span, and participation is replaced
by a constant subgroup play rate. None optimizes the stated 80% coverage objective.
Knowing the outcomes does not turn an arbitrary adjustment into the best achievable one.

Counterexamples on the exact same scored rows and final-year shape used by the report:

| Group / horizon | Base | Reported centre adjustment | Best centre on tested grid | Reported spread adjustment | Twice the original spread |
| --- | ---: | ---: | ---: | ---: | ---: |
| Stars h5 | 60.23% | 64.91% | 68.42% | 67.25% | 88.30% |
| Age <=22 h5 | 66.32% | 65.08% | 69.42% | 75.62% | 89.67% |

The grid uses a common standardized shift from -2 to +2 in increments of 0.025.
It is only a counterexample, not proof that the grid result is an optimum.
Doubling spread is not a model recommendation: coverage alone rewards wider intervals.
It disproves the alleged upper bound and the deduction that three distinct defects have
been identified because no single adjustment could close the gap.

Likewise, one median adjustment worsening young-player coverage does not rule out a
better ability forecast or prospect information. Median alignment among played seasons,
unconditional 80% coverage, and mean forecast accuracy are different objectives.
Replacing individual participation probabilities with one subgroup constant also removes
their within-group differences. Its result cannot isolate correction of the group mean.

## Finding 2: the point-bias table is not a decomposition

Lines 279-305 print season-total WAR error, conditional per-82 rate error, conditional
games-share error and participation probability error. These are valid descriptive
statistics, but their units and samples differ. They are not additive contributions to
the total error. In particular, -0.114 probability error is not -0.114 WAR.

An exact sequential accounting provides a check. Write the prediction as p*r*g and the
observed participation indicator as D. Replace p with D, then r with the realized rate,
then g with realized games share. Average over all subgroup rows:

- Participation contribution: average of (p-D)*r*g.
- Rate contribution: average of D*(r-r_actual)*g.
- Games contribution: average of D*r_actual*(g-g_actual).
- Small source-identity remainder: actual rate times capped games share minus actual WAR.

| Group / horizon | Total error (WAR) | Participation | Rate | Games | Identity remainder |
| --- | ---: | ---: | ---: | ---: | ---: |
| Stars h3 | -0.64654 | -0.00449 | -0.50659 | -0.13546 | approximately 0 |
| Stars h5 | -0.86594 | -0.10073 | -0.67953 | -0.08568 | approximately 0 |
| Age <=22 h3 | -0.34002 | -0.06133 | -0.07160 | -0.20670 | -0.00038 |
| Age <=22 h5 | -0.40689 | -0.07486 | -0.25635 | -0.07568 | approximately 0 |

The remainder comes from the existing games-share cap at one for a few observed totals
above the configured schedule length; the table's own identity guard already documents
that exception. It is not a new implementation finding.

This is an exact accounting in one stated order, not a causal decomposition. Changing
replacement order reallocates interactions. It supports a substantial star rate error
but contradicts treating the young h3 result as established evidence of almost exclusively
participation error. Games cannot be discarded.

## Finding 3: the new diagnostic substitutes the final year's shape again

At line 185, every evaluation year receives the 2021 residual shape. Scales remain
year-specific. The comment's claim that all reported quantiles differ by less than 0.01
is false: the largest difference from 2021 among the checked quantiles is 0.03049.

This changes the baseline the diagnostic claims to explain:

| Star horizon | Diagnostic baseline | Actual intervals using each year's shape |
| --- | ---: | ---: |
| h3 | 72.91% | 73.89% |
| h5 | 60.23% | 60.82% |

The changes are small, but represent actual rows and alter gap percentages.
The prior repaired wrapper and uncertainty runner remain correct. This is a shortcut in
the new diagnostic, not evidence that those previous fixes were reverted.

## Participation: what is established

The reported probabilities reproduce. Young players at h5 are predicted to play at 67.7%
against 80.4% observed; stars at 78.1% against 88.3%. Age 34+ at h0 is predicted at 49.1%
against 37.3%. These are observed subgroup calibration errors on development pages.

Several stronger statements do not follow:

- The pattern is not uniformly one-directional: stars are slightly overpredicted at h0-h3,
  and below-zero players are underpredicted at h3-h5.
- Participation does not improve every undercovered group: the 1-to-2 tier's coverage falls
  from 76.1% to 75.5% at h3 and from 78.6% to 78.1% at h4.
- Overall mean probability errors can offset. Squared individual probability errors do not
  cancel by sign. A Brier score combines calibration, discrimination and outcome uncertainty;
  a roughly flat score does not isolate subgroup calibration. See the
  [official calibration documentation](https://scikit-learn.org/1.8/modules/calibration.html).
- The current leader uses imputation for the aging selection adjustment. The alternative
  inverse-probability aging weights use their own retention fit. Editing the participation
  model does not automatically repair either aging approach.
- Star h5 has 171 rows but only 81 distinct careers; h0-h4 have 203 rows and 88 careers.
  Repeated players limit how much independent evidence those row counts represent.

## Is this selection bias, and can it remain a limitation?

Selection/survivorship is a plausible contributor when observed future performance comes
only from players who remain in the league. Identifying that mechanism requires assumptions
about who becomes observable and how that relates to performance; a calibration table alone
does not identify it. See the methodological discussion of
[endogenous selection](https://pmc.ncbi.nlm.nih.gov/articles/PMC6089543/).

The harness retains absent players as zero season totals. Conditional rate evaluation
among players who played is appropriate for a forecast explicitly conditional on playing.
Neither fact guarantees the model's treatment of selection is adequate, but these results
are not simply the error caused by dropping all retirees from the test sample.
The current model already attempts a selection adjustment by imputing missing aging outcomes;
that assumption itself remains something to assess.

Use the measured description: **long-horizon subgroup miscalibration, with the respective
roles of participation, games played, rate forecasts and selection unresolved.**

It is reasonable to document this now and continue implementation. Reserve any stronger
claim of reliable subgroup intervals or robust trade-mispricing conclusions for the final
evaluation. Participation and mean errors also change expected production, so this limitation
is not confined to the visual width of an interval.

## Reproduction

Added `50_REBUILD/code/review_coverage_decomposition.py`.
It executes the candidate diagnostic with local merged ages (98.4% coverage on development
pages), captures all 40,510 scored rows and year-specific shapes, then performs the independent
counterexamples and common-unit accounting above. No replacement forecast was fitted or adopted.
No holdout was used and no candidate implementation was merged.

Local ignored evidence:
- `50_REBUILD/output/coverage_decomposition_review.log`: complete candidate output;
  the first audit assertion then exposed the documented source-identity exception.
- `50_REBUILD/output/coverage_decomposition_independent.log`: successful independent audit
  rerun on the captured rows, with that small remainder explicitly accounted for.
- `50_REBUILD/output/review_coverage_decomposition.json`: numerical audit results.

The optional `--reuse-scored` flag uses the immediately preceding local capture. Without
that flag the script runs the candidate again. Source and generated player data remain ignored.

