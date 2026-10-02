# xNPV 1's price per win

Written 2026-10-02 from `20_CODE/xnpv1_price_line.py` v1.0, its laptop run log
(`30_OUTPUT/xnpv1_price_line_log.txt`), and the cloud check
`25_TESTS/xnpv1_position_compression.py`. The constants are in force as
`skater_forward_projection.XNPV1_RATE`.

## Why xNPV 1 needs its own line

A season's value is the market's price for the wins the model expects. That price comes from
a line fitted to real contracts: cap share at signing against the player's production. The
line used until now (Stage 3, locked 2026-07-28) measures production with the trailing total,
which weights the last season 60% and the one before it 40%.

xNPV 1 does not price the trailing total. It prices its own forecast of the wins a player will
produce if he plays, and that forecast is pulled toward the league average. On the contracts
below it runs at 0.164 + 0.662 × the trailing total. A player with 4 trailing wins is forecast
at about 2.8.

A slope in dollars per trailing win, applied to forecast wins, under-prices every win above the
line's starting point. Good players then look overpaid and poor ones underpaid by construction.
That is a built-in tilt, and a back-test would read it as mispricing. The fix is a line fitted
on the same quantity it prices.

## What was fitted

The specification is unchanged from Stage 3:

- left-censored at the league minimum, because a contract cannot pay less than the minimum, so
  a minimum-salary deal says only that the market valued the player at the minimum or below;
- one intercept;
- a separate slope for defencemen;
- the same contracts: standard-level UFA and RFA skater deals starting 2018-2025.

The script first rebuilds that sample and re-fits it on the trailing total. It goes on only if
the locked Stage 3 constants come back, which proves the sample is the locked one. It then
changes one input, the trailing total, to xNPV 1's forecast of WAR if he plays in the
contract's first season. That forecast comes from the page of the start year, so it sees only
seasons before the contract starts, the same information the trailing total had. It reads no
contract status, so it cannot see the contract it is pricing.

Two of the 2,349 contracts have no xNPV 1 forecast (Nathan Smith, forward, 2023; Ryan Johnson,
defence, 2025). Both lines are fitted on the remaining 2,347 identical rows, which are
fingerprinted (`69a6edb291fe`). On those rows the trailing-total fit moves by less than
0.00003 in every coefficient from the locked Stage 3 values.

## Result

At the 2025-26 ceiling ($95.5M):

| | Stage 3, per trailing win | xNPV 1 line, per forecast win |
|---|---|---|
| value at zero wins | $1.267M | $0.735M |
| per win, forwards | $2.027M | $2.950M |
| per win, defencemen | $2.301M | $4.350M |
| residual spread (cap share) | 0.02275 | 0.02112 |

The Stage 3 column is the trailing-total fit on the 2,347 rows. The locked Stage 3 constants
on all 2,349 are $1.265M, $2.028M and $2.302M.

**Fit.** On the same rows, outcome and number of parameters, the censored log-likelihood is
4,048.2 for the forecast against 3,902.1 for the trailing total, a gap of 146.1. The
forecast explains the cap hits clubs actually paid better than the trailing total does. That
says xNPV 1's forecast is closer to how clubs price players. It is not a test of whether
the forecast is accurate.

**Tiers.** The table below is mean cap share in $M by trailing-total tier, observed against
each line's expectation (floor included).

| trailing wins | contracts | observed | Stage 3 line | xNPV 1 line |
|---|---|---|---|---|
| below 0 | 763 | 1.50 | 1.63 | 1.66 |
| 0-1 | 1,095 | 2.10 | 2.49 | 2.38 |
| 1-2 | 335 | 4.59 | 4.29 | 4.29 |
| 2-3 | 102 | 6.70 | 6.33 | 6.61 |
| 3+ | 52 | 9.73 | 9.59 | 9.92 |

Of the five tiers, the xNPV 1 line is closer in two (0-1, 2-3) and the Stage 3 line in two
(below 0, 3+). They tie at 1-2. The tiers are cut on the trailing total, which is the Stage
3 line's own input.

## Why the forwards' slope rose about 45% and the defencemen's about 89%

The forwards' rise is the forecast's compression and nothing more. On every player-page xNPV
1 forecast on pages 2018-2025 (cloud; 4,646 forward rows from 1,022 players), the forward
forecast runs at 0.690 × the trailing total. The Stage 3 forward slope divided by 0.690 is
$2.94M, against the fitted $2.95M.

Defencemen are compressed harder: 0.609 × the trailing total (2,471 rows, 539 players). That
is not a quirk of the forecast. Defencemen's realised WAR regresses about as much: 0.618 ×
the trailing total among those who played, against 0.734 for forwards. Stage 3's defence slope
divided by 0.609 is $3.78M. That accounts for about 72% of the rise to $4.35M. The rest
comes from fitting on the contract sample rather than this population and from the censoring;
this check does not separate those two.

These are population figures, not the contract sample, and rows repeat players across pages.

## What the defence slope means for the back-test

Clubs pay defencemen a small premium per trailing win (13.5% under Stage 3). Defencemen's wins
persist less, so per expected win the premium is large: 47% on the xNPV 1 line. Measured per
realised win, using the realised persistence above, it is about 35%.

There are two readings, and the line cannot tell them apart:

- clubs overpay defencemen for production that does not last;
- WAR under-counts something defencemen provide, and clubs pay for it.

The separate defence slope prices whatever the premium is as fair value. A systematic
mispricing of defencemen therefore cannot appear in the back-test as a defence-wide effect.
Stage 3 made the same choice; on the forecast line the premium is more than three times as large (47% against 13.5%). Mispricing
within defencemen (by age, contract length, or how the deal was struck) is still measurable.

## What changed in the code

- `skater_forward_projection.py` v1.6:
  - `XNPV1_RATE` holds the constants above;
  - `price_constants("xNPV 1")` returns them;
  - each xNPV 1 contract season is valued on them, and the spread behind the league-minimum
    floor uses the same slope;
  - every row's `price_line` column says which line priced it.
- `rfa_terminal_value.py` v1.5:
  - the seasons a club still controls after the contract are priced on the same line;
  - the observed rates at which clubs qualify or walk away from their RFAs are grouped by xNPV
    1's forecast for the season after the contract ends, the quantity the rates are later
    applied to. A decision with no forecast counts as below replacement.
  - The rates on the laptop run:

    | group | xNPV 1 forecast | rate | decisions |
    |---|---|---|---|
    | star | 3+ wins | 1.000 | 10 |
    | regular | 1-3 wins | 0.943 | 176 |
    | fringe | 0-1 wins | 0.774 | 1,048 |
    | below replacement | below 0, or none | 0.646 | 1,036 |
- **Unchanged:** xNPV 0 and the draft curve stay on Stage 3. xNPV 0 prices the trailing total
  the line was fitted on; the draft curve prices realised wins.
- **Re-fit check:** every run of `xnpv1_price_line.py` (v1.1) now checks that it gets the
  locked constants back, with the same rows fingerprint.

Not yet measured: the switch comparison on the new line (`25_TESTS/xnpv1_switch_check.py`).
