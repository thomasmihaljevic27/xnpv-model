# A goaltender's control years, and his contract in dollars

Run 2026-09-22 in `50_REBUILD/` (`run_goalie_control_years.py` v1.0). This is the fifth step of the
goalie branch in the plan's Phase 5. Development start years only. **Nothing adopted, and no
production file changed.**

## What was asked, and how it is scored

Three questions, each answered on two goalie forecasts declared before the run:

| forecast | what it is | status |
|---|---|---|
| production | production's season total, the participation model, his trailing share | the default |
| rate | the per-82 rate, the share model, the participation model | the sensitivity |

1. **What his control years are worth.** These are the seasons a club still holds his rights for
   after the contract, kept one season at a time by qualifying offer. They are valued under the same
   six stopping rules the skater run uses.
2. **What the contract is worth as a distribution of dollars**, not only as the price of an
   expected season.
3. **Whether those expected dollars are any good**, scored against the dollars the goaltender
   actually delivered, on contracts whose term has ended.

**The scoring rule was declared in advance.** The target is expected dollars, so squared dollar
error is the primary score, with mean absolute error and bias beside it. The coverage of the
simulated bands tests whether the spread is right. A lower WAR error was not assumed to carry
through, because the league-minimum floor and the control options make dollars a bent function of
the path.

**Realised dollars** are the same signing-dated price line applied to the WAR he actually produced
in each term season, with a season he did not play counting as zero. They answer "what the market
that signed him would have paid for what he delivered". They inherit the currency's circularity,
since the line is fitted to contracts, so they rank valuations on one scale and are not an absolute
measure of value. They are read only for scoring, never by a rule or a forecast.

## What is reused, not copied

- **The control-year machinery**: `run_control_years.price_span`, which does the draws, the
  calibration, the dependence across seasons, the six rules and the leakage check, plus its guards.
  Two optional arguments were added: precomputed forecast bands, and a hook that reads the drawn
  paths so the term is priced on the same draws. The skater output is unchanged in every existing
  column.
- **The forecast band**: `run_npv_simulation.forecast_blocks`, now taking a model factory, handed
  the goalie arms and the goalie panel.
- **The price line**: the pooled line with a goaltender price *level*, the specification that earned
  its place in the price-line work. On every goaltender row the level just adds to the intercept.
  The folded line is asserted equal to the pooled line on every goaltender row, and it lets the
  existing pricing code value a goaltender unchanged.
- **The point forecast**: `run_goalie_price_line.goalie_forecasts`, with participation read at the
  signing. The band is re-dated to the same signing-date participation, and **the simulated forecast's
  expected season is asserted equal to the priced forecast on every contract**, for both forecasts
  (largest gap 4.4 × 10⁻¹⁶ WAR).

## Two defects found on the way, and fixed

**1. A goalie model replayed on an earlier page read the wrong page.** The predictive interval
learns its spread by replaying the fitted model on earlier pages. The goalie models took the page,
the qualifying seasons and the league average from the fit, not from the page they were asked
about. So a model fitted for 2018 and replayed on 2015 would have asked production's projector
about 2018. That projection reads the 2015–2017 seasons the replay then scores it against.

No goalie model had been replayed before this step, so it never fired. The models now read all
three from the page asked about. The bake-off, participation and rate outputs are byte-identical
before and after. Check 38 asserts the behaviour, and removing the fix fails it.

**2. The fit of how much a miss persists returned a curve it had never scored.** This fit sits in
the shared simulation code and measures how much of a forecast miss carries into later seasons.
- **How it worked:** it searched its decay rate on the error of an *unconstrained* fit, then
  clipped the winner's weights into range afterwards.
- **What went wrong:** on the goalie 2018 page the observed correlations were 0.25, 0.21 and 0.06
  at one, two and three seasons. The unconstrained winner had a negative permanent part, and
  clipping turned it into 0.95 at one season: a miss that persists almost entirely, on data that
  says a quarter of it does.
- **The fix:** the weights are now constrained inside the search (non-negative, summing to at most
  one), and the decay rate is chosen on the error of the curve actually returned. The 2018 page now
  reads 0.26 at one season, in line with every other goalie page.

**Skaters.** The clip bound on one skater page, 2015, where the one-season value moves from 0.396
to 0.385. No priced skater contract uses that page, because every contract here was signed from
July 2015. The skater NPV simulation and control-year outputs agree with their baselines to
$0.00000002, which is solver rounding. Check 39 asserts the constrained fit, shows that the old
recipe gives 0.95 on this curve, and fails when the old recipe is restored.

## The sample, and a selection

263 development goaltender contracts are in the census:
- production's forecast prices 174 of them;
- 137 of those get a simulation band, because the goaltender has a 10-game season in the three
  before the page;
- the rate forecast prices the same 137.

**74 of the 263 own control years on eligibility, but only 21 reach the simulation:**

| contracts that own control years | count |
|---|---:|
| in the development census | 74 |
| with a point forecast and a price | 34 |
| a harness subject at the page (a band) | 21 |

The ones lost are goaltenders without an NHL record that production's projector can price, or
without a 10-game season in the three before the signing. These are mostly prospects on first
deals: mean cap hit $0.89M among those lost, against $1.21M among those kept. **The control values
below describe goaltenders with an NHL record, not the whole population that owns control years**,
and 21 contracts is a small sample.

**Eligibility.** For 166 of the 174 priced contracts the export's eligibility year equals the age-27
rule. For 8 it is earlier, through accrued seasons or the CBA's Group VI route. None is later.

## What the control years are worth

Mean dollars per contract that owns control years, discounted to the signing, on the same draws
under all six rules:

| forecast | take every year | production's rule | decide in advance | decide as you go, first loss | **decide as you go** | knew the path |
|---|---:|---:|---:|---:|---:|---:|
| production (21) | $0.911M | $0.129M | $1.037M | $1.065M | **$1.072M** | $1.360M |
| rate (21) | $1.054M | $0.063M | $1.111M | $1.149M | **$1.163M** | $1.494M |

- **Seeing the path so far is worth little:** $0.036M on production's forecast and $0.052M on the
  rate's, with pricing and policy held fixed.
- **Production's rule values the right far below the club's informed decision:** $0.129M against
  $1.072M. That rule prices the *expected* season, including the chance he does not play, and walks
  away at the first year whose price falls short of the qualifying offer. For goaltenders that
  expected price is low, so it stops early. The informed rule keeps him 1.48 of the 1.67 control
  seasons owned, on average.
  - The skater gap for comparison: $0.703M against $0.442M.
- **The two forecasts agree closely** on which rights are worth most: rank correlation 0.908. The
  rate forecast values them about $0.09M higher.
- **Guards:** nothing beats the club that knew the whole path, asserted. The club's expectation does
  not move when the future or the unplayed seasons are redrawn, also asserted.

## The contract's own term, as a distribution

The price of the expected season (the point value) against the average price of the drawn seasons
(the simulated value), on the 137 simulated contracts, in $M:

| forecast | point | simulated | gap | cost | sd | 10–90% width |
|---|---:|---:|---:|---:|---:|---:|
| production | 6.962 | 7.876 | +0.914 | 6.328 | 5.698 | 13.154 |
| rate | 6.898 | 7.759 | +0.862 | 6.328 | 5.524 | 12.653 |

The two values differ because the price line has a floor: a bad path cannot price below the league
minimum, so the average of the prices sits above the price of the average.

## Against what happened

Scored on the 133 ended contracts both forecasts price, in $M:

| forecast | valuation | **RMSE** | MAE | bias | 80% band covers | 50% band covers |
|---|---|---:|---:|---:|---:|---:|
| production | point | **6.859** | 3.496 | −0.376 | — | — |
| production | simulated | 6.882 | 3.985 | +0.566 | 93.2% | 78.9% |
| rate | point | 7.002 | 3.498 | −0.957 | — | — |
| rate | simulated | 6.953 | 3.879 | −0.069 | 91.7% | 73.7% |

Comparisons, resampling goaltenders:
- **Rate against production, simulated values:**
  - the rate forecast has lower squared error in 36% of resamples, so production is ahead in 64%;
  - it has lower absolute error in 81%.
- **Simulated against point, within each forecast:**
  - production: the simulated value beats the point value on squared error in 34%;
  - rate: it beats the point value in 83%.

**Read by the declared hierarchy:**

- **On the primary score, production's forecast stays ahead, but not decisively.** Its point
  valuation has the lowest squared error, and against the rate forecast's simulated value it wins
  64% of resamples. The dollar-level test cannot separate the two forecasts: a single contract's
  realised dollars are very noisy (RMSE about $6.9M against a mean cost of $6.3M), and there are 133
  contracts.
- **On bias, the rate forecast's simulated value is the best calibrated** (−$0.07M). Production's
  simulated value runs $0.57M high while its point value runs $0.38M low.
- **The two scores split again**, as they did on WAR. Absolute error favours the rate forecast;
  squared error favours production.

## The simulated band is too wide for goaltender contract dollars

The 80% band holds 92–93% of realised values, and the 50% band holds 74–79%. The over-coverage
appears on every page with more than a handful of contracts (82–100% at 80%), so the persistence
defect above is not its cause; fixing it narrowed the 2018 page's spread only a little (sd $5.43M →
$5.17M).

**The season-level band is mis-shaped rather than simply too wide.** Scored in the harness on
development pages, the 80% band covers 81% of all goalie cells. That average combines:
- 66% of played seasons, where the band is too narrow;
- 100% of unplayed seasons, which always fall inside the band because it includes the zero.

The 50% band covers 62%.

How that becomes a contract band that is too wide is not established here. The contract spread
combines the season band, the dependence between seasons and the participation draws. **Until the
goalie band is recalibrated, the simulated premium over the point value ($0.91M on production's
forecast) should not be taken at face value.** Production's own bias pattern (point −$0.38M,
simulated +$0.57M) is consistent with a premium larger than the realised dollars support. The rate
forecast's premium ($0.86M) roughly closes its point bias (−$0.96M), so the pattern is not uniform.

## What this settles and what it does not

**Settled, on development contracts:**

- The goalie control-year and contract-distribution machinery runs on the shared code. The forecast
  it simulates is asserted to be the forecast it prices.
- Deciding as you go is worth much more than production's rule for goaltenders ($1.07M against
  $0.13M on the default forecast), and seeing the path so far adds little ($0.04M).
- The two goalie forecasts agree on ranking the control rights (0.91) and differ by about $0.09M in
  level.
- Two defects are fixed, each with a guard: the replay dating of goalie models, and the persistence
  fit.

**Not settled:**

- **Which forecast values goaltenders better in dollars.** Production is ahead on the primary score,
  not decisively (64%); the rate forecast is better on bias and absolute error. Production stays the
  default.
- **The goalie band.** Too wide at contract level, mis-shaped at season level. Recalibrating it is the
  next piece of goalie work before any simulated goalie dollar figure is cited.
- **Control values for goaltenders without an NHL record.** They are outside this sample by
  construction.

## What is checked

Checks 38 and 39 are new, as above, and each is mutation-tested. The runner itself asserts:
- the folded price line equals the pooled line on every goaltender row;
- the simulated forecast equals the priced forecast on every contract;
- nothing beats hindsight;
- the club's expectation does not move when the future or the unplayed seasons are redrawn.

Suite: **39 passed, 0 skipped, 0 failed**.
