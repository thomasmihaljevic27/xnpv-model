"""
defence_dummy_look.py -- in the prospect model, is a defenceman worth a fixed amount more than a forward (a defenceman
dummy), rather than, or as well as, each of his points being worth more (defenceman x production)? (report only, v1.0)

ASKED (Thomas, 2026-11-09): "did we ever test if rather than a defenceman production term if there was more value is a
defenceman dummy variable?" No: defence_terms_look.py (2026-10-24) tested defenceman x production (adopted, v1.13),
x production squared and x draft position; no defenceman dummy on its own. "run the test".

THE TWO FORMS, in each season after the draft (the model has no constant, so a dummy is a defenceman's own starting
value in that season):
  defenceman x production   each NHLe point a defenceman scores is worth f_n more than a forward's
  defenceman dummy          every defenceman prospect is worth h_n more than a forward with the same draft position and
                            points, whatever he scores

THE ARMS (prospect_values' adopted regression, one regression with a full set of interaction terms by season after the
draft, through zero, errors clustered by player; skater prospect-seasons, the model's own rows):
  no defenceman term   draft position (D+1 to D+3), production, its square, production x (age - 18) (D+1 to D+4)
  + dummy              that, plus the defenceman dummy in each season
  + D x production     that, plus defenceman x production in each season: THE ADOPTED MODEL (prospect_values v1.13)
  + both               that, plus both
  Each scored alone and together (CLAUDE.md).

MEASURES (the reporting rule, Thomas 2026-10-27: test by significance and held-out error; report the p-value, held-out
error where the significance test is inconclusive): the Wald test that the added terms are all zero (chi2, as the
documents report it); in "+ both", each form given the other; R-squared measured from zero; held-out error (each draft
predicted from a fit on the other ten; p = the share of 2,000 redraws of the 11 drafts in which an arm's summed squared
error is NOT below the adopted model's, one-sided; seed 20261014, as defence_terms_look.py); a defenceman against a
forward with the same inputs (a 15th pick, 0, 10 and 20 points per 82); the traded prospects' totals.

GUARDS: the adopted arm reproduces prospect_values' fits (prospect_production_fits.csv's main version, every coefficient
to 1e-9), the defenceman test's recorded chi2 (prospect_doc numbers.json "def", to 1e-6), and every traded prospect's
value_M (to 1e-6); the rows are the model's own; no input is rewritten while the test runs.

Run from the repo root:  python 25_TESTS/defence_dummy_look.py   (about 1 minute)
Writes OUTPUT_DIR/defence_dummy_look.csv, defence_dummy_coefficients.csv and defence_dummy_look_log.txt.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "20_CODE"))
import prospect_values as PV                                                    # noqa: E402

SCRIPT_VERSION = "defence_dummy_look.py v1.0 (2026-11-09)"
OUT = Path(os.environ["OUTPUT_DIR"])
SRC = Path(os.environ["SOURCE_DIR"])
N_REDRAW, SEED = 2000, 20261014
GROUPS = ("0", "1", "2", "3", "4+")
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 on"}
LOG = []


def log(s=""):
    print(s, flush=True)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"prospect_values_log": OUT / "prospect_values_log.txt", "fits": OUT / "prospect_production_fits.csv",
     "values": OUT / "prospect_values.csv", "doc": OUT / "prospect_doc" / "numbers.json",
     "slots": SRC / "draft_slot_baseline.csv"}
for k_, p_ in F.items():
    log(f"  input {k_}: {p_.resolve()} (modified {pd.Timestamp(p_.stat().st_mtime, unit='s', tz='UTC').tz_convert('America/Toronto'):%Y-%m-%d %H:%M})")
MTIME = {k_: p_.stat().st_mtime for k_, p_ in F.items()}
log(f"  {(F['prospect_values_log']).read_text(encoding='utf-8').splitlines()[0]}; code {PV.SCRIPT_VERSION}")

# ---- the model's own rows -----------------------------------------------------------------------------------------
_, fitrows = PV.star_values()
rates = PV.production_rates()
fits, prow = PV.production_fits(fitrows, rates)            # skater prospect-seasons, the adopted model's rows
prow = prow.reset_index(drop=True)
prow["d_dummy"] = prow["is_d"].astype(float)              # the defenceman dummy (Elite Prospects' position, as d_x_prod)
assert np.allclose(prow["d_x_prod"], prow["nhle82"] * prow["d_dummy"])
base = lambda g: [c for c in PV.cols_for(g, "main") if c != "d_x_prod"]
ARMS = {"no defenceman term": lambda g: base(g),
        "+ dummy": lambda g: base(g) + ["d_dummy"],
        "+ D x production (adopted)": lambda g: PV.cols_for(g, "main"),
        "+ both": lambda g: PV.cols_for(g, "main") + ["d_dummy"]}
ADOPTED = "+ D x production (adopted)"
log(f"\n  {len(prow):,} skater prospect-seasons, {prow[['draftYear', 'pick']].drop_duplicates().shape[0]:,} players; "
    f"defencemen in {int(prow['d_dummy'].sum()):,} of the rows")


def design(frame, cols_by_group):
    gv = frame["k_group"].astype(str).values
    cols, names = [], []
    for g in GROUPS:
        on = gv == g
        for c in cols_by_group[g]:
            cols.append(np.where(on, frame[c].values.astype(float), 0.0))
            names.append(f"{c}:{LABEL[g]}")
    return np.column_stack(cols), names


def wald(m, names, added):
    idx = [names.index(n) for n in added]
    b, V = m.params[idx], m.cov_params()[np.ix_(idx, idx)]
    W = float(b @ np.linalg.solve(V, b))
    return W, len(idx), float(stats.chi2.sf(W, len(idx)))


def heldout(X, y, years):
    e = np.full(len(y), np.nan)
    for c in sorted(set(years)):
        tr, te = years != c, years == c
        e[te] = y[te] - X[te] @ np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]
    return e


y = prow["remaining_M"].values.astype(float)
yrs = prow["draftYear"].values
cls = sorted(set(yrs))
rng = np.random.default_rng(SEED)
cnt = np.array([[int((dr == c).sum()) for c in cls] for dr in
                [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]])


def p_lower(e1, e2):
    s1 = pd.Series(e1 ** 2).groupby(yrs).sum().reindex(cls).values
    s2 = pd.Series(e2 ** 2).groupby(yrs).sum().reindex(cls).values
    return 1.0 - float(np.mean(cnt @ s1 < cnt @ s2))


FITS, E, rows, coefs = {}, {}, [], []
for arm, fn in ARMS.items():
    cb = {g: fn(g) for g in GROUPS}
    res, m = PV.fit_stacked(prow, cb)                     # the model's own fitting function
    X, names = design(prow, cb)
    assert np.allclose(X @ m.params, m.fittedvalues)       # the design here is the one fit_stacked used
    FITS[arm], E[arm] = (m, names, cb), heldout(X, y, yrs)
    for i, n in enumerate(names):
        term, _, season = n.partition(":")
        coefs.append({"arm": arm, "season": season, "term": term, "coef": m.params[i], "se": m.bse[i], "p": m.pvalues[i]})

# ---- guards: the adopted arm is the model ---------------------------------------------------------------------------
m_ad, names_ad, cb_ad = FITS[ADOPTED]
for g in GROUPS:
    _, b_m, se_m = fits[("main", g, "none")]
    got = [m_ad.params[names_ad.index(f"{c}:{LABEL[g]}")] for c in cb_ad[g]]
    assert np.max(np.abs(np.array(got) - np.array(b_m))) < 1e-9, g                                            # GUARD
log("  guard: the adopted arm's coefficients equal prospect_values' fits (PASS)")
doc = json.loads(F["doc"].read_text(encoding="utf-8"))
w_def = wald(m_ad, names_ad, [n for n in names_ad if n.startswith("d_x_prod:")])
assert abs(w_def[0] - doc["tests"]["def"]["chi2"]) < 1e-6, (w_def, doc["tests"]["def"])                       # GUARD
log(f"  guard: the adopted arm's defenceman x production test reproduces the recorded chi2 {doc['tests']['def']['chi2']:.4f} (PASS)")

# ---- the scores -----------------------------------------------------------------------------------------------------
log("\n  THE ARMS (Wald tests chi2, clustered by player; R-squared from zero; held-out error in $M)")
log(f"  {'arm':<28}{'terms':>6}{'R-squared':>10}{'held-out':>10}{'p held-out':>11}   added terms all zero")
for arm in ARMS:
    m, names, _ = FITS[arm]
    r2 = 1.0 - float(m.resid @ m.resid) / float(y @ y)
    rm = float(np.sqrt(np.mean(E[arm] ** 2)))
    rec = {"arm": arm, "terms": len(names), "r2_from_zero": r2, "rmse_heldout_M": rm}
    txt = ""
    dums = [n for n in names if n.startswith("d_dummy:")]
    dxp = [n for n in names if n.startswith("d_x_prod:")]
    if arm == "+ dummy":
        rec["wald_dummy"] = wald(m, names, dums); txt = "dummy: chi2({1}) = {0:.2f}, p = {2:.4f}".format(*rec["wald_dummy"])
    if arm == ADOPTED:
        rec["wald_dxp"] = wald(m, names, dxp); txt = "D x production: chi2({1}) = {0:.2f}, p = {2:.4f}".format(*rec["wald_dxp"])
    if arm == "+ both":
        rec["wald_both"] = wald(m, names, dums + dxp)
        rec["wald_dummy_given_dxp"] = wald(m, names, dums)
        rec["wald_dxp_given_dummy"] = wald(m, names, dxp)
        txt = ("both: chi2({1}) = {0:.2f}, p = {2:.4f}".format(*rec["wald_both"])
               + "; dummy given D x production: chi2({1}) = {0:.2f}, p = {2:.4f}".format(*rec["wald_dummy_given_dxp"])
               + "; D x production given dummy: chi2({1}) = {0:.2f}, p = {2:.4f}".format(*rec["wald_dxp_given_dummy"]))
    if arm != ADOPTED:
        rec["p_heldout_better_than_adopted"] = p_lower(E[arm], E[ADOPTED])
    rows.append(rec)
    log(f"  {arm:<28}{len(names):>6}{r2:>10.4f}{rm:>10.4f}"
        + (f"{rec['p_heldout_better_than_adopted']:>11.4f}" if arm != ADOPTED else f"{'':>11}") + "   " + txt)
log("  (p held-out: the share of 2,000 redraws of the drafts in which the arm's held-out error is NOT below the adopted")
log("  model's; below 0.05 means the arm predicts left-out drafts better than the adopted model, at the 5% level)")
log(f"  the dummy arm against no defenceman term, held out: p = {p_lower(E['+ dummy'], E['no defenceman term']):.4f}; "
    f"the adopted arm against no defenceman term: p = {p_lower(E[ADOPTED], E['no defenceman term']):.4f}")

log("\n  THE DEFENCEMAN TERMS BY SEASON ($M; clustered standard error; two-sided p)")
for arm in ("+ dummy", ADOPTED, "+ both"):
    m, names, _ = FITS[arm]
    log(f"  {arm}")
    for g in GROUPS:
        parts = [f"{n.split(':')[0]} {m.params[i]:+.4f} ({m.bse[i]:.4f}) p={m.pvalues[i]:.3f}"
                 for i, n in enumerate(names) if n.split(":")[0] in ("d_dummy", "d_x_prod") and n.endswith(":" + LABEL[g])]
        log(f"    {LABEL[g]}: " + "; ".join(parts))

# ---- a defenceman against a forward with the same inputs -------------------------------------------------------------
s15 = float(pd.read_csv(F["slots"]).set_index("draft_pick").loc[15, "p_star"])
log("\n  A DEFENCEMAN LESS A FORWARD WITH THE SAME INPUTS ($M; a 15th pick; 0 and 20 points per 82)")
econ = []
for arm in ARMS:
    m, names, cb = FITS[arm]
    cells = []
    for g in GROUPS:
        for q in (0, 10, 20):
            def val(dm):
                # prod_x_age is production x years past first eligibility (the model's stored form), here 0.5 years,
                # as defence_terms_look.py; the defenceman less forward difference does not depend on it
                row = pd.DataFrame({"k_group": [g], "p_star": [s15], "nhle82": [float(q)], "nhle82_sq": [float(q) ** 2],
                                    "prod_x_age": [q * 0.5], "d_x_prod": [q * dm], "d_dummy": [dm]})
                X, _ = design(row, cb)
                return float(X[0] @ m.params)
            diff = val(1.0) - val(0.0)
            econ.append({"arm": arm, "season": LABEL[g], "points_per_82": q, "forward_M": val(0.0), "difference_M": diff})
            if q in (0, 20):
                cells.append(f"{LABEL[g]} {q}pts {diff:+.2f}")
    log(f"  {arm:<28}" + "  ".join(cells))

# ---- the traded prospects -------------------------------------------------------------------------------------------
pv = pd.read_csv(F["values"])
prod = pv["value_basis"].isin(["production", "slot + production", "production (undrafted, slot at zero)"])
t = pv[prod].copy().reset_index(drop=True)
assert t["is_d_model"].notna().all()
t["p_star"] = t["p_star"].fillna(0.0)
t["nhle82_sq"] = t["nhle82"] ** 2
t["prod_x_age"] = t["nhle82"] * t["past_elig"]
t["d_dummy"] = t["is_d_model"].astype(float)
t["d_x_prod"] = t["nhle82"] * t["d_dummy"]
t["k_group"] = t["k_group"].astype(str)
fixed = pv[pv["value_basis"].str.startswith("slot alone")]["value_M"].sum()
log(f"\n  THE TRADED PROSPECTS valued on production: {len(t)} ({int((t['draftYear'].notna()).sum())} drafted, "
    f"{int(t['draftYear'].isna().sum())} undrafted; {int(t['d_dummy'].sum())} defencemen); goaltenders on draft position "
    f"alone ${fixed:.2f}M, the same in every arm")
V = {}
for arm in ARMS:
    m, _, cb = FITS[arm]
    X, _ = design(t, cb)
    V[arm] = X @ m.params
gap = float(np.max(np.abs(V[ADOPTED] - t["value_M"].values)))
assert gap < 1e-6, gap                                                                                        # GUARD
log(f"  guard: the adopted arm reproduces value_M (largest gap {gap:.1e}) (PASS)")
dr = t["draftYear"].notna().values
for arm, v in V.items():
    mv = v - t["value_M"].values
    i = int(np.argmax(np.abs(mv)))
    r_ = t.iloc[i]
    rows[[r["arm"] for r in rows].index(arm)].update({"traded_drafted_M": float(v[dr].sum()),
                                                      "traded_undrafted_M": float(v[~dr].sum())})
    log(f"  {arm:<28} drafted ${v[dr].sum():.2f}M ({v[dr].sum() - t.loc[dr, 'value_M'].sum():+.2f}), undrafted "
        f"${v[~dr].sum():.2f}M ({v[~dr].sum() - t.loc[~dr, 'value_M'].sum():+.2f}); largest mover {r_['player_name']} "
        f"({'D' if r_['d_dummy'] else 'F'}, {LABEL[r_['k_group']]}, {r_['nhle82']:.1f} points) {r_['value_M']:.2f} -> {v[i]:.2f}")

rewritten = [k_ for k_, p_ in F.items() if p_.stat().st_mtime != MTIME[k_]]
assert not rewritten, rewritten                                                                               # GUARD
log("\n  guard: no input was rewritten while the test ran (PASS)")
pd.DataFrame(rows).to_csv(OUT / "defence_dummy_look.csv", index=False)
pd.DataFrame(coefs).to_csv(OUT / "defence_dummy_coefficients.csv", index=False)
(OUT / "defence_dummy_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"wrote defence_dummy_look.csv, defence_dummy_coefficients.csv and the log in {OUT}")
