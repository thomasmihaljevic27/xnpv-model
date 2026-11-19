"""
clause_fill.py -- each traded player's no-trade or no-move clause at his trade's page, with the gaps in the contract
spine's clause records filled from his CapWages page (Thomas, 2026-11-19: the clause gap "has to be fixed"; declared in
40_DOCS/Backtest_Protocol.md before it was built).

WHY. The back-test read a clause only from contract_season_spine.csv (join_clauses_to_spine.py: cap-space's records on
PuckPedia's contracts), and a blank there counted as no clause. 103 of the one regression's 577 main players had a blank:
the 2017 page's contracts come from CapWages and have no spine row; cap-space's bounded sample leaves some players out
(Phaneuf, Hossa); and some cap-space records carry the wrong seasons and signing date (Kessel's eight-year deal stamped
from 2009-10), so the season join misses them.

THE RULE (the protocol's, 2026-11-19), for each traded player asset (trade_asset_values, asset_type player):
  1. the spine's flag where the spine holds a MATCHED clause record (has_any_clause not blank) for (his NHL id from
     traded_player_values, the page season): any record with a clause counts;
  2. otherwise his CapWages page (contracts_2017.find_page: the cached copies, then 30_OUTPUT/capwages_2017): the
     contract covering the page season and signed on or before the trade date (the latest such), its Clause cell for
     that season (contracts_2017.parse_contracts v1.2): any NTC or NMC, full or modified, is a clause; "-" or blank none;
     used ONLY when that season's cap hit on the page is within $1,000 of a cap hit the model holds for him: the
     contract spine's model_cap_hit for (his NHL id, the page season), the 2017 page's cap_hit_2017
     (page_2017_values), or the trade ledger's cap hit (prospect_values.csv) plus any salary the trade retained;
     the check against a namesake's page;
  3. otherwise unknown, counted as no clause by the readers and named in the log.
clause_set(output_dir) is the one place every reader takes the clause from (backtest.py's clause group,
who_overpaid_any.player_facts, groups_any). No asset's value reads a clause.

--fetch NAME ...: request those players' CapWages pages first, 1.5 s apart, into 30_OUTPUT/capwages_2017 (Thomas's
approval each time; approved 2026-11-19 for Hossa, Berglund, Schlemko, Schneider, Oleksy).

OUTPUTS: OUTPUT_DIR/clause_fill.csv (every player asset: its clause, the source that decided it, the CapWages cell),
clause_fill_log.txt. Run with OUTPUT_DIR set to each folder the back-test runs in (30_OUTPUT, 30_OUTPUT/_extended_run).
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contracts_2017 as K                                        # noqa: E402

SCRIPT_VERSION = "clause_fill.py v1.0 (2026-11-19)"
# the CapWages page caches always in the repo's own 30_OUTPUT (contracts_2017 builds them from OUTPUT_DIR, which is the
# extended run's folder when this runs there, and that copy lacks the pages fetched since it was made)
_ROOT_OUT = Path(__file__).resolve().parent.parent / "30_OUTPUT"
K.CACHE_FETCH = _ROOT_OUT / "capwages_2017"
K.CACHES = [K.SOURCE_DIR / "capwages_cache", _ROOT_OUT / "capwages_elc", _ROOT_OUT / "capwages_top_picks", K.CACHE_FETCH]
CAP_TOL = 1000.0                                                 # $ between the page's cap hit and the ledger's
CLAUSE = re.compile(r"NTC|NMC|no[- ]?trade|no[- ]?move", re.I)
LOG = []


def log(s=""):
    print(s.encode("ascii", "replace").decode())   # the console is cp1252; the log file keeps the names
    LOG.append(s)


def spine_known(output_dir):
    """(nhl_id, season) -> 1/0 where the spine holds a matched clause record (any record with a clause counts)."""
    ss = pd.read_csv(Path(output_dir) / "contract_season_spine.csv", usecols=["nhl_id", "season_start", "has_any_clause"])
    ss = ss[ss["nhl_id"].notna() & ss["has_any_clause"].notna()]
    return {(int(a), int(b)): int(v) for (a, b), v in ss.groupby(["nhl_id", "season_start"])["has_any_clause"].max().items()}


def clause_by_asset(output_dir):
    """asset_id -> (clause 1/0, source) from clause_fill.csv (written by main() in the same folder)."""
    f = pd.read_csv(Path(output_dir) / "clause_fill.csv")
    return {int(a): (None if pd.isna(c) else int(c), s) for a, c, s in zip(f["asset_id"], f["clause"], f["source"])}


def clause_set(output_dir):
    """The asset ids whose player had a clause at his trade's page: every reader's clause."""
    return {a for a, (c, _s) in clause_by_asset(output_dir).items() if c == 1}


def page_clause(name, season, date, caps):
    """(clause 1/0 or None, CapWages cell, note) for one player's page season; caps: the cap hits the model holds."""
    f = K.find_page(name)
    if f is None:
        return None, "", "no CapWages page"
    cons = K.parse_contracts(K.page_lines(f.read_text(encoding="utf-8", errors="ignore")))
    run = [c for c in cons if season in c["seasons"] and pd.notna(c.get("signing_date")) and c["signing_date"] <= date]
    if not run:
        return None, "", "page has no contract covering the season signed by the trade date"
    c = max(run, key=lambda x: x["signing_date"])
    hit, cell = c["seasons"].get(season), c.get("clause", {}).get(season, "")
    caps = [float(x) for x in caps if x is not None and np.isfinite(x) and x > 0]
    if not caps:
        return None, cell, "no cap hit held for him to check the page against"
    if hit is None or min(abs(hit - x) for x in caps) > CAP_TOL:
        return None, cell, (f"cap hit on the page ${hit or 0:,.0f} against the model's "
                            + "/".join(f"${x:,.0f}" for x in caps) + " (refused)")
    return int(bool(CLAUSE.search(cell or ""))), cell, "CapWages page"


def fetch(names):
    import requests
    K.CACHE_FETCH.mkdir(exist_ok=True)
    sess, got, bad = requests.Session(), 0, []
    for n in names:
        f = K.CACHE_FETCH / f"{K.slugs(n)[0]}.html"
        if f.exists():
            continue
        try:
            resp = sess.get(f"https://capwages.com/players/{f.stem}", headers={"User-Agent": K.UA}, timeout=20)
        except requests.RequestException as e:
            bad.append(f"{n}: {type(e).__name__}")
            continue
        time.sleep(1.5)
        if resp.status_code != 200:
            bad.append(f"{n}: HTTP {resp.status_code}")
            continue
        f.write_text(resp.text, encoding="utf-8")
        got += 1
    log(f"  fetched {got} pages into {K.CACHE_FETCH}; refused {len(bad)}: " + "; ".join(bad))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", nargs="+", metavar="NAME", help="request these players' CapWages pages first (approved)")
    args = ap.parse_args()
    out = Path(os.environ["OUTPUT_DIR"])
    log(SCRIPT_VERSION)
    log(f"  {K.SCRIPT_VERSION}; output folder {out}")
    if args.fetch:
        fetch(args.fetch)
    tav = pd.read_csv(out / "trade_asset_values.csv")
    pl = tav[tav["asset_type"] == "player"].copy()
    tpv = pd.read_csv(out / "traded_player_values.csv").drop_duplicates("asset_id").set_index("asset_id")
    pv = pd.read_csv(out / "prospect_values.csv", low_memory=False).drop_duplicates("asset_id").set_index("asset_id")
    known = spine_known(out)
    sc = pd.read_csv(out / "contract_season_spine.csv", usecols=["nhl_id", "season_start", "model_cap_hit"])
    sc = sc[sc["nhl_id"].notna() & sc["model_cap_hit"].notna()]
    spine_caps = sc.groupby([sc["nhl_id"].astype(int), sc["season_start"].astype(int)])["model_cap_hit"].apply(list).to_dict()
    p17 = pd.read_csv(out / "page_2017_values.csv").drop_duplicates("asset_id").set_index("asset_id")["cap_hit_2017"]
    rows = []
    for r in pl.itertuples():
        aid, page, date = int(r.asset_id), int(r.valuation_page), pd.Timestamp(r.trade_date)
        nid = tpv.at[aid, "nhl_id"] if aid in tpv.index else np.nan
        key = (int(nid), page) if pd.notna(nid) else None
        cap = pv.at[aid, "cap_hit"] if aid in pv.index and "cap_hit" in pv.columns else np.nan
        cap = float(cap) + float(r.retained_aav if pd.notna(r.retained_aav) else 0.0) if pd.notna(cap) else np.nan
        caps = (spine_caps.get(key, []) if key is not None else []) + [p17.get(aid, np.nan), cap]
        cw, cell, note = page_clause(r.name, page, date, caps)
        rec = {"asset_id": aid, "trade_id": r.trade_id, "trade_date": r.trade_date, "name": r.name, "page": page,
               "nhl_id": nid, "ledger_cap_hit": cap, "capwages_clause": cw, "capwages_cell": cell, "capwages_note": note}
        if key is not None and key in known:
            rec.update({"clause": known[key], "source": "contract spine", "spine_clause": known[key]})
        elif cw is not None:
            rec.update({"clause": cw, "source": "CapWages page", "spine_clause": np.nan})
        elif str(r.source).startswith("prospect model") or str(r.status).startswith("rights"):
            # no NHL contract running at the trade (a prospect, or an unsigned player's rights): no clause to carry
            # (the readers counted these as no clause before; labelled so the unknowns below are NHL players only)
            kind = "rights" if str(r.status).startswith("rights") else "prospect"
            rec.update({"clause": 0, "source": f"no NHL contract at the trade ({kind})", "spine_clause": np.nan})
        else:
            rec.update({"clause": np.nan, "source": f"unknown ({note})", "spine_clause": np.nan})
        rows.append(rec)
    d = pd.DataFrame(rows)
    log(f"\n  player assets {len(d):,}")
    log("  decided by: " + "; ".join(f"{k.split(' (')[0]} {v:,}" for k, v in
                                     d["source"].str.replace(r" \(.*", "", regex=True).value_counts().items()))
    fill = d[d["source"] == "CapWages page"]
    log(f"  filled from CapWages: {len(fill):,}, of them with a clause {int(fill['clause'].sum()):,}")
    both = d[(d["source"] == "contract spine") & d["capwages_clause"].notna()]
    agree = (both["capwages_clause"] == both["spine_clause"])
    log(f"  CHECK where both sources answer ({len(both):,} assets): CapWages agrees with the spine on {int(agree.sum()):,} "
        f"({agree.mean():.1%}); spine clause, CapWages none {int(((both['spine_clause'] == 1) & (both['capwages_clause'] == 0)).sum())}; "
        f"spine none, CapWages clause {int(((both['spine_clause'] == 0) & (both['capwages_clause'] == 1)).sum())}")
    unk = d[d["clause"].isna()]
    log(f"  still unknown (counted as no clause): {len(unk):,}")
    for x in unk.sort_values(["page", "name"]).itertuples():
        log(f"    {x.trade_date} {x.name} (page {x.page}): {x.capwages_note}")
    log("\n  filled, with a clause:")
    for x in fill[fill["clause"] == 1].sort_values(["page", "name"]).itertuples():
        log(f"    {x.trade_date} {x.name} (page {x.page}): {x.capwages_cell}")
    d.to_csv(out / "clause_fill.csv", index=False)
    (out / "clause_fill_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
