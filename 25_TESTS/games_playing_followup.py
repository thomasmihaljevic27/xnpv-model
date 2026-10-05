"""games_playing_followup.py -- D2 + E1 together, and a chance of playing for contracted seasons.

WHY (Thomas, 2026-10-05, on games_and_playing_de.py v1.0). Adopted, each scored alone: D2 (the
games-share line plus age squared) and E1 (the before-2018 marker back in the chance of playing). E3
dropped; open decision 2 decided (status read at the signing; built at step 6). CLAUDE.md: score the
adopted parts together before crediting the whole. And E0 found players under contract under-forecast,
the gap growing with the seasons ahead (all qualities: forecast 0.893 against 0.916 played in the
valuation season, 0.687 against 0.858 five seasons out). Thomas's point: a player with years left on
his deal should not have his chance lowered by other players' walk-aways. This run tests that fix.
TEST ONLY: nothing in 20_CODE changes and nothing is adopted by running it.

VERSIONS
    D2, E1        alone, as in v1.0 (guard: they must reproduce v1.0's figures)
    D2+E1         the combination
    D2+E1+K       the combination, and for each season a player is under contract (as known on the
                  valuation date) a chance of playing estimated ONLY on player-seasons under contract.
                  K is one logistic fit across seasons ahead 0..the page's fitted range, inputs the
                  chance-of-playing model's own (age - 27, its square, the trailing WAR total, the
                  trailing games share, experience, defence) plus SEASONS AHEAD (linear; a setting this
                  test introduces, because one fit per season ahead has too few contracted rows),
                  regularised as participation_model fits (alpha 1e-4), predictions clipped to
                  0.005-0.995 as it clips. Rows not under contract keep the combination's chance.
  DATA LIMIT: the export sees contracts from 2018, so a page can train K only on outcome seasons
  2018..t0-1: none on pages 2015-2018. K needs MIN_ROWS contracted rows with at least MIN_SIDE of each
  outcome; where it cannot be fitted the page keeps the combination. Results are shown for all pages
  and for 2019-2021, where K exists.
  The log also lists, per page and season ahead, whether today's fit (the build) carries the contract
  column at all (participation_model drops a column that lacks support).

SCORES as in v1.0 (40,510 player-seasons; 2,000 career resamples), plus E0's calibration table
(forecast chance against share who played, players under contract, seasons 2018 on).

HOW TO RUN (repo root, laptop; needs the contract export; about 15-25 minutes):
    python 25_TESTS/games_playing_followup.py
Writes 30_OUTPUT/games_playing_followup_log.txt.
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
from games_and_playing_de import boot_lower, fit_share, logloss, predict_share, wrmse

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
MIN_ROWS, MIN_SIDE = 400, 50          # participation_model.MIN_FIT_ROWS and MIN_LEVEL_ROWS
K_FEATURES = list(PM.BASE_FEATURES) + ["h"]
# games_and_playing_de.py v1.0, laptop 2026-10-05: (share, logloss, Brier, season-WAR RMSE)
RECORDED = {"base": (0.2657, 0.4044, 0.1313, 0.8088), "D2": (0.2654, 0.4044, 0.1313, 0.8078),
            "E1": (0.2657, 0.4047, 0.1313, 0.8085)}
ARMS = ["D2", "E1", "D2+E1", "D2+E1+K"]
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def fit_contracted(part, all_anchors, act, before, hmax):
    """K: one logistic fit on player-seasons under contract (as known at each row's own valuation
    date, participation_model._rows), seasons ahead 0..hmax, outcomes finished before the page."""
    import statsmodels.api as sm
    parts = []
    for h in range(hmax + 1):
        a = all_anchors[all_anchors["t0"] + h < before]
        if not len(a):
            continue
        d = part._rows(a, h)
        d = d[d["under_contract"] > 0].copy()
        if not len(d):
            continue
        gp = act.reindex(pd.MultiIndex.from_arrays([d["career_key"], d["season"]])).fillna(0.0).to_numpy()
        d["y"] = (gp >= C.PARTICIPATION_GP).astype(float)
        d["h"] = float(h)
        parts.append(d)
    if not parts:
        return None, 0
    d = pd.concat(parts, ignore_index=True).replace([np.inf, -np.inf], np.nan).dropna(subset=K_FEATURES + ["y"])
    n1 = int(d["y"].sum()); n0 = len(d) - n1
    if len(d) < MIN_ROWS or min(n0, n1) < MIN_SIDE:
        return None, len(d)
    X = sm.add_constant(d[K_FEATURES].to_numpy(float), has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = sm.Logit(d["y"].to_numpy(float), X).fit_regularized(alpha=1e-4, disp=0, maxiter=200)
    return np.asarray(r.params, float), len(d)


def main():
    C.banner("games_playing_followup.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"),
                                                   share=("gp_share", "first"))
    f_age = list(SF.GP_FEATURES) + ["age_c2"]

    frames = []
    log("\ntoday's chance of playing (the build): seasons ahead whose fit carries the contract column")
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        carried = [h for h in sorted(mod.part_.coef_) if mod.part_.coef_.get(h) is not None
                   and "under_contract" in mod.part_.used_.get(h, [])]
        log(f"    {t0}: {carried}")
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        pairs = mod._training_pairs(iset.seasons, t0, C.CANDIDATE_HORIZONS)
        share_d2 = {h: predict_share(fit_share(pairs[pairs["h"] == h], f_age, False), pa, f_age) for h in HS}

        n = mod.N_SEASONS
        e1 = PM.ParticipationModel(contracts, exclude=(), contract_state=mod.CONTRACT_STATE).fit(
            iset.seasons, t0, anchors_fn=lambda p: SF._anchors(p, n), horizons=mod.fitted_horizons_)
        keep = mod.part_; mod.part_ = e1
        p_e1 = {h: mod._p_play(pa, subs, h) for h in HS}
        mod.part_ = keep

        played_all = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
        act = iset.seasons.set_index(["career_key", "syr"])["GP"]
        beta, nk = fit_contracted(e1, SF._anchors(played_all, n), act, t0, max(mod.fitted_horizons_))
        log(f"    {t0}: K {'fitted on' if beta is not None else 'NOT fitted,'} {nk:,} contracted player-seasons")
        p_k, uc = {}, {}
        for h in HS:
            d = e1._rows(pa.reset_index(), h)
            uc[h] = d["under_contract"].to_numpy(float)
            p = p_e1[h].copy()
            if beta is not None:
                d["h"] = float(h)
                M = d[K_FEATURES].to_numpy(float); ok = np.isfinite(M).all(axis=1) & (uc[h] > 0)
                z = np.clip(beta[0] + M[ok] @ beta[1:], -30, 30)
                p[ok] = np.clip(1.0 / (1.0 + np.exp(-z)), 0.005, 0.995)
            p_k[h] = p

        rows = []
        for h in HS:
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(pa.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            rows.append(pd.DataFrame({
                "career_key": pa.index, "t0": t0, "h": h, "rate": ph["rate_82"].to_numpy(),
                "s|base": ph["gp_share"].to_numpy(), "p|base": ph["p_play"].to_numpy(),
                "s|D2": share_d2[h], "p|E1": p_e1[h], "p|K": p_k[h],
                "gp": gp, "y82": rr["y"].to_numpy(), "share_act": np.where(gp > 0, rr["share"].to_numpy(), np.nan),
                "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                "played": (gp >= C.PARTICIPATION_GP).astype(float), "level": pa["tw_WAR"].to_numpy(float),
                "uc": uc[h], "season": t0 + h}))
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players")

    D = pd.concat(frames, ignore_index=True)
    g = D["career_key"].to_numpy(); hh = D["h"].to_numpy(); y = D["played"].to_numpy()
    app = np.isfinite(D["share_act"]).to_numpy()
    cols = {"base": ("s|base", "p|base"), "D2": ("s|D2", "p|base"), "E1": ("s|base", "p|E1"),
            "D2+E1": ("s|D2", "p|E1"), "D2+E1+K": ("s|D2", "p|K")}
    L = {}
    for arm, (sc, pc) in cols.items():
        ew = (D[pc] * D["rate"] * D[sc] - D["war_act"]).to_numpy()
        L[arm] = {"share": np.where(app, (D[sc] - D["share_act"]).to_numpy() ** 2, 0.0),
                  "logloss": logloss(D[pc].to_numpy(), y), "brier": (D[pc].to_numpy() - y) ** 2,
                  "war_sq": ew ** 2, "war_abs": np.abs(ew)}

    def score(arm, m=None):
        m = np.ones(len(D), bool) if m is None else m
        Lx = L[arm]
        return (float(np.sqrt(Lx["share"][m & app].mean())), float(Lx["logloss"][m].mean()),
                float(Lx["brier"][m].mean()), float(np.sqrt(Lx["war_sq"][m].mean())), float(Lx["war_abs"][m].mean()))

    log(f"\nreproduction of games_and_playing_de.py v1.0 (share / log loss / Brier / season WAR), {len(D):,} rows:")
    for arm, rec in RECORDED.items():
        got = tuple(round(x, 4) for x in score(arm)[:4])
        ok = all(abs(a_ - b_) < 1e-9 for a_, b_ in zip(got, rec)) and len(D) == 40510
        log(f"  {arm:5s} {' / '.join(f'{x:.4f}' for x in got)}   recorded {' / '.join(f'{x:.4f}' for x in rec)}   "
            f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"{arm} does not reproduce v1.0; results not read")

    rng = np.random.default_rng(20261005)
    late = D["t0"].to_numpy() >= 2019
    for label, m in (("ALL PAGES", None), ("PAGES 2019-2021 (where K exists)", late)):
        log(f"\n{label}: 'lower in' = resamples (of 2,000 careers) in which the version's summed loss is below the build's")
        log(f"  {'version':10s}{'share':>8s}{'logloss':>9s}{'Brier':>8s}{'WAR RMSE':>10s}{'WAR MAE':>9s}"
            f"   lower in: share / logloss / Brier / WAR")
        mm = np.ones(len(D), bool) if m is None else m
        for arm in ["base"] + ARMS:
            s = score(arm, mm)
            tail = "" if arm == "base" else "   " + " / ".join(
                f"{boot_lower(L[arm][k][mm], L['base'][k][mm], g[mm], rng):5d}" for k in ("share", "logloss", "brier", "war_sq"))
            log(f"  {arm:10s}{s[0]:8.4f}{s[1]:9.4f}{s[2]:8.4f}{s[3]:10.4f}{s[4]:9.4f}{tail}")
        log("  D2+E1+K against D2+E1: " + " / ".join(
            f"{boot_lower(L['D2+E1+K'][k][mm], L['D2+E1'][k][mm], g[mm], rng):5d}" for k in ("logloss", "brier", "war_sq"))
            + "  (log loss / Brier / WAR)")

    log("\nBY SEASON AHEAD: season-WAR RMSE")
    log(f"  {'version':10s}" + "".join(f"{'+' + str(h):>8s}" for h in HS))
    for arm in ["base"] + ARMS:
        log(f"  {arm:10s}" + "".join(f"{score(arm, hh == h)[3]:8.4f}" for h in HS))

    m_uc = (D["uc"].to_numpy() > 0) & (D["season"].to_numpy() >= 2018)
    lv = D["level"].to_numpy()
    bands = (("below 0", lv < 0), ("0-1", (lv >= 0) & (lv < 1)), ("1-2", (lv >= 1) & (lv < 2)), ("2+", lv >= 2),
             ("all", np.ones(len(D), bool)))
    for label, extra in (("all pages", np.ones(len(D), bool)), ("pages 2019-2021", late)):
        log(f"\nE0 CALIBRATION, players under contract for the season, seasons 2018 on, {label}: "
            "forecast chance (build / D2+E1 / D2+E1+K) against share who played, rows")
        log(f"  {'trailing WAR total':20s}" + "".join(f"{'+' + str(h):>30s}" for h in HS))
        for name, mk in bands:
            cells = []
            for h in HS:
                m = m_uc & extra & mk & (hh == h)
                cells.append(f"{D['p|base'][m].mean():.3f}/{D['p|E1'][m].mean():.3f}/{D['p|K'][m].mean():.3f} "
                             f"{y[m].mean():.3f} {int(m.sum()):4d}" if m.any() else "-")
            log(f"  {name:20s}" + "".join(f"{c:>30s}" for c in cells))
        mm = m_uc & extra
        log("  scores on these rows: " + "; ".join(
            f"{arm} logloss {score(arm, mm)[1]:.4f}, Brier {score(arm, mm)[2]:.4f}" for arm in ("base", "D2+E1", "D2+E1+K")))

    C.record_inspection("games_playing_followup.py", "pages", PAGES,
                        "D2+E1 together; contracted-seasons chance of playing (Thomas 2026-10-05)")
    p = C.out_path("games_playing_followup_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
