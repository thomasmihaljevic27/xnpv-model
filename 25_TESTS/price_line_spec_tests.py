"""price_line_spec_tests.py -- the specification tests on the locked term-in price line (step 7).

WHY (00_STATE/MODEL_DIRECTIVES.md, plan of record step 7). The locked line, XNPV1_RATE, prices a
skater season as cap share = alpha + (beta + beta_D x defence) x forecast WAR + gamma x years of
contract, fitted left-censored at the league minimum on 2,296 contracts with the forecast dated at each
signing. The July specification tests (straight line, contract length, RFA/UFA, stability) were run on
an earlier line fitted to the 60/40 trailing total without length; none has been run on this line. The
length term also raised a question carried to this step: whether the premium per year of length should
depend on the player's quality (long, cheap contracts for mid-level players lead the valuations).

THOMAS'S SETUP (2026-10-05, fixed before any result was seen):
  - length and hidden quality: outcome measured by BOTH Game Value (GV-adj, headline; no Bacon input)
    and Bacon WAR (the quantity the model prices);
  - length and quality on the price side: BOTH shapes, side by side -- one added term (the premium per
    year changes in a straight line with the forecast) and a premium per forecast group (below 0, 0-1,
    1-2, 2+ wins);
  - REPORT ONLY: no variant replaces the locked line by rule; Thomas decides on the results.
MEASUREMENT ONLY: nothing changes.

WHAT IT REPORTS
  0. GUARD. The locked rows (n 2,296, fingerprint b9067879bf72) and the term-in fit equal to the lock.
  1. LENGTH AND HIDDEN QUALITY (July's term premium test, on the forecast). On contracts whose first K
     seasons are all observable (K = 3; K = 2 and 4 as legs): the average realized wins a season over
     the K seasons from the start (a season with no NHL games counts as 0, a fixed window whatever the
     contract's length), regressed on the signing-dated forecast, years of length (centred on the
     sample mean) and start-year indicators, standard errors clustered by player. f is extra realized
     wins a season per year of length beyond the forecast; s = f x beta / gamma is the share of the
     line's length premium that realized production would account for. Outcomes: GV-adj wins (5.903
     goals a win, the two short seasons prorated as July did) and Bacon WAR (season totals as the
     forecast table carries them).
  2. PRICE-SIDE VARIANTS, each the locked specification plus extra columns, fitted the same way on the
     same rows: length x forecast (one term); length premium by forecast group (three terms; below 0 is
     the reference); quadratic in the forecast; a bend at one forecast win; separate RFA line (four
     terms); separate line for contracts starting 2022-2025 against 2018-2021 (four terms). For each:
     the added coefficients with standard errors (numerical Hessian), the censored log-likelihood gain
     and its likelihood-ratio p-value, and what the variant implies in dollars at the 2025-26 cap.
  3. HELD-OUT PREDICTION. Players split into five groups, each held out in turn, repeated 20 times
     (seed 20261005); each variant and the locked specification predict the held-out contracts'
     expected cap hit; reported: mean held-out error (RMSE and MAE, $M at the 2025-26 cap) and in how
     many of the 20 repeats the variant beats the locked specification.

HOW TO RUN (repo root, laptop; needs the PuckPedia export, GAMELOG_DB and WAR_with_age.csv at 99%+;
about fifteen minutes):
    python 25_TESTS/price_line_spec_tests.py
Writes 30_OUTPUT/price_line_spec_tests_log.txt.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from scipy import stats

import forecast_config as C

SCRIPT_VERSION = "1.0"
CAP = None                          # 2025-26 ceiling, set in main()
PRORATION = {2019: 82 / 70, 2020: 82 / 56}   # July's D20 proration of the two short seasons
GOALS_PER_WIN = 5.903
K_MAIN, K_LEGS = 3, (2, 4)
LAST_SEASON = 2025                   # last season with an outcome (Game Value and WAR)
N_REPEATS, N_FOLDS, SEED = 20, 5, 20261005
GROUP_EDGES = [-np.inf, 0.0, 1.0, 2.0, np.inf]
GROUP_NAMES = ["below 0", "0 to 1", "1 to 2", "2 or more"]
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


# =========================================================================== fitting
def nll_factory(y, lo, X):
    """The censored negative log-likelihood in the fitter's own units (percentage points of the cap,
    log sigma last), as xnpv1_price_line.fit_censored writes it."""
    cens = y <= lo + 1e-12

    def nll(q):
        mu, sig = X @ q[:-1], np.exp(q[-1])
        ll = np.where(cens, stats.norm.logcdf((lo - mu) / sig), stats.norm.logpdf((y - mu) / sig) - np.log(sig))
        return -ll.sum()
    return nll


def fit(d, extra):
    """Fit the locked specification plus the columns in `extra` (a dict name -> array). Returns
    (coefficient names, coefficients in cap share, sigma, log-likelihood, standard errors)."""
    import xnpv1_price_line as XPL
    base = XPL.design(d, "xwar_signed", True)                 # wins, defence x wins, years
    names = ["alpha", "beta", "beta_d_add", "gamma"] + list(extra)
    Xc = np.column_stack([base] + [np.asarray(v, float) for v in extra.values()]) if extra else base
    f = XPL.fit_censored(d["cap_pct"], Xc, d["floor_pct"])
    coef = np.asarray(f["coef"], float)
    q = np.append(coef * 100.0, np.log(f["sigma"] * 100.0))
    y = d["cap_pct"].to_numpy(float) * 100.0
    lo = d["floor_pct"].to_numpy(float) * 100.0
    X = np.column_stack([np.ones(len(y)), Xc])
    nll = nll_factory(y, lo, X)
    k = len(q)
    eps = np.maximum(np.abs(q) * 1e-4, 1e-5)
    H = np.empty((k, k))
    for i in range(k):
        for j in range(k):
            ei, ej = np.eye(k)[i] * eps[i], np.eye(k)[j] * eps[j]
            H[i, j] = (nll(q + ei + ej) - nll(q + ei - ej) - nll(q - ei + ej) + nll(q - ei - ej)) / (4 * eps[i] * eps[j])
    se = np.sqrt(np.clip(np.diag(np.linalg.inv(H)), 0, None))[:-1] / 100.0
    # back to cap-share units, as XPL.loglik: only an uncensored row's density carries the scale,
    # log(s_pct) = log(s) + log(100), so each adds log(100); a censored row's probability is unit-free
    n_unc = int((y > lo + 1e-12).sum())
    ll_share = -nll(q) + n_unc * np.log(100.0)
    return names, coef, f["sigma"], ll_share, se, f["converged"]


def expected_cap(coef, sigma, Xfull, floor):
    """E[max(y*, floor)] for the censored line: the expected cap share a contract is predicted at."""
    mu = Xfull @ coef
    z = (floor - mu) / sigma
    return floor * stats.norm.cdf(z) + mu * (1 - stats.norm.cdf(z)) + sigma * stats.norm.pdf(z)


# =========================================================================== the variants
def variants(d):
    w = d["xwar_signed"].to_numpy(float)
    yrs = d["length"].to_numpy(float)
    isd = d["is_d"].to_numpy(float)
    rfa = (d["signing_status"].astype(str) == "RFA").to_numpy(float)
    late = (d["start_yr"].astype(int) >= 2022).to_numpy(float)
    grp = pd.cut(d["xwar_signed"], GROUP_EDGES, labels=GROUP_NAMES, right=False).astype(str).to_numpy()
    return {
        "length x forecast (one term)": {"years x forecast": yrs * w},
        "length premium by forecast group": {f"years x [{g}]": yrs * (grp == g) for g in GROUP_NAMES[1:]},
        "quadratic in the forecast": {"forecast squared": w * w},
        "bend at one forecast win": {"max(forecast - 1, 0)": np.maximum(w - 1.0, 0.0)},
        "separate RFA line": {"RFA": rfa, "RFA x forecast": rfa * w, "RFA x defence x forecast": rfa * isd * w,
                              "RFA x years": rfa * yrs},
        "separate 2022-2025 line": {"2022-25": late, "2022-25 x forecast": late * w,
                                    "2022-25 x defence x forecast": late * isd * w, "2022-25 x years": late * yrs},
    }


def implied(name, names, coef):
    """What a variant implies, in dollars at the 2025-26 cap."""
    c = dict(zip(names, coef))
    if name == "length x forecast (one term)":
        return ("length premium a season per year, by forecast: " +
                ", ".join(f"{w:+.0f} win {((c['gamma'] + c['years x forecast'] * w) * CAP / 1e6):.3f}M"
                          for w in (0, 1, 2, 3)))
    if name == "length premium by forecast group":
        out = [f"below 0 {c['gamma'] * CAP / 1e6:.3f}M"]
        out += [f"{g} {((c['gamma'] + c[f'years x [{g}]']) * CAP / 1e6):.3f}M" for g in GROUP_NAMES[1:]]
        return "length premium a season per year, by group: " + ", ".join(out)
    if name == "quadratic in the forecast":
        return ("price per forecast win (forwards) at 0, 1, 2, 3 wins: " +
                ", ".join(f"{((c['beta'] + 2 * c['forecast squared'] * w) * CAP / 1e6):.3f}M" for w in (0, 1, 2, 3)))
    if name == "bend at one forecast win":
        return (f"price per forecast win (forwards): below one win {c['beta'] * CAP / 1e6:.3f}M, above "
                f"{(c['beta'] + c['max(forecast - 1, 0)']) * CAP / 1e6:.3f}M")
    if name == "separate RFA line":
        return (f"RFA against UFA: intercept {c['RFA'] * CAP / 1e6:+.3f}M, per forecast win (F) "
                f"{c['RFA x forecast'] * CAP / 1e6:+.3f}M, per year of length {c['RFA x years'] * CAP / 1e6:+.3f}M")
    if name == "separate 2022-2025 line":
        return (f"2022-25 against 2018-21: intercept {c['2022-25'] * CAP / 1e6:+.3f}M, per forecast win (F) "
                f"{c['2022-25 x forecast'] * CAP / 1e6:+.3f}M, per year of length {c['2022-25 x years'] * CAP / 1e6:+.3f}M")
    return ""


def price_side(d, base):
    import xnpv1_price_line as XPL
    log("\n2. PRICE-SIDE VARIANTS (same rows, same censored fit; dollars at the 2025-26 cap)")
    bn, bc, bs, bll, bse, _ = base
    out = {}
    for name, extra in variants(d).items():
        names, coef, sig, ll, se, conv = fit(d, extra)
        lr = 2 * (ll - bll)
        df_ = len(extra)
        p = float(stats.chi2.sf(max(lr, 0.0), df_))
        log(f"\n  {name}: log-likelihood {ll:,.1f} (locked specification {bll:,.1f}); gain {ll - bll:+.1f}, "
            f"LR {lr:.2f} on {df_} df, p {p:.4f}; converged {conv}")
        for nm, b, s_ in zip(names, coef, se):
            if nm in extra:
                log(f"    {nm:32s} {b * 100:+.4f}% of the cap (s.e. {s_ * 100:.4f}%)  ${b * CAP / 1e6:+.3f}M")
        log(f"    core: gamma {coef[3] * 100:.4f}% (${coef[3] * CAP / 1e6:.3f}M a year), beta {coef[1] * 100:.4f}%, "
            f"beta_D_add {coef[2] * 100:.4f}%, alpha {coef[0] * 100:.4f}%")
        log(f"    {implied(name, names, coef)}")
        out[name] = extra
    return out


# =========================================================================== held-out prediction
def held_out(d, var_extra):
    import xnpv1_price_line as XPL
    log(f"\n3. HELD-OUT PREDICTION: players split into {N_FOLDS} groups, each held out in turn, "
        f"{N_REPEATS} repeats (seed {SEED}); expected cap hit, $M at the 2025-26 cap")
    base_X = XPL.design(d, "xwar_signed", True)
    specs = {"locked specification": {}} | var_extra
    players = d["nk"].astype(str).to_numpy()
    uniq = np.unique(players)
    rng = np.random.default_rng(SEED)
    y = d["cap_pct"].to_numpy(float); fl = d["floor_pct"].to_numpy(float)
    rmse = {k: [] for k in specs}; mae = {k: [] for k in specs}
    for rep in range(N_REPEATS):
        fold_of = dict(zip(uniq, rng.permutation(len(uniq)) % N_FOLDS))
        fold = np.array([fold_of[p] for p in players])
        pred = {k: np.full(len(d), np.nan) for k in specs}
        for f_ in range(N_FOLDS):
            tr, te = fold != f_, fold == f_
            for k, extra in specs.items():
                Xc = np.column_stack([base_X] + [np.asarray(v, float) for v in extra.values()]) if extra else base_X
                ft = XPL.fit_censored(y[tr], Xc[tr], fl[tr])
                Xf = np.column_stack([np.ones(int(te.sum())), Xc[te]])
                pred[k][te] = expected_cap(np.asarray(ft["coef"], float), ft["sigma"], Xf, fl[te])
        for k in specs:
            e = (pred[k] - y) * CAP / 1e6
            rmse[k].append(float(np.sqrt(np.mean(e ** 2)))); mae[k].append(float(np.mean(np.abs(e))))
    log(f"  {'specification':36s}{'RMSE':>9s}{'MAE':>9s}{'beats locked (RMSE)':>22s}{'(MAE)':>9s}")
    b_r, b_m = np.array(rmse["locked specification"]), np.array(mae["locked specification"])
    for k in specs:
        r_, m_ = np.array(rmse[k]), np.array(mae[k])
        tail = ("" if k == "locked specification" else
                f"{int((r_ < b_r).sum()):>13} of {N_REPEATS}{int((m_ < b_m).sum()):>5} of {N_REPEATS}")
        log(f"  {k:36s}{r_.mean():>9.4f}{m_.mean():>9.4f}{tail:>31s}")


# =========================================================================== length and hidden quality
def outcomes(fc):
    """Realized wins a season by (nhl_id, season) from Game Value, and by (career_key, season) from
    Bacon WAR, each with the two short seasons on an 82-game basis as July did for Game Value."""
    import gv_4b_circularity_check as P
    gv = P.load_gv_side()                      # gv_adj_wins, 5.903 goals a win
    gv["w"] = gv["gv_adj_wins"] * gv["season_start"].map(PRORATION).fillna(1.0)
    gv_lut = gv.set_index(["nhl_id", "season_start"])["w"].to_dict()
    war_lut = fc.table.groupby(["career_key", "syr"])["WAR"].sum().to_dict()
    return gv_lut, war_lut


def hidden_quality(d, fc, base):
    import statsmodels.api as sm
    bn, bc = base[0], base[1]
    beta, gamma = bc[1], bc[3]
    log("\n1. LENGTH AND HIDDEN QUALITY: does length predict realized production beyond the forecast?")
    log(f"   s = f x beta / gamma, with the locked line's beta {beta * 100:.4f}% and gamma {gamma * 100:.4f}% "
        f"(forwards' price per win): the share of the length premium realized production accounts for")
    gv_lut, war_lut = outcomes(fc)
    d = d.copy()
    d["nhl_id"] = pd.to_numeric(d["nhl_id"], errors="coerce")
    d["career_key"] = d["nk"].map(fc.career_of)
    for K in (K_MAIN,) + K_LEGS:
        s = d[(d["start_yr"].astype(int) + K - 1 <= LAST_SEASON)].copy()
        for lab, key, lut in (("GV-adj (headline)", "nhl_id", gv_lut), ("Bacon WAR", "career_key", war_lut)):
            vals, zeros = [], []
            for kk, y0 in zip(s[key], s["start_yr"].astype(int)):
                v = [float(lut.get((kk, y0 + j), 0.0)) if pd.notna(kk) else np.nan for j in range(K)]
                vals.append(np.mean(v)); zeros.append(sum(1 for x in v if x == 0.0))
            s["realized"] = vals; s["zeros"] = zeros
            g = s.dropna(subset=["realized", key])
            g = g[g[key].notna()]
            mean_len = float(g["length"].mean())
            X = pd.DataFrame({"forecast": g["xwar_signed"].astype(float),
                              "length_c": g["length"].astype(float) - mean_len}, index=g.index)
            X = pd.concat([X, pd.get_dummies(g["start_yr"].astype(int), prefix="yr", drop_first=True).astype(float)], axis=1)
            X = sm.add_constant(X)
            grp = pd.factorize(g[key].astype(str))[0]
            res = sm.OLS(g["realized"].astype(float), X).fit(cov_type="cluster", cov_kwds={"groups": grp})
            f_, lo, hi = res.params["length_c"], *res.conf_int().loc["length_c"]
            log(f"\n  [{lab}, K = {K}] n {len(g):,} contracts, {len(np.unique(grp)):,} players, start years "
                f"{int(g['start_yr'].min())}-{int(g['start_yr'].max())}; mean length {mean_len:.3f}; "
                f"seasons at zero {g['zeros'].sum() / (len(g) * K):.1%}; corr(length, zero seasons) "
                f"{g['length'].astype(float).corr(g['zeros'].astype(float)):+.3f}")
            log(f"    forecast coefficient {res.params['forecast']:+.4f} (t {res.tvalues['forecast']:+.2f})")
            log(f"    length coefficient f {f_:+.4f} wins a season per year (s.e. {res.bse['length_c']:.4f}); "
                f"95% interval [{lo:+.4f}, {hi:+.4f}] {'excludes' if not lo <= 0 <= hi else 'contains'} zero")
            log(f"    share s {f_ * beta / gamma:+.3f} [{lo * beta / gamma:+.3f}, {hi * beta / gamma:+.3f}]; "
                f"an 8-year contract implies {f_ * (8 - mean_len):+.2f} wins a season beyond its forecast")


def main():
    global CAP
    import xnpv1_price_line as XPL
    import skater_forward_projection as SFP
    import skater_value_engine as SVE
    import skater_forecast as SF
    CAP = SVE.CAP_CEILING[2025]
    log(f"price_line_spec_tests.py v{SCRIPT_VERSION}; skater_forecast v{SF.SCRIPT_VERSION}")
    quiet = XPL.log
    XPL.log = lambda s="": None                 # run() logs its own report (in the price-line log)
    try:
        sk = XPL.stage3_sample()
        fc = SF.ContractForecaster()
        d, fp, free, tin = XPL.run(sk, fc, CAP)
    finally:
        XPL.log = quiet
    L = SFP.XNPV1_RATE
    base = fit(d, {})
    gap = max(abs(base[1][i] - L[k]) for i, k in enumerate(("alpha", "beta", "beta_d_add", "gamma_term")))
    log(f"\n0. GUARD: {len(d):,} contracts (locked {L['n']:,}), fingerprint {fp} (locked {L['rows_fingerprint']}), "
        f"largest coefficient gap to the lock {gap:.1e}")
    assert fp == L["rows_fingerprint"] and len(d) == L["n"] and gap < 1e-8, "not the locked line; nothing below is read"
    ll_lock = XPL.loglik(tin, d, "xwar_signed")
    log(f"   log-likelihood here {base[3]:,.3f}; xnpv1_price_line's own {ll_lock:,.3f}")
    assert abs(base[3] - ll_lock) < 1e-6, "this script's log-likelihood is not the price-line script's"
    for c in ("nhl_id", "signing_status", "length", "start_yr"):
        assert c in d.columns, f"the price-line rows lack {c}"
    log(f"   locked line: alpha {base[1][0] * 100:.4f}%, beta {base[1][1] * 100:.4f}%, beta_D_add "
        f"{base[1][2] * 100:.4f}%, gamma {base[1][3] * 100:.4f}% (s.e. {base[4][3] * 100:.4f}%); "
        f"log-likelihood {base[3]:,.1f}")
    log(f"   RFA {int((d['signing_status'] == 'RFA').sum()):,}, UFA {int((d['signing_status'] == 'UFA').sum()):,}; "
        f"starts 2018-21 {int((d['start_yr'] < 2022).sum()):,}, 2022-25 {int((d['start_yr'] >= 2022).sum()):,}; "
        "by forecast group: " + ", ".join(
            f"{g} {n:,}" for g, n in pd.cut(d['xwar_signed'], GROUP_EDGES, labels=GROUP_NAMES, right=False)
            .value_counts().reindex(GROUP_NAMES).items()))
    hidden_quality(d, fc, base)
    var_extra = price_side(d, base)
    held_out(d, var_extra)
    p = Path(os.environ["OUTPUT_DIR"]) / "price_line_spec_tests_log.txt"
    p.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
