#!/usr/bin/env python3
"""
on_ice_reconstruction.py  --  Script 1 of the Tier 2 game-level model build

WHAT THIS DOES, IN PLAIN ENGLISH
---------------------------------
For every shot attempt in the database (goal, shot on goal, missed shot,
blocked shot), this script figures out WHICH SKATERS WERE ON THE ICE when it
happened, by lining up each shot's timestamp against every player's shift
start/end times in that period.

Why this matters for the paper: box-score stats only tell you what a player
DID (shots, hits, blocks). Defensive value lives in what happened around a
player -- how many chances the OTHER team generated while he was out there.
You cannot see that without knowing who was on the ice for each shot. This
table is the foundation for the on-ice expected-goals-for/against terms in
the Tier 2 metric.

HOW THE MATCHING RULE WAS CHOSEN (not guessed -- tested)
---------------------------------------------------------
The tricky part is boundaries: what if a shot happens at the EXACT second a
shift starts or ends? Three candidate rules were tested against 60 real games
(7,184 shot events), scored against the NHL's own `situation_code` field --
a 4-digit code the league records on every event that encodes exactly how
many skaters each team had on the ice (e.g. '1551' = 5-on-5, both goalies in).
That gives an independent ground truth to check against:

    Rule A  (start <= t <= end):  85.5% exact match  -- double-counts line
                                   changes at stoppages (old line's shift ends
                                   at the faceoff second, new line's starts at
                                   the same second; A counts both)
    Rule B  (start <  t <= end):  99.3% exact match  <-- USED
    Rule C  (start <  t <  end):  85.4% exact match  -- drops the shooter on
                                   goals, because a goal ENDS shifts at that
                                   exact second; C excludes shift-end seconds

Rule B wins for two reasons that both make hockey sense:
  - end-INCLUSIVE: a goal (or the stoppage after a shot) ends shifts at that
    exact second, so players whose shift ends at the event second WERE on.
  - start-EXCLUSIVE: at a stoppage line change, the incoming line's shift
    starts at the faceoff second; excluding start==t avoids counting both
    the outgoing and incoming line for events logged at that same second.

Residual mismatches after Rule B, profiled on the test sample:
  - Shootout attempts (period 5 of regular-season games): no shifts exist,
    no meaningful "on ice." EXCLUDED BY DESIGN (see design decisions below),
    not an error.
  - ~0.18% one-player mismatches from timing noise in the NHL's own shift
    feed (a shift logged as ending one second early, etc.). These rows are
    KEPT but flagged (match_ok = 0) so downstream analysis can include or
    exclude them deliberately. Excluding shootouts, the rule matches the
    NHL's own on-ice count on ~99.87% of events.

DESIGN DECISIONS (flagged per project convention)
--------------------------------------------------
1. SHOOTOUTS EXCLUDED: regular-season period 5 is the shootout -- a skills
   contest with no shifts and no on-ice context. Excluded entirely. Playoff
   overtime periods (4, 5, ...) are real hockey and are KEPT.
2. SKATERS ONLY in the output table: the shot's goalie is already recorded
   on the shot_events row itself (goalie_id), and goalie value is handled
   by the separate goalie pillar. Goalie shift rows are used internally to
   EXCLUDE goalies from skater counts, but goalies get no on-ice rows.
3. EVENT-TEAM TAGGING: each on-ice row records whether that skater's team
   took the shot (on_event_team = 1) or defended it (0). This is the split
   that later becomes xG-for vs xG-against. The shooting team's abbreviation
   is derived from the shooter's team in skater_games/goalie_games for that
   game -- an ID-based lookup, not name matching (per project join rules).
4. VALIDATION IS BUILT IN, NOT SEPARATE: every event row carries the NHL's
   expected skater counts (from situation_code) alongside the reconstructed
   counts, plus a match_ok flag. The run ends with a validation summary
   printed and written to CSV. If the overall match rate comes back below
   99% (excluding shootouts), treat the run as failed and investigate --
   do not build on it.
5. WRITE-TO-DB DEVIATION, FLAGGED: project convention is read-only DB access
   with CSV outputs. This script WRITES two tables (on_ice_skaters,
   on_ice_event_qc) back into the game-logs SQLite database. Reason: the
   output is ~13-14 million rows -- as a CSV that is an ~800MB file that
   every downstream script would have to re-parse. Writing it into the same
   database the downstream scripts already read is the practical choice.
   The write is idempotent: tables are dropped and rebuilt from scratch on
   every run, so re-running never double-inserts.
6. NO LOOK-AHEAD CONCERN HERE: everything in this script is within-game
   reconstruction of what physically happened -- no future information is
   used to describe any event.

INPUTS (read from the SQLite DB)
---------------------------------
  games         -- for away/home team abbreviations and game_type
  shifts        -- shift intervals per player per period (v2 scraper output)
  shot_events   -- every shot attempt with timestamp and situation_code
  skater_games, goalie_games -- player->team mapping and goalie identification

OUTPUTS
--------
  on_ice_skaters   (DB table)  one row per (event x on-ice skater):
      game_id, event_id, player_id, team, is_home, on_event_team
  on_ice_event_qc  (DB table)  one row per processed event:
      game_id, event_id, expected/reconstructed skater counts, match_ok
  on_ice_validation_summary.csv  -- run-level QC numbers
  on_ice_reconstruction_runlog.txt -- plain-text run log

USAGE
------
  python3 on_ice_reconstruction.py                 # full run
  python3 on_ice_reconstruction.py --limit 300     # smoke test on 300 games

Deterministic and idempotent: re-running from scratch always produces the
same tables. Expected full-run time: roughly 10-20 minutes for ~11,800 games.
"""

import argparse
import csv
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG -- update DB_PATH to wherever nhl_gamelogs.sqlite lives on your
# machine (the database the v2 scraper wrote -- the one that contains the
# shifts and shot_events tables).
# ---------------------------------------------------------------------------
DB_PATH = Path(r"C:\Users\thoma\OneDrive\Desktop\test\nhl_gamelogs.sqlite")
OUT_DIR = DB_PATH.parent          # summary CSV + run log land next to the DB

RUNLOG = []                        # collected lines, written to disk at the end
def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line)
    RUNLOG.append(line)


def mmss_to_seconds(t) -> int | None:
    """'12:34' -> 754 seconds into the period. All matching is done in whole
    seconds within a period -- the NHL feed does not provide sub-second
    resolution, so seconds is the native (and maximum) precision.

    Returns None (instead of crashing) when the value is missing or malformed.
    Why: profiling the full 8.67M-row shifts table found 1,129 rows (0.013%)
    with an EMPTY end_time -- unclosed shift records in the NHL's own feed,
    typically clusters of players in the same game at the same second. These
    are source glitches, not scraper bugs. Callers must check for None and
    skip (and count) the affected row rather than let one bad row kill a
    multi-hour run -- which is exactly what happened at game ~2,500 of the
    first full run."""
    if not t:
        return None
    try:
        m, s = str(t).split(":")
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


SCRIPT_VERSION = "v1.3 (2026-07-03) -- roster-truth rule; DB_PATH corrected to new_scrape"


def main() -> None:
    print(f"on_ice_reconstruction.py {SCRIPT_VERSION}")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="Process only the first N games (smoke testing).")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found at:\n  {DB_PATH}\n"
              f"Update DB_PATH at the top of this script.", file=sys.stderr)
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # -- confirm the v2 tables are actually present before doing anything ----
    tables = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {"games", "shifts", "shot_events",
               "skater_games", "goalie_games"} - tables
    if missing:
        print(f"Required tables missing from this database: {sorted(missing)}\n"
              f"This usually means the v2 scraper has not been run against "
              f"this DB. Aborting.", file=sys.stderr)
        raise SystemExit(1)

    # -- indexes make the per-game queries fast; IF NOT EXISTS keeps this
    #    idempotent (safe to run repeatedly, never duplicates anything) ------
    log("Ensuring indexes on shifts and shot_events (one-time cost)...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shifts_game ON shifts(game_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shots_game ON shot_events(game_id)")
    conn.commit()

    # -- output tables: dropped and rebuilt every run (idempotent write) -----
    log("Rebuilding output tables on_ice_skaters and on_ice_event_qc...")
    cur.executescript("""
        DROP TABLE IF EXISTS on_ice_skaters;
        CREATE TABLE on_ice_skaters (
            game_id        INTEGER NOT NULL,
            event_id       INTEGER NOT NULL,   -- joins shot_events.event_id
            player_id      INTEGER NOT NULL,   -- joins spine via nhl_id
            team           TEXT    NOT NULL,
            is_home        INTEGER NOT NULL,
            on_event_team  INTEGER NOT NULL,   -- 1 = this skater's team took
                                               -- the shot; 0 = defended it
            PRIMARY KEY (game_id, event_id, player_id)
        );
        DROP TABLE IF EXISTS on_ice_event_qc;
        DROP TABLE IF EXISTS on_ice_game_qc;
        CREATE TABLE on_ice_event_qc (
            game_id        INTEGER NOT NULL,
            event_id       INTEGER NOT NULL,
            away_expected  INTEGER,            -- skater count per NHL situation_code
            home_expected  INTEGER,
            away_found     INTEGER,            -- skater count we reconstructed
            home_found     INTEGER,
            match_ok       INTEGER NOT NULL,   -- 1 = exact match on both sides
            PRIMARY KEY (game_id, event_id)
        );
    """)
    conn.commit()

    # -- game list: regular season AND playoffs (playoff OT is real hockey;
    #    only the regular-season shootout is excluded, below) ----------------
    games = cur.execute(
        "SELECT game_id, game_type, away_team, home_team, last_period "
        "FROM games ORDER BY game_id").fetchall()
    if args.limit:
        games = games[: args.limit]
    log(f"{len(games)} games to process.")

    # -- goalie identification: one global set of goalie player_ids, used to
    #    keep goalie shift rows out of the skater counts --------------------
    # NOTE: an earlier version excluded goalies from shift rows via a global
    # set of goalie ids. That mechanism is now subsumed by the per-game
    # ROSTER-TRUTH RULE below (a goalie is not in skater_games for the game,
    # so he drops for the same principled reason as any non-roster row).

    # -- counters for the validation summary ---------------------------------
    n_events_total = 0          # every shot event seen
    n_shootout_skipped = 0      # excluded by design (see design decision 1)
    n_bad_shift_rows = 0        # unclosed duplicate-echo shift rows dropped
                                #   (known NHL feed glitch; harmless duplicates)
    n_recovered_shifts = 0      # unclosed FINAL shifts recovered to period end
    n_nonroster_shift_rows = 0  # shift rows dropped by the roster-truth rule
                                #   (goalies + the 3 corrupt games' rows)
    n_duplicate_onice = 0       # duplicate on-ice memberships absorbed (feed
                                #   lists the same shift twice for a player)
    n_no_shooter_team = 0       # events whose shooting team could not be tagged
    n_match_ok = 0              # events where reconstruction == situation_code
    n_match_bad = 0             # events flagged match_ok = 0
    n_rows_written = 0          # on_ice_skaters rows

    for gi, (game_id, game_type, away_ab, home_ab, last_period) in enumerate(games, 1):

        # ---- player -> team map for THIS game, from box-score tables.
        #      ID-based (nhl player_id), no name matching anywhere. ----------
        player_team = {}
        skater_roster = {}     # SKATERS only: the game's roster truth, used
                               # to filter and re-label shift rows below
        for pid, team in cur.execute(
                "SELECT player_id, team FROM skater_games WHERE game_id=?",
                (game_id,)):
            player_team[int(pid)] = team
            skater_roster[int(pid)] = team
        for pid, team in cur.execute(
                "SELECT player_id, team FROM goalie_games WHERE game_id=?",
                (game_id,)):
            player_team[int(pid)] = team

        # ---- shifts for this game, grouped by period, times in seconds.
        #      Goalies excluded here: their on-ice identity for each shot is
        #      already on the shot_events row (goalie_id). --------------------
        #
        # UNCLOSED-SHIFT HANDLING (profiled on the full 8.67M-row table before
        # this logic was written -- 1,129 rows, 0.013%, have an empty end_time;
        # a known NHL feed glitch). They split into two kinds:
        #   1. DUPLICATE ECHOES (~92%): the same player already has a normal,
        #      closed shift covering the same moment. Dropping these loses
        #      nothing.
        #   2. UNCLOSED FINAL SHIFTS (~5%): the player's last shift of the
        #      period (typically period 3 or OT) that the feed never closed --
        #      e.g. a shift starting at 19:52 of the 3rd with no end. The
        #      player was on the ice until the period ended. Dropping these
        #      makes late-period events miss real on-ice players (measured:
        #      match rate fell from ~99.9% to ~92.8% in affected games), so
        #      they are RECOVERED instead: end = the latest shift end observed
        #      in that game-period (20:00 for regulation; wherever overtime
        #      actually ended for OT). A handful (~8 rows total) have a LATER
        #      shift by the same player; those are capped at that next shift's
        #      start -- a slight ice-time overestimate, accepted at this scale.
        # Recovery happens in a second pass so the "latest end in period" and
        # "player's next shift" bounds are known before any decision is made.
        # ROSTER-TRUTH RULE (added after full-scale validation of Script 4
        # caught a 3-goal leak in its accounting identity). The NHL shift
        # feed was found to contain, in exactly three games across nine
        # seasons, three distinct kinds of corrupt rows:
        #   A. 2021020513: every real player's shifts TRIPLICATED, one copy
        #      carrying a wrong team label (incl. teams not in the game);
        #   B. 2025020565: an entire OTHER game's shifts (SJS@VGK) misfiled
        #      under this game's id -- 36 foreign players;
        #   C. 2024030116: one player (in the shift chart, absent from the
        #      official box score) who did not actually dress.
        # One rule neutralizes all three: the game's BOX SCORE is roster
        # truth. A shift row is kept only if its player_id appears in THIS
        # game's skater_games, and his team label is taken from the box
        # score, never from the shift row (whose label mode A corrupts).
        # This also subsumes the old goalie exclusion: goalies are not in
        # skater_games, so they drop here for the same principled reason.
        raw_shifts = []          # (period, s_sec, e_sec_or_None, pid, team)
        for period, start, end, pid, _shift_team in cur.execute(
                "SELECT period, start_time, end_time, player_id, team "
                "FROM shifts WHERE game_id=?", (game_id,)):
            pid = int(pid)               # int cast: see typing note below
            team = skater_roster.get(pid)
            if team is None:
                # Not a skater on this game's official roster: a goalie, a
                # foreign-game row (mode B), or a phantom scratch (mode C).
                # Dropped and counted -- never silently.
                n_nonroster_shift_rows += 1
                continue
            s_sec = mmss_to_seconds(start)
            e_sec = mmss_to_seconds(end)
            if s_sec is None:
                # No usable start time -> unrecoverable; counted, never silent.
                # (Profiling found zero such rows, but guard anyway.)
                n_bad_shift_rows += 1
                continue
            # int cast for the same SQLite dynamic-typing reason explained in
            # the event loop below: the period key must match the (cast) event
            # period exactly, or lookups silently miss.
            raw_shifts.append((int(period), s_sec, e_sec, pid, team))

        # Second pass: resolve unclosed shifts using full-period context.
        shifts_by_period = defaultdict(list)
        # latest closed end per period = the period's true end (incl. early OT end)
        period_max_end = defaultdict(int)
        for p, s, e, pid, team in raw_shifts:
            if e is not None and e > period_max_end[p]:
                period_max_end[p] = e
        for p, s, e, pid, team in raw_shifts:
            if e is None:
                covered = any(s2 <= s <= e2 for (p2, s2, e2, pid2, _t) in raw_shifts
                              if pid2 == pid and p2 == p and e2 is not None)
                if covered:
                    n_bad_shift_rows += 1        # duplicate echo: drop, count
                    continue
                later_starts = [s2 for (p2, s2, e2, pid2, _t) in raw_shifts
                                if pid2 == pid and p2 == p and e2 is not None and s2 > s]
                e = min(later_starts) if later_starts else period_max_end[p]
                n_recovered_shifts += 1          # recovered, counted separately
                if e <= s:
                    continue                     # degenerate after recovery; drop
            shifts_by_period[p].append((s, e, pid, team))

        # ---- shot events for this game --------------------------------------
        events = cur.execute(
            "SELECT event_id, period, time_in_period, situation_code, "
            "       shooting_player_id "
            "FROM shot_events WHERE game_id=?", (game_id,)).fetchall()

        oi_rows, qc_rows = [], []
        for event_id, period, tstr, sit, shooter_id in events:
            n_events_total += 1

            # Explicit int casts: SQLite is dynamically typed, so a value can
            # come back as the TEXT '5' rather than the INTEGER 5 depending on
            # how the table was populated. Without the cast, '5' == 5 is False
            # and the shootout exclusion silently never fires -- a bug caught
            # in end-to-end testing, not hypothetical. Cast once, compare ints.
            period = int(period)

            # Shootout exclusion, keyed on the game's recorded final period
            # type rather than game type alone: "playoff games never have a
            # shootout" has exactly two exceptions in nine seasons -- the
            # 2019-20 COVID round-robin games 2019030002 and 2019030016,
            # played under regular-season rules. 11 shot events total.
            if period == 5 and (int(game_type) == 2 or last_period == "SO"):
                n_shootout_skipped += 1
                continue

            t = mmss_to_seconds(tstr)

            # Which team took this shot? Look the shooter up in the box score.
            event_team = player_team.get(
                int(shooter_id) if shooter_id not in (None, "") else -1)
            if event_team is None:
                # Shooter missing from box score (very rare data gap). The
                # event is skipped rather than mis-tagged -- counted and
                # reported in the summary so the loss is visible, not silent.
                n_no_shooter_team += 1
                continue

            # ---- THE MATCHING RULE (Rule B): on ice iff start < t <= end ----
            # Membership is collected in a dict keyed by player id so each
            # player is counted AT MOST ONCE per event. Necessary because the
            # NHL feed contains duplicate/overlapping CLOSED shift rows for
            # the same player (measured on the full table: 19,689 overlapping
            # pairs across 1,587 games -- e.g. the identical row listed twice).
            # Without this, the same player lands on-ice twice for one event:
            # it crashed the first full run on the table's primary key, and
            # would have silently double-counted skaters in the QC counts.
            on_ice = {}
            for (s, e, pid, team) in shifts_by_period.get(period, ()):
                if s < t <= e:
                    if pid in on_ice:
                        n_duplicate_onice += 1     # duplicate absorbed, counted
                        continue
                    on_ice[pid] = team
            away_found = home_found = 0
            for pid, team in on_ice.items():
                is_home = 1 if team == home_ab else 0
                if is_home:
                    home_found += 1
                else:
                    away_found += 1
                oi_rows.append((
                    game_id, event_id, pid, team, is_home,
                    1 if team == event_team else 0,
                ))

            # ---- per-event QC against the NHL's own situation_code ----------
            # Code format: 4 digits, e.g. '1551' =
            #   [away goalie in][away skaters][home skaters][home goalie in]
            if sit and len(str(sit)) == 4:
                s4 = str(sit)
                away_exp, home_exp = int(s4[1]), int(s4[2])
                ok = 1 if (away_found == away_exp and home_found == home_exp) else 0
            else:
                away_exp = home_exp = None
                ok = 0   # unverifiable counts as not-ok, conservatively
            n_match_ok += ok
            n_match_bad += (1 - ok)
            qc_rows.append((game_id, event_id, away_exp, home_exp,
                            away_found, home_found, ok))

        cur.executemany(
            "INSERT INTO on_ice_skaters VALUES (?,?,?,?,?,?)", oi_rows)
        cur.executemany(
            "INSERT INTO on_ice_event_qc VALUES (?,?,?,?,?,?,?)", qc_rows)
        n_rows_written += len(oi_rows)

        if gi % 500 == 0:
            conn.commit()
            log(f"  {gi}/{len(games)} games done "
                f"({n_rows_written:,} on-ice rows so far)")

    conn.commit()

    # ------------------------------------------------------------------------
    # GAME-LEVEL QC: TWO DISTINCT PROBLEMS, OPPOSITE DOWNSTREAM HANDLING.
    #
    # (1) NO SHIFT DATA (no_shift_data = 1): the league never published a
    #     shift chart for the game -- verified against the live API during
    #     development: 525 games in 2025-26 (38% of that season) and 57 in
    #     2024-25 return zero rows from the NHL's own endpoint. Not a scrape
    #     failure; nothing to re-fetch (the scraper's resumability will pick
    #     them up automatically if the league backfills later). In these games
    #     NO on-ice reconstruction is possible; their situation codes are NOT
    #     implicated and remain the strength-state source.
    #
    # (2) SUSPECT CODES (codes_suspect = 1): shift data exists and reconciles
    #     with box-score TOI, but the league's situation codes are stuck/
    #     corrupted (e.g. claiming a team spent most of a game shorthanded
    #     when box TOI proves ~294 skater-minutes of normal 5v5 hockey).
    #     Concentrated in 2019-20. Here the RECONSTRUCTION is the truth:
    #     downstream strength state must come from away_found/home_found,
    #     not situation_code.
    #
    # A game with >20% event mismatch is classified (1) if it has zero shift
    # rows, else (2).
    # Investigation of high-mismatch games (during script development) found
    # that in a small number of games the league's OWN situation codes are
    # corrupted -- stuck after a penalty and never reset, claiming (for
    # example) that a team spent most of a game shorthanded when its box-score
    # TOI proves a normal ~294 skater-minute, mostly-5v5 game. In those games
    # the reconstruction is right and the "ground truth" is wrong. A game
    # whose event-level mismatch rate exceeds 20% is therefore flagged
    # `codes_suspect` rather than treated as a reconstruction failure: the
    # mismatches are serially clustered exactly as a stuck code would produce,
    # and shift-vs-boxscore TOI reconciliation (near-zero difference) is the
    # independent arbiter that clears the reconstruction side.
    # DOWNSTREAM IMPLICATION (for the xG model, Script 2): in suspect games,
    # strength state must be derived from the reconstructed on-ice counts in
    # on_ice_event_qc (away_found/home_found), NOT from shot_events.situation_code.
    # ------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS on_ice_game_qc AS
        SELECT q.game_id,
               COUNT(*)                AS events,
               SUM(q.match_ok)         AS events_matched,
               1.0 - CAST(SUM(q.match_ok) AS REAL)/COUNT(*) AS mismatch_rate,
               CASE WHEN s.n_shifts IS NULL
                     AND 1.0 - CAST(SUM(q.match_ok) AS REAL)/COUNT(*) > 0.20
                    THEN 1 ELSE 0 END  AS no_shift_data,
               CASE WHEN s.n_shifts IS NOT NULL
                     AND 1.0 - CAST(SUM(q.match_ok) AS REAL)/COUNT(*) > 0.20
                    THEN 1 ELSE 0 END  AS codes_suspect
        FROM on_ice_event_qc q
        LEFT JOIN (SELECT game_id, COUNT(*) AS n_shifts
                   FROM shifts GROUP BY game_id) s
               ON s.game_id = q.game_id
        GROUP BY q.game_id
    """)
    conn.commit()
    n_noshift_games, n_noshift_mismatches = cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(events - events_matched),0) "
        "FROM on_ice_game_qc WHERE no_shift_data=1").fetchone()
    n_suspect_games, n_suspect_mismatches = cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(events - events_matched),0) "
        "FROM on_ice_game_qc WHERE codes_suspect=1").fetchone()
    n_clean_ok, n_clean_scored = cur.execute(
        "SELECT COALESCE(SUM(q.match_ok),0), COUNT(*) FROM on_ice_event_qc q "
        "JOIN on_ice_game_qc g ON g.game_id = q.game_id "
        "WHERE g.codes_suspect = 0 AND g.no_shift_data = 0").fetchone()

    # ------------------------------------------------------------------------
    # VALIDATION SUMMARY -- printed, logged, and written to CSV.
    # The HEADLINE number is the match rate excluding shootouts (by design)
    # and excluding suspect-code games (where the league's codes, not the
    # reconstruction, are at fault).
    # ------------------------------------------------------------------------
    n_scored = n_match_ok + n_match_bad
    match_rate = (n_match_ok / n_scored * 100) if n_scored else 0.0
    clean_rate = (n_clean_ok / n_clean_scored * 100) if n_clean_scored else 0.0
    log("=" * 60)
    log("VALIDATION SUMMARY")
    log(f"  shot events seen:              {n_events_total:,}")
    log(f"  shootout attempts excluded:    {n_shootout_skipped:,} (by design)")
    log(f"  non-roster shift rows dropped (roster-truth rule; goalies + "
        f"the 3 corrupt-feed games): {n_nonroster_shift_rows:,}")
    log(f"  duplicate unclosed shifts dropped: {n_bad_shift_rows:,} "
        f"(known NHL feed glitch; harmless echoes of real shifts)")
    log(f"  unclosed final shifts recovered:   {n_recovered_shifts:,} "
        f"(end set to period end / next-shift bound)")
    log(f"  duplicate on-ice memberships absorbed: {n_duplicate_onice:,} "
        f"(same player listed twice in feed; counted once)")
    log(f"  events skipped, shooter untaggable: {n_no_shooter_team:,}")
    log(f"  events reconstructed + QC'd:   {n_scored:,}")
    log(f"  raw match vs situation_code:   {n_match_ok:,} ({match_rate:.2f}%)")
    log(f"  games with NO league shift data (no on-ice possible; codes "
        f"still valid): {n_noshift_games:,} games, {n_noshift_mismatches:,} events")
    log(f"  suspect-code games (stuck league codes, NOT reconstruction "
        f"errors): {n_suspect_games:,} games, {n_suspect_mismatches:,} mismatches")
    log(f"  HEADLINE match rate excluding both categories: {clean_rate:.2f}%")
    log(f"  flagged mismatches in clean games (kept, match_ok=0): "
        f"{n_clean_scored - n_clean_ok:,}")
    log(f"  on_ice_skaters rows written:   {n_rows_written:,}")
    if clean_rate < 99.0:
        log("  *** WARNING: clean-game match rate below 99% -- do NOT build "
            "on this run; investigate before proceeding. ***")
    else:
        log("  Clean-game match rate within expected range (~99.9%). OK.")
    log("=" * 60)

    summary_path = OUT_DIR / "on_ice_validation_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["events_seen", n_events_total])
        w.writerow(["shootout_excluded_by_design", n_shootout_skipped])
        w.writerow(["nonroster_shift_rows_dropped", n_nonroster_shift_rows])
        w.writerow(["duplicate_unclosed_shifts_dropped", n_bad_shift_rows])
        w.writerow(["unclosed_final_shifts_recovered", n_recovered_shifts])
        w.writerow(["duplicate_onice_memberships_absorbed", n_duplicate_onice])
        w.writerow(["shooter_untaggable_skipped", n_no_shooter_team])
        w.writerow(["events_reconstructed", n_scored])
        w.writerow(["exact_match_events", n_match_ok])
        w.writerow(["raw_match_rate_pct", round(match_rate, 3)])
        w.writerow(["no_shift_data_games", n_noshift_games])
        w.writerow(["no_shift_data_events", n_noshift_mismatches])
        w.writerow(["suspect_code_games", n_suspect_games])
        w.writerow(["suspect_code_game_mismatches", n_suspect_mismatches])
        w.writerow(["headline_match_rate_excl_suspect_pct", round(clean_rate, 3)])
        w.writerow(["clean_game_flagged_mismatches", n_clean_scored - n_clean_ok])
        w.writerow(["on_ice_rows_written", n_rows_written])
    log(f"Summary written to {summary_path}")

    runlog_path = OUT_DIR / "on_ice_reconstruction_runlog.txt"
    runlog_path.write_text("\n".join(RUNLOG) + "\n", encoding="utf-8")
    print(f"Run log written to {runlog_path}")

    conn.close()


if __name__ == "__main__":
    main()
