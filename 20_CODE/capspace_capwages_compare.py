#!/usr/bin/env python3
"""
capspace_capwages_compare.py  (PHASE 1)
=======================================
Per-season comparison of cap-space.com vs CapWages.com clause data.
Surfaces every disagreement at the (player x contract x season) level into
an interactive XLSX (with dropdown decision column) plus a machine-readable CSV.

WORKFLOW
--------
    PHASE 1 (this script): scrape CapWages -> compare per-season -> emit
        disagreements XLSX/CSV for manual adjudication.
    PHASE 2 (capspace_capwages_finalize.py): read reviewed XLSX -> apply
        decisions -> emit finalized clause panel.

THE HARD PART — making CapWages PER-SEASON
------------------------------------------
CapWages gives ONE clause sentence per contract. Many contracts are uniform
("Player submits a 3 team trade list") and applies to all seasons. But
transition contracts ("No Trade Clause through Jan 1, 2029; converts to a
Modified No-Trade Clause with a 15-team list starting Jan 2, 2029...") need
parsing into per-season designations. This script handles the common
patterns explicitly and flags anything it can't parse as `UNCLEAR`, which
flows into the review file for manual decision.

OUTPUTS (under capspace_out/)
-----------------------------
- clause_disagreements.xlsx  : the review file — open this and fill the
                               'decision' column. Hyperlinks, dropdown.
- clause_disagreements.csv   : same content, machine-readable
- capwages_per_season.csv    : the full parsed CapWages panel (audit)
- capwages_cache/            : cached CapWages HTML pages (resume-safe)

USAGE
-----
    pip install requests beautifulsoup4 lxml pandas openpyxl
    python capspace_capwages_compare.py

First run scrapes CapWages for every player in capspace_clauses.csv that
isn't already cached. ~1.5s/request -> roughly 40 min for the full 1,634-player
sample. The cache makes re-runs free.
"""

import argparse
import csv
import os
import re
import time
import unicodedata

import pandas as pd
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CLAUSES_CSV   = r"C:\Users\thoma\OneDrive\Desktop\xNPV Model\outputs\capspace_out\capspace_clauses.csv"
OUT_DIR       = r"C:\Users\thoma\OneDrive\Desktop\xNPV Model\outputs\capspace_out"
CACHE_DIR     = os.path.join(OUT_DIR, "capwages_cache")
OUT_XLSX      = os.path.join(OUT_DIR, "clause_disagreements.xlsx")
OUT_CSV       = os.path.join(OUT_DIR, "clause_disagreements.csv")
PARSED_CSV    = os.path.join(OUT_DIR, "capwages_per_season.csv")

UA = ("capspace-academic-comparator/1.0 (NHL MSc research; one-time cross-check; "
      "contact: you@university.edu)")
DELAY = 1.5
TIMEOUT = 20

NUM_WORDS = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,
             "eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,
             "fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,
             "eighteen":18,"nineteen":19,"twenty":20}

# Restrictiveness ordering (only used for tie-break ordering, not the join):
TYPE_RANK = {"none": 0, "m_ntc": 1, "m_nmc": 1, "ntc_full": 2, "nmc_full": 3,
             "unclear": -1}


# ---------------------------------------------------------------------------
# CapWages fetching
# ---------------------------------------------------------------------------
def to_slug(name):
    """First-last lowercase ASCII slug. Strips accents and most punctuation."""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    n = re.sub(r"[^A-Za-z\- ]", "", n).strip().lower()
    return re.sub(r"\s+", "-", n)


def fetch_capwages(slug, session):
    """Polite, cached fetch. Returns (html, status)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = f"{CACHE_DIR}/{slug}.html"
    if os.path.exists(cp):
        return open(cp, encoding="utf-8").read(), "cache"
    try:
        r = session.get(f"https://capwages.com/players/{slug}",
                        headers={"User-Agent": UA}, timeout=TIMEOUT)
    except requests.RequestException:
        return None, "error"
    if r.status_code == 404:
        return None, "not_found"
    if not r.ok:
        return None, f"http_{r.status_code}"
    with open(cp, "w", encoding="utf-8") as fh:
        fh.write(r.text)
    time.sleep(DELAY)
    return r.text, "ok"


# ---------------------------------------------------------------------------
# CapWages page parsing
# ---------------------------------------------------------------------------
def parse_capwages_contracts(html):
    """Extract all contracts from a CapWages page as dicts with signing_date,
    term_years, total_value, cap_hit, clause_text."""
    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    blocks = re.split(r"(?=Signing Date:)", text)
    contracts = []
    for b in blocks:
        b = b.strip()
        if not b.startswith("Signing Date"):
            continue
        sd = re.search(r"Signing Date:\s*([A-Za-z]+\.?\s*\d+,\s*\d{4})", b)
        intro = re.search(
            r"signed a\s+(\d+)\s*year(?:s)?,\s*\$([\d,]+)\s*contract.*?"
            r"cap hit of\s*\$([\d,]+)", b, re.I | re.S)
        cl = re.search(r"Clause Details:\s*([^\n]+?)(?=\n|$)", b)
        c = {
            "signing_date_raw": sd.group(1).strip() if sd else None,
            "clause_text": cl.group(1).strip() if cl else None,
        }
        if intro:
            c["term_years"]  = int(intro.group(1))
            c["total_value"] = int(intro.group(2).replace(",", ""))
            c["cap_hit"]     = int(intro.group(3).replace(",", ""))
        contracts.append(c)
    return contracts


def parse_capwages_date_to_iso(raw):
    """'Jul. 1, 2019' -> '2019-07-01'."""
    if not raw: return None
    s = raw.replace(".", "").strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try: return pd.to_datetime(s, format=fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError): pass
    try: return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception: return None


# ---------------------------------------------------------------------------
# The hard part — parsing CapWages prose into per-season designations
# ---------------------------------------------------------------------------
def season_of_date(date_str, side="contains"):
    """Map a date to an NHL season string 'YYYY-YYYY'.
    side='contains'   : the season that contains the date (mid-season)
    side='through_end': the season ending on/after the date (treats Jul 1+ as next season)
    side='starting'   : the season that starts on/after the date
    NHL league year = Jul 1 to Jun 30.
    """
    try:
        d = pd.to_datetime(date_str)
    except Exception:
        return None
    if d.month >= 7:                # July-December -> league year YYYY-(YYYY+1)
        y = d.year
    else:                            # January-June -> league year (YYYY-1)-YYYY
        y = d.year - 1
    if side == "starting" and d.month >= 7:
        # 'starting Jul 1, X' means season X-(X+1) -> y already correct
        pass
    return f"{y}-{y + 1}"


def parse_team_count(s):
    """Extract a team count from text like '15-team' or 'three team'."""
    m = re.search(r"(\d+|\w+)[- ]team", s.lower())
    if not m: return None
    w = m.group(1)
    return int(w) if w.isdigit() else NUM_WORDS.get(w)


def parse_simple_designation(text):
    """Map a clean clause-type segment to (type, team_count, confidence)."""
    t = (text or "").lower()
    if not t.strip():
        return ("none", None, "high")
    # Strip parenthetical notes, normalize "no-trade" to "no trade", etc.
    t = t.replace("no-trade", "no trade").replace("no-move", "no move") \
         .replace("no-movement", "no movement")
    # Modified clauses — team-count phrasing
    tc = parse_team_count(t)
    if tc is not None and ("trade list" in t or "no trade list" in t
                            or "trade exemption" in t or "submits" in t
                            or "modified" in t):
        return ("m_ntc", tc, "high")
    if "no move" in t or "no movement" in t or re.search(r"\bnmc\b", t):
        # Full NMC unless explicitly modified
        if "modified" in t or "limited" in t:
            return ("m_nmc", tc, "high" if tc else "medium")
        return ("nmc_full", None, "high")
    if "no trade" in t or re.search(r"\bntc\b", t):
        if "modified" in t or "limited" in t:
            return ("m_ntc", tc, "high" if tc else "medium")
        return ("ntc_full", None, "high")
    # Trade list without 'no' keyword (e.g., 'Player submits a 3 team trade list')
    if "submits" in t and "trade list" in t and tc:
        return ("m_ntc", tc, "high")
    return ("unclear", None, "low")


# Date-range patterns inside a transition contract.
RANGE_PATTERNS = [
    # "through Jun 30, 2027" / "through January 1, 2029"
    (re.compile(r"through\s+([A-Za-z]+\.?\s*\d+,\s*\d{4})", re.I), "through"),
    # "starting Jul 1, 2024" / "starting July 1, 2024" / "from Jul 1, 2024"
    (re.compile(r"(?:starting|from|effective)\s+([A-Za-z]+\.?\s*\d+,\s*\d{4})", re.I), "starting"),
    # "upon execution"
    (re.compile(r"upon execution", re.I), "upon_execution"),
    # "remainder of (the )?contract" / "for the rest of (the )?contract"
    (re.compile(r"remainder of (?:the )?contract|rest of (?:the )?contract", re.I), "remainder"),
    # "in YYYY-YY" — explicit single season
    (re.compile(r"in\s+(\d{4})-(\d{2}|\d{4})", re.I), "in_season"),
    # "for the YYYY-YY season"
    (re.compile(r"for the\s+(\d{4})-(\d{2}|\d{4})\s+season", re.I), "in_season"),
]


def split_into_segments(text):
    """Break a CapWages clause text into segments at transition delimiters."""
    # Split at ";" or at " and " preceding a date pattern.
    # Keep it simple: split on ";" first, then on " then " or commas before "starting/in/through".
    parts = re.split(r";\s*", text)
    out = []
    for p in parts:
        # Further split on " then " or " and a " where a transition starts
        sub = re.split(r"\s+then\s+|\s+,\s*(?=(?:a\s+)?(?:modified|full|\d+))", p, flags=re.I)
        out.extend([s.strip() for s in sub if s.strip()])
    return out


def parse_capwages_to_per_season(text, contract_start_season, term_years):
    """Parse one contract's CapWages clause text into a dict
    {season: {type, team_count, raw_fragment, confidence}}.

    contract_start_season: e.g. '2019-2020' (the first season).
    term_years: contract length in NHL seasons.
    """
    seasons = []
    y0 = int(contract_start_season.split("-")[0])
    for i in range(term_years):
        seasons.append(f"{y0 + i}-{y0 + i + 1}")

    # No clause text -> all 'none'
    if not text or not text.strip():
        return {s: {"type": "none", "team_count": None, "raw_fragment": "",
                    "confidence": "high"} for s in seasons}

    text_clean = text.strip().rstrip(".")

    # Detect transition keywords. If absent -> single designation across all seasons.
    has_transition = bool(re.search(
        r"\b(through|starting|from|converts to|then|in\s+\d{4}-)\b",
        text_clean, re.I))

    if not has_transition:
        typ, tc, conf = parse_simple_designation(text_clean)
        return {s: {"type": typ, "team_count": tc, "raw_fragment": text_clean,
                    "confidence": conf} for s in seasons}

    # Transition: split into segments and try to attach each to a season range
    segments = split_into_segments(text_clean)
    # For each segment, figure out (type, team_count, applicable seasons)
    season_set = set(seasons)
    designations = {s: None for s in seasons}  # season -> (type, tc, fragment, conf)

    # First pass: explicit "in YYYY-YY" segments take that season directly
    leftover_segments = []
    for seg in segments:
        m = re.search(r"in\s+(\d{4})-(\d{2,4})", seg, re.I)
        if m:
            y = int(m.group(1))
            season = f"{y}-{y + 1}"
            if season in season_set:
                typ, tc, conf = parse_simple_designation(seg)
                designations[season] = (typ, tc, seg, conf)
            continue
        leftover_segments.append(seg)

    # Second pass: 'through DATE' / 'starting DATE' / 'remainder' style
    # Apply them in order; each segment carries a (type, tc) AND a date scope.
    for seg in leftover_segments:
        typ, tc, conf = parse_simple_designation(seg)
        # find date scope in segment
        through = re.search(r"through\s+([A-Za-z]+\.?\s*\d+,\s*\d{4})", seg, re.I)
        starting = re.search(
            r"(?:starting|from|effective)\s+([A-Za-z]+\.?\s*\d+,\s*\d{4})", seg, re.I)
        remainder = bool(re.search(r"remainder|rest of", seg, re.I))
        upon_exec = bool(re.search(r"upon execution", seg, re.I))
        # determine target season range
        target_seasons = []
        if through and starting:
            s_from = season_of_date(starting.group(1))
            s_to = season_of_date(through.group(1))
            if s_from and s_to:
                in_range = False
                for s in seasons:
                    if s == s_from: in_range = True
                    if in_range: target_seasons.append(s)
                    if s == s_to: in_range = False; break
        elif through:
            s_to = season_of_date(through.group(1))
            if s_to:
                for s in seasons:
                    target_seasons.append(s)
                    if s == s_to: break
        elif starting or upon_exec:
            s_from = season_of_date(starting.group(1)) if starting else seasons[0]
            if s_from:
                hit = False
                for s in seasons:
                    if s == s_from: hit = True
                    if hit: target_seasons.append(s)
        elif remainder:
            # remainder means "from the previous segment's end to contract end"
            # find first not-yet-assigned season
            for s in seasons:
                if designations[s] is None:
                    target_seasons.append(s)
        else:
            # no date scope — applies to all remaining unassigned
            target_seasons = [s for s in seasons if designations[s] is None]

        for s in target_seasons:
            if designations[s] is None:
                designations[s] = (typ, tc, seg, conf)

    # Any unassigned seasons -> unclear
    out = {}
    for s in seasons:
        if designations[s] is None:
            out[s] = {"type": "unclear", "team_count": None,
                      "raw_fragment": text_clean, "confidence": "low"}
        else:
            typ, tc, frag, conf = designations[s]
            out[s] = {"type": typ, "team_count": tc, "raw_fragment": frag,
                      "confidence": conf}
    return out


# ---------------------------------------------------------------------------
# cap-space side
# ---------------------------------------------------------------------------
def capspace_type_of(row):
    if row["nmc_full"]: return "nmc_full"
    if row["ntc_full"]: return "ntc_full"
    if row["m_ntc"] or row["m_nmc"]: return "m_ntc"
    return "none"


def capspace_team_count(row):
    m = re.match(r"(\d+|\w+)\s+team", str(row.get("clause_limits", "")).lower())
    if not m: return None
    w = m.group(1)
    return int(w) if w.isdigit() else NUM_WORDS.get(w)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def disagreement_kind(cs_t, cs_n, cw_t, cw_n):
    """Classify the disagreement -> short tag."""
    if cw_t == "unclear":
        return "capwages_unparsed"
    if cs_t == "none" and cw_t != "none":
        return "cs_none_vs_cw_clause"
    if cs_t != "none" and cw_t == "none":
        return "cs_clause_vs_cw_none"
    if cs_t != cw_t:
        return "type_differs"
    if cs_t in ("m_ntc", "m_nmc"):
        if cs_n is not None and cw_n is not None and cs_n != cw_n:
            return "team_count_differs"
        if cs_n is None and cw_n is not None:
            return "cs_team_count_missing"
        if cs_n is not None and cw_n is None:
            return "cw_team_count_missing"
    return None  # agreement


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="cap player count (for testing)")
    args = ap.parse_args()

    if not os.path.exists(CLAUSES_CSV):
        raise SystemExit(f"Not found: {CLAUSES_CSV} (run capspace_scraper.py first)")
    cs = pd.read_csv(CLAUSES_CSV)
    os.makedirs(OUT_DIR, exist_ok=True)

    # Distinct players to compare
    players = cs.dropna(subset=["puckpedia_ep_id"]).drop_duplicates("puckpedia_ep_id")
    players = players[["puckpedia_ep_id", "name"]].reset_index(drop=True)
    if args.limit:
        players = players.head(args.limit)

    session = requests.Session()
    print(f"Comparing {len(players)} players. Cache: {CACHE_DIR}/  Delay: {DELAY}s\n")

    # Build CapWages per-season panel
    cw_rows = []
    fetch_counts = {"ok": 0, "cache": 0, "not_found": 0, "error": 0}
    for i, p in enumerate(players.itertuples(index=False), start=1):
        slug = to_slug(p.name)
        html, status = fetch_capwages(slug, session)
        fetch_counts[status] = fetch_counts.get(status, 0) + 1
        if html is None:
            cw_rows.append({"puckpedia_ep_id": p.puckpedia_ep_id, "name": p.name,
                            "slug": slug, "capwages_status": status,
                            "signing_date": None, "season": None,
                            "cw_type": None, "cw_team_count": None,
                            "cw_text": None, "cw_fragment": None,
                            "cw_confidence": None})
            continue

        cw_contracts = parse_capwages_contracts(html)
        cs_player = cs[cs["puckpedia_ep_id"] == p.puckpedia_ep_id]
        # For each cap-space contract group (signing_date), find matching CW contract
        for sd, g in cs_player.groupby("signing_date", dropna=False):
            cs_cap = g["cap_hit"].iloc[0]
            cs_seasons_in_contract = sorted(g["season"].unique())
            if not cs_seasons_in_contract:
                continue
            term_years = len(cs_seasons_in_contract)
            start_season = cs_seasons_in_contract[0]
            # Match on (signing_date, cap_hit) then fall back to signing_date only
            cw_match = None
            for cw in cw_contracts:
                if (parse_capwages_date_to_iso(cw["signing_date_raw"]) == sd
                        and cw.get("cap_hit") == cs_cap):
                    cw_match = cw; break
            if cw_match is None:
                for cw in cw_contracts:
                    if parse_capwages_date_to_iso(cw["signing_date_raw"]) == sd:
                        cw_match = cw; break
            if cw_match is None:
                # CapWages doesn't have this contract
                for season in cs_seasons_in_contract:
                    cw_rows.append({"puckpedia_ep_id": p.puckpedia_ep_id, "name": p.name,
                                    "slug": slug, "capwages_status": "no_match",
                                    "signing_date": sd, "season": season,
                                    "cw_type": None, "cw_team_count": None,
                                    "cw_text": None, "cw_fragment": None,
                                    "cw_confidence": None})
                continue

            per_season = parse_capwages_to_per_season(
                cw_match.get("clause_text"), start_season, term_years)
            for season in cs_seasons_in_contract:
                d = per_season.get(season, {"type": "unclear", "team_count": None,
                                            "raw_fragment": None, "confidence": "low"})
                cw_rows.append({
                    "puckpedia_ep_id": p.puckpedia_ep_id, "name": p.name,
                    "slug": slug, "capwages_status": status,
                    "signing_date": sd, "season": season,
                    "cw_type": d["type"], "cw_team_count": d["team_count"],
                    "cw_text": cw_match.get("clause_text"),
                    "cw_fragment": d["raw_fragment"],
                    "cw_confidence": d["confidence"],
                })

        if i % 50 == 0 or i == len(players):
            print(f"  [{i}/{len(players)}] last: {p.name} -> {status}", flush=True)

    cw_panel = pd.DataFrame(cw_rows)
    cw_panel.to_csv(PARSED_CSV, index=False)
    print(f"\nCapWages fetch summary: {fetch_counts}")
    print(f"  -> {PARSED_CSV}  ({len(cw_panel):,} rows)")

    # Build per-season comparison
    print("\nComputing per-season disagreements...")
    cs_keys = cs[["puckpedia_ep_id", "signing_date", "season",
                  "cap_hit", "aav", "contract_label", "nmc_full", "ntc_full",
                  "m_ntc", "m_nmc", "clause_raw", "clause_limits"]].copy()
    cs_keys["cs_type"] = cs_keys.apply(capspace_type_of, axis=1)
    cs_keys["cs_team_count"] = cs_keys.apply(capspace_team_count, axis=1)

    merged = cs_keys.merge(
        cw_panel,
        on=["puckpedia_ep_id", "signing_date", "season"],
        how="left",
    )

    # Classify each row
    def classify(row):
        if pd.isna(row.get("cw_type")):
            # CapWages didn't return a season-level value -> only flag if we can't match
            if row.get("capwages_status") in ("not_found", "no_match", "error"):
                # no CapWages data to compare -> not a disagreement, skip
                return None
            return None
        return disagreement_kind(row["cs_type"], row["cs_team_count"],
                                 row["cw_type"], row["cw_team_count"])

    merged["disagreement"] = merged.apply(classify, axis=1)
    diss = merged[merged["disagreement"].notna()].copy()
    print(f"Disagreements: {len(diss):,} rows across "
          f"{diss['puckpedia_ep_id'].nunique()} players")
    print(diss["disagreement"].value_counts().to_string())

    # Build review file
    write_review_files(diss)


def write_review_files(diss):
    """Emit clause_disagreements.{csv,xlsx} for manual adjudication."""
    diss = diss.copy()
    diss["url_capspace"]    = diss["puckpedia_ep_id"].apply(
        lambda e: f"https://cap-space.com/person/ep-{int(e)}" if pd.notna(e) else "")
    diss["url_capwages"]    = diss["slug"].apply(
        lambda s: f"https://capwages.com/players/{s}" if isinstance(s, str) and s else "")
    diss["decision"]        = ""       # USER FILLS: capspace | capwages | other | skip
    diss["final_type"]      = ""       # USER FILLS (only if decision == 'other')
    diss["final_team_count"] = ""      # USER FILLS (only if decision == 'other')
    diss["notes"]           = ""

    col_order = [
        "name", "puckpedia_ep_id", "signing_date", "season", "cap_hit",
        "disagreement",
        "cs_type", "cs_team_count", "clause_raw", "clause_limits",
        "cw_type", "cw_team_count", "cw_fragment", "cw_text",
        "url_capspace", "url_capwages",
        "decision", "final_type", "final_team_count", "notes",
    ]
    diss = diss[col_order]
    diss.to_csv(OUT_CSV, index=False)
    print(f"  -> {OUT_CSV}")

    # XLSX with dropdown on decision + hyperlinks
    wb = Workbook()
    ws = wb.active
    ws.title = "review"
    # Instructions row
    ws["A1"] = ("Review each row: open url_capspace + url_capwages, decide which "
                "source is correct, fill 'decision' (dropdown), and final_type / "
                "final_team_count if 'other'. Then run capspace_capwages_finalize.py.")
    ws["A1"].font = Font(italic=True, color="555555")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(col_order))
    # Header
    header_fill = PatternFill("solid", start_color="DDDDDD")
    for j, c in enumerate(col_order, start=1):
        cell = ws.cell(row=2, column=j, value=c)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    # Data
    for i, rec in enumerate(diss.itertuples(index=False), start=3):
        for j, col in enumerate(col_order, start=1):
            v = getattr(rec, col)
            if pd.isna(v): v = ""
            cell = ws.cell(row=i, column=j, value=v)
            if col in ("url_capspace", "url_capwages") and v:
                cell.hyperlink = v
                cell.font = Font(color="0563C1", underline="single")

    # Column widths
    widths = {"name": 24, "puckpedia_ep_id": 10, "signing_date": 12, "season": 10,
              "cap_hit": 10, "disagreement": 22, "cs_type": 10, "cs_team_count": 6,
              "clause_raw": 14, "clause_limits": 24, "cw_type": 10, "cw_team_count": 6,
              "cw_fragment": 32, "cw_text": 40, "url_capspace": 24, "url_capwages": 24,
              "decision": 14, "final_type": 12, "final_team_count": 8, "notes": 28}
    for j, c in enumerate(col_order, start=1):
        ws.column_dimensions[get_column_letter(j)].width = widths.get(c, 14)

    # Freeze header + add dropdown validation on 'decision' column
    ws.freeze_panes = "A3"
    dec_col = col_order.index("decision") + 1
    dec_letter = get_column_letter(dec_col)
    dv = DataValidation(
        type="list",
        formula1='"capspace,capwages,other,skip"',
        allow_blank=True,
        showDropDown=False,   # False here = dropdown VISIBLE (openpyxl quirk)
    )
    dv.error = "Pick capspace / capwages / other / skip"
    dv.errorTitle = "Invalid decision"
    dv.add(f"{dec_letter}3:{dec_letter}{len(diss) + 2}")
    ws.add_data_validation(dv)

    # final_type dropdown
    ft_col = col_order.index("final_type") + 1
    ft_letter = get_column_letter(ft_col)
    dv2 = DataValidation(
        type="list",
        formula1='"none,m_ntc,m_nmc,ntc_full,nmc_full"',
        allow_blank=True,
        showDropDown=False,
    )
    dv2.add(f"{ft_letter}3:{ft_letter}{len(diss) + 2}")
    ws.add_data_validation(dv2)

    wb.save(OUT_XLSX)
    print(f"  -> {OUT_XLSX}  (open this, fill 'decision' column, then run Phase 2)")


if __name__ == "__main__":
    main()
