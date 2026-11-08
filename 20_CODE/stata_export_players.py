"""
stata_export_players.py -- the player model's regression data as flat CSVs, for Stata (v1.1).

v1.1 (2026-11-08; Thomas: "simple and ready to go", "comprehensive as far as regressions we can run"): the price lines'
outcome and floor in $M at the 2025-26 cap (cap_m, min_m), so a Stata coefficient reads in the documents' units; the
variables of the price line's other forms (is_rfa, start_2022_on, xwar_over1, term_x_0to1, term_x_1to2, term_x_2plus,
term_x_0plus) and of the whole-term pricing test (xwar_term_avg, xwar_term_avg_exp, from term_average_price_line.py's
rows when they match today's forecast); numeric cluster ids (player_num, career_num); the dropped terms' squares
(p_age_c2 for skaters, age_c2 for goaltenders); yes/no columns as 0/1. And every figure the walkthrough's Part 3 should
print, computed from the CSVs as Stata computes it (stata_expected.py), in stata/expected_players.json.

WHY: every regression the model runs should be reproducible by hand in Stata from files on disk (supervisor meeting,
2026-10-23; Thomas: "create stata csvs for everything", every valuation page). stata_export.py covers the draft pick
curve and the prospect model; this script covers the player model. Its rows come from the model's own functions
(xnpv1_price_line.stage3_sample and run, skater_forecast._anchors and XNPV1._training_pairs,
participation_model.ParticipationModel._rows, contract_npv.GoalieProjector), except the goalie price line's rows,
which goalie_value_engine.stage_rate builds inside its fit: they are rebuilt here line for line and must give the
locked line's row count and row fingerprint back.

OUTPUTS (OUTPUT_DIR/stata/; codebook: 40_DOCS/Stata_Data_Codebook.md):
  price_line_skaters.csv       one row per skater contract in the price line's sample (2,388): cap share, the
                               league minimum's share, forecast WAR at the signing, term.
  price_line_goalies.csv       one row per goaltender contract in the goalie line's sample (333).
  skater_forecast_pairs.csv    one row per skater, valuation season and season ahead (0-12): the games share's and
                               the chance of playing's inputs and outcomes. A page's fit uses the rows whose outcome
                               season is before the page.
  goalie_age_rows.csv          one row per goaltender-season of 20+ games with a trailing value and an age: the age
                               term's outcome (WAR less the pulled trailing value) and age.
  goalie_play_rows.csv         one row per goaltender, valuation season and season ahead: the goalie chance of
                               playing's inputs and outcome.
  forecast_fits.csv            the model's own coefficients for each page and season ahead (each regression above
                               refitted per page), to compare a Stata run with.
  stata_export_players_log.txt the run log, with every check below.

CHECKS (each must PASS or the script stops; each refit reads the CSV back from disk):
  1. The skater price line, refitted from price_line_skaters.csv (censored at the league minimum, term in and term
     free), gives skater_forward_projection.XNPV1_RATE and XNPV1_RATE_TERM_FREE (to 1e-8).
  2. The goalie price line, refitted from price_line_goalies.csv, gives contract_npv.GOALIE_RATE and
     GOALIE_RATE_TERM_FREE (to 1e-8), on the locked rows (count and fingerprint).
  3. For every page 2010-2026 and season ahead: the games share refitted from skater_forecast_pairs.csv equals the
     model's own fit (to 1e-9); the chance of playing refitted the model's way (lightly penalised logit, the columns
     the model kept) equals it (to 1e-6), and the plain logit Stata runs is reported beside it.
  4. For every page: the goalie age term and the goalie chance of playing refitted from their CSVs equal the model's
     (to 1e-9 and 1e-6).

Run from the repo root:  python 20_CODE/stata_export_players.py   (after the dashboard chain; about two minutes)
"""

import hashlib
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

import contract_source as CS                    # noqa: E402
import forecast_config as C                     # noqa: E402
import information_set as ISET                  # noqa: E402
import participation_model as PMOD              # noqa: E402
import skater_forecast as SF                    # noqa: E402
import skater_forward_projection as SFP         # noqa: E402
import skater_value_engine as SVE               # noqa: E402
import stata_expected as SE                     # noqa: E402
import xnpv1_price_line as XPL                  # noqa: E402

SCRIPT_VERSION = "stata_export_players.py v1.1 (2026-11-08)"   # v1.1: test columns, $M outcome, expected figures
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
OUT = OUTPUT_DIR / "stata"
PAGES = range(2010, 2027)                       # 2010-11 to 2026-27, the pages the model values on
PENALTY = 1e-4                                  # participation_model's fit_regularized alpha
TABLE_PAGE = 2025                               # the page the walkthrough fits by hand (model_doc_figures' TABLE_PAGE)
CAP25_M = SVE.CAP_CEILING[2025] / 1e6           # the 2025-26 cap in $M: cap_m = cap share x this
LOG = []


def log(s=""):
    print(s, flush=True)
    LOG.append(str(s))


def ols_const(y, X):
    """Least squares with an intercept (skater_forecast._ols, contract_npv.GoalieProjector.age_coef)."""
    A = np.column_stack([np.ones(len(y)), X])
    return np.linalg.lstsq(A, y, rcond=None)[0]


def logit(y, X, penalised):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        Xc = sm.add_constant(X, has_constant="add")
        if penalised:
            return np.asarray(sm.Logit(y, Xc).fit_regularized(alpha=PENALTY, disp=0, maxiter=200).params, float)
        return np.asarray(sm.Logit(y, Xc).fit(disp=0, maxiter=200).params, float)


def term_average(rows):
    """The whole-term pricing test's two regressors (25_TESTS/term_average_price_line.py v1.0, 2026-10-21): the
    forecast of WAR if he plays averaged over the contract's term, and the same times the chance of playing. Read from
    its rows file, joined on player, first season, term, signing date and cap share, and kept only if its first-season
    forecast equals xwar on every row (the same forecast); otherwise left blank, and the log says to re-run the test."""
    f = OUTPUT_DIR / "term_average_price_line_rows.csv"
    blank = pd.DataFrame({"contract_id": rows["contract_id"], "xwar_term_avg": np.nan, "xwar_term_avg_exp": np.nan})
    if not f.exists():
        log("  NOTE: term_average_price_line_rows.csv not found: the whole-term columns are blank "
            "(run python 25_TESTS/term_average_price_line.py, about 20 minutes)")
        return blank
    t = pd.read_csv(f)
    key = rows[["contract_id", "player_key", "first_season", "term_years", "signing_date", "cap_share", "xwar"]].copy()
    t = t.rename(columns={"nk": "player_key", "start_yr": "first_season", "length": "term_years", "signed": "signing_date",
                          "cap_pct": "cap_share"})
    t["signing_date"] = pd.to_datetime(t["signing_date"]).dt.strftime("%Y-%m-%d")
    t["cap_share"], key["cap_share"] = t["cap_share"].round(12), key["cap_share"].round(12)
    j = key.merge(t, on=["player_key", "first_season", "term_years", "signing_date", "cap_share"], how="left")
    ok = len(j) == len(key) and j["x_first"].notna().all() and float(np.max(np.abs(j["x_first"] - j["xwar"]))) < 1e-9
    if not ok:
        log("  NOTE: term_average_price_line_rows.csv does not match today's price-line rows and forecast: the "
            "whole-term columns are blank (re-run python 25_TESTS/term_average_price_line.py, about 20 minutes)")
        return blank
    log(f"  the whole-term columns: term_average_price_line_rows.csv matches today's forecast on all {len(j):,} rows")
    return pd.DataFrame({"contract_id": j["contract_id"], "xwar_term_avg": j["x_avg"], "xwar_term_avg_exp": j["x_exp"]})


# =============================== 1. the skater price line ==============================================================
def skater_price_line(fc):
    sk = XPL.stage3_sample()
    assert len(sk) == XPL.SAMPLE_N and XPL.fingerprint(sk) == XPL.SAMPLE_FINGERPRINT, "not the locked sample"
    d, fp, free, tin = XPL.run(sk, fc, SVE.CAP_CEILING[2025])
    lock, lock_free = SFP.XNPV1_RATE, SFP.XNPV1_RATE_TERM_FREE
    assert len(d) == lock["n"] and fp == lock["rows_fingerprint"], "not the locked line's rows"
    rows = pd.DataFrame({
        "contract_id": d["contract_id"], "pp_player_id": d["player_id"],
        "player_name": d["first_name"].astype(str) + " " + d["last_name"].astype(str), "player_key": d["nk"],
        "position_group": d["posgrp"], "is_d": d["is_d"].astype(int), "signing_status": d["signing_status"],
        "signing_date": d["signed"].dt.strftime("%Y-%m-%d"), "first_season": d["start_yr"].astype(int),
        "term_years": d["length"], "aav": d["aav"], "cap_ceiling": d["start_yr"].map(SVE.CAP_CEILING),
        "cap_share": d["cap_pct"], "min_share": d["floor_pct"],
        "at_minimum": (d["cap_pct"] <= d["floor_pct"] + 1e-12).astype(int),
        "signing_page": d["sign_page"].astype(int), "seasons_ahead": d["sign_h"].astype(int),
        "xwar": d["xwar_signed"], "xwar_start_dated": d["xwar_start"]})
    # v1.1: the outcome and the floor in $M at the 2025-26 cap; the clustering id; the other forms' variables
    rows["cap_m"], rows["min_m"] = rows["cap_share"] * CAP25_M, rows["min_share"] * CAP25_M
    rows["player_num"] = pd.factorize(rows["player_key"])[0] + 1                 # one per player (model_doc: nk)
    w, yrs = rows["xwar"], rows["term_years"]
    rows["is_rfa"] = (rows["signing_status"].astype(str) == "RFA").astype(int)    # price_line_spec_tests.variants
    rows["start_2022_on"] = (rows["first_season"] >= 2022).astype(int)
    rows["xwar_over1"] = np.maximum(w - 1.0, 0.0)                                # a bend at one forecast win
    rows["term_x_0to1"] = yrs * ((w >= 0) & (w < 1))                              # the premium by forecast group
    rows["term_x_1to2"] = yrs * ((w >= 1) & (w < 2))
    rows["term_x_2plus"] = yrs * (w >= 2)
    rows["term_x_0plus"] = yrs * (w >= 0)                                         # the one step at replacement
    rows = rows.merge(term_average(rows), on="contract_id", how="left")
    rows.to_csv(OUT / "price_line_skaters.csv", index=False)
    R = pd.read_csv(OUT / "price_line_skaters.csv")
    for lab, term, lk in (("term in", True, lock), ("term free", False, lock_free)):
        cols = [R["xwar"].values, R["is_d"].values * R["xwar"].values] + ([R["term_years"].values] if term else [])
        f = XPL.fit_censored(R["cap_share"], np.column_stack(cols), R["min_share"])
        c = f["coef"]
        got = dict(alpha=c[0], beta=c[1], beta_d_add=c[2], gamma_term=c[3] if term else 0.0)
        gap = max(abs(got[k] - lk[k]) for k in got)
        assert f["converged"] and gap < 1e-8, (lab, gap)
        log(f"  check 1, skater price line ({lab}), from price_line_skaters.csv: alpha {c[0]:.10f}, beta {c[1]:.10f}, "
            f"defence add {c[2]:.10f}" + (f", term {c[3]:.10f}" if term else "") + f", sigma {f['sigma']:.8f}; "
            f"{len(R):,} contracts, {int(R['at_minimum'].sum())} at the minimum; = the lock (gap {gap:.1e}) (PASS)")


# =============================== 2. the goalie price line ==============================================================
def goalie_price_line():
    """goalie_value_engine.stage_rate's rows, rebuilt line for line (v2.0), and its two fits."""
    import goalie_value_engine as GVE
    from skater_forward_projection import league_min_path
    CN, GP, _nn = GVE._projector()
    raw = pd.read_excel(GVE.F_CONTRACT_XLSX)
    raw["start_yr"] = CS.contract_terms(raw)["first_yr"]
    d = raw[(raw["position"] == "Goaltender") & (raw["contract_level"] == "standard_level")
            & raw["start_yr"].between(2015, 2025)].copy()
    d["nname"] = CS.war_full_name(d, d["first_name"].astype(str) + " " + d["last_name"].astype(str)).map(_nn)
    d["cap"] = d["start_yr"].map(lambda y: GVE.ceiling_for(int(y))[0])
    d["cap_pct"] = d["aav"] / d["cap"]
    d["floor_pct"] = d["start_yr"].map(league_min_path) / d["cap"]
    d["signed"] = pd.to_datetime(d["signing_date"], errors="coerce")
    d["bd"] = pd.to_datetime(d["birthdate"], errors="coerce")
    d["length"] = pd.to_numeric(d["length"], errors="coerce")
    xs, pages, hs = [], [], []
    for r in d.itertuples():
        page, ok = XPL.signing_page(r.signed)
        h = None if page is None else int(r.start_yr) - int(page)
        pages.append(page); hs.append(h)
        if not ok or h is None or h < 0:
            xs.append(np.nan); continue
        a0 = None if pd.isna(r.bd) else int(page) - r.bd.year - ((9, 15) < (r.bd.month, r.bd.day))
        fc, src = GP.forecast(r.nname, int(page), h, a0)
        if fc is not None and src == "stale_anchor":
            xs.append(np.nan); continue
        xs.append(np.nan if fc is None else GP.shrunk_projection(r.nname, int(page))[0])
    d["x"], d["page"], d["h"] = xs, pages, hs
    d = d[np.isfinite(d["x"]) & d["cap_pct"].notna() & d["length"].notna()].reset_index(drop=True)
    key = d[["nname", "start_yr", "cap_pct"]].astype(str).agg("|".join, axis=1).sort_values()
    fp = hashlib.sha1("\n".join(key).encode()).hexdigest()[:12]
    lock, lock_free = CN.GOALIE_RATE, CN.GOALIE_RATE_TERM_FREE
    assert len(d) == lock["n"] and fp == lock["rows_fingerprint"], (len(d), fp)
    rows = pd.DataFrame({
        "contract_id": d["contract_id"], "pp_player_id": d["player_id"],
        "player_name": d["first_name"].astype(str) + " " + d["last_name"].astype(str), "player_key": d["nname"],
        "signing_status": d["signing_status"], "signing_date": d["signed"].dt.strftime("%Y-%m-%d"),
        "first_season": d["start_yr"].astype(int), "term_years": d["length"], "aav": d["aav"],
        "cap_ceiling": d["cap"], "cap_share": d["cap_pct"], "min_share": d["floor_pct"],
        "at_minimum": (d["cap_pct"] <= d["floor_pct"] + 1e-12).astype(int),
        "signing_page": d["page"].astype(int), "seasons_ahead": d["h"].astype(int), "xwar": d["x"]})
    rows["cap_m"], rows["min_m"] = rows["cap_share"] * CAP25_M, rows["min_share"] * CAP25_M       # v1.1
    rows.to_csv(OUT / "price_line_goalies.csv", index=False)
    R = pd.read_csv(OUT / "price_line_goalies.csv")
    for lab, cols, lk in (("term in", ["xwar", "term_years"], lock), ("term free", ["xwar"], lock_free)):
        f = XPL.fit_censored(R["cap_share"], R[cols].to_numpy(float), R["min_share"])
        c = f["coef"]
        got = dict(alpha=c[0], beta=c[1], gamma_term=c[2] if len(c) > 2 else 0.0)
        gap = max(abs(got[k] - lk[k]) for k in got)
        assert f["converged"] and gap < 1e-8, (lab, gap)
        log(f"  check 2, goalie price line ({lab}), from price_line_goalies.csv: alpha {c[0]:.10f}, beta {c[1]:.10f}"
            + (f", term {c[2]:.10f}" if len(c) > 2 else "") + f", sigma {f['sigma']:.8f}; {len(R)} contracts, "
            f"{int(R['at_minimum'].sum())} at the minimum; = the lock (gap {gap:.1e}) (PASS)")
    return CN, GP


# =============================== 3. the skater forecast pieces ===========================================================
def skater_pairs(fc, contracts):
    """Every (player, valuation season t0, season ahead h) pair any page can train on, from the full season table:
    the inputs at t0 (seasons before t0 only) and the outcome in season t0 + h. A page's fit takes the pairs whose
    outcome season is before the page (XNPV1._training_pairs; ParticipationModel.fit)."""
    table = fc.table
    last = int(table["syr"].max())
    anchors = SF._anchors(table[table["GP"] >= C.MIN_GP], SF.XNPV1.N_SEASONS)
    pm = PMOD.ParticipationModel(contracts, exclude=tuple(SF.XNPV1.PART_EXCLUDE),
                                 contract_state=SF.XNPV1.CONTRACT_STATE)
    act = table.set_index(["career_key", "syr"])
    parts = []
    for h in C.CANDIDATE_HORIZONS:
        a = anchors[anchors["t0"] + h <= last].reset_index(drop=True)
        prt = pm._rows(a, h)                                    # the chance of playing's columns, dated per row
        ix = pd.MultiIndex.from_arrays([a["career_key"], a["t0"] + h])
        y_gp = act["GP"].reindex(ix).to_numpy()
        parts.append(pd.DataFrame({
            "career_key": a["career_key"], "player_key": a["pkey"], "position": a["pos"], "is_d": a["is_D"],
            "page_season": a["t0"], "h": h, "season": a["t0"] + h,
            "tr_gp_share": a["tr_gp_share"], "exp_seasons": a["exp_seasons"], "age_c": a["age_c"],
            "age_c2": a["age_c2"], "tw_war": a["tw_WAR"],
            "y_gp_share": act["gp_share"].reindex(ix).to_numpy(),
            "p_age_c": prt["age"].to_numpy(), "under_contract": prt["under_contract"].to_numpy(),
            "contract_unknown": prt["contract_unknown"].to_numpy(),
            "y_gp": np.nan_to_num(y_gp), "y_played": (np.nan_to_num(y_gp) >= C.PARTICIPATION_GP).astype(int)}))
    pairs = pd.concat(parts, ignore_index=True)
    # v1.1: 0/1 for yes/no columns (Stata reads True/False as text); a numeric cluster id; the dropped age squared
    for c in ("is_d", "under_contract", "contract_unknown"):
        pairs[c] = pd.to_numeric(pairs[c].astype(float)).round().astype("Int64")
    pairs["career_num"] = pd.factorize(pairs["career_key"])[0] + 1
    pairs["p_age_c2"] = pairs["p_age_c"] ** 2                       # participation_model._rows' age_sq (dropped v2.0)
    pairs = pairs.replace([np.inf, -np.inf], np.nan)
    pairs.to_csv(OUT / "skater_forecast_pairs.csv", index=False)
    log(f"\n  wrote skater_forecast_pairs.csv: {len(pairs):,} pairs (seasons ahead 0-{max(C.CANDIDATE_HORIZONS)}, "
        f"outcome seasons to {last})")
    return pd.read_csv(OUT / "skater_forecast_pairs.csv")


def skater_pages(fc, contracts, P):
    """Check 3: every page's games share and chance of playing, from the CSV against the model's own fits."""
    GPF = ["tr_gp_share", "exp_seasons", "age_c", "tw_war", "age_c2"]          # skater_forecast.GP_FEATURES
    assert [c.lower() for c in SF.GP_FEATURES] == GPF
    PART = {"age": "p_age_c", "level": "tw_war", "gp_share": "tr_gp_share", "is_D": "is_d",
            "under_contract": "under_contract", "contract_unknown": "contract_unknown"}
    fits, worst_plain = [], 0.0
    for page in PAGES:
        iset = ISET.build(fc.table, ISET.decision_date_for_page(page), t0=page)
        m = SF.XNPV1()
        pairs = m._training_pairs(iset.seasons, page, C.CANDIDATE_HORIZONS)
        n_gs = 0
        for h, g in pairs.groupby("h"):
            s = g.dropna(subset=["y_gp_share"] + SF.GP_FEATURES)
            mine = SF._ols(s[SF.GP_FEATURES], s["y_gp_share"]) if len(s) > 50 else None
            x = P[(P["h"] == h) & (P["season"] < page)].dropna(subset=["y_gp_share"] + GPF)
            assert len(x) == len(s), (page, h, len(x), len(s))
            if mine is None:
                continue
            b = ols_const(x["y_gp_share"].to_numpy(float), x[GPF].to_numpy(float))
            assert np.max(np.abs(b - mine[1])) < 1e-9, (page, h)
            fits.append({"regression": "skater games share", "page": page, "h": int(h), "rows": len(x),
                         "columns": " ".join(["_cons"] + GPF), **{f"b{i}": v for i, v in enumerate(mine[1])}})
            n_gs += 1
        pm = PMOD.ParticipationModel(contracts, exclude=tuple(SF.XNPV1.PART_EXCLUDE),
                                     contract_state=SF.XNPV1.CONTRACT_STATE).fit(
            iset.seasons, page, anchors_fn=lambda p: SF._anchors(p, SF.XNPV1.N_SEASONS), horizons=m.fitted_horizons_)
        n_pl = 0
        for h in m.fitted_horizons_:
            coef = pm.coef_.get(h)
            if coef is None:
                continue
            cols = [PART[c] for c in pm.used_[h]]
            x = P[(P["h"] == h) & (P["season"] < page)].dropna(subset=list(PART.values()) + ["y_played"])
            b = logit(x["y_played"].to_numpy(float), x[cols].to_numpy(float), True)
            assert np.max(np.abs(b - coef)) < 1e-6, (page, h, np.max(np.abs(b - coef)))
            bp = logit(x["y_played"].to_numpy(float), x[cols].to_numpy(float), False)
            worst_plain = max(worst_plain, float(np.max(np.abs(bp - coef))))
            fits.append({"regression": "skater chance of playing", "page": page, "h": int(h), "rows": len(x),
                         "columns": " ".join(["_cons"] + cols), **{f"b{i}": v for i, v in enumerate(coef)},
                         "plain_logit_largest_gap": float(np.max(np.abs(bp - coef)))})
            n_pl += 1
        log(f"    page {page}: games share {n_gs} seasons ahead, chance of playing {n_pl}: CSV = the model's fits")
    log(f"  check 3: every page's skater games share (to 1e-9) and chance of playing (to 1e-6) from "
        f"skater_forecast_pairs.csv (PASS); a plain logit (Stata's logit) differs from the model's lightly penalised "
        f"one by at most {worst_plain:.2e} in any coefficient")
    return fits


# =============================== 4. the goalie forecast pieces ===========================================================
def goalie_pieces(CN, GP):
    lam, avg = CN.LAMBDA_G, CN.GOALIE_LEAGUE_AVG
    rows = []
    for (n, y) in GP.lut.index:                                          # as GoalieProjector.age_coef
        if GP._gp(n, y) < GP.AGE_MIN_GP:
            continue
        tr, a = GP._trail(n, y), GP.age(n, y)
        if pd.isna(tr) or a is None:
            continue
        pred = (1 - lam) * tr + lam * avg
        rows.append({"player_key": n, "season": int(y), "gp": GP._gp(n, y), "war": GP._get(n, y),
                     "trailing_war": tr, "age": a, "age_c": a - C.AGE_CENTRE, "pulled": pred,
                     "war_less_pulled": GP._get(n, y) - pred})
    pd.DataFrame(rows).to_csv(OUT / "goalie_age_rows.csv", index=False)
    by_season = {}
    for (n, y) in GP.lut.index:
        by_season.setdefault(int(y), []).append(n)
    top = max(PAGES)
    play = []
    for tp in range(GP.PLAY_FIRST_PAGE, top):                            # as GoalieProjector.play_models(top)
        for n in by_season.get(tp - 1, []):
            tr, a = GP._trail(n, tp), GP.age(n, tp - 1)
            if pd.isna(tr) or a is None:
                continue
            pw = (1 - lam) * tr + lam * avg
            gs = GP._gp(n, tp - 1) / 82.0
            for h in range(0, top - tp):
                play.append({"player_key": n, "page_season": tp, "h": h, "season": tp + h,
                             "age_c": a + 1 + h - C.AGE_CENTRE, "pulled": pw, "gp_share_last": gs,
                             "played": int(GP._gp(n, tp + h) >= C.PARTICIPATION_GP)})
    play = pd.DataFrame(play)
    play["age_c2"] = play["age_c"] ** 2                             # v1.1: the age squared tested and dropped
    play.to_csv(OUT / "goalie_play_rows.csv", index=False)
    A = pd.read_csv(OUT / "goalie_age_rows.csv")
    Q = pd.read_csv(OUT / "goalie_play_rows.csv")
    log(f"\n  wrote goalie_age_rows.csv ({len(A):,} goaltender-seasons) and goalie_play_rows.csv ({len(Q):,} rows)")
    fits, worst = [], 0.0
    for page in PAGES:
        c0, c1, n = GP.age_coef(page)
        x = A[A["season"] < page]
        b = ols_const(x["war_less_pulled"].to_numpy(float), x[["age_c"]].to_numpy(float))
        assert len(x) == n and abs(b[0] - c0) < 1e-9 and abs(b[1] - c1) < 1e-9, page
        fits.append({"regression": "goalie age term", "page": page, "h": None, "rows": n, "columns": "_cons age_c",
                     "b0": c0, "b1": c1})
        try:
            models = GP.play_models(page)
        except AssertionError:                                           # no season ahead has 200 rows yet
            log(f"    page {page}: no goalie chance-of-playing regression can be fitted (as in the model)")
            continue
        for h, (coef, _share) in models.items():
            x = Q[(Q["h"] == h) & (Q["season"] < page)]
            b = logit(x["played"].to_numpy(float), x[["age_c", "pulled", "gp_share_last"]].to_numpy(float), False)
            worst = max(worst, float(np.max(np.abs(b - coef))))
            assert np.max(np.abs(b - coef)) < 1e-6, (page, h)
            fits.append({"regression": "goalie chance of playing", "page": page, "h": int(h), "rows": len(x),
                         "columns": "_cons age_c pulled gp_share_last", **{f"b{i}": v for i, v in enumerate(coef)}})
    log(f"  check 4: every page's goalie age term (to 1e-9) and chance of playing (to 1e-6; largest gap {worst:.1e}) "
        f"from the CSVs (PASS)")
    return fits


def expected_figures(fits):
    """v1.1: what each command in the walkthrough's Part 3 should print, from the CSVs as written, computed as Stata
    computes it (stata_expected.py). Step numbers are the do-file's. The forecast pieces are fitted by hand on one page,
    TABLE_PAGE (2025-26), the page "Valuing Players, Draft Picks, and Prospects" tables."""
    E = SE.Expected()
    log("\nEXPECTED FIGURES (Part 3 of the do-file; Stata's conventions; $M at the 2025-26 cap)")
    R = pd.read_csv(OUT / "price_line_skaters.csv")
    xd = (R["xwar"] * R["is_d"]).to_numpy()

    def tob(cols, names, cluster=None, frame=R):
        X = np.column_stack(cols)
        return SE.Tobit(frame["cap_share"], X, names, frame["min_share"], CAP25_M, cluster=cluster)

    base_cols, base_names = [R["xwar"], xd, R["term_years"]], ["xwar", "c.xwar#c.is_d", "term_years"]
    tin = tob(base_cols, base_names)
    lk = SFP.XNPV1_RATE
    gap = max(abs(tin.share_coef[0] - lk["alpha"]), abs(tin.share_coef[1] - lk["beta"]),
              abs(tin.share_coef[2] - lk["beta_d_add"]), abs(tin.share_coef[3] - lk["gamma_term"]))
    assert gap < 1e-8, gap
    tcl = tob(base_cols, base_names, cluster=R["player_num"])
    for k_, nm in (("C", "_cons"), ("W", "xwar"), ("D", "c.xwar#c.is_d"), ("T", "term_years")):
        E.add(f"S14_{k_}", tin.coef(nm), "{:.4f}"); E.add(f"S14_{k_}SE", tin.sei(nm), "{:.4f}")
        E.add(f"S14_{k_}CSE", tcl.sei(nm), "{:.4f}")
    E.add("S14_SIG", tin.sigma, "{:.4f}"); E.add("S14_LL", tin.ll, "{:,.2f}")
    E.add("S14_N", f"{tin.n:,}"); E.add("S14_CENS", f"{tin.n_cens:,}")
    log(f"  step 14, the skater price line: intercept {tin.coef('_cons'):.4f}, per forecast win {tin.coef('xwar'):.4f}, "
        f"defence add {tin.coef('c.xwar#c.is_d'):.4f}, per year of term {tin.coef('term_years'):.4f}, sigma "
        f"{tin.sigma:.4f}, log-likelihood {tin.ll:,.2f} ({tin.n:,} contracts, {tin.n_cens} at the minimum) = the lock")
    log(f"    clustered by player: s.e. {tcl.sei('xwar'):.4f} / {tcl.sei('c.xwar#c.is_d'):.4f} / {tcl.sei('term_years'):.4f}")

    t_w = tob([R["xwar"]], ["xwar"])
    t_wd = tob([R["xwar"], xd], ["xwar", "c.xwar#c.is_d"])
    for key, small, big, df in (("S15_DEF", t_w, t_wd, 1), ("S15_TERM", t_wd, tin, 1)):
        lr, p = SE.lrtest(small, big, df)
        E.add(key + "_LR", lr, "{:.2f}"); E.p(key + "_P", p)
    E.add("S15_LLW", t_w.ll, "{:,.2f}"); E.add("S15_LLWD", t_wd.ll, "{:,.2f}")
    E.add("S15_FW", t_wd.coef("xwar"), "{:.4f}"); E.add("S15_FD", t_wd.coef("c.xwar#c.is_d"), "{:.4f}")
    log(f"  step 15: log-likelihood wins {t_w.ll:,.2f}, + defence {t_wd.ll:,.2f} (LR {E.v['S15_DEF_LR']}, "
        f"{E.v['S15_DEF_P']}), + term {tin.ll:,.2f} (LR {E.v['S15_TERM_LR']}, {E.v['S15_TERM_P']})")

    w, yrs, rfa, late = R["xwar"], R["term_years"], R["is_rfa"], R["start_2022_on"]
    forms = {
        "S16_RFA": ([rfa, rfa * w, rfa * xd, rfa * yrs], ["is_rfa", "c.is_rfa#c.xwar", "c.is_rfa#c.xwar#c.is_d",
                                                           "c.is_rfa#c.term_years"]),
        "S16_TXW": ([yrs * w], ["c.term_years#c.xwar"]),
        "S16_GRP": ([R["term_x_0to1"], R["term_x_1to2"], R["term_x_2plus"]], ["term_x_0to1", "term_x_1to2", "term_x_2plus"]),
        "S16_STEP": ([R["term_x_0plus"]], ["term_x_0plus"]),
        "S16_SQ": ([w * w], ["c.xwar#c.xwar"]),
        "S16_BEND": ([R["xwar_over1"]], ["xwar_over1"]),
        "S16_LATE": ([late, late * w, late * xd, late * yrs], ["start_2022_on", "c.start_2022_on#c.xwar",
                                                              "c.start_2022_on#c.xwar#c.is_d", "c.start_2022_on#c.term_years"]),
    }
    fitted = {}
    for key, (cols, names) in forms.items():
        t = tob(base_cols + cols, base_names + names)
        fitted[key] = t
        lr, p = SE.lrtest(tin, t, len(cols))
        E.add(key + "_LR", lr, "{:.2f}"); E.p(key + "_P", p)
        log(f"  step 16 ({key}): log-likelihood gain {lr / 2:+.2f}, LR {lr:.2f} on {len(cols)}, {E.v[key + '_P']}")
    lr, p = SE.lrtest(fitted["S16_STEP"], fitted["S16_GRP"], 2)
    E.add("S16_GVS_LR", lr, "{:.2f}"); E.p("S16_GVS_P", p)
    log(f"  step 16: the premium by group against the one step: LR {lr:.2f} on 2, {E.v['S16_GVS_P']}")

    if R["xwar_term_avg"].notna().all():
        for key, col in (("S17_AVG", "xwar_term_avg"), ("S17_EXP", "xwar_term_avg_exp")):
            t = tob([R[col], R[col] * R["is_d"], yrs], [col, f"c.{col}#c.is_d", "term_years"])
            E.add(key, t.ll, "{:,.2f}"); E.add(key + "_W", t.coef(col), "{:.4f}")
        log(f"  step 17, whole-term pricing: log-likelihood first season {tin.ll:,.2f}, term average {E.v['S17_AVG']}, "
            f"term average x chance of playing {E.v['S17_EXP']}")
    else:
        for key in ("S17_AVG", "S17_EXP", "S17_AVG_W", "S17_EXP_W"):
            E.add(key, "not built (re-run 25_TESTS/term_average_price_line.py, then this export)")
        log("  step 17: the whole-term columns are blank; its expected figures say so")

    Gl = pd.read_csv(OUT / "price_line_goalies.csv")
    gin = SE.Tobit(Gl["cap_share"], Gl[["xwar", "term_years"]], ["xwar", "term_years"], Gl["min_share"], CAP25_M)
    gfr = SE.Tobit(Gl["cap_share"], Gl[["xwar"]], ["xwar"], Gl["min_share"], CAP25_M)
    import contract_npv as CN
    assert abs(gin.share_coef[1] - CN.GOALIE_RATE["beta"]) < 1e-8 and abs(gfr.share_coef[1] - CN.GOALIE_RATE_TERM_FREE["beta"]) < 1e-8
    for k_, nm in (("C", "_cons"), ("W", "xwar"), ("T", "term_years")):
        E.add(f"S18_{k_}", gin.coef(nm), "{:.4f}"); E.add(f"S18_{k_}SE", gin.sei(nm), "{:.4f}")
    E.add("S18_N", f"{gin.n:,}"); E.add("S18_CENS", f"{gin.n_cens:,}"); E.add("S18_LL", gin.ll, "{:,.2f}")
    E.add("S18_FREE_W", gfr.coef("xwar"), "{:.4f}"); E.add("S18_FREE_LL", gfr.ll, "{:,.2f}")
    lr, p = SE.lrtest(gfr, gin, 1)
    E.add("S18_LR", lr, "{:.2f}"); E.p("S18_P", p)
    log(f"  step 18, the goalie price line: intercept {gin.coef('_cons'):.4f}, per forecast win {gin.coef('xwar'):.4f}, "
        f"per year of term {gin.coef('term_years'):.4f} ({gin.n} contracts); term LR {lr:.2f}, {E.v['S18_P']} = the lock")

    # ---- the forecast pieces on the 2025-26 page ---------------------------------------------------------------------
    P = pd.read_csv(OUT / "skater_forecast_pairs.csv")
    GPF = ["tr_gp_share", "exp_seasons", "age_c", "age_c2", "tw_war"]
    PPF = ["p_age_c", "tw_war", "tr_gp_share", "is_d", "under_contract", "contract_unknown"]
    used = {r["h"]: r["columns"].split()[1:] for r in fits
            if r["regression"] == "skater chance of playing" and r["page"] == TABLE_PAGE}
    gs_line, gs_def, pp_sq, pp_exp, pp_r2 = [], [], [], [], []
    for h in range(6):
        x = P[(P["h"] == h) & (P["season"] < TABLE_PAGE)].dropna(subset=["y_gp_share"] + GPF)
        m = SE.OLS(x["y_gp_share"], x[GPF], GPF, cluster=x["career_num"], const=True)
        mine = next(r for r in fits if r["regression"] == "skater games share" and r["page"] == TABLE_PAGE and r["h"] == h)
        order = ["_cons", "tr_gp_share", "exp_seasons", "age_c", "tw_war", "age_c2"]          # the model's column order
        assert max(abs(m.coef(c) - mine[f"b{i}"]) for i, c in enumerate(order)) < 1e-9, (h,)
        if h == 0:
            for c in ["_cons"] + GPF:
                E.add(f"S19_{c.upper()}", f"{m.coef(c):.4f} ({m.sei(c):.4f})")
            E.add("S19_R2", m.r2, "{:.4f}"); E.add("S19_N", f"{m.n:,}")
            # built up one term at a time (the document's table "Games share in the valuation season, built up")
            bu = []
            for cols in (["tr_gp_share"], ["tr_gp_share", "exp_seasons"], ["tr_gp_share", "exp_seasons", "age_c", "age_c2"]):
                xb = P[(P["h"] == 0) & (P["season"] < TABLE_PAGE)].dropna(subset=["y_gp_share"] + cols)
                bu.append(SE.OLS(xb["y_gp_share"], xb[cols], cols, cluster=xb["career_num"], const=True).r2)
            E.add("S19_BUILD", ", ".join(f"{r:.4f}" for r in bu + [m.r2]))
        gs_line.append(f"h{h} {m.r2:.3f}")
        md = SE.OLS(x["y_gp_share"], x[GPF + ["is_d"]], GPF + ["is_d"], cluster=x["career_num"], const=True)
        gs_def.append(f"h{h} {md.pval('is_d'):.3f}")
        # each logit drops the rows missing any of its own variables, as Stata does
        y = P[(P["h"] == h) & (P["season"] < TABLE_PAGE)].dropna(subset=PPF + ["y_played"])
        assert set(used[h]) == set(PPF), (h, used[h])                     # every column carries a coefficient here
        lg = SE.Logit(y["y_played"], y[PPF], PPF, cluster=y["career_num"])
        if h == 0:
            for c in ["_cons"] + PPF:
                E.add(f"S20_{c.upper()}", f"{lg.coef(c):.4f} ({lg.se[lg.names.index(c)]:.4f})")
            E.add("S20_PR2", lg.pr2, "{:.4f}"); E.add("S20_N", f"{lg.n:,}")
            # built up (the document's table "Chance of playing in the valuation season, built up")
            bu = []
            for cols in (["p_age_c"], ["p_age_c", "tw_war", "tr_gp_share", "is_d"]):
                yb = P[(P["h"] == 0) & (P["season"] < TABLE_PAGE)].dropna(subset=["y_played"] + cols)
                bu.append(SE.Logit(yb["y_played"], yb[cols], cols, cluster=yb["career_num"]).pr2)
            E.add("S20_BUILD", ", ".join(f"{r:.4f}" for r in bu + [lg.pr2]))
        y2 = y.dropna(subset=["p_age_c2", "exp_seasons"])
        lo = SE.Logit(y2["y_played"], y2[PPF + ["p_age_c2", "exp_seasons"]], PPF + ["p_age_c2", "exp_seasons"],
                      cluster=y2["career_num"])
        pp_r2.append(f"h{h} {lg.pr2:.3f}")
        pp_sq.append(f"h{h} {lo.pval('p_age_c2'):.3f}")
        pp_exp.append(f"h{h} {lo.pval('exp_seasons'):.3f}")
    E.add("S19_R2_BY_H", ", ".join(gs_line)); E.add("S19_DEF_P", ", ".join(gs_def))
    E.add("S20_SQ_P", ", ".join(pp_sq)); E.add("S20_EXP_P", ", ".join(pp_exp)); E.add("S20_PR2_BY_H", ", ".join(pp_r2))
    log(f"  step 19, the games share (2025-26 page, clustered by player): h=0 R-squared {E.v['S19_R2']}, N {E.v['S19_N']}"
        f"; = the model's fits; R-squared by season ahead {E.v['S19_R2_BY_H']}; defenceman p {E.v['S19_DEF_P']}")
    log(f"  step 20, the chance of playing: h=0 pseudo R-squared {E.v['S20_PR2']}, N {E.v['S20_N']}; age squared p "
        f"{E.v['S20_SQ_P']}; seasons since debut p {E.v['S20_EXP_P']}")

    A = pd.read_csv(OUT / "goalie_age_rows.csv")
    a = A[A["season"] < TABLE_PAGE]
    ma = SE.OLS(a["war_less_pulled"], a[["age_c"]], ["age_c"], const=True)
    E.add("S21_B", ma.coef("age_c"), "{:.4f}"); E.add("S21_SE", ma.sei("age_c"), "{:.4f}"); E.p("S21_P", ma.pval("age_c"))
    E.add("S21_N", f"{ma.n:,}")
    Q = pd.read_csv(OUT / "goalie_play_rows.csv")
    gh = sorted(r["h"] for r in fits if r["regression"] == "goalie chance of playing" and r["page"] == TABLE_PAGE)
    sq = []
    for h in gh:
        q = Q[(Q["h"] == h) & (Q["season"] < TABLE_PAGE)]
        lg = SE.Logit(q["played"], q[["age_c", "pulled", "gp_share_last"]], ["age_c", "pulled", "gp_share_last"])
        if h == 0:
            for c in ("_cons", "age_c", "pulled", "gp_share_last"):
                E.add(f"S22_{c.upper()}", f"{lg.coef(c):.4f}")
            E.add("S22_N", f"{lg.n:,}")
        l2 = SE.Logit(q["played"], q[["age_c", "pulled", "gp_share_last", "age_c2"]], ["age_c", "pulled", "gp_share_last", "age_c2"])
        sq.append(f"h{h} {l2.pval('age_c2'):.3f}")
    E.add("S22_SQ_P", ", ".join(sq)); E.add("S22_H", f"0 to {max(gh)}"); E.add("S22_HMAX", str(max(gh)))
    assert gh == list(range(max(gh) + 1)), gh                      # the fitted seasons ahead run 0, 1, ... without a gap
    log(f"  step 21, the goalie age term: {ma.coef('age_c'):.4f} WAR a year ({ma.sei('age_c'):.4f}), {E.v['S21_P']}, "
        f"{ma.n} goaltender-seasons")
    log(f"  step 22, the goalie chance of playing: fitted for seasons ahead {E.v['S22_H']}; age squared p {E.v['S22_SQ_P']}")
    E.write(OUT / "expected_players.json")
    log(f"  wrote expected_players.json ({len(E.v)} figures)")


def main():
    log(SCRIPT_VERSION)
    OUT.mkdir(parents=True, exist_ok=True)
    log(f"  skater_forecast v{SF.SCRIPT_VERSION}, participation_model v{PMOD.SCRIPT_VERSION}, "
        f"xnpv1_price_line v{XPL.SCRIPT_VERSION}; outputs in {OUTPUT_DIR.resolve()}")
    fc = SF.ContractForecaster()
    contracts, _ = CS.load_contracts()
    log("\nTHE SKATER PRICE LINE")
    skater_price_line(fc)
    log("\nTHE GOALIE PRICE LINE")
    CN, GP = goalie_price_line()
    log("\nTHE SKATER GAMES SHARE AND CHANCE OF PLAYING, every page")
    P = skater_pairs(fc, contracts)
    fits = skater_pages(fc, contracts, P)
    log("\nTHE GOALIE AGE TERM AND CHANCE OF PLAYING, every page")
    fits += goalie_pieces(CN, GP)
    pd.DataFrame(fits).to_csv(OUT / "forecast_fits.csv", index=False)
    log(f"\n  wrote forecast_fits.csv ({len(fits):,} fits)")
    expected_figures(fits)
    (OUT / "stata_export_players_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
