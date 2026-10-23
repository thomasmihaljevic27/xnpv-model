"""
prospect_term_combinations.py -- every combination of draft position, production, production squared and the age
discount for prospects in D+5 and later: held-out error, significance and the traded prospects' values (report only)

ASKED (Thomas, 2026-10-16): "tell me all permutations of decisions. show me what the results would be (value changes,
RMSE, p values) of each possible combination between draft position, production, production squared, and aging".
The decision on the table is how to value prospects from D+5 on, where production and its square are not jointly
statistically significant in the adopted model (p = 0.089, prospect_doc_figures.py v2.2).

THE SIXTEEN COMBINATIONS: each of four terms on or off in the D+5-and-later regression only:
  draft position     p_star, the star probability for his draft position (Bacon)
  production         nhle82, NHLe points per 82, 50/30/20 over the three seasons before
  production squared nhle82_sq
  age discount       prod_x_age = production x years past first eligibility (age on September 15 of the season,
                     less the seasons since the draft, less 18) -- the variable the model's code uses. In D+1 to D+4
                     each season holds one value of k, so this and production x (age - 18) give the same values; in
                     D+5 and later k runs 4 to 8 and they differ, so production x (age - 18) is run beside it.
  The no-record indicator goes in whenever any production-based term is in (as in every production model), and draft
  levels are always in (draft-year indicators summing to zero, no constant: each value describes an average draft).
  With no term at all, every D+5-and-later prospect is worth zero.
  D+1 to D+4 stay on the adopted model throughout (draft position in D+1 to D+3, linear and squared production, the
  no-record indicator, the age discount), so the whole-sample error moves only through the D+5-and-later rows.

SCORING (as prospect_production_form.py v1.2): held-out error, each draft predicted at the average draft from a fit
without it; one-sided p from 2,000 redraws of the 11 drafts (same seed): the share of redraws in which the
combination's summed squared error is NOT below the comparison's. Compared with the adopted model and with draft
position alone. Coefficients from the D+5-and-later fit, standard errors clustered by player (one player appears in
several seasons), two-sided p; and the joint test that all the combination's terms are zero (Wald, chi-squared).
TRADED PROSPECTS: each combination fitted on all drafts and applied to prospect_values.csv's D+5-and-later skaters
(drafted and undrafted; undrafted at draft position zero). Goaltenders stay on draft position alone (the production
measure is a skater's); skaters without an Elite Prospects record keep their values. Earlier seasons unchanged.
GUARDS: the rows' fingerprint; draft position alone and the adopted model reproduce prospect_production_form_scores.csv
(D+5-and-later and whole-sample errors) to 1e-9; the adopted combination reproduces value_M to 1e-6.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, draft_pick_linkage.csv, prospect_production_form_scores.csv,
prospect_values.csv. OUTPUTS: OUTPUT_DIR/prospect_term_combinations.csv, prospect_term_combinations_log.txt.
Run from the repo root:  python 25_TESTS/prospect_term_combinations.py
"""

import hashlib
import itertools
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_term_combinations.py v1.0 (2026-10-16)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "linkage": OUTPUT_DIR / "draft_pick_linkage.csv",
     "form_scores": OUTPUT_DIR / "prospect_production_form_scores.csv", "values": OUTPUT_DIR / "prospect_values.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

N_REDRAW, SEED = 2000, 20261014            # as prospect_production_form.py
FIRST_ELIGIBLE_AGE = 18.0
SLOT_EARLY, AGE_GROUPS = ["0", "1", "2"], ["0", "1", "2", "3"]
LATE = "4+"                                # k >= 4: D+5 and later
TERMS = ["p_star", "nhle82", "nhle82_sq", "age"]
SHORT = {"p_star": "DP", "nhle82": "P", "nhle82_sq": "P2", "age": "AGE"}
PROD_TERMS = {"nhle82", "nhle82_sq", "age"}

# ---- rows (the production look's 13,104 skater prospect-rows) --------------------------------------------
d = pd.read_csv(F["rows"])
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "cff3583de536", FP                                          # GUARD: the production look's rows
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
assert d["birthDate"].notna().all()
d["k_group"] = d["k_group"].astype(str)
d["age"] = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
d["past_elig"] = d["age"] - d["k"] - FIRST_ELIGIBLE_AGE
d["prod_x_elig"] = d["nhle82"] * d["past_elig"]                         # the code's age discount
d["prod_x_age18"] = d["nhle82"] * (d["age"] - FIRST_ELIGIBLE_AGE)        # production x (age - 18)
d["pid"] = d["draftYear"].astype(str) + "-" + d["pick"].astype(str)
d = d.reset_index(drop=True)
late = d["k_group"] == LATE
log(f"  rows: {len(d):,} skater prospect-seasons; D+5 and later {int(late.sum()):,} "
    f"({d.loc[late, 'pid'].nunique():,} players, {d.loc[late, 'draftYear'].nunique()} drafts)")


def draft_cols(frame):
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    return [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]


def fit(frame, cols, cluster):
    X = np.column_stack([frame[c].values for c in cols] + draft_cols(frame))
    if cluster:
        return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster",
                                                         cov_kwds={"groups": pd.factorize(frame["pid"])[0]})
    return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")


def adopted_cols(g):
    return (["p_star"] if g in SLOT_EARLY else []) + ["nhle82", "nhle82_sq", "no_record"] + \
           (["prod_x_elig"] if g in AGE_GROUPS else [])


def late_cols(combo, age_col):
    c = [t for t in ["p_star", "nhle82", "nhle82_sq"] if t in combo] + (["no_record"] if combo & PROD_TERMS else [])
    return c + ([age_col] if "age" in combo else [])


def held_out(frame, cols, cluster):
    e = np.zeros(len(frame))
    for c in sorted(frame["draftYear"].unique()):
        tr, te = frame[frame["draftYear"] != c], frame[frame["draftYear"] == c]
        pred = te[cols].values @ fit(tr, cols, cluster).params[:len(cols)] if cols else np.zeros(len(te))
        e[frame.index.get_indexer(te.index)] = te["remaining_M"].values - pred     # positions within frame
    return e


def rmse(e):
    return float(np.sqrt(np.mean(e ** 2)))


# ---- errors: D+1 to D+4 on the adopted model, once ---------------------------------------------------------
E_early = {}
for g, x in d[~late].groupby("k_group"):
    E_early[g] = pd.Series(held_out(x, adopted_cols(g), False), index=x.index)
e_early = pd.concat(E_early.values()).sort_index()
L = d[late]
cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
sse_early = (e_early ** 2).groupby(d.loc[e_early.index, "draftYear"].values).sum()

# ---- the traded prospects ----------------------------------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)",
                            "undrafted prospect, valued (goalie: slot alone, so zero)"])
prod = pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[valued & prod & (pv["k_group"].astype(str) == LATE)].copy()
fixed_late = pv[valued & ~prod & (pv["k_group"].astype(str) == LATE)]   # goalies: draft position alone, unchanged
t["nhle82_sq"] = t["nhle82"] ** 2
t["no_record"] = (t["n_prod_seasons"] == 0).astype(float)
t["prod_x_elig"] = t["nhle82"] * t["past_elig"]
t["prod_x_age18"] = t["nhle82"] * (t["past_elig"] + t["seasons_since_draft"])
t["p_star"] = t["p_star"].fillna(0.0)                                   # undrafted: draft position zero
t["drafted"] = t["draftYear"].notna()
total_all = float(pv.loc[valued, "value_M"].sum())
late_adopted = float(t["value_M"].sum() + fixed_late["value_M"].sum())
log(f"  traded prospects valued: {int(valued.sum())} assets, ${total_all:.2f}M; D+5 and later {len(t) + len(fixed_late)} "
    f"(${late_adopted:.2f}M): {int(t['drafted'].sum())} drafted skaters, {int((~t['drafted']).sum())} undrafted skaters, "
    f"{len(fixed_late)} goaltenders (draft position alone, unchanged)")

# ---- every combination ---------------------------------------------------------------------------------------
rows, E_late = [], {}
for age_col in ("prod_x_elig", "prod_x_age18"):
    for r in range(0, 5):
        for combo in itertools.combinations(TERMS, r):
            combo = set(combo)
            if age_col == "prod_x_age18" and "age" not in combo:
                continue                                                # the same fit as the first pass
            cols = late_cols(combo, age_col)
            key = (" + ".join(SHORT[t_] for t_ in TERMS if t_ in combo) or "none") + \
                  (" [age - 18]" if age_col == "prod_x_age18" else "")
            e_l = pd.Series(held_out(L, cols, True), index=L.index)
            E_late[key] = e_l
            rec = {"combination": key, "terms": len(combo), "rmse_late": rmse(e_l.values),
                   "rmse_all": rmse(np.concatenate([e_early.values, e_l.values]))}
            if cols:
                m = fit(L, cols, True)
                for i, c in enumerate(cols):
                    nm = {"prod_x_elig": "age", "prod_x_age18": "age"}.get(c, c)
                    rec[f"coef_{nm}"], rec[f"se_{nm}"], rec[f"p_{nm}"] = m.params[i], m.bse[i], m.pvalues[i]
                tested = [i for i, c in enumerate(cols) if c != "no_record"]
                R = np.zeros((len(tested), len(m.params)))
                for j, i in enumerate(tested):
                    R[j, i] = 1.0
                w = m.wald_test(R, use_f=False, scalar=True)
                rec["joint_chi2"], rec["joint_df"], rec["joint_p"] = float(w.statistic), len(tested), float(w.pvalue)
                v = pd.Series(t[cols].values @ m.params[:len(cols)], index=t.index)
            else:
                v = pd.Series(0.0, index=t.index)
            rec["value_drafted_M"] = float(v[t["drafted"]].sum())
            rec["value_undrafted_M"] = float(v[~t["drafted"]].sum())
            rec["value_late_M"] = float(v.sum() + fixed_late["value_M"].sum())
            rec["change_M"] = rec["value_late_M"] - late_adopted
            rec["value_all_M"] = total_all + rec["change_M"]
            rec["below_zero"] = int((v < -1e-9).sum())
            rec["_v"] = v
            rows.append(rec)

R_ = pd.DataFrame(rows).set_index("combination")
ADOPTED, DP = "P + P2", "DP"
ref = pd.read_csv(F["form_scores"])
ref = ref[ref["sample"] == "all drafts"].drop_duplicates("form").set_index("form")
assert abs(R_.at[DP, "rmse_late"] - ref.at["slot alone", "D+5+"]) < 1e-9                 # GUARD
assert abs(R_.at[ADOPTED, "rmse_late"] - ref.at["curved", "D+5+"]) < 1e-9                # GUARD
assert abs(R_.at[ADOPTED, "rmse_all"] - ref.at["curved", "rmse_M"]) < 1e-9               # GUARD
gap = (R_.at[ADOPTED, "_v"] - t["value_M"]).abs().max()
assert gap < 1e-6, gap                                                                    # GUARD
log(f"  guard: draft position alone and the adopted model reproduce the recorded held-out errors; the adopted model "
    f"reproduces value_M (largest gap {gap:.1e}) (PASS)")

sse_late = {k: (e ** 2).groupby(L.loc[e.index, "draftYear"].values).sum() for k, e in E_late.items()}


def p_vs(a, b):
    w = sum((sse_late[a][list(dr)].sum() < sse_late[b][list(dr)].sum()) for dr in draws)
    return 1 - w / N_REDRAW


R_["p_vs_adopted"] = [p_vs(k, ADOPTED) if k != ADOPTED else np.nan for k in R_.index]
R_["p_vs_dp"] = [p_vs(k, DP) if k != DP else np.nan for k in R_.index]
R_["pct_vs_adopted"] = 100 * (R_["rmse_late"] / R_.at[ADOPTED, "rmse_late"] - 1)

log("\nD+5 AND LATER: EACH COMBINATION (DP draft position, P production, P2 production squared, AGE production x age;")
log("held-out error in $M of remaining surplus per prospect-season; one-sided p from 2,000 redraws; values $M)")
log(f"  {'combination':<26}{'D+5 err':>9}{'vs adopt':>9}{'p<adopt':>8}{'p<DP':>7}{'all err':>9}{'joint p':>9}"
    f"{'D+5 value':>10}{'change':>8}{'below 0':>8}")
for k, r in R_.sort_values("rmse_late").iterrows():
    log(f"  {k:<26}{r.rmse_late:>9.4f}{r.pct_vs_adopted:>+8.2f}%"
        f"{'' if np.isnan(r.p_vs_adopted) else f'{r.p_vs_adopted:.3f}':>8}{'' if np.isnan(r.p_vs_dp) else f'{r.p_vs_dp:.3f}':>7}"
        f"{r.rmse_all:>9.4f}{'' if pd.isna(r.get('joint_p')) else f'{r.joint_p:.3f}':>9}{r.value_late_M:>10.2f}"
        f"{r.change_M:>+8.2f}{int(r.below_zero):>8}")
log("\nCOEFFICIENTS (coefficient, clustered standard error, two-sided p)")
for k, r in R_.iterrows():
    parts = [f"{SHORT.get(c, c)} {r[f'coef_{c}']:.4f} ({r[f'se_{c}']:.4f}) p {r[f'p_{c}']:.3f}"
             for c in ["p_star", "nhle82", "nhle82_sq", "age", "no_record"] if pd.notna(r.get(f"coef_{c}"))]
    log(f"  {k:<26}" + ("; ".join(parts) if parts else "-"))

out = R_.drop(columns="_v").reset_index()
out.to_csv(OUTPUT_DIR / "prospect_term_combinations.csv", index=False)
(OUTPUT_DIR / "prospect_term_combinations_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_term_combinations.csv and its log in {OUTPUT_DIR}")
