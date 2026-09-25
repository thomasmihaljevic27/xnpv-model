"""run_model_scorecard.py -- the current player model against the rebuilt
candidates, on one set of pages, rows and currency, for the decision of which
to carry forward.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 and development start
years only; this run does not score the 2022-2025 pages. Those pages are NOT a
pristine holdout: about thirty variants were inspected on them before the
rebuild (plan decision D records it as prior selection). Scoring only: nothing
is fitted on realised seasons and nothing is adopted by this run.

THE THREE, DECLARED BEFORE THE RUN
    current    the production chain's own skater forecast, run through
               `production_adapter.ProductionChain`: production's locked aging
               path and exit-hazard survival, imported, not reimplemented; games
               share 1 (production has no separate availability forecast). It
               inherits production's documented look-ahead: its aging curve is
               fitted on the whole panel, including seasons after some pages.
    adopted    the rebuilt skater leader (`run_npv_simulation.LEADER`, visible
               contract status in participation, adopted provisionally
               2026-09-23)
    previous   the rebuilt leader before that (`PRIOR_LEADER`, no contract data)

WHAT IS SCORED
    1. season WAR on the harness (1 July of each development page, zero to five
       seasons ahead): squared error primary, absolute error and bias beside
       it, participation Brier, player-resampled shares against the current
       model as exact counts of 2,000; and the bias by trailing tier and
       horizon for each;
    2. contract dollars: every forecast's point valuation, the candidates'
       simulated means, and the realised production, priced on ONE line, the
       adopted candidate's (primary), with the current forecast's line as the
       sensitivity; the realised target is asserted identical across forecasts
       (`dollar_scoring`). The current model has no simulated distribution, so
       it is scored on its point valuation only.
    3. both of the above again on PRODUCTION'S ANSWERABLE SAMPLE. Where
       production has no anchor (no qualifying season in either of the two
       before the page), `ProductionChain.predict` falls back to the harness's
       trailing total carried flat and tags the row `outside_production`. Those
       rows are the adapter's extension, not production's forecast, so the full
       sample is "production plus its declared fallback" and the answerable
       sample drops them from ALL THREE arms (same rows for every model). For
       dollars the same test is run at each contract's signing page (t0 = the
       last season readable at signing + 1, as `forecast_blocks` batches). The
       dollar subset is a scoring sensitivity on the already-fitted lines; no
       price line is refitted without the fallback contracts.
    This prices the current model's FORECAST on the rebuild's currency. It is
    not a score of production's own full chain in its own currency: each
    chain's currency gives a different realised target, and scores against
    different targets are not comparable. The full-chain difference is the
    reconciliation (`run_production_reconciliation.py`), reported beside.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import run_npv_simulation as RNS
import run_skater_contract_test as RSC
import run_skater_dollar_scoring as SDS
from contract_price_model import contract_sample
from player_season_table import build as build_table, birthdate_source
from production_adapter import ProductionChain
from dollar_scoring import realised_path, score_on_line, report_scores

SCRIPT_VERSION = "1.1"
KEY = "contract_id"
MODELS = (("current", ProductionChain, False),
          ("adopted", RNS.LEADER, True),
          ("previous", RNS.PRIOR_LEADER, True))
TIERS = ["below 0", "0 to 1", "1 to 2", "2 to 3", "3+"]


def tier_table(runs: dict) -> None:
    C.log("  season WAR bias over every forecast, by trailing tier (rows) and seasons")
    C.log("  ahead (columns), for each model:")
    for k, d in runs.items():
        C.log(f"    {k}")
        C.log(f"      {'tier':<10}" + "".join(f"{'h' + str(h):>9}" for h in RSC.HORIZONS))
        for t in TIERS:
            line = f"      {t:<10}"
            for h in RSC.HORIZONS:
                m = (d["tier"] == t) & (d["h"] == h)
                line += f"{d.loc[m, 'e_war'].mean():>+9.3f}"
            C.log(line)
    C.log("")
    C.log("  season WAR RMSE by seasons ahead:")
    C.log(f"    {'model':<10}" + "".join(f"{'h' + str(h):>9}" for h in RSC.HORIZONS))
    for k, d in runs.items():
        C.log(f"    {k:<10}" + "".join(
            f"{np.sqrt((d.loc[d['h'] == h, 'e_war'] ** 2).mean()):>9.4f}" for h in RSC.HORIZONS))
    C.log("")


def production_unanswerable(sample: pd.DataFrame, ids) -> set:
    """Contracts whose signing page production cannot anchor, by production's
    own anchor rule (`ProductionChain._anchor`, which calls production's code).
    The page is the one the valuation read: the last season readable at the
    signing plus one. The anchor lookup does not depend on the fit year."""
    prod = ProductionChain()
    prod.fit(pd.DataFrame(), before=max(C.DEV_PAGES))
    s = sample.set_index(KEY).loc[list(ids)]
    return {int(cid) for cid, r in s.iterrows()
            if pd.isna(prod._anchor(f"{r.pkey}", int(r.latest_complete) + 1)[0])}


def main() -> None:
    C.banner("run_model_scorecard.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    C.log("")

    # ---- 1. season forecasts ----------------------------------------------
    har = H.Harness(table)
    runs = {}
    for k, cls, _ in MODELS:
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=RSC.HORIZONS)
        C.log(f"  ran {k}: {len(runs[k])} forecasts")
    C.log("")
    C.log("1. SEASON FORECASTS ON THE HARNESS")
    RSC.season_scores(runs, ref="current",
                      pairs=(("current", "adopted"), ("current", "previous"),
                             ("previous", "adopted")))
    tier_table(runs)

    # ---- 1b. production's answerable sample --------------------------------
    # The fallback rows are production's missing answers, filled by the adapter.
    # Dropped from every arm on the same keys, so the three score one row set.
    keys = ["career_key", "page", "h"]
    ans = runs["current"].loc[runs["current"]["outside_production"] == 0, keys]
    sub = {k: d.merge(ans, on=keys, how="inner", validate="one_to_one")
           for k, d in runs.items()}
    n_fb = len(runs["current"]) - len(ans)
    assert all(len(d) == len(ans) for d in sub.values())
    C.log(f"1b. PRODUCTION'S ANSWERABLE SAMPLE: {len(ans)} of {len(runs['current'])} forecasts;")
    C.log(f"    {n_fb} rows where production has no anchor and the adapter carried the")
    C.log("    harness's trailing total flat are dropped from all three models.")
    RSC.season_scores(sub, ref="current",
                      pairs=(("current", "adopted"), ("current", "previous"),
                             ("previous", "adopted")))
    tier_table(sub)

    # ---- 2. contract dollars on one line -----------------------------------
    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_model_scorecard")
    priced, results, draws = {}, {}, {}
    for label, cls, sim in MODELS:
        pt, lines, ok, keep = SDS.price_and_simulate(label, cls, sample, table, cohorts,
                                                     simulate=sim)
        priced[label] = (pt, lines)
        results[label] = ok if ok is not None else pt[[KEY, "end_yr"]]
        draws.update({label: keep} if sim else {})
    common = sorted(set.intersection(*[
        set(r.loc[r["end_yr"] <= C.LAST_SOURCE_SEASON, KEY]) for r in results.values()]))
    rows_of = {lab: priced[lab][0].set_index(KEY) for lab in priced}
    labels = tuple(l for l, _, _ in MODELS)
    real = realised_path(table)
    C.log("2. CONTRACT DOLLARS IN ONE CURRENCY. Ended terms priced by all three.")
    C.log("Every valuation and the realised path on the same line; realised target")
    C.log("asserted identical; squared error primary; $M; shares are counts of 2,000")
    C.log("player-resamples in which the later model's error is lower than the")
    C.log("current model's. The current model is scored on its point valuation only.")
    C.log("")
    fallback = production_unanswerable(sample, common)
    C.log(f"  {len(fallback)} of {len(common)} contracts have no production anchor on")
    C.log("  their signing page (the current model's value there is the adapter's")
    C.log("  fallback); each line is scored on all, then without them.")
    C.log("")
    for line_label in ("adopted", "current"):
        d = score_on_line(common, rows_of, priced[line_label][1], draws, labels, real)
        d["production_answerable"] = ~d[KEY].isin(fallback)
        tag = "PRIMARY" if line_label == "adopted" else "sensitivity"
        C.log(f"  on the {line_label} model's line ({tag}), {len(d)} contracts, "
              f"{d['pkey'].nunique()} players:")
        report_scores(d, labels, exact=True)
        C.log("")
        a = d[d["production_answerable"]].copy()
        C.log(f"  same line, production's answerable contracts only ({len(a)} contracts,")
        C.log(f"  {a['pkey'].nunique()} players; line as fitted, not refitted):")
        report_scores(a, labels, exact=True)
        C.log("")
        if line_label == "adopted":
            d.drop(columns=[c for c in d.columns if c.startswith("draws_")]).to_csv(
                C.out_path("model_scorecard_dollars.csv"), index=False)
    out = pd.concat([d.assign(model=k) for k, d in runs.items()], ignore_index=True)
    out.to_csv(C.out_path("model_scorecard_seasons.csv"), index=False)
    C.write_log("model_scorecard_run_log.txt")


if __name__ == "__main__":
    main()
