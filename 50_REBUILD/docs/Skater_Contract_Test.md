# Should the skater leader's participation use contract data? A matched test

Run 2026-09-23 in `50_REBUILD/` (`run_skater_contract_test.py` v1.0; `ability_forecast.py` v1.8).
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

1,217 development contracts valued, 1,176 with an ended term scored. Every version's point
valuation and the realised production are priced on the leader's line (primary). The observable
version's line is the sensitivity.

| version | moves contract value, mean abs | RMSE | MAE | bias | beats leader on squared error |
|---|---:|---:|---:|---:|---:|
| leader | — | $3.533M | $1.679M | −$0.597M | — |
| as known | $0.060M | $3.525M | $1.681M | −$0.597M | 89% |
| observable | $0.092M | $3.541M | $1.678M | −$0.655M | 12% |
| period only | $0.018M | $3.537M | $1.678M | −$0.612M | 0% |
| **contract only** | $0.021M | $3.528M | $1.679M | −$0.594M | **91%** |

The sensitivity line gives the same ordering: as known 88%, observable 11%, period only 0%,
contract only 91%.

What this says:
- **Contract status only is the one contract version that improves dollars on the primary score**,
  in 91% of resamples. That is consistent, but not decisive by a 95% standard, and it is tiny: $5,000
  of RMSE on $3.5 million. It moves an average contract's value by $21,000.
- **The observable version is worse in dollars** (12%): adding the period indicator to contract
  status costs accuracy, for skaters as for goaltenders.
- **Point valuations only.** The contract distributions from the path simulation were not rerun for
  every version. The point values moved by $0.02–0.09M, so a simulated comparison is unlikely to
  reorder them, but that is not shown here.

## What this settles and what it does not

**Settled, on development pages:**
- The skater contract export carries survival on early pages, more mildly than the goaltender one.
- For skaters the before/after-2018 period indicator adds nothing, and adding it to contract status
  costs dollar accuracy.
- Visible contract status is the only contract input that improves the skater forecast on the
  declared scores: participation, season WAR and point-valued dollars. The improvement is
  consistent and very small.

**Recommendation: keep the leader as it is (no contract inputs).**
- **The size is too small to matter.** The gain is 0.05% of season WAR RMSE and $5,000 of $3.5
  million in dollar RMSE, and in dollars it clears 91%, not 95%.
- **It would create a dependency on a vendor snapshot.** That snapshot's coverage has already
  produced two defects in this rebuild, and the gain rests on an unverified completeness assumption.
- **It keeps skaters and goaltenders on the same footing.** The goalie baseline adopted on
  2026-09-23 also reads no contract inputs.

Contract status only is recorded as the best-supported alternative, to revisit if a later stage,
such as the matched path simulation or the back-test, shows it moving results. **This is a decision
for Thomas; nothing is adopted.**

## What is checked

The suite covers the participation model's contract-state definition (check 41) and every
registered skater variant (check 23). The skater mixin's two new settings default to the recorded
behaviour. The leader's Brier (0.1340) and the old definition's (0.1326) reproduce the 2026-09-22
ablation exactly.

Suite: **41 passed, 0 skipped, 0 failed**.
