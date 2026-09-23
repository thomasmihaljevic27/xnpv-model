# Should the skater leader's participation use contract data? A matched test

Run 2026-09-23 in `50_REBUILD/` (`run_skater_contract_test.py` v1.1; `ability_forecast.py` v1.9;
`contract_price_model.py` v1.5). Adoption and downstream reruns: `ability_forecast.py` v2.0,
`run_npv_simulation.py` v2.4, `repair_checks.py` v3.2.
Development pages and development start years only. **Contract status only was adopted provisionally
as the skater leader on 2026-09-23**; the downstream reruns are in "Downstream, after adoption".

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
  100% of resamples on both scores, to the whole-percent rounding the runner prints, but season WAR
  RMSE moves from 0.8155 to 0.8151, 0.05%, and WAR absolute error does not move (0.4565 both). Adding the
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
contract is a player who has just signed one. First-season participation on the contracts with an attached forecast,
read at the signing, against whether he played that season (1,458 started contracts,
player-resampled intervals). These are counted before the price-line availability filter; 1,217 of
them are valued in dollars below, and 1,176 scored:

| version | predicted | played | gap |
|---|---:|---:|---:|
| leader | 0.782 | 0.900 | −0.118 [−0.136, −0.101] |
| as known | 0.902 | 0.900 | +0.002 [−0.014, +0.018] |
| observable | 0.844 | 0.900 | −0.055 [−0.072, −0.039] |
| period only | 0.760 | 0.900 | −0.140 [−0.158, −0.122] |
| contract only | 0.845 | 0.900 | −0.055 [−0.072, −0.039] |

- **The leader under-predicts a signed player's first season by 12 points.** It does not know he has
  just signed, and a skater who has just signed plays that season nine times in ten. How much of the
  12 points that accounts for is only partly measured (next point).
- **Visible contract status, read at the signing, closes about half the gap** (6.3 points of 11.8).
  That does not show the whole gap was missing contract status. The rest is plausibly
  the dating mismatch: the model is trained with contract state read at 1 July of each training
  page, and applied at the signing. That explanation is not tested here.
- **The old definition is on target, but that is not evidence it is right.** Its contract
  coefficient was learned partly from early training rows where being under a visible contract meant
  having survived.

**The dollars.** 1,217 development contracts valued, 1,176 with an ended term scored. Every
version's point valuation and the realised production are priced on the leader's line (primary);
the observable version's line is the sensitivity.

| version | moves contract value, mean abs | RMSE | MAE | bias | beats leader on squared error (rounded) |
|---|---:|---:|---:|---:|---:|
| leader | — | $3.533M | $1.679M | −$0.597M | — |
| as known | $0.113M | $3.500M | $1.686M | −$0.515M | 100% |
| observable | $0.066M | $3.517M | $1.681M | −$0.550M | 100% |
| period only | $0.018M | $3.537M | $1.678M | −$0.612M | 0% |
| **contract only** | $0.066M | **$3.517M** | $1.681M | **−$0.549M** | **100%** |

The shares are rounded to whole percents. The independent closure review counted them exactly:
contract only and observable beat the leader in **1,999 of 2,000** player-resamples on the primary
line, as known in 2,000, period only in 1. On the sensitivity line (observable's) contract only beats
it in 2,000 of 2,000; as known, observable and contract only each read 100% and period only 0%. That
review's rerun gives RMSE $3.534M for the leader and $3.518M for contract only; the last-digit
differences are rounding and are not otherwise explained.

What this says:
- **Visible contract status, read at the signing, improves contract dollars on the declared primary
  score** in 1,999 of 2,000 resamples on the primary line and 2,000 of 2,000 on the sensitivity line.
  The gain is modest: $16,000 of RMSE on $3.5 million (0.45%) and $48,000 of the leader's −$0.60M
  bias.
- **It is not better on every measure.** Absolute dollar error is slightly worse ($1.681M against
  $1.679M). The recommendation rests on squared error being the declared primary score.
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
- **The leader under-predicts the attached contracts' own first seasons by 12 points** (0.782 against
  0.900), partly because it does not know the player has just signed.
- Visible contract status, read at the signing, is the only contract input that improves the skater
  forecast's primary scores (Brier, season WAR squared error, contract-dollar squared error) without
  the survival signal. On participation and season WAR the gain is consistent and very small (0.05%
  of RMSE). On contract dollars it wins 1,999 of 2,000 resamples (0.45% of RMSE, 8% of the bias), and
  closes about half the first-season gap. Absolute dollar error is slightly worse, and WAR absolute
  error is unchanged.
- These are development contracts on the chosen price line. They do not show a large economic effect,
  remove the vendor-coverage assumption, or count as confirmatory evidence.

**Decision (the earlier "keep the leader" is withdrawn): visible contract status only is adopted
provisionally for the skater leader's participation.** This means `USE_CONTRACTS`, the observable
definition and the period indicator excluded, read at the signing for contract valuation.
- **It wins on the declared primary score** (squared error), not on absolute error. It is the
  rule-consistent choice once the valuation reads contract state at the right date.
- **It carries two stated assumptions:** that the vendor snapshot is complete for contracts ending
  from 2018, and that training at 1 July and valuing at the signing is acceptable (it still leaves
  first seasons 5.5 points low).
- **The goalie decision stays closed.** On the goalie fixed line the observable specification's RMSE
  was $6.880M against $6.932M for no contract inputs. That comparison was already part of the
  trade-off recorded when no contract inputs was adopted (`Goalie_Branch_Baseline.md`); it is not
  new evidence from this skater work, and it does not reopen that choice.

Adoption moves the leader's forecasts everywhere they feed: the path simulation, control years and
the skater side of every price line. Those are rerun below. The previous leader stays importable by
name (`A1HingeExposure`, `run_npv_simulation.PRIOR_LEADER`) as the no-contract sensitivity.

## Downstream, after adoption

The contract-status version is now the skater leader (`A1HingeExposureStatus`, the switch
`run_npv_simulation.LEADER`; the no-contract model is kept as `PRIOR_LEADER`). The previous outputs
are kept beside the new ones, and each run below is compared with its own earlier run.

**Correction: not every consumer moved at first.** The first pass reran the runners that import
`LEADER`, and said everything downstream had been rerun. That was too broad. The market comparison
(`run_valuation_sensitivity.py`) imported the old class by name and labelled it "the adopted
candidate", so its point surplus and the simulation's disagreed by up to $1.06M on 948 contracts and
the integration refused them. Five diagnostics (look-ahead, stress, uncertainty, coverage, the named
players) pinned their own copy of the old class too. All now take the leader from the one switch;
both valuation artifacts record the class they were built on, the integration refuses a mismatch by
name, and check 44 pins it. The market comparison keeps the previous leader as a labelled column and
cuts its tiers on the adopted model (declared; the previous membership is printed beside it with the
number of contracts that change tier).

**One more dating gap closed first.** The path simulation builds its season-by-season forecasts in
`forecast_blocks`, a second caller that still read contract state at 1 July of the page. The paths
would then have carried a different probability of playing from the point valuation they are checked
against. It now reads contract state at each signing, as `attach_forecasts` does. Check 43 drives
both callers on one batch and requires equal expected term totals and first-season participation;
a page-dated copy of `forecast_blocks` fails it.

**Contract values move on its own price line** (each run fits its own line, so these describe the
change, not accuracy; the accuracy comparison on one fixed line is the dollar table above):

| | old leader | contract status |
|---|---:|---:|
| point surplus, mean of 1,217 | $0.19M | $0.23M |
| simulated surplus, mean | $0.37M | $0.43M |
| gap, simulated minus point | $0.18M | $0.21M |
| contracts changing sign between the two | 223 | 226 |
| zero-spread identity, largest gap | $1.5e-08 | $7.5e-09 (passes) |

- **Only the 2019–2021 pages move** (mean point surplus +$0.04M to +$0.08M). Contracts on the 2017 and
  2018 pages are unchanged: no training row there targets a season from 2018 with a visible contract,
  so status never enters the fit.
- **Long deals move most:** +$0.01M on one-year deals, +$0.10M to +$0.19M from four years up.

**A finding: status enters only where it is supported, so long terms get a cliff.** The participation
model keeps a contract column only at horizons where enough training rows carry each value. Contract
status therefore enters at:

| page | status coefficient by seasons ahead (log-odds) | absent from |
|---|---|---|
| 2017, 2018 | — | every horizon |
| 2019 | +0.99 to +1.32 through four ahead | five ahead |
| 2020 | +1.06 to +1.29 through four; +1.96 at five | six ahead |
| 2021 | +1.04 to +1.24 through four; +1.87, +2.32 at five and six | seven ahead |

Past the supported range the forecast falls back to the no-contract fit. On an eight-year deal signed
in 2021 participation reads about 0.93 through the seventh season and **0.45** in the eighth, which
is exactly the old leader's number. The coefficients at the edge of support are also larger (+1.9 to
+2.3 against about +1.1) and rest on few rows.

**A separate issue: rises the simulation cannot deliver.** On 15 of 1,217 terms (2 under the old
leader) the chance of playing rises from one season to the next faster than the simulation's return
rate allows, and the exit probability that would deliver it has to be clipped. Its cost is small.
Propagated exactly through the chain's own recursion, clipping moves expected production by **0.000415
WAR a season** on average across the 15 (at most 0.000937; signed −0.000290). The largest probability
discrepancy in any season is 0.025. **Withdrawn:** the first version of this section gave 0.014 WAR
(at most 0.031), which was simulated production minus the point forecast, and so mostly the
simulation's own sampling noise, not the clipping. These are production figures, not dollars through
the floor.

The cliff and the clipping are different problems. A steep fall is something the chain represents
without difficulty (the adoption review's example, contract 6587, falls from 0.88 to 0.32 with no
clipping); clipping comes from a rise, often earlier in the same term (contract 6500 clips on a rise at season six, then falls at
season eight). Smoothing the fall does not by itself remove the rises.

The matched test's dollar result (1,999 of 2,000) was scored on this same model, cliff included. So
this is a property of what was adopted, not a new error in it. Carrying the last supported horizon's
status effect forward is a modelling assumption; it is scored as a named sensitivity below, and the
adopted model stays the baseline meanwhile.

**Control years** (`run_control_years.py`, 398 contracts owning them): deciding as you go $0.691M a
contract, against $0.703M; the value of seeing the path $0.063M against $0.066M; age-rule
sensitivity $0.704M against $0.717M. The control years fall after the term, where no contract covers
the season, so a model that separates covered from uncovered seasons values them slightly lower.

**Goalie price line** (`run_goalie_price_line.py`; the skater side of the pooled line uses the
leader). The goalie conclusions stand:
- a goaltender level: 0.006858 mean absolute error in cap share, against 0.006882;
- a separate goaltender slope on top: better than the level alone in 32% of resamples (33%);
- the goaltender-to-skater ratio for one more win every season: 0.79 unrestricted (0.77), 0.78
  restricted (0.76);
- the skater price of one more win every season, on the last fit: $1.96M (was $2.02M).

**Goalie control years** (`run_goalie_control_years.py`, no-contract goalie baseline; the skater side
of its pooled price line is the leader). The goalie conclusions stand:
- deciding as you go, the 21 contracts' control years: $1.051M on production's forecast (unchanged)
  and $1.092M on the rate forecast ($1.091M);
- against realised dollars, 133 ended terms, on this run's own production line: production's
  simulated value RMSE $7.153M, bias +$0.082M (was $7.111M and +$0.082M on the previous run's own
  line; the lines differ, so the RMSEs are not comparable); the rate forecast has lower squared error
  in 17% of resamples (17%) and lower absolute error in 86% (87%);
- calibration (randomized PIT) unchanged to the second decimal.

## Verification reruns on the adopted model

Every runner that values contracts or tests the leader, rerun after the scope correction above:

- **Market comparison** (`run_valuation_sensitivity.py` v2.1), six forecasts on 1,217 contracts. On
  groups cut on the adopted model, every group keeps its sign and the five groups keep their order in
  all six columns. On the previous membership the same holds. 29 contracts change group between the
  two memberships, all upward (24 from 0–0.5 into 0.5–1, 4 from 0.5–1 into 1–2, 1 from 0–0.5 to below
  0). The top group is unchanged (18 contracts).
- **Integration** (`run_valuation_integration.py` v1.3): both artifacts name `A1HingeExposureStatus`;
  the point surplus agrees to $0.00 on all 1,217 contracts; the guard passes.
- **Production reconciliation** (`run_production_reconciliation.py`, reading the integrated table):
  completes. The rebuild's gap to production's long contracts moves by $0.1M–0.2M (eight-year deals
  $33.63M to $33.82M), and term groups still account for 85% of the squared dollar gap.
- **Look-ahead tests** (`run_leakage_tests.py` v1.3, the adopted leader): all four pass with a largest
  change of exactly zero on all seven development pages. Its input-sensitivity section now completes;
  it had crashed on a subject whose history was removed (`int(NaN)` in the participation model, under
  both leaders). Unanswered subjects are reported, e.g. 4,764 of 41,496 subject-horizons when last
  season is removed. Check 45 covers it.
- **Stress tests** (`run_stress_tests.py` v1.2): the full-chain look-ahead passes; the leader beats
  production's forecast on all seven pages and in every position, age, experience, level and horizon
  group.
- **Uncertainty and coverage** (`run_uncertainty.py` v1.4, `run_coverage_decomposition.py` v1.2): move
  by about 0.01 at most. The clearest change is predicted participation for young players (23–26)
  next season, 0.922 to 0.937 against 0.954 observed.

These describe the adopted model. They are not a matched scoring of it against the previous leader:
the dollar comparison on one fixed line above remains the adoption evidence, and a matched comparison
of the simulated distributions is still outstanding.

**The carried-status sensitivity**: scoring in progress at this commit; results follow.

## What is checked

The suite covers the participation model's contract-state definition (check 41), every registered
skater variant (check 23), and, through the real caller, a skater contract valued with contract
state read at its signing (check 42). Check 42:
- reproduces Chara's 33.7% at 1 July against 58.9% at the signing;
- requires a copy of the contract dated 1 July to reproduce the page-dated valuation exactly,
  including a seven-year deal's extrapolated tail;
- requires the no-contract model to be unmoved by the date.

It fails when the caller ignores the signing date, and when the tail's decay is dropped. Check 43
requires the path simulation's season blocks to carry the same participation as the point valuation
for the adopted leader (see above). The skater mixin's two new settings default to the recorded
behaviour. The leader's Brier (0.1340) and the old definition's (0.1326) reproduce the 2026-09-22
ablation exactly.

Suite: **43 passed, 0 skipped, 0 failed**.
