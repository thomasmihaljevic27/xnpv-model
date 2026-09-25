"""run_bakeoff.py -- score every live candidate on the same rows, and keep a
public count of how many have been tried.

EXPERIMENTAL (50_REBUILD).

WHY A STANDING BAKE-OFF RATHER THAN A KNOCKOUT
    A model that is behind on raw forecast accuracy can still be the right one
    once it is carrying dollars: what matters in the end is the error in the
    VALUE of a contract, and the two are not the same quantity. A model that
    is slightly worse on average but better on the expensive players, or better
    at the far end of a long deal, can win the thing that actually matters. So
    nothing is retired here. Every candidate stays in and gets rerun as
    participation, aging and pricing are added underneath it, and the decision
    is taken once, at the end, on dollars.

THE COUNT, AND WHY IT IS WRITTEN DOWN
    Every variant scored on the development seasons is another look at the same
    data. Look often enough and something wins by luck. The register this
    script appends to -- `docs/variant_register.csv`, committed, no player rows
    in it -- is the honest tally, so the final confirmatory run can state how
    many variants preceded it instead of implying the winner was the first
    idea. The seasons held back for that final run are never touched here.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from ability_forecast import (A0Production, A1Calibrated, A1Calibrated3, A1NoAgeTerms,
                              A2Raw, A2Component, A2NoAgeTerms, A2PerHorizonTrust,
                              A2PerHorizonTrust3, A2PerHorizonTrust4, A2PerHorizonAll3,
                              A1Calibrated3PerHorizon, A2PerComponentWindow,
                              A2PerComponentWindow4, A1Calibrated3Aging,
                              A2ComponentAging, A1Calibrated3AgingNaive,
                              A1AgingParticipation, A1AgingParticipationNoContracts,
                              A1ParticipationNoAging, A2AgingParticipation,
                              A1AgingParticipationImputed, A1AgingParticipationImputedNC,
                              A1AgingParticipationIPW, A2AgingParticipationImputed,
                              A1Hinge, A1HingeTwo, A1Exposure, A1HingeExposure,
                              A2PerHorizonTrustNoAge)
from player_season_table import build as build_table

SCRIPT_VERSION = "1.1"
REGISTER = C.DOCS_DIR / "variant_register.csv"

# The line every variant is measured against: the best model found so far, so
# a new idea has to beat the standing leader rather than an old one. It moved
# here from the two-season calibrated total once the three-season window won.
BENCHMARK = A1AgingParticipationImputedNC

CANDIDATES = [
    A0Production,          # the flat benchmark (NOT the live chain; that is ProductionChain) -- the floor
    A1Calibrated,          # the benchmark
    A1NoAgeTerms,          # control: do age terms help the simple model?
    A2Raw,                 # diagnostic: the split with no shrinking
    A2Component,           # the plan's lead candidate
    A2NoAgeTerms,          # repair 1: age carried only by the shrinkage target
    A2PerHorizonTrust,     # repair 2: trust fitted per season forecast
    A2PerHorizonTrustNoAge,  # both repairs together
    A1Calibrated3,           # the benchmark, reading three seasons
    A2PerHorizonTrust3,      # the leading component model, reading three seasons
    A2PerHorizonTrust4,      # and four, to find where the window stops paying
    A2PerHorizonAll3,        # trust AND window both fitted per horizon
    A1Calibrated3PerHorizon,  # control: per-horizon window on the simple model
    A2PerComponentWindow,    # a window fitted separately for each skill
    A2PerComponentWindow4,   # the same, with a fourth season available
    A1Calibrated3Aging,      # the leader, reaching later seasons by aging
    A2ComponentAging,        # the best component model, likewise
    A1Calibrated3AgingNaive,  # diagnostic: the same with the biased aging curve
    A1ParticipationNoAging,  # participation on its own, no aging walk
    A1AgingParticipation,    # aging AND participation
    A1AgingParticipationNoContracts,  # how much of it rests on the contract export
    A2AgingParticipation,    # the component model, aging and participation
    A1AgingParticipationImputed,    # survivorship: missing seasons imputed
    A1AgingParticipationImputedNC,  # the same in the leader's configuration
    A1AgingParticipationIPW,        # survivorship by reweighting -- does not work
    A2AgingParticipationImputed,    # the component model, corrected
    A1Hinge, A1HingeTwo, A1Exposure, A1HingeExposure,  # elite-relief variants
]

SEASON_LABEL = {0: "valuation season", 1: "+1 season", 2: "+2 seasons",
                3: "+3 seasons", 4: "+4 seasons", 5: "+5 seasons"}


def main() -> None:
    C.banner("run_bakeoff.py", SCRIPT_VERSION)
    bd = C.OUT_DIR / "birthdates.csv"
    if not bd.exists():
        C.log("  birthdates.csv absent -- run contract_source.py first. Stopping: a "
              "bake-off without ages would compare a different set of models.")
        return
    table = build_table(birthdate_csv=bd, verbose=False)
    C.log(f"  season table {len(table)} rows, age coverage {table['has_age'].mean():.1%}")
    C.log(f"  development seasons {C.DEV_PAGES[0]}-{C.DEV_PAGES[-1]}; "
          f"{C.CONFIRMATORY_PAGES[0]}-{C.CONFIRMATORY_PAGES[-1]} sealed and untouched")
    C.log("")

    harness = H.Harness(table)
    scored = {}
    for cls in CANDIDATES:
        m = cls()
        scored[m.name] = harness.run(m)
        C.log(f"  ran {m.name}")
    C.log("")

    # --- accuracy by how far ahead the forecast reaches ---
    C.log("AVERAGE MISS, IN WINS, BY HOW FAR AHEAD THE FORECAST REACHES")
    C.log("(lower is better; this is the average size of the miss, ignoring direction)")
    C.log("")
    hs = sorted(SEASON_LABEL)
    head = f"  {'model':<52}" + "".join(f"{SEASON_LABEL[h][:9]:>10}" for h in hs)
    C.log(head)
    C.log("  " + "-" * (len(head) - 2))
    rows = {}
    for name, s in scored.items():
        summ = H.Harness.summary(s, "h").set_index("h")["mae_war"]
        rows[name] = summ
        C.log(f"  {name:<52}" + "".join(f"{summ.get(h, np.nan):>10.3f}" for h in hs))
    C.log("")

    # --- head to head against the benchmark ---
    bench_name = BENCHMARK.name
    C.log(f"HEAD TO HEAD AGAINST THE BENCHMARK ({bench_name})")
    C.log("  Negative means the variant is BETTER. The interval is a 95% range built by")
    C.log("  resampling whole careers, because one player contributes many seasons and")
    C.log("  they are not independent. An interval that does not straddle zero is a real")
    C.log("  difference rather than noise.")
    C.log("")
    for name, s in scored.items():
        if name == bench_name:
            continue
        cmp = H.Harness.compare(scored[bench_name], s, n_boot=1000)
        parts = []
        for x in cmp.itertuples():
            mark = "*" if (x.ci_lo < 0 and x.ci_hi < 0) else ("x" if (x.ci_lo > 0 and x.ci_hi > 0) else " ")
            parts.append(f"{SEASON_LABEL[int(x.h)][:9]:>10}{x.pct:+6.1f}%{mark}")
        C.log(f"  {name}")
        C.log("     " + "  ".join(parts))
    C.log("     (* variant better, real;  x benchmark better, real;  blank = tie)")
    C.log("")

    # --- the star problem, which is what the rebuild exists to fix ---
    C.log("THE STAR PROBLEM: average miss on players coming off a big season")
    C.log("  Bias, in wins, over the valuation season through two seasons out. Positive")
    C.log("  means the model says he is better than he turns out to be. Today's model")
    C.log("  over-rates a 3+ win player by a full win, and that is the defect the")
    C.log("  rebuild exists to remove.")
    C.log("")
    tiers = ["below 0", "0 to 1", "1 to 2", "2 to 3", "3+"]
    C.log(f"  {'model':<52}" + "".join(f"{t:>10}" for t in tiers))
    C.log("  " + "-" * 102)
    tilts = {}
    for name, s in scored.items():
        t = H.Harness.summary(s[s["h"] <= 2], ["tier"]).set_index("tier")["bias_war"]
        tilts[name] = t
        C.log(f"  {name:<52}" + "".join(f"{t.get(x, np.nan):>+10.2f}" for x in tiers))
    C.log("")

    _append_register(rows, tilts, scored)
    C.log(f"  variant register now at {len(pd.read_csv(REGISTER))} entries -> {REGISTER}")
    C.write_log("bakeoff_run_log.txt")


def _append_register(rows, tilts, scored) -> None:
    """Append this run's variants to the committed register. Model names and
    summary figures only -- no player, no contract, nothing confidential."""
    today = date.today().isoformat()
    recs = []
    for name, mae in rows.items():
        rec = {"last_run": today, "model": name,
               "pages": f"{C.DEV_PAGES[0]}-{C.DEV_PAGES[-1]}",
               "n_rows": int(len(scored[name]))}
        for h in C.FITTED_HORIZONS:
            rec[f"mae_plus{h}"] = round(float(mae.get(h, np.nan)), 4)
        rec["bias_3plus"] = round(float(tilts[name].get("3+", np.nan)), 4)
        recs.append(rec)
    new = pd.DataFrame(recs)
    if REGISTER.exists():
        new = pd.concat([pd.read_csv(REGISTER), new], ignore_index=True)
        # One row per VARIANT, not per run. The register exists to count how
        # many distinct models have been inspected on the development seasons,
        # because that is the number that bears on selection bias. Re-running
        # yesterday's variant today is not a new look at the data in the sense
        # that matters, and counting it as one would inflate the tally --
        # which sounds conservative but is not: an inflated denominator makes
        # the eventual winner look more heavily vetted than it was.
        new = new.drop_duplicates(subset=["model"], keep="last")
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(REGISTER, index=False)


if __name__ == "__main__":
    main()
