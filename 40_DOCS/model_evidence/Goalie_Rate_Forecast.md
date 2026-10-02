# How good is he per game? The goalie rate forecast

> **Adopted baseline, 2026-09-23.** The figures below were produced with the goalie participation
> model reading contract state from the vendor export (the old specification). The adopted
> baseline uses no contract inputs; the branch's figures on it, and the frozen status, are in
> `Goalie_Branch_Baseline.md`.

Run 2026-09-22 in `50_REBUILD/` (`run_goalie_rate.py` v1.1; price comparison in
`run_goalie_price_line.py` v2.4). This is the fourth step of the goalie branch in the plan's
Phase 5. Development pages only. **Nothing adopted, and no production file changed. The goaltender
price specification stays provisional.**

## Why a rate

A goaltender's expected season is three numbers multiplied together:

1. the chance he plays at all;
2. the share of the schedule he plays if he does;
3. how good he is per game.

The previous step built the first two as models. The third was still production's goalie projector,
and that projector does not forecast a rate. It forecasts a **season total**, shrunk toward a league
average of 2.19 WAR, which is roughly what a starter produces. To fit into the three-way product,
that total was divided by the goaltender's trailing share of the schedule. For a backup, whose total
has been pulled toward a starter's, the division inflates his implied rate. The share model then
forecast share better but made the season forecast worse.

The working diagnosis was that production's number cannot be split into a rate and a share, so a
real per-game forecast should let the share model be used. This step tests that.

## What is forecast

For each horizon (seasons ahead), the forecast is WAR per 82 games in a season he plays:

    rate = w × his trailing rate + (1 − w) × norm
    w    = G / (G + k)

- **His trailing rate** pools his last three seasons, each weighted by its games and by recency. The
  recency weights are the locked 60/40 decay carried to a third season: 1, 0.667, 0.444. A rate is a
  per-game quantity, so a 12-game cameo counts as 12 games of evidence, not a season's worth. Every
  season the source records counts, down to its two-game floor. Production's lookup also has no
  games filter, and weighting by games is what makes that safe.
- **G** is the same recency-weighted games: the evidence behind his number.
- **k** is the number of games at which his own record and the norm carry equal weight. It is fitted
  per horizon on a grid, which includes the option of giving his own record no weight at all.
- **The norm** comes in two versions, run side by side:
  - *Flat*: one number for every goaltender.
  - *Role*: a + b × his trailing share of the schedule. Coaches give starts to the goaltender they
    think is better, so role might carry information about ability.

**How it is fitted.** Per horizon, on (goaltender, valuation season) pairs whose outcome season is
strictly before the page. The subjects are the harness's own: goaltenders with a 10-game season in
the three seasons before the valuation season.

- **The outcome** is the per-82 rate in a season he actually played, weighted by that season's
  games. A rate from two games estimates the same quantity as one from sixty, with far more noise.
- **The estimation.** For a given k the model is linear in a and b, so each grid value is an
  ordinary weighted least squares, and the k with the lowest weighted squared error is kept.
- **Thin horizons.** A horizon with fewer than 150 outcome seasons borrows the nearest shorter
  horizon's fit. That happens only on the earliest pages.

**What the weighted fit estimates.** Weighting each outcome season by its games targets an
*exposure-weighted* rate: total WAR over total games, given the record and that he plays. That is
not the plain average rate of a randomly chosen played season. The two differ whenever games and
performance move together, and for goaltenders they do, because the one playing well gets the
starts.

That weighting is also what makes the product work. The exposure-weighted rate times the average
share of the schedule *is* the expected season:
- as a formula, E[games × rate] / E[games] × E[share] = E[rate × share];
- no assumption that rate and workload are uncorrelated is needed;
- the covariance correction belongs to the *unweighted* average rate, not to this one.

An earlier version of this report said the product needed rate and share to be uncorrelated. That
was too strong for a games-weighted rate and is withdrawn.

What the identity does not give:
- It holds for the true conditional quantities, on one set of information and one schedule length.
  The fitted rate and share are separate approximations, and seasons of different lengths are mixed.
- An expected season is not a distribution. A season-by-season path that runs through a salary floor
  or a control option needs the joint distribution of rate and workload, not only their means.

It is fitted only on seasons he played, so it answers "how good, given that he plays", which is
exactly the factor the product needs. Whether he plays belongs to the participation model. **No
age**, for the reason in `Goalie_Participation.md`: a goaltender's birthdate is available mostly
because he survived into the contract era.

## What the fit chose

The shrinkage is heavy, and it gets heavier fast with the horizon:

| seasons ahead | k chosen, across the seven development pages | weight on his own record, one full season behind him |
|---|---|---:|
| next season | 120–160 games | about a third |
| one after | 160–400 | about a fifth |
| two after | 300–1,500 | under a fifth, falling to about 4% |
| three to five after | 600 up to "no weight at all" | under 10%, often none |

So from three seasons out, the forecast is essentially the norm. Among goaltenders who are still
playing, per-game quality three or more seasons ahead is barely predictable from the record. The
norm itself runs from about 2.4 to 4.9 WAR per 82 games, depending on page, horizon and role.

**The role norm earns nothing.** Its slope on trailing share is positive next season and the one
after (+1.8 to +3.3 WAR per 82 per unit of share, across pages). From two seasons out it changes
sign from page to page and is mostly negative (+0.5 to −2.8).
In accuracy it is indistinguishable from the flat norm everywhere below. **The flat norm is the one
carried forward**, because the simpler specification was tested and the extra term did not beat it.

## The rate on its own

The first test scores the rate alone, on seasons he played, against production's implied rate (its
season total divided by his trailing share):

| rule | mean abs error | games-weighted | games-weighted bias |
|---|---:|---:|---:|
| production's total ÷ trailing share | 5.253 | 4.157 | +0.708 |
| **rate, flat norm** | **4.866** | **3.903** | −0.317 |
| rate, role norm | 4.867 | 3.907 | −0.307 |

The rate forecast is better in **100%** of goaltender-resamples. As a per-game forecast it clearly
beats what production's number implies.

## The season: better calibrated, less sharp

Now the season forecast, which is what gets priced. Every arm uses the participation model; the arms
differ only in the rate and in whether the share of the schedule is trailing or modelled. Two scores
are reported because they ask different questions:

- **Mean absolute error** rewards getting the *median* outcome right.
- **Squared error** rewards getting the *mean* right.

Almost half these cells are seasons he did not play, scored as zero, so the two can disagree. A
forecast feeding a sum of expected dollars is a forecast of the mean.

| season forecast | mean abs error | beats first row | RMSE | beats first row | bias |
|---|---:|---:|---:|---:|---:|
| production's total, trailing share | **1.432** | — | **2.073** | — | +0.096 |
| production's total, share model | 1.492 | 0% | 2.111 | 1% | +0.183 |
| rate (flat norm), trailing share | 1.441 | 25% | 2.104 | 1% | +0.002 |
| rate (role norm), trailing share | 1.439 | 30% | 2.105 | 1% | +0.005 |
| rate (flat norm), share model | 1.466 | 0% | 2.099 | 2% | +0.030 |
| rate (role norm), share model | 1.464 | 0% | 2.098 | 2% | +0.030 |

"Beats first row" is the share of goaltender-resamples in which the arm's error is lower than
production's total with trailing share.

**Production's season total is still the most accurate season forecast on both scores.** The rate
forecast ties it on absolute error and loses on squared error in 98–99% of resamples. Where the
difference shows is ranking: production's total separates good goaltenders from poor ones better at
every horizon. Here is the correlation between forecast and outcome (rate columns use the flat norm):

| seasons ahead | production's total | rate, trailing share | rate, share model |
|---|---:|---:|---:|
| next season | **0.431** | 0.395 | 0.403 |
| one after | **0.360** | 0.328 | 0.328 |
| two after | **0.303** | 0.264 | 0.259 |
| three after | **0.254** | 0.207 | 0.176 |
| four after | **0.220** | 0.151 | 0.116 |
| five after | **0.139** | 0.103 | 0.113 |

**What the rate decomposition does better is calibration.** The pooled bias falls from +0.096 WAR to
between +0.002 and +0.030. By trailing role, cut into thirds on the same cells, it looks like this:

| trailing role | production's total, trailing share | production's total, share model | rate, trailing share | **rate, share model** |
|---|---:|---:|---:|---:|
| backup-ish | −0.068 | +0.237 | −0.261 | **−0.072** |
| middle | +0.207 | +0.328 | +0.037 | **+0.123** |
| starter-ish | +0.152 | −0.017 | +0.235 | **+0.041** |
| mean of the three, absolute | 0.142 | 0.194 | 0.178 | **0.079** |

(Rate columns are the flat norm; the role norm is within 0.03 in every cell.)

**The share model now helps where it used to hurt, but only on one score.** With production's total,
adding the share model worsened both scores: absolute error +0.060 and squared error +0.158, lower in
0–1% of resamples. With the rate forecast:

- squared error improves by 0.020 (flat norm, lower in 66% of resamples) to 0.027 (role norm, 70%);
- absolute error worsens by 0.025–0.026 (lower in 0–1%);
- the role biases flatten, from −0.26/+0.04/+0.24 to −0.07/+0.12/+0.04.

So the earlier diagnosis holds in part. Production's total really could not take a modelled share,
and a real rate can. But the share model's damage to absolute error does not go away. That is the
signature of a forecast moving toward the mean, which absolute error does not reward.

**A fitting variant that did not help.** Season-WAR error is rate error times games played, so
squared season error weights each season by games *squared*, while the rate is fitted by games.
Refitting the rate by games squared, to match the season score, made everything worse: season
absolute error 1.503, RMSE 2.120, bias +0.166, all lower than production's in 0% of resamples. It is
not in the runner.

## What it does to the price line

`run_goalie_price_line.py` now builds a third goalie forecast for pricing: the per-82 rate (flat
norm), times the share model, times the participation model dated at the signing. It is
horizon-specific, so the season average over the term actually changes with term.

- **Which contracts it can price.** 165 of the 205 goaltender contracts with a production forecast
  get one. The other 40 are goaltenders with no 10-game season in the three before the page, whom
  the harness's subject rule does not cover.
- **How far it moves the forecast.** Against the production-projector forecast, the season average
  moves −0.242 WAR on average and 0.342 in absolute terms, up to 0.977; the correlation is 0.924.

Both forecasts are compared on the **137 contracts** both can price inside the development cohorts:

| line | production's projector | rate × share × participation |
|---|---:|---:|
| no goaltender terms | 0.011131 | **0.010027** |
| goaltender level only | 0.008635 | **0.008503** |
| goaltender level and slope | 0.008787 | 0.008626 |
| level beats no terms in | 100% of resamples | 99% |
| slope beats level alone in | 28% | 28% |
| whole-path response, UFA, skater / goalie | $2.074M / $1.514M (ratio 0.73) | $2.110M / $1.702M (ratio **0.81**) |

Errors are mean absolute error in cap share.

**One forecast, priced as tested.** The first version of this comparison built the share of the
schedule for pricing separately from the scored forecast. Where the share model had a fit, the two
agreed. Where it did not, which is the long horizons of the early pages, they fell back differently:
- the price runner used a share pooled over all recorded seasons with recency decay;
- the scored forecast used the qualifying-season trailing share.

435 page-goaltender-horizon cells differed, by up to 1.6 WAR before participation.

Both now call one implementation, `ConditionalSeason` in `run_goalie_rate.py`. It carries the rate,
the share, the share model's fallback and the horizon clamp. The repair changes 8 contracts, by at
most 0.0076 WAR per season after participation and averaging over the term. The price results move
in the fourth decimal place or less, and no conclusion changes: the figures in this section are the
repaired ones.

**Which forecast prices goaltenders better, same contracts, same line.** Resampling the 82
goaltenders:

- With no goaltender terms, the decomposed forecast cuts mean absolute error by 0.001105, better in
  **99%** of resamples.
- With the goaltender level, the difference is 0.000132, better in **67%**. That is not decisive.

Read plainly:

- **The level carries it again.** Under either forecast, a goaltender price level on the shared win
  slope delivers the improvement, and a separate goaltender slope does not earn its place.
- **The goalie gap shrinks.** With no goaltender terms, the decomposed forecast leaves goaltenders
  less mispriced on the skater line. That is consistent with part of what the level term absorbs
  being forecast bias. It is not tested beyond that.
- **The slope is still unstable.** The ratio of a goaltender's whole-path price response to a
  skater's has now read 1.07, 0.75, 0.79, and 0.73 or 0.81 on this subset, across four versions of
  the goalie forecast.

**The specification stays provisional. D7, whether skaters and goaltenders share one market, is not
settled.**

## What this settles and what it does not

**Settled, on the development pages:**

- A per-game goalie rate, pooled by games and shrunk toward a norm, is a better per-game forecast
  than production's implied rate (100% of resamples).
- Role in the shrinkage target adds nothing.
- Heavy shrinkage is right: from three seasons out, a goaltender's own record carries under a tenth
  of the weight, often none.
- With a real rate, the share model no longer damages squared error, and the combined forecast
  (rate × share × participation) is the best calibrated of every arm, overall and by role.

**Decided (2026-09-22):**

- **Production's season total is the default goalie season forecast.** It has the lower season
  error on both scores and ranks goaltenders better at every horizon. A smaller average bias does not
  outweigh that on its own, because positive and negative errors can cancel.
- **The decomposition (rate × share × participation) is carried as a sensitivity** into the
  control-year work, because it is horizon-specific and the control-year step needs season-by-season
  forecasts. It is not promoted on calibration alone.
- **How forecasts are scored from here, declared before the next comparison:**
  1. **Primary: squared error**, for any point forecast meant to enter an expected-value sum. It
     targets the conditional mean, which is what a sum of expected dollars needs.
  2. **Alongside it:** mean absolute error, for the size of a typical miss.
  3. **Also alongside:** bias by horizon and by role or tier.

  The hierarchy is fixed in advance so that a metric is not picked because a candidate happens to
  win on it.
- **The lowest WAR error is not automatically the best dollar valuation.** The salary floor and the
  control options make dollars a nonlinear function of the WAR path, so pricing the mean path need
  not give mean dollars. The eventual choice is tested on expected dollars and on the simulated
  distribution of outcomes, not on WAR scores alone.

**Not settled:**
- **Why production's total ranks better.** Candidates, none tested here:
  - it keeps 35% of the trailing total at every horizon, where the fitted rate keeps almost nothing
    from three seasons out;
  - a season total carries role and ability together, and the two are correlated.
- **What caused the pooled bias.** Swapping production's total for the rate, with participation and
  share held fixed, moves the pooled bias from +0.096 to +0.002. So on these arms and pages the change
  goes with the rate. That is not an identified decomposition. A pooled mean can move because errors
  in different groups offset differently, and the by-role table shows exactly that: the rate arm with
  trailing share is near zero overall while missing by −0.26 and +0.24 at the two ends.

## What is checked

Check 36, "the goalie rate is a rate, and cannot see the page", asserts four things:

- The trailing rate is unmoved when every season outside the three before the page is scrambled.
- Pooling is by games, on a synthetic goaltender whose answer is known exactly.
- The fit refuses a table that holds the page, and a thin horizon borrows a shorter one.
- On a real page, every forecast lies between the goaltender's own trailing rate and the norm.

Each has been broken on purpose to confirm the check catches it: a window that reaches the page,
pooling by seasons instead of games, and a forecast that overshoots past his own rate. All three
fail.

Check 37, "the forecast priced is the forecast tested", compares the price runner's conditional
season (rate × share, before participation) with the scored arm's. The comparison runs through the
contract census's name join, on every development page and every horizon from 0 to 7, where 6 and 7
must equal the arm's clamped horizon 5.
- It covers 4,759 cells, with a largest gap of exactly zero.
- It meets 1,235 cells on the share model's fallback and 1,235 on a borrowed rate horizon, so it
  tests the paths that failed.

Two deliberate breaks both fail it:
- restoring the old fallback (0.578 WAR apart at the 2015 page, four seasons out);
- a wrong clamp in the price runner only (1.94 WAR apart at the 2017 page, six seasons out).

Participation is left out of this check on purpose. The price runner dates it at each contract's
signing and the harness at 1 July, and check 34 covers that.

Suite: **37 passed, 0 skipped, 0 failed**.
