# Goalie price-line review

Reviewed `16d1d5f` in an isolated checkout. Runs began on 2026-09-18; review
completed on 2026-09-22. Production code and canonical outputs were unchanged.

## Decision

The implementation runs and its reported results reproduce. Two conclusions need
correction before this closes the price-line question: the comparison does not
establish that both goalie terms are needed, and the dollar-per-win table describes
only a particular partial coefficient of the fitted price equation.

The goalie participation prototype can proceed while the price specification stays
provisional. The preceding goalie forecast review remains closed. Do not record
the two-term specification as a settled D7 result on this evidence.

## What reproduced

- Full suite: **33 passed, 0 skipped, 0 failed**.
- The original fit and scoring run reproduces the published slopes and errors.
  All 52 executed fits captured in that run report successful optimizer termination.
- There are 174 identical goalie contracts in the two pooled-line error comparisons.
  The assembled sample has no duplicate contract IDs.
- Independently replacing the goalie slope with the interaction alone, and allowing
  future signings into training, both make check 33 fail.
- The bias qualification reproduces: career-bootstrap interval approximately
  [-0.129, +0.315], predicted participation 64.1%, observed 55.3%. No price was
  shifted to cancel the observed WAR bias.

## 1. A different goalie price level explains the measured gain [P2]

The runner compares a pooled line without goalie terms to a pooled line with both
`is_G` and `g_x_war`. It concludes that both the level and slope differ. That
comparison only tests the two additions together. It cannot establish that the
slope interaction contributes beyond a different goalie price level.

The independent audit adds the missing level-only challenger, with the same
training contracts, signing-quarter cutoffs, censoring model, minimum sample,
price floor, and 174 scored contracts.

| Pooled specification | Goalie contracts | MAE, cap share | Mean error |
|---|---:|---:|---:|
| No goalie terms | 174 | 0.0103179 | +0.0066271 |
| Goalie price-level term only | 174 | **0.0074561** | +0.0001448 |
| Goalie level and slope terms | 174 | 0.0074891 | +0.0001415 |

The level-only line achieves the error reduction and near-zero mean error. Adding
the slope slightly increases MAE by 0.0000330 cap share. A bootstrap resampling
goalies, while keeping each goalie's paired contracts together, gives a 95%
interval of **[-0.0000161, +0.0000824]** for that difference. It is inconclusive.

Required correction: include the level-only challenger and withdraw the claim that
both terms are established, or that the two-term line is the only defensible pooled
specification. A goalie adjustment is supported by this development comparison;
the incremental benefit of a goalie win-slope term is not demonstrated. This does
not prove the population slopes are equal.

## 2. The dollar-per-win table omits other changing regressors [P2]

`run_goalie_price_line.py:dollars_per_win` takes the `war_per_season` coefficient,
adds `g_x_war` for goalies, and multiplies by the cap. The fitted equation also
contains `war_year1` and `is_RFA * war_per_season`.

Thus the published numbers describe a **UFA partial slope with first-year
production held fixed**, before the price floor. They are not a general price
response to increasing a player's forecast production. The conditional-association
caveat addresses causality, but does not specify this omitted distinction.

For a defined intervention of one additional expected win in each contract season,
with term and rights fixed, both average and first-year production increase by one.
The latent per-season dollar response is:

`cap * (b_average + b_first_year + is_RFA*b_RFA_interaction + is_G*b_goalie_interaction)`

Using the last fit and its own $83.945M cap conversion:

| Change in forecast | Skater, $M | Goalie, $M |
|---|---:|---:|
| Published UFA partial slope, first year fixed | 0.819 | 0.964 |
| UFA: +1 expected win in each season | **2.022** | **2.167** |
| RFA: +1 expected win in each season | **1.928** | **2.073** |

These are per-season latent price responses, not total contract NPVs. Directly
perturbing the fitted price inputs reproduces the complete responses to within
$0.000001. The UFA whole-path ratio is about **1.07**, rather than the reported
partial-slope ratio of 1.18. At the binding salary floor, the realized price response
also depends on whether the change moves the contract above the floor.

The goalie-minus-skater interaction remains the fitted conditional difference for
matched rights and forecast changes: common first-year and RFA terms cancel in
that difference. The problem is the unqualified interpretation of the levels and
ratios, not the addition of the interaction itself.

Required correction: declare the forecast change and rights status the table
measures. Either label it as a partial coefficient table, or calculate the full
price response through all affected features and the floor. Extend the synthetic
check to include a nonzero first-year coefficient and RFA cases. Its current
synthetic first-year coefficient is zero, so it cannot expose this omission.

## Sample and reporting corrections

- The shared census returns **263 eligible development goalie contracts** after its
  signing-date and other guards. **205** receive forecasts and enter the pooled
  development frame; **174** receive rolling pooled prices. The report's 266 should
  not be described as the number available to fit the goalie-only line.
- The goalie-only line prices five contracts under the chosen **200-observation
  minimum**. That supports calling it too limited to compare under this protocol,
  not declaring separate estimation inherently impossible.
- All three lines use contracts signed before each quarterly cutoff, which is an
  expanding training sample. The goalie-only line does not use a different window
  scheme from the pooled lines, despite the runner's explanation.
- The new +0.167 WAR participation calculation assigns the same 1.89 WAR to each
  played season. It is an illustrative calculation using the average participation
  gap, not a decomposition proving how much observed bias participation caused.
  Preserve the diagnostic qualification when describing it.

## Reproduction and next work

`50_REBUILD/code/review_goalie_price.py` provides setup, original-run capture,
full checks, independent level-only comparison and derivative audit, two mutation
checks, and the bias qualification rerun. Generated evidence is ignored under
`50_REBUILD/output/goalie_price_*`.

Keep the price-line experiment and the shared position-aware census. Correct the
specification claim and coefficient interpretation before adopting a goalie currency.
Participation, the goalie control-year gate, dollar scoring, and the declared
back-test remain open. No confirmatory market cohorts were scored or candidate
implementation merged by this review.
