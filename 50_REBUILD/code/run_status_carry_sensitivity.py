"""run_status_carry_sensitivity.py -- does carrying contract status past its
support improve the adopted skater leader?

EXPERIMENTAL (50_REBUILD). Development pages and development start years only.
A SCORED SENSITIVITY: nothing is adopted by this run.

WHY THIS RUN EXISTS
    The adopted skater leader (`A1HingeExposureStatus`, adopted provisionally
    2026-09-23) reads visible contract status in its participation model. That
    column enters a horizon's fit only where enough training rows carry each
    value, and visible status exists only for seasons from 2018, so on the
    development pages it enters for the first four to six seasons ahead and
    not beyond. Past that the forecast is the no-contract one: an eight-year
    deal signed in 2021 reads about 0.93 to play in season seven and 0.45 in
    season eight.

    The candidate (`A1HingeExposureStatusCarry`) carries the last supported
    horizon's fit forward, with the player's status read for the actual
    season and a league-wide decay per extra season. It is an assumption. It
    is scored here before anything changes.

WHAT IS COMPARED -- THREE VERSIONS, MATCHED
    previous  the no-contract leader (`A1HingeExposure`)
    adopted   the provisional leader, status where supported
    carried   the adopted leader, status carried past its support
    Ability, aging, the rate and games halves, and the harness are identical;
    only participation differs.

THE SCORES, DECLARED BEFORE THE RUN
    1. participation (Brier) and season WAR (squared error primary; absolute
       error and bias beside it), harness at 1 July, horizons 0-5;
    2. contract dollars: every version's point valuation and the realised
       production priced on ONE line -- the adopted version's (primary; it is
       the incumbent), the previous leader's as the sensitivity -- with the
       realised target asserted identical across versions, ended terms only;
    3. the shape of the season-by-season participation the path simulation
       is handed, through its own caller (`forecast_blocks`): how many terms
       carry a one-season fall of more than 0.25 while the player is under
       contract (a cliff), how many ask for a rise the simulation's return
       rate cannot deliver (clipped), and the EXACT expected production that
       clipping costs, from the chain's own recursion rather than from draws.
    The candidate is judged against the adopted version on 1 and 2; 3 says
    whether it removes what it was built to remove, and is not a score.

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
import npv_simulation as SIM
from contract_price_model import contract_sample
from player_season_table import build as build_table, birthdate_source
from ability_forecast import A1HingeExposureStatusCarry
from run_npv_simulation import LEADER, PRIOR_LEADER, forecast_blocks
import run_skater_contract_test as RSC

SCRIPT_VERSION = "1.0"

VARIANTS = {"previous": PRIOR_LEADER, "adopted": LEADER,
            "carried": A1HingeExposureStatusCarry}
REF = "adopted"
PAIRS = (("adopted", "carried"), ("previous", "adopted"), ("previous", "carried"))
CLIFF = 0.25          # a one-season fall in P(plays) larger than this, under contract


def path_shape(table: pd.DataFrame) -> None:
    """Scores 3: the participation each version hands the path simulation."""
    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_status_carry_sensitivity")
    s = sample[sample["start_yr"].isin(cohorts)
               & (sample["signed"] >= pd.Timestamp("2015-07-01"))]
    C.log("THE PARTICIPATION HANDED TO THE PATH SIMULATION, over each contract's")
    C.log(f"own term, through forecast_blocks; {len(s)} development contracts asked.")
    C.log(f"A cliff is a one-season fall of more than {CLIFF} in the chance of")
    C.log("playing; every season asked here is inside the contract's term.")
    C.log("")
    C.log(f"    {'version':<10}{'terms':>7}{'with a cliff':>14}{'clipped':>9}"
          f"{'clipping, mean |WAR|/season':>30}{'largest':>10}")
    rets, keep = {}, {}
    for k in ("adopted", "carried"):
        blocks, _ = forecast_blocks(s, table, model_factory=VARIANTS[k])
        n_cliff = n_clip = 0
        eff = []
        for cid, (t0, mu, _sig, pp, _yrs) in blocks.items():
            r = rets.setdefault(t0, SIM.return_rate(table, before=t0))
            n_cliff += int((np.diff(pp) < -CLIFF).any())
            e, clipped = SIM.exit_schedule(pp, r)
            if clipped:
                n_clip += 1
                # The chain the simulation actually walks, from its own
                # recursion: the marginal it delivers, against the one asked.
                a = np.empty(len(pp))
                a[0] = pp[0]
                for h in range(1, len(pp)):
                    a[h] = a[h - 1] * (1 - e[h]) + (1 - a[h - 1]) * r
                eff.append(float(np.mean((a - pp) * mu)))
        keep[k] = blocks
        eff = np.abs(np.array(eff)) if eff else np.zeros(1)
        C.log(f"    {k:<10}{len(blocks):>7}{n_cliff:>14}{n_clip:>9}"
              f"{eff.mean():>30.6f}{eff.max():>10.6f}")
    C.log("")
    C.log("  the eight-year 2021 deal that showed the cliff (contract 6500):")
    for k, blocks in keep.items():
        if 6500 in blocks:
            C.log(f"    {k:<10}" + " ".join(f"{x:.3f}" for x in blocks[6500][3]))
    C.log("")


def main() -> None:
    C.banner("run_status_carry_sensitivity.py", SCRIPT_VERSION)
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
    RSC.dollars(table, variants=VARIANTS, ref=REF, line_tags=("adopted", "previous"))
    path_shape(table)
    out = pd.concat([d.assign(variant=k) for k, d in runs.items()], ignore_index=True)
    out.to_csv(C.out_path("status_carry_sensitivity.csv"), index=False)
    C.write_log("status_carry_sensitivity_run_log.txt")


if __name__ == "__main__":
    main()
