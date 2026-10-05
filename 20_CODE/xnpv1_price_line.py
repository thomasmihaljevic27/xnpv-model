"""xnpv1_price_line.py -- the market's price per FORECAST win, for pricing xNPV 1.

v2.0 (2026-10-05, plan of record step 6; 00_STATE/MODEL_DIRECTIVES.md directives 4 and 5).
    DIRECTIVE 5: each contract's forecast is dated at its SIGNING, not at its start year. The
    signing date's information set is matched to the valuation page whose 1 July information set is
    identical (page = the newest season readable at the signing, plus one; asserted per contract),
    and the forecast is that page's WAR if he plays h = start year - page seasons ahead. v1.x took
    the start year's page, which for a deal signed before its start reads seasons played after the
    pen moved (30% of this sample in the 2026-09-14 audit).
    DIRECTIVE 4 (details settled 2026-10-05): contract length enters as ONE linear term in years,
    cap share = alpha + (beta + beta_d_add x defence) x forecast wins + gamma_term x years, the same
    left-censored fit; no RFA terms (the RFA/UFA question is the step 7 specification test).
    Four fits on the same rows, so each directive is scored alone and together: start-dated without
    term (v1.x's specification on today's forecast), signing-dated without term (directive 5 alone;
    the TERM-FREE line valuations report beside the term-in one), start-dated with term (directive 4
    alone), signing-dated with term (both; the TERM-IN line to lock). The forecast is
    skater_forecast v2.2, the directed model; the v1.x lock (XNPV1_RATE, fitted on v1.x's forecast)
    is not comparable and is replaced only when Thomas locks this run's lines.

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
    calibrated on xNPV 1's forecast (rfa_terminal_value).

v1.2 (2026-10-02): xNPV 0 archived, so step 5 prints the qualify-rate table on
xNPV 1's forecast only (the trailing-total column was xNPV 0's calibration;
its laptop figures are in the 2026-10-02 session log). The fit is unchanged.

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

SCRIPT_VERSION = "2.0"
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


def fit_line(d, xcol):
    return SVE._fit_censored_interaction(d["cap_pct"].to_numpy(float), d[xcol].to_numpy(float),
                                         d["is_d"].to_numpy(float), d["floor_pct"].to_numpy(float))


def fit_censored(cap_pct, X, floor_pct):
    """Left-censored maximum likelihood on an intercept plus the columns of X, written as
    skater_value_engine._fit_censored_interaction is (outcome in percentage points of the cap,
    BFGS with the same fallbacks, convergence judged on the gradient), for any set of columns.
    Returns (coefficients in cap share, intercept first; sigma; converged; largest gradient).
    Guarded in run(): on the v1 columns it must give the engine's own fit back."""
    from scipy import optimize as _opt
    y = np.asarray(cap_pct, float) * 100.0
    lo = np.asarray(floor_pct, float) * 100.0
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    cens = y <= lo + 1e-12
    k = X.shape[1]

    def neg_ll(p):
        beta, sig = p[:k], np.exp(p[k])
        mu = X @ beta
        ll = np.empty_like(y)
        ll[~cens] = -np.log(sig) + stats.norm.logpdf((y[~cens] - mu[~cens]) / sig)
        ll[cens] = stats.norm.logcdf((lo[cens] - mu[cens]) / sig)
        return 1e10 if not np.all(np.isfinite(ll)) else -ll.sum()

    ols = np.linalg.lstsq(X, y, rcond=None)[0]
    start = np.append(ols, np.log(max(np.std(y - X @ ols), 1e-6)))
    res = _opt.minimize(neg_ll, start, method="BFGS", options=dict(maxiter=20000, gtol=1e-9))
    if not res.success:
        alt = _opt.minimize(neg_ll, res.x, method="Nelder-Mead",
                            options=dict(maxiter=50000, xatol=1e-10, fatol=1e-10))
        if alt.fun < res.fun:
            res = alt
        r2_ = _opt.minimize(neg_ll, res.x, method="BFGS", options=dict(maxiter=20000, gtol=1e-9))
        if r2_.fun <= res.fun:
            res = r2_
    p = res.x.copy()
    h = np.maximum(np.abs(p) * 1e-4, 1e-6)
    grad = np.array([(neg_ll(p + np.eye(len(p))[i] * h[i]) - neg_ll(p - np.eye(len(p))[i] * h[i])) / (2 * h[i])
                     for i in range(len(p))])
    return dict(coef=p[:k] / 100.0, sigma=float(np.exp(p[k]) / 100.0),
                converged=bool(np.max(np.abs(grad)) < 1e-3), grad_max=float(np.max(np.abs(grad))))


def design(d, xcol, term):
    """The columns after the intercept: forecast wins, defence x wins (, years of term)."""
    cols = [d[xcol].to_numpy(float), d["is_d"].to_numpy(float) * d[xcol].to_numpy(float)]
    if term:
        cols.append(d["length"].to_numpy(float))
    return np.column_stack(cols)


def as_line(f, term):
    c = f["coef"]
    out = dict(alpha=float(c[0]), beta=float(c[1]), beta_d_add=float(c[2]), sigma=f["sigma"],
               converged=f["converged"], grad_max=f["grad_max"])
    out["gamma_term"] = float(c[3]) if term else 0.0
    return out


def loglik(line, d, xcol):
    """The censored log-likelihood at a line, in cap-share units (comparable across lines on the
    same rows and outcome)."""
    mu = (line["alpha"] + (line["beta"] + line["beta_d_add"] * d["is_d"].to_numpy(float)) * d[xcol].to_numpy(float)
          + line["gamma_term"] * d["length"].to_numpy(float))
    s = line["sigma"]; cap_ = d["cap_pct"].to_numpy(float); fl = d["floor_pct"].to_numpy(float)
    cens = cap_ <= fl + 1e-12
    return float(np.where(cens, stats.norm.logcdf((fl - mu) / s),
                          stats.norm.logpdf((cap_ - mu) / s) - np.log(s)).sum())


def expected_cap_line(line, d, xcol):
    mu = (line["alpha"] + (line["beta"] + line["beta_d_add"] * d["is_d"].to_numpy(float)) * d[xcol].to_numpy(float)
          + line["gamma_term"] * d["length"].to_numpy(float))
    s = line["sigma"]; fl = d["floor_pct"].to_numpy(float)
    z = (fl - mu) / s
    return fl * stats.norm.cdf(z) + mu * (1 - stats.norm.cdf(z)) + s * stats.norm.pdf(z)


def signing_page(signed):
    """(page, ok): the valuation page whose 1 July information set equals what was readable on the
    signing date. ok is False where no page matches (then the contract is left out and listed)."""
    import information_set as ISET
    if pd.isna(signed):
        return None, False
    readable = ISET.seasons_complete_at(pd.Timestamp(signed).date())
    if not readable:
        return None, False
    page = max(readable) + 1
    at_page = ISET.seasons_complete_at(ISET.decision_date_for_page(page))
    return page, bool(at_page) and max(at_page) == max(readable)


def run(sk, fc, cap):
    """Steps 2-4 on a proven sample; split out so the steps can be exercised on their own."""
    # ---- 2. the forecasts: start-dated (v1.x) and signing-dated (directive 5) ------------------
    sk = sk.copy()
    sk["signed"] = pd.to_datetime(sk["signing_date"], errors="coerce")
    xs, xg, pages, hs, why = [], [], [], [], []
    for nk, yr, sg in zip(sk["nk"], sk["start_yr"], sk["signed"]):
        f = fc.forecast(nk, int(yr), 0)
        xs.append(np.nan if f is None else float(f.iloc[0]["war_if_plays"]))
        page, ok = signing_page(sg)
        h = None if page is None else int(yr) - page
        if not ok or h is None or h < 0:
            xg.append(np.nan); pages.append(page); hs.append(h)
            why.append("no signing date" if pd.isna(sg) else ("page mismatch" if not ok else "signed after start"))
            continue
        g = fc.forecast(nk, page, h)
        xg.append(np.nan if g is None else float(g.iloc[h]["war_if_plays"]))
        pages.append(page); hs.append(h); why.append("" if g is not None else "no forecast at signing")
    sk["xwar_start"], sk["xwar_signed"], sk["sign_page"], sk["sign_h"], sk["why"] = xs, xg, pages, hs, why
    log(f"\n[2] forecasts (skater_forecast v{fc_version()}), WAR if he plays in the contract's first season:")
    log(f"    start-dated (page = start year): {int(sk['xwar_start'].notna().sum()):,} of {len(sk):,}")
    log(f"    signing-dated (directive 5):     {int(sk['xwar_signed'].notna().sum()):,} of {len(sk):,}")
    for w, n in sk.loc[sk["why"] != "", "why"].value_counts().items():
        log(f"      left out, {w}: {n:,}")
    ok_h = sk["sign_h"].dropna().astype(int)
    log("    seasons between the signing page and the start: " +
        ", ".join(f"{h}: {n:,}" for h, n in ok_h.value_counts().sort_index().items()))
    d = sk[sk["xwar_start"].notna() & sk["xwar_signed"].notna()].copy()
    fp = fingerprint(d)
    log(f"    rows with both forecasts (every fit below uses exactly these): {len(d):,}, fingerprint {fp}")

    # ---- 3. four fits on the same rows ------------------------------------------------------
    chk = fit_line(d, "xwar_start")
    mine = as_line(fit_censored(d["cap_pct"], design(d, "xwar_start", False), d["floor_pct"]), False)
    gap = max(abs(chk[k] - mine[k]) for k in ("alpha", "beta", "beta_d_add"))
    assert gap < 1e-7, f"the general fitter does not reproduce the engine's fit (gap {gap:.1e})"
    log(f"\n[3] four fits, same {len(d):,} contracts (the general fitter reproduces the engine's fit, gap {gap:.1e}):")
    fits = {}
    for name, xcol, term in (("start-dated, no term (v1.x specification)", "xwar_start", False),
                             ("SIGNING-dated, no term (directive 5 alone; TERM-FREE line)", "xwar_signed", False),
                             ("start-dated, with term (directive 4 alone)", "xwar_start", True),
                             ("SIGNING-dated, with term (directives 4 + 5; TERM-IN line)", "xwar_signed", True)):
        ln = as_line(fit_censored(d["cap_pct"], design(d, xcol, term), d["floor_pct"]), term)
        ln["loglik"] = loglik(ln, d, xcol); ln["xcol"] = xcol
        fits[name] = ln
        log(f"  {name}")
        log(f"    alpha {ln['alpha']:.10f}  beta_F {ln['beta']:.10f} (${ln['beta'] * cap / 1e6:.3f}M per win)  "
            f"beta_D_add {ln['beta_d_add']:.10f} (defence ${(ln['beta'] + ln['beta_d_add']) * cap / 1e6:.3f}M per win)")
        if term:
            log(f"    gamma_term {ln['gamma_term']:.10f}  (${ln['gamma_term'] * cap / 1e6:.3f}M a season per year of term)")
        log(f"    sigma {ln['sigma']:.8f}  log-likelihood {ln['loglik']:,.1f}  converged {ln['converged']} "
            f"(max gradient {ln['grad_max']:.1e})")
    names = list(fits)
    log("    log-likelihood gains (same rows and outcome): signing-dating "
        f"{fits[names[1]]['loglik'] - fits[names[0]]['loglik']:+,.1f}; term "
        f"{fits[names[2]]['loglik'] - fits[names[0]]['loglik']:+,.1f}; both "
        f"{fits[names[3]]['loglik'] - fits[names[0]]['loglik']:+,.1f}")

    # ---- 4. calibration by tier and by term ---------------------------------------------------
    free, tin = fits[names[1]], fits[names[3]]
    d["e_free"] = expected_cap_line(free, d, "xwar_signed")
    d["e_in"] = expected_cap_line(tin, d, "xwar_signed")
    d["tier"] = pd.cut(d["xwar_signed"], [-99, 0, 0.5, 1, 2, 99], labels=["below 0", "0-0.5", "0.5-1", "1-2", "2+"])
    log(f"\n[4] mean cap share ($M at the 2025-26 cap) observed against each line, signing-dated forecast")
    log(f"    {'by forecast WAR':<16}{'n':>6}{'observed':>10}{'term-free':>11}{'term-in':>9}")
    for t, g in d.groupby("tier", observed=True):
        log(f"    {t:<16}{len(g):>6}{g['cap_pct'].mean() * cap / 1e6:>10.2f}{g['e_free'].mean() * cap / 1e6:>11.2f}"
            f"{g['e_in'].mean() * cap / 1e6:>9.2f}")
    log(f"    {'by term (years)':<16}")
    for t, g in d.groupby("length"):
        log(f"    {int(t):<16}{len(g):>6}{g['cap_pct'].mean() * cap / 1e6:>10.2f}{g['e_free'].mean() * cap / 1e6:>11.2f}"
            f"{g['e_in'].mean() * cap / 1e6:>9.2f}")
    return d, fp, free, tin


def fc_version():
    import skater_forecast as SF
    return SF.SCRIPT_VERSION


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

    import skater_forecast as SF
    fc = SF.ContractForecaster()
    d, fp, free, tin = run(sk, fc, cap)

    # ---- 5. the RFA qualify rates on this forecast (informational; re-measured with the weight) --
    import skater_forward_projection as SFP
    import rfa_terminal_value as RTV
    sp1 = SFP.SkaterProjector()
    sp1._forecaster = fc
    q1 = RTV.TerminalValuer(sp1)
    log(f"\n[5] RFA qualify rates by quality bucket at the decision, bucketed on {q1.qualify_basis}:")
    for bkt in ("star", "regular", "fringe", "negative"):
        log(f"    {bkt:<10}{q1.qualify_p.get(bkt, float('nan')):>8.3f} (n {q1.qualify_n.get(bkt, 0):>4})")

    # ---- 6. write, and the guard against a lock made by this version --------------------------
    def pack(line):
        return dict(alpha=line["alpha"], beta=line["beta"], beta_d_add=line["beta_d_add"],
                    gamma_term=line["gamma_term"], sigma=line["sigma"], n=int(len(d)), rows_fingerprint=fp)
    out = dict(model="xNPV 1", skater_forecast_version=SF.SCRIPT_VERSION, script=f"xnpv1_price_line.py v{SCRIPT_VERSION}",
               fit_on="xNPV 1 WAR if he plays, contract's first season, forecast dated at the signing",
               term_in=pack(tin), term_free=pack(free))
    (OUTPUT_DIR / "xnpv1_price_line.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    lock, lock_free = SFP.XNPV1_RATE, getattr(SFP, "XNPV1_RATE_TERM_FREE", None)
    if lock is not None and "gamma_term" in lock and lock_free is not None:
        bad = []
        for nm, got, lk in (("term-in", tin, lock), ("term-free", free, lock_free)):
            gaps = max(abs(got[k] - lk[k]) for k in ("alpha", "beta", "beta_d_add", "gamma_term"))
            same = got["converged"] and gaps <= SVE.TOL_NEW_COEF and len(d) == lk["n"] and fp == lk["rows_fingerprint"]
            log(f"\n[guard] {nm} against the lock: n {len(d)} (locked {lk['n']}), fingerprint {fp} "
                f"(locked {lk['rows_fingerprint']}), largest gap {gaps:.1e}: {'PASS' if same else 'GUARD FAILED'}")
            bad += [] if same else [nm]
        if bad:
            (OUTPUT_DIR / "xnpv1_price_line_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
            raise SystemExit(1)
    else:
        log("\n[guard] the lock in skater_forward_projection is v1.x's (start-dated, no term, fitted on the v1.x "
            "forecast): not comparable; this run's lines replace it once Thomas locks them.")
    log("\n[6] to lock, in skater_forward_projection.py:")
    for nm, line in (("XNPV1_RATE", tin), ("XNPV1_RATE_TERM_FREE", free)):
        log(f"    {nm} = dict(alpha={line['alpha']:.10f}, beta={line['beta']:.10f}, beta_d_add={line['beta_d_add']:.10f},")
        log(f"        gamma_term={line['gamma_term']:.10f}, n={len(d)}, sigma={line['sigma']:.8f}, rows_fingerprint=\"{fp}\")")
    (OUTPUT_DIR / "xnpv1_price_line_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {OUTPUT_DIR / 'xnpv1_price_line_log.txt'} and {OUTPUT_DIR / 'xnpv1_price_line.json'}")


if __name__ == "__main__":
    main()
