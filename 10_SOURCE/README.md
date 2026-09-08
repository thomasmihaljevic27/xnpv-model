# Source data

Code reads this directory and never writes to it. Model output goes to `30_OUTPUT/`.

## Committed to the repo

Four datasets are included so the model chain runs end to end without a separate data request.

| File | Rows | Coverage | Origin |
|---|---|---|---|
| `WAR.csv` | 17,123 | 2007-08 to 2025-26 | Skater wins above replacement, component-decomposed, from the TopDownHockey / hockeystats.com public WAR model. Regressions use 2015 onward; the pre-2015 vintage is excluded. |
| `Goalies_WAR.csv` | 1,639 | 2007-08 to 2025-26 | Goaltender WAR from the same model. |
| `nhle_temporal.csv` | 2,196 | 2006-07 to 2025-26 | Era-varying NHL equivalency factors across 142 leagues. The 2004-05 lockout year is absent by design. |
| `draft_slot_baseline.csv` | 225 | Per draft slot | NHLer and star probabilities by pick number, monotone decreasing. |

These are third-party datasets, redistributed here for research reproducibility with
attribution to their original authors. They are not my work and I claim no rights over them.
If you are the rights holder and want them removed, open an issue and I will take them down.

**Single-provider discipline applies.** All player-value inputs come from one provider on
purpose. Blending a second source would make the surplus-dollar scale incoherent across
pillars. MoneyPuck has been used exactly once, as an external validation benchmark, never as
a model input.

## Not committed, and why

**PuckPedia player-contract and trades exports.** Confidential vendor data. Not
redistributable under any circumstances. The trades export covers 980 trades from 2018 to
2026, one row per asset per trade, and is the cost backbone the whole model joins against.
Without it the pipeline will not run.

**NHL game-log database and event CSVs.** `nhl_gamelogs.sqlite` is 2.3 GB, well past what
belongs in git, and the shift and shot event CSVs add roughly another 700 MB. All of it
rebuilds from the public NHL API using `20_CODE/nhl_gamelog_scraper.py` (v2.4, 11,870 games
covering 2017-18 through 2025-26, including 582 games recovered through an HTML shift-report
fallback).

**Clause and age scrapes.** `capspace_clauses.csv` and `.db` (15,261 contract-season rows,
no-trade and no-movement clauses from cap-space.com), `trades.db`, `ep_ages.db`, and the
`html_cache/` and `capwages_cache/` directories. All rebuildable from the scrapers in
`20_CODE/`.
