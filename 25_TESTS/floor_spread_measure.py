"""floor_spread_measure.py -- re-measure the league-minimum floor's spread on the directed forecast.

WHY (plan of record step 6, 2026-10-05). skater_forecast.WAR_IF_PLAYS_MAE is xNPV 1's own mean absolute
miss of the WAR if he plays, by season ahead; contract_npv turns it into the spread behind the
league-minimum floor (MAE x 1.2533; skater_forward_projection.expected_floored_value). It was measured
on the v1.x forecast (2026-10-02) and is stale since v2.0. This re-measures it, the same way, on
skater_forecast v2.2. MEASUREMENT ONLY: it prints the dict to lock; nothing is changed by running it.

THE DEFINITION (skater_forecast.py's docstring, "THE FLOOR SPREAD"): every row the forecast makes on the
development pages 2015-2021, seasons ahead 0-5 (40,510 forecasts); the miss is |WAR if he plays (rate per
82 x games share) - his actual season WAR| on the seasons he played (one game or more); the mean by
season ahead. Guard: the rows and the rate must be the build's (start 1.1506, whole 1.3587, 40,510 rows,
the de_build_check.py figures), or nothing is read.

HOW TO RUN (repo root, laptop; needs the contract export; about ten minutes):
    python 25_TESTS/floor_spread_measure.py
Writes 30_OUTPUT/floor_spread_measure_log.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
GUARD = {"start": 1.1506, "whole": 1.3587, "rows": 40510}
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def wrmse(e, w):
    return float(np.sqrt(np.sum(w * e ** 2) / np.sum(w)))


def main():
    C.banner("floor_spread_measure.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}; the dict in force: {SF.WAR_IF_PLAYS_MAE}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    SF.check_age_coverage(SF.war_age_path())
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"))
    frames = []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        for h in HS:
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(a.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([a.index, np.full(len(a), t0 + h)]))
            frames.append(pd.DataFrame({"h": h, "rate": ph["rate_82"].to_numpy(),
                                        "wip": (ph["rate_82"] * ph["gp_share"]).to_numpy(),
                                        "gp": np.nan_to_num(rr["GP"].to_numpy()), "y82": rr["y"].to_numpy(),
                                        "war": rr["war"].to_numpy()}))
        log(f"  page {t0}: {len(a):,} players")
    D = pd.concat(frames, ignore_index=True)
    rp = D[(D["gp"] > 0) & np.isfinite(D["y82"])]
    got = {"start": round(wrmse((rp[rp["h"] == 0]["rate"] - rp[rp["h"] == 0]["y82"]).to_numpy(), rp[rp["h"] == 0]["gp"].to_numpy()), 4),
           "whole": round(wrmse((rp[rp["h"] > 0]["rate"] - rp[rp["h"] > 0]["y82"]).to_numpy(), rp[rp["h"] > 0]["gp"].to_numpy()), 4),
           "rows": len(D)}
    log(f"\nguard: start {got['start']}, whole {got['whole']}, rows {got['rows']:,} "
        f"(the build: {GUARD['start']}, {GUARD['whole']}, {GUARD['rows']:,})")
    if any(abs(got[k] - GUARD[k]) > 1e-9 for k in GUARD):
        raise RuntimeError("not the build's rows and rate; nothing read")
    log("  PASS")
    played = D[(D["gp"] >= C.PARTICIPATION_GP) & np.isfinite(D["war"]) & np.isfinite(D["wip"])]
    mae = {h: float((played[played["h"] == h]["wip"] - played[played["h"] == h]["war"]).abs().mean()) for h in HS}
    log("\nWAR if he plays, mean absolute miss on seasons played, by season ahead (old -> new):")
    for h in HS:
        log(f"  +{h}: {SF.WAR_IF_PLAYS_MAE[h]:.4f} -> {mae[h]:.4f}   ({int((played['h'] == h).sum()):,} seasons played)")
    log("\nto lock, in skater_forecast.py:")
    log("    WAR_IF_PLAYS_MAE = {" + ", ".join(f"{h}: {mae[h]:.4f}" for h in HS) + "}")
    p = C.out_path("floor_spread_measure_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
