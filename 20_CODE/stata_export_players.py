"""
stata_export_players.py -- the player model's regression data as flat CSVs, for Stata (v1.0).

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
import xnpv1_price_line as XPL                  # noqa: E402

SCRIPT_VERSION = "stata_export_players.py v1.0 (2026-10-23)"
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
OUT = OUTPUT_DIR / "stata"
PAGES = range(2010, 2027)                       # 2010-11 to 2026-27, the pages the model values on
PENALTY = 1e-4                                  # participation_model's fit_regularized alpha
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
    pd.DataFrame(play).to_csv(OUT / "goalie_play_rows.csv", index=False)
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
    (OUT / "stata_export_players_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
