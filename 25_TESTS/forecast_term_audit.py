"""forecast_term_audit.py -- the skater forecast's terms that are not statistically significant, and three settings
Thomas asked to test (report only).

WHY (Thomas, 2026-10-21, round 2 of his notes on "Valuing Players, Draft Picks, and Prospects"; MODEL_DIRECTIVES,
"Thomas's second round of notes", items 2 and 3). "I'm getting tired of seeing things that aren't statistically
significant in these results." Every adopted regression is checked, and the rule for dropping a term was agreed BEFORE
any result was seen: a term goes if it is not statistically significant at the 5% level AND dropping it does not worsen
the held-out forecast; the failing terms are tested together as a set as well as one at a time; a term that fails on p
but helps the held-out forecast goes to Thomas with both numbers. Each season ahead should keep the same terms "in
theory", decided once the results are seen, so each candidate is scored on all seasons ahead together, and by season.
TEST ONLY: nothing in 20_CODE changes and nothing is adopted by running it. The back-test is not read.

PART A, IN SAMPLE (the 2025-26 fit, the one the document tables; every fitted season ahead, not only 0-5). Each term of
the games-share line (least squares) and the chance of playing (logistic, unpenalised), standard errors clustered by
player, as 25_TESTS/model_doc_figures.py fits them for Tables 4, 5, A1 and A2. Every term with p > 0.05 is listed.

PART B, HELD OUT (the development pages 2015-16 to 2021-22, each forecast fitted only on seasons before its page; the
pages 2022-2025 are not touched). Each version changes ONE thing against the build unless it says otherwise:
  games share         G1 no defenceman term; G2 floor at 0 instead of 0.05 (the cap at 1 kept)
  chance of playing   P1 no (age - 27) squared; P2 no seasons since his debut; P3 no no-contract-record marker
  together            S1 = G1 + P1 + P2 (every term failing in every season ahead it is tabled for, 0-5, other than
                      the marker); S2 = S1 + P3
  the starting level  R1 no games weighting: plain 50/30/20 on his own rate AND on the comparables' level
                      (aging_curve.LEVEL_BY_GAMES = False), the two sides kept the same, as Thomas required 2026-10-04
                      R2 a counting season at 5 or more games; R3 at 20 or more (forecast_config.MIN_GP, the 10 that
                      decides which seasons are evidence of a player's rate, in his own rate and in the anchors every
                      regression reads; the comparables' level keeps its own 20, aging_curve.MIN_GP, as it is today)
  CENTRING (Thomas: "check out both options"): age centred at 27 against centred at the sample's mean age and not
  centred, in the games share. A shift of centre is a re-labelling of the same quadratic: the run checks the forecasts
  are identical and logs the coefficients each way.

SCORES (the same rows for every version; CLAUDE.md: same rows and weights, identical targets)
  rows      each skater on each page with a 10-game season in the three before (the build's anchors), seasons 0-5
            ahead that have been played. R2 and R3 change who has an anchor: they are scored on the rows every version
            answers, and the rows each one loses or gains are counted.
  start     root mean squared error of WAR per 82 in the valuation season, weighted by games, seasons he played
  1-5 ahead the same, one to five seasons out
  season WAR chance of playing x WAR per 82 x games share against his actual season WAR (0 if he did not play)
  share     root mean squared error of the games share, seasons he appeared in; log loss of the chance of playing
  p         one-sided: the share of 2,000 redraws of careers (seed 20261021) in which the version's summed squared
            error is NOT below the build's ("version better"), and the reverse ("build better")
GUARD: the build reproduces start 1.1506 and one-to-five-ahead 1.3569 on 40,510 rows, as 25_TESTS/floor_spread_measure.py
scores today's model (run 2026-10-21). The 2026-10-05 record, 1.3587, predates the September 15 ages, the name crosswalk
and the integer-age fix (floor_spread_measure gave 1.3579 on 2026-10-14); v1.0's first run stopped on it. Season WAR,
the share and the log loss are reported fresh: the contract table changed on 2026-10-20.

HOW TO RUN (repo root, laptop; needs the contract export; about 1-2 hours):
    python 25_TESTS/forecast_term_audit.py
Writes 30_OUTPUT/forecast_term_audit_log.txt, forecast_term_audit_scores.csv, forecast_term_audit_insample.csv.
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import statsmodels.api as sm

import aging_curve as AC
import forecast_config as C
import information_set as ISET
import participation_model as PM
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "forecast_term_audit.py v1.2 (2026-10-21)"   # v1.2: all rows as well as the common rows; the floor counted; v1.1: the guard on today's figures
PAGES = C.DEV_PAGES
TABLE_PAGE = 2025
HS = tuple(range(6))
NBOOT, SEED = 2000, 20261021
RECORDED = {"start": 1.1506, "whole": 1.3569, "rows": 40510}   # floor_spread_measure.py on today's model, 2026-10-21
LOG = []
ORIG_ANCHORS = SF._anchors
ORIG_MIN_GP = C.MIN_GP


def log(s=""):
    print(s, flush=True)
    LOG.append(str(s))


def wrmse(e, w):
    return float(np.sqrt(np.sum(w * e ** 2) / np.sum(w)))


def logloss(p, y):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


# ---------------------------------------------------------------------------------------------------- part A
def insample(table, contracts):
    """Every term's p-value in the 2025-26 fit, every fitted season ahead."""
    iset = ISET.build(table, ISET.decision_date_for_page(TABLE_PAGE), t0=TABLE_PAGE)
    mod = SF.XNPV1().fit(iset.seasons, before=TABLE_PAGE)
    pairs = mod._training_pairs(iset.seasons, TABLE_PAGE, C.CANDIDATE_HORIZONS)
    out = []
    log(f"\nPART A. IN SAMPLE, the {TABLE_PAGE}-{(TABLE_PAGE + 1) % 100:02d} fit; fitted seasons ahead "
        f"{list(mod.fitted_horizons_)}. Terms with p > 0.05 (two-sided, errors clustered by player):")
    for h in mod.fitted_horizons_:
        s_ = pairs[pairs["h"] == h].replace([np.inf, -np.inf], np.nan).dropna(subset=["y_gp_share"] + SF.GP_FEATURES)
        grp = pd.factorize(s_["career_key"])[0]
        r_ = sm.OLS(s_["y_gp_share"].to_numpy(float), sm.add_constant(s_[SF.GP_FEATURES].to_numpy(float))).fit(
            cov_type="cluster", cov_kwds={"groups": grp})
        for i, c in enumerate(["intercept"] + SF.GP_FEATURES):
            out.append({"model": "games share", "h": h, "term": c, "coef": r_.params[i], "se": r_.bse[i],
                        "p": r_.pvalues[i], "n": len(s_)})
    part = mod.part_
    played = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
    anchors = SF._anchors(played, 3)
    act = iset.seasons.set_index(["career_key", "syr"])["GP"]
    for h in mod.fitted_horizons_:
        a_ = anchors[anchors["t0"] + h < TABLE_PAGE]
        dd = part._rows(a_, h)
        ix = pd.MultiIndex.from_arrays([dd["career_key"], dd["season"]])
        dd["y"] = (act.reindex(ix).fillna(0.0).to_numpy() >= C.PARTICIPATION_GP).astype(float)
        used = list(part.used_[h])
        dd = dd.replace([np.inf, -np.inf], np.nan).dropna(subset=used + ["y"])
        grp = pd.factorize(dd["career_key"])[0]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r_ = sm.Logit(dd["y"].to_numpy(float), sm.add_constant(dd[used].to_numpy(float), has_constant="add")).fit(
                disp=0, cov_type="cluster", cov_kwds={"groups": grp}, maxiter=200)
        for i, c in enumerate(["intercept"] + used):
            out.append({"model": "chance of playing", "h": h, "term": c, "coef": r_.params[i], "se": r_.bse[i],
                        "p": r_.pvalues[i], "n": len(dd)})
    A = pd.DataFrame(out)
    for model, g in A.groupby("model", sort=False):
        log(f"  {model}:")
        for term, gg in g.groupby("term", sort=False):
            bad = gg[gg["p"] > 0.05]
            if len(bad):
                log(f"    {term:<18} fails in {len(bad)} of {len(gg)} seasons ahead: "
                    + ", ".join(f"+{int(r.h)} (p = {r.p:.3f})" for r in bad.itertuples()))
    # centring: the games share at the valuation season, three ways
    s0 = pairs[pairs["h"] == 0].replace([np.inf, -np.inf], np.nan).dropna(subset=["y_gp_share"] + SF.GP_FEATURES)
    mean_age = float(s0["age"].mean())
    fits = {}
    for nm, ctr in (("centred at 27 (today)", 27.0), (f"centred at the mean age, {mean_age:.2f}", mean_age),
                    ("not centred", 0.0)):
        X = s0[["tr_gp_share", "is_D", "exp_seasons", "tw_WAR"]].assign(a=s0["age"] - ctr, a2=(s0["age"] - ctr) ** 2)
        r_ = sm.OLS(s0["y_gp_share"].to_numpy(float), sm.add_constant(X.to_numpy(float))).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(s0["career_key"])[0]})
        fits[nm] = r_
    f0 = list(fits.values())[0].fittedvalues
    gap = max(float(np.max(np.abs(r.fittedvalues - f0))) for r in fits.values())
    log(f"\n  CENTRING, games share at the valuation season ({len(s0):,} player-seasons): the fitted shares differ by at "
        f"most {gap:.1e} across the three ({'identical: PASS' if gap < 1e-9 else 'NOT IDENTICAL'})")
    names = ["intercept", "trailing games share", "defenceman", "seasons since debut", "trailing WAR", "age", "age squared"]
    for nm, r_ in fits.items():
        log(f"    {nm:<32}" + "; ".join(f"{n} {b:+.4f} (p {p:.3f})" for n, b, p in zip(names, r_.params, r_.pvalues)
                                       if n in ("intercept", "age", "age squared")))
    A.to_csv(C.out_path("forecast_term_audit_insample.csv"), index=False)
    return A


# ---------------------------------------------------------------------------------------------------- part B
def fit_share(pairs, h, feats):
    s = pairs[pairs["h"] == h].dropna(subset=["y_gp_share"] + feats)
    return SF._ols(s[feats], s["y_gp_share"]) if len(s) > 50 else None


def plain_anchors(*args, **kw):
    """R1: his own rate on plain 50/30/20 (the trailing rate per 82 the anchors already carry as tr_WAR)."""
    a = ORIG_ANCHORS(*args, **kw)
    if "tr_WAR" in a.columns:
        a["own_82"] = a["tr_WAR"]
    return a


def page_forecast(iset, t0, subs, setup):
    """A full refit of the forecast on page t0 under a setting, the build's machinery throughout."""
    SF._anchors, C.MIN_GP, AC.LEVEL_BY_GAMES = setup["anchors"], setup["min_gp"], setup["by_games"]
    try:
        if setup.get("new_curve"):
            SF.XNPV1._curves.pop(t0, None)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        if setup.get("new_curve"):
            SF.XNPV1._curves.pop(t0, None)     # the build's curve is rebuilt for the next page's build
    finally:
        SF._anchors, C.MIN_GP, AC.LEVEL_BY_GAMES = ORIG_ANCHORS, ORIG_MIN_GP, True
    return mod, pr


def evaluate(D, ARMS, title):
    """Every version's errors and one-sided p against the build, on the rows of D."""
    hh = D["h"].to_numpy()
    g = D["career_key"].to_numpy()
    played_ok = ((D["gp"] > 0) & np.isfinite(D["y82"])).to_numpy()
    w = np.where(played_ok, D["gp"], 0.0)
    app = np.isfinite(D["share_act"]).to_numpy()
    y = D["played"].to_numpy()

    def losses(arm):
        r, s, p = D[f"r|{arm}"].to_numpy(), D[f"s|{arm}"].to_numpy(), D[f"p|{arm}"].to_numpy()
        e82 = np.where(played_ok, r - D["y82"].to_numpy(), 0.0)
        return {"start_sq": np.where(hh == 0, w * e82 ** 2, 0.0), "whole_sq": np.where(hh > 0, w * e82 ** 2, 0.0),
                "war_sq": (p * r * s - D["war_act"].to_numpy()) ** 2,
                "share_sq": np.where(app, (s - D["share_act"].to_numpy()) ** 2, 0.0), "logloss": logloss(p, y)}

    L = {arm: losses(arm) for arm in ARMS}

    def score(arm, m=None):
        m = np.ones(len(D), bool) if m is None else m
        Lx = L[arm]
        return {"start": float(np.sqrt(Lx["start_sq"][m].sum() / w[m & (hh == 0)].sum())) if (m & (hh == 0)).any() else np.nan,
                "whole": float(np.sqrt(Lx["whole_sq"][m].sum() / w[m & (hh > 0)].sum())) if (m & (hh > 0)).any() else np.nan,
                "war": float(np.sqrt(Lx["war_sq"][m].mean())), "share": float(np.sqrt(Lx["share_sq"][m & app].mean())),
                "logloss": float(Lx["logloss"][m].mean())}

    codes, uniq = pd.factorize(g)
    rng = np.random.default_rng(SEED)
    idx = [rng.integers(0, len(uniq), len(uniq)) for _ in range(NBOOT)]

    def p_better(la, lb):
        """One-sided: the share of redraws in which la's summed loss is NOT below lb's."""
        sa = np.bincount(codes, la, len(uniq)); sb = np.bincount(codes, lb, len(uniq))
        return 1.0 - float(np.mean([sa[ix].sum() < sb[ix].sum() for ix in idx]))

    log(f"\nPART B. HELD OUT: {title}; {len(uniq):,} players. Errors: start and 1-5 ahead in WAR per 82 (weighted by")
    log("games); season WAR in wins; share in share of 82 games; log loss of the chance of playing. p (one-sided, 2,000")
    log("redraws of careers): 'version better' = share of redraws in which the version's summed squared season-WAR error is")
    log("NOT below the build's; 'build better' the reverse. Below 0.05: statistically significant at the 5% level.")
    log(f"  {'version':<34}{'start':>8}{'1-5 ahead':>10}{'season WAR':>11}{'share':>8}{'log loss':>9}"
        f"{'p: version':>11}{'p: build':>9}   (start and 1-5 ahead: p version / p build, R versions)")
    rows = []
    for arm in ARMS:
        s = score(arm)
        rec = {"rows_set": title, "version": arm, **s, "rows": int(len(D))}
        if arm != "base":
            rec["p_version_better_war"] = p_better(L[arm]["war_sq"], L["base"]["war_sq"])
            rec["p_build_better_war"] = p_better(L["base"]["war_sq"], L[arm]["war_sq"])
            for k in ("start_sq", "whole_sq", "share_sq", "logloss"):
                rec[f"p_version_better_{k}"] = p_better(L[arm][k], L["base"][k])
                rec[f"p_build_better_{k}"] = p_better(L["base"][k], L[arm][k])
        for h in HS:
            rec[f"war_h{h}"] = score(arm, hh == h)["war"]
        rows.append(rec)
        extra = "" if arm == "base" else (f"{rec['p_version_better_war']:>11.4f}{rec['p_build_better_war']:>9.4f}"
                                          + (f"   start {rec['p_version_better_start_sq']:.3f}/{rec['p_build_better_start_sq']:.3f},"
                                             f" 1-5 {rec['p_version_better_whole_sq']:.3f}/{rec['p_build_better_whole_sq']:.3f}"
                                             if arm.startswith("R") else ""))
        log(f"  {arm:<34}{s['start']:>8.4f}{s['whole']:>10.4f}{s['war']:>11.4f}{s['share']:>8.4f}{s['logloss']:>9.4f}" + extra)
    log("  season WAR by season ahead (wins)")
    log(f"  {'version':<34}" + "".join(f"{'+' + str(h):>8}" for h in HS))
    for r in rows:
        log(f"  {r['version']:<34}" + "".join(f"{r[f'war_h{h}']:>8.4f}" for h in HS))
    return rows


def main():
    C.banner("forecast_term_audit.py", SCRIPT_VERSION)
    log(f"{SCRIPT_VERSION}; skater_forecast v{SF.SCRIPT_VERSION}")
    bd, _ = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = SF.war_age_path(); SF.check_age_coverage(path)
    log(f"age table: {path}")
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    log(f"contract export: {len(contracts):,} rows")
    insample(table, contracts)

    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"),
                                                   share=("gp_share", "first"))
    SETUPS = {"R1 no games weighting": {"anchors": plain_anchors, "min_gp": ORIG_MIN_GP, "by_games": False,
                                        "new_curve": True},
              "R2 counting season at 5 games": {"anchors": ORIG_ANCHORS, "min_gp": 5, "by_games": True},
              "R3 counting season at 20 games": {"anchors": ORIG_ANCHORS, "min_gp": 20, "by_games": True}}
    PDROP = {"P1 no age squared": ("age_sq",), "P2 no seasons since debut": ("exp_seasons",),
             "P3 no no-contract-record marker": ("contract_unknown",),
             "S1 G1+P1+P2": ("age_sq", "exp_seasons"), "S2 S1+P3": ("age_sq", "exp_seasons", "contract_unknown")}
    f_noD = [f for f in SF.GP_FEATURES if f != "is_D"]
    frames, used_log = [], []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        pairs = mod._training_pairs(iset.seasons, t0, C.CANDIDATE_HORIZONS)
        share = {"G1 no defenceman": {h: np.clip(SF._apply(fit_share(pairs, h, f_noD), pa[f_noD], pa["tr_gp_share"]),
                                                 0.05, 1.0) for h in HS},
                 "G2 floor at 0": {h: np.clip(SF._apply(mod.gp_coef_.get(h), pa[SF.GP_FEATURES], pa["tr_gp_share"]),
                                              0.0, 1.0) for h in HS}}
        share["S1 G1+P1+P2"] = share["S2 S1+P3"] = share["G1 no defenceman"]
        play = {}
        n = mod.N_SEASONS
        for arm, excl in PDROP.items():
            part = PM.ParticipationModel(contracts, exclude=tuple(mod.PART_EXCLUDE) + excl,
                                         contract_state=mod.CONTRACT_STATE).fit(
                iset.seasons, t0, anchors_fn=lambda p: SF._anchors(p, n), horizons=mod.fitted_horizons_)
            assert not any(set(excl) & set(part.used_.get(h, [])) for h in HS), (arm, part.used_)   # GUARD
            used_log.append(f"    {t0} {arm}: terms used at +0 {part.used_.get(0)}")
            keep = mod.part_
            mod.part_ = part
            play[arm] = {h: mod._p_play(pa, subs, h) for h in HS}
            mod.part_ = keep
        full = {}
        for arm, setup in SETUPS.items():
            m2, p2 = page_forecast(iset, t0, subs, setup)
            full[arm] = p2
        rows = []
        for h in HS:
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(pa.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            d = pd.DataFrame({"career_key": pa.index, "t0": t0, "h": h, "gp": gp, "y82": rr["y"].to_numpy(),
                              "share_act": np.where(gp > 0, rr["share"].to_numpy(), np.nan),
                              "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                              "played": (gp >= C.PARTICIPATION_GP).astype(float),
                              "r|base": ph["rate_82"].to_numpy(), "s|base": ph["gp_share"].to_numpy(),
                              "p|base": ph["p_play"].to_numpy(),
                              "s_raw": SF._apply(mod.gp_coef_.get(h), pa[SF.GP_FEATURES], pa["tr_gp_share"])})
            for arm, v in share.items():
                d[f"s|{arm}"] = v[h]
            for arm, v in play.items():
                d[f"p|{arm}"] = v[h]
            for arm, p2 in full.items():
                q = p2.xs(h, level="h").reindex(pa.index)
                d[f"r|{arm}"], d[f"s|{arm}"], d[f"p|{arm}"] = (q["rate_82"].to_numpy(), q["gp_share"].to_numpy(),
                                                               q["p_play"].to_numpy())
            rows.append(d)
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players")
    log("\n".join(used_log))

    D = pd.concat(frames, ignore_index=True)
    # GUARD on the build's own rows, before any version narrows them
    ok_ = ((D["gp"] > 0) & np.isfinite(D["y82"]) & np.isfinite(D["r|base"])).to_numpy()
    e_ = (D["r|base"] - D["y82"]).to_numpy()
    w_ = np.where(ok_, D["gp"], 0.0)
    got = {"start": wrmse(e_[ok_ & (D["h"] == 0).to_numpy()], w_[ok_ & (D["h"] == 0).to_numpy()]),
           "whole": wrmse(e_[ok_ & (D["h"] > 0).to_numpy()], w_[ok_ & (D["h"] > 0).to_numpy()])}
    got["rows"] = len(D)
    bad = [k for k, v in RECORDED.items() if (got[k] != v if k == "rows" else abs(round(got[k], 4) - v) > 1e-9)]
    log(f"\nGUARD: rows {got['rows']:,} (recorded {RECORDED['rows']:,}); the build gives start {got['start']:.4f} and one to five ahead {got['whole']:.4f} on its own rows, "
        f"against the recorded {RECORDED['start']} and {RECORDED['whole']}: {'PASS' if not bad else 'FAIL ' + str(bad)}")
    if bad:
        raise RuntimeError("the build's rate is not reproduced; results not read")
    ARMS =["base", "G1 no defenceman", "G2 floor at 0", "P1 no age squared", "P2 no seasons since debut",
            "P3 no no-contract-record marker", "S1 G1+P1+P2", "S2 S1+P3", *SETUPS]
    for arm in ARMS:                                    # a version that does not change a part keeps the build's
        for part in ("r", "s", "p"):
            if f"{part}|{arm}" not in D:
                D[f"{part}|{arm}"] = D[f"{part}|base"]
    D.to_pickle(C.out_path("forecast_term_audit_rows.pkl"))         # v1.2: every row and version, for re-scoring
    raw = D["s_raw"].to_numpy(float)
    log(f"\nTHE GAMES-SHARE FLOOR: of {np.isfinite(raw).sum():,} forecast shares (seasons 0-5 ahead, pages {PAGES[0]}-{PAGES[-1]}), "
        f"{int((raw < 0.05).sum())} fall below 0.05 before the floor and {int((raw < 0).sum())} below 0; "
        f"{int((raw > 1).sum())} are above the cap at 1")
    log(f"\nROWS: {len(D):,} player-seasons on pages {PAGES[0]}-{PAGES[-1]}")
    for arm in SETUPS:
        lost = int((np.isfinite(D["r|base"]) & ~np.isfinite(D[f"r|{arm}"])).sum())
        log(f"  {arm}: no forecast for {lost:,} of the build's rows (no counting season in the three before)")
    base_ok = np.isfinite(D["r|base"].to_numpy())
    allv = [a_ for a_ in ARMS if np.isfinite(D.loc[base_ok, f"r|{a_}"]).all()]
    common = np.ones(len(D), bool)
    for arm in ARMS:
        common &= np.isfinite(D[f"r|{arm}"].to_numpy())
    rows = evaluate(D[base_ok].reset_index(drop=True), allv,
                    f"ALL {int(base_ok.sum()):,} ROWS THE BUILD ANSWERS (every version that answers each of them)")
    rows += evaluate(D[common].reset_index(drop=True), ARMS,
                     f"THE {int(common.sum()):,} ROWS THAT EVERY VERSION ANSWERS, the 20-game version included")
    S = pd.DataFrame(rows)
    S.to_csv(C.out_path("forecast_term_audit_scores.csv"), index=False)
    C.record_inspection("forecast_term_audit.py", "pages", PAGES,
                        "terms not statistically significant; games weighting; counting threshold (Thomas 2026-10-21)")
    p = C.out_path("forecast_term_audit_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
