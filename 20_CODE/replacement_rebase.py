#!/usr/bin/env python3
"""
replacement_rebase.py  --  Script 5 (post-assembly refinement of the Game-Value layer)

WHAT THIS DOES, IN PLAIN ENGLISH
---------------------------------
Two independent refinements to the game-level metric, requested 2026-07-06.
Both operate on the FINISHED output of Script 4 (metric_assembly.py); neither
re-runs the xG engine or touches the score-state work.

  1. REPLACEMENT-LEVEL REBASING.
     Right now Game Value (GV) is baselined at LEAGUE AVERAGE: the accounting
     identity forces the league-wide on-ice sum to 0, so "0" means "an average
     skater." Every published WAR model (Evolving-Hockey, Bacon) instead
     baselines at REPLACEMENT LEVEL -- the freely-available fill-in player, who
     is BELOW average. We move GV's zero-point down to replacement level using
     Evolving-Hockey's "poor man's replacement" recipe:

        - Within each (season, team), rank skaters by regular-season ice time.
        - Forwards below the top 13, and defencemen below the top 7, are the
          "replacement pool" (that is roughly a team's 14th+ forward and 8th+
          defenceman -- the guys a team swaps in and out without thinking).
        - Average that pool's GV-per-60 minutes, per season and per position.
          This is a NEGATIVE number (they are below average). Call it the
          replacement rate.
        - Rebase every player: gv_repl = game_value - (rate/60) * that game's TOI.
          Because the rate is negative, this ADDS value to everyone in
          proportion to how much they played -- exactly the goals-above-average
          -> goals-above-replacement transform WAR models use.

     WHY the threshold is safe for Karl: the cut is pure ice-time rank, set by
     coaches, using no outcome data -- so it introduces NO circularity, NO
     look-ahead, NO selection bias. It also uses only our own game data: no
     second player-value provider is touched, so single-provider discipline
     holds. GV is an OUTCOME yardstick (it measures what actually happened
     around a trade), not a trailing-window valuation input, so using full
     realized-season data to set the baseline is correct here and is NOT a
     look-ahead leak -- the same logic that already licenses GV using realized
     xG.

  2. SEASON-SPECIFIC GOALS-PER-WIN.
     Script 4 pools every team-season into one regression (wins on goal
     differential) -> a single 5.90 goals per win. Scoring environments drift
     over time, so we now fit ONE goals-per-win PER SEASON (regress that
     season's team wins on that season's goal differential, invert the slope).
     The pooled number is still computed as a reproduction guard and continuity
     value.

  3. xG IS KEPT. No change to inputs on either side of the ice. GV still prices
     expected goals for and against; we only re-baseline the finished number.

WHAT IS AND ISN'T CHANGED
--------------------------
  - UNTOUCHED: player_game_value (Script 4's table) and its league accounting
    identity. This script reads it, never writes it.
  - NEW TABLE: player_game_value_repl -- a full mirror of player_game_value
    PLUS the rebasing columns. The original game_value column is carried
    through unchanged next to the new gv_repl, so both baselines coexist and
    downstream code chooses per use:
        * mid-season ALLOCATION can stay on the zero-sum game_value (see note),
        * Phase 4b LEVEL comparisons use gv_repl (same zero-point as Bacon WAR).
  - NEW CSVs: goals_per_win_by_season.csv, replacement_baseline_by_season_pos.csv,
    replacement_rebase_validation.csv, replacement_rebase_runlog.txt.
  - metric_validation.csv (Script 4's) is left alone.

NEW COLUMNS ON player_game_value_repl
--------------------------------------
  position_raw       NHL box-score position for that game (C/L/R/D)
  pos_bucket         'F' (C/L/R) or 'D'; 'U' if position was never recorded
  season_team_toi    player's total regular-season TOI for that (season, team)
  toi_rank           his ice-time rank within (season, team, pos_bucket)
  is_replacement     1 if below the top-13 F / top-7 D cut, else 0
  is_regular_season  1 if game_type == 2 (rebasing applies to reg-season only)
  repl_rate_per60    the (season, pos_bucket) replacement baseline applied
  gv_repl            REBASED Game Value = goals above replacement

ASSERTS / GUARDS (fail loudly, never silently)
-----------------------------------------------
  G1  Required tables exist (player_game_value, skater_games, games).
  G2  Row-count parity: player_game_value_repl == player_game_value.
  G3  EXACT invariant: for every (season, pos_bucket), the replacement pool's
      gv_repl sums to ~0 by construction (we subtracted their own mean rate).
      Any group off by > 1e-4 is a build error -> reported.
  G4  Coverage: regular-season rows missing TOI or position are counted and
      reported (they cannot be ranked/rebased and are passed through unchanged).
  G5  Pooled goals-per-win reproduces Script 4's ~5.90 within 0.10 (a
      reproduce-before-extend check in the spirit of the D-log discipline).

USAGE (Windows, local):
    python replacement_rebase.py
Deterministic and idempotent: the output table is dropped and rebuilt each run.
Run AFTER metric_assembly.py.
"""

import csv
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from dotenv import load_dotenv

load_dotenv()

# db_inventory.py -- lists which chain tables exist + row counts. Read-only.
import sqlite3
DB_PATH = os.environ["GAMELOG_DB"]
con = sqlite3.connect(DB_PATH)
have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
# the chain, in dependency order: raw scrape -> Script1 -> 2 -> 3 -> 4
chain = ["games","skater_games","goalie_games","goal_events",   # raw scrape
         "on_ice_skaters",                                       # Script 1
         "shot_xg",                                              # Script 2
         "shot_score_state","score_state_factors",               # Script 3
         "penalty_events","player_game_value"]                   # Script 4 (+input)
for t in chain:
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t in have else None
    print(f"  {'OK ' if t in have else 'MISSING':<8} {t:<22} {n if n is not None else ''}")
con.close()

# ===========================================================================
# CONFIG  --  GAMELOG_DB is the SHARED path used by Scripts 1-4, read from
# .env (see .env.example). All five scripts in the chain resolve it the same
# way now, so the pre-reorg "Script 1 pointing at the wrong folder" incident
# cannot recur. Secondary CSVs + runlog land next to the DB, matching the
# other four chain scripts (OUT_DIR = DB_PATH.parent).
# ===========================================================================
DB_PATH = os.environ["GAMELOG_DB"]
OUT_DIR = Path(DB_PATH).parent                               # CSVs land next to the DB

TOP_F = 13     # forwards ranked 1..13 by TOI are "roster"; 14+ are replacement
TOP_D = 7      # defencemen ranked 1..7 are "roster"; 8+ are replacement
INVARIANT_TOL = 1e-4          # G3 tolerance on the per-(season,pos) zero-sum
POOLED_GPW_REF = 5.903        # Script 4's locked pooled goals-per-win (G5 check)
POOLED_GPW_TOL = 0.10

RUNLOG = []
def log(msg: str):
    """Print and capture -- the runlog is the audit trail Thomas keeps."""
    print(msg)
    RUNLOG.append(msg)


def main():
    # -----------------------------------------------------------------------
    # G1: connect and confirm the tables we depend on are present.
    # -----------------------------------------------------------------------
    if not Path(DB_PATH).exists():
        sys.exit(f"FATAL: DB not found at {DB_PATH}. Set GAMELOG_DB in .env to the shared path.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    have = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    need = {"player_game_value", "skater_games", "games"}
    missing = need - have
    if missing:
        sys.exit(f"FATAL: missing required tables {missing}. Run Scripts 1-4 first.")
    log(f"Connected. DB = {DB_PATH}")

    # =======================================================================
    # SECTION 1 -- REPLACEMENT-LEVEL REBASING
    # =======================================================================

    # -----------------------------------------------------------------------
    # STEP 1a: per-(season, team, player) REGULAR-SEASON stint aggregates.
    #   reg_gv  = sum of that stint's game_value  (from player_game_value)
    #   reg_toi = sum of that stint's ice time    (from skater_games)
    # We rank on regular-season ice time and estimate the replacement rate on
    # regular-season play only -- EH's replacement level is a regular-season
    # roster construct, and playoffs would distort ice-time ranks.
    # -----------------------------------------------------------------------
    log("\n[1a] Building (season, team, player) regular-season stint aggregates...")
    stints = {}   # (season, team, player_id) -> dict(reg_gv, reg_toi)
    for r in cur.execute("""
            SELECT v.season           AS season,
                   v.team             AS team,
                   v.player_id        AS player_id,
                   SUM(v.game_value)  AS reg_gv,
                   SUM(sg.toi_minutes) AS reg_toi
            FROM player_game_value v
            LEFT JOIN skater_games sg
              ON sg.game_id = v.game_id AND sg.player_id = v.player_id
            WHERE v.game_type = 2
            GROUP BY v.season, v.team, v.player_id"""):
        stints[(r["season"], r["team"], r["player_id"])] = {
            "reg_gv": r["reg_gv"] if r["reg_gv"] is not None else 0.0,
            "reg_toi": r["reg_toi"] if r["reg_toi"] is not None else 0.0,
        }
    log(f"     {len(stints):,} regular-season player-team stints.")

    # -----------------------------------------------------------------------
    # STEP 1b: assign each stint a position bucket by MODAL box-score position.
    #   Position can in principle vary game to game; we take the most frequent
    #   non-null code across the stint's regular-season games.
    #   Bucket: 'D' -> defenceman; C/L/R/F -> 'F'; nothing recorded -> 'U'.
    # -----------------------------------------------------------------------
    log("[1b] Assigning F/D buckets from modal box-score position...")
    pos_votes = defaultdict(lambda: defaultdict(int))   # stintkey -> {pos: count}
    for r in cur.execute("""
            SELECT g.season AS season, s.team AS team, s.player_id AS player_id,
                   s.position AS position, COUNT(*) AS c
            FROM skater_games s
            JOIN games g ON g.game_id = s.game_id
            WHERE CAST(g.game_type AS INTEGER) = 2 AND s.position IS NOT NULL
            GROUP BY g.season, s.team, s.player_id, s.position"""):
        pos_votes[(r["season"], r["team"], r["player_id"])][r["position"]] += r["c"]

    def bucket_for(stintkey):
        votes = pos_votes.get(stintkey)
        if not votes:
            return "U"                      # position never recorded
        modal = max(votes.items(), key=lambda kv: kv[1])[0]
        return "D" if modal == "D" else "F"  # C/L/R (and any 'F') -> forward

    n_u = 0
    for k in stints:
        b = bucket_for(k)
        stints[k]["pos_bucket"] = b
        if b == "U":
            n_u += 1
    if n_u:
        log(f"     *** {n_u} stints had NO recorded position -> bucket 'U'; "
            f"they are NOT ranked and NOT rebased (passed through unchanged). ***")
    else:
        log("     Position coverage complete: every stint bucketed F or D.")

    # -----------------------------------------------------------------------
    # STEP 1c: rank within (season, team, bucket) by reg-season TOI and flag
    #          the replacement pool (rank beyond the roster cut).
    # -----------------------------------------------------------------------
    log("[1c] Ranking by ice time and flagging the replacement pool...")
    by_group = defaultdict(list)            # (season, team, bucket) -> [stintkeys]
    for k, v in stints.items():
        if v["pos_bucket"] in ("F", "D"):
            by_group[(k[0], k[1], v["pos_bucket"])].append(k)

    for (season, team, bucket), keys in by_group.items():
        # rank by TOI descending; ties broken by player_id for determinism
        keys.sort(key=lambda kk: (-stints[kk]["reg_toi"], kk[2]))
        cut = TOP_F if bucket == "F" else TOP_D
        for i, kk in enumerate(keys, start=1):
            stints[kk]["toi_rank"] = i
            stints[kk]["is_replacement"] = 1 if i > cut else 0
    # 'U' stints get no rank / not replacement
    for k, v in stints.items():
        v.setdefault("toi_rank", 0)
        v.setdefault("is_replacement", 0)

    n_repl = sum(v["is_replacement"] for v in stints.values())
    log(f"     replacement pool: {n_repl:,} of {len(stints):,} stints "
        f"({100*n_repl/max(1,len(stints)):.1f}%).")

    # -----------------------------------------------------------------------
    # STEP 1d: replacement RATE per (season, pos_bucket), in goals per 60.
    #   rate = 60 * (sum reg_gv over pool) / (sum reg_toi over pool)
    #   This is the baseline we subtract. It is negative (pool is below avg).
    # -----------------------------------------------------------------------
    log("[1d] Estimating replacement baseline per (season, position)...")
    pool_gv = defaultdict(float)            # (season, bucket) -> sum reg_gv
    pool_toi = defaultdict(float)           # (season, bucket) -> sum reg_toi
    for k, v in stints.items():
        if v["is_replacement"] == 1:
            key = (k[0], v["pos_bucket"])
            pool_gv[key] += v["reg_gv"]
            pool_toi[key] += v["reg_toi"]

    repl_rate = {}                          # (season, bucket) -> rate_per60
    baseline_rows = []
    for key in sorted(pool_gv):
        toi = pool_toi[key]
        if toi <= 0:
            log(f"     *** WARNING: no replacement TOI for {key}; rate set 0. ***")
            rate = 0.0
        else:
            rate = 60.0 * pool_gv[key] / toi
        repl_rate[key] = rate
        baseline_rows.append((key[0], key[1],
                              sum(1 for k, v in stints.items()
                                  if v["is_replacement"] == 1
                                  and (k[0], v["pos_bucket"]) == key),
                              round(toi, 1), round(rate, 6)))

    # -----------------------------------------------------------------------
    # STEP 1e: push the per-stint flags and per-(season,pos) rates into TEMP
    #          tables, then build player_game_value_repl by a single SQL join.
    #          Doing the arithmetic in SQL keeps it fast and auditable.
    # -----------------------------------------------------------------------
    log("[1e] Writing rebased table player_game_value_repl...")
    cur.executescript("""
        DROP TABLE IF EXISTS _repl_flag;
        DROP TABLE IF EXISTS _repl_rate;
        CREATE TEMP TABLE _repl_flag (
            season TEXT, team TEXT, player_id INTEGER,
            pos_bucket TEXT, reg_toi REAL, toi_rank INTEGER, is_replacement INTEGER
        );
        CREATE TEMP TABLE _repl_rate (
            season TEXT, pos_bucket TEXT, rate_per60 REAL
        );
    """)
    cur.executemany(
        "INSERT INTO _repl_flag VALUES (?,?,?,?,?,?,?)",
        [(k[0], k[1], k[2], v["pos_bucket"], round(v["reg_toi"], 6),
          v["toi_rank"], v["is_replacement"]) for k, v in stints.items()])
    cur.executemany(
        "INSERT INTO _repl_rate VALUES (?,?,?)",
        [(s, b, r) for (s, b), r in repl_rate.items()])
    cur.executescript("""
        CREATE INDEX _ix_flag ON _repl_flag(season, team, player_id);
        CREATE INDEX _ix_rate ON _repl_rate(season, pos_bucket);
    """)

    # gv_repl = game_value - (rate/60) * TOI, applied to REGULAR-SEASON rows
    # that have both a rate and a TOI. Playoff rows and un-bucketed/no-TOI rows
    # pass through unchanged (gv_repl = game_value, repl_rate NULL).
    cur.executescript("""
        DROP TABLE IF EXISTS player_game_value_repl;
        CREATE TABLE player_game_value_repl AS
        SELECT
            v.*,                                   -- every original column, incl. game_value
            sg.toi_minutes                      AS toi_minutes,
            sg.position                         AS position_raw,
            COALESCE(f.pos_bucket, 'U')         AS pos_bucket,
            f.reg_toi                           AS season_team_toi,
            COALESCE(f.toi_rank, 0)             AS toi_rank,
            COALESCE(f.is_replacement, 0)       AS is_replacement,
            CASE WHEN v.game_type = 2 THEN 1 ELSE 0 END AS is_regular_season,
            CASE WHEN v.game_type = 2 THEN r.rate_per60 ELSE NULL END AS repl_rate_per60,
            CASE
              WHEN v.game_type = 2
                   AND sg.toi_minutes IS NOT NULL
                   AND r.rate_per60 IS NOT NULL
              THEN v.game_value - (r.rate_per60 / 60.0) * sg.toi_minutes
              ELSE v.game_value
            END                                 AS gv_repl
        FROM player_game_value v
        LEFT JOIN skater_games sg
          ON sg.game_id = v.game_id AND sg.player_id = v.player_id
        LEFT JOIN _repl_flag f
          ON f.season = v.season AND f.team = v.team AND f.player_id = v.player_id
        LEFT JOIN _repl_rate r
          ON r.season = v.season AND r.pos_bucket = COALESCE(f.pos_bucket, 'U');
    """)
    conn.commit()

    # -------------------- GUARDS G2, G3, G4 --------------------
    n_src = cur.execute("SELECT COUNT(*) FROM player_game_value").fetchone()[0]
    n_out = cur.execute("SELECT COUNT(*) FROM player_game_value_repl").fetchone()[0]
    log(f"     rows: source {n_src:,} -> rebased {n_out:,}")
    assert n_src == n_out, f"G2 FAIL: row-count mismatch {n_src} vs {n_out}"

    # G3: replacement pool's gv_repl must sum to ~0 within each (season, pos).
    bad = []
    for r in cur.execute("""
            SELECT season, pos_bucket, SUM(gv_repl) AS s
            FROM player_game_value_repl
            WHERE is_regular_season = 1 AND is_replacement = 1
            GROUP BY season, pos_bucket"""):
        if abs(r["s"]) > INVARIANT_TOL:
            bad.append((r["season"], r["pos_bucket"], r["s"]))
    if bad:
        for s, b, val in bad[:10]:
            log(f"     *** G3 WARNING: replacement pool {s}/{b} sums to "
                f"{val:+.6f} (should be ~0). ***")
    else:
        log("     [G3] Replacement-pool zero-sum invariant holds for every "
            "(season, position).")

    # G4: coverage of TOI/position on regular-season rows.
    miss_toi = cur.execute("""SELECT COUNT(*) FROM player_game_value_repl
        WHERE is_regular_season = 1 AND toi_minutes IS NULL""").fetchone()[0]
    miss_pos = cur.execute("""SELECT COUNT(*) FROM player_game_value_repl
        WHERE is_regular_season = 1 AND pos_bucket = 'U'""").fetchone()[0]
    log(f"     [G4] regular-season rows missing TOI: {miss_toi}; "
        f"missing position: {miss_pos} (both passed through un-rebased).")

    # Report the size of the shift: total goals above replacement (reg season).
    gar_total = cur.execute("""SELECT SUM(gv_repl) FROM player_game_value_repl
        WHERE is_regular_season = 1""").fetchone()[0]
    gaa_total = cur.execute("""SELECT SUM(game_value) FROM player_game_value_repl
        WHERE is_regular_season = 1""").fetchone()[0]
    log(f"     league reg-season sum: game_value(avg-based) = {gaa_total:+.2f} "
        f"(~0 by identity); gv_repl(above replacement) = {gar_total:+.2f} "
        f"(positive: the league is above replacement, as expected).")

    # =======================================================================
    # SECTION 2 -- SEASON-SPECIFIC GOALS-PER-WIN
    # (Mirrors Script 4's STEP 5C, but fit once per season. Regular season only,
    #  in-play differential: the shootout winner's +1 is stripped so both sides
    #  of the regression describe the same on-ice thing.)
    # =======================================================================
    log("\n[2] Season-specific goals-per-win (wins ~ goal differential)...")
    per_season = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # season -> team -> [wins, diff]
    pooled = defaultdict(lambda: [0, 0])                            # team-season pooled

    for r in cur.execute("""
            SELECT season, away_team, home_team, away_score, home_score, last_period
            FROM games WHERE CAST(game_type AS INTEGER) = 2"""):
        asc, hsc = r["away_score"], r["home_score"]
        if asc is None or hsc is None:
            continue
        asc, hsc = int(asc), int(hsc)
        winner = r["home_team"] if hsc > asc else r["away_team"]
        a2, h2 = asc, hsc
        if r["last_period"] == "SO":            # strip shootout deciding goal
            if asc > hsc: a2 -= 1
            else: h2 -= 1
        s = r["season"]
        per_season[s][r["home_team"]][0] += 1 if winner == r["home_team"] else 0
        per_season[s][r["home_team"]][1] += h2 - a2
        per_season[s][r["away_team"]][0] += 1 if winner == r["away_team"] else 0
        per_season[s][r["away_team"]][1] += a2 - h2
        pooled[(s, r["home_team"])][0] += 1 if winner == r["home_team"] else 0
        pooled[(s, r["home_team"])][1] += h2 - a2
        pooled[(s, r["away_team"])][0] += 1 if winner == r["away_team"] else 0
        pooled[(s, r["away_team"])][1] += a2 - h2

    def gpw_from(points):
        """points: list of [wins, diff]; returns (goals_per_win, slope, n)."""
        W = np.array([p[0] for p in points], dtype=float)
        D = np.array([p[1] for p in points], dtype=float)
        X = np.column_stack([np.ones(len(D)), D])
        b, *_ = np.linalg.lstsq(X, W, rcond=None)
        slope = b[1]
        return (1.0 / slope if slope != 0 else float("nan"), slope, len(W))

    season_rows = []
    for s in sorted(per_season):
        pts = list(per_season[s].values())
        gpw, slope, n = gpw_from(pts)
        if n < 10:
            log(f"     *** WARNING: season {s} has only {n} teams; gpw noisy. ***")
        season_rows.append((s, n, round(slope, 6), round(gpw, 3)))
        log(f"     {s}: {n} teams, goals/win = {gpw:.3f}")

    # Pooled (continuity + G5 reproduction guard).
    pooled_gpw, pooled_slope, pooled_n = gpw_from(list(pooled.values()))
    log(f"     POOLED (all seasons): {pooled_n} team-seasons, goals/win = {pooled_gpw:.3f}")
    if abs(pooled_gpw - POOLED_GPW_REF) > POOLED_GPW_TOL:
        log(f"     *** G5 WARNING: pooled goals/win {pooled_gpw:.3f} differs "
            f"from Script 4's {POOLED_GPW_REF} by > {POOLED_GPW_TOL}. Investigate "
            f"before trusting the season splits. ***")
    else:
        log(f"     [G5] pooled goals/win reproduces Script 4's "
            f"{POOLED_GPW_REF} within {POOLED_GPW_TOL}.")

    # =======================================================================
    # SECTION 3 -- WRITE CSVs + RUNLOG
    # =======================================================================
    log("\n[3] Writing CSV outputs...")

    with open(OUT_DIR / "goals_per_win_by_season.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["season", "n_teams", "wins_per_goal_slope", "goals_per_win"])
        for row in season_rows:
            w.writerow(row)
        w.writerow(["POOLED", pooled_n, round(pooled_slope, 6), round(pooled_gpw, 3)])

    with open(OUT_DIR / "replacement_baseline_by_season_pos.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["season", "pos_bucket", "n_replacement_stints",
                    "replacement_toi_min", "replacement_rate_per60"])
        for row in sorted(baseline_rows):
            w.writerow(row)

    with open(OUT_DIR / "replacement_rebase_validation.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["check", "value", "note"])
        w.writerow(["rows_source", n_src, "player_game_value"])
        w.writerow(["rows_rebased", n_out, "player_game_value_repl (must match)"])
        w.writerow(["replacement_stint_share",
                    round(100 * n_repl / max(1, len(stints)), 2),
                    "% of stints below the top-13F/top-7D cut"])
        w.writerow(["reg_season_gv_repl_total", round(gar_total, 2),
                    "total goals above replacement (positive by design)"])
        w.writerow(["invariant_groups_failed", len(bad),
                    "(season,pos) groups where replacement pool != 0"])
        w.writerow(["reg_rows_missing_toi", miss_toi, "passed through un-rebased"])
        w.writerow(["reg_rows_missing_position", miss_pos, "passed through un-rebased"])
        w.writerow(["pooled_goals_per_win", round(pooled_gpw, 3),
                    f"continuity; Script 4 ref {POOLED_GPW_REF}"])

    (OUT_DIR / "replacement_rebase_runlog.txt").write_text(
        "\n".join(RUNLOG) + "\n", encoding="utf-8")

    conn.close()
    log("\nDone. New table: player_game_value_repl. CSVs written to " + str(OUT_DIR.resolve()))


if __name__ == "__main__":
    main()
