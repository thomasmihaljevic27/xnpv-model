"""
trade_ledger_reconcile.py - does PuckPedia's trades export agree with the trade ledger where the two overlap?

WHY. The back-test's trades come from trades.db (CapFriendly's record, ends 2022-03-28). PuckPedia's trades export
(10_SOURCE, May 2026) runs 2018-06-23 to 2026-05-15 and could supply the trades after March 2022 (Thomas, 2026-11-11:
"Extend", "Yes, reconcile"). Before it is used, every kind of difference between the two over the dates both cover
must be explained. This script reads both, writes neither, and values nothing.

WHAT IT COMPARES, 2018-07-01 to 2022-03-28
  1. trades: each ledger trade matched to the export trade of the same date sharing the most assets
  2. assets within matched trades: players (by name), picks (by draft year, round and original club)
  3. for matched assets: the acquiring club, the cap hit, retained salary, conditional picks
  4. trades and assets only one side has, described by what they are

BAKED-IN ASSUMPTIONS
  - a player is matched on his name (accents, punctuation and case removed; the first two and last six letters) and on
    the trade date, one day either way
  - a pick is matched on (draft year, round, original club); the export's original club is draft_pick_team
  - club codes: the export's NAS, WAS, UTA (Arizona's later code), and any others listed in CODES, mapped to the ledger's
  - the export's acquirer is to_team; the ledger's is its leg's acquiring_team
  - the ledger's cap_hit_aav is compared with the export's cap_hit and with cap_hit minus retained_hit
  - a three-team ledger trade may be several export trades (linked_trade_id); a ledger trade is matched to the UNION of
    export trades on the date that share an asset with it

INPUTS: SOURCE_DIR/trades.db, SOURCE_DIR/PuckPedia_Trades_Contract_Export_May_22_2026__CONFIDENTIAL.csv
OUTPUTS: OUTPUT_DIR/trade_ledger_reconcile_log.txt, trade_ledger_reconcile_assets.csv
"""
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "trade_ledger_reconcile.py v1.1 (2026-11-11)"   # v1.1: a date one day apart still matches; names keyed on first two and last six letters
START, END = "2018-07-01", "2022-03-28"
CODES = {"NAS": "NSH", "WAS": "WSH", "UTA": "ARI", "LA": "LAK", "NJ": "NJD", "SJ": "SJS", "TB": "TBL", "VEG": "VGK",
         "CLB": "CBJ", "MON": "MTL", "CAL": "CGY", "WIN": "WPG", "ANH": "ANA", "PHX": "ARI"}
LOG = []


def log(s=""):
    print(s)
    LOG.append(s)


def nm(s):
    """Name key: letters only, then the first two and last six (Nic / Nicolas Petan, Zach / Zachary Sanford agree)."""
    x = re.sub("[^a-z]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
    return x[:2] + x[-6:]


def season(d):
    return int(d[:4]) if d[5:7] >= "07" else int(d[:4]) - 1


def main():
    log(SCRIPT_VERSION)
    con = sqlite3.connect(SOURCE_DIR / "trades.db")
    L = pd.read_sql("select a.*, t.trade_date, t.n_teams, l.acquiring_team from trade_assets a join trades t using(trade_id) "
                    "join trade_legs l using(leg_id) where t.trade_date between ? and ?", con, params=(START, END))
    E = pd.read_csv(SOURCE_DIR / "PuckPedia_Trades_Contract_Export_May_22_2026__CONFIDENTIAL.csv", low_memory=False)
    E["trade_date"] = pd.to_datetime(E["trade_date"]).dt.strftime("%Y-%m-%d")
    E = E[E["trade_date"].between(START, END)].copy()
    for c in ("from_team", "to_team", "draft_pick_team"):
        E[c] = E[c].map(lambda x: CODES.get(x, x))
    log(f"  club codes in the export not in the ledger after mapping: "
        f"{sorted(set(E['to_team'].dropna()) - set(L['acquiring_team']))}; in the ledger not the export: "
        f"{sorted(set(L['acquiring_team']) - set(E['to_team'].dropna()))}")
    # ---- one key per asset ------------------------------------------------------------------------------------------------
    L["kind"] = L["asset_type"]
    L["key"] = [("P|" + nm(r.player_name)) if r.asset_type == "player" else
                f"K|{int(r.pick_year)}|{int(r.pick_round)}|{r.pick_original_team}" if pd.notna(r.pick_year) else f"?|{r.asset_id}"
                for r in L.itertuples()]
    E["kind"] = ["player" if pd.notna(p) else "pick" if pd.notna(k) else "other" for p, k in zip(E["player_id"], E["draft_pick_id"])]
    E["key"] = [("P|" + nm(str(r.first_name) + str(r.last_name))) if r.kind == "player" else
                f"K|{int(r.draft_year)}|{int(r.draft_round)}|{r.draft_pick_team}" if r.kind == "pick" and pd.notna(r.draft_year)
                else f"?|{r.trade_detail_id}" for r in E.itertuples()]
    log(f"  ledger: {L['trade_id'].nunique()} trades, {len(L)} assets ({(L['kind'] == 'player').sum()} players, {(L['kind'] == 'pick').sum()} picks)")
    log(f"  export: {E['trade_id'].nunique()} trades, {len(E)} rows ({(E['kind'] == 'player').sum()} players, {(E['kind'] == 'pick').sum()} picks, "
        f"{(E['kind'] == 'other').sum()} neither)")
    log(f"  export rows whose from and to club are the same: {(E['from_team'] == E['to_team']).sum()}; pick rows flagged "
        f"'asset not transferred': {int(E['draft_pick_asset_not_transferred'].sum())}")

    # ---- 1. match trades -------------------------------------------------------------------------------------------------
    emap = {}                                                                # ledger trade -> set of export trade ids
    used = set()
    for d, lg in L.groupby("trade_date"):
        near = [(pd.Timestamp(d) + pd.Timedelta(days=k)).strftime("%Y-%m-%d") for k in (-1, 0, 1)]   # the export dates some trades a day earlier
        eg = E[E["trade_date"].isin(near)]
        for tid, g in lg.groupby("trade_id"):
            keys = set(g["key"])
            hit = set(eg.loc[eg["key"].isin(keys), "trade_id"])
            emap[tid] = hit
            used |= hit
    Lt = L.groupby("trade_id").agg(date=("trade_date", "first"), n=("asset_id", "size"), n_teams=("n_teams", "first"),
                                   minor=("is_ahl_jr", "min"), cap=("cap_hit_aav", lambda x: x.fillna(0).max()),
                                   picks=("kind", lambda x: (x == "pick").sum()),
                                   names=("player_name", lambda x: "; ".join(x.dropna()))).reset_index()
    Lt["matched"] = Lt["trade_id"].map(lambda t: len(emap[t]) > 0)
    Lt["season"] = Lt["date"].map(season)
    Et = E.groupby("trade_id").agg(date=("trade_date", "first"), n=("trade_detail_id", "size"),
                                   cap=("cap_hit", "max"), details=("details", "first")).reset_index()
    Et["matched"] = Et["trade_id"].isin(used)
    Et["season"] = Et["date"].map(season)
    log("\n1. TRADES BY SEASON (starting year)")
    log(f"  {'season':<8}{'ledger':>8}{'in export':>11}{'ledger only':>13}{'export':>9}{'in ledger':>11}{'export only':>13}")
    for y in sorted(set(Lt["season"]) | set(Et["season"])):
        a, b = Lt[Lt["season"] == y], Et[Et["season"] == y]
        log(f"  {y:<8}{len(a):>8}{a['matched'].sum():>11}{(~a['matched']).sum():>13}{len(b):>9}{b['matched'].sum():>11}{(~b['matched']).sum():>13}")
    lo = Lt[~Lt["matched"]]
    log(f"\n  LEDGER-ONLY TRADES ({len(lo)}): every player a minor-leaguer or junior (is_ahl_jr) {int((lo['minor'] == 1).sum())}; "
        f"highest cap hit $0 {int((lo['cap'] == 0).sum())}; under $1M {int((lo['cap'] < 1e6).sum())}; $1M or more {int((lo['cap'] >= 1e6).sum())}")
    for y in sorted(lo["season"].unique()):
        z = lo[(lo["season"] == y)]
        log(f"    {y}: {len(z)} trades; with a cap hit of $1M or more: {int((z['cap'] >= 1e6).sum())}; first and last date {z['date'].min()} to {z['date'].max()}")
    big = lo[(lo["cap"] >= 1e6) & (lo["season"] >= 2019)]
    log(f"  ledger-only trades from 2019-20 on with a cap hit of $1M or more ({len(big)}):")
    for r in big.itertuples():
        log(f"    {r.date}  ${r.cap / 1e6:.2f}M  {r.names[:90]}")
    eo = Et[~Et["matched"]]
    log(f"\n  EXPORT-ONLY TRADES ({len(eo)}): by season {eo.groupby('season').size().to_dict()}")
    for r in eo.head(25).itertuples():
        log(f"    {r.date}  {str(r.details)[:150]}")
    first_e = Et.groupby("season")["date"].min().to_dict()
    log(f"  the export's first trade date in each season: {first_e}")

    # ---- 2, 3. assets of matched trades ----------------------------------------------------------------------------------
    rows = []
    for tid, g in L.groupby("trade_id"):
        if not emap[tid]:
            continue
        eg = E[E["trade_id"].isin(emap[tid])]
        ek = {k: x for k, x in eg.groupby("key")}
        for r in g.itertuples():
            x = ek.get(r.key)
            rec = {"ledger_trade": tid, "date": r.trade_date, "season": season(r.trade_date), "kind": r.kind, "key": r.key,
                   "n_teams": r.n_teams, "in_export": x is not None, "l_acq": r.acquiring_team, "l_cap": r.cap_hit_aav,
                   "l_ret": r.retained_aav, "l_cond": r.is_conditional, "l_minor": r.is_ahl_jr, "l_rights": r.is_signing_rights}
            if x is not None:
                # a three-team trade can list an asset twice (two hops): take the row with the ledger's acquirer if any
                y = x[x["to_team"] == r.acquiring_team]
                y = (y if len(y) else x).iloc[0]
                rec.update({"e_acq": y["to_team"], "e_from": y["from_team"], "e_cap": y["cap_hit"], "e_ret": y["retained_hit"],
                            "e_cond": int(pd.notna(y["draft_pick_conditions"])), "e_rows": len(x),
                            "e_not_transferred": y["draft_pick_asset_not_transferred"]})
            rows.append(rec)
        lk = set(g["key"])
        for r in eg[~eg["key"].isin(lk)].itertuples():
            rows.append({"ledger_trade": tid, "date": r.trade_date, "season": season(r.trade_date), "kind": r.kind, "key": r.key,
                         "in_export": True, "in_ledger": False, "e_acq": r.to_team, "e_from": r.from_team, "e_cap": r.cap_hit,
                         "e_ret": r.retained_hit, "e_not_transferred": r.draft_pick_asset_not_transferred})
    A = pd.DataFrame(rows)
    A["in_ledger"] = A["in_ledger"].fillna(True).astype(bool)
    A.to_csv(OUTPUT_DIR / "trade_ledger_reconcile_assets.csv", index=False)
    both = A[A["in_ledger"] & A["in_export"]]
    log("\n2. ASSETS OF THE MATCHED TRADES")
    log(f"  {'season':<8}{'kind':<8}{'ledger':>8}{'in both':>9}{'ledger only':>13}{'export only':>13}")
    for (y, k), g in A.groupby(["season", "kind"]):
        log(f"  {y:<8}{k:<8}{int(g['in_ledger'].sum()):>8}{int((g['in_ledger'] & g['in_export']).sum()):>9}"
            f"{int((g['in_ledger'] & ~g['in_export']).sum()):>13}{int((~g['in_ledger']).sum()):>13}")
    lonly = A[A["in_ledger"] & ~A["in_export"]]
    pl = lonly[lonly["kind"] == "player"]
    log(f"  ledger-only players in matched trades ({len(pl)}): minor-leaguer or junior {int((pl['l_minor'] == 1).sum())}, signing rights "
        f"{int((pl['l_rights'] == 1).sum())}, cap hit $0 or blank {int((pl['l_cap'].fillna(0) == 0).sum())}, cap hit above $0 {int((pl['l_cap'].fillna(0) > 0).sum())}")
    for r in pl[pl["l_cap"].fillna(0) > 0].head(20).itertuples():
        log(f"    {r.date} {r.key} ${r.l_cap / 1e6:.2f}M to {r.l_acq}")
    pk = lonly[lonly["kind"] == "pick"]
    log(f"  ledger-only picks in matched trades ({len(pk)}): conditional {int((pk['l_cond'] == 1).sum())}")
    for r in pk.head(15).itertuples():
        log(f"    {r.date} {r.key} to {r.l_acq} conditional={r.l_cond}")
    eonly = A[~A["in_ledger"]]
    log(f"  export-only assets in matched trades ({len(eonly)}): {eonly['kind'].value_counts().to_dict()}; pick rows flagged not transferred "
        f"{int(eonly['e_not_transferred'].fillna(0).sum())}")
    for r in eonly.head(20).itertuples():
        log(f"    {r.date} {r.key} {r.e_from}->{r.e_acq}")

    log("\n3. MATCHED ASSETS: do the facts agree")
    acq = both["l_acq"] == both["e_acq"]
    log(f"  acquiring club equal: {int(acq.sum())} of {len(both)}; in two-team trades {int((acq & (both['n_teams'] == 2)).sum())} of "
        f"{int((both['n_teams'] == 2).sum())}; in three-team trades {int((acq & (both['n_teams'] == 3)).sum())} of {int((both['n_teams'] == 3).sum())}")
    for r in both[~acq & (both["n_teams"] == 2)].head(15).itertuples():
        log(f"    {r.date} {r.key}: ledger to {r.l_acq}; export {r.e_from}->{r.e_acq}")
    p = both[(both["kind"] == "player")].copy()
    p["l_cap"] = p["l_cap"].fillna(0)
    p["l_ret"] = p["l_ret"].fillna(0)
    full = (p["l_cap"] - p["e_cap"]).abs() <= 1000
    net = (p["l_cap"] - (p["e_cap"] - p["e_ret"])).abs() <= 1000
    zero = (p["l_cap"] == 0)
    log(f"  players' cap hit ({len(p)}): ledger equals the export's cap hit {int(full.sum())}; equals cap hit minus retained "
        f"{int((net & ~full).sum())}; ledger shows $0 (minor-league or unsigned) {int((zero & ~full & ~net).sum())}; "
        f"neither {int((~full & ~net & ~zero).sum())}")
    oth = p[~full & ~net & ~zero].assign(diff=lambda x: x["l_cap"] - x["e_cap"])
    log(f"    of the {len(oth)} that differ: ledger lower {int((oth['diff'] < 0).sum())}, higher {int((oth['diff'] > 0).sum())}; median "
        f"absolute difference ${oth['diff'].abs().median():,.0f}; within $100,000 {int((oth['diff'].abs() <= 1e5).sum())}; by season "
        f"{oth.groupby('season').size().to_dict()}")
    for r in oth.sort_values("diff", key=abs, ascending=False).head(15).itertuples():
        log(f"    {r.date} {r.key}: ledger ${r.l_cap:,.0f} (retained ${r.l_ret:,.0f}); export ${r.e_cap:,.0f} (retained ${r.e_ret:,.0f})")
    lr, er = p["l_ret"] > 0, p["e_ret"] > 0
    log(f"  retained salary: both show it {int((lr & er).sum())}; ledger only {int((lr & ~er).sum())}; export only {int((~lr & er).sum())}; "
        f"where both do, the amount equal to $1,000: {int(((p['l_ret'] - p['e_ret']).abs() <= 1000)[lr & er].sum())}")
    for r in p[lr ^ er].head(15).itertuples():
        log(f"    {r.date} {r.key}: ledger retained ${r.l_ret:,.0f}; export ${r.e_ret:,.0f}")
    k = both[both["kind"] == "pick"]
    log(f"  picks ({len(k)}): conditional in both {int(((k['l_cond'] == 1) & (k['e_cond'] == 1)).sum())}; ledger only "
        f"{int(((k['l_cond'] == 1) & (k['e_cond'] == 0)).sum())}; export only {int(((k['l_cond'] == 0) & (k['e_cond'] == 1)).sum())}; neither "
        f"{int(((k['l_cond'] == 0) & (k['e_cond'] == 0)).sum())}")
    t3 = Lt[(Lt["n_teams"] == 3) & Lt["matched"]]
    log(f"  three-team ledger trades matched: {len(t3)}; export trades each is spread over: "
        f"{sorted(len(emap[t]) for t in t3['trade_id'])}")
    multi = [t for t in Lt.loc[Lt["matched"] & (Lt["n_teams"] == 2), "trade_id"] if len(emap[t]) > 1]
    log(f"  two-team ledger trades matched to more than one export trade: {len(multi)}")
    for t in multi[:10]:
        log(f"    ledger {t} {Lt.set_index('trade_id').at[t, 'date']}: export trades {sorted(emap[t])}; {Lt.set_index('trade_id').at[t, 'names'][:70]}")
    (OUTPUT_DIR / "trade_ledger_reconcile_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
