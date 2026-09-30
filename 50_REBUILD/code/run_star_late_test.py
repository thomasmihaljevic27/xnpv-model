"""run_star_late_test.py -- the late star miss in Model 3: two quality-by-age terms.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

THE BASE is Model 3: the current model with every listed fix, comparable-player
aging, and the games-share forecast reading the player's level
(star_candidates.candidate(gp=True); Star_Bias_Test.md, change G).

WHAT THE SPLIT BY AGE SHOWED (Model 3's forecasts, rows the current model
answers, three to five seasons out; read before this runner was written)
    chance of playing  too low for good players from about 29: 3+ win players
                       aged 29-31 were given 0.84 and played 0.96; 2-3 win
                       players 0.74 against 0.89 (29-31) and 0.38 against 0.49
                       (32+); 1-2 win players aged 32+ were right (0.28, 0.27).
    rate               the largest star miss is YOUNG stars: aged 24 or under,
                       predicted 3.28 per 82 against 4.36 in seasons played, and
                       already 0.47 too low in the valuation season.

THE CANDIDATES, each ONE added term (star_candidates v1.3)
    A  participation reads level x age, so age can cost a good player less
    S  the fitted starting rate reads level x age, so the pull toward the
       league can differ for young and old stars
    and A+S together.

THE RULE, DECLARED BEFORE THE RUN (the rows the current model answers)
    * A candidate IMPROVES Model 3 only if its season-WAR squared error is lower
      in at least 1,950 of 2,000 player resamples, and neither its rate error
      (per 82, seasons 1-5, seasons played) nor its Brier score is higher in
      1,950 or more.
    * The 3+ tier's mean season-WAR bias over seasons 1-5 is reported with its
      95% player-resampled interval, beside the point estimate; with 88 players
      the interval is wide, so it is reported, not used as the verdict.
    * Bias by tier and age band, three to five seasons out, is reported for
      every arm so a fix paid for elsewhere is visible.

GUARDS
    * the age table production reads is logged by its real path;
    * one row set and target for every arm;
    * the base reproduces the saved Model 3 forecasts (star_bias_forecasts.csv,
      arm "G") exactly, where that file exists;
    * A moves only the chance of playing; S moves only the rate.
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
TIERS = ("below 0", "0 to 1", "1 to 2", "2 to 3", "3+")
AGE_BANDS = ([0, 24, 28, 31, 60], ["<=24", "25-28", "29-31", "32+"])
ARMS = {"model3": SC.candidate(gp=True), "A": SC.candidate(gp=True, part_age=True),
        "S": SC.candidate(gp=True, start_age=True),
        "A+S": SC.candidate(gp=True, part_age=True, start_age=True),
        "current": PA.ProductionChain}
LABEL = {"model3": "Model 3 (base)", "A": "A: participation level x age",
         "S": "S: start level x age", "A+S": "A + S", "current": "Model 1 (current)"}


def guards(al):
    ref = al["model3"]
    for k, d in al.items():
        assert d.index.equals(ref.index), f"{k} answered different rows"
        for c in ("act_war", "played"):
            assert np.array_equal(d[c].to_numpy(), ref[c].to_numpy()), f"{k}: target {c} differs"
    same = lambda k, c: np.array_equal(al[k][c].to_numpy(), ref[c].to_numpy())
    assert same("A", "rate_82") and same("A", "gp_share") and not same("A", "p_play")
    assert same("S", "gp_share") and same("S", "p_play") and not same("S", "rate_82")
    C.log("  guards: one row set and target; A moves only the chance of playing, S only the rate")
    saved = C.out_path("star_bias_forecasts.csv")
    if Path(saved).exists():
        s = pd.read_csv(saved, low_memory=False)
        s = s[s["arm"] == "G"].set_index(KEYS).sort_index()
        mine = ref.reindex(s.index)
        for c in ("rate_82", "gp_share", "p_play"):
            gap = float(np.nanmax(np.abs(mine[c].to_numpy() - s[c].to_numpy())))
            assert gap < 1e-12, f"base does not reproduce Model 3 on {c} ({gap:.2e})"
        C.log(f"  guard: the base reproduces the saved Model 3 forecasts on {len(s)} rows")


def score(al, label, keep):
    base = al["model3"].reset_index()[keep]
    boot = Boot(base["career_key"])
    b_se = (base["pred_war"] - base["act_war"]) ** 2
    b_br = (base["p_play"] - base["played"].astype(float)) ** 2
    pl = ((base["h"] >= 1) & base["played"].astype(bool)).to_numpy()
    boot_pl = Boot(base.loc[pl, "career_key"])
    b_re = (base.loc[pl, "rate_82"] - base.loc[pl, "act_rate_82"]).abs()
    star = (base["tier"] == "3+").to_numpy()
    boot_st = Boot(base.loc[star, "career_key"])
    s15 = star & (base["h"] >= 1).to_numpy()
    boot_s15 = Boot(base.loc[s15, "career_key"])
    C.log(f"  {label}: {int(keep.sum())} forecasts, {base['career_key'].nunique()} players; "
          f"3+ tier {int(star.sum())} forecasts, {base.loc[star, 'career_key'].nunique()} players")
    C.log(f"    {'arm':<30}{'RMSE':>8}{'lower':>11}{'MAE':>8}{'rate err':>10}{'higher':>11}"
          f"{'Brier':>8}{'higher':>11}{'3+ RMSE':>9}{'lower':>11}")
    out = []
    for k in ARMS:
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        se = e ** 2
        br = (d["p_play"] - d["played"].astype(float)) ** 2
        re_ = (d.loc[pl, "rate_82"] - d.loc[pl, "act_rate_82"]).abs()
        rate_ok = k != "current"
        lo = "--" if k == "model3" else _count(boot.lower_share(b_se, se))
        hr = "--" if k in ("model3", "current") else _count(boot_pl.lower_share(re_, b_re))
        hb = "--" if k == "model3" else _count(boot.lower_share(br, b_br))
        st = "--" if k == "model3" else _count(boot_st.lower_share(b_se[star], se[star]))
        C.log(f"    {LABEL[k]:<30}{np.sqrt(se.mean()):>8.4f}{lo:>11}{e.abs().mean():>8.4f}"
              f"{(re_.mean() if rate_ok else float('nan')):>10.4f}{hr:>11}{br.mean():>8.4f}{hb:>11}"
              f"{np.sqrt(se[star].mean()):>9.4f}{st:>11}")
        m, lo95, hi95 = boot_s15.mean_ci(e[s15])
        out.append(dict(sample=label, arm=k, rmse=float(np.sqrt(se.mean())), mae=float(e.abs().mean()),
                        rate_mae=float(re_.mean()) if rate_ok else np.nan, brier=float(br.mean()),
                        star_rmse=float(np.sqrt(se[star].mean())), star_bias_1_5=m,
                        star_bias_lo=lo95, star_bias_hi=hi95))
    C.log("    ('lower' = resamples, of 2,000, with lower error than Model 3; 'higher' = with")
    C.log("    HIGHER rate error / Brier than Model 3, which the rule caps below 1,950)")
    C.log("    3+ tier season-WAR bias by seasons ahead; mean over 1-5 [95%]:")
    C.log("    " + f"{'arm':<30}" + "".join(f"{'h' + str(h):>8}" for h in HORIZONS) + "   mean 1-5 [95%]")
    for row, k in zip(out, ARMS):
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        cells = "".join(f"{e[star & (d['h'] == h).to_numpy()].mean():>+8.2f}" for h in HORIZONS)
        C.log("    " + f"{LABEL[k]:<30}" + cells +
              f"   {row['star_bias_1_5']:+.3f} [{row['star_bias_lo']:+.3f}, {row['star_bias_hi']:+.3f}]")
    C.log("    three to five seasons out, by tier and age at valuation: chance of playing")
    C.log("    (predicted/observed) and rate per 82 in seasons played (predicted/actual):")
    for tier in ("3+", "2 to 3", "1 to 2", "0 to 1"):
        C.log(f"      tier {tier}:")
        for k in ARMS:
            if k == "current":
                continue
            d = al[k].reset_index()[keep]
            d = d[(d["tier"] == tier) & (d["h"] >= 3)].copy()
            d["band"] = pd.cut(d["age"], AGE_BANDS[0], labels=AGE_BANDS[1])
            cells = []
            for b in AGE_BANDS[1]:
                x = d[d["band"] == b]
                p = x[x["played"].astype(bool)]
                cells.append(f"{b} play {x['p_play'].mean():.2f}/{x['played'].mean():.2f} "
                             f"rate {p['rate_82'].mean():.2f}/{p['act_rate_82'].mean():.2f}")
            C.log(f"        {LABEL[k]:<28} " + " | ".join(cells))
    C.log("    season-WAR bias five seasons out, other tiers:")
    C.log("    " + f"{'arm':<30}" + "".join(f"{t:>10}" for t in TIERS[:-1]))
    for k in ARMS:
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        C.log("    " + f"{LABEL[k]:<30}" + "".join(
            f"{e[(d['tier'] == t) & (d['h'] == 5)].mean():>+10.2f}" for t in TIERS[:-1]))
    C.log("    THE DECLARED RULE:")
    for k in ("A", "S", "A+S"):
        d = al[k].reset_index()[keep]
        se = (d["pred_war"] - d["act_war"]) ** 2
        br = (d["p_play"] - d["played"].astype(float)) ** 2
        re_ = (d.loc[pl, "rate_82"] - d.loc[pl, "act_rate_82"]).abs()
        better = boot.lower_share(b_se, se) >= 0.975
        worse_rate = boot_pl.lower_share(re_, b_re) >= 0.975
        worse_brier = boot.lower_share(br, b_br) >= 0.975
        verdict = "IMPROVES Model 3" if (better and not worse_rate and not worse_brier) else "does not improve"
        C.log(f"      {LABEL[k]:<30} {verdict}")
    C.log("")
    return out


def main() -> None:
    C.banner("run_star_late_test.py", SCRIPT_VERSION)
    path, how = RAC._birthdates()
    C.log(f"  birthdates: {how}")
    SFP = PA._production()[0]
    C.log(f"  production age table read: {Path(SFP.F_WAR_AGE).resolve()}")
    table = build_table(birthdate_csv=path, verbose=False)
    har = H.Harness(table)
    runs = {}
    for k, cls in ARMS.items():
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS)
        C.log(f"  ran {k} ({cls.name}): {len(runs[k])} forecasts")
    C.log("")
    al = {k: d.set_index(KEYS).sort_index() for k, d in runs.items()}
    guards(al)
    C.log("")
    ans = al["current"]["outside_production"].eq(0).to_numpy()
    rows = score(al, "rows the current model answers", ans)
    rows += score(al, "full grid (current model plus its fallback)", np.ones(len(ans), bool))
    pd.DataFrame(rows).to_csv(C.out_path("star_late_summary.csv"), index=False)
    pd.concat([d.assign(arm=k) for k, d in runs.items()], ignore_index=True).to_csv(
        C.out_path("star_late_forecasts.csv"), index=False)
    C.write_log("star_late_run_log.txt")


if __name__ == "__main__":
    main()
