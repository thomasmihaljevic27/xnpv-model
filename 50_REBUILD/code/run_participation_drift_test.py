"""run_participation_drift_test.py -- do good players stay in the league longer than the model learned?

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

WHAT PROMPTED IT (read-only checks, 2026-09-30, session log)
    Model 3 under-predicts good players' chance of playing three to five seasons
    out on every development page (2+ win players, three seasons out: 0.82
    against 0.88 on the 2015 page, 0.90 against 0.93 on 2021). The season table
    shows why it might: 2+ win players still playing three seasons on were
    0.945 (aged 25-28) and 0.901 (29-31) when valued 2009-2014, and 0.987 and
    0.976 when valued 2015-2021. A model fitted on the older seasons learns exit
    rates that no longer hold.

THE CANDIDATES, each ONE change to Model 3's chance of playing (star_candidates v1.5)
    T  a linear trend in the target season (season - 2015), fitted on outcomes
       before the page and extrapolated from there
    W  the same model fitted only on anchors valued in the last nine seasons
       before the page (the window width is declared here, not searched)

THE RULE, DECLARED BEFORE THE RUN (rows the current model answers)
    A candidate IMPROVES Model 3 only if its season-WAR squared error is lower
    in at least 1,950 of 2,000 player resamples and its Brier score is lower in
    at least 1,950. (Both change only the chance of playing, which is asserted.)

GUARDS
    * the age table production reads is logged by its real path;
    * one row set and target; rate and games share identical to Model 3;
    * the base reproduces the saved Model 3 forecasts where that file exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table
import production_adapter as PA
import star_candidates as SC
from run_skater_contract_test import Boot, _count
import run_aging_choices_test as RAC

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)
KEYS = ["career_key", "page", "h"]
AGE_BANDS = ([0, 24, 28, 31, 60], ["<=24", "25-28", "29-31", "32+"])
WINDOW = 9
ARMS = {"model3": SC.candidate(gp=True), "T": SC.candidate(gp=True, part_trend=True),
        "W": SC.candidate(gp=True, part_window=WINDOW), "current": PA.ProductionChain}
LABEL = {"model3": "Model 3 (base)", "T": "T: season trend in participation",
         "W": f"W: participation on last {WINDOW} seasons", "current": "Model 1 (current)"}


def main() -> None:
    C.banner("run_participation_drift_test.py", SCRIPT_VERSION)
    path, how = RAC._birthdates()
    C.log(f"  birthdates: {how}")
    SFP = PA._production()[0]
    C.log(f"  production age table read: {Path(SFP.F_WAR_AGE).resolve()}")
    table = build_table(birthdate_csv=path, verbose=False)
    har = H.Harness(table)
    al = {}
    for k, cls in ARMS.items():
        al[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS).set_index(KEYS).sort_index()
        C.log(f"  ran {k} ({cls.name}): {len(al[k])} forecasts")
    ref = al["model3"]
    for k, d in al.items():
        assert d.index.equals(ref.index), f"{k} answered different rows"
        assert np.array_equal(d["act_war"].to_numpy(), ref["act_war"].to_numpy()), k
    for k in ("T", "W"):
        for c in ("rate_82", "gp_share"):
            assert np.array_equal(al[k][c].to_numpy(), ref[c].to_numpy()), f"{k} moved {c}"
        assert not np.array_equal(al[k]["p_play"].to_numpy(), ref["p_play"].to_numpy()), f"{k} moved nothing"
    saved = C.out_path("star_late_forecasts.csv")
    if Path(saved).exists():
        s = pd.read_csv(saved, low_memory=False)
        s = s[s["arm"] == "model3"].set_index(KEYS).sort_index()
        for c in ("rate_82", "gp_share", "p_play"):
            gap = float(np.nanmax(np.abs(ref.reindex(s.index)[c].to_numpy() - s[c].to_numpy())))
            assert gap < 1e-12, f"base does not reproduce Model 3 on {c}"
        C.log(f"  guard: the base reproduces the saved Model 3 forecasts on {len(s)} rows")
    C.log("  guards: one row set and target; T and W move only the chance of playing")
    C.log("")
    keep = al["current"]["outside_production"].eq(0).to_numpy()
    base = ref.reset_index()[keep]
    boot = Boot(base["career_key"])
    se = lambda k: (al[k].reset_index()[keep]["pred_war"] - base["act_war"]) ** 2
    br = lambda k: (al[k].reset_index()[keep]["p_play"] - base["played"].astype(float)) ** 2
    star = (base["tier"] == "3+").to_numpy()
    s15 = star & (base["h"] >= 1).to_numpy()
    bs = Boot(base.loc[s15, "career_key"])
    C.log(f"  rows the current model answers: {int(keep.sum())} forecasts")
    C.log(f"    {'model':<36}{'RMSE':>8}{'lower':>11}{'Brier':>8}{'lower':>11}{'3+ bias 1-5 [95%]':>28}")
    for k in ARMS:
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        m, lo, hi = bs.mean_ci(e[s15])
        C.log(f"    {LABEL[k]:<36}{np.sqrt(se(k).mean()):>8.4f}"
              f"{('--' if k == 'model3' else _count(boot.lower_share(se('model3'), se(k)))):>11}"
              f"{br(k).mean():>8.4f}{('--' if k == 'model3' else _count(boot.lower_share(br('model3'), br(k)))):>11}"
              f"      {m:+.3f} [{lo:+.3f}, {hi:+.3f}]")
    C.log("    ('lower' = resamples, of 2,000, with lower error than Model 3)")
    C.log("    chance of playing three to five seasons out, predicted/observed, by tier and age:")
    for tier in ("3+", "2 to 3", "1 to 2", "0 to 1", "below 0"):
        C.log(f"      tier {tier}:")
        for k in ("model3", "T", "W"):
            d = al[k].reset_index()[keep]
            d = d[(d["tier"] == tier) & (d["h"] >= 3)].copy()
            d["band"] = pd.cut(d["age"], AGE_BANDS[0], labels=AGE_BANDS[1])
            C.log(f"        {LABEL[k]:<36} " + " | ".join(
                f"{b} {d.loc[d['band'] == b, 'p_play'].mean():.2f}/{d.loc[d['band'] == b, 'played'].mean():.2f}"
                for b in AGE_BANDS[1]))
    C.log("    chance of playing, all tiers, predicted minus observed by seasons ahead:")
    for k in ("model3", "T", "W"):
        d = al[k].reset_index()[keep]
        C.log(f"      {LABEL[k]:<36}" + "".join(
            f"{(d.loc[d.h == h, 'p_play'] - d.loc[d.h == h, 'played'].astype(float)).mean():>+8.3f}"
            for h in HORIZONS))
    C.log("    THE DECLARED RULE:")
    for k in ("T", "W"):
        ok = (boot.lower_share(se("model3"), se(k)) >= 0.975) and (boot.lower_share(br("model3"), br(k)) >= 0.975)
        C.log(f"      {LABEL[k]:<36} {'IMPROVES Model 3' if ok else 'does not improve'}")
    pd.concat([d.reset_index().assign(arm=k) for k, d in al.items()], ignore_index=True).to_csv(
        C.out_path("participation_drift_forecasts.csv"), index=False)
    C.write_log("participation_drift_run_log.txt")


if __name__ == "__main__":
    main()
