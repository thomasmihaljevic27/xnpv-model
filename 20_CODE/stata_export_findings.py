"""
stata_export_findings.py -- every regression the findings document ("Trade Back-test Findings", findings_doc.js v3.8)
reports, as ONE flat CSV for Stata, a do-file with the figure each command should print, and checks that the CSV gives
the model's figures back (v1.0, 2026-11-19; Thomas: "I need a csv for all the data and a stata codebook styled like the
last codebook"; scope: the findings document, one CSV, one row a club side).

ROWS: one per club side of every complete trade from 2017-07-01 to 2026-03-13 (the extended run's backtest_sides.csv,
complete == True). Yes/no columns pick out each section's sample:
  declared    the trade is in the declared window (to 2022-03-28): Sections 2 and 3
  in_reg      the 556 two-team trades of Section 3's regression (one_regression.py's frame): both clubs' rows (v1.2: the
              regression reads one of them, first_club == 1; the other row is its mirror image)
  in_price    the 886 club sides with a main player valued by the player model and a cost (Section 4)
  first_club  1 for the first club (alphabetically) of a two-team trade: who_overpaid.py part A's one row a trade

COLUMNS (Stata names; the codebook, 40_DOCS/Stata_Findings_Codebook.md, says what each is):
  outcomes    grade (trade-day grade), real_war, real_gv (realized value on WAR, Game Value), real_played (seasons played)
  Section 2   favoured (the club the trade-day grade favoured: backtest.py's rule), ahead_war, ahead_gv
  Section 3   m_<term> and a_<term>: the club's side less the other club's side in each of the 23 terms, under the main
              player and the any player rule (one_regression.py's columns, values A - B on the first club's row and B - A
              on the second's); blank outside in_reg
              cd_cap, cd_career, cd_best: the main player's cap hit, career WAR and best season, side less other side
              (clause_disguise.py's measures); dump_trade: 1 when either club took a contract to clear cap
              own_clause_main, own_clause_any, own_seller: the club's OWN yes/no (Step 4's averages)
  Section 4   price, perf_value, cap_cost, perf_played (who_overpaid.py part B; who_overpaid_checks.py's delivered value)
  part A      j_<group> (the 13 groups less the club that received nothing) and j_cap: the first club's group less the
              second's, on the first club's row (who_overpaid.py part A)

CHECKS (each must pass or nothing is kept): the CSV, read back, gives every figure below back from the model's own
outputs, coefficients and standard errors to 1e-9: test A's slope and favoured share (backtest_results.csv); Section 3's
regression, every term, both rules, four outcomes (one_regression.csv); the clause with the cap hit, with reputation and
without the cap dumps (clause_disguise.csv); the clause and seller averages (groups_any.csv, groups_clustered.csv); the
sellers with the cap hit held (who_overpaid.csv); Section 4's three price fits (who_overpaid_checks.csv; the two-stage
coefficients only, its standard errors there being resampled). The do-file's expected figures are computed as Stata
computes them (stata_expected.OLS: robust errors HC1, p-values on t with N-K degrees of freedom; clustered errors
G/(G-1) x (N-1)/(N-K), p-values on t with G-1 degrees of freedom; the
document's p-values use the normal, so a third decimal can differ).

OUTPUTS: 30_OUTPUT/stata/findings_data.csv, findings_walkthrough.do, stata_export_findings_log.txt
Run from the repo root, after the back-test and the findings scripts: python 20_CODE/stata_export_findings.py
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy import stats

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "20_CODE"))
import stata_expected as SE                                                  # noqa: E402

OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
OUT = OUTPUT_DIR / "stata"
SCRIPT_VERSION = "stata_export_findings.py v1.2 (2026-11-21)"   # v1.2: Section 3 on one row a trade (one_row_per_trade == 1), robust errors (Thomas: "Yes, switch"); v1.1: plain variable names (Thomas: "variable names that make sense"); nothing else changes
DECLARED_END = "2022-03-28"
TOL = 1e-9
LOG, DO = [], []

# one_regression's columns -> the Stata name's stem (main player rule m_, any player rule a_)
STEM = {"t_futures": "sold_picks", "t_deadline_buyer": "deadline_buyer", "t_other_buyer": "earlier_buyer",
        "t_rental": "rental", "a_rental": "rental", "m_retained": "retained", "t_retained": "retained",
        "t_single": "one_for_many", "t_dump": "took_dump", "t_newgm": "new_gm", "a_newgm": "new_gm",
        "m_rfa": "rfa_final", "a_rfa": "rfa_final", "t_late": "late_picks",
        "age28": "age28_31", "age32": "age32_plus", "defence": "defence", "main_clause": "clause", "ufa": "ufa_signed",
        "left2": "left2", "left3": "left3_plus", "top15": "top15", "trailing_war": "production", "rep_gap": "above_fcst",
        "gp_share_last": "games_share", "goalie": "goalie",
        "any_age28": "age28_31", "any_age32": "age32_plus", "any_defence": "defence", "any_clause": "clause",
        "any_ufa": "ufa_signed", "any_left2": "left2", "any_left3": "left3_plus", "any_top15": "top15", "avg_war": "production",
        "avg_gap": "above_fcst", "avg_gs": "games_share", "any_goalie": "goalie", "recv": "got_player"}
JSTEM = {"t_futures": "j_sold_picks", "t_deadline_buyer": "j_deadline_buyer", "t_other_buyer": "j_earlier_buyer",
         "t_rental": "j_rental", "t_retained": "j_retained", "t_age28": "j_age28_31", "t_age32": "j_age32_plus",
         "t_def": "j_defence", "t_clause": "j_clause", "t_top15": "j_top15_below", "t_single": "j_one_for_many",
         "t_dump": "j_took_dump", "t_newgm": "j_new_gm", "cap_M": "j_cap"}
# v1.1 (Thomas, 2026-11-19: "could you make the csv have variable names that make sense or are more obvious what they
# mean?"): the CSV and the do-file carry these names (at most 32 characters, lower case, as Stata takes them); the
# script works on the short names and maps them at the end (the checks read the CSV back under the plain names)
_TYPE = {"sold_picks": "sold_for_just_picks", "deadline_buyer": "deadline_buyer", "earlier_buyer": "buyer_earlier_in_season",
         "rental": "got_rental", "retained": "retained_salary", "one_for_many": "got_one_for_two_or_more",
         "took_dump": "took_cap_dump", "new_gm": "new_gm_sold_old_contract", "rfa_final": "got_final_year_rfa",
         "late_picks": "got_only_late_picks", "age28_31": "age_28_31", "age32_plus": "age_32_plus", "defence": "defenceman",
         "goalie": "goalie", "clause": "clause", "ufa_signed": "signed_as_ufa", "left2": "two_seasons_left",
         "left3_plus": "three_plus_seasons_left", "top15": "former_top15_pick", "production": "recent_war",
         "above_fcst": "war_above_forecast", "games_share": "games_played_share", "got_player": "got_a_player"}
NICE = {"grade": "tradeday_grade", "real_war": "realized_war", "real_gv": "realized_gamevalue",
        "real_played": "realized_war_played_only", "declared": "in_2017_22", "favoured": "favoured_by_grade",
        "ahead_war": "came_out_ahead_war", "ahead_gv": "came_out_ahead_gamevalue", "in_reg": "in_main_regression",
        "cd_cap": "main_cap_hit", "cd_career": "main_career_war", "cd_best": "main_best_season_war",
        "dump_trade": "trade_had_cap_dump", "own_clause_main": "own_main_player_has_clause",
        "own_clause_any": "own_any_player_has_clause", "own_seller": "own_sold_for_just_picks", "in_price": "in_price_regression",
        "price": "price_paid_main_player", "perf_value": "performance_value", "cap_cost": "cap_hit_cost",
        "perf_played": "performance_delivered", "first_club": "one_row_per_trade",
        "j_sold_picks": "grp_sold_for_just_picks", "j_deadline_buyer": "grp_deadline_buyer",
        "j_earlier_buyer": "grp_buyer_earlier_in_season", "j_rental": "grp_got_rental", "j_retained": "grp_retained_salary",
        "j_age28_31": "grp_age_28_31", "j_age32_plus": "grp_age_32_plus", "j_defence": "grp_defenceman", "j_clause": "grp_clause",
        "j_top15_below": "grp_top15_below_average", "j_one_for_many": "grp_got_one_for_two_or_more",
        "j_took_dump": "grp_took_cap_dump", "j_new_gm": "grp_new_gm_sold_old_contract", "j_cap": "grp_cap_hit"}
for _k, _v in _TYPE.items():
    NICE[f"m_{_k}"], NICE[f"a_{_k}"] = f"main_{_v}", f"any_{_v}"
assert all(len(v) <= 32 for v in NICE.values()) and len(set(NICE.values())) == len(NICE), "Stata names: unique, <= 32"
SHORT = {v: k for k, v in NICE.items()}


def plain(line):
    """The do-file's command and expect lines under the plain names (whole words only)."""
    import re
    return re.sub(r"\b[a-z][a-z0-9_]*\b", lambda m: NICE.get(m.group(0), m.group(0)), line)


YS = [("grade", "net_M"), ("real_war", "out_net_M"), ("real_gv", "gv_net_M"), ("real_played", "real_net_M")]


def log(s=""):
    print(s)
    LOG.append(s)


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "25_TESTS" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def eq(a, b, what):
    assert abs(float(a) - float(b)) < TOL, f"{what}: {a} against {b}"


def pfmt(p):
    return "p < 0.001" if p < 0.001 else (f"p = {p:.3f}" if p < 0.1 else f"p = {p:.2f}")


def expect(o, name):
    return f"{o.coef(name):+.4f} (se {o.sei(name):.4f}, {pfmt(o.pval(name))})"


def main():
    log(SCRIPT_VERSION)
    OR = load("one_regression")
    OR.log = lambda s="": None
    WO = load("who_overpaid")
    WO.log = lambda s="": None
    CD = load("clause_disguise")
    log(f"  on {OR.SCRIPT_VERSION}; {WO.SCRIPT_VERSION}; {CD.SCRIPT_VERSION}")
    key = ["trade_id", "club"]

    # ---- the rows: every complete club side, all trades ----
    s = pd.read_csv(EXT / "backtest_sides.csv")
    s = s[s["complete"].astype(bool)].copy()
    g = pd.read_csv(EXT / "backtest_sides_gv_adj.csv")[key + ["out_net_M"]].rename(columns={"out_net_M": "gv_net_M"})
    s = s.merge(g, on=key, how="left")
    d = s[key + ["trade_date", "net_M", "out_net_M", "gv_net_M", "real_net_M"]].copy()
    d["declared"] = (d["trade_date"] <= DECLARED_END).astype(int)
    # backtest.py's favoured club: the trade's highest grade, above zero, the first on a tie
    top = d.groupby("trade_id")["net_M"].transform("max")
    first_top = d.index.isin(d.groupby("trade_id")["net_M"].idxmax())
    d["favoured"] = (first_top & (d["net_M"] > 0) & (d["net_M"] == top)).astype(int)
    d["ahead_war"], d["ahead_gv"] = (d["out_net_M"] > 0).astype(int), (d["gv_net_M"] > 0).astype(int)
    log(f"  rows: {len(d):,} club sides of {d['trade_id'].nunique():,} complete trades ({int(d['declared'].sum()):,} sides "
        f"in the declared window)")

    # ---- Section 3: one_regression's frame, both rules ----
    A, B, t, f, _k, WO_ = OR.frame()
    ref = pd.read_csv(OUTPUT_DIR / "one_regression.csv")
    rows = []
    reg_cols = {}
    for rule, pre in (("main player rule", "m_"), ("any player rule", "a_")):
        cols = list(dict.fromkeys(ref.loc[ref["rule"] == rule, "col"]))
        reg_cols[rule] = [(c, pre + STEM[c]) for c in cols]
    for side, sign in ((A, 1.0), (B, -1.0)):
        r = pd.DataFrame({"trade_id": side.index, "club": side["club"].values})
        for rule in reg_cols:
            for c, nm in reg_cols[rule]:
                r[nm] = sign * (A[c].astype(float).values - B[c].astype(float).values)
        rows.append(r)
    sec3 = pd.concat(rows, ignore_index=True)
    sec3["in_reg"] = 1
    # the clause investigation's measures (clause_disguise.py's construction, main player rule)
    p = CD.player_measures(f, WO_)
    main = p.sort_values("cap_hit", ascending=False, kind="stable").drop_duplicates(key).set_index(key)
    meas = {}
    for nm, col in (("cd_cap", "cap_M"), ("cd_career", "career_war"), ("cd_best", "best_war")):
        va = np.array([main[col].get((tid, c), np.nan) if r == 1 else 0.0 for tid, c, r in zip(A.index, A["club"], A["recv"])], float)
        vb = np.array([main[col].get((tid, c), np.nan) if r == 1 else 0.0 for tid, c, r in zip(B.index, B["club"], B["recv"])], float)
        meas[nm] = np.r_[va - vb, vb - va]
    for nm, v in meas.items():
        sec3[nm] = v
    dump = ((A["t_dump"] == 1) | (B["t_dump"] == 1)).astype(int).values
    sec3["dump_trade"] = np.r_[dump, dump]
    d = d.merge(sec3, on=key, how="left")
    d["in_reg"] = d["in_reg"].fillna(0).astype(int)
    assert int(d["in_reg"].sum()) == 2 * len(A), "every regression side found among the complete sides"

    # own yes/no (groups_any_sides.csv): the clause under each rule, the seller
    ga = pd.read_csv(OUTPUT_DIR / "groups_any_sides.csv")[key + ["m_clause", "t_clause", "t_futures"]]
    ga = ga.rename(columns={"m_clause": "own_clause_main", "t_clause": "own_clause_any", "t_futures": "own_seller"})
    d = d.merge(ga, on=key, how="left")
    for c in ("own_clause_main", "own_clause_any", "own_seller"):
        d[c] = d[c].fillna(False).astype(int)

    # ---- Section 4 and part A: who_overpaid.build() ----
    GC, tw = WO.build()
    real = pd.read_csv(EXT / "backtest_sides.csv")[key + ["real_net_M"]].rename(columns={"real_net_M": "_r"})
    av = pd.read_csv(EXT / "backtest_assets.csv")[["asset_id", "realised_M"]].drop_duplicates("asset_id")
    tw = tw.merge(real, on=key, how="left").merge(av.rename(columns={"realised_M": "V_real"}), on="asset_id", how="left")
    b4 = tw[tw["perf"].notna() & tw["price"].notna() & tw["V_out"].notna()].copy()
    b4["perf_played"] = b4["V_real"] + b4["cost"]
    b4 = b4[key + ["price", "perf", "cost", "perf_played"]].rename(columns={"perf": "perf_value", "cost": "cap_cost"})
    b4["in_price"] = 1
    d = d.merge(b4, on=key, how="left")
    d["in_price"] = d["in_price"].fillna(0).astype(int)
    jcols = [c for _, c in GC.GROUPS[:-1]]
    n = tw.groupby("trade_id")["club"].transform("size")
    two = tw[n == 2].sort_values(key)
    JA = two.groupby("trade_id").nth(0).set_index("trade_id")
    JB = two.groupby("trade_id").nth(1).set_index("trade_id")
    J = pd.DataFrame({JSTEM[c]: JA[c].astype(int) - JB[c].astype(int) for c in jcols}, index=JA.index)
    J["j_cap"] = JA["cap_M"] - JB["cap_M"]
    J["trade_id"], J["club"], J["first_club"] = J.index, JA["club"].values, 1
    d = d.merge(J.reset_index(drop=True), on=key, how="left")
    d["first_club"] = d["first_club"].fillna(0).astype(int)

    d = d.rename(columns={"net_M": "grade", "out_net_M": "real_war", "gv_net_M": "real_gv", "real_net_M": "real_played"})
    d = d.sort_values(key).reset_index(drop=True)
    OUT.mkdir(exist_ok=True)
    d.rename(columns=NICE).to_csv(OUT / "findings_data.csv", index=False)
    D = pd.read_csv(OUT / "findings_data.csv")                         # every check reads the CSV as written
    D = D.rename(columns=SHORT)                                        # back to the short names the checks use
    log(f"  wrote findings_data.csv: {len(D):,} rows, {D.shape[1]} variables; in_reg {int(D['in_reg'].sum()):,} rows "
        f"({int(D['in_reg'].sum()) // 2} trades), in_price {int(D['in_price'].sum()):,}, first_club {int(D['first_club'].sum()):,}")

    # ================= checks, and the do-file's commands with their figures =================
    def do(comment, cmd, fig=None):
        DO.append(f"* {comment}")
        DO.append(cmd)
        if fig:
            DO.append(f"*   expect: {fig}")
        DO.append("")

    DO.extend([f"* findings_walkthrough.do -- written by {SCRIPT_VERSION}",
           "* Every regression in the findings document, from findings_data.csv. Each command's expected figure is",
           "* computed as Stata computes it (robust p-values on t with N-K degrees of freedom, clustered on G-1).", "",
           'cd "C:\\Users\\thoma\\Desktop\\xNPV\\30_OUTPUT\\stata"', 'import delimited using "findings_data.csv", clear', ""])

    # 1. test A (Section 2)
    br = pd.read_csv(OUTPUT_DIR / "backtest_results.csv")
    c = D[D["declared"] == 1]
    o = SE.OLS(c["real_war"], c[["grade"]], ["grade"])
    want = br.loc[br["test"].astype(str).str.startswith("A. slope") & (br["group"].astype(str) == "all complete trades"), "estimate"]
    eq(o.coef("grade"), want.iloc[0], "test A slope")
    share = float(c.loc[c["favoured"] == 1, "ahead_war"].mean())
    want = br.loc[br["test"].astype(str).str.startswith("A. share") & (br["group"].astype(str) == "all complete trades"), "estimate"]
    eq(share, want.iloc[0], "favoured share")
    og = SE.OLS(c["real_gv"], c[["grade"]], ["grade"])
    do("1. Section 2: realized value on the trade-day grade, declared window", "regress real_war grade if declared == 1, noconstant",
       f"slope {o.coef('grade'):.4f}; R-squared {o.r2:.4f}")
    do("1. Game Value", "regress real_gv grade if declared == 1, noconstant", f"slope {og.coef('grade'):.4f}; R-squared {og.r2:.4f}")
    do("1. the favoured club came out ahead (WAR, Game Value)", "mean ahead_war ahead_gv if declared == 1 & favoured == 1",
       f"{share:.4f}, {float(c.loc[c['favoured'] == 1, 'ahead_gv'].mean()):.4f}")
    log(f"  check 1: test A's slope {o.coef('grade'):.4f} and favoured share {share:.4f} equal backtest_results.csv (PASS)")

    # 2. Section 3's regression, both rules, four outcomes
    R = D[D["in_reg"] == 1]
    # v1.2 (Thomas, 2026-11-21: "Yes, switch"): one row a trade, the first club's (one_regression.py v2.4); the other row
    # is its mirror image, so which club is read does not change a coefficient or a robust standard error
    R1 = R[R["first_club"] == 1]
    assert len(R1) == len(R) // 2 == R1["trade_id"].nunique(), "one row for each of the regression's trades"
    n_ok = 0
    for rule, pre in (("main player rule", "m_"), ("any player rule", "a_")):
        names = [nm for _, nm in reg_cols[rule]]
        for ystata, ylab in zip([y for y, _ in YS], ["trade-day grade", "realized value, WAR", "realized value, Game Value",
                                                       "realized value, seasons played"]):
            o = SE.OLS(R1[ystata], R1[names], names, robust=True)
            rr = ref[(ref["rule"] == rule) & (ref["outcome"] == ylab)].set_index("col")
            for col, nm in reg_cols[rule]:
                eq(o.coef(nm), rr.at[col, "estimate"], f"{rule} {ylab} {nm}")
                eq(o.sei(nm), rr.at[col, "se"], f"{rule} {ylab} {nm} se")
                n_ok += 1
            figs = "; ".join(f"{nm} {o.coef(nm):+.4f} ({pfmt(o.pval(nm))})" for nm in names if nm.split("_", 1)[1] in
                             ("clause", "age28_31", "defence"))
            do(f"2. Section 3, {rule}, {NICE[ystata]}: the first club's side less the other's, one row a trade",
               f"regress {ystata} {' '.join(names)} if in_reg == 1 & first_club == 1, noconstant vce(robust)", figs)
    log(f"  check 2: Section 3's regression from the CSV equals one_regression.csv on {n_ok} coefficients and standard errors (PASS)")

    # 3. the clause investigation (main player rule)
    cdr = pd.read_csv(OUTPUT_DIR / "clause_disguise.csv")
    names = [nm for _, nm in reg_cols["main player rule"]]
    for lab, add, msk in (("+ cap hit", ["cd_cap"], None), ("+ career WAR and best season", ["cd_career", "cd_best"], None),
                          ("without the cap-dump trades", [], "nodump")):
        RR = R1[R1["dump_trade"] == 0] if msk else R1
        # one_regression.joint's rule: a yes/no difference non-zero in fewer than five trades is left out of the fit
        cont = {"m_production", "m_above_fcst", "m_games_share"} | set(add)
        use = [x for x in names + add if x in cont or (RR[x] != 0).sum() >= 5]
        for ystata, y in (("grade", "net_M"), ("real_war", "out_net_M")):
            o = SE.OLS(RR[ystata], RR[use], use, robust=True)
            w = cdr[(cdr["part"] == lab) & (cdr["rule"] == "main player rule") & (cdr["term"] == "clause") & (cdr["outcome"] == y)]
            eq(o.coef("m_clause"), w["estimate"].iloc[0], f"clause {lab} {y}")
            eq(o.sei("m_clause"), w["se"].iloc[0], f"clause {lab} {y} se")
            cond = "in_reg == 1 & first_club == 1" + (" & dump_trade == 0" if msk else "")
            do(f"3. the clause, {lab} ({NICE[ystata]})", f"regress {ystata} {' '.join(use)} if {cond}, noconstant vce(robust)",
               f"m_clause {expect(o, 'm_clause')}" + (f"; cd_cap {expect(o, 'cd_cap')}" if "cd_cap" in add else ""))
    log("  check 3: the clause with the cap hit, with reputation and without the cap dumps equal clause_disguise.csv (PASS)")

    # 4. Step 4's averages: the clause (each rule) and the sellers, declared window
    gar = pd.read_csv(OUTPUT_DIR / "groups_any.csv")
    gar = gar[(gar["part"] == "v1.1 group mean, declared window") & (gar["group"] == "a clause")]
    for own, rule in (("own_clause_main", "main player"), ("own_clause_any", "any player")):
        cc = D[(D["declared"] == 1) & (D[own] == 1)]
        figs = []
        for ystata, y in (("grade", "priced"), ("real_war", "outcome, WAR")):
            o = SE.OLS(cc[ystata], np.ones((len(cc), 0)), [], cluster=cc["trade_id"], const=True)
            w = gar[(gar["rule"] == rule) & (gar["outcome"] == y)]
            eq(o.coef("_cons"), w["estimate"].iloc[0], f"clause alone {rule} {y}")
            eq(o.sei("_cons"), w["se"].iloc[0], f"clause alone {rule} {y} se")
            figs.append(f"{ystata} {o.coef('_cons'):+.4f} (se {o.sei('_cons'):.4f})")
        do(f"4. the average club acquiring a player with a clause, {rule} rule", f"mean grade real_war if declared == 1 & {own} == 1, vce(cluster trade_id)",
           "; ".join(figs) + f"; {len(cc)} clubs")
    gcl = pd.read_csv(EXT / "groups_clustered.csv")
    gcl = gcl[(gcl["scope"] == "DECLARED WINDOW") & (gcl["part"] == "group mean") & (gcl["group"] == "futures for players")]
    cc = D[(D["declared"] == 1) & (D["own_seller"] == 1)]
    figs = []
    for ystata, y in (("grade", "priced"), ("real_war", "outcome, WAR")):
        o = SE.OLS(cc[ystata], np.ones((len(cc), 0)), [], cluster=cc["trade_id"], const=True)
        w = gcl[gcl["outcome"] == y]
        eq(o.coef("_cons"), w["estimate"].iloc[0], f"sellers {y}")
        eq(o.sei("_cons"), w["se"].iloc[0], f"sellers {y} se")
        figs.append(f"{ystata} {o.coef('_cons'):+.4f} (se {o.sei('_cons'):.4f})")
    do("4. the average club selling a player for just picks and prospects", "mean grade real_war if declared == 1 & own_seller == 1, vce(cluster trade_id)",
       "; ".join(figs) + f"; {len(cc)} clubs")
    log("  check 4: the clause and seller averages equal groups_any.csv and groups_clustered.csv (PASS)")

    # 5. the sellers with the cap hit held (who_overpaid part A, declared window, one row a trade, robust)
    wor = pd.read_csv(OUTPUT_DIR / "who_overpaid.csv")
    J1 = D[(D["first_club"] == 1) & (D["declared"] == 1)]
    jn = [JSTEM[c] for c in jcols] + ["j_cap"]
    jn = [x for x in jn if (J1[x] != 0).sum() >= 5]
    for ystata, y in (("grade", "net_M"), ("real_war", "out_net_M"), ("real_gv", "gv_net_M")):
        o = SE.OLS(J1[ystata], J1[jn], jn, robust=True)
        w = wor[(wor["part"] == "A, scope") & (wor["term"] == "futures for players") & (wor["scope"] == "declared window") & (wor["outcome"] == y)]
        eq(o.coef("j_sold_picks"), w["with"].iloc[0], f"sellers with the cap hit {y}")
        eq(o.sei("j_sold_picks"), w["se"].iloc[0], f"sellers with the cap hit {y} se")
        do(f"5. Section 4: the sellers with the cap hit of the player sold held fixed ({NICE[ystata]})",
           f"regress {ystata} {' '.join(jn)} if first_club == 1 & declared == 1, noconstant vce(robust)",
           f"j_sold_picks {expect(o, 'j_sold_picks')}; j_cap {expect(o, 'j_cap')}")
    log("  check 5: the sellers with the cap hit held equal who_overpaid.csv (PASS)")

    # 6. Section 4's price fits (all trades)
    woc = pd.read_csv(OUTPUT_DIR / "who_overpaid_checks.csv")
    woc = woc[(woc["check"].astype(str) == "2") & (woc["scope"] == "all trades")].set_index("model")
    P = D[D["in_price"] == 1]
    for lab, x in (("the model's performance value (part B)", "perf_value"), ("the same, seasons played only", "perf_played")):
        o = SE.OLS(P["price"], P[[x, "cap_cost"]], [x, "cap_cost"], cluster=P["trade_id"], const=True)
        eq(o.coef(x), woc.at[lab, "perf"], f"price on {x}")
        eq(o.sei(x), woc.at[lab, "perf_se"], f"price on {x} se")
        eq(o.coef("cap_cost"), woc.at[lab, "cost"], f"price on cost ({x})")
        do(f"6. Section 4: the price paid on {NICE[x]} and the cap cost", f"regress price {x} cap_cost if in_price == 1, vce(cluster trade_id)",
           f"{x} {expect(o, x)}; cap_cost {expect(o, 'cap_cost')}")
    first = sm.OLS(P["perf_value"], sm.add_constant(P[["perf_played", "cap_cost"]])).fit()
    second = sm.OLS(P["price"], sm.add_constant(pd.DataFrame({"hat": first.fittedvalues, "cap_cost": P["cap_cost"]}))).fit()
    lab = "two-stage, instrument: seasons played"
    eq(second.params["hat"], woc.at[lab, "perf"], "two-stage perf")
    eq(second.params["cap_cost"], woc.at[lab, "cost"], "two-stage cost")
    do("6. Section 4: two-stage least squares, the performance value instrumented by what the seasons played delivered",
       "ivregress 2sls price cap_cost (perf_value = perf_played) if in_price == 1, vce(cluster trade_id)",
       f"perf_value {second.params['hat']:+.4f}; cap_cost {second.params['cap_cost']:+.4f} (the document's standard errors are "
       f"from 2,000 resamples of trades: 0.19 and 0.16; Stata's clustered ones differ)")
    do("6. its first stage", "regress perf_value perf_played cap_cost if in_price == 1",
       f"perf_played {first.params['perf_played']:+.4f} (t = {first.tvalues['perf_played']:.1f})")
    log("  check 6: Section 4's price fits equal who_overpaid_checks.csv (two-stage: coefficients) (PASS)")

    out = [x if x.startswith("* ") and not x.startswith("*   expect:") else plain(x) for x in DO]
    (OUT / "findings_walkthrough.do").write_text("\n".join(out), encoding="utf-8")
    (OUT / "stata_export_findings_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"  wrote findings_walkthrough.do ({sum(1 for x in DO if x.startswith(('regress', 'mean', 'ivregress')))} commands)")


if __name__ == "__main__":
    main()
