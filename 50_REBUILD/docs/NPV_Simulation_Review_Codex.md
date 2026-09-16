# Phase 5 simulation review

Reviewed 2026-09-16. Candidate `95750f5`, tested in isolated checkout
`50_REBUILD/output/simulation_review`.

## Verdict

**Not ready to close Phase 5.** The aggregate contract simulator runs and its deterministic
pricing arithmetic checks out, but historical uncertainty uses future information and
the copula does not impose the rank correlations it was fitted to reproduce. Absorbing
exits also omit the returns required by the plan; a lack of rising marginal probabilities
does not show that returns are irrelevant.

These are focused implementation and scope issues. They do not require restarting the
forecast-model search or reopening the preceding valuation-grouping review.

## Verified results

- The standard repair suite passes 24/24, with no skips.
- The new variant check fits and queries all 34 registered variants on the 2018 page.
  The previously reported component initialization defect is repaired on that tested path.
- The runner values 1,217 contracts with 2,000 paths each.
- Its 300-contract deterministic identity reports zero dollars of difference.
- An additional independent check compares deterministic simulated prices with
  `ProductionCurrency.value`, rather than using the same pricing helper on both sides:
  maximum difference $7.45e-09 across 300 contracts.
- The published dependence coefficients reproduce: permanent 0.253142, fading 0.263162,
  persistence rate 0.66; observed lag-one rank correlation rounds to 0.433.
- This rerun gives a mean simulated surplus increase of $0.188096M. The eight-year cohort
  has mean simulated surplus $5.342280M, average within-contract standard deviation
  $11.305130M and average negative-surplus probability 37.7%.
- The seven-year conditional-error dependence contrast rounds to 44%.

Not every published Monte Carlo figure reproduces exactly. Mean production here is 0.3491
point versus 0.3495 simulated, not the report's 0.3487 simulated. Eight-year mean surplus
is $5.34M, agreeing with its spread table but not its $5.39M point-comparison table.
The quoted values appear to mix run outputs. Small simulation gaps need sampling-error
qualification; their precise magnitudes are not deterministic model identities.

## Finding 1 [P1]: future calibration enters all historical simulations

In `run_npv_simulation.py:152-159`, the runner takes the latest page across the complete
contract input and fits one anchor calibrator and persistence model. Lines 206 and 215
then use that anchor's residual shape for every contract, discarding the page-specific
shapes returned by `per_season`.

The latest anchor is **2025**. Its replay contains realized residual outcomes through
**2024**. All **1,217** simulated development contracts have an earlier forecast page.
Their price equations are rolling, but their simulated uncertainty is not.

This is not merely a harmless reuse of identical parameters:

| Available forecast page | Fitted permanent weight | Fading weight | Fade rate |
| --- | ---: | ---: | ---: |
| 2015 | 0.000000 | 0.483179 | 0.82 |
| 2018 | 0.198436 | 0.367304 | 0.56 |
| 2021 | 0.249781 | 0.319737 | 0.49 |
| 2025, used globally | 0.253142 | 0.263162 | 0.66 |

The shape quantiles differ too. The early contracts therefore do not retain exactly
their own previously evaluated marginal distributions, even though their scales are
page-specific. The simulation also uses outcomes in the later calendar window reserved
for final evaluation; excluding those contracts from reported output does not remove
this parameter look-ahead.

**Required:** retain the signing-page shape and fit/cache dependence using only residual
outcomes available before that page. Add a simulation-level future-data intervention:
alter later outcomes and require earlier contract distributions/prices to remain unchanged
under fixed random draws. The existing interval-only leakage test does not cover this runner.
Reproduce the simulation report after the correction.

## Finding 2 [P2]: rank correlation is used as Gaussian correlation

`Persistence.fit` measures Spearman rank correlation at `npv_simulation.py:131`.
`matrix` then supplies those fitted values directly as correlations of the Gaussian draws.
For a Gaussian copula, a latent Gaussian correlation r implies rank correlation
6/pi * asin(r/2), which is generally not r.

Independent simulation of 600,000 two-season paths:

- Requested rank correlation: 0.426580.
- Actual simulated rank correlation: 0.409271.
- Rank correlation implied by the implemented Gaussian matrix: 0.410507.

The direction and size agree with the conversion error. More directly, the candidate's
own `self_test(n_paths=600000)` fails: adjacent correlation 0.318 versus requested 0.334.
The usual 3,000-path check passes because its tolerance cannot distinguish that discrepancy.

**Required:** fit dependence in latent-Gaussian space or convert rank targets appropriately
and verify the resulting valid correlation matrix. Test the population relationship
analytically and check simulated rank dependence with a justified Monte Carlo tolerance.
Do not solve this by further widening the tolerance.

The permanent/fading weights are parameters of this chosen dependence model. They should
not be reported as measured causal fractions of every forecast mistake.

## Finding 3 [P1 for full Phase 5 closure]: returns are excluded, not shown absent

`survival_path` at lines 191-217 makes absence absorbing. It reproduces non-increasing
participation marginals, but the plan explicitly permits an absent player to return.

A decreasing sequence can still contain returns. For example:

- 60% play both seasons.
- 30% play only the first.
- 10% play only the second.

Participation falls from 90% to 70%, yet 10% of paths return. The runner's rising-marginal
diagnostic reports zero for this example. Consequently, zero rising terms in the sample
cannot justify the report's statement that nothing is lost by omitting returns.

The effect on total-value uncertainty cannot be signed from that diagnostic alone.

**Required:** implement return-capable paths consistent with the participation design,
or explicitly obtain agreement to a reduced prototype scope and assess the absorbing
assumption as a sensitivity. Do not call the planned joint career model complete while
treating zero rising marginals as evidence that it includes every relevant transition.

## Test and reporting corrections

1. The runner's 300-contract identity calls `SIM.contract_value` on both sides. It checks
   deterministic path collapse, but a shared pricing bug could pass it. Retain the independent
   comparison with `ProductionCurrency.value` demonstrated in this review.
2. The supposed independent-seasons comparison removes conditional residual dependence but
   retains absorbing participation in both arms. Label the 44% result accordingly; the
   total season outcomes are not independent in that counterfactual.
3. A point forecast does not assume independent errors. Expectations can be averaged under
   any dependence structure. Dependence matters to uncertainty and nonlinear path valuation.
4. The one-year comparison is not exactly zero in the rerun: mean standard deviations differ
   by -0.0486%, which rounds to zero. Separate random samples need not agree exactly.
   Use common draws for an exact one-season identity or state a sampling tolerance.
5. “No sign changes anywhere” is false. There are 229 individual contract sign changes in
   this rerun, and the one- and two-year cohort means change from negative to positive.
   The fixed production-tier mean signs remain unchanged.
6. `predict_tobit` returns a linear predictor. The implemented price is that predictor
   floored by the league minimum; censoring affects the fitted coefficients but does not
   introduce a second nonlinear prediction curve. The floor is the operative convexity.
7. The eight-year summary averages statistics across 22 different contract distributions.
   Label it as a cohort summary, not one representative contract's distribution.

## Adherence to the plan and what can proceed

The aggregate conditional-season-total draw is a useful prototype for the current price
interface, which consumes average and first-season total production. Its residual already
includes both rate and availability error. This does not by itself fulfill or retire the
plan's explicit joint rate, games and participation design for all later consumers.

The RFA walk-away/control-year logic, goalie treatment and full production-spine dollar
reconciliation remain absent. The report acknowledges some of these omissions, but
“Phase 5 built” overstates completion against the written plan. In particular, absence of
a future control-year option does not imply every signed-contract downside is an option
the club could have avoided.

After the dated-calibration and correlation fixes, development can continue with a clearly
labelled aggregate simulator while the agreed remaining integration work is completed.
Final Phase 5 acceptance requires the remaining path rules, development dollar scoring and
contract-by-contract reconciliation specified by the plan.

## Reproduction and workspace scope

Added `50_REBUILD/code/review_npv_simulation.py`. Run mode executes the candidate runner
and captures its page calibrators in ignored output; audit mode examines that capture,
runs the dependence counterexample and the larger-sample self-test, and counts sign changes.

Evidence under ignored `50_REBUILD/output`:

- `simulation_review.log`: full candidate simulation.
- `simulation_checks.log`: 24/24 repair checks.
- `simulation_independent_audit.log` and `review_npv_simulation.json`: independent audit.
- `simulation_currency_identity.log`: separate pricing identity comparison.
- `simulation_replay_audit.log`: calibration dates and reproduced outputs.

No candidate implementation was changed or merged. No source or production output was
rewritten. Existing unrelated untracked documents and the `env` item were left untouched.
The first fetch approval timed out; its permitted retry succeeded.

