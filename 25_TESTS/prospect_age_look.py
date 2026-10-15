"""
prospect_age_look.py -- does a prospect's age add to his slot and production? (report only)

ASKED (Thomas, 2026-10-14): "Before building, investigate age as the next addition so production and age can be
built together." The base is step two as decided (MODEL_DIRECTIVES directive 6, "Prospects, step two"): curved
production (NHLe level and its square, 50/30/20 over the three seasons before) with a no-record indicator; the
slot's star chance as well for seasons 0-2 since the draft, production alone from 3.

THE AGE INPUT (a choice made for this look; an option for Thomas)
  * Age on September 15 of the valuation season (the CBA date used everywhere since 2026-10-14), from the draft
    records' birthdates (draft_pick_linkage.csv; every row has one).
  * Within one season group, age = his age in the autumn after his draft + seasons since the draft, so "older
    now" and "drafted older" are the same input. It enters as YEARS PAST FIRST ELIGIBILITY: his age in the autumn
    after his draft minus 18 (v1.2; 18.5 in v1.0-v1.1: a first-time-eligible player is 18.0-19.0 then). Centred so
    the through-zero form still gives zero to a mid-birthday first-time-eligible pick with no other signal.

THE ARMS (each fitted for each season group 0, 1, 2, 3, 4+; through zero, draft-year indicators that sum to
zero; the slot's star chance in seasons 0-2 only, as decided):
  chosen                 step two as decided
  + age                  adds years past first eligibility
  + age x production     adds production x years past first eligibility (does the same scoring count for less
                         from an older player?)
  + age and age x production   both

SCORING: the pick curve's rule (held-out error with one draft left out at a time, 2,000 redraws of the drafts),
each arm against the chosen one on the same rows. Each addition is scored alone and in combination (CLAUDE.md).

v1.1 (2026-10-15): the rows leave out the six drafted players who died before reaching the NHL (Thomas;
pick_curve.py v1.6); v1.0 ran on 13,152 rows (fingerprint 8aa11d737772) and reproduces from git before this.
v1.2 (2026-10-15, Thomas): centred at 18; the adopted arm's values are unchanged, the flat-age arms move (they
have no constant, so the centre changes their fit).
GUARD: the chosen arm reproduces prospect_nhle_look.py v1.1's 2.2015 (to 1e-9, from prospect_nhle_look.csv).

TRAILING WEIGHTING CHECK (directive 6): production reads 50/30/20 (prospect_nhle_look.py); age reads no trailing
seasons.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, prospect_nhle_look.csv (prospect_nhle_look.py v1.1),
draft_pick_linkage.csv. OUTPUTS: OUTPUT_DIR/prospect_age_look.csv, prospect_age_coefficients.csv,
prospect_age_look_log.txt.
Run from the repo root:  python 25_TESTS/prospect_age_look.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_age_look.py v1.2 (2026-10-15)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "nhle_scores": OUTPUT_DIR / "prospect_nhle_look.csv",
     "linkage": OUTPUT_DIR / "draft_pick_linkage.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

FIRST_ELIGIBLE_AGE = 18.0          # v1.2: a first-time-eligible draftee is 18.0-19.0 on September 15 after his draft
N_REDRAW, SEED = 2000, 20261014    # as prospect_nhle_look.py
EARLY = ["0", "1", "2"]            # the slot enters in these season groups only (decided 2026-10-14)

d = pd.read_csv(F["rows"])
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
assert d["birthDate"].notna().all()
d["age"] = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
d["past_elig"] = d["age"] - d["k"] - FIRST_ELIGIBLE_AGE
d["prod_x_age"] = d["nhle82"] * d["past_elig"]
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "cff3583de536", FP                                    # GUARD: the step-two look's rows (v1.1: deceased draftees out)
log(f"\nrows: {len(d):,} (fingerprint {FP}, the production look's rows)")
x0 = d[d["k"] == 0]
log(f"  years past first eligibility, at the draft: first-time eligible (under 0.5) {int((x0['past_elig'] < 0.5).sum()):,}; "
    f"one year older {int(x0['past_elig'].between(0.5, 1.5, inclusive='left').sum()):,}; "
    f"two or more {int((x0['past_elig'] >= 1.5).sum()):,}")
log(f"  correlation with the star chance (at the draft): {np.corrcoef(x0['past_elig'], x0['p_star'])[0, 1]:.2f}; "
    f"with production: {np.corrcoef(x0['past_elig'], x0['nhle82'])[0, 1]:.2f}")

BASE = ["nhle82", "nhle82_sq", "no_record"]
ADD = {"chosen": [], "+ age": ["past_elig"], "+ age x production": ["prod_x_age"],
       "+ age and age x production": ["past_elig", "prod_x_age"]}


def cols_for(arm, g):
    return (["p_star"] if g in EARLY else []) + BASE + ADD[arm]


def fit(frame, cols, cluster):
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    X = np.column_stack([frame[c].values for c in cols]
                        + [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]])
    if cluster:
        groups = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
        return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")


err = {a: np.zeros(len(d)) for a in ADD}
coef = []
for g, x in d.groupby("k_group"):
    clus = g == "4+"
    for a in ADD:
        cols = cols_for(a, g)
        m = fit(x, cols, clus)
        coef.append({"k_group": g, "arm": a, **{c: m.params[i] for i, c in enumerate(cols)},
                     **{c + "_se": m.bse[i] for i, c in enumerate(cols)}})
        for c in sorted(x["draftYear"].unique()):
            tr, te = x[x["draftYear"] != c], x[x["draftYear"] == c]
            mt = fit(tr, cols, clus)
            err[a][te.index] = te["remaining_M"].values - te[cols].values @ mt.params[:len(cols)]
co = pd.DataFrame(coef)

ref = pd.read_csv(F["nhle_scores"]).set_index("arm").loc["chosen", "rmse_M"]
rm = float(np.sqrt(np.mean(err["chosen"] ** 2)))
assert abs(rm - ref) < 1e-9, (rm, ref)                              # GUARD
log(f"  guard: the chosen arm reproduces the production look's {ref:.4f} (PASS)")

log("\nCOEFFICIENTS ON ALL DRAFTS (age terms; $M of remaining surplus per year past first eligibility; se in brackets)")
for g in ["0", "1", "2", "3", "4+"]:
    for a in list(ADD)[1:]:
        r = co[(co["k_group"] == g) & (co["arm"] == a)].iloc[0]
        log(f"  {g:>2} {a:<28} " + "; ".join(f"{c} {r[c]:.3f} ({r[c + '_se']:.3f})" for c in ADD[a]))

cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
sse = {a: d.assign(e2=err[a] ** 2).groupby("draftYear")["e2"].sum() for a in ADD}
log("\nHELD-OUT ERROR ($M of remaining surplus a row; same rows for every arm)")
out = []
for a in ADD:
    r_ = float(np.sqrt(np.mean(err[a] ** 2)))
    by_k = {g: float(np.sqrt(np.mean(err[a][x.index] ** 2))) for g, x in d.groupby("k_group")}
    wins = None if a == "chosen" else int(sum(sse[a][list(dr)].sum() < sse["chosen"][list(dr)].sum() for dr in draws))
    out.append({"arm": a, "rmse_M": r_, **{f"rmse_k{g}": v for g, v in by_k.items()}, "redraws_beating_chosen": wins,
                "rows": len(d), "fingerprint": FP})
    log(f"  {a:<28} RMSE {r_:.4f} ({100 * (r_ / rm - 1):+.2f}%)  by k: " + ", ".join(f"{g} {v:.4f}" for g, v in by_k.items())
        + ("" if wins is None else f"  | beats the chosen arm in {wins:,} of {N_REDRAW:,} redraws"))

both, inter = "+ age and age x production", "+ age x production"
w2 = int(sum(sse[both][list(dr)].sum() < sse[inter][list(dr)].sum() for dr in draws))
log(f"  {both} against {inter} alone: beats it in {w2:,} of {N_REDRAW:,} redraws")
# age adds nothing four or more seasons on: age x production in seasons 0-3 only, the chosen arm from 4
late = (d["k_group"] == "4+").values
e03 = np.where(late, err["chosen"], err[inter])
s03 = d.assign(e2=e03 ** 2).groupby("draftYear")["e2"].sum()
for base_arm in ("chosen", inter):
    w3 = int(sum(s03[list(dr)].sum() < sse[base_arm][list(dr)].sum() for dr in draws))
    log(f"  age x production in seasons 0-3 only: RMSE {np.sqrt(np.mean(e03 ** 2)):.4f} "
        f"({100 * (np.sqrt(np.mean(e03 ** 2)) / rm - 1):+.2f}%); beats {base_arm} in {w3:,} of {N_REDRAW:,} redraws")
out.append({"arm": "age x production, seasons 0-3", "rmse_M": float(np.sqrt(np.mean(e03 ** 2))),
            "redraws_beating_chosen": int(sum(s03[list(dr)].sum() < sse["chosen"][list(dr)].sum() for dr in draws)),
            "rows": len(d), "fingerprint": FP})

log("\nWHAT IT MEANS: a #20 pick one season after his draft ($M at the average draft; production in NHL-equivalent "
    "points per 82)")
x1 = d[(d["k_group"] == "1") & (d["n_seasons"] > 0)]
p20 = float(d.loc[d["pick"] == 20, "p_star"].iloc[0])


def value(arm, q, pe):
    """The arm's fitted value (all drafts) for production q and years past first eligibility pe.
    nhle82_sq is stored as the level squared (prospect_nhle_look.py v1.2)."""
    r = co[(co["k_group"] == "1") & (co["arm"] == arm)].iloc[0]
    v = r["p_star"] * p20 + r["nhle82"] * q + r["nhle82_sq"] * q * q
    if "past_elig" in ADD[arm]:
        v += r["past_elig"] * pe
    if "prod_x_age" in ADD[arm]:
        v += r["prod_x_age"] * q * pe
    return v


for qq, ql in ((float(x1["nhle82"].median()), "median"), (float(x1["nhle82"].quantile(0.9)), "90th percentile")):
    log(f"  production at the {ql} ({qq:.1f}): chosen ${value('chosen', qq, 0):.2f}M")
    for pe, lab in ((-0.4, "first-time eligible, late birthday"), (0.0, "first-time eligible, mid-year birthday"),
                    (1.0, "drafted a year older")):
        log(f"    {lab:<40} + age ${value('+ age', qq, pe):.2f}M; + age x production ${value(inter, qq, pe):.2f}M")

pd.DataFrame(out).to_csv(OUTPUT_DIR / "prospect_age_look.csv", index=False)
co.to_csv(OUTPUT_DIR / "prospect_age_coefficients.csv", index=False)
(OUTPUT_DIR / "prospect_age_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_age_look.csv, prospect_age_coefficients.csv and the log in {OUTPUT_DIR}")
