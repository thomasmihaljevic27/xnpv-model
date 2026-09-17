# RFA control-year repair review

Reviewed `fc4190d` on 2026-09-17 in an isolated checkout. The review does not
merge the candidate or change production.

## Decision

The four targeted repairs work, and the principal numbers reproduce. Further
prototype development can proceed. The stopping policy remains an approximation,
and the eligibility exercise is a sensitivity. Those limits need to accompany the
results before this becomes the adopted control-year valuation.

This closes the specific expiry-label filter, hidden missed-season information,
historical qualifying-offer example, and unequal pricing baseline defects. It
does not establish historically known accrued-season eligibility, optimal stopping,
accurate final-year salary costs, or completion of Phase 5.

## Reproduced results

The full suite returns **28 passed, 0 skipped, 0 failed**. The original runner
prices 398 contracts with control years, using 2,000 paths per contract.

| Rule | Mean control value, $M |
|---|---:|
| Take all control years | 0.284929 |
| Production-style point rule | 0.443230 |
| Decide in advance, matching expected-price calculation | 0.636647 |
| Informed, next-season decision only | 0.703553 |
| Informed, remaining expected seasons counted | 0.704391 |
| Best stopping date with hindsight | 0.903579 |

The informed-minus-declared difference is **$67,744.62** per contract. Adding
the remaining expected seasons to the informed decision changes the mean by
**$837.82**. Informed minus compulsory participation is **$419,462.28**.

The age audit reproduces 1,087 equal eligibility years, 130 earlier, and none
later, among 1,217 development contracts. The published age-only run has 405
contracts and a $26,318.40 mean difference on the 398 shared contracts.

Independent instrumentation changed only hidden normals from earlier seasons
with no participation. Conditional output changed by **exactly zero** across
both valuation runs, including 313,614 path histories containing an unobserved
season. The actual fitted shapes had no tied entries, and prior-season spreads
were nonzero. Those checks matter because monotonicity alone does not guarantee
that an observed value uniquely identifies a latent normal draw.

I independently reintroduced the expiry argument, conditioning on unplayed
seasons, future offer bands, and the first-loss stopping rule. Checks 26-28 reject
all four mutations. The signature check protects that interface; it is not a
general test of whether all upstream eligibility fields were known at signing.

## 1. Remaining expected profits are not the full continuation option [P2]

`control_years.py:467-481` takes the largest cumulative sum of expected annual
profits. At each later date it repeats that calculation with updated information.
This is a feasible policy that considers later seasons. It does not calculate
the value of retaining the ability to stop after future information arrives.

The distinction changes decisions even with the module's Gaussian information
model and its floored linear price. The independent `policy` probe supplies two
control seasons, certain participation, unit offers and discount factors, means
0.99/0.90, spreads 0.01/0.50, and correlation 0.90. The production observation in
the first season reveals its shock. The future shock is never observed early.

The current expected surpluses are -0.0100 and -0.0933. The implemented policy
therefore stops on all 40,000 paths for value zero. A feasible alternative takes
the first season and then qualifies for the second only when its conditional
expected surplus is positive. That earns **0.12336 units**, with simulation
standard error 0.00138. This constructed example demonstrates a missing option;
it does not estimate the size of the omission on the 398 actual contracts.

The $67,745 comparison remains interpretable as the gain from observed history
under the specified policy and matched pricing. The $838 comparison measures the
effect of adding expected future profits to that policy. It cannot establish that
the full continuation option is negligible. Likewise, $419,462 is the gain from
this walk-away policy over the obligation, not an estimate proven optimal.

For the next development step, label the rule as an approximate policy and retain
this limitation. A claim to the full option value would instead require a backward
calculation that includes the value of future choices, plus a test with uncertain
future information. The deterministic +5/-1/+10 check cannot establish that.

## 2. The age exercise changes draws and does not establish a value bound [P2]

`run_control_years.py:317-337` restarts the same random seed, but consumes a
variable number of draws per contract. Adding contracts or extending a horizon
shifts later draws. The two eligibility runs consequently do not share paths for
unchanged contracts.

Of the 398 shared contracts, 356 have identical control windows. Their reported
values nevertheless differ by $391.36 on average and by as much as $235,365.54
in absolute value for one contract. Thus the published $26,318 difference includes
simulation noise from contracts whose eligibility treatment did not change.

The review also reruns both arms with a contract-specific seed and fixed-width
draw arrays, so matching seasons receive the same performance and participation
draws. The mean difference is **$25,866.86** on the 398 shared contracts;
all 356 unchanged windows now give exactly identical values. The aggregate
result still rounds to $0.026M, so correcting the draw pairing does not overturn
this sensitivity result.

An age-only window is an upper limit on years under the two eligibility routes
modelled here. This alone does not make the difference between two simulated
policies a bound on historical eligibility bias. The export still supplies the
baseline eligibility year without reconstructing accrued seasons known at signing.
Describe the exercise as sensitivity to that input. A historically admissible
eligibility model remains necessary before adoption.

## Reporting corrections

- The production-zero breakdown in the report is **97 no-QO, 33 plain UFA,
  and 57 RFA**, totalling 187. The chat's "130 no-QO" is incorrect. Do not
  infer that all plain-UFA records describe a non-qualification decision.
- The salary paragraph retains the previous reversed front-loading explanation.
  Front-loading places more salary early, not in the final year. The actual
  runner now reports 650 within 1%, 232 above, and 23 below among 905 broader
  input records; the report still quotes 421/155/17 among 593. Neither table
  establishes the dollar bias on the 398 valuation contracts. Report that sample
  separately, and retain both directions of the cost approximation.
- The six adjacent rules do not each change only one thing. The specifically
  paired informed/declared and informed/myopic comparisons are the useful ones.
- $0.068M is about one quarter of the $0.267M gap between declared and hindsight,
  not one tenth as written in the report.

## Reproduction and scope

`50_REBUILD/code/review_control_repairs.py` provides setup, checks, original-run,
audit, mutation, policy-example, and paired-draw modes. Evidence is ignored under
`50_REBUILD/output/`: `control_repair_*` and `control_paired_*`. Vendor inputs are
read-only. Production inputs come from the previously regenerated isolated
production output directory. No canonical output is overwritten.

The plan still requires the goalie branch and tender gate, the joint production
and participation design, development dollar scoring, and the declared back-test.
The prior reconciliation and simulator review closures stand within their scopes.
