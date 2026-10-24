"""
defence_terms_look.py -- is a defenceman's draft position or production worth a different amount from a forward's?
(report only)

ASKED (Thomas, 2026-10-24): "did we ever interact defenceman with star value? ... was that in the draft model?" No: the
only defence test was prospect_nhle_look.py v1.1 (2026-10-14), a separate production rate for defencemen on the model
of that date (straight-line production, no square, no age, draft-year terms, seasons past club control), and no
position term was ever tested in the pick curve. "I want you to run all those tests." The supervisor meeting of
2026-10-23 asked the document to describe the production test as "a separate regression was run using a defenceman
dummy interacted with production"; this re-runs it on the model as it now stands. Nothing in 20_CODE/ changes.

DEFENCEMAN (D = 1): the prospect rows' Elite Prospects position starting "D" (prospect_nhle_rows.csv is_d); the pick
curve's linkage position "D"; a traded prospect's position from prospect_values.csv, and for an undrafted one from
PuckPedia's contract export by NHL id.

PART 1, THE PICK CURVE (pick_curve.fit_scale: career NPV of each 2007-2017 drafted player, deceased draftees out, on
the star chance S through zero, robust HC1 errors, one row per player):
  adopted          a S
  + D x S          a S + a_D (D S): a defenceman's star chance worth a + a_D, a forward's or goaltender's a
  + D x S, G x S   a S + a_D (D S) + a_G (G S): forwards the base, each other position its own star value
  The Wald test of each added term is its statistical significance. NOTE: a pick traded before its draft has no player,
  so no position: a position term could value only picks traded after their draft (or the drafted players
  themselves), never a future pick.

PART 2, THE PROSPECT MODEL (the adopted regression, prospect_values.fit_stacked: every term its own coefficient in
each season after the draft; S in D+1 to D+3, production P and P^2 in every season, P x years past first eligibility
in D+1 to D+4; through zero; errors clustered by player), skaters only:
  adopted          as above
  + D x P          D times production, in every season (the meeting's "defenceman dummy interacted with production")
  + D x P, D x P^2 both production terms for defencemen
  + D x S          D times the star chance, D+1 to D+3
  + all three      D x S, D x P, D x P^2
  Each scored alone and together (CLAUDE.md).

MEASURES (the meeting of 2026-10-23): R-squared (centred) and adjusted R-squared; the Wald test that the added terms
are all zero (one regression, clustered by player for the prospects, HC1 for the pick curve), and each term's p by
season; economic significance: the star value or production's value for a defenceman against a forward, and the
traded prospects' totals; held-out error (supplementary): each draft predicted from a fit without it, p = the share of
2,000 redraws of the 11 drafts in which the arm's summed squared error is NOT below the adopted model's (one-sided;
seed 20261014).

GUARDS: the pick curve's adopted arm reproduces pick_curve_scales.csv's main star value to 1e-9; the prospect rows'
fingerprint; the prospect adopted arm reproduces prospect_age_form_look.py's held-out error and prospect_values.csv's
value_M to 1e-6; every traded prospect valued on production has a position; no input is rewritten while the test
runs.

TRAILING WEIGHTING CHECK (directive 6): production reads 50/30/20 (as stored); the pick curve reads realised seasons.

INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_scales.csv, prospect_nhle_rows.csv, draft_pick_linkage.csv,
prospect_age_form_look.csv, prospect_values.csv; SOURCE_DIR/PuckPedia contract export (CSV; positions of undrafted).
OUTPUTS: OUTPUT_DIR/defence_terms_look.csv, defence_terms_coefficients.csv, defence_terms_traded_summary.csv,
defence_terms_look_log.txt.
Run from the repo root:  python 25_TESTS/defence_terms_look.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "defence_terms_look.py v1.0 (2026-10-24)"
load_dotenv(Path.cwd() / ".env")
OUTPUT_DIR, SOURCE_DIR = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"players": OUTPUT_DIR / "pick_curve_players.csv", "scales": OUTPUT_DIR / "pick_curve_scales.csv",
     "rows": OUTPUT_DIR / "prospect_nhle_rows.csv", "linkage": OUTPUT_DIR / "draft_pick_linkage.csv",
     "form_scores": OUTPUT_DIR / "prospect_age_form_look.csv", "values": OUTPUT_DIR / "prospect_values.csv",
     "puckpedia": SOURCE_DIR / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.csv"}
for k_, p_ in F.items():
    log(f"  input {k_}: {p_.resolve()}  (modified {pd.Timestamp(p_.stat().st_mtime, unit='s', tz='UTC').tz_convert('America/Toronto'):%Y-%m-%d %H:%M})")
MTIME = {k_: p_.stat().st_mtime for k_, p_ in F.items()}
N_REDRAW, SEED = 2000, 20261014
GROUPS = ("0", "1", "2", "3", "4+")
EARLY = ("0", "1", "2")
AGE_GROUPS = ("0", "1", "2", "3")
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 on"}


def r2(resid, yv):
    return 1.0 - float(resid @ resid) / float(((yv - yv.mean()) ** 2).sum())


def adj(r, n, k):
    return 1 - (1 - r) * (n - 1) / (n - k)


def redraw_counts(years):
    cls = sorted(set(years))
    rng = np.random.default_rng(SEED)
    cnt = np.array([[int((dr == c).sum()) for c in cls] for dr in
                    [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]])
    return cls, cnt


def p_lower(e1, e2, years, cls, cnt):
    s1 = pd.Series(e1 ** 2).groupby(years).sum().reindex(cls).values
    s2 = pd.Series(e2 ** 2).groupby(years).sum().reindex(cls).values
    return 1.0 - float(np.mean(cnt @ s1 < cnt @ s2))


def heldout(X, y, years):
    e = np.full(len(y), np.nan)
    for c in sorted(set(years)):
        tr, te = years != c, years == c
        b = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]
        e[te] = y[te] - X[te] @ b
    return e


def wald(m, names, added):
    idx = [names.index(n_) for n_ in added]
    R = np.zeros((len(idx), len(names)))
    for j, i in enumerate(idx):
        R[j, i] = 1.0
    w = m.wald_test(R, use_f=False, scalar=True)
    return float(w.statistic), len(idx), float(w.pvalue)


scores, coefs = [], []

# =============================================== PART 1: THE PICK CURVE ===========================================
pc = pd.read_csv(F["players"])
pc = pc[~pc["excluded_deceased"].astype(bool)].reset_index(drop=True)
pc["D"] = (pc["position"].astype(str) == "D").astype(float)
pc["G"] = pc["is_goalie"].astype(bool).astype(float)
assert not ((pc["D"] == 1) & (pc["G"] == 1)).any()
y_pc = pc["surplus"].values / 1e6
S_pc = pc["p_star"].values.astype(float)
yrs_pc = pc["draftYear"].values
PC_ARMS = {"adopted": ([S_pc], ["S"]),
           "+ D x S": ([S_pc, S_pc * pc["D"].values], ["S", "D x S"]),
           "+ D x S, G x S": ([S_pc, S_pc * pc["D"].values, S_pc * pc["G"].values], ["S", "D x S", "G x S"])}
log(f"\nPART 1: THE PICK CURVE ({len(pc):,} drafted players 2007-2017, deceased draftees out: "
    f"{int(pc['D'].sum())} defencemen, {int(pc['G'].sum())} goaltenders, {int(len(pc) - pc['D'].sum() - pc['G'].sum())} "
    "forwards; outcome career NPV, $M at the 2025-26 cap)")
cls_pc, cnt_pc = redraw_counts(yrs_pc)
E_pc = {}
for arm, (cols, names) in PC_ARMS.items():
    X = np.column_stack(cols)
    m = sm.OLS(y_pc, X).fit(cov_type="HC1")
    E_pc[arm] = heldout(X, y_pc, yrs_pc)
    rr = r2(m.resid, y_pc)
    rec = {"part": "pick curve", "arm": arm, "coefficients": len(names), "rows": len(pc), "r2": rr,
           "adj_r2": adj(rr, len(pc), len(names)), "rmse_heldout_M": float(np.sqrt(np.mean(E_pc[arm] ** 2)))}
    if arm != "adopted":
        rec["wald_chi2"], rec["wald_df"], rec["wald_p"] = wald(m, names, names[1:])
        rec["p_heldout_vs_adopted"] = p_lower(E_pc[arm], E_pc["adopted"], yrs_pc, cls_pc, cnt_pc)
    scores.append(rec)
    for i, n_ in enumerate(names):
        coefs.append({"part": "pick curve", "arm": arm, "season": "career", "term": n_, "coef": m.params[i],
                      "se": m.bse[i], "p": m.pvalues[i]})
    if arm == "adopted":
        ref = pd.read_csv(F["scales"]).set_index("scale_kind").loc["main", "scale_M"]
        assert abs(m.params[0] - ref) < 1e-9, (m.params[0], ref)                                          # GUARD
        log(f"  guard: the adopted arm reproduces pick_curve_scales.csv's star value {ref:.4f} (PASS)")
    sv = {"forward": m.params[0]}
    if "D x S" in names:
        sv["defenceman"] = m.params[0] + m.params[names.index("D x S")]
    if "G x S" in names:
        sv["goaltender"] = m.params[0] + m.params[names.index("G x S")]
    log(f"  {arm:<16} R-squared {rr:.4f}, adjusted {rec['adj_r2']:.4f}; held-out {rec['rmse_heldout_M']:.4f}"
        + ("" if arm == "adopted" else f" (p = {rec['p_heldout_vs_adopted']:.4f}); added terms: chi2({rec['wald_df']}) = "
           f"{rec['wald_chi2']:.2f}, p = {rec['wald_p']:.4f}"))
    log("  " + " " * 16 + " " + "; ".join(f"{n_} {m.params[i]:.3f} (se {m.bse[i]:.3f}, p = {m.pvalues[i]:.3f})"
                                          for i, n_ in enumerate(names))
        + "   star value: " + ", ".join(f"{k} ${v:.2f}M" for k, v in sv.items()))

# =============================================== PART 2: THE PROSPECT MODEL =======================================
d = pd.read_csv(F["rows"], dtype={"k_group": str})
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left").reset_index(drop=True)
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "1a0aa6bb93a0", FP                                                                              # GUARD
assert d["is_d"].isin([0.0, 1.0]).all()
age = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
A_ = (age - d["k"] - 18.0).values
G = d["k_group"].astype(str).values
S_ = d["p_star"].values.astype(float)
P_ = d["nhle82"].values.astype(float)
D_ = d["is_d"].values.astype(float)
y = d["remaining_M"].values.astype(float)
yrs = d["draftYear"].values
players = pd.factorize(d["draftYear"].astype(str) + "-" + d["pick"].astype(str))[0]
PR_ARMS = {"adopted": (False, False, False), "+ D x P": (True, False, False),
           "+ D x P, D x P^2": (True, True, False), "+ D x S": (False, False, True),
           "+ D x S, D x P, D x P^2": (True, True, True)}


def design(g_, S, P, A, Dm, arm):
    dp, dp2, ds = PR_ARMS[arm]
    cols, names = [], []
    for g in GROUPS:
        on = g_ == g
        if g in EARLY:
            cols.append(np.where(on, S, 0.0)); names.append(f"S:{LABEL[g]}")
            if ds:
                cols.append(np.where(on, Dm * S, 0.0)); names.append(f"D x S:{LABEL[g]}")
        cols += [np.where(on, P, 0.0), np.where(on, P * P, 0.0)]
        names += [f"P:{LABEL[g]}", f"P^2:{LABEL[g]}"]
        if dp:
            cols.append(np.where(on, Dm * P, 0.0)); names.append(f"D x P:{LABEL[g]}")
        if dp2:
            cols.append(np.where(on, Dm * P * P, 0.0)); names.append(f"D x P^2:{LABEL[g]}")
        if g in AGE_GROUPS:
            cols.append(np.where(on, P * A, 0.0)); names.append(f"P x age:{LABEL[g]}")
    return np.column_stack(cols), names


log(f"\nPART 2: THE PROSPECT MODEL ({len(d):,} skater prospect-seasons, {d[['draftYear', 'pick']].drop_duplicates().shape[0]:,} "
    f"skaters, {int(D_.sum()):,} of the rows defencemen; fingerprint {FP}; outcome remaining NPV, $M)")
cls_pr, cnt_pr = redraw_counts(yrs)
early = np.isin(G, AGE_GROUPS)
FITS, E_pr = {}, {}
for arm in PR_ARMS:
    X, names = design(G, S_, P_, A_, D_, arm)
    m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": players})
    FITS[arm] = (m, names)
    E_pr[arm] = heldout(X, y, yrs)
    rr = r2(m.resid, y)
    rec = {"part": "prospect model", "arm": arm, "coefficients": len(names), "rows": len(d), "r2": rr,
           "adj_r2": adj(rr, len(d), len(names)), "r2_D1_D4": r2(m.resid[early], y[early]),
           "rmse_heldout_M": float(np.sqrt(np.mean(E_pr[arm] ** 2)))}
    added = [n_ for n_ in names if n_.startswith("D x")]
    if added:
        rec["wald_chi2"], rec["wald_df"], rec["wald_p"] = wald(m, names, added)
        rec["p_heldout_vs_adopted"] = p_lower(E_pr[arm], E_pr["adopted"], yrs, cls_pr, cnt_pr)
        for stem in ("D x S", "D x P", "D x P^2"):
            part = [n_ for n_ in added if n_.startswith(stem + ":")]
            if part and len(part) < len(added):
                rec[f"wald_p_{stem}"] = wald(m, names, part)[2]
    scores.append(rec)
    for i, n_ in enumerate(names):
        term, _, season = n_.partition(":")
        coefs.append({"part": "prospect model", "arm": arm, "season": season, "term": term, "coef": m.params[i],
                      "se": m.bse[i], "p": m.pvalues[i]})
rm_ad = float(np.sqrt(np.mean(E_pr["adopted"] ** 2)))
ref = pd.read_csv(F["form_scores"])
ref = ref[ref["centre"] == 18.0].set_index("arm").loc["production x age (adopted)", "rmse_M"]
assert abs(rm_ad - ref) < 1e-6, (rm_ad, ref)                                                                # GUARD
log(f"  guard: the adopted arm reproduces prospect_age_form_look.py's held-out error {ref:.4f} (PASS)")
S_df = pd.DataFrame(scores)
log(f"  {'arm':<26}{'coef.':>6}{'R-squared':>10}{'adjusted':>9}{'D+1-D+4':>9}{'held-out':>9}{'p held-out':>11}"
    f"   added terms all zero (Wald)")
for _, r in S_df[S_df["part"] == "prospect model"].iterrows():
    extra = "" if r["arm"] == "adopted" else f"chi2({int(r['wald_df'])}) = {r['wald_chi2']:.2f}, p = {r['wald_p']:.4f}"
    for stem in ("D x S", "D x P", "D x P^2"):
        v = r.get(f"wald_p_{stem}", np.nan)
        if pd.notna(v):
            extra += f"; {stem} terms alone in it p = {v:.4f}"
    log(f"  {r['arm']:<26}{int(r['coefficients']):>6}{r['r2']:>10.4f}{r['adj_r2']:>9.4f}{r['r2_D1_D4']:>9.4f}"
        f"{r['rmse_heldout_M']:>9.4f}"
        + (f"{r['p_heldout_vs_adopted']:>11.4f}" if r["arm"] != "adopted" else f"{'':>11}") + "   " + extra)
log("  (p held-out: the share of redraws in which the arm's held-out error is NOT below the adopted model's; below 0.05")
log("  means the arm predicts left-out drafts better, statistically significant at the 5% level)")

log("\n  THE DEFENCE TERMS BY SEASON ($M; standard errors clustered by player; p two-sided)")
for arm in PR_ARMS:
    if arm == "adopted":
        continue
    m, names = FITS[arm]
    log(f"  {arm}")
    for g in GROUPS:
        parts = [f"{n_.split(':')[0]} {m.params[i]:+.4f} ({m.bse[i]:.4f}) p={m.pvalues[i]:.3f}"
                 for i, n_ in enumerate(names) if n_.startswith("D x") and n_.endswith(":" + LABEL[g])]
        if parts:
            log(f"    {LABEL[g]}: " + "; ".join(parts))

# ---- economic: a defenceman against a forward with the same inputs ------------------------------------------
log("\n  A DEFENCEMAN AGAINST A FORWARD WITH THE SAME INPUTS ($M: the defenceman's value less the forward's; a 15th")
log("  pick's star chance, 0.5 years past first eligibility)")
base = pd.read_csv(SOURCE_DIR / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
s15 = float(base.loc[15])
econ = []
for arm in PR_ARMS:
    if arm == "adopted":
        continue
    m, names = FITS[arm]
    cells = []
    for g in GROUPS:
        for q in (10, 20):
            one = lambda dm: float(design(np.array([g]), np.array([s15 if g in EARLY else 0.0]), np.array([float(q)]),
                                          np.array([0.5]), np.array([dm]), arm)[0][0] @ m.params)
            diff = one(1.0) - one(0.0)
            econ.append({"arm": arm, "season": LABEL[g], "points_per_82": q, "forward_M": one(0.0),
                         "defenceman_M": one(1.0), "difference_M": diff})
            cells.append(f"{LABEL[g]} {q}pts {diff:+.2f} (F {one(0.0):.2f})")
    log(f"  {arm:<26}" + "  ".join(cells))

# ---- the traded prospects ------------------------------------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)"])
prod = valued & pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[prod].copy()
import sys
sys.path.insert(0, str(Path.cwd() / "20_CODE"))
from contract_source import read_csv_detect                     # the export's encoding, detected as the model does
pp = read_csv_detect(F["puckpedia"])[0][["nhl_id", "position"]].dropna().drop_duplicates("nhl_id")
pp_pos = dict(zip(pp["nhl_id"].astype(int), pp["position"].astype(str)))
pos = t["position"].copy()
miss = pos.isna() & t["nhl_id_undrafted"].notna()
pos[miss] = t.loc[miss, "nhl_id_undrafted"].astype(int).map(pp_pos)
assert pos.notna().all(), t.loc[pos.isna(), "player_name"].tolist()                                          # GUARD
t["D"] = pos.astype(str).str.startswith("D").astype(float)
tg = t["k_group"].astype(str).values
fixed = pv[valued & ~prod]
drafted, fixed_d = t["draftYear"].notna(), fixed["draftYear"].notna()
n_dr = int(drafted.sum()) + int(fixed_d.sum())
V = {}
for arm in PR_ARMS:
    m, _ = FITS[arm]
    X, _ = design(tg, t["p_star"].fillna(0.0).values, t["nhle82"].values.astype(float), t["past_elig"].values,
                  t["D"].values, arm)
    V[arm] = pd.Series(X @ m.params, index=t.index)
gap_v = float((V["adopted"] - t["value_M"]).abs().max())
assert gap_v < 1e-6, gap_v                                                                                   # GUARD
base_d = t.loc[drafted, "value_M"].sum() + fixed.loc[fixed_d, "value_M"].sum()
base_u = t.loc[~drafted, "value_M"].sum()
log(f"\n  THE TRADED PROSPECTS (guard: the adopted arm reproduces value_M, largest gap {gap_v:.1e} (PASS)); {n_dr} drafted "
    f"({int(fixed_d.sum())} goaltenders on draft position alone, the same in every arm), {int((~drafted).sum())} undrafted "
    f"(positions from PuckPedia for {int(miss.sum())}); defencemen among those valued on production: "
    f"{int(t.loc[drafted, 'D'].sum())} drafted, {int(t.loc[~drafted, 'D'].sum())} undrafted")
log(f"  {'arm':<26}{'drafted':>9}{'change':>8}{'moved $0.25M+':>15}{'undrafted':>11}{'change':>8}   largest mover")
trd = []
for arm, v in V.items():
    tot_d = v[drafted].sum() + fixed.loc[fixed_d, "value_M"].sum()
    tot_u = v[~drafted].sum()
    mv = v - t["value_M"]
    i = mv.abs().idxmax()
    r_ = t.loc[i]
    big = (f"{r_['player_name']} ({r_['trade_date']}, {LABEL[str(r_['k_group'])]}, {'D' if r_['D'] else 'F'}, "
           f"{r_['nhle82']:.1f} points) ${r_['value_M']:.2f}M -> ${v[i]:.2f}M")
    n_mv = int((mv[drafted].abs() >= 0.25).sum())
    log(f"  {arm:<26}{tot_d:>9.2f}{tot_d - base_d:>+8.2f}{n_mv:>9} of {n_dr:<3}{tot_u:>11.2f}{tot_u - base_u:>+8.2f}   "
        f"{big if arm != 'adopted' else '-'}")
    trd.append({"arm": arm, "drafted_total_M": tot_d, "drafted_change_M": tot_d - base_d, "drafted_moved_025": n_mv,
                "undrafted_total_M": tot_u, "undrafted_change_M": tot_u - base_u, "largest_mover": big})

rewritten = [k_ for k_, p_ in F.items() if p_.stat().st_mtime != MTIME[k_]]
assert not rewritten, f"inputs rewritten while the test ran: {rewritten}"                                     # GUARD
log("\n  guard: no input was rewritten while the test ran (PASS)")
S_df.to_csv(OUTPUT_DIR / "defence_terms_look.csv", index=False)
pd.DataFrame(coefs).to_csv(OUTPUT_DIR / "defence_terms_coefficients.csv", index=False)
pd.DataFrame(econ).to_csv(OUTPUT_DIR / "defence_terms_economic.csv", index=False)
pd.DataFrame(trd).to_csv(OUTPUT_DIR / "defence_terms_traded_summary.csv", index=False)
(OUTPUT_DIR / "defence_terms_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote defence_terms_look.csv, _coefficients.csv, _economic.csv, _traded_summary.csv and the log in {OUTPUT_DIR}")
