"""
prospect_doc_figures.py -- the numbers and figures behind "Valuing Prospects" (40_DOCS/Supervisor_Drafts/), v2.0.

v2.0 (2026-10-15, Thomas's 20 notes and the decisions of session 2026-10-15b): rebuilt for the revised document.
  * the model as it runs now: prospect_values.py v1.7 (deceased draftees out of every fit, age centred at 18,
    production squared as it is, no age-removed version);
  * new evidence: NHL arrival timing (nhl_arrival_timing.py), the slot-fade rules (prospect_fade_rules.py), the three
    forms of production (prospect_production_form.py, prospect_curve_vs_line.py), the age correlations (computed
    here, as prospect_age_correlation.py), Bacon's NHLe factors for the leagues draftees played in;
  * the model built up one term at a time, for each season (fitted here with the live script's rows and form);
  * figures: the star value with the rejected fade rules; arrival timing; NHLe by league; production (no age);
    age; the traded prospects.
Reads outputs only, except the regressions it refits for standard errors and the build-up (GUARD: the adopted
refit equals prospect_production_fits.csv to 1e-9; the worked prospect's parts add to his value).

INPUTS (OUTPUT_DIR): prospect_slot_years.csv, prospect_star_values.csv, prospect_nhle_look.csv,
prospect_nhle_coefficients.csv, prospect_nhle_rows.csv, prospect_age_look.csv, prospect_age_coefficients.csv,
prospect_production_fits.csv, prospect_values.csv, prospect_fade_rules.csv, prospect_fade_rules_scores.csv,
prospect_production_form_scores.csv, prospect_curve_vs_line.csv, nhl_arrival_timing_summary.csv,
draft_pick_linkage.csv, ep_out/ep_prospects.db; SOURCE_DIR/draft_slot_baseline.csv, nhle_temporal.csv.
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
import deceased_draftees as DD                                     # noqa: E402

import matplotlib                                                  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

SCRIPT_VERSION = "prospect_doc_figures.py v2.0 (2026-10-15)"
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
FIG = OUT / "prospect_doc"
FIG.mkdir(exist_ok=True)
N = {"script": SCRIPT_VERSION}
print(SCRIPT_VERSION)
GROUPS = ["0", "1", "2", "3", "4+"]
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later"}


def pval(b, se):
    """Two-sided p-value from a robust z statistic (normal reference)."""
    return math.erfc(abs(b / se) / math.sqrt(2))


def p_one(wins):
    """One-sided p: the share of 2,000 redraws in which the candidate is NOT lower."""
    return None if wins is None or pd.isna(wins) else (2000 - int(wins)) / 2000


bacon = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
N["p_star"] = {str(k): float(bacon[k]) for k in (1, 10, 13, 20, 32)}
N["excluded"] = [{"name": nm, "draft": y, "pick": k, "died": died} for (y, k), (nm, died) in DD.DECEASED.items()]

# ---- 1. the slot by season ---------------------------------------------------------------------------
sy = pd.read_csv(OUT / "prospect_slot_years.csv", dtype={"seasons_since_draft": str})
N["step1"] = [{"k": r.seasons_since_draft, "rows": int(r.rows), "players": int(r.players), "star": r.star_value_M,
               "se": r.se_M, "p": pval(r.star_value_M, r.se_M), "pick1": r.star_value_M * float(bacon[1]),
               "pick10": r.star_value_M * float(bacon[10]), "pick32": r.star_value_M * float(bacon[32]),
               "lodo_min": r.lodo_min_M, "lodo_max": r.lodo_max_M, "top10": int(r.top10_prospects)}
              for r in sy.itertuples()]
fr = pd.read_csv(OUT / "prospect_fade_rules.csv")
fs = pd.read_csv(OUT / "prospect_fade_rules_scores.csv")
RULES = ["separate", "no fade", "straight line", "same percentage"]
N["fade_curve"] = {r: [float(x) for x in fr[r]] for r in RULES}
N["fade_scores"] = {r: {"rmse": float(fs.loc[fs["rule"] == r, "rmse_M"].iloc[0]),
                        "p": p_one(fs.loc[fs["rule"] == r, "redraws_adopted_lower"].iloc[0]) if r != "separate" else None,
                        "total": float(fs.loc[fs["rule"] == f"traded total: {r}", "total_M"].iloc[0]),
                        "below_zero": int(fs.loc[fs["rule"] == f"traded total: {r}", "below_zero"].iloc[0])}
                    for r in RULES}
w_ = fs[fs["rule"].str.startswith("equal steps")].iloc[0]
N["fade_wald"] = {"chi2": float(w_["chi2"]), "p": float(w_["p"])}
N["fade_rows"] = int(fs.loc[fs["rule"] == "separate", "rows"].iloc[0])
ar = pd.read_csv(OUT / "nhl_arrival_timing_summary.csv")
N["arrival"] = {g: {"n_arrived": int(x.loc[x["season"] != "never", "arrived"].sum()),
                    "n": int(x["arrived"].sum()),
                    "share": {s: float(v) for s, v in zip(x["season"], x["share_of_arrivals"]) if s != "never"},
                    "never": int(x.loc[x["season"] == "never", "arrived"].iloc[0])}
                for g, x in ar.groupby("group")}

# ---- 2. production -----------------------------------------------------------------------------------
nl = pd.read_csv(OUT / "prospect_nhle_look.csv")
base = float(nl.loc[nl["arm"] == "slot", "rmse_M"].iloc[0])
N["prod_arms"] = [{"arm": r["arm"], "rmse": r["rmse_M"], "pct": 100 * (r["rmse_M"] / base - 1),
                   "by_k": [r[f"rmse_k{g}"] for g in GROUPS], "p": p_one(r["redraws_beating_slot"])}
                  for _, r in nl.iterrows()]
nc = pd.read_csv(OUT / "prospect_nhle_coefficients.csv", dtype={"k_group": str})
pr = pd.read_csv(OUT / "prospect_nhle_rows.csv", dtype={"k_group": str})
N["prod_rows"] = {"rows": len(pr), "players": int(pr[["draftYear", "pick"]].drop_duplicates().shape[0]),
                  "no_record_share": float(pr["no_record"].mean()),
                  "no_record_by_k": {g: int(x["no_record"].sum()) for g, x in pr.groupby("k_group")}}
k1 = pr[(pr["k_group"] == "1") & (pr["n_seasons"] > 0)]["nhle82"]
N["prod_pct_k1"] = {q: float(k1.quantile(q / 100)) for q in (25, 50, 75, 90)}
N["prod_median_by_k"] = {g: float(x.loc[x["n_seasons"] > 0, "nhle82"].median()) for g, x in pr.groupby("k_group")}
cv = pd.read_csv(OUT / "prospect_curve_vs_line.csv").set_index("comparison")
N["curve_vs_line"] = {c: {"straight": float(cv.loc[c, "rmse_straight"]), "curved": float(cv.loc[c, "rmse_curved"]),
                          "p": float(cv.loc[c, "one_sided_p"])} for c in ("1", "2", "3")}
N["squared_noage"] = {"rmse": float(cv.loc["2 squared alone", "rmse_squared_only"]),
                      "p_vs_curved": p_one(cv.loc["2 squared alone", "redraws_squared_lower_than_curved"]),
                      "p_vs_straight": p_one(cv.loc["2 squared alone", "redraws_squared_lower_than_straight"])}
pf = pd.read_csv(OUT / "prospect_production_form_scores.csv")
N["forms"] = {}
for s_, x in pf.groupby("sample"):
    N["forms"][s_] = {"rmse": {r.form: float(r.rmse_M) for r in x[x["rmse_M"].notna()].itertuples()},
                      "by_k": {r.form: [float(getattr(r, c)) for c in ("_4", "_5", "_6", "_7", "_8")]
                               for r in x[x["rmse_M"].notna()].itertuples()},
                      "pairs": {r.form: float(r.one_sided_p) for r in x[x["one_sided_p"].notna()].itertuples()},
                      "joint": {r.form: {"chi2": float(r.chi2), "df": int(r.df), "p": float(r.p)}
                                for r in x[x["chi2"].notna()].itertuples()}}
dpos = nc[nc["arm"] == "slot+production by position"]
N["defence_rate"] = [{"k": r.k_group, "f": r.nhle_f, "f_se": r.nhle_f_se, "d": r.nhle_d, "d_se": r.nhle_d_se,
                      "p_diff": None} for r in dpos.itertuples()]

# ---- 3. age ------------------------------------------------------------------------------------------
al = pd.read_csv(OUT / "prospect_age_look.csv")
abase = float(al.loc[al["arm"] == "chosen", "rmse_M"].iloc[0])
N["age_arms"] = [{"arm": r.arm, "rmse": r.rmse_M, "pct": 100 * (r.rmse_M / abase - 1),
                  "pct_vs_slot": 100 * (r.rmse_M / base - 1), "p": p_one(r.redraws_beating_chosen)}
                 for r in al.itertuples()]
for a_, (_, r) in zip(N["age_arms"], al.iterrows()):
    a_["by_k"] = [None if pd.isna(r.get(f"rmse_k{g}")) else float(r[f"rmse_k{g}"]) for g in GROUPS]
ac = pd.read_csv(OUT / "prospect_age_coefficients.csv", dtype={"k_group": str})
N["age_coefs"] = json.loads(ac.to_json(orient="records"))
N["prod_coefs"] = json.loads(nc.to_json(orient="records"))
# the age look's head-to-head of both age terms against the discount alone (its log; not in its csv)
import re                                                                  # noqa: E402
m_ = re.search(r"\+ age and age x production against \+ age x production alone: beats it in ([\d,]+) of",
               (OUT / "prospect_age_look_log.txt").read_text(encoding="utf-8"))
N["age_both_vs_discount_p"] = p_one(int(m_.group(1).replace(",", "")))
# the traded drafted and undrafted prospects under each production form (prospect_production_form.py)
tf = pd.read_csv(OUT / "prospect_production_form_traded.csv")
N["forms_traded"] = {f: {"drafted": float(tf.loc[tf["draftYear"].notna(), f"{f} (all drafts)"].sum()),
                         "below_zero": int((tf[f"{f} (all drafts)"] < 0).sum())}
                     for f in ("straight", "curved", "squared alone")}

# ---- the adopted model and the build-up, refitted ------------------------------------------------------
sv, fitrows = PV.star_values()
rates = PV.production_rates()
fits, prow = PV.production_fits(fitrows, rates)
live = pd.read_csv(OUT / "prospect_production_fits.csv", dtype={"k_group": str, "left_out": str})
# the age correlations on the fit rows
age_now = prow["past_elig"] + prow["k"] + PV.FIRST_ELIGIBLE_AGE
N["age_corr"] = {"age_vs_k": float(np.corrcoef(age_now, prow["k"])[0, 1]),
                 "past_vs_k": float(np.corrcoef(prow["past_elig"], prow["k"])[0, 1]),
                 "past_range_k0": [float(prow.loc[prow["k"] == 0, "past_elig"].min()),
                                   float(prow.loc[prow["k"] == 0, "past_elig"].max())]}


def fit(x, cols, cluster):
    cl = sorted(x["draftYear"].unique())
    yrs = x["draftYear"].values
    X = np.column_stack([x[c].values for c in cols] + [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float)
                                                       for c in cl[:-1]])
    if cluster:
        grp = pd.factorize(x["draftYear"].astype(str) + "-" + x["pick"].astype(str))[0]
        return sm.OLS(x["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": grp})
    return sm.OLS(x["remaining_M"].values, X).fit(cov_type="HC1")


def table(m, x, cols):
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    Xc = np.column_stack([np.ones(len(x))] + [x[c].values for c in cols])
    return {"rows": int(m.nobs), "players": int(x[["draftYear", "pick"]].drop_duplicates().shape[0]),
            "drafts": int(x["draftYear"].nunique()), "r2": float(m.rsquared),
            "terms": {c: {"b": float(m.params[i]), "se": float(m.bse[i]), "p": pval(m.params[i], m.bse[i]),
                          "vif": float(variance_inflation_factor(Xc, i + 1)) if len(cols) > 1 else 1.0}
                      for i, c in enumerate(cols)}}


BUILD = {"slot alone": lambda g: ["p_star"],
         "slot + production": lambda g: ["p_star", "nhle82", "no_record"],
         "slot + production + squared": lambda g: ["p_star", "nhle82", "nhle82_sq", "no_record"],
         "adopted": lambda g: PV.cols_for(g, "main")}
N["build"], N["adopted"] = {}, []
for g, x in prow.groupby("k_group"):
    N["build"][g] = {}
    for spec, cf in BUILD.items():
        cols = cf(g)
        m = fit(x, cols, g.endswith("+"))
        N["build"][g][spec] = table(m, x, cols)
        if spec == "adopted":
            lv = live[(live["version"] == "main") & (live["k_group"] == g) & (live["left_out"] == "none")].iloc[0]
            for i, c in enumerate(cols):
                assert abs(m.params[i] - lv[c]) < 1e-9, (g, c)           # GUARD: the live script's coefficients
            N["adopted"].append({"k": g, **N["build"][g][spec]})
print("  guard: the adopted refit equals prospect_production_fits.csv (PASS)")

# ---- 4. the traded prospects ----------------------------------------------------------------------------
v = pd.read_csv(OUT / "prospect_values.csv")
dv = v[v["status"].astype(str).str.startswith("prospect, valued")].copy()
uv = v[v["status"].astype(str).str.startswith("undrafted prospect, valued")].copy()
allv = pd.concat([dv, uv])
d_prod = dv["value_M"] - dv["value_slot_only_M"]
N["traded"] = {
    "drafted": len(dv), "drafted_players": int(dv["player_name"].nunique()), "undrafted": len(uv),
    "undrafted_skaters_valued": int((uv["value_basis"] == "production (undrafted, slot at zero)").sum()),
    "goalies": int(dv["is_goalie"].astype(bool).sum()),
    "tot_main": float(dv["value_M"].sum()), "tot_slot": float(dv["value_slot_only_M"].sum()),
    "tot_own_out": float(dv["value_own_draft_out_M"].sum()), "tot_all": float(allv["value_M"].sum()),
    "tot_undrafted": float(uv["value_M"].sum()), "max_undrafted": float(uv["value_M"].max()),
    "max_undrafted_name": uv.loc[uv["value_M"].idxmax(), "player_name"],
    "undrafted_k_min": int(uv["seasons_since_draft"].min()),
    "moved_025": int((d_prod.abs() >= 0.25).sum()), "moved_050": int((d_prod.abs() >= 0.5).sum()),
    "rank": float(dv["value_M"].rank().corr(dv["value_slot_only_M"].rank())),
    "top20_same_slot": len(set(dv.nlargest(20, "value_M")["asset_id"]) & set(dv.nlargest(20, "value_slot_only_M")["asset_id"])),
    "neg_drafted": int((dv["value_M"] < 0).sum()), "neg_drafted_sum": float(dv.loc[dv["value_M"] < 0, "value_M"].sum()),
    "neg_all": int((allv["value_M"] < 0).sum()), "neg_all_sum": float(allv.loc[allv["value_M"] < 0, "value_M"].sum()),
    "neg_min": float(allv["value_M"].min()),
    "top10": [{"date": r.trade_date, "name": r.player_name, "draft": int(r.draftYear), "pick": int(r.pick),
               "k": int(r.seasons_since_draft), "prod": None if pd.isna(r.nhle82) else float(r.nhle82),
               "past": None if pd.isna(r.past_elig) else float(r.past_elig), "main": r.value_M,
               "slot": r.value_slot_only_M} for r in dv.nlargest(10, "value_M").itertuples()],
}
sk = dv[~dv["is_goalie"].astype(bool) & dv["nhle82"].notna()].copy()
gk_tot = float(dv.loc[~dv.index.isin(sk.index), "value_M"].sum())
sk["no_record"] = (sk["n_prod_seasons"] == 0).astype(float)
sk["nhle82_sq"] = sk["nhle82"] ** 2                               # v1.7: squared as it is
sk["prod_x_age"] = sk["nhle82"] * sk["past_elig"]
sk["kg"] = sk["k_group"].astype(str)


def arm_total(tab, arm_by_k, cols_by_k):
    tot = 0.0
    for r in sk.itertuples():
        row = tab[(tab["k_group"] == r.kg) & (tab["arm"] == arm_by_k(r.kg))].iloc[0]
        xx = {"p_star": r.p_star, "nhle82": r.nhle82, "nhle82_sq": r.nhle82_sq, "no_record": r.no_record,
              "prod_x_age": r.prod_x_age, "past_elig": r.past_elig}
        tot += sum(row[c] * xx[c] for c in cols_by_k(r.kg))
    return tot + gk_tot


early = lambda g: g in ("0", "1", "2")                                       # noqa: E731
N["alt_totals"] = {
    "slot_no_fade": float((dv["p_star"] * N["step1"][0]["star"]).sum()),
    "slot_by_season": float(dv["value_slot_only_M"].sum()),
    "straight_slot_throughout": arm_total(nc, lambda g: "slot+production", lambda g: ["p_star", "nhle82", "no_record"]),
    "curved_slot_throughout": arm_total(nc, lambda g: "slot+production curved",
                                        lambda g: ["p_star", "nhle82", "nhle82_sq", "no_record"]),
    "curved_slot_early_no_age": arm_total(nc, lambda g: "slot+production curved" if early(g) else "production curved",
                                          lambda g: (["p_star"] if early(g) else []) + ["nhle82", "nhle82_sq", "no_record"]),
    "age_flat": arm_total(ac, lambda g: "+ age", lambda g: (["p_star"] if early(g) else [])
                          + ["nhle82", "nhle82_sq", "no_record", "past_elig"]),
    "age_both": arm_total(ac, lambda g: "+ age and age x production", lambda g: (["p_star"] if early(g) else [])
                          + ["nhle82", "nhle82_sq", "no_record", "past_elig", "prod_x_age"]),
    "adopted": float(dv["value_M"].sum()), "own_draft_out": float(dv["value_own_draft_out_M"].sum()),
    "skaters_priced": int(len(sk)), "others_on_slot": int(len(dv) - len(sk)),
}
cur = nc[nc["arm"] == "slot+production curved"]
N["slot_late"] = {g: {"b": float(r["p_star"]), "se": float(r["p_star_se"]), "p": pval(r["p_star"], r["p_star_se"])}
                  for g in ("3", "4+") for _, r in [(None, cur[cur["k_group"] == g].iloc[0])]}

# ---- the worked prospect (Nick Suzuki, the highest-valued drafted prospect) -----------------------------
w = dv.nlargest(1, "value_M").iloc[0]
g = str(w["k_group"])
terms = next(t for t in N["adopted"] if t["k"] == g)["terms"]
q, pe = float(w["nhle82"]), float(w["past_elig"])
inputs = {"p_star": float(w["p_star"]), "nhle82": q, "nhle82_sq": q * q, "no_record": 0.0, "prod_x_age": q * pe}
parts = {c: terms[c]["b"] * inputs[c] for c in terms}
assert abs(sum(parts.values()) - float(w["value_M"])) < 1e-9                # GUARD: the parts add to his value
wn = {"p_star": inputs["p_star"], "nhle82": q, "nhle82_sq": q * q, "no_record": 0.0}
no_age = sum(N["build"][g]["slot + production + squared"]["terms"][c]["b"] * wn[c]
             for c in N["build"][g]["slot + production + squared"]["terms"])
N["worked"] = {"name": w["player_name"], "date": w["trade_date"], "draft": int(w["draftYear"]), "pick": int(w["pick"]),
               "k": int(w["seasons_since_draft"]), "prod": q, "past": pe, "inputs": inputs,
               "coefs": {c: terms[c]["b"] for c in terms}, "parts": parts, "value": float(w["value_M"]),
               "slot": float(w["value_slot_only_M"]), "own_out": float(w["value_own_draft_out_M"]),
               "no_age": float(no_age)}

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

# Figure 1: the star value by season, with the three simpler rules over it
fig, ax = plt.subplots(figsize=(6.6, 3.5), dpi=200)
s1 = N["step1"]
for i in range(4):
    ax.bar(i, s1[i]["star"], color=A1, width=0.6, zorder=2,
           label="A separate value for each season (adopted; one value from D+5 on)" if i == 0 else None)
    ax.errorbar(i, s1[i]["star"], yerr=1.96 * s1[i]["se"], fmt="none", ecolor=INK, capsize=3, lw=1, zorder=3)
ax.bar(5.5, s1[4]["star"], color=A1, width=3.6, alpha=0.85, zorder=2)
ax.errorbar(5.5, s1[4]["star"], yerr=1.96 * s1[4]["se"], fmt="none", ecolor=INK, capsize=3, lw=1, zorder=3)
xs = np.arange(8)
for rule, col, ls in (("no fade", MUTED, "-"), ("straight line", A2, "--"), ("same percentage", A3, ":")):
    ax.plot(xs, N["fade_curve"][rule], color=col, lw=1.8, ls=ls, marker="o", ms=3, zorder=4,
            label={"no fade": "One value for every season", "straight line": "Straight-line decline (one interaction term)",
                   "same percentage": "Same percentage decline each season"}[rule])
ax.axhline(0, color=INK, lw=0.6)
ax.set_xticks(xs, [f"D+{i + 1}" for i in range(8)])
ax.set_xlabel("Season (D+1 is the season after the draft)")
ax.set_ylabel("Star value ($ millions, 2025-26 cap)")
ax.set_ylim(-2.5, 23)
ax.legend(frameon=False, fontsize=8, loc="upper right")
fig.tight_layout()
fig.savefig(FIG / "fig_star_value.png")
plt.close(fig)

# Figure: arrival timing, cumulative share of arrivals by season, by draft group
fig, ax = plt.subplots(figsize=(6.4, 3.3), dpi=200)
seasons = [f"D+{i}" for i in range(1, 10)]
for grp, col in (("picks 1-10", A1), ("rest of round 1", A2), ("round 2", A3), ("rounds 3-7", A4)):
    a = N["arrival"][grp]
    cum = np.cumsum([a["share"].get(s, 0.0) for s in seasons]) * 100
    ax.plot(range(1, 10), cum, color=col, lw=1.8, marker="o", ms=3,
            label=f"{grp.capitalize()}: {a['n_arrived']} of {a['n']} reached the NHL")
ax.set_xticks(range(1, 10), seasons)
ax.set_ylim(0, 102)
ax.set_xlabel("Season of the first NHL season of 10 or more games (a goaltender's first game)")
ax.set_ylabel("Share of those who reached the NHL (%)")
ax.legend(frameon=False, fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig(FIG / "fig_arrival.png")
plt.close(fig)

# Figure: NHLe factors over time for the ten leagues draftees played most in their draft season
NAMES = {"ohl": "OHL", "whl": "WHL", "qmjhl": "QMJHL", "ushl": "USHL", "ncaa": "NCAA", "shl": "SHL", "khl": "KHL",
         "liiga": "Liiga", "mhl": "MHL", "allsvenskan": "Allsvenskan", "j20-nationell": "J20 Nationell",
         "u20-sm-liiga": "U20 SM-liiga", "czechia": "Czechia", "nl": "National League (Switzerland)", "ahl": "AHL",
         "usdp": "US NTDP", "ntdp": "US NTDP", "vhl": "VHL", "russia": "Russia", "extraliga": "Czech Extraliga",
         "czech": "Czech Extraliga", "hockeyallsvenskan": "Allsvenskan", "mestis": "Mestis", "bchl": "BCHL",
         "ajhl": "AJHL", "russia2": "VHL", "u20-elit": "U20 Elit", "u20-nationell": "J20 Nationell (Sweden)",
         "ushs-prep": "US high school (prep)", "ushs-mn": "US high school (Minnesota)"}
HIGHLIGHT = "ohl"
PAL = ["#2F6DB5", "#D9822B", "#3E9A5B", "#9B4F96", "#C0392B", "#7F8C8D", "#B7950B", "#17A589", "#5D6D7E", "#2B2A28"]
fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=200)
for lg, col in zip(top, PAL):
    x = nh[nh["league"] == lg].sort_values("season_start_year")
    hl = lg == HIGHLIGHT
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

# Figure: a #20 pick in D+2, value against production, before age (slot alone, straight, curved)
coef = {(r["k_group"], r["arm"]): r for _, r in nc.iterrows()}
p20 = float(bacon[20])
qs = np.linspace(0, 25, 251)
st = coef[("1", "slot+production")]
cu = coef[("1", "slot+production curved")]
fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
ax.plot(qs, np.full_like(qs, coef[("1", "slot")]["p_star"] * p20), color=MUTED, lw=1.6, label="Slot alone")
ax.plot(qs, st["p_star"] * p20 + st["nhle82"] * qs, color=A2, lw=1.6, label="Slot + production, straight line")
ax.plot(qs, cu["p_star"] * p20 + cu["nhle82"] * qs + cu["nhle82_sq"] * qs ** 2, color=A1, lw=1.8,
        label="Slot + production, curved")
for qq, v_ in N["prod_pct_k1"].items():
    ax.axvline(v_, color="#D5D4CF", lw=0.8, zorder=0)
    ax.text(v_ + 0.12, -0.45, f"{qq}th", ha="left", va="bottom", fontsize=8, color=MUTED)
ax.set_xlabel("Production: NHL-equivalent points per 82 games (50/30/20 over the three seasons before)")
ax.set_ylabel("Prospect value ($ millions)")
ax.set_xlim(0, 25)
ax.set_ylim(-0.5, 6.5)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig_production.png")
plt.close(fig)
gap = (st["p_star"] * p20 + st["nhle82"] * qs) - (cu["p_star"] * p20 + cu["nhle82"] * qs + cu["nhle82_sq"] * qs ** 2)
N["fig_production"] = {"p20": p20, "gap_max": float(gap.max()), "gap_at": float(qs[np.argmax(gap)])}
diff = (cu["nhle82"] * qs + cu["nhle82_sq"] * qs ** 2) - (st["nhle82"] * qs) + (cu["p_star"] - st["p_star"]) * p20
above = qs[(diff > 0) & (qs > 5)]
N["fig_production"]["cross"] = float(above.min()) if len(above) else None

# Figure: age, the adopted model for a #20 pick in D+2
ad = next(t for t in N["adopted"] if t["k"] == "1")["terms"]
fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
for Y, col, ls, lab in ((0.5, A1, "-", "18.5 in the autumn after his draft (a first-time eligible player)"),
                        (1.5, A2, "--", "19.5 (drafted a year older)"), (2.5, A4, ":", "20.5 (drafted two years older)")):
    val = ad["p_star"]["b"] * p20 + ad["nhle82"]["b"] * qs + ad["nhle82_sq"]["b"] * qs ** 2 + ad["prod_x_age"]["b"] * qs * Y
    ax.plot(qs, val, color=col, lw=1.8, ls=ls, label=lab)
for qq, v_ in N["prod_pct_k1"].items():
    ax.axvline(v_, color="#D5D4CF", lw=0.8, zorder=0)
    ax.text(v_ + 0.12, -0.95, f"{qq}th", ha="left", va="bottom", fontsize=8, color=MUTED)
ax.set_xlabel("Production: NHL-equivalent points per 82 games (50/30/20 over the three seasons before)")
ax.set_ylabel("Prospect value ($ millions)")
ax.set_xlim(0, 25)
ax.set_ylim(-1, 6.5)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig_age.png")
plt.close(fig)

# Figure: the traded prospects, slot alone against the adopted model
fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=200)
for lab, sel, col in (("D+1 to D+3 (season at the trade)", dv["k_group"].isin(["0", "1", "2"]), A1),
                      ("D+4", dv["k_group"] == "3", A2), ("D+5 or later", dv["k_group"] == "4+", A3)):
    ax.scatter(dv.loc[sel, "value_slot_only_M"], dv.loc[sel, "value_M"], s=14, color=col, alpha=0.8, label=lab)
lim = max(dv["value_M"].max(), dv["value_slot_only_M"].max()) + 0.3
ax.plot([-0.5, lim], [-0.5, lim], color=MUTED, lw=0.8, ls="--")
ax.set_xlim(-0.5, lim)
ax.set_ylim(-0.5, lim)
ax.set_xlabel("Value on the slot alone ($ millions)")
ax.set_ylabel("Value, adopted model ($ millions)")
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig_traded.png")
plt.close(fig)

(FIG / "numbers.json").write_text(json.dumps(N, indent=1, default=float), encoding="utf-8")
print(f"  wrote numbers.json and six figures in {FIG}")
print(f"  worked prospect: {N['worked']['name']} ({N['worked']['date']}): ${N['worked']['value']:.2f}M; top leagues: "
      + ", ".join(f"{r['league']} {r['draftees']}" for r in N["leagues"]))
