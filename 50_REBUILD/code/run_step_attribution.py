"""run_step_attribution.py -- the current and rebuilt skater forecasts, piece by piece.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

THE QUESTION
    The scorecard (Model_Scorecard.md, 2026-09-24) compared the two whole
    forecasts before the current model's two 2026-09-28 revisions (aging curve
    and exit hazard fitted on seasons before each valuation date, older careers
    restored to the age table). This run repeats the whole-forecast comparison
    against the current model AS IT NOW RUNS, and splits the gap into its
    pieces so no piece is credited with another's gain.

HOW A SEASON FORECAST IS BUILT, IN BOTH MODELS (forecast_harness.py)
    expected season WAR = p_play * rate_82 * gp_share
      production if he plays  T = rate_82 * gp_share
          current: the 60/40 trailing total walked along the aging path;
                   gp_share is 1 because the current model has no games
                   forecast (production_adapter.py, "THE MAPPING")
          rebuilt: the shrunk per-82 rate walked by the fitted aging equation,
                   times its own games-share forecast
      chance he plays         P = p_play
          current: the exit-hazard survival factor, one in the valuation season
          rebuilt: its participation model
    So the season forecast is P * T, and the two pieces can be swapped.

THE ARMS (same rows, same targets)
    current           P_current * T_current     the live chain (ProductionChain v1.3)
    rebuilt_T         P_current * T_rebuilt     only "production if he plays" swapped
    rebuilt_P         P_rebuilt * T_current     only "chance he plays" swapped
    rebuilt           P_rebuilt * T_rebuilt     the rebuilt forecast
    Each swap is scored alone and together, and in both orders, because a gain
    from one piece can depend on the other.

    The rebuilt forecast here is `A1HingeExposure`, the adopted leader's twin
    WITHOUT contract data: the adopted leader reads the contract export, which
    is not in this container. The scorecard measured the two within 0.0005 of
    season-WAR RMSE (0.8640 against 0.8645 on production's answerable rows).

THE PIECES SCORED DIRECTLY
    * production if he plays: T against realised season WAR, seasons played;
      the valuation season isolates the starting level (no aging has been
      applied yet), seasons 1-5 add aging (split further in
      run_aging_method_test.py);
    * chance he plays: Brier score and predicted-minus-observed;
    * season WAR: the four arms, RMSE, MAE, bias, by horizon and by tier.
    Every score is on the full grid (production plus its fallback) and on the
    rows production answers itself; the same rows for every arm. Shares are
    counts of 2,000 player resamples.

GUARDS
    * the age table production reads is logged by its real path;
    * both models answer the same rows with the same realised targets;
    * the current arm reproduces the harness's own pred_war for ProductionChain,
      and the rebuilt arm reproduces the harness's pred_war for A1HingeExposure;
    * current P is exactly one in the valuation season.
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
from run_skater_contract_test import Boot, _count
import run_aging_choices_test as RAC

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)
KEYS = ["career_key", "page", "h"]
TIERS = ("below 0", "0 to 1", "1 to 2", "2 to 3", "3+")


def build_arms(cur: pd.DataFrame, reb: pd.DataFrame) -> pd.DataFrame:
    """One frame, one row per forecast, with both models' pieces side by side."""
    a = cur.set_index(KEYS).sort_index()
    b = reb.set_index(KEYS).sort_index()
    assert a.index.equals(b.index), "the two models answered different rows"
    for c in ("act_war", "played"):
        assert np.array_equal(a[c].to_numpy(), b[c].to_numpy()), f"target {c} differs"
    d = a[["act_war", "played", "tier", "outside_production"]].copy()
    d["T_cur"] = a["rate_82"] * a["gp_share"]
    d["T_reb"] = b["rate_82"] * b["gp_share"]
    d["P_cur"] = a["p_play"]
    d["P_reb"] = b["p_play"]
    h0 = d.index.get_level_values("h") == 0
    assert np.all(d.loc[h0, "P_cur"] == 1.0), "current survival is not one in the valuation season"
    d["current"] = d["P_cur"] * d["T_cur"]
    d["rebuilt_T"] = d["P_cur"] * d["T_reb"]
    d["rebuilt_P"] = d["P_reb"] * d["T_cur"]
    d["rebuilt"] = d["P_reb"] * d["T_reb"]
    # the swaps' end points are the harness's own forecasts, recomputed
    assert np.allclose(d["current"], a["pred_war"], rtol=0, atol=1e-12)
    assert np.allclose(d["rebuilt"], b["pred_war"], rtol=0, atol=1e-12)
    return d.reset_index()


ARMS = ("current", "rebuilt_T", "rebuilt_P", "rebuilt")


def season_war(d: pd.DataFrame, label: str) -> list:
    boot = Boot(d["career_key"])
    ref = (d["current"] - d["act_war"]) ** 2
    C.log(f"  SEASON WAR, {label}: {len(d)} forecasts, {d['career_key'].nunique()} players")
    C.log(f"    {'arm':<12}{'RMSE':>9}{'vs current':>12}{'lower':>11}{'MAE':>9}{'bias':>9}")
    out = []
    for k in ARMS:
        e = d[k] - d["act_war"]
        rmse = float(np.sqrt((e ** 2).mean()))
        lo = "--" if k == "current" else _count(boot.lower_share(ref, e ** 2))
        row = dict(sample=label, arm=k, n=len(d), rmse=rmse, mae=float(e.abs().mean()),
                   bias=float(e.mean()))
        out.append(row)
    base = out[0]["rmse"]
    for row in out:
        k = row["arm"]
        lo = "--" if k == "current" else _count(boot.lower_share(ref, (d[k] - d["act_war"]) ** 2))
        C.log(f"    {k:<12}{row['rmse']:>9.4f}{(row['rmse'] / base - 1) * 100:>+11.1f}%{lo:>11}"
              f"{row['mae']:>9.4f}{row['bias']:>+9.4f}")
    # the swap in both orders
    r = {row["arm"]: row["rmse"] for row in out}
    C.log("    the gap, split two ways (change in RMSE):")
    C.log(f"      production-if-plays first: {r['rebuilt_T'] - r['current']:+.4f}, "
          f"then chance-of-playing: {r['rebuilt'] - r['rebuilt_T']:+.4f}")
    C.log(f"      chance-of-playing first:   {r['rebuilt_P'] - r['current']:+.4f}, "
          f"then production-if-plays: {r['rebuilt'] - r['rebuilt_P']:+.4f}")
    C.log(f"    RMSE by seasons ahead ({label}):")
    C.log("    " + f"{'arm':<12}" + "".join(f"{'h' + str(h):>9}" for h in HORIZONS))
    for k in ARMS:
        C.log("    " + f"{k:<12}" + "".join(
            f"{np.sqrt(((d.loc[d['h'] == h, k] - d.loc[d['h'] == h, 'act_war']) ** 2).mean()):>9.4f}"
            for h in HORIZONS))
    C.log(f"    bias by tier of trailing total, valuation season -> five out ({label}):")
    C.log("    " + f"{'arm':<12}" + "".join(f"{t:>16}" for t in TIERS))
    for k in ("current", "rebuilt"):
        cells = []
        for t in TIERS:
            m = d["tier"] == t
            b0 = (d.loc[m & (d["h"] == 0), k] - d.loc[m & (d["h"] == 0), "act_war"]).mean()
            b5 = (d.loc[m & (d["h"] == 5), k] - d.loc[m & (d["h"] == 5), "act_war"]).mean()
            cells.append(f"{b0:+.2f} -> {b5:+.2f}")
        C.log("    " + f"{k:<12}" + "".join(f"{c:>16}" for c in cells))
    C.log("")
    return out


def pieces(d: pd.DataFrame, label: str) -> list:
    out = []
    pl = d["played"].astype(bool)
    dp = d[pl]
    boot_p = Boot(dp["career_key"])
    C.log(f"  PRODUCTION IF HE PLAYS, {label}: {len(dp)} seasons played, "
          f"{dp['career_key'].nunique()} players (season WAR, predicted minus actual)")
    C.log(f"    {'seasons ahead':<22}{'current MAE':>12}{'rebuilt MAE':>12}{'change':>9}{'lower':>11}"
          f"{'current bias':>14}{'rebuilt bias':>14}")
    for name, m in [("valuation season", dp["h"] == 0), ("one to five", dp["h"] >= 1)] + \
                   [(f"  {h} out", dp["h"] == h) for h in HORIZONS[1:]]:
        ec = (dp.loc[m, "T_cur"] - dp.loc[m, "act_war"])
        er = (dp.loc[m, "T_reb"] - dp.loc[m, "act_war"])
        bb = Boot(dp.loc[m, "career_key"])
        lo = _count(bb.lower_share(ec.abs(), er.abs()))
        C.log(f"    {name:<22}{ec.abs().mean():>12.4f}{er.abs().mean():>12.4f}"
              f"{(er.abs().mean() / ec.abs().mean() - 1) * 100:>+8.1f}%{lo:>11}"
              f"{ec.mean():>+14.3f}{er.mean():>+14.3f}")
        out.append(dict(sample=label, piece="production_if_plays", rows=name.strip(), n=int(m.sum()),
                        cur_mae=float(ec.abs().mean()), reb_mae=float(er.abs().mean()),
                        cur_bias=float(ec.mean()), reb_bias=float(er.mean())))
    C.log(f"    by tier, valuation season (MAE current / rebuilt; bias current / rebuilt):")
    for t in TIERS:
        m = (dp["h"] == 0) & (dp["tier"] == t)
        ec = dp.loc[m, "T_cur"] - dp.loc[m, "act_war"]
        er = dp.loc[m, "T_reb"] - dp.loc[m, "act_war"]
        C.log(f"      {t:<10} n={int(m.sum()):>5}  MAE {ec.abs().mean():.3f} / {er.abs().mean():.3f}"
              f"   bias {ec.mean():+.3f} / {er.mean():+.3f}")
    C.log("")
    boot = Boot(d["career_key"])
    y = d["played"].astype(float)
    bc = (d["P_cur"] - y) ** 2
    br = (d["P_reb"] - y) ** 2
    C.log(f"  CHANCE HE PLAYS, {label}: {len(d)} forecasts")
    C.log(f"    Brier current {bc.mean():.4f}, rebuilt {br.mean():.4f} "
          f"({(br.mean() / bc.mean() - 1) * 100:+.1f}%), rebuilt lower in {_count(boot.lower_share(bc, br))}")
    C.log(f"    {'seasons ahead':<16}{'observed':>10}{'current':>10}{'rebuilt':>10}"
          f"{'Brier cur':>11}{'Brier reb':>11}")
    for h in HORIZONS:
        m = d["h"] == h
        C.log(f"    {h:<16}{y[m].mean():>10.3f}{d.loc[m, 'P_cur'].mean():>10.3f}"
              f"{d.loc[m, 'P_reb'].mean():>10.3f}{bc[m].mean():>11.4f}{br[m].mean():>11.4f}")
        out.append(dict(sample=label, piece="chance_plays", rows=f"h{h}", n=int(m.sum()),
                        observed=float(y[m].mean()), cur_mean=float(d.loc[m, "P_cur"].mean()),
                        reb_mean=float(d.loc[m, "P_reb"].mean()),
                        cur_brier=float(bc[m].mean()), reb_brier=float(br[m].mean())))
    C.log("")
    return out


def main() -> None:
    C.banner("run_step_attribution.py", SCRIPT_VERSION)
    path, how = RAC._birthdates()
    C.log(f"  birthdates: {how}")
    # The label above names 30_OUTPUT whatever OUTPUT_DIR says; log the file
    # production actually reads (a practice OUTPUT_DIR holds a stale copy).
    SFP = PA._production()[0]
    C.log(f"  production age table read: {Path(SFP.F_WAR_AGE).resolve()}")
    table = build_table(birthdate_csv=path, verbose=False)
    har = H.Harness(table)
    cur = har.run(PA.ProductionChain(), pages=C.DEV_PAGES, horizons=HORIZONS)
    C.log(f"  ran the current model (production_adapter v{PA.SCRIPT_VERSION}): {len(cur)} forecasts")
    reb = har.run(A1HingeExposure(), pages=C.DEV_PAGES, horizons=HORIZONS)
    C.log(f"  ran the rebuilt model ({A1HingeExposure.name}): {len(reb)} forecasts")
    d = build_arms(cur, reb)
    C.log("  guards: same rows and targets; both end points reproduce the harness's forecasts; "
          "current survival is one in the valuation season")
    C.log("")
    rows = []
    for label, m in (("full grid (production plus its fallback)", np.ones(len(d), bool)),
                     ("rows production answers", d["outside_production"].eq(0).to_numpy())):
        dd = d[m].reset_index(drop=True)
        rows += [dict(kind="season_war", **r) for r in season_war(dd, label)]
        rows += [dict(kind="piece", **r) for r in pieces(dd, label)]
    pd.DataFrame(rows).to_csv(C.out_path("step_attribution_summary.csv"), index=False)
    d.to_csv(C.out_path("step_attribution_forecasts.csv"), index=False)
    C.write_log("step_attribution_run_log.txt")


if __name__ == "__main__":
    main()
