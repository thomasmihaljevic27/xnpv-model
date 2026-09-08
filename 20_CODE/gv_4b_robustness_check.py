"""
gv_4b_robustness_check.py -- Phase 4b: GV-raw ROBUSTNESS leg
==============================================================

WHY THIS EXISTS (plain English):
  The locked Phase 4b design is a PAIR of validators: GV-adj (primary,
  already run 2026-07-14, r = 0.576) and GV-raw (robustness -- this
  script). GV-raw is the simpler, unadjusted version of the game-level
  metric: no teammate/competition separation, no finishing-talent
  shrinkage. Running the same test against it answers one question:
  does the primary result depend on the adjustments baked into GV-adj,
  or does the agreement hold even against the rawest form of the
  independent data? If both legs agree, the convergent-validity claim
  is sturdier; if they diverge sharply, that's a finding about which
  layer of the benchmark carries the signal.

WHAT'S DIFFERENT FROM THE PRIMARY SCRIPT:
  Only the outcome side. The Bacon side (trailing_war from the skater
  spine, with the retention-split collapse) is IDENTICAL -- same rows,
  same guards -- so any difference in results is attributable to the
  benchmark, not the sample.

  GV-raw lives at the per-GAME level (table player_game_value_repl),
  so this script aggregates it to player-seasons first. It reports TWO
  variants of the same test:
    (a) zero-sum GV-raw   -- SUM(game_value):  value relative to the
        league AVERAGE skater (league total is exactly zero).
    (b) rebased GV-raw    -- SUM(gv_repl):     value relative to a
        REPLACEMENT-level skater, which is the same baseline concept
        trailing_war uses ("wins above replacement"). Conceptually the
        better-matched variant; the zero-sum one is kept because the
        rebase is known to inflate offensive defencemen (a documented
        GV-raw limitation), so seeing both brackets the effect.

  Regular-season games only (is_regular_season = 1), because Bacon WAR
  is a regular-season metric -- mixing playoff games into the outcome
  would grade the projection against something it never claimed to
  predict.

KNOWN, EXPECTED WEAKNESS (do not "fix" it if it appears):
  GV-raw carries the full teammate confound (equal on-ice credit), so
  its agreement with trailing_war is EXPECTED to be lower than GV-adj's,
  especially for defencemen. That is why it is the robustness leg and
  not the primary. A lower number here is not a failure of the model.

INPUTS:
  1. skater_value_spine.csv                     (same as primary)
  2. Local SQLite, table player_game_value_repl (confirmed in inventory)

HOW TO RUN:
  python gv_4b_robustness_check.py
  (from the folder containing skater_value_spine.csv)
"""

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy import stats as scipy_stats
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False
    print("NOTE: scipy not found -- Spearman rank correlation will be "
          "skipped (Pearson + OLS still run).")

# ---------------------------------------------------------------------------
# PATHS -- same conventions as the primary script.
# ---------------------------------------------------------------------------
DB_PATH = Path(r"C:\Users\thoma\OneDrive\Desktop\test\nhl_gamelogs.sqlite")
SPINE_PATH = Path("skater_value_spine.csv")
OUT_DIR = Path("gv_4b_outputs")

# ---------------------------------------------------------------------------
# LOCKED CONSTANTS -- identical to the primary run. Not tunable.
# ---------------------------------------------------------------------------
GOALS_PER_WIN = 5.903

# For comparability, the headline of the PRIMARY run (GV-adj), so the
# console report can print the robustness numbers side by side with it.
PRIMARY_HEADLINE = {"pearson_r": 0.576, "spearman_rho": 0.460,
                    "r2": 0.331, "n": 6027}


def fail(msg: str) -> None:
    print("\n" + "!" * 70)
    print("STOPPED: " + msg)
    print("!" * 70)
    sys.exit(1)


# ---------------------------------------------------------------------------
# BACON SIDE -- byte-for-byte the same logic as the primary script, so the
# two legs are guaranteed to test the identical sample. If you ever edit
# one copy, edit both (or better: tell Claude, and we'll factor it out).
# ---------------------------------------------------------------------------
def load_bacon_side() -> pd.DataFrame:
    if not SPINE_PATH.exists():
        fail(f"Can't find {SPINE_PATH.resolve()}. Run this script from the "
             "folder containing skater_value_spine.csv, or edit SPINE_PATH.")

    df = pd.read_csv(SPINE_PATH)

    required = {"player_id", "nhl_id", "season_start", "trailing_war",
                "merged_name_excluded", "position", "market_label"}
    missing = required - set(df.columns)
    if missing:
        fail(f"skater_value_spine.csv is missing expected columns: {missing}.")

    n0 = len(df)
    df = df[df["merged_name_excluded"] != True]  # noqa: E712
    n1 = len(df)
    print(f"  Dropped {n0 - n1} merged-name-collision rows.")

    df = df.dropna(subset=["trailing_war"])
    n2 = len(df)
    print(f"  Dropped {n1 - n2} rows with no trailing_war.")

    # Retention-split duplicate collapse (mid-season trade + salary
    # retention -> two cost legs, one identical projection). Guard: the
    # collapse is only valid if the projection really is identical.
    dupe_ct = df.duplicated(subset=["player_id", "season_start"]).sum()
    if dupe_ct:
        war_spread = (df.groupby(["player_id", "season_start"])["trailing_war"]
                        .agg(lambda s: s.max() - s.min()))
        assert float(war_spread.max()) < 1e-6, (
            "Duplicated player-seasons DISAGREE on trailing_war across "
            "contract legs -- investigate before trusting the merge.")
        df = (df.sort_values("contract_id")
                .drop_duplicates(subset=["player_id", "season_start"],
                                 keep="first"))
        print(f"  Collapsed {dupe_ct} retention-split duplicate rows.")

    out = df[["player_id", "nhl_id", "season_start", "trailing_war",
              "position", "market_label"]].copy()
    n_pre = len(out)
    out = out.dropna(subset=["nhl_id"])
    if len(out) < n_pre:
        print(f"  Dropped {n_pre - len(out)} rows with no nhl_id.")
    out["nhl_id"] = out["nhl_id"].astype(int)
    print(f"  Bacon-side rows ready: {len(out):,}")
    return out


# ---------------------------------------------------------------------------
# GV-RAW SIDE -- aggregate the per-game table to player-seasons.
# ---------------------------------------------------------------------------
def load_gv_raw_side() -> pd.DataFrame:
    if not DB_PATH.exists():
        fail(f"Database not found at {DB_PATH}. Edit DB_PATH at the top.")

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)

    # The aggregation happens IN SQL so the 427k-row table never has to
    # travel into pandas whole. Both columns summed in one pass:
    #   game_value = zero-sum GV-raw (vs league average)
    #   gv_repl    = replacement-rebased GV-raw (vs replacement level)
    # Regular-season only: Bacon WAR is a regular-season metric, so the
    # outcome must be too, or we'd grade the projection against games it
    # never claimed to cover.
    df = pd.read_sql(
        """
        SELECT player_id      AS nhl_id,          -- NHL id, same as primary
               season,
               SUM(game_value) AS gv_raw_goals,   -- zero-sum variant
               SUM(gv_repl)    AS gv_repl_goals,  -- rebased variant
               COUNT(*)        AS n_games
        FROM player_game_value_repl
        WHERE is_regular_season = 1
        GROUP BY player_id, season
        """, con)
    con.close()

    assert df["season"].astype(str).str.len().eq(8).all(), (
        "Expected 8-digit season codes (e.g. 20172018) in "
        "player_game_value_repl -- parse assumption violated.")
    df["season_start"] = df["season"].astype(str).str[:4].astype(int)
    implied_end = df["season"].astype(str).str[4:].astype(int)
    assert (implied_end == df["season_start"] + 1).all(), (
        "Season codes are not start-year followed by start-year+1.")

    dupes = df.duplicated(subset=["nhl_id", "season_start"]).sum()
    assert dupes == 0, (
        f"{dupes} duplicate (nhl_id, season_start) after aggregation -- "
        "the GROUP BY should make this impossible; investigate.")

    # Goals -> wins at the locked pooled rate (same as primary; the only
    # cross-side conversion, and it's a hockey unit constant, not the
    # Bacon-derived dollar rate).
    df["gv_raw_wins"] = df["gv_raw_goals"] / GOALS_PER_WIN
    df["gv_repl_wins"] = df["gv_repl_goals"] / GOALS_PER_WIN

    print(f"  GV-raw player-seasons aggregated: {len(df):,} "
          f"(spans {df['season_start'].min()}-{df['season_start'].max()}, "
          f"regular season only)")
    return df[["nhl_id", "season_start", "gv_raw_wins", "gv_repl_wins"]]


def correlate(x: pd.Series, y: pd.Series, label: str) -> dict:
    n = len(x)
    if n < 10:
        print(f"  [{label}] n={n} -- too small, skipping.")
        return {"label": label, "n": n}
    pearson_r = float(np.corrcoef(x, y)[0, 1])
    if HAVE_SCIPY:
        spearman_rho = float(scipy_stats.spearmanr(x, y)[0])
    else:
        spearman_rho = np.nan
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    print(f"  [{label}] n={n:,}  Pearson r={pearson_r:.3f}  "
          f"Spearman rho={spearman_rho:.3f}  OLS slope={slope:.3f}  "
          f"R^2={r2:.3f}")
    return {"label": label, "n": n, "pearson_r": pearson_r,
            "spearman_rho": spearman_rho, "ols_slope": slope,
            "ols_intercept": intercept, "r2": r2}


def run_variant(bacon: pd.DataFrame, gv: pd.DataFrame,
                wins_col: str, tag: str) -> list:
    """
    Run the full primary/secondary/per-season/position battery for ONE
    GV-raw variant (zero-sum or rebased). Mirrors the primary script's
    structure exactly so the numbers are directly comparable.
    """
    results = []
    print(f"\n{'='*70}\nVARIANT: {tag}\n{'='*70}")

    # ---- same-season ----
    same = bacon.merge(gv[["nhl_id", "season_start", wins_col]],
                       on=["nhl_id", "season_start"], how="inner")

    # Zero-overlap tripwire, same as the primary script: within the
    # covered season window, an ID-to-ID join must match substantially.
    gv_years = set(gv["season_start"].unique())
    in_window = bacon[bacon["season_start"].isin(gv_years)]
    if len(in_window) > 0:
        rate = len(same) / len(in_window)
        assert rate > 0.5, (
            f"Only {rate:.1%} of in-window Bacon rows matched -- join-key "
            "problem, not a coverage gap. Fix before trusting anything.")

    print(f"  Merge: {len(same):,} of {len(bacon):,} Bacon rows matched "
          f"({len(same)/len(bacon):.1%}).")
    r = correlate(same["trailing_war"], same[wins_col],
                  f"{tag} same-season")
    r["variant"] = tag
    results.append(r)

    print(f"\n  Per-season breakdown ({tag}):")
    for yr, g in same.groupby("season_start"):
        rr = correlate(g["trailing_war"], g[wins_col], f"season {yr}")
        rr["variant"], rr["season_start"] = tag, yr
        results.append(rr)

    print(f"\n  Position breakdown ({tag}, diagnostic only):")
    for pos, g in same.groupby(same["position"].str.startswith("D").map(
            {True: "D", False: "F"})):
        rr = correlate(g["trailing_war"], g[wins_col], f"position {pos}")
        rr["variant"], rr["position"] = tag, pos
        results.append(rr)

    # ---- one season out ----
    gv_next = gv[["nhl_id", "season_start", wins_col]].copy()
    gv_next = gv_next.rename(columns={wins_col: wins_col + "_next"})
    gv_next["season_start"] = gv_next["season_start"] - 1
    nxt = bacon.merge(gv_next, on=["nhl_id", "season_start"], how="inner")
    print(f"\n  t+1 merge: {len(nxt):,} rows.")
    r = correlate(nxt["trailing_war"], nxt[wins_col + "_next"],
                  f"{tag} t vs t+1")
    r["variant"] = tag
    results.append(r)

    # save row-level file for this variant
    OUT_DIR.mkdir(exist_ok=True)
    same.to_csv(OUT_DIR / f"gv_4b_robust_{tag}_matched_rows.csv", index=False)
    return results


def main() -> None:
    print("=" * 70)
    print("PHASE 4B -- ROBUSTNESS LEG (GV-raw, both variants)")
    print("=" * 70)

    print("\nLoading Bacon-side projections (identical to primary run)...")
    bacon = load_bacon_side()

    print("\nLoading + aggregating GV-raw (local database, read-only)...")
    gv = load_gv_raw_side()

    all_results = []
    # Rebased first: it shares trailing_war's above-replacement baseline,
    # so it's the conceptually matched robustness comparison.
    all_results += run_variant(bacon, gv, "gv_repl_wins", "rebased")
    # Zero-sum second: brackets the rebase's known offensive-D inflation.
    all_results += run_variant(bacon, gv, "gv_raw_wins", "zerosum")

    summary = pd.DataFrame(all_results)
    summary.to_csv(OUT_DIR / "gv_4b_robustness_summary.csv", index=False)

    # Side-by-side with the primary headline, so the console output alone
    # answers the robustness question.
    print("\n" + "=" * 70)
    print("HEADLINE COMPARISON (same-season, pooled)")
    print("=" * 70)
    print(f"  GV-adj  (PRIMARY, run 2026-07-14): "
          f"r={PRIMARY_HEADLINE['pearson_r']:.3f}  "
          f"rho={PRIMARY_HEADLINE['spearman_rho']:.3f}  "
          f"R^2={PRIMARY_HEADLINE['r2']:.3f}  "
          f"n={PRIMARY_HEADLINE['n']:,}")
    for tag in ("rebased", "zerosum"):
        row = next(r for r in all_results
                   if r.get("variant") == tag and "same-season" in r["label"])
        print(f"  GV-raw {tag:8s} (robustness):      "
              f"r={row['pearson_r']:.3f}  rho={row['spearman_rho']:.3f}  "
              f"R^2={row['r2']:.3f}  n={row['n']:,}")

    print(f"\nOutputs written to {OUT_DIR.resolve()}:")
    print("  gv_4b_robust_rebased_matched_rows.csv")
    print("  gv_4b_robust_zerosum_matched_rows.csv")
    print("  gv_4b_robustness_summary.csv")
    print("\nCopy the console output back into the chat for interpretation "
          "and the 4b close-out.")


if __name__ == "__main__":
    main()
