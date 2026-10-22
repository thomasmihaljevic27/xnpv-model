"""
prospect_linear_drop_centre.py -- the prospect model without linear production: does the verdict hang on the centre of age?
(report only)

DECIDED (Thomas, 2026-10-21, note 38 on "Valuing Players, Draft Picks, and Prospects"): "The model should be a c d and
e": star probability (a, D+1 to D+3), production squared (c), the no-record indicator (d), production x age (e, D+1 to
D+4); linear production (b) dropped in every season. Before the build (MODEL_DIRECTIVES, "Thomas's second round of notes",
item 1): with b in the model, where age is centred changes no value (b absorbs the shift: b' = b + e x shift); without
b it does, because production x (age - centre) then carries a linear production term of -e x centre. Recorded
2026-10-15: this form's in-sample rejection was p = 0.0027 with age centred at 18.5 and 0.063 at 18. This run shows how
much the held-out verdict and the traded prospects' values move with the centre, for each centre a reader could defend.

THE AGE MEASURES (both on September 15 of the valuation season, D+n = code k + 1):
  years past first eligibility  age - k - centre: what prospect_values.py stores (centre 18). Zero, at centre 18, for a
                                prospect drafted at his first opportunity, who turned 18 by the September 15 after his
                                draft, in every season after the draft.
  age                           age - centre: what "Valuing Prospects" reports since 2026-10-15 (option A). Zero, at
                                centre 18, only for an 18-year-old; in D+2 no prospect is 18.
  With b in the model the two measures, and every centre, give the same values (the adopted arm is fitted once).

THE ARMS: "adopted" = a + b + c + d + e (prospect_values.py v1.11); "no linear" = a + c + d + e at each age measure and
centre below. D+5 and later have no age term and no draft position in any arm; there "no linear" is c + d.

SCORING (prospect_age_form_look.py's rule; the same rows and weights for every arm): held-out error, each draft
predicted from a fit without it, in $M of remaining surplus a prospect-season. p = the share of 2,000 redraws of the 11
drafts (seed 20261014) in which the first arm's summed squared held-out error is NOT below the second's (one-sided).
IN SAMPLE (beside, not the verdict): b's coefficient and p in each season of the adopted model at each centre, and the
joint test that b is zero in all five seasons (one regression with the full set of interaction terms, errors
clustered by player, as prospect_values.fit_stacked; Wald, chi-squared with 5 degrees of freedom).
TRADED PROSPECTS: each arm fitted on all drafts and applied to prospect_values.csv's prospects valued on production.

GUARDS: the rows' fingerprint (prospect_age_form_look.py's rows); the adopted arm's held-out error reproduces
prospect_age_look.csv's to 1e-9; the adopted arm's values reproduce prospect_values.csv's value_M to 1e-6; the adopted
arm's values are the same at every centre (to 1e-9); no input is rewritten while the test runs.
TRAILING WEIGHTING (directive 6): production reads 50/30/20 (prospect_nhle_look.py, as stored in the rows and in
prospect_values.csv); age reads no trailing seasons.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, draft_pick_linkage.csv, prospect_age_look.csv, prospect_values.csv.
OUTPUTS: OUTPUT_DIR/prospect_linear_drop_centre.csv (each arm: held-out errors, p, traded totals),
prospect_linear_drop_centre_insample.csv (b in the adopted model at each centre), prospect_linear_drop_centre_log.txt.
Run from the repo root:  python 25_TESTS/prospect_linear_drop_centre.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy import stats

SCRIPT_VERSION = "prospect_linear_drop_centre.py v1.0 (2026-10-21)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "linkage": OUTPUT_DIR / "draft_pick_linkage.csv",
     "age_scores": OUTPUT_DIR / "prospect_age_look.csv", "values": OUTPUT_DIR / "prospect_values.csv"}
for k_, p_ in F.items():
    log(f"  input {k_}: {p_.resolve()}  (modified {pd.Timestamp(p_.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
MTIME = {k_: p_.stat().st_mtime for k_, p_ in F.items()}

N_REDRAW, SEED = 2000, 20261014
EARLY = ("0", "1", "2")                  # the star chance enters in D+1 to D+3 only (decided 2026-10-14)
AGE_GROUPS = ("0", "1", "2", "3")        # the age term applies in D+1 to D+4 only (decided 2026-10-14)
GROUPS = ("0", "1", "2", "3", "4+")
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 on"}
# (age measure, centre): each a centre a reader could defend, plus the uncentred age as the far case
CENTRES = [("past", 17.5), ("past", 18.0), ("past", 18.5), ("past", 19.0),
           ("age", 18.0), ("age", 19.0), ("age", 20.0), ("age", 21.0), ("age", 0.0)]
MEASURE = {"past": "years past first eligibility", "age": "age"}


def arm_name(m, c):
    return f"no linear, {MEASURE[m]} less {c:g}" if c else f"no linear, {MEASURE[m]} not centred"


# ---- the rows (prospect_age_form_look.py's) ---------------------------------------------------------------------
d = pd.read_csv(F["rows"], dtype={"k_group": str})
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
d = d.reset_index(drop=True)
assert d["birthDate"].notna().all()
d["age_sep15"] = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "1a0aa6bb93a0", FP                                    # GUARD: prospect_age_form_look.py's rows
assert np.max(np.abs(d["nhle82_sq"] - d["nhle82"] ** 2)) < 1e-6
d["player"] = d["draftYear"].astype(str) + "-" + d["pick"].astype(str)
log(f"\nrows: {len(d):,} prospect-seasons, {d['player'].nunique():,} skaters (fingerprint {FP})")


def age_term(frame, m, c, k):
    """The age measure at centre c for rows in season k (code); `frame` carries age_sep15."""
    return (frame["age_sep15"] - k - c).values if m == "past" else (frame["age_sep15"] - c).values


def design(arm, x, g, m=None, c=None):
    """(X, names). arm: 'adopted' (b in, age as years past first eligibility less 18) or 'nolin' (b out, measure m, c)."""
    P, P2, NR = x["nhle82"].values.astype(float), x["nhle82_sq"].values.astype(float), x["no_record"].values.astype(float)
    cols, names = ([x["p_star"].values.astype(float)], ["p_star"]) if g in EARLY else ([], [])
    if arm == "adopted":
        cols, names = cols + [P], names + ["nhle82"]
        m, c = "past", 18.0
    cols, names = cols + [P2, NR], names + ["nhle82_sq", "no_record"]
    if g in AGE_GROUPS:
        cols, names = cols + [P * age_term(x, m, c, int(g))], names + ["prod_x_age"]
    return np.column_stack(cols), names


def run(arm, m=None, c=None):
    """Held-out errors (each draft left out) and the all-drafts coefficients for one arm."""
    err = np.full(len(d), np.nan)
    full = {}
    for g, x in d.groupby("k_group"):
        X, names = design(arm, x, g, m, c)
        y = x["remaining_M"].values.astype(float)
        full[g] = (np.linalg.lstsq(X, y, rcond=None)[0], names)
        yrs = x["draftYear"].values
        for yr in sorted(set(yrs)):
            tr, te = yrs != yr, yrs == yr
            b = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]
            err[x.index.values[te]] = y[te] - X[te] @ b
    assert np.isfinite(err).all()
    return err, full


log("\nfitting the adopted model and the model without linear production at each centre")
E, FULL = {}, {}
E["adopted"], FULL["adopted"] = run("adopted")
for m, c in CENTRES:
    E[(m, c)], FULL[(m, c)] = run("nolin", m, c)

ref = pd.read_csv(F["age_scores"]).set_index("arm")
rm_adopted = float(np.sqrt(np.mean(E["adopted"] ** 2)))
assert abs(rm_adopted - ref.loc["age x production, seasons 0-3", "rmse_M"]) < 1e-9, rm_adopted                 # GUARD
log(f"  guard: the adopted model's held-out error reproduces prospect_age_look.py's ({rm_adopted:.4f}) (PASS)")

cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
CNT = np.array([[int((dr == c).sum()) for c in cls] for dr in draws])


def p_lower(e1, e2):
    """One-sided p: the share of redraws in which e1's summed squared error is NOT below e2's."""
    s1 = pd.Series(e1 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    s2 = pd.Series(e2 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    return 1.0 - float(np.mean(CNT @ s1 < CNT @ s2))


# ---- the traded prospects ---------------------------------------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)"])
prod = valued & pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[prod].copy()
t["k_group"] = t["k_group"].astype(str)
t["nhle82_sq"] = t["nhle82"] ** 2
t["no_record"] = (t["n_prod_seasons"] == 0).astype(float)
t["p_star"] = t["p_star"].fillna(0.0)
# age on September 15 from prospect_values.py's own measure: past_elig = age - k - 18 (D+1 to D+4, where it is used)
kk = pd.to_numeric(t["k_group"], errors="coerce")
t["age_sep15"] = t["past_elig"] + 18.0 + kk
fixed = pv[valued & ~prod]                       # goalies on draft position alone: the same under every arm
drafted, fixed_d = t["draftYear"].notna(), fixed["draftYear"].notna()


def traded_values(key, arm, m=None, c=None):
    v = pd.Series(np.nan, index=t.index)
    for g, x in t.groupby("k_group"):
        b, _ = FULL[key][g]
        X, _ = design(arm, x, g, m, c)
        v[x.index] = X @ b
    assert v.notna().all()
    return v


V = {"adopted": traded_values("adopted", "adopted")}
gap_v = float((V["adopted"] - t["value_M"]).abs().max())
assert gap_v < 1e-6, gap_v                                                                                       # GUARD
log(f"  guard: the adopted model reproduces prospect_values.csv's value_M (largest gap {gap_v:.1e}) (PASS)")
for m, c in CENTRES:
    V[(m, c)] = traded_values((m, c), "nolin", m, c)
fixed_tot = fixed.loc[fixed_d, "value_M"].sum()

# ---- the adopted model does not depend on the centre (its b absorbs the shift) -------------------------------------
for m, c in [("past", 18.5), ("age", 18.0), ("age", 20.0)]:
    worst = 0.0
    for g, x in d.groupby("k_group"):
        Xa, _ = design("adopted", x, g)
        X2, _ = design("nolin", x, g, m, c)
        X2 = np.column_stack([X2[:, :len(X2[0]) - (1 if g in AGE_GROUPS else 0)], x["nhle82"].values]
                             + ([X2[:, -1]] if g in AGE_GROUPS else []))
        y = x["remaining_M"].values
        f1 = Xa @ np.linalg.lstsq(Xa, y, rcond=None)[0]
        f2 = X2 @ np.linalg.lstsq(X2, y, rcond=None)[0]
        worst = max(worst, float(np.max(np.abs(f1 - f2))))
    assert worst < 1e-9, (m, c, worst)                                                                            # GUARD
log("  guard: with linear production in, the fitted values are the same at every centre tested (PASS)")

# ---- results ------------------------------------------------------------------------------------------------------
early = d["k_group"].isin(AGE_GROUPS).values
late = ~early
log("\nHELD-OUT ERROR ($M of remaining surplus a prospect-season; the same rows and weights for every arm)")
log("  p (defined once): the share of 2,000 redraws of the 11 drafts in which the first model's summed squared held-out")
log("  error is NOT below the second's (one-sided). Below 0.05: statistically significant at the 5% level.")
hdr = (f"  {'model':<50}{'all':>8}{'D+1-D+4':>9}{'D+5 on':>8}{'vs adopted':>11}{'p: adopted':>12}{'p: this':>9}"
       f"{'drafted':>10}{'undrafted':>11}")
log(hdr)
log(f"  {'':<50}{'':>8}{'':>9}{'':>8}{'':>11}{'better':>12}{'better':>9}{'$M':>10}{'$M':>11}")
rows = []
for key in ["adopted"] + CENTRES:
    e = E[key]
    name = "adopted (linear production in; any centre)" if key == "adopted" else arm_name(*key)
    rec = {"model": name, "measure": None if key == "adopted" else key[0], "centre": None if key == "adopted" else key[1],
           "rmse_M": float(np.sqrt(np.mean(e ** 2))), "rmse_D1_D4": float(np.sqrt(np.mean(e[early] ** 2))),
           "rmse_D5_on": float(np.sqrt(np.mean(e[late] ** 2))),
           **{f"rmse_{LABEL[g]}": float(np.sqrt(np.mean(e[(d['k_group'] == g).values] ** 2))) for g in GROUPS},
           "traded_drafted_M": float(V[key][drafted].sum() + fixed_tot),
           "traded_undrafted_M": float(V[key][~drafted].sum()), "rows": len(d), "fingerprint": FP}
    if key != "adopted":
        rec["p_adopted_better"] = p_lower(E["adopted"], e)
        rec["p_this_better"] = p_lower(e, E["adopted"])
    rows.append(rec)
    log(f"  {name:<50}{rec['rmse_M']:>8.4f}{rec['rmse_D1_D4']:>9.4f}{rec['rmse_D5_on']:>8.4f}"
        + ("" if key == "adopted" else f"{100 * (rec['rmse_M'] / rm_adopted - 1):>+10.3f}%"
           f"{rec['p_adopted_better']:>12.4f}{rec['p_this_better']:>9.4f}")
        + ("" if key != "adopted" else " " * 32)
        + f"{rec['traded_drafted_M']:>10.2f}{rec['traded_undrafted_M']:>11.2f}")
S = pd.DataFrame(rows)

log("\nBY SEASON (held-out error, $M)")
log(f"  {'model':<50}" + "".join(f"{LABEL[g]:>9}" for g in GROUPS))
for r in rows:
    log(f"  {r['model']:<50}" + "".join(f"{r['rmse_' + LABEL[g]]:>9.4f}" for g in GROUPS))

log("\nTHE AGE TERM WITHOUT LINEAR PRODUCTION (all drafts; $M a point a year of age; the implied linear value of a point")
log("  at age 18 on September 15 is -e x (the centre's distance from 18), in D+n for years past eligibility: -e x (c - 18 + k))")
for key in CENTRES:
    parts = []
    for g in AGE_GROUPS:
        b, names = FULL[key][g]
        parts.append(f"{LABEL[g]} e {b[names.index('prod_x_age')]:+.4f}, c {b[names.index('nhle82_sq')]:.4f}")
    log(f"  {arm_name(*key):<50}" + "; ".join(parts))

# ---- in sample: b in the adopted model, at each centre --------------------------------------------------------------
log("\nIN SAMPLE (beside the held-out test, not the verdict): linear production's coefficient in the adopted model")
log("  b moves with the centre (b' = b + e x shift) while the values do not; its p-value moves with it.")
ins = []
for m, c in [("past", 18.0), ("past", 18.5), ("age", 18.0), ("age", 19.0), ("age", 20.0)]:
    blocks, pos, bcols = [], 0, []
    for g in GROUPS:
        x = d[d["k_group"] == g]
        X, names = design("nolin", x, g, m, c)
        X = np.column_stack([X, x["nhle82"].values])
        names = names + ["nhle82"]
        Z = np.zeros((len(d), X.shape[1]))
        Z[x.index.values] = X
        blocks.append(Z)
        bcols.append(pos + len(names) - 1)
        pos += X.shape[1]
    Xs = np.column_stack(blocks)
    ms = sm.OLS(d["remaining_M"].values, Xs).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d["player"])[0]})
    bb, vv = ms.params[bcols], ms.cov_params()[np.ix_(bcols, bcols)]
    w = float(bb @ np.linalg.solve(vv, bb))
    pj = float(stats.chi2.sf(w, len(bcols)))
    rec = {"measure": m, "centre": c, "joint_wald": w, "joint_p": pj,
           **{f"b_{LABEL[g]}": float(ms.params[i]) for g, i in zip(GROUPS, bcols)},
           **{f"p_{LABEL[g]}": float(ms.pvalues[i]) for g, i in zip(GROUPS, bcols)}}
    ins.append(rec)
    log(f"  {MEASURE[m]} less {c:g}: joint p = {pj:.4f}; "
        + "; ".join(f"{LABEL[g]} {rec['b_' + LABEL[g]]:+.4f} (p = {rec['p_' + LABEL[g]]:.3f})" for g in GROUPS))
INS = pd.DataFrame(ins)

assert all(p_.stat().st_mtime == MTIME[k_] for k_, p_ in F.items()), "an input was rewritten during the run"  # GUARD
S.to_csv(OUTPUT_DIR / "prospect_linear_drop_centre.csv", index=False)
INS.to_csv(OUTPUT_DIR / "prospect_linear_drop_centre_insample.csv", index=False)
log("\nwrote prospect_linear_drop_centre.csv, prospect_linear_drop_centre_insample.csv and the log")
(OUTPUT_DIR / "prospect_linear_drop_centre_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
