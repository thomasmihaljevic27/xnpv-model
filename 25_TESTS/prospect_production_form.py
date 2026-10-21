"""
prospect_production_form.py -- production straight, curved, or squared alone? Full results and significance,
on all drafts, without the prospects who died, and without the 2007 draft (report only)

ASKED (Thomas, 2026-10-15): "I think we need to test without 2007", the draft whose production rests on one season
(Elite Prospects seasons and the NHLe factors start in 2006-07) and which holds Alexei Cherepanov; deceased
prospects "should probably be noted or excluded from the data because he obviously did not make the NHL through no
fault of his own"; and production squared alone: "I'd be interested in exploring this version. Give me the full
test results and I want to see statistical significance on this."

THE FORMS (the adopted structure throughout: the slot's star chance in D+1 to D+3 only; production x years past
first eligibility in D+1 to D+4; a no-record indicator; one regression per season group D+1, D+2, D+3, D+4, D+5 and
later, through zero, draft-year indicators that sum to zero; robust (HC1) errors, clustered by player for D+5 on):
  slot alone       star chance only, every season (Section 1; the baseline)
  straight         production
  curved           production and production squared (ADOPTED)
  squared alone    production squared only (the curve then bottoms out at zero production)

THE SAMPLES (the production look's 13,104 skater prospect-rows, fingerprint asserted, and one cut of them):
  all drafts       2007-2017, without the drafted players who died before reaching the NHL (pick_curve.py v1.6)
  2007 out         without the 2007 draft (every 2007 draftee's D+1 production rests on at most one season)
v1.0 ran on the 13,152 rows that still held three deceased draftees (Cherepanov, Winkler, Pelss) and scored a
"deaths out" sample beside them; Thomas then excluded all six deceased draftees from every fit (2026-10-15), so
v1.1's "all drafts" is v1.0's deaths-out case with Renaud, Rufenach and Sobchenko also out. v1.0 reproduces from git.

SCORING, for each sample: held-out error (each draft predicted at the average draft from a fit without it), and
2,000 redraws of the sample's drafts (seed as the prospect looks) for each pair; the one-sided p is the share of
redraws in which the first form's summed squared error is NOT below the second's.
SIGNIFICANCE IN THE FIT, for each sample: each term's coefficient, robust standard error and two-sided p, season by
season; and joint tests across the five seasons on one stacked regression (every term and draft level interacted
with the season group, so the coefficients equal the separate fits; errors clustered by player throughout, since a
player appears in several seasons). Squared alone is curved with the production term set to zero, so the test of
squared alone against curved is the test that production's coefficient is zero.
TRADED PROSPECTS: each form fitted on all drafts and applied to the traded prospects' inputs in
prospect_values.csv; the curved form must reproduce value_M (GUARD), goalies keep the slot alone.

NOTE: statsmodels warns "rank-deficient" nine times. Each is a held-out fit in D+3 without the 2009 draft: the
whole data has one D+3 prospect-season with no production record (2009), so without that draft the no-record
column is all zero and its coefficient is undetermined (set to 0). The recorded looks run the same fits.
GUARDS: the rows' fingerprint; slot alone reproduces prospect_nhle_look.csv, straight and curved reproduce
prospect_curve_vs_line.csv's adopted-model arms; curved reproduces prospect_values.csv's value_M to 1e-6.
Season labels: k = 0 in the code is D+1, as in the document.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, draft_pick_linkage.csv, prospect_curve_vs_line.csv, prospect_values.csv.
OUTPUTS: OUTPUT_DIR/prospect_production_form_scores.csv, prospect_production_form_coefficients.csv,
prospect_production_form_traded.csv, prospect_production_form_log.txt.
Run from the repo root:  python 25_TESTS/prospect_production_form.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy import stats

SCRIPT_VERSION = "prospect_production_form.py v1.4 (2026-10-21)"   # v1.4: the rows of the 2026-10-20 prospect chain; v1.3   # no draft-year terms (Thomas, 2026-10-16)
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "linkage": OUTPUT_DIR / "draft_pick_linkage.csv",
     "curve_vs_line": OUTPUT_DIR / "prospect_curve_vs_line.csv", "values": OUTPUT_DIR / "prospect_values.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

N_REDRAW, SEED = 2000, 20261014
FIRST_ELIGIBLE_AGE = 18.0                 # v1.2, as prospect_values.py v1.7
GROUPS = ["0", "1", "2", "3", "4+"]
SLOT_EARLY, AGE_GROUPS = ["0", "1", "2"], ["0", "1", "2", "3"]
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5+"}
FORMS = ["slot alone", "straight", "curved", "squared alone"]
NAME = {"p_star": "star chance", "nhle82": "production", "nhle82_sq": "production squared",
        "no_record": "no record", "prod_x_age": "production x years past eligibility"}
PAIRS = [("straight", "slot alone"), ("curved", "slot alone"), ("squared alone", "slot alone"),
         ("curved", "straight"), ("squared alone", "straight"), ("squared alone", "curved"),
         ("curved", "squared alone")]

# ---- rows ------------------------------------------------------------------------------------------------
d0 = pd.read_csv(F["rows"])
FP = hashlib.sha1(pd.util.hash_pandas_object(d0[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "1a0aa6bb93a0", FP   # GUARD: the production look's rows (v1.4, 2026-10-21: the rows after 2026-10-20; v1.3: cff3583de536, reproduce from git 166a98b)
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d0 = d0.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
assert d0["birthDate"].notna().all()
d0["k_group"] = d0["k_group"].astype(str)
d0["age"] = (pd.to_datetime(d0["season"].astype(str) + "-09-15") - d0["birthDate"]).dt.days / 365.25
d0["past_elig"] = d0["age"] - d0["k"] - FIRST_ELIGIBLE_AGE
d0["prod_x_age"] = d0["nhle82"] * d0["past_elig"]
d0["pid"] = d0["draftYear"].astype(str) + "-" + d0["pick"].astype(str)
SAMPLES = {"all drafts": d0.copy(), "2007 out": d0[d0["draftYear"] != 2007].copy()}
for s_, x in SAMPLES.items():
    SAMPLES[s_] = x.reset_index(drop=True)
    log(f"  sample {s_:<11} {len(x):6,} rows, {x['pid'].nunique():,} players, {x['draftYear'].nunique()} drafts")


def cols_for(form, g):
    if form == "slot alone":
        return ["p_star"]
    c = ["p_star"] if g in SLOT_EARLY else []
    c += {"straight": ["nhle82"], "curved": ["nhle82", "nhle82_sq"], "squared alone": ["nhle82_sq"]}[form]
    c += ["no_record"] + (["prod_x_age"] if g in AGE_GROUPS else [])
    return c


def draft_cols(frame):
    return []                                                               # v1.3: no draft-year terms


def fit(frame, cols, cluster):
    X = np.column_stack([frame[c].values for c in cols] + draft_cols(frame))
    if cluster:
        return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster",
                                                         cov_kwds={"groups": pd.factorize(frame["pid"])[0]})
    return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")


def held_out(d, form):
    e = np.zeros(len(d))
    for g, x in d.groupby("k_group"):
        cols = cols_for(form, g)
        for c in sorted(x["draftYear"].unique()):
            tr, te = x[x["draftYear"] != c], x[x["draftYear"] == c]
            m = fit(tr, cols, g == "4+")
            e[te.index] = te["remaining_M"].values - te[cols].values @ m.params[:len(cols)]
    return e


def stacked(d, form):
    """One regression: every term and draft level interacted with the season group (coefficients equal the separate
    fits), errors clustered by player. Returns the fit and the column names."""
    cols, names = [], []
    for g in GROUPS:
        x_in = (d["k_group"].values == g).astype(float)
        for c in cols_for(form, g):
            cols.append(x_in * d[c].values)
            names.append((g, c))
    m = sm.OLS(d["remaining_M"].values, np.column_stack(cols)).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d["pid"])[0]})
    return m, names


def joint(m, names, term):
    idx = [i for i, n in enumerate(names) if n[1] == term]
    R = np.zeros((len(idx), len(names)))
    for r_, i in enumerate(idx):
        R[r_, i] = 1
    w = m.wald_test(R, scalar=True)
    return float(w.statistic), len(idx), float(w.pvalue)


def rmse(e, idx=None):
    return float(np.sqrt(np.mean((e if idx is None else e[idx]) ** 2)))


scores, coef_rows, ERR = [], [], {}
for s_, d in SAMPLES.items():
    log(f"\n{'=' * 100}\nSAMPLE: {s_.upper()} ({len(d):,} prospect-rows, {d['draftYear'].nunique()} drafts)")
    E = {f: held_out(d, f) for f in FORMS}
    ERR[s_] = E
    if s_ == "all drafts":                                              # GUARD
        ref = pd.read_csv(F["curve_vs_line"]).set_index("comparison")
        assert abs(rmse(E["straight"]) - ref.loc["3", "rmse_straight"]) < 1e-9
        assert abs(rmse(E["curved"]) - ref.loc["3", "rmse_curved"]) < 1e-9
        ref_s = pd.read_csv(OUTPUT_DIR / "prospect_nhle_look.csv").set_index("arm").loc["slot", "rmse_M"]
        assert abs(rmse(E["slot alone"]) - ref_s) < 1e-9
        log("  guard: slot alone, straight and curved reproduce the recorded held-out errors (PASS)")
    cls = sorted(d["draftYear"].unique())
    rng = np.random.default_rng(SEED)
    draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
    sse = {f: pd.Series(E[f] ** 2).groupby(d["draftYear"].values).sum() for f in FORMS}

    log("\n  HELD-OUT ERROR ($M of remaining surplus per prospect-season; lower is better)")
    log("    " + f"{'form':<15}{'all':>8}" + "".join(f"{LABEL[g]:>9}" for g in GROUPS) + f"{'vs slot':>10}")
    for f in FORMS:
        log("    " + f"{f:<15}{rmse(E[f]):>8.4f}" + "".join(f"{rmse(E[f], x.index):>9.4f}" for g, x in d.groupby('k_group'))
            + f"{100 * (rmse(E[f]) / rmse(E['slot alone']) - 1):>+9.2f}%")
        scores.append({"sample": s_, "form": f, "rmse_M": rmse(E[f]),
                       **{LABEL[g]: rmse(E[f], x.index) for g, x in d.groupby("k_group")}})
    log("\n  HEAD TO HEAD (2,000 redraws of the drafts; one-sided p = share of redraws the first is NOT lower)")
    for a, b in PAIRS:
        w = int(sum(sse[a][list(dr)].sum() < sse[b][list(dr)].sum() for dr in draws))
        per = (pd.Series(E[b] ** 2 - E[a] ** 2).groupby(d["draftYear"].values).sum() > 0).sum()
        log(f"    {a:<14} vs {b:<14} lower in {w:5,} of {N_REDRAW:,}   p = {1 - w / N_REDRAW:.4f}   "
            f"lower in {per} of {len(cls)} drafts")
        scores.append({"sample": s_, "form": f"{a} vs {b}", "redraws_first_lower": w, "one_sided_p": 1 - w / N_REDRAW,
                       "drafts_first_lower": int(per)})

    log("\n  COEFFICIENTS BY SEASON (coefficient, robust se, two-sided p)")
    for f in ["straight", "curved", "squared alone"]:
        log(f"\n    {f}")
        for g, x in d.groupby("k_group"):
            cols = cols_for(f, g)
            m = fit(x, cols, g == "4+")
            log(f"      {LABEL[g]:<5} " + "; ".join(f"{NAME[c].split(' x ')[0] if c != 'prod_x_age' else 'prod x age'} "
                                                 f"{m.params[i]:.3f} ({m.bse[i]:.3f}) p {m.pvalues[i]:.3f}"
                                                 for i, c in enumerate(cols)) + f"; R2 {m.rsquared:.3f}")
            for i, c in enumerate(cols):
                coef_rows.append({"sample": s_, "form": f, "season": LABEL[g], "term": NAME[c], "coef": m.params[i],
                                  "se": m.bse[i], "p": m.pvalues[i], "rows": len(x)})

    log("\n  JOINT TESTS ACROSS THE FIVE SEASONS (stacked regression, clustered by player; chi-squared)")
    for f, term, what in (("curved", "nhle82", "production's own term is zero in every season (squared alone "
                                               "suffices)"),
                          ("curved", "nhle82_sq", "the squared term is zero in every season (straight suffices)"),
                          ("squared alone", "nhle82_sq", "squared alone: the squared term is zero in every season"),
                          ("straight", "nhle82", "straight: production is zero in every season")):
        st, df_, p_ = joint(*stacked(d, f), term)
        log(f"    {what:<75} chi2({df_}) = {st:7.2f}  p = {p_:.4f}")
        scores.append({"sample": s_, "form": f"joint: {f}, {term} = 0", "chi2": st, "df": df_, "p": p_})
    # where squared alone and curved turn: curved's minimum value point by season (production at which an extra
    # point starts adding value, for a prospect of typical draft age)
    log("\n  CURVED: production at which an extra point starts to add value (typical draft age), by season")
    turns = []
    for g, x in d.groupby("k_group"):
        cols = cols_for("curved", g)
        m = fit(x, cols, g == "4+")
        b, c = m.params[cols.index("nhle82")], m.params[cols.index("nhle82_sq")]
        q25 = x.loc[x["no_record"] == 0, "nhle82"].quantile(0.25)
        turns.append(f"{LABEL[g]} {(-b / (2 * c)) if c > 0 else float('nan'):.1f} (25th percentile {q25:.1f})")
    log("    " + "; ".join(turns))

# ---- the traded prospects under each form ----------------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)"])
prod = valued & pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[prod].copy()
t["k_group"] = t["k_group"].astype(str)
t["nhle82_sq"] = t["nhle82"] ** 2
t["no_record"] = (t["n_prod_seasons"] == 0).astype(float)
t["prod_x_age"] = t["nhle82"] * t["past_elig"]
t["p_star"] = t["p_star"].fillna(0.0)


def apply(form, d):
    out = pd.Series(0.0, index=t.index)
    for g, x in d.groupby("k_group"):
        cols = cols_for(form, g)
        m = fit(x, cols, g == "4+")
        sel = t["k_group"] == g
        out[sel] = t.loc[sel, cols].values @ m.params[:len(cols)]
    return out


V = {}
for s_ in ("all drafts",):
    for f in ["straight", "curved", "squared alone"]:
        V[(s_, f)] = apply(f, SAMPLES[s_])
gap = (V[("all drafts", "curved")] - t["value_M"]).abs().max()
assert gap < 1e-6, gap                                                  # GUARD
log(f"\n{'=' * 100}\nTRADED PROSPECTS (fit on each sample, applied at each prospect's trade season; goalies on the slot "
    f"alone in every form)\n  guard: curved on all drafts reproduces prospect_values.csv's value_M (largest gap "
    f"{gap:.1e}) (PASS)")
fixed = pv[valued & ~prod]                                             # goalies and no-EP-id skaters: unchanged
drafted = t["draftYear"].notna()
fixed_d = fixed["draftYear"].notna()
log(f"  {int(drafted.sum()) + int(fixed_d.sum())} drafted ({int(fixed_d.sum())} on the slot alone, unchanged) and "
    f"{int((~drafted).sum())} undrafted skaters valued by production")
log(f"    {'version':<36}{'drafted':>10}{'undrafted':>11}{'below zero':>12}{'rank corr. with adopted':>25}")
for (s_, f), v in V.items():
    rc = stats.spearmanr(v, t["value_M"])[0]
    log(f"    {f + ', ' + s_:<36}{v[drafted].sum() + fixed.loc[fixed_d, 'value_M'].sum():>10.2f}"
        f"{v[~drafted].sum() + fixed.loc[~fixed_d, 'value_M'].sum():>11.2f}{int((v < 0).sum()):>12}{rc:>25.3f}")
sq = V[("all drafts", "squared alone")]
mv = (sq - t["value_M"])
log(f"  squared alone against the adopted curve (all drafts): {int((mv.abs() >= 0.25).sum())} values move by $0.25M or more,"
    f" {int((mv.abs() >= 0.5).sum())} by $0.5M or more; largest moves:")
for i in mv.abs().sort_values(ascending=False).index[:8]:
    r_ = t.loc[i]
    log(f"    {r_['player_name']:<24} {r_['trade_date']}  {LABEL.get(r_['k_group'], r_['k_group'])}  production "
        f"{r_['nhle82']:5.1f}  adopted ${r_['value_M']:5.2f}M  squared alone ${sq[i]:5.2f}M ({mv[i]:+.2f})")
top_a = set(t.nlargest(10, "value_M").index)
top_s = set(sq.nlargest(10).index)
log(f"  the ten most valuable: {len(top_a & top_s)} of 10 the same under both")
tr = t[["asset_id", "player_name", "trade_date", "draftYear", "pick", "k_group", "nhle82", "past_elig", "value_M"]].copy()
for (s_, f), v in V.items():
    tr[f"{f} ({s_})"] = v

pd.DataFrame(scores).to_csv(OUTPUT_DIR / "prospect_production_form_scores.csv", index=False)
pd.DataFrame(coef_rows).to_csv(OUTPUT_DIR / "prospect_production_form_coefficients.csv", index=False)
tr.to_csv(OUTPUT_DIR / "prospect_production_form_traded.csv", index=False)
(OUTPUT_DIR / "prospect_production_form_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_production_form_scores.csv, _coefficients.csv, _traded.csv and the log in {OUTPUT_DIR}")
