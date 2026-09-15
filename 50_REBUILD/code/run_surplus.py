"""run_surplus.py -- the first dollar values out of the rebuilt chain."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from contract_price_model import contract_sample, attach_forecasts
from production_currency import ProductionCurrency
from player_season_table import build as build_table
from ability_forecast import A1AgingParticipationImputedNC
from run_phase4_decisions import prep

SCRIPT_VERSION = "1.0"


def main() -> None:
    C.banner("run_surplus.py", SCRIPT_VERSION)
    table = build_table(birthdate_csv=C.OUT_DIR / "birthdates.csv", verbose=False)
    d = prep(attach_forecasts(contract_sample(), A1AgingParticipationImputedNC,
                              table, verbose=False))

    # Rolling: each contract priced on a line fitted only to deals signed
    # before its own start season.
    out = []
    for yr in range(2018, 2026):
        te = d[d["start_yr"] == yr]
        if not len(te):
            continue
        for mode in ("in", "free"):
            cur = ProductionCurrency(mode).fit(d, before=yr)
            if cur.coef_ is None:
                continue
            v = cur.value(te)
            te = te.assign(**{f"value_{mode}": v})
        te["cost"] = ProductionCurrency("in").cost(te)
        out.append(te)
    r = pd.concat(out, ignore_index=True)
    r["surplus_in"] = r["value_in"] - r["cost"]
    r["surplus_free"] = r["value_free"] - r["cost"]

    C.log(f"  {len(r)} contracts priced, 2018-2025 starts, each on a line fitted")
    C.log("  only to deals signed before its own start season")
    C.log("")
    C.log("  SURPLUS UNDER THE ADOPTED CURRENCY (term-in), $M over the whole deal.")
    C.log("  Positive means the club paid less than the average club paid for a")
    C.log("  comparable forecast. It is deviation from the market, not profit --")
    C.log("  the line is fitted to observed contracts, so the average is near zero")
    C.log("  by construction.")
    C.log("")
    tiers = pd.cut(r["war_per_season"], [-np.inf, 0, 0.5, 1.0, 2.0, np.inf],
                   labels=["below 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2+"])
    C.log(f"  {'forecast':<10}{'n':>6}{'mean $M':>10}{'median':>9}{'sd':>8}"
          f"{'% positive':>12}")
    for t, g in r.groupby(tiers, observed=True):
        C.log(f"  {str(t):<10}{len(g):>6}{g['surplus_in'].mean()/1e6:>10.2f}"
              f"{g['surplus_in'].median()/1e6:>9.2f}{g['surplus_in'].std()/1e6:>8.2f}"
              f"{100*(g['surplus_in']>0).mean():>11.0f}%")
    C.log(f"  {'ALL':<10}{len(r):>6}{r['surplus_in'].mean()/1e6:>10.2f}"
          f"{r['surplus_in'].median()/1e6:>9.2f}{r['surplus_in'].std()/1e6:>8.2f}"
          f"{100*(r['surplus_in']>0).mean():>11.0f}%")
    C.log("")
    C.log("  BY TERM -- where the term-in choice does its work:")
    C.log(f"  {'term':<7}{'n':>6}{'term-in $M':>13}{'term-free $M':>15}{'difference':>13}")
    for L, g in r.groupby("length"):
        if len(g) < 20:
            continue
        C.log(f"  {int(L):<7}{len(g):>6}{g['surplus_in'].mean()/1e6:>13.2f}"
              f"{g['surplus_free'].mean()/1e6:>15.2f}"
              f"{(g['surplus_in']-g['surplus_free']).mean()/1e6:>13.2f}")
    C.log("")
    C.log("  The sensitivity is reported, not discarded: under term-free the same")
    C.log("  contracts would show the differences above, and long deals for good")
    C.log("  players are where the two answers diverge.")
    r.to_csv(C.out_path("contract_surplus.csv"), index=False)
    C.log(f"  wrote {C.OUT_DIR/'contract_surplus.csv'}")
    C.write_log("surplus_run_log.txt")


if __name__ == "__main__":
    main()
