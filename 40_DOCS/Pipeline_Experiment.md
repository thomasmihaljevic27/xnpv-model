# Reducing the level tilt: a sweep of the whole player chain

Test date: 2026-09-14. Production model unchanged. Scripts: `20_CODE/pipeline_experiment.py`
v1.1 (with `pipeline_experiment2.py`), `20_CODE/market_line_experiment.py` v1.0,
`20_CODE/market_line_search.py` v1.0, `20_CODE/games_line_experiment.py` v1.1. All of them patch
the production engine inside the test process and check production hashes before and after; none
writes to a production file. The second pass (the last section) was run the same day after the
first pass was read.

## The problem

`npv_realized_by_tier.py` found the priced value of a contract season is right on average but
tilted by the player's level when valued: −25% below replacement, +14% at 3+ WAR. Two earlier
fixes were tested: pulling the starting point toward typical (fixed 2009-2017 calibration) helped
the middle and overshot stars; refitting the market line did nothing.

This sweep tries every remaining lever in the chain, with one discipline throughout: **every
rule is calibrated only on seasons before the valuation date.** A valuation at season t0 uses a
rule fitted on 2009 to t0−1. Nothing sees the season it prices.

## What was tried

**Starting point** (replaces the raw 60/40 two-season blend that feeds the price line and the
aging ratios):

| Rule | What it does |
|---|---|
| L | expected next-season WAR given the blend: a + b × blend, by position and by one- or two-season source |
| L6 | L fitted on the last six seasons only |
| P | L with a second slope above 2 WAR, so stars can keep a different share |
| LB | free weights on the two seasons instead of 60/40 |
| LB3 | LB plus a third season back where available |
| RG | per-82 rate and games share modelled separately, so a short season lowers the anchor through games, not rate |
| C | the aging curve's own pull toward comparables, passed through to the valuation (production computes it and discards it when it turns the curve into percentages) |
| M | L plus the WAR implied by the player's own cap hit. **Diagnostic only**: value built from cost makes surplus partly circular. It measures how much the market knows that the stats do not. |

**Other pieces:** top 50 comparables in the aging curve (the best rule from the comparables
test); an exit hazard estimated only on players who held a contract for the next season (**H**);
applying the exit hazard to the valuation season too (**S0**); and combinations.

**Market line** (separate test): thirteen specifications of the price-per-win line, each fitted on
signings up to year y−1 and scored on year-y signings, 2020 to 2025.

**Games-aware value line** (separate test): a line that prices games played alongside wins, run
through the full NPV chain with a projected games share per season.

## How it was scored

Every played contract season of the 2,591 skater contracts in the NPV spine (4,677 seasons):
survival × projected value against what the player produced, priced on the same line, $0 if he
had left the league. Two views are reported. **All pages** is every valuation 2018 to 2025.
**2020 to 2025 pages** (3,372 seasons) is the fair test: on the 2018 and 2019 pages the rolling
calibration window is the same 2009-2017 window the earlier fixed test used, so those pages add
nothing new and, as it turns out, behave differently.

## Results

### The starting point is the lever that matters

Change in error against production, 2020 to 2025 pages. WAR error is line-free; dollar error is
at the production line. Bias is projected minus realized, as a share of realized value.

| | Production bias | L bias | L change in WAR error | L change in dollar error |
|---|---:|---:|---:|---:|
| all seasons | +3.5% | −2.9% | −5.7% | −2.8% |
| below 0 | −27.2% | −8.4% | −12.7% | +4.9% (worse) |
| 0 to 1 | −2.0% | +0.9% | +1.2% | +1.1% |
| 1 to 2 | +15.1% | −3.5% | −5.9% | −6.4% |
| 2 to 3 | +18.5% | −4.1% | −10.8% | −11.3% |
| 3+ | +23.9% | −3.8% | −12.9% | −12.8% |

The tilt of dollar error on the starting level falls from +$0.46M per WAR to −$0.01M. On these
pages the pull-back is close to unbiased at every level from replacement up, and it removes about
an eighth of the error for players valued at 2+ WAR. Below replacement the dollar error rises
slightly even though the WAR error falls, because the league-minimum floor makes a small upward
correction cost more when it is wrong than it earns when it is right.

The variants of the rule (L6, P, LB, LB3, RG) land within a point or two of L. LB3 is the best of
them on error (−6.9% WAR, −4.1% dollars) but runs 5% low overall. None of them changes the
picture, so the simplest, L, is the one to carry forward.

**Why the earlier test overshot stars.** On the 2018 and 2019 pages production was unbiased for
3+ players (−0.5%) and the pull-back ran 23% low. On the 2020 to 2025 pages production ran 24%
high and the pull-back is 4% low. The stars valued in 2018 and 2019 (McDavid 2018, Matthews,
Panarin and Karlsson 2019 among them) held their level; the stars valued since have not. With 52
elite contracts in total the two periods cannot be told apart statistically, but the fair test is
the second one, and the pull-back passes it.

**What the market knows.** M, which lets the player's own cap hit inform the starting point,
beats every stats-only rule: −8.2% WAR error and −5.7% dollar error on 2020 to 2025 pages, and
the smallest star bias (−0.9%). The gap between M and L, about 2.5 points, is the information
teams have about a player that his WAR record does not carry. It cannot be used, because a value
built from the contract's own cost prices the contract off itself, but it bounds what any
stats-only fix can reach.

### The exit hazard is estimated on the wrong population

The production hazard is estimated on every player-season with 10+ games. Most of those seasons
end in an expiring contract, and the exit rate is 10.6% a year. Among player-seasons where the
player holds a contract for the following season, the rate is 5.3%. The chain prices only the
second kind of season. At k ≥ 1 production expects 11.7% of contracted seasons to be lost to exit;
7.0% were.

Correcting the population (H) fixes that on its own (6.1% expected against 7.0% realized) and
raises value by about $0.3M to $0.4M per contract. It makes the error slightly worse on its own
(+0.8%), because the over-predicted exits had been cancelling part of the over-projected
production. Combined with the pull-back (L+H), each error is fixed by its own correction:

| 2020 to 2025 pages | Production | L | L+H |
|---|---:|---:|---:|
| bias, all | +3.5% | −2.9% | −0.5% |
| bias, below 0 / 0-1 / 1-2 / 2-3 / 3+ | −27 / −2 / +15 / +19 / +24 | −8 / +1 / −4 / −4 / −4 | −5 / +4 / −1 / −3 / −3 |
| change in dollar error | | −2.8% | −2.2% |
| change in WAR error | | −5.7% | −5.6% |
| expected exit at k ≥ 1 (realized 7.0%) | 11.7% | 12.4% | 6.2% |
| net NPV movement, 2,591 contracts | | −$1,186M | −$645M |

L+H is the best-calibrated combination at every level, and it moves total NPV half as far as the
pull-back alone.

### The rest

- **Top 50 comparables**: −0.7% overall, −3.4% for 3+. Small, consistent, as in the comparables
  test. Worth taking with the pull-back, not instead of it.
- **Hazard at the valuation season (S0)**: 9.6% of contracts' players had no NHL game in the
  valuation season, and S0 improves the valuation-season WAR error by 3.4%. But it pushes
  expected exits to 18% against 7% realized and makes below-replacement contracts 8% to 9% worse
  in dollars. Not with the production hazard; possibly with H, where the combination (L+all) is
  close to L+H.
- **The curve's own mean reversion (C)**: −4.4% WAR error, but it under-corrects the 1-2 WAR
  tier (+4.5% bias) and over-corrects stars. The curve's pull is calibrated for per-82 levels at
  an age, not for season totals at a contract start.

### The market line

Rolling out of sample on 1,769 signings, 2020 to 2025, error in $M at a $95.5M cap:

| Specification | Error | Change | Admissible as a value line? |
|---|---:|---:|---|
| production (WAR, position slope) | $1.177M | | yes |
| + WAR² | $1.181M | +0.4% | yes |
| + age, age² | $1.180M | +0.3% | yes |
| + RFA flag | $1.176M | −0.1% | a contract attribute; see the second pass |
| one-season-anchor flag | $1.115M | −5.3% | yes |
| two seasons weighted freely, one-season flag | $1.103M | −6.3% | yes |
| the above + age | $1.091M | −7.2% | yes |
| the above + games share | $0.980M | −16.8% | yes, but see below |
| + contract length | $0.817M | −30.6% | a framing decision; see the second pass |

Three things stand out. First, the market discounts a one-season record heavily: about $0.9M off
at the same WAR. Second, the market's error is not tilted by level: +$0.20M at 3+, close to zero
in the middle. The production line is not over-paying stars; the over-valuation is entirely in
projected production. Third, **games played carry a price of their own**. At the same WAR totals,
a full season against half a season is worth about $2.1M, and once games are in the line the
price per win falls from $2.03M to about $0.8M. The production line charges wins for what teams
partly pay for availability. Contract length is the strongest predictor of all. Whether it belongs
in a value line is a framing question, taken up in the second pass.

### The games-aware value line in the chain

Run through the full NPV chain with a rolling games-share projection, scored on its own currency
(realized value priced on the same line from realized WAR and realized games):

| 2020 to 2025 pages | error as a share of realized value, production line | games-aware line |
|---|---:|---:|
| all | 56.5% | 49.8% |
| 1 to 2 | 58.4% | 46.0% |
| 2 to 3 | 49.0% | 38.9% |
| 3+ | 47.1% | 39.6% |

The relative error falls by six to twelve points above 1 WAR, with or without the pull-back. The
line also runs about 6% low overall, so it would need recalibrating before use, and it changes
what "value" means in the thesis (D6 to D9): a player's worth becomes a function of projected
wins and projected games rather than wins alone. That is a design decision, not a tuning.

## NPV consequences

Mean change in NPV per contract against production, 2020 to 2025 pages:

| Level at valuation | L | L+H | LB3 |
|---|---:|---:|---:|
| below 0 | +$0.40M | +$0.50M | +$0.40M |
| 0 to 1 | +$0.11M | +$0.30M | $0.00M |
| 1 to 2 | −$2.12M | −$1.63M | −$2.48M |
| 2 to 3 | −$4.25M | −$3.83M | −$4.48M |
| 3+ | −$9.47M | −$8.97M | −$10.09M |

Named contracts, NPV in $M, production → L+H: McDavid 2018 −1.8 → −24.4; Matthews 2024 +3.2 →
−8.9; Pastrnak 2023 −1.5 → −18.5; Draisaitl 2025 −9.6 → −28.4; Makar 2021 −11.0 → −21.9;
MacKinnon 2023 −35.4 → −45.8; Karlsson 2019 +14.2 → +2.1; Seth Jones 2022 −60.9 → −57.4.

## What this recommends

1. **Adopt a rolling pull-back of the starting point (L) together with the contracted-population
   hazard (H).** Both are calibrated strictly before the valuation date. Together they remove the
   level tilt, are within 5% of unbiased at every level, cut projection error 5.6% and dollar
   error 2.2%, and move total NPV by −$645M rather than −$1.2B. Both change locked rules: the
   k=0 identity between Layer 1 and Layer 2 (the valuation season would no longer equal the
   observed-season value), and the hazard population in `exit_hazard.py`.
2. **Take top 50 comparables with it.** Small and consistent.
3. **Decide on the games-aware line as a design question**, not a tuning. It is the largest
   remaining gain in relative error and it changes what the model prices.
4. **Do not use the market-informed anchor**, but keep its result as the ceiling for stats-only
   accuracy.

The second pass below revises 1 and 3.

## Limits

- The aging curve, its comparables pool and both hazard tables are fitted on all seasons,
  identically for every variant. A rolling refit of the curve was not run.
- Contract seasons only; RFA control years move NPV but are not scored. Goaltenders untouched.
- The spine values every contract at its first season. Trades happen mid-contract, and the
  contract-start population is selected (teams commit to players they know things about). The
  pull-back's calibration is on all player-seasons, so it does not depend on that selection, but
  the scoring population does.
- 52 elite contracts; every elite-tier interval includes zero. The elite results are consistent
  across rules and pages, which is the evidence, not any single interval.
- About thirty variants were compared across the three scripts.

## Reproduction

From the repository root: `python 20_CODE/pipeline_experiment.py` (about 11 minutes, 19
variants), `python 20_CODE/market_line_experiment.py` (15 seconds), `python
20_CODE/games_line_experiment.py` (2.5 minutes). Outputs in `30_OUTPUT/` carry each script's
name as prefix. The 2020-2025 page cut and the named-contract table were produced by an inline
readout over `pipeline_experiment_seasons.csv` and `_contracts.csv`.

## Second pass: the lowest-error combination, with locked decisions open

The first pass kept contract term out of the value line on the grounds that a line reading the
contract's own term prices the contract off itself. That was too strong. The value line asks what
the free-agent market charges for a player of this quality, and there are two framings of that
alternative: sign a one-year replacement each remaining season (term-free), or sign one replacement
for the remaining term (term enters). Neither is privileged. What term carries is a mix of the
market's price for commitment and the private information teams hold when they commit long, so a
line with term moves the term premium from "mispricing to be measured" into "fair value". That is a
decision about what the back-test tests, not a rule. Below, term is allowed, and every locked
choice is open. Nothing here ships.

### Contract prediction: what predicts cap hits best

Forward stepwise selection over the candidate features, scored by rolling out-of-sample error on
2020-2022 signings; the chosen line then scored, unchanged, on 2023-2025 signings (842). Error in
$M at a $95.5M cap.

| WAR block | Term allowed | Features chosen, in order | Held-out error | Change |
|---|---|---|---:|---:|
| production | | WAR, position slope | $1.235M | |
| 60/40 blend | no | + games share, one-season flag, age² | $1.023M | −17% |
| two seasons free | no | + games share, one-season flag, age² | $0.997M | −19% |
| per-82 rate | no | + one-season flag, age² | $1.068M | −14% |
| 60/40 blend | yes | + term, games, one-season flag, term², RFA, age×term | $0.760M | −38% |
| **two seasons free** | **yes** | **+ term, games, one-season flag, RFA, term², age×term** | **$0.755M** | **−39%** |
| per-82 rate | yes | + term, one-season flag, term×WAR, RFA, age×term | $0.774M | −37% |

The best term-free line is unbiased within $0.1M at every level except the top (−$0.77M at 3+,
where the players who sign are paid more than their two seasons say). The best line with term is
unbiased overall (+$0.02M) and within $0.15M at every level except 2 to 3 (+$0.62M). Its
coefficients, in $M at a $95.5M cap: each of the two trailing seasons about $0.47M per win, games
share +$2.7M per unit, one-season record −$0.64M, RFA +$0.44M, term +$0.43M per season plus a small
rising term², and a small age × term term. Read plainly: once term and games are in, a win is worth
about $0.9M a year, a season of commitment about $0.45M a year, and a full season of availability
about $2.7M against none.

Age never enters on its own; a one-season record is always penalised; the RFA flag enters only once
term is in (D7 found no RFA/UFA difference in a term-free line, and that still holds).

### Performance prediction: age in the pull-back

Second sweep, same harness, 2020-2025 pages (3,372 seasons). Bias is projected minus realized as a
share of realized value; the tilt is the slope of dollar error on the starting level.

| Rule | bias, all | bias 0-1 / 1-2 / 2-3 / 3+ | WAR error | dollar error | tilt | net NPV movement |
|---|---:|---|---:|---:|---:|---:|
| production | +3.5% | −2 / +15 / +19 / +24 | | | +$0.46M | |
| L | −2.9% | +1 / −4 / −4 / −4 | −5.7% | −2.8% | 0 | −$1,186M |
| LA (L + age) | +1.0% | +5 / +1 / −1 / −2 | −5.8% | −3.1% | 0 | −$274M |
| LB3 | −5.1% | −2 / −7 / −6 / −6 | −6.9% | −4.1% | 0 | −$1,525M |
| LB3A (LB3 + age) | +0.2% | +4 / −1 / −1 / −4 | −6.4% | −3.9% | 0 | −$382M |
| L+H | −0.5% | +4 / −1 / −3 / −3 | −5.6% | −2.2% | 0 | −$645M |
| LB3A+H | +2.5% | +7 / +1 / 0 / −4 | −6.3% | −3.2% | 0 | +$153M |
| LB3A+H+top50 | +1.7% | +7 / −1 / −2 / −6 | −6.4% | −3.3% | 0 | +$71M |

Age in the pull-back is the change that matters in the second pass. It lifts young players and
lowers older ones at the starting point, which the pull-back without age had been treating alike,
and it turns a package that moved total NPV by −$1.2B into one that moves it by −$0.3B (or about
zero with the hazard fix), with the tilt gone. Its weak spot is the 0-1 WAR tier, which it
over-projects by 4% to 7%; every other level is within 4%.

The lowest-error stats-only rule for projected production is LB3A (three seasons weighted freely,
plus age): 6.4% less WAR error than production. The market-informed diagnostic from the first pass
is still about 2 points better, and remains the ceiling.

### NPV: the lines through the chain

The chain run with four lines, each refitted rolling on signings before the page (so the comparison
is line against line, with the production specification also refitted): the production
specification, plus games share (G), plus games share and remaining term (GT). Term for a page is
the seasons left on the contract. It is identical on the projected and realized sides, so it
raises the level of value on both and cancels out of the error; what changes the error is the
lower price per win the line then carries ($0.89M against $2.03M), which makes a WAR miss cost
less in market terms. The dollar errors below are on each line's own currency.

| 2020-2025 pages | dollar error | bias | 3+ bias | 3+ dollar error | net NPV movement |
|---|---:|---:|---:|---:|---:|
| production line | $1.287M | +3.5% | +24% | $3.08M | |
| production spec, refitted rolling | $1.307M | +0.8% | +24% | $3.14M | −$156M |
| + games | $1.257M | −6.3% | +15% | $2.47M | +$186M |
| + games + term | $0.831M | −3.7% | +8% | $1.55M | +$4,069M |
| L pull-back, production line | $1.251M | −2.9% | −4% | $2.69M | −$1,186M |
| L pull-back + games | $1.252M | −11.3% | −6% | $2.35M | −$833M |
| L pull-back + games + term | $0.842M | −6.4% | −2% | $1.50M | +$3,342M |

Two things to take from this. The refitted production specification behaves like the locked one,
so the in-sample fit of the locked line is not what is holding it up. And the term line adds
$3.3B to $4.1B of NPV across 2,591 contracts: every long contract is worth more once the market's
price for commitment is counted as value. That is the framing choice made concrete. Under it, the
pull-back plus the games-and-term line leaves stars close to their production NPVs (3+ moves
−$0.05M on average) with the level tilt removed; under the term-free framing the same pull-back
lowers stars by $9M to $10M each.

### What the second pass recommends

- **Lowest error on production:** LB3A (+ H, + top 50). WAR error −6.4%, tilt removed, within 4%
  of unbiased everywhere except the 0-1 tier, and close to NPV-neutral in aggregate.
- **Lowest error on contracts:** two seasons weighted freely + games share + one-season flag +
  age² (−19%, term-free), or the same with term, RFA and their interactions (−39%). Which one is
  the framing decision above.
- **NPV:** the combination follows from those two choices. With term in the line, aggregate NPV
  rises by about $3.3B and stars sit near their current values with the tilt gone; without it,
  stars fall $9M to $10M each.
- Every one of these changes a locked decision (the k=0 identity, D6-D9's definition of value,
  the hazard population, the curve's comparables). None is a tuning; the point of this pass was to
  see the ceiling before deciding which of them to open, and whether to do that before or after
  the draft and prospect pillars are built.

### Reproduction, second pass

`python 20_CODE/market_line_search.py` (100 seconds), `python 20_CODE/pipeline_experiment2.py`
(about 7 minutes; harness `pipeline_experiment.py` v1.1), `python 20_CODE/games_line_experiment.py`
(2 minutes, v1.1). Outputs in `30_OUTPUT/` carry each script's prefix; the 2020-2025 page cuts
were read from the `_seasons.csv` files inline.
