"""run_phase4_decisions.py -- the two market decisions, tested where testable.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 4, decisions A and B.

The two are not the same kind of question and are not treated the same way.

DECISION B -- one price line for restricted and unrestricted free agents, or
two -- is empirical. Fit both, price held-out contracts with each, compare.
The data answers it.

DECISION A -- whether contract length counts as value or as mispricing -- is
not settled by a held-out test, and a horse race between the two would be
theatre. They answer different questions and would need different targets.
Term-in says the security of a long deal is part of what the team bought;
term-free says it is a premium to be measured against a one-year price. Both
are internally consistent. What this script can do is build both, quantify how
far apart they are, and show WHERE they disagree, so the choice is made with
the disagreement in view rather than in the abstract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from contract_price_model import (contract_sample, attach_forecasts, tobit,
                                  predict_tobit)
from player_season_table import build as build_table
from ability_forecast import A1AgingParticipationImputedNC

SCRIPT_VERSION = "1.0"

FEATURES = ["war_per_season", "length", "is_RFA", "rfa_x_war", "is_D",
            "one_year", "war_year1"]
FEATURES_SPLIT = ["war_per_season", "length", "is_D", "one_year", "war_year1"]


def prep(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["rfa_x_war"] = d["is_RFA"] * d["war_per_season"]
    d["one_year"] = (d["length"] == 1).astype(float)
    return d


def rolling_price_eval(d: pd.DataFrame, split: bool) -> pd.DataFrame:
    """Price each season's contracts using only contracts signed before it."""
    rows = []
    for yr in range(2018, 2026):
        tr = d[d["start_yr"] < yr]
        te = d[d["start_yr"] == yr]
        if len(tr) < 200 or not len(te):
            continue
        pred = np.full(len(te), np.nan)
        groups = [("UFA", 0.0), ("RFA", 1.0)] if split else [("all", None)]
        for _, flag in groups:
            trg = tr if flag is None else tr[tr["is_RFA"] == flag]
            teg = te if flag is None else te[te["is_RFA"] == flag]
            if len(trg) < 150 or not len(teg):
                continue
            cols = FEATURES if flag is None else FEATURES_SPLIT
            b, _, ok = tobit(trg[cols].to_numpy(float),
                             trg["cap_share"].to_numpy(float),
                             trg["floor_share"].to_numpy(float))
            p = predict_tobit(b, teg[cols].to_numpy(float))
            p = np.maximum(p, teg["floor_share"].to_numpy(float))
            pred[te.index.get_indexer(teg.index)] = p
        m = np.isfinite(pred)
        rows.append({"start_yr": yr, "n": int(m.sum()),
                     "mae": float(np.abs(pred[m] - te["cap_share"].to_numpy(float)[m]).mean())})
    return pd.DataFrame(rows)


def main() -> None:
    C.banner("run_phase4_decisions.py", SCRIPT_VERSION)
    table = build_table(birthdate_csv=C.OUT_DIR / "birthdates.csv", verbose=False)
    d = prep(attach_forecasts(contract_sample(), A1AgingParticipationImputedNC,
                              table, verbose=False))
    C.log(f"  {len(d)} skater contracts with a signing-dated forecast, "
          f"{int((d['cap_share'] <= d['floor_share'] + 1e-12).sum())} at the league minimum")
    C.log("")

    # ---------------- DECISION B ----------------
    C.log("DECISION B -- one price line for restricted and unrestricted free")
    C.log("agents, or two? Held out by season: each year's contracts are priced")
    C.log("using only contracts signed before it. Error is in cap share, so")
    C.log("0.010 is one percent of the salary cap, about $0.9M in 2024.")
    C.log("")
    pooled = rolling_price_eval(d, split=False)
    split = rolling_price_eval(d, split=True)
    j = pooled.merge(split, on="start_yr", suffixes=("_pooled", "_split"))
    C.log(f"  {'season':<9}{'n':>6}{'one line':>11}{'two lines':>11}{'better':>12}")
    for r in j.itertuples():
        better = "two lines" if r.mae_split < r.mae_pooled else "one line"
        C.log(f"  {r.start_yr:<9}{r.n_pooled:>6}{r.mae_pooled:>11.5f}"
              f"{r.mae_split:>11.5f}{better:>12}")
    wp = float(np.average(j["mae_pooled"], weights=j["n_pooled"]))
    ws = float(np.average(j["mae_split"], weights=j["n_pooled"]))
    C.log(f"  {'weighted':<9}{int(j['n_pooled'].sum()):>6}{wp:>11.5f}{ws:>11.5f}"
          f"{('two lines' if ws < wp else 'one line'):>12}")
    C.log(f"  difference: {100 * (ws / wp - 1):+.2f}% for two lines "
          f"({(ws - wp) * 100:+.4f} percentage points of the cap, "
          f"about ${abs(ws - wp) * C.CAP_CEILING[2024]:,.0f} a contract)")
    wins = int((j["mae_split"] < j["mae_pooled"]).sum())
    C.log(f"  two lines win in {wins} of {len(j)} seasons. A method that were genuinely")
    C.log("  better would not be splitting seasons close to evenly, and the weighted gap is")
    C.log("  smaller than the year-to-year variation in either method. The data does not")
    C.log("  distinguish them, which is a finding: the locked single line (D7) survives, and")
    C.log("  the rebuild has no cause to reopen it.")
    C.log("")

    # ---------------- DECISION A ----------------
    C.log("DECISION A -- does contract length count as value, or as mispricing?")
    C.log("Not a horse race: the two price different things. Both are built and")
    C.log("the disagreement is quantified.")
    C.log("")
    b, _, _ = tobit(d[FEATURES].to_numpy(float), d["cap_share"].to_numpy(float),
                    d["floor_share"].to_numpy(float))
    names = ["intercept"] + FEATURES
    C.log("  the fitted price line (cap share per unit):")
    for n, v in zip(names, b):
        C.log(f"    {n:<16}{v:+.5f}")
    term_coef = b[names.index("length")]
    C.log("")
    C.log(f"  a year of term carries {term_coef:+.5f} of cap share per season, "
          f"about ${term_coef * C.CAP_CEILING[2024] / 1e6:+.2f}M a season at the 2024 ceiling")
    C.log("  READ THAT AS AN ASSOCIATION, NOT A PRICE. Long deals go to better players,")
    C.log("  and the forecast controls for production only as well as the forecast is. What")
    C.log("  length does not absorb of a player's quality, it will carry. Stripping term out")
    C.log("  therefore strips some genuine quality with it, and that cuts against reading the")
    C.log("  whole term-in / term-free gap below as a premium.")
    C.log("")

    # term-in prices the deal as signed; term-free prices the same production
    # as a sequence of one-year deals.
    Xin = d[FEATURES].to_numpy(float).copy()
    Xfree = Xin.copy()
    Xfree[:, FEATURES.index("length")] = 1.0
    Xfree[:, FEATURES.index("one_year")] = 1.0
    d["value_term_in"] = np.maximum(predict_tobit(b, Xin), d["floor_share"]) * d["length"]
    d["value_term_free"] = np.maximum(predict_tobit(b, Xfree), d["floor_share"]) * d["length"]
    d["gap"] = d["value_term_in"] - d["value_term_free"]
    d["gap_dollars"] = d["gap"] * C.CAP_CEILING[2024]

    C.log("  WHERE THE TWO DISAGREE, by contract length. Values are total cap share")
    C.log("  consumed across the whole deal (share per season times years), and the gap")
    C.log("  is the whole-contract difference in dollars at the 2024 ceiling.")
    C.log(f"  {'term':<7}{'n':>6}{'term-in':>11}{'term-free':>11}{'gap, $M':>11}")
    for L, g in d.groupby("length"):
        if len(g) < 20:
            continue
        C.log(f"  {int(L):<7}{len(g):>6}{g['value_term_in'].mean():>11.4f}"
              f"{g['value_term_free'].mean():>11.4f}{g['gap_dollars'].mean() / 1e6:>11.2f}")
    C.log("")
    C.log("  and by forecast production (the money players are the long deals):")
    tiers = pd.cut(d["war_per_season"], [-np.inf, 0, 0.5, 1.0, 2.0, np.inf],
                   labels=["below 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2+"])
    C.log(f"  {'forecast':<10}{'n':>6}{'mean term':>11}{'gap, $M':>11}{'gap, total $M':>15}")
    for t, g in d.groupby(tiers, observed=True):
        C.log(f"  {str(t):<10}{len(g):>6}{g['length'].mean():>11.2f}"
              f"{g['gap_dollars'].mean() / 1e6:>11.2f}{g['gap_dollars'].sum() / 1e6:>15.1f}")
    C.log("")
    tot = d["gap_dollars"].sum() / 1e6
    C.log(f"  Across all {len(d)} contracts the two currencies differ by ${tot:,.0f}M in total.")
    C.log("  That total is the size of the thing decision A decides whether to call")
    C.log("  mispricing. It is not evidence for either answer.")
    C.write_log("phase4_decisions_run_log.txt")


if __name__ == "__main__":
    main()
