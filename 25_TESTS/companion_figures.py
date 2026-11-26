"""
companion_figures.py -- the regressions the companion document ("Figures and Regression Results") shows in full that the
four chunks give only in prose, each re-estimated with its standard errors and guarded against the figure the model uses.

ASKED (Thomas, 2026-11-27: "Build it", on the companion outline agreed that day: one file for the four chunks; each
chunk's tables and figures repeated under its own numbers, then each regression's full output).

WHAT IT ESTIMATES (the 2025-26 valuation season, as the chunks' regressions; written to OUTPUT_DIR/companion/numbers.json)
  1. The goaltender age term: least squares of the forecast's error on age (centred), on goaltender-seasons of 20+ games
     before 2025-26 (contract_npv.GoalieProjector.age_coef). Standard errors clustered by goaltender.
     GUARD: the coefficients equal age_coef(2025) to 1e-10, and the row count.
  2. The goaltender chance of playing: a logistic regression for each season ahead on age, the forecast before the age
     term, and the most recent games share (GoalieProjector.play_models). Standard errors clustered by goaltender.
     GUARD: the coefficients equal play_models(2025) to 1e-6.
  3. The goaltender price line: the censored (Tobit) regression of cap share on the track-record forecast at signing and
     contract length (goalie_value_engine.stage_rate, its sample rebuilt the same way). Standard errors clustered by
     goaltender, by the sandwich model_doc_figures.py uses for the skater price line.
     GUARD: n, the rows' fingerprint, and the coefficients equal contract_npv.GOALIE_RATE (1e-8).
  4. Section 2 of the findings with standard errors clustered by trade (both clubs of a trade are mirror-image rows):
     realized NPV (WAR, Game Value) on trade-day xNPV through zero, 2017-07-01 to 2022-03-28, from
     OUTPUT_DIR/stata/findings_data.csv. GUARD: the slope equals findings_doc/numbers.json's (1e-9).
  5. The linear trend in the star value across draft years, both terms (model_doc_figures.py reports the trend alone).
     GUARD: the trend and its standard error equal model_doc/numbers.json's (1e-9).

Run from the repo root:  python 25_TESTS/companion_figures.py
"""

import hashlib
import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from scipy import stats

SCRIPT_VERSION = "companion_figures.py v1.0 (2026-11-27)"
load_dotenv(".env")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "20_CODE"))
OUT = Path(os.environ["OUTPUT_DIR"])
DEST = OUT / "companion"
DEST.mkdir(exist_ok=True)
print(SCRIPT_VERSION)

import goalie_value_engine as GVE           # noqa: E402
import forecast_config as FC                # noqa: E402
import xnpv1_price_line as XPL              # noqa: E402
import contract_source as CS                # noqa: E402
from skater_forward_projection import league_min_path   # noqa: E402

PAGE = 2025
NUM = {"script": SCRIPT_VERSION, "page": PAGE}


def guard(what, ok, detail=""):
    print(f"  [guard] {what}: {'PASS' if ok else 'GUARD FAILED'} {detail}")
    if not ok:
        raise SystemExit(1)


def cell(b, se, p):
    return {"b": float(b), "se": float(se), "p": float(p)}


CN, GP, _nn = GVE._projector()
LAM, AVG = CN.LAMBDA_G, CN.GOALIE_LEAGUE_AVG

# ---- 1. the age term ----------------------------------------------------------------------------------------------------
rows = []
for (n, y) in GP.lut.index:
    if y >= PAGE or GP._gp(n, y) < GP.AGE_MIN_GP:
        continue
    tr, a = GP._trail(n, y), GP.age(n, y)
    if pd.isna(tr) or a is None:
        continue
    rows.append((n, a - FC.AGE_CENTRE, GP._get(n, y) - ((1 - LAM) * tr + LAM * AVG)))
A = pd.DataFrame(rows, columns=["g", "age_c", "err"])
m = sm.OLS(A["err"], sm.add_constant(A["age_c"])).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(A["g"])[0]})
c0, c1, n0 = GP.age_coef(PAGE)
guard("goaltender age term equals the model's", abs(m.params.iloc[0] - c0) < 1e-10 and abs(m.params.iloc[1] - c1) < 1e-10
      and len(A) == n0, f"({m.params.iloc[1]:.6f} / {c1:.6f}; n {len(A)} / {n0})")
NUM["g_age"] = {"terms": {"intercept": cell(m.params.iloc[0], m.bse.iloc[0], m.pvalues.iloc[0]),
                          "age_c": cell(m.params.iloc[1], m.bse.iloc[1], m.pvalues.iloc[1])},
                "n": int(len(A)), "goalies": int(A["g"].nunique()), "r2": float(m.rsquared), "centre": float(FC.AGE_CENTRE)}

# ---- 2. the chance of playing, each season ahead ------------------------------------------------------------------------
by_season = {}
for (n, y) in GP.lut.index:
    by_season.setdefault(int(y), []).append(n)
rows = []
for tp in range(GP.PLAY_FIRST_PAGE, PAGE):
    for n in by_season.get(tp - 1, []):
        tr, a = GP._trail(n, tp), GP.age(n, tp - 1)
        if pd.isna(tr) or a is None:
            continue
        pw = (1 - LAM) * tr + LAM * AVG
        gs = GP._gp(n, tp - 1) / 82.0
        for h in range(0, PAGE - tp):
            rows.append((n, h, a + 1 + h - FC.AGE_CENTRE, pw, gs, float(GP._gp(n, tp + h) >= FC.PARTICIPATION_GP)))
R = pd.DataFrame(rows, columns=["g", "h", "age_c", "fc", "gs", "played"])
model = GP.play_models(PAGE)
NUM["g_play"] = {}
for h, (params, share) in model.items():
    x = R[R["h"] == h]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        f = sm.Logit(x["played"].to_numpy(), sm.add_constant(x[["age_c", "fc", "gs"]].to_numpy(), has_constant="add")).fit(
            disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": pd.factorize(x["g"])[0]})
    gap = float(np.max(np.abs(np.asarray(f.params) - params)))
    guard(f"goaltender chance of playing, {h} seasons ahead, equals the model's", gap < 1e-6, f"(gap {gap:.1e}, n {len(x)})")
    NUM["g_play"][str(h)] = {"terms": {k: cell(f.params[i], f.bse[i], f.pvalues[i])
                                       for i, k in enumerate(["intercept", "age_c", "fc", "gs"])},
                             "n": int(len(x)), "goalies": int(x["g"].nunique()), "pseudo_r2": float(f.prsquared),
                             "played": float(x["played"].mean())}

# ---- 3. the goaltender price line (goalie_value_engine.stage_rate's sample, rebuilt) ---------------------------------------
raw = pd.read_excel(GVE.F_CONTRACT_XLSX)
raw["start_yr"] = CS.contract_terms(raw)["first_yr"]
d = raw[(raw["position"] == "Goaltender") & (raw["contract_level"] == "standard_level")
        & raw["start_yr"].between(2015, 2025)].copy()
d["nname"] = CS.war_full_name(d, d["first_name"].astype(str) + " " + d["last_name"].astype(str)).map(_nn)
d["cap"] = d["start_yr"].map(lambda y: GVE.ceiling_for(int(y))[0])
d["cap_pct"] = d["aav"] / d["cap"]
d["floor_pct"] = d["start_yr"].map(league_min_path) / d["cap"]
d["signed"] = pd.to_datetime(d["signing_date"], errors="coerce")
d["length"] = pd.to_numeric(d["length"], errors="coerce")
xs = []
for r in d.itertuples():
    page, ok = XPL.signing_page(r.signed)
    hh = None if page is None else int(r.start_yr) - int(page)
    if not ok or hh is None or hh < 0:
        xs.append(np.nan)
        continue
    bd = pd.to_datetime(r.birthdate, errors="coerce")
    a0 = None if pd.isna(bd) else int(page) - bd.year - ((9, 15) < (bd.month, bd.day))
    fc, src = GP.forecast(r.nname, int(page), hh, a0)
    xs.append(np.nan if fc is None or src == "stale_anchor" else GP.shrunk_projection(r.nname, int(page))[0])
d["x"] = xs
d = d[np.isfinite(d["x"]) & d["cap_pct"].notna() & d["length"].notna()].reset_index(drop=True)
key = d[["nname", "start_yr", "cap_pct"]].astype(str).agg("|".join, axis=1).sort_values()
fp = hashlib.sha1("\n".join(key).encode()).hexdigest()[:12]
LK = CN.GOALIE_RATE
f = XPL.fit_censored(d["cap_pct"], d[["x", "length"]].to_numpy(float), d["floor_pct"])
gap = max(abs(f["coef"][0] - LK["alpha"]), abs(f["coef"][1] - LK["beta"]), abs(f["coef"][2] - LK["gamma_term"]))
guard("goaltender price line equals contract_npv.GOALIE_RATE", len(d) == LK["n"] and fp == LK["rows_fingerprint"] and gap < 1e-8,
      f"(n {len(d)}, fingerprint {fp}, gap {gap:.1e})")
y = d["cap_pct"].to_numpy(float) * 100.0
lo = d["floor_pct"].to_numpy(float) * 100.0
cens = y <= lo + 1e-12
X = np.column_stack([np.ones(len(y)), d["x"].to_numpy(float), d["length"].to_numpy(float)])


def ll_vec(pv):
    k = X.shape[1]
    mu, sig = X @ pv[:k], np.exp(pv[k])
    o = np.empty_like(y)
    o[~cens] = -np.log(sig) + stats.norm.logpdf((y[~cens] - mu[~cens]) / sig)
    o[cens] = stats.norm.logcdf((lo[cens] - mu[cens]) / sig)
    return o


pv = np.append(f["coef"] * 100.0, np.log(f["sigma"] * 100.0))
k = len(pv)
h_ = np.maximum(np.abs(pv) * 1e-4, 1e-6)
E = np.eye(k)
S = np.column_stack([(ll_vec(pv + E[j] * h_[j]) - ll_vec(pv - E[j] * h_[j])) / (2 * h_[j]) for j in range(k)])
Hs = np.empty((k, k))
for j in range(k):
    sp_ = np.column_stack([(ll_vec(pv + E[j] * h_[j] + E[i] * h_[i]) - ll_vec(pv + E[j] * h_[j] - E[i] * h_[i])) / (2 * h_[i])
                           for i in range(k)]).sum(0)
    sm_ = np.column_stack([(ll_vec(pv - E[j] * h_[j] + E[i] * h_[i]) - ll_vec(pv - E[j] * h_[j] - E[i] * h_[i])) / (2 * h_[i])
                           for i in range(k)]).sum(0)
    Hs[j] = (sp_ - sm_) / (2 * h_[j])
Hinv = np.linalg.inv(-(Hs + Hs.T) / 2)
G = pd.DataFrame(S).groupby(d["nname"].to_numpy()).sum().to_numpy()
se = np.sqrt(np.diag(Hinv @ (G.T @ G) @ Hinv))[: k - 1] / 100.0
n_unc = int((~cens).sum())
NUM["g_line"] = {"terms": {nm: cell(f["coef"][i], se[i], 2 * stats.norm.sf(abs(f["coef"][i] / se[i])))
                           for i, nm in enumerate(["intercept", "per forecast win", "per year of term"])},
                 "sigma": float(f["sigma"]), "n": int(len(d)), "goalies": int(d["nname"].nunique()),
                 "censored": int(cens.sum()), "loglik_share": float(ll_vec(pv).sum() + n_unc * np.log(100.0))}
print(f"  goaltender price line: {len(d)} contracts by {d['nname'].nunique()} goaltenders; "
      + "; ".join(f"{k_} {v['b']:.5f} ({v['se']:.5f})" for k_, v in NUM["g_line"]["terms"].items()))

# ---- 4. Section 2 of the findings, clustered by trade --------------------------------------------------------------------
FD = pd.read_csv(OUT / "stata" / "findings_data.csv")
FN = json.loads((OUT / "findings_doc" / "numbers.json").read_text(encoding="utf-8"))
w = FD[FD["in_2017_22"] == 1]
NUM["s2_cluster"] = {}
for lab, col, ref in (("war", "realized_war", FN["s2"]["war"]["slope"][0]), ("gv", "realized_gamevalue", FN["s2"]["gv"]["slope"][0])):
    x = w.dropna(subset=[col, "tradeday_grade"])
    r = sm.OLS(x[col], x[["tradeday_grade"]]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(x["trade_id"])[0]})
    r0 = sm.OLS(x[col], x[["tradeday_grade"]]).fit()
    guard(f"Section 2 slope ({lab}) equals the findings document's", abs(r.params.iloc[0] - ref) < 1e-9, f"({r.params.iloc[0]:.6f})")
    NUM["s2_cluster"][lab] = {"b": float(r.params.iloc[0]), "se": float(r.bse.iloc[0]), "p": float(r.pvalues.iloc[0]),
                              "se_plain": float(r0.bse.iloc[0]), "n": int(len(x)), "trades": int(x["trade_id"].nunique()),
                              "r2_uncentred": float(r.rsquared)}
    print(f"  Section 2 ({lab}): slope {r.params.iloc[0]:.4f}, clustered s.e. {r.bse.iloc[0]:.4f} "
          f"(unclustered {r0.bse.iloc[0]:.4f}); {len(x)} club sides, {x['trade_id'].nunique()} trades")

# ---- 5. the trend in the star value across drafts (model_doc_figures.py's regression, both terms) -----------------------
pk = pd.read_csv(OUT / "pick_curve_players.csv")
pk = pk[~pk["excluded_deceased"].astype(bool)].copy().reset_index(drop=True)
pk["y"] = pk["surplus"] / 1e6
pk["p_trend"] = pk["p_star"] * (pk["draftYear"] - 2012)
MD = json.loads((OUT / "model_doc" / "numbers.json").read_text(encoding="utf-8"))["picks"]["trend"]
NUM["trend"] = {}
for lab, f_ in (("all", pk), ("without_2015_2016", pk[~pk["draftYear"].isin([2015, 2016])])):
    m_ = sm.OLS(f_["y"].to_numpy(float), f_[["p_star", "p_trend"]].to_numpy(float)).fit(cov_type="HC1")
    guard(f"star-value trend ({lab}) equals the pick document's", abs(m_.params[1] - MD[lab]["b"]) < 1e-9
          and abs(m_.bse[1] - MD[lab]["se"]) < 1e-9, f"({m_.params[1]:.4f})")
    NUM["trend"][lab] = {"terms": {k_: cell(m_.params[i], m_.bse[i], m_.pvalues[i]) for i, k_ in enumerate(["p_star", "p_trend"])},
                         "n": int(len(f_)), "drafts": int(f_["draftYear"].nunique())}

(DEST / "numbers.json").write_text(json.dumps(NUM, indent=1), encoding="utf-8")
print(f"wrote {DEST / 'numbers.json'}")
