"""
who_overpaid.py - what the main player's cap hit explains, how trade prices follow a contract's value, and who clubs pay
more than they are worth (Thomas, 2026-11-17: "the more interesting finding is to follow the pattern of who is
overpaid"; declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only, exploratory.)

WHY. clause_checks.py found that the main player's cap hit carries the clause result. A contract's xNPV is the value of
its forecasted performance less its cap hit, so "clubs overpay for expensive contracts" restates the model's own
definition. The question is instead which players clubs pay more for than they are worth, described by what a club
sees about the player before the trade, with the cap hit left out.

  A  the joint regression's thirteen coefficients with and without the main player's cap hit ($M); and the cap hit's
     coefficient on the trades after 2022-03-28 alone (its replication)
  B  the price paid for the main player = what the club gave up less everything else it received (models' values) =
     his xNPV less the club's priced net. Regressed on his contract's two parts: PERFORMANCE VALUE (the forecasted
     performance and control seasons: his xNPV plus the cost below) and COST (the present value of the cap hit he
     carries over the seasons left: cap hit x the share of the season left, then each further season, each divided by
     1.03^k, at the 2025-26 cap; retention already netted in the ledger's cap hit; injured-reserve relief left out, so
     approximate). A price that follows each part in full: +1 on performance value, -1 on cost.
  C  who: the club's overpay (minus its priced net) and its realised loss (minus its outcome net) on the main player's
     characteristics before the trade, none of them his cap hit: aged 28 to 31, aged 32 or over (27 and under the
     base), defenceman, a clause, signed as an unrestricted free agent, two seasons left, three or more (one the base),
     production (50/30/20 trailing WAR total), record above the forecast (that total less expected first-season WAR),
     games share in the most recent season, a former top-15 pick. All together, then each alone.

BAKED-IN ASSUMPTIONS: the main player and his cap hit, signing status and record as clause_checks.main_players (the
highest ledger cap hit received; PuckPedia's signing status; the forecast at the page); seasons left from the season
spine as backtest_cuts.py; games share = his games in the season before the page / that season's games a club played
(82; 70 in 2019-20, 56 in 2020-21, 48 in 2012-13). Standard errors clustered by trade (robust for the joint regression,
one row a trade).

INPUTS: the extended run (groups_clustered.sides(), backtest_assets.csv, prospect_values.csv), contract_season_spine.csv,
        WAR_with_age.csv, xnpv1_forecasts.csv; the PuckPedia contract export
OUTPUTS: OUTPUT_DIR/who_overpaid_log.txt, who_overpaid.csv
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()
import skater_forward_projection as SFP              # noqa: E402

OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "who_overpaid.py v1.0 (2026-11-17)"
DECLARED_END = "2022-03-28"
CAP = SFP.CAP_CEILING
CAP_NOW = CAP[2025]
SEASON_GAMES = {2012: 48, 2019: 70, 2020: 56}
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def build():
    CC = load("clause_checks")
    GC, t = CC.load_sides()
    mp = CC.main_players()
    # the main asset itself: its xNPV and outcome, page, season share (clause_checks keeps one row a side, same rule)
    a = pd.read_csv(EXT / "backtest_assets.csv")
    pv = pd.read_csv(EXT / "prospect_values.csv", low_memory=False)[["asset_id", "nhl_id", "cap_hit"]].drop_duplicates("asset_id")
    pl = a[(a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))].merge(pv, on="asset_id", how="left")
    main = pl.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(["trade_id", "acquiring_team"]).rename(columns={"acquiring_team": "club"})
    main = main[["trade_id", "club", "asset_id", "value_2025_cap_M", "outcome_M", "valuation_page", "season_share", "trade_date"]].rename(
        columns={"value_2025_cap_M": "V", "outcome_M": "V_out", "trade_date": "date"})
    t = t.merge(mp, on=["trade_id", "club"], how="left").merge(main, on=["trade_id", "club"], how="left")
    side = pd.read_csv(EXT / "backtest_cuts_all_sides.csv")[["trade_id", "club", "age", "pos", "pick", "during_regular_season"]]
    t = t.merge(side, on=["trade_id", "club"], how="left")
    # seasons left on the contract at the page (backtest_cuts.py's rule)
    ss = pd.read_csv(OUTPUT_DIR / "contract_season_spine.csv", low_memory=False, usecols=["nhl_id", "season_start", "pp_signed_end", "pp_signing_date"])
    ss["signed"] = pd.to_datetime(ss["pp_signing_date"])
    by = {k: g for k, g in ss.groupby(["nhl_id", "season_start"])}
    left = []
    for r in t.itertuples():
        g = by.get((r.nhl_id, int(r.valuation_page))) if pd.notna(r.nhl_id) and pd.notna(r.valuation_page) else None
        if g is None:
            left.append(np.nan)
            continue
        d = pd.Timestamp(r.date)
        g = g[g["signed"] <= d] if (g["signed"] <= d).any() else g
        left.append(max(int(g.sort_values("signed").iloc[0]["pp_signed_end"]) - int(r.valuation_page) + 1, 1))
    t["left"] = left
    share = t["season_share"].fillna(1.0)
    t["cost"] = [np.nan if pd.isna(l) or pd.isna(c) or pd.isna(p) else
                 c * CAP_NOW / CAP[int(p)] * (s + sum(1 / 1.03 ** k for k in range(1, int(l)))) / 1e6
                 for l, c, p, s in zip(t["left"], t["cap_hit"], t["valuation_page"], share)]
    t["perf"] = t["V"] + t["cost"]
    t["price"] = t["V"] - t["net_M"]
    t["price_out"] = t["V_out"] - t["out_net_M"]
    # games share in the most recent season before the page
    w = pd.read_csv(OUTPUT_DIR / "WAR_with_age.csv", usecols=["nhl_id", "Season", "GP"]).dropna(subset=["nhl_id"])
    w["y"] = 2000 + w["Season"].str[:2].astype(int)
    gp = w.groupby(["nhl_id", "y"])["GP"].sum()
    t["gp_share_last"] = [np.nan if pd.isna(n_) or pd.isna(p) else
                          min(float(gp.get((n_, int(p) - 1), 0.0)) / SEASON_GAMES.get(int(p) - 1, 82), 1.0)
                          for n_, p in zip(t["nhl_id"], t["valuation_page"])]
    t["age28"] = t["age"].between(28, 32, inclusive="left").astype(float)
    t["age32"] = (t["age"] >= 32).astype(float)
    t["defence"] = (t["pos"] == "D").astype(float)
    t["clause"] = t["t_clause"].astype(float)
    t["ufa"] = t["ufa_signed"].fillna(0).astype(float)
    t["left2"] = (t["left"] == 2).astype(float)
    t["left3"] = (t["left"] >= 3).astype(float)
    t["top15"] = (t["pick"] <= 15).astype(float)
    t["cap_M"] = t["cap_hit"].fillna(0) / 1e6
    return GC, t


def fmt(m, k):
    return f"{m.params[k]:+.2f} ({m.bse[k]:.2f}) p={m.pvalues[k]:.3f}"


def main():
    log(SCRIPT_VERSION)
    log(f"  reads {EXT}")
    GC, t = build()

    # ---- A ---------------------------------------------------------------------------------------------------------------
    cols = [g for _, g in GC.GROUPS[:-1]]
    nm = dict((g, l) for l, g in GC.GROUPS)
    n = t.groupby("trade_id")["club"].transform("size")
    two = t[n == 2].sort_values(["trade_id", "club"])
    A = two.groupby("trade_id").nth(0).set_index("trade_id")
    B = two.groupby("trade_id").nth(1).set_index("trade_id")
    X = pd.DataFrame({g: A[g].astype(int) - B[g].astype(int) for g in cols}, index=A.index)
    X["cap_M"] = A["cap_M"] - B["cap_M"]
    dates = A["trade_date"]
    log("\nA. WHAT THE CAP HIT EXPLAINS: the joint regression, all trades, each coefficient without -> with the main player's cap hit")
    log(f"  {'characteristic':<38}" + "".join(f"{y:>34}" for y in ("priced", "outcome, WAR", "outcome, Game Value")))
    fits = {}
    for y in ("net_M", "out_net_M", "gv_net_M"):
        fits[y] = (sm.OLS(A[y], X[cols]).fit(cov_type="HC1"), sm.OLS(A[y], X[cols + ["cap_M"]]).fit(cov_type="HC1"))
    for g in cols + ["cap_M"]:
        cells = []
        for y in ("net_M", "out_net_M", "gv_net_M"):
            m0, m1 = fits[y]
            b0 = f"{m0.params[g]:+.2f}" if g in m0.params else "  -  "
            cells.append(f"{b0} -> {m1.params[g]:+.2f}{'*' if m1.pvalues[g] < 0.05 else ' '} (p={m1.pvalues[g]:.3f})")
            OUT.append({"part": "A", "term": nm.get(g, "cap hit, per $1M"), "outcome": y, "without": m0.params.get(g, np.nan),
                        "with": m1.params[g], "se": m1.bse[g], "p": m1.pvalues[g]})
        log(f"  {nm.get(g, 'main player cap hit, per $1M'):<38}" + "".join(f"{c:>34}" for c in cells))
    for scope, msk in (("declared window", (dates <= DECLARED_END).values), ("after 2022-03-28 (replication)", (dates > DECLARED_END).values)):
        Xs = X.loc[msk, cols + ["cap_M"]]
        Xs = Xs.loc[:, (Xs != 0).sum() >= 5]
        cells = []
        for y in ("net_M", "out_net_M", "gv_net_M"):
            m = sm.OLS(A.loc[msk, y], Xs).fit(cov_type="HC1")
            cells.append(f"{y} {fmt(m, 'cap_M')}")
            OUT.append({"part": "A, scope", "term": "cap hit, per $1M", "scope": scope, "outcome": y, "with": m.params["cap_M"],
                        "se": m.bse["cap_M"], "p": m.pvalues["cap_M"]})
        log(f"  cap hit per $1M, {scope} ({int(msk.sum())} trades): " + "; ".join(cells))

    # ---- B ---------------------------------------------------------------------------------------------------------------
    d = t[t["perf"].notna() & t["price"].notna()].copy()
    log(f"\nB. HOW THE PRICE FOLLOWS THE CONTRACT: club sides with a main player valued by the player model and a cost: {len(d)}")
    log(f"  the main player's performance value: mean {d['perf'].mean():+.2f}; cost {d['cost'].mean():.2f}; xNPV {d['V'].mean():+.2f} ($M at the 2025-26 cap)")
    log(f"  {'scope':<18}{'price paid on':<16}{'performance value':>28}{'cost':>28}{'n':>6}")
    for scope, msk in (("all trades", pd.Series(True, index=d.index)), ("declared window", d["trade_date"] <= DECLARED_END)):
        dd = d[msk]
        for lab, y, perf in (("price, priced", "price", "perf"), ("price, outcome", "price_out", "perf")):
            m = sm.OLS(dd[y], sm.add_constant(dd[[perf, "cost"]])).fit(cov_type="cluster", cov_kwds={"groups": dd["trade_id"]})
            log(f"  {scope:<18}{lab:<16}{fmt(m, 'perf'):>28}{fmt(m, 'cost'):>28}{len(dd):>6}")
            OUT.append({"part": "B", "scope": scope, "outcome": lab, "perf": m.params["perf"], "perf_se": m.bse["perf"],
                        "cost": m.params["cost"], "cost_se": m.bse["cost"], "n": len(dd)})
    log("  (a price that follows each part in full: +1.00 on performance value, -1.00 on cost)")

    # ---- C ---------------------------------------------------------------------------------------------------------------
    chars = [("aged 28 to 31", "age28"), ("aged 32 or over", "age32"), ("defenceman", "defence"), ("a clause", "clause"),
             ("signed as a free agent", "ufa"), ("two seasons left", "left2"), ("three or more seasons left", "left3"),
             ("production (trailing WAR total)", "trailing_war"), ("record above the forecast (WAR)", "rep_gap"),
             ("games share, most recent season", "gp_share_last"), ("former top-15 pick", "top15")]
    cc = [c for _, c in chars]
    d = t[t["name"].notna()].dropna(subset=cc + ["age"]).copy()
    d["overpay"], d["loss"], d["loss_gv"] = -d["net_M"], -d["out_net_M"], -d["gv_net_M"]
    log(f"\nC. WHO CLUBS PAY MORE THAN THEY ARE WORTH: club sides with a main player and every characteristic known: {len(d)} "
        f"({d['trade_id'].nunique()} trades); $M a side, positive = the club paid more / lost more; clustered by trade")
    for scope, msk in (("all trades", pd.Series(True, index=d.index)), ("declared window", d["trade_date"] <= DECLARED_END)):
        dd = d[msk]
        log(f"\n  {scope} ({len(dd)} sides)")
        log(f"  {'characteristic':<34}" + "".join(f"{y + ', together':>30}{'alone':>14}" for y in ("overpay", "loss, WAR", "loss, GV")))
        fits = {y: sm.OLS(dd[y], sm.add_constant(dd[cc])).fit(cov_type="cluster", cov_kwds={"groups": dd["trade_id"]})
                for y in ("overpay", "loss", "loss_gv")}
        for lab, c in chars:
            cells = []
            for y in ("overpay", "loss", "loss_gv"):
                m = fits[y]
                al = sm.OLS(dd[y], sm.add_constant(dd[[c]])).fit(cov_type="cluster", cov_kwds={"groups": dd["trade_id"]})
                cells.append(f"{m.params[c]:+.2f}{'*' if m.pvalues[c] < 0.05 else ' '} (p={m.pvalues[c]:.3f})")
                cells.append(f"{al.params[c]:+.2f}{'*' if al.pvalues[c] < 0.05 else ' '}")
                OUT.append({"part": "C", "scope": scope, "term": lab, "outcome": y, "together": m.params[c], "se": m.bse[c],
                            "p": m.pvalues[c], "alone": al.params[c], "alone_p": al.pvalues[c], "n": len(dd)})
            log(f"  {lab:<34}" + "".join(f"{x:>30}" if i % 2 == 0 else f"{x:>14}" for i, x in enumerate(cells)))
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "who_overpaid.csv", index=False)
    (OUTPUT_DIR / "who_overpaid_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
