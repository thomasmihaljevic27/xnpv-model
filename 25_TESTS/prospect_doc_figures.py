"""
prospect_doc_figures.py -- the numbers and figures behind "Valuing Prospects" (40_DOCS/Supervisor_Drafts/), v4.0.

v4.0 (2026-10-27, on prospect_values.py v1.13: defenceman x production in every season, Thomas 2026-10-24). The
document's fit measures follow the supervisor meeting of 2026-10-23: R-squared, statistical significance and economic
significance, with held-out error a supplementary note. So every model the document compares is fitted HERE, on one
set of rows, by one engine (fit_design):
  * R-squared measured from zero (the regressions have no constant; 1 - SSR / sum of y squared, which is what
    statsmodels and Stata's `regress ..., noconstant` report) and adjusted R-squared (statsmodels' rsquared_adj);
  * statistical significance: the Wald test that the added terms are all zero (or, for a pooling test, that a term is
    equal across seasons), in the one regression with the full set of interaction terms, errors clustered by player;
    a pair of models that are not nested gets no test;
  * economic significance: what the model is worth on the traded prospects (the same assets for every model) and on
    one worked prospect;
  * held-out error (supplementary): each draft predicted from a fit without it, root mean squared error. No redraw
    p-value: held-out error is a note now.
Models, in the document's order (each term its own coefficient in each season group unless pooled):
  Section 2: draft position alone; linear production alone; draft position + linear production; + squared;
             linear and squared production alone; the Section 2 model (draft position in D+1 to D+3 only);
             production squared alone with draft position in D+1 to D+3.
  Section 3 (on the Section 2 model): + age less 18 (a flat amount), + production x (age - 18) (adopted), + both,
             + production x (age - 18) from D+5 on as well.
  Section 4 (on the Section 3 model): + defenceman x production (adopted: prospect_values.cols_for); + defenceman x
             production squared; + defenceman x draft position (D+1 to D+3); each term pooled across seasons; the
             adopted model without linear production at each age measure and starting age; the adopted model without
             any term from D+5 on.
Age is his age on September 15 of the valuation season, less 18 (the document's measure since v2.1). With linear
production in the model this gives the same values as prospect_values' years past first eligibility (GUARD below).
Recorded results not refitted here, each read from its own output: the star value's alternatives
(prospect_fade_rules.py), the discounted age forms (prospect_age_discount_look.py, non-linear in their discount; fitted
before the defenceman term), the pick curve's position test (defence_terms_look.py).
GUARDS: the adopted model's values equal prospect_values.csv's value_M for each traded prospect (1e-6); its
coefficients' fitted values equal the live fits (1e-9); the held-out errors of six models reproduce their recorded
tests (prospect_nhle_look, prospect_age_discount_look, defence_terms_look) to 1e-9; R-squared of three models reproduces
prospect_age_discount_look's (1e-9); the defenceman test's Wald p reproduces defence_terms_look's (1e-9); the stacked
star values equal prospect_slot_years.csv's; the arrival shares end at the share who ever arrived.

v3.0 (2026-10-22): no no-record indicator (prospect_values.py v1.12). v2.2 (2026-10-16): each coefficient table one
regression with the full set of interaction terms. v2.1 (2026-10-15): age reported as age on September 15 less 18;
arrival figure as shares of all players; the star value figure as three panels. v2.0 (2026-10-15): rebuilt for the
revised document. Earlier versions are in git.
INPUTS (OUTPUT_DIR): prospect_slot_years.csv, prospect_fade_rules.csv, prospect_fade_rules_scores.csv,
prospect_nhle_look.csv, prospect_nhle_rows.csv, prospect_age_discount_look.csv, prospect_age_discount_coefficients.csv,
prospect_age_discount_traded_summary.csv, defence_terms_look.csv, defence_terms_coefficients.csv,
prospect_production_fits.csv, prospect_values.csv, nhl_arrival_timing_summary.csv, ep_out/ep_prospects.db,
pick_curve_players.csv, draft_pick_linkage.csv; SOURCE_DIR/draft_slot_baseline.csv, nhle_temporal.csv.
OUTPUTS: OUTPUT_DIR/prospect_doc/numbers.json and six figures (fig_*.png).
Run from the repo root (matplotlib on PYTHONPATH):  python 25_TESTS/prospect_doc_figures.py
"""

import json
import math
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import prospect_values as PV                                       # noqa: E402

import matplotlib                                                  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

SCRIPT_VERSION = "prospect_doc_figures.py v4.1 (2026-10-27)"   # v4.1: the same-percentage test; v4.0: one engine for every model; R-squared, Wald tests, dollars; defenceman x production
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
FIG = OUT / "prospect_doc"
FIG.mkdir(exist_ok=True)
N = {"script": SCRIPT_VERSION}
print(SCRIPT_VERSION)
GROUPS = ["0", "1", "2", "3", "4+"]
EARLY = ("0", "1", "2")                     # draft position in D+1 to D+3 (prospect_values.SLOT_GROUPS)
AGEG = ("0", "1", "2", "3")                 # the age term in D+1 to D+4 (prospect_values.AGE_GROUPS)
assert tuple(PV.SLOT_GROUPS) == EARLY and tuple(PV.AGE_GROUPS) == AGEG


def pval(b, se):
    """Two-sided p-value from a robust z statistic (normal reference); None when the standard error is zero."""
    if se < 1e-12:
        return None
    return math.erfc(abs(b / se) / math.sqrt(2))


bacon = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
N["p_star"] = {str(k): float(bacon[k]) for k in (1, 10, 13, 20, 32)}

# ---- 1. draft position by season --------------------------------------------------------------------
sy = pd.read_csv(OUT / "prospect_slot_years.csv", dtype={"seasons_since_draft": str})
N["step1"] = [{"k": r.seasons_since_draft, "rows": int(r.rows), "players": int(r.players), "star": r.star_value_M,
               "pick1": r.star_value_M * float(bacon[1]), "pick10": r.star_value_M * float(bacon[10]),
               "pick32": r.star_value_M * float(bacon[32]), "top10": int(r.top10_prospects)}
              for r in sy.itertuples()]
fr = pd.read_csv(OUT / "prospect_fade_rules.csv")
fs = pd.read_csv(OUT / "prospect_fade_rules_scores.csv")
RULES = ["separate", "no fade", "straight line", "same percentage"]
N["fade_curve"] = {r: [float(x) for x in fr[r]] for r in RULES}
N["fade_scores"] = {r: {"rmse": float(fs.loc[fs["rule"] == r, "rmse_M"].iloc[0]),
                        "total": float(fs.loc[fs["rule"] == f"traded total: {r}", "total_M"].iloc[0]),
                        "below_zero": int(fs.loc[fs["rule"] == f"traded total: {r}", "below_zero"].iloc[0])}
                    for r in RULES}
w_ = fs[fs["rule"].str.startswith("equal steps")].iloc[0]
N["fade_wald_steps"] = {"chi2": float(w_["chi2"]), "p": float(w_["p"]), "df": 2}
N["fade_rows"] = int(fs.loc[fs["rule"] == "separate", "rows"].iloc[0])

# the star values' rows: R-squared of each alternative and the test that one value fits every season
sv, fitrows = PV.star_values()
srows = fitrows[fitrows["prospect"]].copy()
srows["k_group"] = srows["k_group"].astype(str)
assert len(srows) == N["fade_rows"], len(srows)
y_s = srows["remaining_M"].values
ss0 = float(np.sum(y_s ** 2))
curve = {r: np.array(N["fade_curve"][r]) for r in RULES}
assert srows["k"].max() < len(curve["separate"])                     # every season has its value in the curve
N["fade_r2"] = {}
NPAR = {"separate": 5, "no fade": 1, "straight line": 2, "same percentage": 2}
for r in RULES:
    pred = curve[r][srows["k"].astype(int).values] * srows["p_star"].values
    r2 = 1 - float(np.sum((y_s - pred) ** 2)) / ss0
    n_ = len(srows)
    N["fade_r2"][r] = {"r2": r2, "adj": 1 - n_ / (n_ - NPAR[r]) * (1 - r2), "params": NPAR[r]}
st_s, m_s = PV.fit_stacked(srows, {g: ["p_star"] for g in GROUPS})
svm = sv[sv["left_out"] == "none"].set_index("k_group")
for r in N["step1"]:
    assert abs(float(svm.loc[r["k"], "star_value_M"]) - r["star"]) < 1e-9, r["k"]   # GUARD: the same star values
    assert abs(float(st_s[r["k"]][0][0]) - r["star"]) < 1e-9, r["k"]
    r["se"] = float(svm.loc[r["k"], "se_M"])
    r["p"] = pval(r["star"], r["se"])
Rm = np.zeros((4, 5))
for i in range(4):
    Rm[i, i], Rm[i, i + 1] = 1.0, -1.0
w = m_s.wald_test(Rm, use_f=False, scalar=True)
N["fade_wald_one"] = {"chi2": float(w.statistic), "df": 4, "p": float(w.pvalue)}
# v4.1 (Thomas, 2026-10-27: "Might as well do a test"): the same percentage decline as a restriction of the adopted
# star values, as the equal-drops test is: the same share kept from D+1 to D+2, D+2 to D+3 and D+3 to D+4, i.e.
# t2/t1 = t3/t2 = t4/t3, written g = (t2^2 - t1 t3, t3^2 - t2 t4) = 0. Non-linear, so a delta-method Wald test:
# chi2 = g' (J V J')^-1 g, J the Jacobian of g, V the clustered covariance of the five star values (2 restrictions).
th, V_ = np.asarray(m_s.params), np.asarray(m_s.cov_params())
g_ = np.array([th[1] ** 2 - th[0] * th[2], th[2] ** 2 - th[1] * th[3]])
J_ = np.array([[-th[2], 2 * th[1], -th[0], 0.0, 0.0], [0.0, -th[3], 2 * th[2], -th[1], 0.0]])
chi_r = float(g_ @ np.linalg.solve(J_ @ V_ @ J_.T, g_))
from scipy import stats as _st                                       # noqa: E402
N["fade_wald_ratio"] = {"chi2": chi_r, "df": 2, "p": float(_st.chi2.sf(chi_r, 2)),
                        "shares": [float(th[1] / th[0]), float(th[2] / th[1]), float(th[3] / th[2])]}
# the same delta-method form reproduces the equal-drops test (a linear restriction, so it must equal it exactly)
gl = np.array([th[1] - th[0] - (th[2] - th[1]), th[2] - th[1] - (th[3] - th[2])])
Jl = np.array([[1.0, -2.0, 1.0, 0.0, 0.0], [0.0, 1.0, -2.0, 1.0, 0.0]])
chi_l = float(gl @ np.linalg.solve(Jl @ V_ @ Jl.T, gl))
assert abs(chi_l - N["fade_wald_steps"]["chi2"]) < 1e-6, (chi_l, N["fade_wald_steps"]["chi2"])   # GUARD
print(f"  same percentage decline, D+1 to D+4: chi2(2) = {chi_r:.2f}, p = {N['fade_wald_ratio']['p']:.3g} "
      f"(guard: the equal-drops test reproduced, chi2 {chi_l:.4f})")
N["star_r2_by_k"] = {g: 1 - float(np.sum((y_s[srows["k_group"].values == g]
                                         - st_s[g][0][0] * srows["p_star"].values[srows["k_group"].values == g]) ** 2))
                     / float(np.sum(y_s[srows["k_group"].values == g] ** 2)) for g in GROUPS}
print(f"  guard: the stacked star values equal prospect_slot_years.csv (PASS); one value for every season: "
      f"chi2(4) = {N['fade_wald_one']['chi2']:.2f}, p = {N['fade_wald_one']['p']:.2g}")

ar = pd.read_csv(OUT / "nhl_arrival_timing_summary.csv")
N["arrival"] = {g: {"n_arrived": int(x.loc[x["season"] != "never", "arrived"].sum()),
                    "n": int(x["arrived"].sum()),
                    "share_all": {s: float(v) for s, v in zip(x["season"], x["share_of_all"]) if s != "never"},
                    "never": int(x.loc[x["season"] == "never", "arrived"].iloc[0])}
                for g, x in ar.groupby("group")}

# ---- 2. the prospect rows and the production measure -------------------------------------------------
rates = PV.production_rates()
fits, prow = PV.production_fits(fitrows, rates)
prow = prow.assign(k_group=prow["k_group"].astype(str)).reset_index(drop=True)
assert set(prow["k_group"]) == set(GROUPS)
pr = pd.read_csv(OUT / "prospect_nhle_rows.csv", dtype={"k_group": str})
assert len(pr) == len(prow), (len(pr), len(prow))
N["prod_rows"] = {"rows": len(prow), "players": int(prow[["draftYear", "pick"]].drop_duplicates().shape[0]),
                  "defencemen": int(prow.loc[prow["is_d"] == 1, ["draftYear", "pick"]].drop_duplicates().shape[0]),
                  "no_record_share": float(prow["no_record"].mean()),
                  "no_record_by_k": {g: int(x["no_record"].sum()) for g, x in prow.groupby("k_group")}}
k1 = prow[(prow["k_group"] == "1") & (prow["n_prod_seasons"] > 0)]["nhle82"]
N["prod_pct_k1"] = {q: float(k1.quantile(q / 100)) for q in (25, 50, 75, 90)}
N["prod_median_by_k"] = {g: float(x.loc[x["n_prod_seasons"] > 0, "nhle82"].median()) for g, x in prow.groupby("k_group")}
N["prod_median_pos"] = {g: {pos: float(x.loc[(x["n_prod_seasons"] > 0) & (x["is_d"] == d_), "nhle82"].median())
                             for pos, d_ in (("F", 0.0), ("D", 1.0))} for g, x in prow.groupby("k_group")}
age_now = prow["past_elig"] + prow["k"] + PV.FIRST_ELIGIBLE_AGE
N["age_corr"] = {"age_vs_k": float(np.corrcoef(age_now, prow["k"])[0, 1])}


def add_cols(f):
    """Every column a model below can use. f has p_star, nhle82, past_elig (age - k - 18), k and is_d.
    S draft position's star probability; P production; Q production squared; A production x (age - 18);
    F age - 18; D defenceman x production; DQ defenceman x production squared; DS defenceman x star probability;
    C<m><c> production x (his age measure m less c): m = 1 his age in D+1 (age - k), m = n his age now."""
    f = f.copy()
    a18 = f["past_elig"] + f["k"]                                    # his age on September 15, less 18
    f["S"], f["P"], f["Q"] = f["p_star"], f["nhle82"], f["nhle82"] ** 2
    f["A"], f["F"] = f["nhle82"] * a18, a18
    f["Fe"] = f["past_elig"]                                         # years past first eligibility (the age tests' flat term)
    f["D"], f["DQ"], f["DS"] = f["nhle82"] * f["is_d"], f["nhle82"] ** 2 * f["is_d"], f["p_star"] * f["is_d"]
    for c in (17.5, 18, 18.5, 19):
        f[f"C1_{c}"] = f["nhle82"] * (f["past_elig"] + PV.FIRST_ELIGIBLE_AGE - c)
    for c in (0, 18, 19, 20, 21):
        f[f"Cn_{c}"] = f["nhle82"] * (a18 + PV.FIRST_ELIGIBLE_AGE - c)
    return f


prow = add_cols(prow)


# ---- the engine: one regression per model -------------------------------------------------------------
# A model is a list of blocks (column, groups): the column times the indicator for being in one of those season
# groups. A block for one group is a term with its own coefficient in that season; a block over several groups is a
# term pooled across them. Through zero; errors clustered by player (draftYear-pick), as prospect_values.fit_stacked.
def by(col, groups=GROUPS):
    return [(col, (g,)) for g in groups]


def design(f, blocks):
    gv = f["k_group"].values
    return np.column_stack([np.where(np.isin(gv, gs), f[c].values, 0.0) for c, gs in blocks])


PLAYERS = pd.factorize(prow["draftYear"].astype(str) + "-" + prow["pick"].astype(str))[0]
Y = prow["remaining_M"].values
DRAFTS = sorted(prow["draftYear"].unique())
FITS = {}


def fit_design(name, blocks):
    X = design(prow, blocks)
    m = sm.OLS(Y, X).fit(cov_type="cluster", cov_kwds={"groups": PLAYERS})
    # held-out error (supplementary): each draft predicted from a fit on the other ten
    err = np.empty(len(Y))
    for c in DRAFTS:
        tr = prow["draftYear"].values != c
        b = np.linalg.lstsq(X[tr], Y[tr], rcond=None)[0]
        err[~tr] = Y[~tr] - X[~tr] @ b
    gv = prow["k_group"].values
    FITS[name] = {"blocks": blocks, "m": m, "err": err,
                  "r2": float(m.rsquared), "adj": float(m.rsquared_adj), "n_coef": len(blocks),
                  "rmse": float(np.sqrt(np.mean(err ** 2))),
                  "rmse_by_k": {g: float(np.sqrt(np.mean(err[gv == g] ** 2))) for g in GROUPS}}
    return FITS[name]


def idx(name, col, g=None):
    """The positions of a model's coefficients on column col (in group g, or every block of col)."""
    bl = FITS[name]["blocks"]
    return [i for i, (c, gs) in enumerate(bl) if c == col and (g is None or g in gs)]


def wald(name, positions=None, equal=None):
    """Wald test (clustered by player) that the listed coefficients are all zero, or (equal=list of positions) that
    they are all equal."""
    m = FITS[name]["m"]
    k_ = len(m.params)
    if equal is not None:
        R = np.zeros((len(equal) - 1, k_))
        for j in range(len(equal) - 1):
            R[j, equal[j]], R[j, equal[j + 1]] = 1.0, -1.0
    else:
        R = np.zeros((len(positions), k_))
        for j, p_ in enumerate(positions):
            R[j, p_] = 1.0
    w_ = m.wald_test(R, use_f=False, scalar=True)
    return {"chi2": float(w_.statistic), "df": int(R.shape[0]), "p": float(w_.pvalue)}


def coef_table(name):
    """{group: {column: {b, se, p}}} for a model whose blocks are each one group."""
    m, out = FITS[name]["m"], {g: {} for g in GROUPS}
    for i, (c, gs) in enumerate(FITS[name]["blocks"]):
        assert len(gs) == 1
        out[gs[0]][c] = {"b": float(m.params[i]), "se": float(m.bse[i]), "p": pval(m.params[i], m.bse[i])}
    return out


def season_r2(name):
    """R-squared from zero within each season (the block-diagonal stack equals each season's own fit)."""
    fv, gv = FITS[name]["m"].fittedvalues, prow["k_group"].values
    return {g: 1 - float(np.sum((Y[gv == g] - fv[gv == g]) ** 2)) / float(np.sum(Y[gv == g] ** 2)) for g in GROUPS}


def summary(name):
    f = FITS[name]
    return {"r2": f["r2"], "adj": f["adj"], "n_coef": f["n_coef"], "rmse": f["rmse"], "rmse_by_k": f["rmse_by_k"]}


S_E, P_ALL, Q_ALL = by("S", EARLY), by("P"), by("Q")
MODELS = {
    # Section 2: production (before age and the defenceman term)
    "slot": by("S"),
    "lin_alone": by("P"),
    "slot_lin": by("S") + by("P"),
    "slot_linsq": by("S") + by("P") + by("Q"),
    "linsq_alone": by("P") + by("Q"),
    "s2": S_E + P_ALL + Q_ALL,
    "s2_sq_alone": S_E + Q_ALL,
    # Section 3: age, on the Section 2 model
    "s3_flat": S_E + P_ALL + Q_ALL + by("F", AGEG),
    "s3": S_E + P_ALL + Q_ALL + by("A", AGEG),
    "s3_both": S_E + P_ALL + Q_ALL + by("F", AGEG) + by("A", AGEG),
    "s3_age_late": S_E + P_ALL + Q_ALL + by("A"),
    # the flat term measured as years past first eligibility (prospect_age_discount_look.py's form): a check, since
    # through zero a flat age term's fit depends on where age is measured from
    "s3_flat_pe": S_E + P_ALL + Q_ALL + by("Fe", AGEG),
    "s3_both_pe": S_E + P_ALL + Q_ALL + by("Fe", AGEG) + by("A", AGEG),
    # Section 4: defencemen, on the Section 3 model; "adopted" is prospect_values.cols_for
    "adopted": S_E + P_ALL + Q_ALL + by("A", AGEG) + by("D"),
    "adopted_dq": S_E + P_ALL + Q_ALL + by("A", AGEG) + by("D") + by("DQ"),
    "adopted_ds": S_E + P_ALL + Q_ALL + by("A", AGEG) + by("D") + by("DS", EARLY),
    # each term pooled across seasons (the adopted model's terms)
    "pool_prod": S_E + [("P", tuple(GROUPS)), ("Q", tuple(GROUPS))] + by("A", AGEG) + by("D"),
    "pool_age": S_E + P_ALL + Q_ALL + [("A", AGEG)] + by("D"),
    "pool_def": S_E + P_ALL + Q_ALL + by("A", AGEG) + [("D", tuple(GROUPS))],
    "pool_all": S_E + [("P", tuple(GROUPS)), ("Q", tuple(GROUPS)), ("A", AGEG), ("D", tuple(GROUPS))],
    # the adopted model with nothing from D+5 on (its D+5 rows predicted at zero)
    "no_late": S_E + by("P", GROUPS[:4]) + by("Q", GROUPS[:4]) + by("A", AGEG) + by("D", GROUPS[:4]),
}
# the adopted model without linear production: production x (his age measure less c) in D+1 to D+4; from D+5 on Q, D
NOLIN = [("1", c) for c in (17.5, 18, 18.5, 19)] + [("n", c) for c in (18, 19, 20, 21, 0)]
for m_, c in NOLIN:
    MODELS[f"nolin_{m_}_{c}"] = S_E + Q_ALL + by(f"C{m_}_{c}", AGEG) + by("D")
for nm, bl in MODELS.items():
    fit_design(nm, bl)
print(f"  fitted {len(MODELS)} models on {len(prow):,} prospect-seasons")

# GUARD: the adopted model is the live model (cols_for) and gives the live fitted values
for g in GROUPS:
    live_cols = PV.cols_for(g, "main")
    mine = [c for c, gs in MODELS["adopted"] if gs == (g,)]
    tr_ = {"p_star": "S", "nhle82": "P", "nhle82_sq": "Q", "prod_x_age": "A", "d_x_prod": "D"}
    assert [tr_[c] for c in live_cols] == mine, (g, live_cols, mine)
st_live, m_live = PV.fit_stacked(prow, {g: PV.cols_for(g, "main") for g in GROUPS})
assert np.max(np.abs(m_live.fittedvalues - FITS["adopted"]["m"].fittedvalues)) < 1e-9
print("  guard: the adopted model has the live columns and the live fitted values (PASS)")

# GUARDS: held-out errors and R-squared reproduce the recorded tests
nl = pd.read_csv(OUT / "prospect_nhle_look.csv").set_index("arm")
ad_ = pd.read_csv(OUT / "prospect_age_discount_look.csv")
ad_ = ad_[ad_["centre"] == 18.0].set_index("key")
dl = pd.read_csv(OUT / "defence_terms_look.csv")
dlp = dl[dl["part"] == "prospect model"].set_index("arm")
for mine, ref in (("slot", nl.loc["slot", "rmse_M"]), ("s2", nl.loc["chosen", "rmse_M"]),
                  ("slot_linsq", nl.loc["slot+production curved", "rmse_M"]),
                  ("s3", ad_.loc["adopted", "rmse_heldout_M"]), ("s3_flat_pe", ad_.loc["age_alone", "rmse_heldout_M"]),
                  ("s3_both_pe", ad_.loc["pair", "rmse_heldout_M"]), ("adopted", dlp.loc["+ D x P", "rmse_heldout_M"])):
    assert abs(FITS[mine]["rmse"] - float(ref)) < 1e-9, (mine, FITS[mine]["rmse"], ref)
for mine, key in (("s3", "adopted"), ("s3_flat_pe", "age_alone"), ("s3_both_pe", "pair")):
    assert abs(FITS[mine]["r2"] - float(ad_.loc[key, "r2_all_uncentred"])) < 1e-9, mine
W_D = wald("adopted", idx("adopted", "D"))
assert abs(W_D["p"] - float(dlp.loc["+ D x P", "wald_p"])) < 1e-9, W_D
print("  guard: seven held-out errors, three R-squared and the defenceman test reproduce their recorded tests (PASS)")

# ---- tests -------------------------------------------------------------------------------------------
T = {}
T["prod_vs_slot"] = wald("slot_linsq", idx("slot_linsq", "P") + idx("slot_linsq", "Q"))
T["lin_vs_slot"] = wald("slot_lin", idx("slot_lin", "P"))
T["sq_given_lin"] = wald("slot_linsq", idx("slot_linsq", "Q"))
T["slot_all"] = wald("slot_linsq", idx("slot_linsq", "S"))                # draft position once production is in
T["slot_late"] = wald("slot_linsq", idx("slot_linsq", "S", "3") + idx("slot_linsq", "S", "4+"))
T["sq_s2"] = wald("s2", idx("s2", "Q"))
T["lin_s2"] = wald("s2", idx("s2", "P"))                              # production squared alone, before age
T["flat"] = wald("s3_flat", idx("s3_flat", "F"))
T["disc"] = wald("s3", idx("s3", "A"))
T["flat_given_disc"] = wald("s3_both", idx("s3_both", "F"))
T["disc_given_flat"] = wald("s3_both", idx("s3_both", "A"))
T["flat_pe"] = wald("s3_flat_pe", idx("s3_flat_pe", "Fe"))
T["flat_pe_given_disc"] = wald("s3_both_pe", idx("s3_both_pe", "Fe"))
T["age_late"] = wald("s3_age_late", idx("s3_age_late", "A", "4+"))
T["def"] = W_D
T["dq"] = wald("adopted_dq", idx("adopted_dq", "DQ"))
T["ds"] = wald("adopted_ds", idx("adopted_ds", "DS"))
T["late_prod"] = wald("adopted", idx("adopted", "P", "4+") + idx("adopted", "Q", "4+"))
T["late_all"] = wald("adopted", idx("adopted", "P", "4+") + idx("adopted", "Q", "4+") + idx("adopted", "D", "4+"))
m_ad = FITS["adopted"]["m"]


def wald_equal_sets(name, cols):
    """Each listed column equal across its season blocks, jointly."""
    m, k_, rows = FITS[name]["m"], len(FITS[name]["m"].params), []
    for c in cols:
        pos = idx(name, c)
        for j in range(len(pos) - 1):
            r = np.zeros(k_)
            r[pos[j]], r[pos[j + 1]] = 1.0, -1.0
            rows.append(r)
    w_ = m.wald_test(np.array(rows), use_f=False, scalar=True)
    return {"chi2": float(w_.statistic), "df": len(rows), "p": float(w_.pvalue)}


T["pool_prod"] = wald_equal_sets("adopted", ["P", "Q"])
T["pool_age"] = wald_equal_sets("adopted", ["A"])
T["pool_def"] = wald_equal_sets("adopted", ["D"])
T["pool_all"] = wald_equal_sets("adopted", ["P", "Q", "A", "D"])
# linear production's coefficient zero in every season, by where age is measured from (the same fitted values)
T["lin_zero"] = {}
for c in (18, 19, 20):
    bl = S_E + P_ALL + Q_ALL + by(f"Cn_{c}", AGEG) + by("D")
    fit_design(f"centre_{c}", bl)
    assert np.max(np.abs(FITS[f"centre_{c}"]["m"].fittedvalues - m_ad.fittedvalues)) < 1e-8, c   # GUARD: same values
    T["lin_zero"][str(c)] = wald(f"centre_{c}", idx(f"centre_{c}", "P"))
N["tests"] = T
N["models"] = {nm: summary(nm) for nm in MODELS}
for k_, v_ in T.items():
    if isinstance(v_, dict) and "p" in v_:
        print(f"  {k_:<16} chi2({v_['df']}) = {v_['chi2']:.2f}, p = {v_['p']:.3g}")

# coefficient tables
N["coefs"] = {nm: coef_table(nm) for nm in ("slot", "slot_lin", "slot_linsq", "s3", "s3_flat", "s3_both", "s3_flat_pe", "adopted")}
N["season_r2"] = {nm: season_r2(nm) for nm in ("slot", "slot_lin", "slot_linsq", "s3", "adopted")}
N["adopted_counts"] = {g: {"rows": int((prow["k_group"] == g).sum()),
                           "players": int(prow.loc[prow["k_group"] == g, ["draftYear", "pick"]].drop_duplicates().shape[0]),
                           "drafts": int(prow.loc[prow["k_group"] == g, "draftYear"].nunique())} for g in GROUPS}

# ---- traded prospects under each model -----------------------------------------------------------------
v = pd.read_csv(OUT / "prospect_values.csv")
dv = v[v["status"].astype(str).str.startswith("prospect, valued")].copy()
uv = v[v["status"].astype(str).str.startswith("undrafted prospect, valued")].copy()
allv = pd.concat([dv, uv])


def traded_frame(f):
    f = f.rename(columns={"seasons_since_draft": "k_raw"}).copy()
    f["k"] = f["k_raw"].astype(float)
    f["is_d"] = f["is_d_model"].astype(float)
    f["k_group"] = f["k_group"].astype(str)
    f["p_star"] = f["p_star"].fillna(0.0)
    return add_cols(f)


sk = traded_frame(dv[~dv["is_goalie"].astype(bool) & dv["nhle82"].notna()])
uk = traded_frame(uv[uv["nhle82"].notna()])
assert sk["is_d"].notna().all() and uk["is_d"].notna().all()
gk_tot = float(dv.loc[~dv.index.isin(sk.index), "value_M"].sum())       # goaltenders: draft position alone
uk_other = float(uv.loc[~uv.index.isin(uk.index), "value_M"].sum())     # undrafted with no production record


def values_of(name, f):
    b = FITS[name]["m"].params
    return design(f, FITS[name]["blocks"]) @ b


for f_, ref in ((sk, dv.loc[sk.index, "value_M"]), (uk, uv.loc[uk.index, "value_M"])):
    assert np.max(np.abs(values_of("adopted", f_) - ref.values)) < 1e-6        # GUARD: the live values
print("  guard: the adopted model's values equal prospect_values.csv for each traded prospect (PASS)")
N["model_traded"] = {nm: {"drafted": float(values_of(nm, sk).sum()) + gk_tot, "undrafted": float(values_of(nm, uk).sum()) + uk_other,
                          "below_zero": int((values_of(nm, sk) < 0).sum())} for nm in FITS}
d_def = values_of("adopted", sk) - values_of("s3", sk)
N["def_moved"] = {"n025": int((np.abs(d_def) >= 0.25).sum()),
                  "largest": sk.iloc[int(np.argmax(np.abs(d_def)))]["player_name"],
                  "largest_date": sk.iloc[int(np.argmax(np.abs(d_def)))]["trade_date"],
                  "largest_from": float(values_of("s3", sk)[int(np.argmax(np.abs(d_def)))]),
                  "largest_to": float(values_of("adopted", sk)[int(np.argmax(np.abs(d_def)))]),
                  "n_d_traded": int((sk["is_d"] == 1).sum())}

d_prod = dv["value_M"] - dv["value_slot_only_M"]
N["traded"] = {
    "drafted": len(dv), "drafted_players": int(dv["player_name"].nunique()), "undrafted": len(uv),
    "goalies": int(dv["is_goalie"].astype(bool).sum()), "skaters_priced": len(sk), "others_on_slot": len(dv) - len(sk),
    "tot_main": float(dv["value_M"].sum()), "tot_slot": float(dv["value_slot_only_M"].sum()),
    "tot_own_out": float(dv["value_own_draft_out_M"].sum()), "tot_all": float(allv["value_M"].sum()),
    "tot_undrafted": float(uv["value_M"].sum()), "max_undrafted": float(uv["value_M"].max()),
    "max_undrafted_name": uv.loc[uv["value_M"].idxmax(), "player_name"],
    "undrafted_k_min": int(uv["seasons_since_draft"].min()),
    "moved_025": int((d_prod.abs() >= 0.25).sum()),
    "rank": float(dv["value_M"].rank().corr(dv["value_slot_only_M"].rank())),
    "top20_same_slot": len(set(dv.nlargest(20, "value_M")["asset_id"]) & set(dv.nlargest(20, "value_slot_only_M")["asset_id"])),
    "neg_drafted": int((dv["value_M"] < 0).sum()), "neg_drafted_sum": float(dv.loc[dv["value_M"] < 0, "value_M"].sum()),
    "neg_all": int((allv["value_M"] < 0).sum()), "neg_min": float(allv["value_M"].min()),
    "slot_no_fade": float((dv["p_star"] * N["step1"][0]["star"]).sum()),
}
assert abs(N["model_traded"]["adopted"]["drafted"] - N["traded"]["tot_main"]) < 1e-6

# ---- economic significance: worked numbers -------------------------------------------------------------
CA = N["coefs"]["adopted"]
p20 = float(bacon[20])
N["econ"] = {
    "def_20_by_k": {g: 20 * CA[g]["D"]["b"] for g in GROUPS},
    "def_10_by_k": {g: 10 * CA[g]["D"]["b"] for g in GROUPS},
    "fwd_20_k1": CA["1"]["S"]["b"] * p20 + CA["1"]["P"]["b"] * 20 + CA["1"]["Q"]["b"] * 400 + CA["1"]["A"]["b"] * 20 * 1.5,
    "age_year_10_k1": -10 * CA["1"]["A"]["b"], "age_year_20_k1": -20 * CA["1"]["A"]["b"],
    "flat_year_by_k": {g: N["coefs"]["s3_flat"][g]["F"]["b"] for g in AGEG},
}
N["econ"]["def_20_k1_value"] = N["econ"]["fwd_20_k1"] + N["econ"]["def_20_by_k"]["1"]

# ---- recorded tests read, not refitted ---------------------------------------------------------------------
adc = pd.read_csv(OUT / "prospect_age_discount_coefficients.csv")
adc = adc[(adc["centre"] == 18.0) & (adc["key"] == "adj_disc")].set_index("season")
ats = pd.read_csv(OUT / "prospect_age_discount_traded_summary.csv").set_index("arm")
DISC = {"adopted": "production x age (adopted)", "adj_line": "age-adjusted points, straight line",
        "adj_disc": "age-adjusted points, discounted", "val_disc": "production's value, discounted",
        "one_disc": "P(1 + P), discounted, one coefficient"}
N["disc_forms"] = {k_: {"r2": float(ad_.loc[k_, "r2_all_uncentred"]), "rmse": float(ad_.loc[k_, "rmse_heldout_M"]),
                        "n_coef": int(ad_.loc[k_, "k_D1_D4"]) + 2, "drafted": float(ats.loc[nm_, "drafted_total_M"])}
                   for k_, nm_ in DISC.items()}
assert abs(N["disc_forms"]["adopted"]["r2"] - FITS["s3"]["r2"]) < 1e-9
assert abs(N["disc_forms"]["adopted"]["drafted"] - N["model_traded"]["s3"]["drafted"]) < 1e-6
N["disc_y"] = {s_: float(adc.loc[s_, "y"]) for s_ in ("D+1", "D+2", "D+3", "D+4")}
N["disc_p_heldout"] = float(ad_.loc["adj_disc", "p_heldout_vs_adopted"])
dlc = pd.read_csv(OUT / "defence_terms_coefficients.csv")
pc = dlc[(dlc["part"] == "pick curve") & (dlc["arm"] == "+ D x S")].set_index("term")
dlk = dl[dl["part"] == "pick curve"].set_index("arm")
N["pick_def"] = {"fwd": float(pc.loc["S", "coef"]), "d": float(pc.loc["S", "coef"] + pc.loc["D x S", "coef"]),
                 "p": float(pc.loc["D x S", "p"]), "r2_from": float(dlk.loc["adopted", "r2"]),
                 "r2_to": float(dlk.loc["+ D x S", "r2"]), "n": int(dlk.loc["adopted", "rows"])}

# ---- the worked prospect (the highest-valued drafted prospect) -----------------------------------------------
wi = sk["value_M"].idxmax()
wr = sk.loc[wi]
g = str(wr["k_group"])
terms = CA[g]
parts = {c: terms[c]["b"] * float(wr[c]) for c in terms}
assert abs(sum(parts.values()) - float(wr["value_M"])) < 1e-9                # GUARD: the parts add to his value
N["worked"] = {"name": wr["player_name"], "date": wr["trade_date"], "draft": int(wr["draftYear"]), "pick": int(wr["pick"]),
               "k": int(wr["k"]), "g": g, "prod": float(wr["P"]), "age": float(wr["F"]) + 18, "is_d": float(wr["is_d"]),
               "inputs": {c: float(wr[c]) for c in terms}, "coefs": {c: terms[c]["b"] for c in terms}, "parts": parts,
               "value": float(wr["value_M"]), "slot": float(wr["value_slot_only_M"]), "own_out": float(wr["value_own_draft_out_M"]),
               "no_age": float(values_of("s2", sk.loc[[wi]])[0]), "s3": float(values_of("s3", sk.loc[[wi]])[0])}

# ---- the leagues prospects play in, and their NHLe factors ---------------------------------------------
con = sqlite3.connect(OUT / "ep_out" / "ep_prospects.db")
ep = pd.read_sql("select ep_player_id, season, league, gp from ep_skater_seasons", con)
ep["syr"] = ep["season"].str[:4].astype(int)
ep["gp"] = pd.to_numeric(ep["gp"], errors="coerce")
ep["ep_player_id"] = pd.to_numeric(ep["ep_player_id"], errors="coerce")
dr = pd.read_sql("select draft_year, draft_overall, ep_player_id from ep_draft_selections", con)
dr["ep_player_id"] = pd.to_numeric(dr["ep_player_id"], errors="coerce")
dr = dr[dr["draft_year"].between(2007, 2017)]
d0 = ep.merge(dr, on="ep_player_id")
d0 = d0[d0["syr"] == d0["draft_year"] - 1]                          # the draft season, D0
d0 = d0.sort_values("gp", ascending=False).drop_duplicates("ep_player_id")
lg_counts = d0["league"].value_counts()
nh = pd.read_csv(SRC / "nhle_temporal.csv")
top = [lg for lg in lg_counts.index if lg in set(nh["league"])][:10]
N["leagues"] = [{"league": lg, "draftees": int(lg_counts[lg]),
                 "nhle_2006": float(nh[(nh.league == lg) & (nh.season_start_year == nh[nh.league == lg].season_start_year.min())].nhle.iloc[0]),
                 "nhle_2025": float(nh[(nh.league == lg) & (nh.season_start_year == nh[nh.league == lg].season_start_year.max())].nhle.iloc[0])}
                for lg in top]
N["leagues_share_top10"] = float(lg_counts[top].sum() / lg_counts.sum())

# ---- figures --------------------------------------------------------------------------------------------
plt.rcParams.update({"font.family": "Calibri", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
INK, MUTED, A1, A2, A3, A4 = "#2B2A28", "#8A8984", "#2F6DB5", "#D9822B", "#3E9A5B", "#9B4F96"

# Figure 2: the star value by season against each rejected alternative, one panel each
s1 = N["step1"]
xs = np.arange(1, 9)                                                  # D+1 .. D+8
fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.7), dpi=200, sharey=True)
for ax, (rule, title) in zip(axes, (("no fade", "One value for every season"),
                                     ("straight line", "Straight-line decline"),
                                     ("same percentage", "Same percentage decline"))):
    ax.fill_between([4.6, 8.4], s1[4]["star"] - 1.96 * s1[4]["se"], s1[4]["star"] + 1.96 * s1[4]["se"],
                    color=A1, alpha=0.15, lw=0, zorder=1)
    ax.plot([4.6, 8.4], [s1[4]["star"]] * 2, color=A1, lw=2, zorder=3)
    ax.errorbar(xs[:4], [r["star"] for r in s1[:4]], yerr=[1.96 * r["se"] for r in s1[:4]], fmt="o", ms=5,
                color=A1, ecolor=A1, elinewidth=1.2, capsize=0, zorder=3)
    ax.plot(xs, N["fade_curve"][rule][:8], color=A2, lw=2, zorder=4)
    ax.axhline(0, color=MUTED, lw=0.6, zorder=0)
    ax.set_title(title, fontsize=9.5, color=INK, loc="left")
    ax.set_xticks(xs, [f"+{i}" for i in xs], fontsize=8)
    ax.set_xlim(0.5, 8.5)
    ax.grid(axis="y", color="#E6E5E0", lw=0.6, zorder=0)
axes[0].set_ylabel("Star value ($ millions)")
axes[0].set_ylim(-2.5, 23)
axes[1].set_xlabel("Season after the draft (D+n)")
axes[0].text(4.7, 4.4, "Adopted", color=A1, fontsize=8, va="center")
axes[0].text(5.2, 16.6, "Alternative", color=A2, fontsize=8, va="center")
fig.tight_layout(w_pad=0.6)
fig.savefig(FIG / "fig_star_value.png")
plt.close(fig)

# Figure 1: arrival timing, as a share of all the group's players
fig, ax = plt.subplots(figsize=(6.4, 3.7), dpi=200)
seasons = [f"D+{i}" for i in range(1, 10)]
for grp, col in (("picks 1-10", A1), ("rest of round 1", A2), ("round 2", A3), ("rounds 3-7", A4)):
    a = N["arrival"][grp]
    cum = np.cumsum([a["share_all"].get(s, 0.0) for s in seasons]) * 100
    assert abs(cum[-1] / 100 - a["n_arrived"] / a["n"]) < 1e-9, grp    # GUARD: ends at the share who ever arrived
    ax.plot(range(1, 10), cum, color=col, lw=1.8, marker="o", ms=3,
            label=f"{grp.capitalize()}: {a['n_arrived']} of {a['n']} reached the NHL")
    ax.text(9.15, cum[-1], f"{cum[-1]:.0f}%", color=INK, fontsize=8, va="center")
ax.set_xticks(range(1, 10), seasons)
ax.set_xlim(0.7, 9.6)
ax.set_ylim(0, 100)
ax.grid(axis="y", color="#E6E5E0", lw=0.6, zorder=0)
ax.set_xlabel("Season (D+1 is the season after the draft)")
ax.set_ylabel("Reached the NHL by then (%)")
ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
fig.tight_layout()
fig.savefig(FIG / "fig_arrival.png")
plt.close(fig)

# Figure 3: NHLe factors over time for the ten leagues draftees played most in their draft season
NAMES = {"ohl": "OHL", "whl": "WHL", "qmjhl": "QMJHL", "ushl": "USHL", "ncaa": "NCAA", "shl": "SHL", "khl": "KHL",
         "liiga": "Liiga", "mhl": "MHL", "allsvenskan": "Allsvenskan", "j20-nationell": "J20 Nationell",
         "u20-sm-liiga": "U20 SM-liiga", "czechia": "Czechia", "nl": "National League (Switzerland)", "ahl": "AHL",
         "usdp": "US NTDP", "ntdp": "US NTDP", "vhl": "VHL", "russia": "Russia", "extraliga": "Czech Extraliga",
         "czech": "Czech Extraliga", "hockeyallsvenskan": "Allsvenskan", "mestis": "Mestis", "bchl": "BCHL",
         "ajhl": "AJHL", "russia2": "VHL", "u20-elit": "U20 Elit", "u20-nationell": "J20 Nationell (Sweden)",
         "ushs-prep": "US high school (prep)", "ushs-mn": "US high school (Minnesota)"}
PAL = ["#2F6DB5", "#D9822B", "#3E9A5B", "#9B4F96", "#C0392B", "#7F8C8D", "#B7950B", "#17A589", "#5D6D7E", "#2B2A28"]
fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=200)
for lg, col in zip(top, PAL):
    x = nh[nh["league"] == lg].sort_values("season_start_year")
    hl = lg == "ohl"
    ax.plot(x["season_start_year"], x["nhle"], color=col, lw=2.6 if hl else 1.1, zorder=3 if hl else 2,
            label=f"{NAMES.get(lg, lg.upper())} ({int(lg_counts[lg])} draftees)")
ax.legend(frameon=False, fontsize=7.5, loc="center left", bbox_to_anchor=(1.0, 0.5))
ax.set_xlim(2006, 2025)
ax.set_xticks(range(2006, 2026, 3))
ax.set_xlabel("Season (start year)")
ax.set_ylabel("NHLe factor (NHL points per point)")
fig.tight_layout()
fig.savefig(FIG / "fig_nhle.png")
plt.close(fig)

# Figure 4: a #20 pick in D+2, value against production, before age (draft position each season, as Table 3)
qs = np.linspace(0, 25, 251)
C = N["coefs"]
fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
ax.plot(qs, np.full_like(qs, C["slot"]["1"]["S"]["b"] * p20), color=MUTED, lw=1.6, label="Draft position alone")
st1 = C["slot_lin"]["1"]
cu1 = C["slot_linsq"]["1"]
ln = st1["S"]["b"] * p20 + st1["P"]["b"] * qs
cv = cu1["S"]["b"] * p20 + cu1["P"]["b"] * qs + cu1["Q"]["b"] * qs ** 2
ax.plot(qs, ln, color=A2, lw=1.6, label="Draft position + linear production")
ax.plot(qs, cv, color=A1, lw=1.8, label="Draft position + linear and squared production")
for qq, v_ in N["prod_pct_k1"].items():
    ax.axvline(v_, color="#D5D4CF", lw=0.8, zorder=0)
    ax.text(v_ + 0.12, -0.45, f"{qq}th", ha="left", va="bottom", fontsize=8, color=MUTED)
ax.set_xlabel("Production: NHLe points per 82 games (50/30/20 over the three seasons before)")
ax.set_ylabel("Prospect xNPV ($ millions)")
ax.set_xlim(0, 25)
ax.set_ylim(-0.5, 6.5)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig_production.png")
plt.close(fig)
gap = ln - cv
N["fig_production"] = {"p20": p20, "gap_max": float(gap.max())}

# Figure 5: the Section 3 model (age, before the defenceman term of Section 4) for a #20 pick in D+2 at three ages
fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
a3 = N["coefs"]["s3"]["1"]
for A_, col, ls, lab in ((19.5, A1, "-", "Age 19.5 (drafted at his first opportunity)"),
                         (20.5, A2, "--", "Age 20.5"), (21.5, A4, ":", "Age 21.5")):
    ax.plot(qs, a3["S"]["b"] * p20 + a3["P"]["b"] * qs + a3["Q"]["b"] * qs ** 2 + a3["A"]["b"] * qs * (A_ - 18),
            color=col, lw=1.8, ls=ls, label=lab)
for qq, v_ in N["prod_pct_k1"].items():
    ax.axvline(v_, color="#D5D4CF", lw=0.8, zorder=0)
    ax.text(v_ + 0.12, -0.95, f"{qq}th", ha="left", va="bottom", fontsize=8, color=MUTED)
ax.set_xlabel("Production: NHLe points per 82 games (50/30/20 over the three seasons before)")
ax.set_ylabel("Prospect xNPV ($ millions)")
ax.set_xlim(0, 25)
ax.set_ylim(-1, 6.5)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig_age.png")
plt.close(fig)

# Figure 6: the traded prospects, draft position alone against the adopted model
fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=200)
for lab, sel, col in (("D+1 to D+3 (season at the trade)", dv["k_group"].astype(str).isin(["0", "1", "2"]), A1),
                      ("D+4", dv["k_group"].astype(str) == "3", A2), ("D+5 or later", dv["k_group"].astype(str) == "4+", A3)):
    ax.scatter(dv.loc[sel, "value_slot_only_M"], dv.loc[sel, "value_M"], s=14, color=col, alpha=0.8, label=lab)
lim = max(dv["value_M"].max(), dv["value_slot_only_M"].max()) + 0.3
ax.plot([-0.5, lim], [-0.5, lim], color=MUTED, lw=0.8, ls="--")
ax.set_xlim(-0.5, lim)
ax.set_ylim(-0.5, lim)
ax.set_xlabel("xNPV on draft position alone ($ millions)")
ax.set_ylabel("xNPV, adopted model ($ millions)")
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig_traded.png")
plt.close(fig)

(FIG / "numbers.json").write_text(json.dumps(N, indent=1, default=float), encoding="utf-8")
print(f"  wrote numbers.json and six figures in {FIG}")
print(f"  adopted: R-squared {FITS['adopted']['r2']:.4f} (adjusted {FITS['adopted']['adj']:.4f}), held-out "
      f"{FITS['adopted']['rmse']:.4f}; traded drafted ${N['traded']['tot_main']:.2f}M; worked prospect "
      f"{N['worked']['name']} ${N['worked']['value']:.2f}M")
