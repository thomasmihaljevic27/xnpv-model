"""term_average_price_line.py -- should the price line be fitted on the forecast over the contract's whole term?
(report only)

ASKED (Thomas, 2026-10-21, note 27 on "Valuing Players, Draft Picks, and Prospects"): "wouldn't you also want to
consider the performance you are expecting to buy? This model has no input for *future projected performance over the
course of the contract*, we are only projecting one year forward instead of over the full term of the deal. It's worth
considering." The design, agreed by Thomas before this run ("Yes: test pricing on the term average of WAR if he plays as
the main version, and the average with the chance of playing beside it, held out as the price-line tests did, on the
new forecast"):

THE THREE VERSIONS (each the price line's own form: cap share = alpha + (beta + beta_D x defence) x X + gamma x years
of term, left-censored at the league minimum, on the same contracts; and each without term beside it)
  first season (today)    X = his forecasted WAR if he plays in the contract's first season, dated at the signing
  term average (main)     X = the average of his forecasted WAR if he plays over every season of the contract, each
                          from the signing page (seasons past the page's fitted range follow the forecast's declared
                          extension, ContractForecaster's cache). Valuation would be unchanged: each season priced on
                          its own forecast times the chance of playing, less the cap hit. The line is straight, so the
                          seasons' prices add up to the term times the price of the average: the line is fitted on the
                          quantity it is applied to.
  term average, expected  X = the average over the term of WAR if he plays TIMES the chance of playing (read at the
                          signing date, contract status as known when he signed). Clubs would pay less for a player
                          they expect to miss seasons. Adopting it would change the valuation (each season priced on
                          expected WAR, the chance of playing no longer multiplying the price): it is reported beside.
  Seasons are averaged without discounting: the line is in cap shares, where 3% cap growth and 3% discounting cancel
  (D11, D17), as the contract value adds its seasons.

THE FORECAST: skater_forecast v2.4 / participation_model v2.0 (Thomas's audit decisions, 2026-10-21), not yet locked.
The rows are xnpv1_price_line.run's on this forecast (the Stage 3 sample, proven by its size and fingerprint, with a
forecast at the signing), so the first-season version is exactly the line the re-lock would fit.

SCORES (the same rows for every version)
  in sample   the censored log-likelihood (same rows, same outcome, same number of terms: comparable)
  held out    as price_line_spec_tests.py v1.1 does it: players split into 5 groups, each held out in turn, 20 repeats
              (seed 20261005); each version predicts the held-out contracts' expected cap hit; mean RMSE and MAE in $M
              at the 2025-26 cap, and in how many of the 20 repeats each version beats the first-season version
  calibration mean cap hit observed against each version's expected cap hit, by years of term and by forecast tier
  dollars     each version's price per forecasted win (forward, defenceman) and premium per year of term

GUARDS: the Stage 3 sample (xnpv1_price_line.SAMPLE_N, SAMPLE_FINGERPRINT); the term average's first season equals the
price line's forecast row by row (window_forecasts' guard); the first-season version's in-sample fit equals
xnpv1_price_line.run's term-in line on these rows (to 1e-8). TRAILING WEIGHTING (directive 6): every forecast here
reads 50/30/20 (skater_forecast.TRAIL_WEIGHTS); nothing reads a 60/40 total.

HOW TO RUN (repo root, laptop; needs the PuckPedia export as .xlsx and .csv and WAR_with_age.csv; about 20 minutes):
    python 25_TESTS/term_average_price_line.py
Writes 30_OUTPUT/term_average_price_line_log.txt and term_average_price_line_rows.csv.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from scipy import stats

SCRIPT_VERSION = "term_average_price_line.py v1.0 (2026-10-21)"
N_REPEATS, N_FOLDS, SEED = 20, 5, 20261005          # price_line_spec_tests.py's splits
LOG = []
VERSIONS = {"first season (today)": "x_first", "term average (main)": "x_avg",
            "term average, expected": "x_exp"}


def log(s=""):
    print(s, flush=True)
    LOG.append(str(s))


def expected_cap(coef, sigma, Xfull, floor):
    mu = Xfull @ coef
    z = (floor - mu) / sigma
    return floor * stats.norm.cdf(z) + mu * (1 - stats.norm.cdf(z)) + sigma * stats.norm.pdf(z)


def main():
    import skater_forecast as SF
    import skater_value_engine as SVE
    import xnpv1_price_line as XPL
    from price_line_spec_tests import window_forecasts
    cap = SVE.CAP_CEILING[2025]
    log(f"{SCRIPT_VERSION}; skater_forecast v{SF.SCRIPT_VERSION}; xnpv1_price_line v{XPL.SCRIPT_VERSION}")
    assert SF.TRAIL_WEIGHTS == (0.5, 0.3, 0.2)

    sk = XPL.stage3_sample()
    fp0 = XPL.fingerprint(sk)
    assert len(sk) == XPL.SAMPLE_N and fp0 == XPL.SAMPLE_FINGERPRINT, (len(sk), fp0)               # GUARD
    log(f"Stage 3 sample: {len(sk):,} contracts, fingerprint {fp0} (the locked sample: PASS)")
    quiet = XPL.log
    XPL.log = lambda s="": None
    try:
        fc = SF.ContractForecaster()
        d, fp, free, tin = XPL.run(sk, fc, cap)
    finally:
        XPL.log = quiet
    d = d.reset_index(drop=True)
    L = d["length"].astype(int).to_numpy()
    log(f"rows with a forecast at the signing: {len(d):,} (fingerprint {fp}); term 1 to {L.max()} years, "
        f"mean {L.mean():.2f}")
    wip, pp, gap = window_forecasts(d, fc, int(L.max()))
    log(f"window forecasts: the first season equals the price line's forecast (largest gap {gap:.1e}: PASS)")
    j = np.arange(wip.shape[1])[None, :]
    inside = j < L[:, None]
    d["x_first"] = d["xwar_signed"].to_numpy(float)
    d["x_avg"] = np.where(inside, wip, 0.0).sum(axis=1) / L
    d["x_exp"] = np.where(inside, wip * pp, 0.0).sum(axis=1) / L
    log(f"  mean forecast WAR if he plays: first season {d['x_first'].mean():.3f}; term average {d['x_avg'].mean():.3f}; "
        f"term average x chance of playing {d['x_exp'].mean():.3f}")
    log("  by years of term, mean (first season / term average / term average expected): " + "; ".join(
        f"{t}: {g['x_first'].mean():.2f} / {g['x_avg'].mean():.2f} / {g['x_exp'].mean():.2f} (n {len(g)})"
        for t, g in d.groupby("length")))
    log(f"  correlation of the first season with the term average {np.corrcoef(d['x_first'], d['x_avg'])[0, 1]:.3f}")

    # ---- in sample -------------------------------------------------------------------------------------------------
    fits = {}
    log("\nIN SAMPLE (censored regression on the same contracts; $M at the 2025-26 cap; log-likelihood in cap-share units)")
    for name, xcol in VERSIONS.items():
        for term in (True, False):
            ln = XPL.as_line(XPL.fit_censored(d["cap_pct"], XPL.design(d, xcol, term), d["floor_pct"]), term)
            ln["loglik"] = XPL.loglik(ln, d, xcol)
            fits[(name, term)] = ln
            log(f"  {name:<26}{'with term' if term else 'no term':<10} alpha ${ln['alpha'] * cap / 1e6:6.2f}M  "
                f"per win: forward ${ln['beta'] * cap / 1e6:5.3f}M, defenceman ${(ln['beta'] + ln['beta_d_add']) * cap / 1e6:5.3f}M"
                + (f"  per year of term ${ln['gamma_term'] * cap / 1e6:5.3f}M" if term else " " * 30)
                + f"  log-likelihood {ln['loglik']:,.1f}  converged {ln['converged']}")
    g0 = max(abs(fits[("first season (today)", True)][k] - tin[k]) for k in ("alpha", "beta", "beta_d_add", "gamma_term"))
    assert g0 < 1e-8, g0                                                                                          # GUARD
    log(f"  guard: the first-season version is xnpv1_price_line's term-in line on these rows (gap {g0:.1e}: PASS)")
    b = fits[("first season (today)", True)]["loglik"]
    log("  log-likelihood against the first season, with term: " + "; ".join(
        f"{n} {fits[(n, True)]['loglik'] - b:+,.1f}" for n in VERSIONS if n != "first season (today)"))

    # ---- held out --------------------------------------------------------------------------------------------------
    log(f"\nHELD OUT: players split into {N_FOLDS} groups, each held out in turn, {N_REPEATS} repeats (seed {SEED}); "
        "expected cap hit against the cap hit, $M at the 2025-26 cap")
    players = d["nk"].astype(str).to_numpy()
    uniq = np.unique(players)
    rng = np.random.default_rng(SEED)
    y = d["cap_pct"].to_numpy(float); fl = d["floor_pct"].to_numpy(float)
    specs = [(n, t) for n in VERSIONS for t in (True, False)]
    X = {(n, t): XPL.design(d, VERSIONS[n], t) for n, t in specs}
    rmse = {s: [] for s in specs}; mae = {s: [] for s in specs}
    for rep in range(N_REPEATS):
        fold_of = dict(zip(uniq, rng.permutation(len(uniq)) % N_FOLDS))
        fold = np.array([fold_of[p] for p in players])
        pred = {s: np.full(len(d), np.nan) for s in specs}
        for f_ in range(N_FOLDS):
            tr, te = fold != f_, fold == f_
            for s in specs:
                ft = XPL.fit_censored(y[tr], X[s][tr], fl[tr])
                pred[s][te] = expected_cap(np.asarray(ft["coef"], float), ft["sigma"],
                                           np.column_stack([np.ones(int(te.sum())), X[s][te]]), fl[te])
        for s in specs:
            e = (pred[s] - y) * cap / 1e6
            rmse[s].append(float(np.sqrt(np.mean(e ** 2)))); mae[s].append(float(np.mean(np.abs(e))))
    base_r, base_m = np.array(rmse[("first season (today)", True)]), np.array(mae[("first season (today)", True)])
    log(f"  {'version':<38}{'RMSE':>8}{'MAE':>8}{'beats the first season, with term (RMSE / MAE)':>50}")
    out = []
    for s in specs:
        r_, m_ = np.array(rmse[s]), np.array(mae[s])
        lab = f"{s[0]}, {'with term' if s[1] else 'no term'}"
        tail = "" if s == ("first season (today)", True) else \
            f"{int((r_ < base_r).sum()):>3} of {N_REPEATS} / {int((m_ < base_m).sum()):>2} of {N_REPEATS}"
        log(f"  {lab:<38}{r_.mean():>8.4f}{m_.mean():>8.4f}{tail:>50}")
        out.append({"version": s[0], "term": s[1], "rmse_M": r_.mean(), "mae_M": m_.mean(),
                    "rmse_beats_first": int((r_ < base_r).sum()), "mae_beats_first": int((m_ < base_m).sum()),
                    **{k: fits[s][k] for k in ("alpha", "beta", "beta_d_add", "gamma_term", "sigma", "loglik")}})

    # ---- calibration -----------------------------------------------------------------------------------------------
    log("\nCALIBRATION, with term: mean cap hit observed against each version's expected cap hit ($M at the 2025-26 cap)")
    for n in VERSIONS:
        d[f"e|{n}"] = XPL.expected_cap_line(fits[(n, True)], d, VERSIONS[n])
    log(f"  {'years of term':<14}{'n':>6}{'observed':>10}" + "".join(f"{n[:22]:>24}" for n in VERSIONS))
    for t, g in d.groupby("length"):
        log(f"  {int(t):<14}{len(g):>6}{g['cap_pct'].mean() * cap / 1e6:>10.2f}"
            + "".join(f"{g[f'e|{n}'].mean() * cap / 1e6:>24.2f}" for n in VERSIONS))
    d["tier"] = pd.cut(d["x_first"], [-99, 0, 0.5, 1, 2, 99], labels=["below 0", "0-0.5", "0.5-1", "1-2", "2+"])
    log(f"  {'first-season tier':<14}")
    for t, g in d.groupby("tier", observed=True):
        log(f"  {str(t):<14}{len(g):>6}{g['cap_pct'].mean() * cap / 1e6:>10.2f}"
            + "".join(f"{g[f'e|{n}'].mean() * cap / 1e6:>24.2f}" for n in VERSIONS))
    out_dir = Path(os.environ["OUTPUT_DIR"])
    pd.DataFrame(out).to_csv(out_dir / "term_average_price_line.csv", index=False)
    d[["nk", "start_yr", "length", "signed", "sign_page", "sign_h", "cap_pct", "is_d", "x_first", "x_avg", "x_exp"]].to_csv(
        out_dir / "term_average_price_line_rows.csv", index=False)
    (out_dir / "term_average_price_line_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {out_dir / 'term_average_price_line_log.txt'}, term_average_price_line.csv, _rows.csv")


if __name__ == "__main__":
    main()
