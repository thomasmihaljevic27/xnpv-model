"""
war_name_crosswalk.py -- each contracted player's name as the WAR tables spell it, found from evidence.

WHY (Thomas, 2026-10-14: "Fix here now"). The player chain joins a PuckPedia contract to the player's NHL seasons
by cleaned name (player_season_table.norm_name: accents, punctuation and a fixed list of short first names). WAR.csv
and Goalies_WAR.csv have no player id. Where the two sources spell a player differently beyond that list, his
contract never meets his seasons and the player model has no row for him: Evgenii/Evgeny Dadonov, Matthew/Matty
Beniers, John-Jason/JJ Peterka, Joseph/Joe Veleno, Cameron/Cam York (found 2026-10-14, while auditing the traded
assets neither model values).

WHAT IT DOES
  For every NHL id in the PuckPedia contract export:
  1. SAME NAME: his cleaned PuckPedia name has rows in the WAR table for his position (skaters WAR.csv, goalies
     Goalies_WAR.csv). Nothing to do; the chain already joins him.
  2. Otherwise, MATCHED ON THE GAME LOGS: his NHL id's regular seasons in nhl_gamelogs.sqlite (2017-18 on; games and
     the teams he dressed for) are compared, season by season, with each WAR name's (season, team, games).
     Candidates: WAR names with the same cleaned surname (the last word), or, failing that, any WAR name that agrees
     on two or more seasons. A season AGREES when the team sets share a team and the games differ by 2 or fewer; it
     CONFLICTS when both have the season and either test fails. Accepted: the one candidate with the most agreeing
     seasons, at least one, no conflicting season, and no other candidate as good; and a WAR name no other NHL id
     already holds (by same name or by match).
  3. Otherwise UNRESOLVED, with the reason (no NHL games in the logs; no candidate; a tie; a conflict; claimed).
     Goalies are compared on games played (on the ice), not games dressed for.
     ONE SEASON UNDER TWO WAR NAMES: where WAR writes one season of one player under two names and the two together
     agree with the logs (J.J. Moser 19 + Janis Moser 24 = 43 games, 2021-22), the best name is accepted and the
     other recorded (war_name_split), not merged: the chain keys careers on WAR names, and merging them would change
     the season table its production guard checks. A stated limitation for that season.

OUTPUT: OUTPUT_DIR/war_name_crosswalk.csv: nhl_id, pp_name, war_name (raw, as the WAR file spells it; empty when
unresolved), is_goalie, method (same name / game-log match / unresolved: ...), seasons_agree, seasons_conflict.
contract_source.war_full_name() reads it: the chain's consumers take the WAR spelling for a matched id and the
PuckPedia spelling otherwise, so a player who already joined is untouched.

GUARD: no WAR name is held by two NHL ids.
INPUTS: SOURCE_DIR/PuckPedia contract export (contract_source.load_contracts), WAR.csv, Goalies_WAR.csv,
nhl_gamelogs.sqlite. Run from the repo root:  python 20_CODE/war_name_crosswalk.py  (before age_join.py)
"""

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "war_name_crosswalk.py v1.0 (2026-10-14)"
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_source as CS                       # noqa: E402
from player_season_table import norm_name          # noqa: E402  the chain's own name rule
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])
GP_TOL, MIN_FALLBACK = 2, 2
TEAM = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL"}     # WAR codes -> NHL API codes
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def war_seasons(path, name_col):
    """{raw WAR name: {start year: (GP, team set)}} and the raw names by cleaned name."""
    w = pd.read_csv(path, usecols=[name_col, "Season", "Team", "GP"])
    w["syr"] = 2000 + w["Season"].astype(str).str[:2].astype(int)
    out = {}
    for (n, y), g in w.groupby([name_col, "syr"]):
        teams = {TEAM.get(t, t) for x in g["Team"].astype(str) for t in x.split("/")}
        out.setdefault(n, {})[int(y)] = (float(g["GP"].sum()), teams)
    by_clean = {}
    for n in out:
        by_clean.setdefault(norm_name(n), []).append(n)
    return out, by_clean


def log_seasons(con, table):
    """{NHL id: {start year: (games, teams)}}. Goalies: games he played (on the ice), not games he dressed for,
    as the WAR table counts them (Aleksei Kolosov 2024-25: dressed 34, played 17, WAR 17)."""
    played = " and s.toi_minutes > 0" if table == "goalie_games" else ""
    q = (f"select s.player_id, g.season, s.team, count(*) gp from {table} s join games g using(game_id) "
         f"where g.game_type = 2{played} group by 1, 2, 3")
    d = pd.read_sql(q, con)
    d["syr"] = d["season"].str[:4].astype(int)
    out = {}
    for (i, y), g in d.groupby(["player_id", "syr"]):
        out.setdefault(int(i), {})[int(y)] = (float(g["gp"].sum()), set(g["team"]))
    return out


def compare(mine, theirs):
    agree = conflict = 0
    for y, (gp, teams) in mine.items():
        if y in theirs:
            gp2, teams2 = theirs[y]
            if teams & teams2 and abs(gp - gp2) <= GP_TOL:
                agree += 1
            else:
                conflict += 1
    return agree, conflict


def main():
    log(SCRIPT_VERSION)
    pc, enc = CS.load_contracts()
    con = sqlite3.connect(SOURCE_DIR / "nhl_gamelogs.sqlite")
    W = {False: war_seasons(SOURCE_DIR / "WAR.csv", "Player"), True: war_seasons(SOURCE_DIR / "Goalies_WAR.csv", "Goalie")}
    L = {False: log_seasons(con, "skater_games"), True: log_seasons(con, "goalie_games")}
    # season index for the fallback: (goalie?, year, team) -> raw WAR names with their games
    IDX = {}
    for gk, (ws, _) in W.items():
        for n, ss in ws.items():
            for y, (gp, teams) in ss.items():
                for t in teams:
                    IDX.setdefault((gk, y, t), []).append((n, gp))
    pp = pc.dropna(subset=["nhl_id"]).drop_duplicates("nhl_id").copy()
    pp["pp_name"] = pp["first_name"].astype(str).str.strip() + " " + pp["last_name"].astype(str).str.strip()
    pp["is_goalie"] = pp["position"].astype(str).eq("Goaltender")
    log(f"  PuckPedia contract export ({enc}): {len(pp):,} NHL ids")

    rows, claimed = [], {}
    for r in pp.itertuples():
        gk, nid = bool(r.is_goalie), int(r.nhl_id)
        ws, by_clean = W[gk]
        clean = norm_name(r.pp_name)
        rec = {"nhl_id": nid, "pp_name": r.pp_name, "is_goalie": gk, "war_name": "", "war_name_split": "",
               "seasons_agree": 0, "seasons_conflict": 0}
        if clean in by_clean:
            rec.update(method="same name", war_name=by_clean[clean][0])
            rows.append(rec)
            continue
        mine = L[gk].get(nid)
        if not mine:
            rec["method"] = "unresolved: no NHL games in the logs (2017-18 on)"
            rows.append(rec)
            continue
        sur = clean.split()[-1] if clean else ""
        cands = [n for c, ns in by_clean.items() if c.split() and c.split()[-1] == sur for n in ns]
        how = "surname"
        if not cands:                               # fallback: names that share his seasons and teams
            hits = {}
            for y, (gp, teams) in mine.items():
                for t in teams:
                    for n, gp2 in IDX.get((gk, y, t), []):
                        if abs(gp - gp2) <= GP_TOL:
                            hits[n] = hits.get(n, 0) + 1
            cands = [n for n, c in hits.items() if c >= MIN_FALLBACK]
            how = "seasons"
        scored = sorted(((compare(mine, ws[n]), n) for n in cands), key=lambda x: (-x[0][0], x[0][1]))
        if not scored:
            rec["method"] = "unresolved: no candidate"
        else:
            (ag, cf), best = scored[0]
            tie = len(scored) > 1 and scored[1][0][0] == ag and scored[1][0][1] == 0
            split = None
            if cf > 0 and how == "surname":
                # WAR may write one season of one player under two names (J.J. Moser 19 + Janis Moser 24 = 43
                # in 2021-22): accept the best name when one other same-surname name fills each conflicting
                # season exactly, and record that name (not merged: the chain keys careers on WAR names)
                for _, other in scored[1:]:
                    both = {y: (ws[best].get(y, (0, set()))[0] + ws[other].get(y, (0, set()))[0],
                                ws[best].get(y, (0, set()))[1] | ws[other].get(y, (0, set()))[1])
                            for y in set(ws[best]) | set(ws[other])}
                    a2, c2 = compare(mine, both)
                    if c2 == 0 and a2 >= ag:
                        split = other
                        break
            if ag < 1:
                rec["method"] = "unresolved: no season agrees"
            elif cf > 0 and split is not None:
                rec.update(method=f"game-log match ({how}; WAR splits a season under {split}, not merged)",
                           war_name=best, war_name_split=split, seasons_agree=ag, seasons_conflict=cf)
            elif cf > 0:
                rec["method"] = f"unresolved: conflict ({best})"
            elif tie:
                rec["method"] = f"unresolved: tie ({best} / {scored[1][1]})"
            else:
                rec.update(method=f"game-log match ({how})", war_name=best, seasons_agree=ag, seasons_conflict=cf)
        rows.append(rec)
    x = pd.DataFrame(rows)

    # a WAR name held by a same-name id cannot also be matched to another id
    held = x[x["method"] == "same name"].groupby(["is_goalie", "war_name"]).size()
    clash = x["method"].str.startswith("game-log") & x.apply(
        lambda r: (r["is_goalie"], r["war_name"]) in held.index, axis=1)
    x.loc[clash, "method"] = "unresolved: WAR name already held by a same-name id"
    x.loc[clash, "war_name"] = ""
    m = x[x["method"].str.startswith("game-log")]
    dup = m.groupby(["is_goalie", "war_name"]).size()
    dup = dup[dup > 1]
    for (gk, n), _ in dup.items():
        sel = m[(m["is_goalie"] == gk) & (m["war_name"] == n)].index
        x.loc[sel, "method"] = "unresolved: two ids match one WAR name"
        x.loc[sel, "war_name"] = ""
    m = x[x["method"].str.startswith("game-log")]
    assert not m.duplicated(["is_goalie", "war_name"]).any()                    # GUARD

    log("\n" + x["method"].map(lambda s: s.split(" (")[0] if s.startswith(("game-log", "unresolved: conflict",
                                                                            "unresolved: tie")) else s)
        .value_counts().to_string())
    log(f"\nMATCHED ON THE GAME LOGS: {len(m)} ids")
    for r in m.sort_values("pp_name").itertuples():
        log(f"  {r.nhl_id}  {r.pp_name:<28} -> {r.war_name:<26} ({r.seasons_agree} season{'s' if r.seasons_agree != 1 else ''}"
            f" agree; {r.method})")
    un = x[x["method"].str.startswith("unresolved") & ~x["method"].str.contains("no NHL games")]
    log(f"\nUNRESOLVED WITH NHL GAMES: {len(un)}")
    for r in un.itertuples():
        log(f"  {r.nhl_id}  {r.pp_name:<28} {r.method}")
    x.to_csv(OUTPUT_DIR / "war_name_crosswalk.csv", index=False)
    (OUTPUT_DIR / "war_name_crosswalk_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote war_name_crosswalk.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
