"""
traded_pick_values.py -- what each traded draft pick was worth when it was traded.

SPECIFICATION: 00_STATE/MODEL_DIRECTIVES.md directive 6 (decided 2026-10-09).
  value = SCALE for the trade season x Bacon's star chance for the pick's slot,
  with the slot known as follows:
  * THE NEXT DRAFT'S PICK, traded during or after that draft's regular season
    (at least one regular-season game played before the trade date): the slot
    the original team's place in the standings on the trade date gives
    [meeting 2026-10-09: "assume whatever position that draft pick was the
    moment we agreed to the trade"]. Standings by points percentage (two points
    a win, one for an overtime or shootout loss; ties by more wins, then team
    code), worst first; slot = (round - 1) x teams in that draft + place.
    NOT MODELLED: the lottery, playoff results reordering playoff teams,
    compensatory or forfeited picks. Once the regular season is over, the
    standings on the trade date are the final standings.
  * THE NEXT DRAFT'S PICK traded before that season's first game, and ANY LATER
    DRAFT'S PICK: the average star chance over the round's slots for that
    draft's number of teams [meeting 2026-10-09: "take the average value of a
    draft pick in that round"].
  * A PICK TRADED DURING ITS OWN DRAFT (between the draft's first and last day):
    its actual slot, which is known on the draft floor (v1.1; v1.0 treated a draft
    as over once its first day had passed and left 155 such picks unvalued).
  "The next draft" is the first draft whose last day is on or after the trade date (draft
  dates from the cached NHL draft records: the 2020 draft was in October and the
  2021 draft in late July, so picks for them were still being traded after July 1).
  * SCALE: the KNOWABLE scale for the trade season (pick_curve.py: classes drafted
    nine or more seasons earlier), with the POOLED scale beside it as the
    sensitivity. Trade season = the season starting July 1 on or before the trade.
  * CONDITIONAL picks (trades.db is_conditional) are valued as if unconditional
    and flagged; resolving them (met or not) is a separate, owed step.

INPUTS: OUTPUT_DIR/pick_curve_scales.csv (pick_curve.py), SOURCE_DIR/trades.db,
SOURCE_DIR/games.csv (regular-season results, 2017-18 on), SOURCE_DIR/
draft_slot_baseline.csv, OUTPUT_DIR/draft_raw/draft_YYYY.json (draft dates and
teams per round, cached by draft_pick_linkage.py).
OUTPUTS: OUTPUT_DIR/traded_pick_values.csv, OUTPUT_DIR/traded_pick_values_log.txt.

Run from the repo root:  python 20_CODE/traded_pick_values.py
"""

import json
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "traded_pick_values.py v1.1 (2026-10-09)"
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"scales": OUTPUT_DIR / "pick_curve_scales.csv", "trades": SOURCE_DIR / "trades.db",
     "games": SOURCE_DIR / "games.csv", "bacon": SOURCE_DIR / "draft_slot_baseline.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
curve_log = (OUTPUT_DIR / "pick_curve_log.txt").read_text(encoding="utf-8").splitlines()[0]
log(f"  scales from: {curve_log}")

# ---- drafts: first day and teams per round, from the cached NHL draft records -------------------
DRAFT_DAY, DRAFT_END, TEAMS = {}, {}, {}
for f in sorted((OUTPUT_DIR / "draft_raw").glob("draft_*.json")):
    rows = json.loads(f.read_text(encoding="utf-8"))["data"]
    y = int(f.stem.split("_")[1])
    DRAFT_DAY[y] = pd.Timestamp(min(r["draftDate"] for r in rows))
    DRAFT_END[y] = pd.Timestamp(max(r["draftDate"] for r in rows))
    TEAMS[y] = sum(1 for r in rows if r["roundNumber"] == 1)
LAST_KNOWN = max(DRAFT_DAY)


def draft_day(y):
    return DRAFT_DAY.get(y, pd.Timestamp(y, 6, 26))   # drafts beyond the cache: late June (only for ordering)


def draft_end(y):
    return DRAFT_END.get(y, pd.Timestamp(y, 6, 27))


def teams(y):
    return TEAMS.get(y, TEAMS[LAST_KNOWN])           # 32 from 2021


bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]


def round_average(y, rnd):
    n = teams(y)
    slots = range((rnd - 1) * n + 1, rnd * n + 1)
    return float(np.mean([bacon[s] for s in slots if s in bacon.index]))


# ---- standings on a date ------------------------------------------------------------------------
games = pd.read_csv(F["games"])
games = games[games["game_type"] == 2].copy()
games["date"] = pd.to_datetime(games["game_date"])


def standings(season_label, on):
    """Teams of one regular season ranked worst first by points percentage, from games before `on`."""
    g = games[(games["season"] == season_label) & (games["date"] < on)]
    if g.empty:
        return None
    rec = {}
    for r in g.itertuples():
        home_won = r.home_score > r.away_score
        for team, won in ((r.home_team, home_won), (r.away_team, not home_won)):
            w, l, otl = rec.get(team, (0, 0, 0))
            if won:
                w += 1
            elif r.last_period in ("OT", "SO"):
                otl += 1
            else:
                l += 1
            rec[team] = (w, l, otl)
    t = pd.DataFrame([(k, *v) for k, v in rec.items()], columns=["team", "w", "l", "otl"])
    t["gp"] = t["w"] + t["l"] + t["otl"]
    t["pts_pct"] = (2 * t["w"] + t["otl"]) / (2 * t["gp"])
    t = t.sort_values(["pts_pct", "w", "team"], ascending=[True, True, True]).reset_index(drop=True)
    t["place"] = t.index + 1
    return t.set_index("team")


# ---- the traded picks -------------------------------------------------------------------------------
scales = pd.read_csv(F["scales"])
pooled = float(scales.loc[scales["scale_kind"] == "pooled", "scale_M"].iloc[0])
knowable = scales[scales["scale_kind"] == "knowable"].set_index("trade_season")["scale_M"].to_dict()
con = sqlite3.connect(F["trades"])
p = pd.read_sql("select a.asset_id, a.trade_id, a.pick_year, a.pick_round, a.pick_original_team, a.pick_number, "
                "a.is_conditional, a.raw_text, t.trade_date from trade_assets a join trades t using(trade_id) "
                "where a.asset_type = 'pick'", con)
p["date"] = pd.to_datetime(p["trade_date"])
p["trade_season"] = np.where(p["date"].dt.month >= 7, p["date"].dt.year, p["date"].dt.year - 1)
p = p[p["trade_season"].isin(knowable)].copy()
log(f"\npicks traded in trade seasons {int(min(knowable))}-{int(max(knowable))} present in trades.db: {len(p)} "
    f"(trades.db ends {pd.read_sql('select max(trade_date) m from trades', con)['m'][0]})")

cache = {}
out = []
for r in p.itertuples():
    day = r.date.normalize()
    nxt = min(y for y in list(DRAFT_DAY) + [LAST_KNOWN + k for k in range(1, 6)] if draft_end(y) >= day)
    y, rnd = int(r.pick_year), int(r.pick_round)
    method, slot, place, star = None, None, None, None
    if y < nxt:
        method = "draft already held"                 # the pick was used before the trade; not valued
    elif y == nxt and draft_day(y) <= day and pd.notna(r.pick_number):
        slot = int(r.pick_number)
        star = float(bacon[slot])
        method = "actual slot (traded during the draft)"
    elif y == nxt:
        key = (int(f"{y - 1}{y}"), day)                 # games.csv stores the season as 20172018
        if key not in cache:
            cache[key] = standings(*key)
        st = cache[key]
        if st is None:
            method = "round average (before the season's first game)"
        elif r.pick_original_team not in st.index:
            method = "round average (original team not in the standings)"
        else:
            place = int(st.loc[r.pick_original_team, "place"])
            slot = (rnd - 1) * teams(y) + place
            star = float(bacon[slot])
            method = "slot on the trade date"
    else:
        method = "round average (a later draft)"
    if method.startswith("round average"):
        star = round_average(y, rnd)
    out.append({"asset_id": r.asset_id, "trade_id": r.trade_id, "trade_date": r.trade_date,
                "trade_season": r.trade_season, "pick_year": y, "pick_round": rnd,
                "original_team": r.pick_original_team, "conditional": bool(r.is_conditional),
                "method": method, "standings_place": place, "projected_slot": slot,
                "actual_slot": r.pick_number, "star_chance": star,
                "value_knowable_M": None if star is None else knowable[r.trade_season] * star,
                "value_pooled_M": None if star is None else pooled * star})
v = pd.DataFrame(out)

log("\nHOW EACH PICK WAS VALUED")
g = v.groupby("method").agg(picks=("asset_id", "size"), knowable_M=("value_knowable_M", "sum"),
                            pooled_M=("value_pooled_M", "sum"))
log(g.round(1).to_string())
vv = v[v["value_knowable_M"].notna()]
log(f"  total: knowable ${vv['value_knowable_M'].sum():,.1f}M, pooled ${vv['value_pooled_M'].sum():,.1f}M "
    f"({100 * (vv['value_knowable_M'].sum() / vv['value_pooled_M'].sum() - 1):+.1f}%); conditional picks among them: "
    f"{int(vv['conditional'].sum())}")
log("\nBY ROUND (mean $M a pick, knowable scale)")
log(vv.groupby("pick_round")["value_knowable_M"].agg(["size", "mean", "min", "max"]).round(2).to_string())

slot = v[v["method"] == "slot on the trade date"]
if len(slot):
    gap = (slot["projected_slot"] - slot["actual_slot"]).abs()
    log(f"\nPROJECTED AGAINST ACTUAL SLOT ({len(slot)} picks valued on the trade-date standings): "
        f"median miss {gap.median():.0f} slots, mean {gap.mean():.1f}; within 3 slots: {int((gap <= 3).sum())}")
    first = slot[slot["pick_round"] == 1]
    if len(first):
        fg = (first["projected_slot"] - first["actual_slot"]).abs()
        log(f"  first-round picks ({len(first)}): median miss {fg.median():.0f}, largest {fg.max():.0f}")

v.to_csv(OUTPUT_DIR / "traded_pick_values.csv", index=False)
(OUTPUT_DIR / "traded_pick_values_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote traded_pick_values.csv and its log in {OUTPUT_DIR}")
