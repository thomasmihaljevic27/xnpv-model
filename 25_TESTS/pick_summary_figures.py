"""
pick_summary_figures.py v1.2 -- the figures and computed tables of "Valuing Draft Picks".

WHY (Thomas, 2026-10-09): the document must show, with graphs and tables, why each decision about
the pick curve was made. CLAUDE.md: each figure is read off a run, with its row label. This script
reads the outputs of the live scripts and the tests and writes:
  OUTPUT_DIR/pick_summary/*.png      the figures
  OUTPUT_DIR/pick_summary/numbers.json   every computed number the document quotes
It changes no model file. Needs matplotlib (run it with an environment that has it).

v1.2 (after Thomas's comments on v2.0 of the document): one star value for every year (pick_curve.py
v1.2), so the trade-season figure is gone; Figure 1 on a linear axis; the actual average at each
pick in Table 1; the regression results (Table 2, with and without the pick number); star value by
draft (the evidence for one value); draft-slot persistence (the evidence for the round average);
Brayden Point's draft and junior seasons; the effect of each appendix choice in pick dollars.

SOURCES: pick_curve_players.csv / pick_curve_seasons.csv / pick_curve_scales.csv (pick_curve.py
v1.2), top_pick_control_look.csv (top_pick_control_look.py v1.1), pick_slot_persistence.csv
(pick_slot_persistence.py v1.0), SOURCE_DIR/draft_slot_baseline.csv (Bacon), ep_prospects.db (Point's
junior seasons). Figures in the reference palette, light surface.

Run from the repo root:  <python with matplotlib> 25_TESTS/pick_summary_figures.py
"""

import json
import os
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                   # noqa: E402
import numpy as np                                # noqa: E402
import pandas as pd                               # noqa: E402
import statsmodels.api as sm                      # noqa: E402
from dotenv import load_dotenv                    # noqa: E402

SCRIPT_VERSION = "pick_summary_figures.py v1.2 (2026-10-09)"
print(SCRIPT_VERSION)
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
FIG = OUT / "pick_summary"
FIG.mkdir(exist_ok=True)
for f in ("pick_curve_log.txt", "traded_pick_values_log.txt"):
    print(f"  {f}: {(OUT / f).read_text(encoding='utf-8').splitlines()[0]}")

BLUE, ORANGE, AQUA, GRAY, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#52514e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#c9c8c3",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#ecebe8", "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 200, "savefig.bbox": "tight", "legend.frameon": False})
N = {}
bacon = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")
sc = pd.read_csv(OUT / "pick_curve_scales.csv").set_index("scale_kind")
STAR, STAR_S = float(sc.loc["main", "scale_M"]), float(sc.loc["sensitivity", "scale_M"])
N["star_value"] = {"main": STAR, "main_se": float(sc.loc["main", "se_M"]), "sens": STAR_S,
                   "sens_se": float(sc.loc["sensitivity", "se_M"])}


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)
    print(f"  wrote {name}")


pc = pd.read_csv(OUT / "pick_curve_players.csv")
pc["y"] = pc["surplus"] / 1e6
CL = sorted(pc["draftYear"].unique())


def year_cols(frame):
    yrs = frame["draftYear"].values
    cl = sorted(set(yrs))
    return [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]


# ---- Figure 1 and Table 1: three curves, adopted pricing ------------------------------------------
def fit_curve(frame, kind):
    Y = year_cols(frame)
    if kind == "star":
        b = np.linalg.lstsq(np.column_stack([frame["p_star"].values] + Y), frame["y"].values, rcond=None)[0]
        return lambda pick: b[0] * bacon.loc[np.asarray(pick), "p_star"].values
    x = frame["pick"].values.astype(float) if kind == "line" else np.log(frame["pick"].values)
    b = np.linalg.lstsq(np.column_stack([np.ones(len(frame)), x] + Y), frame["y"].values, rcond=None)[0]
    if kind == "line":
        return lambda pick: b[0] + b[1] * np.asarray(pick, float)
    return lambda pick: b[0] + b[1] * np.log(np.asarray(pick, float))


grid = np.arange(1, 218)
fits = {k: fit_curve(pc, k) for k in ("line", "log", "star")}
held = {}
for k in fits:
    sq = []
    for c in CL:
        tr, te = pc[pc["draftYear"] != c], pc[pc["draftYear"] == c]
        sq.append((te["y"].values - fit_curve(tr, k)(te["pick"].values)) ** 2)
    held[k] = float(np.sqrt(np.concatenate(sq).mean()))
per_pick = pc.groupby("pick")["y"].mean()
fig, ax = plt.subplots(figsize=(6.5, 3.4))
ax.scatter(per_pick.index, per_pick.values, s=9, color="#bdbcb6", zorder=2,
           label="Average surplus of the players taken at that pick")
for k, colour, lab in (("line", ORANGE, "Straight line in the pick number"), ("log", AQUA, "Log of the pick number"),
                       ("star", BLUE, "Star value x star probability (adopted)")):
    ax.plot(grid, fits[k](grid), color=colour, lw=2, zorder=3, label=lab)
ax.set_xlim(0, 220)
ax.set_xticks([1, 32, 64, 96, 128, 160, 192, 217])
ax.set_xlabel("Overall pick")
ax.set_ylabel("Surplus per pick ($M, 2025-26 cap)")
ax.set_ylim(-3, 32)
ax.axhline(0, color="#c9c8c3", lw=0.8)
ax.legend(loc="upper right", fontsize=8)
save(fig, "f1_shape.png")
at = [1, 10, 32, 64]
N["t1"] = {"curves": {k: {str(p): float(fits[k](np.array([p]))[0]) for p in at} for k in fits},
           "actual": {str(p): float(per_pick[p]) for p in at},
           "actual_n": {str(p): int((pc["pick"] == p).sum()) for p in at}, "held_out": held,
           "picks": int(len(pc)), "never_played": int((pc["nhl_seasons"] == 0).sum()),
           "mean_1_10": float(pc.loc[pc["pick"] <= 10, "y"].mean()),
           "mean_after_32": float(pc.loc[pc["pick"] > 32, "y"].mean())}

# ---- Table 2: the regression, and the same with the pick number added ----------------------------------
Y = year_cols(pc)
mA = sm.OLS(pc["y"].values, np.column_stack([pc["p_star"].values] + Y)).fit(cov_type="HC1")
mB = sm.OLS(pc["y"].values, np.column_stack([np.ones(len(pc)), pc["p_star"].values, pc["pick"].values.astype(float)] + Y)).fit(cov_type="HC1")
sst = ((pc["y"] - pc["y"].mean()) ** 2).sum()
N["t2"] = {"A": {"b": mA.params[0], "se": mA.bse[0], "p": mA.pvalues[0], "r2": 1 - mA.ssr / sst},
           "B": {"a": mB.params[0], "a_se": mB.bse[0], "b1": mB.params[1], "b1_se": mB.bse[1], "b1_p": mB.pvalues[1],
                 "b2": mB.params[2], "b2_se": mB.bse[2], "b2_p": mB.pvalues[2], "r2": 1 - mB.ssr / sst},
           "n": int(len(pc)), "drafts": len(CL)}
assert abs(mA.params[0] - STAR) < 1e-6, "Table 2 must reproduce pick_curve.py's star value"
print(f"  Table 2: star value {mA.params[0]:.2f} (se {mA.bse[0]:.2f}); with pick number: b1 {mB.params[1]:.2f}, "
      f"b2 {mB.params[2]:+.4f} (se {mB.bse[2]:.4f}, p {mB.pvalues[2]:.3f})")

# ---- stars' share of surplus (the evidence that value comes from stars) ---------------------------------
st = pd.read_csv(OUT / "pick_star_and_rights_checks.csv")[["draftYear", "pick", "star"]]
m = pc.merge(st, on=["draftYear", "pick"], how="inner")
m = m[m["draftYear"] <= 2015]
N["stars"] = {"picks": int(len(m)), "stars": int(m["star"].sum()), "share_picks": float(100 * m["star"].mean()),
              "share_surplus": float(100 * m.loc[m["star"], "surplus"].sum() / m["surplus"].sum()),
              "top10_share_picks": float(100 * m.loc[m["pick"] <= 10, "star"].mean()),
              "top10_share_surplus": float(100 * m.loc[(m["pick"] <= 10) & m["star"], "surplus"].sum() / m.loc[m["pick"] <= 10, "surplus"].sum())}

# ---- Figure 2: the star value fitted on each draft -------------------------------------------------------
yrs = pc["draftYear"].values
Xc = np.column_stack([pc["p_star"].values * (yrs == c) for c in CL] + Y)
mc = sm.OLS(pc["y"].values, Xc).fit(cov_type="HC1")
R = np.zeros((len(CL) - 1, Xc.shape[1]))
for j in range(len(CL) - 1):
    R[j, j], R[j, len(CL) - 1] = 1, -1
w = mc.wald_test(R, scalar=True)
bc, sec = mc.params[:len(CL)], mc.bse[:len(CL)]
t = (yrs - 2012).astype(float)
tr_all = sm.OLS(pc["y"].values, np.column_stack([pc["p_star"].values, pc["p_star"].values * t] + Y)).fit(cov_type="HC1")
keep = ~pc["draftYear"].isin([2015, 2016]).values
pk = pc[keep]
tr_wo = sm.OLS(pk["y"].values, np.column_stack([pk["p_star"].values, pk["p_star"].values * (pk["draftYear"].values - 2012)] + year_cols(pk))).fit(cov_type="HC1")
no17 = pc[pc["draftYear"] != 2017]
b17 = np.linalg.lstsq(np.column_stack([no17["p_star"].values] + year_cols(no17)), no17["y"].values, rcond=None)[0][0]
fig, ax = plt.subplots(figsize=(6.5, 3.0))
ax.errorbar(CL, bc, yerr=2 * sec, fmt="o", color=BLUE, ecolor=BLUE, elinewidth=1, capsize=2, ms=5,
            label="Star value fitted on one draft (bars: two standard errors)")
ax.axhline(STAR, color=INK2, lw=1.3, label=f"All eleven drafts, the adopted value ({STAR:.1f})")
ax.axhline(STAR_S, color=GRAY, lw=1.2, ls="--", label=f"Without 2015 and 2016, the sensitivity ({STAR_S:.1f})")
ax.set_xticks(CL, [str(c) for c in CL])
ax.set_xlabel("Draft")
ax.set_ylabel("Star value ($M, 2025-26 cap)")
ax.legend(loc="upper left", fontsize=8)
save(fig, "f2_star_value_by_draft.png")
N["f2"] = {"scale": [float(v) for v in bc], "se": [float(v) for v in sec], "wald_chi2": float(w.statistic),
           "wald_df": len(CL) - 1, "wald_p": float(w.pvalue),
           "trend_all": float(tr_all.params[1]), "trend_all_p": float(tr_all.pvalues[1]),
           "trend_wo": float(tr_wo.params[1]), "trend_wo_p": float(tr_wo.pvalues[1]), "star_no2017": float(b17)}

# ---- Figure 3: control cost -----------------------------------------------------------------------------
tl = pd.read_csv(OUT / "top_pick_control_look.csv")
rows = []
for lo, hi in ((1, 10), (11, 15), (16, 32)):
    g = tl[tl["pick"].between(lo, hi) & (tl["nhl_seasons"] > 0)]
    rows.append({"band": f"Picks {lo}-{hi}", "n": len(g), "value": g["value_$M"].mean(),
                 "cost_model": g["cost_model_$M"].mean(), "cost_actual": g["cost_actual_$M"].mean()})
cc = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(6.5, 3.0))
x = np.arange(len(cc))
for off, col, colour, lab in ((-0.27, "value", BLUE, "Value delivered"),
                              (0, "cost_model", AQUA, "Cost charged by the model (qualifying-offer chain)"),
                              (0.27, "cost_actual", ORANGE, "Cost actually paid (cap hits)")):
    ax.bar(x + off, cc[col], width=0.25, color=colour, label=lab)
ax.set_xticks(x, [f"{b}\n({n} NHL players)" for b, n in zip(cc["band"], cc["n"])])
ax.set_ylabel("$M per player, while his club holds his rights")
ax.legend(loc="upper right", fontsize=8)
save(fig, "f3_control_cost.png")
N["f3"] = cc.round(3).to_dict("records")

# ---- Figure 4: draft-slot persistence ---------------------------------------------------------------------
ps = pd.read_csv(OUT / "pick_slot_persistence.csv")
bands = [(1, 5), (6, 10), (11, 16), (17, 24), (25, 32)]
rows = []
for k in (1, 2):
    j = ps[ps["gap"] == k]
    for lo, hi in bands:
        g = j[j["slot"].between(lo, hi)]
        rows.append({"gap": k, "band": f"{lo}-{hi}", "n": len(g), "mean": g["later"].mean(), "p10": g["later"].quantile(.1),
                     "p90": g["later"].quantile(.9), "value": STAR * g["later_star"].mean(),
                     "round_avg": STAR * g["round_avg_star"].mean()})
pr = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(6.5, 3.0))
xb = np.arange(len(bands))
for k, off, colour, lab in ((1, -0.12, BLUE, "Next draft"), (2, 0.12, ORANGE, "Two drafts later")):
    q = pr[pr["gap"] == k]
    ax.errorbar(xb + off, q["mean"], yerr=[q["mean"] - q["p10"], q["p90"] - q["mean"]], fmt="o", color=colour,
                ecolor=colour, elinewidth=1, capsize=3, ms=5, label=lab)
ax.set_xticks(xb, [f"Picked {b[0]}-{b[1]}" for b in bands])
ax.set_ylim(33, 0)
ax.set_yticks([1, 8, 16, 24, 32])
ax.set_ylabel("Its own first-round slot in a later draft")
ax.set_xlabel("The team's own first-round slot in this draft")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=8)
save(fig, "f4_slot_persistence.png")
cor = {k: float(np.corrcoef(ps.loc[ps["gap"] == k, "slot"], ps.loc[ps["gap"] == k, "later"])[0, 1]) for k in (1, 2)}
N["f4"] = {"rows": pr.round(3).to_dict("records"), "corr": cor, "pairs": {k: int((ps["gap"] == k).sum()) for k in (1, 2)},
           "median_move": {k: float((ps.loc[ps["gap"] == k, "later"] - ps.loc[ps["gap"] == k, "slot"]).abs().median()) for k in (1, 2)}}

# ---- values by pick, traded picks, Point, appendix effects ---------------------------------------------
N["values"] = {str(k): {"p": float(bacon.loc[k, "p_star"]), "v": STAR * float(bacon.loc[k, "p_star"]),
                        "v_s": STAR_S * float(bacon.loc[k, "p_star"])} for k in (1, 2, 3, 5, 10, 20, 32, 64, 100, 200)}
tp = pd.read_csv(OUT / "traded_pick_values.csv")
N["traded"] = {"picks": int(len(tp)), "total": float(tp["value_M"].sum()), "total_s": float(tp["value_sensitivity_M"].sum()),
               "conditional": int(tp["conditional"].sum()),
               "by_method": tp.groupby("method")["asset_id"].size().to_dict(),
               "by_round": tp.groupby("pick_round")["value_M"].mean().round(3).to_dict(),
               "first_round": int((tp["pick_round"] == 1).sum())}
slot = tp[tp["method"] == "slot on the trade date"]
gap = (slot["projected_slot"] - slot["actual_slot"]).abs()
N["traded"]["projection"] = {"picks": int(len(slot)), "within3": int((gap <= 3).sum()), "median": float(gap.median())}
se_ = pd.read_csv(OUT / "pick_curve_seasons.csv")
s = se_[(se_["draftYear"] == 2014) & (se_["pick"] == 79)].copy()
s["value_M"], s["cost_M"] = s["value_share"] * 95.5, s["cost_share"] * 95.5
pt = pc[(pc["draftYear"] == 2014) & (pc["pick"] == 79)].iloc[0]
con = sqlite3.connect(OUT / "ep_out" / "ep_prospects.db")
junior = pd.read_sql("select season, league, team, gp from ep_skater_seasons where player like 'Brayden Point%' "
                     "and season in ('2014-2015', '2015-2016') order by season", con)
N["point"] = {"total": float(pt["surplus"] / 1e6), "p_star": float(bacon.loc[79, "p_star"]), "window_end": int(pt["window_end"]),
              "seasons": s[["season", "gp", "war_82", "in_entry_level", "value_M", "cost_M"]].round(4).to_dict("records"),
              "junior": junior.to_dict("records")}
p10 = float(bacon.loc[10, "p_star"])
N["pick10"] = {"main": STAR * p10, "sens": STAR_S * p10}
(FIG / "numbers.json").write_text(json.dumps(N, indent=1, default=float), encoding="utf-8")
print(f"  wrote numbers.json; Wald chi2 {N['f2']['wald_chi2']:.1f} p {N['f2']['wald_p']:.4f}; trend all {N['f2']['trend_all']:+.2f} "
      f"(p {N['f2']['trend_all_p']:.3f}), without 2015-16 {N['f2']['trend_wo']:+.2f} (p {N['f2']['trend_wo_p']:.3f}); "
      f"star value without 2017 {b17:.2f}")
print(f"  Point junior rows: {junior.to_dict('records')}")
