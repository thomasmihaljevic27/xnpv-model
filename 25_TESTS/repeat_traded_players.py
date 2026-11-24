"""
repeat_traded_players.py v1.0 (2026-11-23) - report only; writes nothing.

Karl's question at the findings meeting (2026-11-23): "how many players appear in multiple ... have been traded more than
once? Like, what proportion are we talking about here?" The realized value follows an asset whoever holds it later
(backtest.py's docstring), so a player traded on again carries his later seasons back to the first trade.

Sample: the 556 trades in Section 3's regression (findings_data.csv, in_main_regression == 1; 2017-07-01 to 2022-03-28).
Players are the ledger's player rows (rostered players, prospects and signing rights; picks and retained salary left out),
identified by the ledger's player_slug inside 10_SOURCE/trades.db. Later trades after 2022-03-28 come from
30_OUTPUT/trades_extended.db, whose PuckPedia rows carry no slug, so those are matched on the name with accents, full
stops and hyphens removed (a spelling that differs between the two sources is missed, so that figure is a floor).
Guard: the in-sample count is repeated from backtest_assets.csv by name and must give the same players and the same count.
"""
import os
import sqlite3
import sys
import unicodedata

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "20_CODE"))
OUT = os.path.join(ROOT, "30_OUTPUT")
SCRIPT_VERSION = "repeat_traded_players.py v1.0"
WINDOW_END = "2022-03-28"   # the declared window's last trade date

Q = ("select a.trade_id, a.player_name, a.player_slug, t.trade_date from trade_assets a "
     "join trades t using(trade_id) where a.asset_type = 'player'")


def norm(s):
    # name key for the post-2022 match: accents, full stops and hyphens removed, lower case
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower().replace(".", "").replace("-", " ").strip()


def main():
    print(SCRIPT_VERSION)
    reg = set(pd.read_csv(os.path.join(OUT, "stata", "findings_data.csv"))
              .query("in_main_regression == 1").trade_id)
    old = pd.read_sql(Q, sqlite3.connect(os.path.join(ROOT, "10_SOURCE", "trades.db")))
    ext = pd.read_sql(Q, sqlite3.connect(os.path.join(OUT, "trades_extended.db")))
    ext = ext[ext.trade_date > WINDOW_END].copy()
    ext["k"] = ext.player_name.map(norm)

    r = old[old.trade_id.isin(reg)].copy()
    r["k"] = r.player_name.map(norm)
    led = set(pd.read_sql("select trade_id from trades",
                          sqlite3.connect(os.path.join(ROOT, "10_SOURCE", "trades.db"))).trade_id)
    assert len(reg) == 556 and reg <= led, "the regression's trades are not all in the ledger"
    assert r.player_slug.notna().all()

    # In-sample: players in two or more of the 556 trades
    g = r.groupby("player_slug").trade_id.nunique()
    rep = set(g[g > 1].index)

    # Guard: the same count by name from the back-test's asset file
    a = pd.read_csv(os.path.join(OUT, "backtest_assets.csv"))
    a = a[(a.asset_type == "player") & a.trade_id.isin(reg)]
    ga = a.groupby("name").trade_id.nunique()
    ok = len(a) == len(r) and len(ga) == len(g) and (ga > 1).sum() == len(rep) \
        and sorted(ga.value_counts()) == sorted(g.value_counts())
    print(f"guard (asset file by name gives the same players and counts): {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit(1)

    n_tr = len(reg)
    print(f"trades {n_tr}; with a player {r.trade_id.nunique()}; player assets {len(r)}; players {len(g)}")
    print(f"players in 2+ of the 556 trades: {len(rep)} = {len(rep) / len(g):.1%} "
          f"(times: {dict(sorted(g[g > 1].value_counts().items()))})")
    ap = r.player_slug.isin(rep)
    print(f"player assets belonging to such a player: {ap.sum()} = {ap.mean():.1%}")
    t2 = r[ap].trade_id.nunique()
    print(f"trades with such a player: {t2} = {t2 / n_tr:.1%}")

    # Traded again after this trade, to the extended ledger's end
    in_win = [((old.player_slug == x.player_slug) & (old.trade_date > x.trade_date)).any() for x in r.itertuples()]
    after = [(ext.k == x.k).any() for x in r.itertuples()]
    r["in_win"], r["after"] = in_win, after
    r["later"] = r.in_win | r.after
    print(f"player assets whose player was traded again after it (to {ext.trade_date.max()}): "
          f"{r.later.sum()} = {r.later.mean():.1%} (by {WINDOW_END}: {r.in_win.sum()}; only after it: "
          f"{(r.later & ~r.in_win).sum()})")
    pl = r.groupby("player_slug").later.any()
    print(f"players traded again after one of these trades: {pl.sum()} = {pl.mean():.1%}")
    tl = r[r.later].trade_id.nunique()
    print(f"trades with at least one such asset: {tl} = {tl / n_tr:.1%}")


if __name__ == "__main__":
    main()
