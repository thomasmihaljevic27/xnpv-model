# Stress-testing the player model

Run 2026-09-15 in `50_REBUILD/`. Development seasons 2015–2021 only; the confirmatory seal is
untouched. Leading model: calibrated total, three-season window, survivorship-corrected aging,
participation.

An average is a place for a failure to hide. Every headline so far has been a mean over 6,124
player-seasons a horizon, and a model can win that comfortably while being useless on
defencemen, or on players with one season of history, or in 2020.

## What passed

**It wins every subgroup.** Against what the chain does today, there is no group where the
rebuild is worse:

| by position | | | by age | |
|---|---:|---|---|---:|
| defencemen | −31.8% | | 22 and under | −4.8% |
| forwards | −29.1% | | 23–26 | −20.3% |
| | | | 27–30 | −36.5% |
| | | | 31–33 | −55.2% |
| | | | **34 and over** | **−75.8%** |

By trailing level it ranges from −23.9% (3+ wins) to −45.7% (below replacement). By experience,
−14.8% to −50.5%. By horizon, −15.8% at the valuation season to −43.5% five seasons out.

**It wins every season, 7 of 7**, from −38.1% in 2015 to −22.3% in 2021.

**The whole chain is frozen at the decision date.** The season table's guard has always passed,
but it had never been run on the full chain with aging, participation and the survivorship
correction in it. Deleting every season at or after the decision date changes the forecast by
**exactly 0.00e+00** on both pages tested. Nothing downstream of the season table reaches
forward.

**The 2023-24 export break is not distorting anything.** Seasons on either side of it score the
same (0.504 against 0.499). Carrying the unallocated residual as a seventh component works.

**Edge cases do not produce nonsense.** Negative trailing anchors score better than average
(0.245), players who appeared in under 20 games are handled (0.232), and players 36 and over are
the best-forecast group in the model (0.108, bias +0.004).

## What failed

### 1. It under-predicts everywhere, and worst at the top

| decile of prediction | n | predicted | actual | miss |
|---|---:|---:|---:|---:|
| 1 | 1,838 | −0.130 | −0.039 | −0.091 |
| 5 | 1,837 | 0.116 | 0.158 | −0.042 |
| 9 | 1,837 | 1.026 | 1.147 | −0.120 |
| **10** | 1,838 | **1.951** | **2.229** | **−0.279** |

Every decile misses low. The model is systematically conservative, increasingly so as it gets
more optimistic.

**The mechanism is the shrinkage, not participation.** Decomposing the top decile:

| | model | actual |
|---|---:|---:|
| probability of playing | 0.984 | 0.988 |
| games share | 0.838 | 0.895 |
| **rate per 82** | **2.360** | **2.698** |

Participation is nearly perfect. The rate is 12.5% low. **The reliability shrinkage pulls the
genuinely elite too far toward the norm** — it cannot tell a player who is hot from a player who
is good, and at the top of the distribution most of them are good.

This is the same defect as the star bias reported all session, now located. A candidate fix is
to let the shrinkage weaken at high exposure and high level, where the evidence is strongest.
That is a model change and another look at the development seasons, so it is recorded as a test
to run rather than a tuning to apply.

### 2. Young players are the weak spot

| | n | error | bias |
|---|---:|---:|---:|
| aged 20 and under | 1,526 | **1.034** | **−0.346** |
| debut-season players | 3,386 | 0.511 | −0.134 |

The 20-and-under group is the worst-forecast population in the model by a factor of two, and the
22-and-under subgroup is the only one where the rebuild barely improves on today's chain
(−4.8%, against −30% or better everywhere else).

Both halves are wrong for the same reason: the model expects too little of them. It predicts a
0.781 chance of playing against 0.867 actual, and a 1.164 rate against 1.626. **A young player
who reaches the NHL at all is a selected survivor** — clubs do not promote 19-year-olds who are
not ready — and the model, fitted on everyone, does not know that.

This is the population the prospect pillar exists to price. The right fix is probably a prior
from that pillar rather than more machinery here, and the plan already says so.

### 3. The advantage is shrinking, year on year

| page | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---:|---:|---:|---:|---:|---:|---:|
| improvement | −38.1% | −36.9% | −32.3% | −27.0% | −26.6% | −25.2% | −22.3% |

Seven wins out of seven, but monotonically narrowing — a 16-point decline across the
development window.

**This predicts a smaller advantage on the confirmatory seasons.** They are 2022–2025, further
along the same trend, and if it continues the rebuild's edge there will be nearer 20% than 40%.
Recording it now, before the confirmatory run, so that a smaller number then is a prediction
confirmed rather than a disappointment explained.

The cause is not established. It could be the trailing window having more seasons to work with
on early pages, or something about the recent game, or the shortened 2019-20 and 2020-21 seasons
sitting in the trailing window of the late pages.

## What this means

The model is sound: no subgroup failure, no leakage anywhere in the chain, no era where it
loses, and sensible behaviour at every edge tested. The three weaknesses are all *conservatism*
— it under-rates the best players, under-rates the youngest, and its edge is narrowing — and
none of them is the kind of failure that invalidates a result.

The first two are diagnosed rather than merely observed, which makes them fixable. The third is
a caveat to carry into the confirmatory run.

---

# Acting on failure 1: letting the pull weaken at the top

The stress test located the star bias in the rate rather than participation, and in a specific
place: a straight pull-back toward the league is the best *linear* predictor, and a linear
predictor undershoots at the top whenever the true relationship bends. It does bend here,
because a high trailing number from a genuinely good player regresses less than the same number
from a lucky one — and at the top of the distribution most of them are good.

Four ways of letting it bend, all fitted on the rolling window like everything else:

| model | valuation | +2 | +4 | +5 | top-decile miss | star bias |
|---|---:|---:|---:|---:|---:|---:|
| leader (current) | 0.5501 | 0.5260 | 0.4616 | 0.4171 | −0.279 | −0.418 |
| + slope above one win | 0.5492 | 0.5248 | 0.4606 | 0.4164 | −0.262 | −0.375 |
| **+ slopes above one and two** | **0.5483** | **0.5242** | **0.4602** | **0.4156** | **−0.226** | −0.435 |
| + level × evidence | 0.5496 | 0.5257 | 0.4613 | 0.4167 | −0.262 | −0.393 |
| **+ hinge and evidence** | 0.5490 | 0.5248 | 0.4607 | 0.4163 | −0.252 | **−0.365** |

All four beat the current leader at every horizon. The two best, tested paired and clustered by
career, improve at **6 of 6 horizons with every interval excluding zero** — the two-hinge version
by 0.22% to 0.36%, the hinge-and-evidence version by 0.18% to 0.25%.

**They are real and they are small.** A third of a percent on a 0.42-win error is about
0.0015 wins, and no one should present that as the fix for anything. What is not small is the
top-decile miss, which falls from 0.279 wins to 0.226 — a fifth of the calibration failure
removed by letting one slope change.

**The two leaders trade off in the direction this project cares about.** Two hinges give the best
aggregate error and the best calibration at the top of the *prediction* distribution, but leave
the 3-plus trailing tier slightly worse (−0.435 against −0.418). The hinge-and-evidence version
gives up a little aggregate accuracy and is the only variant that improves the star tier
materially, to −0.365 — a 13% reduction in how far the model under-rates the players who carry
the surplus.

**Adopted: hinge and evidence.** It improves aggregate error and the star tier together, where
the alternative buys the first with the second. That is the same tension that has run through
every round of this rebuild, and the same answer: on a project about surplus value, a variant
that is better everywhere except the expensive players is not better.

The change does not close the gap. The model still under-rates its best players by a third of a
win over the first three seasons, and the remaining bias is now the clearest single target left
in the player chain.
