"""
ep_age_scraper.py
=================
Recover BIRTHDATES for the WAR players that age_join.py could not match to the
PuckPedia export (mostly pre-2018 retirees absent from the current contract
file). It resolves each name to an Elite Prospects player and pulls the exact
date of birth, producing a name -> birthdate file that slots into age_join.py
as a SECOND birthdate source so the aging curve can be fit on the full 2007-2025
history rather than only 2018+ players.

WHY THIS IS A SEPARATE SCRIPT FROM ep_extract.py
------------------------------------------------
ep_extract.py is ID-BASED: it already knows each player's Elite Prospects id
(from PuckPedia's eliteprospects_id column) and fetches bios from those ids.
These players are exactly the ones with NO PuckPedia row, so we have no EP id to
start from. This script adds the missing front half: NAME -> EP id resolution.
Once an id is found, only the birthdate is needed, so it reads the two EP
endpoints directly (both verified working) rather than depending on the heavier
TopDownHockey bio scrape.

THE TWO EP ENDPOINTS (both verified)
------------------------------------
1. Autocomplete (one cheap JSON call per name):
       https://autocomplete.eliteprospects.com/all?q=<name>
   Returns candidate players with: id, fullname, slug, position (F/D/G),
   `age` (which is actually the BIRTH YEAR), team, experience (e.g. "NHL"),
   and _type ("player"/"staff").
2. Player page (one call per RESOLVED player):
       https://www.eliteprospects.com/player/<id>/<slug>
   Its JSON-LD carries the exact DOB as  "birthDate":"YYYY-MM-DD".

HOW A NAME IS RESOLVED (the disambiguation that makes this safe)
---------------------------------------------------------------
Many names return multiple people (e.g. ten "Aaron Miller"s). Each candidate is
scored, and the winner must clear a confidence bar:
  * POSITION must match the WAR position group (F or D)         -> +2
  * EXPERIENCE contains "NHL" (our players are all NHLers)      -> +3
  * AGE PLAUSIBLE: (last NHL season - birth year) in [16, 46]   -> +1
The correct player in testing always carried NHL experience and the right
position; decoys (junior/Euro namesakes) did not. A match is tagged:
  * "ok"        - one clear winner with NHL experience + right position
  * "review"    - a best guess was taken but it is weak (no NHL tag, position
                  mismatch, or a near-tie). DOB is still fetched and USABLE, but
                  the row is also written to a review file for a human glance.
  * "unmatched" - no acceptable candidate (no birthdate produced)
  * "dob_fail"  - resolved an id but the page DOB could not be parsed (the
                  autocomplete birth YEAR is kept as a fallback)

MATCHING THE PROJECT'S STANDING RULES
-------------------------------------
  * CACHED / RESUMABLE - every resolved name is written to SQLite immediately;
    re-running skips names already done. Safe to interrupt (Ctrl-C) and restart.
  * RATE-LIMITED        - a polite pause between requests, with exponential
    backoff on 403/429 (EP blocks aggressive scraping). If blocked past the
    retry budget the script saves progress and exits cleanly; just rerun later.
  * PROVENANCED         - every row carries source and scrape_date.
  * NAME-JOIN HYGIENE   - the output is keyed on the EXACT WAR `Player` string,
    so age_join.py can map it back with no fuzzy step. The four known same-name
    collisions are not expected here (they are 2018+ players, already matched in
    PuckPedia) but are tagged "review" automatically if they appear.

USAGE
-----
    pip install requests pandas
    python3 ep_age_scraper.py                 # full run (resumable)
    python3 ep_age_scraper.py --limit 25      # smoke test on first 25 names
Inputs : age_join_misses.csv  (produced by age_join.py: Player, Position,
                                last_season_seen)
Outputs: ep_ages.db            SQLite cache (resumable source of truth)
         ep_birthdates.csv     name -> birthdate, for the age_join.py join
         ep_ages_review.csv    weak/ambiguous/unmatched rows for manual eyes
         ep_age_scraper_log.txt  run summary
"""

import argparse
import datetime
import re
import sqlite3
import sys
import time
import unicodedata

import pandas as pd
import requests

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
MISSES_PATH = "age_join_misses.csv"
DB_PATH = "ep_ages.db"
OUT_BIRTHDATES = "ep_birthdates.csv"
OUT_REVIEW = "ep_ages_review.csv"
LOG_PATH = "ep_age_scraper_log.txt"

AUTOCOMPLETE_URL = "https://autocomplete.eliteprospects.com/all"
PLAYER_URL = "https://www.eliteprospects.com/player/{id}/{slug}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"

SLEEP_BETWEEN = 2.5          # polite seconds between requests
BACKOFF_SCHEDULE = [30, 60, 120, 240]   # seconds to wait on 403/429 before retry
PLAUSIBLE_MIN_AGE = 16       # (last NHL season - birth year) lower bound
PLAUSIBLE_MAX_AGE = 46       # upper bound

BIRTHDATE_RE = re.compile(r'"birthDate":"(\d{4}-\d{2}-\d{2})"')
SOURCE_LABEL = "eliteprospects.com (autocomplete + player page)"


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def norm(name):
    """Loose key for comparing names (accents/case/punctuation removed)."""
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"\(.*?\)", "", s).lower().replace("-", " ").replace("'", "").replace(".", "")
    return re.sub(r"\s+", " ", s).strip()


def ep_position_group(pos):
    """Map an EP position string to the WAR F/D/G grouping."""
    if not pos:
        return None
    p = str(pos).upper()
    if p.startswith("G"):
        return "G"
    if p.startswith("D"):
        return "D"
    return "F"   # F, C, LW, RW, W all collapse to forward


class Blocked(Exception):
    """Raised when EP keeps refusing past the backoff budget."""


def http_get(session, url, params=None):
    """GET with exponential backoff on 403/429. Returns a Response or raises Blocked."""
    for wait in [0] + BACKOFF_SCHEDULE:
        if wait:
            print(f"    blocked (waiting {wait}s before retry)...")
            time.sleep(wait)
        resp = session.get(url, params=params, timeout=25)
        if resp.status_code == 200:
            return resp
        if resp.status_code not in (403, 429):
            return resp   # other errors (e.g. 404) handled by caller
    raise Blocked(f"still blocked after backoff: {url}")


# ----------------------------------------------------------------------------
# resolution + DOB
# ----------------------------------------------------------------------------
def autocomplete(session, name):
    """Return the list of candidate dicts EP offers for a name query."""
    resp = http_get(session, AUTOCOMPLETE_URL, params={"q": name})
    if resp.status_code != 200:
        return []
    try:
        return resp.json()
    except ValueError:
        return []


def score_candidate(cand, war_pos, last_season):
    """Score one autocomplete candidate against the WAR player we are seeking."""
    score, notes = 0, []
    if cand.get("_type") != "player":
        return -99, ["not-a-player"]
    if ep_position_group(cand.get("position")) == war_pos:
        score += 2
    else:
        notes.append("pos-mismatch")
    exp = str(cand.get("experience") or "")
    if "NHL" in exp.upper():
        score += 3
    else:
        notes.append("no-NHL-tag")
    by = cand.get("age")
    try:
        by = int(by)
        if PLAUSIBLE_MIN_AGE <= (int(last_season) - by) <= PLAUSIBLE_MAX_AGE:
            score += 1
        else:
            notes.append("age-implausible")
    except (TypeError, ValueError):
        notes.append("no-birth-year")
    return score, notes


def resolve_name(session, name, war_pos, last_season):
    """
    Resolve a WAR name to one EP candidate. Returns a dict describing the match
    (status, ep_id, slug, birth_year, n_candidates, confidence_notes).
    Tries the full name first, then a last-name-only query as a fallback.
    """
    for query in (name, name.split()[-1] if len(name.split()) > 1 else None):
        if query is None:
            continue
        cands = autocomplete(session, query)
        players = [c for c in cands if c.get("_type") == "player"]
        if not players:
            continue
        scored = sorted(((score_candidate(c, war_pos, last_season), c) for c in players),
                        key=lambda x: x[0][0], reverse=True)
        (best_score, best_notes), best = scored[0]
        runner = scored[1][0][0] if len(scored) > 1 else -99
        if best_score <= 0:
            continue                    # nothing credible from this query
        # confident only if the winner has the NHL tag and a clear lead
        status = "ok" if (best_score >= 5 and best_score - runner >= 2) else "review"
        return {
            "status": status, "ep_id": best.get("id"), "ep_slug": best.get("slug"),
            "ep_fullname": best.get("fullname"), "ep_position": best.get("position"),
            "ep_birth_year": best.get("age"), "n_candidates": len(players),
            "confidence": f"score={best_score};runner={runner};" + ",".join(best_notes),
        }
    return {"status": "unmatched", "ep_id": None, "ep_slug": None,
            "ep_fullname": None, "ep_position": None, "ep_birth_year": None,
            "n_candidates": 0, "confidence": "no-player-candidate"}


def fetch_birthdate(session, ep_id, slug):
    """Pull exact DOB ('YYYY-MM-DD') from a player's EP page, or None."""
    url = PLAYER_URL.format(id=ep_id, slug=slug or "")
    resp = http_get(session, url)
    if resp.status_code != 200:
        return None
    m = BIRTHDATE_RE.search(resp.text)
    return m.group(1) if m else None


# ----------------------------------------------------------------------------
# SQLite cache
# ----------------------------------------------------------------------------
CACHE_COLS = ["war_name", "war_position", "last_season_seen", "ep_id", "ep_slug",
              "ep_fullname", "ep_position", "ep_birth_year", "birthdate",
              "n_candidates", "status", "confidence", "source", "scrape_date"]


def init_cache(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ep_age_cache ("
        "war_name TEXT PRIMARY KEY, war_position TEXT, last_season_seen INTEGER, "
        "ep_id TEXT, ep_slug TEXT, ep_fullname TEXT, ep_position TEXT, "
        "ep_birth_year TEXT, birthdate TEXT, n_candidates INTEGER, status TEXT, "
        "confidence TEXT, source TEXT, scrape_date TEXT)")
    conn.commit()


def already_done(conn):
    return {r[0] for r in conn.execute("SELECT war_name FROM ep_age_cache")}


def upsert(conn, row):
    conn.execute(
        f"INSERT OR REPLACE INTO ep_age_cache ({','.join(CACHE_COLS)}) "
        f"VALUES ({','.join('?' for _ in CACHE_COLS)})",
        [row.get(c) for c in CACHE_COLS])
    conn.commit()


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="only process the first N un-done names (smoke test)")
    args = ap.parse_args()

    misses = pd.read_csv(MISSES_PATH)
    conn = sqlite3.connect(DB_PATH)
    init_cache(conn)
    done = already_done(conn)
    todo = misses[~misses["Player"].isin(done)]
    if args.limit:
        todo = todo.head(args.limit)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print(f"{len(misses)} misses total | {len(done)} already cached | "
          f"{len(todo)} to process this run")

    processed = 0
    try:
        for _, r in todo.iterrows():
            name = r["Player"]
            war_pos = r["Position"]
            last_season = r.get("last_season_seen")
            res = resolve_name(session, name, war_pos, last_season)
            time.sleep(SLEEP_BETWEEN)

            birthdate = None
            if res["ep_id"]:
                birthdate = fetch_birthdate(session, res["ep_id"], res["ep_slug"])
                time.sleep(SLEEP_BETWEEN)
                if res["status"] != "unmatched" and birthdate is None:
                    res["status"] = "dob_fail"

            upsert(conn, {
                "war_name": name, "war_position": war_pos,
                "last_season_seen": last_season, "ep_id": res["ep_id"],
                "ep_slug": res["ep_slug"], "ep_fullname": res["ep_fullname"],
                "ep_position": res["ep_position"], "ep_birth_year": res["ep_birth_year"],
                "birthdate": birthdate, "n_candidates": res["n_candidates"],
                "status": res["status"], "confidence": res["confidence"],
                "source": SOURCE_LABEL, "scrape_date": datetime.date.today().isoformat()})
            processed += 1
            # one line per player so the run is never silent; flush so it
            # appears immediately on Windows consoles.
            shown = birthdate or res.get("ep_birth_year") or "--"
            print(f"  [{processed}/{len(todo)}] {name[:26]:<26} {res['status']:<9} {shown}",
                  flush=True)
    except Blocked as exc:
        print(f"\n!! {exc}\n   Progress saved ({processed} this run). Rerun later to resume.")
    except KeyboardInterrupt:
        print(f"\n   Interrupted; {processed} saved this run. Rerun to resume.")

    # ---- export from the full cache ----
    cache = pd.read_sql_query("SELECT * FROM ep_age_cache", conn)
    conn.close()

    good = cache[cache["birthdate"].notna()][["war_name", "war_position", "ep_id",
            "ep_fullname", "birthdate", "status", "confidence", "source", "scrape_date"]]
    good.to_csv(OUT_BIRTHDATES, index=False)
    review = cache[cache["status"].isin(["review", "unmatched", "dob_fail"])]
    review.to_csv(OUT_REVIEW, index=False)

    log = [
        "=== ep_age_scraper run summary ===",
        f"misses in input        : {len(misses)}",
        f"cached (cumulative)    : {len(cache)}",
        f"  status 'ok'          : {(cache['status']=='ok').sum()}",
        f"  status 'review'      : {(cache['status']=='review').sum()}",
        f"  status 'dob_fail'    : {(cache['status']=='dob_fail').sum()}",
        f"  status 'unmatched'   : {(cache['status']=='unmatched').sum()}",
        f"birthdates produced    : {len(good)}  -> {OUT_BIRTHDATES}",
        f"rows needing review    : {len(review)}  -> {OUT_REVIEW}",
    ]
    print("\n".join(log))
    with open(LOG_PATH, "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    sys.exit(main())
