"""
model_doc_figures.py -- the numbers and figures behind "Valuing Players, Draft Picks, and Prospects"
(40_DOCS/Supervisor_Drafts/), v2.0 (2026-10-19).

v2.0 (2026-10-19): the document's second draft, at the level of detail of "Valuing Draft Picks" and "Valuing
Prospects": each decision with the test that settled it, on today's model (the pick curve after the 2026-10-18/19
fixes; the prospect fits without seasons past club control). New: the pick model's alternative shapes scored again on
today's surplus (each draft left out; 2,000 redraws of the drafts), the star value fitted on each draft and its trend,
stars' share of surplus, first-round value against three costs, Brayden Point's seasons, the standings' accuracy for
traded picks; the prospect model's star values, build-up and adopted tables from prospect_values' own functions (one
stacked regression, errors clustered by player), linear against linear-and-squared production and production squared
alone in the adopted structure (the age test's procedure, guarded to reproduce its adopted error), and the outputs of
the prospect tests that read today's rows (fade rules, production, age, age form, arrival timing); retained salary in
the trade under the rule decided for the back-test. v1.0 read the prospect document's numbers.json (2026-10-16).

v3.0 (2026-10-21): the model as it runs after 2026-10-20: the two traded players valued as traded_player_values.py
v1.5 values them (a contract signed on the trade date left out, the retained share inside the acquirer's value, the season
left, LTIR relief); the trade's club sides read from trade_sides.csv (received less given up); the forecast path drawn
from the forecast itself, since Pacioretty's valued contract is now one season. Guarded as before.

Nothing here prices anything new. Every figure is read from the code that runs, and GUARDED against the output it
must reproduce: the traded players and the joined trade file (to $1 or 1e-6), the locked price lines, the 2025-26 page
fits, the star value, the prospect star values and fits, Suzuki's parts, the tests' own adopted arms.

Outputs: OUTPUT_DIR/model_doc/numbers.json, nine figures (fig_*.png), heavy.json (the engine's figures, for --reuse)
and model_doc_figures_log.txt.

Run from the repo root:  python 25_TESTS/model_doc_figures.py           (about 12 minutes: builds the engine)
                         python 25_TESTS/model_doc_figures.py --reuse   (reads heavy.json; everything else)
Run after trade_refresh.py, prospect_fade_rules.py and nhl_arrival_timing.py.
"""

import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "20_CODE"))

import matplotlib                                                  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

SCRIPT_VERSION = "model_doc_figures.py v4.2 (2026-10-27)"   # v4.2: the prospect model with defenceman x production; the prospect document's tests read in; v4.1: figure labels say NPV and xNPV, not surplus (Thomas); v4.0: the model after 2026-10-21 (round-2 notes)
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
FIG = OUT / "model_doc"
FIG.mkdir(exist_ok=True)
REUSE = "--reuse" in sys.argv
LOG = []
TRADE_DATE, TRADE_PAGE = "2018-09-10", 2018
TABLE_PAGE = 2025                       # the page whose games-share and chance-of-playing fits are tabled


def log(s=""):
    print(s)
    LOG.append(str(s))


def guard(name, ok, detail=""):
    log(f"  GUARD {name}: {'PASS' if ok else 'FAILED'} {detail}")
    if not ok:
        (FIG / "model_doc_figures_log.txt").write_text("\n".join(LOG), encoding="utf-8")
        raise SystemExit(f"GUARD FAILED: {name} {detail}")


def tcell(b, se, p):
    return {"b": float(b), "se": float(se), "p": None if p is None or not np.isfinite(p) else float(p)}


log(SCRIPT_VERSION)
N = {"script": SCRIPT_VERSION}


# =====================================================================================================================
# HEAVY PART: the engine, the forecaster's page fits, the price line
# =====================================================================================================================
def heavy():
    import aging_curve as AC
    import contract_npv as CN
    import forecast_config as C
    import skater_forecast as SF
    import skater_forward_projection as SFP
    import xnpv1_price_line as XPL
    H = {}
    eng = CN.NPVEngine()
    fc = eng.sp.forecaster
    H["versions"] = {"contract_npv": CN.SCRIPT_VERSION, "skater_forecast": SF.SCRIPT_VERSION,
                     "price_line_script": XPL.SCRIPT_VERSION}

    # ---- 1. the two traded players, valued as traded_player_values.py values them ---------------------------------
    import trade_page as TP
    tp = pd.read_csv(OUT / "traded_player_values.csv")
    RET = TP.retention()["retention_pct"].to_dict()
    war = pd.read_csv(SRC / "WAR.csv", usecols=["Player"])
    display = {}
    for nm in war["Player"]:
        display.setdefault(AC.career_key(nm), nm)
    H["players"] = {}
    for name in ("Max Pacioretty", "Tomas Tatar"):
        r = tp[(tp["player_name"] == name) & (tp["trade_date"] == TRADE_DATE)].iloc[0]
        pid, page, as_of = int(r["player_id"]), int(r["valuation_page"]), pd.Timestamp(r["as_of"])
        date = pd.Timestamp(TRADE_DATE)
        # traded_player_values.py v1.4: a contract signed on or after the trade date is left out (its signing date masked
        # for this valuation); v1.2: the season left and the retained share
        share, rpct = TP.season_left_share(date, page), float(RET.get(r["asset_id"], 0.0))
        before = eng.npv(pid, page, as_of, first_season_share=share, retained_pct=rpct)[1]   # with the extension
        spine_ = eng.sp.spine[eng.sp.spine["player_id"] == pid]
        masked = {}
        for c in spine_["contract_id"].unique():
            sg = eng.sp.signed.get(int(c))
            if pd.notna(sg) and date <= sg <= as_of:
                masked[int(c)] = sg
                eng.sp.signed[int(c)] = pd.NaT
        det, s = eng.npv(pid, page, as_of, first_season_share=share, retained_pct=rpct)
        eng.sp.signed.update(masked)
        guard(f"{name}: value equals traded_player_values.csv (the engine's value, before LTIR relief)",
              abs(s["npv_total"] - r["npv_total_engine"]) < 1.0 and abs(float(r.get("ltir_relief", 0.0) or 0.0)) < 1e-9,
              f"({s['npv_total']:,.0f} against {r['npv_total_engine']:,.0f})")
        rows = det[det["row_type"] == "contract"]
        seasons = [{k: (None if pd.isna(x[k]) else (float(x[k]) if isinstance(x[k], (int, float, np.floating, np.integer))
                                                    else str(x[k])))
                    for k in ("season_start", "k", "age_at_valuation", "rate_82", "gp_share", "projected_war", "p_play",
                              "value_point_estimate", "uncertainty_correction", "value_dollars", "term_premium_dollars",
                              "cost_dollars", "discount", "pv_dollars", "cap_ceiling_exante", "league_min", "term_years",
                              "contract_id", "is_extension")}
                   for _, x in rows.iterrows()]
        guard(f"{name}: season rows add to the contract value",
              abs(sum(x["pv_dollars"] for x in seasons) - s["npv_contract"]) < 1.0)
        # the start of the forecast, from its parts (skater_forecast.XNPV1._rate)
        nk = eng.sp.spine.loc[eng.sp.spine["player_id"] == pid, "nk"].iloc[0]
        ck = fc.career_of[nk]
        m, iset, p, a = fc.page(page)
        row = a.loc[ck]
        g = int(row["last_lag"])
        cn, path = m._path(ck, row["pos"], float(row["age_last"]), g)
        start = SF.K_OWN * float(row["own_82"]) + (1 - SF.K_OWN) * cn + path[g]
        guard(f"{name}: the start rebuilt from its parts equals the forecast's rate",
              abs(start - float(p.loc[(ck, 0), "rate_82"])) < 1e-9)
        t = fc.table[(fc.table["career_key"] == ck) & (fc.table["syr"].between(page - 3, page - 1))]
        own_seasons = [{"syr": int(z.syr), "GP": float(z.GP), "WAR": float(z.WAR), "WAR_82": float(z.WAR_82),
                        "counted": bool(z.GP >= C.MIN_GP)} for z in t.sort_values("syr").itertuples()]
        # his comparable players at the age of his last counted season (aging_curve.AgingModel, as XNPV1._path)
        M = m.curve_
        P = M.players[ck]
        ss = P["seasons"]
        age_last = int(row["age_last"])
        idx = next(q for q, z in enumerate(ss) if z["age"] == age_last)
        lo = idx if not P["adjacent"].get(age_last, False) else max(0, idx - (AC.WIN - 1))
        mu, sd = M.stats[P["pos"]]
        tv = ((AC._profile(ss[lo: idx + 1], P["sm"][age_last]) - mu) / sd) * np.sqrt(M.fw)
        cand, wt = M._weights(tv, P["pos"], age_last, exclude=ck)
        lv = M.Lser[cand, age_last - M.AMIN]
        ok = ~np.isnan(lv)
        order = np.argsort(-wt)[:5]
        H["players"][name] = {
            "player_id": pid, "page": page, "as_of": str(as_of.date()), "summary": {
                k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                for k, v in s.items() if k in ("npv_total", "npv_contract", "npv_terminal", "n_contract_seasons",
                                               "term_years", "npv_total_term_free", "npv_total_qo")},
            "seasons": seasons, "own_seasons": own_seasons,
            "season_share": float(share), "retained_pct": rpct, "retained_pv": float(s.get("retained_pv", 0.0)),
            "extension_left_out": len(masked), "npv_with_extension": float(before["npv_total"]),
            "forecast_path": [{"k": int(k_), **{c_: float(p.loc[(ck, k_), c_]) for c_ in ("rate_82", "gp_share", "p_play")
                                                if c_ in p.columns}}
                              for k_ in range(6) if (ck, k_) in p.index],
            "own_82": float(row["own_82"]), "tw_WAR": float(row["tw_WAR"]), "age_last": age_last, "last_lag": g,
            "pos": str(row["pos"]), "comparables_level": float(cn), "path": [float(x) for x in path[: g + 8]],
            "start": float(start),
            "comparables": {"n_at_age": int(len(cand)), "weight_sum": float(wt[ok].sum()),
                            "effective_n": float(wt[ok].sum() ** 2 / (wt[ok] ** 2).sum()),
                            "league_level": float(M.glevel.get(("D" if P["pos"] == "D" else "F", age_last), np.nan)),
                            "weighted_mean_level": float(np.sum(wt[ok] * lv[ok]) / wt[ok].sum()),
                            "top": [{"name": display.get(M.names[cand[i]], M.names[cand[i]].title()),
                                     "weight": float(wt[i]), "level": float(lv[i])} for i in order]},
        }
        log(f"  {name}: ${s['npv_total'] / 1e6:,.2f}M at the {page} page; start {start:.3f} WAR per 82 "
            f"(own {row['own_82']:.3f}, comparables {cn:.3f}, step {path[g]:+.3f}); "
            f"{len(cand)} comparables at {age_last}, weights sum {wt[ok].sum():.2f}")
    H["cap"] = {str(y): float(v) for y, v in SFP.CAP_CEILING.items()}
    H["k_own"] = SF.K_OWN
    H["shrink_k"] = AC.SHRINK_K
    H["war_if_plays_mae"] = {str(k): float(v) for k, v in SF.WAR_IF_PLAYS_MAE.items()}

    # ---- 2. control seasons: the rates this run's engine measured ------------------------------------------------
    tv_ = eng.tv
    H["control"] = {"qualify_p": tv_.qualify_p, "qualify_n": tv_.qualify_n, "plays_given_q": tv_.plays_given_q,
                    "plays_given_q_n": tv_.plays_given_q_n,
                    "goalie": {"qualify_p": eng.g_qualify_p, "plays_given_q": eng.g_plays_given_q,
                               "n": list(eng.g_control_n), "weight": eng.g_control_weight}}
    log(f"  control weights: " + ", ".join(f"{b} {tv_.qualify_p[b]:.3f} x {tv_.plays_given_q.get(b, 1.0):.3f}"
                                            for b in ("star", "regular", "fringe", "negative")))

    # ---- 3. the price line: three nested fits on the locked sample ------------------------------------------------
    sk = XPL.stage3_sample()
    guard("price line: the locked sample", len(sk) == XPL.SAMPLE_N and XPL.fingerprint(sk) == XPL.SAMPLE_FINGERPRINT)
    d, fp, free, tin = XPL.run(sk, fc, SFP.CAP_CEILING[2025])
    guard("price line: the fitted rows are the locked rows", fp == SFP.XNPV1_RATE["rows_fingerprint"], fp)
    y = d["cap_pct"].to_numpy(float) * 100.0
    lo_ = d["floor_pct"].to_numpy(float) * 100.0
    war_, isd, term = (d["xwar_signed"].to_numpy(float), d["is_d"].to_numpy(float), d["length"].to_numpy(float))
    specs = {"wins": [war_], "wins + defence": [war_, isd * war_], "wins + defence + term": [war_, isd * war_, term]}
    cens = y <= lo_ + 1e-12
    H["price_line"] = {"n": int(len(d)), "players": int(d["nk"].nunique()), "censored": int(cens.sum()),
                       "fits": {}}

    def ll_vec(pv, X):
        k = X.shape[1]
        beta, sig = pv[:k], np.exp(pv[k])
        mu = X @ beta
        out = np.empty_like(y)
        out[~cens] = -np.log(sig) + stats.norm.logpdf((y[~cens] - mu[~cens]) / sig)
        out[cens] = stats.norm.logcdf((lo_[cens] - mu[cens]) / sig)
        return out

    for nm, cols in specs.items():
        f = XPL.fit_censored(d["cap_pct"], np.column_stack(cols), d["floor_pct"])
        X = np.column_stack([np.ones(len(y))] + cols)
        pv = np.append(f["coef"] * 100.0, np.log(f["sigma"] * 100.0))
        k = len(pv)
        h = np.maximum(np.abs(pv) * 1e-4, 1e-6)
        # scores (per contract) and the Hessian of the summed log-likelihood, by central differences
        S = np.column_stack([(ll_vec(pv + np.eye(k)[j] * h[j], X) - ll_vec(pv - np.eye(k)[j] * h[j], X)) / (2 * h[j])
                             for j in range(k)])
        Hs = np.empty((k, k))
        for j in range(k):
            sp_ = np.column_stack([(ll_vec(pv + np.eye(k)[j] * h[j] + np.eye(k)[i] * h[i], X)
                                    - ll_vec(pv + np.eye(k)[j] * h[j] - np.eye(k)[i] * h[i], X)) / (2 * h[i])
                                   for i in range(k)]).sum(0)
            sm_ = np.column_stack([(ll_vec(pv - np.eye(k)[j] * h[j] + np.eye(k)[i] * h[i], X)
                                    - ll_vec(pv - np.eye(k)[j] * h[j] - np.eye(k)[i] * h[i], X)) / (2 * h[i])
                                   for i in range(k)]).sum(0)
            Hs[j] = (sp_ - sm_) / (2 * h[j])
        Hs = (Hs + Hs.T) / 2
        Hinv = np.linalg.inv(-Hs)
        G = pd.DataFrame(S).groupby(d["nk"].to_numpy()).sum().to_numpy()
        V = Hinv @ (G.T @ G) @ Hinv
        se = np.sqrt(np.diag(V))[: k - 1] / 100.0
        coef = f["coef"]
        zz = coef / se
        names = ["intercept", "per forecast win", "defence addition per win", "per year of term"][: k - 1]
        H["price_line"]["fits"][nm] = {
            "terms": {n_: tcell(coef[i], se[i], 2 * stats.norm.sf(abs(zz[i]))) for i, n_ in enumerate(names)},
            "sigma": f["sigma"], "loglik": float(ll_vec(pv, X).sum()), "converged": f["converged"]}
        log(f"  price line [{nm}]: " + "; ".join(f"{n_} {coef[i]:.6f} ({se[i]:.6f})" for i, n_ in enumerate(names))
            + f"; log-likelihood {ll_vec(pv, X).sum():,.1f}")
    lf, li = H["price_line"]["fits"]["wins + defence"]["terms"], H["price_line"]["fits"]["wins + defence + term"]["terms"]
    TF, TI = SFP.XNPV1_RATE_TERM_FREE, SFP.XNPV1_RATE
    gap_f = max(abs(lf["intercept"]["b"] - TF["alpha"]), abs(lf["per forecast win"]["b"] - TF["beta"]),
                abs(lf["defence addition per win"]["b"] - TF["beta_d_add"]))
    gap_i = max(abs(li["intercept"]["b"] - TI["alpha"]), abs(li["per forecast win"]["b"] - TI["beta"]),
                abs(li["defence addition per win"]["b"] - TI["beta_d_add"]), abs(li["per year of term"]["b"] - TI["gamma_term"]))
    # The locks were kept on 2026-10-18 (Thomas) after the calendar-age fix moved the refit inside the lock's own
    # tolerance (skater_value_engine.TOL_NEW_COEF): the table reports today's refit, the text the locked line that prices.
    import skater_value_engine as SVE
    guard("price line: wins + defence equals XNPV1_RATE_TERM_FREE within the lock's tolerance", gap_f <= SVE.TOL_NEW_COEF,
          f"(gap {gap_f:.1e}, tolerance {SVE.TOL_NEW_COEF:.0e})")
    guard("price line: wins + defence + term equals XNPV1_RATE within the lock's tolerance", gap_i <= SVE.TOL_NEW_COEF,
          f"(gap {gap_i:.1e}, tolerance {SVE.TOL_NEW_COEF:.0e})")
    H["price_line"]["locked"] = {"term_in": {k: float(TI[k]) for k in ("alpha", "beta", "beta_d_add", "gamma_term", "n")},
                                 "term_free": {k: float(TF[k]) for k in ("alpha", "beta", "beta_d_add", "n")},
                                 "gap_term_in": gap_i, "gap_term_free": gap_f, "tolerance": SVE.TOL_NEW_COEF}
    H["price_line"]["signing_log"] = [l.strip() for l in XPL.LOG if "seasons between" in l or "left out" in l
                                      or "start-dated (page" in l or "signing-dated (directive" in l]
    d["e_in"] = XPL.expected_cap_line(tin, d, "xwar_signed")
    d["e_free"] = XPL.expected_cap_line(free, d, "xwar_signed")
    cap25 = SFP.CAP_CEILING[2025]
    H["price_line"]["by_term"] = [{"years": int(t_), "n": int(len(g_)), "observed": float(g_["cap_pct"].mean() * cap25 / 1e6),
                                   "term_free": float(g_["e_free"].mean() * cap25 / 1e6),
                                   "term_in": float(g_["e_in"].mean() * cap25 / 1e6)}
                                  for t_, g_ in d.groupby("length")]
    H["price_line"]["points"] = d[["xwar_signed", "cap_pct", "is_d", "length"]].round(6).to_dict("list")

    # ---- 4. the games share and the chance of playing, on the most recent page ------------------------------------
    m25, iset25, p25, a25 = fc.page(TABLE_PAGE)
    pairs = SF.XNPV1()._training_pairs(iset25.seasons, TABLE_PAGE, C.CANDIDATE_HORIZONS)
    # v4.0: skater_forecast v2.4 (no defenceman term)
    gp_specs = {"games share": ["tr_gp_share"],
                "+ seasons since debut": ["tr_gp_share", "exp_seasons"],
                "+ age, age squared": ["tr_gp_share", "exp_seasons", "age_c", "age_c2"],
                "+ trailing WAR (adopted)": list(SF.GP_FEATURES)}
    H["games_share"] = {"page": TABLE_PAGE, "by_h": {}}
    for hh in range(6):
        s_ = pairs[pairs["h"] == hh].replace([np.inf, -np.inf], np.nan).dropna(subset=["y_gp_share"] + SF.GP_FEATURES)
        grp = pd.factorize(s_["career_key"])[0]
        out = {}
        for nm, cols in gp_specs.items():
            r_ = sm.OLS(s_["y_gp_share"].to_numpy(float), sm.add_constant(s_[cols].to_numpy(float))).fit(
                cov_type="cluster", cov_kwds={"groups": grp})
            out[nm] = {"terms": {c: tcell(r_.params[i + 1], r_.bse[i + 1], r_.pvalues[i + 1]) for i, c in enumerate(cols)}
                       | {"intercept": tcell(r_.params[0], r_.bse[0], r_.pvalues[0])},
                       "r2": float(r_.rsquared), "n": int(len(s_)), "players": int(s_["career_key"].nunique())}
            if nm.endswith("(adopted)"):
                own = m25.gp_coef_[hh]
                gap = float(np.max(np.abs(np.asarray(own[1]) - r_.params)))
                guard(f"games share h={hh}: equals the page's fit", list(own[0]) == cols and gap < 1e-8, f"(gap {gap:.1e})")
        H["games_share"]["by_h"][str(hh)] = out
    PM = m25.part_
    played = iset25.seasons[iset25.seasons["GP"] >= C.MIN_GP]
    anchors = SF._anchors(played, 3)
    act = iset25.seasons.set_index(["career_key", "syr"])["GP"]
    # v4.0: participation_model v2.0 (no age squared, no seasons since debut)
    pp_specs = {"age": ["age"], "+ level, games share, defence": ["age", "level", "gp_share", "is_D"]}
    H["participation"] = {"page": TABLE_PAGE, "by_h": {}, "event_gp": C.PARTICIPATION_GP}
    for hh in range(6):
        a_ = anchors[anchors["t0"] + hh < TABLE_PAGE]
        dd = PM._rows(a_, hh)
        ix = pd.MultiIndex.from_arrays([dd["career_key"], dd["season"]])
        dd["y"] = (act.reindex(ix).fillna(0.0).to_numpy() >= C.PARTICIPATION_GP).astype(float)
        dd = dd.replace([np.inf, -np.inf], np.nan).dropna(subset=PM.features + ["y"])
        used = PM.used_[hh]
        grp = pd.factorize(dd["career_key"])[0]
        out = {}
        for nm, cols in list(pp_specs.items()) + [("+ contract status (adopted)", used)]:
            r_ = sm.Logit(dd["y"].to_numpy(float), sm.add_constant(dd[cols].to_numpy(float), has_constant="add")).fit(
                disp=0, cov_type="cluster", cov_kwds={"groups": grp}, maxiter=200)
            out[nm] = {"terms": {c: tcell(r_.params[i + 1], r_.bse[i + 1], r_.pvalues[i + 1]) for i, c in enumerate(cols)}
                       | {"intercept": tcell(r_.params[0], r_.bse[0], r_.pvalues[0])},
                       "pseudo_r2": float(r_.prsquared), "loglik": float(r_.llf), "n": int(len(dd)),
                       "players": int(dd["career_key"].nunique()), "base": float(dd["y"].mean())}
            if nm.endswith("(adopted)"):
                gap = float(np.max(np.abs(np.asarray(PM.coef_[hh]) - r_.params)))
                guard(f"chance of playing h={hh}: unpenalized fit agrees with the page's", gap < 0.02, f"(gap {gap:.4f})")
                out[nm]["gap_to_page_fit"] = gap
                out[nm]["used"] = list(used)
        H["participation"]["by_h"][str(hh)] = out

    # ---- 5. the aging curve: league-average changes by age and position, and the yardsticks ---------------------
    M25 = m25.curve_
    H["aging"] = {"page": TABLE_PAGE, "gdelta": {f"{p_}|{a_}": float(v) for (p_, a_), v in M25.gdelta.items()},
                  "glevel": {f"{p_}|{a_}": float(v) for (p_, a_), v in M25.glevel.items()},
                  "yardstick": {k_: float(v) for k_, v in M25.h_by_pos.items()}, "pool": int(len(M25.names)),
                  "careers": int(len(M25.players)), "imputed": int(M25.n_imputed)}
    pac = H["players"]["Max Pacioretty"]
    m18 = fc.page(TRADE_PAGE)[0]
    H["aging"]["page_2018_gdelta"] = {f"{p_}|{a_}": float(v) for (p_, a_), v in m18.curve_.gdelta.items()}
    log(f"  aging curve at the {TABLE_PAGE} page: {len(M25.players):,} careers, {len(M25.names):,} comparable entries, "
        f"yardsticks {H['aging']['yardstick']}")
    return H


if REUSE:
    H = json.loads((FIG / "heavy.json").read_text(encoding="utf-8"))
    log(f"  --reuse: heavy.json from {H['versions']}")
else:
    H = heavy()
    (FIG / "heavy.json").write_text(json.dumps(H, indent=1, default=float), encoding="utf-8")
N["heavy"] = H
# The price line's log-likelihoods in cap-share units, as xnpv1_price_line.py reports them (heavy() works in percentage
# points of the cap: each uncensored contract's density differs by log(100)); GUARD: the term-free and term-in values
# equal the price line's own log
PLH = H["price_line"]
n_unc = PLH["n"] - PLH["censored"]
for f_ in PLH["fits"].values():
    f_["loglik_share"] = f_["loglik"] + n_unc * np.log(100.0)
xlog = (OUT / "xnpv1_price_line_log.txt").read_text(encoding="utf-8")
ll_free = float(re.search(r"TERM-FREE line\)\n.*\n\s+sigma [\d.]+\s+log-likelihood ([\d,.]+)", xlog).group(1).replace(",", ""))
ll_in = float(re.search(r"TERM-IN line\)\n.*\n.*\n\s+sigma [\d.]+\s+log-likelihood ([\d,.]+)", xlog).group(1).replace(",", ""))
# today's refit sits inside the lock's tolerance (above), so its log-likelihoods differ slightly from the lock's log of
# 2026-10-14; both are recorded, and the difference must stay small (declared bound: 1.0)
PLH["loglik_locked_log"] = {"term_free": ll_free, "term_in": ll_in}
guard("price line: log-likelihoods within 1.0 of xnpv1_price_line_log.txt",
      abs(PLH["fits"]["wins + defence"]["loglik_share"] - ll_free) < 1.0
      and abs(PLH["fits"]["wins + defence + term"]["loglik_share"] - ll_in) < 1.0,
      f"(today {PLH['fits']['wins + defence']['loglik_share']:.2f} / {PLH['fits']['wins + defence + term']['loglik_share']:.2f};"
      f" log {ll_free} / {ll_in})")


# =====================================================================================================================
# LIGHT PARTS (v2.0)
# =====================================================================================================================
CAP25M = H["cap"]["2025"] / 1e6
N_REDRAW = 2000


def redraw_p(sse_alt, sse_base, draws):
    """One-sided p that `alt` predicts better than `base`: the share of redraws of the drafts in which alt's total
    squared held-out error is NOT lower than base's (the convention of the prospect tests)."""
    return float(np.mean([sse_alt[list(dr)].sum() >= sse_base[list(dr)].sum() for dr in draws]))


# ---- draft picks ------------------------------------------------------------------------------------------------------
pk = pd.read_csv(OUT / "pick_curve_players.csv")
pk = pk[~pk["excluded_deceased"].astype(bool)].copy().reset_index(drop=True)
sc = pd.read_csv(OUT / "pick_curve_scales.csv").set_index("scale_kind")
bac = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")
pk["p_nhler"] = pk["pick"].map(bac["p_nhler"])
assert pk["p_nhler"].notna().all() and pk["p_star"].notna().all()
pk["y"] = pk["surplus"] / 1e6
pk["log_pick"] = np.log(pk["pick"].astype(float))
pk["log_pick_sq"] = pk["log_pick"] ** 2
pk["p_star_sq"] = pk["p_star"] ** 2
SHAPES = {"straight line in draft position": (["pick"], True), "log of draft position": (["log_pick"], True),
          "log of draft position and its square": (["log_pick", "log_pick_sq"], True),
          "star probability (adopted)": (["p_star"], False), "star probability and an intercept": (["p_star"], True),
          "star probability and its square": (["p_star", "p_star_sq"], False),
          "star and NHL-player probabilities": (["p_star", "p_nhler"], False),
          "star probability, draft position and an intercept": (["p_star", "pick"], True)}


def Xof(f, cols, icpt):
    X = f[cols].to_numpy(float)
    return np.column_stack([np.ones(len(f)), X]) if icpt else X


def ols(f, cols, icpt, y="y"):
    return sm.OLS(f[y].to_numpy(float), Xof(f, cols, icpt)).fit(cov_type="HC1")


drafts = sorted(pk["draftYear"].unique())
rng = np.random.default_rng(20261009)
pdraws = [rng.choice(drafts, size=len(drafts), replace=True) for _ in range(N_REDRAW)]
grid = pd.DataFrame({"pick": np.arange(1, 225)})
grid["log_pick"] = np.log(grid["pick"].astype(float)); grid["log_pick_sq"] = grid["log_pick"] ** 2
grid["p_star"] = grid["pick"].map(bac["p_star"]); grid["p_star_sq"] = grid["p_star"] ** 2
grid["p_nhler"] = grid["pick"].map(bac["p_nhler"])
held, shp = {}, {}
for nm, (cols, ic) in SHAPES.items():
    e = np.zeros(len(pk))
    for c in drafts:
        tr, te = pk[pk["draftYear"] != c], pk[pk["draftYear"] == c]
        e[te.index] = te["y"].to_numpy() - Xof(te, cols, ic) @ ols(tr, cols, ic).params
    held[nm] = e
    m = ols(pk, cols, ic)
    curve = Xof(grid, cols, ic) @ m.params
    names = (["intercept"] if ic else []) + cols
    rises = [int(k) for k in range(2, 225) if curve[k - 1] > curve[k - 2] + 1e-12]
    shp[nm] = {"terms": {n_: tcell(m.params[i], m.bse[i], m.pvalues[i]) for i, n_ in enumerate(names)},
               "params": len(names), "rmse_in": float(np.sqrt(np.mean(m.resid ** 2))),
               "held": float(np.sqrt(np.mean(e ** 2))), "at": {str(k): float(curve[k - 1]) for k in (1, 2, 3, 5, 10, 13, 20, 32, 50, 64, 100, 137, 150, 200)},
               "first_rise": rises[0] if rises else None, "curve": [float(x) for x in curve]}
psse = {nm: pd.Series(e ** 2).groupby(pk["draftYear"]).sum() for nm, e in held.items()}
for nm in SHAPES:
    shp[nm]["p_vs_adopted"] = None if nm.endswith("(adopted)") else redraw_p(psse[nm], psse["star probability (adopted)"], pdraws)
STAR = shp["star probability (adopted)"]["terms"]["p_star"]["b"]
guard("pick curve: the adopted shape equals pick_curve_scales.csv main", abs(STAR - sc.loc["main", "scale_M"]) < 1e-9)
avg_at = pk.groupby("pick")["y"].mean()
# an intercept for each draft (the nested table's third column)
D = pd.get_dummies(pk["draftYear"], dtype=float)
m3 = sm.OLS(pk["y"].to_numpy(float), np.column_stack([pk["p_star"].to_numpy(float), D.to_numpy(float)])).fit(cov_type="HC1")
k_ = D.shape[1]
R = np.zeros((k_, 1 + k_)); R[:, 1:] = np.eye(k_)
w0 = m3.wald_test(R, scalar=True)
R2 = np.zeros((k_ - 1, 1 + k_))
for i in range(k_ - 1):
    R2[i, 1 + i], R2[i, 2 + i] = 1, -1
w1 = m3.wald_test(R2, scalar=True)
e3 = np.zeros(len(pk))
for c in drafts:                                   # a left-out draft has no intercept of its own: the others' mean
    tr, te = pk[pk["draftYear"] != c], pk[pk["draftYear"] == c]
    Dt = pd.get_dummies(tr["draftYear"], dtype=float)
    mt = sm.OLS(tr["y"].to_numpy(float), np.column_stack([tr["p_star"].to_numpy(float), Dt.to_numpy(float)])).fit()
    e3[te.index] = te["y"].to_numpy() - (mt.params[0] * te["p_star"].to_numpy() + mt.params[1:].mean())
psse["draft intercepts"] = pd.Series(e3 ** 2).groupby(pk["draftYear"]).sum()
PK = {"n": int(len(pk)), "drafts": len(drafts), "played": int((pk["nhl_seasons"] > 0).sum()),
      "goalies": int(pk["is_goalie"].sum()), "routes": pk["route"].value_counts().to_dict(),
      "shapes": shp, "avg_at": {str(k): float(avg_at.get(k, np.nan)) for k in (1, 2, 3, 5, 10, 13, 20, 32, 50, 64, 100, 200)},
      "avg_curve": [float(avg_at.get(k, np.nan)) for k in range(1, 225)],
      "draft_intercepts": {"star": tcell(m3.params[0], m3.bse[0], m3.pvalues[0]), "rmse_in": float(np.sqrt(np.mean(m3.resid ** 2))),
                           "held": float(np.sqrt(np.mean(e3 ** 2))), "p_vs_adopted": redraw_p(psse["draft intercepts"], psse["star probability (adopted)"], pdraws),
                           "joint_zero": {"chi2": float(w0.statistic), "df": k_, "p": float(w0.pvalue)},
                           "joint_equal": {"chi2": float(w1.statistic), "df": k_ - 1, "p": float(w1.pvalue)},
                           "values": {str(int(c)): float(v) for c, v in zip(D.columns, m3.params[1:])}},
      "sensitivity": {"star": float(sc.loc["sensitivity", "scale_M"]), "se": float(sc.loc["sensitivity", "se_M"])},
      "qo_chain": {"star": float(sc.loc["qo_chain", "scale_M"]), "se": float(sc.loc["qo_chain", "se_M"])},
      "qo_chain_sensitivity": float(sc.loc["qo_chain_sensitivity", "scale_M"]),
      "mean_surplus": float(pk["y"].mean()), "share_zero": float((pk["y"] == 0).mean())}
srt = np.sort(pk["y"].to_numpy())[::-1]
PK["top5"] = {"n": int(round(0.05 * len(srt))), "share": float(srt[: int(round(0.05 * len(srt)))].sum() / srt.sum())}
PK["p_star"] = {str(k): float(bac.loc[k, "p_star"]) for k in (1, 2, 3, 5, 10, 13, 20, 32, 50, 64, 100, 150, 200)}
# stars (Bacon's definition, with 200+ NHL games; pick_star_and_rights_checks.csv), skaters drafted 2007-2015
st = pd.read_csv(OUT / "pick_star_and_rights_checks.csv")[["draftYear", "pick", "star"]]
ss_ = pk.merge(st, on=["draftYear", "pick"], how="inner")
ss_ = ss_[ss_["draftYear"] <= 2015]
top10 = ss_[ss_["pick"] <= 10]
PK["stars"] = {"skaters": int(len(ss_)), "stars": int(ss_["star"].sum()), "share_players": float(ss_["star"].mean()),
               "share_surplus": float(ss_.loc[ss_["star"].astype(bool), "y"].sum() / ss_["y"].sum()),
               "top10_share_players": float(top10["star"].mean()),
               "top10_share_surplus": float(top10.loc[top10["star"].astype(bool), "y"].sum() / top10["y"].sum())}
# one star value for every draft: each draft alone, the equality test, the trend
per = []
for c in drafts:
    f = pk[pk["draftYear"] == c]
    m = ols(f, ["p_star"], False)
    per.append({"draft": int(c), "star": float(m.params[0]), "se": float(m.bse[0]), "n": int(len(f))})
Xd = np.column_stack([pk["p_star"].to_numpy(float) * (pk["draftYear"] == c).to_numpy(float) for c in drafts])
mi = sm.OLS(pk["y"].to_numpy(float), Xd).fit(cov_type="HC1")
Rq = np.zeros((len(drafts) - 1, len(drafts)))
for i in range(len(drafts) - 1):
    Rq[i, i], Rq[i, i + 1] = 1, -1
wq = mi.wald_test(Rq, scalar=True)
pk["p_trend"] = pk["p_star"] * (pk["draftYear"] - 2012)
mt_all = ols(pk, ["p_star", "p_trend"], False)
sub = pk[~pk["draftYear"].isin([2015, 2016])]
mt_sub = ols(sub, ["p_star", "p_trend"], False)
PK["per_draft"] = per
PK["equal_test"] = {"chi2": float(wq.statistic), "df": len(drafts) - 1, "p": float(wq.pvalue)}
PK["trend"] = {"all": tcell(mt_all.params[1], mt_all.bse[1], mt_all.pvalues[1]),
               "without_2015_2016": tcell(mt_sub.params[1], mt_sub.bse[1], mt_sub.pvalues[1])}
log(f"  picks: star value {STAR:.3f}; per-draft {min(p['star'] for p in per):.2f} to {max(p['star'] for p in per):.2f}, equal p "
    f"{wq.pvalue:.4f}; trend {mt_all.params[1]:+.2f} (p {mt_all.pvalues[1]:.3f}), without 2015-16 {mt_sub.params[1]:+.2f} (p {mt_sub.pvalues[1]:.3f})")
for nm in SHAPES:
    log(f"    {nm:<52} held-out {shp[nm]['held']:.4f}  #1 {shp[nm]['at']['1']:.2f}  p vs adopted {shp[nm]['p_vs_adopted']}")
# what first-round picks delivered, and three measures of cost (skaters who played for their drafting club's side)
sea = pd.read_csv(OUT / "pick_curve_seasons.csv")
kept = pk[pk["route"].isin(["same team", "traded first", "signed by the drafting club"]) & (pk["nhl_seasons"] > 0)
          & ~pk["is_goalie"].astype(bool) & (pk["pick"] <= 32)]
agg = sea.groupby(["draftYear", "pick"])[["value_share", "cost_share", "cost_qo_share"]].sum() * CAP25M
kept = kept.join(agg, on=["draftYear", "pick"])
act = pd.read_csv(OUT / "top_pick_control_look.csv").set_index(["draftYear", "pick"])["cost_actual_$M"]
kept["actual"] = [act.get((a, b), np.nan) for a, b in zip(kept["draftYear"], kept["pick"])]
PK["first_round"] = []
for lo, hi in ((1, 10), (11, 15), (16, 32)):
    g = kept[kept["pick"].between(lo, hi)]
    PK["first_round"].append({"lo": lo, "hi": hi, "n": int(len(g)), "value": float(g["value_share"].mean()),
                              "cost_qo": float(g["cost_qo_share"].mean()), "cost_arb": float(g["cost_share"].mean()),
                              "cost_actual": float(g["actual"].mean()), "n_actual": int(g["actual"].notna().sum())})
# a worked drafted player (v4.0; Thomas, 2026-10-21: Montreal received the 50th pick of 2019, so a player taken 50th, of
# Colton Sissons (2012) and Jordan Greenway (2015) "whoever has the higher games played"; Milan Lucic, 2006, is outside
# the 2007-2017 drafts): NHL games from WAR.csv, every season
_war = pd.read_csv(SRC / "WAR.csv", usecols=["Player", "GP"])
_cand = {"Colton Sissons": (2012, 50), "Jordan Greenway": (2015, 50)}
_gp = {nm: int(_war.loc[_war["Player"] == nm, "GP"].sum()) for nm in _cand}
_who = max(_gp, key=_gp.get)
_dy, _pk = _cand[_who]
log(f"  worked pick: NHL games {_gp}; {_who} ({_dy}, #{_pk})")
pt = pk[(pk["draftYear"] == _dy) & (pk["pick"] == _pk)].iloc[0]
ps_ = sea[(sea["draftYear"] == _dy) & (sea["pick"] == _pk)].sort_values("season")
guard("worked pick: his seasons add to his surplus", abs(ps_["surplus_2025_cap"].sum() / 1e6 - pt["y"]) < 1e-6)
PK["point"] = {"name": _who, "draft": int(_dy), "pick": int(_pk), "nhl_games": _gp,
               "window_end": int(pt["window_end"]), "route": pt["route"], "p_star": float(pt["p_star"]), "surplus": float(pt["y"]),
               "surplus_qo": float(pt["surplus_qo"] / 1e6),
               "seasons": [{"season": int(r.season), "gp": float(r.gp), "war82": float(r.war_82), "elc": bool(r.in_entry_level),
                            "arb": bool(r.arb_eligible), "arb_war": None if pd.isna(r.arb_market_war) else float(r.arb_market_war),
                            "value": float(r.value_share * CAP25M), "cost": float(r.cost_share * CAP25M),
                            "cost_qo": float(r.cost_qo_share * CAP25M), "surplus": float(r.surplus_2025_cap / 1e6)}
                           for r in ps_.itertuples()]}
# traded picks: how each draft position is known, and how close the standings get
tpk = pd.read_csv(OUT / "traded_pick_values.csv")
stn = tpk[tpk["method"] == "slot on the trade date"].dropna(subset=["projected_slot", "actual_slot"])
gap_ = (stn["projected_slot"] - stn["actual_slot"]).abs()
PK["traded"] = {"n": int(len(tpk)), "total": float(tpk["value_M"].sum()), "total_sens": float(tpk["value_sensitivity_M"].sum()),
                "methods": tpk["method"].value_counts().to_dict(), "standings_n": int(len(stn)),
                "within3": int((gap_ <= 3).sum()), "median_gap": float(gap_.median())}
r_ = tpk[(tpk["trade_date"] == TRADE_DATE) & (tpk["pick_year"] == 2019) & (tpk["pick_round"] == 2)].iloc[0]
PK["trade_pick"] = {"star_chance": float(r_["star_chance"]), "value": float(r_["value_M"]), "sens": float(r_["value_sensitivity_M"]),
                    "actual_slot": float(r_["actual_slot"]), "method": r_["method"]}
guard("traded pick: value = star value x star chance", abs(STAR * r_["star_chance"] - r_["value_M"]) < 1e-9)
psist = pd.read_csv(OUT / "pick_slot_persistence.csv")
one = psist[psist["gap"] == 1]
PK["persistence"] = {"corr1": float(one[["slot", "later"]].corr().iloc[0, 1]),
                     "corr2": float(psist[psist["gap"] == 2][["slot", "later"]].corr().iloc[0, 1]),
                     "median_move": float((one["later"] - one["slot"]).abs().median()),
                     "top5_later": float(one.loc[one["slot"] <= 5, "later_star"].mean() * STAR),
                     "bottom_later": float(one.loc[one["slot"] >= 25, "later_star"].mean() * STAR),
                     "round_avg": float(one["round_avg_star"].mean() * STAR)}
N["picks"] = PK

# ---- prospects: the model's own functions, and the tests that measured each decision ------------------------------
import prospect_values as PV                                                # noqa: E402
svt, fitrows = PV.star_values()
svf = pd.read_csv(OUT / "prospect_star_values.csv")
svf = svf[svf["left_out"] == "none"].set_index("k_group")
sv0 = svt[svt["left_out"] == "none"].set_index("k_group")
guard("prospects: star values equal prospect_star_values.csv", max(abs(sv0.loc[g, "star_value_M"] - svf.loc[g, "star_value_M"]) for g in sv0.index) < 1e-9)
rates = PV.production_rates()
fits, prow = PV.production_fits(fitrows, rates)
prow = prow.reset_index(drop=True)
pf = pd.read_csv(OUT / "prospect_production_fits.csv")
G5 = ["0", "1", "2", "3", "4+"]
prow["age18"] = prow["past_elig"] + prow["k"]                               # his age on September 15, less 18
prow["prod_x_age18"] = prow["nhle82"] * prow["age18"]


def adopted_cols(g, age_col="prod_x_age"):
    return [c if c != "prod_x_age" else age_col for c in PV.cols_for(g, "main")]


def stacked(cols_by_g, frame=prow):
    res, m = PV.fit_stacked(frame, cols_by_g)
    out = {}
    for g, (pos, n) in m.positions.items():
        cols = cols_by_g[g]
        x = frame[frame["k_group"].astype(str) == g]
        bb = m.params[pos:pos + n]
        y_ = x["remaining_M"].to_numpy(float)
        fit_ = x[cols].to_numpy(float) @ bb
        out[g] = {"terms": {c: tcell(m.params[pos + i], m.bse[pos + i], m.pvalues[pos + i]) for i, c in enumerate(cols)},
                  "rows": int(len(x)), "players": int(x[["draftYear", "pick"]].drop_duplicates().shape[0]),
                  "r2": float(1 - np.sum((y_ - fit_) ** 2) / np.sum(y_ ** 2))}
    return out


ADO = stacked({g: adopted_cols(g, "prod_x_age18") for g in G5})
ADO_past = stacked({g: adopted_cols(g) for g in G5})
gap, checked = 0.0, 0
for g in G5:
    ref = pf[(pf["version"] == "main") & (pf["k_group"].astype(str) == g) & (pf["left_out"].astype(str) == "none")]
    assert len(ref) == 1, g
    for c, t in ADO_past[g]["terms"].items():
        assert np.isfinite(float(ref[c].iloc[0])), (g, c)
        gap = max(gap, abs(t["b"] - float(ref[c].iloc[0])))
        checked += 1
n_terms = sum(len(adopted_cols(g)) for g in G5)          # v4.0: no no-record indicator (17 terms)
guard("prospects: the adopted fit equals prospect_production_fits.csv", gap < 1e-9 and checked == n_terms, f"({checked} terms, gap {gap:.1e})")
# the same fitted values on age now (Thomas's presentation) as on years past first eligibility (the code)
fv_gap = 0.0
for g in G5:
    x = prow[prow["k_group"].astype(str) == g]
    a = x[adopted_cols(g, "prod_x_age18")].to_numpy(float) @ np.array([t["b"] for t in ADO[g]["terms"].values()])
    b = x[adopted_cols(g)].to_numpy(float) @ np.array([t["b"] for t in ADO_past[g]["terms"].values()])
    fv_gap = max(fv_gap, float(np.max(np.abs(a - b))))
guard("prospects: age now gives the same fitted values", fv_gap < 1e-8, f"(gap {fv_gap:.1e})")
BUILD = {}
specs = {"draft position alone": lambda g: ["p_star"], "+ linear production": lambda g: ["p_star", "nhle82"],
         "+ production squared": lambda g: ["p_star", "nhle82", "nhle82_sq"],
         "adopted": lambda g: adopted_cols(g, "prod_x_age18")}
for nm, fn in specs.items():
    BUILD[nm] = stacked({g: fn(g) for g in G5})
# held-out forms in the adopted structure (the age test's procedure: season fits, each draft left out, redraws)
pdr = sorted(prow["draftYear"].unique())
rng2 = np.random.default_rng(20261014)
qdraws = [rng2.choice(pdr, size=len(pdr), replace=True) for _ in range(N_REDRAW)]


def heldout(colfn):
    e = np.zeros(len(prow))
    for g, x in prow.groupby(prow["k_group"].astype(str)):
        cols = colfn(g)
        for c in pdr:
            tr, te = x[x["draftYear"] != c], x[x["draftYear"] == c]
            if not len(te):
                continue
            bb = np.linalg.lstsq(tr[cols].to_numpy(float), tr["remaining_M"].to_numpy(float), rcond=None)[0]
            e[te.index] = te["remaining_M"].to_numpy(float) - te[cols].to_numpy(float) @ bb
    return e


FORMS = {"adopted": lambda g: adopted_cols(g),
         "linear production": lambda g: [c for c in adopted_cols(g) if c != "nhle82_sq"],
         "production squared alone": lambda g: [c for c in adopted_cols(g) if c != "nhle82"]}
fe = {nm: heldout(fn) for nm, fn in FORMS.items()}
fsse = {nm: pd.Series(e ** 2).groupby(prow["draftYear"]).sum() for nm, e in fe.items()}
# v4.2: the adopted model has defenceman x production (prospect_values v1.13), measured by defence_terms_look.py's arm
dlk_ = pd.read_csv(OUT / "defence_terms_look.csv")
dlk_ = dlk_[(dlk_["part"] == "prospect model") & (dlk_["arm"] == "+ D x P")].iloc[0]
ad_rmse = float(np.sqrt(np.mean(fe["adopted"] ** 2)))
guard("prospects: the replicated held-out error equals the defence test's adopted arm",
      abs(ad_rmse - float(dlk_["rmse_heldout_M"])) < 1e-6, f"({ad_rmse:.6f})")
FORM = {nm: {"rmse": float(np.sqrt(np.mean(e ** 2))),
             "by_k": {g: float(np.sqrt(np.mean(e[prow.index[prow["k_group"].astype(str) == g]] ** 2))) for g in G5}}
        for nm, e in fe.items()}
FORM["linear production"]["p_adopted_better"] = redraw_p(fsse["adopted"], fsse["linear production"], qdraws)
FORM["production squared alone"]["p_better_than_adopted"] = redraw_p(fsse["production squared alone"], fsse["adopted"], qdraws)
FORM["production squared alone"]["p_adopted_better"] = redraw_p(fsse["adopted"], fsse["production squared alone"], qdraws)
# from D+5 on: are production and its square jointly zero? (the adopted stacked regression, errors clustered by player)
_r, mst = PV.fit_stacked(prow, {g: adopted_cols(g) for g in G5})
pos4, n4 = mst.positions["4+"]
Rj = np.zeros((2, len(mst.params))); Rj[0, pos4], Rj[1, pos4 + 1] = 1, 1
wj = mst.wald_test(Rj, scalar=True)
JOINT_LATE = {"chi2": float(wj.statistic), "df": 2, "p": float(wj.pvalue)}
# the traded drafted skater prospects under each production form (each form's fit on all drafts; past_elig as the code)
pv_ = pd.read_csv(OUT / "prospect_values.csv")
tsk = pv_[pv_["status"].astype(str).str.startswith("prospect, valued") & ~pv_["is_goalie"].astype(bool)].copy()
tsk["k_group"] = tsk["seasons_since_draft"].astype(int).map(lambda k: str(k) if k < 4 else "4+")
tsk["no_record"] = (tsk["n_prod_seasons"].fillna(0) == 0).astype(float)
tsk["nhle82"] = tsk["nhle82"].fillna(0.0)
tsk["nhle82_sq"] = tsk["nhle82"] ** 2
tsk["prod_x_age"] = tsk["nhle82"] * tsk["past_elig"]
tsk["d_x_prod"] = tsk["nhle82"] * tsk["is_d_model"].astype(float)          # v4.2: defenceman x production
FORM_TRADED = {}
for nm, fn in FORMS.items():
    cb = {g: fn(g) for g in G5}
    res_, _m = PV.fit_stacked(prow, cb)
    v_ = np.zeros(len(tsk))
    for i, (g, row) in enumerate(zip(tsk["k_group"], tsk.itertuples())):
        v_[i] = sum(float(b) * float(getattr(row, c)) for b, c in zip(res_[g][0], cb[g]))
    FORM_TRADED[nm] = {"total": float(v_.sum()), "below_zero": int((v_ < 0).sum())}
    if nm == "adopted":
        gapv = float(np.max(np.abs(v_ - tsk["value_M"].to_numpy(float))))
        guard("prospects: the adopted form reproduces the traded skaters' values", gapv < 1e-9, f"(gap {gapv:.1e}, {len(tsk)} skaters)")

# the traded prospects, and Nick Suzuki
val = pv_[pv_["status"].astype(str).str.startswith("prospect, valued")]
und = pv_[pv_["status"].astype(str).str.startswith("undrafted prospect, valued")]
sz = pv_[(pv_["player_name"] == "Nick Suzuki") & (pv_["trade_date"] == TRADE_DATE)].iloc[0]
k_sz = str(int(sz["seasons_since_draft"]))
co = {c: t["b"] for c, t in ADO[k_sz]["terms"].items()}
inp = {"p_star": float(sz["p_star"]), "nhle82": float(sz["nhle82"]), "nhle82_sq": float(sz["nhle82"]) ** 2, "no_record": 0.0,
       "prod_x_age18": float(sz["nhle82"]) * (float(sz["past_elig"]) + int(sz["seasons_since_draft"])),
       "d_x_prod": float(sz["nhle82"]) * float(sz["is_d_model"])}          # v4.2: defenceman x production
parts = {c: co[c] * inp[c] for c in co}
guard("Suzuki: his parts add to his value", abs(sum(parts.values()) - sz["value_M"]) < 1e-9, f"({sum(parts.values()):.6f} vs {sz['value_M']:.6f})")
d2 = prow[(prow["k_group"].astype(str) == k_sz) & (prow["no_record"] == 0)]["nhle82"]
PRS = {"star": {g: {"b": float(sv0.loc[g, "star_value_M"]), "se": float(sv0.loc[g, "se_M"]), "rows": int(sv0.loc[g, "rows"])} for g in G5},
       "adopted": ADO, "build": BUILD, "forms": FORM, "forms_traded": FORM_TRADED, "joint_late": JOINT_LATE,
       "traded_skaters": int(len(tsk)),
       "rows": int(len(prow)), "players": int(prow[["draftYear", "pick"]].drop_duplicates().shape[0]),
       "no_record_by_k": {g: int(prow.loc[prow["k_group"].astype(str) == g, "no_record"].sum()) for g in G5},
       "no_record_share": float(prow["no_record"].mean()),
       "median_prod": {g: float(prow.loc[(prow["k_group"].astype(str) == g) & (prow["no_record"] == 0), "nhle82"].median()) for g in G5},
       "pct_d2": {str(q): float(d2.quantile(q / 100)) for q in (25, 50, 75, 90)},
       "suzuki": {"k": int(sz["seasons_since_draft"]), "age": float(sz["past_elig"]) + int(sz["seasons_since_draft"]) + 18,
                  "inputs": inp, "coefs": co, "parts": parts, "value": float(sz["value_M"]), "slot": float(sz["value_slot_only_M"]),
                  "own_out": float(sz["value_own_draft_out_M"]), "star_value": float(sz["star_value_M"])},
       "traded": {"drafted": int(len(val)), "drafted_players": int(val["player_name"].nunique()), "tot_drafted": float(val["value_M"].sum()),
                  "undrafted": int(len(und)), "tot_undrafted": float(und["value_M"].sum()),
                  "slot_alone": float(val["value_slot_only_M"].sum()), "own_out": float(val["value_own_draft_out_M"].sum()),
                  "below_zero": int((val["value_M"] < 0).sum()), "below_zero_sum": float(val.loc[val["value_M"] < 0, "value_M"].sum()),
                  "goalies": int(val["is_goalie"].astype(bool).sum()), "max_undrafted": float(und["value_M"].max()),
                  "max_undrafted_name": str(und.loc[und["value_M"].idxmax(), "player_name"]),
                  "top10": [{"date": r.trade_date, "name": r.player_name, "draft": int(r.draftYear), "pick": int(r.pick),
                             "season": f"D+{int(r.seasons_since_draft) + 1}", "prod": float(r.nhle82),
                             "age": float(r.past_elig) + int(r.seasons_since_draft) + 18, "slot": float(r.value_slot_only_M),
                             "value": float(r.value_M)} for r in val.sort_values("value_M", ascending=False).head(10).itertuples()]}}
# the tests' own outputs, read as they are (each guarded by its own script against the model's outputs)
PRS["fade"] = {"curves": pd.read_csv(OUT / "prospect_fade_rules.csv").to_dict("list"),
               "scores": pd.read_csv(OUT / "prospect_fade_rules_scores.csv").to_dict("records")}
PRS["nhle_look"] = pd.read_csv(OUT / "prospect_nhle_look.csv").to_dict("records")
PRS["age_look"] = pd.read_csv(OUT / "prospect_age_look.csv").to_dict("records")
afl = pd.read_csv(OUT / "prospect_age_form_look.csv")
PRS["age_forms"] = afl[afl["centre"] == 18.0].to_dict("records")
PRS["age_cost"] = pd.read_csv(OUT / "prospect_age_form_year_cost.csv").to_dict("records")
arr = pd.read_csv(OUT / "nhl_arrival_timing_summary.csv")
PRS["arrival"] = {g: x.set_index("season")[["arrived", "share_of_all"]].to_dict("index") for g, x in arr.groupby("group")}
guard("prospects: the fade test's adopted column equals the star values",
      max(abs(a - PRS["star"][g]["b"]) for a, g in zip(PRS["fade"]["curves"]["separate"][:5], G5)) < 1e-9)
guard("prospects: the production test's rows are the model's", int(PRS["nhle_look"][0]["rows"]) == len(prow))
# v4.2: every model the prospect document compares, with R-squared, Wald tests and traded totals (prospect_doc_figures.py
# v4.1, guarded against the live model); the player document's prospect section reports from it
pdoc_ = json.loads((OUT / "prospect_doc" / "numbers.json").read_text(encoding="utf-8"))
assert pdoc_["script"].startswith("prospect_doc_figures.py v4."), pdoc_["script"]
guard("prospects: the prospect document's adopted traded total equals this run's",
      abs(pdoc_["traded"]["tot_main"] - PRS["traded"]["tot_drafted"]) < 1e-6)
PRS["doc"] = {k_: pdoc_[k_] for k_ in ("models", "tests", "model_traded", "coefs", "season_r2", "fade_wald_one",
                                         "fade_wald_steps", "fade_wald_ratio", "fade_r2", "pick_def", "disc_forms",
                                         "disc_p_heldout", "econ", "prod_median_pos", "prod_rows", "worked", "def_moved")}
N["prospects"] = PRS
log(f"  prospects: star values " + " / ".join(f"{PRS['star'][g]['b']:.2f}" for g in G5) + f"; Suzuki ${sz['value_M']:.3f}M; "
    f"forms held-out: " + ", ".join(f"{k} {v['rmse']:.4f}" for k, v in FORM.items()))

# ---- WAR and Game Value; goalies (as v1.0) ------------------------------------------------------------------------------
glog = (OUT / "gv_investigation_f_log.txt").read_text(encoding="utf-8")
N["gv"] = {"script": glog.splitlines()[0]}


def gv_row(section, label):
    blk = glog.split(section, 1)[1]
    line = next(l for l in blk.splitlines() if l.strip().startswith(label))
    return [float(x) for x in re.findall(r"(-?\d\.\d{3}) \(", line)]


for sec, key in (("SAME SEASON, all positions", "all"), ("SAME SEASON, forwards", "F"), ("SAME SEASON, defence", "D"),
                 ("NEXT SEASON, all positions", "next")):
    N["gv"][key] = {"trailing60": gv_row(sec, "trailing 60/40"), "trailing": gv_row(sec, "trailing 50/30/20"),
                    "forecast": gv_row(sec, "WAR if he plays")}
for sec, key in (("SAME SEASON, all positions", "all"),):
    N["gv"]["start"] = gv_row(sec, "starting level")
N["gv"]["n"] = int(re.search(r"COMMON SAMPLE, same season: ([\d,]+)", glog).group(1).replace(",", ""))
N["gv"]["n_next"] = int(re.search(r"ONE SEASON FURTHER: ([\d,]+)", glog).group(1).replace(",", ""))
N["gv"]["players"] = int(re.search(r"player-seasons \(([\d,]+) players\)", glog).group(1).replace(",", ""))
N["gv"]["no_contract"] = gv_row("SAME SEASON, all positions", "expected WAR, no contract status")
N["gv"]["expected"] = gv_row("SAME SEASON, all positions", "expected WAR  ")
N["gv"]["log_date"] = pd.Timestamp((OUT / "gv_investigation_f_log.txt").stat().st_mtime, unit="s").strftime("%Y-%m-%d")
gl = (OUT / "goalie_value_engine_run_log.txt").read_text(encoding="utf-8")
import contract_npv as _CN                       # v4.0: the locked goaltender line (contract_npv.GOALIE_RATE)
N["goalie"] = {"n": int(_CN.GOALIE_RATE["n"]), "alpha": float(_CN.GOALIE_RATE["alpha"]), "beta": float(_CN.GOALIE_RATE["beta"]),
               "gamma": float(_CN.GOALIE_RATE["gamma_term"]), "free_alpha": float(_CN.GOALIE_RATE_TERM_FREE["alpha"]),
               "free_beta": float(_CN.GOALIE_RATE_TERM_FREE["beta"])}
mm = re.search(r"term-in: n=(\d+) \(fingerprint \w+; (\d+) at the minimum\)", gl)
guard("goaltender line: the engine's Stage G fitted the locked rows", mm is not None and int(mm.group(1)) == N["goalie"]["n"])
N["goalie"]["at_min"] = int(mm.group(2))
mm = re.search(r"lambda\* = ([\d.]+)\s+\(n=(\d+) season-targets, (\d+) goalies\)", gl)
N["goalie"].update({"lambda": float(mm.group(1)), "lambda_n": int(mm.group(2)), "lambda_goalies": int(mm.group(3))})
mm = re.search(r"MSE near optimum: (\{.*\})", gl)
N["goalie"]["mse_near"] = {k: float(v) for k, v in re.findall(r"np\.float64\(([\d.]+)\): ([\d.]+)", mm.group(1))} if mm else {}

# ---- v4.0: the forecast audit and the whole-term pricing test (2026-10-21), read from their outputs -----------------------
fa = pd.read_csv(OUT / "forecast_term_audit_scores.csv")
fa_all = fa[fa["rows_set"].str.startswith("ALL")]
fa_com = fa[fa["rows_set"].str.startswith("THE")]
N["audit"] = {"all": fa_all.to_dict("records"), "common": fa_com.to_dict("records"),
              "rows_all": int(fa_all["rows"].iloc[0]), "rows_common": int(fa_com["rows"].iloc[0])}
fal = (OUT / "forecast_term_audit_log.txt").read_text(encoding="utf-8")
mm = re.search(r"of ([\d,]+) forecast shares .*?, (\d+) fall below 0.05 before the floor and (\d+) below 0; (\d+) are above the cap", fal)
N["audit"]["shares"] = int(mm.group(1).replace(",", "")); N["audit"]["below_floor"] = int(mm.group(2))
N["audit"]["above_cap"] = int(mm.group(4))
ins = pd.read_csv(OUT / "forecast_term_audit_insample.csv")
N["audit"]["insample"] = ins.to_dict("records")
ta = pd.read_csv(OUT / "term_average_price_line.csv")
N["term_avg"] = ta.to_dict("records")

# ---- the trade on one scale --------------------------------------------------------------------------------------------
cap = H["cap"]
to25 = cap["2025"] / cap[str(TRADE_PAGE)]
pl = H["players"]
tav = pd.read_csv(OUT / "trade_asset_values.csv")
tav = tav[tav["trade_id"] == 1590].set_index("name")
tpl = tav[tav["asset_type"] == "player"]
guard("trade: Pacioretty and Tatar equal trade_asset_values.csv",
      abs(tpl.loc["Max Pacioretty", "value_page_cap_M"] - pl["Max Pacioretty"]["summary"]["npv_total"] / 1e6) < 1e-6
      and abs(tpl.loc["Tomas Tatar", "value_page_cap_M"] - pl["Tomas Tatar"]["summary"]["npv_total"] / 1e6) < 1e-6)
guard("trade: Suzuki and the pick equal trade_asset_values.csv",
      abs(tpl.loc["Nick Suzuki", "value_2025_cap_M"] - PRS["suzuki"]["value"]) < 1e-9
      and abs(tav.loc["2019 round 2 (CBJ)", "value_2025_cap_M"] - PK["trade_pick"]["value"]) < 1e-9)
# retained salary (Thomas 2026-10-19; contract_npv's retained_pv): the retaining club's entry in trade_asset_values.csv
ret = {}
for nm, club in (("Max Pacioretty", "MTL"), ("Tomas Tatar", "VGK")):
    rr = tav.loc[f"retained: {nm}"]
    guard(f"trade: {nm}'s retained entry equals the engine's retained value",
          abs(-float(rr["value_page_cap_M"]) - pl[nm]["retained_pv"] / 1e6) < 1e-6)
    ret[nm] = {"club": club, "share": pl[nm]["retained_pct"], "amount": float(rr["retained_aav"]),
               "seasons": int(pl[nm]["summary"]["n_contract_seasons"]),
               "pv_page": -float(rr["value_page_cap_M"]), "pv_2025": -float(rr["value_2025_cap_M"])}
sides = pd.read_csv(OUT / "trade_sides.csv")
sides = sides[sides["trade_id"] == 1590].set_index("club")
guard("trade: the two clubs' sides sum to zero", abs(sides["net_M"].sum()) < 1e-9)
N["trade"] = {"to_2025": to25, "retained": ret, "assets": [
    {"asset": "Max Pacioretty", "to": "VGK", "kind": "player", "value_page": float(tpl.loc["Max Pacioretty", "value_page_cap_M"]),
     "value": float(tpl.loc["Max Pacioretty", "value_2025_cap_M"])},
    {"asset": "Tomas Tatar", "to": "MTL", "kind": "player", "value_page": float(tpl.loc["Tomas Tatar", "value_page_cap_M"]),
     "value": float(tpl.loc["Tomas Tatar", "value_2025_cap_M"])},
    {"asset": "Nick Suzuki", "to": "MTL", "kind": "prospect", "value": float(tpl.loc["Nick Suzuki", "value_2025_cap_M"])},
    {"asset": "2019 second-round pick", "to": "MTL", "kind": "pick", "value": float(tav.loc["2019 round 2 (CBJ)", "value_2025_cap_M"])}],
    "sides": {c_: {k_: float(sides.loc[c_, k_]) for k_ in ("received_M", "given_M", "net_M", "recv_players_M", "recv_picks_M",
                                                           "recv_prospects_M", "recv_retained_M", "gave_players_M",
                                                           "gave_picks_M", "gave_prospects_M")} for c_ in ("MTL", "VGK")}}
for side in ("MTL", "VGK"):
    N["trade"][side] = N["trade"]["sides"][side]["net_M"]
pac_ = pl["Max Pacioretty"]
N["trade"]["pacioretty_with_extension"] = {"value_page": pac_["npv_with_extension"] / 1e6,
                                           "value": pac_["npv_with_extension"] / 1e6 * to25}
N["trade"]["season_share"] = pac_["season_share"]
log(f"  the trade at the 2025-26 cap: Montreal net ${N['trade']['MTL']:.2f}M, Vegas ${N['trade']['VGK']:.2f}M; retained "
    + ", ".join(f"{k} ${v['pv_2025']:.2f}M" for k, v in ret.items()))


# =====================================================================================================================
# FIGURES (v2.0)
# =====================================================================================================================
plt.rcParams.update({"font.family": "Calibri", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
INK, MUTED, A1, A2, A3, A4 = "#2B2A28", "#8A8984", "#2F6DB5", "#D9822B", "#3E9A5B", "#9B4F96"
GRID = "#E6E5E0"


def tidy(ax, title=None):
    if title:
        ax.set_title(title, fontsize=9.5, color=INK, loc="left")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)


# Figure: aging (as v1.0)
gd = H["aging"]["gdelta"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), dpi=200)
ax = axes[0]
for pos, col, lab in (("F", A1, "Forwards"), ("D", A2, "Defencemen")):
    ages = sorted(int(k.split("|")[1]) for k in gd if k.startswith(pos + "|"))
    ages = [a_ for a_ in ages if 20 <= a_ <= 37]
    ax.plot([a_ + 1 for a_ in ages], [gd[f"{pos}|{a_}"] for a_ in ages], color=col, lw=1.8, marker="o", ms=2.5, label=lab)
ax.axhline(0, color=MUTED, lw=0.6)
ax.set_xlabel("Age reached")
ax.set_ylabel("Change in WAR per 82 from the age before")
tidy(ax, "League average, by age")
ax.legend(frameon=False, fontsize=8)
ax = axes[1]
pc = H["players"]["Max Pacioretty"]
age_v = pc["age_last"] + pc["last_lag"]
base_syr = TRADE_PAGE - pc["last_lag"]
g18 = H["aging"]["page_2018_gdelta"]
seas = pc["seasons"]
fpath = pc["forecast_path"][:5]
ks = [int(x["k"]) for x in fpath]
ax.plot([age_v + k for k in ks], [x["rate_82"] for x in fpath], color=A1, lw=1.8, marker="o", ms=3,
        label="His forecast (comparable players' changes)")
lg = [pc["start"]]
for k in ks[1:]:
    lg.append(lg[-1] + g18.get(f"F|{age_v + k - 1}", 0.0))
ax.plot([age_v + k for k in ks], lg, color=A2, lw=1.4, ls="--", marker="o", ms=2.5, label="League-average changes")
for z_ in pc["own_seasons"]:
    if z_["counted"]:
        ax.scatter([pc["age_last"] + (z_["syr"] - base_syr)], [z_["WAR_82"]], color=MUTED, s=14, zorder=3)
ax.scatter([], [], color=MUTED, s=14, label="His seasons before the trade")
ax.set_xlabel("Age")
ax.set_ylabel("WAR per 82 games")
tidy(ax, "Max Pacioretty, forecast at the trade")
ax.legend(frameon=False, fontsize=7.5, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "fig_aging.png"); plt.close(fig)

# Figure: the price line (as v1.0)
pts = pd.DataFrame(H["price_line"]["points"])
TI_ = H["price_line"]["fits"]["wins + defence + term"]["terms"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True, dpi=200)
for ax, dflag, title in ((axes[0], 0.0, "Forwards"), (axes[1], 1.0, "Defencemen")):
    q = pts[pts["is_d"] == dflag]
    ax.scatter(q["xwar_signed"], q["cap_pct"] * cap["2025"] / 1e6, s=5, color=MUTED, alpha=0.35, lw=0, zorder=2)
    xs = np.linspace(-1, 3.6, 50)
    slope = TI_["per forecast win"]["b"] + dflag * TI_["defence addition per win"]["b"]
    for yrs, col in ((1, A2), (3, A3), (6, A1)):
        line = (TI_["intercept"]["b"] + slope * xs + TI_["per year of term"]["b"] * yrs) * cap["2025"] / 1e6
        ax.plot(xs, np.maximum(line, 0.775), color=col, lw=1.8, zorder=3)
        ax.text(3.65, max(line[-1], 0.775), f"{yrs} yr", color=col, fontsize=8, va="center")
    tidy(ax, title)
    ax.set_xlabel("Forecast WAR if he plays, first season, dated at signing")
    ax.set_xlim(-1.2, 4.1)
axes[0].set_ylabel("Cap hit ($M at the 2025-26 cap)")
fig.tight_layout(); fig.savefig(FIG / "fig_price_line.png"); plt.close(fig)

# Figure: draft position. Left: Bacon's star probability. Right: average surplus at each draft position, with three curves
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.1), dpi=200)
ax = axes[0]
xs = np.arange(1, 225)
ax.plot(xs, [100 * bac.loc[k, "p_star"] for k in xs], color=A1, lw=1.8)
ax.set_xlabel("Draft position")
ax.set_ylabel("Star probability (%)")
tidy(ax, "Bacon's star probability")
ax = axes[1]
ax.scatter(xs, PK["avg_curve"], s=6, color=MUTED, alpha=0.6, lw=0, zorder=2, label="Average of the 11 players taken")
for nm, col, ls, lab in (("straight line in draft position", A4, ":", "Straight line"), ("log of draft position", A3, "--", "Log of draft position"),
                         ("star probability (adopted)", A2, "-", "Star value x star probability (adopted)")):
    ax.plot(xs, PK["shapes"][nm]["curve"], color=col, lw=1.8, ls=ls, label=lab, zorder=3)
ax.axhline(0, color=MUTED, lw=0.6)
ax.set_xlabel("Draft position")
ax.set_ylabel("Career NPV ($M at the 2025-26 cap)")
ax.set_ylim(-3, max(16, np.nanmax(PK["avg_curve"][:5]) + 1))
tidy(ax, "Career NPV delivered, and three curves")
ax.legend(frameon=False, fontsize=7.2, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "fig_picks.png"); plt.close(fig)

# Figure: the star value fitted on each draft
pdf_ = pd.DataFrame(PK["per_draft"])
fig, ax = plt.subplots(figsize=(6.4, 2.9), dpi=200)
ax.errorbar(pdf_["draft"], pdf_["star"], yerr=2 * pdf_["se"], fmt="o", color=A1, ms=4.5, capsize=0, elinewidth=1.2, zorder=3)
ax.axhline(STAR, color=A2, lw=1.6, label=f"All eleven drafts (${STAR:.2f}M)")
ax.axhline(PK["sensitivity"]["star"], color=A2, lw=1.2, ls="--", label=f"Without 2015 and 2016 (${PK['sensitivity']['star']:.2f}M)")
ax.set_xticks(drafts)
ax.set_xlabel("Draft")
ax.set_ylabel("Star value ($M at the 2025-26 cap)")
tidy(ax)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "fig_pick_drafts.png"); plt.close(fig)

# Figure: first-round picks, value delivered and two measures of cost (v4.0, Thomas's note 37: no qualifying-offer chain)
fr = pd.DataFrame(PK["first_round"])
fig, ax = plt.subplots(figsize=(6.4, 3.0), dpi=200)
xg = np.arange(len(fr))
wbar = 0.26
for i, (col, c_, lab) in enumerate((("value", A3, "Value delivered"),
                                    ("cost_arb", A1, "Cost: adopted rule"), ("cost_actual", A2, "Cost actually paid"))):
    ax.bar(xg + (i - 1) * wbar, fr[col], width=wbar, color=c_, label=lab, zorder=3)
    for x_, v_ in zip(xg + (i - 1) * wbar, fr[col]):
        ax.text(x_, v_ + 0.4, f"{v_:.1f}", ha="center", va="bottom", fontsize=7, color=INK)
ax.set_xticks(xg, [f"Picks {r.lo}-{r.hi}\n({r.n} players)" for r in fr.itertuples()], fontsize=8.5)
ax.set_ylabel("$M per player, at the 2025-26 cap")
tidy(ax)
ax.legend(frameon=False, fontsize=7.5, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "fig_pick_cost.png"); plt.close(fig)

# Figure: when drafted players reach the NHL, as shares of each whole group
fig, ax = plt.subplots(figsize=(6.4, 3.0), dpi=200)
seasons_ = [f"D+{i}" for i in range(1, 10)]
for grp, col in (("picks 1-10", A1), ("rest of round 1", A3), ("round 2", A2), ("rounds 3-7", A4)):
    a_ = PRS["arrival"][grp]
    cum_ = np.cumsum([100 * a_.get(s_, {"share_of_all": 0})["share_of_all"] for s_ in seasons_])
    ax.plot(range(1, 10), cum_, color=col, lw=1.8, marker="o", ms=3, label=grp.capitalize())
    ax.text(9.15, cum_[-1], f"{cum_[-1]:.0f}%", color=INK, fontsize=8, va="center")
ax.set_xticks(range(1, 10), seasons_)
ax.set_ylim(0, 100)
ax.set_ylabel("Share of the group in the NHL (%)")
tidy(ax)
ax.legend(frameon=False, fontsize=8, loc="lower right", ncol=2)
fig.tight_layout(); fig.savefig(FIG / "fig_arrival.png"); plt.close(fig)

# Figure: the star value by season, against each rejected alternative (three panels)
fc_ = PRS["fade"]["curves"]
xs8 = np.arange(1, 9)
fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7), sharey=True, dpi=200)
for ax, (alt, title) in zip(axes, (("no fade", "One value for every season"), ("straight line", "A straight-line decline"),
                                   ("same percentage", "The same percentage each season"))):
    sep = fc_["separate"]
    se_ = [PRS["star"][g]["se"] for g in G5]
    ax.errorbar(xs8[:4], sep[:4], yerr=[1.96 * s for s in se_[:4]], fmt="o", color=A1, ms=4, capsize=0, zorder=3)
    ax.fill_between([4.6, 8.4], sep[4] - 1.96 * se_[4], sep[4] + 1.96 * se_[4], color=A1, alpha=0.15, lw=0, zorder=1)
    ax.plot([4.6, 8.4], [sep[4]] * 2, color=A1, lw=2, zorder=3)
    ax.plot(xs8, fc_[alt][:8], color=A2, lw=2, zorder=4)
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xticks(xs8, [f"D+{i}" for i in xs8], fontsize=7.5)
    tidy(ax, title)
axes[0].set_ylabel("Star value ($M)")
axes[0].text(4.7, sep[4] + 2.6, "Adopted", color=A1, fontsize=8)
axes[0].text(5.0, fc_["no fade"][0] + 1.0, "Alternative", color=A2, fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "fig_star_fade.png"); plt.close(fig)

# Figure: a prospect drafted 13th, in D+2 (Suzuki's season and draft position), at three ages
SZ = PRS["suzuki"]
ad = ADO[str(SZ["k"])]["terms"]
qs = np.linspace(0, 25, 251)
fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=200)
for A, col, ls, lab in ((19.0, A1, "-", "Age 19"), (20.0, A2, "--", "Age 20"), (21.0, A4, ":", "Age 21")):
    v_ = (ad["p_star"]["b"] * SZ["inputs"]["p_star"] + ad["nhle82"]["b"] * qs + ad["nhle82_sq"]["b"] * qs ** 2
          + ad["prod_x_age18"]["b"] * qs * (A - 18.0))
    ax.plot(qs, v_, color=col, lw=1.8, ls=ls, label=lab)
ax.scatter([SZ["inputs"]["nhle82"]], [SZ["value"]], color=INK, s=22, zorder=5)
ax.annotate(f"Nick Suzuki, 2018: ${SZ['value']:.2f}M", (SZ["inputs"]["nhle82"], SZ["value"]),
            xytext=(SZ["inputs"]["nhle82"] - 9.5, SZ["value"] + 1.2), fontsize=8, color=INK,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
for qq, v_ in PRS["pct_d2"].items():
    ax.axvline(v_, color="#D5D4CF", lw=0.8, zorder=0)
    ax.text(v_ + 0.12, -0.95, f"{qq}th", ha="left", va="bottom", fontsize=8, color=MUTED)
ax.axhline(0, color=MUTED, lw=0.6)
ax.set_xlabel("Production level: NHLe points per 82 games (50/30/20 over the three seasons before)")
ax.set_ylabel("Value ($M at the 2025-26 cap)")
ax.set_xlim(0, 25); ax.set_ylim(-1, 7)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "fig_prospect.png"); plt.close(fig)

# Figure: the trade, each club's side (trade_sides.csv: received, given up, and the difference)
sd_ = N["trade"]["sides"]
fig, ax = plt.subplots(figsize=(6.2, 2.5), dpi=200)
rows_ = [("Montreal", "MTL"), ("Vegas", "VGK")]
parts = [("Received", "received_M", "#B9B8B2"), ("Given up", "given_M", MUTED), ("Net: received less given up", "net_M", None)]
hgt = 0.24
for i_, (club, k_) in enumerate(rows_):
    for j_, (lab, col, c_) in enumerate(parts):
        v_ = sd_[k_][col]
        y_ = (len(rows_) - 1 - i_) + (1 - j_) * hgt
        colour = c_ or A1
        ax.barh(y_, v_, height=hgt * 0.9, color=colour, label=lab if i_ == 0 else None)
        ax.text(v_ + (0.12 if v_ >= 0 else -0.12), y_, f"{'-' if v_ < 0 else ''}${abs(v_):.2f}M", va="center",
                ha="left" if v_ >= 0 else "right", fontsize=8, color=INK)
ax.set_yticks([1, 0], [r_[0] for r_ in rows_], fontsize=9)
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("xNPV at the trade ($M at the 2025-26 cap)")
ax.set_xlim(-7.5, 4.5)
ax.grid(axis="x", color=GRID, lw=0.6)
ax.legend(frameon=False, fontsize=7.5, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "fig_trade.png"); plt.close(fig)

def clean(o):
    """NaN and infinities as null, so the document builder (JavaScript) can read the file."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


(FIG / "numbers.json").write_text(json.dumps(clean(N), indent=1, allow_nan=False, default=float), encoding="utf-8")
(FIG / "model_doc_figures_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote numbers.json, nine figures and the log in {FIG}")
