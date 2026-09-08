"""
=============================================================================
 skater_value_engine.py   v1.1                     Phase 1b -- Layer 1
                                                     (D20, 2026-07-05)
=============================================================================
 WHAT THIS SCRIPT DOES (plain English)
 -------------------------------------
 Builds skater_value_spine.csv: for every skater contract-season 2015-2025,
 the dollar value of the player's production (Value_t), what he actually
 cost (Cost_t), and the difference (Surplus_t).

 It runs in three stages:

   STAGE 0a  Reproduction guard, OLD numbers. Rebuilds the ORIGINAL locked
             May-26 regression (position-blind, goalies pooled in, two
             markets, 2015-2025 starts) and asserts the coefficients land
             on the locked report values. This proves the pipeline in this
             file is the same pipeline that produced the locked report --
             if this stage fails, NOTHING downstream can be trusted.

   STAGE 0b  Fits the NEW locked market rate (skaters only, one pooled
             market, 2018-2025 starts -- decisions D6/D7/D8/D9, July 2026)
             and asserts it matches the locked constants embedded below.

   STAGE 1   Builds the spine. For each skater contract-season:
               trailing weighted WAR  ->  predicted cap%  ->  dollars.

 KEY DESIGN DECISIONS BAKED IN (with their decision IDs)
 -------------------------------------------------------
   D6  Skater-only rate (goalies removed from the sample; they have their
       own engine in goalie_value_spine.csv).
   D7  ONE market rate. RFA/UFA are not statistically distinct for skaters
       (F=0.12, p=0.887), so a single line prices both. The RFA/UFA label
       is still written to the spine as metadata.
   D8  Rate estimated on 2018-2025 contract starts only. The PuckPedia
       export's coverage of earlier years is thin and selected
       (63/223/452 contracts for 2015/16/17 vs ~700/yr from 2018).
   D9  No era/regime splits. Residual era differences are marginal
       (p=0.044) and the back-test currency is surplus RATIOS, which are
       robust to level errors in the rate by design. Era-specific rates
       remain available as a robustness re-run.

 LOOK-AHEAD DEFENSE (Karl axis #2 -- the most important comment in here)
 ----------------------------------------------------------------------
   A season-t valuation uses WAR from seasons t-1 and t-2 ONLY -- never
   season t itself. The lookup below is structurally incapable of seeing
   season t: it reads (season_start - 1) and (season_start - 2). Any
   future edit to this file must preserve that property.

 HOW TO RUN (Windows)
 --------------------
   1. Put this file in the folder that contains the four input files
      listed in CONFIG below (or set the XNPV_DATA environment variable).
   2. Run:  python skater_value_engine.py
   3. Outputs land next to the inputs:
        skater_value_spine.csv     the deliverable
        skater_value_run_log.txt   guard results + validation battery
=============================================================================
"""

import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

# ---------------------------------------------------------------------------
# CONFIG -- file locations
# ---------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("XNPV_DATA", "."))

F_CONTRACT_XLSX = DATA_DIR / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx"
F_WAR_SKATERS   = DATA_DIR / "WAR.csv"          # Bacon skater WAR, raw season totals
F_WAR_GOALIES   = DATA_DIR / "Goalies_WAR.csv"  # needed ONLY for the Stage-0a guard
F_SEASON_SPINE  = DATA_DIR / "contract_season_spine.csv"

OUT_SPINE = DATA_DIR / "skater_value_spine.csv"
OUT_LOG   = DATA_DIR / "skater_value_run_log.txt"

# ---------------------------------------------------------------------------
# LOCKED CONSTANTS -- do not edit without a logged decision
# ---------------------------------------------------------------------------
# The OLD locked baseline (WAR_AAV_Regression_Report_v2, May 2026).
# Reproduced to these tolerances on 2026-07-05; the +2/+4 sample-size
# residual is name-variant matching edge cases and moves nothing.
OLD_LOCKED = {
    "UFA": dict(a=0.020182, b=0.015337, n=1616),
    "RFA": dict(a=0.020162, b=0.017049, n=1301),
}
TOL_OLD_COEF = 2.5e-4   # max allowed |difference| on alpha and beta
TOL_OLD_N    = 10       # max allowed sample-size difference

# The pre-D20 rate (D6-D9 as originally locked 2026-07-05, RAW anchors).
# Kept as the Stage-0b continuity guard: reproducing it proves this file
# is still the pipeline that produced the old lock, so the D20 change is
# the ONLY difference between old and new numbers.
PRE_D20_LOCKED = dict(alpha=0.01845160, beta=0.02021386, n=2349, r2=0.463790)

# The D20 skater market rate (same D6-D9 spec, PRORATED anchors;
# locked 2026-07-05). Slope flattens ~5% -- COVID-era anchors grew, cap%
# per WAR unit falls; R2 improves slightly (0.4638 -> 0.4649).
# SUPERSEDED 2026-07-27 by the censored interaction rate below. Retained so
# the size of the change stays visible and any older output can be identified.
OLD_D20_RATE = dict(alpha=0.01831864, beta=0.01924854, n=2349, r2=0.464947)

# The rate in force. Left-censored at the league minimum, straight in
# production, with the position entering as a slope difference rather than a
# constant. Fitted on the same locked n=2,349 sample. Dollar figures are at the
# 2025-26 ceiling of $95.5M.
NEW_LOCKED = dict(
    alpha=0.0132478230,        # $1.2652M, value of a zero-win player
    beta=0.0212322891,         # $2.0277M per win, forwards
    beta_d_add=0.0028702824,   # $0.2741M per win extra, defencemen
    n=2349,
    sigma=0.02276380,
)
NEW_LOCKED["beta_d"] = NEW_LOCKED["beta"] + NEW_LOCKED["beta_d_add"]


def _skater_rate_cap_pct(war, posgrp):
    """Predicted cap share for a skater at `war` trailing wins.

    `posgrp` is "F" or "D". Defencemen carry a steeper slope and the SAME
    intercept: at zero measured wins the market pays the two positions alike,
    which is why the position enters as an interaction and not a constant.
    Accepts scalars or pandas Series."""
    import numpy as _np
    is_d = (posgrp == "D")
    slope = _np.where(is_d, NEW_LOCKED["beta_d"], NEW_LOCKED["beta"])
    return NEW_LOCKED["alpha"] + slope * war


def _fit_censored_interaction(cap_pct, war, is_d, floor_pct):
    """Re-fit the rate in force, so the guard below has something to check.

    Left-censored maximum likelihood. Contracts above the league minimum
    contribute the normal density at their observed price; contracts AT the
    minimum contribute only the probability of falling at or below it.

    The outcome is rescaled to percentage points of the cap internally: a cap
    share near 0.02 gives gradients near 1e-4 and the optimiser stalls on them.
    Convergence is judged on the gradient and a positive-definite Hessian
    rather than the optimiser's own flag."""
    import numpy as _np
    from scipy import optimize as _opt, stats as _sts
    y = _np.asarray(cap_pct, float) * 100.0
    lo = _np.asarray(floor_pct, float) * 100.0
    X = _np.column_stack([_np.ones(len(y)), _np.asarray(war, float),
                          _np.asarray(is_d, float) * _np.asarray(war, float)])
    cens = y <= lo + 1e-12
    k = X.shape[1]

    def neg_ll(p):
        beta, sig = p[:k], _np.exp(p[k])
        mu = X @ beta
        ll = _np.empty_like(y)
        ll[~cens] = -_np.log(sig) + _sts.norm.logpdf((y[~cens] - mu[~cens]) / sig)
        ll[cens] = _sts.norm.logcdf((lo[cens] - mu[cens]) / sig)
        return 1e10 if not _np.all(_np.isfinite(ll)) else -ll.sum()

    ols = _np.linalg.lstsq(X, y, rcond=None)[0]
    start = _np.append(ols, _np.log(max(_np.std(y - X @ ols), 1e-6)))
    res = _opt.minimize(neg_ll, start, method="BFGS",
                        options=dict(maxiter=20000, gtol=1e-9))
    if not res.success:
        alt = _opt.minimize(neg_ll, res.x, method="Nelder-Mead",
                            options=dict(maxiter=50000, xatol=1e-10, fatol=1e-10))
        if alt.fun < res.fun:
            res = alt
        r2_ = _opt.minimize(neg_ll, res.x, method="BFGS",
                            options=dict(maxiter=20000, gtol=1e-9))
        if r2_.fun <= res.fun:
            res = r2_
    p = res.x.copy()
    h = _np.maximum(_np.abs(p) * 1e-4, 1e-6)
    grad = _np.array([(neg_ll(p + _np.eye(len(p))[i] * h[i])
                       - neg_ll(p - _np.eye(len(p))[i] * h[i])) / (2 * h[i])
                      for i in range(len(p))])
    return dict(alpha=p[0] / 100.0, beta=p[1] / 100.0, beta_d_add=p[2] / 100.0,
                sigma=float(_np.exp(p[k]) / 100.0),
                converged=bool(_np.max(_np.abs(grad)) < 1e-3),
                grad_max=float(_np.max(_np.abs(grad))))
TOL_NEW_COEF = 5e-5
TOL_NEW_N    = 5

# Hard salary-cap ceilings by season start year (NHL/NHLPA published).
CAP_CEILING = {
    2015: 71.4e6, 2016: 73.0e6, 2017: 75.0e6, 2018: 79.5e6, 2019: 81.5e6,
    2020: 81.5e6, 2021: 81.5e6, 2022: 82.5e6, 2023: 83.5e6, 2024: 88.0e6,
    2025: 95.5e6,
}

# League minimum BASE salary by season start year (CBA-set floor, source:
# CBA Art. 11.12(a/b), cross-checked PuckPedia/PHR, pulled 2026-07-05).
# DECISION D10 (locked 2026-07-05): Value_t floors at this amount. Rationale
# -- a replacement-level player can always be signed at the league minimum,
# so no player's modeled production value should price below it. This is
# an EXOGENOUS constant (set by the CBA, not by anything in the model), so
# it introduces no circularity, look-ahead, or selection-bias exposure --
# it never uses outcome data, only a public, pre-determined dollar figure.
LEAGUE_MIN_SALARY = {
    2015: 575_000, 2016: 575_000, 2017: 650_000, 2018: 650_000,
    2019: 700_000, 2020: 700_000, 2021: 750_000, 2022: 750_000,
    2023: 775_000, 2024: 775_000, 2025: 775_000,
}

MIN_GP = 10          # a prior season needs >= 10 GP to count as a WAR signal
W_T1, W_T2 = 0.6, 0.4  # locked 60/40 recency weighting

# DECISION D20 (locked 2026-07-05): SCHEDULE PRORATION. WAR is a season
# TOTAL, so the two schedule-shortened seasons mechanically deflate every
# anchor drawn from them (2019-20: ~70 team games; 2020-21: 56). Season
# totals from those two years are scaled to an 82-game basis BEFORE any
# anchor is built. This corrects the league-wide artifact ONLY -- games a
# player missed within a season still count against him (availability is
# real signal). 2019-20 team schedules varied 68-71 games; a single 82/70
# factor is a documented simplification (within +/-2% of exact).
# THIS DICT IS THE SINGLE SOURCE OF TRUTH -- the projection module and the
# goalie engine import it (or assert equality against their local copy).
PRORATION = {2019: 82 / 70, 2020: 82 / 56}

# Names known to be TWO different humans merged under one row-name in
# WAR.csv (locked age-join decision: leave unmatched). Excluded + flagged.
MERGED_WAR_NAMES = {"ryan johnson", "nathan smith"}

# Spine-side name aliases -> WAR.csv row names. The NYI defenseman appears
# in WAR.csv as "Sebastian Aho Swe"; PuckPedia calls him "Sebastian Aho".
# Keys are (normalized name, position group).
NAME_ALIASES = {("sebastian aho", "D"): "sebastian aho swe"}

# ---------------------------------------------------------------------------
# NAME NORMALIZATION -- same rules as age_join.py
# ---------------------------------------------------------------------------
_VARIANTS = {
    "alexander": "alex", "alexandre": "alex", "nicholas": "nick",
    "michael": "mike", "matthew": "matt", "christopher": "chris",
    "maxime": "max", "zachary": "zach", "joshua": "josh", "samuel": "sam",
    "benjamin": "ben", "daniel": "dan", "jonathan": "jon",
    "steven": "steve", "gregory": "greg", "patrick": "pat",
}

def norm_name(s):
    """Accent-strip, lowercase, drop punctuation/suffixes, resolve common
    first-name variants (Alexander -> Alex). Mirrors the age-join rules so
    every pipeline in the project matches names the same way."""
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().replace("-", " ")
    s = re.sub(r"\(.*?\)", "", s)               # strip "(D)"-style tags
    s = re.sub(r"[.'\u2019]", "", s)
    s = re.sub(r"\b(jr|sr|iii|ii|iv)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split()
    if parts:
        parts[0] = _VARIANTS.get(parts[0], parts[0])
    return " ".join(parts)

POSGRP = {"Center": "F", "Left Wing": "F", "Right Wing": "F",
          "Defense": "D", "Goaltender": "G"}

LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))

# ---------------------------------------------------------------------------
# WAR LOOKUPS
# ---------------------------------------------------------------------------
def build_skater_war_lookup(exclude_merged=True, prorate=True):
    """One entry per (normalized name + position group, season start year)
    -> season-total WAR, for seasons with >= MIN_GP games. Merged-name
    rows are excluded so no contract silently inherits a stranger's WAR.
    prorate=True applies the D20 schedule factors; Stage 0a passes False
    so the historical reproduction guard stays on the exact raw inputs
    the locked May-26 report was built from."""
    war = pd.read_csv(F_WAR_SKATERS)
    war["syr"] = war["Season"].str.split("-").str[0].astype(int) + 2000
    if prorate:
        war["WAR"] = war["WAR"] * war["syr"].map(PRORATION).fillna(1.0)
    war["nk"] = war["Player"].map(norm_name) + "|" + war["Position"]
    if exclude_merged:
        bare = war["Player"].map(norm_name)
        war = war[~bare.isin(MERGED_WAR_NAMES)].copy()

    # REVIEW ITEM 1.5. The source spells some traded players differently for
    # each half of a season -- "Nick Paul" for his 59 games in Ottawa,
    # "Nicholas Paul" for his 21 games in Tampa. Both clean to the same key,
    # and the old code kept whichever came first in the file and dropped the
    # other. For Paul that meant keeping the 21-game half and discarding the
    # 59-game one. His 2022 starting value came out at -0.055, and a negative
    # starting value routes a player onto D12 v3's replacement-reversion
    # branch instead of the aging curve -- an entirely different projection,
    # applied across the seven-year contract he signed that same year.
    # Summed, he starts at +0.363 and takes the curve.
    #
    # Summing BEFORE the games filter rather than after mirrors what
    # build_goalie_war_lookup already does, and it means a player whose
    # smaller half falls under MIN_GP still keeps that production.
    dup = war.duplicated(["nk", "syr"], keep=False)
    if dup.any():
        # GUARD. Summing is right only when the rows are two halves of ONE
        # player's season. Two DIFFERENT players sharing a cleaned name and
        # position would collide here too, and adding them together would be
        # a far worse error than the one being fixed. No real season exceeds
        # 82 games, so a combined total above that means two people.
        tot = war[dup].groupby(["nk", "syr"])["GP"].sum()
        assert (tot <= 82).all(), (
            "combined games above a full season for "
            f"{list(tot[tot > 82].index)} -- that is two different players "
            "sharing a name, not one player's two team-halves. Do not sum "
            "them; give one of them a disambiguating alias instead.")
    q = war.groupby(["nk", "syr"], as_index=False).agg(GP=("GP", "sum"),
                                                       WAR=("WAR", "sum"))
    q = q[q["GP"] >= MIN_GP]
    # The dup-key guard inside trailing_weighted_war() was written for the
    # case this grouping now makes impossible. It could never fire before
    # either, because the old drop_duplicates ran first. Left in place as a
    # belt-and-braces check; this assert is the one that actually holds.
    assert not q.duplicated(["nk", "syr"]).any(), \
        "the WAR lookup still holds duplicate keys after grouping"
    return q.set_index(["nk", "syr"])["WAR"].sort_index()

def build_goalie_war_lookup():
    """Goalie WAR for the Stage-0a guard only. Multi-team season rows are
    summed to one row per goalie-season BEFORE the GP filter -- this is how
    the original locked regression was built."""
    gw = pd.read_csv(F_WAR_GOALIES)
    g = gw.groupby(["Goalie", "Season"], as_index=False).agg(GP=("GP", "sum"),
                                                             WAR=("WAR", "sum"))
    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    g["nk"] = g["Goalie"].map(norm_name) + "|G"
    g = g[g["GP"] >= MIN_GP].drop_duplicates(["nk", "syr"])
    return g.set_index(["nk", "syr"])["WAR"].sort_index()

def trailing_weighted_war(key, start_yr, lut):
    """The locked trailing rule: 60% of season t-1 + 40% of season t-2;
    if only one of the two exists, use it alone; if neither, return NaN.
    Returns (weighted_war, source_tag). NEVER reads season t itself."""
    def get(k):
        v = lut.get(k, np.nan)
        return np.nan if isinstance(v, pd.Series) else v   # dup-key guard
    if pd.isna(start_yr):
        return np.nan, "none"
    w1 = get((key, int(start_yr) - 1))
    w2 = get((key, int(start_yr) - 2))
    if pd.notna(w1) and pd.notna(w2):
        return W_T1 * w1 + W_T2 * w2, "both"
    if pd.notna(w1):
        return w1, "t1_only"
    if pd.notna(w2):
        return w2, "t2_only"
    return np.nan, "none"

# ---------------------------------------------------------------------------
# STAGE 0a -- reproduce the OLD locked pooled regression
# ---------------------------------------------------------------------------
def stage0():
    log("=" * 74)
    log("STAGE 0a: reproduction guard vs WAR_AAV_Regression_Report_v2 (locked)")
    log("=" * 74)

    raw = pd.read_excel(F_CONTRACT_XLSX)
    # true start year: the export's own `season` field is unreliable for
    # active multi-year deals; end-year minus length + 1 is the locked fix.
    raw["end_yr"] = pd.to_numeric(
        raw["contract_end"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")
    raw["start_yr"] = raw["end_yr"] - raw["length"] + 1
    raw["posgrp"] = raw["position"].map(POSGRP)
    raw["nk"] = ((raw["first_name"].astype(str) + " " + raw["last_name"].astype(str))
                 .map(norm_name) + "|" + raw["posgrp"].astype(str))

    # The ORIGINAL sample pooled goalies in and did NOT exclude merged names
    # (it predates that decision) -- reproduce it exactly as it was.
    lut_sk = build_skater_war_lookup(exclude_merged=False, prorate=False)  # guard = raw
    lut_go = build_goalie_war_lookup()
    ww = [trailing_weighted_war(k, s, lut_go if str(k).endswith("|G") else lut_sk)[0]
          for k, s in zip(raw["nk"], raw["start_yr"])]
    raw["wWAR"] = ww
    raw["cap_pct"] = raw["aav"] / raw["start_yr"].map(CAP_CEILING)

    ss = raw["signing_status"].astype(str)
    samp = raw[(raw["start_yr"].between(2015, 2025))
               & (raw["contract_level"] == "standard_level")
               & ss.isin(["UFA", "RFA"])
               & raw["wWAR"].notna() & raw["cap_pct"].notna()].copy()

    ok = True
    for mkt, tgt in OLD_LOCKED.items():
        d = samp[samp["signing_status"] == mkt]
        r = sm.OLS(d["cap_pct"], sm.add_constant(d["wWAR"])).fit()
        da, db, dn = (abs(r.params["const"] - tgt["a"]),
                      abs(r.params["wWAR"] - tgt["b"]), abs(len(d) - tgt["n"]))
        status = "PASS" if (da <= TOL_OLD_COEF and db <= TOL_OLD_COEF and dn <= TOL_OLD_N) else "FAIL"
        ok &= (status == "PASS")
        log(f"  {mkt}: n={len(d)} (locked {tgt['n']})  a={r.params['const']:.6f} "
            f"(locked {tgt['a']:.6f})  b={r.params['wWAR']:.6f} (locked {tgt['b']:.6f})  "
            f"R2={r.rsquared:.4f}   [{status}]")
    if not ok:
        log("\nGUARD FAILED -- the pipeline no longer matches the locked report."
            "\nDo not use any output from this run. Investigate before proceeding.")
        return None
    log("  Stage 0a PASSED: this pipeline reproduces the locked report.\n")

    # ------------------------------------------------------------------
    # STAGE 0b -- fit and assert the NEW locked rate (D6/D7/D8/D9)
    # ------------------------------------------------------------------
    log("STAGE 0b: skater market rate -- raw continuity guard, then D20 fit")
    sk = samp[(samp["posgrp"] != "G") & (samp["start_yr"] >= 2018)]
    # 0b-i: RAW continuity guard -- same fit that produced the pre-D20 lock
    r = sm.OLS(sk["cap_pct"], sm.add_constant(sk["wWAR"])).fit(cov_type="HC3")
    a, b = r.params["const"], r.params["wWAR"]
    da, db = abs(a - PRE_D20_LOCKED["alpha"]), abs(b - PRE_D20_LOCKED["beta"])
    status = ("PASS" if (da <= TOL_NEW_COEF and db <= TOL_NEW_COEF
                         and abs(len(sk) - PRE_D20_LOCKED["n"]) <= TOL_NEW_N) else "FAIL")
    log(f"  raw guard: n={len(sk)}  a={a:.8f}  b={b:.8f}  [{status}]")
    if status == "FAIL":
        log("\nGUARD FAILED on the raw continuity fit -- pipeline drift.")
        return None
    # 0b-ii: the D20 rate -- identical sample, PRORATED trailing anchors.
    # (The anchors must be recomputed; the raw lookup fed `samp` above.)
    lut_p = build_skater_war_lookup(exclude_merged=False, prorate=True)
    sk = sk.copy()
    sk["wWAR"] = [trailing_weighted_war(k, y, lut_p)[0]
                  for k, y in zip(sk["nk"], sk["start_yr"])]
    sk = sk[sk["wWAR"].notna()]
    # ITEM 4.5 STEP 1: the guard re-fits the CENSORED INTERACTION rate now,
    # not the old single-slope least-squares one. Same discipline as before --
    # the rate is re-derived from the data on every run and checked against the
    # locked constants, so upstream drift halts the pipeline instead of
    # silently moving every valuation.
    sk = sk.copy()
    sk["is_d"] = (sk["posgrp"] == "D").astype(float)
    sk["floor_pct"] = (sk["start_yr"].map(LEAGUE_MIN_SALARY)
                       / sk["start_yr"].map(CAP_CEILING))
    fit = _fit_censored_interaction(sk["cap_pct"].values, sk["wWAR"].values,
                                    sk["is_d"].values, sk["floor_pct"].values)
    a, b, bd = fit["alpha"], fit["beta"], fit["beta_d_add"]
    da = abs(a - NEW_LOCKED["alpha"])
    db = abs(b - NEW_LOCKED["beta"])
    dbd = abs(bd - NEW_LOCKED["beta_d_add"])
    status = ("PASS" if (fit["converged"] and da <= TOL_NEW_COEF
                         and db <= TOL_NEW_COEF and dbd <= TOL_NEW_COEF
                         and abs(len(sk) - NEW_LOCKED["n"]) <= TOL_NEW_N)
              else "FAIL")
    log(f"  censored interaction rate:  n={len(sk)} (locked {NEW_LOCKED['n']}) "
        f"converged={fit['converged']} (max gradient {fit['grad_max']:.2e})")
    log(f"    alpha      {a:.8f} (locked {NEW_LOCKED['alpha']:.8f})")
    log(f"    beta_F     {b:.8f} (locked {NEW_LOCKED['beta']:.8f})")
    log(f"    beta_D_add {bd:.8f} (locked {NEW_LOCKED['beta_d_add']:.8f})   "
        f"[{status}]")
    if status == "FAIL":
        log("\nGUARD FAILED on the censored rate -- do not use this run's output.")
        return None
    log(f"  contracts at the league minimum (censored): "
        f"{int((sk['cap_pct'] <= sk['floor_pct'] + 1e-12).sum())} of {len(sk)}")
    log(f"  Price of one WAR at the 2025-26 ceiling: "
        f"${NEW_LOCKED['beta'] * CAP_CEILING[2025] / 1e6:.2f}M forwards, "
        f"${NEW_LOCKED['beta_d'] * CAP_CEILING[2025] / 1e6:.2f}M defencemen")
    log(f"  Value of a zero-win player: "
        f"${NEW_LOCKED['alpha'] * CAP_CEILING[2025] / 1e6:.2f}M   "
        f"(was ${OLD_D20_RATE['alpha'] * CAP_CEILING[2025] / 1e6:.2f}M)")
    log("  Stage 0b PASSED.\n")
    return True

# ---------------------------------------------------------------------------
# STAGE 1 -- build the spine
# ---------------------------------------------------------------------------
def stage1():
    log("=" * 74)
    log("STAGE 1: build skater_value_spine.csv")
    log("=" * 74)

    cs = pd.read_csv(F_SEASON_SPINE)
    sk = cs[(cs["position"] != "Goaltender")
            & cs["season_start"].between(2015, 2025)].copy()
    log(f"  skater contract-seasons, 2015-2025: {len(sk):,}")

    sk["posgrp"] = sk["position"].map(POSGRP)
    sk["full_name"] = sk["first_name"].astype(str) + " " + sk["last_name"].astype(str)
    sk["nname"] = sk["full_name"].map(norm_name)

    # Alias resolution BEFORE key construction (Sebastian Aho the defenseman).
    def make_key(row):
        alias = NAME_ALIASES.get((row["nname"], row["posgrp"]))
        return (alias if alias else row["nname"]) + "|" + row["posgrp"]
    sk["nk"] = sk.apply(make_key, axis=1)
    sk["merged_name_excluded"] = sk["nname"].isin(MERGED_WAR_NAMES)

    # Trailing WAR: the ONLY player-value input, drawn strictly from seasons
    # before the season being valued (look-ahead defense, see header).
    lut = build_skater_war_lookup(exclude_merged=True)
    res = [trailing_weighted_war(k, y, lut)
           for k, y in zip(sk["nk"], sk["season_start"])]
    sk["trailing_war"] = [r[0] for r in res]
    sk["war_source"] = [r[1] for r in res]

    # Market label (D1): control status in the season being valued.
    # Metadata only under D7 -- it no longer changes the price.
    sk["market_label"] = np.where(sk["season_start"] < sk["ufa_year"], "RFA", "UFA")
    sk["elc_season"] = sk["cs_entry_level"] == True

    # Value_t: one locked rate, all seasons (D7/D8/D9), floored at the
    # league minimum salary for that season (D10). The floor is applied
    # AFTER the regression prediction -- it never touches trailing_war or
    # predicted_cap_pct, so the raw regression output stays inspectable.
    # ITEM 4.5 STEP 1: position-dependent slope, common intercept. At zero
    # measured wins the market pays forwards and defencemen alike, so the
    # position enters as a slope difference rather than as a constant premium.
    sk["predicted_cap_pct"] = _skater_rate_cap_pct(sk["trailing_war"],
                                                   sk["posgrp"])
    sk["cap_ceiling_used"] = sk["season_start"].map(CAP_CEILING)
    sk["value_dollars_unfloored"] = sk["predicted_cap_pct"] * sk["cap_ceiling_used"]
    sk["league_min_used"] = sk["season_start"].map(LEAGUE_MIN_SALARY)
    sk["floor_bound"] = sk["value_dollars_unfloored"] < sk["league_min_used"]
    sk["value_dollars"] = np.maximum(sk["value_dollars_unfloored"], sk["league_min_used"])

    # Cost_t: per-season cap hit where the clause pipeline matched the season
    # (cs_cap_hit), else the contract-level PuckPedia cap hit.
    sk["cost_dollars"] = sk["cs_cap_hit"].fillna(sk["pp_cap_hit"])
    sk["cost_source"] = np.where(sk["cs_cap_hit"].notna(), "cs_cap_hit", "pp_cap_hit")
    sk["surplus_dollars"] = sk["value_dollars"] - sk["cost_dollars"]

    cols = ["contract_id", "player_id", "ep_id", "nhl_id", "full_name", "position",
            "posgrp", "season", "season_start", "market_label", "elc_season",
            "merged_name_excluded", "trailing_war", "war_source",
            "predicted_cap_pct", "cap_ceiling_used", "value_dollars_unfloored",
            "league_min_used", "floor_bound", "value_dollars",
            "cost_dollars", "cost_source", "surplus_dollars"]
    out = sk[cols].sort_values(["season_start", "full_name"])
    out.to_csv(OUT_SPINE, index=False)
    log(f"  written: {OUT_SPINE}  ({len(out):,} rows)\n")
    return out

# ---------------------------------------------------------------------------
# STAGE 2 -- validation battery
# ---------------------------------------------------------------------------
def stage2(out):
    log("=" * 74)
    log("STAGE 2: validation battery")
    log("=" * 74)

    priced = out["trailing_war"].notna()
    log(f"  priced rows: {priced.sum():,} / {len(out):,}  ({priced.mean()*100:.1f}%)")
    log("  unpriced by reason:")
    unp = out[~priced]
    log(f"    no qualifying prior-season WAR (rookies/AHL/ELC yr-1): {len(unp):,}")
    log(f"    of which merged-name exclusions: {int(unp['merged_name_excluded'].sum()):,}")
    log(f"  war_source mix (priced rows): "
        f"{out.loc[priced, 'war_source'].value_counts().to_dict()}")

    p = out[priced]
    log("\n  mean surplus by contract situation (the sanity story: teams should")
    log("  extract surplus from cost-controlled players, roughly break even on UFAs):")
    g = p.groupby(["elc_season", "market_label"])["surplus_dollars"].agg(["mean", "count"])
    for (elc, mkt), row in g.iterrows():
        tag = ("ELC " if elc else "    ") + mkt
        log(f"    {tag:8s} n={int(row['count']):5d}   mean surplus = ${row['mean']/1e6:+.2f}M")

    log("\n  league totals by season (value vs cost, $B):")
    t = p.groupby("season_start")[["value_dollars", "cost_dollars"]].sum() / 1e9
    for y, row in t.iterrows():
        log(f"    {y}: value {row['value_dollars']:.2f}  cost {row['cost_dollars']:.2f}")

    log("\n  spot checks:")
    for name, yr in [("Connor McDavid", 2024), ("Kirill Marchenko", 2025),
                     ("Sebastian Aho", 2023)]:
        rows = p[(p["full_name"] == name) & (p["season_start"] == yr)]
        for _, r in rows.iterrows():
            log(f"    {name} {yr}-{str(yr+1)[2:]} ({r['position'][:1]}): trailing WAR "
                f"{r['trailing_war']:.2f} -> value ${r['value_dollars']/1e6:.2f}M, "
                f"cost ${r['cost_dollars']/1e6:.2f}M, surplus ${r['surplus_dollars']/1e6:+.2f}M")

    bound = p["floor_bound"].sum()
    delta = (p.loc[p["floor_bound"], "value_dollars"]
             - p.loc[p["floor_bound"], "value_dollars_unfloored"]).sum()
    log(f"\n  D10 league-minimum floor: bound on {bound:,} / {len(p):,} priced rows "
        f"({bound/len(p)*100:.1f}%)")
    log(f"  total value added by the floor across the sample: ${delta/1e6:.2f}M")
    log(f"  (unbound rows are unaffected -- value_dollars == value_dollars_unfloored)")

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if stage0() is None:
        Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
        sys.exit(1)
    out = stage1()
    stage2(out)
    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")
