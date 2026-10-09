"""
pick_summary_figures.py -- the figures and computed tables of the draft-pick summary document.

WHY (Thomas, 2026-10-09): the summary for the supervisor must show, with graphs and tables, why
each decision about the pick curve was made. CLAUDE.md: each figure is read off a run, with its
row label. This script reads the outputs of the live scripts and the tests and writes:
  OUTPUT_DIR/pick_summary/f1_shape.png ... f5_control_cost.png   (the figures)
  OUTPUT_DIR/pick_summary/numbers.json                           (every computed number quoted)
It changes no model file. Needs matplotlib (run it with an environment that has it).

SOURCES, by figure
  f1  pick_first_look_players.csv (skaters, first-look pricing, the basis of the shape test) and
      pick_curve_shape_curves.csv (each shape fitted on all eleven classes, average draft year)
  f2  pick_star_and_rights_checks.csv (our star share, Bacon's definition) and Bacon's p_star
  f3  pick_curve_players.csv (the adopted pricing): one scale per draft class, HC1 errors
  f4  pick_curve_scales.csv: knowable scale by trade season, pooled scale
  f5  top_pick_control_look.csv: modelled and actual control cost, first round
  tables: pick_curve_seasons.csv (worked player), pick_curve_scales.csv and draft_slot_baseline.csv
      (values by pick), traded_pick_values.csv (traded picks)

Run from the repo root:  <python with matplotlib> 25_TESTS/pick_summary_figures.py
"""

import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                   # noqa: E402
import numpy as np                                # noqa: E402
import pandas as pd                               # noqa: E402
import statsmodels.api as sm                      # noqa: E402
from dotenv import load_dotenv                    # noqa: E402

SCRIPT_VERSION = "pick_summary_figures.py v1.1 (2026-10-09)"
print(SCRIPT_VERSION)
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
FIG = OUT / "pick_summary"
FIG.mkdir(exist_ok=True)
for f in ("pick_curve_log.txt", "pick_first_look_log.txt", "traded_pick_values_log.txt"):
    print(f"  {f}: {(OUT / f).read_text(encoding='utf-8').splitlines()[0]}")

# ---- chart style: reference palette, light surface, thin marks, recessive axes -----------------
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#c9c8c3",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#ecebe8", "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 200, "savefig.bbox": "tight", "legend.frameon": False})
N = {}
bacon = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)
    print(f"  wrote {name}")


# ---- f1: the shape, on the ADOPTED pricing (v1.1) ------------------------------------------------
# v1.0 drew this on the first-look pricing (skaters only, slides modelled), the basis of the shape
# test. v1.1 refits the three curves the document compares on pick_curve_players.csv (all positions,
# no slides, lapsed rights at zero), so every number in that section shares one basis. Each curve has
# draft-year indicators (sum to zero) and is read at the average draft year; held-out miss = leave one
# draft out, refit, predict each of its picks (the shape test's scoring), RMSE in $M a pick.
pcf = pd.read_csv(OUT / "pick_curve_players.csv")
pcf["y"], pcf["log_pick"] = pcf["surplus"] / 1e6, np.log(pcf["pick"])
CLf = sorted(pcf["draftYear"].unique())


def fit_curve(frame, kind):
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    Y = [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]
    if kind == "star":                                   # adopted: through zero on the star probability
        b = np.linalg.lstsq(np.column_stack([frame["p_star"].values] + Y), frame["y"].values, rcond=None)[0]
        return lambda pick: b[0] * bacon.loc[pick, "p_star"].values
    x = frame["pick"].values if kind == "line" else frame["log_pick"].values
    b = np.linalg.lstsq(np.column_stack([np.ones(len(frame)), x] + Y), frame["y"].values, rcond=None)[0]
    return (lambda pick: b[0] + b[1] * np.asarray(pick, float)) if kind == "line" else            (lambda pick: b[0] + b[1] * np.log(np.asarray(pick, float)))


grid = np.arange(1, 218)
fits = {k: fit_curve(pcf, k) for k in ("line", "log", "star")}
held = {}
for k in fits:
    sq = []
    for c in CLf:
        tr, te = pcf[pcf["draftYear"] != c], pcf[pcf["draftYear"] == c]
        sq.append((te["y"].values - fit_curve(tr, k)(te["pick"].values)) ** 2)
    held[k] = float(np.sqrt(np.concatenate(sq).mean()))
per_pick = pcf.groupby("pick")["y"].mean()
fig, ax = plt.subplots(figsize=(6.5, 3.4))
ax.scatter(per_pick.index, per_pick.values, s=9, color="#bdbcb6", zorder=2,
           label="Average surplus of the players taken at that pick")
for k, colour, lab in (("line", ORANGE, "Straight line in the pick number"), ("log", AQUA, "Log of the pick number"),
                       ("star", BLUE, "Star probability x dollar scale (adopted)")):
    ax.plot(grid, fits[k](grid), color=colour, lw=2, zorder=3, label=lab)
ax.set_xscale("log")
ax.set_xticks([1, 2, 3, 5, 10, 20, 32, 64, 100, 200])
ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
ax.set_xlabel("Overall pick (log scale)")
ax.set_ylabel("Surplus per pick ($M, 2025-26 cap)")
ax.set_ylim(-3, 32)
ax.axhline(0, color="#c9c8c3", lw=0.8)
ax.legend(loc="upper right", fontsize=8)
save(fig, "f1_shape.png")
N["f1"] = {"raw_mean_pick1": float(per_pick[1]), "raw_mean_33plus": float(pcf.loc[pcf["pick"] > 32, "y"].mean()),
           "raw_mean_1_10": float(pcf.loc[pcf["pick"] <= 10, "y"].mean()),
           "never_played": int((pcf["nhl_seasons"] == 0).sum()), "picks": int(len(pcf)),
           "curves": {k: {str(pk): float(fits[k](np.array([pk]))[0]) for pk in (1, 10, 32, 64, 150)} for k in fits},
           "held_out_rmse": held}
print(f"  f1 basis: adopted pricing, {len(pcf):,} picks; held-out RMSE {held}")

# ---- f2: star rates, ours against Bacon's ------------------------------------------------------------
sr = pd.read_csv(OUT / "pick_star_and_rights_checks.csv")
sr = sr[sr["draftYear"] <= 2015]
bands = [(1, 1), (2, 3), (4, 10), (11, 20), (21, 32), (33, 64), (65, 128), (129, 217)]
rows = []
for lo, hi in bands:
    s = sr[sr["pick"].between(lo, hi)]
    m = s["star"].mean()
    rows.append({"band": f"{lo}" if lo == hi else f"{lo}-{hi}", "n": len(s), "ours": 100 * m,
                 "se2": 200 * np.sqrt(m * (1 - m) / len(s)), "bacon": 100 * s["p_star"].mean()})
st = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(6.5, 3.0))
x = np.arange(len(st))
ax.bar(x - 0.18, st["bacon"], width=0.34, color=BLUE, label="Bacon's star probability (mean over the picks)")
ax.bar(x + 0.18, st["ours"], width=0.34, color=ORANGE, label="Share who became stars, our data")
ax.errorbar(x + 0.18, st["ours"], yerr=st["se2"], fmt="none", ecolor=INK2, elinewidth=0.9, capsize=2)
ax.set_xticks(x, st["band"])
ax.set_xlabel("Overall pick")
ax.set_ylabel("Stars (%)")
ax.legend(loc="upper right", fontsize=8)
save(fig, "f2_star_rates.png")
N["f2"] = st.round(2).to_dict("records")
N["f2_overall"] = {"ours": float(100 * sr["star"].mean()), "bacon": float(100 * sr["p_star"].mean()),
                   "picks": int(len(sr)), "stars": int(sr["star"].sum())}

# ---- f3: one scale per draft class (adopted pricing) ------------------------------------------------
pc = pd.read_csv(OUT / "pick_curve_players.csv")
CL = sorted(pc["draftYear"].unique())
yrs = pc["draftYear"].values
yc = [(yrs == c).astype(float) - (yrs == CL[-1]).astype(float) for c in CL[:-1]]
X = np.column_stack([pc["p_star"].values * (yrs == c) for c in CL] + yc)
m = sm.OLS(pc["surplus"].values / 1e6, X).fit(cov_type="HC1")
R = np.zeros((len(CL) - 1, X.shape[1]))
for j in range(len(CL) - 1):
    R[j, j], R[j, len(CL) - 1] = 1, -1
w = m.wald_test(R, scalar=True)
bc, sec = m.params[:len(CL)], m.bse[:len(CL)]
sc = pd.read_csv(OUT / "pick_curve_scales.csv")
pooled = float(sc.loc[sc["scale_kind"] == "pooled", "scale_M"].iloc[0])
fig, ax = plt.subplots(figsize=(6.5, 3.0))
ax.errorbar(CL, bc, yerr=2 * sec, fmt="o", color=BLUE, ecolor=BLUE, elinewidth=1, capsize=2, ms=5,
            label="Scale fitted on one draft class (bars: two standard errors)")
ax.axhline(pooled, color=GRAY, lw=1.2, ls="--", label=f"Pooled scale, all classes ({pooled:.1f})")
ax.set_xticks(CL, [str(c) for c in CL])
ax.set_xlabel("Draft class")
ax.set_ylabel("Dollar scale ($M per 100% star probability)")
ax.legend(loc="upper left", fontsize=8)
save(fig, "f3_class_scales.png")
N["f3"] = {"classes": CL, "scale": [float(v) for v in bc], "se": [float(v) for v in sec],
           "wald_chi2": float(w.statistic), "wald_df": len(CL) - 1, "wald_p": float(w.pvalue)}
spread, noise = np.std(bc, ddof=1), np.sqrt(np.mean(sec ** 2))
N["f3"]["sd_beyond_noise"] = float(np.sqrt(max(spread ** 2 - noise ** 2, 0)))

# ---- f4: knowable against pooled scale, by trade season -----------------------------------------------
kn = sc[sc["scale_kind"] == "knowable"].copy()
fig, ax = plt.subplots(figsize=(6.5, 2.8))
ax.errorbar(kn["trade_season"], kn["scale_M"], yerr=2 * kn["se_M"], fmt="-o", color=BLUE, ecolor=BLUE,
            elinewidth=1, capsize=2, ms=4, lw=2, label="Scale for the trade season (drafts made nine or more seasons earlier)")
ax.axhline(pooled, color=GRAY, lw=1.2, ls="--", label=f"Scale from all eleven drafts, the sensitivity ({pooled:.1f})")
ax.set_xticks(kn["trade_season"], [f"{int(t)}-{str(int(t) + 1)[2:]}" for t in kn["trade_season"]])
ax.set_xlabel("Trade season")
ax.set_ylabel("Dollar scale ($M per 100% star probability)")
ax.set_ylim(0, 45)
ax.legend(loc="lower right", fontsize=8)
save(fig, "f4_knowable_scale.png")
N["scales"] = sc.round(4).astype(object).where(sc.notna(), None).to_dict("records")   # JSON has no NaN
at = [1, 2, 3, 5, 10, 16, 20, 32, 48, 64, 100, 150, 200]
N["values_by_pick"] = {str(k): {"p_star": float(bacon.loc[k, "p_star"]), "pooled": pooled * float(bacon.loc[k, "p_star"]),
                                **{f"knowable_{int(r.trade_season)}": r.scale_M * float(bacon.loc[k, "p_star"])
                                   for r in kn.itertuples()}} for k in at}

# ---- f5: control cost, modelled against actual --------------------------------------------------------
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
ax.set_ylabel("$M per player over his control years")
ax.legend(loc="upper right", fontsize=8)
save(fig, "f5_control_cost.png")
N["f5"] = cc.round(3).to_dict("records")

# ---- tables -----------------------------------------------------------------------------------------
se_ = pd.read_csv(OUT / "pick_curve_seasons.csv")
pl = pc.set_index(["draftYear", "pick"])
for name, dy, pk in (("point", 2014, 79), ("sbisa", 2008, 19)):
    s = se_[(se_["draftYear"] == dy) & (se_["pick"] == pk)].copy()
    s["value_M"] = s["value_share"] * 95.5
    s["cost_M"] = s["cost_share"] * 95.5
    N[f"worked_{name}"] = {"player": pl.loc[(dy, pk), "player"], "window_end": int(pl.loc[(dy, pk), "window_end"]),
                           "route": pl.loc[(dy, pk), "route"], "total_M": float(pl.loc[(dy, pk), "surplus"] / 1e6),
                           "p_star": float(bacon.loc[pk, "p_star"]),
                           "seasons": s[["season", "gp", "war_82", "in_entry_level", "cap", "cost_$", "value_M",
                                         "cost_M"]].round(4).to_dict("records")}
tp = pd.read_csv(OUT / "traded_pick_values.csv")
N["traded_by_method"] = tp.groupby("method").agg(picks=("asset_id", "size"), knowable=("value_knowable_M", "sum"),
                                                 pooled=("value_pooled_M", "sum")).round(2).reset_index().to_dict("records")
N["traded_by_round"] = tp.groupby("pick_round")["value_knowable_M"].agg(["size", "mean"]).round(3).reset_index().to_dict("records")
N["traded_totals"] = {"picks": int(len(tp)), "knowable": float(tp["value_knowable_M"].sum()),
                      "pooled": float(tp["value_pooled_M"].sum()), "conditional": int(tp["conditional"].sum())}
slot = tp[tp["method"] == "slot on the trade date"]
gap = (slot["projected_slot"] - slot["actual_slot"]).abs()
N["projection"] = {"picks": int(len(slot)), "median_miss": float(gap.median()), "within3": int((gap <= 3).sum()),
                   "first_round": int((slot["pick_round"] == 1).sum()),
                   "first_round_max": float(gap[slot["pick_round"] == 1].max())}
N["routes"] = pc["route"].value_counts().to_dict()
N["players"] = {"picks": int(len(pc)), "goalies": int(pc["is_goalie"].sum()), "played": int((pc["nhl_seasons"] > 0).sum()),
                "lapsed_zeroed_M": float(pc.loc[pc["surplus"] != pc["surplus_before_rights"], "surplus_before_rights"].sum() / 1e6),
                "total_before_M": float(pc["surplus_before_rights"].sum() / 1e6)}
(FIG / "numbers.json").write_text(json.dumps(N, indent=1, default=float), encoding="utf-8")
print(f"  wrote numbers.json; Wald chi2 {N['f3']['wald_chi2']:.1f}, p {N['f3']['wald_p']:.4f}; "
      f"sd beyond noise {N['f3']['sd_beyond_noise']:.2f}")
print(json.dumps({k: N[k] for k in ("worked_point", "worked_sbisa")}, indent=1, default=float)[:3000])
