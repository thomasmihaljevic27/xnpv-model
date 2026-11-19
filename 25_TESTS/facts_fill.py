"""
facts_fill.py - fills the player facts that left trades out of one_regression.py (Thomas, 2026-11-19: "Go and try to
reconcile this. I want as many usable trades in the sample as possible"; the rules declared in
40_DOCS/Backtest_Protocol.md, "Recovering the trades the one regression left out", before this was built).

fill(t, f, WO, CC, log) takes who_overpaid.build()'s club sides t and who_overpaid_any.player_facts()'s players f and
returns them with each missing fact filled, every known fact left as it was:
  name        backtest_assets' war_spelling, else page_2017_values' war_name, else the asset's name
  NHL id      prospect_values (f's), else traded_player_values, else page_2017_values
  birthdate   by NHL id (contract_level_spine, WAR_with_age, goalie_birthdates), else by name (WAR_with_age, goalie
              birthdates), one value required
  recent WAR  backtest.trailing_total on backtest.seasons_for(name) (goalies: the goalie WAR table); none: 0
  forecast    skaters, the player model's h = 0 forecast at the page (xnpv1_forecasts.csv, and page 2017 fitted here by
              skater_forecast.ContractForecaster into xnpv1_forecasts_2017.csv); goalies, goalie_value_spine_v2's
              forecast_war at the page; none: 0
  games share the season before the page: WAR_with_age by NHL id (who_overpaid's rule), else the WAR table by name
              (goalies: the goalie table); none: 0
  seasons left 2017 page with no spine row: page_2017_values' contract_last_season - 2017 + 1
GUARDS: each rule reproduces every value already known (recent WAR, forecast, games share, the age bands); the page 2018
forecast refitted here reproduces xnpv1_forecasts.csv's.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
ROOT = Path(__file__).resolve().parent.parent
FILL_VERSION = "facts_fill.py v1.2 (2026-11-19)"   # v1.2: missing positions filled, a goalie flag; v1.1: games share by recovered NHL id; goalies from the goalie table


def forecasts(CC, log):
    """(career_key, page) -> the h = 0 expected WAR, pages 2017-2025 (2017 fitted here, cached)."""
    fc = pd.read_csv(OUTPUT_DIR / "xnpv1_forecasts.csv", usecols=["career_key", "page", "h", "p_play", "war_if_plays"])
    fc = fc[fc["h"] == 0]
    path17 = OUTPUT_DIR / "xnpv1_forecasts_2017.csv"
    if not path17.exists():
        sys.path.insert(0, str(ROOT / "20_CODE"))
        import skater_forecast as SF
        cf = SF.ContractForecaster()
        # GUARD: this route refits page 2018 to the saved forecasts
        p18 = cf.page(2018)[2].reset_index()
        p18 = p18[p18["h"] == 0].set_index("career_key")
        s18 = fc[fc["page"] == 2018].set_index("career_key")
        both = s18.index.intersection(p18.index)
        assert len(both) == len(s18) and np.allclose(p18.loc[both, "war_if_plays"], s18.loc[both, "war_if_plays"]) \
            and np.allclose(p18.loc[both, "p_play"], s18.loc[both, "p_play"]), "page 2018 refit"
        log(f"  fill: page 2018 refitted here reproduces xnpv1_forecasts.csv for all {len(both)} players (PASS)")
        p17 = cf.page(2017)[2].reset_index()
        p17 = p17[p17["h"] == 0].assign(page=2017)[["career_key", "page", "h", "p_play", "war_if_plays"]]
        p17.to_csv(path17, index=False)
        log(f"  fill: page 2017 forecast fitted, {len(p17)} players, written to {path17.name}")
    else:
        p17 = pd.read_csv(path17)
        log(f"  fill: page 2017 forecast read from {path17.name} ({len(p17)} players)")
    fc = pd.concat([fc, p17], ignore_index=True)
    return (fc["p_play"] * fc["war_if_plays"]).groupby([fc["career_key"], fc["page"]]).first()


def fill(t, f, WO, CC, log):
    log(f"  {FILL_VERSION}")
    sys.path.insert(0, str(ROOT / "20_CODE"))
    import backtest as BT
    PV, PST = BT.PV, CC.PST
    key = ["trade_id", "club"]
    a = pd.read_csv(EXT / "backtest_assets.csv").drop_duplicates("asset_id").set_index("asset_id")
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False).drop_duplicates("asset_id").set_index("asset_id")["nhl_id"]
    tpv = pd.read_csv(EXT / "traded_player_values.csv").drop_duplicates("asset_id").set_index("asset_id")["nhl_id"]
    p17 = pd.read_csv(EXT / "page_2017_values.csv").drop_duplicates("asset_id").set_index("asset_id")
    p = f.copy()
    for c in ("war_spelling", "name", "pos", "valuation_page", "trade_date", "trailing_war"):
        p["a_" + c] = p["asset_id"].map(a[c])
    p["spell"] = p["a_war_spelling"].fillna(p["asset_id"].map(p17["war_name"])).fillna(p["a_name"])
    p["nid"] = p["asset_id"].map(pv).fillna(p["asset_id"].map(tpv)).fillna(p["asset_id"].map(p17["nhl_id"]))
    # v1.2 (protocol b309c1e): a missing position, from page_2017_values, PuckPedia by NHL id, WAR_with_age by name, else
    # goalie when the name is only in the goalie WAR table; known positions unchanged
    known_pos = p["a_pos"].notna()
    pos = p["a_pos"].copy()
    pos = pos.fillna(p["asset_id"].map(p17["position"]))
    cpos = CC.CS.load_contracts()[0][["nhl_id", "position"]].dropna().drop_duplicates("nhl_id")
    pp = cpos.set_index(cpos["nhl_id"].astype(int))["position"].map(
        {"Defense": "D", "Center": "F", "Left Wing": "F", "Right Wing": "F", "Goaltender": "G"})
    pos = pos.fillna(pd.Series([pp.get(int(i)) if pd.notna(i) else None for i in p["nid"]], index=p.index))
    wp = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["Player", "Position"]).dropna()
    wp = wp.assign(n=wp["Player"].map(PV.norm)).groupby("n")["Position"].agg(lambda x: x.unique())
    wp = {k: v[0] for k, v in wp.items() if len(v) == 1}
    pos = pos.fillna(p["spell"].map(lambda s: wp.get(PV.norm(s))))
    gnames = set(BT.TABLES[True].index.get_level_values(0))
    pos = pos.fillna(p["spell"].map(lambda s: "G" if PV.norm(s) in gnames else None))
    assert (pos[known_pos] == p.loc[known_pos, "a_pos"]).all()                     # GUARD: known positions unchanged
    log(f"  fill: positions missing {int((~known_pos).sum())}, filled {int((~known_pos & pos.notna()).sum())} "
        f"({pos[~known_pos].value_counts().to_dict()}), still unknown {int(pos.isna().sum())}")
    p["a_pos"] = pos
    p["pos"] = pos
    p["goalie"] = (pos == "G").astype(int)
    p["defence"] = (pos == "D").astype(int)
    p["gk"] = p["a_pos"] == "G"
    page = p["a_valuation_page"].astype(int)
    date = pd.to_datetime(p["a_trade_date"])

    # ---- birthdate and age ----
    bd_id = {}
    for path, idc, bdc in ((OUTPUT_DIR / "contract_level_spine.csv", "nhl_id", "birthdate"),
                           (OUTPUT_DIR / "WAR_with_age.csv", "nhl_id", "birthdate"),
                           (OUTPUT_DIR / "goalie_birthdates.csv", "nhl_id", "birthdate")):
        d = pd.read_csv(path, usecols=[idc, bdc]).dropna()
        for i, b in zip(d[idc], d[bdc]):
            bd_id.setdefault(int(i), b)
    w = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["Player", "birthdate"]).dropna()
    g = pd.read_csv(OUTPUT_DIR / "goalie_birthdates.csv", usecols=["goalie", "birthdate"]).dropna()
    by_name = {}
    for gk, d, nc in ((False, w, "Player"), (True, g, "goalie")):
        u = d.assign(n=d[nc].map(PV.norm)).groupby("n")["birthdate"].agg(lambda x: x.unique())
        by_name[gk] = {n: v[0] for n, v in u.items() if len(v) == 1}            # one value required
    bd = [bd_id.get(int(i)) if pd.notna(i) else None for i in p["nid"]]
    bd = [b if b is not None else by_name[gk].get(PV.norm(s)) for b, gk, s in zip(bd, p["gk"], p["spell"])]
    # dates are written "YYYY-MM-DD" or "YYYY-MM-DD 00:00:00" (WAR_with_age); the first ten characters are the date
    bds = pd.Series([None if b is None else str(b)[:10] for b in bd], index=p.index)
    p["age"] = (date - pd.to_datetime(bds, format="%Y-%m-%d")).dt.days / 365.25
    a28 = p["age"].between(28, 32, inclusive="left").astype(int)
    a32 = (p["age"] >= 32).astype(int)
    kn = p["age"].notna() & p["nid"].notna() & p["nid"].isin([i for i in bd_id])
    # GUARD: the age bands where player_facts knew the birthdate (contract_level_spine) are unchanged
    spine_ids = set(pd.read_csv(OUTPUT_DIR / "contract_level_spine.csv", usecols=["nhl_id", "birthdate"]).dropna()["nhl_id"].astype(int))
    sk = p["asset_id"].map(pv).isin(spine_ids)
    assert (a28[sk] == p.loc[sk, "age28"]).all() and (a32[sk] == p.loc[sk, "age32"]).all(), "age bands"
    p["age28"], p["age32"] = a28, a32

    # ---- recent WAR, games share ----
    tw, gps = [], []
    for r, pg in zip(p.itertuples(), page):
        s = BT.seasons_for(r.spell, bool(r.gk), r.a_name)
        tw.append(BT.trailing_total(s, pg))
        n = float(s.loc[pg - 1, "GP"]) if (pg - 1) in s.index else 0.0
        gps.append(min(n / WO.SEASON_GAMES.get(pg - 1, 82), 1.0))
    tw, gps = pd.Series(tw, index=p.index), pd.Series(gps, index=p.index)
    known_tw = p["a_trailing_war"].notna()
    assert np.allclose(tw[known_tw], p.loc[known_tw, "a_trailing_war"], equal_nan=False), "recent WAR rule"
    log(f"  fill check: the back-test's recent-WAR rule reproduces all {int(known_tw.sum())} known values (PASS)")
    p["trailing_war"] = p["a_trailing_war"].where(known_tw, tw).fillna(0.0)
    # games share (v1.1, protocol amendment 89d191a). Skaters: who_overpaid's value where it had one; else by the recovered
    # NHL id in WAR_with_age (who_overpaid's own rule); else the WAR table by name. Goalies: the goalie WAR table by name,
    # replacing who_overpaid's 0 (it read the skater table).
    wa = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["nhl_id", "Season", "GP"]).dropna(subset=["nhl_id"])
    wa["y"] = 2000 + wa["Season"].str[:2].astype(int)
    gp_id = wa.groupby(["nhl_id", "y"])["GP"].sum()
    ids_wa = set(wa["nhl_id"].astype(int))
    by_id = pd.Series([min(float(gp_id.get((i, pg - 1), 0.0)) / WO.SEASON_GAMES.get(pg - 1, 82), 1.0)
                       if pd.notna(i) and int(i) in ids_wa else np.nan for i, pg in zip(p["nid"], page)], index=p.index)
    known_gs = p["gp_share"].notna() & ~p["gk"]
    assert np.allclose(by_id[known_gs].fillna(-1), p.loc[known_gs, "gp_share"].where(by_id[known_gs].notna(), -1)), "games share"
    log(f"  fill check: games share by NHL id reproduces the {int((known_gs & by_id.notna()).sum())} known skater values (PASS)")
    sk = (~p["gk"]) & ~known_gs
    gk_old = p.loc[p["gk"], "gp_share"]
    p.loc[sk, "gp_share"] = by_id[sk].fillna(gps[sk])
    p.loc[p["gk"], "gp_share"] = gps[p["gk"]]
    log(f"  fill: skater games shares filled {int(sk.sum())} (by NHL id {int((sk & by_id.notna()).sum())}, by name "
        f"{int((sk & by_id.isna()).sum())}); goalies' read from the goalie table {int(p['gk'].sum())} (were 0 for "
        f"{int((gk_old == 0).sum())})")
    p["gp_share"] = p["gp_share"].fillna(0.0)

    # ---- forecast ----
    fx = forecasts(CC, log)
    gs = pd.read_csv(OUTPUT_DIR / "goalie_value_spine_v2.csv", usecols=["nhl_id", "full_name", "season_start", "forecast_war"])
    gs = gs.dropna(subset=["forecast_war"])
    g_id = gs.groupby(["nhl_id", "season_start"])["forecast_war"].first()
    g_nm = gs.assign(n=gs["full_name"].map(PV.norm)).groupby(["n", "season_start"])["forecast_war"].first()
    ex = []
    for r, pg in zip(p.itertuples(), page):
        if r.gk:
            v = g_id.get((int(r.nid), pg)) if pd.notna(r.nid) else None
            v = v if v is not None else g_nm.get((PV.norm(r.spell), pg))
        else:
            v = fx.get((PST.career_key(r.spell), pg))
        ex.append(np.nan if v is None else float(v))
    ex = pd.Series(ex, index=p.index)
    known_ex = p["expected_war"].notna()
    agree = np.isclose(ex[known_ex], p.loc[known_ex, "expected_war"])
    log(f"  fill check: the forecast by name reproduces {int(agree.sum())} of the {int(known_ex.sum())} known; the known values "
        f"are kept")
    p["expected_war"] = p["expected_war"].where(known_ex, ex).fillna(0.0)

    # ---- seasons left, 2017 page ----
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False, usecols=["nhl_id", "season_start"])
    have = set(zip(ss["nhl_id"].dropna().astype(int), ss["season_start"]))
    cls = p["asset_id"].map(p17["contract_last_season"])
    no_row = (page == 2017) & pd.Series([not (pd.notna(i) and (int(i), 2017) in have) for i in p["nid"]], index=p.index) & cls.notna()
    left = (cls - 2017 + 1).clip(lower=1)
    p.loc[no_row, "left2"] = (left[no_row] == 2).astype(int)
    p.loc[no_row, "left3"] = (left[no_row] >= 3).astype(int)
    log(f"  fill: players received {len(p)}; birthdate found {int(p['age'].notna().sum())}; recent WAR from the rule "
        f"{int((~known_tw).sum())} (of them none: {int((~known_tw & tw.isna()).sum())}); forecast added {int((~known_ex & ex.notna()).sum())}, "
        f"none {int((~known_ex & ex.isna()).sum())}; 2017 seasons left from page_2017_values {int(no_row.sum())}")

    # ---- the main player's facts on the sides (only where missing) ----
    m = p.set_index("asset_id")
    t = t.copy()
    mid = t["asset_id"]
    has = t["name"].notna() & mid.isin(m.index)
    pick = lambda c: mid.map(m[c])                                           # noqa: E731
    age_missing = has & t["age"].isna()
    t.loc[age_missing, "age"] = pick("age")[age_missing]
    t["age28"] = np.where(age_missing, t["age"].between(28, 32, inclusive="left").astype(float), t["age28"])
    t["age32"] = np.where(age_missing, (t["age"] >= 32).astype(float), t["age32"])
    for c, src in (("trailing_war", "trailing_war"), ("gp_share_last", "gp_share")):
        miss = has & t[c].isna()
        t.loc[miss, c] = pick(src)[miss]
    miss = has & t["rep_gap"].isna()
    t.loc[miss, "rep_gap"] = (t["trailing_war"] - pick("expected_war"))[miss]
    lmiss = has & t["left"].isna() & mid.map(no_row.set_axis(p["asset_id"])).fillna(False).astype(bool)
    t.loc[lmiss, "left2"] = pick("left2")[lmiss].astype(float)
    t.loc[lmiss, "left3"] = pick("left3")[lmiss].astype(float)
    global LAST
    LAST = p                                                               # the filled player table, for checks
    pmiss = has & t["pos"].isna()
    t.loc[pmiss, "pos"] = pick("pos")[pmiss]
    t["defence"] = (t["pos"] == "D").astype(float)
    t["goalie"] = (t["pos"] == "G").astype(float)
    p["pos_filled"] = (~known_pos).astype(int)
    f_out = p[list(f.columns) + ["goalie", "pos_filled"]]
    return t, f_out
