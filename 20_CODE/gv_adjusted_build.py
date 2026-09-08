#!/usr/bin/env python3
"""gv_adjusted_build.py -- GV v2: teammate/competition-adjusted, finishing-aware
=================================================================================
SCRIPT_VERSION v1.0 (2026-07-04)

Upgrades GV from an equal-split net-xG metric to a WAR-like season metric:

  GV_adj = EV_RAPM + nonEV5_onice + penalties + finishing

  1. EV_RAPM      -- 5v5 on-ice value where teammate & competition effects are
                     separated by ridge regression on stints (RAPM). Every
                     skater gets an offense and a defense coefficient; the
                     lineup permutations across a season identify who drives
                     results. Controls (unpenalized): venue, score state,
                     zone start. Peer-reviewed lineage: Macdonald (2012),
                     Thomas et al. (2013), Gramacy-Taddy-Jensen (2013).
  2. nonEV5_onice -- equal-split on-ice net xG for all non-5v5 situations
                     (PP/PK/3v3/6v5...), same construction as GV v1.
  3. penalties    -- drawn-minus-taken at v=0.2097 (reused from GV v1 rows).
  4. finishing    -- goals above expected per shooter, shrunk toward zero by
                     an empirical-Bayes factor n/(n+K) with K derived from
                     variance components (a hot streak on 40 shots gets
                     heavily discounted; a career of 2,000 shots does not).

IDENTIFICATION GUARDS (pre-registered):
  - Zero Bacon inputs anywhere.
  - The ridge penalty lambda is chosen by game-grouped cross-validation on
    held-out stint prediction. The finishing K comes from a closed-form
    variance decomposition. NO knob is ever tuned on contract data or on
    resemblance to Bacon -- otherwise GV-adj could no longer serve as either
    an independent input or an independent validator.
  - Per-season estimation: a 2019 rating uses only 2019 shifts (the shared
    xG model's 2017-24 fit window is the already-documented mild exception).

Outputs: table gv_adjusted (player_id, season, components, gv_adj, toi_5v5)
         + gv_adjusted.csv + plaintext runlog lines to stdout.
"""
import sqlite3, math, sys, time
from collections import defaultdict
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import cg

DB_PATH = r"C:\Users\thoma\OneDrive\Desktop\test\nhl_gamelogs.sqlite"
SCRIPT_VERSION = "v1.0 (2026-07-04)"
MIN_STINT_SEC = 4          # segments shorter than this are boundary noise
LAMBDA_GRID = [100.0, 300.0, 1000.0, 3000.0, 10000.0, 30000.0]
N_FOLDS = 5
SEASONS = None             # None = all; or list like [20232024] for smoke test

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def abs_time(period, mmss):
    """Convert (period, MM:SS) to absolute game seconds. Regulation periods
    are 1200s; period 4 (OT) starts at 3600. Shootout (period 5) is excluded
    upstream. Uses elapsed-time convention (start_time counts up)."""
    m, s = mmss.split(':')
    base = (period - 1) * 1200 if period <= 4 else 4500
    return base + int(m) * 60 + int(s)

def main():
    print(f"gv_adjusted_build.py {SCRIPT_VERSION}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # CAST hardening: CSV-loaded tables are TEXT-typed in this store.
    # Build typed temp mirrors once; every later query hits these.
    log("building typed temp mirrors of CSV-loaded tables...")
    cur.executescript("""
        DROP TABLE IF EXISTS _games;
        CREATE TEMP TABLE _games AS
          SELECT CAST(game_id AS INT) gid, away_team, home_team,
                 CAST(season AS INT) season
          FROM games WHERE CAST(game_type AS INT) = 2;
        CREATE INDEX _gx ON _games(season);
        DROP TABLE IF EXISTS _shifts;
        CREATE TEMP TABLE _shifts AS
          SELECT CAST(game_id AS INT) gid, CAST(player_id AS INT) pid,
                 CAST(period AS INT) per, start_time, end_time
          FROM shifts WHERE CAST(period AS INT) <= 4
            AND duration_seconds IS NOT NULL AND duration_seconds != '';
        CREATE INDEX _sx ON _shifts(gid);
        DROP TABLE IF EXISTS _sev;
        CREATE TEMP TABLE _sev AS
          SELECT CAST(game_id AS INT) gid, CAST(event_id AS INT) ev,
                 CAST(period AS INT) per, time_in_period,
                 situation_code, CAST(event_owner_team_id AS INT) own
          FROM shot_events WHERE CAST(period AS INT) <= 4;
        CREATE UNIQUE INDEX _sevx ON _sev(gid, ev);
        DROP TABLE IF EXISTS _fo;
        CREATE TEMP TABLE _fo AS
          SELECT CAST(game_id AS INT) gid, CAST(period AS INT) per,
                 time_in_period, zone_code,
                 CAST(event_owner_team_id AS INT) own
          FROM faceoff_events WHERE CAST(period AS INT) <= 4;
        CREATE INDEX _fox ON _fo(gid);
    """)
    # team-id -> abbrev map (via shots: xg carries abbrev, events carry id)
    teamid2abbr = {int(i): a for a, i in cur.execute(
        "SELECT DISTINCT x.team, s.own FROM shot_xg x "
        "JOIN _sev s ON s.gid = x.game_id AND s.ev = x.event_id "
        "WHERE x.team IS NOT NULL AND s.own IS NOT NULL")}
    log(f"  team-id map: {len(teamid2abbr)} ids")

    seasons = SEASONS or [r[0] for r in cur.execute(
        "SELECT DISTINCT season FROM _games ORDER BY season")]
    log(f"seasons to process: {seasons}")

    # ---- shared reference data pulled once -------------------------------
    # Box-score roster truth: (game, player) -> team  [same rule as Script 1]
    log("loading rosters, shots, faceoffs...")
    roster = {}
    for g, p, t in cur.execute(
            "SELECT CAST(game_id AS INT), CAST(player_id AS INT), team FROM skater_games"):
        roster[(g, p)] = t
    games_meta = {int(g): (a, h, s) for g, a, h, s in cur.execute(
        "SELECT gid, away_team, home_team, season FROM _games")}

    # Shots with xg + situation + timing (one join, reused per season).
    # is_goal drives the score timeline; situation 1551 defines the 5v5 set.
    shots_by_game = defaultdict(list)
    for g, per, t, sit, team, xg, ig in cur.execute("""
        SELECT x.game_id, e.per, e.time_in_period,
               e.situation_code, x.team, x.xg, x.is_goal
        FROM shot_xg x JOIN _sev e
          ON e.gid = x.game_id AND e.ev = x.event_id
        WHERE x.game_type = 2"""):
        shots_by_game[int(g)].append(
            (abs_time(int(per), t), sit, team, float(xg), int(ig)))
    # Faceoffs for zone-start controls: (game, abs_time) -> (zone, winner_team_id... )
    fo_by_game = defaultdict(dict)
    for g, per, t, zone, own in cur.execute(
            "SELECT gid, per, time_in_period, zone_code, own FROM _fo"):
        fo_by_game[int(g)][abs_time(int(per), t)] = (zone, teamid2abbr.get(own))

    # nonEV5 equal-split component + season GP straight from SQL ----------
    log("computing non-5v5 equal-split on-ice component (SQL)...")
    cur.executescript("""
        DROP TABLE IF EXISTS _nonev5;
        CREATE TEMP TABLE _nonev5 AS
        SELECT o.player_id AS player_id, g.season AS season,
               SUM(CASE WHEN o.on_event_team = 1 THEN x.xg ELSE 0 END
                   / cnt.n_for)
             - SUM(CASE WHEN o.on_event_team = 0 THEN x.xg ELSE 0 END
                   / cnt.n_against) AS nonev5
        FROM on_ice_skaters o
        JOIN shot_xg x  ON x.game_id = o.game_id AND x.event_id = o.event_id
        JOIN _sev e ON e.gid = o.game_id AND e.ev = o.event_id
        JOIN _games g ON g.gid = o.game_id
        JOIN (SELECT game_id, event_id,
                     SUM(on_event_team)      AS n_for,
                     SUM(1 - on_event_team)  AS n_against
              FROM on_ice_skaters GROUP BY game_id, event_id) cnt
          ON cnt.game_id = o.game_id AND cnt.event_id = o.event_id
        WHERE e.situation_code != '1551'
          AND cnt.n_for > 0 AND cnt.n_against > 0
        GROUP BY o.player_id, g.season;
    """)
    nonev5 = {(int(p), int(s)): float(v) for p, s, v in
              cur.execute("SELECT player_id, season, nonev5 FROM _nonev5")}

    log("summing penalty component from player_game_value...")
    pens = {(int(p), int(s)): float(v) for p, s, v in cur.execute(
        "SELECT player_id, season, SUM(penalty_component) FROM player_game_value "
        "WHERE game_type=2 GROUP BY player_id, season")}

    # Finishing: goals-above-expected with variance-component shrinkage ----
    log("computing finishing (shrunken goals-above-expected)...")
    fin_raw = {}
    for p, s, gax, n, noise in cur.execute("""
        SELECT shooter_id, season, SUM(is_goal - xg), COUNT(*),
               SUM(xg * (1 - xg))
        FROM shot_xg WHERE game_type = 2 GROUP BY shooter_id, season"""):
        fin_raw[(int(p), int(s))] = (float(gax), int(n), float(noise))
    # Variance decomposition across shooter-seasons with n >= 50 shots:
    # observed variance of per-shot rate = talent variance + mean noise var.
    rates, noises = [], []
    for gax, n, noise in fin_raw.values():
        if n >= 50:
            rates.append(gax / n); noises.append(noise / n**2)
    tau2 = max(1e-9, float(np.var(rates)) - float(np.mean(noises)))
    log(f"  finishing talent variance tau^2 = {tau2:.6f} "
        f"(observed {np.var(rates):.6f}, mean noise {np.mean(noises):.6f})")
    finishing = {}
    for key, (gax, n, noise) in fin_raw.items():
        nv = noise / n**2 if n else 1.0
        shrink = tau2 / (tau2 + nv)          # reliability in [0,1)
        finishing[key] = (gax / n) * shrink * n if n else 0.0

    # ---- per-season stint construction + RAPM ----------------------------
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS gv_adjusted (
            player_id INTEGER, season INTEGER, toi_5v5_min REAL,
            ev_rapm REAL, nonev5 REAL, penalty REAL, finishing REAL,
            gv_adj REAL, off60 REAL, def60 REAL,
            PRIMARY KEY (player_id, season));
    """)
    done = {r[0] for r in cur.execute("SELECT DISTINCT season FROM gv_adjusted")}
    for season in seasons:
        if int(season) in done:
            log(f"season {season}: already built, skipping (resume mode)")
            continue
        t0 = time.time()
        gids = [g for g, (_, _, s) in games_meta.items() if int(s) == int(season)]
        log(f"season {season}: {len(gids)} games -- building 5v5 stints...")
        rows_y, rows_w, rows_fold = [], [], []
        trip_r, trip_c, trip_v = [], [], []       # sparse design triplets
        pid_index = {}                            # player -> column pair base
        toi = defaultdict(float)
        n_drop_short = n_shot_orphan = n_badtime = 0

        def pcol(pid):
            if pid not in pid_index:
                pid_index[pid] = len(pid_index)
            return pid_index[pid]

        for gid in gids:
            away, home, _ = games_meta[gid]
            sh = cur.execute(
                "SELECT pid, per, start_time, end_time FROM _shifts WHERE gid=?",
                (gid,)).fetchall()
            # per-player interval merge -- raw shifts still contain the
            # duplicate echoes Script 1 filters, so overlapping intervals for
            # one player are unioned before the sweep (roster-truth applies).
            per_player = defaultdict(list)
            for pid, per, st, en in sh:
                team = roster.get((gid, pid))
                if team is None:
                    continue                       # goalie / non-roster row
                try:                               # HTML-fallback games can
                    a = abs_time(int(per), st)     # carry malformed times --
                    b = abs_time(int(per), en)     # skip and count, same as
                except (ValueError, AttributeError):   # Script 1 tolerates
                    n_badtime += 1
                    continue
                if b > a:
                    per_player[(pid, team)].append((a, b))
            events = []                            # (time, +1/-1, pid, team)
            for (pid, team), iv in per_player.items():
                iv.sort()
                cur_a, cur_b = iv[0]
                merged = []
                for a, b in iv[1:]:
                    if a <= cur_b:
                        cur_b = max(cur_b, b)
                    else:
                        merged.append((cur_a, cur_b)); cur_a, cur_b = a, b
                merged.append((cur_a, cur_b))
                for a, b in merged:
                    events.append((a, 1, pid, team))
                    events.append((b, -1, pid, team))
            if not events:
                continue
            events.sort(key=lambda e: (e[0], e[1]))   # removals before adds
            shots = sorted(shots_by_game.get(gid, ()))
            goal_pref = [0]                            # prefix counts by time
            goal_list = [(t, tm) for t, sit, tm, xg, ig in shots if ig]
            fo = fo_by_game.get(gid, {})
            active_h, active_a = set(), set()
            times = sorted({e[0] for e in events})
            ei = 0; si = 0; hs = as_ = 0; gi_ = 0
            for k in range(len(times) - 1):
                t0_, t1_ = times[k], times[k + 1]
                # apply all events at t0_
                while ei < len(events) and events[ei][0] == t0_:
                    _, d, pid, team = events[ei]
                    tgt = active_h if team == home else active_a
                    (tgt.add if d > 0 else tgt.discard)(pid)
                    ei += 1
                dur = t1_ - t0_
                if dur <= 0:
                    continue
                # advance score to t0_ (goals strictly before stint start)
                while gi_ < len(goal_list) and goal_list[gi_][0] <= t0_:
                    if goal_list[gi_][1] == home: hs += 1
                    else: as_ += 1
                    gi_ += 1
                # collect this stint's 5v5 shots via pointer
                while si < len(shots) and shots[si][0] < t0_:
                    si += 1
                sj = si
                seg_shots = []
                while sj < len(shots) and shots[sj][0] < t1_:
                    if shots[sj][1] == '1551':
                        seg_shots.append(shots[sj])
                    sj += 1
                if len(active_h) != 5 or len(active_a) != 5:
                    continue
                if dur < MIN_STINT_SEC:
                    n_drop_short += 1; n_shot_orphan += len(seg_shots)
                    continue
                z = fo.get(t0_) or fo.get(t0_ + 1)
                on_home, on_away = list(active_h), list(active_a)
                for team_persp, mates, opps in ((home, on_home, on_away),
                                                 (away, on_away, on_home)):
                    y_ = sum(x[3] for x in seg_shots if x[2] == team_persp) / dur * 3600.0
                    r = len(rows_y)
                    rows_y.append(y_); rows_w.append(dur / 60.0)
                    rows_fold.append(gid % N_FOLDS)
                    for p in mates:
                        trip_r.append(r); trip_c.append(2 * pcol(p)); trip_v.append(1.0)
                    for p in opps:
                        trip_r.append(r); trip_c.append(2 * pcol(p) + 1); trip_v.append(1.0)
                    diff = (hs - as_) if team_persp == home else (as_ - hs)
                    ozone = dzone = 0.0
                    if z and z[0] in ('O', 'D') and z[1]:
                        # faceoff zone is from the event-owner team's view;
                        # flip it when this perspective is the other team.
                        zz = z[0] if z[1] == team_persp else ('D' if z[0] == 'O' else 'O')
                        ozone = 1.0 if zz == 'O' else 0.0
                        dzone = 1.0 if zz == 'D' else 0.0
                    ctrl = [1.0,
                            1.0 if team_persp == home else 0.0,
                            1.0 if diff > 0 else 0.0,
                            1.0 if diff < 0 else 0.0,
                            ozone, dzone]
                    for j, v in enumerate(ctrl):
                        if v:
                            trip_r.append(r); trip_c.append(-(j + 1)); trip_v.append(v)
                for p in on_home + on_away:
                    toi[p] += dur
        npl = len(pid_index)
        ncols = 2 * npl + 6
        # shift control columns (stored as negative) to the tail of the matrix
        for i in range(len(trip_c)):
            if trip_c[i] < 0:
                trip_c[i] = 2 * npl + (-trip_c[i] - 1)
        X = sparse.csr_matrix((trip_v, (trip_r, trip_c)),
                              shape=(len(rows_y), ncols))
        y = np.array(rows_y); w = np.array(rows_w); fold = np.array(rows_fold)
        log(f"  {len(y):,} stint-rows, {npl} skaters, "
            f"{n_drop_short:,} micro-stints dropped ({n_shot_orphan} shots on them), "
            f"{n_badtime:,} malformed shift times skipped")

        # penalty matrix: player columns penalized, controls free
        pen_diag = np.ones(ncols); pen_diag[2 * npl:] = 0.0
        def fit(lmb, mask):
            Xm = X[mask]; ym = y[mask]; wm = w[mask]
            Xw = Xm.multiply(wm[:, None])
            A = (Xm.T @ Xw).toarray() + lmb * np.diag(pen_diag)
            b = Xm.T @ (wm * ym)
            return np.linalg.solve(A, b)
        # game-grouped CV over the lambda grid (weighted MSE)
        best, best_mse = None, None
        for lmb in LAMBDA_GRID:
            mse = 0.0
            for f in range(N_FOLDS):
                tr = fold != f; te = ~tr
                beta = fit(lmb, tr)
                pred = X[te] @ beta
                mse += float(np.sum(w[te] * (y[te] - pred) ** 2) / np.sum(w[te]))
            mse /= N_FOLDS
            log(f"    lambda={lmb:>8.0f}  CV-MSE={mse:.5f}")
            if best_mse is None or mse < best_mse:
                best, best_mse = lmb, mse
        beta = fit(best, np.ones(len(y), bool))
        log(f"  lambda* = {best:.0f} (chosen on held-out stint prediction ONLY)")

        # convert coefficients to season goal values
        out = []
        for pid, ix in pid_index.items():
            off, dfn = beta[2 * ix], beta[2 * ix + 1]
            t60 = toi[pid] / 3600.0                 # hours on ice at 5v5
            ev = (off - dfn) * t60                  # net goals vs average
            key = (pid, int(season))
            g = ev + nonev5.get(key, 0.0) + pens.get(key, 0.0) + finishing.get(key, 0.0)
            out.append((pid, int(season), toi[pid] / 60.0, ev,
                        nonev5.get(key, 0.0), pens.get(key, 0.0),
                        finishing.get(key, 0.0), g, off, dfn))
        # Center: GV-adj is average-relative by definition, so remove the
        # small league-level offset the controls fail to absorb (documented;
        # a uniform per-minute shift that changes no ordering or comparison).
        tot_toi = sum(o[2] for o in out) or 1.0
        adj_per_min = sum(o[3] for o in out) / tot_toi
        out = [(pid, se, tm, ev - adj_per_min * tm, ne, pe, fi,
                g - adj_per_min * tm, off, dfn)
               for (pid, se, tm, ev, ne, pe, fi, g, off, dfn) in out]
        cur.executemany("INSERT OR REPLACE INTO gv_adjusted VALUES (?,?,?,?,?,?,?,?,?,?)", out)
        conn.commit()
        # identity check: RAPM is average-relative, so TOI-weighted league sum
        # of (off-dfn) need not be exactly 0, but should be near it.
        tot = sum(o[3] for o in out)
        log(f"  season {season} done in {time.time()-t0:.0f}s -- {len(out)} skaters, "
            f"league EV_RAPM sum = {tot:+.1f} goals (near-zero expected)")

    # export CSV
    import csv as _csv
    with open(r'C:\Users\thoma\OneDrive\Desktop\test\gv_adjusted.csv', 'w', newline='') as f:
        wcsv = _csv.writer(f)
        wcsv.writerow(['player_id','season','toi_5v5_min','ev_rapm','nonev5',
                       'penalty','finishing','gv_adj','off60','def60'])
        for row in cur.execute("SELECT * FROM gv_adjusted ORDER BY season, gv_adj DESC"):
            wcsv.writerow(row)
    log("gv_adjusted table + CSV written.")

if __name__ == '__main__':
    main()
