"""
findings_numbers.py v1.0 (2026-11-25) -- every figure of the fully worded "Findings" (findings_doc.js v4.0), read from the
outputs that produce it, written to OUTPUT_DIR/findings_doc/numbers.json. Report only; nothing else is written.

WHY (Thomas, 2026-11-25: "turn the Findings doc into a fully worded one of the same format"). The point-form builder held
each figure as a typed constant; this one reads them, so the document cannot drift from the outputs.

UNITS. $M at the 2025-26 cap, as the outputs hold them; the builder prints them as percent of that cap (K25 = 100 / 95.5).
Ratios (the price response, the cost of cap space) have no unit.

SOURCES (OUTPUT_DIR unless _extended_run is named):
  backtest_results.csv, backtest_results_gv_adj.csv     Section 2: slope, favoured share, asset classes (declared window)
  played_out_trades_log.txt                             Section 2: R-squared; the fully played-out trades
  one_regression.csv                                    Section 3 and Tables A1-A2 (556 trades, both rules, four outcomes)
  one_regression_replication.csv                        the three findings after 2022-03-28
  top10_swap.csv, top10_replication.csv                 the exploratory former top-10 pick
  clause_disguise.csv                                   the clause's profile; the clause with the cap hit held
  defence_checks_log.txt                                defencemen against their forecast
  trend_both.csv                                        change over time (declared window)
  _extended_run/groups_clustered.csv, groups_any.csv    sellers, cap dumps; the smallest beyond-its-price p
  who_overpaid.csv                                      the sellers with the cap hit held
  who_overpaid_checks.csv                               Section 4 and Table A3
  _extended_run/backtest_cuts_more_log.txt              the price of cap space
  stata/findings_data.csv                               counts (clubs with two or more players, conditional picks); the
                                                        share of realized NPV that is re-valuation; R-squared of A1-A3
  model_doc/numbers.json                                Game Value's correlation with the forecast, forwards and defencemen
GUARDS: each Section 3 figure is the one_regression.csv row of its rule, term and outcome; Section 2's slope and share
equal stata_export_findings' check 1 (backtest_results.csv); Section 4's three rows are the who_overpaid_checks rows the
point-form document printed (+0.26, +0.18, +0.39 to two decimals).
"""
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUT = Path(os.environ["OUTPUT_DIR"])
EXT = OUT / "_extended_run"
SCRIPT_VERSION = "findings_numbers.py v1.0 (2026-11-25)"
N = {"script": SCRIPT_VERSION}


def row(df, **kw):
    m = np.ones(len(df), dtype=bool)
    for k, v in kw.items():
        m &= (df[k] == v).to_numpy()
    r = df[m]
    assert len(r) == 1, (kw, len(r))
    return r.iloc[0]


def main():
    print(SCRIPT_VERSION)
    # ---- Section 2 -------------------------------------------------------------------------------------------------
    S2 = {}
    for lab, f in (("war", "backtest_results.csv"), ("gv", "backtest_results_gv_adj.csv")):
        br = pd.read_csv(OUT / f)
        sl = br[br["test"].str.startswith("A. slope")].iloc[0]
        fv = br[br["test"].str.startswith("A. share of trades")].iloc[0]
        S2[lab] = {"slope": [sl.estimate, sl.lo95, sl.hi95, sl.p], "fav": [fv.estimate, fv.lo95, fv.hi95, fv.p],
                   "n": int(sl.n_trades)}
        if lab == "war":
            S2["assets"] = {}
            for k in ("players", "picks", "prospects"):
                b = br[(br["test"].str.startswith("B. mean outcome minus forecast")) & (br["group"] == k)].iloc[0]
                S2["assets"][k] = [b.estimate, b.lo95, b.hi95, b.p, int(b.n_assets)]
    po = (OUT / "played_out_trades_log.txt").read_text(encoding="utf-8")
    def block(title):
        i = po.index(title)
        j = po.find("\n\n", i)
        return po[i:j if j > 0 else None]
    def grab(b, lab):
        m = re.search(re.escape(lab) + r"\s+([-+0-9.]+) \[([-+0-9.]+), ([-+0-9.]+)\]", b)
        return [float(m.group(1)), float(m.group(2)), float(m.group(3))]
    allb = block("declared window (2017-07-01 to 2022-03-28), all complete trades")
    outb = block("declared window (2017-07-01 to 2022-03-28), fully played out")
    S2["r2"] = grab(allb, "R-squared")[0]
    S2["played_out"] = {"n": int(re.search(r"fully played out: (\d+) trades", outb).group(1)),
                        "fav": grab(outb, "favoured club ahead"), "fav_nz": grab(outb, "the same, sides with a result of exactly zero set aside"),
                        "slope": grab(outb, "slope of result on grade")}
    assert abs(S2["war"]["slope"][0] - grab(allb, "slope of result on grade")[0]) < 5e-4      # GUARD: the same test
    N["s2"] = S2

    # ---- Section 3 and the appendix ----------------------------------------------------------------------------------
    orr = pd.read_csv(OUT / "one_regression.csv")
    OUTC = ["trade-day grade", "realized value, WAR", "realized value, Game Value", "realized value, seasons played"]
    R = {}
    for rule in ("main player rule", "any player rule"):
        R[rule] = {}
        for _, r in orr[orr["rule"] == rule].iterrows():
            R[rule].setdefault(r["col"], {"term": r["term"]})[r["outcome"]] = [r["estimate"], r["se"], r["p"]]
        for k, v in R[rule].items():
            assert all(o in v for o in OUTC), (rule, k)
    N["reg"] = R
    N["reg_n"] = int(orr["n_trades"].iloc[0])
    # R-squared without a constant, refitted from the Stata CSV on one row a trade (as the appendix of v3.12-v3.14)
    fd = pd.read_csv(OUT / "stata" / "findings_data.csv")
    N["clubs_two_plus"] = None
    rr = fd[(fd["in_main_regression"] == 1)]
    first = rr[rr["one_row_per_trade"] == 1]
    assert len(first) == N["reg_n"]
    # the share of realized NPV from re-valuation (seasons from 2026-27), on the regression's club sides
    sides = pd.read_csv(EXT / "backtest_sides.csv")
    s = sides.merge(rr[["trade_id", "club"]], on=["trade_id", "club"])
    assert len(s) == 2 * N["reg_n"]
    N["revalued_share"] = float((s["out_net_M"] - s["real_net_M"]).abs().sum() / s["out_net_M"].abs().sum())
    N["conditional_trades_reg"] = int(s.loc[s["has_conditional_pick"], "trade_id"].nunique())
    d563 = pd.read_csv(OUT / "backtest_sides.csv")
    d563 = d563[d563["complete"]]
    N["trades_s2"] = int(d563["trade_id"].nunique())
    N["conditional_trades"] = int(d563.loc[d563["has_conditional_pick"], "trade_id"].nunique())
    # clubs that received two or more players valued by the player model
    a = pd.read_csv(EXT / "backtest_assets.csv")
    pl = a[(a["asset_type"] == "player") & a["source"].str.startswith(("player model", "buried"))]
    cnt = pl.groupby(["trade_id", "acquiring_team"]).size()
    N["clubs_two_plus"] = int(sum(cnt.get((t, c), 0) >= 2 for t, c in zip(s["trade_id"], s["club"])))

    rep = pd.read_csv(OUT / "one_regression_replication.csv")
    REP = {}
    for rule, col in (("main player rule", "main_clause"), ("main player rule", "age28"), ("main player rule", "defence"),
                      ("any player rule", "any_clause")):
        REP[f"{rule}|{col}"] = {o: [row(rep, rule=rule, col=col, outcome=o).estimate, row(rep, rule=rule, col=col, outcome=o).p]
                                for o in OUTC[:2]}
    N["replication"] = REP
    N["replication_n"] = int(rep["n_trades"].iloc[0])

    t10 = pd.read_csv(OUT / "top10_swap.csv")
    t10r = pd.read_csv(OUT / "top10_replication.csv")
    T10 = {}
    for rule, col in (("main player rule", "top15"), ("any player rule", "any_top15")):
        T10[rule] = {"2017-22": {o: [row(t10, rule=rule, version="top-10 swap", col=col, outcome=o).estimate,
                                     row(t10, rule=rule, version="top-10 swap", col=col, outcome=o).se,
                                     row(t10, rule=rule, version="top-10 swap", col=col, outcome=o).p] for o in OUTC},
                     "after 2022": {o: [row(t10r, rule=rule, col=col, outcome=o).estimate, row(t10r, rule=rule, col=col, outcome=o).se,
                                        row(t10r, rule=rule, col=col, outcome=o).p] for o in OUTC}}
        # GUARD: the document's top-15 row is one_regression's
        for o in OUTC:
            d_ = row(t10, rule=rule, version="document", col=col, outcome=o)
            assert abs(d_.estimate - R[rule][col][o][0]) < 1e-9
    N["top10"] = T10
    N["top10_n_after"] = int(t10r["n_trades"].iloc[0])

    cd = pd.read_csv(OUT / "clause_disguise.csv")
    prof = cd[cd["part"] == "profile"]
    N["clause_profile"] = {r.term: [r.clause, r.no_clause] for r in prof.itertuples()}
    N["clause_parts"] = sorted(cd["part"].unique().tolist())
    N["clause_cap_held"] = {}
    ch = cd[(cd["part"] == "+ cap hit") & (cd["rule"] == "main player rule") & (cd["term"] == "clause")]
    for _, r in ch.iterrows():
        N["clause_cap_held"][r["outcome"]] = [r["estimate"], r["se"], r["p"]]
    assert set(N["clause_cap_held"]) >= {"net_M", "out_net_M"}

    dc = (OUT / "defence_checks_log.txt").read_text(encoding="utf-8")
    m = re.search(r"D, traded\s+\d+\s+\d+([-+0-9.]+) \[([-+0-9.]+),([-+0-9.]+)\]", dc)
    N["def_war"] = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
    m = re.search(r"D\s+declared window\s+\d+\s+([-+0-9.]+) \[([-+0-9.]+),([-+0-9.]+)\]", dc)
    N["def_side"] = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
    m = re.search(r"F\s+declared window\s+\d+\s+([-+0-9.]+) \[([-+0-9.]+),([-+0-9.]+)\]", dc)
    N["fwd_side"] = [float(m.group(1)), float(m.group(2)), float(m.group(3))]

    tb = pd.read_csv(OUT / "trend_both.csv")
    N["trend"] = {r.value: [r.slope, r.se, r.p] for r in tb[tb["scope"] == "declared window"].itertuples()}

    g = pd.read_csv(EXT / "groups_clustered.csv")
    gm = g[(g["scope"] == "DECLARED WINDOW") & (g["part"] == "group mean")]
    def gmv(grp, o):
        r = row(gm, group=grp, outcome=o)
        return [r.estimate, r.se, r.boot_lo, r.boot_hi, r.p, int(r.n_trades)]
    N["sellers"] = {"priced": gmv("futures for players", "priced"), "outcome": gmv("futures for players", "outcome, WAR")}
    N["dumps"] = {"priced": gmv("took a contract to clear cap", "priced"), "outcome": gmv("took a contract to clear cap", "outcome, WAR")}
    op = g[(g["scope"] == "DECLARED WINDOW") & (g["part"] == "outcome on price")]
    ga = pd.read_csv(OUT / "groups_any.csv")
    gb = ga[ga["part"] == "beyond its price, declared window"]
    cps = list(op["c_p"].dropna()) + list(gb["p"].dropna())   # the beyond-its-price p, each group, both rules, WAR and GV
    N["groups_n"] = int(len(set(op["group"]) | set(gb["group"])))
    N["smallest_c_p"] = float(min(cps))
    wo = pd.read_csv(OUT / "who_overpaid.csv")
    sc = wo[(wo["part"] == "A, scope") & (wo["term"] == "futures for players") & (wo["scope"] == "declared window")]
    N["sellers_cap_held"] = {r["outcome"]: [r["with"], r["se"], r["p"]] for _, r in sc.iterrows()}
    cm = (EXT / "backtest_cuts_more_log.txt").read_text(encoding="utf-8")
    m = re.search(r"declared window \(to 2022-03-28\): (\d+) trades;.*?price of cap space \$([0-9.]+)M of futures per \$1M cleared \[([0-9.]+), ([0-9.]+)\]", cm)
    N["cap_space_price"] = [int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))]

    w = pd.read_csv(OUT / "who_overpaid_checks.csv")
    wm = w[(w["model"].notna()) & (w["scope"] == "all trades")]
    S4 = {}
    for key, model in (("forecast", "the model's performance value (part B)"), ("played", "the same, seasons played only"),
                       ("iv", "two-stage, instrument: seasons played")):
        r = row(wm, model=model)
        S4[key] = {"perf": [r.perf, r.perf_se, r.perf_p], "cost": [r.cost, r.cost_se, r.cost_p], "n": int(r.n),
                   "first": [r.first_stage, r.first_t], "perf_ci": [r.perf_lo, r.perf_hi]}
    assert [round(S4[k]["perf"][0], 2) for k in ("forecast", "played", "iv")] == [0.26, 0.18, 0.39], S4   # GUARD
    N["s4"] = S4

    md = json.loads((OUT / "model_doc" / "numbers.json").read_text(encoding="utf-8"))
    N["gv_r"] = {"F": md["gv"]["F"]["forecast"][0], "D": md["gv"]["D"]["forecast"][0]}

    (OUT / "findings_doc").mkdir(exist_ok=True)
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (float, np.floating)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        return o
    (OUT / "findings_doc" / "numbers.json").write_text(json.dumps(clean(N), indent=1), encoding="utf-8")
    print(f"  wrote {OUT / 'findings_doc' / 'numbers.json'}")
    print(f"  re-valuation share {N['revalued_share']:.3f}; clubs with two or more players {N['clubs_two_plus']}; "
          f"conditional-pick trades {N['conditional_trades']}; smallest beyond-its-price p {N['smallest_c_p']:.3f} over "
          f"{N['groups_n']} groups; clause parts {N['clause_parts']}; cap held {N['clause_cap_held']}")


if __name__ == "__main__":
    main()
