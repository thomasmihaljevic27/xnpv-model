#!/usr/bin/env python3
"""
metric_assembly.py  --  Script 4 of 4: final game-level metric assembly

WHAT THIS DOES, IN PLAIN ENGLISH
---------------------------------
Combines the outputs of Scripts 1-3 into ONE number per skater per game,
denominated in goals: how much did this player's presence tilt the game?
That number is what work-queue items 4 and 5 actually consume:
  - MID-SEASON ALLOCATION: sum a player's game values before and after a
    trade date to split his season's value between the two teams. The
    `team` column on every row is what makes the split mechanical.
  - CIRCULARITY FIX: aggregate to season level and it is a realized-outcome
    yardstick built entirely from NHL source data -- no Bacon inputs at any
    stage -- against which the $/WAR rate can be validated.

THE THREE COMPONENTS OF EACH ROW
----------------------------------
1. ON-ICE COMPONENT (the workhorse). Every scoring chance (xG, Script 2)
   his team created while he was on the ice counts FOR him; every chance
   the opponent created counts AGAINST him. Each chance is weighted by the
   score-state factor (Script 3) so chances piled up while chasing a game
   count slightly less and chances created while protecting a lead count
   slightly more. Credit is split EQUALLY among the skaters actually on
   the ice (locked decision -- see "equal split" below).
2. PENALTY COMPONENT. Each penalty DRAWN is worth the league-average net
   goal value of the power play it creates (estimated from our own data,
   below); each penalty TAKEN is the mirror-image negative.
3. INDIVIDUAL xG (ixg) -- stored as its own column, deliberately NOT added
   into the total: the player's own shots are already inside his on-ice
   total, and adding them again would double-count. Kept so a
   shooter-weighted variant can be built later without re-running anything.

      game_value = on-ice component + penalty component

THE EQUAL SPLIT, PRECISELY (and why it survives a committee)
--------------------------------------------------------------
Each chance's value is divided by the number of skaters ACTUALLY on the ice
for that side at that moment -- xG/5 at full strength, xG/4 for the
shorthanded side, and so on. Two properties fall out:
  - ACCOUNTING IDENTITY: sum every player's on-ice component across the
    league and you get EXACTLY zero, because every chance enters once as
    +xG (split among the attackers) and once as -xG (split among the
    defenders). Nothing estimated, nothing tuned, zero free parameters.
    The identity is CHECKED at runtime, not assumed.
  - TEAM SUMS ARE EXACT: a team's players sum to precisely the team's
    score-adjusted chance differential, which is what the validation
    regression below leans on.
KNOWN COST, DOCUMENTED NOT HIDDEN: an equal split cannot separate a great
player from the linemates he drags around (the teammate confound logged at
Tier 2 selection). That is why this metric is scoped to season-splitting
and aggregate validation -- not standalone player valuation.

SCORE FACTORS APPLY TO EVEN-STRENGTH CHANCES ONLY. The factors were
estimated on even-strength play (Script 3, design decision 2) because on
the power play the manpower edge -- not the scoreboard -- drives volume.
Power-play and shorthanded chances therefore enter at factor 1.0.

THE PENALTY VALUE, ESTIMATED NOT ASSUMED
------------------------------------------
One drawn penalty is worth v goals, where
      v = (league PP goals - league SH goals) / eligible penalties,
computed from our own regular-season data. "Eligible" excludes:
  - COINCIDENTAL penalties (both teams penalized at the same game clock
    instant -- offsetting minors, fights): no power play results.
  - MISCONDUCTS (10+ minutes): the team plays on at full strength.
Simplification, flagged: majors (5 min) are priced at the same flat v as
minors. A major's power play is longer but rarer; a duration-weighted v is
a possible refinement, logged rather than built (minimum-scope rule).
Attribution: the player who DREW the penalty gets +v, the player who TOOK
it gets -v. Bench/team penalties with no individual attached in the feed
are counted and reported but credited to no one.

BUILT-IN VALIDATION (the audit, not an afterthought)
------------------------------------------------------
A. ACCOUNTING IDENTITY: league-wide sum of the on-ice component must be
   ~zero (machine precision). Checked and reported.
B. TEAM-GAME REGRESSION (the locked "validator, not weight source"):
   for every regular-season team-game, regress the ACTUAL goal
   differential on the team's summed metric. This confirms the assembled
   number tracks real outcomes -- without ever fitting anything to Bacon,
   preserving the circularity fix. Reported: slope (should be near 1 --
   the metric is already in goals, so a goal of metric should predict
   about a goal of outcome) and R-squared, which for SINGLE GAMES will be
   modest by nature: one game of hockey is mostly noise, and the metric
   prices chances, not puck luck. The signal compounds over a season,
   which is the horizon the paper actually uses.
   Shootout note: the official final credits the SO winner one goal no
   in-play event produced; the regression uses the in-play differential
   (SO winner's +1 removed) so both sides of the equation describe the
   same thing.
C. GOALS-PER-WIN: the final link in the currency chain (production ->
   goals -> wins -> dollars). Estimated from our own games table: regress
   team regular-season wins on team goal differential across team-seasons;
   the slope inverts to goals-per-win. Reported and written to CSV.

OUTPUTS
--------
  player_game_value   (DB table)  one row per skater per game:
      identifiers, team, on-ice xG for/against (score-adjusted),
      on-ice component, penalties drawn/taken, penalty component,
      game_value, ixg
  metric_validation.csv           identity check, regression, goals/win
  metric_assembly_runlog.txt

DEPENDENCIES
-------------
  numpy (installed alongside scikit-learn in the Script 2 step).

USAGE
------
  python3 metric_assembly.py
Deterministic and idempotent: output table dropped and rebuilt every run.
Runs after Scripts 1-3 (needs on_ice_skaters, shot_xg, shot_score_state,
score_state_factors, penalty_events).
"""

import csv
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from dotenv import load_dotenv

load_dotenv()

SCRIPT_VERSION = "v1.0 (2026-07-03) -- initial metric assembly"

# ---------------------------------------------------------------------------
# CONFIG -- same database Scripts 1-3 wrote into. GAMELOG_DB comes from .env.
# ---------------------------------------------------------------------------
DB_PATH = Path(os.environ["GAMELOG_DB"])
OUT_DIR = DB_PATH.parent

RUNLOG = []
def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line)
    RUNLOG.append(line)


def main() -> None:
    print(f"metric_assembly.py {SCRIPT_VERSION}")
    if not DB_PATH.exists():
        print(f"Database not found at:\n  {DB_PATH}\n"
            f"Set GAMELOG_DB in .env (see .env.example).", file=sys.stderr)
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {"games", "skater_games", "on_ice_skaters", "shot_xg",
               "shot_score_state", "score_state_factors",
               "penalty_events"} - tables
    if missing:
        print(f"Required tables missing: {sorted(missing)}. Run Scripts 1-3 "
            f"first.", file=sys.stderr)
        raise SystemExit(1)

    # -----------------------------------------------------------------------
    # STEP 1: per-event effective xG and on-ice head-counts, as temp tables.
    # eff_xg = xg * score factor (EV only; PP/SH at 1.0 -- see docstring).
    # n_for / n_against = skaters actually on the ice per side, so the
    # equal split divides by the TRUE denominator (4 on a penalty kill),
    # which is exactly what makes the accounting identity hold at 5v4.
    # -----------------------------------------------------------------------
    log("Building per-event effective-xG and on-ice count tables...")
    cur.executescript("""
        DROP TABLE IF EXISTS _event_counts;
        CREATE TEMP TABLE _event_counts AS
        SELECT game_id, event_id,
               SUM(on_event_team)     AS n_for,
               SUM(1 - on_event_team) AS n_against
        FROM on_ice_skaters GROUP BY game_id, event_id;
        CREATE UNIQUE INDEX _ec_pk ON _event_counts(game_id, event_id);

        DROP TABLE IF EXISTS _event_val;
        CREATE TEMP TABLE _event_val AS
        SELECT x.game_id, x.event_id,
               x.xg * CASE WHEN x.strength = 'EV'
                           THEN f.adjustment_factor ELSE 1.0 END AS eff_xg,
               c.n_for, c.n_against
        FROM shot_xg x
        JOIN shot_score_state t
          ON t.game_id = x.game_id AND t.event_id = x.event_id
        JOIN score_state_factors f ON f.score_state = t.score_state
        JOIN _event_counts c
          ON c.game_id = x.game_id AND c.event_id = x.event_id
        WHERE c.n_for > 0 AND c.n_against > 0;
        CREATE UNIQUE INDEX _ev_pk ON _event_val(game_id, event_id);
    """)
    n_events = cur.execute("SELECT COUNT(*) FROM _event_val").fetchone()[0]
    log(f"  {n_events:,} events carry on-ice attribution.")

    # -----------------------------------------------------------------------
    # STEP 2: per-player-per-game on-ice aggregation (the big join).
    # -----------------------------------------------------------------------
    log("Aggregating on-ice xG for/against per player-game (large join)...")
    cur.executescript("""
        DROP TABLE IF EXISTS _onice_agg;
        CREATE TEMP TABLE _onice_agg AS
        SELECT o.game_id, o.player_id, o.team,
               SUM(CASE WHEN o.on_event_team = 1
                        THEN e.eff_xg / e.n_for     ELSE 0 END) AS xgf_adj,
               SUM(CASE WHEN o.on_event_team = 0
                        THEN e.eff_xg / e.n_against ELSE 0 END) AS xga_adj
        FROM on_ice_skaters o
        JOIN _event_val e
          ON e.game_id = o.game_id AND e.event_id = o.event_id
        GROUP BY o.game_id, o.player_id;
    """)

    # Individual xG per player-game (stored, not added -- see docstring).
    cur.executescript("""
        DROP TABLE IF EXISTS _ixg;
        CREATE TEMP TABLE _ixg AS
        SELECT game_id, shooter_id AS player_id, SUM(xg) AS ixg
        FROM shot_xg GROUP BY game_id, shooter_id;
    """)

    # -----------------------------------------------------------------------
    # STEP 3: the penalty value v, from regular-season data.
    # -----------------------------------------------------------------------
    log("Estimating the net goal value of a drawn penalty...")
    # Coincidental detection: two-or-more teams penalized at the identical
    # game clock instant -> offsetting, no power play, excluded.
    cur.executescript("""
        DROP TABLE IF EXISTS _pen_eligible;
        CREATE TEMP TABLE _pen_eligible AS
        SELECT p.game_id, p.event_id, p.period, p.time_in_period,
               p.committed_by_player_id, p.drawn_by_player_id
        FROM penalty_events p
        JOIN (SELECT game_id, period, time_in_period
              FROM penalty_events
              GROUP BY game_id, period, time_in_period
              HAVING COUNT(DISTINCT event_owner_team_id) = 1) ok
          ON ok.game_id = p.game_id AND ok.period = p.period
         AND ok.time_in_period = p.time_in_period
        WHERE CAST(p.duration_minutes AS INTEGER) < 10;
    """)
    n_pen_reg = cur.execute("""
        SELECT COUNT(*) FROM _pen_eligible pe
        JOIN games g ON g.game_id = pe.game_id
        WHERE CAST(g.game_type AS INTEGER) = 2""").fetchone()[0]
    ppg, shg = cur.execute("""
        SELECT SUM(CASE WHEN strength='PP' THEN is_goal ELSE 0 END),
               SUM(CASE WHEN strength='SH' THEN is_goal ELSE 0 END)
        FROM shot_xg WHERE game_type = 2""").fetchone()
    pen_value = (ppg - shg) / n_pen_reg
    log(f"  reg-season eligible penalties: {n_pen_reg:,}; PP goals {ppg:,}; "
        f"SH goals {shg:,}")
    log(f"  net goal value per drawn penalty v = {pen_value:.4f}")

    # Per-player per-game drawn/taken counts (all games; v applied flat).
    cur.executescript("""
        DROP TABLE IF EXISTS _pen_agg;
        CREATE TEMP TABLE _pen_agg AS
        SELECT game_id, player_id,
               SUM(drawn) AS pen_drawn, SUM(taken) AS pen_taken
        FROM (
            SELECT game_id, drawn_by_player_id AS player_id,
                   1 AS drawn, 0 AS taken
            FROM _pen_eligible WHERE drawn_by_player_id IS NOT NULL
            UNION ALL
            SELECT game_id, committed_by_player_id, 0, 1
            FROM _pen_eligible WHERE committed_by_player_id IS NOT NULL
        ) GROUP BY game_id, player_id;
    """)
    n_unattrib = cur.execute("""
        SELECT COUNT(*) FROM _pen_eligible
        WHERE committed_by_player_id IS NULL""").fetchone()[0]
    log(f"  penalties with no individual offender in the feed "
        f"(bench/team -- credited to no one): {n_unattrib:,}")

    # -----------------------------------------------------------------------
    # STEP 3.5: ORPHAN TRIPWIRE. The base-roster join below silently drops
    # any on-ice row whose (game, player) is missing from skater_games --
    # and "silently drops" is exactly how a 3-goal accounting leak hid during
    # development (traced to NHL feed corruption in 2 games: a foreign game's
    # shifts misfiled under one game id, and a shift-chart player absent from
    # the official box score; both now neutralized by Script 1's roster-truth
    # rule). This check makes any recurrence loud instead of silent.
    # -----------------------------------------------------------------------
    n_orphans = cur.execute("""
        SELECT COUNT(*) FROM
        (SELECT DISTINCT game_id, player_id FROM on_ice_skaters) o
        LEFT JOIN (SELECT DISTINCT CAST(game_id AS INTEGER) g,
                          CAST(player_id AS INTEGER) p FROM skater_games) s
          ON s.g = o.game_id AND s.p = o.player_id
        WHERE s.g IS NULL""").fetchone()[0]
    if n_orphans:
        log(f"*** WARNING: {n_orphans} on-ice player-games have no box-score "
            f"row and will be DROPPED by the roster join, leaking the "
            f"accounting identity. Re-run on_ice_reconstruction.py (with the "
            f"roster-truth rule) before trusting this output. ***")
    else:
        log("Orphan tripwire: 0 on-ice player-games missing from the box "
            "score. Roster join is leak-free.")

    # -----------------------------------------------------------------------
    # STEP 4: assemble. Base roster = skater_games (so a skater who dressed
    # but had no attributed events still gets a row, at zero) -- goalies are
    # excluded by construction (goalie pillar prices them separately).
    # -----------------------------------------------------------------------
    log("Assembling player_game_value...")
    cur.executescript(f"""
        DROP TABLE IF EXISTS player_game_value;
        CREATE TABLE player_game_value AS
        SELECT
            CAST(s.game_id AS INTEGER)        AS game_id,
            g.season                          AS season,
            CAST(g.game_type AS INTEGER)      AS game_type,
            g.game_date                       AS game_date,
            CAST(s.player_id AS INTEGER)      AS player_id,
            s.player_name                     AS player_name,
            s.team                            AS team,
            COALESCE(o.xgf_adj, 0.0)          AS onice_xgf_adj,
            COALESCE(o.xga_adj, 0.0)          AS onice_xga_adj,
            COALESCE(o.xgf_adj, 0.0)
              - COALESCE(o.xga_adj, 0.0)      AS onice_component,
            COALESCE(p.pen_drawn, 0)          AS pen_drawn,
            COALESCE(p.pen_taken, 0)          AS pen_taken,
            (COALESCE(p.pen_drawn, 0)
              - COALESCE(p.pen_taken, 0)) * {pen_value} AS penalty_component,
            COALESCE(o.xgf_adj, 0.0) - COALESCE(o.xga_adj, 0.0)
              + (COALESCE(p.pen_drawn, 0)
                 - COALESCE(p.pen_taken, 0)) * {pen_value} AS game_value,
            COALESCE(i.ixg, 0.0)              AS ixg
        FROM skater_games s
        JOIN games g ON g.game_id = s.game_id
        LEFT JOIN _onice_agg o
          ON o.game_id = CAST(s.game_id AS INTEGER)
         AND o.player_id = CAST(s.player_id AS INTEGER)
        LEFT JOIN _pen_agg p
          ON p.game_id = s.game_id AND p.player_id = s.player_id
        LEFT JOIN _ixg i
          ON i.game_id = CAST(s.game_id AS INTEGER)
         AND i.player_id = CAST(s.player_id AS INTEGER);
    """)
    conn.commit()
    n_rows = cur.execute("SELECT COUNT(*) FROM player_game_value").fetchone()[0]
    log(f"player_game_value written: {n_rows:,} skater-game rows.")

    # -----------------------------------------------------------------------
    # STEP 5A: accounting identity -- league sum of on-ice component ~ 0.
    # -----------------------------------------------------------------------
    ident = cur.execute(
        "SELECT SUM(onice_component) FROM player_game_value").fetchone()[0]
    log(f"[A] Accounting identity: league on-ice sum = {ident:+.6f} goals "
        f"(should be ~0 to machine precision).")

    # -----------------------------------------------------------------------
    # STEP 5B: team-game validation regression (regular season).
    # In-play goal differential (SO winner's +1 removed) on team metric sum.
    # -----------------------------------------------------------------------
    log("[B] Team-game validation regression (regular season)...")
    team_game = cur.execute("""
        SELECT v.game_id, v.team, SUM(v.game_value),
               g.away_team, g.home_team, g.away_score, g.home_score,
               g.last_period
        FROM player_game_value v
        JOIN games g ON g.game_id = v.game_id
        WHERE v.game_type = 2
        GROUP BY v.game_id, v.team""").fetchall()
    xs, ys = [], []
    for gid, team, metric, away, home, asc, hsc, lp in team_game:
        if asc is None or hsc is None:
            continue
        asc, hsc = int(asc), int(hsc)
        if lp == "SO":                       # strip the shootout winner's +1
            if asc > hsc: asc -= 1
            else: hsc -= 1
        diff = (hsc - asc) if team == home else (asc - hsc)
        xs.append(metric); ys.append(diff)
    X = np.column_stack([np.ones(len(xs)), np.array(xs)])
    y = np.array(ys, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot
    log(f"    team-games: {len(xs):,}; slope = {beta[1]:.3f}; "
        f"intercept = {beta[0]:+.3f}; R^2 = {r2:.3f}")
    log(f"    CONTEXT (benchmarked, not hand-waved): single-game xG is mostly "
        f"noise for EVERY model. MoneyPuck's public model -- which adds "
        f"pre-shot movement and speed features our feed does not contain -- "
        f"achieves corr(team-game xG, goals) of only 0.259 (R^2 ~ 0.07) on "
        f"its own shot files (2023-24, measured directly during development). "
        f"A slope below 1 here is attenuation: the metric is a noisy measure "
        f"of chance creation, which biases the fitted slope toward zero.")

    # ---- 5B-ii: SEASON-level regression -- the headline validation.
    # The paper's horizon is seasons, not single games; chance-quality signal
    # compounds where single-game shooting luck averages out.
    season_metric = defaultdict(float)
    season_diff = defaultdict(float)
    gid_season = {int(r[0]): str(r[1]) for r in cur.execute(
        "SELECT game_id, season FROM games")}
    per_game_diff = {}
    for gid, team, metric, away, home, asc, hsc, lp in team_game:
        if asc is None or hsc is None:
            continue
        a, h = int(asc), int(hsc)
        if lp == "SO":
            if a > h: a -= 1
            else: h -= 1
        diff = (h - a) if team == home else (a - h)
        key = (gid_season.get(int(gid), str(gid)[:4]), team)
        season_metric[key] += metric
        season_diff[key] += diff
    SM = np.array([season_metric[k] for k in season_metric])
    SD = np.array([season_diff[k] for k in season_metric])
    Xs = np.column_stack([np.ones(len(SM)), SM])
    bs, *_ = np.linalg.lstsq(Xs, SD, rcond=None)
    preds = Xs @ bs
    r2_season = 1 - float(np.sum((SD - preds) ** 2)) / float(np.sum((SD - SD.mean()) ** 2))
    log(f"    SEASON level (headline): {len(SM)} team-seasons; "
        f"slope = {bs[1]:.3f}; R^2 = {r2_season:.3f} -- the assembled metric "
        f"explains {r2_season*100:.0f}% of team-season goal differential, "
        f"fitted to nothing (validator, not weight source).")

    # -----------------------------------------------------------------------
    # STEP 5C: goals-per-win from team-seasons (regular season).
    # -----------------------------------------------------------------------
    log("[C] Goals-per-win from team-season totals (regular season)...")
    team_seasons = defaultdict(lambda: [0, 0])   # (season, team) -> [wins, diff]
    for gid, season, away, home, asc, hsc, lp in cur.execute("""
            SELECT game_id, season, away_team, home_team,
                   away_score, home_score, last_period
            FROM games WHERE CAST(game_type AS INTEGER) = 2"""):
        if asc is None or hsc is None:
            continue
        asc, hsc = int(asc), int(hsc)
        winner = home if hsc > asc else away
        a2, h2 = asc, hsc
        if lp == "SO":                        # in-play differential
            if asc > hsc: a2 -= 1
            else: h2 -= 1
        team_seasons[(season, home)][0] += 1 if winner == home else 0
        team_seasons[(season, home)][1] += h2 - a2
        team_seasons[(season, away)][0] += 1 if winner == away else 0
        team_seasons[(season, away)][1] += a2 - h2
    W = np.array([v[0] for v in team_seasons.values()], dtype=float)
    D = np.array([v[1] for v in team_seasons.values()], dtype=float)
    Xg = np.column_stack([np.ones(len(D)), D])
    bg, *_ = np.linalg.lstsq(Xg, W, rcond=None)
    goals_per_win = 1.0 / bg[1]
    log(f"    team-seasons: {len(W)}; wins-per-goal slope = {bg[1]:.4f} "
        f"-> goals per win = {goals_per_win:.2f}")

    # -----------------------------------------------------------------------
    # STEP 6: write validation CSV + runlog.
    # -----------------------------------------------------------------------
    val_path = OUT_DIR / "metric_validation.csv"
    with open(val_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["check", "value", "note"])
        w.writerow(["accounting_identity_league_sum", round(ident, 6),
                    "on-ice component sums to ~0 by construction"])
        w.writerow(["penalty_value_v_goals", round(pen_value, 4),
                    "net league goals per eligible drawn penalty"])
        w.writerow(["teamgame_regression_slope", round(float(beta[1]), 4),
                    "goals of outcome per goal of metric (expect ~1)"])
        w.writerow(["teamgame_regression_intercept", round(float(beta[0]), 4), ""])
        w.writerow(["teamgame_regression_r2", round(r2, 4),
                    "single-game horizon; MoneyPuck benchmark R^2 ~ 0.07"])
        w.writerow(["teamseason_regression_slope", round(float(bs[1]), 4), ""])
        w.writerow(["teamseason_regression_r2", round(r2_season, 4),
                    "HEADLINE validation: the paper's horizon"])
        w.writerow(["goals_per_win", round(goals_per_win, 3),
                    "from team-season wins vs in-play goal differential"])
        w.writerow(["team_games_in_regression", len(xs), ""])
    log(f"Validation summary written to {val_path}")

    (OUT_DIR / "metric_assembly_runlog.txt").write_text(
        "\n".join(RUNLOG) + "\n", encoding="utf-8")
    conn.close()
    log("Done.")


if __name__ == "__main__":
    main()
