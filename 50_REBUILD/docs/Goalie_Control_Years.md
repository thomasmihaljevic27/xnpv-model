# A goaltender's control years, and his contract in dollars

Run 2026-09-22 in `50_REBUILD/` (`run_goalie_control_years.py` v1.1, after an independent review). This is the fifth step of the
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
error is the primary score, with mean absolute error and bias beside it. Both forecasts are scored
in one declared currency, and calibration is tested with a transform that allows for the floor's
lump (both explained below). A lower WAR error was not assumed to carry through, because the
league-minimum floor and the control options make dollars a bent function of the path.

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
minimum, so the average of the prices sits above the price of the average. These figures are each
forecast on its own price line. Whether the gap is the right size is tested against what happened
in the calibration section below.

## Against what happened, in one currency

**The first version scored each forecast against a different target.** Each forecast fits its own
price line, and version 1.0 priced each forecast's realised dollars on that forecast's own line. So
changing the forecast also changed the answer it was scored against: on the same 133 ended
contracts the two realised targets differed by $0.51M a contract on average and $5.57M at most. Its
headline was that production's simulated value beat the rate forecast's in 64% of resamples. That
headline is **withdrawn**: it was not a comparison on one target.

**Now one currency is declared before the comparison: the default forecast's price line.** It prices
both forecasts' valuations and the realised path. The realised target is computed from each
forecast's own contract row and asserted identical. The rate forecast's line is the sensitivity.
RMSE and the other errors are in $M:

| scoring line | forecast | valuation | **RMSE** | MAE | bias |
|---|---|---|---:|---:|---:|
| production's (primary) | production | point | **6.859** | 3.496 | −0.376 |
| | production | simulated | 6.882 | 3.985 | +0.566 |
| | rate | point | 7.022 | 3.305 | −1.169 |
| | rate | simulated | 6.923 | 3.730 | −0.159 |
| rate's (sensitivity) | production | point | 6.876 | 3.737 | −0.104 |
| | production | simulated | 6.923 | 4.175 | +0.694 |
| | rate | point | 7.002 | 3.498 | −0.957 |
| | rate | simulated | 6.953 | 3.879 | −0.069 |

Rate against production, resampling goaltenders:

| scoring line | valuation | lower squared error in | lower absolute error in |
|---|---|---:|---:|
| production's | simulated | 44% | 100% |
| production's | point | 27% | 96% |
| rate's | simulated | 46% | 100% |
| rate's | point | 32% | 98% |

**Read by the declared hierarchy:**
- **On squared error the two forecasts are not distinguishable.** Production's sample RMSE is a
  little lower, but the rate forecast's simulated value wins 44–46% of resamples.
- **On absolute error and on bias the rate forecast is ahead**, clearly on absolute error.
- **Production stays the provisional default** because nothing here overturns it, **not because it
  has a dollar-performance advantage.**

Each forecast on its own line against its own realised target (the 1.0 comparison) is kept as a
labelled sensitivity. Its figures are production RMSE 6.882, bias +0.566; rate RMSE 6.953, bias
−0.069. It is not a common-target test.

## Is the contract distribution calibrated?

**The first version said the simulated band was too wide. That is withdrawn.** It read 93% of
outcomes inside the 80% interval as "too wide", but the salary floor puts a lump of probability at
one dollar value. About half of each contract's draws sit exactly there. An interval whose lower end
sits on the lump contains the whole lump, so a correct forecast can hold far more than 80%. The same
applies to a season, which is exactly zero when he does not play. Check 40 builds a forecast that is
calibrated by construction:
- the naive count gives 89% on the floor example and 84% on the zero example;
- the test used below gives 80% on both.

**The test used instead: the randomized PIT**, a probability integral transform with random
tie-breaking.
- It records where each outcome falls in the forecast's own distribution. An outcome sitting on a
  lump is spread uniformly across the lump's probability.
- It is uniform when the forecast is calibrated, lumps or not: 80% of values lie between 0.1 and
  0.9, the mean is 0.5, and the variance is 1/12 (0.083).
- Its variance separates the two failures. A variance below 1/12 means outcomes sit nearer the
  middle than forecast (too wide); above 1/12, too narrow.

Beside it, each interval's coverage of outcomes is compared with its coverage of the model's own
draws. That own-draw coverage is what a calibrated forecast would show. On the scoring line, 133
ended contracts, with 95% intervals from resampling goaltenders:

| | production | rate |
|---|---:|---:|
| 80% interval: outcomes / own draws | 93.2% / 89.6% | 91.0% / 89.6% |
| excess over own draws | +3.7 [−0.7, +7.4] | +1.4 [−3.2, +5.6] |
| 50% interval: outcomes / own draws | 78.9% / 71.5% | 76.7% / 71.6% |
| excess over own draws | **+7.5 [+1.4, +13.2]** | +5.1 [−1.4, +11.7] |
| PIT, central 80% share (0.80) | 0.789 [0.726, 0.852] | 0.782 [0.719, 0.847] |
| PIT, central 50% share (0.50) | 0.474 [0.398, 0.546] | 0.481 [0.404, 0.559] |
| PIT mean (0.50) | **0.438 [0.391, 0.486]** | 0.468 [0.421, 0.518] |
| PIT variance (0.083) | 0.078 [0.066, 0.088] | 0.082 [0.071, 0.093] |
| outcomes on the floor / own draws there | 59.4% / 45.5% | 59.4% / 49.2% |
| excess on the floor | **+13.9 [+6.4, +21.5]** | **+10.2 [+2.7, +17.8]** |

What this says:
- **The spread is not shown to be wrong.** Both forecasts' PIT variances and central shares are
  within their intervals of the calibrated values.
- **Production's distribution sits too high.** Outcomes fall low in it (mean PIT 0.44, excluding
  0.5), which is the same finding as its +$0.57M dollar bias. Its central 50% interval also holds more
  outcomes than its own draws say it should. The rate forecast's location is within its interval.
- **Both forecasts under-predict the floor.** 59% of ended contracts delivered floor-level value,
  against 46–49% of the model's own draws.

## Which component: participation, not the performance band

At season level the distribution is a lump at zero (he does not play) and a conditional band (he
plays). Tested apart, on every goaltender-season the harness scores on development pages:

| | production | rate |
|---|---:|---:|
| conditional band on played seasons: PIT central 80% (0.80) | 0.795 [0.761, 0.826] | 0.813 [0.777, 0.847] |
| conditional band: PIT central 50% (0.50) | 0.501 [0.458, 0.545] | 0.512 [0.470, 0.554] |
| conditional band: PIT variance (0.083) | 0.083 [0.075, 0.090] | 0.081 [0.074, 0.088] |
| whole season distribution: PIT central 80% (0.80) | 0.808 [0.780, 0.837] | 0.810 [0.783, 0.840] |
| whole season distribution: PIT mean (0.50) | 0.492 [0.469, 0.517] | 0.500 [0.475, 0.526] |

**The pooled diagnostics did not detect miscalibration in the statistics tested**, for the
conditional performance band or for the season distribution as a whole. That is weaker than saying
they are calibrated. Passing pooled checks can coexist with errors inside subgroups, and the
participation result just below is exactly such an error. (An earlier version of this report said
"calibrated"; that was too strong.)
The first version's "66% of played seasons" tested the unconditional interval, built for the mixture
of playing and not playing, on one group only. That does not measure the conditional band, and it
is withdrawn.

**Participation is where the miss is.** By fifth of the predicted chance of playing (predicted /
observed): 0.27/0.26, 0.40/0.42, 0.52/0.56, 0.73/0.67, 0.95/0.86. In the top fifth the model is
+0.096 too confident [+0.057, +0.141]. The same fifths hold for both forecasts, which share the
participation model. A goaltender forecast to be almost certain to play misses a season more often
than forecast, which is what the excess of floor-level contracts shows in dollars.

**So the repair is not to narrow the band.** The candidate is the top end of the participation
model: a goaltender whose record makes him look nearly certain to play. That is established here as a
calibration failure, not yet as a cause. The overall pooled season calibration is within its
interval, because the top fifth's excess is offset elsewhere.

## What this settles and what it does not

**Settled, on development contracts:**
- The goalie control-year and contract-distribution machinery runs on the shared code. The forecast
  it simulates is asserted to be the forecast it prices.
- **Control years:** deciding as you go is worth far more than production's rule for goaltenders
  ($1.07M against $0.13M on the default forecast, each forecast on its own line), and seeing the path
  so far adds little ($0.04M).
- **Dollar scoring:** in one currency, the two forecasts cannot be separated on squared dollar
  error. The rate forecast is better on absolute error and bias.
- **Calibration:** the pooled tests did not detect miscalibration in the spread of the contract
  distribution or in the conditional season band (a weaker statement than "calibrated"; subgroups can
  still be off). Production's contract distribution sits too high, and
  both forecasts under-predict floor-level outcomes.
- **Participation** is over-confident in its top fifth.
- **Two shared defects fixed**, each with a guard: the replay dating of goalie models and the
  persistence fit.

**Not settled:**
- **Which forecast values goaltenders better in dollars.** Production stays the provisional default;
  the dollar test does not favour it.
- **The participation model's top end:** why the most confident predictions miss, and whether fixing
  it removes production's upward contract offset and the floor excess.
- **Control values for goaltenders without an NHL record.** They are outside this sample by
  construction.

## What is checked

Checks 38, 39 and 40 are new, and each is mutation-tested. Check 40 is the calibrated-by-
construction example above. It fails when either PIT function stops randomizing across the lump.
Such a PIT can still put 80% in its central band by accident, so check 40 also holds the whole
histogram and the mean. The runner itself asserts:
- the realised-dollar target is identical across the two forecasts, contract by contract;
- the folded price line equals the pooled line on every goaltender row;
- the simulated forecast equals the priced forecast on every contract;
- nothing beats hindsight;
- the club's expectation does not move when the future or the unplayed seasons are redrawn.

Suite: **40 passed, 0 skipped, 0 failed**.
