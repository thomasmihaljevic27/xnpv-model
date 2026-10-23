"""
prospect_age_form_look.py -- should the prospect model's age discount reach production squared too? (report only)

ASKED (Thomas, 2026-10-19): why does age get its own term (production x years past first eligibility) rather than
discounting the production terms already in the model? The adopted term does discount production's linear term (a
point is worth b + e x age), but it leaves production squared untouched, and prospect_age_look.py tried only four
arms (no age, age alone, production x age, both). This look tries the forms that discount production squared as
well. Nothing in 20_CODE/ or MODEL_DIRECTIVES.md changes; Thomas decides.

AGE: years past first eligibility = his age on September 15 of the valuation season, less the seasons since his
draft, less 18 (prospect_values.py v1.7): 0 for a draftee who turned 18 on the September 15 after his draft, about
0.5 for a mid-year birthday, one more for each year older at his draft. The discount applies in D+1 to D+4 only (code
k = 0..3); D+5 and later have no age term in any arm, as adopted.

THE ARMS (each fitted for each season after the draft on its own, as the adopted model: the star chance for his draft
position in D+1 to D+3 only; production P = NHL-equivalent points per 82, 50/30/20 over the three seasons before;
production squared; the no-record indicator; through zero, no draft-year terms; "age" below = years past first
eligibility):
  no age                                    b P + c P^2 (prospect_age_look.py's "chosen"; the scale for the rest)
  production x age (adopted)                b P + c P^2 + e P age: each point loses e a year; the square untouched
  + production squared x age                adds f P^2 age: both terms discounted, each at its own rate (one more
                                            coefficient in each of D+1 to D+4)
  production squared x age, in place        f P^2 age instead of e P age: only the square discounted (as many
                                            coefficients as adopted). With the arm above, each discount is scored
                                            alone and together (CLAUDE.md)
  one discount on all of production         (b P + c P^2)(1 + d age): the value from production shrinks by the same
                                            share d for each year (as many coefficients as adopted)
  age-adjusted points in both terms         P* = P (1 + d age), then b P* + c P*^2: an older prospect's points are
                                            marked down before they enter (as many coefficients as adopted)
  The last two are not linear in their coefficients. They are fitted by PROFILING d: for each d on a grid from -1.5
  to 1.5 in steps of 0.002, the other coefficients by least squares; the grid's best d is refined by a bounded
  one-dimensional search between its two neighbours (scipy minimize_scalar, tolerance 1e-10). GUARD: the grid's best
  lies inside the grid. d is profiled again with each draft left out, so a held-out error never sees its own draft.

SCORING (prospect_age_look.py v1.5's rule; the same rows and weights for every arm): held-out error, each draft
predicted from a fit without it, in $M of remaining surplus a prospect-season. p = the share of 2,000 redraws of the
11 drafts (seed 20261014, the same redraws as prospect_age_look.py) in which the arm's summed squared held-out error
is NOT below the comparison's (one-sided). Every arm shares D+5-and-later's errors, so the differences come from D+1
to D+4's rows.
CENTRE CHECK (CLAUDE.md: a verdict must not hang on an arbitrary centre): every arm refitted with age centred at 18.5.
Each age term here multiplies a production term the model already holds with its own coefficient, so a shift of
centre is absorbed (for the two profiled arms d is re-expressed: d at 18.5 = d at 18 / (1 + 0.5 d at 18)); the run
checks that the errors and the p-values do not move.
IN-SAMPLE (beside, not the verdict): the squared discount's coefficient in each season (robust errors, as the fits)
and the four together (one regression with the full set of interaction terms, errors clustered by player, as
prospect_values.fit_stacked; Wald, chi-squared).
GUARDS: the rows' fingerprint (prospect_age_look.py v1.5's rows); no age and the adopted arm reproduce
prospect_age_look.csv's "chosen" and "age x production, seasons 0-3" errors to 1e-9, and the adopted arm's p against
no age reproduces that file's redraws; the adopted arm applied to the traded prospects reproduces prospect_values.csv's
value_M to 1e-6; no input is rewritten while the test runs (a chain run on the same folder would mix two versions).

TRAILING WEIGHTING CHECK (directive 6): production reads 50/30/20 (prospect_nhle_look.py, as stored in the rows and
in prospect_values.csv); age reads no trailing seasons.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv (prospect_nhle_look.py), draft_pick_linkage.csv, prospect_age_look.csv
(prospect_age_look.py v1.5), prospect_values.csv (prospect_values.py v1.11).
OUTPUTS: OUTPUT_DIR/prospect_age_form_look.csv (held-out errors and p), prospect_age_form_coefficients.csv,
prospect_age_form_year_cost.csv (what a year of age costs), prospect_age_form_traded.csv (each traded prospect under
each arm), prospect_age_form_traded_summary.csv, prospect_age_form_look_log.txt.
Run from the repo root:  python 25_TESTS/prospect_age_form_look.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy.optimize import minimize_scalar

SCRIPT_VERSION = "prospect_age_form_look.py v1.1 (2026-10-22)"   # v1.1: no no-record indicator, as prospect_values.py v1.12 (Thomas, 2026-10-21)
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
MTIME = {k_: p_.stat().st_mtime for k_, p_ in F.items()}   # checked again at the end (a chain run can rewrite them)

CENTRE, CENTRE_CHECK = 18.0, 18.5      # years past first eligibility = age - k - centre (prospect_values.py v1.7: 18)
N_REDRAW, SEED = 2000, 20261014        # as prospect_age_look.py
EARLY = ("0", "1", "2")                # the star chance enters in D+1 to D+3 only (decided 2026-10-14)
AGE_GROUPS = ("0", "1", "2", "3")      # the age discount applies in D+1 to D+4 only (decided 2026-10-14)
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 on"}
GRID = np.linspace(-1.5, 1.5, 1501)    # d, the profiled arms' discount a year, in steps of 0.002
ARMS = {"no_age": "no age",
        "adopted": "production x age (adopted)",
        "both": "+ production squared x age",
        "sq_only": "production squared x age, in place",
        "share": "one discount on all of production",
        "adjusted": "age-adjusted points in both terms"}
PROFILED = ("share", "adjusted")
# each pair: (arm, the arm it is scored against). The first reproduces prospect_age_look.py; the next three score
# each discount alone and together; the last two the forms with as many coefficients as the adopted one
COMPARE = [("adopted", "no_age"), ("both", "adopted"), ("sq_only", "adopted"), ("both", "sq_only"),
           ("share", "adopted"), ("adjusted", "adopted")]

# ---- the rows: prospect_age_look.py's, with the age on September 15 -------------------------------------------
d = pd.read_csv(F["rows"], dtype={"k_group": str})
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
d = d.reset_index(drop=True)
assert d["birthDate"].notna().all()
d["age_sep15"] = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "1a0aa6bb93a0", FP                                    # GUARD: prospect_age_look.py v1.5's rows
assert np.max(np.abs(d["nhle82_sq"] - d["nhle82"] ** 2)) < 1e-6    # stored as the level squared (v1.2)
log(f"\nrows: {len(d):,} prospect-seasons, {d[['draftYear', 'pick']].drop_duplicates().shape[0]:,} skaters "
    f"(fingerprint {FP}, prospect_age_look.py's rows); D+1 to D+4: {int(d['k_group'].isin(AGE_GROUPS).sum()):,}")
pe = d["age_sep15"] - d["k"] - CENTRE
log(f"  years past first eligibility, D+1 to D+4 rows: 10th percentile {pe[d['k_group'].isin(AGE_GROUPS)].quantile(0.1):.2f}, "
    f"median {pe[d['k_group'].isin(AGE_GROUPS)].median():.2f}, 90th {pe[d['k_group'].isin(AGE_GROUPS)].quantile(0.9):.2f}, "
    f"largest {pe[d['k_group'].isin(AGE_GROUPS)].max():.2f}")


def arrays(frame, a):
    """The inputs every design reads, as arrays; a = years past first eligibility at the chosen centre."""
    return {"p_star": frame["p_star"].values.astype(float), "P": frame["nhle82"].values.astype(float),
            "P2": frame["nhle82_sq"].values.astype(float), "NR": frame["no_record"].values.astype(float),
            "a": np.asarray(a, dtype=float), "y": frame["remaining_M"].values.astype(float)}


def sub(A, mask):
    return {k: v[mask] for k, v in A.items()}


def design(arm, A, g, delta=None):
    """(X, names) for one arm in season group g. delta: the profiled arms' discount a year (None otherwise)."""
    P, P2, NR, a = A["P"], A["P2"], A["NR"], A["a"]
    cols, names = ([A["p_star"]], ["p_star"]) if g in EARLY else ([], [])
    if g not in AGE_GROUPS or arm == "no_age":          # D+5 on: no age in any arm (as adopted)
        return np.column_stack(cols + [P, P2]), names + ["nhle82", "nhle82_sq"]
    if arm == "adopted":
        return (np.column_stack(cols + [P, P2, P * a]),
                names + ["nhle82", "nhle82_sq", "prod_x_age"])
    if arm == "both":
        return (np.column_stack(cols + [P, P2, P * a, P2 * a]),
                names + ["nhle82", "nhle82_sq", "prod_x_age", "prod_sq_x_age"])
    if arm == "sq_only":
        return (np.column_stack(cols + [P, P2, P2 * a]),
                names + ["nhle82", "nhle82_sq", "prod_sq_x_age"])
    if arm == "share":                                   # (b P + c P^2)(1 + d age): b and c on the discounted terms
        m = 1.0 + delta * a
        return np.column_stack(cols + [P * m, P2 * m]), names + ["nhle82", "nhle82_sq"]
    if arm == "adjusted":                                # P* = P (1 + d age); b P* + c P*^2
        ps = P * (1.0 + delta * a)
        return np.column_stack(cols + [ps, ps * ps]), names + ["nhle82", "nhle82_sq"]
    raise ValueError(arm)


def profile(arm, A, g):
    """The profiled arms' d: the sum of squared errors at each grid value (the other coefficients by least squares),
    then a bounded search between the best grid value's neighbours."""
    y = A["y"]

    def sse(dl):
        X, _ = design(arm, A, g, dl)
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        r = y - X @ b
        return float(r @ r)

    s = np.array([sse(dl) for dl in GRID])
    i = int(np.argmin(s))
    assert 0 < i < len(GRID) - 1, (arm, g, GRID[i])                  # GUARD: the best d lies inside the grid
    r = minimize_scalar(sse, bounds=(GRID[i - 1], GRID[i + 1]), method="bounded", options={"xatol": 1e-10})
    return float(r.x) if r.fun <= s[i] else float(GRID[i])


def fit_arm(arm, A, g, players=None):
    """(d, params, robust se, names). Errors as prospect_age_look.fit: HC1, clustered by player for D+5 on."""
    dl = profile(arm, A, g) if (arm in PROFILED and g in AGE_GROUPS) else None
    X, names = design(arm, A, g, dl)
    if players is not None:
        m = sm.OLS(A["y"], X).fit(cov_type="cluster", cov_kwds={"groups": players})
    else:
        m = sm.OLS(A["y"], X).fit(cov_type="HC1")
    return dl, m.params, m.bse, m.pvalues, names


def run(centre):
    """Every arm at one centre: held-out errors (each draft left out), the all-drafts fits, and d with each draft out."""
    a_all = (d["age_sep15"] - d["k"] - centre).values
    err = {arm: np.full(len(d), np.nan) for arm in ARMS}
    full, d_out = {}, {}
    for g, x in d.groupby("k_group"):
        A = arrays(x, a_all[x.index.values])
        yrs = x["draftYear"].values
        players = pd.factorize(x["draftYear"].astype(str) + "-" + x["pick"].astype(str))[0] if g == "4+" else None
        for arm in ARMS:
            full[(arm, g)] = fit_arm(arm, A, g, players)
            for c in sorted(set(yrs)):
                tr, te = yrs != c, yrs == c
                dl, b, _, _, _ = fit_arm(arm, sub(A, tr), g)
                Xe, _ = design(arm, sub(A, te), g, dl)
                err[arm][x.index.values[te]] = A["y"][te] - Xe @ b
                d_out.setdefault((arm, g), []).append(dl)
    assert all(np.isfinite(e).all() for e in err.values())
    return err, full, d_out


log(f"\nfitting every arm at centre {CENTRE} and {CENTRE_CHECK} (each profiled arm: {len(GRID):,} grid values per fit)")
R = {CENTRE: run(CENTRE), CENTRE_CHECK: run(CENTRE_CHECK)}
err, full, d_out = R[CENTRE]

# ---- guards: the age look's errors and redraws ----------------------------------------------------------------
ref = pd.read_csv(F["age_scores"]).set_index("arm")
rm = {arm: float(np.sqrt(np.mean(e ** 2))) for arm, e in err.items()}
assert abs(rm["no_age"] - ref.loc["chosen", "rmse_M"]) < 1e-9, (rm["no_age"], ref.loc["chosen", "rmse_M"])       # GUARD
assert abs(rm["adopted"] - ref.loc["age x production, seasons 0-3", "rmse_M"]) < 1e-9, rm["adopted"]            # GUARD
cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
CNT = np.array([[int((dr == c).sum()) for c in cls] for dr in draws])           # each draft's count in each redraw


def p_lower(e1, e2):
    """One-sided p: the share of redraws in which e1's summed squared error is NOT below e2's."""
    s1 = pd.Series(e1 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    s2 = pd.Series(e2 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    return 1.0 - float(np.mean(CNT @ s1 < CNT @ s2))


p_ref = 1.0 - ref.loc["age x production, seasons 0-3", "redraws_beating_chosen"] / N_REDRAW
assert abs(p_lower(err["adopted"], err["no_age"]) - p_ref) < 1e-12                                              # GUARD
log(f"  guard: no age and the adopted arm reproduce prospect_age_look.py's held-out errors ({rm['no_age']:.4f}, "
    f"{rm['adopted']:.4f}) and the adopted arm's p against no age ({p_ref:.4f}) (PASS)")

# ---- held-out error -------------------------------------------------------------------------------------------
early = d["k_group"].isin(AGE_GROUPS).values
log("\nHELD-OUT ERROR ($M of remaining surplus a prospect-season; the same rows and weights for every arm)")
log("  p (defined once): the share of 2,000 redraws of the 11 drafts in which the arm's summed squared held-out error")
log("  is NOT below the comparison's (one-sided). Below 0.05: lower error, statistically significant at the 5% level.")
log(f"  {'arm':<38}{'all rows':>9}{'D+1-D+4':>9}" + "".join(f"{LABEL[g]:>8}" for g in AGE_GROUPS)
    + f"{'vs adopted':>12}")
scores = []
for centre, (e_c, _, _) in R.items():
    for arm, e in e_c.items():
        by = {g: float(np.sqrt(np.mean(e[(d["k_group"] == g).values] ** 2))) for g in LABEL}
        rec = {"centre": centre, "arm": ARMS[arm], "key": arm, "rmse_M": float(np.sqrt(np.mean(e ** 2))),
               "rmse_D1_D4": float(np.sqrt(np.mean(e[early] ** 2))), **{f"rmse_{LABEL[g]}": v for g, v in by.items()},
               "rows": len(d), "fingerprint": FP}
        scores.append(rec)
        if centre == CENTRE:
            log(f"  {ARMS[arm]:<38}{rec['rmse_M']:>9.4f}{rec['rmse_D1_D4']:>9.4f}"
                + "".join(f"{by[g]:>8.4f}" for g in AGE_GROUPS)
                + ("" if arm == "adopted" else f"{100 * (rec['rmse_M'] / rm['adopted'] - 1):>+11.3f}%"))
log("  (D+5 on: every arm's error is the adopted model's, "
    f"{float(np.sqrt(np.mean(err['adopted'][~early] ** 2))):.4f})")
S = pd.DataFrame(scores)

log("\nHEAD TO HEAD (p as defined above; p near 1 means the comparison is the lower one in most redraws)")
for centre, (e_c, _, _) in R.items():
    for a1, a2 in COMPARE:
        p = p_lower(e_c[a1], e_c[a2])
        S.loc[(S["centre"] == centre) & (S["key"] == a1), f"p_vs_{a2}"] = p
        if centre == CENTRE:
            r1, r2 = np.sqrt(np.mean(e_c[a1] ** 2)), np.sqrt(np.mean(e_c[a2] ** 2))
            log(f"  {ARMS[a1]:<38} against {ARMS[a2]:<36} {100 * (r1 / r2 - 1):+.3f}%   p = {p:.4f}")

# ---- the centre check -----------------------------------------------------------------------------------------
log(f"\nCENTRE CHECK: every arm refitted with age centred at {CENTRE_CHECK} instead of {CENTRE}")
e2 = R[CENTRE_CHECK][0]
gap = {arm: float(np.max(np.abs(err[arm] - e2[arm]))) for arm in ARMS}
log("  largest change in any held-out error ($M): " + "; ".join(f"{ARMS[a]} {v:.1e}" for a, v in gap.items()))
moved = []
for a1, a2 in COMPARE:
    p18 = S.loc[(S["centre"] == CENTRE) & (S["key"] == a1), f"p_vs_{a2}"].iloc[0]
    p185 = S.loc[(S["centre"] == CENTRE_CHECK) & (S["key"] == a1), f"p_vs_{a2}"].iloc[0]
    log(f"  {ARMS[a1]:<38} against {ARMS[a2]:<36} p = {p18:.4f} at {CENTRE}, {p185:.4f} at {CENTRE_CHECK}")
    if abs(p18 - p185) > 1e-12 or (p18 < 0.05) != (p185 < 0.05):
        moved.append((a1, a2))
for arm in PROFILED:
    for g in AGE_GROUPS:
        d18, d185 = full[(arm, g)][0], R[CENTRE_CHECK][1][(arm, g)][0]
        log(f"  {ARMS[arm]:<38} {LABEL[g]}: d {d18:+.5f} at {CENTRE}; {d185:+.5f} at {CENTRE_CHECK} "
            f"(expected from the re-expression {d18 / (1 + 0.5 * d18):+.5f})")
log("  " + ("no p-value moves with the centre: the verdicts do not depend on it" if not moved else
            f"p-values that move with the centre: {moved}"))

# ---- coefficients ---------------------------------------------------------------------------------------------
log("\nCOEFFICIENTS ON ALL DRAFTS (age centred at 18; $M; robust standard errors in brackets for the linear arms)")
coef = []
for (arm, g), (dl, b, se, pv_, names) in full.items():
    coef.append({"centre": CENTRE, "arm": ARMS[arm], "key": arm, "k_group": g, "season": LABEL[g], "d": dl,
                 **{n: b[i] for i, n in enumerate(names)}, **{n + "_se": se[i] for i, n in enumerate(names)},
                 **{n + "_p": pv_[i] for i, n in enumerate(names)},
                 **({} if dl is None else {"d_draft_out_min": min(d_out[(arm, g)]),
                                           "d_draft_out_max": max(d_out[(arm, g)])})})
for (arm, g), (dl, b, se, pv_, names) in R[CENTRE_CHECK][1].items():
    coef.append({"centre": CENTRE_CHECK, "arm": ARMS[arm], "key": arm, "k_group": g, "season": LABEL[g], "d": dl,
                 **{n: b[i] for i, n in enumerate(names)}})
CO = pd.DataFrame(coef)
SHORT = {"p_star": "star", "nhle82": "P", "nhle82_sq": "P^2", "no_record": "no record", "prod_x_age": "P x age",
         "prod_sq_x_age": "P^2 x age"}
for arm in ARMS:
    log(f"  {ARMS[arm]}")
    for g in AGE_GROUPS:
        dl, b, se, pv_, names = full[(arm, g)]
        if arm in PROFILED:
            lo, hi = min(d_out[(arm, g)]), max(d_out[(arm, g)])
            log(f"    {LABEL[g]}: d {dl:+.4f} (each draft left out {lo:+.4f} to {hi:+.4f}); "
                + "; ".join(f"{SHORT[n]} {b[i]:.4f}" for i, n in enumerate(names) if n not in ("p_star", "no_record")))
        else:
            log(f"    {LABEL[g]}: " + "; ".join(f"{SHORT[n]} {b[i]:.4f} ({se[i]:.4f})" for i, n in enumerate(names)
                                             if n not in ("p_star", "no_record")))

# the squared discount in sample: each season's own fit, and the four together in one regression
log("\nIN SAMPLE (beside the held-out test, not the verdict): the discount on production squared")
for arm in ("both", "sq_only"):
    parts = []
    for g in AGE_GROUPS:
        dl, b, se, pv_, names = full[(arm, g)]
        i = names.index("prod_sq_x_age")
        parts.append(f"{LABEL[g]} {b[i]:+.5f} (p = {pv_[i]:.3f})")
    log(f"  {ARMS[arm]:<38} " + "; ".join(parts))
a18 = (d["age_sep15"] - d["k"] - CENTRE).values
blocks, pos, cols_at = [], 0, {}
for g in sorted(LABEL):
    on = (d["k_group"] == g).values
    X, names = design("both", arrays(d, a18), g)
    blocks += [np.where(on, X[:, j], 0.0) for j in range(X.shape[1])]
    cols_at[g] = {n: pos + j for j, n in enumerate(names)}
    pos += X.shape[1]
players_all = pd.factorize(d["draftYear"].astype(str) + "-" + d["pick"].astype(str))[0]
ms = sm.OLS(d["remaining_M"].values, np.column_stack(blocks)).fit(cov_type="cluster", cov_kwds={"groups": players_all})
for g in AGE_GROUPS:                                                   # GUARD: the stack equals each season's own fit
    dl, b, _, _, names = full[("both", g)]
    assert max(abs(ms.params[cols_at[g][n]] - b[i]) for i, n in enumerate(names)) < 1e-9, g
Rw = np.zeros((len(AGE_GROUPS), len(ms.params)))
for j, g in enumerate(AGE_GROUPS):
    Rw[j, cols_at[g]["prod_sq_x_age"]] = 1.0
wt = ms.wald_test(Rw, use_f=False, scalar=True)
log(f"  + production squared x age, D+1 to D+4 together (one regression, errors clustered by player): "
    f"chi2({len(AGE_GROUPS)}) = {float(wt.statistic):.2f}, p = {float(wt.pvalue):.4f}")

# ---- what a year of age costs ---------------------------------------------------------------------------------
log("\nWHAT A YEAR OF AGE COSTS ($M of production's value: the production terms only, not the star chance; from")
log("0 to 1 year past first eligibility, i.e. a draftee who turned 18 on the September 15 after his draft against one")
log("a year older; share = the year's cost / production's value at 0)")


def prod_value(arm, g, P, a, fits=full):
    dl, b, _, _, names = fits[(arm, g)]
    A = {"p_star": np.zeros(1), "P": np.array([P]), "P2": np.array([P * P]), "NR": np.zeros(1), "a": np.array([a]),
         "y": np.zeros(1)}
    X, _ = design(arm, A, g, dl)
    return float(X[0] @ b)


cost_rows = []
log(f"  {'arm':<38}" + "".join(f"{LABEL[g] + ', ' + str(q) + ' points':>24}" for g in ("0", "1") for q in (10, 20)))
for arm in [a for a in ARMS if a != "no_age"]:
    cells = []
    for g in ("0", "1"):
        for q in (10, 20):
            v0, v1 = prod_value(arm, g, q, 0.0), prod_value(arm, g, q, 1.0)
            cost_rows.append({"arm": ARMS[arm], "season": LABEL[g], "points_per_82": q, "value_at_0_M": v0,
                              "value_at_1_M": v1, "cost_M": v0 - v1, "share": (v0 - v1) / v0})
            cells.append(f"{v0 - v1:5.2f} of {v0:5.2f} ({100 * (v0 - v1) / v0:3.0f}%)")
    log(f"  {ARMS[arm]:<38}" + "".join(f"{c:>24}" for c in cells))

# ---- the traded prospects -------------------------------------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)"])
prod = valued & pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[prod].copy()
t["k_group"] = t["k_group"].astype(str)
t["nhle82_sq"] = t["nhle82"] ** 2
t["no_record"] = (t["n_prod_seasons"] == 0).astype(float)
t["p_star"] = t["p_star"].fillna(0.0)
t["remaining_M"] = 0.0                                     # not used: arrays() needs the column
V = {}
for arm in ARMS:
    v = pd.Series(np.nan, index=t.index)
    for g, x in t.groupby("k_group"):
        dl, b, _, _, _ = full[(arm, g)]
        X, _ = design(arm, arrays(x, x["past_elig"].values), g, dl)    # past_elig: prospect_values.py's, centred at 18
        v[x.index] = X @ b
    V[arm] = v
gap_v = float((V["adopted"] - t["value_M"]).abs().max())
assert gap_v < 1e-6, gap_v                                                                                       # GUARD
fixed = pv[valued & ~prod]                                 # goalies (draft position alone): the same under every arm
drafted, fixed_d = t["draftYear"].notna(), fixed["draftYear"].notna()
n_dr = int(drafted.sum()) + int(fixed_d.sum())
log(f"\nTHE TRADED PROSPECTS (prospect_values.csv; each arm fitted on all drafts; guard: the adopted arm reproduces "
    f"value_M, largest gap {gap_v:.1e} (PASS))")
log(f"  {n_dr} drafted prospects valued ({int(fixed_d.sum())} goalies on draft position alone, the same under every arm) "
    f"and {int((~drafted).sum())} undrafted skaters on NHL contracts")
in_age = t["k_group"].isin(AGE_GROUPS)
log(f"  where the arms differ (D+1 to D+4, valued on production): {int((in_age & drafted).sum())} drafted and "
    f"{int((in_age & ~drafted).sum())} undrafted (an undrafted player's seasons count from his first eligible draft); "
    f"the rest are D+5 or later, the same under every arm")
base_d = t.loc[drafted, "value_M"].sum() + fixed.loc[fixed_d, "value_M"].sum()
base_u = t.loc[~drafted, "value_M"].sum()
log(f"  {'arm':<38}{'drafted':>9}{'change':>8}{'moved $0.25M+':>15}{'rank corr.':>12}{'undrafted':>11}{'change':>8}"
    f"   largest mover")
trd = []
for arm in ARMS:
    v = V[arm]
    tot_d = v[drafted].sum() + fixed.loc[fixed_d, "value_M"].sum()
    tot_u = v[~drafted].sum()
    mv = v - t["value_M"]
    all_new = pd.concat([v[drafted], fixed.loc[fixed_d, "value_M"]])
    all_old = pd.concat([t.loc[drafted, "value_M"], fixed.loc[fixed_d, "value_M"]])
    rc = all_new.rank().corr(all_old.rank())
    i = mv[drafted].abs().idxmax()
    r_ = t.loc[i]
    big = (f"{r_['player_name']} ({r_['trade_date']}, {LABEL[r_['k_group']]}, {r_['nhle82']:.1f} points, "
           f"{r_['past_elig']:.2f} years past) ${r_['value_M']:.2f}M -> ${v[i]:.2f}M")
    n_mv = int((mv[drafted].abs() >= 0.25).sum())
    log(f"  {ARMS[arm]:<38}{tot_d:>9.2f}{tot_d - base_d:>+8.2f}{n_mv:>9} of {n_dr:<3}{rc:>12.3f}{tot_u:>11.2f}"
        f"{tot_u - base_u:>+8.2f}   {big if arm != 'adopted' else '-'}")
    trd.append({"arm": ARMS[arm], "drafted_total_M": tot_d, "drafted_change_M": tot_d - base_d,
                "drafted_moved_025": n_mv, "drafted": n_dr, "rank_corr_drafted": rc, "undrafted_total_M": tot_u,
                "undrafted_change_M": tot_u - base_u,
                "undrafted_moved_025": int((mv[~drafted].abs() >= 0.25).sum()), "largest_mover": big})
tr_out = t[["asset_id", "player_name", "trade_date", "draftYear", "pick", "k_group", "nhle82", "past_elig",
            "value_M"]].copy()
for arm in ARMS:
    tr_out[ARMS[arm]] = V[arm]

rewritten = [k_ for k_, p_ in F.items() if p_.stat().st_mtime != MTIME[k_]]
assert not rewritten, f"inputs rewritten while the test ran: {rewritten}"                                        # GUARD
log("\n  guard: no input was rewritten while the test ran (PASS)")
S.to_csv(OUTPUT_DIR / "prospect_age_form_look.csv", index=False)
CO.to_csv(OUTPUT_DIR / "prospect_age_form_coefficients.csv", index=False)
tr_out.to_csv(OUTPUT_DIR / "prospect_age_form_traded.csv", index=False)
pd.DataFrame(trd).to_csv(OUTPUT_DIR / "prospect_age_form_traded_summary.csv", index=False)
pd.DataFrame(cost_rows).to_csv(OUTPUT_DIR / "prospect_age_form_year_cost.csv", index=False)
(OUTPUT_DIR / "prospect_age_form_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_age_form_look.csv, _coefficients.csv, _traded.csv, _traded_summary.csv, _year_cost.csv and the "
    f"log in {OUTPUT_DIR}")
