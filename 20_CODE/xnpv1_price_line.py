"""xnpv1_price_line.py -- the market's price per FORECAST win, for pricing xNPV 1.

WHY (session 2026-10-02; STANDING_FLAGS)
    The Stage 3 price per win (skater_value_engine.NEW_LOCKED, locked
    2026-07-28) regresses each contract's cap share on the player's TRAILING
    60/40 WAR total at the contract's start. xNPV 1 prices contracts with its
    FORECAST, which runs at about 0.67 of the trailing total's spread (0.180 +
    0.674 x trailing on the development pages; realised WAR is 0.163 + 0.710 x
    trailing). A line fitted per trailing win, applied to forecast wins,
    under-prices every win above its intercept, so good players look overpaid
    by construction. The fix is a line fitted on the same quantity it prices.

WHAT THIS DOES -- ONE CHANGE, everything else held
    1. Builds the Stage 3 sample exactly as skater_value_engine.stage0 does:
       standard-level UFA and RFA skater contracts starting 2018-2025, cap
       share = AAV / that season's ceiling, prorated trailing 60/40 WAR at the
       start year, censored at the league minimum. It then re-fits the locked
       specification on it and REQUIRES the locked Stage 3 constants back (the
       same guard stage0 applies), which proves the sample is the locked one.
    2. Replaces ONE input: the trailing total becomes xNPV 1's forecast of the
       player's WAR if he plays in the contract's first season, from the page
       of the start year (seasons before it only) -- the same information set
       Stage 3 used and the same quantity contract_npv prices each season.
    3. Fits the SAME specification on the SAME rows: left-censored at the
       league minimum, one intercept, a separate defence slope. Both fits are
       run on the identical row set (fingerprinted), so the comparison is one
       change.
    Reported: both fits; price per win at the 2025-26 ceiling; the censored
    log-likelihood of each (same rows, same outcome, same parameter count);
    and, by trailing-WAR tier, the mean cap share observed against each line's
    expected cap share. It also prints the RFA qualify-rate table (D14(c))
    calibrated both ways: on the trailing total (xNPV 0) and on xNPV 1's
    forecast (rfa_terminal_value v1.5).

v1.1 (2026-10-02): once skater_forward_projection.XNPV1_RATE is locked, every
run is also its reproduction guard: the fresh fit must give back the locked
constants (Stage 3's tolerances), the same n and the same rows fingerprint,
or the run prints GUARD FAILED and exits non-zero.

NOTHING IS ADOPTED BY RUNNING THIS. The new constants are written to
30_OUTPUT/xnpv1_price_line.json and printed as a block; they are locked in
skater_forward_projection.XNPV1_RATE only after the result is read.

HOW TO RUN (Windows PowerShell, from the repo root; needs the PuckPedia export
as .xlsx and .csv, about the time of one contract_npv run):
    python 20_CODE\\xnpv1_price_line.py
Output: 30_OUTPUT\\xnpv1_price_line_log.txt (send back) and
30_OUTPUT\\xnpv1_price_line.json.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skater_value_engine as SVE

SCRIPT_VERSION = "1.1"
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def stage3_sample() -> pd.DataFrame:
    """The locked Stage 3 sample, built step for step as stage0 builds it."""
    raw = pd.read_excel(SVE.F_CONTRACT_XLSX)
    raw["end_yr"] = pd.to_numeric(
        raw["contract_end"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")
    raw["start_yr"] = raw["end_yr"] - raw["length"] + 1
    raw["posgrp"] = raw["position"].map(SVE.POSGRP)
    raw["nk"] = ((raw["first_name"].astype(str) + " " + raw["last_name"].astype(str))
                 .map(SVE.norm_name) + "|" + raw["posgrp"].astype(str))
    # stage0 screens the sample on the RAW (pre-D20) trailing total, then
    # recomputes it prorated on the skater subset; both steps are kept.
    lut_raw = SVE.build_skater_war_lookup(exclude_merged=False, prorate=False)
    lut_go = SVE.build_goalie_war_lookup()
    raw["wWAR"] = [SVE.trailing_weighted_war(k, s, lut_go if str(k).endswith("|G") else lut_raw)[0]
                   for k, s in zip(raw["nk"], raw["start_yr"])]
    raw["cap_pct"] = raw["aav"] / raw["start_yr"].map(SVE.CAP_CEILING)
    ss = raw["signing_status"].astype(str)
    samp = raw[(raw["start_yr"].between(2015, 2025))
               & (raw["contract_level"] == "standard_level")
               & ss.isin(["UFA", "RFA"])
               & raw["wWAR"].notna() & raw["cap_pct"].notna()].copy()
    sk = samp[(samp["posgrp"] != "G") & (samp["start_yr"] >= 2018)].copy()
    lut_p = SVE.build_skater_war_lookup(exclude_merged=False, prorate=True)
    sk["wWAR"] = [SVE.trailing_weighted_war(k, y, lut_p)[0] for k, y in zip(sk["nk"], sk["start_yr"])]
    sk = sk[sk["wWAR"].notna()].copy()
    sk["is_d"] = (sk["posgrp"] == "D").astype(float)
    sk["floor_pct"] = sk["start_yr"].map(SVE.LEAGUE_MIN_SALARY) / sk["start_yr"].map(SVE.CAP_CEILING)
    return sk.reset_index(drop=True)


def fingerprint(d: pd.DataFrame) -> str:
    key = d[["nk", "start_yr", "cap_pct"]].astype(str).agg("|".join, axis=1).sort_values()
    return hashlib.sha1("\n".join(key).encode()).hexdigest()[:12]


def censored_loglik(fit, cap_pct, war, is_d, floor_pct) -> float:
    """The left-censored log-likelihood at a fitted line (in cap-share units)."""
    mu = fit["alpha"] + (fit["beta"] + fit["beta_d_add"] * is_d) * war
    s = fit["sigma"]
    cens = cap_pct <= floor_pct + 1e-12
    ll = np.where(cens, stats.norm.logcdf((floor_pct - mu) / s),
                  stats.norm.logpdf((cap_pct - mu) / s) - np.log(s))
    return float(ll.sum())


def expected_cap(fit, war, is_d, floor_pct) -> np.ndarray:
    """E[max(latent, floor)]: the cap share the line expects, floor included."""
    mu = fit["alpha"] + (fit["beta"] + fit["beta_d_add"] * is_d) * war
    s = fit["sigma"]
    d = (floor_pct - mu) / s
    return floor_pct * stats.norm.cdf(d) + mu * (1 - stats.norm.cdf(d)) + s * stats.norm.pdf(d)


def fit_line(d, xcol):
    return SVE._fit_censored_interaction(d["cap_pct"].to_numpy(float), d[xcol].to_numpy(float),
                                         d["is_d"].to_numpy(float), d["floor_pct"].to_numpy(float))


def show(name, f, cap):
    log(f"  {name}")
    log(f"    alpha {f['alpha']:.10f}  (${f['alpha'] * cap / 1e6:.3f}M at a ${cap / 1e6:.1f}M cap)")
    log(f"    beta_F {f['beta']:.10f}  (${f['beta'] * cap / 1e6:.3f}M per win, forwards)")
    log(f"    beta_D_add {f['beta_d_add']:.10f}  (defence ${(f['beta'] + f['beta_d_add']) * cap / 1e6:.3f}M per win)")
    log(f"    sigma {f['sigma']:.8f}   converged {f['converged']} (max gradient {f['grad_max']:.1e})")


def main():
    log("=" * 74)
    log(f" xnpv1_price_line.py  v{SCRIPT_VERSION}")
    log("=" * 74)
    cap = SVE.CAP_CEILING[2025]

    # ---- 1. the locked sample, proven by the locked fit ------------------------
    sk = stage3_sample()
    f0 = fit_line(sk, "wWAR")
    L = SVE.NEW_LOCKED
    ok = (f0["converged"] and abs(len(sk) - L["n"]) <= SVE.TOL_NEW_N
          and abs(f0["alpha"] - L["alpha"]) <= SVE.TOL_NEW_COEF
          and abs(f0["beta"] - L["beta"]) <= SVE.TOL_NEW_COEF
          and abs(f0["beta_d_add"] - L["beta_d_add"]) <= SVE.TOL_NEW_COEF)
    log(f"\n[1] the Stage 3 sample: {len(sk):,} contracts (locked n {L['n']:,}); re-fit on the trailing "
        f"total reproduces the locked rate: {'yes' if ok else 'NO'}")
    if not ok:
        log("GUARD FAILED: this is not the locked Stage 3 sample; nothing below is valid.")
        (OUTPUT_DIR / "xnpv1_price_line_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
        raise SystemExit(1)

    # ---- 2. xNPV 1's forecast for each contract's first season -----------------
    import skater_forecast as SF
    fc = SF.ContractForecaster()
    xw, pp = [], []
    for nk, yr in zip(sk["nk"], sk["start_yr"]):
        f = fc.forecast(nk, int(yr), 0)
        xw.append(np.nan if f is None else float(f.iloc[0]["war_if_plays"]))
        pp.append(np.nan if f is None else float(f.iloc[0]["p_play"]))
    sk["xwar"], sk["p_play0"] = xw, pp
    miss = sk[sk["xwar"].isna()]
    log(f"\n[2] xNPV 1 forecasts (page = start year, valuation season, WAR if he plays): "
        f"{len(sk) - len(miss):,} of {len(sk):,}")
    for r in miss.head(10).itertuples():
        log(f"    no forecast: {r.nk}  start {int(r.start_yr)}")
    d = sk[sk["xwar"].notna()].copy()
    b = np.polyfit(d["wWAR"], d["xwar"], 1)
    log(f"    on these contracts xNPV 1's forecast = {b[1]:+.3f} + {b[0]:.3f} x trailing total")

    # ---- 3. the same specification, the same rows, one input changed ----------
    f0s = fit_line(d, "wWAR")
    f1 = fit_line(d, "xwar")
    fp = fingerprint(d)
    log(f"\n[3] both fits on the same {len(d):,} contracts (rows fingerprint {fp}):")
    show("TRAILING total (the Stage 3 input)" + ("" if len(d) == len(sk) else ", on these rows"), f0s, cap)
    show("xNPV 1 FORECAST (the input contract_npv prices)", f1, cap)
    args = (d["cap_pct"].to_numpy(float), None, d["is_d"].to_numpy(float), d["floor_pct"].to_numpy(float))
    ll0 = censored_loglik(f0s, args[0], d["wWAR"].to_numpy(float), args[2], args[3])
    ll1 = censored_loglik(f1, args[0], d["xwar"].to_numpy(float), args[2], args[3])
    log(f"    censored log-likelihood: trailing {ll0:,.1f}   forecast {ll1:,.1f}   "
        f"(difference {ll1 - ll0:+,.1f}; same rows, outcome and parameter count)")
    log(f"    slope ratio, forecast over trailing: forwards {f1['beta'] / f0s['beta']:.3f}")

    # ---- 4. calibration by tier ------------------------------------------------
    e0 = expected_cap(f0s, d["wWAR"].to_numpy(float), args[2], args[3])
    e1 = expected_cap(f1, d["xwar"].to_numpy(float), args[2], args[3])
    d["e0"], d["e1"] = e0, e1
    d["tier"] = pd.cut(d["wWAR"], [-99, 0, 1, 2, 3, 99], labels=["below 0", "0-1", "1-2", "2-3", "3+"])
    log("\n[4] mean cap share by trailing-WAR tier, observed against each line's expectation")
    log(f"    {'tier':<8}{'n':>6}{'observed':>11}{'trailing line':>15}{'forecast line':>15}   ($M at a $95.5M cap)")
    for t, g in d.groupby("tier", observed=True):
        log(f"    {t:<8}{len(g):>6}{g['cap_pct'].mean() * cap / 1e6:>11.2f}{g['e0'].mean() * cap / 1e6:>15.2f}"
            f"{g['e1'].mean() * cap / 1e6:>15.2f}")

    # ---- 5. the RFA qualify rates, both ways ------------------------------------
    import skater_forward_projection as SFP
    import rfa_terminal_value as RTV
    sp0 = SFP.SkaterProjector(model="xNPV 0")
    sp1 = SFP.SkaterProjector(model="xNPV 1")
    sp1._forecaster = fc                       # the same page fits
    q0, q1 = RTV.TerminalValuer(sp0), RTV.TerminalValuer(sp1)
    log("\n[5] RFA qualify rates (D14(c)), P(qualified) by quality bucket at the decision:")
    log(f"    {'bucket':<10}{'on trailing total (xNPV 0)':>30}{'on xNPV 1 forecast':>26}")
    for bkt in ("star", "regular", "fringe", "negative"):
        log(f"    {bkt:<10}{q0.qualify_p.get(bkt, float('nan')):>22.3f} (n {q0.qualify_n.get(bkt, 0):>4})"
            f"{q1.qualify_p.get(bkt, float('nan')):>18.3f} (n {q1.qualify_n.get(bkt, 0):>4})")

    # ---- 6. write -------------------------------------------------------------
    out = dict(model="xNPV 1", fit_on="xNPV 1 WAR if he plays, valuation season, page = start year",
               alpha=f1["alpha"], beta=f1["beta"], beta_d_add=f1["beta_d_add"],
               beta_d=f1["beta"] + f1["beta_d_add"], sigma=f1["sigma"], n=int(len(d)),
               rows_fingerprint=fp, converged=bool(f1["converged"]),
               script=f"xnpv1_price_line.py v{SCRIPT_VERSION}",
               skater_forecast_version=SF.SCRIPT_VERSION)
    (OUTPUT_DIR / "xnpv1_price_line.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    # ---- v1.1: reproduction guard against the locked line, when there is one ----
    import skater_forward_projection as SFP_
    lock = SFP_.XNPV1_RATE
    if lock is not None:
        gaps = {k: abs(f1[k] - lock[k]) for k in ("alpha", "beta", "beta_d_add")}
        same = (f1["converged"] and max(gaps.values()) <= SVE.TOL_NEW_COEF
                and len(d) == lock["n"] and fp == lock["rows_fingerprint"])
        log(f"\n[guard] against the locked XNPV1_RATE: n {len(d)} (locked {lock['n']}), fingerprint {fp} "
            f"(locked {lock['rows_fingerprint']}), largest coefficient gap {max(gaps.values()):.1e}: "
            f"{'PASS' if same else 'GUARD FAILED'}")
        if not same:
            (OUTPUT_DIR / "xnpv1_price_line_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
            raise SystemExit(1)
    log("\n[6] to lock, in skater_forward_projection.py:")
    log("    XNPV1_RATE = dict(alpha=%.10f, beta=%.10f, beta_d_add=%.10f, n=%d, sigma=%.8f,"
        % (f1["alpha"], f1["beta"], f1["beta_d_add"], len(d), f1["sigma"]))
    log(f"                      rows_fingerprint=\"{fp}\")")
    (OUTPUT_DIR / "xnpv1_price_line_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {OUTPUT_DIR / 'xnpv1_price_line_log.txt'} and {OUTPUT_DIR / 'xnpv1_price_line.json'}")


if __name__ == "__main__":
    main()
