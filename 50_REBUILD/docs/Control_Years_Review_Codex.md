# RFA control-year implementation review

Reviewed `61c62bc` on 2026-09-17 in an isolated checkout.

## Decision

The implementation runs and its principal numbers reproduce. The RFA/control-year
item is not ready to close. Historical ownership uses a later non-qualification
outcome; the informed rule observes hidden performance shocks from missed seasons;
future qualifying-offer bands enter an earlier valuation; and the reported policy
difference does not isolate the value of new information or solve optimal stopping.
These findings concern the new control-year work. The earlier reconciliation and
simulation repair closures remain valid within their reviewed scopes.

## 1. Later non-qualification is used to remove rights at signing [P1]

`control_years.py:182-200` returns no control years unless the export's
`expiry_status` is exactly `RFA`. The runner uses that rule for a signing-date value.
Its explanation treats `UFA no QO` as a decision the club has already made, although
the valuation precedes the expiry and the non-qualification decision.

In the 1,217 development contracts the export has 862 UFA, 254 RFA and **101
UFA no QO** records. All 101 excluded no-QO records have a listed `ufa_year` after
their contract's end year. For example, contract 4260 was signed 2018-06-25, ends in
season 2018, and lists UFA eligibility in 2020; the code suppresses the intervening
control season because of the later no-QO status.

Non-qualification changes free-agent status. See the NHL's description of
[non-qualified players](https://www.nhl.com/news/free-agency-signings-2020-299340484).
Using that later choice to define rights at signing is outcome selection. A simulated
walk-away rule must make the choice; the actual future decision cannot remove the
candidate before simulation. The current 252 is therefore a selected population,
not a verified count of all signing-date rights in the development sample.

Required: derive eligibility and ownership from information available at the valuation
date, retain later tender/non-tender outcomes for evaluation, and audit these 101 cases.
Do not simply relabel all of them RFA without checking age, service and the provenance
of `ufa_year`. Add a test that changing future non-qualification labels leaves the
signing-date valuation population unchanged.

## 2. The informed rule sees performance shocks when the player did not play [P1]

`conditional_nodes` at lines 265-297 conditions on every past latent normal in
`g[:, :j]`. The simulation draws those normals even when `played == 0`; the observed
season total is then zero regardless of the unobserved performance shock.
`value_paths` passes the complete latent history into `expected_surplus`.

The club can observe whether the player played. It cannot infer the unrealized NHL
performance shock from an absent season under the model's stated observation process.
The current implementation supplies that hidden variable directly to its decision rule.
No separate observable scouting signal for it is defined.

I instrumented the actual 252-contract run. At the first control-year decision I held
all realized production, participation, observed played-season history and forecast
inputs fixed, and added three only to past latent normals in seasons with zero
participation. The decision should be invariant to those hidden changes.

- First-control decisions change in **188 of 252 contracts**.
- **26,519 of 504,000** tested path decisions flip.
- The largest change in expected annual surplus is about **$2.83M**.

This is an intentionally strong invariance test, not an estimate of the bias in
the published value. It demonstrates dependence on unavailable information.

Check 28 only scrambles future normals. It correctly prevents future-column access
but does not test whether the past variables it supplies are observable. Requiring
the rule to respond to every past shock can reward this defect.

Required: condition on observed played-season production and participation history,
integrating out performance shocks from absent seasons. If an additional signal is
intended, specify and simulate that signal explicitly. Add a guard that hidden-shock
changes leave the actual control decision unchanged, then regenerate the informed
values. Until then, the $0.716M mean is not a value based solely on stated observations.

## 3. Qualifying-offer bands are not dated to the valuation [P2]

`qualifying_offer` switches to new bands solely on `offseason_year >= 2026`.
The caller dates the league-minimum floor, but not the offer formula itself.
The new agreement was ratified in July 2025, after the historical decisions here.
See the [NHLPA ratification announcement](https://www.nhlpa.com/news/nhl-nhlpa-ratify-four-year-collective-bargaining-agreement/).

A direct example: a 2019-07-01 valuation with a $1.2M salary produces a $1.32M
offer in 2026. Keeping the same dated floor and using the old bands gives $1.2M.

One of the 252 priced contracts reaches the new bands: **6876**, signed
2021-08-06, with control years 2022-2026. Its first four offers are unchanged, but
the 2026 offer is **$1.10M instead of $1.00M** under the rule knowable at signing.
The agreement with production's formula on 4,000 cases verifies copying consistency,
not the historical information boundary.

Required: select the offer regime from dated information and document the assumption
for control years beyond an agreement known at signing. Apply real announcement/effective
dates rather than broad calendar-year approximations. Add a future-policy intervention
test that holds all pre-decision information fixed.

## 4. The informed policy is myopic, and its comparison changes more than information [P2]

`take_matrix` at lines 393-408 retains a right only while each current expected
season surplus is positive. It does not include the value of preserving later rights.
The same continuation issue already fixed for the oracle also applies to a feasible
decision rule, even without uncertainty.

For known payoffs **+5, -1, +10**, the implemented informed policy earns **5**;
committing to all three earns **14**. Nothing in that example requires hindsight.
Thus the informed rule is not generally optimal, and it is not guaranteed to dominate
the committed or declared rules. It is a feasible myopic policy once its observation
set is repaired. Twelve actual contract means fall below the declared-policy means;
that fact alone is not a bug, but a dominance claim is unsupported.

The declared policy also evaluates the price of expected production, while the
informed policy integrates the price over production uncertainty. The floor makes
those different before any new information arrives.

I tested a synthetic one-season decision with certain participation, independent
errors and a floored linear value function. Past observations convey no information.
The declared criterion is **-0.100** and the informed criterion is **+0.277**, so
the policies make different decisions solely because one integrates the distribution.
Those are arbitrary consistent monetary units, not a claim about a real contract.

Required: either implement a stopping policy that includes expected continuation
value, or label the result as a myopic-policy valuation rather than the value of the
right itself. To isolate new information, compare policies using the same valuation
functional and continuation logic while changing only their observation sets. Keep
D13's existing point policy as a separately named baseline. The current $0.266M
informed-minus-declared difference combines multiple changes and cannot be called a
pure information or adaptive-option premium.

## Salary approximation: keep it, but correct the explanation

The diagnostic reproduces **421 approximately equal, 155 higher and 17 lower**
final-year salary/AAV comparisons among 593 records with salaries. These are drawn
from the broader control-candidate input, not just the 252 priced development contracts.

The claim that the approximation has only one direction is not established: replacing
final salary with AAV can understate or overstate it, and floors and caps affect the
resulting offer. Front-loaded means larger payments earlier, not a higher final salary.
The report reverses that explanation. Correct the wording and distinguish the count
diagnostic from a measured dollar effect on this development sample. Prior identified
season-spine cost inconsistencies also counsel against treating every salary entry as
a validated reference automatically.

## Reproduction and test coverage

- Full suite: **28 passed, 0 skipped, 0 failed**.
- Full control runner: **252 contracts**, 2,000 paths each, 19 output columns.
- Mean values: committed **$0.135558M**, declared **$0.450621M**, informed
  **$0.716276M**, hindsight **$0.949574M**.
- The one- and two-control-year tables reproduce at the quoted precision.
- Production comparison: 241 matches, rank correlation **0.547** for declared and
  **0.762** for informed locally (versus the quoted 0.759).
- The best-prefix hindsight ceiling is correct for irreversible stopping, and the
  shared-draw comparison is implemented. Neither proves the observation set is valid.

The audit driver `50_REBUILD/code/review_control_years.py` has `run`, `checks` and
`audit` modes. The run instruments the new consumer without changing its outputs;
the other modes run the full suite and independent counterexamples. Candidate code
and production files are unmodified. Evidence is ignored under `50_REBUILD/output/`:
`control_review_run.log`, `control_review_checks.log`, `control_hidden_information.json`,
`control_independent_audit.json`, and the isolated candidate's `control_years.csv`.

No adoption, production-input correction, candidate merge or implementation repair
was performed during this review. Rebuild documentation remains in `50_REBUILD/docs/`.
