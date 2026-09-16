# An aggregate contract simulator: value as a distribution over careers

Run 2026-09-16 in `50_REBUILD/`. Rebuild plan Phase 5, **prototype scope — not Phase 5 complete**.
Experimental. Development start years only; the reserved market cohorts are refused by the guard.
**Nothing adopted, and no production file changed.**

**Revised after independent review** (`NPV_Simulation_Review_Codex.md`, reviewing `95750f5`).
Two implementation defects and one scope claim, all accepted and fixed; several reporting claims
withdrawn. Section 8 lists them. Every figure below comes from one run after the fixes.

## 1. What a point valuation cannot do

The chain values a contract by taking one forecast per season, averaging it into a production per
season, and pushing that number through the price line. That is the value of the **average path**.
A contract is worth the **average of the values**, and the two differ whenever the price of a path
is not a straight line in the production on it.

It is not straight, and **the operative reason is the league minimum**: a club cannot pay less
than the floor, so a season where the player collapses costs the same as one where he is merely
poor. The downside is truncated and the upside is not, which makes the value of a path convex from
below, so the average of the values sits above the value of the average.

(An earlier version of this report also credited the censored price line with bending the curve.
`predict_tobit` returns a linear predictor; censoring affects the fitted coefficients, not the
shape of the prediction. The floor is the convexity.)

**The gap is not an error in the point valuation. It is the quantity it was approximating**, and a
point valuation is not wrong to average under dependence either — an expectation averages whatever
the dependence is. What dependence changes is the spread, and the value of a path once the price
line stops being straight.

## 2. What the paths carry

**An exit, as a path, with returns.** The point chain multiplies each season by its probability of
playing, pricing every player as a blend of himself and a ghost. On a path he plays or he does
not. The chain is two-state: a player who sits out can come back, at a rate estimated from seasons
before each decision date (about 0.10 across the window), and the chance of dropping out is solved
season by season so the model's own marginals still come back exactly.

**A miss that persists.** Fitted per page, as a permanent part plus a fading one:

| page | permanent | fading | fade rate | rank correlation at one season | return rate |
|---|---:|---:|---:|---:|---:|
| 2015 | 0.000 | 0.483 | 0.82 | 0.396 | 0.102 |
| 2018 | 0.198 | 0.367 | 0.56 | 0.404 | 0.096 |
| 2021 | 0.250 | 0.320 | 0.49 | 0.406 | 0.101 |
| 2025 | 0.253 | 0.263 | 0.66 | 0.427 | 0.106 |

The split between permanent and fading moves a great deal across pages and **the total adjacent
correlation barely moves at all** — 0.39 to 0.43 throughout. An early page's replay cannot reach
far enough to tell a standing misjudgement from one that fades, so the decomposition is weakly
identified there even though the quantity it decomposes is stable. The permanent and fading
weights are parameters of a chosen dependence model, not measured fractions of every forecast
mistake.

**The marginals survive.** Dependence goes in through a Gaussian copula, so each season keeps
exactly the distribution the interval layer fitted, whose coverage has been measured and reviewed;
only the way seasons move together is new.

## 3. What the review found, and what it cost

### Historical contracts were using future information

The first version fitted **one** calibrator on the latest page in the whole contract input — 2025,
whose replay contains outcomes through 2024 — and used its residual shape and its persistence for
every contract, all of which are earlier. Forecasts and price lines were rolling. The uncertainty
around them, the only part of this chain that reads outcomes, was not.

Each contract now uses its own page's shape, persistence and return rate. **A new check
corrupts every season at or after the decision date and requires the shape, the scale, the
persistence and the return rate to be identical to the last digit.** The existing leakage battery
could not have caught this: it tests the forecast and the band, and the defect was in the runner
that consumes them.

### The copula imposed the wrong correlation

Persistence is measured as a Spearman rank correlation, which is right for a long-tailed shape,
and the fitted numbers were handed straight to the normal draws as if the two scales were the
same. A Gaussian copula with latent correlation r delivers rank correlation (6/π)·arcsin(r/2),
always a little below r. Asking for 0.427 delivered 0.410.

Fixed by inverting: r = 2·sin(π·ρ/6). **The test is now analytic** — the relationship either holds
in closed form or it does not — with the simulated check kept as a sanity test at a tolerance
derived from the sampling error of a rank correlation. The old code fails the new analytic test at
every sample size; it passed the old Monte Carlo test at three thousand paths and failed only at
six hundred thousand.

### Returns were excluded, not shown to be absent

The first version made an absence permanent and argued nothing was lost because no term asks for a
probability of playing that **rises**. That does not follow, and the review's counterexample
settles it: 60% play both seasons, 30% only the first, 10% only the second — the marginal falls
from 90% to 70% and one path in ten is a return. A falling marginal says nothing about whether
anyone comes back.

Returns are now modelled. The absorbing version is kept beside them as the sensitivity it always
was, and it turns out to cost little: the eight-year cohort's average within-contract standard
deviation is $11.02M with returns against $11.09M absorbing. Small — but now measured instead of
asserted. Two of 1,217 terms need an exit probability clipped to hold the marginal, so for those
the model's own probability of playing is not reproduced exactly.

## 4. The identity

With the spread set to nothing and participation certain, every path is the same path, so the
simulation must return the point valuation. Checked on 300 real contracts **against
`ProductionCurrency.value` rather than against this file's own pricing helper on both sides** —
the first version did the latter and would have passed with a shared pricing bug in it.

**Largest gap $1.49e-08.**

## 5. What the paths are worth

Average production per season is the same either way — 0.3491 point against 0.3495 simulated, a
Monte Carlo difference, not an identity — so the difference below is the floor.

| term | n | point $M | simulated | gap |
|---|---:|---:|---:|---:|
| 1 yr | 605 | −0.07 | +0.16 | **+0.23** |
| 2 yr | 324 | −0.09 | +0.15 | **+0.24** |
| 3 yr | 109 | +0.14 | +0.19 | +0.05 |
| 6 yr | 33 | +1.53 | +1.56 | +0.03 |
| 8 yr | 22 | +5.44 | +5.51 | +0.07 |
| **all** | 1,217 | +0.19 | +0.38 | **+0.19** |

| forecast | n | point $M | simulated | gap |
|---|---:|---:|---:|---:|
| below 0 | 174 | −0.41 | −0.19 | **+0.21** |
| 0 to 0.5 | 735 | +0.10 | +0.31 | **+0.21** |
| 0.5 to 1 | 199 | +0.56 | +0.70 | +0.14 |
| 1 to 2 | 91 | +1.66 | +1.75 | +0.08 |
| 2+ | 18 | −1.80 | −1.79 | +0.01 |

Concentrated where the floor binds — short deals and cheap players — and vanishing for stars whose
paths never approach it.

**228 of 1,217 individual contracts change sign** between the point valuation and the simulation.
The first version of this report said there were none, which was read off the tier means and was
false of the contracts. The fixed-tier means do keep their signs. Those are two different
statements and they are reported apart.

## 6. The spread

A **cohort summary**, averaging statistics across the contracts in each row rather than describing
one representative distribution:

| term | n | mean $M | sd | 10th | 90th | chance it loses | sd without the miss's dependence | widened by |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 yr | 605 | +0.16 | 0.87 | −0.38 | +1.17 | 37% | 0.87 | 0% |
| 3 yr | 109 | +0.19 | 3.85 | −4.20 | +5.27 | 48% | 3.13 | 23% |
| 7 yr | 27 | +3.69 | 10.06 | −7.81 | +16.83 | 39% | 7.14 | **41%** |
| 8 yr | 22 | +5.51 | 11.02 | −7.09 | +19.93 | 38% | 8.01 | 38% |

The last two columns redraw the same contracts **on the same random draws** with the cross-season
dependence of the forecast's miss removed. **Participation is unchanged in both arms**, so the
seasons are not independent there — this isolates the conditional performance error and nothing
else, and is not an independence counterfactual. The one-year row comes back at 0% because a
single season has no dependence to impose; on common draws that is now exact rather than a
rounding.

## 7. Scope: what this is and is not

It is an **aggregate contract simulator** for the current price interface, which consumes average
and first-season production. Its conditional-season-total draw already contains both rate and
availability error, which is why they are not drawn separately.

It does **not** fulfil the plan's joint rate/games/participation design for later consumers, and
**Phase 5 is not complete**. Still absent:

- **The RFA walk-away and control years.** A restricted player whose value collapses can be walked
  away from, which truncates the club's downside again. The lower tails here are too heavy to that
  extent — and the absence of that option does not mean every signed-contract downside was
  unavoidable.
- **Goalies**, as everywhere in the rebuild.
- **Contract-by-contract dollar reconciliation** against the production spine.
- Not a back-test: nothing is scored against a realised outcome and no trade is priced.

## 8. Claims withdrawn

1. **"Phase 5 built."** Overstated against the written plan. This is a prototype aggregate
   simulator.
2. **"No sign changes anywhere."** 228 contracts change sign. Group means are a different
   statement.
3. **"The independent-seasons comparison."** Participation stays correlated in both arms; it
   isolates the conditional performance error.
4. **"A point valuation implicitly assumes independent errors."** It does not — expectations
   average under any dependence. Dependence matters to the spread and to nonlinear path valuation.
5. **"Nothing is lost by omitting returns, because no term has rising marginals."** A
   non-sequitur. Returns are now modelled.
6. **"The censored price line bends near the floor."** The floor is the convexity; the tobit
   prediction is linear.
7. **The one-year 0% was two random samples rounding to agreement**, not an identity. Now run on
   common draws.
8. **Figures mixing two runs** (0.3487 against 0.3495, $5.39M against $5.34M). Everything above is
   from one run.

## Files

    50_REBUILD/code/npv_simulation.py        paths, persistence, returns, the self test
    50_REBUILD/code/run_npv_simulation.py    the run and its reports

Outputs, ignored under `50_REBUILD/output/`: `npv_simulation_run_log.txt`, `npv_simulation.csv`.
The reviewer's reproduction is `50_REBUILD/code/review_npv_simulation.py`.
