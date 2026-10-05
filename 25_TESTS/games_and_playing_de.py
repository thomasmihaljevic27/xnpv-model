"""games_and_playing_de.py -- investigations D and E (with open decision 2) on the built forecast.

WHY (Thomas, 2026-10-04/05; 00_STATE/MODEL_DIRECTIVES.md, plan of record step 3; versions approved
2026-10-05). D asks whether the games-share equation's form is right; E whether the chance of playing
treats players under contract fairly, and (open decision 2) whether a contract's chance of playing
should read contract status at its signing instead of July 1. Each version is ONE change, scored alone
against the build (skater_forecast v2.1). TEST ONLY: nothing in 20_CODE changes; nothing is adopted.

THE VERSIONS
  D1  the games share as a fractional logit: a logistic curve fitted to the share (statsmodels GLM,
      binomial family, logit link; Papke and Wooldridge 1996), same inputs as today's line
      (skater_forecast.GP_FEATURES); it cannot pass a full season, so no cap or floor
  D2  today's straight line plus age squared (a curved age effect), cap and floor kept
  D3  D1 and D2 together (the logistic curve with age squared)
  E0  DIAGNOSTIC, no change: players under contract for the season (as known on 1 July of the page;
      seasons 2018-19 on, where the export can see contracts): forecast chance of playing against how
      often they played, by quality (trailing WAR total) and season ahead
  E1  the before-2018 marker put back (participation_model's `contract_unknown`, which under the
      "observable" state is 1 exactly for seasons before the export's first end year; the build
      excludes it, XNPV1.PART_EXCLUDE)
  E2  OPEN DECISION 2. Contracts whose first season is the page's season and that were signed after
      1 July of it (until 30 June of the next year, the window contract_npv accepts): the chance of
      playing for each season the contract covers, read at 1 July (today, for a contract valuation)
      and at the signing (production's own XNPV1.p_play_signed), each against whether he played.
      Development pages from 2018 only (the export's coverage).
  E3  a contract effect that varies with quality: under-contract x trailing WAR total added to the
      chance-of-playing model (a subclass of participation_model.ParticipationModel adds the column)

HOW. Per development page t0 (2015-2021) production XNPV1 is fitted once. D refits only the games-share
lines on production's own training pairs (XNPV1._training_pairs) and swaps the page's games shares; E1
and E3 refit only the chance-of-playing model with production's settings and the one change, and swap
the page's chances; the rate per 82 is production's in every version.

SCORES (40,510 player-seasons, 1,609 players; 2,000 career resamples against the build)
    games share   RMSE of the share, seasons he appeared in
    playing       log loss and Brier score of the chance of playing (one game or more)
    season WAR    chance x rate x share against his actual season WAR (0 if he did not play)
  Baseline guard (the build, recorded): start 1.1506, whole 1.3587, season WAR 0.8088 / MAE 0.4673,
  games share 0.2657, log loss 0.4044, Brier 0.1313.
  CAVEAT: the development pages have been examined by many variants; these results choose between
  versions, they are not fresh evidence.

HOW TO RUN (repo root, laptop; needs the contract export; roughly 20-30 minutes):
    python 25_TESTS/games_and_playing_de.py
Writes 30_OUTPUT/games_and_playing_de_log.txt.
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import participation_model as PM
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
NBOOT = 2000
BASE = {"start": 1.1506, "whole": 1.3587, "war_rmse": 0.8088, "war_mae": 0.4673, "share": 0.2657,
        "logloss": 0.4044, "brier": 0.1313, "rows": 40510}
D_ARMS = ["D1 fractional logit", "D2 line + age squared", "D3 logit + age squared"]
E_ARMS = ["E1 before-2018 marker", "E3 contract x quality"]
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def wrmse(e, w):
    return float(np.sqrt(np.sum(w * e ** 2) / np.sum(w)))


def logloss(p, y):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def boot_lower(la, lb, groups, rng):
    codes, uniq = pd.factorize(groups)
    sa = np.bincount(codes, la, len(uniq)); sb = np.bincount(codes, lb, len(uniq))
    n = len(uniq)
    return int(sum(sa[ix].sum() < sb[ix].sum() for ix in (rng.integers(0, n, n) for _ in range(NBOOT))))


# --------------------------------------------------------------------------- D: the games share
def fit_share(tr, feats, logit):
    """One season ahead's games-share model on production's training pairs: production's own line
    (SF._ols) or a fractional logit on the same rows. None when thin (production's > 50 rule)."""
    s = tr.dropna(subset=["y_gp_share"] + feats)
    if len(s) <= 50:
        return None
    if not logit:
        return ("line", SF._ols(s[feats], s["y_gp_share"]))
    import statsmodels.api as sm
    X = sm.add_constant(s[feats].to_numpy(float), has_constant="add")
    y = np.clip(s["y_gp_share"].to_numpy(float), 0.0, 1.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    return ("logit", (feats, np.asarray(r.params, float)))


def predict_share(model, a, feats):
    """Production's clip (0.05-1.0) for the line; the logistic curve as it comes for the logit.
    Rows with a missing input fall back to the trailing share, as production's _apply does."""
    fb = a["tr_gp_share"].to_numpy(float)
    if model is None:
        return np.clip(fb, 0.05, 1.0)
    kind, coef = model
    if kind == "line":
        return np.clip(SF._apply(coef, a[feats], a["tr_gp_share"]), 0.05, 1.0)
    cols, beta = coef
    M = a[cols].to_numpy(float); ok = np.isfinite(M).all(axis=1)
    out = fb.copy()
    out[ok] = 1.0 / (1.0 + np.exp(-(beta[0] + M[ok] @ beta[1:])))
    return out


# --------------------------------------------------------------------------- E3: contract x quality
class QualityContractModel(PM.ParticipationModel):
    """participation_model.ParticipationModel with one more column: under-contract x the level it
    already reads (the trailing WAR total), so a contract's effect on the odds can differ by quality."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        if "under_contract" in self.features:
            self.features = self.features + ["uc_x_level"]

    def _rows(self, anchors, h, as_of=None, table=None):
        d = super()._rows(anchors, h, as_of=as_of, table=table)
        d["uc_x_level"] = d["under_contract"] * d["level"]
        return d


def main():
    C.banner("games_and_playing_de.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    spans = PM.contract_spans(contracts)
    log(f"contract export: {len(contracts):,} rows; first end year {int(spans['end_yr'].min())}")
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"),
                                                   share=("gp_share", "first"))
    career_of = table.drop_duplicates("pkey").set_index("pkey")["career_key"].to_dict()

    frames, e2_rows, cap_raw = [], [], []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        pairs = mod._training_pairs(iset.seasons, t0, C.CANDIDATE_HORIZONS)

        # D: games-share models per season ahead
        sh = {}
        f_line, f_age = list(SF.GP_FEATURES), list(SF.GP_FEATURES) + ["age_c2"]
        for arm, feats, logit in ((D_ARMS[0], f_line, True), (D_ARMS[1], f_age, False), (D_ARMS[2], f_age, True)):
            sh[arm] = {h: predict_share(fit_share(pairs[pairs["h"] == h], feats, logit), pa, feats) for h in HS}
        for h in HS:                                   # how often today's line meets its cap or floor
            raw = SF._apply(mod.gp_coef_.get(h), pa[SF.GP_FEATURES], pa["tr_gp_share"])
            cap_raw.append(pd.DataFrame({"h": h, "raw": raw}))

        # E1 / E3: the chance of playing refitted with one change
        pp = {}
        n = mod.N_SEASONS
        for arm, cls, excl in ((E_ARMS[0], PM.ParticipationModel, ()),
                               (E_ARMS[1], QualityContractModel, tuple(mod.PART_EXCLUDE))):
            part = cls(contracts, exclude=excl, contract_state=mod.CONTRACT_STATE).fit(
                iset.seasons, t0, anchors_fn=lambda p: SF._anchors(p, n), horizons=mod.fitted_horizons_)
            if arm == E_ARMS[0]:
                used = [h for h in HS if "contract_unknown" in part.used_.get(h, [])]
                log(f"    {t0}: E1's before-2018 marker entered the fit at seasons ahead {used} "
                    f"(export coverage from {part.coverage_from_})")
            keep = mod.part_
            mod.part_ = part
            pp[arm] = {h: mod._p_play(pa, subs, h) for h in HS}
            mod.part_ = keep

        # E0: under contract for the season, as known on 1 July of the page (production's own rows)
        uc = {h: mod.part_._rows(pa.reset_index(), h)["under_contract"].to_numpy(float) for h in HS}

        # E2: late-signed contracts starting this season (the export sees them from 2018)
        if t0 >= int(spans["end_yr"].min()):
            jul1 = pd.Timestamp(year=t0, month=7, day=1)
            late = spans[(spans["start_yr"] == t0) & (spans["signed"] > jul1)
                         & (spans["signed"] < pd.Timestamp(year=t0 + 1, month=7, day=1))].copy()
            late["career_key"] = late["pkey"].map(career_of)
            late = late[late["career_key"].isin(set(pa.index))].sort_values("signed").drop_duplicates("career_key")
            if len(late):
                hs = list(range(0, min(int(late["end_yr"].max()) - t0, max(mod.fitted_horizons_)) + 1))
                sig = mod.p_play_signed(iset, late["career_key"].tolist(), hs, late["signed"].tolist())
                j1 = mod.p_play_signed(iset, late["career_key"].tolist(), hs, [jul1] * len(late))
                for h in hs:
                    s = t0 + h
                    cov = (late["end_yr"].to_numpy() >= s) & (s <= last)
                    if not cov.any():
                        continue
                    rr = res.reindex(pd.MultiIndex.from_arrays([late["career_key"], np.full(len(late), s)]))
                    played = (np.nan_to_num(rr["GP"].to_numpy()) >= C.PARTICIPATION_GP).astype(float)
                    e2_rows.append(pd.DataFrame({"career_key": late["career_key"].to_numpy()[cov], "t0": t0, "h": h,
                                                 "played": played[cov], "p_jul1": j1[h][cov], "p_signed": sig[h][cov]}))

        rows = []
        for h in HS:
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(pa.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            d = pd.DataFrame({"career_key": pa.index, "h": h, "rate": ph["rate_82"].to_numpy(),
                              "s|base": ph["gp_share"].to_numpy(), "p|base": ph["p_play"].to_numpy(),
                              "gp": gp, "y82": rr["y"].to_numpy(),
                              "share_act": np.where(gp > 0, rr["share"].to_numpy(), np.nan),
                              "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                              "played": (gp >= C.PARTICIPATION_GP).astype(float),
                              "level": pa["tw_WAR"].to_numpy(float), "uc": uc[h], "season": t0 + h})
            for arm in D_ARMS:
                d[f"s|{arm}"] = sh[arm][h]
            for arm in E_ARMS:
                d[f"p|{arm}"] = pp[arm][h]
            rows.append(d)
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players")

    D = pd.concat(frames, ignore_index=True)
    g = D["career_key"].to_numpy()
    played_ok = ((D["gp"] > 0) & np.isfinite(D["y82"])).to_numpy()
    w = np.where(played_ok, D["gp"], 0.0)
    hh = D["h"].to_numpy()
    app = np.isfinite(D["share_act"]).to_numpy()
    y = D["played"].to_numpy()

    def losses(scol, pcol):
        ew = (D[pcol] * D["rate"] * D[scol] - D["war_act"]).to_numpy()
        return {"share": np.where(app, (D[scol] - D["share_act"]).to_numpy() ** 2, 0.0),
                "logloss": logloss(D[pcol].to_numpy(), y), "brier": (D[pcol].to_numpy() - y) ** 2,
                "war_sq": ew ** 2, "war_abs": np.abs(ew)}

    arms = {"base": ("s|base", "p|base")}
    arms.update({a_: (f"s|{a_}", "p|base") for a_ in D_ARMS})
    arms.update({a_: ("s|base", f"p|{a_}") for a_ in E_ARMS})
    L = {k: losses(*v) for k, v in arms.items()}

    def score(arm, m=None):
        m = np.ones(len(D), bool) if m is None else m
        Lx = L[arm]
        return {"share": float(np.sqrt(Lx["share"][m & app].mean())), "logloss": float(Lx["logloss"][m].mean()),
                "brier": float(Lx["brier"][m].mean()), "war_rmse": float(np.sqrt(Lx["war_sq"][m].mean())),
                "war_mae": float(Lx["war_abs"][m].mean())}

    # baseline guard
    e = (D["rate"] - D["y82"]).to_numpy()
    s0 = played_ok & (hh == 0); s1 = played_ok & (hh > 0)
    b = score("base")
    got = {"start": wrmse(e[s0], w[s0]), "whole": wrmse(e[s1], w[s1]), **b, "rows": len(D)}
    log("\nbaseline (the build, v2.1) against the recorded figures:")
    bad = []
    for k, rec in BASE.items():
        ok = (got[k] == rec) if k == "rows" else abs(round(got[k], 4) - rec) < 1e-9
        log(f"  {k:9s} {got[k]:10.4f}   recorded {rec}   {'PASS' if ok else 'FAIL'}")
        bad += [] if ok else [k]
    if bad:
        raise RuntimeError(f"baseline not reproduced: {bad}; results not read")

    rng = np.random.default_rng(20261005)
    log("\nALL ROWS. 'lower in' = resamples (of 2,000 careers) in which the version's summed loss is below the build's")
    log(f"  {'version':26s}{'share':>8s}{'logloss':>9s}{'Brier':>8s}{'WAR RMSE':>10s}{'WAR MAE':>9s}"
        f"   lower in: share / logloss / Brier / WAR")
    for arm in arms:
        s = score(arm)
        tail = "" if arm == "base" else "   " + " / ".join(
            f"{boot_lower(L[arm][k], L['base'][k], g, rng):5d}" for k in ("share", "logloss", "brier", "war_sq"))
        log(f"  {arm:26s}{s['share']:8.4f}{s['logloss']:9.4f}{s['brier']:8.4f}{s['war_rmse']:10.4f}{s['war_mae']:9.4f}{tail}")
    log("  (D versions change only the games share, so their log loss and Brier equal the build's and count 0;"
        " E versions change only the chance of playing, so their share counts 0)")

    for title, k, which in (("games-share RMSE", "share", ["base"] + D_ARMS),
                            ("chance-of-playing log loss", "logloss", ["base"] + E_ARMS),
                            ("season-WAR RMSE", "war_rmse", list(arms))):
        log(f"\nBY SEASON AHEAD: {title}")
        log(f"  {'version':26s}" + "".join(f"{'+' + str(h):>8s}" for h in HS))
        for arm in which:
            log(f"  {arm:26s}" + "".join(f"{score(arm, hh == h)[k]:8.4f}" for h in HS))

    C_ = pd.concat(cap_raw, ignore_index=True)
    log("\nD: today's line against its cap (1.0) and floor (0.05), page forecasts 0-5 ahead: "
        f"{int((C_['raw'] > 1).sum()):,} of {len(C_):,} at the cap ({(C_['raw'] > 1).mean():.2%}), "
        f"{int((C_['raw'] < 0.05).sum()):,} at the floor; by season ahead at the cap: "
        + ", ".join(f"+{h} {(C_[C_['h'] == h]['raw'] > 1).mean():.2%}" for h in HS))
    hi = D["share_act"].to_numpy() >= 0.9
    log("  games-share RMSE where he actually played 90%+ of the season, by version: "
        + "; ".join(f"{arm} {score(arm, hi)['share']:.4f}" for arm in ["base"] + D_ARMS))

    # E0
    lv = D["level"].to_numpy()
    bands = (("below 0", lv < 0), ("0-1", (lv >= 0) & (lv < 1)), ("1-2", (lv >= 1) & (lv < 2)), ("2+", lv >= 2))
    m_uc = (D["uc"].to_numpy() > 0) & (D["season"].to_numpy() >= 2018)
    log(f"\nE0 DIAGNOSTIC: players under contract for the season (known 1 July of the page), seasons 2018 on: "
        f"{int(m_uc.sum()):,} player-seasons. Forecast chance of playing (build) / share who played / rows")
    log(f"  {'trailing WAR total':20s}" + "".join(f"{'+' + str(h):>22s}" for h in HS))
    for name, mk in bands + (("all", np.ones(len(D), bool)),):
        cells = []
        for h in HS:
            m = m_uc & mk & (hh == h)
            cells.append(f"{D['p|base'][m].mean():.3f} / {y[m].mean():.3f} / {int(m.sum()):4d}" if m.any() else "-")
        log(f"  {name:20s}" + "".join(f"{c:>22s}" for c in cells))
    log("  the same for the E versions (all qualities): forecast / played, by season ahead")
    for arm in E_ARMS:
        log(f"  {arm:26s}" + "  ".join(f"+{h} {D[f'p|{arm}'][m_uc & (hh == h)].mean():.3f}/{y[m_uc & (hh == h)].mean():.3f}"
                                       for h in HS if (m_uc & (hh == h)).any()))
    log("  scores on these under-contract rows: " + "; ".join(
        f"{arm} logloss {score(arm, m_uc)['logloss']:.4f}, Brier {score(arm, m_uc)['brier']:.4f}"
        for arm in ["base"] + E_ARMS))

    # E2
    E2 = pd.concat(e2_rows, ignore_index=True) if e2_rows else pd.DataFrame()
    log("\nE2 / OPEN DECISION 2: contracts signed after 1 July of their first season (pages 2018-2021), each "
        "season the contract covers")
    if len(E2):
        yy = E2["played"].to_numpy()
        lj = logloss(E2["p_jul1"].to_numpy(), yy); ls = logloss(E2["p_signed"].to_numpy(), yy)
        log(f"  {E2.groupby(['career_key', 't0']).ngroups:,} contracts, {len(E2):,} contract-seasons, "
            f"{E2['career_key'].nunique():,} players; played {yy.mean():.3f}")
        log(f"  read at 1 July (today):  mean chance {E2['p_jul1'].mean():.3f}, log loss {lj.mean():.4f}, "
            f"Brier {((E2['p_jul1'] - yy) ** 2).mean():.4f}")
        log(f"  read at the signing:     mean chance {E2['p_signed'].mean():.3f}, log loss {ls.mean():.4f}, "
            f"Brier {((E2['p_signed'] - yy) ** 2).mean():.4f}")
        log(f"  signing lower in log loss in {boot_lower(ls, lj, E2['career_key'].to_numpy(), rng)} of 2,000 resamples; "
            f"in Brier {boot_lower((E2['p_signed'] - yy).to_numpy() ** 2, (E2['p_jul1'] - yy).to_numpy() ** 2, E2['career_key'].to_numpy(), rng)}")
        log("  by season ahead (contract-seasons; played; 1 July / signing):")
        for h, gg in E2.groupby("h"):
            log(f"    +{h}: {len(gg):5,d}  played {gg['played'].mean():.3f}  {gg['p_jul1'].mean():.3f} / {gg['p_signed'].mean():.3f}")
    else:
        log("  no late-signed contracts found on these pages")

    C.record_inspection("games_and_playing_de.py", "pages", PAGES,
                        "investigations D and E, open decision 2, on the built forecast (Thomas 2026-10-05)")
    p = C.out_path("games_and_playing_de_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
