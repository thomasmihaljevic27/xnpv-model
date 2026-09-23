# Should the skater leader's participation use contract data? A matched test

Run 2026-09-23 in `50_REBUILD/` (`run_skater_contract_test.py` v1.1; `ability_forecast.py` v1.9;
`contract_price_model.py` v1.5).
Development pages and development start years only. **Nothing adopted.**

## The question

The standing skater leader forecasts whether a player plays **without** contract data. The earlier
ablation that seemed to justify that was withdrawn for two reasons:
- part of its result came from a defect in the participation fit, fixed on 2026-09-22;
- it used a different ability configuration from the leader.

Two things were then needed:
- **a matched test**, in which the leader is compared only with versions of itself that differ in
  the contract inputs its participation model reads;
- **the goalie lesson applied.** The vendor contract export is a snapshot of contracts ending in 2018
  or later, so the old contract fields can encode survival. The two inputs the replacement
  definition carries have to be scored separately.

## The five versions, matched

Every version is the leader (`A1HingeExposure`) with one thing changed: the contract inputs of its
participation model. Ability, aging, the rate and games halves, and the harness are identical.

| version | participation's contract inputs |
|---|---|
| leader | none (the standing leader) |
| as known | export membership and contract status as known (the old definition) |
| observable | a before/after-2018 period indicator and visible contract status |
| period only | the period indicator alone |
| contract only | visible contract status alone |

Visible contract status counts only deals covering seasons from 2018, the export's earliest end
year, where any covering contract must be in the export *if the vendor's snapshot is complete*. That
completeness is assumed, not verified.

**The scoring was declared before the run:**
1. **participation:** the Brier score, and the calibration of each version's most confident fifth;
2. **season WAR:** squared error primary, with absolute error and bias beside it;
3. **contract dollars:** every version's point valuation, and the WAR each player actually
   delivered, priced on **one** fixed line, the leader's.

The dollar target is asserted identical across versions, and ended terms only are scored.
Comparisons resample players, since one career contributes many forecasts.

## The skater export carries survival too, more mildly

Share of skater anchors the export knows, under a visible contract, and how often each group played:

| page | seasons ahead | known | under | played if unknown | played if known, not under (n) | played if under |
|---|---|---:|---:|---:|---:|---:|
| 2010 | next | 0.01 | 0.01 | 0.69 | — (0) | 1.00 |
| 2014 | next | 0.07 | 0.07 | 0.70 | — (0) | 0.98 |
| 2016 | next | 0.18 | 0.18 | 0.62 | 1.00 (2) | 0.97 |
| 2019 | next | 0.87 | 0.64 | 0.04 | 0.54 (236) | 0.91 |
| 2022 | next | 0.98 | 0.54 | 0.65 | 0.54 (438) | 0.92 |
| 2010 | three | 0.01 | 0.01 | 0.46 | — (0) | 1.00 |
| 2015 | three | 0.11 | 0.11 | 0.39 | — (0) | 0.86 |
| 2019 | three | 0.87 | 0.12 | 0.02 | 0.56 (753) | 0.88 |

The full table is in the run log.

On the early pages a skater under a visible contract played the next season 97–100% of the time,
against 90–92% from 2018. The same survival signal is present as for goaltenders, but the gap is
smaller (about eight points, against about fifteen for goaltenders).

## Participation and season WAR

40,510 forecasts per version, development pages, zero to five seasons ahead. "Beats leader" is the
share of player-resamples in which the version's error is lower.

| version | Brier | beats leader | season WAR RMSE | beats leader | WAR MAE | bias |
|---|---:|---:|---:|---:|---:|---:|
| leader | 0.1340 | — | 0.8155 | — | 0.4565 | −0.068 |
| as known | 0.1326 | 100% | 0.8147 | 100% | 0.4571 | −0.064 |
| observable | 0.1328 | 99% | 0.8150 | 100% | 0.4550 | −0.069 |
| period only | 0.1340 | 29% | 0.8156 | 27% | 0.4560 | −0.069 |
| **contract only** | 0.1328 | **100%** | 0.8151 | **100%** | 0.4565 | −0.067 |

**The inputs separated** (share in which the first-named is lower; Brier / WAR squared error):

| comparison | Brier | WAR squared error |
|---|---:|---:|
| period only against leader | 29% | 27% |
| contract only against leader | 100% | 100% |
| observable against contract only | 48% | 73% |
| observable against period only | 100% | 100% |

**The confident fifth** (predicted minus observed participation, player-resampled interval):

| version | over-prediction |
|---|---:|
| leader | −0.015 [−0.021, −0.008] |
| as known | +0.004 [−0.002, +0.011] |
| observable | −0.012 [−0.018, −0.005] |
| period only | −0.017 [−0.023, −0.010] |
| contract only | −0.010 [−0.016, −0.004] |

What this says:
- **For skaters the period indicator does nothing** (29%, 27%). This is the opposite of goaltenders,
  where it carried the whole gain.
- **Visible contract status helps, consistently but very little.** Contract only beats the leader in
  every resample on both scores, but season WAR RMSE moves from 0.8155 to 0.8151, 0.05%. Adding the
  period indicator on top does not separate from contract only.
- **The old definition scores about as well** (0.1326, 0.8147), and it is the only version whose
  confident fifth is calibrated. It also carries the survival signal above, so its score is not
  evidence that it measures what it claims.
- **One caution about "contract only".** Under the observable definition, visible status is zero
  for every row targeting a season before 2018. So its coefficient partly contrasts post-2018
  contracted players with all pre-2018 rows. That the period indicator alone does nothing makes a
  pure period effect an unlikely explanation. It does not fully separate the two.

## Contract dollars on one fixed line

**Contract state is read at each contract's signing.** Version 1.0 of this test valued contracts
with participation's contract state read at 1 July of the valuation page. So a deal signed later in
the year was valued by a model that did not know it had been signed: under visible contract status,
Chara's October 2021 contract came out at 34% to play its first season, against 59% with the state
known at the signing. Its dollar table, and the conclusion drawn from it ("a trivial gain of $5,000,
not decisive; keep the leader"), are **withdrawn**. `attach_forecasts` now reads contract state at
the signing for any model whose participation reads contract data. The leader reads none and is
unaffected, bit for bit. The season results above are scored at 1 July of each page by design, and
are unchanged.

**First, the population a valuation is about.** The harness scores every player on a page; a
contract is a player who has just signed one. First-season participation on the priced contracts,
read at the signing, against whether he played that season (1,458 started contracts,
player-resampled intervals):

| version | predicted | played | gap |
|---|---:|---:|---:|
| leader | 0.782 | 0.900 | −0.118 [−0.136, −0.101] |
| as known | 0.902 | 0.900 | +0.002 [−0.014, +0.018] |
| observable | 0.844 | 0.900 | −0.055 [−0.072, −0.039] |
| period only | 0.760 | 0.900 | −0.140 [−0.158, −0.122] |
| contract only | 0.845 | 0.900 | −0.055 [−0.072, −0.039] |

- **The leader under-predicts a signed player's first season by 12 points.** It does not know he has
  just signed, and a skater who has just signed plays that season nine times in ten.
- **Visible contract status, read at the signing, closes about half the gap.** The rest is plausibly
  the dating mismatch: the model is trained with contract state read at 1 July of each training
  page, and applied at the signing. That explanation is not tested here.
- **The old definition is on target, but that is not evidence it is right.** Its contract
  coefficient was learned partly from early training rows where being under a visible contract meant
  having survived.

**The dollars.** 1,217 development contracts valued, 1,176 with an ended term scored. Every
version's point valuation and the realised production are priced on the leader's line (primary);
the observable version's line is the sensitivity.

| version | moves contract value, mean abs | RMSE | MAE | bias | beats leader on squared error |
|---|---:|---:|---:|---:|---:|
| leader | — | $3.533M | $1.679M | −$0.597M | — |
| as known | $0.113M | $3.500M | $1.686M | −$0.515M | 100% |
| observable | $0.066M | $3.517M | $1.681M | −$0.550M | 100% |
| period only | $0.018M | $3.537M | $1.678M | −$0.612M | 0% |
| **contract only** | $0.066M | **$3.517M** | $1.681M | **−$0.549M** | **100%** |

The sensitivity line gives the same result: as known, observable and contract only each beat the
leader in 100%, and period only in 0%.

What this says:
- **Visible contract status, read at the signing, improves contract dollars on the declared primary
  score in every resample**, on both lines. The gain is modest: $16,000 of RMSE on $3.5 million
  (0.45%) and $48,000 of the leader's −$0.60M bias.
- **Observable and contract only are the same here**, because the priced contracts' seasons are
  nearly all from 2018 on, where the period indicator is zero.
- **The old definition does best** ($3.500M), but it is set aside on identification grounds, not on
  score. Its contract term carries the survival signal in the export's early rows.
- **Point valuations only.** The contract distributions from the path simulation were not rerun per
  version.

## What this settles and what it does not

**Settled, on development pages:**
- The skater contract export carries survival on early pages, more mildly than the goaltender one.
- For skaters the before/after-2018 period indicator adds nothing, in seasons or in dollars.
- **The leader under-predicts the priced contracts' own first seasons by 12 points** (0.782 against
  0.900), because it does not know the player has just signed.
- Visible contract status, read at the signing, is the only contract input that improves the skater
  forecast on every declared score without the survival signal. On participation and season WAR
  the gain is consistent and very small (0.05% of RMSE). On contract dollars it wins every resample
  (0.45% of RMSE, 8% of the bias), and it halves the first-season gap.

**Recommendation (revised; the earlier "keep the leader" is withdrawn): adopt visible contract
status only for the skater leader's participation.** This means `USE_CONTRACTS`, the observable
definition and the period indicator excluded, read at the signing for contract valuation.
- **It wins on the declared primary score.** It is the rule-consistent choice once the valuation
  reads contract state at the right date.
- **It carries two stated assumptions:** that the vendor snapshot is complete for contracts ending
  from 2018, and that training at 1 July and valuing at the signing is acceptable (it still leaves
  first seasons 5.5 points low).
- **The goalie baseline should be looked at again in this light.** Goaltenders were adopted on no
  contract inputs for simplicity, with the dollar trade-off recorded. On the goalie fixed line
  (already dated at the signing) the observable specification's RMSE was $6.880M against $6.932M for
  no contract inputs, a direction consistent with this skater result. Its paired share against no
  contract inputs was not computed. Whether goaltenders should follow skaters is a separate, small
  decision.

**This is a decision for Thomas; nothing is adopted.** Adopting it would move the leader's forecasts
everywhere they feed: the NPV simulation, control years and the skater side of every price line. All
of those would be rerun.

## What is checked

The suite covers the participation model's contract-state definition (check 41), every registered
skater variant (check 23), and, through the real caller, a skater contract valued with contract
state read at its signing (check 42). Check 42:
- reproduces Chara's 33.7% at 1 July against 58.9% at the signing;
- requires a copy of the contract dated 1 July to reproduce the page-dated valuation exactly,
  including a seven-year deal's extrapolated tail;
- requires the leader to be unmoved by the date.

It fails when the caller ignores the signing date, and when the tail's decay is dropped. The skater mixin's two new settings default to the recorded
behaviour. The leader's Brier (0.1340) and the old definition's (0.1326) reproduce the 2026-09-22
ablation exactly.

Suite: **42 passed, 0 skipped, 0 failed**.
