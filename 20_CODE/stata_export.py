"""
stata_export.py -- the draft pick curve's and the prospect model's regression data as flat CSVs, for Stata (v1.2).

v1.2 (2026-11-08; Thomas: "ensure that all the stata stuff is simple and ready to go", "comprehensive as far as
regressions we can run"): every derived variable a test in the documents uses is a column, so the Stata walkthrough
needs no generate line (draft_players.csv: p_nhler, log_pick, log_pick_sq, p_star_sq, is_d_draft, p_star_x_d_draft,
p_star_trend; prospect_seasons.csv: s_early, age_term, flat_term, prod_sq_x_defence, s_early_x_defence, age_term_19,
age_term_20); and every figure the walkthrough's commands should print, computed from the CSVs as Stata computes it
(stata_expected.py), is written to stata/expected_picks_prospects.json for stata_refresh.py to put in the do-file.
The pick curve's tests in "Valuing Players, Draft Picks, and Prospects" (the nested table, one star value for every
draft, the trend, defencemen, the other shapes) are checked against model_doc_figures.py's numbers where they exist.

WHY: every regression in "Valuing Draft Picks" and "Valuing Prospects" should be reproducible by hand in Stata from
files on disk (supervisor meeting, 2026-10-23). This script writes those files. It builds no data of its own: every
row and every variable comes from the functions the model runs (prospect_values.star_values, production_rates,
production_fits, production_features), so the CSVs cannot drift from the model.

OUTPUTS (OUTPUT_DIR/stata/; the codebook is 40_DOCS/Stata_Data_Codebook.md):
  draft_players.csv       one row per drafted player, 2007-2017 (2,322): the pick curve's outcome (his career
                          net present value) and his draft position's star probability.
  prospect_seasons.csv    one row per drafted player and season D+1 to D+8 (k = 0..7, seasons to 2025-26): the
                          prospect model's outcome (his remaining net present value from that season) and every input, with the
                          flags that pick out each regression's sample.
  production_seasons.csv  one row per Elite Prospects season line (player, season, league) for the 2007-2017
                          skater draftees: games, points and the NHLe factor, from which nhle82 is built.
  stata_export_log.txt    the run log, with every check below.

CHECKS (each must PASS or the script stops; each regression is refitted from the CSV as written, read back from disk):
  1. The prospect-season rows used by the model equal the CSV's sample flags, row for row, with the same outcome and
     inputs (to 1e-9).
  2. The pick curve: draft_players.csv refitted (through zero, robust errors) gives pick_curve_scales.csv's star
     value and standard error.
  3. The star values by season (Valuing Prospects Table 2): prospect_seasons.csv refitted gives prospect_values'
     star values and clustered standard errors.
  4. The adopted model (Table 9): prospect_seasons.csv refitted with years past first eligibility gives
     prospect_values' coefficients; refitted with age less 18 (the document's form) it gives the same fitted values
     and age coefficient, with production's coefficient shifted by k times the age coefficient.
  5. production_seasons.csv, collapsed as the model collapses it, gives the model's NHLe rate for every
     player-season.

Run from the repo root:  python 20_CODE/stata_export.py   (after prospect_values.py; reads its inputs only)
"""

import sqlite3

import numpy as np
import pandas as pd
import statsmodels.api as sm

import prospect_values as PV
import stata_expected as SE

SCRIPT_VERSION = "stata_export.py v1.2 (2026-11-08)"   # v1.2: test columns, expected figures; v1.1: prod_x_defence
OUTPUT_DIR, SOURCE_DIR = PV.OUTPUT_DIR, PV.SOURCE_DIR
OUT = OUTPUT_DIR / "stata"
TOL = 1e-9
GROUP_NUM = {"0": 1, "1": 2, "2": 3, "3": 4, "4+": 5}              # season_group 1..5 = D+1, D+2, D+3, D+4, D+5 on
GROUP_LABEL = {1: "D+1", 2: "D+2", 3: "D+3", 4: "D+4", 5: "D+5 and later"}

LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def season_label(y):
    return f"{y}-{(y + 1) % 100:02d}"


def ols(y, X, groups=None):
    """Through zero (no constant), as every pick and prospect regression. Clustered errors when groups is given
    (Stata: vce(cluster player_id)), robust HC1 otherwise (Stata: vce(robust)); both carry Stata's small-sample
    corrections."""
    if groups is None:
        return sm.OLS(y, X).fit(cov_type="HC1")
    return sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(groups)[0]})


def stacked(frame, cols_by_group):
    """One regression on every row of frame: each column of cols_by_group[g] multiplied by the indicator for season
    group g, through zero, errors clustered by player (prospect_values.fit_stacked, on the CSV's own columns)."""
    blocks, names = [], []
    for g in sorted(cols_by_group):
        on = (frame["season_group"] == g).values
        for c in cols_by_group[g]:
            blocks.append(np.where(on, frame[c].values, 0.0))
            names.append((g, c))
    m = ols(frame["remaining_npv_m"].values, np.column_stack(blocks), frame["player_id"].values)
    return {n: (float(m.params[i]), float(m.bse[i])) for i, n in enumerate(names)}, m


def expected_figures(P, R):
    """v1.2: what each command in the walkthrough's Parts 1 and 2 should print, from the CSVs as written, computed as
    Stata computes it (stata_expected.py). Step numbers are the do-file's. Where the documents' own runs recorded the
    same test, its Wald statistic is checked against them (chi2 = F x q) and the script stops on a difference."""
    E = SE.Expected()
    log("\nEXPECTED FIGURES (Parts 1 and 2 of the do-file; Stata's conventions)")
    mdoc = OUTPUT_DIR / "model_doc" / "numbers.json"
    pdoc = OUTPUT_DIR / "prospect_doc" / "numbers.json"
    import json
    MD = json.loads(mdoc.read_text(encoding="utf-8")) if mdoc.exists() else None
    PD = json.loads(pdoc.read_text(encoding="utf-8")) if pdoc.exists() else None

    def same(label, mine, doc, tol=1e-6):
        """A figure the documents recorded: stop unless this CSV gives it back."""
        assert abs(mine - doc) <= tol * max(1.0, abs(doc)), (label, mine, doc)
        log(f"    = the document's run: {label} {doc:.6g} (PASS)")

    # ---- Part 1: draft picks ----------------------------------------------------------------------------------------
    pk = P[P["excluded_deceased"] == 0].reset_index(drop=True)
    y = pk["career_npv_m"]
    m1 = SE.OLS(y, pk[["p_star"]], ["p_star"], robust=True)
    sc = pd.read_csv(OUTPUT_DIR / "pick_curve_scales.csv").set_index("scale_kind")
    assert abs(m1.coef("p_star") - sc.loc["main", "scale_M"]) < TOL
    E.add("S1_B", m1.coef("p_star"), "{:.3f}"); E.add("S1_SE", m1.sei("p_star"), "{:.3f}")
    E.add("S1_N", f"{m1.n:,}"); E.add("S1_R2", m1.r2, "{:.4f}")
    log(f"  step 1, the pick curve: star value {m1.coef('p_star'):.4f} ({m1.sei('p_star'):.4f}), N {m1.n}, "
        f"R-squared {m1.r2:.4f} (uncentered)")

    sub = pk[~pk["draft_year"].isin([2015, 2016])]
    m2 = SE.OLS(sub["career_npv_m"], sub[["p_star"]], ["p_star"], robust=True)
    assert abs(m2.coef("p_star") - sc.loc["sensitivity", "scale_M"]) < TOL
    E.add("S2_B", m2.coef("p_star"), "{:.3f}"); E.add("S2_SE", m2.sei("p_star"), "{:.3f}"); E.add("S2_N", f"{m2.n:,}")
    log(f"  step 2, without the 2015 and 2016 drafts: {m2.coef('p_star'):.4f} ({m2.sei('p_star'):.4f}) = the sensitivity")

    shapes = MD["picks"]["shapes"] if MD else None
    m3a = SE.OLS(y, pk[["p_star"]], ["p_star"], robust=True, const=True)
    E.add("S3A_B", m3a.coef("p_star"), "{:.3f}"); E.add("S3A_C", m3a.coef("_cons"), "{:.3f}"); E.p("S3A_CP", m3a.pval("_cons"))
    if shapes:
        same("+ an intercept, the intercept", m3a.coef("_cons"), shapes["star probability and an intercept"]["terms"]["intercept"]["b"])
    D = pd.get_dummies(pk["draft_year"], dtype=float)
    yrs = [int(c) for c in D.columns]
    m3b = SE.OLS(y, np.column_stack([pk["p_star"], D.to_numpy()]), ["p_star"] + [f"{c}.draft_year" for c in yrs], robust=True)
    F3b, p3b = m3b.zero([f"{c}.draft_year" for c in yrs])
    E.add("S3B_B", m3b.coef("p_star"), "{:.3f}"); E.add("S3B_F", F3b, "{:.2f}"); E.p("S3B_P", p3b)
    if MD:
        same("draft intercepts jointly zero, chi2", F3b * len(yrs), MD["picks"]["draft_intercepts"]["joint_zero"]["chi2"])
    m3c = SE.OLS(y, pk[["p_star", "pick"]], ["p_star", "pick"], robust=True, const=True)
    E.add("S3C_B", m3c.coef("p_star"), "{:.3f}"); E.add("S3C_PICK", m3c.coef("pick"), "{:.4f}")
    E.p("S3C_PICKP", m3c.pval("pick")); E.p("S3C_CP", m3c.pval("_cons"))
    m3d = SE.OLS(y, pk[["p_star", "p_nhler"]], ["p_star", "p_nhler"], robust=True)
    E.add("S3D_B", m3d.coef("p_star"), "{:.3f}"); E.add("S3D_N", m3d.coef("p_nhler"), "{:.3f}"); E.p("S3D_NP", m3d.pval("p_nhler"))
    if shapes:
        same("+ NHL-player probability, its coefficient", m3d.coef("p_nhler"), shapes["star and NHL-player probabilities"]["terms"]["p_nhler"]["b"])
    log(f"  step 3: + intercept {m3a.coef('_cons'):.4f} (p {m3a.pval('_cons'):.4f}); draft intercepts F {F3b:.3f} "
        f"(p {p3b:.4f}); + pick p {m3c.pval('pick'):.4f}; + NHL-player probability p {m3d.pval('p_nhler'):.4f}")

    Xd = np.column_stack([pk["p_star"] * (pk["draft_year"] == c) for c in yrs])
    m4 = SE.OLS(y, Xd, [f"{c}.draft_year#c.p_star" for c in yrs], robust=True)
    F4, p4 = m4.test([{f"{yrs[i]}.draft_year#c.p_star": 1.0, f"{yrs[i + 1]}.draft_year#c.p_star": -1.0}
                      for i in range(len(yrs) - 1)])
    lo_, hi_ = int(np.argmin(m4.b)), int(np.argmax(m4.b))
    E.add("S4_LO", f"{m4.b[lo_]:.2f} ({yrs[lo_]})"); E.add("S4_HI", f"{m4.b[hi_]:.2f} ({yrs[hi_]})")
    E.add("S4_F", F4, "{:.2f}"); E.p("S4_P", p4)
    if MD:
        same("one star value for every draft, chi2", F4 * (len(yrs) - 1), MD["picks"]["equal_test"]["chi2"])
    m4t = SE.OLS(y, pk[["p_star", "p_star_trend"]], ["p_star", "p_star_trend"], robust=True)
    m4s = SE.OLS(sub["career_npv_m"], sub[["p_star", "p_star_trend"]], ["p_star", "p_star_trend"], robust=True)
    E.add("S4_T", m4t.coef("p_star_trend"), "{:.3f}"); E.p("S4_TP", m4t.pval("p_star_trend"))
    E.add("S4_TS", m4s.coef("p_star_trend"), "{:.3f}"); E.p("S4_TSP", m4s.pval("p_star_trend"))
    if MD:
        same("the trend", m4t.coef("p_star_trend"), MD["picks"]["trend"]["all"]["b"])
        same("the trend without 2015 and 2016", m4s.coef("p_star_trend"), MD["picks"]["trend"]["without_2015_2016"]["b"])
    log(f"  step 4: per draft {m4.b[lo_]:.2f} to {m4.b[hi_]:.2f}, equal F {F4:.3f} (p {p4:.4f}); trend "
        f"{m4t.coef('p_star_trend'):+.3f} (p {m4t.pval('p_star_trend'):.4f}), without 2015-16 "
        f"{m4s.coef('p_star_trend'):+.3f} (p {m4s.pval('p_star_trend'):.4f})")

    m5 = SE.OLS(y, pk[["p_star", "p_star_x_d_draft"]], ["p_star", "p_star_x_d_draft"], robust=True)
    E.add("S5_F", m5.coef("p_star"), "{:.2f}"); E.add("S5_DADD", m5.coef("p_star_x_d_draft"), "{:.2f}")
    E.add("S5_D", m5.coef("p_star") + m5.coef("p_star_x_d_draft"), "{:.2f}"); E.p("S5_P", m5.pval("p_star_x_d_draft"))
    E.add("S5_R2", m5.r2, "{:.4f}")
    if PD:
        same("defencemen's star value", m5.coef("p_star") + m5.coef("p_star_x_d_draft"), PD["pick_def"]["d"])
    log(f"  step 5: forwards and goaltenders {m5.coef('p_star'):.3f}, defencemen "
        f"{m5.coef('p_star') + m5.coef('p_star_x_d_draft'):.3f} (p {m5.pval('p_star_x_d_draft'):.4f})")

    for key, cols, const in (("S6A", ["pick"], True), ("S6B", ["log_pick"], True),
                             ("S6C", ["log_pick", "log_pick_sq"], True), ("S6D", ["p_star", "p_star_sq"], False)):
        m = SE.OLS(y, pk[cols], cols, robust=True, const=const)
        E.add(key, "; ".join(f"{n} {m.coef(n):.4f}" for n in m.names))
        log(f"  step 6 ({key}): " + E.v[key])

    # ---- Part 2: prospects ------------------------------------------------------------------------------------------
    st = R[R["sample_star"] == 1].reset_index(drop=True)
    sp = R[R["sample_production"] == 1].reset_index(drop=True)
    G = [1, 2, 3, 4, 5]
    LAB = {g: GROUP_LABEL[g].replace(" and later", "+") for g in G}

    def stk(frame, cols, groups=G):
        X, names = SE.interact(frame, {g: cols for g in groups})
        keep = [j for j in range(X.shape[1]) if np.any(X[:, j] != 0)]        # Stata omits an all-zero column
        return SE.OLS(frame["remaining_npv_m"], X[:, keep], [names[j] for j in keep], cluster=frame["player_id"])

    def present(m, col):
        return [f"{g}.{col}" for g in G if f"{g}.{col}" in m.names]

    def chk(label, m_test, key):
        """the prospect document's chi2 for the same test (prospect_doc_figures.py)."""
        if PD is None:
            return
        rec = PD["tests"].get(key) if key in PD.get("tests", {}) else PD.get(key)
        if isinstance(rec, dict) and "chi2" in rec:
            same(label + ", chi2", m_test[0] * rec["df"], rec["chi2"])

    m7 = stk(st, ["p_star"])
    E.add("S7", "; ".join(f"{LAB[g]} {m7.coef(f'{g}.p_star'):.2f} ({m7.sei(f'{g}.p_star'):.2f})" for g in G))
    sv = pd.read_csv(OUTPUT_DIR / "prospect_star_values.csv")
    sv = sv[sv["left_out"] == "none"].set_index("k_group")
    for k_, g in GROUP_NUM.items():
        assert abs(m7.coef(f"{g}.p_star") - sv.loc[k_, "star_value_M"]) < TOL
    E.add("S7_N", f"{m7.n:,}")
    log(f"  step 7, star value by season: {E.v['S7']}")
    t1 = m7.test([{f"{g}.p_star": 1.0, f"{g + 1}.p_star": -1.0} for g in G[:-1]])
    # equal drops: (b2 - b1) = (b3 - b2) and (b3 - b2) = (b4 - b3)
    t2 = m7.test([{"1.p_star": 1.0, "2.p_star": -2.0, "3.p_star": 1.0}, {"2.p_star": 1.0, "3.p_star": -2.0, "4.p_star": 1.0}])
    t3 = m7.testnl([lambda b: b["2.p_star"] ** 2 - b["1.p_star"] * b["3.p_star"],
                    lambda b: b["3.p_star"] ** 2 - b["2.p_star"] * b["4.p_star"]])
    for key, t in (("S8_ONE", t1), ("S8_LINE", t2), ("S8_PCT", t3)):
        E.add(key + "_F", t[0], "{:.2f}"); E.p(key + "_P", t[1])
    chk("one value for every season", t1, "fade_wald_one"); chk("straight-line decline", t2, "fade_wald_steps")
    chk("same percentage decline", t3, "fade_wald_ratio")
    log(f"  step 8: one value p {t1[1]:.4f}; straight line p {t2[1]:.4f}; same percentage p {t3[1]:.4f}")

    m9a = stk(sp, ["p_star", "nhle82"])
    t = m9a.zero(present(m9a, "nhle82")); E.p("S9_LIN", t[1]); chk("linear production", t, "lin_vs_slot")
    m9b = stk(sp, ["p_star", "nhle82", "nhle82_sq"])
    t = m9b.zero(present(m9b, "nhle82") + present(m9b, "nhle82_sq")); E.p("S9_PROD", t[1]); chk("production", t, "prod_vs_slot")
    t = m9b.zero(present(m9b, "nhle82_sq")); E.p("S9_SQ", t[1]); chk("production squared", t, "sq_given_lin")
    t = m9b.zero(["4.p_star", "5.p_star"]); E.p("S9_LATE", t[1]); chk("draft position from D+4", t, "slot_late")
    m9c = stk(sp, ["s_early", "nhle82", "nhle82_sq"])
    t = m9c.zero(present(m9c, "nhle82")); E.p("S9_NOLIN", t[1]); chk("without linear production", t, "lin_s2")
    log(f"  step 9: linear {E.v['S9_LIN']}; production {E.v['S9_PROD']}; squared {E.v['S9_SQ']}; "
        f"draft position D+4 on {E.v['S9_LATE']}; linear on candidate (5) {E.v['S9_NOLIN']}")

    m10a = stk(sp, ["s_early", "nhle82", "nhle82_sq", "flat_term"])
    t = m10a.zero(present(m10a, "flat_term")); E.p("S10_FLAT", t[1]); chk("age as a flat amount", t, "flat")
    m10b = stk(sp, ["s_early", "nhle82", "nhle82_sq", "age_term"])
    t = m10b.zero(present(m10b, "age_term")); E.p("S10_DISC", t[1]); chk("age discounting production", t, "disc")
    m10c = stk(sp, ["s_early", "nhle82", "nhle82_sq", "flat_term", "age_term"])
    t = m10c.zero(present(m10c, "flat_term")); E.p("S10_FGD", t[1]); chk("flat given discount", t, "flat_given_disc")
    t = m10c.zero(present(m10c, "age_term")); E.p("S10_DGF", t[1]); chk("discount given flat", t, "disc_given_flat")
    m10d = stk(sp, ["s_early", "nhle82", "nhle82_sq", "prod_x_age_m18"])
    t = m10d.zero(["5.prod_x_age_m18"]); E.p("S10_LATE", t[1]); chk("the discount from D+5 on", t, "age_late")
    log(f"  step 10: flat {E.v['S10_FLAT']}; discount {E.v['S10_DISC']}; flat given discount {E.v['S10_FGD']}; "
        f"discount given flat {E.v['S10_DGF']}; discount from D+5 {E.v['S10_LATE']}")

    adopted = ["s_early", "nhle82", "nhle82_sq", "age_term", "prod_x_defence"]
    m11 = stk(sp, adopted)
    t = m11.zero(present(m11, "prod_x_defence")); E.p("S11_DEF", t[1]); chk("defenceman x production", t, "def")
    t = m11.zero(["5.nhle82", "5.nhle82_sq"]); E.p("S11_LATEPROD", t[1]); chk("production from D+5 on", t, "late_prod")
    m11q = stk(sp, adopted + ["prod_sq_x_defence"])
    t = m11q.zero(present(m11q, "prod_sq_x_defence")); E.p("S11_DQ", t[1]); chk("defenceman x production squared", t, "dq")
    m11s = stk(sp, adopted + ["s_early_x_defence"])
    t = m11s.zero(present(m11s, "s_early_x_defence")); E.p("S11_DS", t[1]); chk("defenceman x draft position", t, "ds")
    # the adopted model's coefficients, against prospect_values' (age as the document writes it)
    names = {"s_early": "S", "nhle82": "P", "nhle82_sq": "P2", "age_term": "PxAge", "prod_x_defence": "PxD"}
    for g in G:
        E.add(f"S12_{g}", "; ".join(f"{names[c]} {m11.coef(f'{g}.{c}'):.4f} ({m11.sei(f'{g}.{c}'):.4f})"
                                    for c in adopted if f"{g}.{c}" in m11.names))
    E.add("S12_N", f"{m11.n:,}"); E.add("S12_R2", m11.r2, "{:.4f}")
    log(f"  step 11: defenceman x production {E.v['S11_DEF']}; production from D+5 {E.v['S11_LATEPROD']}; "
        f"x production squared {E.v['S11_DQ']}; x draft position {E.v['S11_DS']}")
    log(f"  step 12, the adopted model ({m11.n:,} prospect-seasons, R-squared {m11.r2:.4f} uncentered):")
    for g in G:
        log(f"    {LAB[g]:<5} {E.v[f'S12_{g}']}")

    for c, col in ((18, "age_term"), (19, "age_term_19"), (20, "age_term_20")):
        m = stk(sp, ["s_early", "nhle82", "nhle82_sq", col, "prod_x_defence"])
        E.p(f"S13_{c}", m.zero(present(m, "nhle82"))[1])
    log(f"  step 13: linear production zero, age from 18 / 19 / 20: {E.v['S13_18']} / {E.v['S13_19']} / {E.v['S13_20']}")
    E.write(OUT / "expected_picks_prospects.json")
    log(f"  wrote expected_picks_prospects.json ({len(E.v)} figures)")


def main():
    log(SCRIPT_VERSION)
    OUT.mkdir(parents=True, exist_ok=True)
    pc_log = (OUTPUT_DIR / "pick_curve_log.txt").read_text(encoding="utf-8").splitlines()[0]
    pv_log = (OUTPUT_DIR / "prospect_values_log.txt").read_text(encoding="utf-8").splitlines()[0]
    log(f"  built from: {pc_log}; {pv_log} (outputs in {OUTPUT_DIR.resolve()})")
    if pv_log != PV.SCRIPT_VERSION:
        log(f"  NOTE: prospect_values_log.txt was written by {pv_log}, the code here is {PV.SCRIPT_VERSION}")

    # ---- the model's own rows -----------------------------------------------------------------------------------
    sv, fitrows = PV.star_values()            # every drafted player 2007-2017 (deceased out) x k = 0..7, to 2025-26
    rates = PV.production_rates()             # {(EP id, season): NHLe points per 82}, seasons of 10+ games
    fits, prow = PV.production_fits(fitrows, rates)   # the skater prospect-seasons the adopted model is fitted on

    # ---- identities: who each drafted player is ------------------------------------------------------------------
    pl = pd.read_csv(OUTPUT_DIR / "pick_curve_players.csv")
    link = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv", parse_dates=["birthDate"])
    link = link[["draftYear", "overallPickNumber", "birthDate"]].rename(columns={"overallPickNumber": "pick"})
    con = sqlite3.connect(OUTPUT_DIR / "ep_out" / "ep_prospects.db")
    ep = pd.read_sql("select draft_year draftYear, draft_overall pick, ep_player_id, position_ep "
                     "from ep_draft_selections", con)
    ep = ep[ep["draftYear"].between(2007, 2017)]
    assert not ep.duplicated(["draftYear", "pick"]).any(), "two Elite Prospects rows for one draft position"
    assert not link.duplicated(["draftYear", "pick"]).any(), "two linkage rows for one draft position"
    ep["ep_player_id"] = pd.to_numeric(ep["ep_player_id"]).astype("Int64").astype(str).replace("<NA>", "")
    ident = (pl.merge(link, on=["draftYear", "pick"], how="left")
               .merge(ep, on=["draftYear", "pick"], how="left"))
    ident["player_id"] = ident["draftYear"] * 1000 + ident["pick"]              # e.g. 2017013 = 2017, 13th overall
    ident["is_defence"] = ident["position_ep"].astype(str).str.startswith("D").astype(int)   # as prospect_nhle_look

    # ---- 1. draft_players.csv --------------------------------------------------------------------------------------
    players = pd.DataFrame({
        "player_id": ident["player_id"], "draft_year": ident["draftYear"], "pick": ident["pick"],
        "round": ident["round"], "player_name": ident["player"], "position": ident["position"],
        "position_ep": ident["position_ep"], "is_goalie": ident["is_goalie"].astype(int),
        "is_defence": ident["is_defence"], "team": ident["team"],
        "birth_date": ident["birthDate"].dt.strftime("%Y-%m-%d"), "ep_player_id": ident["ep_player_id"],
        "p_star": ident["p_star"], "control_ends": ident["window_end"], "nhl_seasons": ident["nhl_seasons"],
        "career_war": ident["war"], "route": ident["route"],
        "career_npv_m": ident["surplus"] / 1e6,                                     # the pick curve's outcome
        "excluded_deceased": ident["excluded_deceased"].astype(int)})
    # v1.2: the variables of the pick curve's tests ("Valuing Players, Draft Picks, and Prospects", Section 6)
    bac = pd.read_csv(SOURCE_DIR / "draft_slot_baseline.csv").set_index("draft_pick")
    players["p_nhler"] = players["pick"].map(bac["p_nhler"])                     # Bacon's NHL-player probability
    assert players["p_nhler"].notna().all()
    players["log_pick"] = np.log(players["pick"].astype(float))
    players["log_pick_sq"] = players["log_pick"] ** 2
    players["p_star_sq"] = players["p_star"] ** 2
    # the pick curve's defenceman test reads the NHL draft record's position (defence_terms_look.py), not Elite
    # Prospects' (is_defence, the prospect model's)
    players["is_d_draft"] = (players["position"].astype(str) == "D").astype(int)
    players["p_star_x_d_draft"] = players["p_star"] * players["is_d_draft"]
    players["p_star_trend"] = players["p_star"] * (players["draft_year"] - 2012)    # model_doc_figures: draft - 2012
    players.to_csv(OUT / "draft_players.csv", index=False)

    # ---- 2. prospect_seasons.csv ------------------------------------------------------------------------------------
    d = fitrows.merge(ident[["draftYear", "pick", "player_id", "player", "position", "position_ep", "is_goalie",
                             "is_defence", "birthDate", "ep_player_id", "window_end"]],
                      on=["draftYear", "pick"], how="left", validate="many_to_one")
    d["season"] = d["draftYear"] + d["k"]
    sk = ~d["is_goalie"].astype(bool)
    assert d["player_id"].notna().all() and d.loc[sk, "birthDate"].notna().all()   # as production_fits (skaters)
    assert (d.loc[sk, "ep_player_id"] != "").all(), "a skater without an Elite Prospects id"
    # v1.1: is_d, so production_features builds defenceman x production as the model does (prospect_values v1.13)
    feats = PV.production_features(d.loc[sk, ["ep_player_id", "season", "k", "birthDate", "is_defence"]]
                                   .rename(columns={"is_defence": "is_d"}).reset_index(drop=True), rates)
    feats.index = d.index[sk]
    age = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25   # as production_features
    rows = pd.DataFrame({
        "player_id": d["player_id"], "draft_year": d["draftYear"], "pick": d["pick"], "player_name": d["player"],
        "position": d["position"], "position_ep": d["position_ep"], "is_goalie": d["is_goalie"].astype(int),
        "is_defence": d["is_defence"], "birth_date": d["birthDate"].dt.strftime("%Y-%m-%d"),
        "ep_player_id": d["ep_player_id"], "p_star": d["p_star"],
        "k": d["k"], "dplus": d["k"] + 1, "season": d["season"], "season_label": d["season"].map(season_label),
        "season_group": d["k_group"].astype(str).map(GROUP_NUM), "season_group_label": None,
        "in_control": (d["season"] < d["window_end"]).astype(int),
        "prospect": d["prospect"].astype(int),
        "sample_star": d["prospect"].astype(int),                                  # Section 1: every position
        "sample_production": (d["prospect"] & sk).astype(int),                     # Sections 2-3: skaters
        "remaining_npv_m": d["remaining_M"],
        "nhle82": feats["nhle82"], "nhle82_sq": feats["nhle82_sq"],
        "n_prod_seasons": feats["n_prod_seasons"], "no_record": feats["no_record"],
        "age": age, "age_m18": age - 18.0,
        "prod_x_age_m18": feats["nhle82"] * (age - 18.0),                           # the document's age term
        "years_past_elig": feats["past_elig"], "prod_x_years_past_elig": feats["prod_x_age"],   # the code's
        "prod_x_defence": feats["d_x_prod"]})                                        # v1.1: production x is_defence
    rows["season_group_label"] = rows["season_group"].map(GROUP_LABEL)
    assert rows["season_group"].notna().all()
    # v1.2: the variables of the prospect document's tests, so Stata needs no generate line
    early, upto4 = (rows["season_group"] <= 3).astype(float), (rows["season_group"] <= 4).astype(float)
    rows["s_early"] = rows["p_star"] * early                                     # draft position, D+1 to D+3
    rows["age_term"] = rows["prod_x_age_m18"] * upto4                            # production x (age - 18), D+1 to D+4
    rows["flat_term"] = rows["age_m18"] * upto4                                  # age on its own, D+1 to D+4
    rows["prod_sq_x_defence"] = rows["nhle82_sq"] * rows["is_defence"]
    rows["s_early_x_defence"] = rows["s_early"] * rows["is_defence"]
    rows["age_term_19"] = rows["nhle82"] * (rows["age"] - 19.0) * upto4          # age measured from 19
    rows["age_term_20"] = rows["nhle82"] * (rows["age"] - 20.0) * upto4          # and from 20
    rows.to_csv(OUT / "prospect_seasons.csv", index=False)

    # ---- 3. production_seasons.csv ----------------------------------------------------------------------------------
    nh = pd.read_csv(SOURCE_DIR / "nhle_temporal.csv")
    fac = {(r.league, int(r.season_start_year)): float(r.nhle) for r in nh.itertuples()}
    imputed = set()
    for lg in nh["league"].unique():                                                # as production_rates
        if (lg, 2012) not in fac and (lg, 2011) in fac and (lg, 2013) in fac:
            fac[(lg, 2012)] = (fac[(lg, 2011)] + fac[(lg, 2013)]) / 2
            imputed.add(lg)
    s = pd.read_sql("select ep_player_id, season, league, gp, tp from ep_skater_seasons", con)
    s["ep_player_id"] = pd.to_numeric(s["ep_player_id"]).astype(int).astype(str)
    s["gp"], s["tp"] = pd.to_numeric(s["gp"], errors="coerce"), pd.to_numeric(s["tp"], errors="coerce")
    s = s[(s["gp"] > 0) & s["tp"].notna()].copy()                                   # as production_rates
    who = ident.loc[~ident["is_goalie"].astype(bool) & (ident["ep_player_id"] != ""), ["ep_player_id", "player_id"]]
    s = s.merge(who, on="ep_player_id", how="inner")
    s["season_start"] = s["season"].str[:4].astype(int)
    s["nhle_factor"] = [fac.get((lg, y)) for lg, y in zip(s["league"], s["season_start"])]
    s["factor_imputed_2012"] = [int(y == 2012 and lg in imputed) for lg, y in zip(s["league"], s["season_start"])]
    s["nhle_points"] = s["tp"] * s["nhle_factor"]
    prod = s[["player_id", "ep_player_id", "season_start", "season", "league", "gp", "tp", "nhle_factor",
              "factor_imputed_2012", "nhle_points"]].rename(columns={"season": "season_ep", "tp": "points"})
    prod = prod.sort_values(["player_id", "season_start", "league"]).reset_index(drop=True)
    prod.to_csv(OUT / "production_seasons.csv", index=False)
    log(f"\n  wrote draft_players.csv ({len(players):,} rows), prospect_seasons.csv ({len(rows):,} rows), "
        f"production_seasons.csv ({len(prod):,} rows) in {OUT.resolve()}")

    # =============================== the checks, on the CSVs as written ===============================================
    P = pd.read_csv(OUT / "draft_players.csv")
    R = pd.read_csv(OUT / "prospect_seasons.csv", dtype={"ep_player_id": str})
    Q = pd.read_csv(OUT / "production_seasons.csv", dtype={"ep_player_id": str})

    # 1. the model's rows are the CSV's flagged rows, with the same values
    r2 = R[R["sample_production"] == 1].sort_values(["draft_year", "pick", "k"]).reset_index(drop=True)
    pm = prow.sort_values(["draftYear", "pick", "k"]).reset_index(drop=True)
    assert len(r2) == len(pm) and (r2["draft_year"].values == pm["draftYear"].values).all() \
        and (r2["pick"].values == pm["pick"].values).all() and (r2["k"].values == pm["k"].values).all()
    for a_, b_ in (("remaining_npv_m", "remaining_M"), ("nhle82", "nhle82"), ("nhle82_sq", "nhle82_sq"),
                   ("years_past_elig", "past_elig"), ("prod_x_years_past_elig", "prod_x_age"), ("p_star", "p_star"),
                   ("prod_x_defence", "d_x_prod")):
        gap = float(np.max(np.abs(r2[a_].values - pm[b_].values)))
        assert gap < TOL, (a_, gap)
    assert int(R["sample_star"].sum()) == int(fitrows["prospect"].sum())
    log(f"  check 1: the CSV's production sample is the model's {len(pm):,} skater prospect-seasons, row for row, "
        f"same outcome and inputs; its star sample is the model's {int(R['sample_star'].sum()):,} (PASS)")

    # 2. the pick curve (Valuing Draft Picks; Valuing Prospects' D+1 star value)
    pf = P[P["excluded_deceased"] == 0]
    m = ols(pf["career_npv_m"].values, pf[["p_star"]].values)
    sc = pd.read_csv(OUTPUT_DIR / "pick_curve_scales.csv").set_index("scale_kind").loc["main"]
    assert abs(m.params[0] - sc["scale_M"]) < TOL and abs(m.bse[0] - sc["se_M"]) < TOL
    log(f"  check 2: the pick curve from draft_players.csv: star value {m.params[0]:.4f} (robust s.e. {m.bse[0]:.4f}), "
        f"{int(m.nobs):,} players, R-squared {m.rsquared:.3f} = pick_curve_scales.csv (PASS)")

    # 3. the star values by season (Valuing Prospects Table 2)
    s1 = R[R["sample_star"] == 1]
    st, _ = stacked(s1, {g: ["p_star"] for g in range(1, 6)})
    svm = sv[sv["left_out"] == "none"].set_index("k_group")
    log("\n  check 3: star value by season (Valuing Prospects v4.3, Table 1), from prospect_seasons.csv:")
    for k_, g in GROUP_NUM.items():
        b, se = st[(g, "p_star")]
        assert abs(b - svm.loc[k_, "star_value_M"]) < TOL and abs(se - svm.loc[k_, "se_M"]) < TOL, k_
        log(f"    {GROUP_LABEL[g]:<14} {b:7.3f} (clustered s.e. {se:.3f}); {int((s1['season_group'] == g).sum()):,} "
            f"prospect-seasons")
    log("    = prospect_star_values.csv (PASS)")

    # 4. the adopted model (Valuing Prospects Table 9)
    s2 = R[R["sample_production"] == 1]
    cols_code = {GROUP_NUM[g]: [{"p_star": "p_star", "nhle82": "nhle82", "nhle82_sq": "nhle82_sq",
                                 "prod_x_age": "prod_x_years_past_elig", "d_x_prod": "prod_x_defence"}[c]
                                for c in PV.cols_for(g, "main")]
                 for g in GROUP_NUM}
    st_code, m_code = stacked(s2, cols_code)
    for g_, gnum in GROUP_NUM.items():
        cols_m, b_m, se_m = fits[("main", g_, "none")]
        for i, c in enumerate(cols_code[gnum]):
            assert abs(st_code[(gnum, c)][0] - b_m[i]) < TOL and abs(st_code[(gnum, c)][1] - se_m[i]) < TOL, (g_, c)
    cols_doc = {g: [c.replace("prod_x_years_past_elig", "prod_x_age_m18") for c in cs] for g, cs in cols_code.items()}
    st_doc, m_doc = stacked(s2, cols_doc)
    assert float(np.max(np.abs(m_doc.fittedvalues - m_code.fittedvalues))) < TOL       # the same values
    log("\n  check 4: the adopted model (Valuing Prospects v4.3, Table 7), from prospect_seasons.csv, age less 18:")
    names = {"p_star": "star probability", "nhle82": "production", "nhle82_sq": "production squared",
             "prod_x_age_m18": "production x (age - 18)", "prod_x_defence": "production x defenceman"}
    for gnum, cs in cols_doc.items():
        kk = int(s2.loc[s2["season_group"] == gnum, "k"].iloc[0])
        if "prod_x_age_m18" in cs:
            assert s2.loc[s2["season_group"] == gnum, "k"].nunique() == 1
            e_doc, e_code = st_doc[(gnum, "prod_x_age_m18")][0], st_code[(gnum, "prod_x_years_past_elig")][0]
            assert abs(e_doc - e_code) < TOL                                            # the same age coefficient
            assert abs(st_doc[(gnum, "nhle82")][0] - (st_code[(gnum, "nhle82")][0] - kk * e_code)) < TOL
        x = s2[s2["season_group"] == gnum]
        own = ols(x["remaining_npv_m"].values, x[cs].values)                        # the season's own R-squared
        log(f"    {GROUP_LABEL[gnum]:<14} " + "; ".join(f"{names[c]} {st_doc[(gnum, c)][0]:.4f} ({st_doc[(gnum, c)][1]:.4f})"
                                                     for c in cs)
            + f"; {len(x):,} rows, R-squared {own.rsquared:.3f}")
    log("    = prospect_production_fits.csv, the same fitted values and age coefficient (PASS)")

    # 5. production_seasons.csv rebuilds the model's NHLe rate for every player-season
    # by player_id, as Stata would collapse it: a player drafted twice (five of them) has his one Elite Prospects record
    # under both draft rows, so adding up by Elite Prospects id would count his games twice
    q = Q[Q["nhle_factor"].notna()]
    g = q.groupby(["player_id", "ep_player_id", "season_start"]).agg(gp=("gp", "sum"), pts=("nhle_points", "sum"))
    g = g[g["gp"] >= PV.PROD_MIN_GP].reset_index()
    rate = {(p_, e_, y_): v_ for p_, e_, y_, v_ in zip(g["player_id"], g["ep_player_id"], g["season_start"],
                                                       g["pts"] / g["gp"] * 82)}
    pid_of = Q.groupby("ep_player_id")["player_id"].unique().to_dict()
    mine = {(p_, e_, y_): v_ for (e_, y_), v_ in rates.items() if e_ in pid_of for p_ in pid_of[e_]}
    assert set(rate) == set(mine) and max(abs(rate[k_] - mine[k_]) for k_ in rate) < TOL
    log(f"\n  check 5: production_seasons.csv gives the model's NHLe rate for all {len(rate):,} player-seasons (PASS)")

    expected_figures(P, R)
    (OUT / "stata_export_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
