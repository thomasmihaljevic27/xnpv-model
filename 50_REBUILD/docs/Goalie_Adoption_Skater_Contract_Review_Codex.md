# Goalie adoption and skater contract-input review

Reviewed 2026-09-23. Candidate: `1b7d9a7`, including goalie adoption `68b0e13`.
Independent checkout: `50_REBUILD/output/goalie_adoption_skater_review`.

## Decision

The goalie default is consistently set to no contract inputs. The skater
experiment isolates the participation inputs correctly, but its contract-dollar
comparison does not use contract information available at signing. Correct that
comparison before closing the skater decision. The existing no-contract leader
can remain in use while this is repaired.

## Finding: the skater dollar comparison uses July contract status at signing

`run_skater_contract_test.dollars` calls `contract_price_model.attach_forecasts`.
That function batches contracts by the last completed season and predicts once
per batch. `_ParticipationMixin._p_play` calls `ParticipationModel.predict`
without its `as_of` argument, which defaults to July 1 of the forecast page.
Consequently, a contract signed later is invisible to the participation forecast
used to value that very contract. Sharing a season history does not imply sharing
contract information.

Holding the fitted model and season history fixed gives these first-contract-season
participation probabilities:

| Contract | Signing date | Variant | July information | Signing information |
| --- | --- | --- | ---: | ---: |
| 4989, Jay Bouwmeester | 2019-04-08 | old contract definition | 0.243530 | 0.623374 |
| 7041, Zdeno Chara | 2021-10-10 | old contract definition | 0.226883 | 0.616265 |
| 7041, Zdeno Chara | 2021-10-10 | contract status only | 0.336686 | 0.589150 |

In the development census, first-season contract status differs between those
dates for 1,429 of 1,896 eligible contracts. This is an input audit, **not** the
count affected among the 1,217 priced contracts. Bouwmeester's status-only result
does not change: the 2018 fit has no useful fitted status effect. That control is
retained in the reproduction script.

The July-page season test is still a valid July-page comparison. The problem is
the separate assertion that the signing-date dollar gain is too small to matter.
The reported dollar scores measure a different information set, and the direction
or size of their correction has not been established.

Required repair:

1. Keep season data and fitted parameters dated as before; supply each contract's
   signing date for its participation features, including extrapolated horizons.
2. Apply the same rule to historical training forecasts entering each price fit.
   Retain the fixed leader currency as the primary comparison.
3. Re-run the common-contract dollar comparison and reconsider its recommendation.
4. Add a guard through the actual attachment caller. Moving a visible signing
   across the decision date must change a contract-aware forecast, while changing
   a later contract must not. The no-contract leader must remain unchanged.

The existing 41-check suite passes despite this defect. Its goalie signing-date
guard is correctly pinned to a contract-aware goalie specification, but does not
exercise this skater caller. Check 23 discovers classes in `ability_forecast`;
it does not discover the new classes defined in `run_skater_contract_test`.

## Scope qualifications

The small movement in point valuations does not establish that path simulations
would have the same ordering. Participation changes the mass at zero and can
affect floors and control decisions. Keep the absence of that experiment explicit.
Likewise, a bootstrap interval containing zero is absence of detected calibration
error, not proof of calibration. Neither point requires reopening the goalie
implementation or forcing adoption of contract inputs.

The goalie branch's share of the contract census is a scope reason for deferring
more work, not a measured bound on its effect on trade conclusions. Phase 5 and
the trade back-test remain distinct from these development checks.

## Reproduction

The full suite returns **41 passed, 0 skipped, 0 failed**. The skater runner
reproduces all five season-score rows and both dollar tables to within $0.001M at the displayed precision. An independent
artifact audit confirms 40,510 unique, matching (career, page, horizon) cells
per variant, finite scores, and exactly unchanged ability and games-share columns.

| Skater specification | Brier score | Season WAR RMSE | Point-dollar RMSE, $M |
| --- | ---: | ---: | ---: |
| Leader | 0.133960 | 0.815525 | 3.534 |
| Old contract definition | 0.132599 | 0.814675 | 3.526 |
| Period and status | 0.132790 | 0.814996 | 3.542 |
| Period only | 0.134049 | 0.815554 | 3.537 |
| Status only | 0.132789 | 0.815050 | 3.528 |

The dollar table has 1,217 valued contracts and 1,176 completed terms scored.
These are reproduced **as implemented**, subject to the dating finding above.

A fresh default goalie control/scoring run writes the `_none` artifacts. It
reproduces 21 priced control rights, informed values of $1.051M and $1.091M,
rank correlation 0.938, and 133 completed contracts. On the production forecast's
common currency, simulated RMSE is $7.111M with bias +$0.082M; the rate arm wins
30% of squared-error and 99% of absolute-error resamples. The production contract
PIT mean is 0.486 [0.439, 0.531], variance 0.082 [0.071, 0.091]. Default selection,
named sensitivity settings, suffixed artifact consumers, and the pinned goalie
date guard agree with the adoption record. No new goalie blocker was found.

This review re-ran the integrated goalie control/scoring path, not every
standalone goalie diagnostic or every old sensitivity. Reporting uses the same
2,000 career resamples aggregated by career for speed; forecasts and paths are
unchanged.

`50_REBUILD/code/review_goalie_adoption_skater.py` supplies the isolated candidate
environment and modes for setup, the full suite, the skater runner, the date audit,
the default goalie control/scoring runner, and matched-forecast assertions.
Generated logs and artifacts remain under ignored `50_REBUILD/output`.

No candidate merge, forecast/default change, vendor write, or canonical
production-output write was made by this review.
