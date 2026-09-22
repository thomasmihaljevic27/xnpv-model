# Goalie rate forecast review

Reviewed 2026-09-22. Candidate `0bec937`, tested in an isolated worktree.

## Decision

The principal results reproduce. One bounded implementation correction remains:
the price consumer and scored rate/share arm use different fallbacks when the share
model lacks a fitted horizon. Align those paths and add an identity check before
closing this review. The measured effect on current contract prices is small and
does not reverse the conclusion. No redesign of the rate model is required by this
finding. Earlier review closures stand.

Keep production's total as the default season benchmark and the decomposed rate
forecast as a sensitivity. Use squared error as the primary point-forecast score
when estimating an expected quantity, with MAE, subgroup bias and eventual dollar
performance reported alongside it. No model adoption or D7 closure here.

## Finding: price fallback differs from the scored forecast (P2)

`run_goalie_price_line.py:150-157` starts with the rate frame's `s_trail` and retains
it when `ShareModel.predict` returns None. That share pools all recorded seasons
using exponential recency weights. The scored `FlatShare` arm inherits the
participation runner's fallback from `GoalieModel.share_for`: qualifying seasons
only, linearly increasing weights across available seasons, and a 0.05 lower bound.
Both paths use the same fitted share model where one exists; their fallback rules
are different.

A direct comparison of conditional season forecasts (rate times share, before
participation) finds 435 differing subject/page/horizon cells:

| Page | Horizons | Maximum absolute WAR difference |
| --- | --- | ---: |
| 2015 | 4, 5 | 0.578 |
| 2016 | 4, 5 | 0.803 |
| 2017 | 5 | 0.686 |
| 2018 | 5 | 1.612 |

The new check tests rate pooling and shrinkage, but never compares the consumer
with the scored arm. All 36 checks therefore pass despite the mismatch.

I independently replaced the price consumer's conditional forecast with the scored
`FlatShare` arm, keeping the signing-dated participation model, sample and price
specifications unchanged. Eight of 165 forecast-attached development contracts
change; the maximum change in average forecast WAR is 0.00760 per season (Carey
Price, contract 4077). The difference is much smaller than the conditional-season
maximum because these horizons have low participation and are averaged over terms.

On the same 137 priced contracts, level-only price MAE changes from 0.008503 to
0.008504; level-and-slope changes from 0.008623 to 0.008626. The extra slope still
wins 28% of resamples, and the UFA whole-path ratio remains 0.81. The headline is
robust to this repair, but the two implementations should not carry the same model
label while generating different forecasts.

**Required repair:** use one shared rule for the conditional rate/share forecast,
including missing-fit fallbacks. Test consumer equality against the scored arm on
every development page and horizon, including borrowed and clamped horizons. Break
the fallback deliberately to prove that the guard fires. Either fallback can be a
declared design choice; the forecast and valuation must use the same one.

## Results reproduced

Full suite: **36 passed, 0 skipped, 0 failed**. Six arms each return 3,683 scored
cells. These season-WAR results reproduce:

| Arm, participation model in each | MAE | RMSE | Bias |
| --- | ---: | ---: | ---: |
| Production total, trailing share | 1.432 | 2.073 | +0.096 |
| Rate with flat norm, trailing share | 1.441 | 2.104 | +0.002 |
| Rate with flat norm, share model | 1.466 | 2.099 | +0.030 |

Games-weighted rate MAE improves from 4.157 to 3.903. The runner bootstraps the
unweighted rate comparison, so I also computed the weighted comparison independently
by resampling whole goalie careers. It improves in 100% of 2,000 resamples; the
95% interval for the rate MAE difference is [-0.402, -0.115] WAR per 82.

The original price comparison reproduces on 137 contracts across 82 goalies:
level-only MAE 0.008635 under production's forecast versus 0.008503 under the rate
forecast. The rate forecast wins 68% of paired resamples, which does not establish
an improvement. Both sides are refitted on the common contract sample. There are
165 forecast-attached contracts before price fitting, versus 205 for production.
The sample restriction must accompany these results.

Independent negative tests catch the three guarded defects: a window shifted to
include the current season, equal games assigned to each season, and a forecast
that overshoots its own rate/norm interval. An independent end-to-end annual test
changes future WAR, rate, games and share; the page-2019 rate, share and participation
predictions change by exactly zero. These checks support the rate implementation;
they do not cover the consumer mismatch above.

## The two modeling choices

### Which forecast to carry

Production's season total is the stronger current point-forecast benchmark: it has
lower season MAE and RMSE, while the rate/share arm has smaller average errors in
the reported role groups. Near-zero pooled bias alone is insufficient to prefer it;
positive and negative errors can cancel. Retain the rate arm for the control-year
comparison because its decomposition supports that experiment, but do not promote
it on calibration alone. Compare expected dollars and downside distributions before
adoption. The skater contract-data decision remains separately open as recorded in
the preceding closure.

### Which score to use

Squared error targets the conditional mean; absolute error targets the conditional
median. For a point forecast intended to enter an expected-value sum, squared error
is the relevant primary score. MAE remains useful for typical miss size, and bias
by horizon and role remains necessary. Declare that hierarchy before subsequent
comparisons rather than choosing the metric on which an arm happens to win.

This does not make lowest WAR RMSE automatically equivalent to best valuation.
The salary floor and control options make dollars a nonlinear function of the path:
pricing the mean WAR path need not give mean dollars. Assess simulated dollars and
the distribution as part of valuation validation. A direct forecast of mean dollars
can itself be evaluated with squared dollar error.

Also distinguish the target of the new weighted rate fit. Weighting squared error
by realized games estimates an exposure-weighted rate, not automatically the
unweighted mean rate of a randomly chosen played season. Games and performance may
be related. Define that target explicitly when building joint rate/workload paths;
the product of separately fitted means is not a general identity for expected
season production. This is a qualification for the remaining joint-path design,
not a claim that the current empirical improvement is spurious.

## Evidence and scope

Audit: `50_REBUILD/code/review_goalie_rate.py`, modes setup, run, checks, price,
audit, bridge and scores. Generated logs, independent weighted-score results and
eight changed contract IDs use the `goalie_rate_` prefix under
`50_REBUILD/output/`; none is committed. The bridge mode changes only in-memory
behavior to measure the identified inconsistency. No candidate implementation edit,
merge, source write, canonical production write or adoption. All rebuild documents
remain under `50_REBUILD/docs/`.
