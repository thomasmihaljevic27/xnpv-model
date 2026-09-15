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

    TODAY'S CHAIN. Trailing two seasons of WAR blended 60/40, carried flat
    across the term, every player assumed to play every season, priced on the
    locked D20 market rate (alpha 0.01324782, beta 0.02123229, defence premium
    0.00287028), floored at the league minimum.

    THE REBUILT CHAIN. The adopted leader -- three-season window, additive
    aging with the survivorship correction, participation -- priced on the
    adopted log currency, floored at the same minimum.

    Values are in cap share per season summed over the term and converted at
    each season's published ceiling. In cap-share units the cap's growth and
    the discount rate largely cancel, which is the project's existing
    convention; no separate discount factor is applied, and that is a
    simplification rather than a claim.

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
import forecast_harness as H
import information_set as ISET
from player_season_table import build as build_table, norm_name
from ability_forecast import A0Production, A1HingeExposure

SCRIPT_VERSION = "1.1"

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


def prod_value(war_per_season, is_d, years, start_yr):
    """Today's chain: the flat trailing anchor on the locked linear rate."""
    share = PROD_ALPHA + PROD_BETA_F * war_per_season + (
        PROD_BETA_D_ADD * war_per_season if is_d else 0.0)
    total = 0.0
    for k in range(years):
        y = start_yr + k
        floor = (C.LEAGUE_MIN_SALARY.get(y, 775_000)
                 / C.CAP_CEILING.get(y, C.CAP_CEILING[2025]))
        total += max(share, floor) * C.CAP_CEILING.get(y, C.CAP_CEILING[2025])
    return total


def main() -> None:
    C.banner("run_player_comparison.py", SCRIPT_VERSION)
    C.log("  Valuation dates are 1 July of the stated year. All within the")
    C.log("  development window 2015-2021; the confirmatory seasons are sealed.")
    C.log("")
    table = build_table(birthdate_csv=C.OUT_DIR / "birthdates.csv", verbose=False)

    # the log currency, fitted once on contracts before 2015 is not possible,
    # so it is fitted on the whole contract sample and that is stated.
    from contract_price_model import contract_sample, attach_forecasts, tobit, predict_tobit
    from run_phase4_decisions import prep
    from run_curvature_test import add_shapes, BASE
    d = add_shapes(prep(attach_forecasts(contract_sample(), A1HingeExposure,
                                         table, verbose=False)))
    cur_b, _, _ = tobit(d[["war_log"] + BASE].to_numpy(float),
                        d["cap_share"].to_numpy(float),
                        d["floor_share"].to_numpy(float))
    C.log(f"  log currency fitted on {len(d)} signing-dated contracts")
    C.log("")

    rows = []
    for raw, pos, yr, term, note in CASES:
        pkey = norm_name(raw) + "|" + pos
        if pkey not in set(table["pkey"]):
            rows.append({"player": raw, "note": note, "year": yr, "miss": True})
            continue
        iset = ISET.build(table, ISET.decision_date_for_page(yr), t0=yr)
        subs = H.subjects_at(iset)
        sub = subs[subs["pkey"] == pkey]
        if sub.empty:
            rows.append({"player": raw, "note": note, "year": yr, "miss": True})
            continue

        # THE WHOLE TERM, or nothing. This used to be min(term, 8), which
        # silently repriced Shea Weber's ten remaining years as eight and
        # reported the result in a column headed by the truncated number. The
        # truncation did not tilt the comparison, because the benchmark below
        # is priced over the same count, but it answered a question nobody
        # asked and it hid that years seven and eight were already being
        # served by an unfitted participation probability.
        hs = list(range(term))
        unfitted = [h for h in hs if h not in set(C.FITTED_HORIZONS)]
        assert not unfitted, (
            f"{raw} has {term} years of term, so pricing him needs horizons "
            f"{unfitted} that no model is fitted to. Extend the fitted range "
            "to the terms this table prices, or declare and test an "
            "extrapolation, or drop the player from the table and say so. "
            "Do not reprice a ten-year contract as an eight-year one.")
        new = A1HingeExposure()
        new.fit(iset.seasons, before=yr)
        pn = new.predict(iset, sub, hs)
        pn["war"] = pn["p_play"] * pn["rate_82"] * pn["gp_share"]

        old = A0Production()
        old.fit(iset.seasons, before=yr)
        po = old.predict(iset, sub, hs)
        po["war"] = po["p_play"] * po["rate_82"] * po["gp_share"]

        anchor = float(po["rate_82"].iloc[0])      # the flat trailing anchor
        v_old = prod_value(anchor, pos == "D", len(hs), yr)

        # NEW CHAIN. Price each season's forecast production on the log
        # currency, WITH TERM HELD NEUTRAL.
        #
        # This is a correction. The first version passed each contract's actual
        # term into the price line, which put the term coefficient into what
        # was labelled a production value -- and the term coefficient is a
        # PRICE fact, not a production one. It priced Brent Seabrook's 0.20
        # forecast wins at $47.2M, because an eight-year deal carries eight
        # years of term premium whether or not the player produces anything.
        #
        # Term-in does not mean a premium added per season. It means the
        # replacement counterfactual is a player signed for the remaining term
        # rather than re-signed each year, which belongs in the replacement
        # baseline and in the contract-price model. Today's chain has no term
        # term at all, so a like-for-like production comparison has to hold
        # term neutral on both sides. The premium is reported separately below,
        # where it can be seen rather than smuggled.
        v_new = 0.0
        for k, w in enumerate(pn["war"].to_numpy(float)):
            X = np.array([[np.log1p(max(w, 0)), 1.0, 0.0, 0.0,
                           1.0 if pos == "D" else 0.0, 1.0,
                           float(pn["war"].iloc[0])]])
            y = yr + k
            floor = (C.LEAGUE_MIN_SALARY.get(y, 775_000)
                     / C.CAP_CEILING.get(y, C.CAP_CEILING[2025]))
            v_new += max(float(predict_tobit(cur_b, X)[0]), floor) * \
                C.CAP_CEILING.get(y, C.CAP_CEILING[2025])

        # the term premium, priced separately so it is visible
        Xt = np.array([[np.log1p(max(float(pn["war"].mean()), 0)), float(term),
                        0.0, 0.0, 1.0 if pos == "D" else 0.0,
                        1.0 if term == 1 else 0.0, float(pn["war"].iloc[0])]])
        X1 = Xt.copy(); X1[0, 1] = 1.0; X1[0, 5] = 1.0
        prem = (float(predict_tobit(cur_b, Xt)[0]) - float(predict_tobit(cur_b, X1)[0])) \
            * sum(C.CAP_CEILING.get(yr + k, C.CAP_CEILING[2025]) for k in range(len(hs)))

        rows.append({"player": raw, "note": note, "year": yr, "term": len(hs),
                     "premium": prem / 1e6,
                     "anchor": anchor, "war_new": float(pn["war"].sum()),
                     "old": v_old / 1e6, "new": v_new / 1e6,
                     "diff": (v_new - v_old) / 1e6, "miss": False})

    r = pd.DataFrame(rows)
    got, missed = r[~r["miss"]], r[r["miss"]]
    C.log("  PRODUCTION VALUE OVER THE TERM, $M. 'anchor' is the flat trailing")
    C.log("  number today's chain carries forward; 'new wins' is the rebuilt")
    C.log("  chain's total forecast production over the same years.")
    C.log("")
    C.log(f"  {'player':<22}{'yr':>5}{'yrs':>4}{'anchor':>8}{'new wins':>10}"
          f"{'TODAY $M':>10}{'NEW $M':>9}{'diff':>9}{'term':>8}  what it was")
    for grp, lab in [(got.iloc[:10], "CONTRACTS THE MARKET REGRETTED"),
                     (got.iloc[10:17], "CONTRACTS THAT LOOKED LIKE BARGAINS"),
                     (got.iloc[17:25], "THE TOP OF THE MARKET"),
                     (got.iloc[25:], "MEMORABLE TRADES")]:
        if grp.empty:
            continue
        C.log("")
        C.log(f"  -- {lab} --")
        for x in grp.itertuples():
            C.log(f"  {x.player:<22}{x.year:>5}{int(x.term):>4}{x.anchor:>8.2f}"
                  f"{x.war_new:>10.2f}{x.old:>10.1f}{x.new:>9.1f}"
                  f"{x.diff:>+9.1f}{x.premium:>8.1f}  {x.note}")
    C.log("")
    if len(missed):
        C.log(f"  not valued ({len(missed)}): "
              + ", ".join(f"{m.player} ({m.year})" for m in missed.itertuples()))
        C.log("  -- no qualifying NHL history at that date, or a goalie, which this")
        C.log("     skater chain does not price.")
    C.log("")
    C.log(f"  across {len(got)} players the rebuilt chain values production "
          f"${got['diff'].mean():+,.1f}M differently on average, "
          f"${got['diff'].abs().mean():,.1f}M in absolute terms")
    got.to_csv(C.out_path("player_comparison.csv"), index=False)
    C.write_log("player_comparison_run_log.txt")


if __name__ == "__main__":
    main()
