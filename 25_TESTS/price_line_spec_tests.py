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

v1.1 (2026-10-05, Thomas's choices on the v1.0 results, made before this run):
  - the length premium: before choosing a shape, test ONE step -- a separate premium for players
    forecast below replacement, one premium for everyone else (one added term at the existing 0-win
    group edge, not a searched threshold). Reported beside the per-group premium, with the
    likelihood-ratio test of the per-group premium against the one step (do the two extra terms add
    anything?) and the held-out comparison of the two;
  - one price line for RFA and UFA signings (the RFA variant stays in the report as v1.0 ran it);
  - the hidden-quality follow-up: the v1.0 test, with the unplayed seasons counted as zero and the
    first-season forecast as the control, changes two things at once against what the line prices.
    Each is now varied alone and together (CLAUDE.md: score each part alone and in combination):
      outcome  "zeros in"     average over the K seasons, a season with no NHL games at 0 (v1.0);
               "played only"  average over the seasons he played (1+ NHL games in the season table)
                              and the measure has a value; a contract with none drops out;
      control  "first season, if he plays"  the signing-dated forecast of the first season (v1.0);
               "window, if he plays"        the same forecast averaged over the K seasons;
               "window, expected"           the K-season average of WAR if he plays x the chance
                              of playing, the chance read at the signing date (contract status as
                              known when he signed, p_play_signed).
    A reproduction guard holds the v1.0 cell (zeros in, first season) to the recorded figures.

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
     many of the 20 repeats the variant beats the locked specification. The fold split depends only on
     the seed and the players, so v1.0's rows are reproduced exactly (guarded against the recorded
     figures) and the one-step premium is scored on the same splits.

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

SCRIPT_VERSION = "1.1"
CAP = None                          # 2025-26 ceiling, set in main()
PRORATION = {2019: 82 / 70, 2020: 82 / 56}   # July's D20 proration of the two short seasons
GOALS_PER_WIN = 5.903
K_MAIN, K_LEGS = 3, (2, 4)
LAST_SEASON = 2025                   # last season with an outcome (Game Value and WAR)
N_REPEATS, N_FOLDS, SEED = 20, 5, 20261005
GROUP_EDGES = [-np.inf, 0.0, 1.0, 2.0, np.inf]
GROUP_NAMES = ["below 0", "0 to 1", "1 to 2", "2 or more"]
LOG = []
ONE_STEP = "one step: premium below replacement"
BY_GROUP = "length premium by forecast group"
# v1.0's recorded figures (00_STATE/sessions/2026-10-04c.md, run 2026-10-05); this run must give them back
RECORDED_HELD_OUT = {"locked specification": (1.2809, 0.9234), "length x forecast (one term)": (1.2755, 0.9173),
                     BY_GROUP: (1.2712, 0.9150), "separate RFA line": (1.2787, 0.9198)}
RECORDED_LL = {BY_GROUP: 4544.8, "length x forecast (one term)": 4531.9}
RECORDED_F = {"GV-adj (headline)": -0.0321, "Bacon WAR": 0.0793}       # K = 3, zeros in, first season
CONTROLS = ("first season, if he plays", "window, if he plays", "window, expected")
OUTCOMES = ("zeros in", "played only")


def near(a, b, dp):
    """Recorded figures are rounded; a reproduction matches within one unit of the last place."""
    return abs(a - b) <= 1.01 * 10 ** (-dp)


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
        BY_GROUP: {f"years x [{g}]": yrs * (grp == g) for g in GROUP_NAMES[1:]},
        ONE_STEP: {"years x [0 or more]": yrs * (w >= 0.0)},
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
    if name == ONE_STEP:
        return (f"length premium a season per year: below 0 {c['gamma'] * CAP / 1e6:.3f}M, 0 or more "
                f"{(c['gamma'] + c['years x [0 or more]']) * CAP / 1e6:.3f}M")
    if name == BY_GROUP:
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
    out, lls = {}, {}
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
        lls[name] = ll
    for name, rec in RECORDED_LL.items():
        assert near(lls[name], rec, 1), f"{name}: log-likelihood {lls[name]:.2f}, recorded {rec}"
    log(f"\n  reproduction: the v1.0 log-likelihoods come back ({', '.join(f'{k} {lls[k]:,.1f}' for k in RECORDED_LL)})")
    lr = 2 * (lls[BY_GROUP] - lls[ONE_STEP])
    df_ = len(out[BY_GROUP]) - len(out[ONE_STEP])
    log(f"  per-group premium against the one step: gain {lls[BY_GROUP] - lls[ONE_STEP]:+.1f}, LR {lr:.2f} on "
        f"{df_} df, p {float(stats.chi2.sf(max(lr, 0.0), df_)):.4f} (do the separate 0-1, 1-2 and 2+ premiums add "
        "anything once below-replacement players have their own?)")
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
    for k, (rr, mm) in RECORDED_HELD_OUT.items():
        assert near(np.mean(rmse[k]), rr, 4) and near(np.mean(mae[k]), mm, 4), \
            f"{k}: held out {np.mean(rmse[k]):.5f} / {np.mean(mae[k]):.5f}, recorded {rr} / {mm}"
    log("  reproduction: the v1.0 held-out figures come back (" +
        ", ".join(f"{k} {np.mean(rmse[k]):.4f}/{np.mean(mae[k]):.4f}" for k in RECORDED_HELD_OUT) + ")")
    log(f"  {'specification':36s}{'RMSE':>9s}{'MAE':>9s}{'beats locked (RMSE)':>22s}{'(MAE)':>9s}")
    b_r, b_m = np.array(rmse["locked specification"]), np.array(mae["locked specification"])
    for k in specs:
        r_, m_ = np.array(rmse[k]), np.array(mae[k])
        tail = ("" if k == "locked specification" else
                f"{int((r_ < b_r).sum()):>13} of {N_REPEATS}{int((m_ < b_m).sum()):>5} of {N_REPEATS}")
        log(f"  {k:36s}{r_.mean():>9.4f}{m_.mean():>9.4f}{tail:>31s}")
    s_r, s_m = np.array(rmse[ONE_STEP]), np.array(mae[ONE_STEP])
    g_r, g_m = np.array(rmse[BY_GROUP]), np.array(mae[BY_GROUP])
    log(f"  one step against the per-group premium, same splits: one step lower RMSE in {int((s_r < g_r).sum())} "
        f"of {N_REPEATS}, lower MAE in {int((s_m < g_m).sum())} of {N_REPEATS}; mean gap RMSE "
        f"{(s_r - g_r).mean() * 1e3:+.1f}k, MAE {(s_m - g_m).mean() * 1e3:+.1f}k a contract")


# =========================================================================== length and hidden quality
def outcomes(fc):
    """Realized wins a season by (nhl_id, season) from Game Value, and by (career_key, season) from
    Bacon WAR, each with the two short seasons on an 82-game basis as July did for Game Value; and
    NHL games by (career_key, season) from the season table, which says whether he played."""
    import gv_4b_circularity_check as P
    gv = P.load_gv_side()                      # gv_adj_wins, 5.903 goals a win
    gv["w"] = gv["gv_adj_wins"] * gv["season_start"].map(PRORATION).fillna(1.0)
    gv_lut = gv.set_index(["nhl_id", "season_start"])["w"].to_dict()
    war_lut = fc.table.groupby(["career_key", "syr"])["WAR"].sum().to_dict()
    # a traded player's season can sit on more than one row; games are summed over them
    gp_lut = fc.table.groupby(["career_key", "syr"])["GP"].sum().to_dict()
    return gv_lut, war_lut, gp_lut


def window_forecasts(d, fc, kmax):
    """For each contract, the signing-dated forecast for its first kmax seasons: WAR if he plays and
    the chance of playing, both from the signing page (sign_page, seasons sign_h .. sign_h+kmax-1
    ahead), the chance read at the signing date (contract status as known when he signed). Batched by
    page through the same calls ContractForecaster.forecast makes one player at a time."""
    wip = np.full((len(d), kmax), np.nan)
    pp = np.full((len(d), kmax), np.nan)
    ck = d["nk"].map(fc.career_of).to_numpy()
    pages = d["sign_page"].astype(int).to_numpy()
    hs = d["sign_h"].astype(int).to_numpy()
    dates = pd.to_datetime(d["signed"]).to_numpy()
    for page in np.unique(pages):
        idx = np.flatnonzero(pages == page)
        m, iset, pr, _a = fc.page(int(page))
        hmax = int(hs[idx].max()) + kmax - 1
        assert hmax <= fc.MAX_H, f"page {page}: window reaches {hmax} seasons ahead, past the cache"
        sig = m.p_play_signed(iset, ck[idx], list(range(hmax + 1)), dates[idx])
        for r, i in enumerate(idx):
            for j in range(kmax):
                h = hs[i] + j
                wip[i, j] = float(pr.loc[(ck[i], h), "war_if_plays"])
                pp[i, j] = float(sig[h][r])
    # alignment guard: the window's first season is the forecast the price line was fitted on
    gap = np.nanmax(np.abs(wip[:, 0] - d["xwar_signed"].to_numpy(float)))
    assert gap < 1e-9, f"window forecasts do not line up with the price-line rows (gap {gap:.1e})"
    assert np.isfinite(wip).all() and np.isfinite(pp).all(), "a window forecast is missing"
    return wip, pp, gap


def hidden_quality(d, fc, base):
    import statsmodels.api as sm
    bn, bc = base[0], base[1]
    beta, gamma = bc[1], bc[3]
    log("\n1. LENGTH AND HIDDEN QUALITY: does length predict realized production beyond the forecast?")
    log(f"   s = f x beta / gamma, with the locked line's beta {beta * 100:.4f}% and gamma {gamma * 100:.4f}% "
        f"(forwards' price per win): the share of the length premium realized production accounts for")
    log("   f: extra realized wins a season per year of length, holding the control fixed; start-year "
        "indicators, standard errors clustered by player")
    gv_lut, war_lut, gp_lut = outcomes(fc)
    d = d.copy()
    d["nhl_id"] = pd.to_numeric(d["nhl_id"], errors="coerce")
    d["career_key"] = d["nk"].map(fc.career_of)
    kmax = max((K_MAIN,) + K_LEGS)
    wip, pp, gap = window_forecasts(d, fc, kmax)
    log(f"   window forecasts: {len(d):,} contracts x {kmax} seasons from the signing page; the first season "
        f"equals the price line's forecast (largest gap {gap:.1e}); mean chance of playing by season of the "
        "window " + ", ".join(f"{pp[:, j].mean():.3f}" for j in range(kmax)))
    pos = {i: n for n, i in enumerate(d.index)}
    for K in (K_MAIN,) + K_LEGS:
        s = d[(d["start_yr"].astype(int) + K - 1 <= LAST_SEASON)].copy()
        rows = np.array([pos[i] for i in s.index])
        s["c_first"] = s["xwar_signed"].astype(float)
        s["c_window_if"] = wip[rows, :K].mean(axis=1)
        s["c_window_exp"] = (wip[rows, :K] * pp[rows, :K]).mean(axis=1)
        ctrl_col = dict(zip(CONTROLS, ("c_first", "c_window_if", "c_window_exp")))
        log(f"\n  K = {K} (contracts whose first {K} seasons are all observable, starts through "
            f"{LAST_SEASON - K + 1})")
        log(f"    {'outcome':12s} {'control':28s} {'n':>6s} {'players':>8s}  {'control coef':>12s}  "
            f"{'f':>8s} {'95% interval':>20s}  {'share s':>8s}")
        for lab, key, lut in (("GV-adj (headline)", "nhl_id", gv_lut), ("Bacon WAR", "career_key", war_lut)):
            z_in, played, zeros, nv_drop = [], [], [], 0
            for kk, ckk, y0 in zip(s[key], s["career_key"], s["start_yr"].astype(int)):
                if pd.isna(kk):
                    z_in.append(np.nan); played.append(np.nan); zeros.append(np.nan)
                    continue
                v = [float(lut.get((kk, y0 + j), 0.0)) for j in range(K)]          # v1.0: absent -> 0
                z_in.append(np.mean(v)); zeros.append(sum(1 for x in v if x == 0.0))
                pl = []
                for j in range(K):
                    if gp_lut.get((ckk, y0 + j), 0) >= 1:                          # he played that season
                        if (kk, y0 + j) in lut:
                            pl.append(float(lut[(kk, y0 + j)]))
                        else:
                            nv_drop += 1                                            # played, no value: left out
                played.append(np.mean(pl) if pl else np.nan)
            s["zeros in"], s["played only"], s["zeros"] = z_in, played, zeros
            log(f"    [{lab}] seasons at zero {np.nansum(s['zeros']) / (s['zeros'].notna().sum() * K):.1%}; "
                f"corr(length, zero seasons) {s['length'].astype(float).corr(s['zeros'].astype(float)):+.3f}; "
                f"played seasons with no {lab.split(' (')[0]} value, left out of 'played only': {nv_drop:,}")
            for oc in OUTCOMES:
                for cn in CONTROLS:
                    g = s.dropna(subset=[oc, key, ctrl_col[cn]])
                    mean_len = float(g["length"].mean())
                    X = pd.DataFrame({"control": g[ctrl_col[cn]].astype(float),
                                      "length_c": g["length"].astype(float) - mean_len}, index=g.index)
                    X = pd.concat([X, pd.get_dummies(g["start_yr"].astype(int), prefix="yr",
                                                     drop_first=True).astype(float)], axis=1)
                    X = sm.add_constant(X)
                    grp = pd.factorize(g[key].astype(str))[0]
                    res = sm.OLS(g[oc].astype(float), X).fit(cov_type="cluster", cov_kwds={"groups": grp})
                    f_, lo, hi = res.params["length_c"], *res.conf_int().loc["length_c"]
                    if K == K_MAIN and oc == "zeros in" and cn == CONTROLS[0]:
                        assert near(f_, RECORDED_F[lab], 4), f"{lab}: f {f_:.5f}, v1.0 recorded {RECORDED_F[lab]}"
                    flag = "*" if not lo <= 0 <= hi else " "
                    log(f"    {oc:12s} {cn:28s} {len(g):>6,} {len(np.unique(grp)):>8,}  "
                        f"{res.params['control']:>+12.4f}  {f_:>+8.4f} [{lo:+.4f}, {hi:+.4f}]{flag} "
                        f"{f_ * beta / gamma:>+8.3f}")
    log("\n  * the 95% interval excludes zero. Reproduction: the v1.0 cell (K = 3, zeros in, first season) gives "
        "back the recorded f for both measures.")


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
