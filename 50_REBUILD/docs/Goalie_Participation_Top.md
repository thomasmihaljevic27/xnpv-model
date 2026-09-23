# Why the goalie participation model was too sure: a snapshot export

Run 2026-09-23 in `50_REBUILD/` (`run_goalie_participation_top.py` v1.1, after an independent review;
`participation_model.py` v1.6; the dollar effect from `run_goalie_control_years.py` v1.3 run with
`--participation` set to each specification). Development pages only. **A diagnosis and a measured candidate. Nothing adopted.**

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

## Replacing the export-membership signal: five specifications

The first version of this report proposed "contract state only where the export can see it"
(`contract_state="observable"`) and credited its gain to contract information. **That attribution
is withdrawn.** The proposal carries two new inputs, and they have to be scored apart:

1. **A period indicator.** Under the observable definition, the "unknown" column is 1 exactly when
   the target season is before 2018, the same for every goaltender targeting that season. It says
   nothing about the player; it lets the fitted participation rate differ before and after 2018.
2. **Visible contract status.** Whether a deal covering the season is in the export, stated only
   from 2018. From 2018, any covering contract must be in the export, *assuming the vendor's
   snapshot is complete from that year*. That assumption is not verified.

Five specifications, named in one table (`run_goalie_participation.PART_VARIANTS`) that the scored
arms and the price runner both read:

| name | inputs |
|---|---|
| current | export membership and contract status as known (every recorded run) |
| none | no contract inputs |
| observable | period indicator and visible contract status |
| period only | the period indicator alone |
| contract only | visible contract status alone |

## Participation and the season

Production's projector and trailing share are held fixed; only participation changes. "Beats
current" is the share of goaltender-resamples in which the specification beats the current one.

| specification | Brier | beats current | season WAR RMSE | beats current | WAR MAE | bias | top-fifth over-prediction |
|---|---:|---:|---:|---:|---:|---:|---:|
| current | 0.2056 | — | 2.073 | — | 1.432 | +0.096 | +0.096 [+0.057, +0.141] |
| none | 0.1958 | 100% | 2.065 | 99% | 1.410 | +0.037 | −0.003 [−0.039, +0.040] |
| observable | 0.1940 | 100% | 2.062 | 100% | 1.409 | +0.043 | +0.005 [−0.032, +0.052] |
| **period only** | **0.1927** | 100% | **2.062** | 100% | 1.411 | +0.048 | −0.001 [−0.038, +0.043] |
| contract only | 0.1956 | 100% | 2.065 | 99% | 1.410 | +0.040 | +0.002 [−0.034, +0.046] |

**The inputs separated** (share of goaltender-resamples in which the first specification is lower):

| comparison | Brier | WAR squared error |
|---|---:|---:|
| period only against none | 100% | 99% |
| contract only against none | 67% | 51% |
| observable against contract only | 94% | 99% |
| period only against observable | 91% | 55% |

What this says:
- **Removing the export-membership signal is well supported.** Every replacement, including no
  contract inputs at all, beats the current model on both scores, and every one removes the
  confident fifth's over-prediction.
- **The gain over no contract inputs is the period indicator's.** Adding it wins 99–100%; adding
  visible contract status alone does not separate from none (67%, 51%). With the period indicator
  already in, contract status makes the fit worse on Brier (91% favour leaving it out).
- **These results do not establish that knowing a goaltender's contract adds information.** They do
  not establish that it adds none, either.

**No step at 2018 is clearly detected.** For the model with no contract inputs, which has no
period term, observed minus predicted participation by target season sits within ±0.06 every year
from 2015 to 2025, and every interval includes zero. That does not show that no change in the
playing rate at 2018 exists: intervals that wide could hide one. It does mean the indicator's gain
cannot be read as a clearly detected league-wide change. Where inside the fits (by horizon and page)
the gain arises is not established. (An earlier version of this paragraph said the gain was "not from
a league-wide change"; that went further than the evidence.) Two cautions:
- **The boundary is the export's earliest end year**, a property of the data source, not of
  goaltending. Nothing here says 2018 is the right place for a step.
- **It acts only where training straddles 2018.** On pages up to 2018 no training outcome is after
  it, so the indicator has no support and the fit is the no-contract one. Its gain sits at three to
  five seasons out on the later pages (Brier 0.2242 → 0.2208 at three seasons out, 0.2359 → 0.2272
  at five).

A time adjustment that is not tied to the vendor's coverage year, such as recency weighting of the
training rows, would test the same idea without that boundary. It is not run here.

## Contract dollars

Each specification was carried through the goalie control-year runner (`--participation`), which
switches the scored arms and the priced forecast together. All runs' drawn paths are repriced on one
fixed line, with the realised target asserted identical. On the current run's production line
(primary), 133 ended contracts, $M:

| forecast | participation | RMSE | MAE | bias | beats current on squared error |
|---|---|---:|---:|---:|---:|
| production | current | 6.882 | 3.985 | +0.566 | |
| production | observable | 6.880 | 3.849 | +0.187 | 51% |
| production | period only | 6.932 | 3.766 | −0.064 | 33% |
| production | none | 6.931 | — | −0.006 | 32% |
| rate | current | 6.923 | 3.730 | −0.159 | |
| rate | observable | 6.961 | 3.619 | −0.475 | 24% |
| rate | period only | 7.033 | 3.559 | −0.674 | 10% |

The "none" row (no contract inputs, production forecast) is from the independent closure review of
this work, run through the same simulator on the same fixed line; its absolute error was not reported
there and it was not rerun here.

On the other two runs' lines (sensitivities) the shares are:
- production: 56–58% (observable) and 37–38% (period only);
- rate: 28–30% (observable) and 12% (period only).

Within each run, production's contract distribution moves inside its interval under the observable
specification (PIT mean 0.438 → 0.472), and the excess of floor-level outcomes roughly halves
(production +13.9 → +7.1 points, rate +10.2 → +4.1).

What this says:
- **On the primary score, no replacement improves contract dollars.** Observable ties for production
  (51%) and is worse for the rate forecast. Period only is worse for both (33% and 10%), though
  neither loss is decisive for production.
- **On bias and absolute error, the replacements help production.** Its bias goes +$0.57M → +$0.19M
  (observable) → −$0.06M (period only), and absolute error falls. For the rate forecast the bias
  turns more negative.
- **The dollar results and the participation results point different ways.** Participation and
  season-WAR squared error favour period only. Contract-dollar squared error favours none of the
  replacements, and period only least.
- This experiment does not say why lower participation error does not carry into dollars. The
  first version said the remaining error was "dominated by the noise of single contracts"; that
  went further than the evidence and is withdrawn. What is shown is that this change does not
  materially lower squared dollar error. Model error can remain elsewhere.

## What this settles and what it does not

**Settled, on development pages:**
- The confident fifth's over-prediction comes from the contract export being a snapshot. Its
  membership and contract columns carried survival in early training rows. The misses are mostly
  careers that had ended.
- Removing the export-membership signal is supported by every replacement tested, on participation
  and season-WAR squared error, and each removes the over-prediction.
- The gain of the proposed replacement over no contract inputs belongs to the period indicator, not
  to contract information.

**Not settled:**
- **Which replacement.** Period only is best on participation and ties on season WAR, but it is
  tied to the vendor's coverage year and is among the worst on contract-dollar squared error. No
  contract inputs is the simplest, removes the over-prediction and nearly removes production's dollar
  bias (−$0.006M), but it too worsens squared dollar error (32% against current). Observable is in
  between. **Recommended as the provisional baseline: no contract inputs**, for simplicity and because
  it needs neither a vendor-specific 2018 boundary nor an assumption that the export is complete. It is
  **not** the winner on the declared dollar-accuracy score, and that trade-off stays explicit; the
  other specifications stay as sensitivities. **Pending confirmation; nothing adopted.**
- **Whether contract status carries information** once measured without the survival signal. It is
  not separated from none here.
- **Skaters.** The skater contract features read the same export. The skater contract ablation and
  the open skater contract-data decision were measured with contract state as known, so the matched
  skater test should separate the period indicator from contract status in the same way.
- **The vendor snapshot's completeness** from 2018 is an assumption.

## What is checked

Check 41 asserts the observable definition as implemented. It verifies the definition, not the
vendor's completeness:
- the coverage year is the export's own earliest end year;
- before it, every row is not observable and not under contract, whether or not the export knows the
  player;
- from it on, no row is unknown and "under contract" is the export's contract state (the true state
  only if the snapshot is complete).

It also shows the old definition still separates known from unknown players on the same rows. A
mutant that ignores the option fails it.

Suite: **41 passed, 0 skipped, 0 failed**.
