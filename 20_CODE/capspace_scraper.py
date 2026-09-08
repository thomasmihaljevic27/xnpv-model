#!/usr/bin/env python3
"""
capspace_scraper.py
===================
Pulls per-season NTC/NMC clause status and salary-structure (signing bonus,
performance bonuses, NHL/minors salary) from cap-space.com to fill the two
gaps in the PuckPedia contract export:

    (1) Trade-protection clauses  -> contract_year.ntc / .nmc / .clause_limits
    (2) Signing-bonus structure   -> signing_bonus / performance_bonuses / nhl_salary

WHY THIS DESIGN
---------------
cap-space.com's Flask resolver (app/main/person.py) accepts ID-keyed URLs:

    /person/ep-<eliteprospects_id>   -> looked up by ep_id  (PRIMARY key)
    /person/nhl-<nhl_id>             -> looked up by nhl_id  (fallback)

The PuckPedia contract export carries both ids, so we hit exactly one URL per
target player. No name search, no same-name collisions, no crawling the ~20k
sequential id space.

Clauses are stored PER contract-season on the page, so this gives point-in-time
clause status (the value as it stood in the season being priced) -- what the
friction-discount regression in paper Section 2.2 actually needs. The
`clause_limits` text ("Three team no trade list") additionally supports a
*graded* restrictiveness measure rather than a binary clause dummy.

BOUNDED SAMPLE (instead of full-export crawl)
---------------------------------------------
Per the project response protocol's minimum-necessary-scope rule, we fetch only
the players who actually enter the analysis. That sample is the union of two
sub-samples, both restricted to the 2018-present back-test window:

  (a) UFA-signed STANDARD contracts (`signing_status` LIKE 'UFA%',
      `contract_level` != 'entry_level').
      -> needed for the NTC/NMC discount regression, which is identified off
         the full UFA contract cross-section (not the trade sub-sample alone --
         the trade sample selects on transaction occurrence).
      -> contracts without clauses are INCLUDED. clause=0 is informative for
         the discount estimate.

  (b) Players appearing as a player-asset (`player_id` not null) in a trade
      whose `trade_date` falls in the window.
      -> needed for trade asset valuation in the back-test.

ELCs and pre-UFA RFA contracts cannot carry NTC/NMC under the CBA (Group 3 UFA
eligibility is required), so they self-exclude from sample (a). They may still
appear in (b) as traded ELC/RFA players; for those we still fetch the page,
since cap-space will return their full contract history including any later
UFA deal they signed.

CAVEATS (also flag for the paper)
---------------------------------
* cap-space.com is single-maintainer and crowdsourced. Spot-validate a sample
  of `clause_limits` against PuckPedia's clause pages and the TFP / Pro Hockey
  Rumors annual season lists -- same discipline applied to trades.db.
* MIT licenses the code, not necessarily the scraped data. The site cites
  PuckPedia/NHL.com as contract sources, so provenance traces back. Attribute
  the site (it has an /acknowledgements page).
* `contract_label` and the derived `extension` boolean reflect the SITE'S OWN
  labeling, which looked liberal on some 2014-era contracts. Treat as a tag,
  not as truth. Clauses + bonus structure are the rock-solid payoff.

USAGE
-----
    pip install requests beautifulsoup4 lxml pandas openpyxl

    python capspace_scraper.py --dry-run    # print sample composition, no fetch
    python capspace_scraper.py --validate   # smoke-test on Coyle (1 known player)
    python capspace_scraper.py              # full bounded run

The on-disk HTML cache (capspace_out/html_cache/) makes the run resume-safe:
adding players later only fetches the new ones.
"""

import argparse
import csv
import os
import re
import sqlite3
import sys
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------------
# CONFIG -- edit these
# ----------------------------------------------------------------------------
INPUT_CONTRACTS_XLSX = r"C:\Users\thoma\OneDrive\Desktop\xNPV Model\data_sources\data\puckpedia\PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx"
INPUT_TRADES_XLSX    = r"C:\Users\thoma\OneDrive\Desktop\xNPV Model\data_sources\data\puckpedia\PuckPedia_Trades_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx"
WINDOW_START         = "2018-01-01"   # back-test sample window

OUTPUT_DIR  = r"C:\Users\thoma\OneDrive\Desktop\xNPV Model\outputs\capspace_out"
CACHE_DIR   = os.path.join(OUTPUT_DIR, "html_cache")   # resume-safe HTML cache
OUT_CSV     = os.path.join(OUTPUT_DIR, "capspace_clauses.csv")
OUT_DB      = os.path.join(OUTPUT_DIR, "capspace_clauses.db")
OUT_TARGETS = os.path.join(OUTPUT_DIR, "capspace_targets.csv")  # the sample list, for audit
MISS_LOG    = os.path.join(OUTPUT_DIR, "capspace_misses.csv")

# IMPORTANT: put a REAL contact in the UA so the maintainer can reach you.
USER_AGENT    = ("capspace-academic-scraper/1.0 "
                 "(NHL trade-efficiency MSc research; contact: you@university.edu)")
REQUEST_DELAY = 1.5     # seconds between *network* requests (cache hits are free)
MAX_RETRIES   = 4       # transient-error retries (5xx / connection)
TIMEOUT       = 20
BASE          = "https://cap-space.com"

SEASON_HDR = ["Season", "Cap Hit", "AAV", "NHL Salary", "Minors Salary",
              "Signing Bonus", "Perf. Bonuses", "Clause"]
RANGE_RE   = re.compile(r"^\d{4}-\d{4}")   # conditions-table key, e.g. "2024-2025:"


# ----------------------------------------------------------------------------
# Sample selection -- the bounded union of (a) UFA-signed + (b) traded players
# ----------------------------------------------------------------------------
def load_targets_bounded(contracts_xlsx, trades_xlsx, window_start):
    """Return DataFrame[ep_id, nhl_id, name, source] of distinct target players.

    Sample (a): UFA-signed standard contracts in window (clause-discount regression).
    Sample (b): players who appear in a trade in window (back-test valuation).

    Union by `player_id`. Identifiers (ep_id/nhl_id/name) preferred from the
    contracts file (the spine); trade-only players fall back to trade-file
    identifiers. ELCs are excluded from (a) but not from (b) -- a traded ELC
    player may have signed a UFA deal later, and the page returns their full
    contract history.
    """
    # ---- sample (a) -- UFA-signed standard contracts ----
    c = pd.read_excel(contracts_xlsx).rename(columns=str.lower)
    c["signing_date"] = pd.to_datetime(c["signing_date"], errors="coerce")
    # PuckPedia file is one row per contract-season; collapse to one row per contract
    # using (player_id, signing_date) as the contract key.
    c_one = c.drop_duplicates(["player_id", "signing_date"])

    is_ufa = c_one["signing_status"].astype(str).str.startswith("UFA")  # UFA, UFA no QO, UFA-Group6, UFA Group 6
    is_standard = c_one["contract_level"].astype(str).eq("standard_level")  # ELCs excluded
    in_window = c_one["signing_date"] >= pd.Timestamp(window_start)

    sample_a = c_one[is_ufa & is_standard & in_window].copy()
    sample_a["source"] = "a_ufa_signed"

    # ---- sample (b) -- player legs of trades in window ----
    t = pd.read_excel(trades_xlsx).rename(columns=str.lower)
    t["trade_date"] = pd.to_datetime(t["trade_date"], errors="coerce")
    # player-asset legs only (exclude picks / retention legs)
    t_player = t[t["player_id"].notna() & (t["trade_date"] >= pd.Timestamp(window_start))]
    # one row per traded player (a player traded twice still appears once here)
    sample_b = t_player.drop_duplicates("player_id").copy()
    sample_b["source"] = "b_traded"

    # ---- union by player_id, preferring contract-file identifiers ----
    common_cols = ["player_id", "eliteprospects_id", "nhl_id", "first_name", "last_name", "source"]
    sa = sample_a[common_cols]
    sb = sample_b[common_cols]
    # mark overlap before concat
    in_both_ids = set(sa["player_id"]) & set(sb["player_id"])
    union = pd.concat([sa, sb], ignore_index=True)
    # prefer contract-file row (source 'a_ufa_signed' sorts first) on duplicate player_id
    union = union.sort_values("source").drop_duplicates("player_id", keep="first")
    union["in_both_samples"] = union["player_id"].isin(in_both_ids)

    union["name"] = (union["first_name"].astype(str) + " " +
                     union["last_name"].astype(str)).str.strip()
    out = union.rename(columns={"eliteprospects_id": "ep_id"})[
        ["player_id", "ep_id", "nhl_id", "name", "source", "in_both_samples"]
    ]
    # numeric coercion (xlsx loads as float when there are NaNs)
    out["ep_id"]  = pd.to_numeric(out["ep_id"], errors="coerce")
    out["nhl_id"] = pd.to_numeric(out["nhl_id"], errors="coerce")
    # need at least one usable key (ep_id preferred, nhl_id fallback)
    out = out[out["ep_id"].notna() | out["nhl_id"].notna()].reset_index(drop=True)

    # --- sample composition print + audit file ---
    n_a = (out["source"] == "a_ufa_signed").sum()
    n_b = (out["source"] == "b_traded").sum()
    n_both = out["in_both_samples"].sum()
    print(f"Sample composition (window >= {window_start}):")
    print(f"  (a) UFA-signed standard contracts : {len(sample_a):>5} contracts -> {n_a} unique players (after union dedup)")
    print(f"  (b) traded players (player-leg)   : {len(sample_b):>5}")
    print(f"  union (distinct players)          : {len(out):>5}")
    print(f"  in both samples                   : {n_both:>5}")
    print(f"  missing ep_id (will use nhl-)     : {(out['ep_id'].isna()).sum():>5}")
    return out


# ----------------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------------
def _cells(row):
    return [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]


def _money(s):
    """'$5,250,000' -> 5250000 ; '' / None -> None."""
    digits = re.sub(r"[^\d]", "", s or "")
    return int(digits) if digits else None


def parse_clause(txt):
    """Per-season Clause cell text -> structured flags.

    Tokens seen on the site: 'NMC', 'NTC', 'M-NTC', 'M-NMC' (comma-joined).
    Exact-token match so 'M-NTC' does not get misread as a full 'NTC'.
    """
    toks = [t.strip() for t in (txt or "").split(",") if t.strip()]
    return {
        "clause_raw": txt or "",
        "nmc_full": "NMC" in toks,
        "ntc_full": "NTC" in toks,
        "m_ntc":    "M-NTC" in toks,
        "m_nmc":    "M-NMC" in toks,
        "has_any_clause": bool(toks),
    }


def expand_conditions(cond_table):
    """Conditions table -> {season 'YYYY-YYYY': limit_text}, expanding ranges.

    Row keys are either 'YYYY-YYYY:' (single season) or 'YYYY-YYYY to YYYY-YYYY:'
    (inclusive range). The value (e.g. 'Three team no trade list') is the
    modified-list size that powers the graded restrictiveness measure.
    """
    out = {}
    if cond_table is None:
        return out
    for row in cond_table.find_all("tr"):
        c = _cells(row)
        if len(c) < 2:
            continue
        key = c[0].rstrip(":").strip()
        limit = c[1].strip()
        yrs = re.findall(r"\d{4}-\d{4}", key)
        if len(yrs) == 1:
            out[yrs[0]] = limit
        elif len(yrs) == 2:
            start, end = int(yrs[0][:4]), int(yrs[1][:4])
            for y in range(start, end + 1):
                out[f"{y}-{y + 1}"] = limit
    return out


# ----------------------------------------------------------------------------
# Page parser
# ----------------------------------------------------------------------------
def parse_person(html, requested_key, requested_value):
    """Parse one /person page into a list of contract-season dicts."""
    soup = BeautifulSoup(html, "lxml")

    title = soup.find(["h1", "h2"])
    name = title.get_text(" ", strip=True).split("#")[0].strip() if title else ""

    # EP id directly off the EliteProspects link -> identity verification.
    page_ep = None
    for a in soup.find_all("a", href=True):
        m = re.search(r"eliteprospects\.com/player/(\d+)", a["href"])
        if m:
            page_ep = m.group(1)
            break

    rows = []
    for grid in soup.find_all("table"):
        first = grid.find("tr")
        if not first or _cells(first) != SEASON_HDR:
            continue

        # contract meta: nearest preceding 'Total Value' table
        meta_tbl = grid.find_previous("table")
        meta = {}
        if meta_tbl:
            for mr in meta_tbl.find_all("tr"):
                for c in _cells(mr):
                    if "Total Value" in c:
                        meta["Total Value"] = _money(c)
                    elif ":" in c:
                        k, _, v = c.partition(":")
                        meta[k.strip()] = v.strip()

        # contract TYPE label: nearest preceding bold whose text contains 'Contract'
        # (avoids grabbing the meta table's bold 'Signing Team:' label).
        label_el = grid.find_previous(
            lambda t: t.name in ("strong", "b") and "Contract" in t.get_text())
        label = label_el.get_text(" ", strip=True) if label_el else ""
        label = re.sub(r"\s+", " ", label).strip()   # collapse stray newlines

        # conditions table immediately after the grid?
        nxt = grid.find_next("table")
        is_cond = (nxt is not None and nxt.find("tr")
                   and RANGE_RE.match(_cells(nxt.find("tr"))[0]))
        cond_map = expand_conditions(nxt if is_cond else None)

        for tr in grid.find_all("tr")[1:]:
            c = _cells(tr)
            if len(c) < 8 or not re.match(r"\d{4}-\d{4}", c[0]):
                continue
            season = c[0]
            rec = {
                "join_ep_id": page_ep,             # join to PuckPedia eliteprospects_id
                "requested_key": requested_key,
                "requested_value": str(requested_value),
                "id_verified": (requested_key != "ep") or (page_ep == str(requested_value)),
                "name": name,
                "contract_label": label,
                "entry_level": "Entry Level" in label,
                "extension":   "Extension" in label,
                "expiration_status": meta.get("Expiration Status"),
                "signing_date": meta.get("Signing Date"),
                "total_value": meta.get("Total Value"),
                "season": season,
                "cap_hit":       _money(c[1]),
                "aav":           _money(c[2]),
                "nhl_salary":    _money(c[3]),
                "minors_salary": _money(c[4]),
                "signing_bonus": _money(c[5]),
                "perf_bonuses":  _money(c[6]),
                "clause_limits": cond_map.get(season, ""),  # point-in-time modified-list size
            }
            rec.update(parse_clause(c[7]))
            rows.append(rec)
    return rows


# ----------------------------------------------------------------------------
# Fetching (cached, polite, retrying)
# ----------------------------------------------------------------------------
def cache_path(key, value):
    return os.path.join(CACHE_DIR, f"{key}-{value}.html")


def fetch(session, key, value):
    """Return (html, status) for /person/<key>-<value>, using on-disk cache first.

    status in {'cache', 'ok', 'not_found', 'error'}. Network fetches sleep;
    cache hits are free.
    """
    cp = cache_path(key, value)
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as fh:
            return fh.read(), "cache"

    url = f"{BASE}/person/{key}-{value}"
    backoff = 2.0
    for _ in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        except requests.RequestException:
            time.sleep(backoff); backoff *= 2; continue

        if resp.status_code == 404:
            return None, "not_found"
        if resp.status_code == 429:                       # respect Retry-After
            wait = int(resp.headers.get("Retry-After", backoff))
            time.sleep(wait); backoff *= 2; continue
        if resp.status_code >= 500:
            time.sleep(backoff); backoff *= 2; continue
        if resp.ok:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cp, "w", encoding="utf-8") as fh:
                fh.write(resp.text)
            time.sleep(REQUEST_DELAY)
            return resp.text, "ok"
        return None, "error"
    return None, "error"


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------
def write_outputs(rows, misses, targets_df=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if targets_df is not None:
        targets_df.to_csv(OUT_TARGETS, index=False)
    if rows:
        cols = list(rows[0].keys())
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        con = sqlite3.connect(OUT_DB)
        pd.DataFrame(rows).to_sql("capspace_clauses", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_ep_season "
                    "ON capspace_clauses(join_ep_id, season)")
        con.commit(); con.close()
    if misses:
        with open(MISS_LOG, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(misses[0].keys()))
            w.writeheader(); w.writerows(misses)


# ----------------------------------------------------------------------------
# Main fetch loop
# ----------------------------------------------------------------------------
def run(targets):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    rows, misses = [], []
    n = len(targets)
    for i, t in enumerate(targets.itertuples(index=False), start=1):
        ep_id  = int(t.ep_id)  if pd.notna(t.ep_id)  else None
        nhl_id = int(t.nhl_id) if pd.notna(t.nhl_id) else None

        html, status = (None, "error")
        used_key, used_val = None, None
        if ep_id is not None:                            # PRIMARY: ep- key
            html, status = fetch(session, "ep", ep_id)
            used_key, used_val = "ep", ep_id
        if html is None and nhl_id is not None:           # FALLBACK: nhl- key
            html, status = fetch(session, "nhl", nhl_id)
            used_key, used_val = "nhl", nhl_id

        if html is None:
            misses.append({"name": t.name, "ep_id": ep_id, "nhl_id": nhl_id,
                           "player_id": getattr(t, "player_id", None),
                           "source": getattr(t, "source", None),
                           "status": status})
        else:
            parsed = parse_person(html, used_key, used_val)
            if not parsed:
                misses.append({"name": t.name, "ep_id": ep_id, "nhl_id": nhl_id,
                               "player_id": getattr(t, "player_id", None),
                               "source": getattr(t, "source", None),
                               "status": "no_contracts"})
            else:
                for r in parsed:                          # backfill PuckPedia keys
                    r["puckpedia_player_id"] = getattr(t, "player_id", None)
                    r["puckpedia_ep_id"] = ep_id
                    r["puckpedia_nhl_id"] = nhl_id
                    r["sample_source"] = getattr(t, "source", None)
                rows.extend(parsed)

        if i % 25 == 0 or i == n:
            last = getattr(t, "name", "") or f"ep={ep_id}"
            print(f"  [{i}/{n}] rows={len(rows)} misses={len(misses)} (last: {last} -> {status})",
                  flush=True)

    write_outputs(rows, misses, targets_df=targets)
    print(f"\nDONE. {len(rows)} contract-season rows from "
          f"{targets.shape[0] - len(misses)} of {targets.shape[0]} players. "
          f"Misses: {len(misses)}.")
    print(f"  -> {OUT_CSV}")
    print(f"  -> {OUT_DB} (table capspace_clauses, indexed on join_ep_id+season)")
    print(f"  -> {OUT_TARGETS} (the sample list used, for audit)")
    if misses:
        print(f"  -> {MISS_LOG} (validate or retry via nhl- key)")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print bounded-sample composition then exit (no fetching)")
    ap.add_argument("--validate", action="store_true",
                    help="smoke-test on Coyle only (no PuckPedia inputs needed)")
    args = ap.parse_args()

    if args.validate:
        # Coyle (ep_id 60251) exercises every parser branch in one page:
        # NMC+M-NTC w/ conditions, future extension, no-clause contract, and an ELC.
        targets = pd.DataFrame({
            "player_id": [None, None],
            "ep_id":  [60251, 8888888],
            "nhl_id": [8475745, None],
            "name":   ["Charlie Coyle", "Bogus Player"],
            "source": ["validate", "validate"],
            "in_both_samples": [False, False],
        })
    else:
        for p in (INPUT_CONTRACTS_XLSX, INPUT_TRADES_XLSX):
            if not os.path.exists(p):
                sys.exit(f"Input not found: {p}  (edit paths in CONFIG)")
        targets = load_targets_bounded(INPUT_CONTRACTS_XLSX, INPUT_TRADES_XLSX, WINDOW_START)
        if args.dry_run:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            targets.to_csv(OUT_TARGETS, index=False)
            print(f"\n[dry-run] sample written to {OUT_TARGETS}. No fetching performed.")
            est_min = len(targets) * REQUEST_DELAY / 60
            print(f"[dry-run] estimated one-time fetch time @ {REQUEST_DELAY}s/req: ~{est_min:.0f} min")
            return

    print(f"\nTargets: {len(targets)} players. Cache: {CACHE_DIR}/  Delay: {REQUEST_DELAY}s")
    run(targets)


if __name__ == "__main__":
    main()
