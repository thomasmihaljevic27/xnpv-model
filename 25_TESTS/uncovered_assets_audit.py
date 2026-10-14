"""
uncovered_assets_audit.py -- which traded players does neither the player model nor the prospect model value?
(report only; changes no value)

ASKED (Thomas, 2026-10-14): "Value veterans neither model covers" -- first count them and bring options.
Found while building the undrafted step (prospect_values.py v1.3): veterans on NHL contracts with no recent NHL
season (David Clarkson's $5.25M long-term-injury contract; goalies Mike McKenna and Andrew Hammond).

WHAT IT DOES
  1. Every traded player asset in trades.db from 2017-07-01 (prospect_values.csv's 927 rows, with its matching).
  2. His NHL id: the id tier's (PuckPedia), else the drafted match's (draft_pick_linkage playerId), else the
     undrafted path's (prospect_values v1.3).
  3. Covered by the prospect model: a "prospect, valued" or "undrafted prospect, valued" row.
     Covered by the player model: a contract_npv_panel.csv row for his id at the trade season's page
     (valuation_season = the season starting July 1 on or before the trade; the panel's pages run 2018-2026).
  4. Everything else is uncovered, with the reason, and for those on an NHL contract (a PuckPedia contract of his
     running on the trade date) the contract: cap hit, last season, seasons left from the trade season.

INPUTS: OUTPUT_DIR/prospect_values.csv, contract_npv_panel.csv, draft_pick_linkage.csv; the PuckPedia contract
export (through contract_source.py). OUTPUTS: OUTPUT_DIR/uncovered_assets_audit.csv and its log.
Run from the repo root:  python 25_TESTS/uncovered_assets_audit.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "uncovered_assets_audit.py v1.1 (2026-10-14)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import contract_source as CS   # noqa: E402
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"values": OUTPUT_DIR / "prospect_values.csv", "panel": OUTPUT_DIR / "contract_npv_panel.csv",
     "linkage": OUTPUT_DIR / "draft_pick_linkage.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

v = pd.read_csv(F["values"])
panel = pd.read_csv(F["panel"], low_memory=False, usecols=["player_id", "valuation_season", "npv_total"])
FIRST_PAGE = int(panel["valuation_season"].min())
link = pd.read_csv(F["linkage"])[["draftYear", "overallPickNumber", "playerId"]]
LID = {(int(a), int(b)): int(c) for a, b, c in zip(link["draftYear"], link["overallPickNumber"], link["playerId"])
       if pd.notna(c)}
pc, _ = CS.load_contracts()
# the panel's player_id is PuckPedia's own id, not the NHL id (Jack Eichel: 6363 and 8478403): translate
PP2NHL = {int(a): int(b) for a, b in zip(pc["player_id"], pc["nhl_id"]) if pd.notna(a) and pd.notna(b)}
unmapped = set(panel["player_id"].astype(int)) - set(PP2NHL)
assert not unmapped, f"panel ids without an NHL id: {len(unmapped)}"          # GUARD
PRICED = {(PP2NHL[int(p)], int(s)) for p, s in zip(panel["player_id"], panel["valuation_season"])}
pc = pc.dropna(subset=["nhl_id", "signing_date", "contract_end"]).copy()
pc["signed"] = pd.to_datetime(pc["signing_date"], format="%m/%d/%Y")
pc["ends"] = pc["contract_end"].astype(str).str[-4:].astype(int).map(lambda y: pd.Timestamp(y, 6, 30))
pc["last_season"] = pc["contract_end"].astype(str).str[:4].astype(int)
PC = dict(tuple(pc.groupby(pc["nhl_id"].astype(int))))


def nhl_id(r):
    for c in ("nhl_id", "nhl_id_undrafted"):
        if c in r and pd.notna(r[c]):
            return int(r[c])
    if pd.notna(r.get("draftYear")) and pd.notna(r.get("pick")):
        return LID.get((int(r["draftYear"]), int(r["pick"])))
    return None


rows = []
for _, r in v.iterrows():
    i = nhl_id(r)
    date = pd.Timestamp(r["trade_date"])
    y = int(r["valuation_page"])        # v1.2: the trade's page (trade_page.py)
    st = str(r["status"])
    rec = {"asset_id": r["asset_id"], "trade_date": r["trade_date"], "trade_season": r["trade_season"], "valuation_page": y, "player_name": r["player_name"],
           "acquiring_team": r["acquiring_team"], "trade_cap_hit": r["cap_hit"], "nhl_id": i, "prospect_status": st}
    con = None
    if i is not None and i in PC:
        run = PC[i][(PC[i]["signed"] <= date) & (PC[i]["ends"] >= date)]
        if len(run):
            con = run.sort_values("signed").iloc[-1]
            rec.update({"pp_cap_hit": float(con["cap_hit"]), "pp_last_season": int(con["last_season"]),
                        "seasons_left": int(con["last_season"]) - y + 1, "pp_level": con["contract_level"],
                        "pp_signed": con["signing_date"]})
    if st.startswith(("prospect, valued", "undrafted prospect, valued")):
        rec["covered_by"] = "prospect model"
    elif i is not None and (i, y) in PRICED:
        rec["covered_by"] = "player model"
    else:
        rec["covered_by"] = "neither"
        if st.startswith(("undrafted, no NHL contract", "undrafted, signing rights only")):
            why = "zero by rule (no NHL contract, or expired signing rights)"
        elif i is None:
            why = "not identified (no NHL id)"
        elif y < FIRST_PAGE:
            why = f"traded before the player model's first page ({FIRST_PAGE}-{str(FIRST_PAGE + 1)[2:]})"
        elif con is None:
            why = "no NHL contract running on the trade date in PuckPedia"
        elif "control over" in st:
            why = "veteran on an NHL contract, past club control, no recent NHL season"
        else:
            why = "on an NHL contract, but the player model has no row for him at that page"
        rec["why"] = why
    rows.append(rec)
a = pd.DataFrame(rows)
# v1.2: the player model counts a traded player as valued only where traded_player_values.py priced him at his
# trade's page (a panel row at the page can be a contract signed after a post-season trade: Kevin Hayes 2019)
tpv = OUTPUT_DIR / "traded_player_values.csv"
if tpv.exists():
    t_ = pd.read_csv(tpv)
    a.loc[a["asset_id"].isin(set(t_["asset_id"])) & (a["covered_by"] == "player model"), "covered_by"] = "neither"
    a.loc[a["asset_id"].isin(set(t_.loc[t_["status"] == "ok", "asset_id"])), "covered_by"] = "player model"
    ro_ = set(t_.loc[t_["status"].astype(str).str.startswith(("rights only", "no contract at the page")), "asset_id"])
    a.loc[a["asset_id"].isin(ro_), "why"] = "rights only at the page (post-season trade; not valued)"
    # v1.3: rights valued by rights_values.py (adopted 2026-10-14)
    rv_ = set(t_.loc[t_["status"].astype(str).str.startswith("rights:"), "asset_id"])
    a.loc[a["asset_id"].isin(rv_), "covered_by"] = "player model, rights"
# v1.1: the 2017 page (page_2017_values.py) and the buried-contract rule (buried_contract_values.py), where run
for f, lab, ok in (("page_2017_values.csv", "player model, 2017 page", ("ok",)),
                   ("page_2017_values.csv", "buried-contract rule", ("buried veteran (cost above burial)",)),
                   ("buried_contract_values.csv", "buried-contract rule", None)):
    p_ = OUTPUT_DIR / f
    if p_.exists():
        x_ = pd.read_csv(p_)
        ids_ = set(x_["asset_id"] if ok is None else x_.loc[x_["status"].isin(ok), "asset_id"])
        a.loc[a["asset_id"].isin(ids_) & (a["covered_by"] == "neither"), "covered_by"] = lab

log(f"\nTRADED PLAYER ASSETS from 2017-07-01: {len(a)}")
log(a["covered_by"].value_counts().to_string())
n = a[a["covered_by"] == "neither"]
log(f"\nNEITHER MODEL ({len(n)} assets), by reason:")
log(n["why"].value_counts().to_string())
on_c = n[n["pp_cap_hit"].notna()]
log(f"\n  of them on an NHL contract running on the trade date (PuckPedia): {len(on_c)} assets, "
    f"{on_c['player_name'].nunique()} players; cap hits total ${on_c['pp_cap_hit'].sum() / 1e6:,.2f}M a season")
for why, g in on_c.groupby("why"):
    log(f"\n  {why}: {len(g)}")
    for r in g.sort_values("pp_cap_hit", ascending=False).itertuples():
        log(f"    {r.trade_date}  {r.player_name:<24} ${r.pp_cap_hit / 1e6:5.3f}M to {r.pp_last_season}-"
            f"{str(r.pp_last_season + 1)[2:]} ({r.seasons_left} season{'s' if r.seasons_left != 1 else ''} from the "
            f"trade season), {r.pp_level}; to {r.acquiring_team}")
early = n[n["why"].str.startswith("traded before")]
log(f"\n  traded before the player model's first page: {len(early)} assets "
    f"({early['player_name'].nunique()} players); prospect-model statuses among them: "
    + ", ".join(f"{k} {v_}" for k, v_ in early["prospect_status"].value_counts().items()))

a.to_csv(OUTPUT_DIR / "uncovered_assets_audit.csv", index=False)
(OUTPUT_DIR / "uncovered_assets_audit_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote uncovered_assets_audit.csv and its log in {OUTPUT_DIR}")
