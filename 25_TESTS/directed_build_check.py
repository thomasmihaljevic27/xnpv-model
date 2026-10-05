"""directed_build_check.py -- does the built forecast (skater_forecast v2.0) do exactly what was decided?

WHY (2026-10-05, plan of record step 1). Thomas's directives 1-3 and the 2026-10-05 build rules were
decided on test code (25_TESTS/level_games_weighting_test.py, thin_history_check.py,
war_input_uniformity_test.py). The build moved them into 20_CODE/aging_curve.py and
20_CODE/skater_forecast.py. This check holds the production code to the tested design, row by row,
and to every figure the decisions were made on. Every later test runs on the production code.
CHECK ONLY: it changes nothing.

WHAT IT ASSERTS (development pages 2015-2021; seasons ahead 0-5):
  1. THE CURVE. skater_forecast.imputed_aging_model(page) equals
     aging_level_weights_test.build_curve(page, 50/30/20, games-weighted) on every page: each player's
     level by age, the comparables' levels and changes, the league levels and changes, the bandwidth.
  2. THE RATE PER 82. XNPV1().fit(...).predict(...)'s rate_82 equals the tested directed rate (65%
     own + 35% comparables, the step to the valuation season, the walk) for every player, page and
     season ahead, and the same players are forecast -- WITH ONE FIX. The tested code
     (aging_level_weights_test.curve_paths) asked the curve to walk past its oldest age; the curve
     then raised IndexError and the tested code fell back to the league path for that whole player,
     although its stated rule is "past the curve: held". Production stops the walk at the oldest age
     and holds (skater_forecast v2.0, XNPV1._path). So production is compared with the tested code
     with the walk capped the same way, and the check reports how many rows the fix moves.
  3. THE GAMES SHARE AND THE CHANCE OF PLAYING equal war_input_uniformity_test.py's chosen arm (the
     plain 50/30/20 trailing total, no level-above-1.0 term), rebuilt here from that test's builders.
  4. THE RECORDED FIGURES (laptop), from the tested code AS RECORDED (no fix), to show this run's data
     is the data the decisions were made on: start 1.1506 and whole 1-5 out 1.3598 (rate per 82,
     games-weighted); games share RMSE 0.2657; chance of playing log loss 0.4044 and Brier 0.1313;
     season-WAR RMSE 0.8093 and MAE 0.4671, on 40,510 player-seasons. Production's own figures
     (with the fix) are printed beside them.
  Tolerance for 1-3: 1e-9 (the two routes add the same numbers in different orders, so they agree to
  rounding, not to the bit). Figures in 4 are compared at their recorded four decimals.

HOW TO RUN (repo root, laptop; needs the contract export; about ten minutes):
    python 25_TESTS/directed_build_check.py
Writes 30_OUTPUT/directed_build_check_log.txt. Every assertion that fails stops the run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF
from participation_model import ParticipationModel
from aging_level_weights_test import anchors as rate_rows, build_curve, curve_paths, wrmse
from war_input_uniformity_test import logloss, trail, with_level

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
W3 = (0.5, 0.3, 0.2)
TOL = 1e-9
RECORDED = {"start": 1.1506, "whole": 1.3598, "share": 0.2657, "logloss": 0.4044, "brier": 0.1313,
            "war_rmse": 0.8093, "war_mae": 0.4671, "rows": 40510}
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def same(name, x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    assert x.shape == y.shape, (name, x.shape, y.shape)
    assert (np.isnan(x) == np.isnan(y)).all(), f"{name}: missing in one route only"
    gap = float(np.nanmax(np.abs(x - y))) if np.isfinite(x).any() else 0.0
    assert gap < TOL, f"{name}: largest gap {gap:.3e}"
    return gap


def main():
    C.banner("directed_build_check.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    last = int(table["syr"].max())

    # ---- 1. the curve ------------------------------------------------------------------------
    worst = 0.0
    for t0 in PAGES:
        p = SF.imputed_aging_model(path, t0); t = build_curve(path, t0, W3, True)
        assert list(p.names) == list(t.names) and p.h == t.h, f"curve {t0}: pool or bandwidth differs"
        assert set(p.players) == set(t.players)
        for k in p.players:
            assert p.players[k]["sm"].keys() == t.players[k]["sm"].keys()
            worst = max(worst, same(f"curve {t0} level {k}", list(p.players[k]["sm"].values()),
                                    list(t.players[k]["sm"].values())))
        worst = max(worst, same(f"curve {t0} Lser", p.Lser, t.Lser), same(f"curve {t0} Dser", p.Dser, t.Dser))
        assert p.gdelta.keys() == t.gdelta.keys() and p.glevel.keys() == t.glevel.keys()
        worst = max(worst, same(f"curve {t0} gdelta", list(p.gdelta.values()), list(t.gdelta.values())),
                    same(f"curve {t0} glevel", list(p.glevel.values()), list(t.glevel.values())))
    log(f"1. curve: production equals the tested curve on {len(PAGES)} pages (largest gap {worst:.1e})")

    # ---- tested rate per 82: as recorded, and with the walk capped at the curve's oldest age ----
    dr = rate_rows(table)
    q = table[table["GP"] >= C.MIN_GP]
    ia = np.arange(len(dr)); g_ = dr["last_lag"].to_numpy(int)
    tested = {}
    for capped in (False, True):
        cn = np.full(len(dr), np.nan); paths = np.zeros((len(dr), 3 + 5 + 1))
        for t0 in PAGES:
            m = build_curve(path, t0, W3, True)
            if capped:                       # the production rule: stop at the oldest age, hold
                orig = m.project
                m.project = (lambda ck, current_age, horizon, _o=orig, _m=m:
                             _o(ck, current_age=current_age,
                                horizon=max(0, min(horizon, _m.AMIN + _m.nages - current_age))))
            s = q[q["syr"] < t0]
            lp = {pp: float(np.sum(g["WAR_82"] * g["GP"]) / np.sum(g["GP"])) for pp, g in
                  s.assign(pp=np.where(s["pos"] == "D", "D", "F")).groupby("pp")}
            ix, c, pth = curve_paths(dr, m, t0, lp)
            cn[ix], paths[ix] = c, pth
        st = 0.65 * dr["own"].to_numpy() + (1 - 0.65) * cn + paths[ia, g_]
        tested[capped] = {(k, t, h): r for h in HS for k, t, r in
                          zip(dr["career_key"], dr["t0"], st + (paths[ia, g_ + h] - paths[ia, g_]))}
    tested_rate = tested[True]
    moved = np.array([abs(tested[True][k] - tested[False][k]) > TOL for k in tested[True]])
    log(f"   the walk fix moves {int(moved.sum()):,} of {len(moved):,} player-page-season rates "
        f"({len({k[:2] for k, mv in zip(tested[True], moved) if mv}):,} player-pages)")

    # ---- production, and the tested games share / chance of playing, per page ------------------
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"),
                                                   war=("WAR", "sum"), share=("gp_share", "first"))
    out = []
    g_rate = g_share = g_p = 0.0
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        seas = iset.seasons
        allA = trail(seas[seas["GP"] >= C.MIN_GP])
        page = allA[allA["t0"] == t0].drop_duplicates("career_key").reset_index(drop=True)
        subs = pd.DataFrame({"career_key": page["career_key"]})
        mod = SF.XNPV1().fit(seas, before=t0)
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])

        # the tested arm, rebuilt from war_input_uniformity_test's builders
        act = seas.set_index(["career_key", "syr"])
        fa, feats = with_level(allA, "total", False)
        pa, _ = with_level(page, "total", False)
        part = ParticipationModel(contracts, exclude=("contract_unknown",), contract_state="observable")
        part.fit(seas, t0, anchors_fn=lambda p: with_level(trail(p), "total", False)[0], horizons=HS)
        rows = []
        for h in HS:
            tr = fa[fa["t0"] + h < t0].copy()
            tr["y"] = act["gp_share"].reindex(pd.MultiIndex.from_arrays([tr["career_key"], tr["t0"] + h])).to_numpy()
            tr = tr.dropna(subset=["y"] + feats)
            coef = SF._ols(tr[feats], tr["y"]) if len(tr) > 50 else None
            t_share = np.clip(SF._apply(coef, pa[feats], pa["tr_gp_share"]), 0.05, 1.0)
            t_p = part.predict(pa, h).reindex(page["career_key"]).fillna(part.base_[h]).to_numpy()
            ph = pr.xs(h, level="h").reindex(page["career_key"])
            t_rate = np.array([tested_rate.get((k, t0, h), np.nan) for k in page["career_key"]])
            g_rate = max(g_rate, same(f"rate {t0} +{h}", ph["rate_82"], t_rate))
            g_share = max(g_share, same(f"games share {t0} +{h}", ph["gp_share"], t_share))
            g_p = max(g_p, same(f"chance of playing {t0} +{h}", ph["p_play"], t_p))
            if t0 + h <= last:
                rr = res.reindex(pd.MultiIndex.from_arrays([page["career_key"], page["t0"] + h]))
                gp = np.nan_to_num(rr["GP"].to_numpy())
                rows.append(pd.DataFrame({
                    "career_key": page["career_key"], "h": h, "rate": ph["rate_82"].to_numpy(),
                    "share": ph["gp_share"].to_numpy(), "p": ph["p_play"].to_numpy(),
                    "played": (gp >= C.PARTICIPATION_GP).astype(float),
                    "share_act": np.where(gp > 0, rr["share"].to_numpy(), np.nan),
                    "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                    "y82": rr["y"].to_numpy(), "gp": gp,
                    "rate_rec": [tested[False].get((k, t0, h), np.nan) for k in page["career_key"]]}))
        out.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(page):,} players; production equals the tested design")
    log(f"2. rate per 82: equal on every player, page and season ahead (largest gap {g_rate:.1e})")
    log(f"3. games share (largest gap {g_share:.1e}) and chance of playing ({g_p:.1e}): equal")

    # ---- 4. the recorded figures --------------------------------------------------------------
    D = pd.concat(out, ignore_index=True)

    def figures(rate_col):
        rp = D[(D["gp"] > 0) & np.isfinite(D["y82"])]
        e0 = rp[rp["h"] == 0]; ew = rp[rp["h"] > 0]
        app = np.isfinite(D["share_act"])
        ewar = D["p"] * D[rate_col] * D["share"] - D["war_act"]
        return {"start": wrmse((e0[rate_col] - e0["y82"]).to_numpy(), e0["gp"].to_numpy()),
                "whole": wrmse((ew[rate_col] - ew["y82"]).to_numpy(), ew["gp"].to_numpy()),
                "share": float(np.sqrt(((D["share"] - D["share_act"])[app] ** 2).mean())),
                "logloss": float(logloss(D["p"].to_numpy(), D["played"].to_numpy()).mean()),
                "brier": float(((D["p"] - D["played"]) ** 2).mean()),
                "war_rmse": float(np.sqrt((ewar ** 2).mean())), "war_mae": float(ewar.abs().mean()),
                "rows": len(D)}
    rec, prod = figures("rate_rec"), figures("rate")
    log("4. recorded figures: the tested design as recorded, on this run's data; production beside it")
    log(f"     {'':9s} {'as recorded':>12s} {'recorded':>9s}         {'production (walk fixed)':>24s}")
    bad = []
    for k, v in rec.items():
        ok = (v == RECORDED[k]) if k == "rows" else abs(round(v, 4) - RECORDED[k]) < 1e-9
        log(f"     {k:9s} {v:12.4f} {RECORDED[k]:>9}   {'PASS' if ok else 'FAIL'}   {prod[k]:24.4f}")
        if not ok:
            bad.append(k)
    if bad:
        raise RuntimeError(f"recorded figures not reproduced: {bad}")
    log("\nALL CHECKS PASS: skater_forecast v2.0 is the design the decisions were made on, with the walk fix.")
    p = C.out_path("directed_build_check_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"written: {p}")


if __name__ == "__main__":
    main()
