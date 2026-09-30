"""run_obvious_fixes_test.py -- the current model with every listed fix, scored.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

THE QUESTION
    If the current model took every fix with an obvious case (a three-season
    starting rate per 82 with the fitted pull toward the league, a games-share
    forecast, a chance-of-playing forecast, the look-ahead and age-table fixes,
    additive aging changes, the survivorship fix, dated fits) and kept its
    comparable-player aging method, how would it score against the current
    model and the rebuilt one? The model is `obvious_fixes.ObviousFixes`; its
    docstring lists exactly what is and is not changed.

THE LADDER (same rows, same targets; each rung changes one thing)
    current           the live chain (ProductionChain v1.3), as it now runs
    plain_start       fixes applied, but the start is a plain 50/30/20 rate per
                      82 with no pull toward the league
    obvious_fixes     + the fitted pull (the headline)
    survivors_pool    obvious_fixes with production's survivors-only pool:
                      what the survivorship fix adds to comparables
    rebuilt           obvious_fixes with the fitted aging equation instead of
                      comparables: the rebuilt model (A1HingeExposure, the
                      adopted leader's twin without contract data)
    Every rung past the current model shares the rebuilt games share and
    chance of playing exactly (asserted), so the rungs differ only in the rate.

SCORES, DECLARED BEFORE THE RUN
    season WAR squared error (primary), absolute error and bias; the rate per 82
    in seasons played one to five seasons out, absolute error (what aging
    predicts); on the rows production answers (primary) and the full grid.
    Shares are counts of 2,000 player resamples.

GUARDS
    * the age table production reads is logged by its real path;
    * one row set and one target for every arm;
    * games share and chance of playing identical across the four non-current
      arms; the fitted start identical between obvious_fixes and rebuilt in the
      valuation season;
    * survivors_pool reproduces run_aging_method_test's comparables arm on
      every row it saved (where that file exists), so the comparables walk is
      the one already scored.
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
import obvious_fixes as OF
from run_skater_contract_test import Boot, _count
import run_aging_choices_test as RAC

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)
KEYS = ["career_key", "page", "h"]
TIERS = ("below 0", "0 to 1", "1 to 2", "2 to 3", "3+")
ARMS = {"current": PA.ProductionChain, "plain_start": OF.PlainStart,
        "obvious_fixes": OF.ObviousFixes, "survivors_pool": OF.ObviousFixesSurvivors,
        "rebuilt": A1HingeExposure}
LABEL = {"current": "current model, as it runs",
         "plain_start": "fixes, plain 50/30/20 start",
         "obvious_fixes": "fixes, fitted start (headline)",
         "survivors_pool": "fixes, survivors-only pool",
         "rebuilt": "rebuilt model"}


def guards(runs):
    al = {k: d.set_index(KEYS).sort_index() for k, d in runs.items()}
    ref = al["current"]
    for k, d in al.items():
        assert d.index.equals(ref.index), f"{k} answered different rows"
        for c in ("act_war", "played"):
            assert np.array_equal(d[c].to_numpy(), ref[c].to_numpy()), f"{k}: target {c} differs"
    reb = al["rebuilt"]
    for k in ("plain_start", "obvious_fixes", "survivors_pool"):
        for c in ("gp_share", "p_play"):
            assert np.array_equal(al[k][c].to_numpy(), reb[c].to_numpy()), f"{k} moved {c}"
    h0 = reb.index.get_level_values("h") == 0
    for k in ("obvious_fixes", "survivors_pool"):
        assert np.array_equal(al[k].loc[h0, "rate_82"].to_numpy(), reb.loc[h0, "rate_82"].to_numpy()), \
            f"{k}: the fitted start differs from the rebuilt model's"
    C.log("  guards: one row set and target; games share and chance of playing identical")
    C.log("  across the fixed arms and the rebuilt model; fitted start identical in the")
    C.log("  valuation season")
    saved = C.out_path("aging_method_forecasts.csv")
    if Path(saved).exists():
        s = pd.read_csv(saved)
        s = s[s["arm"] == "comparables"].set_index(KEYS).sort_index()
        mine = al["survivors_pool"].reindex(s.index)
        gap = float(np.nanmax(np.abs(mine["rate_82"].to_numpy() - s["rate_82"].to_numpy())))
        assert gap < 1e-9, f"survivors_pool does not reproduce the aging-method comparables arm ({gap:.2e})"
        C.log(f"  guard: survivors_pool reproduces the aging-method test's comparables arm on "
              f"{len(s)} rows (largest gap {gap:.1e})")
    else:
        C.log("  (aging_method_forecasts.csv absent: the reproduction guard was not run)")
    return al


def score(al, label, mask=None):
    base = al["current"].reset_index()
    sel = np.ones(len(base), bool) if mask is None else np.asarray(mask(base), bool)
    b = base[sel]
    boot = Boot(b["career_key"])
    ref_se = (b["pred_war"] - b["act_war"]) ** 2
    reb = al["rebuilt"].reset_index()[sel]
    reb_se = (reb["pred_war"] - reb["act_war"]) ** 2
    C.log(f"  SEASON WAR, {label}: {int(sel.sum())} forecasts, {b['career_key'].nunique()} players")
    C.log(f"    {'arm':<34}{'RMSE':>8}{'vs current':>12}{'lower':>11}{'vs rebuilt':>12}"
          f"{'lower':>11}{'MAE':>8}{'bias':>8}")
    out = []
    r0 = float(np.sqrt(ref_se.mean()))
    rr = float(np.sqrt(reb_se.mean()))
    for k in ARMS:
        d = al[k].reset_index()[sel]
        e = d["pred_war"] - d["act_war"]
        rmse = float(np.sqrt((e ** 2).mean()))
        lc = "--" if k == "current" else _count(boot.lower_share(ref_se, e ** 2))
        lr = "--" if k == "rebuilt" else _count(boot.lower_share(reb_se, e ** 2))
        C.log(f"    {LABEL[k]:<34}{rmse:>8.4f}{(rmse / r0 - 1) * 100:>+11.1f}%{lc:>11}"
              f"{(rmse / rr - 1) * 100:>+11.1f}%{lr:>11}{e.abs().mean():>8.4f}{e.mean():>+8.4f}")
        out.append(dict(sample=label, arm=k, n=int(sel.sum()), rmse=rmse,
                        mae=float(e.abs().mean()), bias=float(e.mean())))
    C.log("    ('lower' = resamples in which the arm's squared error is below the named model's)")
    C.log(f"    RMSE by seasons ahead ({label}):")
    C.log("    " + f"{'arm':<34}" + "".join(f"{'h' + str(h):>8}" for h in HORIZONS))
    for k in ARMS:
        d = al[k].reset_index()[sel]
        C.log("    " + f"{LABEL[k]:<34}" + "".join(
            f"{np.sqrt(((d.loc[d['h'] == h, 'pred_war'] - d.loc[d['h'] == h, 'act_war']) ** 2).mean()):>8.4f}"
            for h in HORIZONS))
    C.log(f"    season WAR bias by tier, valuation season -> five out ({label}):")
    C.log("    " + f"{'arm':<34}" + "".join(f"{t:>15}" for t in TIERS))
    for k in ARMS:
        d = al[k].reset_index()[sel]
        e = d["pred_war"] - d["act_war"]
        cells = [f"{e[(d['tier'] == t) & (d['h'] == 0)].mean():+.2f} -> "
                 f"{e[(d['tier'] == t) & (d['h'] == 5)].mean():+.2f}" for t in TIERS]
        C.log("    " + f"{LABEL[k]:<34}" + "".join(f"{c:>15}" for c in cells))
    # the rate per 82, seasons 1-5 played: the part aging predicts
    pl = (b["h"] >= 1).to_numpy() & b["played"].astype(bool).to_numpy()
    bp = Boot(b.loc[pl, "career_key"])
    ref_r = (reb.loc[pl, "rate_82"] - reb.loc[pl, "act_rate_82"]).abs()
    C.log(f"    RATE PER 82, one to five seasons out, seasons played ({int(pl.sum())}), "
          f"absolute error; 'lower' against the rebuilt model:")
    for k in ARMS:
        if k == "current":
            continue                           # its rate_82 is a season total, not a rate
        d = al[k].reset_index()[sel]
        er = (d.loc[pl, "rate_82"] - d.loc[pl, "act_rate_82"]).abs()
        lr = "--" if k == "rebuilt" else _count(bp.lower_share(ref_r, er))
        tiers = "  ".join(f"{t} {er[d.loc[pl, 'tier'] == t].mean():.3f}" for t in TIERS)
        C.log(f"      {LABEL[k]:<34}{er.mean():>8.4f}{lr:>11}   {tiers}")
    C.log("")
    return out


def main() -> None:
    C.banner("run_obvious_fixes_test.py", SCRIPT_VERSION)
    path, how = RAC._birthdates()
    C.log(f"  birthdates: {how}")
    SFP = PA._production()[0]
    C.log(f"  production age table read: {Path(SFP.F_WAR_AGE).resolve()}")
    table = build_table(birthdate_csv=path, verbose=False)
    har = H.Harness(table)
    runs = {}
    for k, cls in ARMS.items():
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS)
        C.log(f"  ran {k} ({cls.__name__}): {len(runs[k])} forecasts")
    C.log("  departures entered at replacement in the comparables pool, by page: " + ", ".join(
        f"{p} {m.n_imputed:,}" for (imp, p), m in sorted(OF._ComparablesAging._curves.items()) if imp))
    C.log("")
    al = guards(runs)
    C.log("")
    rows = score(al, "rows production answers", lambda d: d["outside_production"].eq(0))
    rows += score(al, "full grid (production plus its fallback)")
    pd.DataFrame(rows).to_csv(C.out_path("obvious_fixes_summary.csv"), index=False)
    pd.concat([d.assign(arm=k) for k, d in runs.items()], ignore_index=True).to_csv(
        C.out_path("obvious_fixes_forecasts.csv"), index=False)
    C.write_log("obvious_fixes_run_log.txt")


if __name__ == "__main__":
    main()
