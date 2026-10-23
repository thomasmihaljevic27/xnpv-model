"""
prospect_fade_rules.py -- how should the slot's value fade while a player stays a prospect? (report only)

ASKED (Thomas, 2026-10-15, on "Valuing Prospects" Section 1 and Figure 1): show the rejected simple rules against the
data and the adopted one, including the single interaction term ("star chance x seasons since the draft") the
supervisor raised. The document rejects two rules by reading Table 1; neither was fitted or scored. This fits and
scores all of them on the same rows.

THE RULES (each one regression on all prospect-rows; only the path of the star value across seasons differs):
  separate        one star value for each season group: D+1, D+2, D+3, D+4, D+5 and later (ADOPTED; Table 1)
  no fade         one star value for every season (the draft-day value kept)
  straight line   star value = s0 + s1 x k (one interaction term: star chance x seasons since the draft)
  same percentage star value = s0 x r^k (the value keeps the same share r of itself each season; r found by search)
k = seasons since the draft, 0 for D+1 (the code's count; the document's D+(k+1)), 0 to 7 in the rows.
Each rule keeps the adopted fits' draft-year levels: one set for each season group, through zero, summing to zero
within the group, so the rules differ only in the star value. The adopted rule written this way IS the separate
fits (same coefficients; asserted). Errors clustered by player (a player appears in several seasons).
A fifth line, "straight line, one set of draft levels", is the version run in chat on 2026-10-15 (18.87 - 2.86 a
season); it is reported for the record only.

SCORING: the document's rule. Held-out error: each draft predicted from a fit without it (the same-percentage rule
searches r again without that draft), at the average draft. Then 2,000 redraws of the eleven drafts (seed as the
prospect looks), counting the redraws in which the adopted rule's summed squared error is below each other rule's.

GUARD: the adopted rule's star values reproduce prospect_star_values.csv (prospect_values.py) to 1e-9.

INPUTS: OUTPUT_DIR/prospect_slot_years_rows.csv (prospect_slot_years_check.py), prospect_star_values.csv.
OUTPUTS: OUTPUT_DIR/prospect_fade_rules.csv (each rule's star value by season, for the figure),
prospect_fade_rules_scores.csv, prospect_fade_rules_log.txt.
Run from the repo root:  python 25_TESTS/prospect_fade_rules.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_fade_rules.py v1.2 (2026-10-16)"   # no draft-year terms (Thomas, 2026-10-16)
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"rows": OUTPUT_DIR / "prospect_slot_years_rows.csv", "star_values": OUTPUT_DIR / "prospect_star_values.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

N_REDRAW, SEED = 2000, 20261014                  # as the prospect looks
GROUPS = ["0", "1", "2", "3", "4+"]               # season groups as prospect_values.k_group (4+ pools k = 4..7)
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 and later"}
R_GRID = np.arange(0.30, 1.0001, 0.005)          # same-percentage rule: coarse search for r, then a fine one

d = pd.read_csv(F["rows"])
d = d[d["prospect"].astype(bool)].reset_index(drop=True)
d["k_group"] = d["k"].map(lambda k: str(k) if k < 4 else "4+")
d["pid"] = pd.factorize(d["draftYear"].astype(str) + "-" + d["pick"].astype(str))[0]
log(f"\nrows: {len(d):,} prospect-rows of {d['pid'].nunique():,} drafted players (skaters and goalies), 2007-2017")


def level_cols(frame):
    """v1.2: none (no draft-year terms, Thomas 2026-10-16); v1.0-v1.1 had one sum-to-zero set per season group."""
    return []


def one_level_cols(frame):
    """v1.2: none, as level_cols (the chat version had one set for every season)."""
    return []


def star_terms(frame, rule, r=None):
    """The star-value regressors of one rule (each multiplies the slot's star chance)."""
    p, k = frame["p_star"].values, frame["k"].values.astype(float)
    if rule == "separate":
        return [p * (frame["k_group"].values == g) for g in GROUPS]
    if rule == "no fade":
        return [p]
    if rule in ("straight line", "straight line, one set of draft levels"):
        return [p, p * k]
    if rule == "same percentage":
        return [p * r ** k]
    raise ValueError(rule)


def design(frame, rule, r=None):
    lv = one_level_cols(frame) if rule == "straight line, one set of draft levels" else level_cols(frame)
    st = star_terms(frame, rule, r)
    return np.column_stack(st + lv), len(st)


def best_r(frame):
    """Same-percentage rule: the r with the least squared error (coarse grid, then a fine one around it)."""
    y = frame["remaining_M"].values

    def sse(r):
        X, _ = design(frame, "same percentage", r)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        return float(np.sum((y - X @ beta) ** 2))

    r0 = min(R_GRID, key=sse)
    fine = np.arange(max(r0 - 0.005, 0.0), min(r0 + 0.005, 1.0) + 1e-9, 0.0001)
    return float(min(fine, key=sse))


def fit(frame, rule):
    r = best_r(frame) if rule == "same percentage" else None
    X, n = design(frame, rule, r)
    m = sm.OLS(frame["remaining_M"].values, X).fit(cov_type="cluster", cov_kwds={"groups": frame["pid"].values})
    return m, n, r


def star_value(rule, params, r, k):
    """The rule's star value in season k (k = 0 is D+1)."""
    if rule == "separate":
        return params[GROUPS.index(str(k) if k < 4 else "4+")]
    if rule == "no fade":
        return params[0]
    if rule.startswith("straight line"):
        return params[0] + params[1] * k
    return params[0] * r ** k


RULES = ["separate", "no fade", "straight line", "same percentage", "straight line, one set of draft levels"]

# ---- fits on all drafts --------------------------------------------------------------------------------
fits = {rule: fit(d, rule) for rule in RULES}
sv = pd.read_csv(F["star_values"])
sv = sv[sv["left_out"].astype(str) == "none"].set_index("k_group")["star_value_M"]
m_sep = fits["separate"][0]
for i, g in enumerate(GROUPS):
    assert abs(m_sep.params[i] - sv[g]) < 1e-9, (g, m_sep.params[i], sv[g])          # GUARD
log("  guard: the adopted rule's star values reproduce prospect_star_values.csv (PASS)")

log("\nEACH RULE ON ALL DRAFTS ($M at the 2025-26 cap; se clustered by player)")
for rule in RULES:
    m, n, r = fits[rule]
    if rule == "separate":
        txt = "; ".join(f"{LABEL[g]} {m.params[i]:.2f} ({m.bse[i]:.2f})" for i, g in enumerate(GROUPS))
    elif rule == "no fade":
        txt = f"{m.params[0]:.2f} ({m.bse[0]:.2f}) in every season"
    elif rule.startswith("straight line"):
        txt = (f"{m.params[0]:.2f} ({m.bse[0]:.2f}) {m.params[1]:+.2f} ({m.bse[1]:.2f}) a season; "
               f"falls below zero from D+{int(np.floor(-m.params[0] / m.params[1])) + 2}" if m.params[1] < 0 else "")
    else:
        txt = (f"{m.params[0]:.2f} ({m.bse[0]:.2f}) x {r:.4f}^k: keeps {r:.1%} of itself each season "
               f"(se of the level given r)")
    log(f"  {rule:<40} {txt}")

curve = []
for k in range(0, 8):
    row = {"k": k, "season": f"D+{k + 1}"}
    for rule in RULES:
        m, n, r = fits[rule]
        row[rule] = star_value(rule, m.params, r, k)
    row["prospect_rows"] = int((d["k"] == k).sum())
    curve.append(row)
curve = pd.DataFrame(curve)
log("\nSTAR VALUE BY SEASON UNDER EACH RULE ($M)")
log("  " + f"{'season':<7}" + "".join(f"{x[:16]:>18}" for x in RULES) + f"{'rows':>8}")
for _, row in curve.iterrows():
    log("  " + f"{row['season']:<7}" + "".join(f"{row[rule]:>18.2f}" for rule in RULES)
        + f"{int(row['prospect_rows']):>8,}")

# ---- held-out error and redraws ---------------------------------------------------------------------
err = {rule: np.zeros(len(d)) for rule in RULES}
for c in sorted(d["draftYear"].unique()):
    tr, te = d[d["draftYear"] != c], d[d["draftYear"] == c]
    for rule in RULES:
        m, n, r = fit(tr, rule)
        pred = np.array([star_value(rule, m.params, r, k) for k in te["k"].values]) * te["p_star"].values
        err[rule][te.index] = te["remaining_M"].values - pred

cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
draws = [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]
sse = {rule: pd.Series(err[rule] ** 2).groupby(d["draftYear"].values).sum() for rule in RULES}


def rmse(e, idx=None):
    return float(np.sqrt(np.mean((e if idx is None else e[idx]) ** 2)))


log("\nHELD-OUT ERROR ($M of remaining surplus per prospect-season; lower is better; same rows for every rule)")
scores = []
for rule in RULES:
    w = None if rule == "separate" else int(sum(sse["separate"][list(dr)].sum() < sse[rule][list(dr)].sum()
                                                 for dr in draws))
    by = {LABEL[g]: rmse(err[rule], x.index) for g, x in d.groupby("k_group")}
    log(f"  {rule:<40} {rmse(err[rule]):.4f}  " + ", ".join(f"{s} {v:.4f}" for s, v in by.items())
        + ("" if w is None else f"  | the adopted rule lower in {w:,} of {N_REDRAW:,} redraws (one-sided p = "
                                f"{1 - w / N_REDRAW:.4f})"))
    scores.append({"rule": rule, "rmse_M": rmse(err[rule]), **by, "redraws_adopted_lower": w, "rows": len(d)})

# ---- is the decline from D+1 to D+4 a straight line? (in-sample test on the adopted fit) -----------------
# The four seasons D+1..D+4 are equally spaced, so a straight decline means equal steps: the D+1->D+2 drop equals
# the D+2->D+3 drop equals the D+3->D+4 drop (two restrictions), tested with the player-clustered covariance.
R = np.zeros((2, len(m_sep.params)))
R[0, :3] = [1, -2, 1]          # (b1 - b0) - (b2 - b1) = 0
R[1, 1:4] = [1, -2, 1]         # (b2 - b1) - (b3 - b2) = 0
wt = m_sep.wald_test(R, scalar=True)
drops = [m_sep.params[i + 1] - m_sep.params[i] for i in range(3)]
log(f"\nEQUAL STEPS FROM D+1 TO D+4? the adopted fit's drops are {drops[0]:+.2f}, {drops[1]:+.2f}, {drops[2]:+.2f} ($M); "
    f"Wald test of equal drops (2 restrictions, clustered by player): chi2 = {float(wt.statistic):.2f}, "
    f"p = {float(wt.pvalue):.4f}")
scores.append({"rule": "equal steps, D+1 to D+4 (Wald)", "chi2": float(wt.statistic), "p": float(wt.pvalue)})   # v1.1

# ---- what each rule does to the traded drafted prospects (slot alone, as Table 7's second row) -------------
pv_path = OUTPUT_DIR / "prospect_values.csv"
if pv_path.exists():
    pv = pd.read_csv(pv_path)
    # the document's 197: drafted, valued (the 8 past club control are zero under every rule and left out)
    pv = pv[pv["draftYear"].notna() & (pv["status"] == "prospect, valued")].copy()
    # value_slot_only_M = star chance x the season group's star value, or 0 past club control (kept 0 here)
    live = pv["value_slot_only_M"] != 0
    log(f"\nTHE {len(pv)} TRADED DRAFTED PROSPECTS ON THE SLOT ALONE, UNDER EACH RULE ($M; input {pv_path.name}, "
        f"modified {pd.Timestamp(pv_path.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
    for rule in RULES[:4]:
        m, n, r = fits[rule]
        new = np.where(live, pv["p_star"] * [star_value(rule, m.params, r, int(k)) for k in pv["seasons_since_draft"]], 0.0)
        scores.append({"rule": f"traded total: {rule}", "total_M": float(new.sum()), "below_zero": int((new < 0).sum())})
        log(f"  {rule:<16} total {new.sum():7.2f}   at D+5 or later: {new[pv['seasons_since_draft'].values >= 4].sum():6.2f}"
            f"   below zero: {int((new < 0).sum())}")
    assert abs(pv["value_slot_only_M"].sum() - np.where(live, pv["p_star"] * [star_value(
        "separate", m_sep.params, None, int(k)) for k in pv["seasons_since_draft"]], 0.0).sum()) < 1e-6   # GUARD
    log("  guard: the adopted rule reproduces prospect_values.csv's slot-alone total (PASS)")

curve.to_csv(OUTPUT_DIR / "prospect_fade_rules.csv", index=False)
pd.DataFrame(scores).to_csv(OUTPUT_DIR / "prospect_fade_rules_scores.csv", index=False)
(OUTPUT_DIR / "prospect_fade_rules_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_fade_rules.csv, prospect_fade_rules_scores.csv and the log in {OUTPUT_DIR}")
