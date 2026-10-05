"""document_figures.py -- every figure the two supervisor documents quote, read off production.

WHY (2026-10-05, plan of record step 6, "update the documents"). `Data, Production, and Aging.docx`
and `Pricing, Control Years, and Contract Value.docx` describe xNPV 1 as it stood before Thomas's
directives 1-5 and open decisions 1-2. Their tables and worked examples (the 2024 page's fitted
equations, Jonathan Marchessault's forecast and contract, the price line) must be re-read off the
code now in production. CLAUDE.md: describe a mechanism from the code that runs it, and take each
run figure from a run, with its row label. MEASUREMENT ONLY: nothing is written but this log.

WHAT IT PRINTS (each section guarded so its numbers are production's, not a re-implementation):
  A. THE FORECAST, 2024 page (fitted on seasons through 2023-24)
     A1 the page: fitted horizons, players forecast, the comparables curve (pool, yardsticks,
        departures filled in)
     A2 Marchessault's three counted seasons and his own rate per 82 (directive 1)
     A3 his comparables at his last counted age: weight total, the league average's share, the
        largest weights
     A4 the start: 65% own + 35% comparables' level + the step to the valuation season
     A5 the walk, the games share and the chance of playing, season by season (the worked table)
     A6 the games-share equation, valuation season, with standard errors clustered by player
     A7 the chance-of-playing equations, valuation season and three seasons out, likewise
     A8 season-WAR bias by trailing tier on the development pages (the star under-forecast,
        re-measured on this forecast as MODEL_DIRECTIVES.md entry 1 says is owed)
  B. THE PRICING
     B1 the term-in price line: standard errors, contracts at the minimum, how the forecast
        relates to the trailing total by position, and term against forecast quality
     B2 Marchessault's contract valued on the 2024 page, season by season (term-in and term-free)
     B3 Michkov's control years valued on the 2025 page (the control-year weight and its chain)
     B4 how many first-season valuations are dated at the signing (open decision 2)
     B5 the control-year weights: skater table and the pooled goalie weight
  A section that fails prints SECTION FAILED with its traceback and the rest still run, so one
  bug does not cost the whole laptop run. A failed section's numbers are not read.

HOW TO RUN (repo root, laptop; about the time of one contract_npv run; needs the PuckPedia
export, the contract spine from the dashboard chain, and WAR_with_age.csv at 99%+ birthdates):
    python 25_TESTS/document_figures.py
Writes 30_OUTPUT/document_figures_log.txt (send it back).
"""
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C

SCRIPT_VERSION = "1.0"
PAGE = 2024                                   # the documents' worked page
# production's player key: the cleaned name + "|" + F/D. The cleaner maps first-name variants
# (Jonathan -> Jon), so the key is "jon marchessault"; his career key is looked up from it in main().
WORKED_PKEY = "jon marchessault|F"
WORKED = None                                 # set in main() from the season table
CTRL_NAME, CTRL_PAGE = "Matvei Michkov", 2025 # the control-year example (an RFA expiry)
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def section(title, fn, *args):
    """Run one section; on an error print SECTION FAILED and carry on (see the docstring)."""
    log("\n" + "=" * 78)
    log(title)
    log("=" * 78)
    try:
        return fn(*args)
    except Exception:                                   # noqa: BLE001
        log("SECTION FAILED -- nothing in this section is to be read:")
        log(traceback.format_exc())
        return None


def cluster_codes(keys):
    """Integer group codes for statsmodels' clustered covariance (one group per career)."""
    return pd.factorize(pd.Series(keys).astype(str))[0]


# =========================================================================== A. the forecast
def a1_page(fc):
    m, iset, p, a = fc.page(PAGE)
    cv = m.curve_
    log(f"page {PAGE}: decision date {iset.as_of}; seasons readable through {int(iset.seasons['syr'].max())}")
    log(f"  players forecast: {len(a):,}; fitted horizons {m.fitted_horizons_[0]}-{m.fitted_horizons_[-1]} "
        f"(each needs {C.MIN_HORIZON_PAIRS}+ training pairs)")
    import aging_curve as AC
    log(f"  comparables curve: {len(cv.players):,} careers, pool of {len(cv.names):,} profiles "
        f"(two consecutive {AC.MIN_GP}+ game seasons each)")
    log(f"  yardstick by position (A1): " + ", ".join(f"{k} {v:.3f}" for k, v in sorted(cv.h_by_pos.items()))
        + f"; pooled median, reporting only, {cv.h:.3f}")
    log(f"  departures filled in at replacement level (C2, C6): {cv.n_imputed:,}")
    log(f"  constants in force: own share K_OWN {__import__('skater_forecast').K_OWN}, curve LAMBDA {AC.LAMBDA}, "
        f"league weight SHRINK_K {AC.SHRINK_K}, level weights {AC.LEVEL_WEIGHTS} by games {AC.LEVEL_BY_GAMES}, "
        f"trailing weights {__import__('skater_forecast').TRAIL_WEIGHTS}, min games {C.MIN_GP} (own) / {AC.MIN_GP} (curve)")
    return m, iset, p, a


def a2_own(fc, page):
    m, iset, p, a = page
    tbl = iset.seasons
    me = tbl[(tbl["career_key"] == WORKED) & tbl["syr"].between(PAGE - 3, PAGE - 1)].sort_values("syr")
    log(f"{WORKED}: his three seasons before {PAGE}-{(PAGE + 1) % 100:02d} (a season counts at {C.MIN_GP}+ games)")
    log(f"  {'season':>8}{'GP':>5}{'WAR':>8}{'WAR/82':>8}{'games share':>13}{'age':>5}")
    for _, r in me.iterrows():
        log(f"  {int(r['syr']):>8}{int(r['GP']):>5}{r['WAR']:>8.3f}{r['WAR_82']:>8.3f}{r['gp_share']:>13.3f}{r['age']:>5.0f}")
    row = a.loc[WORKED]
    # own_82 by hand, from the rows just printed: 50/30/20 x games, rescaled over the counted seasons
    w = dict(zip([PAGE - 1, PAGE - 2, PAGE - 3], (0.5, 0.3, 0.2)))
    cnt = me[me["GP"] >= C.MIN_GP]
    num = sum(w[int(s)] * g * r for s, g, r in zip(cnt["syr"], cnt["GP"], cnt["WAR_82"]))
    den = sum(w[int(s)] * g for s, g in zip(cnt["syr"], cnt["GP"]))
    log(f"  own rate per 82 (games-weighted 50/30/20): by hand {num / den:.4f}; production {row['own_82']:.4f}")
    assert abs(num / den - row["own_82"]) < 1e-9, "the hand calculation does not give production's own rate"
    log(f"  trailing WAR total (plain 50/30/20): {row['tw_WAR']:.4f}; trailing games share {row['tr_gp_share']:.4f}")
    log(f"  seasons counted {int(row['n_seasons'])}; experience {row['exp_seasons']:.0f} seasons; "
        f"age at the valuation season {row['age']:.0f}; last counted season {int(row['last_lag'])} back, at age {row['age_last']:.0f}")
    return row


def a3_comps(fc, page, row):
    import aging_curve as AC
    m, iset, p, a = page
    cv = m.curve_
    key, al = WORKED, int(row["age_last"])
    pl = cv.players[key]
    ss = pl["seasons"]
    idx = next(q for q, s in enumerate(ss) if s["age"] == al)
    lo = idx if not pl["adjacent"].get(al, False) else max(0, idx - (AC.WIN - 1))
    mu, sd = cv.stats[pl["pos"]]
    tv = ((AC._profile(ss[lo: idx + 1], pl["sm"][al]) - mu) / sd) * np.sqrt(cv.fw)
    cand, wt = cv._weights(tv, pl["pos"], al, exclude=key)
    lv = cv.Lser[cand, al - cv.AMIN]
    dl = cv.Dser[cand, al - cv.AMIN]
    has = ~np.isnan(lv)
    ww = wt * has
    glev = cv.glevel.get((pl["pos"], al))
    comp_avg = float(np.nansum(ww * np.where(has, lv, 0.0)) / ww.sum())
    shr = cv._shrunk(lv, cand, wt, glev)
    cn, path = m._path(key, row["pos"], row["age_last"], int(row["last_lag"]))
    log(f"his profile at age {al} (his own level there, games-weighted 50/30/20 over 20+ game seasons): {pl['sm'][al]:.4f}")
    log(f"  same-age, same-position profiles in the pool: {len(cand):,}; with a level at {al}: {int(has.sum()):,}")
    log(f"  weight total {ww.sum():.3f}; league average counts as {AC.SHRINK_K:.0f}, so it carries "
        f"{AC.SHRINK_K / (ww.sum() + AC.SHRINK_K):.1%} of the comparables' level")
    kish = ww.sum() ** 2 / (ww ** 2).sum()
    log(f"  effective number of comparables (Kish, sum(w)^2 / sum(w^2)): {kish:.1f}")
    log(f"  comparables' weighted level {comp_avg:.4f}; league level for {pl['pos']} at {al}: {glev:.4f}; "
        f"blended {shr:.4f} (production's comparables' level {cn:.4f})")
    assert abs(shr - cn) < 1e-9, "the blended level is not production's"
    order = np.argsort(-ww)[:8]
    log(f"  largest weights (name, age-{al} profile weight, level at {al}, change {al}->{al + 1}; "
        "'departed' = filled in at replacement level, 'none' = no 20-game season at the next age):")
    for i in order:
        nm = cv.names[cand[i]]
        tag = "  departed" if (nm, al) in cv.imputed_ else ""
        log(f"    {nm:28s} {ww[i]:6.3f}  {lv[i]:+7.3f}  "
            f"{'   none' if np.isnan(dl[i]) else f'{dl[i]:+7.3f}'}{tag}")
    log(f"  weight within one yardstick of him (w >= exp(-0.5)): {int((ww >= np.exp(-0.5)).sum())} profiles; "
        f"within two (w >= exp(-2)): {int((ww >= np.exp(-2)).sum())}")
    return cn, path


def a4_a5_start_walk(fc, page, row, cn, path):
    import skater_forecast as SF
    m, iset, p, a = page
    g = int(row["last_lag"])
    start = SF.K_OWN * row["own_82"] + (1 - SF.K_OWN) * cn + path[g]
    log(f"start = {SF.K_OWN} x {row['own_82']:.4f} (own) + {1 - SF.K_OWN:.2f} x {cn:.4f} (comparables) "
        f"+ {path[g]:+.4f} (the step from age {row['age_last']:.0f} to {row['age']:.0f}) = {start:.4f}")
    f = p.loc[WORKED]
    assert abs(f.loc[0, "rate_82"] - start) < 1e-9, "the start is not production's valuation-season rate"
    log("\nthe walk and the forecast, season by season (h = 0 is the valuation season):")
    log(f"  {'season':>8}{'age':>5}{'change':>9}{'rate/82':>9}{'games sh':>10}{'WAR if pl':>11}{'chance':>8}{'exp WAR':>9}")
    for h in range(0, 5):
        r = f.loc[h]
        ch = path[g + h] - path[g]
        assert abs(r["rate_82"] - (start + ch)) < 1e-9, f"h={h}: rate is not start + cumulative change"
        log(f"  {PAGE + h:>8}{row['age'] + h:>5.0f}{ch:>+9.3f}{r['rate_82']:>9.3f}{r['gp_share']:>10.3f}"
            f"{r['war_if_plays']:>11.3f}{r['p_play']:>8.3f}{r['war_if_plays'] * r['p_play']:>9.3f}")
    tbl = fc.table
    act = tbl[(tbl["career_key"] == WORKED) & (tbl["syr"] >= PAGE)].sort_values("syr")
    log("  what he did: " + "; ".join(f"{int(r.syr)} {r.WAR:+.2f} WAR in {int(r.GP)} games (rate {r.WAR_82:+.2f})"
                                     for r in act.itertuples()))


def a6_games_share(fc, page):
    import statsmodels.api as sm
    import skater_forecast as SF
    m, iset, p, a = page
    pairs = SF.XNPV1()._training_pairs(iset.seasons, PAGE, C.CANDIDATE_HORIZONS)
    out = {}
    for h in range(0, 6):
        s = pairs[pairs["h"] == h].dropna(subset=["y_gp_share"] + SF.GP_FEATURES)
        X = sm.add_constant(s[SF.GP_FEATURES].to_numpy(float), has_constant="add")
        res = sm.OLS(s["y_gp_share"].to_numpy(float), X).fit(
            cov_type="cluster", cov_kwds={"groups": cluster_codes(s["career_key"])})
        gap = float(np.max(np.abs(res.params - m.gp_coef_[h][1])))
        assert gap < 1e-8, f"h={h}: the refit is not production's games-share line (gap {gap:.1e})"
        out[h] = (res, len(s), s["career_key"].nunique())
    res, n, npl = out[0]
    log(f"games-share line, valuation season: {n:,} player-seasons, {npl:,} players, R-squared {res.rsquared:.3f} "
        "(unweighted; standard errors clustered by player; equals production's fit)")
    names = ["constant"] + SF.GP_FEATURES
    for nm, b, se in zip(names, res.params, res.bse):
        log(f"  {nm:14s} {b:+.4f}  ({se:.4f})")
    log("  coefficient on the trailing games share by season ahead: "
        + ", ".join(f"+{h} {out[h][0].params[1]:.3f}" for h in out))
    log("  coefficient on age - 27 / (age - 27)^2 by season ahead: "
        + ", ".join(f"+{h} {out[h][0].params[4]:+.4f}/{out[h][0].params[6]:+.5f}" for h in out))


def a7_playing(fc, page):
    import statsmodels.api as sm
    import skater_forecast as SF
    m, iset, p, a = page
    pm = m.part_
    table = iset.seasons
    played = table[table["GP"] >= C.MIN_GP]
    act = table.set_index(["career_key", "syr"])["GP"]
    anchors = SF._anchors(played, SF.XNPV1.N_SEASONS)
    for h in (0, 3):
        aa = anchors[anchors["t0"] + h < PAGE]
        d = pm._rows(aa, h)
        ix = pd.MultiIndex.from_arrays([d["career_key"], d["season"]])
        d["y"] = (act.reindex(ix).fillna(0.0).to_numpy() >= C.PARTICIPATION_GP).astype(float)
        d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=pm.features + ["y"])
        use = pm.used_[h]
        X = sm.add_constant(d[use].to_numpy(float), has_constant="add")
        res = sm.Logit(d["y"].to_numpy(float), X).fit(
            disp=0, cov_type="cluster", cov_kwds={"groups": cluster_codes(d["career_key"])})
        gap = float(np.max(np.abs(res.params - pm.coef_[h])))
        log(f"chance of playing, {h} season(s) ahead: {len(d):,} player-seasons, {d['career_key'].nunique():,} players, "
            f"share who played {d['y'].mean():.3f}; columns used {use}")
        log(f"  production's fit is lightly penalised (alpha 1e-4); the unpenalised refit below gives the standard "
            f"errors (clustered by player); largest coefficient gap {gap:.1e}")
        log(f"  rows where contract status is not observable (seasons before {pm.coverage_from_}): "
            f"{int(d['contract_unknown'].sum()):,}; under contract: {int(d['under_contract'].sum()):,}")
        for nm, b, bp, se in zip(["constant"] + use, res.params, pm.coef_[h], res.bse):
            log(f"  {nm:18s} production {bp:+.4f}  refit {b:+.4f}  ({se:.4f})  odds x{np.exp(bp):.3f}")


def a8_tiers(fc):
    """Season-WAR bias by trailing tier on the development pages, scored by the harness on its own
    grid (forecast_harness.subjects_at's 60/40 two-season tier, with its fallbacks). Guarded: the
    whole grid must give the recorded build figures (40,510 rows, season-WAR RMSE 0.8075)."""
    import forecast_harness as H
    import skater_forecast as SF
    d = H.Harness(fc.table).run(SF.XNPV1(), pages=C.DEV_PAGES)
    if "e_war" not in d.columns:
        d = H._score_rows(d)
    rmse = float(np.sqrt((d["e_war"] ** 2).mean()))
    log(f"development pages {C.DEV_PAGES[0]}-{C.DEV_PAGES[-1]}: {len(d):,} rows, {d['career_key'].nunique():,} players; "
        f"season-WAR RMSE {rmse:.4f} (recorded build: 40,510 rows, 0.8075)")
    assert len(d) == 40510 and abs(rmse - 0.8075) < 5e-5, "not the recorded build; nothing below is read"
    rng = np.random.default_rng(0)

    def ci(g):
        # 2,000 resamples of CAREERS (the independent unit), mean bias of the resampled rows
        by = g.groupby("career_key")["e_war"].agg(["sum", "size"])
        s_, n_ = by["sum"].to_numpy(), by["size"].to_numpy()
        draws = []
        for _ in range(2000):
            ix = rng.integers(0, len(by), len(by))
            draws.append(s_[ix].sum() / n_[ix].sum())
        return np.percentile(draws, [2.5, 97.5])
    log("  season-WAR bias (forecast minus outcome; negative = under-forecast), by trailing tier:")
    log(f"    {'tier':9s}" + "".join(f"{'+' + str(h):>8s}" for h in range(6)) + f"{'1-5 out':>10s}{'95% range, 1-5':>20s}{'players':>9s}")
    for t in H.TIER_NAMES:
        g = d[d["tier"] == t]
        by_h = [g.loc[g["h"] == h, "e_war"].mean() for h in range(6)]
        g15 = g[g["h"].between(1, 5)]
        lo, hi = ci(g15)
        log(f"    {t:9s}" + "".join(f"{b:>+8.3f}" for b in by_h)
            + f"{g15['e_war'].mean():>+10.3f}{f'[{lo:+.2f}, {hi:+.2f}]':>20s}{g['career_key'].nunique():>9,}")


# =========================================================================== B. the pricing
def b1_price_line():
    import xnpv1_price_line as XPL
    import skater_forward_projection as SFP
    import skater_value_engine as SVE
    import skater_forecast as SF
    from scipy import stats
    quiet = XPL.log
    XPL.log = lambda s="": None                 # run() logs its own report; it is in the price-line log
    try:
        sk = XPL.stage3_sample()
        fc = SF.ContractForecaster()
        d, fp, free, tin = XPL.run(sk, fc, SVE.CAP_CEILING[2025])
    finally:
        XPL.log = quiet
    L = SFP.XNPV1_RATE
    assert fp == L["rows_fingerprint"] and len(d) == L["n"], "not the locked price-line rows"
    gap = max(abs(tin[k] - L[k]) for k in ("alpha", "beta", "beta_d_add", "gamma_term"))
    assert gap < 1e-8, f"the term-in refit is not the lock (gap {gap:.1e})"
    log(f"term-in price line: {len(d):,} contracts, fingerprint {fp}; equals the lock (gap {gap:.1e})")
    # standard errors: the numerical Hessian of the censored log-likelihood at the fit, in the fitter's
    # own parameters (percentage points of the cap; log sigma), inverted
    y = d["cap_pct"].to_numpy(float) * 100.0
    lo = d["floor_pct"].to_numpy(float) * 100.0
    X = np.column_stack([np.ones(len(y)), XPL.design(d, "xwar_signed", True)])
    cens = y <= lo + 1e-12

    def nll(q):
        mu, sig = X @ q[:-1], np.exp(q[-1])
        return -(np.where(cens, stats.norm.logcdf((lo - mu) / sig),
                          stats.norm.logpdf((y - mu) / sig) - np.log(sig))).sum()
    q0 = np.array([L["alpha"], L["beta"], L["beta_d_add"], L["gamma_term"]]) * 100.0
    q0 = np.append(q0, np.log(L["sigma"] * 100.0))
    k = len(q0)
    eps = np.maximum(np.abs(q0) * 1e-4, 1e-5)
    H = np.empty((k, k))
    for i in range(k):
        for j in range(k):
            ei, ej = np.eye(k)[i] * eps[i], np.eye(k)[j] * eps[j]
            H[i, j] = (nll(q0 + ei + ej) - nll(q0 + ei - ej) - nll(q0 - ei + ej) + nll(q0 - ei - ej)) / (4 * eps[i] * eps[j])
    se = np.sqrt(np.diag(np.linalg.inv(H)))[:4] / 100.0
    cap = SVE.CAP_CEILING[2025]
    for nm, b, s in zip(["alpha", "beta (forwards, per forecast win)", "beta_d_add (defence, added)",
                         "gamma_term (per year of term)"],
                        [L["alpha"], L["beta"], L["beta_d_add"], L["gamma_term"]], se):
        log(f"  {nm:36s} {b * 100:+.3f}% of the cap  (s.e. {s * 100:.3f}%)  ${b * cap / 1e6:+.3f}M at the 2025-26 cap")
    log(f"  sigma {L['sigma'] * 100:.3f}% of the cap")
    log(f"  contracts at the league minimum (censored): {int(cens.sum()):,} of {len(d):,}")
    log(f"  seasons between the signing page and the start: "
        + ", ".join(f"{int(h)}: {n:,}" for h, n in d["sign_h"].value_counts().sort_index().items()))
    # how the forecast relates to the trailing 60/40 total the old line read, overall and by position
    import statsmodels.api as sm
    for lab, g in (("all", d), ("forwards", d[d["is_d"] == 0]), ("defence", d[d["is_d"] == 1])):
        r = sm.OLS(g["xwar_signed"].to_numpy(float), sm.add_constant(g["wWAR"].to_numpy(float))).fit()
        log(f"  forecast on trailing 60/40 total, {lab:9s} n {len(g):,}: {r.params[0]:+.3f} + {r.params[1]:.3f} x trailing")
    log("  mean term and mean forecast, by forecast WAR tier:")
    d["tier"] = pd.cut(d["xwar_signed"], [-99, 0, 0.5, 1, 2, 99], labels=["below 0", "0-0.5", "0.5-1", "1-2", "2+"])
    for t, g in d.groupby("tier", observed=True):
        log(f"    {t:8s} n {len(g):5,}  mean term {g['length'].mean():.2f} years  mean forecast {g['xwar_signed'].mean():+.2f}")
    r = np.corrcoef(d["length"], d["xwar_signed"])[0, 1]
    log(f"  correlation of term with the forecast: {r:.3f}")


def b_engine():
    import contract_npv as CN
    return CN.NPVEngine()


def b2_worked_contract(eng):
    import skater_forward_projection as SFP
    sp = eng.sp
    rows = sp.spine[(sp.spine["nk"] == WORKED_PKEY) & (sp.spine["season_start"] == PAGE)]
    pid = int(rows.iloc[0]["player_id"])
    aod = eng.first_season_as_of(pid, PAGE)
    d, s = eng.npv(pid, PAGE, aod)
    c = d[d["row_type"] == "contract"]
    log(f"{s['full_name']} valued on the {PAGE} page, as of {s['as_of']} (signing-dated: {aod is not None}); "
        f"contracts {s['chain']}, {s['n_contract_seasons']} seasons, price line '{c['price_line'].iloc[0]}', "
        f"term {s['term_years']} years")
    log(f"  {'season':>7}{'k':>3}{'WAR':>7}{'ceiling':>9}{'point':>8}{'floored':>9}{'+unc':>8}{'term prem':>10}"
        f"{'chance':>8}{'cap hit':>9}{'disc':>7}{'PV':>8}{'PV t-free':>10}")
    for _, r in c.iterrows():
        log(f"  {int(r['season_start']):>7}{int(r['k']):>3}{r['projected_war']:>7.3f}{r['cap_ceiling_exante'] / 1e6:>9.3f}"
            f"{r['value_point_estimate'] / 1e6:>8.3f}{r['value_dollars'] / 1e6:>9.3f}{r['uncertainty_correction'] / 1e6:>8.4f}"
            f"{r['term_premium_dollars'] / 1e6:>10.3f}{r['survival']:>8.3f}{r['cost_dollars'] / 1e6:>9.3f}"
            f"{r['discount']:>7.3f}{r['pv_dollars'] / 1e6:>+8.3f}{r['pv_dollars_term_free'] / 1e6:>+10.3f}")
    log(f"  NPV term-in {s['npv_total'] / 1e6:+.3f}M (contract {s['npv_contract'] / 1e6:+.3f}, terminal "
        f"{s['npv_terminal'] / 1e6:+.3f}); term-free {s['npv_total_term_free'] / 1e6:+.3f}M; undiscounted, no chance "
        f"of playing {s['surplus_no_survival'] / 1e6:+.3f}M")
    r0 = c.iloc[0]
    a_, bf, bd, gm, _ = SFP.price_constants()
    slope = bd if str(r0["posgrp"]).startswith("D") else bf
    hand = (a_ + slope * r0["projected_war"] + gm * r0["term_years"]) * r0["cap_ceiling_exante"]
    log(f"  first season by hand: ({a_:.6f} + {slope:.6f} x {r0['projected_war']:.4f} + {gm:.6f} x {int(r0['term_years'])}) "
        f"x {r0['cap_ceiling_exante']:,.0f} = {hand:,.0f} (production's point {r0['value_point_estimate']:,.0f}); "
        f"spread {r0['proj_sd_war']:.4f} WAR")
    assert abs(hand - max(r0["value_point_estimate"], 0)) < 1.0 or r0["floor_bound"], "hand price differs"


def b3_control_years(eng):
    sp = eng.sp
    pid = int(sp.spine[sp.spine["full_name"] == CTRL_NAME].iloc[0]["player_id"])
    tvd, tvs = eng.tv.terminal_value(pid, CTRL_PAGE)
    d, s = eng.npv(pid, CTRL_PAGE)
    log(f"{CTRL_NAME}, valued on the {CTRL_PAGE} page: {tvs['n_control']} control years; chain starts at his chance "
        f"of playing the final contract season, {tvd['chain_start_p_play'].iloc[0]:.4f}")
    log(f"  {'season':>7}{'j':>3}{'WAR':>7}{'value':>8}{'QO':>7}{'surplus':>9}{'weight':>8}{'chain':>8}"
        f"{'counted':>9}{'disc':>7}{'PV':>8}")
    t = d[d["row_type"] == "terminal"].set_index("season_start")
    for _, r in tvd.iterrows():
        tr = t.loc[int(r["control_season"])]
        log(f"  {int(r['control_season']):>7}{int(r['j']):>3}{r['projected_war']:>7.3f}{r['value_dollars'] / 1e6:>8.3f}"
            f"{r['qo_cost'] / 1e6:>7.3f}{r['surplus_dollars'] / 1e6:>+9.3f}{r['control_weight_year']:>8.3f}"
            f"{r['qualify_survival']:>8.4f}{r['surplus_adjusted'] / 1e6:>+9.3f}{tr['discount']:>7.3f}{tr['pv_dollars'] / 1e6:>+8.3f}")
    log(f"  terminal value {s['npv_terminal'] / 1e6:+.3f}M (term-free {s['npv_terminal_term_free'] / 1e6:+.3f}M); "
        f"contract {s['npv_contract'] / 1e6:+.3f}M; total {s['npv_total'] / 1e6:+.3f}M")


def b4_signing_dated():
    sp = pd.read_csv(Path(os.environ["OUTPUT_DIR"]) / "contract_npv_spine.csv")
    sp["july1"] = sp["as_of_date"].astype(str).str.endswith("-07-01")
    for pos, g in sp.groupby("position"):
        log(f"  {pos}: {len(g):,} contracts priced; first season valued at the signing (after 1 July): "
            f"{int((~g['july1']).sum()):,}")
    sk = sp[sp["position"] == "skater"]
    log(f"  skater NPV, term-in against term-free (the term premium's effect), median ${(sk['npv_total'] - sk['npv_total_term_free']).median() / 1e6:+.3f}M, "
        f"by term years: " + ", ".join(f"{int(t)}y {g['npv_total'].median() / 1e6:+.2f}/{g['npv_total_term_free'].median() / 1e6:+.2f}"
                                        for t, g in sk.groupby("term_years")))


def b5_weights(eng):
    tv = eng.tv
    log(f"  {'bucket':10s}{'P(qualified)':>14}{'n':>7}{'P(plays | q)':>14}{'n':>6}{'weight a year':>15}")
    for b in ("star", "regular", "fringe", "negative"):
        log(f"  {b:10s}{tv.qualify_p[b]:>14.3f}{tv.qualify_n[b]:>7,}{tv.plays_given_q[b]:>14.3f}"
            f"{tv.plays_given_q_n[b]:>6,}{tv.qualify_p[b] * tv.plays_given_q[b]:>15.3f}")
    log(f"  goalies, pooled: {eng.g_control_n[0]} decisions, {eng.g_control_n[1]} qualified; "
        f"{eng.g_qualify_p:.3f} x {eng.g_plays_given_q:.3f} = {eng.g_control_weight:.3f} a year")


def main():
    import skater_forecast as SF
    global WORKED
    log(f"document_figures.py v{SCRIPT_VERSION}; skater_forecast v{SF.SCRIPT_VERSION}")
    fc = SF.ContractForecaster()
    WORKED = fc.career_of[WORKED_PKEY]
    log(f"worked player: {WORKED_PKEY} -> career {WORKED}")
    page = section(f"A1. the {PAGE} page", a1_page, fc)
    if page is not None:
        row = section("A2. the worked player's own rate", a2_own, fc, page)
        if row is not None:
            got = section("A3. his comparables", a3_comps, fc, page, row)
            if got is not None:
                section("A4-A5. the start and the walk", a4_a5_start_walk, fc, page, row, *got)
        section("A6. the games-share line", a6_games_share, fc, page)
        section("A7. the chance of playing", a7_playing, fc, page)
    section("A8. bias by trailing tier, development pages", a8_tiers, fc)
    section("B1. the term-in price line", b1_price_line)
    eng = section("B0. the contract engine (builds the spine, the qualify rates and the goalie weight)", b_engine)
    if eng is not None:
        section("B2. the worked contract", b2_worked_contract, eng)
        section("B3. the control-year example", b3_control_years, eng)
        section("B5. the control-year weights", b5_weights, eng)
    section("B4. first seasons dated at the signing (from the last contract_npv run's spine)", b4_signing_dated)
    p = Path(os.environ["OUTPUT_DIR"]) / "document_figures_log.txt"
    p.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
