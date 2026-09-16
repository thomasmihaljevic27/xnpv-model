# A contract's value as a distribution, and what the point valuation was approximating

Run 2026-09-16 in `50_REBUILD/`. Rebuild plan Phase 5. Experimental. Development start years only;
the reserved market cohorts are refused by the guard. **Nothing adopted, and no production file
changed.**

## 1. What a point valuation cannot do

The chain values a contract by taking one forecast per season, averaging it into a production per
season, and pushing that number through the price line. That is the value of the **average path**.
A contract is worth the **average of the values**, and the two differ whenever the price of a path
is not a straight line in the production on it.

It is not a straight line, for two reasons that both push the same way. A club cannot pay less
than the league minimum, so a season where the player collapses costs the same as a season where
he is merely poor — the downside is truncated and the upside is not. And the market's own price
line is censored at that floor, so it bends near the bottom.

Both make the value of a path convex from below in its production, so the average of the values
sits above the value of the average. **The gap is not an error in the point valuation. It is the
quantity the point valuation was approximating**, and this is the first time it has been measured.

## 2. What the paths carry that the average does not

**An exit that sticks.** The point chain multiplies each season's production by that season's
probability of playing, which prices every player as a blend of himself and a ghost who plays 78%
of a season. On a path he either plays or he does not, and an exit carries forward. The marginal
probabilities the participation model reports are reproduced exactly by construction, so nothing
about the forecast changes — the zeros now arrive together instead of being smeared across every
season.

**A miss that persists.** This decides everything about a long contract and had never been
measured. If the misses were independent, a six-year deal's total would be six draws averaging out
and its spread would scale as the square root of the term. If a miss persisted entirely, the
spread would scale with the term.

Fitted on the same replayed misses the band is fitted on, as a permanent part plus a part that
fades:

| seasons apart | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|
| observed | 0.433 | 0.368 | 0.314 | 0.292 | 0.280 | 0.265 |
| fitted | 0.427 | 0.368 | 0.329 | 0.303 | 0.286 | 0.275 |

**0.253 of a miss is permanent, plus 0.263 fading at 0.66 a season.** Some of being wrong about a
player is a standing misjudgement that does not go away; some is form, or a role, or an injury,
and it passes. Neither dominates.

(Measured on the replay's calibration pages, which is the sample the band itself is fitted on and
therefore the consistent choice. The same correlations computed on the scored development pages
alone run a little lower — 0.394 at one season apart against 0.433 — which is a difference of
sample, not of method.)

**One thing is deliberately not drawn separately.** The rate per 82 and the share of the schedule
get no separate draws, because the quantity with a fitted spread is the season total *given he
played*, and that total's miss already contains both — a player who was healthy but worse and a
player who was as good but hurt are both in it. Splitting them would need two spreads where the
data supports one, and their product is what a dollar total reads anyway. This resolves the
standing flag that asked for separate rate and games bands: the joint object the simulation needs
is (participation, conditional season total), and that is what it draws.

**How the marginals survive.** The dependence is imposed with a Gaussian copula — correlated
normals, through the normal CDF to uniforms, then through the empirical shape the interval layer
already fitted. Each season's own distribution is left exactly as it was, so the coverage that has
been measured and reviewed carries over unchanged, and only the way the seasons move together is
new. Adding a shared shock instead would have changed both at once, and the marginal it changed is
the one with evidence behind it.

## 3. The identity the plan asked for

With the spread set to nothing and participation certain, every path is the same path, so the
simulation must return the point valuation exactly. This replaces the k=0 identity the plan
retired.

**300 contracts, largest gap $0.000000.** Checked on real contracts rather than a constructed
case.

## 4. What the paths are worth

The average production per season is the same either way — 0.3491 against 0.3487 across 1,217
contracts — so the whole of the difference below is the curvature and the floor.

| term | n | point $M | simulated | gap |
|---|---:|---:|---:|---:|
| 1 yr | 605 | −0.07 | +0.16 | **+0.23** |
| 2 yr | 324 | −0.09 | +0.15 | **+0.25** |
| 3 yr | 109 | +0.14 | +0.19 | +0.05 |
| 4 yr | 66 | +0.54 | +0.55 | +0.01 |
| 6 yr | 33 | +1.53 | +1.52 | −0.01 |
| 8 yr | 22 | +5.44 | +5.39 | −0.05 |
| **all** | 1,217 | +0.19 | +0.37 | **+0.18** |

| forecast | n | point $M | simulated | gap |
|---|---:|---:|---:|---:|
| below 0 | 174 | −0.41 | −0.19 | **+0.21** |
| 0 to 0.5 | 735 | +0.10 | +0.31 | **+0.22** |
| 0.5 to 1 | 199 | +0.56 | +0.68 | +0.12 |
| 1 to 2 | 91 | +1.66 | +1.71 | +0.05 |
| 2+ | 18 | −1.80 | −1.86 | −0.05 |

**The gap is concentrated exactly where the floor binds**, which is what the mechanism predicts:
short deals and low-production players, whose paths straddle the league minimum. For a star the
floor is never in reach, the price line is locally straight, and the gap vanishes. It is a real
effect worth a fifth of a million on the average contract and it changes no sign anywhere.

No percentage column is reported. The point surplus averages near zero by construction, because
the price line is fitted to these same contracts, so a gap expressed as a share of it reads in the
hundreds of percent and means nothing.

## 5. The spread, which did not exist before

| term | n | mean $M | sd | 10th | 90th | chance it loses | sd if seasons independent | widened by |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 yr | 605 | +0.16 | 0.87 | −0.38 | +1.18 | 37% | 0.87 | **0%** |
| 2 yr | 324 | +0.15 | 1.94 | −1.65 | +2.70 | 47% | 1.71 | 14% |
| 3 yr | 109 | +0.21 | 3.90 | −4.22 | +5.36 | 48% | 3.14 | 24% |
| 5 yr | 31 | −0.51 | 7.94 | −9.39 | +9.83 | 51% | 5.95 | 34% |
| 7 yr | 27 | +3.75 | 10.30 | −8.00 | +17.15 | 40% | 7.18 | **44%** |
| 8 yr | 22 | +5.34 | 11.31 | −7.60 | +20.05 | 38% | 8.02 | 41% |

A club signing an eight-year deal is not buying $5.3M of surplus. It is buying a distribution with
a standard deviation of $11.3M and a better-than-a-third chance of losing money.

**What persistence is worth, measured rather than asserted.** The last two columns redraw the same
contracts with the seasons made independent, which is what averaging them implicitly assumes.
Persistence widens the spread of a seven-year deal by **44%**. The comparison is within a
contract, not across terms — long deals go to better players with wider bands, so a spread that
grows with the term says nothing on its own. The one-year row coming back at exactly 0% is the
check: with a single season there is no dependence to impose and the two draws must agree.

## 6. Limits

- **Not a back-test.** Nothing is scored against a realised outcome and no trade is priced.
- **No RFA walk-away on the path.** A restricted player whose value collapses can be walked away
  from, which truncates the club's downside again and would narrow the lower tail. The rebuild
  tree has no terminal-value machinery yet, so this is absent and the downside is overstated to
  that extent.
- **Returns are not modelled.** The participation model lets a player come back after a missed
  season and about one exiter in five does; the absorbing path cannot honour a probability of
  playing that rises. On this sample **no term asks for one**, so nothing is lost here, but a
  sample that did would have its spread understated.
- **Goalies are untouched**, as everywhere else in the rebuild.
- **The persistence fit is three parameters on a curve that is nearly flat past three seasons.**
  Both weights are clipped at zero, which is what a three-parameter fit needs on a five-point
  curve, and that clipping is a choice.
- **2,000 paths** leaves Monte Carlo noise of a few hundredths of a win on an individual
  contract's average production.

## 7. What this unblocks

The valuation now produces a distribution, so the back-test statistic the plan asks for — a dollar
difference scaled by a declared positive gross-value measure — has something to be computed
against. Remaining before it: valuation integration and contract-by-contract dollar
reconciliation, then the back-test with its grouping rule and evaluation protocol declared in
advance.

## Files

    50_REBUILD/code/npv_simulation.py        the paths, the persistence fit, the self test
    50_REBUILD/code/run_npv_simulation.py    the run and its reports

Outputs, ignored under `50_REBUILD/output/`: `npv_simulation_run_log.txt`, `npv_simulation.csv`.
