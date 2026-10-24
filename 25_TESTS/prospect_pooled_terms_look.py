"""
prospect_pooled_terms_look.py -- does each prospect term need its own coefficient in each season after the draft?
(report only)

ASKED (Thomas, 2026-10-24, from a question of the supervisor's): the adopted prospect model gives every term its own
coefficient in each season after the draft (a full set of interaction terms with the season: prospect_values.cols_for
and fit_stacked). Thomas had understood only the star chance to vary by season. "You might as well run a test. Not
necessarily bad if each term is interacted though as long as it performs best." Nothing in 20_CODE/ or
MODEL_DIRECTIVES.md changes; Thomas decides.

THE ARMS (one regression on every prospect-season, through zero, no draft-year terms, as prospect_values.fit_stacked;
S = the star chance for his draft position, D+1 to D+3 only, its own coefficient in each season in EVERY arm; P = NHL-
equivalent points per 82, 50/30/20 over the three seasons before; age = years past first eligibility, the production x
age term in D+1 to D+4 only, as adopted):
  adopted (all interacted)        P and P^2 their own b and c in each of D+1, D+2, D+3, D+4, D+5-on; P x age its own e
                                  in each of D+1 to D+4. 17 coefficients.
  production pooled               one b and one c across every season; P x age by season. 9 coefficients.
  age pooled                      P and P^2 by season; one e across D+1 to D+4. 14 coefficients.
  production and age pooled       one b, one c, one e: only the star chance varies by season (Thomas's reading).
                                  6 coefficients.
  Each pooling is scored alone and together (CLAUDE.md: don't credit a multi-part change to one of its parts).

MEASURES (the meeting of 2026-10-23: R-squared, statistical significance and economic significance first; held-out
error supplementary):
  R-squared        centred (about the outcome's mean) and adjusted for the number of coefficients, on all rows and on
                   D+1 to D+4; the uncentred one (Stata's "regress ..., noconstant") beside. The arms are nested in the
                   adopted model, so R-squared can only fall when coefficients are pooled; adjusted R-squared charges
                   for the coefficients.
  significance     a Wald test, in the adopted regression (errors clustered by player, as fit_stacked), that the
                   pooled coefficients are equal across seasons: the test of each pooling.
  economic         the traded drafted prospects' total under each arm, and production's value at 10 and 20 points per
                   82 by season.
  held-out         (supplementary) each draft predicted from a fit without it; p = the share of 2,000 redraws of the
                   11 drafts in which the arm's summed squared error is NOT below the adopted model's (one-sided; seed
                   20261014, prospect_age_look.py's redraws).

THE AGE MEASURE CHECK (CLAUDE.md: a verdict must not hang on a choice that leaves the adopted model unchanged). In the
adopted model, years past first eligibility (age - k - 18, what prospect_values stores) and age less 18 (what the
document writes) give the same fit: within a season they differ by k x P, which that season's own production
coefficient absorbs; a centre of 18.5 instead of 18 differs by 0.5 x P, absorbed the same way. Once production is
pooled across seasons, neither is absorbed. The pooled-production arms are run all three ways and each verdict is
checked across them.

GUARDS: the rows' fingerprint (prospect_age_look.py's rows); the adopted arm reproduces prospect_age_form_look.py's
held-out error to 1e-6 and prospect_values.csv's value_M for the traded prospects to 1e-6; the adopted arm is the same
under all three age measures; no input is rewritten while the test runs.

TRAILING WEIGHTING CHECK (directive 6): production reads 50/30/20 (as stored in the rows and in prospect_values.csv);
age reads no trailing seasons.

INPUTS: OUTPUT_DIR/prospect_nhle_rows.csv, draft_pick_linkage.csv, prospect_age_form_look.csv, prospect_values.csv.
OUTPUTS: OUTPUT_DIR/prospect_pooled_terms_look.csv, prospect_pooled_terms_coefficients.csv,
prospect_pooled_terms_traded_summary.csv, prospect_pooled_terms_look_log.txt.
Run from the repo root:  python 25_TESTS/prospect_pooled_terms_look.py
"""

import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "prospect_pooled_terms_look.py v1.0 (2026-10-24)"
load_dotenv(Path.cwd() / ".env")
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
MTIME = {k_: p_.stat().st_mtime for k_, p_ in F.items()}

N_REDRAW, SEED = 2000, 20261014
GROUPS = ("0", "1", "2", "3", "4+")
EARLY = ("0", "1", "2")                # the star chance: D+1 to D+3 (decided 2026-10-14)
AGE_GROUPS = ("0", "1", "2", "3")      # the age term: D+1 to D+4 (decided 2026-10-14)
LABEL = {"0": "D+1", "1": "D+2", "2": "D+3", "3": "D+4", "4+": "D+5 on"}
ARMS = {"adopted": "adopted (all interacted)", "pool_prod": "production pooled", "pool_age": "age pooled",
        "pool_both": "production and age pooled"}
POOL = {"adopted": (False, False), "pool_prod": (True, False), "pool_age": (False, True), "pool_both": (True, True)}
AGE_MEASURES = {"ype18": "years past first eligibility (age - k - 18)",
                "ype185": "years past first eligibility, centred at 18.5",
                "agem18": "age less 18 (the document's)"}

# ---- the rows --------------------------------------------------------------------------------------------------
d = pd.read_csv(F["rows"], dtype={"k_group": str})
link = pd.read_csv(F["linkage"], parse_dates=["birthDate"])[["draftYear", "overallPickNumber", "birthDate"]]
d = d.merge(link.rename(columns={"overallPickNumber": "pick"}), on=["draftYear", "pick"], how="left")
d = d.reset_index(drop=True)
assert d["birthDate"].notna().all()
FP = hashlib.sha1(pd.util.hash_pandas_object(d[["draftYear", "pick", "k"]], index=False).values).hexdigest()[:12]
assert FP == "1a0aa6bb93a0", FP                                    # GUARD: prospect_age_look.py's rows
age_sep15 = (pd.to_datetime(d["season"].astype(str) + "-09-15") - d["birthDate"]).dt.days / 365.25
AGE = {"ype18": (age_sep15 - d["k"] - 18.0).values, "ype185": (age_sep15 - d["k"] - 18.5).values,
       "agem18": (age_sep15 - 18.0).values}
early = d["k_group"].isin(AGE_GROUPS).values
y_all = d["remaining_M"].values.astype(float)
players = pd.factorize(d["draftYear"].astype(str) + "-" + d["pick"].astype(str))[0]
log(f"\nrows: {len(d):,} prospect-seasons, {d[['draftYear', 'pick']].drop_duplicates().shape[0]:,} skaters "
    f"(fingerprint {FP}); D+1 to D+4: {int(early.sum()):,}")


def design(frame_g, S, P, a, arm):
    """(X, names) for the stacked regression. frame_g: each row's season group (str array)."""
    pool_p, pool_a = POOL[arm]
    cols, names = [], []
    for g in EARLY:                                                  # star chance by season in every arm
        cols.append(np.where(frame_g == g, S, 0.0))
        names.append(f"S:{LABEL[g]}")
    if pool_p:
        cols += [P, P * P]
        names += ["P", "P^2"]
    else:
        for g in GROUPS:
            on = frame_g == g
            cols += [np.where(on, P, 0.0), np.where(on, P * P, 0.0)]
            names += [f"P:{LABEL[g]}", f"P^2:{LABEL[g]}"]
    in_age = np.isin(frame_g, AGE_GROUPS)
    if pool_a:
        cols.append(np.where(in_age, P * a, 0.0))
        names.append("P x age")
    else:
        for g in AGE_GROUPS:
            cols.append(np.where(frame_g == g, P * a, 0.0))
            names.append(f"P x age:{LABEL[g]}")
    return np.column_stack(cols), names


G = d["k_group"].astype(str).values
S_ = d["p_star"].values.astype(float)
P_ = d["nhle82"].values.astype(float)


def r2(sse, yv, centred=True):
    tss = float(((yv - yv.mean()) ** 2).sum()) if centred else float((yv ** 2).sum())
    return 1.0 - sse / tss


cls = sorted(d["draftYear"].unique())
rng = np.random.default_rng(SEED)
CNT = np.array([[int((dr == c).sum()) for c in cls] for dr in
                [rng.choice(cls, size=len(cls), replace=True) for _ in range(N_REDRAW)]])


def p_lower(e1, e2):
    s1 = pd.Series(e1 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    s2 = pd.Series(e2 ** 2).groupby(d["draftYear"].values).sum().reindex(cls).values
    return 1.0 - float(np.mean(CNT @ s1 < CNT @ s2))


FITS, ERR, rows_out = {}, {}, []
for am in AGE_MEASURES:
    for arm in ARMS:
        X, names = design(G, S_, P_, AGE[am], arm)
        m = sm.OLS(y_all, X).fit(cov_type="cluster", cov_kwds={"groups": players})
        e = np.full(len(d), np.nan)
        for c in cls:
            tr, te = d["draftYear"].values != c, d["draftYear"].values == c
            b = np.linalg.lstsq(X[tr], y_all[tr], rcond=None)[0]
            e[te] = y_all[te] - X[te] @ b
        FITS[(am, arm)], ERR[(am, arm)] = (m, names), e
        sse = float(m.resid @ m.resid)
        sse14 = float(m.resid[early] @ m.resid[early])
        n, k = len(d), X.shape[1]
        r_all = r2(sse, y_all)
        rows_out.append({"age_measure": am, "arm": ARMS[arm], "key": arm, "coefficients": k,
                         "r2_all": r_all, "adj_r2_all": 1 - (1 - r_all) * (n - 1) / (n - k),
                         "r2_D1_D4": r2(sse14, y_all[early]), "r2_all_uncentred": r2(sse, y_all, centred=False),
                         **{f"r2_{LABEL[g]}": r2(float(m.resid[G == g] @ m.resid[G == g]), y_all[G == g]) for g in GROUPS},
                         "rmse_heldout_M": float(np.sqrt(np.mean(e ** 2))), "rows": n, "fingerprint": FP})
S = pd.DataFrame(rows_out)

# ---- guards ----------------------------------------------------------------------------------------------------
ref = pd.read_csv(F["form_scores"])
ref = ref[(ref["centre"] == 18.0)].set_index("arm").loc["production x age (adopted)", "rmse_M"]
rm_ad = S[(S["age_measure"] == "ype18") & (S["key"] == "adopted")]["rmse_heldout_M"].iloc[0]
assert abs(rm_ad - ref) < 1e-6, (rm_ad, ref)                                                               # GUARD
ad = {am: FITS[(am, "adopted")][0].fittedvalues for am in AGE_MEASURES}
gap_am = max(float(np.max(np.abs(ad[am] - ad["ype18"]))) for am in AGE_MEASURES)
assert gap_am < 1e-8, gap_am                                                                                # GUARD
log(f"  guard: the adopted arm reproduces prospect_age_form_look.py's held-out error ({rm_ad:.4f}) and gives the same "
    f"fit under all three age measures (largest gap {gap_am:.1e}) (PASS)")

# ---- R-squared -------------------------------------------------------------------------------------------------
log("\nR-SQUARED (centred, about the outcome's mean; the outcome is remaining NPV in $M; one regression on every row)")
log(f"  {'arm':<30}{'age measure':<14}{'coef.':>6}" + "".join(f"{LABEL[g]:>9}" for g in GROUPS)
    + f"{'D+1-D+4':>9}{'all rows':>9}{'adj. all':>9}{'uncentred':>10}")
for r in S.itertuples():
    if r.key == "adopted" and r.age_measure != "ype18":
        continue
    if r.key == "pool_age" and r.age_measure != "ype18":
        continue                                         # age pooled keeps production by season: the same fit
    log(f"  {r.arm:<30}{r.age_measure:<14}{r.coefficients:>6}"
        + "".join(f"{S.loc[r.Index, 'r2_' + LABEL[g]]:>9.4f}" for g in GROUPS)
        + f"{r.r2_D1_D4:>9.4f}{r.r2_all:>9.4f}{r.adj_r2_all:>9.4f}{r.r2_all_uncentred:>10.4f}")
pa = max(float(np.max(np.abs(FITS[(am, "pool_age")][0].fittedvalues - FITS[("ype18", "pool_age")][0].fittedvalues)))
         for am in AGE_MEASURES)
log(f"  (age pooled: the same fit under all three age measures, largest gap {pa:.1e}; production by season absorbs the "
    "difference). A season's own R-squared can fall below zero under a pooled arm: its rows are fitted with")
log("  coefficients shared with other seasons, so they can fit worse than the season's mean")

# ---- the Wald tests of equal coefficients ------------------------------------------------------------------------
log("\nSIGNIFICANCE: Wald tests, in the adopted regression (errors clustered by player), that the coefficients are")
log("equal across seasons (p below 0.05: the seasons' coefficients differ, statistically significant at the 5% level)")
wald = []
for am in AGE_MEASURES:
    m, names = FITS[(am, "adopted")]
    ix = {n_: i for i, n_ in enumerate(names)}

    def eq_rows(stem, groups):
        out = []
        for g in groups[1:]:
            r = np.zeros(len(names))
            r[ix[f"{stem}:{LABEL[groups[0]]}"]] = 1.0
            r[ix[f"{stem}:{LABEL[g]}"]] = -1.0
            out.append(r)
        return out

    tests = {"P and P^2 equal across all five seasons": eq_rows("P", GROUPS) + eq_rows("P^2", GROUPS),
             "P x age equal across D+1 to D+4": eq_rows("P x age", AGE_GROUPS)}
    tests["all three equal (only the star chance by season)"] = (tests["P and P^2 equal across all five seasons"]
                                                                  + tests["P x age equal across D+1 to D+4"])
    tests["P and P^2 equal across D+1 to D+4 (D+5 on apart)"] = (eq_rows("P", AGE_GROUPS) + eq_rows("P^2", AGE_GROUPS))
    for lab, rr in tests.items():
        wt = m.wald_test(np.vstack(rr), use_f=False, scalar=True)
        wald.append({"age_measure": am, "test": lab, "df": len(rr), "chi2": float(wt.statistic),
                     "p": float(wt.pvalue)})
W = pd.DataFrame(wald)
for lab in W["test"].unique():
    w = W[W["test"] == lab]
    log(f"  {lab:<52} chi2({int(w['df'].iloc[0])}) = " + "; ".join(
        f"{r.chi2:.2f}, p = {r.p:.4g} ({r.age_measure})" for r in w.itertuples()))
log("  (the tests sit in the adopted regression, whose fit does not depend on the age measure. The production tests' p")
log("  moves with the measure because, with age less 18, each season's production coefficient also carries k times that")
log("  season's age coefficient: a different hypothesis about the same fit. The age test's p does not move)")

# ---- coefficients ----------------------------------------------------------------------------------------------
log("\nCOEFFICIENTS (years past first eligibility, centred at 18; $M; standard errors clustered by player)")
coef = []
for (am, arm), (m, names) in FITS.items():
    for i, n_ in enumerate(names):
        coef.append({"age_measure": am, "arm": ARMS[arm], "term": n_, "coef": m.params[i], "se": m.bse[i],
                     "p": m.pvalues[i]})
CO = pd.DataFrame(coef)
for arm in ARMS:
    m, names = FITS[("ype18", arm)]
    log(f"  {ARMS[arm]}: " + "; ".join(f"{n_} {m.params[i]:.4f} ({m.bse[i]:.4f})" for i, n_ in enumerate(names)
                                        if not n_.startswith("S:")))

# ---- economic: production's value by season -------------------------------------------------------------------
log("\nPRODUCTION'S VALUE BY SEASON ($M at 10 and 20 points per 82, a draftee 0.5 years past first eligibility, the")
log("star chance left out; years past first eligibility centred at 18)")
for arm in ARMS:
    m, names = FITS[("ype18", arm)]
    cells = []
    for g in GROUPS:
        for q in (10, 20):
            Xg, _ = design(np.array([g]), np.zeros(1), np.array([float(q)]), np.array([0.5]), arm)
            cells.append(f"{LABEL[g]} {q}: {float(Xg[0] @ m.params):5.2f}")
    log(f"  {ARMS[arm]:<30}" + "  ".join(cells))

# ---- held-out (supplementary) ----------------------------------------------------------------------------------
log("\nHELD-OUT ERROR (supplementary; $M of remaining NPV a prospect-season, each draft predicted from a fit without it;")
log("p = the share of 2,000 redraws in which the arm's summed squared error is NOT below the adopted model's)")
for am in AGE_MEASURES:
    for arm in ARMS:
        if arm == "adopted":
            continue
        p = p_lower(ERR[(am, arm)], ERR[("ype18", "adopted")])
        S.loc[(S["age_measure"] == am) & (S["key"] == arm), "p_heldout_vs_adopted"] = p
        if arm == "pool_age" and am != "ype18":
            continue
        r1 = float(np.sqrt(np.mean(ERR[(am, arm)] ** 2)))
        log(f"  {ARMS[arm]:<30}{am:<10}{r1:>8.4f}{100 * (r1 / rm_ad - 1):>+9.3f}% against adopted ({rm_ad:.4f}), "
            f"p = {p:.4f}")

# ---- the traded prospects --------------------------------------------------------------------------------------
pv = pd.read_csv(F["values"])
valued = pv["status"].isin(["prospect, valued", "undrafted prospect, valued (NHL contract)"])
prod = valued & pv["value_basis"].isin(["slot + production", "production", "production (undrafted, slot at zero)"])
t = pv[prod].copy()
tg = t["k_group"].astype(str).values
t_age = {"ype18": t["past_elig"].values, "ype185": t["past_elig"].values - 0.5,
         "agem18": t["past_elig"].values + t["seasons_since_draft"].values}
fixed = pv[valued & ~prod]
drafted, fixed_d = t["draftYear"].notna(), fixed["draftYear"].notna()
n_dr = int(drafted.sum()) + int(fixed_d.sum())
V = {}
for am in AGE_MEASURES:
    for arm in ARMS:
        m, _ = FITS[(am, arm)]
        X, _ = design(tg, t["p_star"].fillna(0.0).values, t["nhle82"].values.astype(float), t_age[am], arm)
        V[(am, arm)] = pd.Series(X @ m.params, index=t.index)
gap_v = float((V[("ype18", "adopted")] - t["value_M"]).abs().max())
assert gap_v < 1e-6, gap_v                                                                                       # GUARD
base_d = t.loc[drafted, "value_M"].sum() + fixed.loc[fixed_d, "value_M"].sum()
base_u = t.loc[~drafted, "value_M"].sum()
log(f"\nTHE TRADED PROSPECTS (guard: the adopted arm reproduces prospect_values.csv's value_M, largest gap {gap_v:.1e} "
    f"(PASS)); {n_dr} drafted ({int(fixed_d.sum())} goalies on draft position alone, the same in every arm), "
    f"{int((~drafted).sum())} undrafted")
log(f"  {'arm':<30}{'age measure':<10}{'drafted':>9}{'change':>8}{'moved $0.25M+':>15}{'undrafted':>11}{'change':>8}"
    f"   largest mover")
trd = []
for (am, arm), v in V.items():
    if (arm in ("adopted", "pool_age")) and am != "ype18":
        continue
    tot_d = v[drafted].sum() + fixed.loc[fixed_d, "value_M"].sum()
    tot_u = v[~drafted].sum()
    mv = v - t["value_M"]
    i = mv[drafted].abs().idxmax()
    r_ = t.loc[i]
    big = (f"{r_['player_name']} ({r_['trade_date']}, {LABEL[str(r_['k_group'])]}, {r_['nhle82']:.1f} points) "
           f"${r_['value_M']:.2f}M -> ${v[i]:.2f}M")
    n_mv = int((mv[drafted].abs() >= 0.25).sum())
    log(f"  {ARMS[arm]:<30}{am:<10}{tot_d:>9.2f}{tot_d - base_d:>+8.2f}{n_mv:>9} of {n_dr:<3}{tot_u:>11.2f}"
        f"{tot_u - base_u:>+8.2f}   {big if arm != 'adopted' else '-'}")
    trd.append({"age_measure": am, "arm": ARMS[arm], "drafted_total_M": tot_d, "drafted_change_M": tot_d - base_d,
                "drafted_moved_025": n_mv, "undrafted_total_M": tot_u, "undrafted_change_M": tot_u - base_u,
                "largest_mover": big})

rewritten = [k_ for k_, p_ in F.items() if p_.stat().st_mtime != MTIME[k_]]
assert not rewritten, f"inputs rewritten while the test ran: {rewritten}"                                        # GUARD
log("\n  guard: no input was rewritten while the test ran (PASS)")
S.to_csv(OUTPUT_DIR / "prospect_pooled_terms_look.csv", index=False)
CO.to_csv(OUTPUT_DIR / "prospect_pooled_terms_coefficients.csv", index=False)
W.to_csv(OUTPUT_DIR / "prospect_pooled_terms_wald.csv", index=False)
pd.DataFrame(trd).to_csv(OUTPUT_DIR / "prospect_pooled_terms_traded_summary.csv", index=False)
(OUTPUT_DIR / "prospect_pooled_terms_look_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote prospect_pooled_terms_look.csv, _coefficients.csv, _wald.csv, _traded_summary.csv and the log in "
    f"{OUTPUT_DIR}")
