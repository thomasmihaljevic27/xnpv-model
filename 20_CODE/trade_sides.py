"""
trade_sides.py -- the three models put together: each club's side of each trade, at the 2025-26 cap.

WHY (Thomas, 2026-10-20: "put together the three models and do the back-test"). trade_asset_values.csv gives every
traded asset one value (player model, pick curve or prospect model) at the 2025-26 cap. The back-test compares clubs,
not assets, so this script adds each trade up club by club: what each club received, what it gave up, and the
difference, which is the model's ex-ante verdict on the trade for that club. Nothing here reads a season after the
trade: every value is the one the models give at the trade (trade_asset_values' own information rules).

HOW A CLUB'S SIDE IS ADDED UP (follows the decided rules; no new choice)
  received  = the value of every asset it acquired, at what the acquirer holds (a player net of any retained salary,
              Thomas 2026-10-19), plus any retained-salary entry it carries (that entry is charged to the club that
              retained, trade_asset_values v1.1);
  given up  = the value of every asset it sent, at what it was worth to the club holding it before the trade: the
              acquirer's value plus the retained part, because before the trade the sender paid the whole cap hit;
  net       = received - given up.
  Read with the retained-salary rule, the trade is zero-sum among its clubs: the sender gives up the player at his full
  cap hit and keeps the retained part, so the retention moves value from the retaining club to the acquirer once, not
  twice. (Adding each club's "received" alone and subtracting the other club's would count it twice: the acquirer's
  value is raised by it and the retaining club's lowered.) GUARD: the nets of each trade's clubs sum to zero.
  Who sent an asset: trades.db's from_team in a three-team trade (every asset there carries one); in a two-team trade,
  the other club.
  The season under way: each player's value already counts only the share of the season left after an in-season trade
  (Thomas 2026-10-19), on both sides alike; prospects keep the full season, picks have none.

WHAT IS LEFT OPEN, AND HOW IT IS CARRIED (each is listed in the log, not decided here)
  - 3 assets have no value (Sislo, McKegg, Chapie): their trades are flagged complete = False.
  - Conditional picks are valued as unconditional (traded_pick_values): flagged by has_conditional_pick.
  - An extension signed on the day of a trade (Pacioretty 2018-09-10) is inside the player's value (WORK_QUEUE, open).

INPUTS:  OUTPUT_DIR/trade_asset_values.csv (trade_asset_values.py), SOURCE_DIR/trades.db (legs and conditions).
OUTPUTS: OUTPUT_DIR/trade_sides.csv (one row per club per trade), trade_sides_log.txt.
Run from the repo root, after trade_asset_values.py:  python 20_CODE/trade_sides.py
"""

import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "trade_sides.py v1.0 (2026-10-20)"
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
MONEY = 6                                            # $M rounded to the dollar before the zero-sum guard
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def asset_class(source):
    """The three models, by the file that valued the asset (trade_asset_values' source column)."""
    if source.startswith("pick curve"):
        return "picks"
    if source.startswith("prospect model"):
        return "prospects"
    if source.startswith("retained salary"):
        return "retained"
    return "players"                                 # player model (incl. rights, 2017 page) and buried contracts


def trade_clubs():
    """{trade_id: sorted clubs} from trades.db's legs, and {asset_id: is_conditional}."""
    con = sqlite3.connect(SOURCE_DIR / "trades.db")
    legs = pd.read_sql("select trade_id, acquiring_team from trade_legs", con)
    clubs = legs.groupby("trade_id")["acquiring_team"].apply(lambda s: sorted(set(s))).to_dict()
    cond = pd.read_sql("select asset_id, is_conditional from trade_assets", con).set_index("asset_id")["is_conditional"]
    return clubs, cond


def club_sides(v, col, clubs, cond):
    """Each club's side of each trade from asset values in column `col` ($M; blank counts zero), by the rule in the
    docstring. backtest.py calls it with the outcome in place of the forecast, so both are added up one way."""
    v = v.copy()
    v["cls"] = v["source"].map(asset_class)
    v["val"] = v[col].fillna(0.0)
    moved = v[v["asset_type"] != "retained salary"].copy()
    ret = v[v["asset_type"] == "retained salary"].set_index("asset_id")["val"]
    assert ret.index.is_unique                                                # GUARD: one retained entry per player
    # what the sender held before the trade: the acquirer's value plus the retained part (a cost, so subtracted)
    moved["val_to_sender"] = moved["val"] + moved["asset_id"].map(ret).fillna(0.0)

    def sender(r):
        if pd.notna(r.from_team):
            return r.from_team
        others = [c for c in clubs[r.trade_id] if c != r.acquiring_team]
        assert len(others) == 1, (r.trade_id, r.name, others)                 # GUARD: a two-team trade's other club
        return others[0]
    moved["sender"] = [sender(r) for r in moved.itertuples()]
    moved["conditional"] = moved["asset_id"].map(cond).fillna(0).astype(int).where(moved["asset_type"] == "pick", 0)

    rows = []
    for tid, g in v.groupby("trade_id"):
        m = moved[moved["trade_id"] == tid]
        for c in clubs[tid]:
            got = g[g["acquiring_team"] == c]
            gave = m[m["sender"] == c]
            rec = {"trade_id": tid, "trade_date": g["trade_date"].iloc[0], "valuation_page": int(g["valuation_page"].iloc[0]),
                   "club": c, "n_clubs": len(clubs[tid]),
                   "during_regular_season": bool(g["during_regular_season"].any()),
                   "complete": bool((g["source"] != "not valued").all()),
                   "has_conditional_pick": bool(m["conditional"].any()),
                   "n_received": int((got["asset_type"] != "retained salary").sum()), "n_given": len(gave)}
            for k in ("players", "picks", "prospects", "retained"):
                rec[f"recv_{k}_M"] = got.loc[got["cls"] == k, "val"].sum()
            for k in ("players", "picks", "prospects"):
                rec[f"gave_{k}_M"] = gave.loc[gave["cls"] == k, "val_to_sender"].sum()
            rec["received_M"] = sum(rec[f"recv_{k}_M"] for k in ("players", "picks", "prospects", "retained"))
            rec["given_M"] = sum(rec[f"gave_{k}_M"] for k in ("players", "picks", "prospects"))
            rec["net_M"] = rec["received_M"] - rec["given_M"]
            rows.append(rec)
    s = pd.DataFrame(rows)
    z = s.groupby("trade_id")["net_M"].sum().round(MONEY)
    assert (z == 0).all(), z[z != 0].head()                                  # GUARD: each trade is zero-sum
    assert len(moved) == int(s["n_given"].sum()) == int(s["n_received"].sum())   # GUARD: every asset sent and received once
    assert abs(s["received_M"].sum() - v["val"].sum()) < 1e-6                # GUARD: received adds to the table's total
    return s


def main():
    sys.stdout.reconfigure(errors="replace")          # names with accents on a Windows console
    log(SCRIPT_VERSION)
    p = OUTPUT_DIR / "trade_asset_values.csv"
    first = (OUTPUT_DIR / "trade_asset_values_log.txt").read_text(encoding="utf-8").splitlines()[0]
    log(f"  input: {p.name} (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M} UTC; {first})")
    v = pd.read_csv(p)                                # the 3 unvalued assets count zero; their trades are flagged
    clubs, cond = trade_clubs()
    s = club_sides(v, "value_2025_cap_M", clubs, cond)

    # ---- report ----------------------------------------------------------------------------------------------------------
    n_tr = s["trade_id"].nunique()
    log(f"\nTRADES {s['trade_date'].min()} to {s['trade_date'].max()}: {n_tr} ({(s.groupby('trade_id')['n_clubs'].first() == 3).sum()} "
        f"three-team), {len(s)} club sides; every trade zero-sum to the dollar")
    log(f"  complete (every asset valued): {s.groupby('trade_id')['complete'].first().sum()} of {n_tr}; "
        f"with a conditional pick valued as unconditional: {s.groupby('trade_id')['has_conditional_pick'].first().sum()}; "
        f"one club received nothing recorded: {(s['n_received'] == 0).sum()}")
    log(f"  value moved (sum over sides of what was received, before retained salary): "
        f"${s[['recv_players_M', 'recv_picks_M', 'recv_prospects_M']].sum().sum():,.2f}M "
        f"(players ${s['recv_players_M'].sum():,.2f}M, picks ${s['recv_picks_M'].sum():,.2f}M, "
        f"prospects ${s['recv_prospects_M'].sum():,.2f}M); retained salary carried ${s['recv_retained_M'].sum():,.2f}M")
    a = s["net_M"].abs()
    log(f"\nTHE MODEL'S VERDICT, PER CLUB SIDE ($M at the 2025-26 cap; one side of each two-team trade is the other's "
        f"negative, so the sides' mean is zero by construction)")
    log(f"  size of the verdict |net|: median {a.median():.2f}, mean {a.mean():.2f}, 90th percentile {a.quantile(.9):.2f}, "
        f"largest {a.max():.2f}")
    top = s.loc[s.groupby("trade_id")["net_M"].idxmax()].sort_values("net_M", ascending=False).head(10)
    names = v.groupby(["trade_id", "acquiring_team"])["name"].apply(lambda x: "; ".join(n for n in x if not n.startswith("retained:")))
    log("  the ten trades with the largest gap (the club the model favours, then what each club received):")
    for r in top.itertuples():
        other = [c for c in clubs[r.trade_id] if c != r.club]
        log(f"    {r.trade_date} {r.club} +{r.net_M:.2f}  {r.club} got: {names.get((r.trade_id, r.club), '-')[:70]}")
        for c in other:
            log(f"{'':22}{c} got: {names.get((r.trade_id, c), '-')[:70]}")
    s.to_csv(OUTPUT_DIR / "trade_sides.csv", index=False)
    (OUTPUT_DIR / "trade_sides_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote trade_sides.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
