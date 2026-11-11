"""
trade_ledger_extend.py - the trade ledger carried past 2022-03-28 from PuckPedia's trades export
(Thomas, 2026-11-11: "Extend", "Yes, reconcile", "Yes, build it").

WHY. trades.db (CapFriendly's record) ends 2022-03-28 and CapFriendly has closed. PuckPedia's trades export
(SOURCE_DIR, May 2026) runs 2019-02-22 to 2026-05-15. 25_TESTS/trade_ledger_reconcile.py showed that from 2019-20 on it
holds 317 of the ledger's 320 trades with the same acquiring club for 1,037 of 1,044 matched assets.

WHAT IT WRITES. OUTPUT_DIR/trades_extended.db: a copy of trades.db, unchanged, plus every export trade from
--from (default 2022-03-29) in the SAME tables and columns, so the trade chain reads it without a second code path.
trades.db itself is never written (10_SOURCE is read-only). The chain reads the extended ledger only when the
environment variable XNPV_TRADES_DB names it (trade_page.ledger_path()); without it nothing changes.

HOW AN EXPORT ROW BECOMES A LEDGER ROW (each a baked-in assumption)
  1. NOT TRADES, left out and listed: expansion-draft selections, forfeited picks, offer-sheet compensation
     (the export's `details` text), and, in a trade of three or more
     clubs, rows whose from and to club are the same (an error in the export). In a two-club trade such a row is
     repaired: the receiving club is the other club.
     A trade and its exact reverse within seven days (a trade the league voided) are both left out.
  2. ONE TRADE: export trades sharing a linked_trade_id on one date are one multi-club trade (as the ledger's
     three-team trades); every other export trade_id is one trade.
  3. CLUBS: every club that sent or received an asset gets a leg, in alphabetical order; the export's NAS, WAS and
     UTA (its code for Arizona) are written NSH, WSH and ARI, as the ledger. Seasons from 2024-25 keep UTA.
  4. from_team is filled only in trades of three or more clubs, as the ledger.
  5. CAP HIT: the export's cap_hit is the contract's. cap_hit_aav here is the acquirer's share, the contract's cap
     hit less everything retained on it so far (the ledger's meaning). The ledger also takes off buried-contract
     relief and writes $0 for a minor-leaguer; this file does neither (no chain step reads the cap hit for that).
  6. RETAINED SALARY: the export's retained_hit is CUMULATIVE over every club that has retained on the contract.
     What THIS trade's sender kept = retained_hit minus the largest retained_hit on an earlier row for the same
     player and the same cap hit (an earlier trade in the export, or the previous hop of a multi-club trade).
     retention_pct = kept / (kept + cap_hit_aav), as trade_page.retention() defines it. A retention older than the
     export's first trade (2019-02-22) cannot be seen and would be charged to this trade's sender; none can occur
     after 2022 unless a contract with a retention before February 2019 was traded again more than three years on.
  7. MINOR-LEAGUER (is_ahl_jr): the export has no flag. Rule (Thomas, 2026-11-11): a player with no NHL
     regular-season game in the 365 days before the trade date (nhl_gamelogs.sqlite, by NHL id). 365 days, not
     "this season to date", so that an off-season trade reads the season just played.
  8. SIGNING RIGHTS (is_signing_rights): a player row with a cap hit of $0 (no contract in the export).
  9. PICKS: draft year, round and original club (draft_pick_team). pick_number is the export's overall_position
     only for drafts already held when the export was made (2025 and earlier); for later drafts it is a projection
     and is left blank. is_conditional: the export's draft_pick_conditions is filled (it under-records: 14 of 71 of
     the ledger's conditional picks were missed where the two overlap).
 10. raw_text is written in the ledger's style, with "($X retained - P%)" exactly when the row has a retention, so
     trade_page.retention()'s text guard holds.

--from DATE with a date inside the ledger (the validation build) first removes the ledger's trades from that date.

INPUTS: SOURCE_DIR/trades.db, the PuckPedia trades export (forecast_config.F_TRADES_CSV), nhl_gamelogs.sqlite.
OUTPUTS: OUTPUT_DIR/<--out, default trades_extended.db>, trade_ledger_extend_log.txt (or <out>_log.txt).
"""
import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()
import contract_source as CS                         # noqa: E402  the export's reader (encoding, column check)

SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
SCRIPT_VERSION = "trade_ledger_extend.py v1.0 (2026-11-11)"
LEDGER_END = "2022-03-28"
CODES = {"NAS": "NSH", "WAS": "WSH"}                 # UTA handled by date (Arizona before 2024-25)
NOT_TRADES = r"expansion draft|forfeit|offer sheet"
LAST_DRAFT_HELD = 2025                               # the export is dated May 2026
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th"}
LOG = []


def log(s=""):
    print(s)
    LOG.append(s)


def season_label(d):
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2022-03-29", help="first trade date taken from the export")
    ap.add_argument("--to", dest="end", default="2099-12-31")
    ap.add_argument("--out", default="trades_extended.db")
    args = ap.parse_args()
    log(SCRIPT_VERSION)
    out = OUTPUT_DIR / args.out
    E, enc = CS.load_trades()
    E = E.copy()
    E["date"] = CS.parse_export_dates(E["trade_date"], "PuckPedia trade_date")
    log(f"  export ({enc}): {len(E):,} rows, {E['trade_id'].nunique()} trades, {E['date'].min().date()} to {E['date'].max().date()}")

    # ---- 6 (first, on the whole export): what was already retained before each row --------------------------------------
    E["kind"] = ["player" if pd.notna(p) else "pick" for p in E["player_id"]]
    assert (E["player_id"].notna() ^ E["draft_pick_id"].notna()).all(), "an export row is neither or both a player and a pick"
    E["retained_hit"] = E["retained_hit"].fillna(0.0)
    E["cap_hit"] = E["cap_hit"].fillna(0.0)
    E = E.sort_values(["date", "retained_hit", "trade_detail_id"], kind="stable").reset_index(drop=True)
    prior = []
    seen = {}                                          # (player_id, cap hit) -> largest retained so far
    for r in E.itertuples():
        if r.kind != "player":
            prior.append(0.0)
            continue
        k = (int(r.player_id), round(r.cap_hit))
        prior.append(seen.get(k, 0.0))
        seen[k] = max(seen.get(k, 0.0), r.retained_hit)
    E["prior_retained"] = prior
    E["kept_now"] = (E["retained_hit"] - E["prior_retained"]).clip(lower=0.0)
    E.loc[E["kept_now"] < 1.0, "kept_now"] = 0.0

    # ---- the window, and 1: what is not a trade --------------------------------------------------------------------------
    W = E[(E["date"] >= args.start) & (E["date"] <= args.end)].copy()
    nt = W["details"].fillna("").str.contains(NOT_TRADES, case=False)
    log(f"\n  window {args.start} to {W['date'].max().date()}: {W['trade_id'].nunique()} export trades, {len(W)} rows")
    log(f"  1. not trades, left out: {W.loc[nt, 'trade_id'].nunique()} entries")
    for d in W.loc[nt].drop_duplicates("trade_id").itertuples():
        if "expansion draft" not in str(d.details).lower():
            log(f"       {d.date.date()} {str(d.details)[:130]}")
    log(f"       of them expansion-draft selections: {W.loc[nt & W['details'].str.contains('expansion draft', case=False), 'trade_id'].nunique()}")
    W = W[~nt]
    for c in ("from_team", "to_team", "draft_pick_team"):
        W[c] = W[c].map(lambda x: CODES.get(x, x))
        W.loc[(W[c] == "UTA") & (W["date"] < "2024-07-01"), c] = "ARI"
    same = W["from_team"] == W["to_team"]
    log(f"     rows whose from and to club are the same (an error in the export): {int(same.sum())}")
    drop = []
    for i, r in W[same].iterrows():
        # in a two-club trade the receiving club can only be the other club: repaired; otherwise left out
        mates = W[(W["trade_id"] == r["trade_id"]) & ~same]
        others = (set(mates["from_team"]) | set(mates["to_team"])) - {r["from_team"]}
        if len(others) == 1 and pd.isna(r["linked_trade_id"]):
            W.at[i, "to_team"] = others.pop()
            how = f"repaired: to {W.at[i, 'to_team']}"
        else:
            drop.append(i)
            how = "left out"
        log(f"       {r['date'].date()} {r['from_team']}->{r['from_team']} pick {r['draft_year']:.0f} round {r['draft_round']:.0f}: {how} | {str(r['details'])[:80]}")
    W = W.drop(index=drop)
    assert W["from_team"].notna().all() and W["to_team"].notna().all()

    # a trade the league voided: the export lists it, then its exact reverse within seven days (Dadonov, March 2022)
    pw = W[W["kind"] == "player"]
    sig = {t: frozenset(zip(g["player_id"].astype(int), g["from_team"], g["to_team"])) for t, g in pw.groupby("trade_id")}
    rev = {t: frozenset((p_, b, a_) for p_, a_, b in v) for t, v in sig.items()}
    day = W.groupby("trade_id")["date"].first()
    void = set()
    for t, v in sig.items():
        for u, w in rev.items():
            if u != t and v == w and abs((day[t] - day[u]).days) <= 7:
                void |= {t, u}
    log(f"     voided trades (a trade and its exact reverse within seven days), left out: {len(void)} entries")
    for t in sorted(void):
        log(f"       {day[t].date()} {str(W.loc[W['trade_id'] == t, 'details'].iloc[0])[:120]}")
    W = W[~W["trade_id"].isin(void)]

    # ---- 2: one trade ----------------------------------------------------------------------------------------------------
    W["gid"] = [f"L{int(l)}|{d.date()}" if pd.notna(l) else f"T{int(t)}" for l, t, d in zip(W["linked_trade_id"], W["trade_id"], W["date"])]
    assert W.groupby("gid")["date"].nunique().max() == 1, "a trade spans two dates"

    # ---- 7: minor-leaguers from the game logs ------------------------------------------------------------------------------
    gl = sqlite3.connect(SOURCE_DIR / "nhl_gamelogs.sqlite")
    games = pd.concat([pd.read_sql(f"select s.player_id, g.game_date from {t} s join games g using(game_id) where g.game_type = 2", gl)
                       for t in ("skater_games", "goalie_games")])
    games["game_date"] = pd.to_datetime(games["game_date"])
    by_p = {int(p): g["game_date"].values for p, g in games.groupby("player_id")}

    def played_recently(nid, d):
        if pd.isna(nid) or int(nid) not in by_p:
            return False
        x = by_p[int(nid)]
        return bool(((x < d.to_datetime64()) & (x >= (d - pd.Timedelta(days=365)).to_datetime64())).any())
    W["minor"] = [0 if r.kind != "player" else int(not played_recently(r.nhl_id, r.date)) for r in W.itertuples()]

    # ---- write -----------------------------------------------------------------------------------------------------------
    shutil.copy2(SOURCE_DIR / "trades.db", out)
    con = sqlite3.connect(out)
    cur = con.cursor()
    if args.start <= LEDGER_END:                       # the validation build: the export replaces the ledger from --from
        ids = [r[0] for r in cur.execute("select trade_id from trades where trade_date >= ?", (args.start,))]
        for t in ("trade_assets", "trade_legs", "trade_conditions", "trades"):
            cur.executemany(f"delete from {t} where trade_id = ?", [(i,) for i in ids])
        log(f"\n  validation build: {len(ids)} ledger trades from {args.start} removed and rebuilt from the export")
    cur.execute("create table if not exists extension_rows (asset_id integer primary key, trade_detail_id integer, "
                "export_trade_id integer, nhl_id integer, puckpedia_player_id integer, contract_cap_hit real, "
                "retained_cumulative real)")
    n_tr = n_as = n_multi = 0
    for gid, g in sorted(W.groupby("gid"), key=lambda kv: (kv[1]["date"].iloc[0], kv[0])):
        d = g["date"].iloc[0]
        clubs = sorted(set(g["from_team"]) | set(g["to_team"]))
        cur.execute("insert into trades (trade_date, season, n_teams, source, source_url, forum_thread_id) values (?,?,?,?,?,?)",
                    (d.strftime("%Y-%m-%d"), season_label(d), len(clubs), "puckpedia", None, None))
        tid = cur.lastrowid
        n_tr += 1
        n_multi += len(clubs) > 2
        leg = {}
        for i, c in enumerate(clubs, 1):
            cur.execute("insert into trade_legs (trade_id, acquiring_team, leg_order) values (?,?,?)", (tid, c, i))
            leg[c] = cur.lastrowid
        for r in g.itertuples():
            frm = r.from_team if len(clubs) > 2 else None
            if r.kind == "player":
                name = f"{r.first_name} {r.last_name}".strip()
                carried = r.cap_hit - r.retained_hit
                kept = r.kept_now
                pct = kept / (kept + carried) if kept > 0 and kept + carried > 0 else None
                rights = int(r.cap_hit == 0)
                txt = name + (f" (${kept:,.0f} retained - {100 * pct:.6g}%)" if kept > 0 else "") + \
                    f" · ${carried:,.0f}" + (" (AHL/JR)" if r.minor else "") + (" (Signing Rights)" if rights else "")
                cur.execute("insert into trade_assets (leg_id, trade_id, from_team, asset_type, player_name, cap_hit_aav, salary, "
                            "retention_pct, retained_aav, is_ahl_jr, is_signing_rights, is_conditional, raw_text) "
                            "values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (leg[r.to_team], tid, frm, "player", name, int(round(carried)), None, pct,
                             int(round(kept)) if kept > 0 else None, int(r.minor), rights, 0, txt))
            else:
                held = int(r.draft_year) <= LAST_DRAFT_HELD and pd.notna(r.overall_position)
                cond = int(pd.notna(r.draft_pick_conditions))
                txt = f"{int(r.draft_year)} {ORD[int(r.draft_round)]} round pick ({r.draft_pick_team}" + \
                    (f" - #{int(r.overall_position)}" if held else "") + ")" + (" [Conditional]*" if cond else "")
                cur.execute("insert into trade_assets (leg_id, trade_id, from_team, asset_type, pick_year, pick_round, "
                            "pick_original_team, pick_number, is_conditional, condition_marker, raw_text) values (?,?,?,?,?,?,?,?,?,?,?)",
                            (leg[r.to_team], tid, frm, "pick", int(r.draft_year), int(r.draft_round), r.draft_pick_team,
                             int(r.overall_position) if held else None, cond, "*" if cond else None, txt))
                if cond:
                    cur.execute("insert into trade_conditions (trade_id, marker, condition_text, result_text) values (?,?,?,?)",
                                (tid, "*", str(r.draft_pick_conditions), None))
            cur.execute("insert into extension_rows values (?,?,?,?,?,?,?)",
                        (cur.lastrowid if r.kind == "player" or not cond else
                         cur.execute("select max(asset_id) from trade_assets").fetchone()[0],
                         int(r.trade_detail_id), int(r.trade_id), None if pd.isna(r.nhl_id) else int(r.nhl_id),
                         None if pd.isna(r.player_id) else int(r.player_id), float(r.cap_hit), float(r.retained_hit)))
            n_as += 1
    con.commit()
    # ---- what was written ------------------------------------------------------------------------------------------------
    pl = W[W["kind"] == "player"]
    log(f"\n  WRITTEN to {out.name}: {n_tr} trades ({n_multi} of three or more clubs), {n_as} assets "
        f"({len(pl)} players, {(W['kind'] == 'pick').sum()} picks)")
    log(f"  by season: {W.groupby(W['date'].map(season_label))['gid'].nunique().to_dict()}")
    log(f"  5-6. retained salary: the export shows a retained amount on {int((pl['retained_hit'] > 0).sum())} player rows; kept in this "
        f"trade on {int((pl['kept_now'] > 0).sum())}; retained earlier and only carried on {int(((pl['retained_hit'] > 0) & (pl['kept_now'] == 0)).sum())}; "
        f"partly earlier {int(((pl['kept_now'] > 0) & (pl['prior_retained'] > 0)).sum())}")
    log(f"  7. minor-leaguers (no NHL game in the 365 days before the trade): {int(pl['minor'].sum())} of {len(pl)}; players with no NHL id "
        f"{int(pl['nhl_id'].isna().sum())}")
    log(f"  8. signing rights (cap hit $0): {int((pl['cap_hit'] == 0).sum())}")
    pk = W[W["kind"] == "pick"]
    log(f"  9. picks: conditional {int(pk['draft_pick_conditions'].notna().sum())}; for a draft after {LAST_DRAFT_HELD} (no selection number) "
        f"{int((pk['draft_year'] > LAST_DRAFT_HELD).sum())}; by draft year {pk.groupby(pk['draft_year'].astype(int)).size().to_dict()}")
    chk = pd.read_sql("select count(*) n, min(trade_date) a, max(trade_date) b from trades", con)
    log(f"  the ledger written: {int(chk['n'][0])} trades, {chk['a'][0]} to {chk['b'][0]}")
    z = pd.read_sql("select t.trade_id, t.n_teams, count(distinct l.acquiring_team) c from trades t join trade_legs l using(trade_id) "
                    "where t.source = 'puckpedia' group by 1", con)
    assert (z["n_teams"] == z["c"]).all() and (z["c"] >= 2).all()                   # GUARD: every trade has its clubs' legs
    con.close()
    (OUTPUT_DIR / (Path(args.out).stem + "_log.txt" if args.out != "trades_extended.db" else "trade_ledger_extend_log.txt")
     ).write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
