"""
ep_extract.py (v3) — Elite Prospects production + bio extraction for the
non-roster pillar, with a trade-asset filter on the bio pass.

v3 (2026-09-28), three changes, each for the prospect model's fitting sample
rather than just the traded prospects:
  (a) LEAGUES widened from 12 to 34. The added leagues are every league in
      nhle_temporal.csv that is a regular route to the draft or to the NHL at
      ages 16-22 (Russian, Swedish, Finnish, Czech and Slovak second tiers and
      junior leagues, the US national development program, Canadian junior A,
      US high school and prep, the NAHL and the ECHL). Every added slug was
      checked to load on EP on 2026-09-28. A league with no NHLe factor is
      useless to the model, so none was added.
  (b) Seasons now start in 2006-07 (was 2010-11). The draft curve fits the
      2007-2017 classes; a 2007 draftee's draft season is 2006-07, and
      nhle_temporal.csv starts there too. Stopping at 2010 would have left
      the four oldest fitting classes without their junior seasons.
  (c) A DRAFT PASS reads EP's NHL Entry Draft page for each year (one page
      per draft lists every pick with its EP player id) into
      ep_draft_selections. That table is the EP side of the EP-to-NHL id
      bridge (ep_nhl_bridge.py joins it to the NHL Records draft on draft
      year + overall pick). The bio pass now also covers every drafted player
      by default, so the bridge can check birthdates, not just names.

Pulls junior / college / European / minor-league production and player bios
(including draft slot) via Patrick Bacon's TopDownHockey_Scraper package, and
stores everything in a local SQLite database with scrape-date provenance.

Design principles (matching the project's standing rules):
  1. CACHED       — every (league, season) production pull is saved to a raw
                    CSV before anything else; bios are cached per player in
                    SQLite. Re-running never re-scrapes data already in hand.
                    Safe to interrupt and restart at any time.
  2. RATE-LIMITED — polite pauses between requests, on top of the package's
                    own built-in 403 backoff.
  3. PROVENANCED  — every row carries scrape_date, source, and package
                    version. Cached data keeps its ORIGINAL scrape date.
  4. ID-BASED JOINS — the numeric Elite Prospects player id is extracted from
                    every link and used as the join key everywhere. The
                    PuckPedia trade export carries `eliteprospects_id`
                    natively (99.9% coverage on 2018+ trade assets), so the
                    trade-asset filter is an ID join, NOT a name match. The
                    four known same-name collisions are kept only as an audit
                    tripwire.
  5. TRADE-ASSET FILTER (v2) — the bio pass fetches bios ONLY for players who
                    appear as assets in the PuckPedia trade export (~1,055
                    players), not for every player in every scraped league
                    (tens of thousands). Bios for trade assets are fetched
                    even when the player never appears in the scraped
                    production tables, by constructing the EP link directly
                    from the id — so bio coverage of the asset universe is
                    complete regardless of league coverage.
  6. POINT-IN-TIME WARNING — the bio fields `rights` and `status` are
                    as-of-scrape-date ONLY, stored as rights_AS_OF_SCRAPE /
                    status_AS_OF_SCRAPE so misuse is visible in any query.
                    Never classify historical roster status from them.

Usage:
    pip install TopDownHockey_Scraper pandas openpyxl beautifulsoup4
    python 20_CODE/ep_extract.py                    # full run: draft, production, bios
    python 20_CODE/ep_extract.py --draft-only       # only the draft pages (~22 requests)
    python 20_CODE/ep_extract.py --bio-only         # only fill missing bios
    python 20_CODE/ep_extract.py --bio-scope assets # bios for trade assets only (v2 scope)
    python 20_CODE/ep_extract.py --no-asset-filter  # bios for ALL scraped players
                                                    # (the v1 behavior; very slow)

Run time (v3 full run): 34 leagues x 20 seasons x 2 player types is 1,360
league-season pulls, each several pages, with 15 s between pulls: plan on
10-14 hours. Every pull is cached, so it can be stopped and restarted freely.

Outputs (under OUTPUT_DIR/ep_out/):
    ep_cache/             raw per-(league, season) CSVs and per-year draft
                          pages (provenance archive)
    ep_prospects.db       SQLite database, four tables:
        ep_skater_seasons   one row per skater-league-season-team
        ep_goalie_seasons   one row per goalie-league-season-team
        ep_player_bio       one row per player, keyed by ep_player_id, with
                            the draft string parsed into draft_year /
                            draft_round / draft_overall / draft_team
        ep_draft_selections one row per NHL Entry Draft pick on EP: draft_year,
                            draft_round, draft_overall, team, ep_player_id
"""

import argparse
import datetime
import os
import re
import sqlite3
import sys
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

import TopDownHockey_Scraper.TopDownHockey_EliteProspects_Scraper as tdhepscrape

SCRIPT_VERSION = "3.5"   # printed on every run (stale-file guard)
# v3.5 (2026-10-08): the bio pause is back to 4 seconds (Thomas); the 10 of
# v3.3 answered a block that was the package's false alarm.
# v3.4 (2026-10-08): bios are read by this script's read_bio_page(), not the
# package's get_info(). get_info() treats any first paragraph containing
# "evil" as EP's block page; "Belleville" does, so David Clarkson's page
# (drafted by the Belleville Bulls) was retried forever under a false
# "403 Error". A block is now read from the status code only, and a real
# one stops the pass after about 10 minutes instead of looping.
# v3.3 (2026-10-05): the bio pause is 10 seconds a player (was 4). With 4,
# EP refused the run after 9 players, then on its first request; the earlier
# unpaced run's ~850 requests likely still counted against the connection.
# v3.2 (2026-10-05): the bio pass reads one player at a time through the
# package's get_info() with a 4-second pause after each, instead of calling
# get_player_information(), which has no pause; EP blocked the first batch
# after 48 players. One Ctrl+C now saves the batch read so far and stops.
# v3.1 (2026-09-28): league-season pages are read by this script's own
# read_league_season(), not the package's get_skaters / get_goalies. The
# package's clean-up step writes the text "FW" into a true/false column, which
# pandas 3 refuses ("Invalid value 'FW' for dtype 'bool'"), so every league
# pull failed after the pages had been read. The page requests and table
# selection are unchanged; only the clean-up is ours.

try:
    from importlib.metadata import version as _pkg_version
    PACKAGE_VERSION = _pkg_version("TopDownHockey_Scraper")
except Exception:
    PACKAGE_VERSION = "unknown"

# =============================================================================
# CONFIGURATION — edit these blocks; nothing below should need touching.
# =============================================================================

# --- 1. Leagues -------------------------------------------------------------
# EP league slugs, exactly as in eliteprospects.com/league/<slug>/stats/<season>.
# Verify each slug loads in a browser before a full run; a wrong slug returns
# a 404, which the package reports and skips (no crash, but no data).
# Cross-check against the league list in nhle_temporal.csv. After the first
# full run, the audit lists trade-asset players with no production rows —
# their development leagues are the candidates to add here.
# Rule for inclusion (v3): the league has era-varying factors in
# nhle_temporal.csv AND it is a regular route to the draft or the NHL for
# players aged 16-22. Every slug below matches a league name in
# nhle_temporal.csv exactly, so production joins to its factor with no
# crosswalk. Leagues deliberately left out: under-18 and younger levels
# (factors of 0.03 or less, and the draft-season line is what the model reads),
# and small European pro leagues (Denmark, Norway, Belarus, France, Austria's
# second tier, Germany's DEL2) that send almost no one to the draft. The
# post-run audit lists trade assets with no production rows; if a pattern
# shows up there, add that league.
LEAGUES = [
    # --- v2 leagues (unchanged) ---
    "ohl", "whl", "qmjhl",        # Canadian major junior (CHL)
    "ushl",                        # US junior
    "ncaa",                        # US college
    "ahl",                         # primary NHL feeder
    "khl", "shl", "liiga",        # top European pro
    "nl",                          # Swiss National League (EP slug is "nl", not "nla")
    "del",                         # Germany
    "czechia",                     # Czech Extraliga (EP renamed the slug from "extraliga")
    # --- added v3: European second tiers, where drafted Europeans play at 18-21 ---
    "vhl",                         # Russia second tier (2010-11 onward)
    "russia2",                     # Russia second tier before the VHL (2006-07 to 2013-14 on EP)
    "hockeyallsvenskan",           # Sweden second tier
    "mestis",                      # Finland second tier
    "czechia2",                    # Czech second tier
    "slovakia",                    # Slovak top league
    "sl",                          # Swiss League (second tier)
    "icehl",                       # Austrian-based ICE league
    # --- added v3: European junior leagues (the draft season for most Europeans) ---
    "mhl",                         # Russia junior (2009-10 onward)
    "u20-nationell",               # Sweden J20
    "u20-sm-sarja",                # Finland U20
    "czechia-u20",                 # Czech U20 (EP has no 2019-20 table; skipped cleanly)
    # --- added v3: North American development routes ---
    "ntdp",                        # US National Team Development Program
    "bchl", "ajhl", "ojhl", "cchl", "sjhl",   # Canadian junior A
    "nahl",                        # US tier-2 junior
    "ushs-mn", "ushs-prep",       # US high school: Minnesota, prep schools
    "echl",                        # pro feeder below the AHL
]

# --- 2. Seasons ---------------------------------------------------------------
# v3: 2006-07 onward. The draft curve fits the 2007-2017 classes, and the
# prospect model's fade rate has to be estimated on those finished careers,
# so their draft seasons (D-0 = 2006-07 for the 2007 class) must be in hand.
# nhle_temporal.csv starts in 2006-07 as well, so earlier seasons could not
# be converted anyway. (v2 started at 2010-11, enough for the traded
# prospects but not for the fitting sample.)
FIRST_SEASON_START = 2006
LAST_SEASON_START = 2025
SEASONS = [f"{y}-{y+1}" for y in range(FIRST_SEASON_START, LAST_SEASON_START + 1)]

# --- 2b. Draft years for the draft pass -----------------------------------------
# Matches draft_pick_linkage.csv (NHL Records, 2005-2026).
DRAFT_YEARS = list(range(2005, 2027))
SLEEP_BETWEEN_DRAFT_PAGES = 5      # seconds

# --- 3. Paths (from .env; see .env.example) ----------------------------------
EP_OUT_DIR = os.path.join(os.environ["OUTPUT_DIR"], "ep_out")   # generated EP subtree
CACHE_DIR = os.path.join(EP_OUT_DIR, "ep_cache")
AUDIT_NO_PROD_PATH = os.path.join(EP_OUT_DIR, "audit_assets_without_production.csv")
DB_PATH = os.environ["EP_PROSPECTS_DB"]
# The PuckPedia trade export (drives the trade-asset filter). Set
# PUCKPEDIA_TRADES_XLSX in .env to the local path of the export.
TRADE_EXPORT_PATH = os.environ["PUCKPEDIA_TRADES_XLSX"]
TRADE_EXPORT_SHEET = "trade_export"

# --- 4. Politeness ------------------------------------------------------------
SLEEP_BETWEEN_LEAGUE_SEASONS = 15  # seconds between league-season pulls
BIO_BATCH_SIZE = 100               # players per bio batch; each batch commits,
                                   # so an interruption loses at most one batch
SLEEP_BETWEEN_BIO_BATCHES = 30     # seconds between bio batches
SLEEP_BETWEEN_BIO_REQUESTS = 4     # seconds after each player's bio page (4 in v3.2,
                                   # 10 in v3.3-3.4, back to 4 in v3.5 on Thomas's
                                   # say). The "blocks" behind the 10 were the
                                   # package's false alarm on "Belleville" (see
                                   # read_bio_page), not EP refusing requests.
BIO_BLOCK_WAIT = 120               # seconds to wait after a real 403/429 from EP
BIO_BLOCK_RETRIES = 5              # real 403/429s in a row on one player before the
                                   # pass stops (about 10 minutes of waiting)
BIO_MAX_SKIPS_IN_A_ROW = 5         # unreadable pages in a row before the pass stops

# --- Same-name collisions (audit tripwire only; joins here are ID-based) ------
KNOWN_NAME_COLLISIONS = {
    "sebastian aho", "elias pettersson", "connor murphy", "josh anderson",
}

SOURCE_LABEL = "eliteprospects.com via TopDownHockey_Scraper"
EP_ID_PATTERN = re.compile(r"/player/(\d+)")


def extract_ep_id(link) -> int | None:
    """Pull the numeric EP player id out of any EP player link/url."""
    if link is None:
        return None
    m = EP_ID_PATTERN.search(str(link))
    return int(m.group(1)) if m else None


# =============================================================================
# SQLite helpers
# =============================================================================

def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    EP stats-table headers are read off the live page, so column names can
    vary across leagues and over time. Normalize into safe, stable SQLite
    identifiers: lowercase, symbols spelled out, spaces -> underscores.
    """
    rename = {}
    for col in df.columns:
        new = str(col).strip().lower()
        new = new.replace("+/-", "plus_minus")
        new = new.replace("%", "_pct")
        new = new.replace("/", "_per_")
        new = re.sub(r"[^a-z0-9_]+", "_", new)
        new = re.sub(r"_+", "_", new).strip("_")
        rename[col] = new
    return df.rename(columns=rename)


def append_aligned(df: pd.DataFrame, table: str, conn: sqlite3.Connection) -> None:
    """
    Append a dataframe to a SQLite table even when their column sets differ
    (one league's stats page may carry a column another's doesn't): ALTER the
    table to add new columns, then reindex the dataframe to the table's full
    column set (missing columns become NULL) before inserting.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if cur.fetchone() is None:
        df.to_sql(table, conn, index=False)
        return
    existing_cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
    for col in df.columns:
        if col not in existing_cols:
            cur.execute(f'ALTER TABLE {table} ADD COLUMN "{col}" TEXT')
            existing_cols.append(col)
    df = df.reindex(columns=existing_cols)
    df.to_sql(table, conn, index=False, if_exists="append")


def delete_league_season(table: str, league: str, season: str,
                         conn: sqlite3.Connection) -> None:
    """
    Idempotency for production tables: clear a (league, season) block before
    inserting it, so re-runs can never create duplicates.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if cur.fetchone() is not None:
        cur.execute(
            f"DELETE FROM {table} WHERE league = ? AND season = ?",
            (league, season),
        )
        conn.commit()


# =============================================================================
# Trade-asset universe (drives the bio filter)
# =============================================================================

def load_trade_assets(path: str) -> pd.DataFrame:
    """
    Read the PuckPedia trade export and return one row per unique player
    asset: ep_player_id, puckpedia_player_id, player_name.

    Rows with a player_id are player assets (pick rows carry draft_pick_id
    instead). eliteprospects_id coverage on 2018+ assets is 99.9%; the
    remainder (a nameless junk row in the May 2026 export) is reported and
    skipped.
    """
    df = pd.read_excel(path, sheet_name=TRADE_EXPORT_SHEET)
    players = df[df["player_id"].notna()].copy()

    players["player_name"] = (
        players["first_name"].fillna("").astype(str).str.strip() + " " +
        players["last_name"].fillna("").astype(str).str.strip()
    ).str.strip()

    uniq = players.drop_duplicates("player_id")[
        ["player_id", "eliteprospects_id", "player_name"]
    ].rename(columns={"player_id": "puckpedia_player_id",
                      "eliteprospects_id": "ep_player_id"})

    missing = uniq[uniq["ep_player_id"].isna()]
    if len(missing):
        print(f"  !! {len(missing)} trade-asset player(s) have no eliteprospects_id "
              f"and are excluded from the bio pass:")
        for _, r in missing.iterrows():
            print(f"     puckpedia_player_id={r['puckpedia_player_id']} "
                  f"name='{r['player_name']}'")

    uniq = uniq[uniq["ep_player_id"].notna()].copy()
    uniq["ep_player_id"] = uniq["ep_player_id"].astype(int)
    print(f"  trade-asset universe: {len(uniq)} players with EP ids")
    return uniq


# =============================================================================
# Production pull (skaters + goalies), with CSV cache
# =============================================================================

SLEEP_BETWEEN_PAGES = 1            # seconds between pages of one league-season
MAX_PAGES = 99                     # hard stop; the largest leagues run ~15 pages
PLAYER_POS_PATTERN = re.compile(r"^(?P<name>.*?)\s*\((?P<pos>[^)]*)\)\s*$")


def _find_stats_table(soup, kind):
    """The stats table, picked by its header row (same rule as the package's
    private helper, copied so a package update cannot move it). EP's 2025
    redesign removed the old table classes."""
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).upper() for th in table.find_all("th")]
        if kind == "skaters" and "TP" in headers and "GP" in headers:
            return table
        if kind == "goalies" and "GAA" in headers and "SV%" in headers:
            return table
    return None


def _get_with_backoff(url: str):
    """GET with the package's 403 behaviour (EP throttles with 403): wait
    100 s and retry, at most five times."""
    for _ in range(5):
        resp = requests.get(url, timeout=120)
        if resp.status_code != 403:
            return resp
        print("  .. 403 from EP; sleeping 100 s")
        time.sleep(100)
    return resp


def read_league_season(player_type: str, league: str, season: str) -> pd.DataFrame | None:
    """
    Every row of one league-season stats table, all pages.

    Pages: /league/<slug>/stats/<season>?page=N for skaters, with
    &tab=goalies for goalies. Reading stops at the first page with no stats
    table (EP serves an empty page past the last one). A row is kept only if
    it has as many cells as the header and a non-blank first cell (the rank);
    EP puts blank spacer rows between blocks. The player link is the first
    /player/ link IN THAT ROW, so a row can never be paired with another row's
    player (the package paired them by position across the whole table).
    One row per player per league-season: a player who played for two teams
    in the league appears once, with Team = "totals" and his combined line
    (checked 2026-09-28: 45 such rows in OHL 2019-20, e.g. Philip Tomasino,
    62 GP). That is the season total the NHLe factors apply to.
    """
    tab = "&tab=goalies" if player_type == "goalies" else ""
    rows, header = [], None
    for page in range(1, MAX_PAGES + 1):
        url = f"https://www.eliteprospects.com/league/{league}/stats/{season}?page={page}{tab}"
        resp = _get_with_backoff(url)
        if resp.status_code == 404:
            print(f"  !! 404 for {league} {season}: league-season not on EP")
            return None
        table = _find_stats_table(BeautifulSoup(resp.content, "html.parser"), player_type)
        if table is None:
            break                                  # past the last page
        trs = table.find_all("tr")
        header = [th.get_text(strip=True) for th in trs[0].find_all("th")]
        n_before = len(rows)
        for tr in trs[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) != len(header) or not cells[0]:
                continue
            rec = dict(zip(header, cells))
            rec["link"] = next((a["href"] for a in tr.find_all("a", href=True)
                                if "/player/" in a["href"]), None)
            rec["page"] = page
            rows.append(rec)
        if len(rows) == n_before:
            break                                  # a table with no player rows
        time.sleep(SLEEP_BETWEEN_PAGES)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df = df.drop(columns=[c for c in ("#",) if c in df.columns])
    # "Marco Rossi (C)" -> name + position. Goalie rows carry no position.
    parsed = df["Player"].str.extract(PLAYER_POS_PATTERN)
    df["playername"] = parsed["name"].fillna(df["Player"]).str.strip()
    df["position"] = parsed["pos"] if player_type == "skaters" else "G"
    df["season"] = season
    df["league"] = league
    # Guard: the same player-team twice means pages overlapped.
    dup = df.duplicated(["link", "Team"]).sum()
    if dup:
        print(f"  !! {league} {season}: {dup} repeated player-team rows dropped "
              f"(pages overlapped)")
        df = df.drop_duplicates(["link", "Team"])
    return df


def fetch_production(player_type: str, league: str, season: str) -> pd.DataFrame | None:
    """
    Return the production dataframe for one (player_type, league, season),
    serving from cache when available and scraping (then caching) when not.
    scrape_date is stamped at pull time and frozen into the cache file, so a
    later reload reports the ORIGINAL pull date.
    """
    cache_file = os.path.join(CACHE_DIR, f"{player_type}_{league}_{season}.csv")

    if os.path.exists(cache_file):
        print(f"  [cache] {player_type} {league} {season}")
        return pd.read_csv(cache_file, dtype=str)

    print(f"  [scrape] {player_type} {league} {season}")
    try:
        df = read_league_season(player_type, league, season)
    except Exception as exc:                       # noqa: BLE001 — log and move on
        print(f"  !! scrape failed for {league} {season}: {exc}")
        return None

    if df is None or len(df) == 0:
        # Package prints its own 404 message for nonexistent league-seasons.
        # Do NOT cache an empty file, so a corrected slug retries cleanly.
        print(f"  !! no data returned for {league} {season} (bad slug or no coverage?)")
        return None

    df = normalize_columns(df)
    # ID-based join key, extracted from the player link.
    df["ep_player_id"] = df["link"].apply(extract_ep_id)

    df["scrape_date"] = datetime.date.today().isoformat()
    df["source"] = SOURCE_LABEL
    df["package_version"] = PACKAGE_VERSION

    df.to_csv(cache_file, index=False)
    time.sleep(SLEEP_BETWEEN_LEAGUE_SEASONS)
    return df


def run_production_pass(conn: sqlite3.Connection) -> None:
    """Loop every (league, season) for both player types and load into SQLite."""
    for player_type, table in (("skaters", "ep_skater_seasons"),
                               ("goalies", "ep_goalie_seasons")):
        print(f"\n=== Production pass: {player_type} ===")
        for league in LEAGUES:
            for season in SEASONS:
                df = fetch_production(player_type, league, season)
                if df is None:
                    continue
                delete_league_season(table, league, season, conn)
                append_aligned(df, table, conn)
                conn.commit()


# =============================================================================
# Draft pass (v3): one EP page per NHL Entry Draft -> ep_draft_selections
# =============================================================================
#
# Page layout (checked 2026-09-28 on the 2015 draft): a single <table> whose
# rows are either a round header ("Round 1") or a pick: "#<overall>", a
# /team/ link, a /player/<ep_id>/ link with text "Name ( F )", then career
# NHL totals. The career totals are NOT stored: they are as of the scrape and
# would leak later seasons into anything that read them.
#
# The page is cached as raw HTML, so a parser fix never needs a re-scrape.

OVERALL_PATTERN = re.compile(r"^#\s*(\d+)$")
ROUND_PATTERN = re.compile(r"^Round\s+(\d+)$", re.IGNORECASE)
POS_PATTERN = re.compile(r"^(?P<name>.*?)\s*\(\s*(?P<pos>[^)]*)\)\s*$")


def fetch_draft_page(year: int) -> str | None:
    """Return the EP draft page HTML for one year, from cache or the web."""
    cache_file = os.path.join(CACHE_DIR, f"draft_nhl-entry-draft_{year}.html")
    if os.path.exists(cache_file):
        print(f"  [cache] draft {year}")
        with open(cache_file, encoding="utf-8") as f:
            return f.read()
    url = f"https://www.eliteprospects.com/draft/nhl-entry-draft/{year}"
    print(f"  [scrape] draft {year}")
    for attempt in range(3):
        resp = requests.get(url, timeout=120)
        if resp.status_code == 200:
            break
        print(f"  !! HTTP {resp.status_code} on {url}; sleeping 100 s")
        time.sleep(100)
    else:
        return None
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(resp.text)
    time.sleep(SLEEP_BETWEEN_DRAFT_PAGES)
    return resp.text


def parse_draft_page(html: str, year: int) -> pd.DataFrame:
    """One row per pick. A pick with no player link (forfeited or void) is
    kept with ep_player_id = NULL so the slot count still reconciles."""
    soup = BeautifulSoup(html, "html.parser")
    rows, current_round = [], None
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if not cells:
            continue
        m_round = ROUND_PATTERN.match(cells[0])
        if m_round and len(cells) == 1:
            current_round = int(m_round.group(1))
            continue
        m_overall = OVERALL_PATTERN.match(cells[0])
        if not m_overall:
            continue                              # the header row
        player_link = next((a["href"] for a in tr.find_all("a", href=True)
                            if "/player/" in a["href"]), None)
        team_link = next((a for a in tr.find_all("a", href=True)
                          if "/team/" in a["href"]), None)
        player_text = cells[2] if len(cells) > 2 else ""
        m_pos = POS_PATTERN.match(player_text)
        rows.append({
            "draft_year": year,
            "draft_round": current_round,
            "draft_overall": int(m_overall.group(1)),
            "draft_team": team_link.get_text(" ", strip=True) if team_link else None,
            "ep_player_id": extract_ep_id(player_link),
            "player_name_ep": (m_pos.group("name") if m_pos else player_text) or None,
            "position_ep": m_pos.group("pos").strip() if m_pos else None,
            "link": player_link,
        })
    return pd.DataFrame(rows)


def run_draft_pass(conn: sqlite3.Connection) -> None:
    print("\n=== Draft pass: NHL Entry Draft pages ===")
    for year in DRAFT_YEARS:
        html = fetch_draft_page(year)
        if html is None:
            print(f"  !! draft {year}: no page; skipped")
            continue
        df = parse_draft_page(html, year)
        if df.empty:
            print(f"  !! draft {year}: page parsed to 0 picks -- layout change? "
                  f"Inspect the cached HTML before trusting this table.")
            continue
        # Guard: overall numbers must be 1..N with no gaps or repeats.
        expected = list(range(1, int(df["draft_overall"].max()) + 1))
        if sorted(df["draft_overall"].tolist()) != expected:
            print(f"  !! draft {year}: overall numbers are not a clean 1..N "
                  f"sequence; kept, but flag before use")
        df["scrape_date"] = datetime.date.today().isoformat()
        df["source"] = "eliteprospects.com/draft/nhl-entry-draft (direct)"
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='ep_draft_selections'")
        if cur.fetchone() is not None:
            cur.execute("DELETE FROM ep_draft_selections WHERE draft_year = ?", (year,))
        append_aligned(df, "ep_draft_selections", conn)
        conn.commit()
        print(f"  draft {year}: {len(df)} picks, "
              f"{df['ep_player_id'].notna().sum()} with an EP id")


def drafted_ep_ids(conn: sqlite3.Connection) -> set[int]:
    """Every EP id in ep_draft_selections (empty set if the pass has not run)."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='ep_draft_selections'")
    if cur.fetchone() is None:
        return set()
    return {int(r[0]) for r in cur.execute(
        "SELECT DISTINCT ep_player_id FROM ep_draft_selections "
        "WHERE ep_player_id IS NOT NULL")}


# =============================================================================
# Bio pull, filtered to the trade-asset universe, cached per player in SQLite
# =============================================================================

DRAFT_PATTERN = re.compile(
    r"^(?P<year>\d{4})\s+round\s+(?P<round>\d+)\s+#(?P<overall>\d+)\s+overall\s+by\s+(?P<team>.+)$"
)


def parse_draft_string(raw: str) -> dict:
    """
    Parse the package's draft string, format:
        "{year} round {round} #{overall} overall by {teamName}"
    with "-" meaning undrafted. Anything unparseable is kept raw and flagged,
    never silently dropped.

    Known edge case: a re-drafted player has multiple draft selections on EP;
    the package returns only the FIRST. The raw string is retained so
    re-entries can be audited manually.
    """
    out = {"draft_year": None, "draft_round": None,
           "draft_overall": None, "draft_team": None, "draft_parse_flag": None}
    if raw is None or str(raw).strip() in ("-", "", "nan"):
        out["draft_parse_flag"] = "undrafted_or_missing"
        return out
    m = DRAFT_PATTERN.match(str(raw).strip())
    if m:
        out["draft_year"] = int(m.group("year"))
        out["draft_round"] = int(m.group("round"))
        out["draft_overall"] = int(m.group("overall"))
        out["draft_team"] = m.group("team").strip()
        out["draft_parse_flag"] = "ok"
    else:
        out["draft_parse_flag"] = "UNPARSED"
    return out


def production_links_by_ep_id(conn: sqlite3.Connection) -> dict[int, str]:
    """Map ep_player_id -> a full slugged EP link found in the production tables."""
    links: dict[int, str] = {}
    cur = conn.cursor()
    for table in ("ep_skater_seasons", "ep_goalie_seasons"):
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if cur.fetchone() is None:
            continue
        for ep_id, link in cur.execute(
            f"SELECT DISTINCT ep_player_id, link FROM {table} "
            f"WHERE ep_player_id IS NOT NULL AND link IS NOT NULL"
        ):
            links[int(ep_id)] = str(link)
    return links


def bios_already_stored(conn: sqlite3.Connection) -> set[int]:
    """
    EP ids already present in ep_player_bio (the per-player bio cache).

    v3.4: a row whose player name is EP's page title ("Elite Prospects - ...")
    is the package's fallback for a page with no player data, every other
    field a dash. It does not count as stored, so the next run fetches that
    player again and run_bio_pass replaces the blank row (one such row on
    2026-10-08: EP id 95853, Josh Anderson).
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ep_player_bio'"
    )
    if cur.fetchone() is None:
        return set()
    return {int(r[0]) for r in cur.execute(
        "SELECT DISTINCT ep_player_id FROM ep_player_bio "
        f"WHERE ep_player_id IS NOT NULL AND player NOT LIKE '{BLANK_BIO_NAME}%'")}


# The package stores EP's page title as the name when a page has no player data.
BLANK_BIO_NAME = "Elite Prospects - "

BIO_COLUMNS = ["player", "rights", "status", "dob", "height", "weight",
               "birthplace", "nation", "shoots", "draft", "link"]


class BioBlocked(Exception):
    """EP kept answering 403/429 for one player past BIO_BLOCK_RETRIES."""


class BioUnreadable(Exception):
    """The page came back but holds no player record (404, or no player JSON)."""


def read_bio_page(link: str) -> tuple:
    """
    Request one player's EP page and read his bio, returning the same 11
    fields, in the same order and the same text forms, as the package's
    get_info() (TopDownHockey_Scraper 6.1.69).

    v3.4: replaces get_info(). get_info() takes any page whose first <p>
    contains the letters "evil" to be EP's block page, prints "403 Error" and
    retries every 60 seconds with no limit. "Belleville" contains "evil", so a
    player whose page opens with an OHL draft line "by Belleville Bulls"
    (David Clarkson, EP id 11018) was retried forever on a page that loaded
    fine (status 200). Every stall of the bio pass on 2026-10-05 to 10-08 was
    this. Here a block is read only from the status code, a real 403 or 429
    waits BIO_BLOCK_WAIT seconds and is retried BIO_BLOCK_RETRIES times, and
    then the pass stops (BioBlocked) instead of looping.

    The fields are read from the page's __NEXT_DATA__ JSON exactly as
    get_info() reads them (checked against the package on stored players).
    One difference: where get_info() would fall back to the page title and
    store dashes for every other field, this raises BioUnreadable and the
    player is skipped, so a rerun tries him again instead of keeping a
    blank bio.
    """
    import json

    url = link if link.startswith("http") else "https://www.eliteprospects.com" + link
    for attempt in range(BIO_BLOCK_RETRIES + 1):
        page = requests.get(url, timeout=60)
        if page.status_code not in (403, 429):
            break
        if attempt == BIO_BLOCK_RETRIES:
            raise BioBlocked(f"status {page.status_code} {BIO_BLOCK_RETRIES + 1} times on {url}")
        print(f"    EP answered {page.status_code}; waiting {BIO_BLOCK_WAIT} s "
              f"(try {attempt + 1} of {BIO_BLOCK_RETRIES})")
        time.sleep(BIO_BLOCK_WAIT)
    if page.status_code != 200:
        raise BioUnreadable(f"status {page.status_code}")

    soup = BeautifulSoup(page.content, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    try:
        next_data = json.loads(tag.string) if tag else {}
        p = next_data.get("props", {}).get("pageProps", {}).get("playerData", {}).get("player", {})
    except (json.JSONDecodeError, AttributeError):
        p = {}
    if not p:
        raise BioUnreadable("no player record in the page's __NEXT_DATA__")

    # From here, field by field as in get_info(); "-" means missing.
    player = p.get("name", "-")
    nhl_rights = p.get("nhlRights")
    if nhl_rights and isinstance(nhl_rights, dict):
        team_obj = nhl_rights.get("team", {})
        rights = team_obj.get("name", "-") if team_obj else "-"
        status = nhl_rights.get("rights", "-")
    else:
        rights = "-"
        status = "-"
    dob = p.get("dateOfBirth", "-") or "-"
    height_obj = p.get("height")
    height = (str(height_obj.get("metrics", "-"))
              if height_obj and isinstance(height_obj, dict) else "-")
    weight_obj = p.get("weight")
    weight = (str(weight_obj.get("metrics", "-"))
              if weight_obj and isinstance(weight_obj, dict) else "-")
    birthplace = p.get("placeOfBirth", "-") or "-"
    nation_obj = p.get("nationality") or p.get("nation")
    nation = (nation_obj.get("name", "-")
              if nation_obj and isinstance(nation_obj, dict) else "-")
    # As in get_info(): "catches" is read only when "shoots" is present but empty.
    shoots = p.get("shoots", "-") or p.get("catches", "-") or "-"
    # First draft selection only (a re-drafted player's later picks are not read).
    draft_data = (next_data.get("props", {}).get("pageProps", {})
                  .get("playerData", {}).get("playerDraftSelections", {}))
    draft_edges = draft_data.get("edges", []) if isinstance(draft_data, dict) else []
    if draft_edges:
        d = draft_edges[0]
        draft = (f"{d.get('year', '')} round {d.get('round', '')} "
                 f"#{d.get('overall', '')} overall by {d.get('teamName', '')}")
    else:
        draft = "-"
    # The link returned is the one passed in (ep_player_id is read from it).
    return (player, rights, status, dob, height, weight, birthplace, nation,
            shoots, draft, link)


def fetch_bio_batch(links: list[str]) -> tuple[pd.DataFrame, bool]:
    """
    Read one batch of bio pages, one player at a time, pausing
    SLEEP_BETWEEN_BIO_REQUESTS seconds after each.

    v3.2 replaced the package's get_player_information() (no pause between
    requests) with this loop; v3.4 reads each page with read_bio_page()
    instead of the package's get_info(), whose false "403" stalled the pass.

    A page with no player record is skipped with a warning and stays in the
    to-do list for the next run; BIO_MAX_SKIPS_IN_A_ROW such pages in a row
    stop the pass (that pattern looks like a block page, not a bad player).

    Returns (bios read so far, stop_after). stop_after is True when the loop
    ended early: Ctrl+C, a connection error, a real block, or too many skips.
    The caller saves the partial batch and stops, so nothing read is lost.
    """
    rows = []
    stop_after = False
    skips_in_a_row = 0
    for n, link in enumerate(links, start=1):
        try:
            result = read_bio_page(link)
        except KeyboardInterrupt:
            print(f"  Ctrl+C: stopping after {len(rows)} players in this batch")
            stop_after = True
            break
        except BioBlocked as exc:
            print(f"  !! EP is refusing requests: {exc}. Try again in a few hours.")
            stop_after = True
            break
        except BioUnreadable as exc:
            skips_in_a_row += 1
            print(f"    {n}/{len(links)} SKIPPED {link}: {exc}")
            if skips_in_a_row >= BIO_MAX_SKIPS_IN_A_ROW:
                print(f"  !! {skips_in_a_row} unreadable pages in a row; stopping")
                stop_after = True
                break
            continue
        except (requests.exceptions.RequestException, ConnectionError,
                ValueError) as exc:
            # The same errors the package's own loop stopped on.
            print(f"  !! bio request failed on {link}: {exc}")
            stop_after = True
            break
        skips_in_a_row = 0
        rows.append(result)
        print(f"    {n}/{len(links)} {result[0]}")
        try:
            time.sleep(SLEEP_BETWEEN_BIO_REQUESTS)
        except KeyboardInterrupt:
            print(f"  Ctrl+C: stopping after {len(rows)} players in this batch")
            stop_after = True
            break
    return pd.DataFrame(rows, columns=BIO_COLUMNS), stop_after


def run_bio_pass(conn: sqlite3.Connection, asset_filter: bool,
                 include_drafted: bool = True) -> None:
    """
    Fetch bios in batches, committing each batch so an interruption loses at
    most one batch of work.

    With the asset filter ON (default): targets are the trade-asset EP ids,
    plus (v3, unless --bio-scope assets) every drafted player found by the
    draft pass, about 4,700 more. The drafted players' birthdates are what
    lets ep_nhl_bridge.py check each draft-slot match against the NHL record.
    For a player present in the production tables we use his full slugged
    link; otherwise we construct the link from the id alone
    (eliteprospects.com/player/<id> — EP redirects to the slugged page), so
    every trade asset gets a bio regardless of league coverage.

    With the filter OFF (--no-asset-filter): targets are every unique player
    in the production tables (v1 behavior — tens of thousands of requests).
    """
    prod_links = production_links_by_ep_id(conn)
    done = bios_already_stored(conn)

    if asset_filter:
        assets = load_trade_assets(TRADE_EXPORT_PATH)
        wanted = list(dict.fromkeys(assets["ep_player_id"].tolist()))
        if include_drafted:
            drafted = sorted(drafted_ep_ids(conn) - set(wanted))
            print(f"  drafted players added to the bio targets: {len(drafted)}")
            wanted += drafted
        target_ids = [i for i in wanted if i not in done]
        link_for = {
            i: prod_links.get(i, f"https://www.eliteprospects.com/player/{i}")
            for i in target_ids
        }
        constructed = sum(1 for i in target_ids if i not in prod_links)
        print(f"\n=== Bio pass (trade-asset filter ON): {len(target_ids)} players need bios "
              f"({constructed} not in production tables; using constructed links) ===")
    else:
        target_ids = [i for i in prod_links if i not in done]
        link_for = {i: prod_links[i] for i in target_ids}
        print(f"\n=== Bio pass (filter OFF): {len(target_ids)} players need bios ===")

    if not target_ids:
        return

    for start in range(0, len(target_ids), BIO_BATCH_SIZE):
        batch_ids = target_ids[start:start + BIO_BATCH_SIZE]
        print(f"  bio batch {start // BIO_BATCH_SIZE + 1}: {len(batch_ids)} players")

        bio, stop_after = fetch_bio_batch([link_for[i] for i in batch_ids])

        if bio is None or len(bio) == 0:
            if stop_after:
                break
            continue

        bio = normalize_columns(bio)
        bio["ep_player_id"] = bio["link"].apply(extract_ep_id)

        # Loud renames: these describe the player TODAY, not at a trade date.
        bio = bio.rename(columns={"rights": "rights_AS_OF_SCRAPE",
                                  "status": "status_AS_OF_SCRAPE"})

        parsed = bio["draft"].apply(parse_draft_string).apply(pd.Series)
        bio = pd.concat([bio, parsed], axis=1).rename(columns={"draft": "draft_raw"})

        bio["scrape_date"] = datetime.date.today().isoformat()
        bio["source"] = SOURCE_LABEL
        bio["package_version"] = PACKAGE_VERSION

        # Replace any blank (title-only) row already stored for these players,
        # so a refetched player keeps one row. Only blank rows are deleted.
        ids = [int(i) for i in bio["ep_player_id"].dropna()]
        if ids:
            conn.execute(
                f"DELETE FROM ep_player_bio WHERE player LIKE '{BLANK_BIO_NAME}%' "
                f"AND ep_player_id IN ({','.join('?' * len(ids))})", ids)
        append_aligned(bio, "ep_player_bio", conn)
        conn.commit()
        if stop_after:
            print(f"  {len(bio)} bios from the stopped batch are saved; "
                  f"rerun to resume from the next player")
            break
        time.sleep(SLEEP_BETWEEN_BIO_BATCHES)


# =============================================================================
# Post-run audit
# =============================================================================

def run_audit(conn: sqlite3.Connection, asset_filter: bool) -> None:
    """
    Row counts, draft-parse health, the collision tripwire, and — with the
    asset filter on — league-coverage gaps: trade assets whose production
    never appears in the scraped leagues/seasons. Those names tell you which
    leagues to consider adding to LEAGUES (or whether the player is simply a
    veteran whose junior seasons predate FIRST_SEASON_START, which is fine —
    rostered players are valued from WAR.csv, not from EP production).
    """
    cur = conn.cursor()
    print("\n=== Audit ===")
    for table in ("ep_skater_seasons", "ep_goalie_seasons", "ep_player_bio",
                  "ep_draft_selections"):
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if cur.fetchone() is None:
            print(f"  {table}: (not created)")
            continue
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n} rows")

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ep_player_bio'"
    )
    if cur.fetchone() is not None:
        bad = cur.execute(
            "SELECT COUNT(*) FROM ep_player_bio WHERE draft_parse_flag = 'UNPARSED'"
        ).fetchone()[0]
        if bad:
            print(f"  !! {bad} draft strings UNPARSED — inspect: "
                  f"SELECT player, draft_raw FROM ep_player_bio "
                  f"WHERE draft_parse_flag='UNPARSED'")

        placeholders = ",".join("?" for _ in KNOWN_NAME_COLLISIONS)
        rows = cur.execute(
            f"SELECT player, ep_player_id FROM ep_player_bio "
            f"WHERE LOWER(TRIM(player)) IN ({placeholders})",
            tuple(KNOWN_NAME_COLLISIONS),
        ).fetchall()
        if rows:
            print(f"  note: {len(rows)} bio rows match known same-name collisions. "
                  f"Joins in this pipeline are ID-based and unaffected, but flag "
                  f"these in any later NAME-based join (e.g., to WAR.csv):")
            for player, ep_id in rows:
                print(f"     {player}  ep_player_id={ep_id}")

    if asset_filter and os.path.exists(TRADE_EXPORT_PATH):
        assets = load_trade_assets(TRADE_EXPORT_PATH)
        prod_ids = set(production_links_by_ep_id(conn))
        no_prod = assets[~assets["ep_player_id"].isin(prod_ids)]
        if len(no_prod):
            print(f"\n  {len(no_prod)} trade-asset players have NO rows in the "
                  f"scraped production tables (league-coverage gaps or pre-"
                  f"{FIRST_SEASON_START} juniors). Sample:")
            for _, r in no_prod.head(25).iterrows():
                print(f"     {r['player_name']}  ep_player_id={r['ep_player_id']}")
            os.makedirs(EP_OUT_DIR, exist_ok=True)
            no_prod.to_csv(AUDIT_NO_PROD_PATH, index=False)
            print(f"     full list written to {AUDIT_NO_PROD_PATH}")


# =============================================================================
# Entry point
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="EP production + bio extraction")
    parser.add_argument("--bio-only", action="store_true",
                        help="skip the production pass; only fill missing bios")
    parser.add_argument("--no-asset-filter", action="store_true",
                        help="fetch bios for ALL scraped players, not just "
                             "trade assets (very slow)")
    parser.add_argument("--draft-only", action="store_true",
                        help="run only the draft pass (about 22 page requests)")
    parser.add_argument("--bio-scope", choices=["assets+drafted", "assets"],
                        default="assets+drafted",
                        help="bio targets under the asset filter (default: "
                             "trade assets plus every drafted player)")
    args = parser.parse_args()

    print(f"ep_extract.py SCRIPT_VERSION {SCRIPT_VERSION} | package "
          f"{PACKAGE_VERSION} | {len(LEAGUES)} leagues | seasons "
          f"{SEASONS[0]}..{SEASONS[-1]} | drafts {DRAFT_YEARS[0]}..{DRAFT_YEARS[-1]}")

    asset_filter = not args.no_asset_filter
    if asset_filter and not args.draft_only and not os.path.exists(TRADE_EXPORT_PATH):
        sys.exit(f"Trade export not found at '{TRADE_EXPORT_PATH}'. Set "
                 f"PUCKPEDIA_TRADES_XLSX in .env, or run with --no-asset-filter.")

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    try:
        if args.draft_only:
            run_draft_pass(conn)
            run_audit(conn, asset_filter=False)
            return
        if not args.bio_only:
            run_draft_pass(conn)
            run_production_pass(conn)
        run_bio_pass(conn, asset_filter,
                     include_drafted=(args.bio_scope == "assets+drafted"))
        run_audit(conn, asset_filter)
    finally:
        conn.close()
    print("\nDone.")


if __name__ == "__main__":
    sys.exit(main())
