"""goalie_birthdates.py -- every goaltender's birthdate from the NHL's own records, season by season.

WHY (Thomas, 2026-10-21: "fetch the missing goalie birthdates from the NHL stats API goalie-bios endpoint (the route
tested 2026-09-28), guard the two Matt Murrays, and add them where the goalie model reads ages"). Goalie ages came only
from PuckPedia's contract-export birthdates matched by name (contract_npv's goalie exit-hazard panel), and, counted
2026-10-21, 86 of the 280 goaltenders in Goalies_WAR.csv (322 of 1,560 goalie-seasons, mostly before 2015) had none
from PuckPedia or the draft records. The route was tested on 2026-09-28 (session 2026-09-28b): 96 of the 98 then missing
were found; not wired in until now.

THE SOURCE: api.nhle.com/stats/rest/en/goalie/bios, regular season (gameTypeId 2), one request per season 2007-08 to
2025-26; each row is one goaltender who played that season, with his NHL id, birthdate and games played. Each season's
answer is cached in OUTPUT_DIR/goalie_bios_raw/<seasonId>.json and never fetched again (--refetch overrides), as
draft_pick_linkage.py caches records.nhl.com.

THE JOIN, by season (keyed on the season because one name can be two players):
  * Goalies_WAR.csv's goaltender-seasons (team-split seasons summed, as goalie_value_engine does), name normalised as
    the goalie panel normalises it (skater_forward_projection.norm_name);
  * the NHL's rows for that season under the same normalised name. One NHL id: that player. Two or more (two
    goaltenders with one name in one season): the id whose games played equals the WAR file's for that season; if none
    or more than one match, the season is left without a birthdate and listed (status "ambiguous").
  * THE MATT MURRAYS (GUARD): two goaltenders share the name (NHL ids 8476899, born 1994-05-25, and 8482146? -- read from
    the data, not assumed). Every Matt Murray season must resolve to exactly one NHL id, and the run lists each. A name
    the NHL spells differently from Bacon (an accent, a short first name) is matched only through the crosswalk below;
    the rest are listed as unmatched.
  * CROSSWALK: WAR spellings that differ from the NHL's, found by this run's unmatched list and checked by hand against
    the NHL id's games played in each season (empty until a case is found).

OUTPUT: OUTPUT_DIR/goalie_birthdates.csv, one row per Goalies_WAR goaltender-season: nname, syr, goalie (WAR spelling),
nhl_id, birthdate, gp_war, gp_nhl, status (one id / resolved by games / ambiguous / not in the NHL's records), and
pp_birthdate (PuckPedia's, where the contract export has one under the name) with agree (the two dates equal).
GUARD: where PuckPedia and the NHL both give a date for a name with one NHL id, the dates must agree, or the run lists
each disagreement and stops (a name matched to the wrong player shows up here).

HOW TO RUN (repo root; needs the internet the first time, about 20 requests):  python 20_CODE/goalie_birthdates.py
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from skater_forward_projection import norm_name   # noqa: E402  the goalie panel's normaliser (contract_npv)

SCRIPT_VERSION = "goalie_birthdates.py v1.0 (2026-10-21)"
SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
RAW = OUTPUT_DIR / "goalie_bios_raw"
URL = "https://api.nhle.com/stats/rest/en/goalie/bios"
UA = os.environ.get("SCRAPER_USER_AGENT", "xnpv-model/1.0 (academic research)")
SEASONS = range(2007, 2026)            # 2007-08 .. 2025-26, the seasons Goalies_WAR.csv covers
CROSSWALK = {}                          # WAR spelling (normalised) -> NHL spelling (normalised), each checked by hand
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def season_bios(y, refetch=False):
    sid = f"{y}{y + 1}"
    f = RAW / f"{sid}.json"
    if f.exists() and not refetch:
        return json.loads(f.read_text(encoding="utf-8")), "cache"
    params = {"isAggregate": "false", "isGame": "false", "limit": "-1", "start": "0",
              "cayenneExp": f"gameTypeId=2 and seasonId<={sid} and seasonId>={sid}"}
    r = requests.get(URL, params=params, timeout=30, headers={"User-Agent": UA})
    r.raise_for_status()
    j = r.json()
    assert j.get("total") == len(j.get("data", [])), (sid, j.get("total"), len(j.get("data", [])))   # GUARD: one page
    RAW.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(j), encoding="utf-8")
    time.sleep(1.0)
    return j, "fetched"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refetch", action="store_true", help="fetch every season again, overwriting the cache")
    args = ap.parse_args()
    log(SCRIPT_VERSION)

    # ---- the NHL's goaltender-seasons ------------------------------------------------------------------------------
    rows, how = [], {}
    for y in SEASONS:
        j, src = season_bios(y, args.refetch)
        how[src] = how.get(src, 0) + 1
        for r in j["data"]:
            rows.append({"syr": y, "nhl_id": int(r["playerId"]), "nhl_name": r["goalieFullName"],
                         "birthdate": r.get("birthDate"), "gp_nhl": int(r.get("gamesPlayed") or 0)})
    nhl = pd.DataFrame(rows)
    nhl["nname"] = nhl["nhl_name"].map(norm_name)
    log(f"NHL goalie bios: {len(nhl):,} goaltender-seasons, {nhl['nhl_id'].nunique():,} goaltenders, seasons "
        f"{min(SEASONS)}-{max(SEASONS)} ({how})")
    ids_per = nhl.groupby("nhl_id")["birthdate"].nunique()
    assert (ids_per <= 1).all(), ids_per[ids_per > 1]                                     # GUARD: one date per player

    # ---- the WAR file's rows, one per goaltender, season and team (matched before team-split seasons are summed) --------
    g = pd.read_csv(SOURCE_DIR / "Goalies_WAR.csv")
    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    g["nname"] = g["Goalie"].map(norm_name)
    g["nkey"] = g["nname"].map(lambda n: CROSSWALK.get(n, n))
    g = g.reset_index().rename(columns={"index": "row"})
    log(f"Goalies_WAR.csv: {len(g):,} rows, {g.groupby(['nname', 'syr']).ngroups:,} goaltender-seasons, "
        f"{g['nname'].nunique():,} names")

    # ---- the join, row by row: one NHL id under the name that season, else the one whose games equal the row's ------
    cand = g.merge(nhl, left_on=["nkey", "syr"], right_on=["nname", "syr"], how="left", suffixes=("", "_nhl"))
    rid = {}
    for row, c in cand.groupby("row"):
        c = c[c["nhl_id"].notna()]
        if c.empty:
            rid[row] = (None, "not in the NHL's records")
        elif c["nhl_id"].nunique() == 1:
            rid[row] = (int(c["nhl_id"].iloc[0]), "one id")
        else:
            m = c[c["gp_nhl"] == c["GP"]]
            rid[row] = ((int(m["nhl_id"].iloc[0]), "resolved by games") if m["nhl_id"].nunique() == 1
                        else (None, "ambiguous"))
    g["nhl_id"] = g["row"].map(lambda r: rid[r][0])
    g["status"] = g["row"].map(lambda r: rid[r][1])
    bd = nhl.drop_duplicates("nhl_id").set_index("nhl_id")["birthdate"]
    gpn = nhl.set_index(["nhl_id", "syr"])["gp_nhl"]

    # ---- one row per goaltender-season, as goalie_value_engine and the goalie panel key them (name and season) --------
    out = []
    for (name, y), x in g.groupby(["nname", "syr"], sort=False):
        base = {"goalie": x["Goalie"].iloc[0], "nname": name, "syr": y, "gp_war": int(x["GP"].sum()),
                "teams": "/".join(x["Team"].astype(str))}
        ids = x.dropna(subset=["nhl_id"]).groupby("nhl_id")["GP"].sum().sort_values(ascending=False)
        if ids.empty:
            out.append({**base, "status": x["status"].iloc[0]}); continue
        top = int(ids.index[0])
        st = x["status"].iloc[0] if len(ids) == 1 else (
            f"two players in one WAR season ({'; '.join(f'{int(i)} {int(n)} games' for i, n in ids.items())}); "
            "birthdate of the one with more games")
        out.append({**base, "nhl_id": top, "birthdate": bd[top], "gp_nhl": int(gpn.get((top, y), 0)), "status": st})
    D = pd.DataFrame(out)
    two = D[D["status"].str.startswith("two players")]
    log(f"\nSEASONS IN WHICH THE WAR FILE'S NAME HOLDS TWO NHL PLAYERS (team rows summed by goalie_value_engine and the "
        f"goalie panel): {len(two)}")
    for r in two.itertuples():
        log(f"  {r.goalie} {r.syr}-{(r.syr + 1) % 100:02d} ({r.teams}): {r.status}")

    # ---- the Matt Murrays (GUARD) -------------------------------------------------------------------------------------
    mm = D[D["nname"] == norm_name("Matt Murray")].sort_values("syr")
    ids = nhl.loc[nhl["nname"] == norm_name("Matt Murray"), ["nhl_id", "birthdate"]].drop_duplicates()
    log(f"\nTHE MATT MURRAYS: the NHL has {len(ids)} goaltenders under the name: "
        + "; ".join(f"{int(r.nhl_id)} born {r.birthdate}" for r in ids.itertuples()))
    for r in g[g["nname"] == norm_name("Matt Murray")].sort_values("syr").itertuples():
        log(f"  {r.syr}-{(r.syr + 1) % 100:02d} {r.Team}: WAR games {r.GP}, {r.status} -> {int(r.nhl_id)} born {bd[r.nhl_id]}")
    for r in mm.iloc[0:0].itertuples():
        log(f"  {r.syr}-{(r.syr + 1) % 100:02d}: WAR games {r.gp_war}, {r.status}"
            + (f" -> {int(r.nhl_id)} born {r.birthdate} (NHL games {int(r.gp_nhl)})" if pd.notna(r.nhl_id) else ""))
    assert len(mm) and mm["nhl_id"].notna().all(), "a Matt Murray season is unresolved"
    assert (g.loc[g["nname"] == norm_name("Matt Murray"), "nhl_id"].notna()).all(), "a Matt Murray row is unresolved"

    # ---- against PuckPedia's birthdates (GUARD) ----------------------------------------------------------------------
    pp = pd.read_excel(os.environ["PUCKPEDIA_CONTRACTS_XLSX"])
    pp = pp[pp["position"] == "Goaltender"].copy()
    import contract_source as CS
    pp["nname"] = CS.war_full_name(pp, pp["first_name"].astype(str) + " " + pp["last_name"].astype(str)).map(norm_name)
    pp["pp_birthdate"] = pd.to_datetime(pp["birthdate"], errors="coerce").dt.strftime("%Y-%m-%d")
    ppb = pp.dropna(subset=["pp_birthdate"]).groupby("nname")["pp_birthdate"].agg(lambda s: ";".join(sorted(set(s))))
    D["pp_birthdate"] = D["nname"].map(ppb)
    both = D["birthdate"].notna() & D["pp_birthdate"].notna()
    D["agree"] = pd.NA
    D.loc[both, "agree"] = [b in p.split(";") for b, p in zip(D.loc[both, "birthdate"], D.loc[both, "pp_birthdate"])]
    one_id_names = D.groupby("nname")["nhl_id"].nunique()
    one_id_names = set(one_id_names[one_id_names == 1].index)
    bad = D[both & (D["agree"] == False) & D["nname"].isin(one_id_names)].drop_duplicates("nname")   # noqa: E712
    log(f"\nAGAINST PUCKPEDIA: {int(both.sum()):,} goaltender-seasons carry both dates; they disagree for "
        f"{int((D['agree'] == False).sum())} ({bad['nname'].nunique()} names with one NHL id)")   # noqa: E712
    for r in bad.itertuples():
        log(f"  DISAGREE {r.goalie}: NHL {r.birthdate} (id {int(r.nhl_id)}), PuckPedia {r.pp_birthdate}")
    if len(bad):
        raise SystemExit("PuckPedia and the NHL disagree on a goaltender's birthdate; resolve each before use")

    # ---- coverage -----------------------------------------------------------------------------------------------------
    has_nhl = D["birthdate"].notna()
    has_pp = D["pp_birthdate"].notna()
    names = D.groupby("nname").agg(nhl=("birthdate", lambda s: s.notna().any()), pp=("pp_birthdate", lambda s: s.notna().any()))
    log(f"\nCOVERAGE: goaltender-seasons with an NHL birthdate {int(has_nhl.sum()):,} of {len(D):,}; with PuckPedia's "
        f"{int(has_pp.sum()):,}; with either {int((has_nhl | has_pp).sum()):,}")
    log(f"  goaltenders: NHL {int(names['nhl'].sum())} of {len(names)}; PuckPedia {int(names['pp'].sum())}; either "
        f"{int((names['nhl'] | names['pp']).sum())}")
    for st, n in D["status"].value_counts().items():
        log(f"  status {st}: {n:,}")
    left = D[~has_nhl].sort_values(["nname", "syr"])
    for nm, x in left.groupby("nname"):
        log(f"  NO NHL BIRTHDATE: {x['goalie'].iloc[0]} ({', '.join(str(s) for s in x['syr'])}; {x['status'].iloc[0]})")
    D.to_csv(OUTPUT_DIR / "goalie_birthdates.csv", index=False)
    (OUTPUT_DIR / "goalie_birthdates_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {OUTPUT_DIR / 'goalie_birthdates.csv'}")


if __name__ == "__main__":
    main()
