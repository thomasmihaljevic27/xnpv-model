"""
prospect_curve_vs_line.py -- does curved production beat straight-line production head to head? (report only)

ASKED (Thomas, 2026-10-15, on "Valuing Prospects"): the curved version's improvement over the slot alone has a
one-sided p of 0.084, which is not significant. The production look (prospect_nhle_look.py v1.1) scored each
candidate against the slot alone only; it never compared the curve with the straight line directly. This does.

THREE HEAD-TO-HEAD COMPARISONS, each on the production look's 13,104 skater prospect-rows (fingerprint asserted):
  1. As in Table 2 of the document: slot in every season; straight line against curved.
       straight: surplus = a x star chance + b x production + d x no-record
       curved:   the same plus c x production squared
  2. With the adopted structure (slot in D+1 to D+3 only, production alone from D+4): straight against curved.
  3. The adopted model with age (production x years past first eligibility in D+1 to D+4): straight against curved.
Each fit is the pick curve's form: one regression per season group (D+1, D+2, D+3, D+4, D+5 and later), through
zero, draft-year indicators that sum to zero; robust (HC1) errors, clustered by player for D+5 and later.

SCORING: the document's rule. Held-out error: each draft predicted from a fit without it, at the average draft.
Then the same 2,000 redraws of the eleven drafts as prospect_nhle_look.py (same seed, so the draws are identical),
counting the redraws in which the curved version's summed squared error is below the straight line's. The one-sided
p is the share of redraws in which it is not below. The pick curve's bar was 1,950 of 2,000 (p <= 0.025).

GUARDS: the straight and curved arms of comparison 1 reproduce prospect_nhle_look.csv's held-out errors (2.2285,
2.2009) and redraw counts against the slot alone (1,941 and 1,832); comparison 2's curved arm reproduces the chosen
arm (2.2007); comparison 3's curved arm reproduces prospect_age_look.csv's adopted arm (2.1853); all to 1e-9.

Season labels: k = 0 in the code is D+1 (the season after the draft), as in the document.
TRAILING WEIGHTING CHECK: production is the production look's 50/30/20 level (W_NHLE there); nothing here
re-weights it.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, prospect_nhle_look.csv, prospect_age_look.csv, draft_pick_linkage.csv.
OUTPUTS: OUTPUT_DIR/prospect_curve_vs_line.csv, prospect_curve_vs_line_log.txt.
Run from the repo root:  python 25_TESTS/prospect_curve_vs_line.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_curve_vs_line.py v1.3 (2026-10-16)"   # no draft-year terms (Thomas, 2026-10-16)
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "nhle_scores": OUTPUT_DIR / "prospect_nhle_look.csv",
     "age_scores": OUTPUT_DIR / "prospect_age_look.csv", "linkage": OUTPUT_DIR / "draft_pick_linkage.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

N_REDRAW, SEED = 2000, 20261014          # as prospect_nhle_look.py: the same 2,000 redraws
FIRST_ELIGIBLE_AGE = 18.0                 # as prospect_age_look.py v1.2 / prospect_values.py v1.7
SLOT_ALL = ["0", "1", "2", "3", "4+"]     # comparison 1: the slot in every season group
SLOT_EARLY = ["0", "1", "2"]              # comparisons 2-3: the slot in D+1 to D+3 only (adopted)
AGE_GROUPS = ["0", "1", "2", "3"]         # comparison 3: age discounts production in D+1 to D+4 only (adopted)
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later"}

# ---- the rows: the production look's, with age added as prospect_age_look.py adds it --------------------
d = pd.read_csv(F["rows"])
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "cff3583de536", FP                                     # GUARD: the production look's rows
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
assert d["birthDate"].notna().all()
d["k_group"] = d["k_group"].astype(str)
d["age"] = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
d["past_elig"] = d["age"] - d["k"] - FIRST_ELIGIBLE_AGE
d["prod_x_age"] = d["nhle82"] * d["past_elig"]
# nhle82_sq is stored by the production look as production squared (v1.2)
log(f"\nrows: {len(d):,} skater prospect-rows, {d[['draftYear', 'pick']].drop_duplicates().shape[0]:,} players "
    f"(fingerprint {FP})")


def cols_for(form, slot_groups, age, g):
    """The regressors one arm uses in season group g. form: straight (production), curved (production and its
    square), squared (its square alone, v1.1)."""
    c = ["p_star"] if g in slot_groups else []
    c += {"straight": ["nhle82"], "curved": ["nhle82", "nhle82_sq"], "squared": ["nhle82_sq"]}[form] + ["no_record"]
    if age and g in AGE_GROUPS:
        c += ["prod_x_age"]
    return c


def fit(frame, cols, cluster):
    """The pick curve's form: through zero, no draft-year terms (v1.3)."""
    X = np.column_stack([frame[c].values for c in cols])
    if cluster:
        groups = pd.factorize(frame["draftYear"].astype(str) + "-" + frame["pick"].astype(str))[0]
        return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    return sm.OLS(frame["remaining_M"].values, X).fit(cov_type="HC1")


def held_out(form, slot_groups, age):
    """Each row's held-out miss: its draft predicted at the average draft from a fit without that draft."""
    e = np.zeros(len(d))
    for g, x in d.groupby("k_group"):
        cols = cols_for(form, slot_groups, age, g)
        for c in sorted(x["draftYear"].unique()):
            tr, te = x[x["draftYear"] != c], x[x["draftYear"] == c]
            m = fit(tr, cols, g == "4+")
            e[te.index] = te["remaining_M"].values - te[cols].values @ m.params[:len(cols)]
    return e


def rmse(e, idx=None):
    return float(np.sqrt(np.mean((e if idx is None else e[idx]) ** 2)))


cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]


def wins(e_a, e_b):
    """Redraws in which arm a's summed squared error is below arm b's."""
    sa = pd.Series(e_a ** 2).groupby(d["draftYear"].values).sum()
    sb = pd.Series(e_b ** 2).groupby(d["draftYear"].values).sum()
    return int(sum(sa[list(dr)].sum() < sb[list(dr)].sum() for dr in draws))


# ---- guards: reproduce the recorded arms ------------------------------------------------------------------
ref_n = pd.read_csv(F["nhle_scores"]).set_index("arm")
ref_a = pd.read_csv(F["age_scores"]).set_index("arm")
# the slot alone: star chance only, every season group
e_slot = np.zeros(len(d))
for g, x in d.groupby("k_group"):
    for c in sorted(x["draftYear"].unique()):
        tr, te = x[x["draftYear"] != c], x[x["draftYear"] == c]
        m = fit(tr, ["p_star"], g == "4+")
        e_slot[te.index] = te["remaining_M"].values - te[["p_star"]].values @ m.params[:1]

ARMS = {
    ("1", "straight"): ("straight", SLOT_ALL, False), ("1", "curved"): ("curved", SLOT_ALL, False),
    ("2", "straight"): ("straight", SLOT_EARLY, False), ("2", "curved"): ("curved", SLOT_EARLY, False),
    ("3", "straight"): ("straight", SLOT_EARLY, True), ("3", "curved"): ("curved", SLOT_EARLY, True),
    ("2", "squared"): ("squared", SLOT_EARLY, False), ("3", "squared"): ("squared", SLOT_EARLY, True),
}
E = {key: held_out(*spec) for key, spec in ARMS.items()}

checks = [("slot alone", rmse(e_slot), ref_n.loc["slot", "rmse_M"]),
          ("1 straight", rmse(E[("1", "straight")]), ref_n.loc["slot+production", "rmse_M"]),
          ("1 curved", rmse(E[("1", "curved")]), ref_n.loc["slot+production curved", "rmse_M"]),
          ("2 curved = chosen", rmse(E[("2", "curved")]), ref_n.loc["chosen", "rmse_M"]),
          ("3 curved = adopted", rmse(E[("3", "curved")]), ref_a.loc["age x production, seasons 0-3", "rmse_M"])]
for name, got, want in checks:
    assert abs(got - want) < 1e-9, (name, got, want)
w1s, w1c = wins(E[("1", "straight")], e_slot), wins(E[("1", "curved")], e_slot)
assert (w1s, w1c) == (int(ref_n.loc["slot+production", "redraws_beating_slot"]),
                      int(ref_n.loc["slot+production curved", "redraws_beating_slot"])), (w1s, w1c)
log("  guards: the slot alone, comparison 1's two arms, the chosen arm and the adopted arm reproduce the recorded "
    f"held-out errors; the redraws against the slot alone reproduce {w1s:,} and {w1c:,} (PASS)")

# ---- the head-to-head comparisons ---------------------------------------------------------------------
TITLE = {"1": "slot in every season (Table 2's two rows)",
         "2": "slot in D+1 to D+3 only, without age",
         "3": "the adopted model, with age discounting production in D+1 to D+4"}
log("\nCURVED AGAINST STRAIGHT, HEAD TO HEAD (held-out error, $M of remaining surplus per prospect-season; lower is "
    "better)")
out = []
for cmp in ("1", "2", "3"):
    es, ec = E[(cmp, "straight")], E[(cmp, "curved")]
    w = wins(ec, es)
    log(f"\n  {cmp}. {TITLE[cmp]}")
    log(f"     straight {rmse(es):.4f}   curved {rmse(ec):.4f}   ({100 * (rmse(ec) / rmse(es) - 1):+.2f}%)")
    for g, x in d.groupby("k_group"):
        log(f"       {LABEL[g]:<14} straight {rmse(es, x.index):.4f}  curved {rmse(ec, x.index):.4f}")
    log(f"     curved lower in {w:,} of {N_REDRAW:,} redraws: one-sided p = {1 - w / N_REDRAW:.4f}"
        f"  (the pick curve's bar, 1,950: {'met' if w >= 1950 else 'not met'})")
    # where the gain comes from: each draft's summed squared error, straight minus curved (positive = curved better)
    gain = (pd.Series(es ** 2 - ec ** 2).groupby(d["draftYear"].values).sum()).sort_values(ascending=False)
    worst_y, worst_v = gain.index[-1], gain.iloc[-1]
    log(f"     drafts where curved is lower: {int((gain > 0).sum())} of {len(gain)}; the draft most against it, "
        f"{worst_y}, takes back {abs(worst_v) / gain[gain > 0].sum():.0%} of the gains in the drafts for it "
        f"(summed squared error, straight minus curved, $M squared): "
        + ", ".join(f"{y} {v:+.1f}" for y, v in gain.items()))
    out.append({"comparison": cmp, "what": TITLE[cmp], "rmse_straight": rmse(es), "rmse_curved": rmse(ec),
                "redraws_curved_lower": w, "one_sided_p": 1 - w / N_REDRAW, "rows": len(d), "fingerprint": FP,
                **{f"straight_{LABEL[g]}": rmse(es, x.index) for g, x in d.groupby("k_group")},
                **{f"curved_{LABEL[g]}": rmse(ec, x.index) for g, x in d.groupby("k_group")}})

# ---- the squared term's coefficient in each season, on all drafts (adopted model) ------------------------
log("\nTHE SQUARED TERM IN THE ADOPTED MODEL, ON ALL DRAFTS (coefficient on production squared; robust se; "
    "two-sided p)")
for g, x in d.groupby("k_group"):
    cols = cols_for("curved", SLOT_EARLY, True, g)
    m = fit(x, cols, g == "4+")
    i = cols.index("nhle82_sq")
    log(f"  {LABEL[g]:<14} {m.params[i]:.3f} ({m.bse[i]:.3f})  p = {m.pvalues[i]:.4f}")

# ---- v1.1: where the 2007 draft goes against the curve (adopted model, comparison 3) ------------------------
# Production data (Elite Prospects seasons and the NHLe factors) start in 2006-07, so a 2007 draftee valued in D+1
# has at most one of his three production seasons (his draft season); a 2008 draftee at most two.
es, ec = E[("3", "straight")], E[("3", "curved")]
x7 = d[d["draftYear"] == 2007].copy()
x7["gain"] = es[x7.index] ** 2 - ec[x7.index] ** 2          # positive = curved better on this row
x7["pred_straight"] = x7["remaining_M"] - es[x7.index]
x7["pred_curved"] = x7["remaining_M"] - ec[x7.index]
log("\nTHE 2007 DRAFT IN THE ADOPTED MODEL (summed squared error, straight minus curved; positive = curved better)")
log("  by season: " + ", ".join(f"{LABEL[g]} {v:+.1f}" for g, v in x7.groupby("k_group")["gain"].sum().items()))
log(f"  production seasons behind the level in D+1: mean {d.loc[(d['draftYear'] == 2007) & (d['k'] == 0), 'n_seasons'].mean():.2f}"
    f" for 2007 draftees, {d.loc[(d['draftYear'] > 2008) & (d['k'] == 0), 'n_seasons'].mean():.2f} for 2009-2017")
log("  the rows most against the curve ($M; production in points per 82):")
for r_ in x7.sort_values("gain").head(8).itertuples():
    log(f"    {r_.player:<24} #{r_.pick:<4} {LABEL[r_.k_group]:<6} production {r_.nhle82:5.1f} "
        f"({r_.n_seasons} seasons)  delivered {r_.remaining_M:6.2f}  straight {r_.pred_straight:5.2f}  "
        f"curved {r_.pred_curved:5.2f}  gain {r_.gain:+7.1f}")

# ---- v1.1: production squared alone (no straight production term), asked 2026-10-15 ------------------------
log("\nPRODUCTION SQUARED ALONE (drops the production term; the curve then bottoms out at zero production)")
for cmp in ("2", "3"):
    eq = E[(cmp, "squared")]
    log(f"\n  {cmp}. {TITLE[cmp]}")
    log(f"     squared alone {rmse(eq):.4f}   curved {rmse(E[(cmp, 'curved')]):.4f}   straight {rmse(E[(cmp, 'straight')]):.4f}")
    for g, x in d.groupby("k_group"):
        log(f"       {LABEL[g]:<14} squared alone {rmse(eq, x.index):.4f}  curved {rmse(E[(cmp, 'curved')], x.index):.4f}"
            f"  straight {rmse(E[(cmp, 'straight')], x.index):.4f}")
    for other in ("curved", "straight"):
        w = wins(eq, E[(cmp, other)])
        log(f"     squared alone lower than {other} in {w:,} of {N_REDRAW:,} redraws (one-sided p = {1 - w / N_REDRAW:.4f})")
    out.append({"comparison": f"{cmp} squared alone", "what": TITLE[cmp], "rmse_squared_only": rmse(eq),
                "redraws_squared_lower_than_curved": wins(eq, E[(cmp, "curved")]),
                "redraws_squared_lower_than_straight": wins(eq, E[(cmp, "straight")]), "rows": len(d), "fingerprint": FP})
log("\n  squared alone with age, on all drafts (coefficient, robust se, two-sided p):")
for g, x in d.groupby("k_group"):
    cols = cols_for("squared", SLOT_EARLY, True, g)
    m = fit(x, cols, g == "4+")
    log(f"    {LABEL[g]:<14} " + "; ".join(f"{c} {m.params[i]:.3f} ({m.bse[i]:.3f}) p {m.pvalues[i]:.3f}"
                                         for i, c in enumerate(cols)))

pd.DataFrame(out).to_csv(OUTPUT_DIR / "prospect_curve_vs_line.csv", index=False)
(OUTPUT_DIR / "prospect_curve_vs_line_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_curve_vs_line.csv and the log in {OUTPUT_DIR}")
