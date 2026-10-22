"""
prospect_term_check.py -- the prospect model's terms that are not statistically significant, under the agreed rule
(report only)

WHY (Thomas, 2026-10-21; MODEL_DIRECTIVES, "Thomas's second round of notes", item 2): every adopted regression is
checked, and the rule was agreed before any result: a term goes if it is not statistically significant at the 5% level
AND dropping it does not worsen the held-out forecast; failing terms are tested together as a set as well as one at a
time; a term that fails on p but helps the held-out forecast goes to Thomas with both numbers. Linear production is
outside this check: Thomas kept it (2026-10-21) because its p-value moves with the centre of age.

THE ADOPTED MODEL (prospect_values.py v1.11), by season after the draft (D+n = code k + 1): star probability (a) in D+1
to D+3; production (b) and production squared (c) in every season; the no-record indicator (d) in every season (exactly
zero from D+4, where no prospect without a record delivered surplus); production x (age - 18) (e) in D+1 to D+4. Age is
years past first eligibility, as prospect_values.py stores it (with linear production in, the centre changes no value).

PART A, IN SAMPLE: one regression with the full set of interaction terms (prospect_values.fit_stacked's form), errors
clustered by player; every term with p > 0.05 listed, and the joint tests of the candidates below.
PART B, HELD OUT: each draft predicted from fits without it, $M of remaining surplus a prospect-season; p = the share of
2,000 redraws of the 11 drafts (seed 20261014) in which the first model's summed squared error is NOT below the second's.
  N1  no no-record indicator (a prospect without a record is then valued on draft position alone in D+1 to D+3; from D+4
      the indicator is zero, so nothing changes there)
  N2  no production from D+5 on (b and c out there; every prospect from D+5 on, drafted or undrafted, is then worth zero)
  N3  N1 and N2 together
  Each with the traded prospects' total value (prospect_values.csv's prospects valued on production).

GUARDS: the rows' fingerprint (prospect_age_form_look.py's rows, 1a0aa6bb93a0); the adopted model's values reproduce
prospect_values.csv's value_M to 1e-6 (so the rows carry today's price line); no input is rewritten during the run.
TRAILING WEIGHTING (directive 6): production reads 50/30/20 (prospect_nhle_look.py).

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, prospect_values.csv. OUTPUTS: OUTPUT_DIR/prospect_term_check.csv,
prospect_term_check_insample.csv, prospect_term_check_log.txt.
Run from the repo root (after trade_refresh.py):  python 25_TESTS/prospect_term_check.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy import stats

SCRIPT_VERSION = "prospect_term_check.py v1.0 (2026-10-21)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "values": OUTPUT_DIR / "prospect_values.csv"}
for k_, p_ in F.items():
    log(f"  input {k_}: {p_.resolve()}  (modified {pd.Timestamp(p_.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
MTIME = {k_: p_.stat().st_mtime for k_, p_ in F.items()}
N_REDRAW, SEED = 2000, 20261014
EARLY, AGE_GROUPS, GROUPS = ("0", "1", "2"), ("0", "1", "2", "3"), ("0", "1", "2", "3", "4+")
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 on"}
ARMS = {"adopted": "adopted", "N1": "N1 no no-record indicator", "N2": "N2 no production from D+5",
        "N3": "N3 both"}

d = pd.read_csv(F["rows"], dtype={"k_group": str})
# age as prospect_linear_drop_centre.py builds it (its guard reproduced prospect_values.csv): years past first
# eligibility = age on September 15 of the season, less the seasons since the draft, less 18
link = pd.read_csv(OUTPUT_DIR / "draft_pick_linkage.csv", parse_dates=["birthDate"])[["draftYear", "overallPickNumber",
                                                                                       "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left").reset_index(drop=True)
assert d["birthDate"].notna().all()
d["past_elig"] = ((pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
                  - d["k"] - 18.0)
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "1a0aa6bb93a0", FP                                                                                   # GUARD
assert np.max(np.abs(d["nhle82_sq"] - d["nhle82"] ** 2)) < 1e-6
d["player"] = d["draftYear"].astype(str) + "-" + d["pick"].astype(str)
log(f"\nrows: {len(d):,} prospect-seasons, {d['player'].nunique():,} skaters (fingerprint {FP})")


def design(arm, x, g):
    """(X, names) for one arm in season group g; age = years past first eligibility (x['past_elig'])."""
    cols, names = [], []
    if g in EARLY:
        cols, names = [x["p_star"].values], ["p_star"]
    if not (arm in ("N2", "N3") and g == "4+"):
        cols += [x["nhle82"].values, x["nhle82_sq"].values]; names += ["nhle82", "nhle82_sq"]
    if arm not in ("N1", "N3"):
        cols.append(x["no_record"].values); names.append("no_record")
    if g in AGE_GROUPS:
        cols.append(x["nhle82"].values * x["past_elig"].values); names.append("prod_x_age")
    if not cols:
        return np.zeros((len(x), 0)), []
    return np.column_stack(cols).astype(float), names


def run(arm):
    err, full = np.full(len(d), np.nan), {}
    for g, x in d.groupby("k_group"):
        X, names = design(arm, x, g)
        y = x["remaining_M"].values.astype(float)
        if not names:                                   # nothing left: the value is zero
            full[g] = (np.zeros(0), names)
            err[x.index.values] = y
            continue
        full[g] = (np.linalg.lstsq(X, y, rcond=None)[0], names)
        yrs = x["draftYear"].values
        for yr in sorted(set(yrs)):
            tr, te = yrs != yr, yrs == yr
            b = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]
            err[x.index.values[te]] = y[te] - X[te] @ b
    assert np.isfinite(err).all()
    return err, full


E, FULL = {}, {}
for arm in ARMS:
    E[arm], FULL[arm] = run(arm)

# ---- guard: the adopted model reproduces prospect_values.csv -------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)"])
prod = valued & pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[prod].copy()
t["k_group"] = t["k_group"].astype(str)
t["nhle82_sq"] = t["nhle82"] ** 2
t["no_record"] = (t["n_prod_seasons"] == 0).astype(float)
t["p_star"] = t["p_star"].fillna(0.0)
fixed = pv[valued & ~prod]
drafted, fixed_d = t["draftYear"].notna(), fixed["draftYear"].notna()


def traded(arm):
    v = pd.Series(0.0, index=t.index)
    for g, x in t.groupby("k_group"):
        b, names = FULL[arm][g]
        if names:
            X, _ = design(arm, x, g)
            v[x.index] = X @ b
    return v


V = {arm: traded(arm) for arm in ARMS}
gap = float((V["adopted"] - t["value_M"]).abs().max())
assert gap < 1e-6, gap                                                                                           # GUARD
log(f"  guard: the adopted model reproduces prospect_values.csv's value_M (largest gap {gap:.1e}) (PASS)")

# ---- part A: in sample ----------------------------------------------------------------------------------------------
blocks, cols_at, pos = [], {}, 0
for g in GROUPS:
    x = d[d["k_group"] == g]
    X, names = design("adopted", x, g)
    Z = np.zeros((len(d), X.shape[1])); Z[x.index.values] = X
    blocks.append(Z)
    for i, n in enumerate(names):
        cols_at[(g, n)] = pos + i
    pos += X.shape[1]
Xs = np.column_stack(blocks)
nz = np.abs(Xs).sum(axis=0) > 0
ms = sm.OLS(d["remaining_M"].values, Xs[:, nz]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d["player"])[0]})
idx_of = {k: int(np.flatnonzero(nz)[:].tolist().index(v)) for k, v in cols_at.items() if nz[v]}
ins = []
log("\nPART A. IN SAMPLE (one regression with the full set of interaction terms, errors clustered by player)")
for (g, n), i in idx_of.items():
    ins.append({"season": LABEL[g], "term": n, "coef": ms.params[i], "se": ms.bse[i], "p": ms.pvalues[i]})
I = pd.DataFrame(ins)
for r in I.itertuples():
    flag = "  NOT significant at 5%" if r.p > 0.05 else ""
    log(f"  {r.season:<7}{r.term:<12}{r.coef:+9.4f} ({r.se:.4f})  p = {r.p:.3f}{flag}")


def joint(keys):
    ii = [idx_of[k] for k in keys if k in idx_of]
    b_, V_ = ms.params[ii], ms.cov_params()[np.ix_(ii, ii)]
    w = float(b_ @ np.linalg.solve(V_, b_))
    return w, len(ii), float(stats.chi2.sf(w, len(ii)))


for lab, keys in (("no-record indicator, D+1 to D+3", [(g, "no_record") for g in ("0", "1", "2")]),
                  ("production and its square from D+5", [("4+", "nhle82"), ("4+", "nhle82_sq")])):
    w, k, p = joint(keys)
    log(f"  joint: {lab}: chi-squared {w:.2f} on {k} degrees of freedom, p = {p:.4f}")

# ---- part B: held out -----------------------------------------------------------------------------------------------
cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
CNT = np.array([[int((dr == c).sum()) for c in cls] for dr in (rng.choice(cls, size=len(cls), replace=True)
                                                                   for _ in range(N_REDRAW))])


def p_lower(e1, e2):
    s1 = pd.Series(e1 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    s2 = pd.Series(e2 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    return 1.0 - float(np.mean(CNT @ s1 < CNT @ s2))


log("\nPART B. HELD OUT ($M of remaining surplus a prospect-season; each draft predicted from fits without it)")
log("  p: the share of 2,000 redraws of the 11 drafts in which the first model's summed squared error is NOT below the")
log("  second's (one-sided). Below 0.05: statistically significant at the 5% level.")
log(f"  {'model':<30}{'all':>8}" + "".join(f"{LABEL[g]:>8}" for g in GROUPS) + f"{'p: it':>8}{'p: adopted':>11}"
    f"{'drafted $M':>12}{'undrafted $M':>13}")
rows = []
for arm, lab in ARMS.items():
    e = E[arm]
    rec = {"model": lab, "rmse": float(np.sqrt(np.mean(e ** 2))),
           **{LABEL[g]: float(np.sqrt(np.mean(e[(d["k_group"] == g).values] ** 2))) for g in GROUPS},
           "drafted_M": float(V[arm][drafted].sum() + fixed.loc[fixed_d, "value_M"].sum()),
           "undrafted_M": float(V[arm][~drafted].sum())}
    if arm != "adopted":
        rec["p_it_better"] = p_lower(e, E["adopted"])
        rec["p_adopted_better"] = p_lower(E["adopted"], e)
    rows.append(rec)
    log(f"  {lab:<30}{rec['rmse']:>8.4f}" + "".join(f"{rec[LABEL[g]]:>8.4f}" for g in GROUPS)
        + ("" if arm == "adopted" else f"{rec['p_it_better']:>8.4f}{rec['p_adopted_better']:>11.4f}")
        + (" " * 19 if arm == "adopted" else "") + f"{rec['drafted_M']:>12.2f}{rec['undrafted_M']:>13.2f}")
assert all(p_.stat().st_mtime == MTIME[k_] for k_, p_ in F.items()), "an input was rewritten during the run"  # GUARD
pd.DataFrame(rows).to_csv(OUTPUT_DIR / "prospect_term_check.csv", index=False)
I.to_csv(OUTPUT_DIR / "prospect_term_check_insample.csv", index=False)
(OUTPUT_DIR / "prospect_term_check_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
log("\nwrote prospect_term_check.csv, prospect_term_check_insample.csv and the log")
