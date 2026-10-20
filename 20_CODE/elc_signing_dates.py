"""
elc_signing_dates.py -- when each player signed his first NHL contract (his entry-level deal).

WHY (Thomas, 2026-10-14: "all aging checks should be consistent")
    The CBA reads a player's entry-level length (9.1(b), age per 9.2) and his arbitration need
    (12.1(a), age per 12.1(c)) from his age on September 15 of the calendar year he SIGNS his
    first contract. Until now the code stood in his first NHL season for the signing year, which
    makes him older at signing (median three years from draft to first NHL season). This table
    supplies the real signing date where a source has it; pick_curve.py and rfa_terminal_value.py
    read it and fall back to the first NHL season only where it is missing (counted in each log).

v1.1 (2026-10-14, Thomas: "yes fetch"): --fetch requests capwages.com/players/<first-last> for each
drafted player (2007-2017 drafts) who played and has no date, 1.5 s apart, into 30_OUTPUT/capwages_elc/,
and keeps a page only if its draft line names his draft year and overall pick. Without --fetch nothing is
requested; the folder is read like the other caches.

SOURCES, in order (the first that has the player wins; agreement between them is reported)
    1. PuckPedia's contract export: the earliest `entry_level` contract's `signing_date`, by NHL id.
       Covers entry-level deals signed from 2014 on.
    2. CapWages player pages already cached: 10_SOURCE/capwages_cache/ (the clause scrape) and
       30_OUTPUT/capwages_top_picks/ (top_pick_control_look.py). The earliest "Entry-Level Contract
       ... Signing Date: Mon. D, YYYY" block. A page is used for a drafted player only if its
       "Drafted: YYYY Rd N (#P)" line names the same draft year and overall pick (a namesake's page
       is refused, as in top_pick_control_look.py). Pages are read, never fetched, by this script.

WHO: every player in draft_pick_linkage.csv with a WAR record (war_names; he played an NHL game),
plus every NHL id with a PuckPedia entry-level contract (players under contract, drafted or not).

OUTPUT: OUTPUT_DIR/elc_signing_dates.csv (nhl_id, draftYear, pick, player, signing_date, source,
signing_team (v1.2: the signing club, CapWages's "Signing Team" line where its year agrees, else PuckPedia's contract
club), signing_year), OUTPUT_DIR/elc_signing_dates_log.txt.
Run from the repo root:  python 20_CODE/elc_signing_dates.py
"""

import html as htmlmod
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "elc_signing_dates.py v1.3 (2026-10-19)"   # v1.3: dates after the first NHL season set aside; v1.2: club
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
F_LINK = OUTPUT_DIR / "draft_pick_linkage.csv"
F_PP = SOURCE_DIR / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.csv"
CACHE_FETCH = OUTPUT_DIR / "capwages_elc"           # v1.1: pages fetched by --fetch
CACHES = [SOURCE_DIR / "capwages_cache", OUTPUT_DIR / "capwages_top_picks", CACHE_FETCH]
UA = os.environ.get("SCRAPER_USER_AGENT", "xnpv-model/1.0 (academic research)")
OUT, OUT_LOG = OUTPUT_DIR / "elc_signing_dates.csv", OUTPUT_DIR / "elc_signing_dates_log.txt"
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def page_text(raw):
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)))


def drafted(txt):
    """(draft year, overall pick) from the page's draft line (top_pick_control_look.drafted)."""
    m = re.search(r"Drafted\s*:\s*(\d{4})\s+Rd\s+\d+\s+\(#(\d+)\)", txt)
    return (int(m.group(1)), int(m.group(2))) if m else None


def elc_signed(txt):
    """The earliest entry-level signing date on a page, or None. Each contract block reads
    '<Type> Contract Signed By: ... Signing Date: Mon. D, YYYY'; only Entry-Level blocks count."""
    dates = []
    for m in re.finditer(r"Entry-Level Contract(.{0,400}?)Signing Date:\s*([A-Z][a-z]{2})\.?\s+(\d{1,2}),\s+(\d{4})", txt):
        d = pd.to_datetime(f"{m.group(2)} {m.group(3)} {m.group(4)}", format="%b %d %Y", errors="coerce")
        if pd.notna(d):
            dates.append(d)
    return min(dates) if dates else None


# v1.2 (2026-10-18): the club he signed his entry-level deal with, as the NHL's three-letter code (relocated clubs keep
# their own code: ATL, PHX, UTA; pick_curve maps them to the franchise). CapWages writes the full name, PuckPedia a
# short code of its own for two clubs.
TEAM_CODES = {"Anaheim Ducks": "ANA", "Arizona Coyotes": "ARI", "Phoenix Coyotes": "PHX", "Atlanta Thrashers": "ATL",
              "Boston Bruins": "BOS", "Buffalo Sabres": "BUF", "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR",
              "Chicago Blackhawks": "CHI", "Colorado Avalanche": "COL", "Columbus Blue Jackets": "CBJ",
              "Dallas Stars": "DAL", "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM", "Florida Panthers": "FLA",
              "Los Angeles Kings": "LAK", "Minnesota Wild": "MIN", "Montreal Canadiens": "MTL",
              "Nashville Predators": "NSH", "New Jersey Devils": "NJD", "New York Islanders": "NYI",
              "New York Rangers": "NYR", "Ottawa Senators": "OTT", "Philadelphia Flyers": "PHI",
              "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS", "Seattle Kraken": "SEA", "St. Louis Blues": "STL",
              "Tampa Bay Lightning": "TBL", "Toronto Maple Leafs": "TOR", "Utah Hockey Club": "UTA",
              "Utah Mammoth": "UTA", "Vancouver Canucks": "VAN", "Vegas Golden Knights": "VGK",
              "Washington Capitals": "WSH", "Winnipeg Jets": "WPG"}
PP_CODES = {"NAS": "NSH", "WAS": "WSH"}


def elc_signed_team(txt):
    """v1.2: (signing date, club code) of the earliest entry-level block on a page, or (None, None). The block reads
    '... Signing Team: <club> Signing Date: Mon. D, YYYY'."""
    best = (None, None)
    for m in re.finditer(r"Entry-Level Contract(.{0,700}?)Signing Team:\s*([A-Z][A-Za-z\. ]+?)\s+Signing Date:\s*"
                         r"([A-Z][a-z]{2})\.?\s+(\d{1,2}),\s+(\d{4})", txt):
        d = pd.to_datetime(f"{m.group(3)} {m.group(4)} {m.group(5)}", format="%b %d %Y", errors="coerce")
        if pd.notna(d) and (best[0] is None or d < best[0]):
            best = (d, TEAM_CODES.get(m.group(2).strip()))
    return best


def first_nhl_seasons(link):
    """v1.3: {(draft year, pick): start year of his first season with an NHL game}, from the WAR tables under the
    linkage's names, as pick_curve.seasons_of reads them (accents stripped, letters and spaces; seasons from his draft
    on, so a namesake's earlier seasons cannot leak in)."""
    import unicodedata

    def norm(s):
        s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z ]", "", s.lower()).strip()
    tables = {}
    for gk, (f, col) in {False: ("WAR.csv", "Player"), True: ("Goalies_WAR.csv", "Goalie")}.items():
        w = pd.read_csv(SOURCE_DIR / f, usecols=[col, "Season", "GP"])
        w = w[w["GP"] > 0]
        w["n"], w["start"] = w[col].map(norm), w["Season"].map(lambda x: 2000 + int(str(x)[:2]))
        tables[gk] = w.groupby("n")["start"].apply(sorted).to_dict()
    out = {}
    for r in link[link["war_names"].notna()].itertuples():
        t = tables[str(r.is_goalie).strip().lower() == "true"]
        ys = [y for nm in str(r.war_names).split("|") for y in t.get(norm(nm), []) if y >= int(r.draftYear)]
        if ys:
            out[(int(r.draftYear), int(r.overallPickNumber))] = min(ys)
    return out


def to_slug(name):
    """capspace_capwages_compare.to_slug: first-last lowercase ASCII."""
    import unicodedata
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    n = re.sub(r"[^A-Za-z\- ]", "", n).strip().lower()
    return re.sub(r"\s+", "-", n)


def fetch_missing(link, pp_d, pages):
    """v1.1: fetch pages for drafted players (2007-2017) who played and have no date from either source."""
    import time
    import requests
    CACHE_FETCH.mkdir(exist_ok=True)
    want = link[link["war_names"].notna() & link["draftYear"].between(2007, 2017)]
    sess, fetched, refused, nodate = requests.Session(), 0, [], []
    for r in want.itertuples():
        key = (int(r.draftYear), int(r.overallPickNumber))
        nid = int(r.playerId) if pd.notna(r.playerId) else None
        if (nid is not None and nid in pp_d.index) or (key in pages and pages[key][1] is not None):
            continue
        f = CACHE_FETCH / f"{to_slug(r.playerName)}.html"
        if not f.exists():
            try:
                resp = sess.get(f"https://capwages.com/players/{f.stem}", headers={"User-Agent": UA}, timeout=20)
            except requests.RequestException as e:
                refused.append(f"{key} {r.playerName}: {type(e).__name__}")
                continue
            time.sleep(1.5)
            if resp.status_code != 200:
                refused.append(f"{key} {r.playerName}: HTTP {resp.status_code}")
                continue
            f.write_text(resp.text, encoding="utf-8")
            fetched += 1
        t = page_text(f.read_text(encoding="utf-8", errors="ignore"))
        if drafted(t) != key:                          # GUARD: a namesake's page is refused
            refused.append(f"{key} {r.playerName}: page drafted {drafted(t)}")
            continue
        sd = elc_signed(t)
        pages[key] = (f.name, sd, elc_signed_team(t)[1])
        if sd is None:
            nodate.append(f"{key} {r.playerName}")
    log(f"[fetch] requested {fetched} pages into {CACHE_FETCH}; refused {len(refused)}; "
        f"verified page without an entry-level signing date {len(nodate)}")
    for x in refused + [f"{x}: no entry-level block" for x in nodate]:
        log(f"     {x}")


def main(fetch=False):
    log(SCRIPT_VERSION)
    for k, p in {"linkage": F_LINK, "puckpedia": F_PP}.items():
        log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

    # 1. PuckPedia: earliest entry-level signing date per NHL id
    pp = pd.read_csv(F_PP, low_memory=False, encoding="latin-1")
    e = pp[pp["contract_level"] == "entry_level"].copy()
    e["sd"] = pd.to_datetime(e["signing_date"], errors="coerce")
    e = e.dropna(subset=["nhl_id", "sd"])
    e["nhl_id"] = e["nhl_id"].astype("int64")
    first_elc = e.sort_values("sd").groupby("nhl_id").first()          # the earliest entry-level contract
    pp_d = first_elc["sd"]
    pp_team = first_elc["short_code.1"].map(lambda c: PP_CODES.get(c, c) if pd.notna(c) else None)   # v1.2
    log(f"\n[1] PuckPedia entry-level contracts with a signing date: {len(pp_d):,} players "
        f"(signed {pp_d.min():%Y-%m-%d} to {pp_d.max():%Y-%m-%d})")

    # 2. CapWages pages, indexed by the draft line
    pages, n_files = {}, 0
    for d_ in CACHES:
        if d_.exists():
            for f in d_.glob("*.html"):
                n_files += 1
                t = page_text(f.read_text(encoding="utf-8", errors="ignore"))
                k = drafted(t)
                if k:
                    pages.setdefault(k, (f.name, elc_signed(t), elc_signed_team(t)[1]))
    log(f"[2] CapWages pages read: {n_files:,}; with a draft line: {len(pages):,}; "
        f"of those with an entry-level signing date: {sum(1 for v in pages.values() if v[1] is not None):,}")

    # 3. drafted players who played
    link = pd.read_csv(F_LINK)
    if fetch:
        fetch_missing(link, pp_d, pages)
    played = link[link["war_names"].notna()].copy()
    # v1.3 (2026-10-19, the bug sweep): an entry-level deal is signed before his first NHL season ends (he cannot play
    # without one), so a date after June 30 of that season's end year is not his entry-level signing and is set aside.
    # Found: PuckPedia labels a 2018 deal "entry_level" for Michael Hutchinson, Matt Donovan, David Ullstrom and Mark
    # McNeill; Nail Yakupov's CapWages page gives July 2013, after his 2012-13 debut.
    FIRST = first_nhl_seasons(link)
    set_aside = []
    rows = []
    agree = disagree = 0
    team_agree = team_disagree = 0
    for r in played.itertuples():
        nid = int(r.playerId) if pd.notna(r.playerId) else None
        a = pp_d.get(nid) if nid is not None else None
        cw = pages.get((int(r.draftYear), int(r.overallPickNumber)))
        b = cw[1] if cw else None
        ta = pp_team.get(nid) if nid is not None else None
        tb = cw[2] if cw else None
        if a is not None and b is not None:
            agree += a.year == b.year
            disagree += a.year != b.year
            if a.year == b.year and ta and tb:
                team_agree += ta == tb
                team_disagree += ta != tb
        # v1.3: a date after his first NHL season ended is set aside (see above)
        f1 = FIRST.get((int(r.draftYear), int(r.overallPickNumber)))
        cut = pd.Timestamp(f1 + 1, 6, 30) if f1 is not None else None
        aside = [f"{nm} {x.date()}" for nm, x in (("puckpedia", a), ("capwages", b))
                 if x is not None and cut is not None and x > cut]
        if aside:
            set_aside.append(f"{int(r.draftYear)} #{int(r.overallPickNumber)} {r.playerName}: " + ", ".join(aside)
                             + f" (first NHL season {f1}-{str(f1 + 1)[2:]})")
        a = a if (a is None or cut is None or a <= cut) else None
        b = b if (b is None or cut is None or b <= cut) else None
        # v1.2: the signing club. CapWages's own "Signing Team" line when it has the same signing year (PuckPedia gives
        # the club holding the contract: Brett Howden's Tampa deal reads NYR, Arizona's deals UTA); else PuckPedia's
        sd, src = ((a, "puckpedia") if a is not None else
                   ((b, f"capwages:{cw[0]}") if b is not None else (None, "none")))
        team = tb if (tb and b is not None and (a is None or a.year == b.year)) else (ta if a is not None else None)
        rows.append({"nhl_id": nid, "draftYear": int(r.draftYear), "pick": int(r.overallPickNumber),
                     "player": r.playerName, "signing_date": sd, "source": src, "signing_team": team,
                     "set_aside": "; ".join(aside) or None})
    d = pd.DataFrame(rows)
    seen = set(d["nhl_id"].dropna().astype("int64"))
    extra = [{"nhl_id": int(n), "draftYear": None, "pick": None, "player": None, "signing_date": sd,
              "source": "puckpedia", "signing_team": pp_team.get(n)} for n, sd in pp_d.items() if int(n) not in seen]
    d = pd.concat([d, pd.DataFrame(extra)], ignore_index=True)
    d["signing_date"] = pd.to_datetime(d["signing_date"])
    d["signing_year"] = d["signing_date"].dt.year.astype("Int64")

    dr = d[d["draftYear"].notna()]
    log(f"\n[3] drafted players with an NHL game (linkage war_names): {len(dr):,}")
    log("    by source: " + ", ".join(f"{k.split(':')[0]} {v:,}" for k, v in
                                       dr["source"].str.split(":").str[0].value_counts().items()))
    log(f"    PuckPedia and CapWages both present: same signing year {agree}, different {disagree}; "
        f"where the year agrees, same signing club {team_agree}, different {team_disagree}")
    log(f"    signing club held: {int(dr['signing_team'].notna().sum()):,} of {int(dr['signing_date'].notna().sum()):,} "
        f"with a signing date")
    miss = dr[dr["signing_date"].isna()]
    log(f"    no signing date: {len(miss):,}, by draft: "
        + ", ".join(f"{int(k)} {v}" for k, v in miss.groupby("draftYear").size().items()))
    gap = (dr["signing_year"] - dr["draftYear"]).dropna()
    log(f"    years from draft to signing: median {gap.median():.0f}, "
        + ", ".join(f"{int(k)}: {v}" for k, v in gap.value_counts().sort_index().items()))
    log(f"    players under contract (PuckPedia entry-level, not in the drafted set): {len(extra):,}")
    log(f"    v1.3: dates set aside, signed after his first NHL season ended ({len(set_aside)}):")
    for x in set_aside:
        log(f"      {x}")
    d.to_csv(OUT, index=False)
    OUT_LOG.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote {OUT} and its log")


if __name__ == "__main__":
    import sys
    main(fetch="--fetch" in sys.argv)
