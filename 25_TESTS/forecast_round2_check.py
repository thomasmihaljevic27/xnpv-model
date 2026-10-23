"""forecast_round2_check.py -- the built forecast (skater_forecast v2.4, participation_model v2.0) against the audit.

WHY (Thomas, 2026-10-21, on 25_TESTS/forecast_term_audit.py v1.2): the games share without its defenceman term and
floored at 0, the chance of playing without age squared and seasons since debut, age centred at 27.22. The audit scored
the three drops together as version S1 (all 40,510 rows: season WAR 0.8054, games share 0.2652, log loss 0.4000) with
the floor at 0.05 and the centre at 27. No forecast share fell below 0.05, and the centre changes no games share; in the
chance of playing it moves only the intercept, which the fit's small penalty (1e-4) can move very slightly. So the build
must give the audit's S1 back: start 1.1506 and one to five ahead 1.3569 exactly (the rate is not changed), season WAR,
share and log loss to 1e-4. TEST ONLY.

HOW TO RUN (repo root, laptop; needs the contract export; about 15 minutes):  python 25_TESTS/forecast_round2_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import participation_model as PM
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "forecast_round2_check.py v1.0 (2026-10-21)"
AUDIT_S1 = {"start": 1.1506, "whole": 1.3569, "war": 0.8054, "share": 0.2652, "logloss": 0.4000, "rows": 40510}
HS = tuple(range(6))


def main():
    print(SCRIPT_VERSION, f"skater_forecast v{SF.SCRIPT_VERSION}", f"participation_model v{PM.SCRIPT_VERSION}")
    assert "is_D" not in SF.GP_FEATURES and "age_sq" not in PM.BASE_FEATURES and "exp_seasons" not in PM.BASE_FEATURES
    assert C.AGE_CENTRE == 27.22
    bd, _ = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"),
                                                   share=("gp_share", "first"))
    frames = []
    for t0 in C.DEV_PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        for h in HS:
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(pa.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            frames.append(pd.DataFrame({"career_key": pa.index, "h": h, "gp": gp, "y82": rr["y"].to_numpy(),
                                        "share_act": np.where(gp > 0, rr["share"].to_numpy(), np.nan),
                                        "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                                        "played": (gp >= C.PARTICIPATION_GP).astype(float),
                                        "r": ph["rate_82"].to_numpy(), "s": ph["gp_share"].to_numpy(),
                                        "p": ph["p_play"].to_numpy()}))
        print(f"  page {t0}: {len(pa):,} players; games-share terms {mod.gp_coef_[0][0]}; "
              f"chance-of-playing terms at +0 {mod.part_.used_.get(0)}")
    D = pd.concat(frames, ignore_index=True)
    ok = ((D["gp"] > 0) & np.isfinite(D["y82"])).to_numpy()
    w = np.where(ok, D["gp"], 0.0)
    e = np.where(ok, D["r"] - D["y82"], 0.0)
    h0, h1 = (D["h"] == 0).to_numpy(), (D["h"] > 0).to_numpy()
    p = np.clip(D["p"].to_numpy(), 1e-9, 1 - 1e-9)
    y = D["played"].to_numpy()
    app = np.isfinite(D["share_act"]).to_numpy()
    got = {"start": float(np.sqrt((w * e ** 2)[h0].sum() / w[h0].sum())),
           "whole": float(np.sqrt((w * e ** 2)[h1].sum() / w[h1].sum())),
           "war": float(np.sqrt(np.mean((D["p"] * D["r"] * D["s"] - D["war_act"]).to_numpy() ** 2))),
           "share": float(np.sqrt(np.mean((D["s"] - D["share_act"]).to_numpy()[app] ** 2))),
           "logloss": float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p)))), "rows": len(D)}
    bad = []
    for k, v in AUDIT_S1.items():
        tol = 0 if k == "rows" else (5e-5 if k in ("start", "whole") else 1e-4)
        okk = (got[k] == v) if k == "rows" else abs(got[k] - v) <= tol + 5e-5
        bad += [] if okk else [k]
        print(f"  {k:8s} {got[k]:.4f}   audit S1 {v}   {'PASS' if okk else 'FAIL'}")
    print("ALL PASS: the build is the audit's S1" if not bad else f"FAIL: {bad}")
    C.out_path("forecast_round2_check_log.txt").write_text(
        f"{SCRIPT_VERSION}\n" + "\n".join(f"{k} {got[k]}" for k in got) + f"\nfailed: {bad}\n", encoding="utf-8")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
