"""
groups_any.py - the five back-test categories built from one player, each with an any-player version (Thomas, 2026-11-18:
"yes check all other categories for the any player version"; declared in 40_DOCS/Backtest_Protocol.md before it was built.
Report only.)

THE FIVE (groups_clustered.py's flags built from one player, and their any-player versions):
  rental     one player: the main player (highest cap hit received) is in his final season, unrestricted at expiry, and
             the trade is in-season. Any: any player received is.
  age 28-31, age 32+, defenceman
             one player: the main player's age at the trade date / position. Any: any player received.
  new GM     one player: in a general manager's first 365 days, the highest-paid player the club SENT signed before the
             manager's first day (backtest_cuts_more.py cut GM). Any: any player sent did, the manager in his first 365 days.
Two of groups_clustered's categories are already any-player (the clause, backtest.py C6; a former top-15 pick below the
benchmark, backtest_cuts.py 5b) and seven are not about a player; none of them changes.

EACH PLAYER'S FACTS, as the one-player flags build them:
  players    backtest_assets.csv rows with asset_type "player" and source starting "player model" or "buried"
  age        contract_level_spine.csv birthdate to the trade date, years of 365.25 days (backtest_cuts.py)
  status     backtest_cuts.py's status(): the contract running at the page (season spine at (nhl_id, page), earliest
             signed on or before the trade date, else the earliest); the 2017 page from page_2017_values.csv; rights only
             is not a contract; a rental is "final season, unrestricted at expiry" and the trade in the regular season
  sender     from_team in a trade of three or more clubs, else the other club (backtest_cuts_more.load_sides)
  new GM     backtest_cuts_more_gm_sides.csv's new_gm (first 365 days) and days (the manager's start = trade date - days);
             a player sent counts when his contract's signing date is before that start
A fact unknown for a player counts as "no" for him.

GUARDS: (1) groups_clustered.sides() gives its recorded group sizes and means back (defenceman 181 sides, -0.99 priced,
declared window); (2) on sides with exactly one player received (one player sent, for the manager) each any-player flag
equals the one-player flag.

REPORTS, standard errors clustered by trade, beside the one-player figures:
  1 each group's mean trade-day grade and realized value (WAR, Game Value), declared window
  2 the outcome-on-price coefficient c (the group beyond its price), declared window, WAR and Game Value
  3 the joint regression (groups_clustered.py part 4's design), all trades, the five replaced together
  5 (v1.2) the joint regression with one rule throughout, declared window, with the final-season restricted free agent
    and the late-picks-only club added; guard: the same code reproduces part 4 on all trades without them

INPUTS: OUTPUT_DIR/_extended_run (the back-test's sides and assets, spines, page_2017_values.csv, gm sides, trades db)
OUTPUTS: OUTPUT_DIR/groups_any_log.txt, groups_any.csv
"""
import importlib.util
import os
import sys
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "groups_any.py v1.5 (2026-11-19)"   # v1.5: the main player's clause from clause_fill.clause_set (backtest.py v1.8's rule); the sellers for just picks and prospects come from backtest.py v1.8; v1.4: writes each side's flags (groups_any_sides.csv); v1.3: part 6, aged 28 or over in place of the two bands; v1.2: the joint regression on the declared window, the final-season restricted free agent and late picks added; v1.1: retained salary, former top-15 below and the final-season restricted free agent under both rules; late picks; the joint regression with one rule throughout
DECLARED_END = "2022-03-28"
LOG, OUT = [], []
FIVE = [("rental", "t_rental"), ("aged 28 to 31", "t_age28"), ("aged 32 or over", "t_age32"),
        ("a defenceman", "t_def"), ("sold under a new GM, predecessor's contract", "t_newgm")]


def log(s=""):
    print(s)
    LOG.append(s)


def player_rows():
    """Every player asset with its receiver, sender, age, position, rental status and contract signing date."""
    a = pd.read_csv(EXT / "backtest_assets.csv")
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "nhl_id", "cap_hit"]].drop_duplicates("asset_id")
    con = sqlite3.connect(EXT / "trades_extended.db")
    legs = pd.read_sql("select trade_id, acquiring_team from trade_legs", con)
    clubs = legs.groupby("trade_id")["acquiring_team"].apply(lambda x: sorted(set(x))).to_dict()
    a["sender"] = [r.from_team if pd.notna(r.from_team) else next((c for c in clubs.get(r.trade_id, []) if c != r.acquiring_team), None)
                   for r in a.itertuples()]
    pl = a[(a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))].merge(pv, on="asset_id", how="left")
    pl["date"] = pd.to_datetime(pl["trade_date"])
    ls = pd.read_csv(EXT / "contract_level_spine.csv", usecols=["nhl_id", "birthdate"]).drop_duplicates("nhl_id")
    pl["age"] = (pl["date"] - pd.to_datetime(pl["nhl_id"].map(ls.set_index("nhl_id")["birthdate"]))).dt.days / 365.25
    ss = pd.read_csv(EXT / "contract_season_spine.csv", low_memory=False)
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    p17 = pd.read_csv(EXT / "page_2017_values.csv").set_index("asset_id")
    status = []
    for r in pl.itertuples():                       # backtest_cuts.py status(), the status label only, and the signing date
        if r.source == "player model, rights":
            status.append("rights only"); continue
        if r.valuation_page == 2017:
            if r.asset_id not in p17.index or pd.isna(p17.at[r.asset_id, "contract_last_season"]):
                status.append("unknown"); continue
            x = p17.loc[r.asset_id]
            left, exp, elc = int(x["contract_last_season"]) - 2017 + 1, str(x["expiry"]), "Entry" in str(x["contract"])
            exp = "RFA" if exp.startswith("RFA") else "UFA"
        else:
            g = by.get((r.nhl_id, r.valuation_page)) if pd.notna(r.nhl_id) else None
            if g is None:
                status.append("unknown"); continue
            g = g[g["signed"] <= r.date] if (g["signed"] <= r.date).any() else g
            x = g.sort_values("signed").iloc[0]
            left, exp, elc = int(x["pp_signed_end"]) - int(r.valuation_page) + 1, str(x["pp_expiry"]), x["cs_entry_level"] == 1
            exp = "RFA" if exp == "RFA" else "UFA"
        if elc:
            status.append("entry-level contract")
        elif left <= 1:
            status.append("final season, restricted at expiry" if exp == "RFA" else "final season, unrestricted at expiry")
        else:
            status.append("two or more seasons left")
    pl["cstatus"] = status
    # the signing date as backtest_cuts_more.py cut GM reads it: the season spine at (nhl_id, page) for every page, the 2017
    # page included (status() above reads the 2017 page from page_2017_values.csv, which has no signing date)
    sg = []
    for r in pl.itertuples():
        g = by.get((r.nhl_id, int(r.valuation_page))) if pd.notna(r.nhl_id) else None
        if g is None:
            sg.append(pd.NaT); continue
        g = g[g["signed"] <= r.date] if (g["signed"] <= r.date).any() else g
        sg.append(g.sort_values("signed").iloc[0]["signed"])
    pl["signed"] = sg
    return pl


def main():
    log(SCRIPT_VERSION)
    spec = importlib.util.spec_from_file_location("groups_clustered", Path(__file__).resolve().parent / "groups_clustered.py")
    GC = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(GC)
    GC.OUTPUT_DIR = EXT
    t = GC.sides()
    key = ["trade_id", "club"]
    dec = t["trade_date"] <= DECLARED_END
    # GUARD 1: groups_clustered's recorded defenceman figures (declared window)
    x = t[dec & t["t_def"]]
    assert len(x) == 181 and abs(x["net_M"].mean() + 0.99) < 0.005, (len(x), x["net_M"].mean())
    log("  check 1: groups_clustered.sides() gives its recorded figures back (defenceman, 181 sides, -0.99 priced) (PASS)")

    pl = player_rows()
    # in-season: the asset row's own during_regular_season (backtest_assets.csv; the trade's, the same on every row)
    rec = pd.DataFrame({"trade_id": pl["trade_id"], "club": pl["acquiring_team"]})
    rec["a_rental"] = ((pl["cstatus"] == "final season, unrestricted at expiry") & pl["during_regular_season"].fillna(False).astype(bool)).astype(int)
    rec["a_age28"] = pl["age"].between(28, 32, inclusive="left").astype(int)
    rec["a_age32"] = (pl["age"] >= 32).astype(int)
    rec["a_def"] = (pl["pos"] == "D").astype(int)
    anyr = rec.groupby(key)[["a_rental", "a_age28", "a_age32", "a_def"]].max()
    nrec = rec.groupby(key).size().rename("n_received_players")
    # the manager: a player sent signed before the manager's first day, the manager in his first 365 days
    gm = pd.read_csv(EXT / "backtest_cuts_more_gm_sides.csv")
    gm = gm.merge(t[key + ["trade_date"]], on=key, how="left")
    gm["since"] = pd.to_datetime(gm["trade_date"]) - pd.to_timedelta(gm["days"], unit="D")
    snt = pl[["trade_id", "sender", "signed"]].rename(columns={"sender": "club"}).merge(gm[key + ["new_gm", "since"]], on=key, how="inner")
    snt["a_newgm"] = (snt["new_gm"].astype(bool) & (snt["signed"] < snt["since"])).astype(int)
    anys = snt.groupby(key)["a_newgm"].max()
    nsent = pl.groupby(["trade_id", "sender"]).size().rename("n_sent_players")
    nsent.index = nsent.index.set_names(key)
    t = t.join(anyr, on=key).join(anys, on=key).join(nrec, on=key).join(nsent, on=key)
    for c in ("a_rental", "a_age28", "a_age32", "a_def", "a_newgm"):
        t[c] = t[c].fillna(0).astype(bool)
    pairs = [("rental", "t_rental", "a_rental", "n_received_players"), ("aged 28 to 31", "t_age28", "a_age28", "n_received_players"),
             ("aged 32 or over", "t_age32", "a_age32", "n_received_players"), ("a defenceman", "t_def", "a_def", "n_received_players"),
             ("sold under a new GM, predecessor's contract", "t_newgm", "a_newgm", "n_sent_players")]
    # GUARD 2: one player received (sent): the flags agree
    log("  check 2: sides with exactly one player received (sent, for the manager): any-player flag against the one-player flag")
    bad = {}
    for lab, o, n_, cnt in pairs:
        one = t[t[cnt] == 1]
        bad[lab] = int((one[o].astype(bool) != one[n_]).sum())
        log(f"    {lab:<46} {len(one):>5} sides, {bad[lab]} differ")
    assert all(v == 0 for v in bad.values()), bad
    log("  (PASS)")
    log("\n  clubs in each group, all trades: one player -> any player")
    for lab, o, n_, _ in pairs:
        log(f"    {lab:<46}{int(t[o].sum()):>6} -> {int(t[n_].sum()):>6}   (declared window {int(t.loc[dec, o].sum())} -> {int(t.loc[dec, n_].sum())})")

    # ---- 1 group means, declared window ------------------------------------------------------------------------------------
    d = t[dec]
    log("\n1. GROUP MEANS, declared window ($M a club; mean (clustered se) p): one player -> any player")
    log(f"  {'group':<46}" + "".join(f"{y:>44}" for y, _ in GC.YS))
    for lab, o, n_, _ in pairs:
        cells = []
        for ylab, y in GC.YS:
            r = []
            for rule, f in (("one player", o), ("any player", n_)):
                x = d[d[f].astype(bool)]
                b, se, lo, hi, p = GC.clustered_mean(x[y].to_numpy(float), x["trade_id"].to_numpy())
                r.append(f"{b:+.2f} ({se:.2f}) p={p:.3f}")
                OUT.append({"part": "group mean, declared window", "group": lab, "rule": rule, "outcome": ylab, "n": len(x),
                            "estimate": b, "se": se, "p": p})
            cells.append(" -> ".join(r))
        log(f"  {lab:<46}" + "".join(f"{c:>44}" for c in cells))
        log(f"  {'':<46}{'sides: ' + str(int(d[o].sum())) + ' -> ' + str(int(d[n_].sum())):>44}")

    # ---- 2 beyond its price ------------------------------------------------------------------------------------------------
    log("\n2. OUTCOME ON PRICE, declared window: c, the group beyond what its price predicts (clustered by trade): one -> any")
    for ylab, y in GC.YS[1:]:
        log(f"  outcome: {ylab}")
        for lab, o, n_, _ in pairs:
            r = []
            for rule, f in (("one player", o), ("any player", n_)):
                X = pd.DataFrame({"const": 1.0, "priced": d["net_M"], "G": d[f].astype(float), "GxP": d[f].astype(float) * d["net_M"]})
                m = sm.OLS(d[y], X).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
                r.append(f"{m.params['G']:+.2f} ({m.bse['G']:.2f}) p={m.pvalues['G']:.3f}")
                OUT.append({"part": "beyond its price, declared window", "group": lab, "rule": rule, "outcome": ylab,
                            "estimate": m.params["G"], "se": m.bse["G"], "p": m.pvalues["G"]})
            log(f"    {lab:<46}{' -> '.join(r)}")

    # ---- 3 the joint regression, all trades ---------------------------------------------------------------------------------
    n = t.groupby("trade_id")["club"].transform("size")
    two = t[n == 2].sort_values(key)
    A = two.groupby("trade_id").nth(0).set_index("trade_id")
    B = two.groupby("trade_id").nth(1).set_index("trade_id")
    base = [g for _, g in GC.GROUPS[:-1]]
    swap = {o: n_ for _, o, n_, _ in pairs}
    nm = dict((g, l) for l, g in GC.GROUPS)
    fits = {}
    for rule, cols in (("one player", base), ("any player", [swap.get(g, g) for g in base])):
        X = pd.DataFrame({g: A[g].astype(int) - B[g].astype(int) for g in cols}, index=A.index)
        X = X.loc[:, (X != 0).sum() >= 5]
        fits[rule] = {y: sm.OLS(A[y], X).fit(cov_type="HC1") for _, y in GC.YS}
    log(f"\n3. THE JOINT REGRESSION, all trades, {len(A)} two-team trades, robust standard errors: one player -> any player")
    log(f"  {'characteristic':<46}" + "".join(f"{y:>44}" for y, _ in GC.YS))
    for g in base:
        g2 = swap.get(g, g)
        cells = []
        for ylab, y in GC.YS:
            m1, m2 = fits["one player"][y], fits["any player"][y]
            if g not in m1.params.index or g2 not in m2.params.index:
                cells.append("dropped"); continue
            cells.append(f"{m1.params[g]:+.2f} ({m1.bse[g]:.2f}) -> {m2.params[g2]:+.2f} ({m2.bse[g2]:.2f}) p={m2.pvalues[g2]:.3f}")
            for rule, m, k in (("one player", m1, g), ("any player", m2, g2)):
                OUT.append({"part": "joint, all trades", "group": nm[g], "rule": rule, "outcome": ylab,
                            "estimate": m.params[k], "se": m.bse[k], "p": m.pvalues[k]})
        log(f"  {nm[g]:<46}" + "".join(f"{c:>44}" for c in cells))
    # ==== v1.1: the remaining categories under both rules, and the joint regression with one rule throughout =============
    log("\n" + "=" * 100 + "\nv1.1: EVERY CATEGORY UNDER BOTH RULES")
    pv2 = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "pick", "draftYear"]].drop_duplicates("asset_id")
    pl = pl.merge(pv2, on="asset_id", how="left")
    by_cap = pl.sort_values("cap_hit", ascending=False, kind="stable")
    main_rec = by_cap.drop_duplicates(["trade_id", "acquiring_team"]).set_index(["trade_id", "acquiring_team"])
    main_snt = by_cap.drop_duplicates(["trade_id", "sender"]).set_index(["trade_id", "sender"])
    ix = pd.MultiIndex.from_frame(t[key])
    # former top-15 pick below the benchmark: backtest_cuts.py cut 5b's rule and benchmark, per player
    pcp, pcs = pd.read_csv(EXT / "pick_curve_players.csv"), pd.read_csv(EXT / "pick_curve_seasons.csv")
    top = pcp[(pcp["pick"] <= 15) & pcp["draftYear"].between(2005, 2012) & (pcp["is_goalie"] != True)]   # noqa: E712
    grid = [(r.draftYear, r.pick, y) for r in top.itertuples() for y in range(int(r.draftYear) + 4, min(2016, int(r.window_end) - 1) + 1)]
    wv = pcs.set_index(["draftYear", "pick", "season"])["war_82"]
    bench = float(np.mean([wv.get(k, 0.0) for k in grid]))
    pl["top15_under"] = ((pl["pick"] <= 15) & ((pl["valuation_page"] - pl["draftYear"]) >= 4) & (pl["pos"] != "G")
                         & (pl["trailing_war"] < bench))
    main_rec = main_rec.join(pl.drop_duplicates("asset_id").set_index("asset_id")["top15_under"], on="asset_id")
    t["m_top15"] = main_rec["top15_under"].reindex(ix).fillna(False).astype(bool).values
    a_top = pl[pl["top15_under"]].groupby(["trade_id", "acquiring_team"]).size()
    t["a_top15"] = pd.Series(1, index=a_top.index).reindex(ix).fillna(0).astype(bool).values
    assert (t["a_top15"] == t["t_top15"].astype(bool)).all()                    # GUARD: cut 5b's flag reproduced
    log(f"  check 3: benchmark {bench:.3f} WAR; the any-player top-15 flag equals groups_clustered's on all {len(t)} sides (PASS)")
    # a restricted free agent in his final contract season: backtest_cuts.py's status
    t["m_rfa"] = (main_rec["cstatus"].reindex(ix) == "final season, restricted at expiry").fillna(False).astype(bool).values
    a_rfa = pl[pl["cstatus"] == "final season, restricted at expiry"].groupby(["trade_id", "acquiring_team"]).size()
    t["a_rfa"] = pd.Series(1, index=a_rfa.index).reindex(ix).fillna(0).astype(bool).values
    cs_ = pd.read_csv(EXT / "backtest_cuts_all_sides.csv")[key + ["cstatus", "n_received", "n_clubs"]]
    tt = t[key].merge(cs_, on=key, how="left")
    assert (t["m_rfa"].values == (tt["cstatus"] == "final season, restricted at expiry").values).all()   # GUARD
    log("  check 4: the main-player restricted-free-agent flag equals backtest_cuts.py's main player status on every side (PASS)")
    # retained salary: the retaining club kept part of the salary of the main player it sent (any: backtest.py's g_retained)
    a_all = pd.read_csv(EXT / "backtest_assets.csv")
    ret = a_all[a_all["asset_type"] == "retained salary"]
    ret_set = set(zip(ret["trade_id"], ret["acquiring_team"], ret["name"].str.replace("retained: ", "", regex=False)))
    t["m_retained"] = [bool(k in main_snt.index and (k[0], k[1], main_snt.at[k, "name"]) in ret_set) for k in zip(t["trade_id"], t["club"])]
    t["a_retained"] = t["t_retained"].astype(bool)
    # the clause: backtest.py's rule on the main player received alone (any: g_clause)
    # v1.5: clause_fill.clause_set (the spine where it holds a matched record, else the CapWages page)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "20_CODE"))
    import clause_fill as CF
    cl_assets = CF.clause_set(EXT)
    hc = lambda x: int(x) in cl_assets  # noqa: E731
    t["m_clause"] = [hc(main_rec.at[k, "asset_id"]) if k in main_rec.index else False for k in zip(t["trade_id"], t["club"])]
    t["a_clause"] = t["t_clause"].astype(bool)
    one_r, one_s = t[t["n_received_players"] == 1], t[t["n_sent_players"] == 1]
    agree = {"top-15": int((one_r["m_top15"] != one_r["a_top15"]).sum()), "restricted": int((one_r["m_rfa"] != one_r["a_rfa"]).sum()),
             "clause": int((one_r["m_clause"] != one_r["a_clause"]).sum()), "retained (one player sent)": int((one_s["m_retained"] != one_s["a_retained"]).sum())}
    log(f"  check 5: one player received (sent, for retention): flags differing between the rules: {agree}")
    assert all(v == 0 for v in agree.values()), agree
    log("  (PASS)")
    # the club whose whole return was picks in rounds 6 and 7 (backtest_cuts.py cut 15; not about a player)
    tpk = pd.read_csv(EXT / "traded_pick_values.csv")[["asset_id", "pick_round"]]
    late_ids = set(tpk.loc[tpk["pick_round"] >= 6, "asset_id"])
    aa = a_all[a_all["asset_type"] != "retained salary"].assign(late=lambda x: (x["asset_type"] == "pick") & x["asset_id"].isin(late_ids))
    only = aa.groupby(["trade_id", "acquiring_team"])["late"].all()
    t["t_late"] = (pd.Series(only).reindex(ix).fillna(False).astype(bool).values & (tt["n_received"] > 0).values & (tt["n_clubs"] == 2).values)
    for lab, o, n_ in (("retained salary", "m_retained", "a_retained"), ("former top-15 pick below benchmark", "m_top15", "a_top15"),
                       ("restricted free agent, final season", "m_rfa", "a_rfa"), ("a clause", "m_clause", "a_clause"),
                       ("only picks in rounds 6 and 7 (not about a player)", "t_late", "t_late")):
        log(f"    {lab:<52} all trades {int(t[o].sum()):>4} -> {int(t[n_].sum()):>4}; declared window {int(t.loc[dec, o].sum())} -> {int(t.loc[dec, n_].sum())}")
    d = t[dec]
    new = [("retained salary", "m_retained", "a_retained"), ("former top-15 pick below benchmark", "m_top15", "a_top15"),
           ("restricted free agent, final season", "m_rfa", "a_rfa"), ("only picks in rounds 6 and 7", "t_late", "t_late"),
           ("a clause", "m_clause", "a_clause")]
    log("\n1b. GROUP MEANS, declared window: main player rule -> any player rule; mean (clustered se) p")
    for lab, o, n_ in new:
        cells = []
        for ylab, y in GC.YS:
            r = []
            for rule, f in (("main player", o), ("any player", n_)):
                x = d[d[f].astype(bool)]
                b, se, lo, hi, p = GC.clustered_mean(x[y].to_numpy(float), x["trade_id"].to_numpy())
                r.append(f"{b:+.2f} ({se:.2f}) p={p:.3f}")
                OUT.append({"part": "v1.1 group mean, declared window", "group": lab, "rule": rule, "outcome": ylab, "n": len(x),
                            "estimate": b, "se": se, "p": p})
            cells.append(" -> ".join(r))
        log(f"  {lab:<46} sides {int(d[o].sum())} -> {int(d[n_].sum())}")
        log("     " + " | ".join(f"{GC.YS[i][0]}: {c}" for i, c in enumerate(cells)))
    log("\n2b. OUTCOME ON PRICE, declared window: c (clustered by trade): main player rule -> any player rule")
    for ylab, y in GC.YS[1:]:
        for lab, o, n_ in new:
            r = []
            for rule, f in (("main player", o), ("any player", n_)):
                X = pd.DataFrame({"const": 1.0, "priced": d["net_M"], "G": d[f].astype(float), "GxP": d[f].astype(float) * d["net_M"]})
                m = sm.OLS(d[y], X).fit(cov_type="cluster", cov_kwds={"groups": d["trade_id"]})
                r.append(f"{m.params['G']:+.2f} ({m.bse['G']:.2f}) p={m.pvalues['G']:.3f}")
                OUT.append({"part": "v1.1 beyond its price, declared window", "group": lab, "rule": rule, "outcome": ylab,
                            "estimate": m.params["G"], "se": m.bse["G"], "p": m.pvalues["G"]})
            log(f"  {ylab:<22}{lab:<46}{' -> '.join(r)}")
    # the joint regression with ONE rule throughout (the two new groups not added)
    two = t[n == 2].sort_values(key)
    A = two.groupby("trade_id").nth(0).set_index("trade_id")
    B = two.groupby("trade_id").nth(1).set_index("trade_id")
    main_sw = {"t_clause": "m_clause", "t_retained": "m_retained", "t_top15": "m_top15"}
    any_sw = {**swap}
    fit4 = {}
    for rule, cols in (("main player rule", [main_sw.get(g, g) for g in base]), ("any player rule", [any_sw.get(g, g) for g in base])):
        X = pd.DataFrame({g: A[g].astype(int) - B[g].astype(int) for g in cols}, index=A.index)
        X = X.loc[:, (X != 0).sum() >= 5]
        fit4[rule] = ({y: sm.OLS(A[y], X).fit(cov_type="HC1") for _, y in GC.YS}, cols)
    # GUARD: the any-player rule fit is part 3's any-player fit (the clause, retention and top-15 were already any-player there)
    assert all(np.allclose(fit4["any player rule"][0][y].params.values, fits["any player"][y].params.values) for _, y in GC.YS)
    log(f"\n4. THE JOINT REGRESSION, ONE RULE THROUGHOUT, all trades, {len(A)} two-team trades, robust se (any-player fit = part 3's: PASS)")
    log(f"  {'characteristic':<46}{'rule':>18}" + "".join(f"{y:>30}" for y, _ in GC.YS))
    for i, g in enumerate(base):
        for rule in ("main player rule", "any player rule"):
            ms, cols = fit4[rule]
            k = cols[i]
            cells = []
            for ylab, y in GC.YS:
                m = ms[y]
                if k not in m.params.index:
                    cells.append("dropped"); continue
                cells.append(f"{m.params[k]:+.2f} ({m.bse[k]:.2f}) p={m.pvalues[k]:.3f}")
                OUT.append({"part": "v1.1 joint, one rule, all trades", "group": nm[g], "rule": rule, "outcome": ylab,
                            "estimate": m.params[k], "se": m.bse[k], "p": m.pvalues[k]})
            log(f"  {(nm[g] if rule.startswith('main') else ''):<46}{rule:>18}" + "".join(f"{c:>30}" for c in cells))
    # ==== v1.2: the joint regression, one rule throughout, on the DECLARED WINDOW, with the restricted free agent in his
    # final season and the club whose whole return was late picks added (protocol amendment 2026-11-18; Thomas: "Well it
    # really should be added to the regression"). Same design as part 4: two-team trades, first club minus second, no
    # constant, robust standard errors; a group with fewer than five non-zero differences drops out.
    def joint(rows, cols):
        X = pd.DataFrame({g: rows[0][g].astype(int) - rows[1][g].astype(int) for g in cols}, index=rows[0].index)
        X = X.loc[:, (X != 0).sum() >= 5]
        return {y: sm.OLS(rows[0][y], X).fit(cov_type="HC1") for _, y in GC.YS}
    # GUARD: this code on all trades without the two groups reproduces part 4's fits under both rules
    for rule in ("main player rule", "any player rule"):
        g4 = joint((A, B), fit4[rule][1])
        assert all(np.allclose(g4[y].params.values, fit4[rule][0][y].params.values) for _, y in GC.YS), rule
    log("\n5. THE JOINT REGRESSION, ONE RULE THROUGHOUT, DECLARED WINDOW, the restricted free agent and late picks added")
    log("  check 6: the same code on all trades without the two groups reproduces part 4 under both rules (PASS)")
    dmask = A["trade_date"] <= DECLARED_END
    Ad, Bd = A[dmask], B[dmask]
    add = {"main player rule": ["m_rfa", "t_late"], "any player rule": ["a_rfa", "t_late"]}
    nm5 = {**nm, "m_rfa": "restricted free agent, final season", "a_rfa": "restricted free agent, final season",
           "t_late": "only picks in rounds 6 and 7", "m_clause": nm["t_clause"], "m_retained": nm["t_retained"], "m_top15": nm["t_top15"]}
    fit5 = {rule: (joint((Ad, Bd), fit4[rule][1] + add[rule]), fit4[rule][1] + add[rule]) for rule in add}
    log(f"  {len(Ad)} two-team trades; robust standard errors; club A's value on A minus B")
    log(f"  {'characteristic':<46}{'rule':>18}" + "".join(f"{y:>30}" for y, _ in GC.YS))
    for i in range(len(fit5["main player rule"][1])):
        for rule in ("main player rule", "any player rule"):
            ms, cols = fit5[rule]
            k = cols[i]
            cells = []
            for ylab, y in GC.YS:
                m = ms[y]
                if k not in m.params.index:
                    cells.append("dropped"); continue
                cells.append(f"{m.params[k]:+.2f} ({m.bse[k]:.2f}) p={m.pvalues[k]:.3f}")
                OUT.append({"part": "v1.2 joint, one rule, declared window, two groups added",
                            "group": nm5[fit5["main player rule"][1][i]], "rule": rule,           # one label a group, both rules
                            "outcome": ylab, "estimate": m.params[k], "se": m.bse[k], "p": m.pvalues[k]})
            log(f"  {(nm5[k] if rule.startswith('main') else ''):<46}{rule:>18}" + "".join(f"{c:>30}" for c in cells))
    # v1.2 reading aids (declared before they were run): the late-picks group's overlap with futures for players, and two
    # sums of coefficients with robust 95% intervals (from the fit's own covariance)
    def combo(m, w):
        v = np.array([w.get(k, 0.0) for k in m.params.index])
        b, se = float(v @ m.params.values), float(np.sqrt(v @ m.cov_params().values @ v))
        return f"{b:+.2f} [{b - 1.96 * se:+.2f}, {b + 1.96 * se:+.2f}]", b, se
    dd = t[dec]
    lt = dd[dd["t_late"]]
    log(f"  late-picks-only clubs, declared window: {len(lt)}; of them also futures for players: {int(lt['t_futures'].sum())}")
    for rule in ("main player rule", "any player rule"):
        ms, cols = fit5[rule]
        tr = dict(zip(base, fit4[rule][1]))                  # each base group's column under this rule (t_rental -> a_rental)
        for lab, w0 in (("late picks only + futures for players", {"t_late": 1, "t_futures": 1}),
                       ("deadline rental for picks and prospects", {"t_rental": 1, "t_deadline_buyer": 1, "t_futures": -1})):
            w = {tr.get(k, k): x for k, x in w0.items()}
            assert all(k in ms["net_M"].params.index for k in w), (rule, w)   # GUARD: every term of the sum is in the fit
            cells = []
            for ylab, y in GC.YS:
                s, b, se = combo(ms[y], w)
                cells.append(s)
                OUT.append({"part": "v1.2 profile, declared window", "group": lab, "rule": rule, "outcome": ylab, "estimate": b, "se": se})
            log(f"  {lab:<46}{rule:>18}" + "".join(f"{c:>30}" for c in cells))
    # ==== v1.3: part 6, aged 28 or over in place of the two age bands (protocol amendment 2026-11-18; Thomas: "Replace
    # 28-31 and 32+ with just 28+"). Part 5's design and rows; one flag replaces the two under each rule.
    t["t_age28p"] = t["t_age28"].astype(bool) | t["t_age32"].astype(bool)
    t["a_age28p"] = t["a_age28"].astype(bool) | t["a_age32"].astype(bool)
    two6 = t[n == 2].sort_values(key)
    A6 = two6.groupby("trade_id").nth(0).set_index("trade_id")
    B6 = two6.groupby("trade_id").nth(1).set_index("trade_id")
    m6 = A6["trade_date"] <= DECLARED_END
    A6d, B6d = A6[m6], B6[m6]
    log("\n6. THE JOINT REGRESSION, DECLARED WINDOW, AGED 28 OR OVER IN PLACE OF THE TWO BANDS (part 5 otherwise)")
    for rule in ("main player rule", "any player rule"):
        cols5 = fit5[rule][1]
        g5 = joint((A6d, B6d), cols5)                                       # GUARD: part 5 reproduces on these rows
        assert all(np.allclose(g5[y].params.values, fit5[rule][0][y].params.values) for _, y in GC.YS), rule
        b28 = [c for c in cols5 if c.endswith("age28")][0]
        b32 = [c for c in cols5 if c.endswith("age32")][0]
        cols6 = [(b28 + "p") if c == b28 else c for c in cols5 if c != b32]
        g6 = joint((A6d, B6d), cols6)
        clause = [c for c in cols5 if c.endswith("clause")][0]
        dfn = [c for c in cols5 if c.endswith("_def")][0]
        log(f"  {rule} (part 5 reproduces: PASS)")
        for lab, fs, k in (("aged 28 to 31 (two bands)", fit5[rule][0], b28), ("aged 32 or over (two bands)", fit5[rule][0], b32),
                           ("aged 28 or over (one term)", g6, b28 + "p"), ("clause, two bands", fit5[rule][0], clause),
                           ("clause, one term", g6, clause), ("defenceman, two bands", fit5[rule][0], dfn),
                           ("defenceman, one term", g6, dfn)):
            cells = []
            for ylab, y in GC.YS:
                m = fs[y]
                cells.append(f"{m.params[k]:+.2f} ({m.bse[k]:.2f}) p={m.pvalues[k]:.3f}")
                OUT.append({"part": "v1.3 joint, declared window, 28 or over", "group": lab, "rule": rule, "outcome": ylab,
                            "estimate": m.params[k], "se": m.bse[k], "p": m.pvalues[k]})
            log(f"    {lab:<32}" + "".join(f"{c:>30}" for c in cells))
    # v1.4: each side's flags for one_regression.py (protocol 2026-11-19); no figure here changes
    flag_cols = [c for c in t.columns if c.startswith(("t_", "a_", "m_"))]
    t[key + ["trade_date"] + flag_cols].to_csv(OUTPUT_DIR / "groups_any_sides.csv", index=False)
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "groups_any.csv", index=False)
    (OUTPUT_DIR / "groups_any_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
