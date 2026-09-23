# Goalie participation snapshot candidate: independent review

Reviewed 2026-09-22. Candidate `c4ddcf0`, isolated in
`50_REBUILD/output/goalie_participation_top_review`. No adoption or candidate merge.

## Decision

The old export-membership signal should not be defended by its existing score.
The reported candidate improves on it, and the implementation behaves as
documented. However, do not adopt the proposed specification on the claim that
the improvement establishes useful contract-status information. One intermediate
comparison is missing, and it changes that interpretation.

Keep the participation decision open for this specific comparison. Earlier
review closures remain closed. This is not a request to rebuild the forecast or
repeat the completed currency and calibration repairs.

## Finding: the new unknown flag is a time indicator [P2]

`participation_model.py:287` replaces player-level missingness with
`season < coverage_from_`. In this export that is exactly a before/after-2018
indicator, the same for every player targeting the same season. The proposed
model therefore has two potentially useful inputs: this time indicator and
whether the player is under a visible contract.

The report compares their combined effect with removing both, then says
"Contract state carries real information once it stops carrying survival."
That comparison cannot attribute the gain to contract status.

The review separately removed each new input, retaining the same rolling fits,
production forecast, trailing games share, outcome cells and career-resampling
procedure. All versions have 3,683 scored cells:

| Participation specification | Brier score | Season WAR RMSE |
|---|---:|---:|
| Current export-membership definition | 0.205589 | 2.073319 |
| Neither contract input | 0.195769 | 2.065093 |
| Proposed observable definition: both inputs | 0.194038 | 2.061840 |
| **Before/after-2018 indicator only** | **0.192665** | **2.061686** |
| Observable under-contract status only | 0.195583 | 2.065049 |

The time-indicator-only version beats the proposed combination on Brier score
in **91.2%** of career resamples; WAR squared error is essentially tied
(55.45%). Against neither input, the time indicator wins on Brier in 99.95%
and on WAR squared error in 98.55%. Under-contract status alone has only 67.05%
and 51.15% win shares against neither input.

The time-only version also removes the confident-fifth discrepancy: predicted
minus observed participation is **-0.0013**, with a career-resampled interval
of **-0.0380 to +0.0428**. These are each model's own prediction fifths, as in
the candidate runner; the original high-confidence membership is not held fixed.

**Required correction:** include both intermediate specifications in the
declared comparison, withdraw attribution of the gain to contract information,
and distinguish the temporal adjustment from an observation-coverage rule when
choosing the specification. A different participation rate after 2018 may be
useful predictively; these results do not establish why it changed or that
2018 is a generally appropriate modelling boundary. Do not automatically adopt
the time-only arm on this review's sample either.

The result supports removing the old export-membership signal. It does not
prove that contract status is useless, nor does it establish that the new
combined specification is the best way to replace that signal.

## What reproduced

- **41 checks passed, no skips or failures.** Check 41 fails when the constructor
  ignores the new option. It verifies the implemented definition, not independent
  completeness of the vendor's records.
- The three published season-level scores, confident-fifth calibration results,
  and 93%/97% comparisons with the no-contract-data baseline reproduce.
- The current model's confident-fifth gap is +0.095995. The proposed version's
  gap is +0.005131; the no-contract-data version's is -0.003320.
- Source inspection confirms that the contract-state lookup filters contracts
  by their signing date and fits only completed outcomes before the forecast
  page. The new option remains opt-in. The coverage boundary is inferred from
  the source's earliest end year; it is not a player-specific future outcome.

The report explicitly treats completeness from 2018 onward as an assumption.
That qualification must remain: finding no earlier records does not independently
prove that all later contracts are present. The phrase "true contract state"
in the check is conditional on that assumption.

## Scope of the dollar interpretation

Both control-year runners and their fixed-line cross-run comparison were rerun.
On the current run's production price line, all four predictions share the same
133 realised targets:

| Ability forecast | Participation | Simulated RMSE, $M | Bias, $M | Candidate wins on squared error |
|---|---|---:|---:|---:|
| Production | Current | 6.882 | +0.566 | |
| Production | Proposed observable | 6.879 | +0.187 | 51% |
| Rate | Current | 6.923 | -0.159 | |
| Rate | Proposed observable | 6.961 | -0.475 | 24% |

The sensitivity price line gives 58% and 30% win shares, respectively. These
reproduce the reported substantive results; a few last printed digits differ
slightly (for example 6.879 versus the report's 6.880). Within-run floor excesses
also reproduce: production 13.9 to 7.1 percentage points, rate 10.2 to 4.1.
The unchanged default's realised targets, point values and simulated means
match the preceding closure run exactly after CSV loading. This review did not
independently rerun and hash all three older goalie bake-off output files; it
does not certify the separate byte-identity claim.

The cross-run repricing is correctly structured around one reference price
line, applied to both runs and both ability forecasts. It asserts that their
realised-dollar targets agree. That preserves the previous review's correction.
The participation experiment does not establish that the remaining large
contract errors are irreducible noise. It shows that this particular change
does not materially lower production's squared dollar error; model error can
remain elsewhere. Similarly, improved pooled or fifth-level calibration is
not proof of full conditional calibration.

The separate time-indicator and contract-only arms have been scored in seasons
by this review, not carried through the contract simulator. Their dollar effects
are therefore not claimed here.

## Reproduction

`50_REBUILD/code/review_goalie_participation_top.py` provides `setup`, `checks`,
`top`, `ablation`, `summary`, `mutant`, `control-current`, `control-observable`
and `dollars` modes. Generated evidence is ignored under `50_REBUILD/output/`,
prefixed `goalie_participation_top_`.

Resampling uses the same 2,000 career draws with group sums rather than repeated
DataFrame concatenation. The season-level paired and calibration implementations
were checked against the original functions on 30 resamples; probabilities agree
exactly and interval values agree to 1e-12. The same reporting optimization used
and verified in the preceding closure review accelerates the control runners.
No model fitting, forecast or path simulation is changed by that optimization.
