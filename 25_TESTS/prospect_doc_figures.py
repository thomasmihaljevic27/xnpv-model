"""
prospect_doc_figures.py -- the numbers and figures behind "Valuing Prospects" (40_DOCS/Supervisor_Drafts/).

Reads the outputs of the live prospect model and its tests; re-fits nothing that is not already fitted, except the
chosen model's regressions, which are refitted here with the live script's own functions to report each coefficient's
standard error, z statistic, p-value, rows, players, drafts and R-squared (the live script keeps coefficients only).
GUARD: each refitted coefficient equals prospect_production_fits.csv's to 1e-9.

INPUTS (OUTPUT_DIR): prospect_slot_years.csv, prospect_nhle_look.csv, prospect_nhle_coefficients.csv,
prospect_nhle_rows.csv, prospect_age_look.csv, prospect_age_coefficients.csv, prospect_production_fits.csv,
prospect_values.csv; SOURCE_DIR/draft_slot_baseline.csv.
OUTPUTS: OUTPUT_DIR/prospect_doc/numbers.json and fig1_star_value.png, fig2_production.png, fig3_traded.png.
Run from the repo root (matplotlib on PYTHONPATH):  python 25_TESTS/prospect_doc_figures.py

v1.1 (2026-10-15, Thomas's notes on the document): seasons are named D+1 (the season after the draft, k = 0) to D+5
and later in Figures 1 and 3. Labels only; no number changes. The revised document carries these figures (Figure 1
redrawn from Table 1, Figure 3's legend relabelled); it is no longer rebuilt by prospect_model_doc.js.
"""

import json
import math
import os
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

SCRIPT_VERSION = "prospect_doc_figures.py v1.1 (2026-10-15)"
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
FIG = OUT / "prospect_doc"
FIG.mkdir(exist_ok=True)
N = {"script": SCRIPT_VERSION}
print(SCRIPT_VERSION)


def pval(b, se):
    """Two-sided p-value from a robust z statistic (normal reference)."""
    z = b / se
    return z, math.erfc(abs(z) / math.sqrt(2))


bacon = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
N["p_star"] = {str(k): float(bacon[k]) for k in (1, 5, 10, 20, 32, 64, 100, 200)}

# ---- step one: the star value by seasons since the draft ------------------------------------------
sy = pd.read_csv(OUT / "prospect_slot_years.csv", dtype={"seasons_since_draft": str})
rows = []
for r in sy.itertuples():
    z, p = pval(r.star_value_M, r.se_M)
    rows.append({"k": r.seasons_since_draft, "rows": int(r.rows), "players": int(r.players), "drafts": int(r.drafts),
                 "star": r.star_value_M, "se": r.se_M, "z": z, "p": p, "pick1": r.pick1_value_M,
                 "pick10": r.star_value_M * float(bacon[10]), "pick32": r.star_value_M * float(bacon[32]),
                 "lodo_min": r.lodo_min_M, "lodo_max": r.lodo_max_M, "top10": int(r.top10_prospects),
                 "share_nhl_games": r.share_with_nhl_games})
N["step1"] = rows

# ---- production: every candidate on the same rows ------------------------------------------------
nl = pd.read_csv(OUT / "prospect_nhle_look.csv")
base = float(nl.loc[nl["arm"] == "slot", "rmse_M"].iloc[0])
N["prod_arms"] = [{"arm": r["arm"], "rmse": r["rmse_M"], "pct": 100 * (r["rmse_M"] / base - 1),
                   "by_k": [r[f"rmse_k{g}"] for g in ("0", "1", "2", "3", "4+")],
                   "wins": None if pd.isna(r["redraws_beating_slot"]) else int(r["redraws_beating_slot"])}
                  for _, r in nl.iterrows()]
nc = pd.read_csv(OUT / "prospect_nhle_coefficients.csv", dtype={"k_group": str})
N["prod_coefs"] = json.loads(nc.to_json(orient="records"))
pr = pd.read_csv(OUT / "prospect_nhle_rows.csv", dtype={"k_group": str})
N["prod_rows"] = {"rows": len(pr), "players": int(pr[["draftYear", "pick"]].drop_duplicates().shape[0]),
                  "no_record_share": float(pr["no_record"].mean())}
k1 = pr[(pr["k_group"] == "1") & (pr["n_seasons"] > 0)]["nhle82"]
N["prod_pct_k1"] = {q: float(k1.quantile(q / 100)) for q in (25, 50, 75, 90)}
N["prod_median_by_k"] = {g: float(x.loc[x["n_seasons"] > 0, "nhle82"].median()) for g, x in pr.groupby("k_group")}

# ---- age: every candidate on the same rows -------------------------------------------------------
al = pd.read_csv(OUT / "prospect_age_look.csv")
abase = float(al.loc[al["arm"] == "chosen", "rmse_M"].iloc[0])
N["age_arms"] = [{"arm": r.arm, "rmse": r.rmse_M, "pct": 100 * (r.rmse_M / abase - 1),
                  "pct_vs_slot": 100 * (r.rmse_M / base - 1),
                  "wins": None if pd.isna(r.redraws_beating_chosen) else int(r.redraws_beating_chosen)}
                 for r in al.itertuples()]
ac = pd.read_csv(OUT / "prospect_age_coefficients.csv", dtype={"k_group": str})
N["age_coefs"] = json.loads(ac.to_json(orient="records"))

# ---- the chosen model, refitted for standard errors, p-values and fit statistics ------------------
sv, fitrows = PV.star_values()
rates = PV.production_rates()
fits, prow = PV.production_fits(fitrows, rates)
live = pd.read_csv(OUT / "prospect_production_fits.csv", dtype={"k_group": str, "left_out": str})
tables = {}
for version in PV.VERSIONS:
    out = []
    for g, x in prow.groupby("k_group"):
        cols = PV.cols_for(g, version)
        cl = sorted(x["draftYear"].unique())
        yrs = x["draftYear"].values
        X = np.column_stack([x[c].values for c in cols]
                            + [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]])
        if g.endswith("+"):
            grp = pd.factorize(x["draftYear"].astype(str) + "-" + x["pick"].astype(str))[0]
            m = sm.OLS(x["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": grp})
        else:
            m = sm.OLS(x["remaining_M"].values, X).fit(cov_type="HC1")
        lv = live[(live["version"] == version) & (live["k_group"] == g) & (live["left_out"] == "none")].iloc[0]
        for i, c in enumerate(cols):
            assert abs(m.params[i] - lv[c]) < 1e-9, (version, g, c)     # GUARD: the live script's coefficients
        terms = {}
        for i, c in enumerate(cols):
            z, p = pval(m.params[i], m.bse[i])
            terms[c] = {"b": float(m.params[i]), "se": float(m.bse[i]), "z": float(z), "p": float(p)}
        out.append({"k": g, "rows": int(m.nobs), "players": int(x[["draftYear", "pick"]].drop_duplicates().shape[0]),
                    "drafts": len(cl), "r2": float(m.rsquared), "terms": terms})
    tables[version] = out
N["chosen"] = tables
print("  guard: refitted coefficients equal prospect_production_fits.csv (PASS)")

# ---- the traded prospects ------------------------------------------------------------------------
v = pd.read_csv(OUT / "prospect_values.csv")
dv = v[v["status"].astype(str).str.startswith("prospect, valued")].copy()
uv = v[v["status"].astype(str).str.startswith("undrafted prospect, valued")].copy()
allv = pd.concat([dv, uv])
d_age = dv["value_M"] - dv["value_no_age_M"]
d_prod = dv["value_no_age_M"] - dv["value_slot_only_M"]
top = lambda col: set(dv.nlargest(20, col)["asset_id"])                    # noqa: E731
N["traded"] = {
    "drafted": len(dv), "drafted_players": int(dv["player_name"].nunique()), "undrafted": len(uv),
    "all": len(allv), "goalies": int(dv["is_goalie"].astype(bool).sum()),
    "tot_main": float(dv["value_M"].sum()), "tot_noage": float(dv["value_no_age_M"].sum()),
    "tot_slot": float(dv["value_slot_only_M"].sum()), "tot_own_out": float(dv["value_own_draft_out_M"].sum()),
    "tot_all_main": float(allv["value_M"].sum()), "tot_all_noage": float(allv["value_no_age_M"].sum()),
    "tot_undrafted": float(uv["value_M"].sum()), "max_undrafted": float(uv["value_M"].max()),
    "age_moved_025": int((d_age.abs() >= 0.25).sum()), "age_moved_050": int((d_age.abs() >= 0.5).sum()),
    "age_largest": float(d_age.abs().max()), "age_rank": float(dv["value_M"].rank().corr(dv["value_no_age_M"].rank())),
    "prod_moved_025": int((d_prod.abs() >= 0.25).sum()), "prod_moved_050": int((d_prod.abs() >= 0.5).sum()),
    "prod_largest": float(d_prod.abs().max()),
    "prod_rank": float(dv["value_no_age_M"].rank().corr(dv["value_slot_only_M"].rank())),
    "top20_same_noage": len(top("value_M") & top("value_no_age_M")),
    "top20_same_slot": len(top("value_M") & top("value_slot_only_M")),
    "negative": int((allv["value_M"] < 0).sum()), "negative_sum": float(allv.loc[allv["value_M"] < 0, "value_M"].sum()),
    "negative_min": float(allv["value_M"].min()),
    "by_k": [{"k": g, "n": int(len(x)), "main": float(x["value_M"].sum()), "noage": float(x["value_no_age_M"].sum()),
              "slot": float(x["value_slot_only_M"].sum())} for g, x in dv.groupby("k_group")],
    "top10": [{"date": r.trade_date, "name": r.player_name, "draft": int(r.draftYear), "pick": int(r.pick),
               "k": int(r.seasons_since_draft), "prod": None if pd.isna(r.nhle82) else float(r.nhle82),
               "past": None if pd.isna(r.past_elig) else float(r.past_elig),
               "main": r.value_M, "noage": r.value_no_age_M, "slot": r.value_slot_only_M, "own_out": r.value_own_draft_out_M}
              for r in dv.nlargest(10, "value_M").itertuples()],
}

# ---- each alternative on the same traded prospects (drafted skaters; goalies stay on the slot) -------
sk = dv[~dv["is_goalie"].astype(bool) & dv["nhle82"].notna()].copy()
gk_tot = float(dv.loc[~dv.index.isin(sk.index), "value_M"].sum())         # goalies (and any without production)
sk["no_record"] = (sk["n_prod_seasons"] == 0).astype(float)
sk["nhle82_sq"] = sk["nhle82"] ** 2 / 10
sk["prod_x_age"] = sk["nhle82"] * sk["past_elig"]
sk["past_elig_"] = sk["past_elig"]
sk["kg"] = sk["k_group"].astype(str)


def arm_total(table, arm, cols_by_k):
    tot = 0.0
    for r in sk.itertuples():
        row = table[(table["k_group"] == r.kg) & (table["arm"] == arm)].iloc[0]
        x = {"p_star": r.p_star, "nhle82": r.nhle82, "nhle82_sq": r.nhle82_sq, "no_record": r.no_record,
             "prod_x_age": r.prod_x_age, "past_elig": r.past_elig_}
        tot += sum(row[c] * x[c] for c in cols_by_k(r.kg) if pd.notna(row.get(c)))
    return tot + gk_tot


slot_cols = lambda g: ["p_star"]                                           # noqa: E731
straight = lambda g: ["p_star", "nhle82", "no_record"]                     # noqa: E731
curved = lambda g: ["p_star", "nhle82", "nhle82_sq", "no_record"]          # noqa: E731
N["alt_totals"] = {
    "step1_slot": float(dv["value_slot_only_M"].sum()),
    "slot_no_fade": float((dv["p_star"] * rows[0]["star"]).sum()),
    "straight_slot_throughout": arm_total(nc, "slot+production", straight),
    "curved_slot_throughout": arm_total(nc, "slot+production curved", curved),
    "chosen_no_age": float(dv["value_no_age_M"].sum()),
    "age_alone": arm_total(ac, "+ age", lambda g: (["p_star"] if g in ("0", "1", "2") else [])
                           + ["nhle82", "nhle82_sq", "no_record", "past_elig"]),
    "age_both": arm_total(ac, "+ age and age x production", lambda g: (["p_star"] if g in ("0", "1", "2") else [])
                          + ["nhle82", "nhle82_sq", "no_record", "past_elig", "prod_x_age"]),
    "adopted": float(dv["value_M"].sum()),
    "own_draft_out": float(dv["value_own_draft_out_M"].sum()),
    "skaters_priced": int(len(sk)), "others_on_slot": int(len(dv) - len(sk)),
}
# the slot's coefficient once production is in, three and four-plus seasons on (curved, all drafts)
N["slot_late"] = {g: {"b": float(coef_row["p_star"]), "se": float(coef_row["p_star_se"]),
                      "p": pval(float(coef_row["p_star"]), float(coef_row["p_star_se"]))[1]}
                  for g in ("3", "4+")
                  for coef_row in [nc[(nc["k_group"] == g) & (nc["arm"] == "slot+production curved")].iloc[0]]}
# the defence rate and the age terms' significance, for the comparison tables
dpos = nc[nc["arm"] == "slot+production by position"]
N["defence_rate"] = [{"k": r.k_group, "f": r.nhle_f, "f_se": r.nhle_f_se, "d": r.nhle_d, "d_se": r.nhle_d_se}
                     for r in dpos.itertuples()]

# ---- the worked prospect: the highest-valued drafted prospect, term by term ------------------------
w = dv.nlargest(1, "value_M").iloc[0]
g = str(w["k_group"])
terms = tables["main"][[t["k"] for t in tables["main"]].index(g)]["terms"]
q, pe = float(w["nhle82"]), float(w["past_elig"])
inputs = {"p_star": float(w["p_star"]), "nhle82": q, "nhle82_sq": q * q / 10, "no_record": 0.0, "prod_x_age": q * pe}
parts = {c: terms[c]["b"] * inputs[c] for c in terms}
assert abs(sum(parts.values()) - float(w["value_M"])) < 1e-9                 # GUARD: the parts add to his value
N["worked"] = {"name": w["player_name"], "date": w["trade_date"], "draft": int(w["draftYear"]), "pick": int(w["pick"]),
               "k": int(w["seasons_since_draft"]), "page": int(w["valuation_page"]), "prod": q, "past": pe,
               "inputs": inputs, "coefs": {c: terms[c]["b"] for c in terms}, "parts": parts, "value": float(w["value_M"]),
               "noage": float(w["value_no_age_M"]), "slot": float(w["value_slot_only_M"]),
               "own_out": float(w["value_own_draft_out_M"])}

# ---- figures ------------------------------------------------------------------------------------------
plt.rcParams.update({"font.family": "Calibri", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
INK, MUTED, A1, A2, A3 = "#2B2A28", "#8A8984", "#2F6DB5", "#D9822B", "#3E9A5B"

# Figure 1: star value by season (k = seasons since the draft; k = 0 is D+1, the season after the draft), 95% intervals
fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=200)
xs = np.arange(len(rows))
ax.bar(xs, [r["star"] for r in rows], color=A1, width=0.6)
ax.errorbar(xs, [r["star"] for r in rows], yerr=[1.96 * r["se"] for r in rows], fmt="none", ecolor=INK, capsize=4, lw=1)
for x_, r in zip(xs, rows):
    ax.text(x_ + 0.33, r["star"] + 0.4, f"${r['star']:.2f}M", ha="left", va="bottom", fontsize=9, color=INK)
ax.set_xticks(xs, ["D+1\n(from the draft)", "D+2", "D+3", "D+4", "D+5 and later"])   # v1.1: D+ names (Thomas)
ax.set_xlabel("Season (D+1 is the season after the draft)")
ax.set_ylabel("Star value ($ millions, 2025-26 cap)")
ax.set_ylim(0, 23)
fig.tight_layout()
fig.savefig(FIG / "fig1_star_value.png")
plt.close(fig)

# Figure 2: a #20 pick one season after his draft, value against production
coef_n = {(r["k_group"], r["arm"]): r for r in N["prod_coefs"]}
p20 = float(bacon[20])
qs = np.linspace(0, 25, 251)
slot1 = coef_n[("1", "slot")]["p_star"] * p20
straight = coef_n[("1", "slot+production")]
curved = coef_n[("1", "slot+production curved")]
mt = {c: t["b"] for c, t in terms.items()} if g == "1" else \
    {c: t["b"] for c, t in tables["main"][[t["k"] for t in tables["main"]].index("1")]["terms"].items()}
fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=200)
ax.plot(qs, np.full_like(qs, slot1), color=MUTED, lw=1.6, label="Slot alone")
ax.plot(qs, straight["p_star"] * p20 + straight["nhle82"] * qs, color=A2, lw=1.6, label="Slot + production, straight line")
ax.plot(qs, curved["p_star"] * p20 + curved["nhle82"] * qs + curved["nhle82_sq"] * qs ** 2 / 10, color=A1, lw=1.8,
        label="Slot + production, curved")
for pe_, ls, lab in ((-0.4, "--", "Curved, age-discounted: first-time eligible, late birthday"),
                     (1.0, ":", "Curved, age-discounted: drafted a year older")):
    ax.plot(qs, mt["p_star"] * p20 + mt["nhle82"] * qs + mt["nhle82_sq"] * qs ** 2 / 10 + mt["prod_x_age"] * qs * pe_,
            color=A3, lw=1.6, ls=ls, label=lab)
for qq, v_ in N["prod_pct_k1"].items():
    ax.axvline(v_, color="#D5D4CF", lw=0.8, zorder=0)
    ax.text(v_ + 0.12, -0.38, f"{qq}th", ha="left", va="bottom", fontsize=8, color=MUTED)
ax.set_xlabel("Production: NHL-equivalent points per 82 games (50/30/20 over the three seasons before)")
ax.set_ylabel("Prospect value ($ millions)")
ax.set_xlim(0, 25)
ax.set_ylim(-0.5, 6.5)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig2_production.png")
plt.close(fig)

# Figure 3: the traded prospects, slot alone against the adopted model
fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=200)
colors = {"0": A1, "1": A1, "2": A1, "3": A2, "4+": A3}
for lab, sel, col in (("D+1 to D+3 (season at the trade)", dv["k_group"].isin(["0", "1", "2"]), A1),   # v1.1
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
fig.savefig(FIG / "fig3_traded.png")
plt.close(fig)

(FIG / "numbers.json").write_text(json.dumps(N, indent=1, default=float), encoding="utf-8")
print(f"  wrote numbers.json and three figures in {FIG}")
print(f"  worked prospect: {N['worked']['name']} ({N['worked']['date']}): ${N['worked']['value']:.2f}M")
