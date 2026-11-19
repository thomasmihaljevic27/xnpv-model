"""
who_overpaid_any.py - who clubs overpay, with each yes-or-no characteristic taken from ANY player the club received, not
only its main player (Thomas, 2026-11-18: "I would be interested in seeing the results done without this rule and just if
they got that type of asset at all"; declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only,
exploratory, as who_overpaid.py part C.)

WHAT IT DOES. The rows, outcomes and measured characteristics are who_overpaid.build()'s: the same 735 club sides (all
trades), the overpay (minus the priced net), the loss on WAR and on Game Value (minus the outcome nets), production,
record above the forecast and games share of the main player. Only the eight yes-or-no characteristics change: each is 1
when any player the club received has it.

THE PLAYERS COUNTED: backtest_assets.csv player rows whose source starts "player model" or "buried" (the pool the main
player is chosen from in who_overpaid.build, backtest_cuts.py and clause_checks.py).

EACH PLAYER'S FACTS, by the rule the main player's use:
  age        birthdate (contract_level_spine.csv) to the trade date, in years of 365.25 days (backtest_cuts.py)
  position   the asset's pos (backtest_assets.csv)
  top-15     draft pick <= 15 in prospect_values.csv (who_overpaid.build: t["pick"] <= 15)
  left       the contract running at the page: the earliest-signed contract in the season spine at (nhl_id, page) signed
             on or before the trade date, else the earliest; pp_signed_end - page + 1, at least 1 (who_overpaid.build)
  ufa        that contract's signing status starts "UFA" (clause_checks.main_players)
  clause     backtest.py's own rule (line 1167): the player's (nhl_id, valuation_page) in traded_player_values.csv has a
             season-spine row with has_any_clause == 1. NOTE: backtest.py's g_clause, which every earlier script calls
             "main player with a clause", is ALREADY this any-player flag; the guard below checks it reproduces exactly.
A fact unknown for a player counts as "no" for him (a missing age, contract or pick cannot make a side's flag 1).

v1.4: two more columns, the trade-day grade and the Game Value loss on the declared window.

v1.2 (declared in the protocol before it was built; Thomas: "In the main player model it should look at the production and
etc of the main player acquired, and in the any player model it should be your recommended option"): each rule applied to
every characteristic. Main player rule: the clause too is the main player's (backtest.py's rule on him alone). Any player
rule: the yes-or-no flags as above; production and the record above the forecast are (v1.3) AVERAGES over the players
received, weighted by cap hit (v1.2 summed them);
the games share is their average weighted by cap hit. A player's missing production, forecast or games count is zero
(the rows stay the main-player fit's 735 sides). Guards 4 and 5: on one-player sides the averages equal the main player's
figures and the two clause flags agree; the main asset chosen here is who_overpaid.build's. Output who_overpaid_both.csv.

GUARDS: (1) the all-trades main-player fit reproduces who_overpaid.py's recorded figures (former top-15 pick +1.53 / +1.52);
(2) the any-player clause flag equals g_clause on every side; (3) on sides that received one player, each any-player flag
equals the main player's (age bands, defenceman, top-15, seasons left; ufa within clause_checks' rule).

OUTPUTS: OUTPUT_DIR/who_overpaid_any_log.txt, who_overpaid_any.csv
"""
import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "who_overpaid_any.py v1.4 (2026-11-18)"   # v1.4: the trade-day grade and Game Value columns on the declared window (the findings document moves to it); v1.3: the any player rule's measures as cap-weighted averages (Thomas: "Cap-weighted"); v1.2: each rule applied to every characteristic (the main player's clause; totals for the measures); v1.1: three more columns for the replications (Thomas made the any-player rule the main one)
DECLARED_END = "2022-03-28"
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def player_facts(CS, PST, SEASON_GAMES):
    """One row per player asset in the main-player pool, with the eight yes-or-no facts."""
    a = pd.read_csv(EXT / "backtest_assets.csv")
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "nhl_id", "cap_hit", "pick"]].drop_duplicates("asset_id")
    pl = a[(a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))].merge(pv, on="asset_id", how="left")
    pl["date"] = pd.to_datetime(pl["trade_date"])
    ls = pd.read_csv(OUTPUT_DIR / "contract_level_spine.csv", usecols=["nhl_id", "birthdate"]).drop_duplicates("nhl_id")
    pl["age"] = (pl["date"] - pd.to_datetime(pl["nhl_id"].map(ls.set_index("nhl_id")["birthdate"]))).dt.days / 365.25
    # the contract running at the page: seasons left and signing status
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False,
                     usecols=["nhl_id", "season_start", "contract_id", "pp_signed_end", "pp_signing_date", "has_any_clause"])
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    c, _ = CS.load_contracts()
    st = c.drop_duplicates("contract_id").set_index("contract_id")["signing_status"]
    left, ufa = [], []
    for r in pl.itertuples():
        g = by.get((r.nhl_id, int(r.valuation_page))) if pd.notna(r.nhl_id) and pd.notna(r.valuation_page) else None
        if g is None:
            left.append(np.nan); ufa.append(0); continue
        g = g[g["signed"] <= r.date] if (g["signed"] <= r.date).any() else g
        x = g.sort_values("signed").iloc[0]
        left.append(max(int(x["pp_signed_end"]) - int(r.valuation_page) + 1, 1))
        ufa.append(int(str(st.get(int(x["contract_id"]), "")).startswith("UFA")))
    pl["left"], pl["ufa"] = left, ufa
    # clause: backtest.py's rule, through traded_player_values' nhl_id and page
    cl = set((int(x), int(y)) for x, y, z in zip(ss["nhl_id"], ss["season_start"], ss["has_any_clause"]) if pd.notna(x) and z == 1)
    tpv = pd.read_csv(EXT / "traded_player_values.csv").set_index("asset_id")
    pl["clause"] = [int(x in tpv.index and pd.notna(tpv.at[x, "nhl_id"]) and (int(tpv.at[x, "nhl_id"]), int(tpv.at[x, "valuation_page"])) in cl)
                    for x in pl["asset_id"]]
    # v1.2: each player's measured facts, by who_overpaid.build's and clause_checks.main_players' rules
    w = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["Player", "nhl_id", "Season", "GP"]).dropna(subset=["nhl_id"])
    w["y"] = 2000 + w["Season"].str[:2].astype(int)
    gp = w.groupby(["nhl_id", "y"])["GP"].sum()
    pl["gp_share"] = [np.nan if pd.isna(n_) or pd.isna(p) else
                      min(float(gp.get((n_, int(p) - 1), 0.0)) / SEASON_GAMES.get(int(p) - 1, 82), 1.0)
                      for n_, p in zip(pl["nhl_id"], pl["valuation_page"])]
    ck = w[["Player", "nhl_id"]].dropna().drop_duplicates("nhl_id").set_index("nhl_id")["Player"].map(PST.career_key)
    fc = pd.read_csv(OUTPUT_DIR / "xnpv1_forecasts.csv", usecols=["career_key", "page", "h", "p_play", "war_if_plays"])
    fc = fc[fc["h"] == 0].set_index(["career_key", "page"])
    ex = []
    for r in pl.itertuples():
        k = (ck.get(r.nhl_id), int(r.valuation_page)) if pd.notna(r.nhl_id) else None
        ex.append(float(fc.at[k, "p_play"] * fc.at[k, "war_if_plays"]) if k is not None and k in fc.index else np.nan)
    pl["expected_war"] = ex
    f = pd.DataFrame({"trade_id": pl["trade_id"], "club": pl["acquiring_team"], "asset_id": pl["asset_id"]})
    f["cap_hit"], f["trailing_war"], f["expected_war"], f["gp_share"] = pl["cap_hit"], pl["trailing_war"], pl["expected_war"], pl["gp_share"]
    f["age28"] = pl["age"].between(28, 32, inclusive="left").astype(int)
    f["age32"] = (pl["age"] >= 32).astype(int)
    f["defence"] = (pl["pos"] == "D").astype(int)
    f["clause"] = pl["clause"]
    f["ufa"] = pl["ufa"]
    f["left2"] = (pl["left"] == 2).astype(int)
    f["left3"] = (pl["left"] >= 3).astype(int)
    f["top15"] = (pl["pick"] <= 15).astype(int)
    return f


def main():
    log(SCRIPT_VERSION)
    spec = importlib.util.spec_from_file_location("who_overpaid", Path(__file__).resolve().parent / "who_overpaid.py")
    WO = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(WO)
    CC = WO.load("clause_checks")
    GC, t = WO.build()
    key = ["trade_id", "club"]
    real = pd.read_csv(EXT / "backtest_sides.csv")[key + ["real_net_M"]]
    t = t.merge(real, on=key, how="left")

    flags = ["age28", "age32", "defence", "clause", "ufa", "left2", "left3", "top15"]
    meas = ["trailing_war", "rep_gap", "gp_share_last"]
    labels = {"age28": "aged 28 to 31", "age32": "aged 32 or over", "defence": "defenceman", "clause": "a clause",
              "ufa": "signed as a free agent", "left2": "two seasons left", "left3": "three or more seasons left",
              "top15": "former top-15 pick", "trailing_war": "production (trailing WAR total)",
              "rep_gap": "record above the forecast (WAR)", "gp_share_last": "games share, most recent season"}
    cc = ["age28", "age32", "defence", "clause", "ufa", "left2", "left3", "trailing_war", "rep_gap", "gp_share_last", "top15"]
    d = t[t["name"].notna()].dropna(subset=cc + ["age"]).copy()
    d["overpay"], d["loss"], d["loss_gv"], d["loss_played"] = -d["net_M"], -d["out_net_M"], -d["gv_net_M"], -d["real_net_M"]

    # GUARD 1: the main-player fit is who_overpaid.py's
    m = sm.OLS(d["overpay"], sm.add_constant(d[cc])).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
    m2 = sm.OLS(d["loss"], sm.add_constant(d[cc])).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
    assert abs(m.params["top15"] - 1.53) < 0.005 and abs(m2.params["top15"] - 1.52) < 0.005, (m.params["top15"], m2.params["top15"])
    log(f"  check 1: the main-player fit gives who_overpaid.py's figures back ({len(d)} sides; top-15 +1.53 / +1.52) (PASS)")

    f = player_facts(CC.CS, CC.PST, WO.SEASON_GAMES)
    anyf = f.groupby(key)[flags].max()
    nrec = f.groupby(key).size().rename("n_players")
    d = d.join(anyf.add_prefix("any_"), on=key).join(nrec, on=key)
    # GUARD 2: the clause flag is backtest.py's g_clause, side by side
    gcl = t.set_index(key)["t_clause"].astype(int)
    assert (d.set_index(key)["any_clause"] == gcl.reindex(d.set_index(key).index)).all()
    log(f"  check 2: the any-player clause flag equals backtest.py's g_clause on all {len(d)} sides (PASS): the clause was "
        f"already any player received")
    # GUARD 3: sides with one player received: any-player flag = main player's
    one = d[d["n_players"] == 1]
    bad = {c: int((one[f"any_{c}"] != one[c]).sum()) for c in flags}
    log(f"  check 3: sides with one player received ({len(one)}): any-player flag differs from the main player's: {bad}")
    assert all(v == 0 for k, v in bad.items() if k not in ("ufa",)), bad
    log(f"  sides with two or more players received: {int((d['n_players'] >= 2).sum())} of {len(d)}")
    dw = d[d["trade_date"] <= DECLARED_END]
    log(f"  declared window (v1.4): {int((dw['n_players'] >= 2).sum())} of {len(dw)} sides with two or more players received; "
        f"{dw['trade_id'].nunique()} trades")
    log("\n  clubs flagged: main player -> any player received")
    for c in flags:
        log(f"    {labels[c]:<32}{int(d[c].sum()):>5} -> {int(d[f'any_{c}'].sum()):>5}")

    # ---- the regression, both rules ---------------------------------------------------------------------------------------
    cc_any = [f"any_{c}" if c in flags else c for c in cc]
    cols = [("overpay", "all trades", d["trade_id"].notna(), "overpay"),
            ("loss, WAR", "all trades", d["trade_id"].notna(), "loss"),
            ("loss, Game Value", "all trades", d["trade_id"].notna(), "loss_gv"),
            ("loss, WAR, 2017-22 played", "declared", d["trade_date"] <= DECLARED_END, "loss_played"),
            ("loss, WAR, after 2022", "after", d["trade_date"] > DECLARED_END, "loss"),
            # v1.1: the replications the writeup reports beside the main table
            ("overpay, after 2022", "after", d["trade_date"] > DECLARED_END, "overpay"),
            ("loss, WAR, 2017-22", "declared", d["trade_date"] <= DECLARED_END, "loss"),
            ("loss, WAR, played, all trades", "all trades", d["trade_id"].notna(), "loss_played"),
            # v1.4: the findings document reports the declared window throughout (protocol amendment 2026-11-18)
            ("overpay, 2017-22", "declared", d["trade_date"] <= DECLARED_END, "overpay"),
            ("loss, Game Value, 2017-22", "declared", d["trade_date"] <= DECLARED_END, "loss_gv")]
    log("\nWHO IS OVERPAID: main player -> any player received ($M a side, positive = paid more / lost more; * = p < 0.05, "
        "clustered by trade)")
    log(f"  {'characteristic':<34}" + "".join(f"{c[0]:>30}" for c in cols))
    fits = {}
    for lab, scope, msk, y in cols:
        dd = d[msk]
        for rule, xs in (("main", cc), ("any", cc_any)):
            fits[(lab, rule)] = sm.OLS(dd[y], sm.add_constant(dd[xs])).fit(cov_type="cluster", cov_kwds={"groups": dd["trade_id"]})
    for c in cc:
        cells = []
        for lab, scope, msk, y in cols:
            a_, b_ = fits[(lab, "main")], fits[(lab, "any")]
            ca = f"any_{c}" if c in flags else c
            s1 = f"{a_.params[c]:+.2f}{'*' if a_.pvalues[c] < 0.05 else ' '}"
            s2 = f"{b_.params[ca]:+.2f}{'*' if b_.pvalues[ca] < 0.05 else ' '} (p={b_.pvalues[ca]:.3f})"
            cells.append(f"{s1} -> {s2}")
            OUT.append({"term": labels[c], "column": lab, "n": int(b_.nobs), "main": a_.params[c], "main_p": a_.pvalues[c],
                        "any": b_.params[ca], "any_se": b_.bse[ca], "any_p": b_.pvalues[ca]})
        log(f"  {labels[c]:<34}" + "".join(f"{x:>30}" for x in cells))
    log("  (sides: all trades " + str(len(d)) + "; 2017-22 " + str(int((d['trade_date'] <= DECLARED_END).sum())) + "; after 2022 "
        + str(int((d['trade_date'] > DECLARED_END).sum())) + ")")
    # ---- v1.2: each rule applied to every characteristic --------------------------------------------------------------
    main_a = f.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(key).set_index(key)
    di = d.set_index(key)
    assert (main_a["asset_id"].reindex(di.index) == di["asset_id"]).all()          # GUARD 5a: the same main asset
    d["main_clause"] = main_a["clause"].reindex(di.index).fillna(0).astype(int).values
    g = f.assign(tw=f["trailing_war"].fillna(0), gap=f["trailing_war"].fillna(0) - f["expected_war"].fillna(0),
                 gs=f["gp_share"].fillna(0), cw=f["cap_hit"].fillna(0))
    # v1.3: each measure the cap-weighted average over the players received (the plain average where no cap hit is known)
    for c in ("tw", "gap", "gs"):
        g[f"cw_{c}"] = g["cw"] * g[c]
    tot = g.groupby(key).agg(cw=("cw", "sum"), cw_tw=("cw_tw", "sum"), cw_gap=("cw_gap", "sum"), cw_gs=("cw_gs", "sum"),
                             m_tw=("tw", "mean"), m_gap=("gap", "mean"), m_gs=("gs", "mean"))
    den = tot["cw"].where(tot["cw"] > 0, 1)
    for c, out in (("tw", "avg_war"), ("gap", "avg_gap"), ("gs", "avg_gs")):
        tot[out] = np.where(tot["cw"] > 0, tot[f"cw_{c}"] / den, tot[f"m_{c}"])
    d = d.join(tot[["avg_war", "avg_gap", "avg_gs"]], on=key)
    one = d[d["n_players"] == 1]
    dif = {"production": float((one["avg_war"] - one["trailing_war"]).abs().max()), "record": float((one["avg_gap"] - one["rep_gap"]).abs().max()),
           "games share": float((one["avg_gs"] - one["gp_share_last"]).abs().max()), "clause": int((one["main_clause"] != one["any_clause"]).sum())}
    log(f"\n  check 4 (v1.3): one-player sides ({len(one)}): largest gap, averages against the main player's figures, and clause flags differing: {dif}")
    assert max(dif["production"], dif["record"], dif["games share"]) < 1e-9 and dif["clause"] == 0, dif
    log("  (PASS)")
    log(f"  clubs with a clause: main player {int(d['main_clause'].sum())}, any player {int(d['any_clause'].sum())}")
    cc_m = [("main_clause" if c == "clause" else c) for c in cc]
    cc_a = [f"any_{c}" if c in flags else {"trailing_war": "avg_war", "rep_gap": "avg_gap", "gp_share_last": "avg_gs"}.get(c, c) for c in cc]
    both = []
    log("\nWHO IS OVERPAID, EACH RULE ON EVERY CHARACTERISTIC (v1.3, cap-weighted averages): main player rule | any player rule; estimate (se) p")
    log(f"  {'characteristic':<34}" + "".join(f"{c[0]:>30}" for c in cols))
    fit2 = {}
    for lab, scope, msk, y in cols:
        dd = d[msk]
        for rule, xs in (("main", cc_m), ("any", cc_a)):
            fit2[(lab, rule)] = sm.OLS(dd[y], sm.add_constant(dd[xs])).fit(cov_type="cluster", cov_kwds={"groups": dd["trade_id"]})
    for i, c in enumerate(cc):
        for rule, xs in (("main", cc_m), ("any", cc_a)):
            cells = []
            for lab, scope, msk, y in cols:
                m_ = fit2[(lab, rule)]
                k = xs[i]
                cells.append(f"{m_.params[k]:+.2f} ({m_.bse[k]:.2f}) p={m_.pvalues[k]:.3f}")
                both.append({"term": labels[c], "rule": rule, "column": lab, "n": int(m_.nobs), "estimate": m_.params[k],
                             "se": m_.bse[k], "p": m_.pvalues[k]})
            log(f"  {(labels[c] if rule == 'main' else ''):<26}{rule:>8}" + "".join(f"{x:>30}" for x in cells))
    pd.DataFrame(both).to_csv(OUTPUT_DIR / "who_overpaid_both.csv", index=False)
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "who_overpaid_any.csv", index=False)
    (OUTPUT_DIR / "who_overpaid_any_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
