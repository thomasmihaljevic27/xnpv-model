"""run_star_residual.py -- where the forecast under-rates its best players, and
three single changes that might fix it.

EXPERIMENTAL (50_REBUILD). Development pages and development start years only.
Nothing is adopted by this run.

WHAT THE RESIDUAL IS, LOCATED BEFORE THIS RUN
    On the adopted skater leader (`A1HingeExposureStatus`), for players with a
    trailing total of three wins or more, the rate per 82 games is right at the
    valuation season (-0.03) and then falls about 0.27 a season along the aging
    walk: 3.24 to 1.90 over five seasons, where the stars who played fell from
    3.26 to 2.82. Season WAR is 1.06 low five seasons out. Every tier shows the
    same too-steep walk, smaller. The earlier hinge terms acted on the
    valuation-season fit, where the stars' rate was already about right.

THE CANDIDATES, EACH ONE CHANGE FROM THE ADOPTED LEADER
    survivor_aging  the aging curve fitted on survivors, without the
                    replacement-level imputation of departing players' seasons
                    (the forecast rate is conditional on playing, and departure
                    is the participation model's job)
    no_level_aging  the aging curve without its level terms (age and position
                    alone)
    reduced_form    the rate at each horizon from that horizon's own regression
                    on the anchor, fitted on seasons played, instead of the walk
    Participation, games share, the valuation-season rate and the harness are
    identical. A combination is scored only if two singles each improve.

THE SCORES, DECLARED BEFORE THE RUN
    1. season WAR, harness at 1 July, pages 2015-2021, horizons 0-5: squared
       error primary; absolute error and bias beside it; Brier (unchanged by
       construction, printed as a check that participation did not move);
    2. the residual itself: the rate bias among seasons played, and season WAR
       bias, for the three-win-and-up tier by horizon, and the top tenth of
       each version's own predictions; the tier's squared error against the
       adopted leader's on the same rows;
    3. contract dollars: every version's point valuation and the realised
       production priced on ONE line -- the adopted leader's (primary) and the
       reduced form's (sensitivity, declared as the most different candidate)
       -- realised target asserted identical, ended terms only.
    Comparisons resample players (2,000 draws); shares print as exact counts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table, birthdate_source
from ability_forecast import (A1StatusSurvivorAging, A1StatusNoLevelAging,
                              A1StatusReducedForm)
from run_npv_simulation import LEADER
import run_skater_contract_test as RSC

SCRIPT_VERSION = "1.0"

VARIANTS = {"adopted": LEADER,
            "survivor_aging": A1StatusSurvivorAging,
            "no_level_aging": A1StatusNoLevelAging,
            "reduced_form": A1StatusReducedForm}
REF = "adopted"
PAIRS = tuple((REF, k) for k in VARIANTS if k != REF)
STAR = "3+"


def residual(runs: dict) -> None:
    """Score 2: the star residual itself, by horizon, for every version."""
    keys = ["career_key", "page", "h"]
    lead = runs[REF]
    al = {k: d.set_index(keys).reindex(lead.set_index(keys).index).reset_index()
          for k, d in runs.items()}
    C.log("THE RESIDUAL, three-win-and-up tier (trailing total), by seasons ahead.")
    C.log("Rate bias is predicted minus actual rate per 82 among seasons played;")
    C.log("WAR bias is over every forecast, played or not.")
    C.log("")
    C.log(f"    {'h':<4}" + "".join(f"{k + ' rate':>22}" for k in al))
    for h in RSC.HORIZONS:
        line = f"    {h:<4}"
        for d in al.values():
            m = (d["tier"] == STAR) & (d["h"] == h) & (d["played"] == 1)
            line += f"{d.loc[m, 'e_rate'].mean():>+22.3f}"
        C.log(line)
    C.log("")
    C.log(f"    {'h':<4}" + "".join(f"{k + ' WAR':>22}" for k in al))
    for h in RSC.HORIZONS:
        line = f"    {h:<4}"
        for d in al.values():
            m = (d["tier"] == STAR) & (d["h"] == h)
            line += f"{d.loc[m, 'e_war'].mean():>+22.3f}"
        C.log(line)
    C.log("")
    star = al[REF]["tier"] == STAR
    boot = RSC.Boot(al[REF].loc[star, "career_key"])
    C.log(f"  the tier's season WAR squared error, {int(star.sum())} forecasts, and the")
    C.log("  share of player-resamples in which each version's is lower than the")
    C.log("  adopted leader's:")
    se_ref = al[REF].loc[star, "e_war"] ** 2
    for k, d in al.items():
        se = d.loc[star, "e_war"] ** 2
        share = "--" if k == REF else RSC._count(boot.lower_share(se_ref, se))
        C.log(f"    {k:<16}RMSE {np.sqrt(se.mean()):.4f}   bias {d.loc[star, 'e_war'].mean():+.4f}"
              f"   lower than adopted {share}")
    C.log("")
    C.log("  the top tenth of each version's OWN predicted season WAR:")
    for k, d in al.items():
        top = d["pred_war"] >= d["pred_war"].quantile(0.9)
        C.log(f"    {k:<16}predicted {d.loc[top, 'pred_war'].mean():.3f}   "
              f"actual {d.loc[top, 'act_war'].mean():.3f}   "
              f"miss {(d.loc[top, 'pred_war'] - d.loc[top, 'act_war']).mean():+.3f}   n={int(top.sum())}")
    C.log("")
    C.log("  every tier, rate bias among seasons played, five seasons out:")
    tiers = [t for t in ("below 0", "0 to 1", "1 to 2", "2 to 3", "3+")]
    C.log(f"    {'tier':<10}" + "".join(f"{k:>16}" for k in al))
    for t in tiers:
        line = f"    {t:<10}"
        for d in al.values():
            m = (d["tier"] == t) & (d["h"] == 5) & (d["played"] == 1)
            line += f"{d.loc[m, 'e_rate'].mean():>+16.3f}"
        C.log(line)
    C.log("")


def main() -> None:
    C.banner("run_star_residual.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    C.log("")
    har = H.Harness(table)
    runs = {}
    for k, cls in VARIANTS.items():
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=RSC.HORIZONS)
        C.log(f"  ran {k}: {len(runs[k])} forecasts")
    C.log("")
    RSC.season_scores(runs, ref=REF, pairs=PAIRS)
    residual(runs)
    RSC.dollars(table, variants=VARIANTS, ref=REF, line_tags=("adopted", "reduced_form"))
    out = pd.concat([d.assign(variant=k) for k, d in runs.items()], ignore_index=True)
    out.to_csv(C.out_path("star_residual.csv"), index=False)
    C.write_log("star_residual_run_log.txt")


if __name__ == "__main__":
    main()
