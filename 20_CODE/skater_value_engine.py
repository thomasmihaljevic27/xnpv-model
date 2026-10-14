"""
=============================================================================
 skater_value_engine.py   v2.0                     helpers (2026-10-14)
=============================================================================
 WHAT THIS IS NOW (v2.0, Thomas 2026-10-14: retire the 60/40 checks)
 -------------------------------------------------------------------
 A library. It no longer runs a pipeline or writes skater_value_spine.csv.
 Removed: Stage 0a (re-fit of the May 2026 pooled regression against its
 report), Stage 0b (re-fit of the Stage 3 line against NEW_LOCKED), Stage 1
 (the observed-season spine on the 60/40 trailing total) and its validation
 battery, with the 60/40 rule itself (W_T1, W_T2, trailing_weighted_war) and
 the goalie lookup that only Stage 0a read. None of them priced anything:
 contracts are priced on xNPV 1 (skater_forecast.py), and the spine was read
 only by contract_npv.validate() to pick rows to check (now taken from the
 contract-season spine). The dashboard chain no longer runs this file.

 What stays, because live code imports it: the paths, the cap ceilings and
 league minimums, MIN_GP, the D20 schedule proration (PRORATION, the single
 source of truth), the merged-name list, the name rules (norm_name, POSGRP),
 the WAR lookup, the censored line fitter, and the Stage 3 constants
 (NEW_LOCKED, the documented fallback line). has_recent_season() replaces
 the 60/40 total as the price line's sample screen: it is non-null exactly
 when the 60/40 total was (a 10+ game season at t-1 or t-2).

 The v1.1 file (the July pipeline and its guards) is in git at the commit
 before this one. Finished tests in 25_TESTS/ that import
 trailing_weighted_war or W_T1 reproduce their results only from there.
=============================================================================
"""

import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG -- file locations
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

load_dotenv()

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])   # vendor inputs, read-only
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])   # generated spines / panels / logs

F_CONTRACT_XLSX = Path(os.environ["PUCKPEDIA_CONTRACTS_XLSX"])
F_WAR_SKATERS   = SOURCE_DIR / "WAR.csv"          # Bacon skater WAR, raw season totals
F_WAR_SKATERS   = SOURCE_DIR / "WAR.csv"          # Bacon skater WAR, raw season totals

# The Stage 3 line (locked 2026-07-28). Left-censored at the league minimum, straight
# in production, the position entering as a slope difference. Fitted on the n=2,349
# sample against each contract's 60/40 trailing WAR. No longer re-fitted (v2.0); kept
# as the line skater_forward_projection.price_constants() falls back to when
# XNPV1_RATE is None. Dollar figures are at the
# 2025-26 ceiling of $95.5M.
NEW_LOCKED = dict(
    alpha=0.0132478230,        # $1.2652M, value of a zero-win player
    beta=0.0212322891,         # $2.0277M per win, forwards
    beta_d_add=0.0028702824,   # $0.2741M per win extra, defencemen
    n=2349,
    sigma=0.02276380,
)
NEW_LOCKED["beta_d"] = NEW_LOCKED["beta"] + NEW_LOCKED["beta_d_add"]


def _fit_censored_interaction(cap_pct, war, is_d, floor_pct):
    """The left-censored line fit (used by xnpv1_price_line.py).

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
    prorate=True applies the D20 schedule factors; False gives the raw
    season totals (the price line's sample screen reads either: only
    which keys exist matters there)."""
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
    # One row per key: the assert below is what has_recent_season() relies on.
    assert not q.duplicated(["nk", "syr"]).any(), \
        "the WAR lookup still holds duplicate keys after grouping"
    return q.set_index(["nk", "syr"])["WAR"].sort_index()


def has_recent_season(key, start_yr, lut):
    """True when the player has a 10+ game WAR season at start_yr - 1 or
    start_yr - 2 in `lut` (build_skater_war_lookup). This is exactly when the
    retired 60/40 trailing total was non-null, so the price line's sample
    keeps the same contracts (asserted there by fingerprint). NEVER reads
    season start_yr itself."""
    if pd.isna(start_yr):
        return False
    y = int(start_yr)
    return (key, y - 1) in lut.index or (key, y - 2) in lut.index


if __name__ == "__main__":
    print("skater_value_engine.py v2.0 is a library since 2026-10-14; there is nothing to run.")
