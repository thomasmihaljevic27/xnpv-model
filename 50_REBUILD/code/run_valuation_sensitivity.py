"""run_valuation_sensitivity.py -- does the conclusion move when the forecast does?

EXPERIMENTAL (50_REBUILD). Development start years only; the reserved market
cohorts are refused by the guard, not avoided by habit.

WHY THIS RUN EXISTS
    The forecast has measured errors that concentrate on stars and on young
    players at long horizons, and three rounds of diagnostics could not
    separate their causes. That leaves one question worth asking, and it is not
    another diagnostic: DOES ANY OF IT CHANGE THE ANSWER?

    The thesis does not claim to forecast a player. It claims that certain
    categories of asset are systematically mispriced. If that claim holds under
    every forecast a reasonable person would accept -- including the one the
    live model uses today -- then the forecast's errors are a limitation to
    state, and the argument survives them. If the claim depends on which
    forecast is used, that is a finding about the thesis, and no amount of
    calibration work would have found it.

WHAT IS HELD FIXED AND WHAT VARIES
    Fixed: the contracts, the cost side, the signing-dated rolling protocol,
    the discounting, the cap path, and the development seal.

    Varies: the forecast, across five, from the live chain to the adopted
    candidate. And the term framing, across the two the project has argued
    about, because that is the other axis where the answer is known to move.

EACH FORECAST GETS ITS OWN PRICE LINE, AND THAT IS DELIBERATE
    The currency is fitted on the forecast, so a world with a different
    forecast has a different price of a forecast win. Refitting per forecast
    is what makes each column a complete alternative model rather than one
    model's forecast priced on another's market.

    It also means the LEVEL is not comparable across columns: the line is
    fitted to observed contracts, so the average contract prices near zero
    surplus in every column by construction. What is comparable, and what the
    thesis actually rests on, is the GRADIENT -- which categories sit above
    and below zero, and in what order. That is what the agreement table reads.

WHAT THIS IS NOT
    Not a back-test. Nothing is scored against a realised outcome here and no
    trade is priced. It asks whether the model's own valuation ORDERING is
    stable under a change of forecast, which is the precondition for a
    back-test result meaning anything, not a substitute for one.

    Not a search for the best forecast either. Four of the five columns are
    known to be worse than the fifth on error. They are here because a
    conclusion that only survives under the winner is not a conclusion.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from contract_price_model import contract_sample, attach_forecasts
from production_currency import ProductionCurrency
from player_season_table import build as build_table, birthdate_source
from run_phase4_decisions import prep
from ability_forecast import (A0Production, A1HingeExposure,
                              A1AgingParticipationImputedNC, A1Calibrated3Aging)
from production_adapter import ProductionChain

SCRIPT_VERSION = "1.0"

# Five forecasts, named for what they are, running from what the model does
# today to what the rebuild proposes.
#
# THE COMPONENT MODEL IS ABSENT AND NOT BY CHOICE. A2AgingParticipationImputed
# raises AttributeError on fitted_horizons_ inside its own fit, before any
# contract is priced, so the variant the register carries as a live candidate
# cannot currently be run through the contract path at all. That is a defect
# in the variant, found here and recorded rather than repaired inside a runner
# that is about something else.
FORECASTS = [
    ("today's live chain", ProductionChain),
    ("trailing blend, carried flat", A0Production),
    ("calibrated total + aging + participation", A1AgingParticipationImputedNC),
    # NO PARTICIPATION IN THIS ONE, deliberately. The participation model
    # is the half with a measured subgroup miscalibration, so a column that
    # leaves it out says whether the valuation ordering depends on it.
    ("calibrated total + aging, NO participation", A1Calibrated3Aging),
    ("the adopted candidate", A1HingeExposure),
]

TIER_EDGES = [-np.inf, 0, 0.5, 1.0, 2.0, np.inf]
TIER_NAMES = ["below 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2+"]


def price(d: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Every contract priced on a line fitted only to deals signed before it.

    The quarter cut and the rolling rule are `run_surplus.py`'s, reproduced
    rather than imported so this runner cannot be changed by an edit to that
    one, and vice versa -- the two answer different questions on the same
    protocol and a shared helper would couple them.
    """
    out = []
    for cut, te in d.groupby("cut"):
        cur = ProductionCurrency(mode).fit(d, before_date=cut)
        if cur.coef_ is None:
            continue
        te = te.copy()
        te["value"] = cur.value(te)
        te["cost"] = ProductionCurrency("in").cost(te)
        te["surplus"] = te["value"] - te["cost"]
        out.append(te)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main() -> None:
    C.banner("run_valuation_sensitivity.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    table = build_table(birthdate_csv=path, verbose=False)
    C.log(f"  birthdates: {how}")
    C.log("")

    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_valuation_sensitivity")
    C.log(f"  {len(sample)} contracts in the sample, development start years "
          f"{min(cohorts)}-{max(cohorts)} only")
    C.log("")

    # ---- who survives to be priced, and who does not ----------------------
    # THE TOP TIER LIVES ON LONG DEALS, so a term-selective loss is not a
    # footnote to a result about the top tier -- it is part of it.
    elig = sample[(~sample["start_yr"].isin(C.CONFIRMATORY_START_YEARS))
                  & (sample["signed"] >= pd.Timestamp("2015-07-01"))]
    C.log(f"  {len(elig)} contracts eligible on the development cohorts.")
    C.log("")

    results: dict[str, pd.DataFrame] = {}
    for label, cls in FORECASTS:
        t0 = time.time()
        d = prep(attach_forecasts(sample, cls, table, verbose=False))
        d = d[d["start_yr"].isin(cohorts)].copy()
        d["cut"] = d["signed"].dt.to_period("Q").dt.start_time
        r = price(d, "in")
        r_free = price(d, "free")
        r["surplus_free"] = r_free.set_index(["pkey", "start_yr"]).reindex(
            pd.MultiIndex.from_arrays([r["pkey"], r["start_yr"]]))["surplus"].to_numpy()
        results[label] = r
        C.log(f"  {label:<44}{len(r):>6} contracts priced  "
              f"({time.time() - t0:.0f}s)")
    C.log("")

    # EVERY COLUMN ON THE SAME CONTRACTS. A forecast that declines to answer
    # for a contract drops it, and comparing a table built on 1,900 contracts
    # with one built on 1,700 compares two samples as much as two forecasts.
    keys = None
    for r in results.values():
        k = set(zip(r["pkey"], r["start_yr"]))
        keys = k if keys is None else (keys & k)
    C.log(f"  {len(keys)} contracts answered by all five forecasts; every table")
    C.log("  below is on exactly those, so no column is scored on an easier set.")
    for label in results:
        r = results[label]
        m = [(p, s) in keys for p, s in zip(r["pkey"], r["start_yr"])]
        results[label] = r[m].sort_values(["pkey", "start_yr"]).reset_index(drop=True)
    C.log("")

    C.log("TERM COVERAGE. A contract is priced only if the forecast reaches")
    C.log("every season of its term, and the pages early in the window do not")
    C.log("reach as far as a long deal needs. The loss is not uniform.")
    C.log("")
    kept = results["the adopted candidate"]
    ea = elig["length"].value_counts()
    ka = kept["length"].value_counts()
    C.log(f"    {'term':<8}{'eligible':>10}{'priced':>9}{'kept':>8}")
    for L in sorted(set(ea.index) | set(ka.index)):
        C.log(f"    {int(L)} yr{'':<3}{int(ea.get(L, 0)):>10}{int(ka.get(L, 0)):>9}"
              f"{100 * ka.get(L, 0) / max(ea.get(L, 1), 1):>7.0f}%")
    C.log(f"    {'all':<8}{len(elig):>10}{len(kept):>9}"
          f"{100 * len(kept) / len(elig):>7.0f}%")
    C.log("")
    C.log("  Roughly two thirds of one-year deals survive and about half of the")
    C.log("  six- and eight-year ones. Long contracts are under-represented by")
    C.log("  about a quarter relative to short ones, and they are where the top")
    C.log("  tier lives. Every figure below inherits that.")
    C.log("")

    # ---- the gradient, forecast by forecast -------------------------------
    C.log("SURPLUS BY FORECAST TIER, $M over the whole deal, term-in currency.")
    C.log("Positive means the club paid less than the average club paid for a")
    C.log("comparable forecast. The tier is each column's OWN forecast, because")
    C.log("a claim about 'stars' means the players that model calls stars.")
    C.log("")
    C.log("The LEVEL is not comparable across columns -- each line is fitted to")
    C.log("observed contracts, so the average prices near zero by construction.")
    C.log("The GRADIENT is, and the thesis rests on the gradient.")
    C.log("")
    grid = {}
    C.log(f"  {'forecast':<44}" + "".join(f"{t:>11}" for t in TIER_NAMES))
    for label, r in results.items():
        tiers = pd.cut(r["war_per_season"], TIER_EDGES, labels=TIER_NAMES)
        means = r.groupby(tiers, observed=False)["surplus"].mean() / 1e6
        grid[label] = means
        C.log(f"  {label:<44}" + "".join(
            f"{means.get(t, np.nan):>11.2f}" for t in TIER_NAMES))
    C.log("")
    C.log(f"  {'n per tier (adopted candidate)':<44}" + "".join(
        f"{int(v):>11}" for v in pd.cut(results['the adopted candidate']['war_per_season'],
                                        TIER_EDGES, labels=TIER_NAMES)
        .value_counts().reindex(TIER_NAMES).fillna(0)))
    C.log("")

    # ---- does the conclusion hold? ----------------------------------------
    C.log("DOES THE CONCLUSION HOLD? Three questions a reader would ask.")
    C.log("")
    g = pd.DataFrame(grid).T[TIER_NAMES]
    signs = np.sign(g)
    agree = (signs.nunique(axis=0) == 1)
    C.log("  1. SIGN. Does each tier sit on the same side of zero in all five?")
    for t in TIER_NAMES:
        vals = g[t].to_numpy()
        C.log(f"     {t:<10}{'same sign' if agree[t] else 'SIGN FLIPS':<12}"
              f"range {np.nanmin(vals):>+7.2f} to {np.nanmax(vals):>+7.2f} $M")
    C.log("")
    C.log("  2. ORDER. Is the ranking of tiers by surplus the same in all five?")
    orders = {lab: tuple(g.loc[lab].sort_values().index) for lab in g.index}
    base = orders["the adopted candidate"]
    for lab, o in orders.items():
        C.log(f"     {lab:<44}{'same order' if o == base else 'DIFFERENT'}")
    C.log(f"     order, worst to best: {' < '.join(base)}")
    C.log("")
    C.log("  3. GRADIENT. Does surplus rise with forecast production, which is")
    C.log("     the claim the thesis actually makes?")
    for lab in g.index:
        v = g.loc[lab].to_numpy()
        C.log(f"     {lab:<44}{'rises' if v[-1] > v[0] else 'falls':<8}"
              f"{v[0]:>+8.2f} at the bottom, {v[-1]:>+8.2f} at the top")
    C.log("")

    # ---- the term framing, the other axis ---------------------------------
    C.log("THE TERM FRAMING, which is the other axis the answer is known to move")
    C.log("on. Same contracts, same forecasts, the currency pricing a run of")
    C.log("one-year deals instead of the term the player was given.")
    C.log("")
    C.log(f"  {'forecast':<44}{'top tier, term-in':>19}{'term-free':>12}{'difference':>13}")
    for label, r in results.items():
        tiers = pd.cut(r["war_per_season"], TIER_EDGES, labels=TIER_NAMES)
        top = r[tiers == "2+"]
        if not len(top):
            continue
        C.log(f"  {label:<44}{top['surplus'].mean()/1e6:>19.2f}"
              f"{top['surplus_free'].mean()/1e6:>12.2f}"
              f"{(top['surplus'] - top['surplus_free']).mean()/1e6:>13.2f}")
    C.log("")

    # ---- contract by contract ---------------------------------------------
    C.log("AND CONTRACT BY CONTRACT, against today's live chain. A category")
    C.log("that holds on average can still be built out of contracts the two")
    C.log("models disagree about completely.")
    C.log("")
    live = results["today's live chain"].set_index(["pkey", "start_yr"])["surplus"]
    C.log(f"  {'forecast':<44}{'correlation':>13}{'same sign':>11}"
          f"{'mean |gap| $M':>15}")
    for label, r in results.items():
        if label == "today's live chain":
            continue
        s = r.set_index(["pkey", "start_yr"])["surplus"].reindex(live.index)
        ok = s.notna() & live.notna()
        C.log(f"  {label:<44}{s[ok].corr(live[ok]):>13.3f}"
              f"{100*(np.sign(s[ok]) == np.sign(live[ok])).mean():>10.0f}%"
              f"{(s[ok]-live[ok]).abs().mean()/1e6:>15.2f}")
    C.log("")

    out = pd.concat([r.assign(forecast=lab) for lab, r in results.items()],
                    ignore_index=True)
    out.to_csv(C.out_path("valuation_sensitivity.csv"), index=False)
    C.log(f"  wrote {C.out_path('valuation_sensitivity.csv').name}")
    C.write_log("valuation_sensitivity_run_log.txt")


if __name__ == "__main__":
    main()
