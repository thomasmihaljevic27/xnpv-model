"""abc_build_check.py -- does skater_forecast v2.1 do exactly what investigations A and C decided?

WHY (Thomas, 2026-10-05). Adopted from step 2: A1 (one yardstick per position), C2 (a player absent
one season who appears again later is not filled in as departed), C6 (a departed season counts at his
own last season's games, not 82); C5 dropped. They were decided on test code
(25_TESTS/aging_abc_followup.py, the "A1+C2+C6" version) and built into 20_CODE/aging_curve.py and
20_CODE/skater_forecast.py v2.1. This check holds the production code to that version, row by row and
to its recorded figures. CHECK ONLY: it changes nothing.

WHAT IT ASSERTS (development pages 2015-2021; seasons ahead 0-5):
  1. THE CURVE. skater_forecast.imputed_aging_model(page) equals the tested curve
     (aging_investigations_abc.curve_variant(returners_filled=False, gp_rule="own")) on every page:
     levels, comparables' levels and changes, league changes, and the per-position yardsticks equal
     the tested ones (aging_investigations_abc.yardsticks(by_position=True)).
  2. THE RATE PER 82. Production's rate equals the rate production's own XNPV1._rate gives on the
     tested curve with the tested per-position weights, for every player, page and season ahead.
  3. THE RECORDED FIGURES (laptop; aging_abc_followup.py v1.0, "A1+C2+C6", 2026-10-05): start 1.1506,
     whole one to five out 1.3587, season-WAR RMSE 0.8088 and MAE 0.4673, on 40,510 player-seasons.
  Tolerance for 1-2: 1e-12 (the same arithmetic in the same order).

HOW TO RUN (repo root, laptop; needs the contract export; about ten minutes):
    python 25_TESTS/abc_build_check.py
Writes 30_OUTPUT/abc_build_check_log.txt. Every assertion that fails stops the run.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF
from aging_investigations_abc import curve_variant, weights_by_position, wrmse, yardsticks

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
TOL = 1e-12
RECORDED = {"start": 1.1506, "whole": 1.3587, "war_rmse": 0.8088, "war_mae": 0.4673, "rows": 40510}
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
    C.banner("abc_build_check.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"))

    frames, g_curve, g_rate = [], 0.0, 0.0
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        prod = mod.curve_
        # 1. the curve
        t = curve_variant(path, t0, returners_filled=False, gp_rule="own")
        hpos = yardsticks(t, by_position=True)
        assert list(prod.names) == list(t.names) and prod.h == t.h, f"{t0}: pool or pooled yardstick differs"
        assert prod.h_by_pos.keys() == hpos.keys()
        g_curve = max(g_curve, same(f"{t0} yardsticks", [prod.h_by_pos[k] for k in hpos], list(hpos.values())),
                      same(f"{t0} Lser", prod.Lser, t.Lser), same(f"{t0} Dser", prod.Dser, t.Dser))
        assert prod.gdelta.keys() == t.gdelta.keys() and prod.glevel.keys() == t.glevel.keys()
        g_curve = max(g_curve, same(f"{t0} gdelta", list(prod.gdelta.values()), list(t.gdelta.values())),
                      same(f"{t0} glevel", list(prod.glevel.values()), list(t.glevel.values())))
        # 2. the rate: production as it stands, then production's code on the tested curve
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        t._weights = types.MethodType(weights_by_position(hpos), t)
        mod.curve_ = t; mod._paths = {}
        tested = {h: mod._rate(pa, h) for h in HS}
        mod.curve_ = prod; mod._paths = {}
        rows = []
        for h in HS:
            ph = pr.xs(h, level="h").reindex(pa.index)
            g_rate = max(g_rate, same(f"{t0} rate +{h}", ph["rate_82"], tested[h]))
            if t0 + h > last:
                continue
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            rows.append(pd.DataFrame({"h": h, "rate": ph["rate_82"].to_numpy(), "share": ph["gp_share"].to_numpy(),
                                      "p": ph["p_play"].to_numpy(), "gp": gp, "y82": rr["y"].to_numpy(),
                                      "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0)}))
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players; departures filled in {prod.n_imputed:,}; yardsticks "
            + ", ".join(f"{k} {v:.3f}" for k, v in sorted(prod.h_by_pos.items())) + "; production equals the tested version")
    log(f"1. curve: equal on every page (largest gap {g_curve:.1e})")
    log(f"2. rate per 82: equal on every player, page and season ahead (largest gap {g_rate:.1e})")

    D = pd.concat(frames, ignore_index=True)
    rp = D[(D["gp"] > 0) & np.isfinite(D["y82"])]
    e0 = rp[rp["h"] == 0]; ew = rp[rp["h"] > 0]
    war = D["p"] * D["rate"] * D["share"] - D["war_act"]
    got = {"start": wrmse((e0["rate"] - e0["y82"]).to_numpy(), e0["gp"].to_numpy()),
           "whole": wrmse((ew["rate"] - ew["y82"]).to_numpy(), ew["gp"].to_numpy()),
           "war_rmse": float(np.sqrt((war ** 2).mean())), "war_mae": float(war.abs().mean()), "rows": len(D)}
    log("3. recorded figures (aging_abc_followup.py v1.0, A1+C2+C6):")
    bad = []
    for k, v in got.items():
        ok = (v == RECORDED[k]) if k == "rows" else abs(round(v, 4) - RECORDED[k]) < 1e-9
        log(f"     {k:9s} {v:10.4f}   recorded {RECORDED[k]}   {'PASS' if ok else 'FAIL'}")
        if not ok:
            bad.append(k)
    if bad:
        raise RuntimeError(f"recorded figures not reproduced: {bad}")
    log("\nALL CHECKS PASS: skater_forecast v2.1 is the A1+C2+C6 version Thomas adopted.")
    p = C.out_path("abc_build_check_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"written: {p}")


if __name__ == "__main__":
    main()
