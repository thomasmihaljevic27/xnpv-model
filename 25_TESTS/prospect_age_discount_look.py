"""
prospect_age_discount_look.py -- how should age enter the prospect model? (report only)

ASKED (the supervisor meeting of 2026-10-23, Thomas's action items): test the age term
  * as age on its own: years past first eligibility moving the value line up or down, whatever he scores;
  * as age-adjusted production with its square: an older prospect's points marked down before they enter both
    production terms;
against the adopted form, production x years past first eligibility. And (Thomas, 2026-10-23) "some form of actual
discounting (X/y^z)": production divided by a discount base y raised to the years past first eligibility, as money is
discounted by (1.03)^k. Nothing in 20_CODE/ or MODEL_DIRECTIVES.md changes; Thomas decides.

MEASURES (the meeting: R-squared, statistical significance and economic significance first; held-out error at most a
supplementary note):
  R-squared        1 - (sum of squared errors) / (sum of squares of the outcome about its mean), on all drafts, for
                   each season after the draft and pooled. Stata's "regress ..., noconstant" prints the uncentred one
                   (about zero, not the mean); it is written beside. Every arm is fitted on the same rows to the same
                   outcome, so the arms' R-squared values compare directly.
  significance     each age term's p-value, robust standard errors as the adopted fits (HC1 per season; the D+5-on
                   fit clusters by player and holds no age term in any arm). For the discount base y, H0 is y = 1 (no
                   discount); for the straight-line markdown d, H0 is d = 0. Their standard errors are the sandwich
                   (HC1) errors of the non-linear least squares fit, from its Jacobian at the estimate. That Wald
                   test depends on how the discount is written (y, log y or d), so the discount's verdict is the
                   resampling test: each season's players redrawn 2,000 times, the discount re-profiled, p = twice
                   the smaller share of redraws on either side of no discount (prospect_age_discount_boot.csv).
  economic         what a year of age costs: the value from production at 10 and 20 NHL-equivalent points per 82, in
                   D+1 and D+2, at 0 and at 1 year past first eligibility; and each arm's total for the traded drafted
                   prospects.
  held-out         (supplementary) each draft predicted from a fit without it, $M a prospect-season; p = the share of
                   2,000 redraws of the 11 drafts in which the arm's summed squared held-out error is NOT below the
                   adopted model's (one-sided; prospect_age_look.py's redraws, seed 20261014).

AGE: years past first eligibility = his age on September 15 of the valuation season, less the seasons since his draft,
less 18 (prospect_values.py v1.7): 0 for a draftee who turned 18 on the September 15 after his draft, one more for each
year older. Every age term applies in D+1 to D+4 only (code k = 0..3); D+5 and later have none in any arm, as adopted.

THE ARMS (each season after the draft fitted on its own, as the adopted model: the star chance for his draft position
in D+1 to D+3 only; P = NHL-equivalent points per 82, 50/30/20 over the three seasons before; through zero, no
draft-year terms; "a" = years past first eligibility):
  no age                              b P + c P^2                       (the scale for the rest)
  production x age (adopted)          b P + c P^2 + e P a               each point loses e a year
  age alone, in place                 b P + c P^2 + g a                 every prospect moves g a year, whatever he scores
  production x age + age alone        b P + c P^2 + e P a + g a         the two together (one more coefficient; CLAUDE.md:
                                                                        each part scored alone and together)
  age-adjusted points, straight line  P* = P (1 + d a); b P* + c P*^2   prospect_age_form_look.py's arm, again
  age-adjusted points, discounted     P* = P / y^a; b P* + c P*^2       points discounted at base y a year (X/y^z)
  production's value, discounted      (b P + c P^2) / y^a               the value from production discounted at base y
  P(1 + P), discounted (v1.1)         b P (1 + P) / y^a                 Thomas, 2026-10-23: one coefficient on P + P^2
                                                                        (the two tied 1:1), discounted at base y; one
                                                                        coefficient fewer than adopted. Against the arm
                                                                        above it measures the tie alone
  The last three are not linear in d or y. They are fitted by PROFILING: for each d (or log y) on a grid from -1.5 to
  1.5 in steps of 0.002, the other coefficients by least squares; the grid's best is refined by a bounded search
  between its two neighbours (scipy minimize_scalar, tolerance 1e-10). GUARD: the grid's best lies inside the grid.
  Each is profiled again with each draft left out, so a held-out error never sees its own draft. y = 1.25 means a
  point a year older is worth 1 / 1.25 = 0.8 of one a year younger; y below 1 would mean older points count for more.
  All arms but no age and the pair hold the same number of coefficients as the adopted one.

CENTRE CHECK (CLAUDE.md: a verdict must not hang on an arbitrary centre): every arm refitted with age centred at 18.5.
The arms whose age term multiplies a production term absorb a shift of centre (y and d are re-expressed; the values
do not move). Age alone does not: the fit runs through zero, so g x (age - 18) and g x (age - 18.5) differ by a
constant 0.5 g that no other term can take up, and its fit changes with the centre. The run reports how much.

GUARDS: the rows' fingerprint (prospect_age_look.py's rows); no age, the adopted arm and the straight-line markdown
reproduce prospect_age_form_look.py v1.1's held-out errors to 1e-6; the adopted arm applied to the traded prospects
reproduces prospect_values.csv's value_M to 1e-6; each stacked regression's coefficients equal the seasons' own fits;
no input is rewritten while the test runs.

TRAILING WEIGHTING CHECK (directive 6): production reads 50/30/20 (prospect_nhle_look.py, as stored in the rows and
in prospect_values.csv); age reads no trailing seasons.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv (prospect_nhle_look.py v1.4), draft_pick_linkage.csv,
prospect_age_form_look.csv (prospect_age_form_look.py v1.1), prospect_values.csv (prospect_values.py v1.12).
OUTPUTS: OUTPUT_DIR/prospect_age_discount_look.csv (R-squared and held-out error by arm),
prospect_age_discount_coefficients.csv, prospect_age_discount_boot.csv, prospect_age_discount_year_cost.csv, prospect_age_discount_traded.csv,
prospect_age_discount_traded_summary.csv, prospect_age_discount_look_log.txt.
Run from the repo root:  python 25_TESTS/prospect_age_discount_look.py   (a few minutes: the profiling)
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy.optimize import minimize_scalar
from scipy.stats import norm as normal

SCRIPT_VERSION = "prospect_age_discount_look.py v1.1 (2026-10-23)"   # v1.1: the one-coefficient discounted form (Thomas)
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "linkage": OUTPUT_DIR / "draft_pick_linkage.csv",
     "form_scores": OUTPUT_DIR / "prospect_age_form_look.csv", "values": OUTPUT_DIR / "prospect_values.csv"}
for k_, p_ in F.items():
    log(f"  input {k_}: {p_.resolve()}  (modified {pd.Timestamp(p_.stat().st_mtime, unit='s', tz='UTC').tz_convert('America/Toronto'):%Y-%m-%d %H:%M})")
MTIME = {k_: p_.stat().st_mtime for k_, p_ in F.items()}   # checked again at the end (a chain run can rewrite them)

CENTRE, CENTRE_CHECK = 18.0, 18.5      # years past first eligibility = age - k - centre (prospect_values.py v1.7: 18)
N_REDRAW, SEED = 2000, 20261014        # as prospect_age_look.py
EARLY = ("0", "1", "2")                # the star chance enters in D+1 to D+3 only (decided 2026-10-14)
AGE_GROUPS = ("0", "1", "2", "3")      # every age term applies in D+1 to D+4 only (decided 2026-10-14)
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 on"}
GRID = np.linspace(-1.5, 1.5, 1501)    # d, or log y, in steps of 0.002 (y from 0.22 to 4.48)
ARMS = {"no_age": "no age",
        "adopted": "production x age (adopted)",
        "age_alone": "age alone, in place",
        "pair": "production x age + age alone",
        "adj_line": "age-adjusted points, straight line",
        "adj_disc": "age-adjusted points, discounted",
        "val_disc": "production's value, discounted",
        "one_disc": "P(1 + P), discounted, one coefficient"}
PROFILED = ("adj_line", "adj_disc", "val_disc", "one_disc")
LOGBASE = ("adj_disc", "val_disc", "one_disc")     # profiled on log y; reported as y
OLD_FORM = {"no_age": "no age", "adopted": "production x age (adopted)",
            "adj_line": "age-adjusted points in both terms"}   # prospect_age_form_look.py's names for the guard

# ---- the rows: prospect_age_look.py's, with the age on September 15 -------------------------------------------
d = pd.read_csv(F["rows"], dtype={"k_group": str})
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
d = d.reset_index(drop=True)
assert d["birthDate"].notna().all()
d["age_sep15"] = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "1a0aa6bb93a0", FP                                    # GUARD: prospect_age_look.py's rows
assert np.max(np.abs(d["nhle82_sq"] - d["nhle82"] ** 2)) < 1e-6
early = d["k_group"].isin(AGE_GROUPS).values
log(f"\nrows: {len(d):,} prospect-seasons, {d[['draftYear', 'pick']].drop_duplicates().shape[0]:,} skaters "
    f"(fingerprint {FP}); D+1 to D+4: {int(early.sum()):,}")


def arrays(frame, a):
    return {"p_star": frame["p_star"].values.astype(float), "P": frame["nhle82"].values.astype(float),
            "P2": frame["nhle82_sq"].values.astype(float), "a": np.asarray(a, dtype=float),
            "y": frame["remaining_M"].values.astype(float)}


def sub(A, mask):
    return {k: v[mask] for k, v in A.items()}


def design(arm, A, g, theta=None):
    """(X, names) for one arm in season group g. theta: d for the straight line, log y for the discounted arms."""
    P, P2, a = A["P"], A["P2"], A["a"]
    cols, names = ([A["p_star"]], ["p_star"]) if g in EARLY else ([], [])
    if g not in AGE_GROUPS or arm == "no_age":
        return np.column_stack(cols + [P, P2]), names + ["nhle82", "nhle82_sq"]
    if arm == "adopted":
        return np.column_stack(cols + [P, P2, P * a]), names + ["nhle82", "nhle82_sq", "prod_x_age"]
    if arm == "age_alone":
        return np.column_stack(cols + [P, P2, a]), names + ["nhle82", "nhle82_sq", "age"]
    if arm == "pair":
        return np.column_stack(cols + [P, P2, P * a, a]), names + ["nhle82", "nhle82_sq", "prod_x_age", "age"]
    if arm == "adj_line":                                 # P* = P (1 + d a)
        ps = P * (1.0 + theta * a)
        return np.column_stack(cols + [ps, ps * ps]), names + ["nhle82", "nhle82_sq"]
    if arm == "adj_disc":                                 # P* = P / y^a, y = exp(theta)
        ps = P * np.exp(-theta * a)
        return np.column_stack(cols + [ps, ps * ps]), names + ["nhle82", "nhle82_sq"]
    if arm == "val_disc":                                 # (b P + c P^2) / y^a
        m = np.exp(-theta * a)
        return np.column_stack(cols + [P * m, P2 * m]), names + ["nhle82", "nhle82_sq"]
    if arm == "one_disc":                                 # b P (1 + P) / y^a: the linear and squared terms tied 1:1
        return np.column_stack(cols + [(P + P2) * np.exp(-theta * a)]), names + ["p_1_plus_p"]
    raise ValueError(arm)


def ls(X, y):
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return b, y - X @ b


def profile(arm, A, g):
    y = A["y"]

    def sse(t):
        r = ls(design(arm, A, g, t)[0], y)[1]
        return float(r @ r)

    s = np.array([sse(t) for t in GRID])
    i = int(np.argmin(s))
    assert 0 < i < len(GRID) - 1, (arm, g, GRID[i])                  # GUARD: the best lies inside the grid
    r = minimize_scalar(sse, bounds=(GRID[i - 1], GRID[i + 1]), method="bounded", options={"xatol": 1e-10})
    return float(r.x) if r.fun <= s[i] else float(GRID[i])


def nls_cov(arm, A, g, theta, b, resid):
    """HC1 sandwich covariance of (b, theta) for a profiled arm, from the Jacobian of the fitted values at the
    estimate (theta's column by central difference). For the discounted arms theta is re-expressed as y = exp(theta)
    by the delta method, so the last row and column are y's."""
    X, _ = design(arm, A, g, theta)
    h = 1e-6
    dX = (design(arm, A, g, theta + h)[0] - design(arm, A, g, theta - h)[0]) / (2 * h)
    J = np.column_stack([X, dX @ b])
    n, k = J.shape
    bread = np.linalg.inv(J.T @ J)
    meat = (J * resid[:, None] ** 2).T @ J
    V = bread @ meat @ bread * n / (n - k)
    if arm in LOGBASE:
        G = np.eye(k)
        G[-1, -1] = np.exp(theta)
        V = G @ V @ G.T
    return V


def fit_arm(arm, A, g, players=None, se=True):
    """{'theta', 'b', 'se', 'p', 'names', 'sse'}; theta reported as d or y. Errors HC1 (clustered by player in
    D+5 on, where no arm is profiled)."""
    th = profile(arm, A, g) if (arm in PROFILED and g in AGE_GROUPS) else None
    X, names = design(arm, A, g, th)
    if not se:
        b, r = ls(X, A["y"])
        return {"theta": th, "b": b, "names": names}
    if th is None:
        m = (sm.OLS(A["y"], X).fit(cov_type="cluster", cov_kwds={"groups": players}) if players is not None
             else sm.OLS(A["y"], X).fit(cov_type="HC1"))
        return {"theta": None, "b": m.params, "se": m.bse, "p": m.pvalues, "names": names,
                "sse": float(m.resid @ m.resid)}
    b, r = ls(X, A["y"])
    V = nls_cov(arm, A, g, th, b, r)
    sd = np.sqrt(np.diag(V))
    rep = np.exp(th) if arm in LOGBASE else th
    est = np.append(b, rep)
    null = np.append(np.zeros(len(b)), 1.0 if arm in LOGBASE else 0.0)
    pv = 2 * normal.sf(np.abs((est - null) / sd))
    return {"theta": rep, "b": b, "se": sd, "p": pv, "names": names + ["y" if arm in LOGBASE else "d"],
            "sse": float(r @ r)}


def back(arm, theta_rep):
    """The design's theta from a reported d or y."""
    if theta_rep is None:
        return None
    return float(np.log(theta_rep)) if arm in LOGBASE else theta_rep


def run(centre):
    a_all = (d["age_sep15"] - d["k"] - centre).values
    err = {arm: np.full(len(d), np.nan) for arm in ARMS}
    full, t_out = {}, {}
    for g, x in d.groupby("k_group"):
        A = arrays(x, a_all[x.index.values])
        yrs = x["draftYear"].values
        players = pd.factorize(x["draftYear"].astype(str) + "-" + x["pick"].astype(str))[0] if g == "4+" else None
        for arm in ARMS:
            full[(arm, g)] = fit_arm(arm, A, g, players)
            for c in sorted(set(yrs)):
                tr, te = yrs != c, yrs == c
                f = fit_arm(arm, sub(A, tr), g, se=False)
                Xe, _ = design(arm, sub(A, te), g, f["theta"])
                err[arm][x.index.values[te]] = A["y"][te] - Xe @ f["b"]
                t_out.setdefault((arm, g), []).append(f["theta"])
    assert all(np.isfinite(e).all() for e in err.values())
    return err, full, t_out


log(f"\nfitting every arm at centre {CENTRE} and {CENTRE_CHECK} (each profiled arm: {len(GRID):,} grid values a fit)")
R = {CENTRE: run(CENTRE), CENTRE_CHECK: run(CENTRE_CHECK)}
err, full, t_out = R[CENTRE]

# ---- guards: prospect_age_form_look.py's held-out errors -------------------------------------------------------
ref = pd.read_csv(F["form_scores"])
ref = ref[ref["centre"] == CENTRE].set_index("arm")
rm = {arm: float(np.sqrt(np.mean(e ** 2))) for arm, e in err.items()}
for arm, old in OLD_FORM.items():
    assert abs(rm[arm] - ref.loc[old, "rmse_M"]) < 1e-6, (arm, rm[arm], ref.loc[old, "rmse_M"])               # GUARD
log("  guard: no age, the adopted arm and the straight-line markdown reproduce prospect_age_form_look.py's held-out "
    "errors (" + ", ".join(f"{rm[a]:.4f}" for a in OLD_FORM) + ") (PASS)")

# ---- R-squared -------------------------------------------------------------------------------------------------
y_all = d["remaining_M"].values
groups_y = {g: y_all[(d["k_group"] == g).values] for g in LABEL}


def r2(sse, yv, centred=True):
    tss = float(((yv - yv.mean()) ** 2).sum()) if centred else float((yv ** 2).sum())
    return 1.0 - sse / tss


log("\nR-SQUARED ON ALL DRAFTS (centred: about the outcome's mean; the outcome is remaining NPV in $M; the same rows")
log("and outcome in every arm; D+5 on is the same fit in every arm). k = coefficients in D+1 to D+4 together.")
log(f"  {'arm':<38}{'k':>3}" + "".join(f"{LABEL[g]:>9}" for g in AGE_GROUPS) + f"{'D+1-D+4':>9}{'all rows':>9}"
    f"{'adj. all':>9}{'uncentred':>10}")
scores = []
sse_45 = full[("adopted", "4+")]["sse"]
for centre, (e_c, f_c, _) in R.items():
    for arm in ARMS:
        sse_g = {g: f_c[(arm, g)]["sse"] for g in LABEL}
        k_g = sum(len(f_c[(arm, g)]["names"]) for g in AGE_GROUPS)
        k_all = k_g + len(f_c[(arm, "4+")]["names"])
        y14 = y_all[early]
        rec = {"centre": centre, "arm": ARMS[arm], "key": arm, "k_D1_D4": k_g,
               **{f"r2_{LABEL[g]}": r2(sse_g[g], groups_y[g]) for g in LABEL},
               "r2_D1_D4": 1 - sum(sse_g[g] for g in AGE_GROUPS) / float(((y14 - y14.mean()) ** 2).sum()),
               "r2_all": r2(sum(sse_g.values()), y_all),
               "r2_all_uncentred": r2(sum(sse_g.values()), y_all, centred=False)}
        n = len(y_all)
        rec["adj_r2_all"] = 1 - (1 - rec["r2_all"]) * (n - 1) / (n - k_all)
        rec.update({"rmse_heldout_M": float(np.sqrt(np.mean(e_c[arm] ** 2))),
                    "rmse_heldout_D1_D4": float(np.sqrt(np.mean(e_c[arm][early] ** 2))), "rows": n, "fingerprint": FP})
        scores.append(rec)
        if centre == CENTRE:
            log(f"  {ARMS[arm]:<38}{k_g:>3}" + "".join(f"{rec['r2_' + LABEL[g]]:>9.4f}" for g in AGE_GROUPS)
                + f"{rec['r2_D1_D4']:>9.4f}{rec['r2_all']:>9.4f}{rec['adj_r2_all']:>9.4f}{rec['r2_all_uncentred']:>10.4f}")
S = pd.DataFrame(scores)

# ---- statistical significance ---------------------------------------------------------------------------------
SHORT = {"p_star": "star", "nhle82": "P", "nhle82_sq": "P^2", "prod_x_age": "P x age", "age": "age", "d": "d",
         "y": "y", "p_1_plus_p": "P(1+P)"}
log("\nCOEFFICIENTS AND SIGNIFICANCE, D+1 TO D+4 (age centred at 18; $M; robust standard errors in brackets; p two-")
log("sided; for y the test is y = 1, no discount; for d, d = 0; star chance omitted from the display)")
coef = []
for centre, (_, f_c, to_c) in R.items():
    for (arm, g), f in f_c.items():
        rec = {"centre": centre, "arm": ARMS[arm], "key": arm, "k_group": g, "season": LABEL[g]}
        for i, n_ in enumerate(f["names"]):
            est = f["b"][i] if i < len(f["b"]) else f["theta"]
            rec.update({n_: est, n_ + "_se": f["se"][i], n_ + "_p": f["p"][i]})
        if f["theta"] is not None:
            outs = [np.exp(v) if arm in LOGBASE else v for v in to_c[(arm, g)]]     # reported as y or d
            rec.update({"theta_draft_out_min": min(outs), "theta_draft_out_max": max(outs)})
        coef.append(rec)
CO = pd.DataFrame(coef)
for arm in ARMS:
    if arm == "no_age":
        continue
    log(f"  {ARMS[arm]}")
    for g in AGE_GROUPS:
        f = full[(arm, g)]
        parts = []
        for i, n_ in enumerate(f["names"]):
            if n_ == "p_star":
                continue
            est = f["b"][i] if i < len(f["b"]) else f["theta"]
            fmt = ".4f" if n_ in ("y", "d") else ".4f"
            parts.append(f"{SHORT[n_]} {est:{fmt}} ({f['se'][i]:.4f}) p={f['p'][i]:.3f}")
        extra = ""
        if f["theta"] is not None:
            lo, hi = min(t_out[(arm, g)]), max(t_out[(arm, g)])
            if arm in LOGBASE:
                lo, hi = np.exp(lo), np.exp(hi)
            extra = f"   [each draft left out {lo:.4f} to {hi:.4f}]"
        log(f"    {LABEL[g]}: " + "; ".join(parts) + extra)

# the age terms of the alternatives together, D+1 to D+4: one regression with the full set of interaction terms,
# errors clustered by player (as prospect_values.fit_stacked), for the linear arms
players_all = pd.factorize(d["draftYear"].astype(str) + "-" + d["pick"].astype(str))[0]
a18 = (d["age_sep15"] - d["k"] - CENTRE).values
log("\n  joint tests, D+1 to D+4 together (one regression with the full set of interaction terms, errors clustered by")
log("  player, as prospect_values.fit_stacked; Wald chi-squared):")
for arm, terms in (("adopted", ["prod_x_age"]), ("age_alone", ["age"]), ("pair", ["age"]), ("pair", ["prod_x_age"])):
    blocks, pos, at = [], 0, {}
    for g in sorted(LABEL):
        on = (d["k_group"] == g).values
        X, names = design(arm, arrays(d, a18), g)
        blocks += [np.where(on, X[:, j], 0.0) for j in range(X.shape[1])]
        at[g] = {n_: pos + j for j, n_ in enumerate(names)}
        pos += X.shape[1]
    ms = sm.OLS(y_all, np.column_stack(blocks)).fit(cov_type="cluster", cov_kwds={"groups": players_all})
    for g in AGE_GROUPS:                                             # GUARD: the stack equals each season's own fit
        f = full[(arm, g)]
        assert max(abs(ms.params[at[g][n_]] - f["b"][i]) for i, n_ in enumerate(f["names"])) < 1e-9, (arm, g)
    Rw = np.zeros((len(AGE_GROUPS) * len(terms), len(ms.params)))
    for j, (g, tm) in enumerate([(g, tm) for g in AGE_GROUPS for tm in terms]):
        Rw[j, at[g][tm]] = 1.0
    wt = ms.wald_test(Rw, use_f=False, scalar=True)
    log(f"    {ARMS[arm]:<38} {', '.join(SHORT[t_] for t_ in terms)} in all four seasons: chi2({Rw.shape[0]}) = "
        f"{float(wt.statistic):.2f}, p = {float(wt.pvalue):.4f}")

# the pair's age term at the other centre (through zero, its fit moves with the centre)
a185 = (d["age_sep15"] - d["k"] - CENTRE_CHECK).values
blocks, pos, at = [], 0, {}
for g in sorted(LABEL):
    on = (d["k_group"] == g).values
    X, names = design("pair", arrays(d, a185), g)
    blocks += [np.where(on, X[:, j], 0.0) for j in range(X.shape[1])]
    at[g] = {n_: pos + j for j, n_ in enumerate(names)}
    pos += X.shape[1]
ms = sm.OLS(y_all, np.column_stack(blocks)).fit(cov_type="cluster", cov_kwds={"groups": players_all})
Rw = np.zeros((len(AGE_GROUPS), len(ms.params)))
for j, g in enumerate(AGE_GROUPS):
    Rw[j, at[g]["age"]] = 1.0
wt = ms.wald_test(Rw, use_f=False, scalar=True)
log(f"    {ARMS['pair']:<38} age in all four seasons, age centred at {CENTRE_CHECK}: chi2(4) = {float(wt.statistic):.2f}, "
    f"p = {float(wt.pvalue):.4f}")

# ---- the discount's significance by resampling players ---------------------------------------------------------
# A Wald test on a non-linear parameter depends on how the parameter is written (y, log y or d give different
# p-values for nearly the same fit). Resampling does not: each season's rows are redrawn by player (a season's rows
# hold each player once), the discount re-profiled, and p = twice the smaller share of redraws on either side of
# "no discount" (y = 1, d = 0). The same p for y and log y by construction.
N_BOOT = 2000
COARSE = GRID[::25]                                     # steps of 0.05; refined by a bounded search, as profile()


def profile_fast(arm, A, g):
    y = A["y"]

    def sse(t):
        r = ls(design(arm, A, g, t)[0], y)[1]
        return float(r @ r)

    s = np.array([sse(t) for t in COARSE])
    i = int(np.clip(np.argmin(s), 1, len(COARSE) - 2))
    r = minimize_scalar(sse, bounds=(COARSE[i - 1], COARSE[i + 1]), method="bounded", options={"xatol": 1e-10})
    return float(r.x), int(np.argmin(s))


log(f"\nTHE DISCOUNT BY RESAMPLING PLAYERS ({N_BOOT:,} redraws of each season's players, seed {SEED}; 95% interval "
    "from the 2.5th and 97.5th percentiles; p two-sided against no discount)")
boot_rows = []
for arm in PROFILED:
    parts = []
    for g in AGE_GROUPS:
        x = d[d["k_group"] == g]
        A = arrays(x, a18[x.index.values])
        th0, _ = profile_fast(arm, A, g)
        assert abs(th0 - back(arm, full[(arm, g)]["theta"])) < 1e-6, (arm, g, th0)    # GUARD: the fast search agrees
        rng_b = np.random.default_rng(SEED)
        th, edge = np.empty(N_BOOT), 0
        for b_ in range(N_BOOT):
            idx = rng_b.integers(0, len(x), len(x))
            th[b_], i_ = profile_fast(arm, sub(A, idx), g)
            edge += int(i_ in (0, len(COARSE) - 1))
        null = 0.0                                       # log y = 0 and d = 0 are both "no discount"
        p = min(1.0, 2 * min(float(np.mean(th <= null)), float(np.mean(th >= null))))
        rep = np.exp(th) if arm in LOGBASE else th
        lo, hi = np.percentile(rep, [2.5, 97.5])
        boot_rows.append({"arm": ARMS[arm], "season": LABEL[g], "estimate": full[(arm, g)]["theta"], "lo95": lo,
                          "hi95": hi, "p_boot": p, "redraws_at_grid_edge": edge})
        parts.append(f"{LABEL[g]} {full[(arm, g)]['theta']:.3f} [{lo:.3f}, {hi:.3f}] p={p:.4f}"
                     + (f" ({edge} redraws at the grid's edge)" if edge else ""))
    log(f"  {ARMS[arm]:<38} {'y' if arm in LOGBASE else 'd'}: " + "; ".join(parts))
pd.DataFrame(boot_rows).to_csv(OUTPUT_DIR / "prospect_age_discount_boot.csv", index=False)

# ---- economic significance: what a year of age costs ------------------------------------------------------------
log("\nWHAT A YEAR OF AGE COSTS ($M of the value from production and age: the star chance left out; from 0 to 1 year")
log("past first eligibility, i.e. a draftee who turned 18 on the September 15 after his draft against one a year")
log("older; share = the year's cost / the value at 0)")


def prod_value(arm, g, P, a):
    f = full[(arm, g)]
    A = {"p_star": np.zeros(1), "P": np.array([float(P)]), "P2": np.array([float(P) ** 2]), "a": np.array([a]),
         "y": np.zeros(1)}
    X, _ = design(arm, A, g, back(arm, f["theta"]))
    return float(X[0] @ f["b"])


cost_rows = []
log(f"  {'arm':<38}" + "".join(f"{LABEL[g] + ', ' + str(q) + ' pts':>22}" for g in ("0", "1") for q in (0, 10, 20)))
for arm in [a for a in ARMS if a != "no_age"]:
    cells = []
    for g in ("0", "1"):
        for q in (0, 10, 20):
            v0, v1 = prod_value(arm, g, q, 0.0), prod_value(arm, g, q, 1.0)
            share = (v0 - v1) / v0 if abs(v0) > 1e-12 else np.nan
            cost_rows.append({"arm": ARMS[arm], "season": LABEL[g], "points_per_82": q, "value_at_0_M": v0,
                              "value_at_1_M": v1, "cost_M": v0 - v1, "share": share})
            cells.append(f"{v0 - v1:5.2f} of {v0:5.2f}" + (f" ({100 * share:3.0f}%)" if np.isfinite(share) else "       "))
    log(f"  {ARMS[arm]:<38}" + "".join(f"{c:>22}" for c in cells))
for arm in LOGBASE:
    log(f"  {ARMS[arm]}: y by season " + "; ".join(
        f"{LABEL[g]} {full[(arm, g)]['theta']:.3f} (a year older keeps {100 / full[(arm, g)]['theta']:.0f}% of "
        + ("each point" if arm == "adj_disc" else "production's value") + ")" for g in AGE_GROUPS))

# ---- the centre check -----------------------------------------------------------------------------------------
log(f"\nCENTRE CHECK: every arm refitted with age centred at {CENTRE_CHECK} instead of {CENTRE}")
for arm in ARMS:
    g18 = S[(S["centre"] == CENTRE) & (S["key"] == arm)].iloc[0]
    g185 = S[(S["centre"] == CENTRE_CHECK) & (S["key"] == arm)].iloc[0]
    log(f"  {ARMS[arm]:<38} R-squared all rows {g18['r2_all']:.6f} at {CENTRE}, {g185['r2_all']:.6f} at {CENTRE_CHECK}; "
        f"held-out {g18['rmse_heldout_M']:.6f} / {g185['rmse_heldout_M']:.6f}")
for arm in ("age_alone", "pair"):
    log(f"  {ARMS[arm]:<38} age's p by season at {CENTRE} / {CENTRE_CHECK}: " + "; ".join(
        f"{LABEL[g]} {full[(arm, g)]['p'][full[(arm, g)]['names'].index('age')]:.3f} / "
        f"{R[CENTRE_CHECK][1][(arm, g)]['p'][R[CENTRE_CHECK][1][(arm, g)]['names'].index('age')]:.3f}"
        for g in AGE_GROUPS))

# ---- held-out error (supplementary) ---------------------------------------------------------------------------
cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
CNT = np.array([[int((dr == c).sum()) for c in cls] for dr in draws])


def p_lower(e1, e2):
    s1 = pd.Series(e1 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    s2 = pd.Series(e2 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    return 1.0 - float(np.mean(CNT @ s1 < CNT @ s2))


log("\nHELD-OUT ERROR (supplementary; $M of remaining NPV a prospect-season, each draft predicted from a fit without it;")
log("p = the share of 2,000 redraws of the 11 drafts in which the arm's summed squared error is NOT below the adopted")
log("model's, one-sided; below 0.05 means lower error, statistically significant at the 5% level)")
for centre, (e_c, _, _) in R.items():
    for arm in ARMS:
        p = p_lower(e_c[arm], e_c["adopted"]) if arm != "adopted" else np.nan
        S.loc[(S["centre"] == centre) & (S["key"] == arm), "p_heldout_vs_adopted"] = p
        if centre == CENTRE:
            r1 = np.sqrt(np.mean(e_c[arm] ** 2))
            log(f"  {ARMS[arm]:<38}{r1:>8.4f}" + ("" if arm == "adopted" else
                f"{100 * (r1 / rm['adopted'] - 1):>+9.3f}% against adopted, p = {p:.4f}"))

# ---- the traded prospects -------------------------------------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)"])
prod = valued & pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[prod].copy()
t["k_group"] = t["k_group"].astype(str)
t["nhle82_sq"] = t["nhle82"] ** 2
t["p_star"] = t["p_star"].fillna(0.0)
t["remaining_M"] = 0.0
V = {}
for arm in ARMS:
    v = pd.Series(np.nan, index=t.index)
    for g, x in t.groupby("k_group"):
        f = full[(arm, g)]
        X, _ = design(arm, arrays(x, x["past_elig"].values), g, back(arm, f["theta"]))
        v[x.index] = X @ f["b"]
    V[arm] = v
gap_v = float((V["adopted"] - t["value_M"]).abs().max())
assert gap_v < 1e-6, gap_v                                                                                       # GUARD
fixed = pv[valued & ~prod]
drafted, fixed_d = t["draftYear"].notna(), fixed["draftYear"].notna()
n_dr = int(drafted.sum()) + int(fixed_d.sum())
log(f"\nTHE TRADED PROSPECTS (prospect_values.csv; each arm fitted on all drafts; guard: the adopted arm reproduces "
    f"value_M, largest gap {gap_v:.1e} (PASS))")
in_age = t["k_group"].isin(AGE_GROUPS)
log(f"  {n_dr} drafted prospects valued ({int(fixed_d.sum())} goalies on draft position alone, the same under every arm), "
    f"{int((~drafted).sum())} undrafted skaters; the arms differ only for those in D+1 to D+4: "
    f"{int((in_age & drafted).sum())} drafted, {int((in_age & ~drafted).sum())} undrafted")
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
    rc = pd.concat([v[drafted], fixed.loc[fixed_d, "value_M"]]).rank().corr(
        pd.concat([t.loc[drafted, "value_M"], fixed.loc[fixed_d, "value_M"]]).rank())
    i = mv[drafted].abs().idxmax()
    r_ = t.loc[i]
    big = (f"{r_['player_name']} ({r_['trade_date']}, {LABEL[r_['k_group']]}, {r_['nhle82']:.1f} points, "
           f"{r_['past_elig']:.2f} years past) ${r_['value_M']:.2f}M -> ${v[i]:.2f}M")
    n_mv = int((mv[drafted].abs() >= 0.25).sum())
    log(f"  {ARMS[arm]:<38}{tot_d:>9.2f}{tot_d - base_d:>+8.2f}{n_mv:>9} of {n_dr:<3}{rc:>12.3f}{tot_u:>11.2f}"
        f"{tot_u - base_u:>+8.2f}   {big if arm != 'adopted' else '-'}")
    trd.append({"arm": ARMS[arm], "drafted_total_M": tot_d, "drafted_change_M": tot_d - base_d,
                "drafted_moved_025": n_mv, "drafted": n_dr, "rank_corr_drafted": rc, "undrafted_total_M": tot_u,
                "undrafted_change_M": tot_u - base_u, "largest_mover": big})
tr_out = t[["asset_id", "player_name", "trade_date", "draftYear", "pick", "k_group", "nhle82", "past_elig",
            "value_M"]].copy()
for arm in ARMS:
    tr_out[ARMS[arm]] = V[arm]

rewritten = [k_ for k_, p_ in F.items() if p_.stat().st_mtime != MTIME[k_]]
assert not rewritten, f"inputs rewritten while the test ran: {rewritten}"                                        # GUARD
log("\n  guard: no input was rewritten while the test ran (PASS)")
S.to_csv(OUTPUT_DIR / "prospect_age_discount_look.csv", index=False)
CO.to_csv(OUTPUT_DIR / "prospect_age_discount_coefficients.csv", index=False)
tr_out.to_csv(OUTPUT_DIR / "prospect_age_discount_traded.csv", index=False)
pd.DataFrame(trd).to_csv(OUTPUT_DIR / "prospect_age_discount_traded_summary.csv", index=False)
pd.DataFrame(cost_rows).to_csv(OUTPUT_DIR / "prospect_age_discount_year_cost.csv", index=False)
(OUTPUT_DIR / "prospect_age_discount_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_age_discount_look.csv, _coefficients.csv, _year_cost.csv, _traded.csv, _traded_summary.csv and "
    f"the log in {OUTPUT_DIR}")
