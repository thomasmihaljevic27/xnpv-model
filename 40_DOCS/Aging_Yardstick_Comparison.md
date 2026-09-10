# Shared and target-specific aging yardsticks

Test date: 2026-09-10. Production model unchanged.

The target-specific yardstick produced slightly larger prediction errors. Across the two tests and two measures of performance, average errors increased by 0.10%-0.18%. This gives no reason to replace the shared yardstick with the alternative tested here. The difference is small, and the result does not establish that a shared yardstick is the best possible approach.

## What changed

The model compares a target player with historical players of the same age and position. Their profiles describe playing style, performance per 82 games, ice time, and recent improvement or decline. A smaller distance between profiles means a closer match. The target player is involved in each of these distances under both approaches.

The yardstick determines how much influence a comparable loses as that distance increases:

- The existing approach uses one shared yardstick. It takes the median distance between sampled pairs of historical profiles within the same position. Those pairs can come from different ages; the forward-forward and defence-defence distances are pooled to obtain the median.
- The alternative calculates a new yardstick for each target at each forecast date. It takes the median distance from that target to the eligible historical profiles of the same age and position.

Both approaches give the closest profiles the most weight. The alternative changes how quickly those weights fall. If the target's median distance is larger than the shared yardstick, it gives the available comparables more weight. If it is smaller, it gives them less weight. Because the broader position-and-age average retains ten units of weight, this also changes how much the model relies on that broader average.

This test therefore measures the combined effect on comparable weights and reliance on the broader average. It keeps the ten-unit setting fixed, along with the 55% weight on the player's own recent performance, profile construction, feature weights, and projection rules. It does not separately optimize those settings for the alternative.

## How the comparison was run

Players were divided into five groups. For each group, the aging model was rebuilt using the other four groups. A target's entire career was excluded from the training data. Only the target's history available at the forecast date was then supplied to make that player's prediction. The same forecast was made under each yardstick and compared with the same observed outcome.

The first test used the full historical sample for the training players and predicted performance one to six years ahead. This excludes the target's future from model construction, but allows later seasons from other players to inform the aging pattern.

The second test restricted training to seasons available at each forecast date. It used origins from 2017-18 through 2022-23 and predicted one to three years ahead. For example, a forecast made after 2018-19 used training seasons through 2018-19. Both tests used the same five career groups. These are exploratory comparisons using the current reconstructed source data and previously selected model settings; they are not untouched prospective validation samples.

Two outcomes were checked. The first was future WAR per 82 games, which measures the performance rate predicted by the aging curve. The second applied the curve's percentage change to a trailing season-total baseline, using the production model's 60/40 weighting, shortened-season adjustments, negative-baseline rule, and ratio limits. This checks whether the result survives the conversion from the curve into projected season production.

The season-total test is a matched-sample check of that calculation. It builds its baseline from `WAR_with_age.csv`, rather than running the contract pipeline's `WAR.csv` lookup. It covers forecasts with usable aging profiles and observed future seasons of at least 20 games. It does not test exits, survival weights, contracts, dollar values, missing-curve fallbacks, or the complete contract back-test. Its horizons begin one year after the valuation season, which is two years after the last observed season used to build the profile.

## Results

Average absolute error is the average distance between a forecast and the observed result, ignoring whether the forecast was too high or too low. Smaller values are better. The first two rows are in WAR per 82 games; the last two are in schedule-adjusted season-total WAR.

| Comparison | Forecast-outcome pairs | Players | Shared yardstick error | Target-specific error | Increase in error |
|---|---:|---:|---:|---:|---:|
| Performance rate, full-era training | 26,212 | 1,055 | 1.00238 | 1.00337 | 0.10% |
| Performance rate, historical training windows | 8,278 | 840 | 1.00431 | 1.00608 | 0.18% |
| Season total, full-era training | 19,764 | 938 | 0.93744 | 0.93892 | 0.16% |
| Season total, historical training windows | 5,242 | 750 | 0.92938 | 0.93042 | 0.11% |

A player can contribute several forecast dates and horizons. These counts are therefore not counts of independent observations. The historical check overlaps the first test and is a check on its training window, rather than a second independent sample.

The target-specific rule also had larger errors when larger misses received more weight, measured by root mean squared error. For the performance-rate outcome, it lost in four of the five career groups under full-era training and all five under historical training. For season totals, it lost in all five groups under both training windows.

The one-year performance-rate forecast showed the largest percentage deterioration among the tested horizons: 0.27% under full-era training and 0.32% under historical training. The pooled results for forwards and defencemen both moved in the same direction. Players starting at three or more WAR per 82 games also had larger average errors with the alternative.

Uncertainty was assessed by resampling whole player careers 2,000 times, keeping each player's forecasts together. The estimated increases in average error and their 95% intervals were:

| Comparison | Increase | 95% interval |
|---|---:|---:|
| Performance rate, full-era training | 0.00099 | 0.00036 to 0.00167 |
| Performance rate, historical training windows | 0.00178 | 0.00099 to 0.00271 |
| Season total, full-era training | 0.00149 | 0.00102 to 0.00198 |
| Season total, historical training windows | 0.00103 | 0.00041 to 0.00169 |

These intervals condition on the fitted models and do not account fully for overlapping training groups or prior selection of model settings. They support a small disadvantage for this alternative within the comparison; they do not make the difference economically substantial.

## What this says about the yardstick

The two approaches usually produced similar yardsticks. In the full-era test, the middle target-specific yardstick was 97% of the shared value. The middle 80% ranged from 82% to 126%. Average absolute changes to the forecasts were about 0.012 WAR per 82 games and 0.009 season-total WAR.

The concern that an unusual player could receive too much influence from weak comparables remains plausible, but this test cannot establish it as the explanation for the result. Defining a weak match in advance as a target median distance at least twice the shared yardstick left only ten players with scored performance-rate forecasts in the full-era test and three in the historical check. Their average errors rose, but the group is too small for a firm conclusion about unusual players generally.

The supported decision is to retain the current shared yardstick. A target-specific median of the eligible pool did not improve either forecast outcome with the remaining settings held fixed. Different target-specific rules, or joint adjustment of the yardstick and pooling weight, remain untested.

## Data issue and reproduction

The initial integrity check found that the source's `Erik Gustafsson` and `Erik Gustafsson 88` rows collapse to the same career key. Two qualifying seasons then share age 23. The experiment excluded that career from both training and evaluation in both alternatives. Production data and identity handling were left unchanged; this needs a separate identity review before correction.

The comparison runs through `20_CODE/aging_bandwidth_test.py`, version 1.0, with seed 20260910. It calls the existing aging projection code and substitutes only the weighting method for the alternative. Checks confirmed disjoint training and target careers, reproduction of the shared Gaussian weights, identical paired forecast ages, unique forecast keys, finite predictions, and unchanged hashes for the source and two production scripts.

The five generated artifacts in `30_OUTPUT/` begin with `aging_bandwidth_test_`: `design.json`, `predictions.csv`, `origins.csv`, `summary.csv`, and `run.json`. The design records the comparison before fitting; the run file records input hashes and completion. Generated outputs remain outside Git. This local run needed a process-level `OUTPUT_DIR` override because the configured value was a template path. It also used `python-dotenv` installed under the ignored `Work/aging_test_dependencies` directory. No permanent environment configuration was changed.
