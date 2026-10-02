# Model 3 with contract status in its chance of playing

Run 2026-09-30 on Thomas's laptop (`50_REBUILD/code/run_contract_status_test.py` v1.0, Python 3.14.3,
contract export read: 6,851 rows). Test only: nothing adopted. Figures are copied from
`50_REBUILD/output/contract_status_run_log.txt` (gitignored).

## The models

| Model | What it is |
|---|---|
| Model 1 | the current model as it runs |
| Model 3 | the current model with every listed fix, comparable-player aging, and the games-share forecast reading the player's level (the base) |
| **Model 6** | **Model 3 with one change: its chance of playing reads contract status (the adopted rebuilt model's settings)** |
| Model 4 | the adopted rebuilt model (reads contract status) |
| Model 7 | Model 4 with the games-share change |

Model 6 against Model 7 differs only in the aging method (comparables against the fitted equation):
both read contracts and both carry the games-share change.

The guards passed:
- Models 6, 4 and 7 each read the export;
- Model 6 moved only the chance of playing against Model 3, and Model 7 only the games share against
  Model 4;
- in dollars, Models 1, 3 and 4 reproduce the 2026-09-30 re-score.

**Which age table.** On the laptop the harness reads the merged birthdate file (PuckPedia first, then
Elite Prospects; 4,343 players). The cloud runs read production's age join (3,204 players), because
the merged file needs the export. So this run's season figures differ from the cloud reports for
every model; Model 3 is 0.8617 here against 0.8584 there. The largest difference is Model 1's Brier:
0.249 here against 0.192 in the cloud. That is unexplained and left open. Comparisons within a run
share one table and are like for like.

## Season forecasts (rows the current model answers, 35,878 forecasts)

"Lower in" counts player resamples, of 2,000, with lower squared error than Model 3.

| Model | RMSE | Lower in | MAE | Brier | 3+ bias, seasons 1-5 [95%] |
|---|---:|---:|---:|---:|---|
| Model 1 | 0.9302 | 0 | 0.5763 | 0.2494 | +0.62 [+0.30, +0.97] |
| Model 3 | 0.8617 | | 0.5201 | 0.1370 | -0.26 [-0.57, +0.08] |
| **Model 6** | **0.8614** | **1,925** | 0.5200 | 0.1358 | -0.26 [-0.56, +0.08] |
| Model 4 | 0.8640 | 522 | 0.5082 | 0.1358 | -0.64 [-0.95, -0.30] |
| Model 7 | 0.8596 | 1,657 | 0.5068 | 0.1358 | -0.52 [-0.83, -0.20] |

- **By the declared rule (1,950 of 2,000), Model 6 does not improve Model 3.** It is lower in 1,925,
  and its Brier is lower (Model 3's is lower in 0 of 2,000).
- **The late chance of playing for good players does not move.** Three to five seasons out, 3+ win
  players aged 29-31 are given 0.85 by both Models 3 and 6 and played 0.98. The 2-3 tier aged 25-28
  goes from 0.88 to 0.89 (observed 0.96).
- **Model 6 against Model 7 (aging method only):**
  - Model 7 is lower in squared error in 1,563 of 2,000 (Model 6 in 437), not decisive.
  - Model 7 is clearly lower on absolute error (0.5068 against 0.5200).
  - Model 6's star bias is half Model 7's (-0.26 against -0.52).

## Contract dollars

Adopted model's line, the 1,111 contracts the current model answers, point valuations, $M:

| Model | RMSE | MAE | Bias |
|---|---:|---:|---:|
| Model 1 | 3.681 | 1.865 | -0.179 |
| Model 3 | 3.555 | 1.753 | -0.571 |
| **Model 6** | **3.543** | 1.752 | **-0.528** |
| Model 4 | 3.614 | 1.761 | -0.581 |
| Model 7 | 3.552 | 1.751 | -0.539 |

- **Model 6 against Model 3:** squared error lower in 1,974 of 2,000 on this table. It is 1,975 on all
  contracts, and 1,935 and 1,931 on the current model's line. Absolute error is level (lower in 1,268,
  991, 463 and 730).
- **Model 6 against Model 7:** squared error lower in 1,316 (1,335, 1,402 and 1,407 on the other
  tables). Model 7 has the lower absolute error in all four tables (Model 6 lower in 863-920).
- **Six-to-eight-year deals (41):** Model 6 is at 10.75 (bias -5.72) against Model 1's 10.62
  (-4.09). The long-deal gap to the current model is unchanged.

## Reading

- **Contract status is a small, consistent gain for Model 3, not a fix for stars.** It sharpens the
  chance of playing and lowers dollar squared error in about 1,930-1,975 of 2,000 resamples. On season
  WAR it falls just short of the declared bar. The good players' late chance-of-playing miss, the
  reason for the test, is untouched. The status the model can see at 1 July of the page covers the
  seasons already signed; it says nothing about whether a star re-signs three years later. In dollars
  the model reads status at the signing, which covers the contract's own term.
- **Comparables against the fitted equation still does not separate.**
  - Season squared error leans to the equation (1,563 of 2,000) and absolute error clearly does.
  - Dollar squared error leans to comparables (1,316-1,407).
  - The star bias is half as large with comparables.
- **Where the models stand:**
  - with contract status, comparables, the fitted start and the games-share forecast (Model 6), the
    model is within 0.2% of the best season squared error (Model 7, 0.8596 against 0.8614) and has
    the lowest dollar squared error of the five;
  - its remaining weaknesses are the late star miss (-0.26 over seasons 1-5, -0.40 five out) and long
    deals.

## Open

- Why Model 1's season figures differ this much between the two age tables.
- The late chance of playing for good players: neither age terms, a level hinge nor contract status
  moves it.
