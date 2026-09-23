# Why the goalie participation model was too sure: a snapshot export

Run 2026-09-23 in `50_REBUILD/` (`run_goalie_participation_top.py` v1.0; `participation_model.py`
v1.6; the dollar effect from `run_goalie_control_years.py` v1.2 with and without `--participation
observable`). Development pages only. **A diagnosis and a measured candidate. Nothing adopted.**

## The symptom

In its most confident fifth (predictions of 0.866 and above), the goalie participation model
predicted 95% of goaltender-seasons played where 86% were. The gap is +0.096, with a
goaltender-resampled interval of [+0.057, +0.141], while the pooled checks passed. Priced, it showed
up as too many contracts delivering floor-level value.

## Where the misses sit

The confident fifth is calibrated on the early pages and misses on the later ones (predicted /
observed):

| valuation page | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|
| confident fifth | 0.95/0.97 | 0.94/0.97 | 0.96/0.95 | 0.97/0.89 | 0.96/0.79 | 0.95/0.73 | 0.93/0.88 |

By target season the worst is 2023: 0.95 predicted, 0.59 observed. By horizon it is three seasons
out: 0.95 against 0.62.

The 105 missed cells belong to 61 goaltenders. In 81% of them the goaltender never played an NHL
season again. These are **careers that had ended, predicted as near-certain to continue**. Examples
from the 2020 page, three seasons out, all for 2023:
- Roberto Luongo (last season 2018): 0.91;
- Scott Darling (last season 2018): 0.94;
- Mike Condon (last season 2017): 0.96.

**It is not a data break.** Only 1% of misses have the goaltender's surname in the target season
under another key.

## The mechanism: the contract export is a snapshot

Every contract in the vendor export ends in 2018 or later. Goaltender contracts by end year run 84
(2018), 81, 91, 99, 95, 88, 90, 89, 53 (2026), then a thin tail. A deal that ended before 2018 is
simply not there.

So on an early valuation page, the goaltenders the export "knows" are the ones who went on to sign a
deal running into its era: the ones who kept playing. Among goalie anchors, whether each group
played:

| page | horizon | known to the export | under a visible contract | played if unknown | played if known, not under (n) | played if under |
|---|---|---:|---:|---:|---:|---:|
| 2012 | 0 | 0.04 | 0.02 | 0.72 | 1.00 (1) | 1.00 |
| 2015 | 0 | 0.14 | 0.14 | 0.66 | — (0) | 1.00 |
| 2019 | 0 | 0.96 | 0.73 | 0.00 | 0.38 (21) | 0.85 |
| 2022 | 0 | 1.00 | 0.55 | — | 0.57 (42) | 0.85 |
| 2012 | 3 | 0.04 | 0.04 | 0.42 | — (0) | 1.00 |
| 2015 | 3 | 0.14 | 0.14 | 0.45 | — (0) | 1.00 |
| 2019 | 3 | 0.96 | 0.08 | 0.00 | 0.53 (81) | 0.71 |
| 2022 | 3 | 1.00 | 0.10 | — | 0.47 (85) | 0.89 |

The full table, every page from 2010, is in the run log.

- **Up to 2015**, every goaltender under a visible contract played, at both horizons. In those
  training rows the contract columns are a survival flag.
- **From 2019** nearly every goaltender is known, and the known-but-unsigned ones play about half the
  time.

A fit trained on the first and applied to the second reads "known" as "will play". On the 2020 page
three seasons out, the training rows had too few goaltenders under contract that far ahead to
support "under contract", so the support rule dropped it and the fit kept only "unknown to the
export". It then gave every goaltender the export knew,
retired or not, 0.92–0.96.

**This is the same selection the birthdate finding recorded, from the same source.** A goaltender's
birthdate comes mostly from this export too. There, whether the join finds a record was the outcome;
here, whether the export lists the goaltender is the outcome.

## The candidate: contract state only where the export can see it

`ParticipationModel(contract_state="observable")`:
- **Before 2018** (the export's earliest end year), contract state is not observable. Every row reads
  "not observable" and "not under contract", whatever the export happens to hold.
- **From 2018 on**, any contract covering the season must end in or after it, so it is in the export
  whether or not the player lasted. "Under contract" is the true state, and no row is "unknown".
- **The whole-population "known to the export" signal is gone.**

The assumption, stated: the vendor's snapshot is complete for contracts ending in or after its
earliest end year. The default is unchanged; the candidate is opt-in.

## What it does to participation and the season

Production's projector and trailing share are held fixed; only participation changes. Squared error
is the primary score (declared 2026-09-22). "Beats current" is the share of goaltender-resamples in
which the variant beats the current model.

| participation | Brier | beats current | season WAR RMSE | beats current | WAR MAE | bias |
|---|---:|---:|---:|---:|---:|---:|
| current: contract state as known | 0.2056 | — | 2.073 | — | 1.432 | +0.096 |
| no contract data | 0.1958 | 100% | 2.065 | 99% | 1.410 | +0.037 |
| **contract state where observable** | **0.1940** | **100%** | **2.062** | **100%** | **1.409** | +0.043 |

- **Against no contract data**, the observable version has the lower Brier in 93% of resamples and
  the lower WAR squared error in 97%. Contract state carries real information once it stops carrying
  survival.
- **By horizon** (Brier):
  - no contract data is best next season (0.1337 against 0.1382);
  - the observable version is best from three seasons out (0.2208 against 0.2242 at three).

**The confident fifth is fixed.** Calibration by fifth, predicted / observed:

| participation | fifths | top-fifth over-prediction |
|---|---|---:|
| current | 0.27/0.26, 0.40/0.42, 0.52/0.56, 0.73/0.67, 0.95/0.86 | +0.096 [+0.057, +0.141] |
| no contract data | 0.26/0.27, 0.38/0.39, 0.49/0.55, 0.66/0.65, 0.90/0.90 | −0.003 [−0.039, +0.040] |
| observable | 0.25/0.25, 0.39/0.41, 0.50/0.56, 0.66/0.67, 0.90/0.90 | +0.005 [−0.032, +0.052] |

Bias in season WAR by trailing role (backup-ish / middle / starter-ish):
- current: −0.068 / +0.207 / +0.152;
- observable: −0.119 / +0.142 / +0.107.

The spread across roles narrows, but backups now run lower.

## What it does to contract dollars

The goalie control-year runner was run twice: current participation, and `--participation
observable`, which switches the scored arms and the priced forecast together.

**Within each run** (each on its own lines), the contract-level calibration moves the right way.
These are properties of each run's own distribution against its own target, so they can be set side
by side; dollar errors cannot, which is the next point.

| | current | observable |
|---|---:|---:|
| production: PIT mean (0.5 if calibrated) | 0.438 [0.391, 0.486] | 0.472 [0.426, 0.518] |
| production: outcomes on the floor minus the model's share | +13.9 [+6.4, +21.5] | +7.1 [−0.2, +14.9] |
| rate: outcomes on the floor minus the model's share | +10.2 [+2.7, +17.8] | +4.1 [−3.3, +12.0] |

**Across runs, dollar error must be compared on one line**, because each run refits its price lines
on its own forecasts. The two runs' printed RMSEs are against different targets and are not compared
here. Both runs' drawn paths are repriced on the current run's production line (primary) and on the
candidate run's (sensitivity). The realised target is asserted identical.

On the current run's production line (primary), 133 ended contracts, $M. "Candidate better in"
is the share of goaltender-resamples in which observable participation has the lower squared dollar
error:

| forecast | participation | RMSE | MAE | bias | candidate better in |
|---|---|---:|---:|---:|---:|
| production | current | 6.882 | 3.985 | +0.566 | |
| production | observable | 6.880 | 3.849 | **+0.187** | 51% |
| rate | current | 6.923 | 3.730 | −0.159 | |
| rate | observable | 6.961 | 3.619 | −0.475 | 24% |

On the candidate run's production line (sensitivity), the candidate is better in 58% (production) and
30% (rate). The biases move the same way: production +0.673 → +0.280, rate −0.061 → −0.389.

**How much correcting participation fixes the contract dollars:**
- **Production's forecast:** its upward dollar bias falls by about two thirds (+$0.57M → +$0.19M),
  its contract distribution's location is no longer outside its interval, and its excess of
  floor-level outcomes roughly halves.
- **Squared dollar error does not improve:** 51% and 58% of resamples, a tie. The primary score is
  dominated by the noise of single contracts (RMSE about $6.9M against a mean cost of $6.3M), not by
  this bias.
- **The rate forecast:** squared error is slightly worse (24% and 30%), and its bias turns more
  negative (−$0.16M → −$0.48M). Its contract location was already inside its interval. One reading,
  not tested here: the over-confident participation was offsetting a downward lean elsewhere in the
  rate forecast.
- **So the correction fixes what it was aimed at**, participation's calibration and the bias it
  carried into production's dollars. It is not a route to lower dollar error.

## What this settles and what it does not

**Settled, on development pages:**
- The confident fifth's over-prediction comes from the contract export being a snapshot. Its
  contract columns carried survival in early training rows and were applied to everyone later. The
  misses are mostly careers that had ended.
- Stating contract state only where the export can see it removes the over-prediction (+0.096 →
  +0.005). It improves participation Brier and season WAR squared error in every resample, and beats
  dropping contract data (93% and 97%).
- In contract dollars, on one fixed line, it cuts production's bias by about two thirds but leaves
  squared dollar error unchanged (a tie). For the rate forecast it makes squared error slightly worse
  and its bias more negative.

**Not settled:**
- **Adoption.** Every goalie result recorded so far uses the current participation: the price line,
  the rate forecast's arms and the control years. The candidate would move them, and it goes to
  review first.
- **Skaters.** The skater contract features read the same export, so the same survival signal can
  sit in them. The skater contract ablation and the open question of whether the leader should use
  contract data were both measured with contract state as known. The matched comparison recommended
  for that decision should use the observable definition. Not measured here.
- **The vendor snapshot's completeness** for contracts ending from 2018 is an assumption.

## What is checked

Check 41 asserts the observable definition:
- the coverage year is the export's own earliest end year;
- before it, every row is not observable and not under contract, whether or not the export knows the
  player;
- from it on, no row is unknown and "under contract" is the true state.

It also shows the old definition still separates known from unknown players on the same rows. A
mutant that ignores the option fails it.

Suite: **41 passed, 0 skipped, 0 failed**.
