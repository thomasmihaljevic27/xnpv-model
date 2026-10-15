"""
prospect_age_correlation.py -- are age and time since the draft too collinear to use both? (report only)

ASKED (the supervisor, meeting of 2026-10-15): "I'm just worried about whether ... age and the time are going to be
just very collinear and that you're gonna have some regression issues. So I guess I would need to see correlation
coefficients there when you have the raw data and then seeing if it makes sense to have them both."

WHAT THE MODEL USES (prospect_values.py v1.5): time since the draft never enters a regression as a variable. The
model fits one regression for each season group (D+1, D+2, D+3, D+4, D+5 and later), so time since the draft is
constant inside each of the first four and varies only from 4 to 7 seasons inside the last, which has no age term.
Age enters as years past first eligibility = age on September 15 of the valuation season - seasons since the draft
- 18 (v1.1), i.e. how much older than an 18-year-old he was in the autumn after his draft.

THIS REPORTS, on the 13,104 skater prospect-rows the age terms are fitted on (fingerprint asserted):
  1. pooled over all seasons: correlation of age with seasons since the draft, and of years past first eligibility
     with seasons since the draft (what a single regression with both would face);
  2. inside each season group: age against years past first eligibility (identical up to a constant where the
     group holds one season), and age against seasons since the draft in the pooled D+5 and later group;
  3. inside each season group's adopted regression: the correlations among its terms and each term's variance
     inflation factor (how much its standard error is enlarged by its overlap with the other terms).
Season labels: k = 0 in the code is D+1, as in the document.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, draft_pick_linkage.csv.
OUTPUTS: OUTPUT_DIR/prospect_age_correlation_log.txt.
Run from the repo root:  python 25_TESTS/prospect_age_correlation.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from statsmodels.stats.outliers_influence import variance_inflation_factor

SCRIPT_VERSION = "prospect_age_correlation.py v1.1 (2026-10-15)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "linkage": OUTPUT_DIR / "draft_pick_linkage.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

FIRST_ELIGIBLE_AGE = 18.0                 # as prospect_values.py v1.7
SLOT_EARLY, AGE_GROUPS = ["0", "1", "2"], ["0", "1", "2", "3"]   # the adopted model's terms by season group
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later"}
NAME = {"p_star": "star chance", "nhle82": "production", "nhle82_sq": "production squared",
        "no_record": "no record", "prod_x_age": "production x years past elig."}

d = pd.read_csv(F["rows"])
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "cff3583de536", FP                                     # GUARD: the age terms' rows
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
assert d["birthDate"].notna().all()
d["k_group"] = d["k_group"].astype(str)
d["age"] = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
d["past_elig"] = d["age"] - d["k"] - FIRST_ELIGIBLE_AGE
d["prod_x_age"] = d["nhle82"] * d["past_elig"]
log(f"\nrows: {len(d):,} skater prospect-rows, {d[['draftYear', 'pick']].drop_duplicates().shape[0]:,} players "
    f"(fingerprint {FP})")


def r(a, b):
    return float(np.corrcoef(a, b)[0, 1])


log("\n1. POOLED OVER ALL SEASONS (what one regression holding both would face)")
log(f"  age on September 15 vs seasons since the draft:        r = {r(d['age'], d['k']):.3f}")
log(f"  years past first eligibility vs seasons since the draft: r = {r(d['past_elig'], d['k']):.3f}")
log(f"  age on September 15 vs years past first eligibility:    r = {r(d['age'], d['past_elig']):.3f}")

log("\n2. INSIDE EACH SEASON GROUP (each is its own regression)")
for g, x in d.groupby("k_group"):
    extra = (f"; age vs seasons since the draft r = {r(x['age'], x['k']):.3f} (seasons {x['k'].min()}-{x['k'].max()} "
             f"since the draft; this group has no age term)") if g == "4+" else ""
    log(f"  {LABEL[g]:<14} rows {len(x):5,}  age vs years past first eligibility r = {r(x['age'], x['past_elig']):.3f}"
        f"{extra}")
x0 = d[d["k"] == 0]
log(f"  years past first eligibility in D+1: mean {x0['past_elig'].mean():+.2f}, sd {x0['past_elig'].std():.2f}, "
    f"range {x0['past_elig'].min():+.2f} to {x0['past_elig'].max():+.2f}")

log("\n3. THE ADOPTED REGRESSION'S TERMS, INSIDE EACH SEASON GROUP")
log("   variance inflation factor (VIF): 1 = no overlap with the other terms; a VIF of 10 means the term's standard "
    "error is about 3.2 times what it would be with no overlap (the square root of 10)")
for g, x in d.groupby("k_group"):
    cols = (["p_star"] if g in SLOT_EARLY else []) + ["nhle82", "nhle82_sq", "no_record"] \
        + (["prod_x_age"] if g in AGE_GROUPS else [])
    X = np.column_stack([np.ones(len(x))] + [x[c].values for c in cols])   # with a constant, the usual VIF
    vif = {c: variance_inflation_factor(X, i + 1) for i, c in enumerate(cols)}
    cm = np.corrcoef(np.column_stack([x[c].values for c in cols]), rowvar=False)
    log(f"\n  {LABEL[g]}: VIF " + "; ".join(f"{NAME[c]} {v:.1f}" for c, v in vif.items()))
    for i, a in enumerate(cols):
        log(f"    {NAME[a]:<30}" + "".join(f"{cm[i, j]:>8.2f}" for j in range(len(cols))))

(OUTPUT_DIR / "prospect_age_correlation_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote the log in {OUTPUT_DIR}")
