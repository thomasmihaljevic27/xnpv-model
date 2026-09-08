"""
ep_extract.py (v2) — Elite Prospects production + bio extraction for the
non-roster pillar, with a trade-asset filter on the bio pass.

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
    pip install TopDownHockey_Scraper pandas openpyxl
    python ep_extract.py                    # full run
    python ep_extract.py --bio-only         # only fill missing bios
    python ep_extract.py --no-asset-filter  # bios for ALL scraped players
                                            # (the v1 behavior; very slow)

Outputs:
    ep_cache/             raw per-(league, season) CSVs (provenance archive)
    ep_prospects.db       SQLite database, three tables:
        ep_skater_seasons   one row per skater-league-season-team
        ep_goalie_seasons   one row per goalie-league-season-team
        ep_player_bio       one row per player, keyed by ep_player_id, with
                            the draft string parsed into draft_year /
                            draft_round / draft_overall / draft_team
"""

import argparse
import datetime
import os
import re
import sqlite3
import sys
import time

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

import TopDownHockey_Scraper.TopDownHockey_EliteProspects_Scraper as tdhepscrape

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
LEAGUES = [
    "ohl", "whl", "qmjhl",        # Canadian major junior (CHL)
    "ushl",                        # US junior
    "ncaa",                        # US college
    "ahl",                         # primary NHL feeder
    "khl", "shl", "liiga",        # top European pro
    "nl",                          # Swiss National League (EP slug is "nl", not "nla")
    "del",                         # Germany
    "czechia",                     # Czech Extraliga (EP renamed the slug from "extraliga")
]

# --- 2. Seasons ---------------------------------------------------------------
# Back-test starts 2018; prospects moved in 2018+ trades were drafted roughly
# 2011 onward, and the pedigree layer needs D-1 through D+2 seasons, so
# production reaches back to 2010-11.
FIRST_SEASON_START = 2010
LAST_SEASON_START = 2025
SEASONS = [f"{y}-{y+1}" for y in range(FIRST_SEASON_START, LAST_SEASON_START + 1)]

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
    scraper = (tdhepscrape.get_skaters if player_type == "skaters"
               else tdhepscrape.get_goalies)
    try:
        df = scraper(league, season)
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
    """EP ids already present in ep_player_bio (the per-player bio cache)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ep_player_bio'"
    )
    if cur.fetchone() is None:
        return set()
    return {int(r[0]) for r in cur.execute(
        "SELECT DISTINCT ep_player_id FROM ep_player_bio "
        "WHERE ep_player_id IS NOT NULL")}


def run_bio_pass(conn: sqlite3.Connection, asset_filter: bool) -> None:
    """
    Fetch bios in batches, committing each batch so an interruption loses at
    most one batch of work.

    With the asset filter ON (default): targets are the trade-asset EP ids.
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
        target_ids = [i for i in assets["ep_player_id"].tolist() if i not in done]
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

        # get_player_information only reads the `link` column of its input.
        batch_df = pd.DataFrame({"link": [link_for[i] for i in batch_ids]})
        try:
            bio = tdhepscrape.get_player_information(batch_df)
        except Exception as exc:                   # noqa: BLE001
            print(f"  !! bio batch failed: {exc} — committed batches are safe; "
                  f"rerun to resume")
            break

        if bio is None or len(bio) == 0:
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

        append_aligned(bio, "ep_player_bio", conn)
        conn.commit()
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
    for table in ("ep_skater_seasons", "ep_goalie_seasons", "ep_player_bio"):
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
    args = parser.parse_args()

    asset_filter = not args.no_asset_filter
    if asset_filter and not os.path.exists(TRADE_EXPORT_PATH):
        sys.exit(f"Trade export not found at '{TRADE_EXPORT_PATH}'. Set "
                 f"TRADE_EXPORT_PATH at the top of this script, or run with "
                 f"--no-asset-filter.")

    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = get_connection()
    try:
        if not args.bio_only:
            run_production_pass(conn)
        run_bio_pass(conn, asset_filter)
        run_audit(conn, asset_filter)
    finally:
        conn.close()
    print("\nDone.")


if __name__ == "__main__":
    sys.exit(main())
