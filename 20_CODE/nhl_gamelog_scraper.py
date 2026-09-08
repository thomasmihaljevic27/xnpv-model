#!/usr/bin/env python3
"""
nhl_gamelog_scraper.py  (v2 -- adds shifts, full shot events, penalties, faceoffs)

Per-game player performance scraper for the NHL Trade Market Efficiency project.

PURPOSE
-------
Builds the game-level box-score + play-by-play database that powers the bespoke
goal-denominated outcome metric (mid-season trade splits + non-Bacon realized-
outcome validation). Pulls every regular-season and playoff game from the NHL's
own JSON API for the configured season range.

v2 CHANGE SUMMARY (2026-07-01)
-------------------------------
The v1 scraper (games / skater_games / goalie_games / goal_events) is UNCHANGED
below -- every existing table, column, and row is identical, so nothing that
already reads v1 output breaks. Four tables are ADDED:

  - shot_events    : every shot ATTEMPT (goal, shot-on-goal, missed-shot,
                     blocked-shot), with coordinates, shot type, shooter,
                     goalie, and (for blocks) the blocking player. This is
                     the training material for the xG/xGA model -- goal_events
                     alone only tells you what went IN, not what was tried.
  - penalty_events : who took a penalty vs who DREW it, kept separate because
                     a goal-denominated metric should reward drawing penalties
                     as its own skill, not lump it in with taking fewer.
  - faceoff_events : actual per-draw winner/loser. The boxscore only stores a
                     season-cumulative percentage per player per game, which
                     can't distinguish 1-for-1 from 10-for-10.
  - shifts         : raw shift intervals (player, period, start/end time).
                     This is the raw material needed to know who was ON THE
                     ICE for a given shot/goal -- i.e. defensive value, which
                     box-score counting stats miss almost entirely. NOTE: this
                     script only stores the raw intervals. Matching shifts to
                     events ("on-ice for") is a separate downstream script by
                     design -- collection and modeling stay separate, per
                     project convention.

WHY THESE FOUR: this is the complete data requirement for a goal-denominated,
defense-aware outcome metric (xG/xGA weighted by team goal differential) that
does not touch Bacon at any stage -- see Decision Log entry on the non-Bacon
yardstick. It is deliberately NOT a full WAR rebuild (no zone-start, no
competition/teammate adjustment, no RAPM) -- that scope decision is logged
separately.

DESIGN DECISIONS (flagged per project conventions)
---------------------------------------------------
1. SOURCE: NHL official API, not a third-party site. League-source data is the
   accuracy ceiling for box scores; no HTML parsing fragility.
2. SEASONS: default 2017-18 through 2025-26. Trade dataset starts June 2018, so
   2018-19 is the first trade-relevant season; 2017-18 is included as a buffer
   season to deepen the season-level calibration. Adjustable via --seasons.
3. GAME TYPES: regular season (type 2) AND playoffs (type 3) are both collected.
   Whether playoff games enter the metric is an ANALYSIS-TIME decision; collecting
   both now avoids a re-pull either way. gameType is stored on every row.
4. RAW JSON CACHING: every API response (boxscore, play-by-play, AND shift
   chart) is written to disk before parsing. Re-runs never re-fetch a cached
   game; parsing bugs can be fixed and re-run against cache at zero network cost.
5. A1/A2 SPLIT: boxscore reports total assists only. Primary/secondary assists
   are derived from goal events in the play-by-play feed and reconciled against
   the boxscore total as a validation check. (v1, unchanged.)
6. PLUS-MINUS: collected per user decision (defensive-stat scarcity), with the
   known caveat that it is a noisy team-context stat. (v1, unchanged.)
7. JOIN KEY: NHL playerId, which matches the `nhl_id` column in the PuckPedia
   contract export -> clean ID-based join to the project spine (no name matching).
8. PROVENANCE: every parsed row carries scraped_at (UTC ISO) and source game id.
9. SHIFT CHART IS A SEPARATE API HOST: shift data lives on api.nhle.com/stats/rest,
   not api-web.nhle.com (the boxscore/play-by-play host). Confirmed live and
   working (2026-07-01 smoke test) before writing this parser -- see
   SHIFT_API_BASE below. Different host, same caching/retry machinery.
10. SHIFT ROW FILTER: the shift-chart feed mixes real shifts (typeCode 517)
    with zero-duration goal/event annotation rows (typeCode 505) that are NOT
    ice-time intervals. Only typeCode 517 rows are kept as shifts; confirmed
    against a live sample (689 real shifts vs 5 annotation rows in one game).
11. shot_events DELIBERATELY DUPLICATES goals already in goal_events (with
    shot_result='goal'). This is intentional: the xG model wants one consistent
    table of every shot ATTEMPT (make and miss together) rather than joining
    two tables to reconstruct "shots that didn't score." goal_events is left
    untouched for anything already built against it.
12. RESUMABILITY REDEFINED: v1 considered a game "done" once it had a row in
    `games`. Since Thomas's existing DB already has all ~11,800 games parsed
    under v1, a naive "already in `games`" skip would NEVER fetch the new
    shift charts for that backlog. v2 instead treats a game as fully done only
    once it ALSO has at least one row in `shifts`. Practically: for games
    already parsed under v1, the boxscore/play-by-play calls are free (served
    from the existing disk cache) and the ONLY new network traffic is the
    shift-chart pull -- see volume estimate below. --skip-shifts restores the
    old v1-only resumability if you ever want to run without shifts.

v2.1 CHANGE SUMMARY (2026-07-03) -- HTML SHIFT-REPORT FALLBACK
------------------------------------------------------------------
The full v2 run found 582 games (525 in 2025-26, 57 in 2024-25) with ZERO
rows from the JSON shiftcharts endpoint used below. Initial conclusion was
that the league had not published shift data for these games at all.

That conclusion was WRONG, and was corrected by testing, not assumption.
Reading the source of a public R package (RentoSaijo/nhlscraper) surfaced a
second, older NHL data source: the legacy per-team HTML "Time On Ice"
reports at nhl.com/scores/htmlreports/. Verification before adopting this
(per project convention -- confirm, don't assume):
  - Live-tested 25 of the 582 "gap" games against this URL pattern:
    25/25 (100%) returned real, parseable shift data.
  - Cross-validated one recovered game's summed shift time against
    box-score TOI (a source already fully trusted): 36/36 players matched,
    mean and max difference = 0.00 minutes.
The gap was in which of two NHL data sources this scraper checked, not in
what the league published. v2.1 adds the HTML report as an automatic
fallback: tried ONLY when the JSON endpoint returns zero real shift rows
for a game, so games the JSON endpoint already serves correctly are
completely unaffected by this change.

Mechanics of the fallback (see fetch_and_parse_html_shifts() below):
  - The HTML report gives jersey number + name per shift, not a numeric
    player id. IDs are resolved via the play-by-play roster
    (pbp['rosterSpots']), matching jersey number within the correct team --
    the same roster data this script already fetches for every game, so no
    new API calls are needed for identity resolution.
  - The HTML report has no native shift-row id (the JSON path's own 'id'
    field). Rows recovered this way are given a NEGATIVE synthetic
    shift_id, which can never collide with the JSON API's own (always
    positive) ids. This makes the row's SOURCE self-documenting from its
    sign alone: shift_id > 0 means the JSON API; shift_id < 0 means the
    HTML fallback. No new column needed, and the existing 8.67M rows from
    the original run need no migration.


  python3 nhl_gamelog_scraper.py                      # full default run (all tables)
  python3 nhl_gamelog_scraper.py --seasons 20232024   # one season
  python3 nhl_gamelog_scraper.py --skip-shifts        # v1 behavior only, no shift pull
  python3 nhl_gamelog_scraper.py --validate-only      # run checks on existing DB
  python3 nhl_gamelog_scraper.py --export-csv         # dump CSVs from the DB

Resumable: interrupt at any time; re-running skips work already cached on disk
and (for shifts) already present in the DB.

VOLUME ESTIMATE
----------------
Fresh run, nothing cached: 3 requests/game (boxscore + play-by-play + shifts)
x ~11,800 games ~= 35,400 requests. At the default 0.35s spacing, roughly
3.5-4 hours.

Backfill run against Thomas's EXISTING v1 cache (the actual situation here):
boxscore + play-by-play are served from disk at zero network cost, so it is
effectively 1 NEW request/game (shifts only) x ~11,800 games ~= 11,800
requests ~= roughly 70-90 minutes. Run locally.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
API_BASE = "https://api-web.nhle.com/v1"
SHIFT_API_BASE = "https://api.nhle.com/stats/rest/en"   # separate host -- see design note 9
SCRIPT_VERSION = "v2.4 (2026-07-03) -- foreign-team shift filter; OUT_DIR corrected to new_scrape"
OUT_DIR = Path(os.environ["SCRAPE_OUT_DIR"])          # all outputs live here (from .env)
RAW_DIR = OUT_DIR / "raw"                    # cached API JSON, one file per call
DB_PATH = OUT_DIR / "nhl_gamelogs.sqlite"
REQUEST_SPACING_S = 0.35                     # polite rate limit between requests
TIMEOUT_S = 30
MAX_RETRIES = 4

# Default season range. Season key format: 20172018 means the 2017-18 season.
DEFAULT_SEASONS = [
    "20172018", "20182019", "20192020", "20202021", "20212022",
    "20222023", "20232024", "20242025", "20252026",
]

# Approximate first/last calendar bounds per season for schedule walking.
# Deliberately generous (COVID seasons shifted); the walker simply finds no
# games outside the true window, so over-wide bounds cost a few cheap calls.
SEASON_BOUNDS = {
    "20172018": ("2017-09-15", "2018-06-15"),
    "20182019": ("2018-09-15", "2019-06-15"),
    "20192020": ("2019-09-15", "2020-10-01"),   # COVID bubble playoffs ran to Sep 2020
    "20202021": ("2021-01-01", "2021-07-15"),   # COVID-shortened 56-game season
    "20212022": ("2021-09-15", "2022-06-30"),
    "20222023": ("2022-09-15", "2023-06-30"),
    "20232024": ("2023-09-15", "2024-06-30"),
    "20242025": ("2024-09-15", "2025-06-30"),
    "20252026": ("2025-09-15", "2026-06-30"),
}

GAME_TYPES_KEPT = {2, 3}  # 2 = regular season, 3 = playoffs (1 = preseason, excluded)

# Shot-attempt event types kept in shot_events, and how each typeDescKey maps
# to the shot_result value stored on the row.
SHOT_TYPE_MAP = {
    "goal": "goal",
    "shot-on-goal": "shot-on-goal",
    "missed-shot": "missed-shot",
    "blocked-shot": "blocked-shot",
}

session = requests.Session()
session.headers.update({"User-Agent": "academic-research-gamelog-collector"})


# ----------------------------------------------------------------------------
# HTTP layer: cached, rate-limited, retrying
# ----------------------------------------------------------------------------
def fetch_json(url: str, cache_name: str) -> dict | None:
    """Fetch a URL with on-disk caching. Cache hit -> zero network traffic.

    Returns parsed JSON, or None on persistent failure (logged, not fatal:
    a single bad game must not kill a multi-hour run)."""
    cache_file = RAW_DIR / cache_name
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            cache_file.unlink()  # corrupt cache entry; refetch below

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(REQUEST_SPACING_S)
            resp = session.get(url, timeout=TIMEOUT_S)
            if resp.status_code == 404:
                return None  # game id exists in schedule but feed missing; skip
            resp.raise_for_status()
            data = resp.json()
            cache_file.write_text(json.dumps(data))
            return data
        except (requests.RequestException, json.JSONDecodeError) as exc:
            wait = 2 ** attempt  # exponential backoff: 2,4,8,16s
            print(f"  WARN attempt {attempt}/{MAX_RETRIES} failed for {url}: {exc}; "
                  f"retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"  ERROR giving up on {url}", file=sys.stderr)
    return None


# ----------------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------------
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    -- One row per game.                                                (v1, unchanged)
    CREATE TABLE IF NOT EXISTS games (
        game_id        INTEGER PRIMARY KEY,
        season         TEXT NOT NULL,
        game_type      INTEGER NOT NULL,          -- 2 reg, 3 playoff
        game_date      TEXT NOT NULL,             -- YYYY-MM-DD
        away_team      TEXT NOT NULL,
        home_team      TEXT NOT NULL,
        away_score     INTEGER,
        home_score     INTEGER,
        last_period    TEXT,                      -- REG / OT / SO: needed because the
                                                  -- wins conversion may treat SO goals
                                                  -- and 3-on-3 OT differently
        scraped_at     TEXT NOT NULL
    );

    -- One row per skater per game. Column names mirror the API for auditability.
    -- (v1, unchanged)
    CREATE TABLE IF NOT EXISTS skater_games (
        game_id        INTEGER NOT NULL,
        player_id      INTEGER NOT NULL,          -- joins PuckPedia spine via nhl_id
        player_name    TEXT,
        team           TEXT NOT NULL,             -- team the player dressed FOR this
                                                  -- game: this is the field that
                                                  -- solves the mid-season-split problem
        opponent       TEXT NOT NULL,
        is_home        INTEGER NOT NULL,
        position       TEXT,
        goals          INTEGER,
        assists        INTEGER,                   -- boxscore total (A1+A2 check below)
        a1             INTEGER,                   -- primary assists, from play-by-play
        a2             INTEGER,                   -- secondary assists, from play-by-play
        points         INTEGER,
        plus_minus     INTEGER,                   -- collected per user decision; noisy
        pim            INTEGER,
        sog            INTEGER,
        hits           INTEGER,
        blocked_shots  INTEGER,
        giveaways      INTEGER,
        takeaways      INTEGER,
        pp_goals       INTEGER,
        faceoff_pct    REAL,
        toi_minutes    REAL,                      -- parsed from "MM:SS"
        shifts         INTEGER,
        scraped_at     TEXT NOT NULL,
        PRIMARY KEY (game_id, player_id)
    );

    -- One row per goalie per game.                                     (v1, unchanged)
    CREATE TABLE IF NOT EXISTS goalie_games (
        game_id        INTEGER NOT NULL,
        player_id      INTEGER NOT NULL,
        player_name    TEXT,
        team           TEXT NOT NULL,
        opponent       TEXT NOT NULL,
        is_home        INTEGER NOT NULL,
        starter        INTEGER,
        shots_against  INTEGER,
        saves          INTEGER,
        goals_against  INTEGER,
        ev_shots_against INTEGER,
        pp_shots_against INTEGER,
        sh_shots_against INTEGER,
        ev_goals_against INTEGER,
        pp_goals_against INTEGER,
        sh_goals_against INTEGER,
        toi_minutes    REAL,
        scraped_at     TEXT NOT NULL,
        PRIMARY KEY (game_id, player_id)
    );

    -- One row per goal event.                                          (v1, unchanged)
    -- situation_code encodes the on-ice strength (e.g. '1551' = 5v5, both
    -- goalies in). Left exactly as-is so nothing already built against it breaks.
    CREATE TABLE IF NOT EXISTS goal_events (
        game_id        INTEGER NOT NULL,
        event_idx      INTEGER NOT NULL,
        period         INTEGER,
        time_in_period TEXT,
        situation_code TEXT,
        scoring_player INTEGER,
        assist1_player INTEGER,
        assist2_player INTEGER,
        scoring_team_id INTEGER,
        scraped_at     TEXT NOT NULL,
        PRIMARY KEY (game_id, event_idx)
    );

    -- =========================== NEW IN v2 ================================

    -- One row per shot ATTEMPT: goal, shot-on-goal, missed-shot, blocked-shot.
    -- The xG/xGA model's training table. Coordinates are on the ice relative
    -- to the SHOOTING team's attacking end (per the API's own convention).
    CREATE TABLE IF NOT EXISTS shot_events (
        game_id             INTEGER NOT NULL,
        event_id            INTEGER NOT NULL,     -- NHL API's own eventId (unique per game)
        period              INTEGER,
        time_in_period      TEXT,
        situation_code      TEXT,                 -- on-ice strength state
        shot_result         TEXT NOT NULL,        -- goal / shot-on-goal / missed-shot / blocked-shot
        zone_code           TEXT,                 -- O/D/N, relative to the shooting team
        x_coord             REAL,
        y_coord             REAL,
        shot_type           TEXT,                 -- wrist/slap/snap/backhand/tip-in/etc
        shooting_player_id  INTEGER,
        blocking_player_id  INTEGER,               -- populated only when shot_result='blocked-shot'
        goalie_id           INTEGER,                -- goalie in net; NULL on some empty-net goals
        event_owner_team_id INTEGER NOT NULL,       -- the SHOOTING team's NHL team id
        scraped_at          TEXT NOT NULL,
        PRIMARY KEY (game_id, event_id)
    );

    -- One row per penalty. committed_by and drawn_by are kept as separate
    -- columns on purpose -- a goal-denominated metric should credit drawing
    -- penalties as its own skill, not net it against penalties taken.
    CREATE TABLE IF NOT EXISTS penalty_events (
        game_id                INTEGER NOT NULL,
        event_id               INTEGER NOT NULL,
        period                  INTEGER,
        time_in_period          TEXT,
        situation_code          TEXT,
        penalty_type            TEXT,              -- MIN / MAJ / MIS / GAME / BENCH etc
        penalty_desc             TEXT,              -- 'tripping', 'hooking', etc
        duration_minutes         INTEGER,
        committed_by_player_id   INTEGER,
        drawn_by_player_id       INTEGER,           -- NULL for bench/team penalties
        event_owner_team_id      INTEGER,           -- team that was PENALIZED
        scraped_at               TEXT NOT NULL,
        PRIMARY KEY (game_id, event_id)
    );

    -- One row per faceoff, with the actual winner/loser -- the boxscore only
    -- gives a season-cumulative PERCENTAGE per player per game, which can't
    -- distinguish a 1-for-1 night from a 10-for-10 night.
    CREATE TABLE IF NOT EXISTS faceoff_events (
        game_id                INTEGER NOT NULL,
        event_id               INTEGER NOT NULL,
        period                  INTEGER,
        time_in_period          TEXT,
        situation_code          TEXT,
        zone_code                TEXT,
        winning_player_id        INTEGER,
        losing_player_id         INTEGER,
        event_owner_team_id      INTEGER,           -- team of the WINNING player
        scraped_at               TEXT NOT NULL,
        PRIMARY KEY (game_id, event_id)
    );

    -- One row per shift: a continuous stretch of ice time for one player.
    -- This is the RAW MATERIAL for on-ice reconstruction (who was out there
    -- for a given shot/goal, needed to value defensive play). Matching shifts
    -- to events is intentionally NOT done in this script -- see design note 12
    -- in the module docstring. This table only stores the raw intervals.
    CREATE TABLE IF NOT EXISTS shifts (
        game_id           INTEGER NOT NULL,
        shift_id          INTEGER NOT NULL,        -- NHL API's own shift row id
        player_id         INTEGER NOT NULL,
        player_name       TEXT,
        team              TEXT NOT NULL,           -- team abbreviation, matches skater_games.team
        period             INTEGER NOT NULL,
        shift_number        INTEGER,
        start_time           TEXT,                  -- MM:SS within the period
        end_time              TEXT,
        duration_seconds       INTEGER,             -- parsed from the API's MM:SS duration
        scraped_at            TEXT NOT NULL,
        PRIMARY KEY (game_id, shift_id)
    );
    """)
    conn.commit()


# ----------------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------------
def toi_to_minutes(toi: str | None) -> float | None:
    """'18:42' -> 18.7 minutes. API occasionally omits TOI; return None, never 0,
    so missing data is distinguishable from a 0:00 appearance."""
    if not toi:
        return None
    try:
        mm, ss = toi.split(":")
        return round(int(mm) + int(ss) / 60.0, 2)
    except (ValueError, AttributeError):
        return None


def duration_to_seconds(duration: str | None) -> int | None:
    """Shift-chart durations are 'MM:SS' strings, e.g. '00:47'. Unlike TOI we
    keep this in whole seconds (not minutes) because shifts are short enough
    that minute-level rounding would matter for on-ice reconstruction later."""
    if not duration:
        return None
    try:
        mm, ss = duration.split(":")
        return int(mm) * 60 + int(ss)
    except (ValueError, AttributeError):
        return None


def clock_to_seconds(clock: str) -> int:
    """Parses a single 'MM:SS' clock reading (as opposed to duration_to_seconds,
    which parses a SPAN like '00:47'). Used by the HTML shift-report fallback
    to turn its start/end clock readings into a duration by subtraction."""
    m, s = clock.split(":")
    return int(m) * 60 + int(s)


def enumerate_games(season: str) -> list[dict]:
    """Walk the public schedule endpoint week by week across the season's
    calendar bounds, collecting finished games of kept types.

    Uses /v1/schedule/{date}, which returns one week of games plus a
    nextStartDate cursor -- ~27 calls per season instead of 365 daily calls."""
    start_s, end_s = SEASON_BOUNDS[season]
    cursor = date.fromisoformat(start_s)
    end = date.fromisoformat(end_s)
    games: dict[int, dict] = {}

    while cursor <= end:
        data = fetch_json(f"{API_BASE}/schedule/{cursor.isoformat()}",
                          f"schedule_{cursor.isoformat()}.json")
        if data is None:
            cursor += timedelta(days=7)
            continue
        for day in data.get("gameWeek", []):
            for g in day.get("games", []):
                # Filter to: our season, reg/playoff, game actually completed.
                if (str(g.get("season")) == season
                        and g.get("gameType") in GAME_TYPES_KEPT
                        and g.get("gameState") in ("OFF", "FINAL")):
                    games[g["id"]] = {"game_id": g["id"], "date": day["date"]}
        nxt = data.get("nextStartDate")
        # Defensive cursor advance: if the API omits nextStartDate, step a week
        # manually rather than looping forever on the same date.
        cursor = date.fromisoformat(nxt) if nxt else cursor + timedelta(days=7)

    out = sorted(games.values(), key=lambda x: x["game_id"])
    print(f"  {season}: {len(out)} completed reg/playoff games found")
    return out


def fetch_text(url: str, cache_name: str) -> str | None:
    """Same caching/retry/rate-limit policy as fetch_json(), but for plain
    HTML pages (the legacy shift reports) rather than JSON API responses.
    Kept as a separate function rather than reused, since the two return
    fundamentally different content types and any shared abstraction would
    need type-checking at every call site for no real benefit."""
    cache_file = RAW_DIR / cache_name
    if cache_file.exists():
        try:
            return cache_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass  # fall through and refetch

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(REQUEST_SPACING_S)
            resp = session.get(url, timeout=TIMEOUT_S)
            if resp.status_code == 404:
                return None  # report genuinely doesn't exist for this game
            resp.raise_for_status()
            text = resp.text
            cache_file.write_text(text, encoding="utf-8")
            return text
        except requests.RequestException as exc:
            wait = 2 ** attempt
            print(f"  WARN attempt {attempt}/{MAX_RETRIES} failed for {url}: {exc}; "
                f"retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"  ERROR giving up on {url}", file=sys.stderr)
    return None


def html_shift_report_url(game_id: int, team_tag: str) -> str:
    """Builds the legacy HTML shift-report URL for a game. team_tag is 'TH'
    for the home team's report or 'TV' for the away/visitor team's report.
    URL pattern reverse-engineered from the nhlscraper R package and
    confirmed live against 25 sample games before being used here (see the
    v2.1 changelog entry in the module docstring)."""
    season_start = game_id // 1_000_000
    game_code = f"{game_id % 1_000_000:06d}"
    return (f"https://www.nhl.com/scores/htmlreports/"
        f"{season_start}{season_start + 1}/{team_tag}{game_code}.HTM")


def parse_html_period_label(label: str, is_playoffs: bool) -> int | None:
    """Converts the HTML report's period label to the same integer
    convention used everywhere else in this project: 1/2/3 as normal,
    4 = first overtime, 5 = second overtime (or the shootout in a regular-
    season game -- excluded downstream by on_ice_reconstruction.py's
    existing shootout rule, so no special handling is needed here).
    Logic ported from the nhlscraper R package's .parse_html_period_label(),
    which already handles the '2OT', '3OT', etc. playoff labels correctly."""
    x = label.strip().upper()
    if not x:
        return None
    if x.isdigit():
        return int(x)
    if x == "OT":
        return 4
    m = re.match(r"^(\d+)OT$", x)
    if m:
        return 3 + int(m.group(1))
    if x == "SO":
        return None if is_playoffs else 5
    return None


def parse_html_shift_report(html: str, is_playoffs: bool) -> list[dict]:
    """Parses one team's HTML shift-report page into shift rows.

    Report structure (confirmed by inspecting the raw HTML, not guessed):
      - A player-header row is a single cell like '53 SEIDER, MORITZ',
        marking the start of that player's block of shifts.
      - Each shift is a table row: shift number, period, a start-time cell
        formatted 'elapsed / remaining' (e.g. '12:06 / 7:54'), and an
        end-time cell in the same format. Only the elapsed (first) number
        of each pair is used -- the same clock convention as the rest of
        this project's shift data.
    Returns dicts with jersey number and period already resolved to ints;
    player identity (jersey -> nhl playerId) is resolved by the caller,
    which has access to that game's roster."""
    rows_html = re.split(r"<tr[^>]*>", html)[1:]
    out = []
    current_jersey = None
    current_label = None
    for row in rows_html:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        cells = [re.sub("<[^>]+>", "", c).replace("&nbsp;", " ").strip()
            for c in cells]
        cells = [c for c in cells if c != ""]

        if len(cells) == 1 and re.match(r"^\d+\s+.+", cells[0]) and "Shift" not in cells[0]:
            m = re.match(r"^(\d+)\s+(.+)$", cells[0])
            if m:
                current_jersey = int(m.group(1))
                current_label = m.group(2)
            continue

        if len(cells) >= 4 and re.match(r"^\d+$", cells[0]) and current_jersey is not None:
            period = parse_html_period_label(cells[1], is_playoffs)
            if period is None:
                continue
            m_start = re.search(r"(\d{1,2}:\d{2})\s*/\s*(\d{1,2}:\d{2})", cells[2])
            m_end = re.search(r"(\d{1,2}:\d{2})\s*/\s*(\d{1,2}:\d{2})", cells[3])
            if not (m_start and m_end):
                continue
            out.append({
                "jersey": current_jersey,
                "label": current_label,
                "shift_number": int(cells[0]),
                "period": period,
                "start": m_start.group(1),
                "end": m_end.group(1),
            })
    return out


def fetch_and_parse_html_shifts(game_id: int, away_ab: str, home_ab: str,
                                pbp: dict, is_playoffs: bool,
                                conn: sqlite3.Connection, now: str) -> int:
    """Fallback shift source, tried ONLY when the JSON shiftcharts endpoint
    returns zero real rows for a game -- see the v2.1 changelog entry above
    for why this exists and how it was verified before being trusted.

    Returns the number of shift rows written (0 if the fallback also found
    nothing -- rare, but possible for e.g. a genuinely uncompleted/future
    game slipping into the schedule walk)."""
    roster: dict[int, dict[int, tuple[int, str]]] = defaultdict(dict)
    for spot in pbp.get("rosterSpots", []):
        team_id = spot.get("teamId")
        jersey = spot.get("sweaterNumber")
        pid = spot.get("playerId")
        if team_id is None or jersey is None or pid is None:
            continue
        first = spot.get("firstName", {}).get("default", "")
        last = spot.get("lastName", {}).get("default", "")
        roster[team_id][jersey] = (pid, f"{first} {last}".strip())

    away_id = pbp.get("awayTeam", {}).get("id")
    home_id = pbp.get("homeTeam", {}).get("id")

    rows = []
    neg_id = -1   # synthetic shift_id counter; see sign-convention note above
    n_unresolved = 0
    for tag, team_id, team_ab in (("TH", home_id, home_ab),
                                  ("TV", away_id, away_ab)):
        if team_id is None:
            continue
        html = fetch_text(
            html_shift_report_url(game_id, tag),
            f"{game_id}_{tag}_shiftreport.html",
        )
        if html is None:
            continue
        for r in parse_html_shift_report(html, is_playoffs):
            entry = roster.get(team_id, {}).get(r["jersey"])
            if entry is None:
                # Jersey number didn't resolve against this game's roster
                # (e.g. an emergency call-up not in rosterSpots). Skipped
                # and counted -- never silently guessed at an identity.
                n_unresolved += 1
                continue
            pid, name = entry
            rows.append((
                game_id, neg_id, pid, name, team_ab, r["period"],
                r["shift_number"], r["start"], r["end"],
                clock_to_seconds(r["end"]) - clock_to_seconds(r["start"]), now,
            ))
            neg_id -= 1

    if n_unresolved:
        print(f"  NOTE game {game_id}: {n_unresolved} HTML shift rows had "
            f"an unresolvable jersey number and were dropped.")

    conn.executemany(
        "INSERT OR REPLACE INTO shifts VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    return len(rows)


def parse_shifts(game_id: int, shifts_json: dict | None, conn: sqlite3.Connection,
                  now: str, valid_teams: set | None = None) -> int:
    """Parse the shift-chart feed into the `shifts` table.

    Filters out typeCode 505 rows: these are zero-duration goal/event
    annotation rows the feed mixes in alongside real shifts (typeCode 517).
    Confirmed against a live sample before writing this filter -- see design
    note 10 in the module docstring.

    Returns the number of real shift rows written -- v2.1 uses this to
    decide whether the HTML fallback needs to run for this game.

    v2.3: valid_teams (the game's two team abbrevs) filters out rows the
    NHL's own feed misfiles under the wrong game id. Found in exactly two
    games across nine seasons of data: 2025020565 (an entire other game's
    shifts -- 36 foreign players -- filed under this game's id) and
    2021020513 (every real shift triplicated, one copy carrying a corrupted
    team label). Foreign-team rows are dropped and counted here; Script 1's
    roster-truth rule provides a second, stronger layer of defense (it also
    fixes wrong-but-VALID team labels, which this filter cannot see)."""
    if shifts_json is None:
        return 0
    rows = []
    n_foreign = 0
    for r in shifts_json.get("data", []):
        if r.get("typeCode") != 517:      # keep only real ice-time shifts
            continue
        if valid_teams and r.get("teamAbbrev") not in valid_teams:
            n_foreign += 1                # misfiled foreign-game row: drop
            continue
        name = f"{r.get('firstName', '')} {r.get('lastName', '')}".strip()
        rows.append((
            game_id, r.get("id"), r.get("playerId"), name, r.get("teamAbbrev"),
            r.get("period"), r.get("shiftNumber"), r.get("startTime"),
            r.get("endTime"), duration_to_seconds(r.get("duration")), now,
        ))
    if n_foreign:
        print(f"  NOTE game {game_id}: {n_foreign} shift rows carried a team "
            f"not in this game (NHL feed misfiling) and were dropped.")
    conn.executemany(
        "INSERT OR REPLACE INTO shifts VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    return len(rows)


def parse_game(game_id: int, conn: sqlite3.Connection, fetch_shifts: bool = True) -> bool:
    """Fetch + parse one game (boxscore + play-by-play + shift chart) into the DB.
    Returns True on success. Boxscore/play-by-play calls are free (served from
    the on-disk cache) for any game already parsed under v1 -- only the shift
    chart is genuinely new network traffic for the existing backlog."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    box = fetch_json(f"{API_BASE}/gamecenter/{game_id}/boxscore",
                     f"{game_id}_boxscore.json")
    pbp = fetch_json(f"{API_BASE}/gamecenter/{game_id}/play-by-play",
                     f"{game_id}_pbp.json")
    if box is None:
        return False

    away, home = box["awayTeam"]["abbrev"], box["homeTeam"]["abbrev"]

    # --- play-by-play: single pass building all four event tables -------------
    # (v1 only built goal_rows here; v2 adds shot/penalty/faceoff rows in the
    # same loop rather than re-scanning plays four times.)
    a1_count: dict[int, int] = {}
    a2_count: dict[int, int] = {}
    goal_rows, shot_rows, penalty_rows, faceoff_rows = [], [], [], []
    if pbp is not None:
        for play in pbp.get("plays", []):
            t = play.get("typeDescKey")
            det = play.get("details", {})
            period = play.get("periodDescriptor", {}).get("number")
            tip = play.get("timeInPeriod")
            sit = play.get("situationCode")
            eid = play.get("eventId")

            if t == "goal":
                a1 = det.get("assist1PlayerId")
                a2 = det.get("assist2PlayerId")
                if a1:
                    a1_count[a1] = a1_count.get(a1, 0) + 1
                if a2:
                    a2_count[a2] = a2_count.get(a2, 0) + 1
                # v1 table (unchanged): keyed by loop-order index, not eventId,
                # to exactly preserve the original schema/behavior.
                goal_rows.append((
                    game_id, len(goal_rows), period, tip, sit,
                    det.get("scoringPlayerId"), a1, a2,
                    det.get("eventOwnerTeamId"), now,
                ))
                shot_rows.append((
                    game_id, eid, period, tip, sit, "goal",
                    det.get("zoneCode"), det.get("xCoord"), det.get("yCoord"),
                    det.get("shotType"), det.get("scoringPlayerId"), None,
                    det.get("goalieInNetId"), det.get("eventOwnerTeamId"), now,
                ))
            elif t in ("shot-on-goal", "missed-shot"):
                shot_rows.append((
                    game_id, eid, period, tip, sit, t,
                    det.get("zoneCode"), det.get("xCoord"), det.get("yCoord"),
                    det.get("shotType"), det.get("shootingPlayerId"), None,
                    det.get("goalieInNetId"), det.get("eventOwnerTeamId"), now,
                ))
            elif t == "blocked-shot":
                shot_rows.append((
                    game_id, eid, period, tip, sit, t,
                    det.get("zoneCode"), det.get("xCoord"), det.get("yCoord"),
                    det.get("shotType"), det.get("shootingPlayerId"),
                    det.get("blockingPlayerId"), None,
                    det.get("eventOwnerTeamId"), now,
                ))
            elif t == "penalty":
                penalty_rows.append((
                    game_id, eid, period, tip, sit,
                    det.get("typeCode"), det.get("descKey"), det.get("duration"),
                    det.get("committedByPlayerId"), det.get("drawnByPlayerId"),
                    det.get("eventOwnerTeamId"), now,
                ))
            elif t == "faceoff":
                faceoff_rows.append((
                    game_id, eid, period, tip, sit, det.get("zoneCode"),
                    det.get("winningPlayerId"), det.get("losingPlayerId"),
                    det.get("eventOwnerTeamId"), now,
                ))

    # --- shift chart: separate API host, see design note 9 --------------------
    shifts_json = None
    if fetch_shifts:
        shifts_json = fetch_json(
            f"{SHIFT_API_BASE}/shiftcharts?cayenneExp=gameId={game_id}",
            f"{game_id}_shifts.json",
        )

    # --- game row ---------------------------------------------------------- (v1, unchanged)
    conn.execute(
        "INSERT OR REPLACE INTO games VALUES (?,?,?,?,?,?,?,?,?,?)",
        (game_id, str(box["season"]), box["gameType"], box["gameDate"],
         away, home,
         box["awayTeam"].get("score"), box["homeTeam"].get("score"),
         box.get("periodDescriptor", {}).get("periodType"), now),
    )

    # --- skater + goalie rows ------------------------------------------------ (v1, unchanged)
    for side, team, opp, is_home in (("awayTeam", away, home, 0),
                                     ("homeTeam", home, away, 1)):
        stats = box["playerByGameStats"][side]
        for p in stats.get("forwards", []) + stats.get("defense", []):
            pid = p["playerId"]
            conn.execute(
                "INSERT OR REPLACE INTO skater_games VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (game_id, pid, p.get("name", {}).get("default"), team, opp,
                 is_home, p.get("position"),
                 p.get("goals"), p.get("assists"),
                 a1_count.get(pid, 0) if pbp else None,   # NULL if pbp missing,
                 a2_count.get(pid, 0) if pbp else None,   # so absence is explicit
                 p.get("points"), p.get("plusMinus"), p.get("pim"),
                 p.get("sog"), p.get("hits"), p.get("blockedShots"),
                 p.get("giveaways"), p.get("takeaways"),
                 p.get("powerPlayGoals"), p.get("faceoffWinningPctg"),
                 toi_to_minutes(p.get("toi")), p.get("shifts"), now),
            )
        for p in stats.get("goalies", []):
            conn.execute(
                "INSERT OR REPLACE INTO goalie_games VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (game_id, p["playerId"], p.get("name", {}).get("default"),
                 team, opp, is_home,
                 1 if p.get("starter") else 0,
                 p.get("shotsAgainst"), p.get("saves"), p.get("goalsAgainst"),
                 p.get("evenStrengthShotsAgainst"), p.get("powerPlayShotsAgainst"),
                 p.get("shorthandedShotsAgainst"), p.get("evenStrengthGoalsAgainst"),
                 p.get("powerPlayGoalsAgainst"), p.get("shorthandedGoalsAgainst"),
                 toi_to_minutes(p.get("toi")), now),
            )

    # --- goal_events (v1, unchanged) ------------------------------------------
    for row in goal_rows:
        conn.execute("INSERT OR REPLACE INTO goal_events VALUES (?,?,?,?,?,?,?,?,?,?)",
                     row)

    # --- new v2 tables ---------------------------------------------------------
    conn.executemany(
        "INSERT OR REPLACE INTO shot_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        shot_rows,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO penalty_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        penalty_rows,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO faceoff_events VALUES (?,?,?,?,?,?,?,?,?,?)",
        faceoff_rows,
    )
    n_real_shifts = parse_shifts(game_id, shifts_json, conn, now,
                                 valid_teams={away, home})
    if fetch_shifts and n_real_shifts == 0 and pbp is not None:
        # v2.1: the JSON shiftcharts endpoint returned nothing for this
        # game -- fall back to the legacy HTML reports. See the v2.1
        # changelog entry in the module docstring for why this exists and
        # how it was verified (25/25 sample games recovered; cross-checked
        # against box-score TOI at 0.00 min mean/max difference).
        fetch_and_parse_html_shifts(
            game_id, away, home, pbp, box["gameType"] == 3, conn, now
        )

    conn.commit()
    return True


# ----------------------------------------------------------------------------
# Validation harness (mirrors the cap-space scraper's internal-checks pattern)
# ----------------------------------------------------------------------------
def validate(conn: sqlite3.Connection) -> None:
    print("\n=== VALIDATION ===")
    q = lambda sql: conn.execute(sql).fetchall()

    # 1. Season coverage: games per season vs known schedule sizes.        (v1)
    print("\n[1] Games per season (expect ~1271/1312 reg; 1082 in 2019-20, 868 in 2020-21):")
    for season, gt, n in q("SELECT season, game_type, COUNT(*) FROM games "
                           "GROUP BY season, game_type ORDER BY season, game_type"):
        print(f"    {season} type{gt}: {n}")

    # 2. A1+A2 must equal boxscore assists wherever play-by-play was available. (v1)
    bad = q("SELECT COUNT(*) FROM skater_games "
            "WHERE a1 IS NOT NULL AND (a1 + a2) != assists")[0][0]
    tot = q("SELECT COUNT(*) FROM skater_games WHERE a1 IS NOT NULL")[0][0]
    print(f"\n[2] A1/A2 vs boxscore assist reconciliation: {bad} mismatches "
          f"of {tot} rows ({(bad/tot*100 if tot else 0):.3f}%)")

    # 3. Sum of player goals per team-game must equal team score net of SO.  (v1)
    bad = q("""
        SELECT COUNT(*) FROM (
          SELECT s.game_id, s.team, SUM(s.goals) pg,
                 CASE WHEN s.team = g.away_team THEN g.away_score ELSE g.home_score END ts,
                 g.last_period lp
          FROM skater_games s JOIN games g USING (game_id)
          GROUP BY s.game_id, s.team
        ) WHERE pg != ts AND NOT (lp = 'SO' AND ts - pg = 1)
    """)[0][0]
    print(f"[3] Player-goal sums vs team scores (SO-adjusted): {bad} mismatched team-games")

    # 4. Missing TOI (distinguishes data gaps from true zeros).             (v1)
    miss = q("SELECT COUNT(*) FROM skater_games WHERE toi_minutes IS NULL")[0][0]
    print(f"[4] Skater rows with missing TOI: {miss}")

    # 5. Mid-season-split smoke test: players appearing for 2+ teams in a season. (v1)
    n = q("""SELECT COUNT(*) FROM (
             SELECT s.player_id, g.season FROM skater_games s
             JOIN games g USING (game_id) WHERE g.game_type = 2
             GROUP BY s.player_id, g.season
             HAVING COUNT(DISTINCT s.team) >= 2)""")[0][0]
    print(f"[5] Multi-team skater-seasons captured (the split the project needs): {n}")

    # ============================ NEW IN v2 =================================

    # 6. shot_events: the 'goal' rows in shot_events must exactly match
    #    goal_events row-for-row (both come from the same 'goal' plays parsed
    #    in the same loop -- any mismatch means a bug in the v2 shot_rows logic).
    a = q("SELECT COUNT(*) FROM shot_events WHERE shot_result='goal'")[0][0]
    b = q("SELECT COUNT(*) FROM goal_events")[0][0]
    print(f"\n[6] shot_events goal rows ({a}) vs goal_events rows ({b}): "
          f"{'OK match' if a == b else 'MISMATCH -- investigate'}")

    # 7. shot_events coverage by type -- sanity-check the mix looks like hockey
    #    (goals should be a small minority of all shot attempts).
    print("[7] shot_events by result type:")
    for res, n in q("SELECT shot_result, COUNT(*) FROM shot_events GROUP BY shot_result"):
        print(f"    {res}: {n}")

    # 8. penalty_events: drawn_by should be non-null for the large majority of
    #    standard penalties (bench minors/too-many-men lack an individual drawer).
    tot_p = q("SELECT COUNT(*) FROM penalty_events")[0][0]
    null_drawn = q("SELECT COUNT(*) FROM penalty_events WHERE drawn_by_player_id IS NULL")[0][0]
    print(f"[8] Penalty rows: {tot_p} total, {null_drawn} with no drawn_by "
          f"({(null_drawn/tot_p*100 if tot_p else 0):.1f}% -- expect a small minority, "
          f"mostly bench/too-many-men)")

    # 9. shifts coverage + a rough TOI reconciliation: summed shift duration
    #    per player-game should be close to the boxscore toi_minutes for that
    #    player-game. This is the key cross-check that on-ice reconstruction
    #    will be built on later, so it is worth checking now rather than after.
    covered = q("""SELECT COUNT(*) FROM (
                    SELECT DISTINCT s.game_id, s.player_id
                    FROM skater_games s
                    JOIN shifts sh ON sh.game_id = s.game_id AND sh.player_id = s.player_id)""")[0][0]
    total_sk = q("SELECT COUNT(*) FROM skater_games")[0][0]
    print(f"[9a] skater_games rows with >=1 shift row: {covered} / {total_sk} "
          f"({(covered/total_sk*100 if total_sk else 0):.1f}%)")

    diffs = q("""
        SELECT AVG(ABS(s.toi_minutes - sh.sum_sec/60.0)) FROM skater_games s
        JOIN (SELECT game_id, player_id, SUM(duration_seconds) sum_sec
              FROM shifts GROUP BY game_id, player_id) sh
          ON sh.game_id = s.game_id AND sh.player_id = s.player_id
        WHERE s.toi_minutes IS NOT NULL
    """)[0][0]
    if diffs is not None:
        print(f"[9b] Mean |boxscore TOI - summed shift duration| across matched "
              f"player-games: {diffs:.2f} minutes (small values confirm shifts "
              f"and boxscore agree; large values flag a parsing issue)")
    else:
        print("[9b] No matched rows yet to reconcile (shifts not populated).")

    # 10. v2.1: HTML shift-report fallback usage. Rows recovered this way
    #     carry a NEGATIVE synthetic shift_id (see the v2.1 changelog entry
    #     in the module docstring) -- this makes provenance queryable
    #     without a schema change or a separate tracking table.
    n_html_games = q("SELECT COUNT(DISTINCT game_id) FROM shifts WHERE shift_id < 0")[0][0]
    n_html_rows = q("SELECT COUNT(*) FROM shifts WHERE shift_id < 0")[0][0]
    n_still_zero = q("""SELECT COUNT(*) FROM games g WHERE NOT EXISTS
                        (SELECT 1 FROM shifts s WHERE s.game_id = g.game_id)""")[0][0]
    print(f"\n[10] HTML shift-report fallback: {n_html_games} games recovered "
        f"this way, {n_html_rows} shift rows. Games still with ZERO shift "
        f"rows after both sources: {n_still_zero} "
        f"(expect near-zero -- investigate any that remain).")


def export_csv(conn: sqlite3.Connection) -> None:
    """Exports every table currently in the database to CSV.

    Two things worth knowing about this function:
    1. encoding="utf-8" on the open() call is a REQUIRED fix, not a nicety.
       Windows' default text encoding (cp1252) cannot represent every
       character that appears in NHL player names (e.g. Czech/Slovak
       characters like 'ě'), and crashes instead of silently mangling them.
       This fix was applied once already in an earlier session and was
       accidentally reverted when a later edit copied an older working copy
       of this file over the fixed one. Re-applied here; if this function
       is ever edited again, this line must survive the edit.
    2. Tables are read from sqlite_master rather than a hardcoded list, so
       any future new table exports automatically without editing this
       function again.
    """
    import csv
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for table in tables:
        path = OUT_DIR / f"{table}.csv"
        cur = conn.execute(f"SELECT * FROM {table}")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            w.writerows(cur)
        print(f"  wrote {path}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    print(f"nhl_gamelog_scraper.py {SCRIPT_VERSION}")
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="*", default=DEFAULT_SEASONS,
                    help="Season keys like 20232024")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--export-csv", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="Cap games per season (smoke testing)")
    ap.add_argument("--skip-shifts", action="store_true",
                    help="v1 behavior only -- do not fetch shift charts. "
                         "Restores the old 'done if in games table' resumability.")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if args.validate_only:
        validate(conn); return
    if args.export_csv:
        export_csv(conn); return

    for season in args.seasons:
        print(f"\n=== Season {season} ===")
        games = enumerate_games(season)
        if args.limit:
            games = games[: args.limit]

        # Resumability -- see design note 12 in the module docstring.
        # v1 only checked `games`; that would silently skip the shift-chart
        # backfill for every game already parsed under v1. v2 additionally
        # requires a `shifts` row before treating a game as fully done.
        games_done = {r[0] for r in conn.execute("SELECT game_id FROM games")}
        if args.skip_shifts:
            todo = [g for g in games if g["game_id"] not in games_done]
        else:
            shifts_done = {r[0] for r in conn.execute("SELECT DISTINCT game_id FROM shifts")}
            todo = [g for g in games
                   if g["game_id"] not in games_done or g["game_id"] not in shifts_done]

        print(f"  {len(todo)} to fetch/backfill ({len(games) - len(todo)} fully done)")
        for i, g in enumerate(todo, 1):
            ok = parse_game(g["game_id"], conn, fetch_shifts=not args.skip_shifts)
            if i % 100 == 0 or not ok:
                print(f"  [{i}/{len(todo)}] game {g['game_id']} {'ok' if ok else 'FAILED'}")

    validate(conn)
    export_csv(conn)
    print("\nDone. Outputs in", OUT_DIR.resolve())


if __name__ == "__main__":
    main()
