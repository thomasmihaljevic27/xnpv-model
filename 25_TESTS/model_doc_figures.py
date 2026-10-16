"""
model_doc_figures.py -- the numbers and figures behind "Valuing Players, Draft Picks, and Prospects"
(40_DOCS/Supervisor_Drafts/), v1.0 (2026-10-16).

The document explains the three valuation models on one scale, with one trade (Montreal and Vegas, 2018-09-10:
Max Pacioretty for Tomas Tatar, Nick Suzuki and a 2019 second-round pick) carried through. This script prices
nothing new: each figure is read from the code that runs, and each is GUARDED against the output it must reproduce.

  PLAYERS (the engine and the forecaster's page fits, built here as contract_npv builds them)
    * Pacioretty's and Tatar's values at the trade equal traded_player_values.csv (to $1); their season rows are
      the engine's own; the start of Pacioretty's forecast is rebuilt from its parts and equals the forecast.
    * The price line: three nested fits on the locked sample (the same rows, fingerprinted). The term-free fit equals
      skater_forward_projection.XNPV1_RATE_TERM_FREE and the adopted fit XNPV1_RATE (to 1e-7). Standard errors are
      computed here (the model's fit does not compute them): the sandwich form, clustered by player.
    * The games share and the chance of playing on the 2025 page, the most recent: nested fits on the page's own
      training rows; the adopted fits equal the page's coefficients (games share 1e-8; chance of playing: the page's
      fit carries a 1e-4 penalty against separation, so its coefficients are compared at 0.02 and the table reports
      this unpenalized fit, errors clustered by player).
    * Control seasons: the qualify rates and plays-given-qualified rates the engine measured on this run.
  DRAFT PICKS: pick_curve_players.csv refitted three ways; the adopted fit equals pick_curve_scales.csv (1e-9).
  PROSPECTS: OUTPUT_DIR/prospect_doc/numbers.json (prospect_doc_figures.py), checked against prospect_values.csv.
  WAR AND GAME VALUE: parsed from gv_investigation_f_log.txt; GOALIES: goalie_value_engine_run_log.txt.

Outputs: OUTPUT_DIR/model_doc/numbers.json, the figures (fig_*.png), heavy.json (the engine's figures, so --reuse
can redraw the figures without rebuilding the engine) and model_doc_figures_log.txt.

Run from the repo root:  python 25_TESTS/model_doc_figures.py           (about 10 minutes: builds the engine)
                         python 25_TESTS/model_doc_figures.py --reuse   (reads heavy.json; figures and light parts)
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

SCRIPT_VERSION = "model_doc_figures.py v1.0 (2026-10-16)"
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
    tp = pd.read_csv(OUT / "traded_player_values.csv")
    war = pd.read_csv(SRC / "WAR.csv", usecols=["Player"])
    display = {}
    for nm in war["Player"]:
        display.setdefault(AC.career_key(nm), nm)
    H["players"] = {}
    for name in ("Max Pacioretty", "Tomas Tatar"):
        r = tp[(tp["player_name"] == name) & (tp["trade_date"] == TRADE_DATE)].iloc[0]
        pid, page, as_of = int(r["player_id"]), int(r["valuation_page"]), pd.Timestamp(r["as_of"])
        det, s = eng.npv(pid, page, as_of)
        guard(f"{name}: value equals traded_player_values.csv", abs(s["npv_total"] - r["npv_total"]) < 1.0,
              f"({s['npv_total']:,.0f} against {r['npv_total']:,.0f})")
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
    guard("price line: wins + defence equals XNPV1_RATE_TERM_FREE", gap_f < 1e-7, f"(gap {gap_f:.1e})")
    guard("price line: wins + defence + term equals XNPV1_RATE", gap_i < 1e-7, f"(gap {gap_i:.1e})")
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
    gp_specs = {"games share": ["tr_gp_share"],
                "+ defence, experience": ["tr_gp_share", "is_D", "exp_seasons"],
                "+ age, age squared": ["tr_gp_share", "is_D", "exp_seasons", "age_c", "age_c2"],
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
    pp_specs = {"age": ["age", "age_sq"], "+ level, games share, experience, defence":
                ["age", "age_sq", "level", "gp_share", "exp_seasons", "is_D"]}
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
guard("price line: log-likelihoods equal xnpv1_price_line_log.txt",
      abs(PLH["fits"]["wins + defence"]["loglik_share"] - ll_free) < 0.06
      and abs(PLH["fits"]["wins + defence + term"]["loglik_share"] - ll_in) < 0.06, f"({ll_free}, {ll_in})")

# =====================================================================================================================
# LIGHT PARTS
# =====================================================================================================================
# ---- draft picks: the star value, three ways ------------------------------------------------------------------------
d = pd.read_csv(OUT / "pick_curve_players.csv")
d = d[~d["excluded_deceased"].astype(bool)].copy()
sc = pd.read_csv(OUT / "pick_curve_scales.csv").set_index("scale_kind")
yv = d["surplus"].to_numpy(float) / 1e6
m1 = sm.OLS(yv, d[["p_star"]].to_numpy(float)).fit(cov_type="HC1")
guard("pick curve: through zero equals pick_curve_scales.csv main", abs(m1.params[0] - sc.loc["main", "scale_M"]) < 1e-9)
m2 = sm.OLS(yv, sm.add_constant(d[["p_star"]].to_numpy(float))).fit(cov_type="HC1")
D = pd.get_dummies(d["draftYear"], dtype=float)
m3 = sm.OLS(yv, np.column_stack([d["p_star"].to_numpy(float), D.to_numpy(float)])).fit(cov_type="HC1")
k_ = D.shape[1]
R = np.zeros((k_, 1 + k_)); R[:, 1:] = np.eye(k_)
w3 = m3.wald_test(R, scalar=True)
R2 = np.zeros((k_ - 1, 1 + k_))
for i in range(k_ - 1):
    R2[i, 1 + i], R2[i, 2 + i] = 1, -1
w3eq = m3.wald_test(R2, scalar=True)
rmse = lambda m: float(np.sqrt(np.mean(m.resid ** 2)))
N["picks"] = {
    "n": int(len(d)), "drafts": int(d["draftYear"].nunique()), "played": int((d["nhl_seasons"] > 0).sum()),
    "goalies": int(d["is_goalie"].sum()), "lapsed": int(d["route"].isin(["lapsed", "drafted twice (earlier pick)"]).sum()),
    "fits": {"through zero (adopted)": {"star": tcell(m1.params[0], m1.bse[0], m1.pvalues[0]), "rmse": rmse(m1)},
             "one intercept": {"star": tcell(m2.params[1], m2.bse[1], m2.pvalues[1]),
                               "intercept": tcell(m2.params[0], m2.bse[0], m2.pvalues[0]), "rmse": rmse(m2)},
             "an intercept for each draft": {"star": tcell(m3.params[0], m3.bse[0], m3.pvalues[0]), "rmse": rmse(m3),
                                             "joint_zero": {"chi2": float(w3.statistic), "df": k_, "p": float(w3.pvalue)},
                                             "joint_equal": {"chi2": float(w3eq.statistic), "df": k_ - 1, "p": float(w3eq.pvalue)},
                                             "range": [float(m3.params[1:].min()), float(m3.params[1:].max())]}},
    "sensitivity": {"star": float(sc.loc["sensitivity", "scale_M"]), "se": float(sc.loc["sensitivity", "se_M"])},
    "qo_chain": {"star": float(sc.loc["qo_chain", "scale_M"]), "se": float(sc.loc["qo_chain", "se_M"])},
    "mean_surplus": float(yv.mean()), "share_negative": float((yv < 0).mean()), "share_zero": float((yv == 0).mean()),
}
srt = np.sort(yv)[::-1]
N["picks"]["concentration"] = {"top5_n": int(round(0.05 * len(srt))), "top5_share": float(srt[: int(round(0.05 * len(srt)))].sum() / srt.sum()),
                               "positive": int((yv > 0).sum()), "negative": int((yv < 0).sum()), "zero": int((yv == 0).sum())}
star = float(m1.params[0])
bacon = pd.read_csv(SRC / "draft_slot_baseline.csv").set_index("draft_pick")["p_star"]
N["picks"]["p_star"] = {str(k): float(bacon[k]) for k in (1, 2, 5, 10, 13, 20, 32, 33, 50, 64, 100, 150, 200)}
groups = [(1, 5), (6, 10), (11, 20), (21, 32), (33, 64), (65, 96), (97, 128), (129, 224)]
N["picks"]["by_group"] = []
for lo, hi in groups:
    g = d[d["pick"].between(lo, hi)]
    N["picks"]["by_group"].append({"lo": lo, "hi": hi, "n": int(len(g)), "mean": float(g["surplus"].mean() / 1e6),
                                   "se": float(g["surplus"].std() / 1e6 / np.sqrt(len(g))),
                                   "fitted": float(star * g["p_star"].mean())})
log(f"  picks: star value {star:.3f} (se {m1.bse[0]:.3f}); one intercept {m2.params[0]:+.3f} (p {m2.pvalues[0]:.3f}); "
    f"draft intercepts jointly zero p {w3.pvalue:.3f}, equal p {w3eq.pvalue:.3f}")
plog = (OUT / "pick_curve_log.txt").read_text(encoding="utf-8")
mm = re.search(r"picks 1-10: value delivered ([\d,.]+); cost ([\d,.]+) \(([\d.]+)x", plog)
N["picks"]["top10_value_cost"] = [float(mm.group(1).replace(",", "")), float(mm.group(2).replace(",", "")), float(mm.group(3))]
mm = re.search(r"control seasons played: ([\d,]+); priced at arbitration: ([\d,]+)", plog)
N["picks"]["control_seasons"] = [int(mm.group(1).replace(",", "")), int(mm.group(2).replace(",", ""))]

# ---- the traded pick in the trade --------------------------------------------------------------------------------------
tpk = pd.read_csv(OUT / "traded_pick_values.csv")
r = tpk[(tpk["trade_date"] == TRADE_DATE) & (tpk["pick_year"] == 2019) & (tpk["pick_round"] == 2)].iloc[0]
N["trade_pick"] = {k: (None if pd.isna(r[k]) else (float(r[k]) if isinstance(r[k], (float, np.floating, int, np.integer)) else str(r[k])))
                   for k in ("pick_year", "pick_round", "original_team", "method", "actual_slot", "star_chance",
                             "value_M", "value_sensitivity_M")}
avg2 = float(np.mean([bacon[k] for k in range(32, 63)]))
guard("traded pick: the round average of round 2's star chances (31 teams in 2019)", abs(avg2 - r["star_chance"]) < 1e-6,
      f"({avg2:.6f})")
guard("traded pick: value = star value x star chance", abs(star * r["star_chance"] - r["value_M"]) < 1e-9)
N["traded_picks"] = {"n": int(len(tpk)), "total": float(tpk["value_M"].sum()),
                     "methods": tpk["method"].value_counts().to_dict()}

# ---- prospects: the prospect document's numbers, checked against the model's output ------------------------------------
PN = json.loads((OUT / "prospect_doc" / "numbers.json").read_text(encoding="utf-8"))
pv = pd.read_csv(OUT / "prospect_values.csv")
val = pv[pv["status"] == "prospect, valued"]
guard("prospects: numbers.json's traded total equals prospect_values.csv", abs(val["value_M"].sum() - PN["traded"]["tot_main"]) < 1e-9)
sz = pv[(pv["player_name"] == "Nick Suzuki") & (pv["trade_date"] == TRADE_DATE)].iloc[0]
guard("prospects: Suzuki's value equals numbers.json's worked prospect", abs(sz["value_M"] - PN["worked"]["value"]) < 1e-9)
sv = pd.read_csv(OUT / "prospect_star_values.csv")
sv = sv[sv["left_out"] == "none"].set_index("k_group")["star_value_M"]
guard("prospects: star values equal prospect_star_values.csv",
      max(abs(sv[str(r_["k"])] - r_["star"]) for r_ in PN["step1"]) < 1e-9)
N["prospects"] = {k: PN[k] for k in ("script", "step1", "build", "adopted", "worked", "traded", "arrival", "p_star",
                                     "excluded", "prod_rows", "prod_pct_k1", "joint_late", "fade_scores", "age_corr")}
N["prospects"]["all_valued"] = float(pv.loc[pv["status"].astype(str).str.contains("valued"), "value_M"].sum())

# ---- WAR and Game Value ---------------------------------------------------------------------------------------------------
glog = (OUT / "gv_investigation_f_log.txt").read_text(encoding="utf-8")
N["gv"] = {"script": glog.splitlines()[0]}
def gv_row(section, label):
    blk = glog.split(section, 1)[1]
    line = next(l for l in blk.splitlines() if l.strip().startswith(label))
    return [float(x) for x in re.findall(r"(-?\d\.\d{3}) \(", line)]
for sec, key in (("SAME SEASON, all positions", "all"), ("SAME SEASON, forwards", "F"), ("SAME SEASON, defence", "D"),
                 ("NEXT SEASON, all positions", "next")):
    N["gv"][key] = {"trailing": gv_row(sec, "trailing 50/30/20"),
                    "forecast": gv_row(sec, "WAR if he plays")}
N["gv"]["n"] = int(re.search(r"COMMON SAMPLE, same season: ([\d,]+)", glog).group(1).replace(",", ""))
N["gv"]["n_next"] = int(re.search(r"ONE SEASON FURTHER: ([\d,]+)", glog).group(1).replace(",", ""))
N["gv"]["players"] = int(re.search(r"player-seasons \(([\d,]+) players\)", glog).group(1).replace(",", ""))
N["gv"]["no_contract"] = gv_row("SAME SEASON, all positions", "expected WAR, no contract status")
N["gv"]["expected"] = gv_row("SAME SEASON, all positions", "expected WAR  ")
N["gv"]["log_date"] = pd.Timestamp((OUT / "gv_investigation_f_log.txt").stat().st_mtime, unit="s").strftime("%Y-%m-%d")
log(f"  Game Value: r {N['gv']['all']['forecast'][0]:.3f} (forecast) against {N['gv']['all']['trailing'][0]:.3f} (trailing), "
    f"n {N['gv']['n']:,}; log dated {N['gv']['log_date']}")

# ---- goalies --------------------------------------------------------------------------------------------------------------
gl = (OUT / "goalie_value_engine_run_log.txt").read_text(encoding="utf-8")
mm = re.search(r"PRORATED: n=(\d+)\s+alpha_G=([\d.]+)\s+beta_G=([\d.]+)\s+R2=([\d.]+)", gl)
N["goalie"] = {"n": int(mm.group(1)), "alpha": float(mm.group(2)), "beta": float(mm.group(3)), "r2": float(mm.group(4))}
mm = re.search(r"lambda\* = ([\d.]+)\s+\(n=(\d+) season-targets, (\d+) goalies\)", gl)
N["goalie"].update({"lambda": float(mm.group(1)), "lambda_n": int(mm.group(2)), "lambda_goalies": int(mm.group(3))})

# ---- the trade, on one scale ------------------------------------------------------------------------------------------------
cap = H["cap"]
to25 = cap["2025"] / cap[str(TRADE_PAGE)]
pl = H["players"]
N["trade"] = {"to_2025": to25, "assets": [
    {"asset": "Max Pacioretty", "to": "VGK", "kind": "player", "value_page": pl["Max Pacioretty"]["summary"]["npv_total"] / 1e6,
     "value": pl["Max Pacioretty"]["summary"]["npv_total"] / 1e6 * to25},
    {"asset": "Tomas Tatar", "to": "MTL", "kind": "player", "value_page": pl["Tomas Tatar"]["summary"]["npv_total"] / 1e6,
     "value": pl["Tomas Tatar"]["summary"]["npv_total"] / 1e6 * to25},
    {"asset": "Nick Suzuki", "to": "MTL", "kind": "prospect", "value": float(sz["value_M"])},
    {"asset": "2019 second-round pick", "to": "MTL", "kind": "pick", "value": float(r["value_M"])}]}
for side in ("MTL", "VGK"):
    N["trade"][side] = float(sum(a_["value"] for a_ in N["trade"]["assets"] if a_["to"] == side))
# Pacioretty's 2018-19 season alone: the season of his old contract, the only one Montreal held (the four-year
# extension was signed with Vegas on the day of the trade)
s0 = [x for x in pl["Max Pacioretty"]["seasons"] if int(x["k"]) == 0][0]
guard("trade: Pacioretty's first season is his old contract", s0["is_extension"] in (0.0, "False", False))
N["trade"]["pacioretty_old_contract"] = {"value_page": s0["pv_dollars"] / 1e6, "value": s0["pv_dollars"] / 1e6 * to25}
log(f"  the trade at the 2025-26 cap: Montreal received ${N['trade']['MTL']:.2f}M, Vegas ${N['trade']['VGK']:.2f}M")

# =====================================================================================================================
# FIGURES
# =====================================================================================================================
plt.rcParams.update({"font.family": "Calibri", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
INK, MUTED, A1, A2, A3, A4 = "#2B2A28", "#8A8984", "#2F6DB5", "#D9822B", "#3E9A5B", "#9B4F96"
GRID = "#E6E5E0"

# Figure: the price line. Each contract's cap hit (at the 2025-26 cap) against its forecast at signing; the term-in
# line for a forward at one, three and six years of term.
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
    ax.set_title(title, fontsize=9.5, color=INK, loc="left")
    ax.set_xlabel("Forecast WAR if he plays, first season, dated at signing")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    ax.set_xlim(-1.2, 4.1)
axes[0].set_ylabel("Cap hit ($M at the 2025-26 cap)")
fig.tight_layout()
fig.savefig(FIG / "fig_price_line.png")
plt.close(fig)

# Figure: aging. Left: the league-average yearly change in WAR per 82 by age (2025 page). Right: Pacioretty's forecast
# rate from his comparable players' changes against the league-average changes for forwards.
gd = H["aging"]["gdelta"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), dpi=200)
ax = axes[0]
for pos, col, lab in (("F", A1, "Forwards"), ("D", A2, "Defencemen")):
    ages = sorted(int(k.split("|")[1]) for k in gd if k.startswith(pos + "|"))
    ages = [a_ for a_ in ages if 20 <= a_ <= 37]
    ax.plot([a_ + 1 for a_ in ages], [gd[f"{pos}|{a_}"] for a_ in ages], color=col, lw=1.8, marker="o", ms=2.5, label=lab)
ax.axhline(0, color=MUTED, lw=0.6)
ax.set_xlabel("Age")
ax.set_ylabel("Change in WAR per 82 from the year before")
ax.set_title("League average, by age", fontsize=9.5, color=INK, loc="left")
ax.legend(frameon=False, fontsize=8)
ax.grid(axis="y", color=GRID, lw=0.6)
ax = axes[1]
pc = pl["Max Pacioretty"]
age_v = pc["age_last"] + pc["last_lag"]                 # his age in the valuation season (k = 0)
base_syr = TRADE_PAGE - pc["last_lag"]                  # the season of his last counted age
g18 = H["aging"]["page_2018_gdelta"]
seas = pc["seasons"]
ks = [int(x["k"]) for x in seas]
ax.plot([age_v + k for k in ks], [x["rate_82"] for x in seas], color=A1, lw=1.8, marker="o", ms=3,
        label="His forecast (comparable players' changes)")
lg = [pc["start"]]
for k in ks[1:]:
    lg.append(lg[-1] + g18.get(f"F|{age_v + k - 1}", 0.0))   # gdelta (pos, a): the change from age a to a + 1
ax.plot([age_v + k for k in ks], lg, color=A2, lw=1.4, ls="--", marker="o", ms=2.5, label="League-average changes")
for z in pc["own_seasons"]:
    if z["counted"]:
        ax.scatter([pc["age_last"] + (z["syr"] - base_syr)], [z["WAR_82"]], color=MUTED, s=14, zorder=3)
ax.scatter([], [], color=MUTED, s=14, label="His seasons before the trade")
ax.set_xlabel("Age")
ax.set_ylabel("WAR per 82 games")
ax.set_title("Max Pacioretty, forecast at the trade", fontsize=9.5, color=INK, loc="left")
ax.legend(frameon=False, fontsize=7.5, loc="lower left")
ax.grid(axis="y", color=GRID, lw=0.6)
fig.tight_layout()
fig.savefig(FIG / "fig_aging.png")
plt.close(fig)

# Figure: draft picks. Left: Bacon's star probability by draft position. Right: the mean surplus of each group of draft
# positions (with a 95% interval) and the model's value for the same group.
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), dpi=200)
ax = axes[0]
xs = np.arange(1, 225)
ax.plot(xs, [100 * bacon[k] for k in xs], color=A1, lw=1.8)
ax.set_xlabel("Draft position")
ax.set_ylabel("Star probability (%)")
ax.set_title("Bacon's star probability", fontsize=9.5, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.6)
ax = axes[1]
bg = N["picks"]["by_group"]
xp = np.arange(len(bg))
ax.errorbar(xp, [b["mean"] for b in bg], yerr=[1.96 * b["se"] for b in bg], fmt="o", color=MUTED, ms=4, capsize=0,
            label="Mean surplus delivered")
ax.plot(xp, [b["fitted"] for b in bg], color=A2, lw=1.8, marker="s", ms=3.5, label="Model value")
ax.set_xticks(xp, [f"{b['lo']}-{b['hi']}" for b in bg], rotation=40, fontsize=7.5)
ax.axhline(0, color=MUTED, lw=0.6)
ax.set_xlabel("Draft positions")
ax.set_ylabel("$M at the 2025-26 cap")
ax.set_title("Surplus delivered and model value", fontsize=9.5, color=INK, loc="left")
ax.legend(frameon=False, fontsize=8)
ax.grid(axis="y", color=GRID, lw=0.6)
fig.tight_layout()
fig.savefig(FIG / "fig_picks.png")
plt.close(fig)

# Figure: the trade. Each asset's value at the trade, by the club that received it.
tr = N["trade"]["assets"]
fig, ax = plt.subplots(figsize=(6.2, 2.6), dpi=200)
labels = [f"{a_['asset']} (to {'Montreal' if a_['to'] == 'MTL' else 'Vegas'})" for a_ in tr]
vals = [a_["value"] for a_ in tr]
cols = [A1 if a_["to"] == "MTL" else A2 for a_ in tr]
yy = np.arange(len(tr))[::-1]
ax.barh(yy, vals, color=cols, height=0.55)
for y_, v_ in zip(yy, vals):
    ax.text(v_ + (0.3 if v_ >= 0 else -0.3), y_, f"{'-' if v_ < 0 else ''}${abs(v_):.2f}M", va="center",
            ha="left" if v_ >= 0 else "right", fontsize=8.5, color=INK)
ax.set_yticks(yy, labels, fontsize=8.5)
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("Surplus value at the trade ($M at the 2025-26 cap)")
ax.set_xlim(min(vals) - 4, max(vals) + 3)
ax.grid(axis="x", color=GRID, lw=0.6)
fig.tight_layout()
fig.savefig(FIG / "fig_trade.png")
plt.close(fig)

# Figure: a prospect in D+2 drafted 13th (Nick Suzuki's season and draft position): the adopted model's value against
# his production, at three ages on September 15 of the valuation season; Suzuki marked.
W = PN["worked"]
ad = next(t for t in PN["adopted"] if t["k"] == "1")["terms"]
gap = max(abs(ad[c]["b"] - W["coefs"][c]) for c in W["coefs"])
guard("prospect figure: the adopted D+2 terms are the worked prospect's", gap < 1e-9)
ps13 = PN["worked"]["inputs"]["p_star"]
qs = np.linspace(0, 25, 251)
fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=200)
for A, col, ls, lab in ((19.0, A1, "-", "Age 19"), (20.0, A2, "--", "Age 20"), (21.0, A4, ":", "Age 21")):
    v_ = (ad["p_star"]["b"] * ps13 + ad["nhle82"]["b"] * qs + ad["nhle82_sq"]["b"] * qs ** 2
          + ad["prod_x_age"]["b"] * qs * (A - 18.0))
    ax.plot(qs, v_, color=col, lw=1.8, ls=ls, label=lab)
ax.scatter([W["prod"]], [W["value"]], color=INK, s=22, zorder=5)
ax.annotate(f"Nick Suzuki, 2018: ${W['value']:.2f}M", (W["prod"], W["value"]), xytext=(W["prod"] - 9.5, W["value"] + 1.2),
            fontsize=8, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
for qq, v_ in PN["prod_pct_k1"].items():
    ax.axvline(v_, color="#D5D4CF", lw=0.8, zorder=0)
    ax.text(v_ + 0.12, -0.95, f"{qq}th", ha="left", va="bottom", fontsize=8, color=MUTED)
ax.axhline(0, color=MUTED, lw=0.6)
ax.set_xlabel("Production level: NHLe points per 82 games (50/30/20 over the three seasons before)")
ax.set_ylabel("Value ($M at the 2025-26 cap)")
ax.set_xlim(0, 25)
ax.set_ylim(-1, 7)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "fig_prospect.png")
plt.close(fig)

(FIG / "numbers.json").write_text(json.dumps(N, indent=1, default=float), encoding="utf-8")
(FIG / "model_doc_figures_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote numbers.json, four figures and the log in {FIG}")
