"""
gv_4b_circularity_check.py -- Phase 4b: circularity validation
================================================================

WHAT THIS TESTS (plain English):
  The model's dollars-per-win rate comes from regressing real contracts
  against Bacon's WAR numbers. That's fine for pricing, but it means we
  can't use Bacon's OWN metric to prove the rate is "correct" -- that
  would just be checking Bacon against Bacon. This script checks the
  model's trailing-season projection (the same quantity that gets priced
  into every contract's Value_t) against GV-adj: a metric built entirely
  from raw NHL play-by-play data, with ZERO Bacon inputs anywhere in its
  construction. If the two agree, that's real evidence the market-rate
  approach is measuring something real, not an artifact of one vendor's
  model. If they diverge, that's a genuine validity finding to report,
  not a bug to fix.

WHAT "trailing_war" MEANS HERE:
  For a player's season t, trailing_war is a weighted average of his
  WAR in seasons t-1 and t-2 -- i.e., only information a GM would have
  had BEFORE season t started. This is exactly the number the model
  turns into a dollar price for that season. So comparing trailing_war(t)
  to what actually happened in season t is a fair, honest, ex-ante test:
  nothing here can leak information from the future into the projection.

INPUTS:
  1. skater_value_spine.csv   (Bacon side -- already in the project)
  2. Local SQLite database, table `gv_adjusted`  (the non-Bacon side)
     Confirmed table: player_id, season (e.g. 20172018), gv_adj (goals)

OUTPUT:
  A single console report + a CSV of the merged, row-level comparison
  data (so you can eyeball individual players / seasons and give this
  to Karl directly if he wants to inspect it).

HOW TO RUN:
  python gv_4b_circularity_check.py
"""

import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

try:
    from scipy import stats as scipy_stats
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False
    print("NOTE: scipy not found -- Spearman rank correlation will be "
          "skipped (Pearson + OLS still run). `pip install scipy` for "
          "the full report.")

# ---------------------------------------------------------------------------
# PATHS -- all from .env (see .env.example). GAMELOG_DB is the game-log store;
# skater_value_spine.csv is a generated deliverable; the gv_4b_outputs folder
# is a generated subtree.
# ---------------------------------------------------------------------------
DB_PATH = Path(os.environ["GAMELOG_DB"])
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SPINE_PATH = OUTPUT_DIR / "skater_value_spine.csv"
OUT_DIR = OUTPUT_DIR / "gv_4b_outputs"

# ---------------------------------------------------------------------------
# LOCKED CONSTANTS -- do not tune these to improve the result. They come
# from prior, separately-validated work. Changing them here to make this
# test "pass" would BE the circularity problem this script exists to rule
# out.
# ---------------------------------------------------------------------------
GOALS_PER_WIN = 5.903          # locked pooled rate, Phase 4a-i / rebase session


def fail(msg: str) -> None:
    print("\n" + "!" * 70)
    print("STOPPED: " + msg)
    print("!" * 70)
    sys.exit(1)


def load_bacon_side() -> pd.DataFrame:
    """
    Load the model's own trailing-season projections.
    This is the ONLY quantity from the model side we use -- it is exactly
    what gets priced into Value_t for each contract-season, so testing it
    directly (rather than re-deriving a projection) keeps this script
    honest about what it's actually validating.
    """
    if not SPINE_PATH.exists():
        fail(f"Can't find {SPINE_PATH.resolve()}. Run this script from the "
             "folder containing skater_value_spine.csv, or edit SPINE_PATH.")

    df = pd.read_csv(SPINE_PATH)

    required = {"player_id", "nhl_id", "season_start", "trailing_war",
                "merged_name_excluded", "position", "market_label"}
    missing = required - set(df.columns)
    if missing:
        fail(f"skater_value_spine.csv is missing expected columns: {missing}. "
             "This script was built against the current schema -- if the "
             "spine has changed, the column list above needs updating.")

    n0 = len(df)

    # Drop the known same-name collision rows (Ryan Johnson / Nathan Smith,
    # two different real players merged under one name in WAR.csv). Keeping
    # these in would silently mix two players' careers into one WAR figure.
    df = df[df["merged_name_excluded"] != True]  # noqa: E712 (explicit bool compare on purpose)
    n1 = len(df)
    print(f"  Dropped {n0 - n1} merged-name-collision rows "
          f"(Ryan Johnson / Nathan Smith).")

    # We need an actual projection to test -- drop rows with no trailing WAR
    # (players with no observed prior seasons at that valuation point).
    df = df.dropna(subset=["trailing_war"])
    n2 = len(df)
    print(f"  Dropped {n1 - n2} rows with no trailing_war (no prior "
          f"seasons observed -- nothing to project from).")

    # ---- Retention-driven duplicate handling --------------------------------
    # Some player-seasons appear TWICE in the spine. Every such case is the
    # same player, same season, split across TWO contract rows because of a
    # mid-season trade WITH SALARY RETENTION: the cap hit is divided between
    # the two teams, so the spine (correctly) carries one row per contract-
    # team leg. The COST differs across legs, but the projected production
    # (trailing_war) is a player-level quantity and is IDENTICAL on both.
    #
    # Phase 4b Tier 1 compares trailing_war(t) to GV-adj(t) -- both
    # player-level. The cost split is irrelevant to this test, so we collapse
    # to one row per player-season. Nothing the test uses is lost, because
    # the legs agree on trailing_war (asserted below).
    dupe_ct = df.duplicated(subset=["player_id", "season_start"]).sum()
    if dupe_ct:
        # GUARD: the collapse is only safe if the projection genuinely agrees
        # across legs. If a future spine version ever produced two DIFFERENT
        # trailing_war values for one player-season, silently keeping one
        # would hide a real problem -- so we stop loudly instead.
        war_spread = (df.groupby(["player_id", "season_start"])["trailing_war"]
                        .agg(lambda s: s.max() - s.min()))
        max_spread = float(war_spread.max())
        assert max_spread < 1e-6, (
            f"Some duplicated player-seasons have DIFFERING trailing_war "
            f"across their contract legs (max spread {max_spread:.6f}). The "
            "retention-collapse assumes the projection is identical across "
            "legs -- investigate before trusting the merge.")
        # Deterministic collapse: sort by contract_id so the retained-position
        # / market_label kept for the F-vs-D DIAGNOSTIC split is reproducible.
        # (These are the same across legs in every observed case; the sort
        #  just removes any dependence on row order. It never touches the
        #  headline number, which is position-blind.)
        df = (df.sort_values("contract_id")
                .drop_duplicates(subset=["player_id", "season_start"],
                                 keep="first"))
        print(f"  Collapsed {dupe_ct} retention-split duplicate rows "
              f"(mid-season trade + salary retention): kept one row per "
              f"player-season, projection identical across legs.")

    out = df[["player_id", "nhl_id", "season_start", "trailing_war",
              "position", "market_label"]].copy()
    # nhl_id is the bridge to the GV tables (built from the NHL game feed,
    # whose player_id IS the NHL id -- a DIFFERENT numbering system from the
    # spine's PuckPedia player_id). Joining on the wrong one silently returns
    # zero matches, so we drop rows with no nhl_id and count them explicitly.
    n_pre = len(out)
    out = out.dropna(subset=["nhl_id"])
    if len(out) < n_pre:
        print(f"  Dropped {n_pre - len(out)} rows with no nhl_id "
              "(cannot bridge to the NHL-feed GV table).")
    out["nhl_id"] = out["nhl_id"].astype(int)
    print(f"  Bacon-side (trailing_war) rows ready: {len(out):,}")
    return out


def load_gv_side() -> pd.DataFrame:
    """
    Load GV-adj from the local database. Read-only connection -- this
    script only ever SELECTs, never writes.
    """
    if not DB_PATH.exists():
        fail(f"Database not found at {DB_PATH}. Set GAMELOG_DB in .env "
             "(see .env.example).")

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    df = pd.read_sql("SELECT player_id, season, gv_adj FROM gv_adjusted", con)
    con.close()

    # The gv_adjusted table is built from the NHL game feed, so its
    # `player_id` column is actually an NHL id (7-digit, 84xxxxx), NOT the
    # PuckPedia player_id the spine uses. Rename it to nhl_id so the merge
    # keys are unambiguous and correct.
    df = df.rename(columns={"player_id": "nhl_id"})

    n0 = len(df)
    assert df["season"].astype(str).str.len().eq(8).all(), (
        "Expected `season` in gv_adjusted to be an 8-digit year-pair "
        "(e.g. 20172018). Found a different format -- the season_start "
        "conversion below would silently produce garbage.")

    # season is stored like 20172018 -- season_start is the first 4 digits.
    df["season_start"] = df["season"].astype(str).str[:4].astype(int)

    # Sanity check the encoding really is "start-year then start+1", not
    # something else that happens to also be 8 digits.
    implied_end = df["season"].astype(str).str[4:].astype(int)
    bad = (implied_end != df["season_start"] + 1).sum()
    assert bad == 0, (
        f"{bad} rows in gv_adjusted have a season code that isn't "
        "start-year immediately followed by start-year+1 -- the "
        "season_start parse assumption is wrong for some rows.")

    dupe_check = df.duplicated(subset=["nhl_id", "season_start"]).sum()
    assert dupe_check == 0, (
        f"gv_adjusted has {dupe_check} duplicate (nhl_id, season_start) "
        "rows -- expected exactly one GV-adj figure per player-season.")

    # Convert from goals (the unit GV-adj is built in) to wins, using the
    # LOCKED pooled rate. This is the only place a rate crosses from one
    # side to the other, and it is a hockey unit-conversion constant
    # (goals per win), not the Bacon-derived dollars-per-win rate --
    # keeping this distinction clean is the whole point of the script.
    df["gv_adj_wins"] = df["gv_adj"] / GOALS_PER_WIN

    print(f"  GV-adj rows loaded: {n0:,} (spans "
          f"{df['season_start'].min()}-{df['season_start'].max()})")
    return df[["nhl_id", "season_start", "gv_adj_wins"]]


def correlate(x: pd.Series, y: pd.Series, label: str) -> dict:
    """
    Run Pearson r, Spearman rho (if scipy available), and a simple OLS
    slope/intercept/R^2 -- all standard, off-the-shelf stats. Nothing
    here is fit or tuned; it just reports how the two series relate.
    """
    n = len(x)
    if n < 10:
        print(f"  [{label}] n={n} -- too small for a meaningful "
              "correlation, skipping.")
        return {"label": label, "n": n}

    pearson_r = float(np.corrcoef(x, y)[0, 1])

    if HAVE_SCIPY:
        spearman_rho, _ = scipy_stats.spearmanr(x, y)
        spearman_rho = float(spearman_rho)
    else:
        spearman_rho = np.nan

    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    print(f"  [{label}] n={n:,}  Pearson r={pearson_r:.3f}  "
          f"Spearman rho={spearman_rho:.3f}  "
          f"OLS slope={slope:.3f}  intercept={intercept:.3f}  R^2={r2:.3f}")

    return {"label": label, "n": n, "pearson_r": pearson_r,
            "spearman_rho": spearman_rho, "ols_slope": slope,
            "ols_intercept": intercept, "r2": r2}


def main() -> None:
    print("=" * 70)
    print("PHASE 4B -- CIRCULARITY VALIDATION (Tier 1, player-level)")
    print("=" * 70)

    print("\nLoading Bacon-side projections (skater_value_spine.csv)...")
    bacon = load_bacon_side()

    print("\nLoading GV-adj (local database, read-only)...")
    gv = load_gv_side()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # PRIMARY TEST: same-season.
    # trailing_war(t) was computed BEFORE season t happened; gv_adj_wins(t)
    # is what actually happened in season t. Comparing them is a clean
    # ex-ante-prediction-vs-outcome test with no look-ahead exposure.
    # -----------------------------------------------------------------
    print("\n--- PRIMARY TEST: trailing_war(t) vs GV-adj wins(t) ---")
    same = bacon.merge(gv, on=["nhl_id", "season_start"], how="inner")

    # TRIPWIRE: an ID-system mismatch (PuckPedia id vs NHL id) silently
    # returns zero matches and would otherwise look like a "completed" run
    # with empty output. Both tables cover 2017-18 onward, so within that
    # overlapping window we MUST get substantial matches. If we don't, the
    # join key is wrong -- stop loudly rather than report a null result.
    gv_years = set(gv["season_start"].unique())
    bacon_in_window = bacon[bacon["season_start"].isin(gv_years)]
    if len(bacon_in_window) > 0:
        overlap_rate = len(same) / len(bacon_in_window)
        assert overlap_rate > 0.5, (
            f"Only {len(same)} matches from {len(bacon_in_window)} Bacon-side "
            f"rows that fall inside GV-adj's season window "
            f"({overlap_rate:.1%}). Expected a high match rate on an ID-to-ID "
            "join over the same seasons -- this signals a join-KEY problem "
            "(e.g. joining PuckPedia player_id against NHL id), not a genuine "
            "coverage gap. Fix the key before trusting any result.")

    join_rate = len(same) / len(bacon)
    print(f"  Merge: {len(same):,} of {len(bacon):,} Bacon-side rows "
          f"matched to a GV-adj season ({join_rate:.1%}).")
    if join_rate < 0.5:
        print("  WARNING: less than half of Bacon-side rows found a GV-adj "
              "match. GV-adj only covers 2017-18 onward -- if the spine's "
              "priced window extends earlier, low join rate there is "
              "expected, not a bug. Check the season range below.")
    print(f"  Matched season range: {same['season_start'].min()}-"
          f"{same['season_start'].max()}")

    primary_result = correlate(same["trailing_war"], same["gv_adj_wins"],
                               "PRIMARY same-season")

    # Per-season breakdown, so a single noisy season doesn't get mistaken
    # for a stable relationship (or vice versa) -- same caution applied to
    # the goals-per-win figure in the rebase session.
    print("\n  Per-season breakdown (primary test):")
    per_season_rows = []
    for yr, g in same.groupby("season_start"):
        r = correlate(g["trailing_war"], g["gv_adj_wins"], f"season {yr}")
        r["season_start"] = yr
        per_season_rows.append(r)

    # Position breakdown -- diagnostic only. This is NOT re-litigating the
    # GV-vs-Bacon full-replacement battery (that's closed). It's here
    # because if the Bacon-vs-GV-adj relationship is forward-driven and
    # weak for defencemen, that's useful context for interpreting the
    # headline number, not a new decision point.
    print("\n  Position breakdown (primary test, diagnostic only):")
    pos_rows = []
    for pos, g in same.groupby(same["position"].str.startswith("D").map(
            {True: "D", False: "F"})):
        r = correlate(g["trailing_war"], g["gv_adj_wins"], f"position {pos}")
        r["position"] = pos
        pos_rows.append(r)

    # -----------------------------------------------------------------
    # SECONDARY TEST: one season out.
    # trailing_war(t) vs GV-adj wins(t+1) -- checks whether the projection
    # still tracks reality a year further downstream, or whether any
    # same-season agreement is coincidental / short-lived.
    # -----------------------------------------------------------------
    print("\n--- SECONDARY TEST: trailing_war(t) vs GV-adj wins(t+1) ---")
    gv_next = gv.rename(columns={"season_start": "season_start_next",
                                 "gv_adj_wins": "gv_adj_wins_next"})
    gv_next["season_start"] = gv_next["season_start_next"] - 1
    nxt = bacon.merge(
        gv_next[["nhl_id", "season_start", "gv_adj_wins_next"]],
        on=["nhl_id", "season_start"], how="inner")
    print(f"  Merge: {len(nxt):,} rows have a t+1 GV-adj season available.")
    secondary_result = correlate(nxt["trailing_war"], nxt["gv_adj_wins_next"],
                                 "SECONDARY t vs t+1")

    # -----------------------------------------------------------------
    # SAVE outputs
    # -----------------------------------------------------------------
    same.to_csv(OUT_DIR / "gv_4b_primary_matched_rows.csv", index=False)
    nxt.to_csv(OUT_DIR / "gv_4b_secondary_matched_rows.csv", index=False)

    summary = pd.DataFrame(
        [primary_result, secondary_result] + per_season_rows + pos_rows)
    summary.to_csv(OUT_DIR / "gv_4b_summary_stats.csv", index=False)

    print("\n" + "=" * 70)
    print(f"DONE. Outputs written to {OUT_DIR.resolve()}:")
    print("  gv_4b_primary_matched_rows.csv   (row-level, primary test)")
    print("  gv_4b_secondary_matched_rows.csv (row-level, secondary test)")
    print("  gv_4b_summary_stats.csv          (all correlation stats)")
    print("=" * 70)
    print("\nCopy the console output above (or the summary CSV) back into "
          "the chat -- that's what the interpretation pass needs.")


if __name__ == "__main__":
    main()
