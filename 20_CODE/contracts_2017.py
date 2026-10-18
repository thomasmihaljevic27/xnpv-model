"""
contracts_2017.py -- the contracts of players traded in 2017-18, read from CapWages, for the player model's 2017 page.

DECIDED (Thomas, 2026-10-14): "Build a 2017 page"; "Yes, fetch 25". The player model's pages start in 2018-19
because PuckPedia's contract export holds contracts running in 2018-19 or later, so 135 traded player assets of
2017-18 were valued by neither model (25_TESTS/uncovered_assets_audit.py). CapWages player pages carry each
player's whole contract history; this reads them. A SECOND CONTRACT SOURCE, used only where PuckPedia has nothing:
contract terms, never a player-value input (the single-provider rule is about value inputs).

WHAT IT DOES
  1. The traded player assets of 2017-18 (prospect_values.csv, trade season 2017) that no model values: not a
     valued prospect (contract_npv_panel has no 2017 page at all).
  2. Their CapWages pages: cached ones (10_SOURCE/capwages_cache, 30_OUTPUT/capwages_elc, capwages_top_picks) or,
     with --fetch, capwages.com/players/<first-last> into 30_OUTPUT/capwages_2017/, 1.5 seconds apart.
  3. Every contract on the page: type (standard / entry level; extension or not), signing date, length, expiry
     status (UFA / RFA), and the cap hit of each season.
  4. For each asset, the contract RUNNING on the trade date (signed on or before it; its seasons include 2017-18)
     and any extension signed on or before it. GUARD: a page with no contract covering 2017-18 is refused (a
     namesake's page, or the wrong player).

OUTPUT: OUTPUT_DIR/contracts_2017.csv (one row per asset: the running contract and any known extension, season by
season cap hits as text), contracts_2017_log.txt.
Run from the repo root:  python 20_CODE/contracts_2017.py [--fetch]
"""

import argparse
import html as H
import os
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "contracts_2017.py v1.1 (2026-10-18)"   # v1.1: a page without contracts counts as missing
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
CACHE_FETCH = OUTPUT_DIR / "capwages_2017"
CACHES = [SOURCE_DIR / "capwages_cache", OUTPUT_DIR / "capwages_elc", OUTPUT_DIR / "capwages_top_picks", CACHE_FETCH]
UA = "Mozilla/5.0 (research; xNPV thesis)"
PAGE_SEASON = 2017
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def to_slug(name):
    """elc_signing_dates.to_slug: first-last lowercase ASCII."""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    n = re.sub(r"[^A-Za-z\- ]", "", n).strip().lower()
    return re.sub(r"\s+", "-", n)


def page_lines(raw):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    return [x.strip() for x in H.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n") if x.strip()]


MONEY = re.compile(r"^\$[\d,]+$")
SEASON = re.compile(r"^(\d{4})-(\d{2})$")


def parse_contracts(lines):
    """Each contract block: a heading ending in 'Contract' or 'Contract (Extension)', then labelled fields, then a
    season table whose rows start 'YYYY-YY' with the cap hit two cells on (season, clause, cap hit, ...)."""
    out, i = [], 0
    while i < len(lines):
        head = lines[i]
        if re.match(r"^(Standard|Entry-Level|Entry Level|35\+|Professional Tryout|Two-Way)?.*Contract( \(Extension\))?$",
                     head) and i + 1 < len(lines) and lines[i + 1] == "Signed By:":
            c = {"type": head, "extension": "Extension" in head, "seasons": {}}
            j = i + 1
            while j < len(lines) and not SEASON.match(lines[j]):
                if lines[j] == "Length:":
                    m = re.match(r"(\d+)", lines[j + 1])
                    c["length"] = int(m.group(1)) if m else None
                elif lines[j] == "Expiry Status:":
                    c["expiry_status"] = lines[j + 1]
                elif lines[j] == "Signing Date:":
                    c["signing_date"] = pd.to_datetime(lines[j + 1].replace(".", ""), format="%b %d, %Y", errors="coerce")
                elif lines[j] == "Signing Team:":
                    c["signing_team"] = lines[j + 1]
                if j > i + 1 and lines[j].endswith("Contract") and lines[j + 1:j + 2] == ["Signed By:"]:
                    break
                j += 1
            while j < len(lines) and SEASON.match(lines[j]):
                # a season row runs from its label to the next season label or TOTAL (the cell count varies: a
                # clause cell may be blank or carry text); the cap hit is the row's first dollar amount
                y = int(SEASON.match(lines[j]).group(1))
                k = j + 1
                while k < len(lines) and not SEASON.match(lines[k]) and lines[k] != "TOTAL":
                    k += 1
                # cells: cap hit, AAV, performance and signing bonuses, base, total (and minors). The CBA's cap hit is
                # the AAV: the page's per-season "Cap Hit" column can differ (Marcus Johansson 2016-19: $2,750,000
                # in the column, AAV and the page's own sentence $4,583,333), so the contract's stated cap hit is
                # used (below), and the AAV column where the sentence is missing
                money = [x for x in lines[j + 1:k] if MONEY.match(x)]
                # a season belongs to the contract only if its row carries an AAV: CapWages lists placeholder rows
                # past the term ($0, no AAV; Kyle Turris's Nashville deal shows 2024-25 to 2027-28 after 2023-24)
                if len(money) > 1:
                    c["seasons"][y] = float(money[1].replace("$", "").replace(",", ""))
                    # base salary (the fifth dollar cell), which starts the qualifying-offer chain at expiry
                    c.setdefault("base", {})[y] = (float(money[4].replace("$", "").replace(",", ""))
                                                   if len(money) > 4 else None)
                j = k
            stated = [re.search(r"cap hit of \$([\d,]+)", x) for x in lines[i:j]]
            stated = [m for m in stated if m]
            if stated:
                hit = float(stated[0].group(1).replace(",", ""))
                c["seasons"] = {y: hit for y in c["seasons"]}
            out.append(c)
            i = j
        else:
            i += 1
    return out


# the page addresses CapWages uses where the trade's spelling gives a different slug (fetched 2026-10-14). v1.1
# (2026-10-18): capwages.com/players/jt-miller now answers 404; his page is j-t-miller (draft line 2011 #15 checked).
# A list is tried in order (the first is the one --fetch requests), so a copy cached under the old address still serves.
SLUG_OVERRIDES = {"J.T. Miller": ["j-t-miller", "jt-miller"], "Patrick Maroon": ["pat-maroon"]}


def slugs(name):
    return SLUG_OVERRIDES.get(name, [to_slug(name)])


def find_page(name):
    """v1.1 (2026-10-18): the first cached page, in CACHES order, that lists a contract; a page with none (Greg McKegg's
    clause-scrape copy shows career earnings of $0 and no contract block) is used only when no cache has a better one."""
    found = [d / f"{sl}.html" for sl in slugs(name) for d in CACHES if (d / f"{sl}.html").exists()]
    for f in found:
        if parse_contracts(page_lines(f.read_text(encoding="utf-8", errors="ignore"))):
            return f
    return found[0] if found else None


def has_contracts(f):
    return f is not None and bool(parse_contracts(page_lines(f.read_text(encoding="utf-8", errors="ignore"))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true",
                    help="request missing pages (or cached ones listing no contract) from capwages.com (1.5 s apart)")
    ap.add_argument("--only", nargs="+", metavar="NAME",
                    help="limit --fetch to these traded names, as trades.db spells them (v1.1)")
    args = ap.parse_args()
    log(SCRIPT_VERSION)
    v = pd.read_csv(OUTPUT_DIR / "prospect_values.csv")
    a = v[(v["valuation_page"] == PAGE_SEASON)    # 2026-10-14: the trade's page (trade_page.py)
          & ~v["status"].astype(str).str.startswith(("prospect, valued", "undrafted prospect, valued"))].copy()
    log(f"  traded player assets of {PAGE_SEASON}-{str(PAGE_SEASON + 1)[2:]} no model values: {len(a)} "
        f"({a['player_name'].nunique()} players)")

    if args.fetch:
        import requests
        CACHE_FETCH.mkdir(exist_ok=True)
        sess, got, bad = requests.Session(), 0, []
        for n in sorted(a["player_name"].unique()):
            f = CACHE_FETCH / f"{slugs(n)[0]}.html"
            # v1.1: a cached page with no contract on it counts as missing (fetched once, into CACHE_FETCH)
            if has_contracts(find_page(n)) or f.exists() or (args.only and n not in args.only):
                continue
            try:
                resp = sess.get(f"https://capwages.com/players/{f.stem}", headers={"User-Agent": UA}, timeout=20)
            except requests.RequestException as e:
                bad.append(f"{n}: {type(e).__name__}")
                continue
            time.sleep(1.5)
            if resp.status_code != 200:
                bad.append(f"{n}: HTTP {resp.status_code}")
                continue
            f.write_text(resp.text, encoding="utf-8")
            got += 1
        log(f"  fetched {got} pages into {CACHE_FETCH}; refused {len(bad)}: " + "; ".join(bad))

    rows = []
    for r in a.itertuples():
        date = pd.Timestamp(r.trade_date)
        f = find_page(r.player_name)
        rec = {"asset_id": r.asset_id, "trade_date": r.trade_date, "player_name": r.player_name,
               "acquiring_team": r.acquiring_team, "trade_cap_hit": r.cap_hit, "page": str(f) if f else ""}
        if f is None:
            rec["status"] = "no CapWages page"
            rows.append(rec)
            continue
        cons = parse_contracts(page_lines(f.read_text(encoding="utf-8", errors="ignore")))
        running = [c for c in cons if PAGE_SEASON in c["seasons"] and pd.notna(c.get("signing_date"))
                   and c["signing_date"] <= date]
        if not running:
            rec["status"] = ("page has no contract covering 2017-18 (refused: namesake or wrong page)" if cons
                             else "no contracts parsed")
            rows.append(rec)
            continue
        c = max(running, key=lambda x: x["signing_date"])
        ext = [e for e in cons if e is not c and pd.notna(e.get("signing_date")) and e["signing_date"] <= date
               and min(e["seasons"], default=0) > max(c["seasons"])]
        rec.update({"status": "contract found", "type": c["type"], "signing_date": c["signing_date"].date(),
                    "length": c.get("length"), "expiry_status": c.get("expiry_status"),
                    "first_season": min(c["seasons"]), "last_season": max(c["seasons"]),
                    "cap_hit_2017": c["seasons"].get(PAGE_SEASON),
                    "cap_hits": "; ".join(f"{y}: {h:.0f}" for y, h in sorted(c["seasons"].items()) if h is not None),
                    "known_extensions": "; ".join(f"{e['type']} signed {e['signing_date'].date()} "
                                                  f"{min(e['seasons'])}-{max(e['seasons'])}" for e in ext)})
        rows.append(rec)
    d = pd.DataFrame(rows)
    log(f"\n" + d["status"].value_counts().to_string())
    ok = d[d["status"] == "contract found"]
    agree = ok[pd.to_numeric(ok["trade_cap_hit"], errors="coerce").fillna(0) > 0]
    same = (agree["trade_cap_hit"].astype(float) - agree["cap_hit_2017"].astype(float)).abs() < 1
    log(f"  check against trades.db's cap hit (assets listed with one): {int(same.sum())} of {len(agree)} equal")
    for r in agree[~same].itertuples():
        log(f"    differ: {r.trade_date} {r.player_name}: trades.db ${float(r.trade_cap_hit):,.0f}, CapWages "
            f"${float(r.cap_hit_2017):,.0f} ({r.type}, signed {r.signing_date})")
    for r in d[d["status"] != "contract found"].itertuples():
        log(f"  {r.status}: {r.trade_date} {r.player_name}")
    d.to_csv(OUTPUT_DIR / "contracts_2017.csv", index=False)
    (OUTPUT_DIR / "contracts_2017_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote contracts_2017.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
