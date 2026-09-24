# The star residual: located in the aging walk, not yet repaired

**Update in progress (v1.1):** the matched no-level comparison and the next aging candidate are being scored; see the correction under "Three changes, scored".

Run 2026-09-24 in `50_REBUILD/` (`run_star_residual.py` v1.0; `ability_forecast.py` v2.2).
Development pages and development start years only. **Nothing adopted.**

## Where the miss is

The adopted skater leader (visible contract status in participation, adopted provisionally
2026-09-23) under-rates its best players. For players whose trailing total is three wins or more,
split into the two halves of a season forecast (rate per 82 games among seasons played, and season
WAR over every forecast):

| seasons ahead | predicted rate | actual rate (played) | rate miss | season WAR miss |
|---|---:|---:|---:|---:|
| valuation season | 3.24 | 3.26 | −0.03 | −0.17 |
| one | 2.99 | 3.26 | −0.27 | −0.42 |
| three | 2.47 | 3.10 | −0.63 | −0.64 |
| five | 1.90 | 2.82 | −0.92 | −0.87 |

**The starting point is right; the path forward is too steep.** The forecast walks a star's rate
down about 0.27 wins per 82 games a season. The stars who kept playing lost about 0.09. Every
trailing tier shows the same too-steep walk, smaller (five seasons out: −0.07 below replacement,
−0.13 for 0–1, −0.23 for 1–2, −0.29 for 2–3).

That is why the earlier repair recovered only a fifth of the gap: the hinge and evidence terms
changed the valuation-season fit, where the stars' rate was already about right.

**A caution on the rate column.** It is measured on seasons played, and the stars who played five
seasons later are a selected group. The season WAR column counts every forecast, played or not,
and shows the same growing miss, so selection does not explain it away. It could still inflate the
rate column's size.

## Three changes, scored

**Correction (after review): only two of the three were single changes.** Removing the aging
curve's level terms also changed the curve's training sample. The lagged-level fit drops every pair
with no season before the change (its level is missing), and the no-level fit kept them: 7,164 rows
against 9,459 on the 2021 page. So the "no level terms" row below changed the formula and the
sample together. The matched comparison, same rows and weights, is in the next section. (The code
comment that said such rows were "fitted on age and position alone rather than dropped" was wrong
and is corrected.)

Each is the adopted leader with the stated change; participation, games share and the
valuation-season rate are identical (Brier and first-season participation are unchanged to four
decimals in every version, which checks that).

| version | what changes |
|---|---|
| survivors-only curve | the aging curve fitted without the replacement-level seasons imputed for departing players. The forecast rate is conditional on playing, and leaving the league is priced by the participation model, so the imputed curve may count an exit twice. |
| no level terms | the aging curve on age and position alone, so a star is not walked down faster for being a star; **also admits 2,295 more training rows (2021 page)** |
| per-season regression | the rate at each horizon from that horizon's own regression on the anchor (fitted on seasons played), instead of walking the valuation-season rate forward |

The scores were declared in the runner before it ran. Shares are exact counts of 2,000
player-resamples in which the version's error is lower than the adopted leader's.

**Season WAR, every player (primary):**

| version | RMSE | lower than adopted | MAE | bias |
|---|---:|---:|---:|---:|
| adopted | 0.8151 | — | 0.4565 | −0.067 |
| survivors-only curve | 0.8146 | 1601/2000 | 0.4584 | −0.076 |
| no level terms | 0.8147 | 1130/2000 | 0.4619 | −0.073 |
| per-season regression | 0.8144 | 1288/2000 | 0.4676 | −0.037 |

None separates from the adopted leader on squared error, and all three are worse on absolute error.

**The residual itself, three-win-and-up tier:**

| seasons ahead | adopted | survivors-only | no level terms | per-season regression |
|---|---:|---:|---:|---:|
| rate miss, one | −0.27 | −0.23 | −0.13 | −0.29 |
| rate miss, three | −0.63 | −0.55 | −0.22 | −0.60 |
| rate miss, five | −0.92 | −0.83 | −0.26 | −0.68 |
| season WAR miss, five | −0.87 | −0.80 | −0.45 | −0.74 |

| version | tier RMSE | tier bias | tier error lower than adopted |
|---|---:|---:|---:|
| adopted | 1.859 | −0.549 | — |
| survivors-only curve | 1.844 | −0.503 | 1998/2000 |
| no level terms | 1.801 | −0.298 | 1975/2000 |
| per-season regression | 1.873 | −0.529 | 546/2000 |

The top tenth of each version's own predictions misses by −0.30 (adopted), −0.29, −0.21 and −0.31.

**What the level terms do to everyone else**, rate miss five seasons out:

| tier | adopted | survivors-only | no level terms | per-season regression |
|---|---:|---:|---:|---:|
| below 0 | −0.07 | −0.17 | −0.36 | +0.18 |
| 0 to 1 | −0.13 | −0.20 | −0.29 | +0.10 |
| 1 to 2 | −0.23 | −0.26 | −0.17 | −0.03 |
| 2 to 3 | −0.29 | −0.27 | +0.02 | −0.08 |
| 3+ | −0.92 | −0.83 | −0.26 | −0.68 |

**Contract dollars** (1,176 ended terms, realised target asserted identical across versions):

| line | adopted RMSE | survivors-only | no level terms | per-season regression |
|---|---:|---:|---:|---:|
| adopted's (primary) | $3.513M | $3.512M, 1065/2000 | $3.500M, 1183/2000 | $3.507M, 1212/2000 |
| per-season regression's (sensitivity) | $3.758M | $3.760M, 537/2000 | $3.767M, 449/2000 | $3.765M, 734/2000 |

Nothing separates in dollars either, and the direction flips between the two lines.

## What this says

- **The star residual is the aging walk, and mostly its level terms.** Removing the level terms
  (with the sample change; see the matched comparison) takes the stars' five-season rate miss from
  −0.92 to −0.26 and their season WAR bias from −0.55
  to −0.30, with the tier's squared error lower in 1,975 of 2,000 resamples. Fitting the curve on
  survivors helps a little (−0.83); the per-season regression does not help stars.
- **The level terms are also what keeps the lower tiers right.** Without them the two lowest tiers
  are walked down too fast (below replacement −0.07 to −0.36). The curve's single level slope is
  doing two jobs, and one slope cannot do both.
- **No candidate improves the declared primary scores.** Pooled season WAR squared error and
  contract dollars do not separate from the adopted leader, and absolute error is worse for all
  three. By the rule declared before the run, none is adopted, and no combination is scored
  (neither single improves a primary score).
- **For the thesis the star tier is where the money is**, so a repair that fixes it without
  breaking the lower tiers is worth designing. The obvious shape is a level effect that is not a
  single straight line: allowed to differ above and below some level, or estimated on a
  multi-season level rather than one season's rate. That is a new candidate and would be scored
  the same way; it is not built here.

## What is not settled

- Why the fitted curve walks stars down so much faster than the stars actually declined. The level
  term is measured against the rate one season before the change starts, which removes the obvious
  regression-to-the-mean artefact; whether a residual version of it remains, or whether one level
  slope simply averages over tiers that age differently, is not established.
- Whether the stars' observed slow decline is partly selection: stars who declined sharply may be
  the ones not playing five seasons later. The season WAR column argues against this being the
  whole story.

## Files

- `50_REBUILD/code/ability_forecast.py` v2.2: `A1StatusSurvivorAging`, `A1StatusNoLevelAging`,
  `A1StatusReducedForm` (each one change from the adopted leader; none adopted)
- `50_REBUILD/code/run_star_residual.py` v1.0
- output (ignored): `star_residual_run_log.txt`, `star_residual.csv`
