"""run_player_comparison.py -- named players, both models, side by side.

EXPERIMENTAL (50_REBUILD). A demonstration, not a test: no model is selected
or tuned here, and nothing in it feeds a decision.

WHY NAMED PLAYERS
    Everything so far has been a mean over thousands of player-seasons. That
    is how a model should be judged and it is a terrible way to understand one.
    A hockey person reading "the star bias moved from +0.999 to -0.365" learns
    less than they do from seeing what the two models said about Milan Lucic in
    July 2016.

VALUATION DATES ARE ALL 2015-2021. The 2022-2025 seasons are the confirmatory
holdout and are not touched, here or anywhere else, until the one run at the
end of Phase 5. Several obvious cases -- Eichel to Vegas, the recent extensions
-- are therefore absent by design rather than by oversight.

WHAT IS COMPARED
    Production value over the contract term, in dollars, under two chains:

    THE LIVE CHAIN. Production's own forecast, through production's locked aging
    curve, its negative-anchor rule and its exit-hazard survival, by way of
    production_adapter.ProductionChain. The earlier version of this file
    compared against the flat benchmark and called it today's chain, which it
    is not: the benchmark drops the aging path and the survival weighting.

    THE REBUILT CHAIN. The adopted candidate from the variant register: three-
    season window, additive aging with the survivorship correction,
    participation, and the hinge-and-evidence interaction; since 2026-09-23 its
    participation also reads visible contract status (run_npv_simulation.LEADER).

    BOTH PRICED ON ONE CURRENCY. A single censored price line is fitted per
    signing quarter, on contracts signed strictly before that quarter, and the
    same fitted line prices both forecasts. Fitting a line to each forecast
    separately, which this file used to do, returns different coefficients and
    makes the printed difference a forecast change and a price change added
    together.

    DATES AND DISCOUNTING. A valuation uses the cap ceilings announced by its
    own signing date and grows the rest at 3%; value and cost are both
    discounted from the signing rather than from the contract's first season.
    The earlier version summed realised ceilings with no discounting at all and
    described the cancellation of growth against discount as a reason it did
    not need to.

    This is the VALUE side only. Cost, retention and trade-side accounting are
    not in it.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from production_currency import ProductionCurrency
from run_phase4_decisions import prep
import forecast_harness as H
import information_set as ISET
from player_season_table import build as build_table, norm_name
# The adopted skater leader, from the one switch, not pinned by name.
from run_npv_simulation import LEADER

SCRIPT_VERSION = "1.5"

# The locked production market rate (D20 Tobit, skaters, 2018-2025 starts).
PROD_ALPHA, PROD_BETA_F, PROD_BETA_D_ADD = 0.01324782, 0.02123229, 0.00287028

# (raw WAR.csv name, position, valuation year, term, what it is)
CASES = [
    # --- contracts the market later regretted ---
    ("Milan Lucic", "F", 2016, 7, "UFA deal, Edmonton"),
    ("Loui Eriksson", "F", 2016, 6, "UFA deal, Vancouver"),
    ("David Backes", "F", 2016, 5, "UFA deal, Boston"),
    ("Andrew Ladd", "F", 2016, 7, "UFA deal, NY Islanders"),
    ("Brent Seabrook", "D", 2016, 8, "extension, Chicago"),
    ("Dion Phaneuf", "D", 2016, 3, "carried term, Ottawa"),
    ("Jeff Skinner", "F", 2019, 8, "extension, Buffalo"),
    ("Oliver Ekman-Larsson", "D", 2019, 8, "extension, Arizona"),
    ("Erik Gudbranson", "D", 2018, 3, "extension, Vancouver"),
    ("Tyler Myers", "D", 2019, 5, "UFA deal, Vancouver"),
    # --- contracts that looked like bargains ---
    ("Nathan MacKinnon", "F", 2016, 7, "extension, Colorado"),
    ("Johnny Gaudreau", "F", 2016, 6, "extension, Calgary"),
    ("Nikita Kucherov", "F", 2019, 8, "extension, Tampa Bay"),
    ("Brad Marchand", "F", 2017, 8, "extension, Boston"),
    ("Mark Stone", "F", 2019, 8, "extension, Vegas"),
    ("Roope Hintz", "F", 2021, 3, "bridge, Dallas"),
    ("Jordan Binnington", "G", 2019, 2, "bridge, St Louis"),
    # --- the very top of the market ---
    ("Connor McDavid", "F", 2018, 8, "extension, Edmonton"),
    ("Auston Matthews", "F", 2019, 5, "extension, Toronto"),
    ("Mitch Marner", "F", 2019, 6, "extension, Toronto"),
    ("Artemi Panarin", "F", 2019, 7, "UFA deal, NY Rangers"),
    ("Sebastian Aho", "F", 2019, 5, "offer sheet, Carolina"),
    ("Drew Doughty", "D", 2019, 8, "extension, Los Angeles"),
    ("Erik Karlsson", "D", 2019, 8, "UFA deal, San Jose"),
    ("Tyler Seguin", "F", 2019, 8, "extension, Dallas"),
    # --- memorable trades, valued at the trade ---
    ("Taylor Hall", "F", 2016, 4, "traded to New Jersey"),
    ("P.K. Subban", "D", 2016, 6, "traded to Nashville"),
    ("Shea Weber", "D", 2016, 10, "traded to Montreal"),
    ("Matt Duchene", "F", 2017, 2, "traded to Ottawa"),
    ("Ryan O'Reilly", "F", 2018, 5, "traded to St Louis"),
    ("Jack Eichel", "F", 2018, 8, "extension, Buffalo"),
    ("Dougie Hamilton", "D", 2018, 3, "traded to Carolina"),
]


def price_on_one_currency(rebuilt: pd.DataFrame, live: pd.DataFrame):
    """Price two forecast tables on ONE fitted currency per signing quarter.

    The table above this says the difference between its two columns is the
    forecast rather than the price line. The first version of this code did not
    do that: it called ProductionCurrency separately on each forecast table, and
    since the tables carry different forecast regressors the two fits returned
    different coefficients in all 18 comparable quarters. The printed difference
    was therefore a forecast change and a pricing change added together, while
    the text claimed otherwise.

    THE REFERENCE IS THE REBUILT TABLE, declared rather than implied. The
    currency is the market's price for forecast production, and the rebuilt
    forecast is the one whose production is being valued; fitting on it and then
    applying the same fitted object to the live forecast asks what the market
    would pay for each forecast at one price. Fitting on the live table instead
    would answer the same question through a different reference and is a
    sensitivity worth running, not a second answer to be averaged with this one.

    Returns (priced, coefs): a dict of label to priced rows, and the fitted
    coefficient vector per quarter, so a test can confirm that one vector
    served both valuations.
    """
    ref = rebuilt.copy()
    other = live.copy()
    for d in (ref, other):
        d["cut"] = d["signed"].dt.to_period("Q").dt.start_time

    priced = {"rebuilt": [], "live": []}
    coefs: dict = {}
    for cut in sorted(set(ref["cut"]) | set(other["cut"])):
        cur = ProductionCurrency("in").fit(ref, before_date=cut)
        if cur.coef_ is None:
            continue
        coefs[cut] = np.asarray(cur.coef_, dtype=float).copy()
        for label, d in (("rebuilt", ref), ("live", other)):
            te = d[d["cut"] == cut].copy()
            if te.empty:
                continue
            te["value"] = cur.value(te)
            te["cost"] = cur.cost(te)
            priced[label].append(te)
    return ({k: (pd.concat(v, ignore_index=True) if v else pd.DataFrame())
             for k, v in priced.items()}, coefs)


def main() -> None:
    C.banner("run_player_comparison.py", SCRIPT_VERSION)
    C.log("  ROUTED THROUGH THE REPAIRED VALUATION PATH (2026-09-15).")
    C.log("  The previous version fitted its price line on the whole contract")
    C.log("  sample including signings after the dates it illustrated, compared")
    C.log("  against the flat benchmark while calling it today's chain, and summed")
    C.log("  realised cap ceilings with no discounting. Every one of those is a")
    C.log("  defect the rest of the tree has already had repaired, so the table")
    C.log("  now uses the same API as run_surplus: a currency fitted only on deals")
    C.log("  signed before each contract's own signing quarter, a cap path known")
    C.log("  at the signing, discounting from the signing, and the LIVE CHAIN as")
    C.log("  the comparator rather than the flat benchmark.")
    C.log("")

    table = build_table(birthdate_csv=C.OUT_DIR / "birthdates.csv", verbose=False)

    # BOTH SIDES PRICED ON THE SAME CURRENCY. The question this table asks is
    # what the two FORECASTS are worth, so the price line has to be held
    # constant across them or the difference mixes a forecast change with a
    # pricing change. The live chain's forecast is attached the same way the
    # rebuilt one is, through the same harness and the same contract sample.
    from contract_price_model import contract_sample, attach_forecasts
    from production_adapter import ProductionChain

    sample = contract_sample()
    dev = [y for y in sorted(sample["start_yr"].dropna().unique().astype(int))
           if y not in C.CONFIRMATORY_START_YEARS]
    sample = sample[sample["start_yr"].isin(C.check_market_cohorts(
        dev, "run_player_comparison"))]

    rebuilt = prep(attach_forecasts(sample, LEADER, table, verbose=False))
    live = prep(attach_forecasts(sample, ProductionChain, table, verbose=False))

    priced, coefs = price_on_one_currency(rebuilt, live)

    # The earliest quarter with enough prior signings to fit a currency on.
    # Dating the fit at the signing is what creates this boundary: before it
    # there is no market to have learned from yet.
    first_priced = min(
        (d["signed"].min() for d in priced.values() if len(d)), default=None)

    rows, missing = [], []
    for raw, pos, yr, term, note in CASES:
        pk = norm_name(raw) + "|" + pos
        got = {}
        for label, d in priced.items():
            m = d[(d["pkey"] == pk) & (d["start_yr"] == yr)]
            if len(m):
                got[label] = m.iloc[0]
        if len(got) < 2:
            in_sample = ((sample["pkey"] == pk) & (sample["start_yr"] == yr)).any()
            sgn = sample.loc[(sample["pkey"] == pk) & (sample["start_yr"] == yr), "signed"]
            if in_sample and first_priced is not None and len(sgn) and sgn.iloc[0] < first_priced:
                why = "signed before the market has enough history to fit a price line"
            elif in_sample:
                why = "no full-term forecast on its page"
            else:
                why = "not in the repaired contract sample"
            missing.append((raw, note, yr, why))
            continue
        r_new, r_old = got["rebuilt"], got["live"]
        rows.append({
            "player": raw, "note": note, "year": int(yr),
            "term": int(r_new["length"]),
            "war_new": float(r_new["war_total"]),
            "war_live": float(r_old["war_total"]),
            "new": float(r_new["value"]) / 1e6,
            "live": float(r_old["value"]) / 1e6,
            "cost": float(r_new["cost"]) / 1e6,
            "extrap": int(r_new.get("n_years_extrapolated", 0)),
        })

    if not rows:
        C.log("  no named case survived the repaired sample; nothing to show")
        return
    r = pd.DataFrame(rows).sort_values("year")
    r["surplus_new"] = r["new"] - r["cost"]
    r["surplus_live"] = r["live"] - r["cost"]

    C.log("  FORECAST PRODUCTION PRICED OVER THE TERM, $M, discounted to the")
    C.log("  signing. ONE currency is fitted per signing quarter, on the rebuilt")
    C.log("  forecasts, and the same fitted line prices both columns, so the")
    C.log("  difference between them is the forecast and not the price line.")
    C.log("  Surplus is value minus the")
    C.log("  discounted cap hit, and is deviation from the market rather than")
    C.log("  profit: the line is fitted to observed contracts.")
    C.log("")
    C.log(f"  {'player':<22}{'yr':>5}{'tm':>4}{'live $M':>9}{'new $M':>9}"
          f"{'cost $M':>9}{'surp live':>11}{'surp new':>10}")
    for x in r.itertuples():
        C.log(f"  {x.player:<22}{x.year:>5}{x.term:>4}{x.live:>9.1f}{x.new:>9.1f}"
              f"{x.cost:>9.1f}{x.surplus_live:>11.1f}{x.surplus_new:>10.1f}")
    C.log("")
    n_ex = int(r["extrap"].sum())
    if n_ex:
        C.log(f"  {n_ex} contract seasons in this table are extrapolated beyond")
        C.log("  what their page fitted. See predict_beyond_fit for the rule and")
        C.log("  its measured bias.")
    if missing:
        C.log(f"  {len(missing)} of {len(CASES)} named cases are NOT shown, and they")
        C.log("  are not missing at random. Dating the price line at the signing")
        C.log("  means the earliest contracts have no market to have learned from:")
        C.log(f"  the first signing this tree can price is {first_priced.date()}, so the")
        C.log("  whole 2016 group goes, and those are the most familiar cases in the")
        C.log("  list. That is the honest cost of removing the look-ahead rather")
        C.log("  than a gap to be filled by widening the training window again.")
        for raw, note, yr, why in missing:
            C.log(f"    {raw} ({yr}, {note}): {why}")
    C.log("")
    C.log("  wrote " + str(C.out_path("named_player_comparison.csv")))
    r.to_csv(C.out_path("named_player_comparison.csv"), index=False)


if __name__ == "__main__":
    main()
