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

SCRIPT_VERSION = "1.1"

# One shared line; rights enter as features. Settled by the decision-B test.
FEATURES = ["war_per_season", "length", "is_RFA", "rfa_x_war", "is_D",
            "one_year", "war_year1"]


class ProductionCurrency:
    """The price of forecast production, in cap share per season."""

    def __init__(self, term_mode: str = "in"):
        assert term_mode in ("in", "free"), term_mode
        self.term_mode = term_mode
        self.coef_ = None

    def fit(self, d: pd.DataFrame, before_date=None):
        """Fit on contracts SIGNED before `before_date`.

        This used to split on the contract's start year, which is not when the
        market spoke. An extension signed in 2017 starts in 2019, so a fit
        dated by start year trained a 2019 valuation on deals signed in 2018
        and called it ex ante. Dating the player's forecast at his signing, as
        attach_forecasts already does, does not make those later signings
        available: the price line has to be frozen at the decision too.

        The docstring on this module claimed signing-dated fits before this was
        true of the fit. It is true now.
        """
        if isinstance(before_date, (int, np.integer)):
            raise TypeError(
                "fit() takes a signing DATE, not a season. A year was what "
                "split the sample by contract start and let a valuation train "
                "on contracts signed after it. Pass the decision date.")
        tr = d if before_date is None else d[d["signed"] < pd.Timestamp(before_date)]
        if before_date is not None and len(tr):
            latest = tr["signed"].max()
            assert latest < pd.Timestamp(before_date), (
                f"the training sample reaches {latest.date()}, which is not "
                f"before the decision date {pd.Timestamp(before_date).date()}")
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
        # Cap share times the ceiling in each contract season, DISCOUNTED, on
        # the cap path as it was knowable at the signing. The previous version
        # summed realised ceilings and substituted the 2025 ceiling for
        # anything later, so a historical valuation knew the flat-cap years
        # before they happened and no discounting was applied at all.
        #
        # Under locked decision D24 the 3% growth and the 3% discount cancel in
        # cap-share terms, so for a fully extrapolated path this reduces to the
        # sum of shares times one ceiling. That is asserted in repair_checks
        # rather than assumed here, which is why both rates appear explicitly
        # below instead of being cancelled away in the algebra.
        dollars = np.zeros(len(d))
        for i, r in enumerate(d.itertuples()):
            yrs = list(range(int(r.start_yr), int(r.end_yr) + 1))
            path = C.cap_path(r.signed, yrs)
            dollars[i] = share[i] * sum(
                path[y] / (1.0 + C.DISCOUNT_RATE) ** k for k, y in enumerate(yrs))
        return pd.Series(dollars, index=d.index)

    def cost(self, d: pd.DataFrame) -> pd.Series:
        """What the club actually committed: the cap hit across the term,
        discounted on the same schedule as the value side.

        Value and cost have to be dated and discounted identically or their
        difference is not a surplus. The cap hit is a known nominal amount in
        each contract season, so only the discount applies; there is no cap
        path on this side because the commitment is in dollars, not in share.
        """
        out = np.zeros(len(d))
        for i, r in enumerate(d.itertuples()):
            out[i] = sum(r.aav / (1.0 + C.DISCOUNT_RATE) ** k
                         for k in range(int(r.length)))
        return pd.Series(out, index=d.index)
