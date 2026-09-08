"""
=============================================================================
 contract_npv_panel.py   v1.0                    Validation exhibit (2026-07-05)
=============================================================================
 WHAT THIS PRODUCES (plain English)
 ----------------------------------
 A year-by-year league panel of contract NPVs. For every league-year t0
 from 2018 through 2025, it values EVERY contract active that season -- as
 of that season, using only trailing information available then. One
 contract that runs 2021-2026 therefore appears on the 2021, 2022, 2023,
 2024, and 2025 pages, RE-ANCHORED each year as its trailing window rolls
 forward. That re-anchoring is the entire point: it is how the model's
 opinion of a player updates as his production actually arrives.

   Output: contract_npv_panel.csv -- one row per (contract, valuation year).

 WHY THIS EXISTS -- AND WHAT IT IS NOT (the firewall, read this)
 --------------------------------------------------------------
 This is a VALIDATION / MONITORING exhibit, NOT a back-test input. Two
 distinct objects, and they must never cross:

   * The BACK-TEST spine (contract_npv_spine.csv) values each contract
     ONCE, at the information set its GMs actually had. A trade is scored
     on THAT valuation and no other.
   * THIS PANEL re-values the same contract every year. Its purpose is to
     SHOW CONVERGENCE: young-star extensions that price as "overpays" at
     signing (because trailing WAR could not yet see the breakout) climb
     toward positive surplus on later pages as the breakout enters the
     trailing window. That trajectory is evidence the framework is not
     permanently broken on stars -- it is not, and must never become, the
     number a historical trade is graded against.

 Grading a 2021 trade on this panel's 2024 page would be scoring a past
 decision with information that arrived after it -- the exact look-ahead
 violation the whole project is built to avoid. The panel is safe ONLY as
 a diagnostic. This header, the CSV's own `artifact_role` column, and the
 run-log banner all say so, so no future session mistakes it for scoring
 material.

 WHY IT IS LOOK-AHEAD-CLEAN PAGE BY PAGE
 ---------------------------------------
 Each page reuses the SAME engine as the back-test (contract_npv.py's
 NPVEngine.npv), which for any t0:
   * anchors on trailing seasons t0-1 / t0-2 only (never t0 or later),
   * walks the aging curve based at age-1 (D21), never the t0 season,
   * uses the ex-ante cap path (D11), never realized future ceilings.
 So every individual page is itself a valid ex-ante valuation. What makes
 the panel a diagnostic rather than a scoring table is only that it
 repeats the valuation across years -- each page is clean; the CROSS-YEAR
 comparison is the thing you must not feed into a trade score.

 D20/D21 INHERITED AUTOMATICALLY
 -------------------------------
 This script builds NOTHING of its own valuation logic -- it imports the
 engine and loops. Schedule proration (D20), the refit rates, and the
 curve-routing fix (D21) all flow through unchanged. If the engine passes
 its guards, so does every page here.

 USAGE (Windows):  python contract_npv_panel.py
 Requires the same inputs as contract_npv.py, plus goalie_value_spine_v2.csv.
 Run contract_npv.py at least once first (nothing hard-depends on its
 output, but you want the engine's guards to have passed on this machine).
=============================================================================
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

# The engine is the single source of valuation truth. Importing it (rather
# than re-implementing) guarantees the panel can never silently drift from
# the back-test's pricing -- same rates, same curve, same survival, same
# D20/D21 fixes.
from contract_npv import NPVEngine, DATA_DIR

OUT_PANEL = DATA_DIR / "contract_npv_panel.csv"
OUT_LOG   = DATA_DIR / "contract_npv_panel_run_log.txt"

PANEL_FIRST, PANEL_LAST = 2018, 2025      # league-years to lay out as pages

LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))


def build_panel():
    log("=" * 74)
    log("CONTRACT NPV PANEL  --  VALIDATION EXHIBIT, NOT A BACK-TEST INPUT")
    log("=" * 74)
    log("Each contract is valued from EVERY league-year it is active, re-")
    log("anchored on that year's trailing window. Convergence diagnostic only:")
    log("a historical trade is scored on its OWN year's page and no other.")
    log("")

    eng = NPVEngine()

    # The universe of (contract, active-season) pairs. We drive the panel
    # off the SAME two spines the engine already loaded, so a contract is
    # "active in year t0" exactly when it has a spine row with
    # season_start == t0. We value from t0; the engine then walks only the
    # REMAINING seasons (season_start >= t0) internally.
    spine_all = pd.concat([eng.sp.spine, eng.gp_spine], ignore_index=True)
    active = spine_all[spine_all["season_start"].between(PANEL_FIRST, PANEL_LAST)]
    # one job per (contract, season): dedupe in case a spine carries
    # duplicate season rows for a contract
    # is_elc_season (Thomas 2026-07-05): keep EVERY active league-year as a
    # page -- ELC years included, because a cheap rookie-deal season is a
    # real surplus and belongs in the dashboard -- but tag whether the
    # valuation season (t0) is itself an entry-level season, so ELC-inflated
    # rows can be filtered out of any leaderboard at will. cs_entry_level is
    # a season-level boolean already on both spines.
    keep = ["contract_id", "player_id", "season_start", "cs_entry_level"]
    jobs = active.drop_duplicates(["contract_id", "season_start"])[keep]
    log(f"panel jobs (contract x active league-year): {len(jobs):,}")

    rows, skipped = [], {}
    for j in jobs.itertuples(index=False):
        d, s = eng.npv(int(j.player_id), int(j.season_start))
        if s.get("status") != "ok":
            skipped[s.get("status", "unknown")] = \
                skipped.get(s.get("status", "unknown"), 0) + 1
            continue
        # remaining contract length AS SEEN from this page (k=0..end)
        n_remaining = int(s["n_contract_seasons"])
        rows.append({
            "artifact_role": "VALIDATION_PANEL_not_backtest_input",
            "contract_id": int(j.contract_id),
            "player_id": int(j.player_id),
            "full_name": s["full_name"],
            "position": s["position"],
            "valuation_season": int(j.season_start),
            "is_elc_season": bool(j.cs_entry_level) if pd.notna(j.cs_entry_level) else False,
            "seasons_remaining": n_remaining,
            "path": s.get("path", ""),
            "npv_contract": s["npv_contract"],
            "npv_terminal": s["npv_terminal"],
            "npv_total": s["npv_total"],
            "surplus_no_survival": s["surplus_no_survival"],
        })
    panel = pd.DataFrame(rows).sort_values(
        ["valuation_season", "npv_total"], ascending=[True, False])
    panel.to_csv(OUT_PANEL, index=False)

    log(f"panel rows written: {len(panel):,}   "
        f"(skipped: {sum(skipped.values()):,} -> {skipped})")
    log(f"output: {OUT_PANEL.name}")
    return eng, panel


def validate(panel):
    """A few sanity views + the convergence exhibit the panel exists for."""
    log("\n" + "=" * 74)
    log("PANEL VALIDATION VIEWS")
    log("=" * 74)

    # ---- 1. coverage per page ----------------------------------------------
    log("\n[1] contracts priced per league-year (page size):")
    for t0, g in panel.groupby("valuation_season"):
        med = g["npv_total"].median() / 1e6
        log(f"    {t0}: {len(g):5,d} contracts   median NPV ${med:+.2f}M")

    # ---- 2. THE convergence exhibit ----------------------------------------
    # For the marquee young-star extensions that read as overpays at
    # signing, trace NPV across the pages. The number should climb as the
    # breakout enters the trailing window. This is the slide.
    log("\n[2] convergence exhibit -- young-star extensions, NPV by page:")
    log("    (negative early = trailing WAR can't see the breakout yet;")
    log("     climbing later = production has arrived in the trailing window)")
    marquee = ["Cale Makar", "Quinn Hughes", "Jack Hughes", "Luke Hughes",
               "Auston Matthews", "Elias Pettersson"]
    for name in marquee:
        g = panel[panel["full_name"] == name].sort_values("valuation_season")
        if g.empty:
            continue
        traj = "  ".join(f"{int(r.valuation_season)}:${r.npv_total/1e6:+.0f}M"
                         for r in g.itertuples())
        log(f"    {name:20s} {traj}")

    # ---- 3. a single page, top and bottom, as a readable dashboard ---------
    log("\n[3] sample page -- 2024, top 8 and bottom 5 by NPV (ELC seasons")
    log("    excluded from this leaderboard view; they remain in the CSV):")
    p24 = panel[(panel["valuation_season"] == 2024)
                & (~panel["is_elc_season"])]
    elc24 = int((panel["valuation_season"] == 2024).sum() - len(p24))
    log(f"    (2024 page: {len(p24)} veteran-deal rows shown, {elc24} ELC rows hidden)")
    for _, r in p24.head(8).iterrows():
        log(f"    +  {r['full_name']:22s} ${r['npv_total']/1e6:+6.1f}M  "
            f"({int(r['seasons_remaining'])}yr left)")
    log("    ...")
    for _, r in p24.tail(5).iterrows():
        log(f"    -  {r['full_name']:22s} ${r['npv_total']/1e6:+6.1f}M  "
            f"({int(r['seasons_remaining'])}yr left)")

    # ---- 4. firewall restated in the log -----------------------------------
    log("\n[4] FIREWALL: this file is a diagnostic. Do NOT join it to trades")
    log("    to score mispricing -- use contract_npv_spine.csv (each trade at")
    log("    its own date). Every row here is tagged artifact_role =")
    log("    'VALIDATION_PANEL_not_backtest_input' so the boundary travels")
    log("    with the data.")

    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")


if __name__ == "__main__":
    _eng, _panel = build_panel()
    validate(_panel)
