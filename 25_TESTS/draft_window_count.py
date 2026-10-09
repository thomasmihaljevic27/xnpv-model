"""
draft_window_count.py -- how many drafted players' windows run past 2025-26?

WHAT THIS ANSWERS (MODEL_DIRECTIVES.md directive 6, 2026-10-09)
-------------------------------------------------------------------
A pick is valued over each drafted player's seasons from the draft to the end
of the qualifying-offer chain, i.e. until he becomes an unrestricted free
agent. The data ends with 2025-26. A player whose control runs past 2025-26
has seasons the club still controls that we cannot see yet. Thomas decides,
once these are counted, whether to drop such classes or cut the window at
2025-26. This script counts; it prices nothing and changes no model file.

THE RULE, FROM THE CBA (2013 CBA as published at media.nhl.com/.../CBA.pdf;
read 2026-10-09)
-------------------------------------------------------------------
* Section 10.1(a)(i), Group 3: a player with SEVEN Accrued Seasons, or who is
  27 OR OLDER AS OF JUNE 30 at the end of a League Year, becomes a UFA when
  his contract has expired. Under the qualifying-offer chain every contract
  after the entry-level deal is one year, so it expires each June 30.
* Article 1, "Accrued Season": a League Year in which the player was on a
  club's ACTIVE ROSTER for 40 or more regular-season games (30 for a goalie);
  games missed injured while on the active roster count (that year and at
  most one more). No age condition.
* Exhibit table, item 9: for 2012-13 (48 games) the 40/30 thresholds are
  pro-rated 48/82.
* Section 10.1(c)(i), Group 6: a player aged 25 or older with three or more
  professional seasons, whose contract has expired, with fewer than 80 NHL
  games (goalie: fewer than 28 NHL games of 30+ minutes), is a UFA.

APPROXIMATIONS (each one is ours, not the CBA's)
-------------------------------------------------------------------
1. ACTIVE-ROSTER GAMES ARE NOT IN THE DATA; NHL GAMES PLAYED STAND IN.
   Healthy scratches and injured games on the roster count toward an
   Accrued Season but not toward games played, so this UNDER-counts Accrued
   Seasons (worst for backup goalies, who sit on the roster most nights).
   Effect: some players reach seven Accrued Seasons earlier than counted
   here, so a few windows counted as running past 2025-26 may in fact end
   inside it. The PuckPedia check below measures the gap.
2. 2019-20 AND 2020-21 THRESHOLDS: the 2020 MOU's text was not read. The
   thresholds are pro-rated by schedule as the CBA did for 2012-13:
   70/82 for 2019-20 (the project's D20 factor) and 56/82 for 2020-21.
   ASSUMPTION, flagged.
3. GROUP 6 is reported as a BOUND, not built: professional seasons (minor
   league and Europe under an NHL contract) are not observed, so the
   "with Group 6" column assumes every player had three professional seasons
   by 25. It shows the most Group 6 could shorten windows.
4. The entry-level deal is assumed to have expired by the Group 3 date (true
   unless a player signed very late); not modelled.

DATA AND JOINS
-------------------------------------------------------------------
* Picks: OUTPUT_DIR/draft_pick_linkage.csv (draft_pick_linkage.py), classes
  2007-2017, birthdates from the NHL draft records.
* NHL games: Bacon's SOURCE_DIR/WAR.csv (skaters) and Goalies_WAR.csv
  (goalies), joined on the linkage's `war_names` (pipe-separated spellings,
  normalised as the linkage normalises them). GUARD: only seasons starting
  in or after the draft year count (a namesake's earlier career cannot
  leak in). Rows for one player-season split by team are SUMMED.
* PuckPedia check: OUTPUT_DIR/contract_level_spine.csv `ufa_year` (the
  start year of the first UFA season = the end year of the last controlled
  season, the convention used here), joined on the NHL id. Confidential
  vendor data: read locally, nothing written from it.

SEASON LABELS: a season is named by the year it ENDS (2025-26 -> 2026),
because both CBA dates are June 30.

Run from the repo root:  python 25_TESTS/draft_window_count.py
"""

import os
import re
import sys
import unicodedata

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "draft_window_count.py v1.0 (2026-10-09)"
print(SCRIPT_VERSION)

load_dotenv()
SOURCE_DIR = os.environ["SOURCE_DIR"]
OUTPUT_DIR = os.environ["OUTPUT_DIR"]
LINK_PATH = os.path.join(OUTPUT_DIR, "draft_pick_linkage.csv")
WAR_PATH = os.path.join(SOURCE_DIR, "WAR.csv")
GW_PATH = os.path.join(SOURCE_DIR, "Goalies_WAR.csv")
SPINE_PATH = os.path.join(OUTPUT_DIR, "contract_level_spine.csv")
OUT_PATH = os.path.join(OUTPUT_DIR, "draft_window_count.csv")
for p in (LINK_PATH, WAR_PATH, GW_PATH, SPINE_PATH):
    print(f"  input: {os.path.abspath(p)}  (modified {pd.Timestamp(os.path.getmtime(p), unit='s'):%Y-%m-%d %H:%M})")

CLASSES = range(2007, 2018)   # 2007-2017 draft classes (read in the 2026-10-09 meeting)
LAST_SEEN = 2026              # 2025-26 is the last season in the data (end-year label)

# Accrued Season thresholds (Article 1): 40 skater / 30 goalie games.
BASE = {False: 40, True: 30}
# Pro-ration by end-year. 2013: CBA exhibit item 9 (48/82). 2020, 2021: ASSUMPTION 2.
PRORATE = {2013: 48 / 82, 2020: 70 / 82, 2021: 56 / 82}
G6_GAMES = {False: 80, True: 28}   # Group 6 NHL-games ceiling (goalie: 30+ minute games; GP stands in)


def norm(s):
    """Same normalisation as draft_pick_linkage.norm: strip accents, lowercase, letters and spaces."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def end_year(season):
    """'07-08' -> 2008 (the season's June 30 year)."""
    y = int(str(season).split("-")[0])
    return (y if y > 1900 else 2000 + y) + 1


def year_reaching(birth, age):
    """End-year of the first League Year at whose June 30 the player is `age` or older."""
    return birth.year + age + (1 if (birth.month, birth.day) > (6, 30) else 0)


# ---- picks ---------------------------------------------------------------
link = pd.read_csv(LINK_PATH, parse_dates=["birthDate"])
picks = link[link["draftYear"].isin(CLASSES)].copy()
picks["is_goalie"] = picks["is_goalie"].astype(bool)
print(f"\npicks in classes 2007-2017: {len(picks):,}  (goalies {picks['is_goalie'].sum()})")

# ---- NHL games per player-season, summed over team rows -----------------
war = pd.read_csv(WAR_PATH, usecols=["Player", "Season", "GP"]).rename(columns={"Player": "name"})
gw = pd.read_csv(GW_PATH, usecols=["Goalie", "Season", "GP"]).rename(columns={"Goalie": "name"})
games = {}
for is_g, df in ((False, war), (True, gw)):
    df = df.assign(name_n=df["name"].map(norm), ey=df["Season"].map(end_year))
    games[is_g] = df.groupby(["name_n", "ey"])["GP"].sum()


def player_seasons(row):
    """NHL games by end-year for one pick, all listed spellings, seasons from his draft on."""
    if pd.isna(row["war_names"]):
        return pd.Series(dtype=float)
    tbl = games[row["is_goalie"]]
    parts = []
    for nm in str(row["war_names"]).split("|"):
        n = norm(nm)
        if n in tbl.index.get_level_values(0):
            parts.append(tbl.loc[n])
    if not parts:
        return pd.Series(dtype=float)
    s = pd.concat(parts).groupby(level=0).sum()
    return s[s.index >= row["draftYear"] + 1]   # GUARD: first possible season ends draftYear+1


rows = []
for _, r in picks.iterrows():
    gp = player_seasons(r)
    thr = {y: BASE[r["is_goalie"]] * PRORATE.get(y, 1.0) for y in gp.index}
    accrued = sorted(y for y, g in gp.items() if g >= thr[y])
    a7 = accrued[6] if len(accrued) >= 7 else None          # end-year of his 7th Accrued Season
    b = r["birthDate"]
    y27 = year_reaching(b, 27) if pd.notna(b) else None
    y25 = year_reaching(b, 25) if pd.notna(b) else None
    # Group 3: the earlier of the age-27 date and the 7th Accrued Season.
    g3 = min(x for x in (y27, a7) if x is not None) if (y27 or a7) else None
    # Group 6 bound: at 25 if under the games ceiling by then (three pro seasons assumed).
    g6 = None
    if y25 is not None and y25 <= LAST_SEEN:
        if gp[gp.index <= y25].sum() < G6_GAMES[r["is_goalie"]]:
            g6 = y25
    with6 = min(x for x in (g3, g6) if x is not None) if (g3 or g6) else None
    rows.append({
        "draftYear": r["draftYear"], "overall": r["overallPickNumber"], "round": r["roundNumber"],
        "playerId": r["playerId"], "playerName": r["playerName"], "is_goalie": r["is_goalie"],
        "link_status": r["link_status"], "birthDate": b, "nhl_gp": gp.sum(), "n_accrued": len(accrued),
        "y27": y27, "a7": a7, "end_g3": g3, "end_with_g6_bound": with6,
    })
w = pd.DataFrame(rows)
w["played_nhl"] = w["nhl_gp"] > 0
unknown = w["end_g3"].isna() | (w["link_status"] == "excluded_merged_name")
w["past_g3"] = ~unknown & (w["end_g3"] > LAST_SEEN)
w["past_g6"] = ~unknown & (w["end_with_g6_bound"] > LAST_SEEN)

print(f"\nwindow end unknown (no birthdate or merged-name exclusion): {unknown.sum()}")
for _, r in w[unknown].iterrows():
    print(f"   {r['draftYear']} #{r['overall']} {r['playerName']} ({r['link_status']}, birth {r['birthDate']})")

# ---- the count, by class -------------------------------------------------
print("\nWINDOWS RUNNING PAST 2025-26, by draft class")
print("  (Group 3 = the CBA's age-27 / seven-Accrued-Season rule; with Group 6 = the most")
print("   Group 6 could shorten windows; 'played' = at least one NHL game by 2025-26)")
tab = w[~unknown].groupby("draftYear").agg(
    picks=("past_g3", "size"),
    past_g3=("past_g3", "sum"),
    past_g3_played=("past_g3", lambda s: (s & w.loc[s.index, "played_nhl"]).sum()),
    past_g6=("past_g6", "sum"),
    past_g6_played=("past_g6", lambda s: (s & w.loc[s.index, "played_nhl"]).sum()),
)
tab.loc["all"] = tab.sum()
print(tab.to_string())

# How far past: the last controlled season's end-year among windows past 2025-26.
past = w[w["past_g3"]]
print("\nGroup 3: last controlled season (end-year) for windows past 2025-26:")
print(past["end_g3"].value_counts().sort_index().to_string())
print("\nBy round, classes 2015-2017, Group 3 (past / picks; played NHL among past):")
late = w[~unknown & w["draftYear"].between(2015, 2017)]
print(late.groupby(["draftYear", "round"]).apply(
    lambda d: f"{d['past_g3'].sum()}/{len(d)} ({(d['past_g3'] & d['played_nhl']).sum()} played)",
    include_groups=False).unstack().to_string())

# ---- check against PuckPedia's UFA year ------------------------------------
spine = pd.read_csv(SPINE_PATH, usecols=["nhl_id", "ufa_year"]).dropna()
spine = spine.groupby("nhl_id")["ufa_year"].max().astype(int)   # latest contract's UFA year per player
chk = w[w["playerId"].notna() & w["end_g3"].notna()].copy()
chk["pp_ufa"] = chk["playerId"].astype(int).map(spine)
chk = chk[chk["pp_ufa"].notna()]
chk["diff"] = chk["pp_ufa"] - chk["end_g3"]          # + means PuckPedia's UFA year is later than ours
print(f"\nCHECK vs PuckPedia ufa_year ({len(chk)} drafted players with a PuckPedia contract):")
print("  difference in seasons (PuckPedia minus this rule), counts:")
print(chk["diff"].value_counts().sort_index().to_string())
seen = chk[chk["end_g3"] <= LAST_SEEN]
print(f"  among windows this rule ends by 2025-26: {(seen['diff'] == 0).sum()} of {len(seen)} agree")
earlier = chk[chk["diff"] < 0]
print(f"  PuckPedia earlier than this rule (the roster-games gap would do this): {len(earlier)}")
print(earlier.sort_values("diff")[["draftYear", "overall", "playerName", "is_goalie", "nhl_gp",
                                   "n_accrued", "y27", "a7", "end_g3", "pp_ufa"]].head(15).to_string(index=False))
later = chk[chk["diff"] > 0]
print(f"  PuckPedia later than this rule: {len(later)}")
print(later.sort_values("diff", ascending=False)[["draftYear", "overall", "playerName", "is_goalie",
      "nhl_gp", "n_accrued", "y27", "a7", "end_g3", "pp_ufa"]].head(15).to_string(index=False))

w.to_csv(OUT_PATH, index=False)
print(f"\nwrote {OUT_PATH} ({len(w):,} rows)")
