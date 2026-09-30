"""run_star_bias_test.py -- three single changes aimed at the star under-forecast.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

THE BASE is obvious_fixes.ObviousFixes (the current model with every listed
fix, comparable-player aging kept). The candidates are in star_candidates.py:
    G  the games-share forecast reads the player's level
    P  the chance of playing gets a second level slope above two wins
    R  the comparables' yearly changes measured on raw seasons after the match
    H  (v1.1) the comparables' similarity window at half the yardstick
Each is scored alone, then G+R and G+P+R, and (v1.1) G+H. H was added after
v1.0's results were read; the rule below is unchanged and applies to it.
(v1.2) "rebuilt+G" is the rebuilt model with G only, so both models are
compared with the same games-share fix; its rows are scored against the base
like every arm, and against the rebuilt model in the log line after the table. The rebuilt model and the current
model are printed for reference.

THE RULE, DECLARED BEFORE THE RUN (rows the current model answers)
    * A candidate IMPROVES the base only if its season-WAR squared error is
      lower in at least 1,950 of 2,000 player resamples, and neither its rate
      error (per 82, seasons 1-5, seasons played) nor its Brier score is higher
      in 1,950 or more.
    * The star bias counts as REMOVED if the 3+ tier's mean season-WAR bias
      over seasons 1-5 has a 95% player-resampled interval that includes zero.
      The 3+ tier holds 88 players, so the interval, not the point, decides.
    * Lower tiers' bias five seasons out is reported so that a star fix paid
      for elsewhere is visible.

GUARDS
    * the age table production reads is logged by its real path;
    * one row set and target for every arm;
    * the base with every switch off reproduces the saved ObviousFixes
      forecasts (obvious_fixes_forecasts.csv) exactly, where that file exists;
    * G moves only games share, P only the chance of playing, R only the rate
      past the valuation season (asserted against the base).
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
from ability_forecast import A1HingeExposure
import production_adapter as PA
import star_candidates as SC
from run_skater_contract_test import Boot, _count
import run_aging_choices_test as RAC

SCRIPT_VERSION = "1.2"
HORIZONS = (0, 1, 2, 3, 4, 5)
KEYS = ["career_key", "page", "h"]
TIERS = ("below 0", "0 to 1", "1 to 2", "2 to 3", "3+")
ARMS = {"base": SC.candidate(), "G": SC.candidate(gp=True), "P": SC.candidate(part=True),
        "R": SC.candidate(raw=True), "G+R": SC.candidate(gp=True, raw=True),
        "G+P+R": SC.candidate(gp=True, part=True, raw=True),
        "H": SC.candidate(half=True), "G+H": SC.candidate(gp=True, half=True),
        "rebuilt": A1HingeExposure, "rebuilt+G": SC.RebuiltGamesLevel,
        "current": PA.ProductionChain}
LABEL = {"base": "obvious fixes (base)", "G": "G: games share reads level",
         "P": "P: participation hinge", "R": "R: raw comparables steps",
         "G+R": "G + R", "G+P+R": "G + P + R", "H": "H: half-width comparables",
         "G+H": "G + H", "rebuilt": "rebuilt model", "rebuilt+G": "rebuilt model + G",
         "current": "current model"}


def guards(al):
    ref = al["base"]
    for k, d in al.items():
        assert d.index.equals(ref.index), f"{k} answered different rows"
        for c in ("act_war", "played"):
            assert np.array_equal(d[c].to_numpy(), ref[c].to_numpy()), f"{k}: target {c} differs"
    same = lambda k, c: np.array_equal(al[k][c].to_numpy(), ref[c].to_numpy())
    h0 = ref.index.get_level_values("h") == 0
    assert same("G", "rate_82") and same("G", "p_play") and not same("G", "gp_share")
    assert same("P", "rate_82") and same("P", "gp_share") and not same("P", "p_play")
    assert same("R", "gp_share") and same("R", "p_play") and not same("R", "rate_82")
    assert np.array_equal(al["R"].loc[h0, "rate_82"].to_numpy(), ref.loc[h0, "rate_82"].to_numpy())
    assert same("H", "gp_share") and same("H", "p_play") and not same("H", "rate_82")
    assert np.array_equal(al["H"].loc[h0, "rate_82"].to_numpy(), ref.loc[h0, "rate_82"].to_numpy())
    C.log("  guards: one row set and target; G moves only games share, P only the chance")
    C.log("  of playing, R and H only the rate past the valuation season")
    saved = C.out_path("obvious_fixes_forecasts.csv")
    if Path(saved).exists():
        s = pd.read_csv(saved, low_memory=False)
        s = s[s["arm"] == "obvious_fixes"].set_index(KEYS).sort_index()
        mine = ref.reindex(s.index)
        for c in ("rate_82", "gp_share", "p_play"):
            gap = float(np.nanmax(np.abs(mine[c].to_numpy() - s[c].to_numpy())))
            assert gap < 1e-12, f"base does not reproduce ObviousFixes on {c} ({gap:.2e})"
        C.log(f"  guard: the base reproduces the saved ObviousFixes forecasts on {len(s)} rows")


def score(al, label, keep):
    base = al["base"].reset_index()[keep]
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
    C.log(f"    {'arm':<30}{'RMSE':>8}{'lower':>11}{'MAE':>8}{'rate err':>10}{'higher':>9}"
          f"{'Brier':>8}{'higher':>9}{'3+ RMSE':>9}{'lower':>11}")
    out = []
    for k in ARMS:
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        se = e ** 2
        br = (d["p_play"] - d["played"].astype(float)) ** 2
        re_ = (d.loc[pl, "rate_82"] - d.loc[pl, "act_rate_82"]).abs()
        rate_ok = k != "current"                      # its rate_82 is a season total
        lo = "--" if k == "base" else _count(boot.lower_share(b_se, se))
        hr = "--" if k in ("base", "current") else _count(boot_pl.lower_share(re_, b_re))
        hb = "--" if k == "base" else _count(boot.lower_share(br, b_br))
        st = "--" if k == "base" else _count(boot_st.lower_share(b_se[star], se[star]))
        C.log(f"    {LABEL[k]:<30}{np.sqrt(se.mean()):>8.4f}{lo:>11}{e.abs().mean():>8.4f}"
              f"{(re_.mean() if rate_ok else float('nan')):>10.4f}{hr:>9}{br.mean():>8.4f}{hb:>9}"
              f"{np.sqrt(se[star].mean()):>9.4f}{st:>11}")
        m, lo95, hi95 = boot_s15.mean_ci(e[s15])
        out.append(dict(sample=label, arm=k, rmse=float(np.sqrt(se.mean())), mae=float(e.abs().mean()),
                        rate_mae=float(re_.mean()) if rate_ok else np.nan, brier=float(br.mean()),
                        star_rmse=float(np.sqrt(se[star].mean())), star_bias_1_5=m,
                        star_bias_lo=lo95, star_bias_hi=hi95))
    C.log("    ('lower' = resamples, of 2,000, with lower error than the base; 'higher' = with")
    C.log("    HIGHER rate error / Brier than the base, which the rule caps below 1,950)")
    for a_, b_ in (("rebuilt", "rebuilt+G"), ("rebuilt+G", "G")):
        x = al[a_].reset_index()[keep]; y = al[b_].reset_index()[keep]
        C.log(f"    {LABEL[b_]} against {LABEL[a_]}: season-WAR squared error lower in "
              f"{_count(boot.lower_share((x['pred_war'] - x['act_war']) ** 2, (y['pred_war'] - y['act_war']) ** 2))}")
    C.log(f"    3+ tier season-WAR bias by seasons ahead, and its mean over 1-5 with 95% interval:")
    C.log("    " + f"{'arm':<30}" + "".join(f"{'h' + str(h):>8}" for h in HORIZONS) + "   mean 1-5 [95%]")
    for row, k in zip(out, ARMS):
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        cells = "".join(f"{e[star & (d['h'] == h).to_numpy()].mean():>+8.2f}" for h in HORIZONS)
        C.log("    " + f"{LABEL[k]:<30}" + cells +
              f"   {row['star_bias_1_5']:+.3f} [{row['star_bias_lo']:+.3f}, {row['star_bias_hi']:+.3f}]")
    C.log("    3+ tier pieces (predicted / observed), five seasons out: chance of playing; games")
    C.log("    share and rate per 82 among seasons played:")
    for k in ARMS:
        d = al[k].reset_index()[keep]
        x = d[star & (d["h"] == 5).to_numpy()]
        p = x[x["played"].astype(bool)]
        C.log(f"      {LABEL[k]:<30} play {x['p_play'].mean():.3f}/{x['played'].mean():.3f}   "
              f"games {p['gp_share'].mean():.3f}/{p['act_gp_share'].mean():.3f}   "
              f"rate {p['rate_82'].mean():.2f}/{p['act_rate_82'].mean():.2f}")
    C.log("    season-WAR bias five seasons out, other tiers:")
    C.log("    " + f"{'arm':<30}" + "".join(f"{t:>10}" for t in TIERS[:-1]))
    for k in ARMS:
        d = al[k].reset_index()[keep]
        e = d["pred_war"] - d["act_war"]
        C.log("    " + f"{LABEL[k]:<30}" + "".join(
            f"{e[(d['tier'] == t) & (d['h'] == 5)].mean():>+10.2f}" for t in TIERS[:-1]))
    # the declared rule
    C.log("    THE DECLARED RULE:")
    for k in ARMS:
        if k in ("base", "current", "rebuilt", "rebuilt+G"):
            continue
        d = al[k].reset_index()[keep]
        se = (d["pred_war"] - d["act_war"]) ** 2
        br = (d["p_play"] - d["played"].astype(float)) ** 2
        re_ = (d.loc[pl, "rate_82"] - d.loc[pl, "act_rate_82"]).abs()
        better = boot.lower_share(b_se, se) >= 0.975
        worse_rate = boot_pl.lower_share(re_, b_re) >= 0.975
        worse_brier = boot.lower_share(br, b_br) >= 0.975
        row = next(r for r in out if r["arm"] == k)
        removed = row["star_bias_lo"] <= 0 <= row["star_bias_hi"]
        verdict = "IMPROVES the base" if (better and not worse_rate and not worse_brier) else "does not improve"
        C.log(f"      {LABEL[k]:<30} {verdict}; star bias {'REMOVED' if removed else 'not removed'}")
    C.log("")
    return out


def main() -> None:
    C.banner("run_star_bias_test.py", SCRIPT_VERSION)
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
    pd.DataFrame(rows).to_csv(C.out_path("star_bias_summary.csv"), index=False)
    pd.concat([d.assign(arm=k) for k, d in runs.items()], ignore_index=True).to_csv(
        C.out_path("star_bias_forecasts.csv"), index=False)
    C.write_log("star_bias_run_log.txt")


if __name__ == "__main__":
    main()
