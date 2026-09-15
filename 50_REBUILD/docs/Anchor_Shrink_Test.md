# Pulling the valuation's starting point toward typical

Test date: 2026-09-13. Production model unchanged. Script: `20_CODE/anchor_shrink_test.py`
v1.1, seed 20260913.

## Summary

1. **Mean reversion does not improve the market-rate regression.** Refitting the price line on a
   pulled-back WAR makes the price per win steeper and the base lower, but the prices it predicts
   barely move. Predicting what teams paid on 2022-25 signings from a line fitted on 2018-21
   signings, the error is $1.206M with raw WAR and $1.203M with pulled-back WAR. The market
   already discounts a strong two-season run, and that discount sits inside today's slope.
2. **Pulling back the starting point improves the forecasts, modestly overall and clearly in the
   middle.** Across 4,677 played contract seasons, the error in projected production falls 4.6%
   and the dollar error falls 1.4% to 1.8% (intervals exclude zero). The tilt by player level
   disappears. For players valued at 1 to 3 WAR (449 contracts) the dollar error falls 6% to 7%,
   and a 15% to 16% over-projection becomes a 3% to 7% under-projection.
3. **For the best players it overshoots the other way.** Players valued at 3+ WAR go from +$0.98M
   a season too high to −$0.84M too low. The overshoot is already there in the valuation season,
   so it is not mainly the aging curve pulling them back a second time.
4. **The overshoot comes from the calibration period.** The pull-back was fitted on 2009-2017.
   Since 2018, forwards hold more of their level, and stars starting a new contract hold much
   more (89% of their starting level, against 72% for stars in 2009-2017).
5. **Doing both fixes gives back today's NPVs.** The refit price line returns what the pulled-back
   start takes away: average NPV for 3+ contracts moves −$0.8M, against −$9.3M for the start
   alone.
6. **Whether the best players are over-valued in dollars depends on how a delivered win is
   priced.** At today's price line they are. Priced at the refit line's price per delivered win,
   the tilt largely disappears, and projections sit about 12% low overall (6% to 22% by level, stars 15%). The data do not
   settle which currency is right. It is a decision for how the back-test prices realized
   outcomes.

## The two places mean reversion could go

**The starting point.** Every projected season is the player's raw two-season blend (60% last
season, 40% the season before) multiplied by the aging curve's percentage path, then priced by the
market line. Fix A replaces the raw blend with the expected next-season WAR given that blend:

    starting point = a + b × raw blend

`a` and `b` come from a straight-line fit of each player's actual season WAR on his raw blend. The
fit uses seasons 2009 to 2017 and players who played that season (leaving the league is handled
separately by the exit-risk table). It is fitted separately by position and by whether the blend
used two seasons or only one:

| | b (share of the blend kept) | a | pulls toward | player-seasons |
|---|---:|---:|---:|---:|
| Forwards, two seasons | 0.685 | +0.196 | +0.62 | 3,112 |
| Forwards, one season | 0.577 | +0.237 | +0.56 | 866 |
| Defence, two seasons | 0.631 | +0.114 | +0.31 | 1,644 |
| Defence, one season | 0.461 | +0.145 | +0.27 | 421 |

A player's next season keeps about two-thirds of his distance from typical. The fit ends before
the first contract scored (2018), so fix A is out of sample for every contract in the test.

In the calibration seasons a straight line is the right shape. Its average miss is within 0.07
WAR at every level, including 3+ players (−0.03) and players at 3+ in both prior seasons (−0.06).

**The market line.** The price line is a regression of each contract's cap share at signing on
the same raw blend. It is fitted on 2,349 skater contracts starting 2018-2025, censored at the
league minimum, with a common base and a slope that differs by position. Fix B refits the same
model on the pulled-back WAR. It only makes sense together with A, because a line in units of
expected wins has to be applied to expected wins.

| | base (cap share) | price per win, forwards | price per win, defence |
|---|---:|---:|---:|
| Production line (raw blend) | 0.01324 | 0.02124 ($2.03M at a $95.5M cap) | 0.02411 ($2.30M) |
| Refit on pulled-back WAR | 0.00732 | 0.03059 ($2.92M) | 0.04273 ($4.08M) |

Applying each line to its own WAR, predicted prices differ by $0.06M on average (largest $1.71M).
A straight-line pull-back mostly just rescales the slope. The small differences come from the
separate pull-back for one-season blends and from the shared base across positions.

A2 is fix A with the aging curve limited to aging. The curve's pull toward comparables reaches the
valuation only through the denominator of its percentage path, where it steepens the decline of
above-average players. With the starting point already pulled back, that pulls back a second time.
A2 sets the curve's kept share to 1 for the percentage path only.

## Design

The engine is the production NPV engine. It is patched inside the test process (starting point,
price line, curve kept share) and restored afterwards. Production code and source hashes are
unchanged after the run. All 2,591 skater contracts in the NPV spine are valued, each from its
first season (2018-2025). Every contract season already played (through 2025-26) is scored:

- **Projected:** survival × projected value, exactly as the engine prices it.
- **Realized:** the player's actual season WAR, priced with the same line, the same forecast cap
  ceiling and the same league-minimum floor, or $0 if he had no NHL season.

Cost is identical on both sides and cancels. The WAR columns are line-free and compare every
variant on the same footing. AB's dollar errors are on a different price per win, so they are not
comparable with the other variants' dollar errors.

## Results

### All played contract seasons (4,677)

| | Bias per season | Dollar error per season | Change vs production | WAR bias | WAR error | Tilt ($M per WAR of starting level) |
|---|---:|---:|---:|---:|---:|---:|
| Production | +$0.035M (+1.5%) | $1.323M | | +0.011 | 0.744 | +0.37 |
| A | −$0.143M (−6.1%) | $1.299M | −$0.024M (−0.043 to −0.004) | −0.054 | 0.710 | −0.12 |
| A2 | −$0.128M (−5.5%) | $1.304M | −$0.019M (−0.037 to −0.001) | −0.046 | 0.713 | −0.10 |
| AB | −$0.333M (−12.1%) | on its own price scale | | −0.054 | 0.710 | −0.13 |

### By level at valuation (bias per season, and change in dollar error)

| Level (season-total WAR) | Seasons | Production bias | A2 bias | A2 change in dollar error |
|---|---:|---:|---:|---:|
| below 0 | 1,227 | −$0.32M (−25%) | −$0.07M (−6%) | +$0.048M (worse) |
| 0 to 1 | 2,073 | −$0.13M (−7%) | −$0.08M (−4%) | +$0.017M (worse) |
| 1 to 2 | 874 | +$0.49M (+16%) | −$0.11M (−3%) | −$0.125M (−6.7%) |
| 2 to 3 | 322 | +$0.68M (+15%) | −$0.30M (−7%) | −$0.129M (−6.1%) |
| 3+ | 181 | +$0.98M (+14%) | −$0.84M (−12%) | −$0.183M (−5.8%), interval includes zero |

For 3+ players the sign flips in the valuation season itself: +$0.80M under production, −$1.24M
under A and A2 (52 contracts). Later seasons go from +$1.05M to −$0.68M under A2, against −$0.83M
under A. Removing the second pull-back accounts for only a small part of the overshoot.

### Why stars overshoot: the calibration period

This check is diagnostic only: it uses the scored era, and it ran as an inline script, not a
saved one. The same next-season fit was run on 2018-2025, and each era was compared with the
2009-2017 line.

| | 2009-17 | 2018-25 |
|---|---:|---:|
| Share of the blend kept, forwards (two seasons) | 0.685 | 0.745 |
| Share kept, defence (two seasons) | 0.631 | 0.627 |
| 2 to 3 WAR players: actual minus the 2009-17 line | +0.07 | +0.23 |
| 3+ players: actual minus the 2009-17 line | −0.03 | +0.29 |

Among 3+ players since 2018, those starting a new contract kept 89% of their starting level (52
cases); the other 223 kept 77%. In 2009-2017, 3+ players kept 72%. Two things are happening.
Forwards hold their level better than they did, and players who have just signed or started a new
contract are a selected group: the team committing to them knows things the stats do not. The NPV
spine values every contract at its first season, so it is made up entirely of that selected
group. Trades happen mid-contract, so the spine is not the population the back-test will value.

### How much NPV moves

Mean change in NPV per contract against production:

| Level | Contracts | Production mean NPV | A | A2 | AB |
|---|---:|---:|---:|---:|---:|
| below 0 | 870 | −$1.16M | +$0.40M | +$0.40M | +$0.08M |
| 0 to 1 | 1,220 | −$1.35M | +$0.09M | +$0.11M | +$0.19M |
| 1 to 2 | 347 | −$4.21M | −$2.23M | −$2.11M | −$0.30M |
| 2 to 3 | 102 | −$5.72M | −$4.58M | −$4.08M | −$0.12M |
| 3+ | 52 | −$6.29M | −$10.40M | −$9.25M | −$0.82M |
| Net, all contracts | 2,591 | | −$1,318M | −$1,149M | +$140M |

Named contracts, NPV in $M (production → A2): McDavid 2018 −1.8 → −24.6; Matthews 2024 +3.2 →
−10.1; Pastrnak 2023 −1.5 → −18.9; Draisaitl 2025 −9.6 → −28.4; MacKinnon 2023 −35.4 → −46.0;
Makar 2021 −11.0 → −21.6. The size of these moves is the reason the calibration choice matters.

## What the results show

**The market line already contains mean reversion.** The line records what teams pay for a player
whose last two seasons look a given way. Teams know hot runs fade, so the price per win of recent
production is lower than the price per win of production actually delivered. Pulling back the WAR
and refitting recovers the same prices with a steeper slope. It does not predict contracts better,
and when combined with the starting-point fix it returns today's NPVs.

**The starting point is where the forecast improves.** Raw recent production overstates the next
seasons of above-average players and understates below-average ones, and a pull-back calibrated
before 2018 corrects most of that for the large middle of the league. It overshoots at the top
because forwards and newly signed stars have held their level better since 2018 than the
calibration period implies. A pull-back calibrated on a rolling recent window, measured at the
dates assets are valued rather than at contract starts, is the obvious next version. It needs its
own out-of-sample test before any result from it is trusted.

**The dollar verdict on stars depends on the currency.** Under today's line, a realized win is
priced at the market's price per recent win, and stars' contracts come out over-valued. Priced at
the refit line's price per delivered win, the same projections show almost no tilt and sit about
12% low overall (6% to 22% low by level). How the back-test prices a realized win decides whether stars are
over-valued in the thesis's own currency. The back-test has to fix that choice, and use it the
same way on both sides of every trade, before a star-versus-package result is read as mispricing.

## Limits

- The aging curve and exit table were fitted on data that include the scored seasons, identically
  for every variant.
- Only contract seasons are scored. RFA control years move NPV but are not scored.
- The 3+ tier holds 52 contracts. Its intervals include zero for every variant's change in error.
- The starting point, the k=0 identity with the observed-season value, the curve's kept share and
  the price line are locked. Nothing here changes them.

## Reproduction

`python 20_CODE/anchor_shrink_test.py` from the repository root runs in about 2.5 minutes. Outputs
in `30_OUTPUT/` begin with `anchor_shrink_test_`: `seasons.csv`, `contracts.csv`, `summary.csv`,
`npv_movement.csv`, and `run.json` (calibration, both market-line fits, hashes).
