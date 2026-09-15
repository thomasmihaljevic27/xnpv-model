"""production_currency.py -- forecast production, in dollars.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 4, second half.

DECISION A IS SETTLED: TERM-IN (2026-09-15, Thomas). The security of a long
deal is part of what the club bought, so the currency prices the remaining
term rather than a sequence of one-year deals. Term-free is retained as the
required sensitivity, not as the primary. The reason is about the data: the
one-year counterfactual does not exist for the players who carry the money --
94% of 3.5-win contracts are signed with the player's own club -- so pricing a
star at a one-year rate compares him against a market that never had the
chance to bid, and then calls the difference mispricing.

DECISION B IS SETTLED BY THE TEST: ONE LINE. Restricted and unrestricted free
agents are priced on shared estimation, with rights entering as a feature
rather than as a separate market. Two lines beat one by $7,203 on the average
contract while winning four seasons of eight, which is not a distinction.

WHAT THE CURRENCY IS, AND WHAT IT IS NOT
    It is the market's own price for forecast production, fitted on
    signing-dated forecasts so its slope is the price of a FORECAST win rather
    than of a realised one.

    It is therefore not an absolute value of a win, and surplus computed
    against it is not absolute surplus. Because the line is fitted to observed
    contracts, the average contract prices at roughly zero surplus by
    construction, and a positive number means "paid less than the average club
    paid for a comparable forecast" -- deviation from the market, not profit.
    Every claim built on it inherits that, and the back-test says so out loud
    rather than in a footnote. This is the circularity the project has always
    known about: it is bounded here, not removed.

    Both sides of a back-test comparison are priced on this same line, so the
    units match. That is the point of having one currency.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from contract_price_model import tobit, predict_tobit

SCRIPT_VERSION = "1.0"

# One shared line; rights enter as features. Settled by the decision-B test.
FEATURES = ["war_per_season", "length", "is_RFA", "rfa_x_war", "is_D",
            "one_year", "war_year1"]


class ProductionCurrency:
    """The price of forecast production, in cap share per season."""

    def __init__(self, term_mode: str = "in"):
        assert term_mode in ("in", "free"), term_mode
        self.term_mode = term_mode
        self.coef_ = None

    def fit(self, d: pd.DataFrame, before: int | None = None):
        """Fit on contracts signed before `before`, so a valuation never sees
        the market it is being judged against."""
        tr = d if before is None else d[d["start_yr"] < before]
        if len(tr) < 200:
            return self
        self.coef_, self.sigma_, self.ok_ = tobit(
            tr[FEATURES].to_numpy(float), tr["cap_share"].to_numpy(float),
            tr["floor_share"].to_numpy(float))
        self.n_fit_ = len(tr)
        return self

    def value(self, d: pd.DataFrame) -> pd.Series:
        """Total dollars the market would pay for this forecast production
        over this contract's term.

        Under term-in the player's actual term is used, so the security he was
        given is priced. Under the term-free sensitivity the same production is
        priced as a run of one-year deals.
        """
        X = d[FEATURES].to_numpy(float).copy()
        if self.term_mode == "free":
            X[:, FEATURES.index("length")] = 1.0
            X[:, FEATURES.index("one_year")] = 1.0
        share = np.maximum(predict_tobit(self.coef_, X),
                           d["floor_share"].to_numpy(float))
        # Cap share times the ceiling in each contract season, summed. The
        # ceiling is used season by season rather than at the start year,
        # because a share of an 88M cap is not a share of a 95.5M one.
        dollars = np.zeros(len(d))
        for i, r in enumerate(d.itertuples()):
            yrs = range(int(r.start_yr), int(r.end_yr) + 1)
            dollars[i] = share[i] * sum(C.CAP_CEILING.get(y, C.CAP_CEILING[2025])
                                        for y in yrs)
        return pd.Series(dollars, index=d.index)

    def cost(self, d: pd.DataFrame) -> pd.Series:
        """What the club actually committed: the cap hit across the term."""
        return d["aav"] * d["length"]
