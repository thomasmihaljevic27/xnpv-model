# Skater contract values scored in dollars (Phase 5 acceptance)

Run 2026-09-24 in `50_REBUILD/` (`run_skater_dollar_scoring.py` v1.0; `dollar_scoring.py`;
`run_npv_simulation.py` v2.6; `run_control_years.py` for the path draws). Development start years
only. Scoring only: nothing is fitted on realised seasons, nothing is adopted.

## What this is for

The rebuild plan's Phase 5 acceptance has three parts:
1. **the simulation's identity:** with the spread removed, the simulated contract value equals the
   point valuation (`run_npv_simulation.py` report 2; checks 24, 25 and 43);
2. **the valuations scored in dollars on development pages** (this run);
3. **the full chain's movement against the production spine, contract by contract**
   (`run_production_reconciliation.py`, rebuilt on the adopted leader on 2026-09-23).

This run also gives the matched comparison of the adopted skater leader (visible contract status in
participation) against the previous one (no contract data) on their simulated distributions, which
the adoption review left open.

## The comparison, declared before the run

- **Forecasts:** the adopted leader and the previous leader.
- **What is valued:** each development contract's own term (control years are the control-year
  runner's), two ways per forecast: the point valuation, which prices the expected season, and the
  mean of 2,000 simulated career paths priced one by one.
- **One currency:** a single price line prices every valuation and the realised production. The
  adopted leader's line is primary; the previous leader's is the sensitivity. The realised target
  is computed from each forecast's own contract row and asserted identical, contract by contract.
- **Scores:** squared error primary, absolute error and bias beside it; shares are exact counts of
  2,000 resamples of players (one player signs several contracts). Calibration of the simulated
  distribution uses the randomized PIT and interval coverage against the model's own draws; both
  work with the lump at the league-minimum floor.
- **Rows:** 1,176 ended terms, simulated under both forecasts; 767 players.

Before scoring, each forecast's season bands were checked against its point valuation: on all 1,217
contracts the band's expected season equals the priced forecast (largest gap 0 and 9e-16 WAR). The
look-ahead check on the drawn paths passed for both.

## Results

Error against realised dollars, $M, 1,176 contracts:

| line | forecast | valuation | RMSE | MAE | bias |
|---|---|---|---:|---:|---:|
| adopted's (primary) | adopted | point | 3.513 | 1.675 | −0.549 |
| | adopted | simulated | 3.513 | 1.758 | −0.335 |
| | previous | point | 3.529 | 1.674 | −0.594 |
| | previous | simulated | 3.526 | 1.743 | −0.406 |
| previous's (sensitivity) | adopted | point | 3.517 | 1.681 | −0.549 |
| | adopted | simulated | 3.516 | 1.767 | −0.333 |
| | previous | point | 3.533 | 1.679 | −0.597 |
| | previous | simulated | 3.530 | 1.749 | −0.407 |

The previous leader against the adopted, share of 2,000 player-resamples in which the previous
leader's error is lower:

| line | valuation | squared error | absolute error |
|---|---|---:|---:|
| primary | simulated | 15 | 2,000 |
| primary | point | 1 | 1,056 |
| sensitivity | simulated | 12 | 2,000 |
| sensitivity | point | 1 | 1,423 |

- **On the declared primary score the adopted leader wins,** for the point valuation (1,999 of 2,000)
  and for the simulated mean (1,985 of 2,000), on both lines. The point result reproduces the
  adoption test ($3.513M against $3.529M on this line).
- **On absolute error the simulated comparison goes the other way:** the previous leader's simulated
  mean has the lower absolute error in every resample ($1.743M against $1.758M). The point
  comparison on absolute error is even (1,056 and 1,423 of 2,000).
- **Point against simulated, adopted leader:** the same squared error ($3.513M), less bias
  (−$0.335M against −$0.549M) and more absolute error ($1.758M against $1.675M). The paths' floor
  lifts the average of a contract's value above the value of its average path, which removes about
  $0.21M of the under-valuation and costs some absolute accuracy.

## Is the simulated distribution calibrated?

On the primary line, 1,176 outcomes; intervals resample players.

| | adopted | previous |
|---|---:|---:|
| draws exactly at the floor | 33.5% | 34.1% |
| outcomes at the floor | 35.3% | 35.3% |
| excess at the floor | +1.8 points [−0.3, +3.9] | +1.2 points [−0.9, +3.3] |
| 80% interval: outcomes / own draws | 87.5% / 87.3% | 85.9% / 87.3% |
| 50% interval: outcomes / own draws | 63.4% / 65.0% | 59.9% / 65.3% |
| 50% interval excess | −1.6 points [−4.4, +1.1] | **−5.4 points [−8.2, −2.6]** |
| PIT central 80% (0.80 if calibrated) | 0.803 [0.780, 0.825] | 0.790 [0.766, 0.813] |
| PIT central 50% (0.50) | 0.488 [0.459, 0.516] | **0.448 [0.419, 0.477]** |
| PIT mean (0.50) | 0.501 [0.484, 0.518] | 0.512 [0.495, 0.529] |
| PIT variance (0.083) | 0.085 [0.081, 0.089] | **0.090 [0.086, 0.095]** |

- **The adopted leader's contract distribution passes every test here:** each PIT statistic's
  interval contains its calibrated value, and interval coverage matches the model's own draws.
  "Passes" means these pooled tests did not detect miscalibration; subgroups can still be off (the
  star tier is known to be, `Star_Residual.md`).
- **The previous leader's distribution is too narrow in the middle:** its 50% interval holds 5.4
  points fewer outcomes than its own draws, and its PIT variance is above the uniform's.

## Repairs after review (2026-09-24)

Two scoring defects were fixed, neither touching a valuation:
- **The comparison guard** priced every forecast's realised target from the first forecast's
  player, dates and discount factor, so it could not see a mismatch in them (a different player,
  $2.475M, and a different signing date, $26,000, were accepted in a deliberate test). It now checks
  player, signing date, seasons, term, pricing quarter and the fixed pricing features field by field,
  and prices each forecast's target from its own row (check 47).
- **Monetary ties**: values that should be tied differed by about $2e-10, and the randomized PIT read
  that as a position above or below a lump (one contract moved by 0.544). Dollars are now rounded to
  six decimal places before ties and interval membership (check 48).

After the repair every valuation is identical (1,176 contracts, largest difference 0), and the
calibration table above is the refreshed one; its conclusions are unchanged.

## What this settles

- **Phase 5's dollar scoring on development pages is done for skaters** on the adopted leader, with
  the matched comparison against the previous one: the adopted leader is better on the declared
  primary score for both valuations, worse on the simulated mean's absolute error, and its simulated
  distribution passes the pooled calibration tests that the previous one fails in the middle.
- **With the identity and the reconciliation already current, the three Phase 5 acceptance items
  each have a current run on the adopted leader.** Whether that closes Phase 5 is for review.
- **Not settled here:** control-year values scored against outcomes (not scored in this run);
  goaltenders (scored on their own branch, frozen); anything on
  the confirmatory pages; the star tier's known bias.

## Shared code

The scoring pieces were built first inside the goalie control-year runner. They now live in
`dollar_scoring.py` and both runners import them. The goalie runner was rerun on the shared module and
reproduces its recorded output exactly (run log identical after the header; scored table identical
on all 133 contracts). Check 47 requires the shared scorer to refuse a realised target that moves
with the forecast; a copy with that guard removed fails it.

## Files

- `50_REBUILD/code/run_skater_dollar_scoring.py` v1.0 (new)
- `50_REBUILD/code/dollar_scoring.py` (new; moved from `run_goalie_control_years.py`, which is v1.5)
- `50_REBUILD/code/run_npv_simulation.py` v2.6 (`point_valuation` extracted from `main`, unchanged)
- `50_REBUILD/code/repair_checks.py` v3.8 (check 47)
- output (ignored): `skater_dollar_scoring_run_log.txt`, `skater_dollar_scoring.csv`
