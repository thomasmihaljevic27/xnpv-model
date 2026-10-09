"""
pick_star_and_rights_checks.py -- two checks on the adopted pick curve.

CHECK 1: BACON'S STAR RATES AGAINST OUR DATA (report only)
-------------------------------------------------------------------
The curve prices a pick on Bacon's star chance for its slot. His definition
(hockeystats.com/draft/guide, read 2026-10-09): a star has career WAR per 82
games of 1.8+ (forwards) or 1.23+ (defencemen); an NHLer has 200+ NHL games.
OUR READING, flagged: a star must also be an NHLer (200+ games), since a rate
over a handful of games is not a career. Career = every NHL season in Bacon's
WAR.csv from his draft year through 2025-26 (WAR per game needs no short-season
scaling). Skaters only (his star is a skater definition); position F unless the
draft record says D. Classes 2007-2015 are compared (careers of ten or more
seasons); 2016-2017 are shown apart (careers still running).
Compared by pick range: our share of stars against the mean of his star
chances over the same picks; the same for NHLers. NOT independent: his model is
fitted on largely the same drafts with the same WAR, so agreement mainly shows
that our data and reading match his.

CHECK 2: RIGHTS THAT LAPSE (report only)
-------------------------------------------------------------------
The curve credits a pick with a player's NHL surplus whichever club he played
for. A club that never signs its pick loses his rights, and he may sign or be
re-drafted elsewhere. For every drafted skater (2007-2017) who played an NHL
game, his first NHL season's team(s) (WAR.csv; franchise moves joined:
ATL=WPG, PHX=ARI=UTA) are compared with the drafting team:
  same team        first season includes the drafting franchise
  traded first     not the same, but he appears as a player asset in trades.db
                   between his draft and the end of his first NHL season (v1.1: v1.0
                   stopped at October 1 of that season and missed Filip Forsberg,
                   traded at the 2013 deadline and debuting after it); names match
                   on last name and first name with common short forms joined
                   (v1.1: "Tony DeAngelo" is "Anthony Deangelo" in trades.db)
  drafted twice    his NHL id is drafted in two classes; the EARLIER pick's rights
                   lapsed (the later pick is classified on its own)
  neither          most likely rights lapsed and he signed elsewhere; trades.db
                   ends 2022-03-28, so a later trade also lands here
Surplus from pick_regression_first_look.py v1.1 (skaters). Reported: counts,
share of the curve's surplus, the largest cases, and the pooled scale if
"drafted twice" (earlier pick) and "neither" were worth zero to the pick.

Run from the repo root:  python 25_TESTS/pick_star_and_rights_checks.py
"""

import os
import re
import sqlite3
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_star_and_rights_checks.py v1.1 (2026-10-09)"
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"linkage": OUT / "draft_pick_linkage.csv", "WAR": SRC / "WAR.csv", "players": OUT / "pick_first_look_players.csv",
     "fl_log": OUT / "pick_first_look_log.txt", "bacon": SRC / "draft_slot_baseline.csv", "trades": SRC / "trades.db"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
assert F["fl_log"].read_text(encoding="utf-8").startswith("pick_regression_first_look.py v1.1")

STAR = {"F": 1.8, "D": 1.23}           # career WAR per 82 games (Bacon's guide)
NHLER_GP = 200
FRANCHISE = {"N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "L.A": "LAK", "ATL": "WPG", "PHX": "ARI", "UTA": "ARI"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


SHORT_FORMS = {"tony": "anthony", "josh": "joshua", "mike": "michael", "alex": "alexander", "matt": "matthew",
               "nick": "nicholas", "will": "william", "zach": "zachary", "jake": "jacob", "dan": "daniel",
               "danny": "daniel", "chris": "christopher", "sam": "samuel", "ben": "benjamin", "tom": "thomas",
               "jon": "jonathan", "joe": "joseph", "andy": "andrew", "nate": "nathan", "max": "maxim",
               "steve": "steven", "rob": "robert", "bobby": "robert", "jt": "jt", "tj": "tj"}


def name_key(s):
    """(last name, first name with short forms joined), on the normalised name."""
    parts = norm(s).split()
    if len(parts) < 2:
        return (norm(s), "")
    return (parts[-1], SHORT_FORMS.get(parts[0], parts[0]))


def fr(code):
    return FRANCHISE.get(code, code)


bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")
link = pd.read_csv(F["linkage"])
sk = link[link["draftYear"].between(2007, 2017) & ~link["is_goalie"].astype(bool)
          & (link["link_status"] != "excluded_merged_name") & (link["playerName"] != "FORFEIT")].copy()
sk["pos"] = np.where(sk["position"] == "D", "D", "F")

war = pd.read_csv(F["WAR"], usecols=["Player", "Season", "Team", "GP", "WAR"])
war["name_n"] = war["Player"].map(norm)
war["start"] = war["Season"].map(lambda s: 2000 + int(str(s)[:2]))


def career(row):
    if pd.isna(row["war_names"]):
        return None
    names = {norm(x) for x in str(row["war_names"]).split("|")}
    c = war[war["name_n"].isin(names) & (war["start"] >= row["draftYear"])]
    return c if len(c) else None


rec = []
for r in sk.itertuples():
    c = career(r._asdict())
    gp = c["GP"].sum() if c is not None else 0
    w82 = c["WAR"].sum() / gp * 82 if gp else np.nan
    first_teams, first_start = set(), None
    if c is not None and (c["GP"] > 0).any():
        first_start = int(c.loc[c["GP"] > 0, "start"].min())
        for t in c.loc[c["start"] == first_start, "Team"].astype(str):
            first_teams |= {fr(x) for x in t.split("/")}
    rec.append({"draftYear": r.draftYear, "pick": r.overallPickNumber, "player": r.playerName, "playerId": r.playerId,
                "pos": r.pos, "team": fr(r.triCode), "gp": gp, "war82": w82,
                "nhler": gp >= NHLER_GP, "star": gp >= NHLER_GP and w82 >= STAR[r.pos],
                "first_start": first_start, "first_teams": "/".join(sorted(first_teams))})
c = pd.DataFrame(rec)
c["p_star"] = c["pick"].map(bacon["p_star"])
c["p_nhler"] = c["pick"].map(bacon["p_nhler"])

# ---- check 1 ------------------------------------------------------------------------------------
log("\nCHECK 1: STAR AND NHLER RATES, OURS AGAINST BACON'S (skaters)")
bands = [(1, 1), (2, 3), (4, 10), (11, 20), (21, 32), (33, 64), (65, 128), (129, 217)]
for lab, lo, hi in (("classes 2007-2015", 2007, 2015), ("classes 2016-2017 (careers running)", 2016, 2017)):
    e = c[c["draftYear"].between(lo, hi)]
    rows = []
    for blo, bhi in bands:
        s = e[e["pick"].between(blo, bhi)]
        k = int(s["star"].sum())
        se = np.sqrt(max(s["star"].mean() * (1 - s["star"].mean()), 1e-9) / len(s))
        rows.append({"picks": f"{blo}-{bhi}", "n": len(s), "stars": k, "our star %": 100 * s["star"].mean(),
                     "+/- 2se": 200 * se, "Bacon star %": 100 * s["p_star"].mean(),
                     "our NHLer %": 100 * s["nhler"].mean(), "Bacon NHLer %": 100 * s["p_nhler"].mean()})
    log(f"  {lab}: {len(e):,} picks, {int(e['star'].sum())} stars ({100 * e['star'].mean():.1f}%; Bacon "
        f"{100 * e['p_star'].mean():.1f}%), NHLers {100 * e['nhler'].mean():.1f}% (Bacon {100 * e['p_nhler'].mean():.1f}%)")
    log(pd.DataFrame(rows).round(1).to_string(index=False))

# ---- check 2 ------------------------------------------------------------------------------------
fl = pd.read_csv(F["players"])[["draftYear", "pick", "surplus"]]
c = c.merge(fl, on=["draftYear", "pick"], how="left", validate="one_to_one")
con = sqlite3.connect(F["trades"])
ta = pd.read_sql("select a.player_name, t.trade_date from trade_assets a join trades t using(trade_id) "
                 "where a.asset_type = 'player'", con)
ta["key"], ta["date"] = ta["player_name"].map(name_key), pd.to_datetime(ta["trade_date"])
twice = link.dropna(subset=["playerId"]).groupby("playerId")["draftYear"].agg(["nunique", "max"])
twice = twice[twice["nunique"] > 1]

played = c[c["first_start"].notna()].copy()


def classify(r):
    if r["team"] in r["first_teams"].split("/"):
        return "same team"
    if pd.notna(r["playerId"]) and r["playerId"] in twice.index and r["draftYear"] < twice.loc[r["playerId"], "max"]:
        return "drafted twice (earlier pick)"
    after_draft, first_ends = pd.Timestamp(int(r["draftYear"]), 6, 1), pd.Timestamp(int(r["first_start"]) + 1, 7, 1)
    if ((ta["key"] == name_key(r["player"])) & (ta["date"] > after_draft) & (ta["date"] < first_ends)).any():
        return "traded first"
    return "neither"


played["route"] = played.apply(classify, axis=1)
tot = c["surplus"].sum()
log(f"\nCHECK 2: WHO COLLECTED THE PICK'S VALUE ({len(played):,} drafted skaters who played; "
    f"total surplus ${tot / 1e6:,.1f}M)")
g = played.groupby("route").agg(players=("player", "size"), surplus_M=("surplus", lambda s: s.sum() / 1e6))
g["share of total %"] = 100 * g["surplus_M"] / (tot / 1e6)
log(g.round(1).to_string())
nei = played[played["route"].isin(["neither", "drafted twice (earlier pick)"])].nlargest(12, "surplus")
log("\nlargest surpluses not collected through the drafting club or a trade:")
log(nei.assign(surplus=nei["surplus"] / 1e6)[["draftYear", "pick", "player", "team", "first_start", "first_teams",
                                              "route", "surplus"]].round(2).to_string(index=False))

# the pooled scale if those picks were worth zero to their drafting club
lost = played.loc[played["route"].isin(["neither", "drafted twice (earlier pick)"]), ["draftYear", "pick"]]
c["surplus_kept"] = c["surplus"]
c.loc[c.set_index(["draftYear", "pick"]).index.isin(lost.set_index(["draftYear", "pick"]).index), "surplus_kept"] = 0.0
CL = sorted(c["draftYear"].unique())


def scale(y):
    yrs = c["draftYear"].values
    X = [c["p_star"].values] + [(yrs == k).astype(float) - (yrs == CL[-1]).astype(float) for k in CL[:-1]]
    b, *_ = np.linalg.lstsq(np.column_stack(X), y, rcond=None)
    return b[0]


b0, b1 = scale(c["surplus"].values / 1e6), scale(c["surplus_kept"].values / 1e6)
log(f"\npooled scale: as adopted {b0:.2f}; with lapsed or unexplained routes at zero {b1:.2f} ({100 * (b1 / b0 - 1):+.1f}%)")

c.to_csv(OUT / "pick_star_and_rights_checks.csv", index=False)
(OUT / "pick_star_and_rights_checks_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote pick_star_and_rights_checks.csv and its log in {OUT}")
