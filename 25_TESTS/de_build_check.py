"""de_build_check.py -- does skater_forecast v2.2 do exactly what investigations D and E decided?

WHY (Thomas, 2026-10-05). Adopted from step 3: D2 (age squared in the games-share line, cap and floor
kept) and E1 (the before-2018 marker back in the chance of playing); E3 and the contracted-seasons
chance of playing dropped. They were decided on test code (25_TESTS/games_and_playing_de.py and
games_playing_followup.py, the "D2+E1" version) and built into 20_CODE/skater_forecast.py v2.2. This
check holds production to that version. CHECK ONLY: it changes nothing.

WHAT IT ASSERTS (development pages 2015-2021; seasons ahead 0-5):
  1. THE GAMES SHARE. Production's gp_share equals the tested D2 line (games_and_playing_de.fit_share /
     predict_share on production's own training pairs) for every player, page and season ahead.
  2. THE CHANCE OF PLAYING. Production's p_play equals a participation_model.ParticipationModel fitted
     with nothing excluded (the tested E1) for every player, page and season ahead.
  3. THE RATE PER 82 is untouched by D and E: start 1.1506, whole one to five out 1.3587.
  4. THE RECORDED FIGURES (laptop; games_playing_followup.py v1.0, "D2+E1", 2026-10-05): games share
     0.2654, log loss 0.4047, Brier 0.1313, season-WAR RMSE 0.8075 and MAE 0.4656, 40,510 rows.
  Tolerance for 1-2: 1e-12.

HOW TO RUN (repo root, laptop; needs the contract export; about ten minutes):
    python 25_TESTS/de_build_check.py
Writes 30_OUTPUT/de_build_check_log.txt. Every assertion that fails stops the run.
"""
import sys
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
from games_and_playing_de import fit_share, logloss, predict_share, wrmse

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
TOL = 1e-12
RECORDED = {"start": 1.1506, "whole": 1.3587, "share": 0.2654, "logloss": 0.4047, "brier": 0.1313,
            "war_rmse": 0.8075, "war_mae": 0.4656, "rows": 40510}
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
    C.banner("de_build_check.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}; games-share inputs {SF.GP_FEATURES}; "
        f"chance of playing excludes {list(SF.XNPV1.PART_EXCLUDE)}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"),
                                                   share=("gp_share", "first"))
    f_age = list(SF.GP_FEATURES[:5]) + ["age_c2"]       # the tested D2 inputs, in the tested order
    assert f_age == list(SF.GP_FEATURES), "production's games-share inputs are not the tested D2 inputs"

    frames, g_share, g_p = [], 0.0, 0.0
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        pairs = mod._training_pairs(iset.seasons, t0, C.CANDIDATE_HORIZONS)
        n = mod.N_SEASONS
        e1 = PM.ParticipationModel(contracts, exclude=(), contract_state="observable").fit(
            iset.seasons, t0, anchors_fn=lambda p: SF._anchors(p, n), horizons=mod.fitted_horizons_)
        keep = mod.part_; mod.part_ = e1
        t_p = {h: mod._p_play(pa, subs, h) for h in HS}
        mod.part_ = keep
        rows = []
        for h in HS:
            ph = pr.xs(h, level="h").reindex(pa.index)
            t_share = predict_share(fit_share(pairs[pairs["h"] == h], f_age, False), pa, f_age)
            g_share = max(g_share, same(f"{t0} games share +{h}", ph["gp_share"], t_share))
            g_p = max(g_p, same(f"{t0} chance of playing +{h}", ph["p_play"], t_p[h]))
            if t0 + h > last:
                continue
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            rows.append(pd.DataFrame({"h": h, "rate": ph["rate_82"].to_numpy(), "share": ph["gp_share"].to_numpy(),
                                      "p": ph["p_play"].to_numpy(), "gp": gp, "y82": rr["y"].to_numpy(),
                                      "share_act": np.where(gp > 0, rr["share"].to_numpy(), np.nan),
                                      "played": (gp >= C.PARTICIPATION_GP).astype(float),
                                      "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0)}))
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players; production equals the tested D2 + E1")
    log(f"1. games share: equal on every player, page and season ahead (largest gap {g_share:.1e})")
    log(f"2. chance of playing: equal on every player, page and season ahead (largest gap {g_p:.1e})")

    D = pd.concat(frames, ignore_index=True)
    rp = D[(D["gp"] > 0) & np.isfinite(D["y82"])]
    e0 = rp[rp["h"] == 0]; ew = rp[rp["h"] > 0]
    app = np.isfinite(D["share_act"])
    war = D["p"] * D["rate"] * D["share"] - D["war_act"]
    got = {"start": wrmse((e0["rate"] - e0["y82"]).to_numpy(), e0["gp"].to_numpy()),
           "whole": wrmse((ew["rate"] - ew["y82"]).to_numpy(), ew["gp"].to_numpy()),
           "share": float(np.sqrt(((D["share"] - D["share_act"])[app] ** 2).mean())),
           "logloss": float(logloss(D["p"].to_numpy(), D["played"].to_numpy()).mean()),
           "brier": float(((D["p"] - D["played"]) ** 2).mean()),
           "war_rmse": float(np.sqrt((war ** 2).mean())), "war_mae": float(war.abs().mean()), "rows": len(D)}
    log("3-4. recorded figures (rate: the build; the rest: games_playing_followup.py v1.0, D2+E1):")
    bad = []
    for k, v in got.items():
        ok = (v == RECORDED[k]) if k == "rows" else abs(round(v, 4) - RECORDED[k]) < 1e-9
        log(f"     {k:9s} {v:10.4f}   recorded {RECORDED[k]}   {'PASS' if ok else 'FAIL'}")
        bad += [] if ok else [k]
    if bad:
        raise RuntimeError(f"recorded figures not reproduced: {bad}")
    log("\nALL CHECKS PASS: skater_forecast v2.2 is the D2 + E1 version Thomas adopted.")
    p = C.out_path("de_build_check_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"written: {p}")


if __name__ == "__main__":
    main()
