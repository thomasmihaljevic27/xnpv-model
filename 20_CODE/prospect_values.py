"""
prospect_values.py -- the prospect model, step one: what each prospect in the trade inventory was worth when
he was traded, from his draft slot and the seasons since his draft.

SPECIFICATION: 00_STATE/MODEL_DIRECTIVES.md directive 6, "Prospects, step one" (Thomas, 2026-10-14). Every
rule below is a recorded decision; the bracket says where.

WHO IS A PROSPECT [opening decision 2]
  A drafted player the player model does not take yet at the valuation season y:
  * skaters: no NHL season of 10+ games in the three before y (forecast_config.MIN_GP; the skater forecast's
    three-season anchor);
  * goalies: no NHL game in the six seasons before y (the goalie forecast takes any NHL season in the three
    before, walking back up to three more: contract_npv.shrunk_projection, STALE_MAXBACK = 3).
  A player the player model takes is valued there, not here. Undrafted players have no slot: step one gives
  them no value; they enter with production [spec item 5].

WHAT HE IS WORTH [opening decisions 1 and 3]
  value = Bacon's star chance for his slot (draft_slot_baseline.csv p_star) x STAR VALUE(k),
  k = seasons since his draft = y - draft year (k = 0: the season starting the autumn after his draft, the
  pick curve's first season). The currency is the pick curve's: remaining NHL seasons priced on the contract
  line minus his cost (entry-level deal, then the qualifying offer or the arbitration price), to the end of
  club control, at the 2025-26 cap.
  * STAR VALUE(k): pick_curve.fit_scale's regression (through zero, draft-year indicators that sum to zero,
    robust HC1 errors) on the 2007-2017 drafted players who were prospects at k, outcome their remaining
    surplus: pick_curve_seasons.csv's priced seasons from y on (season y in full), lapsed rights zeroed as the
    pick curve zeroes them. k = 0, 1, 2, 3 one fit each; 4 and later one fit on the stacked rows for k = 4..7,
    errors clustered by player. Kept: the through-zero form (Thomas, 2026-10-14), the pick curve's current
    form; the free-constant alternative is an open choice (WORK_QUEUE).
  * Past the end of club control (CBA Group 3, as pick_curve.window_end: 27 as of June 30, or seven Accrued
    Seasons) a prospect is worth zero: nothing is left to control.
  * THE OVERLAP [opening decision 4]: a 2007-2017 draftee sits inside the fit that values him. Stated as a
    limitation; his value with his own draft left out of the fit is reported beside (value_own_draft_out_M).

THE TRADE INVENTORY (trades.db, player assets, from 2017-07-01 as for traded picks; trade season = the season
starting July 1 on or before the trade date; valuation season y = the trade season, or his draft year when he
is traded between his draft and July 1).
  MATCHING a traded name to a drafted player (draft_pick_linkage.csv, drafts 2005-2026), ours:
  * names compared as surname plus a canonical first name (pick_curve.name_key's short forms, widened here
    with nic/nicolas, nate, phil, sammy, evgenii, yegor) and a hand list of initials-forms (P.O Joseph, J-F
    Berube), hyphens read as spaces;
  * only players whose draft had begun by the trade date;
  * initials joined before comparing ("P.O Joseph" and "Pierre-Olivier Joseph"; "A.J." and "AJ");
  * a NAMESAKE GUARD: a candidate with no NHL record (link_status zero_no_nhl_record) is rejected when the
    traded name has NHL seasons in the WAR tables between his draft and the trade: those seasons belong to
    someone else, so the traded player is not this draftee. Seasons before his draft are an older namesake's
    and do not reject him;
  * two or more candidates left: not valued, listed (ambiguous).

TRAILING WEIGHTING CHECK (directive 6): this script reads no trailing total itself; the surplus it fits on
carries the pick curve's arbitration price, which reads the forecast's 50/30/20 (pick_curve.py v1.5).

INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_seasons.csv, pick_curve_scales.csv (pick_curve.py),
OUTPUT_DIR/draft_pick_linkage.csv, OUTPUT_DIR/draft_raw/draft_YYYY.json, SOURCE_DIR/trades.db, WAR.csv,
Goalies_WAR.csv, draft_slot_baseline.csv.
OUTPUTS: OUTPUT_DIR/prospect_values.csv (one row per traded player asset), prospect_star_values.csv (the star
value for each k, and with each draft left out), prospect_values_log.txt.

Run from the repo root:  python 20_CODE/prospect_values.py   (after pick_curve.py)
"""

import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_values.py v1.0 (2026-10-14)"
load_dotenv()
SOURCE_DIR, OUTPUT_DIR = Path(os.environ["SOURCE_DIR"]), Path(os.environ["OUTPUT_DIR"])

# ---- constants (each from the specification above) ----------------------------------------------
SKATER_GP, SKATER_BACK = 10, 3        # skater forecast: a 10+ game season in the three before
GOALIE_BACK = 6                       # goalie forecast: three before, walk-back up to three more
POOL_FROM, K_MAX = 4, 7               # k = 0..3 one fit each; 4+ one fit on k = 4..7
LAST_START = 2025                     # 2025-26, the last season in the data (start year)
FIT_CLASSES = range(2007, 2018)       # the pick curve's drafts
LAPSED = ("lapsed", "drafted twice (earlier pick)")
TRADES_FROM = "2017-07-01"
ACCRUE_PRORATE = {2012: 48 / 82, 2019: 70 / 82, 2020: 56 / 82}   # as pick_curve (Accrued Season thresholds)
FIRST_FORMS = {"tony": "anthony", "josh": "joshua", "mike": "michael", "alex": "alexander", "matt": "matthew",
               "nick": "nicholas", "will": "william", "zach": "zachary", "jake": "jacob", "dan": "daniel",
               "danny": "daniel", "chris": "christopher", "sam": "samuel", "ben": "benjamin", "tom": "thomas",
               "jon": "jonathan", "joe": "joseph", "andy": "andrew", "nate": "nathan", "max": "maxim",
               "steve": "steven", "rob": "robert", "bobby": "robert",           # pick_curve.SHORT_FORMS
               "nic": "nicholas", "nicolas": "nicholas", "phil": "philip", "sammy": "samuel",   # added here
               "evgenii": "evgeni", "yegor": "egor"}
INITIAL_FORMS = {"po joseph": "pierre olivier joseph", "jf berube": "jean francois berube"}   # after joining

LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def norm(s):
    """pick_curve.norm, with hyphens read as spaces: strip accents, lowercase, letters and spaces."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", "", s.lower().replace("-", " ").replace(".", " "))
    return re.sub(r"\s+", " ", s).strip()


def name_key(s):
    n = re.sub(r"\b([a-z]) (?=[a-z]\b)", r"\1", norm(s))   # initials joined: "p o joseph" -> "po joseph"
    n = INITIAL_FORMS.get(n, n)
    parts = n.split()
    if len(parts) < 2:
        return (n, "")
    return (parts[-1], " ".join(FIRST_FORMS.get(x, x) for x in parts[:-1]))


def year_reaching(birth, age):
    """pick_curve.year_reaching: END-year of the first League Year at whose June 30 he is `age` or older."""
    return birth.year + age + (1 if (birth.month, birth.day) > (6, 30) else 0)


def window_end(birth, is_goalie, seasons):
    """pick_curve.window_end: END-year of his last controlled season (CBA Group 3)."""
    base = 30 if is_goalie else 40
    accrued = sorted(y + 1 for y, g in seasons["GP"].items() if g >= base * ACCRUE_PRORATE.get(y, 1.0))
    y27 = year_reaching(birth, 27)
    return min(y27, accrued[6]) if len(accrued) >= 7 else y27


def is_prospect(seasons, y, is_goalie):
    """True when the player model does not take him at season y (rule above). `seasons`: GP by start year."""
    before = seasons[(seasons.index < y) & (seasons["GP"] > 0)]
    if is_goalie:
        return not (before.index >= y - GOALIE_BACK).any()
    return not ((before.index >= y - SKATER_BACK) & (before["GP"] >= SKATER_GP)).any()


def k_group(k):
    return str(k) if k < POOL_FROM else f"{POOL_FROM}+"


# ---- the star values ----------------------------------------------------------------------------------
def fit(frame, cluster=False):
    """pick_curve.fit_scale on remaining surplus: through zero, sum-to-zero draft-year columns."""
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    X = np.column_stack([frame["p_star"].values]
                        + [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]])
    if cluster:
        groups = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    else:
        m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")
    return float(m.params[0]), float(m.bse[0])


def star_values():
    """The star value for each k group, and with each 2007-2017 draft left out. Returns (table, rows)."""
    p = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")
    s = pd.read_csv(OUTPUT_DIR / "pick_curve_seasons.csv")
    lapsed = p.loc[p["route"].isin(LAPSED), ["draftYear", "pick"]].assign(lapsed=True)
    s = s.merge(lapsed, on=["draftYear", "pick"], how="left")
    s["sur_M"] = np.where(s["lapsed"].fillna(False).astype(bool), 0.0, s["surplus_2025_cap"] / 1e6)
    by_player = {key: g.set_index("season").rename(columns={"gp": "GP"}) for key, g in s.groupby(["draftYear", "pick"])}
    empty = s.iloc[0:0].set_index("season").rename(columns={"gp": "GP"})
    rows = []
    for r in p.itertuples():
        mine = by_player.get((r.draftYear, r.pick), empty)
        for k in range(0, K_MAX + 1):
            y = r.draftYear + k
            if y > LAST_START:
                break
            rows.append({"draftYear": r.draftYear, "pick": r.pick, "p_star": r.p_star, "k": k,
                         "prospect": is_prospect(mine, y, bool(r.is_goalie)),
                         "remaining_M": float(mine.loc[mine.index >= y, "sur_M"].sum())})
    d = pd.DataFrame(rows)
    d["k_group"] = d["k"].map(lambda k: k_group(min(k, K_MAX)))
    out = []
    for grp, g in d[d["prospect"]].groupby("k_group", sort=True):
        clus = grp.endswith("+")
        b, se = fit(g, clus)
        out.append({"k_group": grp, "left_out": "none", "star_value_M": b, "se_M": se, "rows": len(g)})
        for c in sorted(g["draftYear"].unique()):
            bb, ss = fit(g[g["draftYear"] != c], clus)
            out.append({"k_group": grp, "left_out": str(c), "star_value_M": bb, "se_M": ss,
                        "rows": int((g["draftYear"] != c).sum())})
    return pd.DataFrame(out), d


# ---- NHL seasons by name (as pick_curve.season_table) -----------------------------------------------
FRANCHISE = {"N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "L.A": "LAK", "ATL": "WPG", "PHX": "ARI", "UTA": "ARI"}


def season_table(path, name_col):
    w = pd.read_csv(path, usecols=[name_col, "Season", "GP", "WAR"])
    w["name_n"] = w[name_col].map(norm)
    w["start"] = w["Season"].map(lambda x: 2000 + int(str(x)[:2]))
    return w.groupby(["name_n", "start"]).agg(GP=("GP", "sum"), WAR=("WAR", "sum"))


def main():
    log(SCRIPT_VERSION)
    F = {"pick_curve_players": OUTPUT_DIR / "pick_curve_players.csv",
         "pick_curve_seasons": OUTPUT_DIR / "pick_curve_seasons.csv",
         "pick_curve_scales": OUTPUT_DIR / "pick_curve_scales.csv",
         "linkage": OUTPUT_DIR / "draft_pick_linkage.csv", "trades": SOURCE_DIR / "trades.db",
         "WAR": SOURCE_DIR / "WAR.csv", "GWAR": SOURCE_DIR / "Goalies_WAR.csv",
         "bacon": SOURCE_DIR / "draft_slot_baseline.csv"}
    for k, p in F.items():
        log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
    log(f"  pick curve: {(OUTPUT_DIR / 'pick_curve_log.txt').read_text(encoding='utf-8').splitlines()[0]}")

    # ---- 1. the star values -----------------------------------------------------------------------
    sv, fitrows = star_values()
    main_sv = sv[sv["left_out"] == "none"].set_index("k_group")
    curve_main = pd.read_csv(F["pick_curve_scales"]).set_index("scale_kind").loc["main", "scale_M"]
    assert abs(main_sv.loc["0", "star_value_M"] - curve_main) < 1e-9          # GUARD: k = 0 is the pick curve
    log(f"\n  guard: at the draft the star value reproduces the pick curve's {curve_main:.4f} (PASS)")
    chk = OUTPUT_DIR / "prospect_slot_years.csv"                                # the check that measured step one
    if chk.exists():
        c = pd.read_csv(chk, dtype={"seasons_since_draft": str}).set_index("seasons_since_draft")["star_value_M"]
        gap = max(abs(main_sv.loc[g, "star_value_M"] - c[g]) for g in main_sv.index)
        assert gap < 1e-9, gap                                                   # GUARD
        log(f"  guard: star values equal prospect_slot_years_check.py's for {len(main_sv)} of {len(main_sv)} groups (PASS)")
    log("\nSTAR VALUE FOR A PLAYER STILL A PROSPECT ($M at the 2025-26 cap), by seasons since the draft")
    for g, r in main_sv.iterrows():
        lo = sv[(sv["k_group"] == g) & (sv["left_out"] != "none")]["star_value_M"]
        log(f"  {g:>2}: {r.star_value_M:6.2f} (se {r.se_M:.2f}); each draft left out {lo.min():.2f} to {lo.max():.2f}")

    # ---- 2. drafted players and their NHL seasons --------------------------------------------------
    bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
    link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])
    link["is_goalie"] = link["is_goalie"].astype(bool)
    link = link[link["link_status"] != "excluded_merged_name"].copy()
    link["key"] = link["playerName"].map(name_key)
    draft_day = {}
    for f in sorted((OUTPUT_DIR / "draft_raw").glob("draft_*.json")):
        rows = json.loads(f.read_text(encoding="utf-8"))["data"]
        draft_day[int(f.stem.split("_")[1])] = pd.Timestamp(min(r["draftDate"] for r in rows))
    tables = {False: season_table(F["WAR"], "Player"), True: season_table(F["GWAR"], "Goalie")}
    names_with_nhl = {}                                    # normalised name -> NHL start years (either table)
    for t in tables.values():
        for (n, y) in t.index:
            names_with_nhl.setdefault(n, set()).add(int(y))

    def seasons_of(row):
        tbl = tables[row["is_goalie"]]
        empty = pd.DataFrame({"GP": [], "WAR": []}, index=pd.Index([], name="start"))
        if pd.isna(row["war_names"]):
            return empty
        names = {norm(x) for x in str(row["war_names"]).split("|")} & set(tbl.index.get_level_values(0))
        if not names:
            return empty
        s = pd.concat([tbl.loc[n] for n in names]).groupby(level=0).sum()
        return s[s.index >= row["draftYear"]]             # GUARD (as pick_curve): no namesake's earlier seasons

    # ---- 3. the traded players ----------------------------------------------------------------------
    con = sqlite3.connect(F["trades"])
    a = pd.read_sql("select a.asset_id, a.trade_id, a.player_name, a.from_team, a.is_ahl_jr, a.is_signing_rights, "
                    "l.acquiring_team, t.trade_date from trade_assets a join trades t using(trade_id) "
                    "join trade_legs l using(leg_id) where a.asset_type = 'player' and t.trade_date >= ?",
                    con, params=(TRADES_FROM,))
    a["date"] = pd.to_datetime(a["trade_date"])
    a["trade_season"] = np.where(a["date"].dt.month >= 7, a["date"].dt.year, a["date"].dt.year - 1)
    log(f"\nplayers traded from {TRADES_FROM}: {len(a)} assets "
        f"(trades.db ends {pd.read_sql('select max(trade_date) m from trades', con)['m'][0]})")

    sv_main = main_sv["star_value_M"].to_dict()
    sv_out = {(r.k_group, int(r.left_out)): r.star_value_M for r in sv[sv["left_out"] != "none"].itertuples()}
    out = []
    for r in a.itertuples():
        key = name_key(r.player_name)
        cand = link[(link["key"] == key)
                    & link["draftYear"].map(lambda y: draft_day.get(y, pd.Timestamp(y, 6, 26)) <= r.date)]
        nhl_years = names_with_nhl.get(norm(r.player_name), set())
        # NAMESAKE GUARD: NHL seasons under this name between his draft and the trade would be his, but he has
        # none (zero_no_nhl_record), so the traded player is someone else. Seasons before his draft belong to
        # an older namesake and say nothing (Nathan Smith, drafted 2018, traded 2022).
        rejected = cand[(cand["link_status"] == "zero_no_nhl_record")
                        & cand["draftYear"].map(lambda dy: any(dy <= z < r.trade_season for z in nhl_years))]
        cand = cand.drop(rejected.index)
        rec = {"asset_id": r.asset_id, "trade_id": r.trade_id, "trade_date": r.trade_date,
               "trade_season": r.trade_season, "player_name": r.player_name, "from_team": r.from_team,
               "acquiring_team": r.acquiring_team, "is_ahl_jr": bool(r.is_ahl_jr),
               "is_signing_rights": bool(r.is_signing_rights), "namesakes_rejected": len(rejected)}
        if len(cand) == 0:
            rec["status"] = "no drafted match (undrafted, drafted before 2005, or name not found)"
            out.append(rec)
            continue
        if len(cand) > 1:
            rec["status"] = "ambiguous name (not valued)"
            rec["candidates"] = "; ".join(f"{c.draftYear} #{c.overallPickNumber}" for c in cand.itertuples())
            out.append(rec)
            continue
        c = cand.iloc[0]
        s = seasons_of(c)
        y = max(int(r.trade_season), int(c["draftYear"]))
        k = y - int(c["draftYear"])
        slot = int(c["overallPickNumber"])
        p_star = float(bacon[min(slot, int(bacon.index.max()))])   # picks past 225 (2005 only): the last slot's chance
        end = window_end(c["birthDate"], c["is_goalie"], s) if pd.notna(c["birthDate"]) else None
        rec.update({"draftYear": int(c["draftYear"]), "pick": slot, "drafted_name": c["playerName"],
                    "position": c["position"], "is_goalie": bool(c["is_goalie"]), "link_status": c["link_status"],
                    "valuation_season": y, "seasons_since_draft": k, "k_group": k_group(k),
                    "nhl_games_before": float(s.loc[s.index < y, "GP"].sum()), "window_end": end,
                    "p_star": p_star})
        if not is_prospect(s, y, bool(c["is_goalie"])):
            rec["status"] = "player model (not a prospect)"
        elif end is not None and y >= end:
            rec["status"] = "prospect, club control over (worth zero)"
            rec["value_M"] = 0.0
        else:
            rec["status"] = "prospect, valued"
            rec["star_value_M"] = sv_main[k_group(k)]
            rec["value_M"] = p_star * sv_main[k_group(k)]
            if int(c["draftYear"]) in FIT_CLASSES:
                rec["value_own_draft_out_M"] = p_star * sv_out[(k_group(k), int(c["draftYear"]))]
            else:
                rec["value_own_draft_out_M"] = rec["value_M"]   # his draft is not in the fit
            if end is None:
                rec["status"] = "prospect, valued (no birthdate: control window not checked)"
        out.append(rec)
    v = pd.DataFrame(out)

    # ---- 4. report ----------------------------------------------------------------------------------
    log("\nHOW EACH TRADED PLAYER WAS TREATED")
    log(v.groupby("status").agg(assets=("asset_id", "size"), value_M=("value_M", "sum")).round(2).to_string())
    log(f"  namesakes rejected by the guard: {int(v['namesakes_rejected'].sum())} candidate rows")
    amb = v[v["status"].str.startswith("ambiguous")]
    for r in amb.itertuples():
        log(f"  ambiguous: {r.player_name} ({r.trade_date}): {r.candidates}")
    pv = v[v["status"].str.startswith("prospect, valued")]
    log(f"\nPROSPECTS VALUED: {len(pv)} assets, {pv['player_name'].nunique()} players, total ${pv['value_M'].sum():,.1f}M "
        f"(own draft left out: ${pv['value_own_draft_out_M'].sum():,.1f}M)")
    log(pv.groupby("k_group").agg(assets=("asset_id", "size"), mean_M=("value_M", "mean"),
                                  total_M=("value_M", "sum")).round(2).to_string())
    log(f"  beyond the fitted seasons (k > {K_MAX}, valued at the 4+ star value): {int((pv['seasons_since_draft'] > K_MAX).sum())}")
    log(f"  with 1-9 NHL games before the valuation season: {int((pv['nhl_games_before'] > 0).sum())}; "
        f"flagged signing rights: {int(pv['is_signing_rights'].sum())}; flagged AHL/junior: {int(pv['is_ahl_jr'].sum())}")
    log(f"  inside the fit's drafts (2007-2017; the stated overlap): {int(pv['draftYear'].isin(FIT_CLASSES).sum())}")
    log("\n  the twenty most valuable:")
    for r in pv.sort_values("value_M", ascending=False).head(20).itertuples():
        log(f"    {r.trade_date}  {r.player_name:<24} {int(r.draftYear)} #{int(r.pick):<3} k={int(r.seasons_since_draft)}  "
            f"${r.value_M:5.2f}M (own draft out ${r.value_own_draft_out_M:5.2f}M)  to {r.acquiring_team}")
    nd = v[v["status"].str.startswith("no drafted")]
    log(f"\n  not matched to a drafted player: {len(nd)} assets, of them flagged AHL/junior {int(nd['is_ahl_jr'].sum())}, "
        f"signing rights {int(nd['is_signing_rights'].sum())}, with NHL seasons in the WAR tables "
        f"{int(nd['player_name'].map(lambda n: norm(n) in names_with_nhl).sum())}")
    nn = nd[~nd["player_name"].map(lambda n: norm(n) in names_with_nhl)]
    log(f"  of them with no NHL season under the name (undrafted prospects or names not found; no value in step one): "
        + ", ".join(sorted(nn["player_name"].unique())))
    rj = v[v["namesakes_rejected"] > 0]
    for r in rj.itertuples():
        log(f"  namesake guard: {r.player_name} ({r.trade_date}) -> {r.status}")
    co = v[v["status"].str.contains("control over")]
    log(f"  past club control (worth zero): " + "; ".join(
        f"{r.player_name} ({int(r.draftYear)} #{int(r.pick)}, control ended {int(r.window_end)})" for r in co.itertuples()))

    v.drop(columns=[c for c in ("date",) if c in v.columns]).to_csv(OUTPUT_DIR / "prospect_values.csv", index=False)
    sv.to_csv(OUTPUT_DIR / "prospect_star_values.csv", index=False)
    (OUTPUT_DIR / "prospect_values_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nwrote prospect_values.csv, prospect_star_values.csv, prospect_values_log.txt in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
