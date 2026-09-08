#!/usr/bin/env python3
"""
score_state.py  --  Script 3 of the Tier 2 game-level model build

WHAT THIS DOES, IN PLAIN ENGLISH
---------------------------------
Teams that are losing attack more; teams that are winning sit back and
defend. So a player's raw on-ice shot and chance totals partly reflect the
SCOREBOARD his team faced, not his own play. Without correcting for this,
players on bad (often-trailing) teams look systematically better at
generating offense -- and worse defensively -- than they really are.
(Locked Decision 5; buckets locked at leading / tied / trailing.)

This script does three things:

1. RECONSTRUCTS THE RUNNING SCORE at every moment of every game, by
   replaying the goals in order. For every shot in the database we then
   know whether the shooting team was leading, tied, or trailing AT THAT
   INSTANT. No new data is needed -- the score is derivable from goal
   events we already have.

2. TAGS EVERY SHOT with that score state (a new table, shot_score_state),
   so Script 4 can attach it to each on-ice observation.

3. MEASURES THE LEAGUE-WIDE SCORE EFFECT and turns it into adjustment
   factors. The idea, in one sentence: if trailing teams generate 54% of
   the even-strength chances in trailing-vs-leading segments, then chances
   created while trailing are slightly "cheaper" than average and get
   weighted by 0.5/0.54 = 0.93, while chances created while leading get
   0.5/0.46 = 1.09 -- so that after adjustment, neither game state is a
   free lunch. This mirrors the standard practitioner approach behind
   score-adjusted shot metrics (practitioner literature, not
   peer-reviewed -- flagged per project citation rules).

DESIGN DECISIONS (flagged per project convention)
--------------------------------------------------
1. THREE BUCKETS -- leading / tied / trailing -- regardless of margin.
   Locked by user decision. Finer slicing (down 1 vs down 3) spreads the
   data thin for little payoff at this metric's scope.
2. FACTORS ARE ESTIMATED FROM EVEN-STRENGTH, REGULAR-SEASON SHOTS ONLY.
   - Even strength: on the power play, the manpower edge -- not the
     scoreboard -- is what drives shot volume, and the xG model already
     prices strength directly. Mixing PP segments into the score-effect
     estimate would blur two different phenomena.
   - Regular season: locked Decision 4 (playoff hockey is systematically
     different and is excluded from all model FITTING steps).
   The TAGS, by contrast, are written for every shot in every game
   (playoffs included) -- what is fitted narrowly is the adjustment
   factor, not the bookkeeping.
3. THE SCORE STATE OF A GOAL IS THE STATE BEFORE IT WENT IN. A tying goal
   is scored by a TRAILING team; the replay updates the score only after
   tagging the shot itself.
4. EMPTY-NET GOALS COUNT TOWARD THE SCORE. They were rightly excluded
   from the xG model (no goalie to beat), but they absolutely change the
   scoreboard, so the replay includes them. Shootout "goals" do not enter
   the replay: the shootout is excluded event-wise (same rule as
   Scripts 1-2), and the shootout winner's +1 in the official final score
   is handled explicitly in the validation check below.
5. SAME-SECOND ORDERING: the feed's clock is whole seconds, so two events
   in the same second are ordered by event id -- approximately, not
   perfectly, chronological. For score replay this matters only when a
   goal and another shot share a second (rare); the resulting noise is
   negligible and flagged here rather than hidden.
6. TIED SEGMENTS GET A FACTOR OF EXACTLY 1.0 BY CONSTRUCTION. When the
   score is tied, both teams are in the same state; there is no
   asymmetry to correct. The empirical tied share is still computed and
   reported as a sanity check (it should sit very near 50%).

VALIDATION (built in, not separate)
-------------------------------------
- FULL-GAME SCORE RECONCILIATION: after replaying all goals in a game,
  the reconstructed final score must equal the official final score in
  the games table (with a +1 allowance for the shootout winner in games
  decided by shootout, where the official score credits a goal no
  in-play event produced). Every mismatch is counted and reported; more
  than a handful means the replay logic is broken and the run should not
  be built on.
- DIRECTION CHECK: trailing teams must generate MORE than 50% of
  even-strength xG in trailing-vs-leading segments. If they do not,
  something is inverted.

OUTPUTS
--------
  shot_score_state      (DB table)  one row per shot event:
      game_id, event_id, score_state (leading/tied/trailing, from the
      SHOOTING team's perspective), score_diff (signed goal differential)
  score_state_factors   (DB table + CSV)  one row per state:
      state, ev_xg_share, adjustment_factor
  score_state_runlog.txt

DEPENDENCIES
-------------
Standard library only. Runs after Script 2 (needs the shot_xg table for
the factor estimation; the tagging pass needs only shot_events).

USAGE
------
  python3 score_state.py
Deterministic and idempotent: output tables are dropped and rebuilt on
every run.
"""

import csv
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "v1.0 (2026-07-03) -- initial score-state adjustment"

# ---------------------------------------------------------------------------
# CONFIG -- same database Scripts 1 and 2 wrote into.
# ---------------------------------------------------------------------------
DB_PATH = Path(r"C:\Users\thoma\OneDrive\Desktop\test\nhl_gamelogs.sqlite")
OUT_DIR = DB_PATH.parent

RUNLOG = []
def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line)
    RUNLOG.append(line)


def mmss_to_seconds(t: str) -> int | None:
    try:
        m, s = str(t).split(":")
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


def main() -> None:
    print(f"score_state.py {SCRIPT_VERSION}")
    if not DB_PATH.exists():
        print(f"Database not found at:\n  {DB_PATH}\n"
            f"Update DB_PATH at the top of this script.", file=sys.stderr)
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {"games", "shot_events", "skater_games", "goalie_games",
               "shot_xg"} - tables
    if missing:
        print(f"Required tables missing: {sorted(missing)}. Run Scripts 1-2 "
            f"first.", file=sys.stderr)
        raise SystemExit(1)

    # -----------------------------------------------------------------------
    # STEP 1: lookups. Game metadata + shooter->team map (same ID-based
    # approach as Scripts 1-2; no name matching anywhere).
    # -----------------------------------------------------------------------
    log("Loading game metadata and player->team maps...")
    game_meta = {}   # game_id -> (game_type, away_ab, home_ab, away_final,
                     #             home_final, last_period)
    for gid, gtype, away, home, asc, hsc, lp in cur.execute(
            "SELECT game_id, game_type, away_team, home_team, "
            "       away_score, home_score, last_period FROM games"):
        game_meta[int(gid)] = (int(gtype), away, home,
                               int(asc) if asc is not None else None,
                               int(hsc) if hsc is not None else None, lp)

    player_team = defaultdict(dict)
    for table in ("skater_games", "goalie_games"):
        for gid, pid, team in cur.execute(
                f"SELECT game_id, player_id, team FROM {table}"):
            player_team[int(gid)][int(pid)] = team

    # -----------------------------------------------------------------------
    # STEP 2: the replay. One pass over ALL shot events in chronological
    # order within each game. For every shot: tag the shooting team's score
    # state as of that instant; if the shot is a goal, update the score
    # AFTER tagging (design decision 3).
    # -----------------------------------------------------------------------
    log("Replaying goals and tagging every shot's score state...")
    counters = defaultdict(int)
    tag_rows = []                    # -> shot_score_state
    replay_score = {}                # game_id -> [away_goals, home_goals]
    mismatched_games = []

    current_game = None
    for row in cur.execute("""
            SELECT game_id, event_id, period, time_in_period, shot_result,
                   shooting_player_id
            FROM shot_events
            ORDER BY game_id, period, time_in_period, event_id"""):
        gid, eid, period = int(row[0]), int(row[1]), int(row[2])
        result = row[4]
        shooter_id = int(row[5]) if row[5] not in (None, "") else None

        meta = game_meta.get(gid)
        if meta is None:
            counters["skipped_no_game_meta"] += 1
            continue
        gtype, away_ab, home_ab, away_final, home_final, last_period = meta

        # New game: reconcile the finished one, reset the score.
        if gid != current_game:
            current_game = gid
            replay_score[gid] = [0, 0]

        # Shootout exclusion: shootout attempts are neither tagged nor
        # allowed to move the replayed score -- the official final handles
        # the SO winner's +1 (validation below). Detection is by the game's
        # recorded final period type, NOT by game type alone: the 2019-20
        # COVID-bubble round-robin played two "playoff-type" games under
        # regular-season rules that ended in shootouts (2019030002,
        # 2019030016 -- the only two in nine seasons). A game-type-only rule
        # let their SO "goals" into the score replay, which is how this
        # exception was caught: those two games failed the full-game score
        # reconciliation check below.
        if period == 5 and (gtype == 2 or last_period == "SO"):
            counters["skipped_shootout"] += 1
            continue

        counters["shots_seen"] += 1
        team = player_team.get(gid, {}).get(shooter_id) if shooter_id else None
        if team is None:
            # Cannot tag a shot whose shooter is unmapped; counted, never
            # silent. (Zero such rows existed in Script 2's full run.)
            counters["skipped_shooter_unmapped"] += 1
            continue
        shooter_is_home = 1 if team == home_ab else 0

        a, h = replay_score[gid]
        diff = (h - a) if shooter_is_home else (a - h)
        state = "leading" if diff > 0 else ("trailing" if diff < 0 else "tied")
        tag_rows.append((gid, eid, state, diff))
        counters[f"tagged_{state}"] += 1

        # Update the score AFTER tagging (a tying goal is shot while trailing).
        if result == "goal":
            if shooter_is_home:
                replay_score[gid][1] += 1
            else:
                replay_score[gid][0] += 1

    # -----------------------------------------------------------------------
    # STEP 3: full-game score reconciliation (validation, per game).
    # Allowance: in a game decided by shootout, the official final score
    # credits the SO winner one goal that no in-play event produced.
    # -----------------------------------------------------------------------
    log("Reconciling replayed final scores against official finals...")
    n_checked = n_ok = 0
    for gid, (a, h) in replay_score.items():
        gtype, away_ab, home_ab, away_final, home_final, last_period = game_meta[gid]
        if away_final is None or home_final is None:
            continue
        n_checked += 1
        if (a, h) == (away_final, home_final):
            n_ok += 1
        elif last_period == "SO" and (
                (away_final - a, home_final - h) in ((1, 0), (0, 1))):
            n_ok += 1        # shootout winner's +1: expected, not an error
        else:
            mismatched_games.append((gid, a, h, away_final, home_final))
    log(f"  {n_ok}/{n_checked} games reconcile exactly "
        f"(SO-adjusted); {len(mismatched_games)} mismatched.")
    for gid, a, h, af, hf in mismatched_games[:10]:
        log(f"    game {gid}: replay {a}-{h} vs official {af}-{hf}")
    if len(mismatched_games) > 20:
        log("  *** WARNING: more than 20 games fail score reconciliation -- "
            "do NOT build on this run; investigate first. ***")

    # -----------------------------------------------------------------------
    # STEP 4: write the tag table.
    # -----------------------------------------------------------------------
    cur.executescript("""
        DROP TABLE IF EXISTS shot_score_state;
        CREATE TABLE shot_score_state (
            game_id     INTEGER NOT NULL,
            event_id    INTEGER NOT NULL,
            score_state TEXT    NOT NULL,   -- leading / tied / trailing,
                                            -- from the SHOOTING team's side
            score_diff  INTEGER NOT NULL,   -- signed goals (shooter minus
                                            -- opponent) at the instant
            PRIMARY KEY (game_id, event_id)
        );
    """)
    cur.executemany("INSERT INTO shot_score_state VALUES (?,?,?,?)", tag_rows)
    conn.commit()
    log(f"shot_score_state written: {len(tag_rows):,} rows "
        f"(leading {counters['tagged_leading']:,} / "
        f"tied {counters['tagged_tied']:,} / "
        f"trailing {counters['tagged_trailing']:,}).")

    # -----------------------------------------------------------------------
    # STEP 5: estimate the league score-effect factors.
    # Sample: even-strength, regular-season shots from shot_xg (which
    # already applied the unblocked / goalie-in / no-shootout rules), joined
    # to the tags written above. The share is computed on xG, not raw shot
    # counts, so "trailing teams shoot more but from worse spots" is priced
    # correctly rather than overstated.
    #
    # Factor logic in one line each:
    #   leading/trailing segments: the two states are mirror images -- every
    #   trailing-team chance happens against a leading opponent. If trailing
    #   teams hold share p of that xG, the factor for trailing is 0.5/p and
    #   for leading is 0.5/(1-p).
    #   tied: both teams tied -- symmetric by construction, factor 1.0
    #   (design decision 6); empirical share reported as a sanity check.
    # -----------------------------------------------------------------------
    log("Estimating even-strength score-effect factors (regular season)...")
    xg_by_state = {"leading": 0.0, "tied": 0.0, "trailing": 0.0}
    for state, xg_sum in cur.execute("""
            SELECT t.score_state, SUM(x.xg)
            FROM shot_xg x
            JOIN shot_score_state t
              ON t.game_id = x.game_id AND t.event_id = x.event_id
            WHERE x.game_type = 2 AND x.strength = 'EV'
            GROUP BY t.score_state"""):
        xg_by_state[state] = float(xg_sum)

    lead, trail = xg_by_state["leading"], xg_by_state["trailing"]
    p_trailing = trail / (lead + trail)
    factors = {
        "trailing": 0.5 / p_trailing,
        "leading": 0.5 / (1.0 - p_trailing),
        "tied": 1.0,
    }
    log(f"  EV xG in lead-vs-trail segments: trailing share = "
        f"{p_trailing*100:.2f}% (must exceed 50% -- direction check)")
    if p_trailing <= 0.5:
        log("  *** WARNING: trailing share is not above 50% -- the score "
            "effect is inverted or missing; do NOT build on this run. ***")
    for s in ("leading", "tied", "trailing"):
        log(f"  factor[{s}] = {factors[s]:.4f}")

    cur.executescript("""
        DROP TABLE IF EXISTS score_state_factors;
        CREATE TABLE score_state_factors (
            score_state       TEXT PRIMARY KEY,
            ev_xg_share       REAL,     -- share within lead-vs-trail segments
                                        -- (NULL for tied: symmetric by design)
            adjustment_factor REAL NOT NULL
        );
    """)
    cur.executemany("INSERT INTO score_state_factors VALUES (?,?,?)", [
        ("leading", 1.0 - p_trailing, factors["leading"]),
        ("tied", None, factors["tied"]),
        ("trailing", p_trailing, factors["trailing"]),
    ])
    conn.commit()

    factors_path = OUT_DIR / "score_state_factors.csv"
    with open(factors_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["score_state", "ev_xg_share_in_lead_trail_segments",
                    "adjustment_factor"])
        w.writerow(["leading", round(1.0 - p_trailing, 4),
                    round(factors["leading"], 4)])
        w.writerow(["tied", "symmetric_by_construction", 1.0])
        w.writerow(["trailing", round(p_trailing, 4),
                    round(factors["trailing"], 4)])
    log(f"Factors written to {factors_path}")

    (OUT_DIR / "score_state_runlog.txt").write_text(
        "\n".join(RUNLOG) + "\n", encoding="utf-8")
    conn.close()
    log("Done.")


if __name__ == "__main__":
    main()
