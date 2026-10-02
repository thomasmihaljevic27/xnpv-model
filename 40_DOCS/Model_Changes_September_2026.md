# Changes to the Player Model, September 2026

This note explains what changed in the player model on 28 September 2026 and why. It covers
changes that affect how the aging curve and the exit risk are built, the settings that were
tested and kept, and how the rebuilt model handles the same points. Each figure comes from a
recorded test or run; the scripts and reports are listed at the end.

## 1. What the Model Does, in Brief

The model values a player's contract season by season.

- Recent level. His starting level is a 60/40 weighted average of his wins above replacement in
  the last two seasons.
- Aging. Each later season applies the aging curve to that level. A player below replacement
  level is instead projected at replacement level after the current season.
- Value. Projected wins are priced in dollars, with a floor at the league minimum.
- Survival. The value is multiplied by the chance he is still in the league, which is the exit
  risk.
- Surplus. His cap hit is subtracted, and the result is discounted at 3% a year.
- Control years. For a player who will be a restricted free agent, his control years are added,
  priced against his qualifying offers and the chance his team keeps his rights.

The aging curve is built from comparable players. Players of the same age and position are
weighted by how similar their recent profile is, and the weighted average of how those players
changed from one year to the next, blended with the league average, gives the curve.

## 2. Changes Made

### The aging curve uses only seasons before the valuation date

Before this change, the aging curve was built once from all seasons in the data. A valuation
dated July 2018 therefore drew on comparable players' seasons from 2018-19 onward, which no team
could have seen. This affected four pieces: the comparable players themselves, the averages and
spreads used to standardize their profiles, the yardstick that turns profile distance into
similarity, and the league-average curve the comparables are blended with.

The curve is now rebuilt for each valuation season from seasons that had finished before it. A
2018 valuation uses seasons up to 2017-18 only.

This costs some accuracy. On the original age table, the average size of season forecast misses
rose 1.7%. That 1.7% was accuracy the model had borrowed from information no team had. With the
age table corrected (next item), the cost falls to 0.8%.

### Older careers restored to the age table

Each player's age comes from joining his birthdate to his seasons. The birthdates of players who
retired before 2018 come from a separate Elite Prospects file, because the contract export holds
almost no player who retired before about 2018. The join was reading that file from a folder it no
longer sits in and skipped it without an error. As a result, 1,278 of 3,199 skaters had no age.
Only 17% of 2007-08 seasons had an age, against 100% from 2018-19.

This mattered because a player without an age cannot enter the pool of comparable players. The
pool therefore held mostly careers that lasted into the contract years, which is a selection on
survival. With the file read, 99.9% of seasons have an age. The comparable pool grew from 7,531
to 10,057 two-season profiles and from 1,172 to 1,813 careers. The join now stops with an error if
the file is missing.

With the older careers restored and the curve limited to earlier seasons, forecast misses are
0.6% smaller than they were with neither change. The version with no look-ahead is, therefore,
more accurate than the original.

### Birthdates corrected

Checking the restored table turned up two older errors.

- Ten retired players had a sibling's or namesake's birthdate. The join matches on last name,
  first initial, and position when only one player in the contract export fits; for a retired
  player, that one player can be his brother. For example, Rick Nash had Riley Nash's birthdate
  (1989 instead of 1984). The others are Marcel Hossa, Jared Staal, Taylor Pyatt, Brett and Brody
  Sutter, Mark Cullen, Patrick Holland, Chris Brown, and Jeff Schultz. Each date was checked by
  hand, and the join now stops if an identifier is shared by two names not recorded as the same
  player.
- Two players had a wrong date from the Elite Prospects scrape: Alex Picard (the Columbus forward)
  and Mikko Lehtonen (the Boston forward). Both are corrected and take effect at the next run of
  the age join.

### The exit risk uses only exits before the valuation date

The exit risk is the chance that a player has no NHL season the following year, by quality and
age. It was estimated once from 2018-2024, so a 2018 valuation also drew on exits from 2019 to
2025. The window started in 2018 because older years lacked ages for the players most likely to
leave. With the age table corrected that reason no longer holds.

The exit risk is now estimated for each valuation season from 2007 up to the last exit known
before that season. On the same forecasts, the error in the predicted chance of playing fell
5.8%, and season forecast misses fell 0.3%. Both results held in each of 2,000 resamples of
players. The goaltender exit risk is unchanged; see Section 5.

## 3. Settings Tested and Kept

Several settings in the aging curve were chosen by hand. Each was changed one at a time and
scored on careers held out of the fit.

- The yardstick sample. The yardstick is the median distance between pairs of profiles, drawn
  from a random sample of 1,200 per position, and a player's two seasons can form a pair. Using
  all pairs, or removing a player's pairs with himself, changed forecast error by less than
  0.01%. Redrawing the random sample moves the yardstick more than either change.
- One yardstick for forwards and defence. Separate yardsticks (2.49 for forwards and 2.57 for
  defence, against 2.53 pooled) changed error by less than 0.01%.
- The measure weights. Style, ice time, level, and trend each carry equal weight. The square root
  in the calculation is only arithmetic: it gives the same result as weighting the squared
  difference. Across 65 different proportions of the four weights, equal weights ranked 28th to
  32nd, and no proportion moved error by more than 0.4%. The proportion that did best on the projected rate per 82
  games did worse on the projected season total. Eight proportions had slightly lower error on
  both, by at most 0.3%, but none by more than chance on each comparison.
- The weighting formula. Weighting each same-age player equally was worse on each of the four
  comparisons (0.5% to 0.9%), so similarity weighting earns its place. A narrower weighting (half
  the yardstick) was better on each (0.2% to 0.6%); this was not adopted, because it was one of
  many settings tried on the same data.
- The weight of ten on the league average. Any value from near zero to twenty gave the same error
  to within 0.06%. Giving the league average a fixed 5% share instead was no better.

## 4. How the Rebuilt Model Handles the Same Points

The rebuilt player model is a separate, experimental model built to answer the same question. The
choice between it and the current model has been deferred until the draft-pick and prospect
models are complete. It differs from the current model on each of the points above.

- No comparable players. Its aging curve is a smooth function of age, fitted on each player's
  change from one season to the next, so there is no pool, yardstick, measure weights, or league
  weight to set.
- Refit at each valuation date. The curve uses only season pairs that finished before the
  valuation date.
- Changes are added, not multiplied. The current model multiplies a player's recent total by a
  ratio from the curve. Near or below zero a ratio behaves badly, which is why it needs floors, a
  cap, and a flat fallback. The rebuilt model adds the yearly change in wins, so those guards are
  not needed.
- One starting point. In the current model, the pull of a player's recent level toward similar
  players (55% his own, 45% theirs) shapes the curve, but the projection is then applied to his
  unadjusted recent total. The rebuilt model starts the walk from its adjusted level and adds each
  year's change to it.
- The pull toward the league is estimated. How far a player's recent level is pulled toward the
  league average is fitted from the data instead of being set at 55%.

On the last matched comparison, made before the exit-risk change, the rebuilt model's season
forecast misses were 4.6% smaller than those of the corrected current model.

## 5. Effect on Values, and What Remains

Across the 2,981 contracts priced from their first season in 2018-2025:

- The aging change and the corrected age table moved 1,097 contracts, a net fall of $295.1M.
  All but two were skaters valued through the aging curve, and the other two changed projection
  path. The largest falls were long deals for stars, for example Logan Couture (2019) and Connor
  McDavid (2018).
- The exit-risk change moved 1,359 contracts, a net fall of $188.1M. Stars rose, because stars
  leave the league less often in the longer history, and older and weaker players fell.
- The tenth-percentile contract moved from -$7.80M to -$8.32M, and the median from +$0.29M to
  +$0.27M.

Two items remain.

- Goaltender exit risk. The same change cannot yet be made for goaltenders. Their ages come only
  from the contract export, which holds almost no player who retired before about 2018; the Elite
  Prospects file covers skaters only. Of 280 goaltenders, 109 were last seen before 2018, and they
  account for half of the goaltender seasons from 2007 to 2016 (336 of 660). Those are the
  goaltenders who left, so extending the window without their ages would undercount exits. This
  needs an Elite Prospects scrape of goaltender birthdates first.
- The two corrected Elite Prospects birthdates take effect when the age join is next run. They
  change five seasons, none long enough to enter the comparable pool.

## Sources

- Aging settings and look-ahead: `40_DOCS/model_evidence/Aging_Choices_Test.md`
- Exit risk: `40_DOCS/model_evidence/Exit_Hazard_Window_Test.md`
- Code: `20_CODE/aging_curve.py`, `20_CODE/skater_forward_projection.py`, `20_CODE/exit_hazard.py`,
  `20_CODE/contract_npv.py`, `20_CODE/age_join.py`
