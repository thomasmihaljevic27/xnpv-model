"""
traits_test.py - handedness, size, playoff performance and birthplace in the who-is-overpaid regression (Thomas,
2026-11-18: "I want to see handedness, size, playoff performance, and European or not"; "Both terms", "Height and
weight", "Fetch spring 2017"; declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only.)

ROWS: who_overpaid_any.py v1.4's club sides in the declared window (trades to 2022-03-28), with its characteristics under
both rules, rebuilt here the same way (who_overpaid.build(), who_overpaid_any.player_facts(), v1.3's cap-weighted
averages). GUARD 1: on those rows the fit without the new terms reproduces who_overpaid_both.csv's declared-window
coefficients (trade-day grade and realized WAR) for every term under both rules.

EACH PLAYER'S NEW FACTS, by his NHL id (PuckPedia's contract export through contract_source.load_contracts(); one value a
player, GUARD 2: no player has two different values):
  right shot          shoots == "right" (a goalie or a player with no recorded side counts as no)
  right-shot D        right shot and the asset's position D (backtest_assets.csv pos)
  height              inches;  weight: per 10 lb
  born in Europe      country (birth country) neither Canada nor USA; unknown counts as no
  playoff points      points in the most recent NHL playoffs completed before the trade date, zero if he played no game
                      in them. 2018-2022 playoffs: nhl_gamelogs.sqlite skater_games joined to games with game_type 3,
                      completed = the season's last playoff game date. 2017 playoffs: the NHL stats API's skater summary
                      (10_SOURCE/raw/nhl_api_playoff_skaters_20162017.json), completed 2017-06-11 (the Cup final's game
                      6). GUARD 3: the API's 2017-18 playoff points (nhl_api_playoff_skaters_20172018.json) equal the
                      game logs' for every player.
RULES: main player rule, the main player's facts; any player rule, the yes-or-no facts are 1 when any player received has
them, and height, weight and playoff points are cap-weighted averages over the players received whose figure is known.

REPORTS ($M a club, positive = the club gained, clustered by trade), outcomes: trade-day grade (net_M), realized value on
WAR (out_net_M), on Game Value (gv_net_M), on the seasons played only (real_net_M):
  1 each new term alone (the outcome on that one term)
  2 every new term added to the Section 3 regression together; the clause, age 28 to 31 and defenceman coefficients in that
    fit beside the base fit on the same rows

OUTPUTS: OUTPUT_DIR/traits_test_log.txt, traits_test.csv
"""
import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
GAMELOG_DB = Path(os.environ["GAMELOG_DB"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "traits_test.py v1.1 (2026-11-18)"   # v1.1: the rows built in frame(), shared with age_band_test.py; results unchanged
DECLARED_END = "2022-03-28"
PLAYOFFS_2017_END = pd.Timestamp("2017-06-11")
LOG, OUT = [], []
YS = [("trade-day grade", "net_M"), ("realized value, WAR", "out_net_M"), ("realized value, Game Value", "gv_net_M"),
      ("realized value, seasons played", "real_net_M")]
NEW = ["rshot", "rshot_d", "height", "weight10", "europe", "playoff_pts"]
NEW_FLAGS = ["rshot", "rshot_d", "europe"]
LABEL = {"rshot": "right shot", "rshot_d": "right-shot defenceman", "height": "height, each inch",
         "weight10": "weight, each 10 lb", "europe": "born in Europe", "playoff_pts": "playoff points, most recent playoffs",
         "clause": "a clause", "age28": "aged 28 to 31", "defence": "defenceman"}


def log(s=""):
    print(s)
    LOG.append(s)


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fit(d, y, xs):
    return sm.OLS(d[y], sm.add_constant(d[xs])).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})


def playoff_points():
    """(nhl_id, season start year) -> playoff points, and each season's playoff end date."""
    con = sqlite3.connect(GAMELOG_DB)
    g = pd.read_sql("SELECT s.player_id, g.season, g.game_date, s.points FROM skater_games s JOIN games g "
                    "ON s.game_id = g.game_id WHERE g.game_type = 3", con)
    con.close()
    g["y"] = g["season"].astype(str).str[:4].astype(int)
    pts = g.groupby(["player_id", "y"])["points"].sum()
    ends = pd.to_datetime(g.groupby("y")["game_date"].max())
    api = {}
    for s in ("20162017", "20172018"):
        j = json.loads((SOURCE_DIR / "raw" / f"nhl_api_playoff_skaters_{s}.json").read_text(encoding="utf8"))
        api[int(s[:4])] = pd.Series({int(r["playerId"]): int(r["points"]) for r in j["data"]})
    # GUARD 3: the API's 2017-18 playoffs equal the game logs' for every player
    gl = pts.xs(2017, level="y")
    both = api[2017].index.union(gl.index)
    diff = (api[2017].reindex(both).fillna(0) - gl.reindex(both).fillna(0)).abs()
    assert diff.max() == 0, diff[diff > 0].head()
    log(f"  check 3: the API's 2017-18 playoff points equal the game logs' for all {len(both)} players (PASS)")
    for k, v in api[2016].items():
        pts.loc[(k, 2016)] = v
    ends.loc[2016] = PLAYOFFS_2017_END
    return pts, ends.sort_index()


def frame():
    """who_overpaid_any.py v1.4's declared-window rows, both rules, with guard 1 (v1.1: shared with age_band_test.py)."""
    WO = load("who_overpaid")
    WA = load("who_overpaid_any")
    CC = WO.load("clause_checks")
    GC, t = WO.build()
    key = ["trade_id", "club"]
    t = t.merge(pd.read_csv(EXT / "backtest_sides.csv")[key + ["real_net_M"]], on=key, how="left")
    # ---- who_overpaid_any.py v1.4's rows and characteristics (its main(), unchanged) ----
    flags = ["age28", "age32", "defence", "clause", "ufa", "left2", "left3", "top15"]
    cc = ["age28", "age32", "defence", "clause", "ufa", "left2", "left3", "trailing_war", "rep_gap", "gp_share_last", "top15"]
    d = t[t["name"].notna()].dropna(subset=cc + ["age"]).copy()
    f = WA.player_facts(CC.CS, CC.PST, WO.SEASON_GAMES)
    d = d.join(f.groupby(key)[flags].max().add_prefix("any_"), on=key).join(f.groupby(key).size().rename("n_players"), on=key)
    main_a = f.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(key).set_index(key)
    di = d.set_index(key)
    assert (main_a["asset_id"].reindex(di.index) == di["asset_id"]).all()
    d["main_clause"] = main_a["clause"].reindex(di.index).fillna(0).astype(int).values
    g = f.assign(tw=f["trailing_war"].fillna(0), gap=f["trailing_war"].fillna(0) - f["expected_war"].fillna(0),
                 gs=f["gp_share"].fillna(0), cw=f["cap_hit"].fillna(0))
    for c in ("tw", "gap", "gs"):
        g[f"cw_{c}"] = g["cw"] * g[c]
    tot = g.groupby(key).agg(cw=("cw", "sum"), cw_tw=("cw_tw", "sum"), cw_gap=("cw_gap", "sum"), cw_gs=("cw_gs", "sum"),
                             m_tw=("tw", "mean"), m_gap=("gap", "mean"), m_gs=("gs", "mean"))
    den = tot["cw"].where(tot["cw"] > 0, 1)
    for c, out in (("tw", "avg_war"), ("gap", "avg_gap"), ("gs", "avg_gs")):
        tot[out] = np.where(tot["cw"] > 0, tot[f"cw_{c}"] / den, tot[f"m_{c}"])
    d = d.join(tot[["avg_war", "avg_gap", "avg_gs"]], on=key)
    cc_m = [("main_clause" if c == "clause" else c) for c in cc]
    cc_a = [f"any_{c}" if c in flags else {"trailing_war": "avg_war", "rep_gap": "avg_gap", "gp_share_last": "avg_gs"}.get(c, c) for c in cc]
    d = d[d["trade_date"] <= DECLARED_END].copy()
    log(f"  declared window: {len(d)} club sides, {d['trade_id'].nunique()} trades")
    # GUARD 1: the base fits reproduce who_overpaid_both.csv (its sign: overpay = -net, loss = -outcome)
    both = pd.read_csv(OUTPUT_DIR / "who_overpaid_both.csv")
    for rule, xs in (("main", cc_m), ("any", cc_a)):
        for col, y in (("overpay, 2017-22", "net_M"), ("loss, WAR, 2017-22", "out_net_M"), ("loss, Game Value, 2017-22", "gv_net_M")):
            m = fit(d, y, xs)
            ref = both[(both["rule"] == rule) & (both["column"] == col)].set_index("term")["estimate"]
            got = pd.Series(-m.params[xs].values, index=ref.index)       # who_overpaid_both lists terms in cc's order
            assert np.allclose(got.values, ref.values, atol=1e-9), (rule, col)
    log("  check 1: the base fits reproduce who_overpaid_any.py v1.4's declared-window coefficients, both rules (PASS)")
    return WO, CC, d, f, key, flags, cc, cc_m, cc_a


def main():
    log(SCRIPT_VERSION)
    WO, CC, d, f, key, flags, cc, cc_m, cc_a = frame()
    # ---- the new facts, a player at a time ----
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "nhl_id"]].drop_duplicates("asset_id")
    a = pd.read_csv(EXT / "backtest_assets.csv")[["asset_id", "pos", "trade_date"]].drop_duplicates("asset_id")
    f = f.merge(pv, on="asset_id", how="left").merge(a, on="asset_id", how="left")
    c, _ = CC.CS.load_contracts()
    bio = c[["nhl_id", "shoots", "height", "weight", "country"]].dropna(subset=["nhl_id"])
    bio["nhl_id"] = bio["nhl_id"].astype(int)
    nun = bio.groupby("nhl_id")[["shoots", "height", "weight", "country"]].nunique()
    assert (nun <= 1).all().all(), nun[(nun > 1).any(axis=1)].head()                 # GUARD 2: one value a player
    log(f"  check 2: PuckPedia gives one shooting side, height, weight and birth country a player ({len(nun)} players) (PASS)")
    bio = bio.groupby("nhl_id").first()
    nid = f["nhl_id"].astype("Int64")
    f["rshot"] = (nid.map(bio["shoots"]).astype(str).str.lower() == "right").astype(int).values
    f["rshot_d"] = ((f["rshot"] == 1) & (f["pos"] == "D")).astype(int)
    f["height"] = pd.to_numeric(nid.map(bio["height"]), errors="coerce").values
    f["weight10"] = pd.to_numeric(nid.map(bio["weight"]), errors="coerce").values / 10
    ctry = nid.map(bio["country"])
    f["europe"] = (ctry.notna() & ~ctry.isin(["Canada", "USA"])).astype(int).values
    pts, ends = playoff_points()
    td = pd.to_datetime(f["trade_date"])
    last = [int(ends.index[ends < x].max()) if (ends < x).any() else np.nan for x in td]   # most recent completed playoffs
    f["playoff_pts"] = [np.nan if pd.isna(n) or pd.isna(y) else float(pts.get((int(n), int(y)), 0)) for n, y in zip(nid, last)]
    log(f"  players received: {len(f)}; known: right shot side {int(nid.map(bio['shoots']).notna().sum())}, height "
        f"{int(f['height'].notna().sum())}, birth country {int(ctry.notna().sum())}, playoff points {int(f['playoff_pts'].notna().sum())}")
    log(f"  most recent playoffs used, by season: {pd.Series(last).value_counts().sort_index().to_dict()}")

    # main player rule: the main player's facts; any player rule: flags = any, measures = cap-weighted over known figures
    mf = f.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(key).set_index(key)
    for k in NEW:
        d[f"m_{k}"] = mf[k].reindex(d.set_index(key).index).values
    anyf = f.groupby(key)[NEW_FLAGS].max()
    for k in NEW_FLAGS:
        d[f"a_{k}"] = anyf[k].reindex(d.set_index(key).index).fillna(0).values
    for k in ("height", "weight10", "playoff_pts"):
        h = f[f[k].notna()].assign(w=lambda x: x["cap_hit"].fillna(0), wx=lambda x: x["cap_hit"].fillna(0) * x[k])
        s = h.groupby(key).agg(w=("w", "sum"), wx=("wx", "sum"), mx=(k, "mean"))
        avg = pd.Series(np.where(s["w"] > 0, s["wx"] / s["w"].where(s["w"] > 0, 1), s["mx"]), index=s.index)
        d[f"a_{k}"] = avg.reindex(d.set_index(key).index).values
    one = d[d["n_players"] == 1]
    gap = {k: float((one[f"m_{k}"].fillna(-99) - one[f"a_{k}"].fillna(-99)).abs().max()) for k in NEW}
    assert max(gap.values()) < 1e-9, gap                                                   # GUARD 4: one player, same facts
    log(f"  check 4: on the {len(one)} sides with one player received, each new fact is the same under both rules (PASS)")
    nm, na = [f"m_{k}" for k in NEW], [f"a_{k}" for k in NEW]
    r = d.dropna(subset=nm + na)
    log(f"  sides with every new fact known: {len(r)} of {len(d)} ({r['trade_id'].nunique()} trades)")
    log("  share of sides, main player rule: " + "; ".join(
        f"{LABEL[k]} {r[f'm_{k}'].mean():.2f}" if k in NEW_FLAGS else f"{LABEL[k]} mean {r[f'm_{k}'].mean():.1f}" for k in NEW))

    # ---- 1 alone ----
    log("\n1. EACH NEW TERM ALONE (outcome on that term; $M a club, positive = gained; clustered by trade)")
    for rule, pre in (("main player rule", "m_"), ("any player rule", "a_")):
        log(f"  {rule}")
        for k in NEW:
            cells = []
            for ylab, y in YS:
                m = fit(r, y, [pre + k])
                cells.append(f"{m.params[pre + k]:+.2f} ({m.bse[pre + k]:.2f}) p={m.pvalues[pre + k]:.3f}")
                OUT.append({"part": "alone", "rule": rule, "term": LABEL[k], "outcome": ylab, "n": int(m.nobs),
                            "estimate": m.params[pre + k], "se": m.bse[pre + k], "p": m.pvalues[pre + k]})
            log(f"    {LABEL[k]:<38}" + "".join(f"{x:>28}" for x in cells))
    # ---- 2 together, with the Section 3 regression's characteristics ----
    log("\n2. ADDED TOGETHER TO THE SECTION 3 REGRESSION (every existing characteristic held)")
    log(f"  {'':<40}" + "".join(f"{y:>28}" for y, _ in YS))
    for rule, base, pre in (("main player rule", cc_m, "m_"), ("any player rule", cc_a, "a_")):
        log(f"  {rule}")
        xs = base + [pre + k for k in NEW]
        fits = {y: fit(r, y, xs) for _, y in YS}
        bfits = {y: fit(r, y, base) for _, y in YS}
        for k in NEW:
            cells = []
            for ylab, y in YS:
                m = fits[y]
                cells.append(f"{m.params[pre + k]:+.2f} ({m.bse[pre + k]:.2f}) p={m.pvalues[pre + k]:.3f}")
                OUT.append({"part": "together", "rule": rule, "term": LABEL[k], "outcome": ylab, "n": int(m.nobs),
                            "estimate": m.params[pre + k], "se": m.bse[pre + k], "p": m.pvalues[pre + k]})
            log(f"    {LABEL[k]:<38}" + "".join(f"{x:>28}" for x in cells))
        log("    the findings, base fit -> with the new terms (same rows):")
        for k in ("clause", "age28", "defence"):
            bk = base[cc.index(k)]
            cells = []
            for ylab, y in YS:
                b0, m = bfits[y], fits[y]
                cells.append(f"{b0.params[bk]:+.2f} -> {m.params[bk]:+.2f} p={m.pvalues[bk]:.3f}")
                OUT.append({"part": "findings with the new terms", "rule": rule, "term": LABEL[k], "outcome": ylab, "n": int(m.nobs),
                            "base": b0.params[bk], "estimate": m.params[bk], "se": m.bse[bk], "p": m.pvalues[bk]})
            log(f"    {LABEL[k]:<38}" + "".join(f"{x:>28}" for x in cells))
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "traits_test.csv", index=False)
    (OUTPUT_DIR / "traits_test_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
