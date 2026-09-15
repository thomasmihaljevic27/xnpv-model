# Verification of Claude's rebuild repairs

Reviewed 2026-09-15. Candidate: `d651998`, branch `claude/loving-maxwell-rd3w5v`.
Source report: `50_REBUILD/docs/Review_Repair_Report.md` on that branch.
The candidate was tested in an isolated checkout; its implementation was not merged or edited.

## Assessment

Several original defects are repaired, and the repair checks execute successfully. The new
13-17% improvement against the live chain is still unverified because the production adapter
does not reproduce production. Market normalization, discount timing, and the extrapolation
interface also require repair. These affect requirements the report describes as addressed,
separate from the simulation and stress-test work it leaves open.

No corrected model-performance or contract-NPV figure was estimated in this verification.

## What passes

I ran repair checks 1-11 with the merged PuckPedia and Elite Prospects birthdates. All passed.
Check 12 initially skipped because a required production environment variable was absent.
After supplying the actual production input paths, I ran that check successfully too.
All twelve checks were therefore executed successfully across two invocations, with 98.3% age
coverage and the existing production `WAR_with_age.csv` available.

The executed checks support the raw-rate/D20 correction, consistent games units, the one-game
participation event, the prediction-grid guard, admission of the 120 third-year-history
subjects on the 2021 page, and signing-date filtering of market records. Longer horizons are
now fitted or explicitly extrapolated rather than silently receiving the old universal 0.6.
The holdout inventory documents the already-inspected market cohorts.

The extrapolation check reproduces its reported deviation from fitted-model forecasts:
+3.0%, +10.0%, and +19.8% on average at horizons 6-8, with +32.4% on the worst tested page at
horizon 8. These compare extrapolations with longer fitted forecasts, not realized outcomes.

## Findings requiring repair

### 1. P1: the adapter omits production's negative-anchor rule

`production_adapter.py:193,205` computes projected WAR as `anchor * ratio` for each season.
Production instead calls `SkaterProjector.multiplier()` in
`20_CODE/skater_forward_projection.py:648-664,717-720`. For a negative anchor, that method
returns one in the valuation season and zero in each later season. This is the locked
replacement-reversion rule.

Executed on the 2021 page: **266 subjects with negative anchors under production's own anchor
method receive nonzero horizon-one WAR from the adapter**, where production requires zero.
The adapter's hazard calculation also reads its incorrect preceding projected level, so the
discrepancy can reach survival as well as production.

The report specifically attributes gains to below-replacement players. That comparison must
be rerun after the adapter applies production's rule. A curve import alone does not reproduce
the complete projection.

### 2. P1: the adapter uses different trailing seasons from production

`production_adapter.py:143-156` selects the last two qualifying observations anywhere before
the valuation date. Production's `SkaterProjector.anchor()` reads exactly `t0-1` and `t0-2`,
renormalizes if only one exists, and returns missing if neither exists.

Executed on the 2021 page using the same lookup for both methods:

- **142 anchors differ where production has a defined answer.**
- The largest absolute difference is **1.0220 WAR**.
- **120 subjects have no production anchor**, but the adapter supplies older history.

A fallback for subjects production cannot answer may be useful for common-sample evaluation,
but it must be identified as an extension to production and reported separately.

Check 12 misses both adapter errors because it asserts only that rates change with horizon
and survival falls below 0.95. It never compares the adapter against production's own output
or its anchor and multiplier methods. Required: direct parity checks covering positive and
negative anchors, missing seasons, curve fallbacks, and survival transitions.

### 3. P1: signing-date filtering still admits future cap information through the target

`contract_price_model.py:66-70` continues to define cap share and its floor using the
**realized contract-start salary cap**, while `ProductionCurrency.fit()` now admits records
according to their signing date. An early-signed extension can enter training before its
start-year denominator is available.

Executed sample audit: a **2019-01-01 training cutoff admits 20 eligible records with 2019 or
later start years**. Their targets use ceilings not yet available under the candidate's own
announcement policy. This is before forecast attachment and final pricing eligibility, not
a count of confirmed final fitted rows.

The date guard checks signing timestamps only. Required: choose and document a cap-share
denominator available at the signing, apply it consistently to the target and floor, and
ensure historical price fits cannot change when future cap observations are perturbed.
Any resulting change to the currency's units must carry through its application.

### 4. P1: discounting starts at the contract start, not the stated valuation date

`production_currency.py:125,140` discounts by position within the contract schedule:
the first season always has exponent zero. The signing date selects the cap path but does not
set the discount origin. The waiting period between signing and an extension's start is omitted.

Executed example: a one-year, $1M contract starting in 2019 has a reported present cost of
**$1M whether signed on 2017-07-01 or 2018-07-01**. On the annual page convention, those
costs require two and one periods of discounting respectively. The current output is dated
at the contract start even though market and cap information are dated at signing.

Value and cost share this omission, which keeps them internally aligned but does not produce
signing-date NPV. The cap-growth cancellation test cannot detect a common missing delay.
Required: an explicit valuation origin and consistent season offsets on both sides.

### 5. P2: extrapolated forecasts depend on the other requested horizons and players

`ability_forecast.py:122-153` estimates tail decay from the last two **requested** fitted
horizons and mean forecasts of the **requested** subjects. It treats their ratio as a
one-year change even when the two horizons are not consecutive.

Executed with the 2021 hinge-and-evidence model, restricted to fitted horizons 0-5 to exercise
the tail path:

- Requesting `[4,5,6]` versus `[3,5,6]` changes the same horizon-six prediction by as much as
  **0.5156 WAR**; the mean absolute change is **0.02957 WAR**.
- Requesting one player alone versus in the full population changes that player's forecast
  too. The demonstrated difference is 0.00104 WAR; the interface failure exists regardless
  of that example's size.

The fitted model and decision date are identical. Required: derive extrapolation from fixed
adjacent fitted horizons and a defined reference population, independent of the query.
Test invariance to horizon subsets, subject subsets, and row order.

Also, `attach_forecasts()` drops the `extrapolated` tag when constructing its WAR lookup
(`contract_price_model.py:117-127`). The resulting contract table cannot report which seasons
or dollars came from extrapolation. Carry the tag and extrapolated-year count into outputs.

### 6. P2: repaired entry points remain unusable for some advertised tasks

- `run_player_comparison.py:155-163` checks the old global six-horizon constant before fitting
  the page's model. It refuses a seven-year term even when that page supports one, and never
  calls the explicit extrapolation path. The first seven-year case triggers it.
- `run_phase4_decisions.py:55` and the curvature runner request cohorts 2018-2025 directly
  from a guard that rejects 2022-2025. Blocking reserved cohorts is correct; the entry points
  still need a runnable development-cohort selection.
- `attach_forecasts()` retains the horizon-eight limit and filters nonfinite/missing years
  instead of asserting full-term coverage. No current eligible contract exceeded that horizon
  in my raw-sample check, so the ceiling is a latent coverage defect rather than demonstrated
  current-sample truncation.

The named-player executable also retains its full-sample log currency and realized-cap
summation. It should remain withdrawn until routed through the repaired valuation API.

## Still open by the report's own account

The full-chain leakage test still compares rates only; subgroup results pool horizons;
predictive intervals are absent; and the export-break test compares outcome eras rather
than perturbed inputs. Joint simulation, the trade-date update, control-year integration,
goalies, the announced later cap ceilings, and full dollar reconciliation remain incomplete.
These are acknowledged limitations, not newly discovered regressions.

The inspection ledger is useful, but the guards do not enforce once-only use by consulting it.
The market guard also accepts an empty reason with an explicit unseal. Documenting past
inspection is distinct from enforcing future confirmatory use.

## Reproduction and scope

Independent script: `50_REBUILD/code/review_repair_followup.py`. Run it with `--candidate-root`
pointing to a checkout of `d651998`; prepare that checkout's merged
`50_REBUILD/output/birthdates.csv` with its existing `contract_source.birthdate_table()`.
The script reads this repository's vendor files and production age output. Aggregate evidence
is saved in `50_REBUILD/output/review_repair_followup.json` and remains ignored.

I did not rerun the full development leaderboard, choose new models, score reserved forecast
pages, or calculate corrected contract NPVs. The direct method comparisons reject claimed
production parity; they do not establish the eventual corrected improvement. No production
or candidate implementation changed. The branch has not been merged into main.
