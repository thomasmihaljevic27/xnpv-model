"""predictive_interval.py -- turning a point forecast into a distribution.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 1/5 prerequisite.

WHAT WAS MISSING
    Every model in `ability_forecast.py` answers three questions about a
    future season -- how good he will be per 82 games, how much of the
    schedule he will be available for, and whether he will be in the league
    at all -- and the harness multiplies the three into one expected number
    of wins. That expectation is all any of them has ever produced. The
    harness has scored interval coverage since the day it was written, and
    the column has been empty in every run, because no model has ever stated
    a range.

    A point forecast is not enough for what comes next. The valuation walks
    career paths and averages them, so it needs to know how wide the paths
    spread; a contract is worth more when the same expected production
    carries a chance of being much better, because the club keeps the upside
    and the cap hit does not move. A model that says "1.2 wins" and a model
    that says "1.2 wins, and anywhere from -0.1 to 3.0 would not surprise me"
    price a long deal differently, and only the second one can be checked
    against what happened.

THE SHAPE OF THE ANSWER, AND WHY IT IS NOT A BELL CURVE
    A season's win total is not a smooth spread around a central value. It
    has a lump of probability sitting exactly on zero -- the seasons the
    player spends out of the league, hurt, in the minors or retired -- and a
    continuous spread for the seasons he plays. A normal distribution around
    the expectation gets the middle roughly right and the edges badly wrong:
    for a fringe player with a 50% chance of playing at all, the honest tenth
    percentile IS zero, and no bell curve centred on 0.4 wins will say so.

    So the distribution here is a mixture, written the way the forecast is
    already built:

        with probability (1 - p_play)   the season is exactly 0
        with probability p_play         the season is drawn from a spread
                                        around rate_82 * gp_share

    The second piece is the conditional forecast -- what he does GIVEN he
    plays -- which is exactly what the rate and games halves of every model
    already mean. Nothing is re-derived and nothing is double counted: the
    participation probability enters here once, in the same place and with
    the same meaning it has in the harness's integration rule.

WHERE THE SPREAD COMES FROM
    Fitted, not assumed, and fitted rolling like everything else.

    At a decision date the calibrator replays the model on earlier pages --
    pages whose outcome seasons had all finished before this date -- and
    collects what the model got wrong. Those misses are the evidence about
    how wrong it tends to be. Two things are read off them:

    1. SCALE, per horizon. Misses are bigger for better players and bigger
       further out, so the scale is fitted as a straight line in the size of
       the forecast itself, separately for each season ahead. A player
       forecast at 3 wins gets a wider band than one forecast at 0.3, because
       he has earned one.

    2. SHAPE, pooled. After dividing each miss by its own scale, what is left
       is the shape of the error: how fat the tails are, how lopsided it is.
       That is taken as the empirical distribution of the scaled misses, not
       as a formula, which is the point -- season-to-season win totals have a
       long right tail (a career year) and a short left one (there is a floor
       on how bad a player can be before he stops playing), and no two-
       parameter curve carries that.

    IN-SAMPLE OPTIMISM, STATED. The replay uses the coefficients fitted at
    the current decision date, so the misses it measures are the misses of a
    model that has already seen those outcome seasons in its own training.
    That makes the fitted spread slightly too narrow. It is not look-ahead:
    nothing after the decision date is read, and the calibration pages are
    the model's own training window. It is the ordinary optimism of an
    in-sample residual, which for a regression with eight terms and thousands
    of rows is small. `run_uncertainty.py` measures it rather than assuming
    it away, by comparing the fitted spread against the spread of the
    harness's genuinely out-of-sample misses.

NOT A CONFIDENCE INTERVAL
    This is a PREDICTIVE interval: a range for one player's one season, which
    is dominated by how unpredictable hockey is and only slightly by how
    uncertain the coefficients are. A confidence interval on the fitted line
    would be perhaps a tenth as wide and would answer a question nobody in
    this project has asked.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import information_set as ISET

SCRIPT_VERSION = "1.3"

# The stated interval. 80% is the plan's own wording ("interval coverage --
# how often the stated 80% range contained the outcome"), and the harness
# scores lo/hi against it.
DEFAULT_LEVEL = 0.80

# Extra levels reported by the calibration runner. A single coverage number
# can be right by luck when one tail is too fat and the other too thin; three
# levels and both tails separately is what makes that visible.
REPORT_LEVELS = (0.50, 0.80, 0.90)

# HOW FAR BACK THE REPLAY REACHES. The models already train on pairs back to
# the first source season, so the calibration window matches their own: a
# page needs the trailing seasons its anchor reads, which is why it starts two
# years after the source does rather than at the source's first year.
CAL_FIRST_PAGE = C.FIRST_SOURCE_SEASON + 2

# A horizon needs this many replayed misses before its scale is fitted from
# its own evidence rather than extended from the horizon below.
MIN_CAL_ROWS = 300

# The scale never falls below this share of the typical miss at the horizon.
# Without it a player forecast at almost exactly zero -- a fourth-liner, or
# anyone the model has little to say about -- gets a band of almost no width
# and is scored as a miss every time the season is ordinary.
SCALE_FLOOR_SHARE = 0.25


# ---------------------------------------------------------------------------
# The mixture, as arithmetic. Kept as a free function with no model and no
# data in it so it can be checked against a case whose right answer is known
# by construction -- which is what self_test() below does.
# ---------------------------------------------------------------------------
def mixture_quantile(q: float, p_play, mu, sigma, zs: np.ndarray) -> np.ndarray:
    """The q-th quantile of the season total, for each row.

    The distribution being inverted, written out:

        F(x) = p_play * G(x) + (1 - p_play) * 1{x >= 0}

    where G is the conditional-on-playing distribution, built by sliding and
    stretching the empirical shape `zs` to sit at `mu` with width `sigma`.
    The second term is the lump on zero. Note where that lump sits: in the
    MIDDLE of G's support, not at its edge, because a player who does play
    can still finish below zero wins. That is why this is inverted by hand
    rather than by shifting a standard formula -- the jump is interior, so
    the quantile function has a flat step at exactly 0 and the rows whose
    q falls inside that step are the rows whose honest answer IS zero.

    Args:
        q:      the probability level, a scalar in (0, 1)
        p_play: probability the player plays at all, per row
        mu:     the conditional forecast, rate_82 * gp_share, per row
        sigma:  the fitted scale of the miss, per row
        zs:     sorted scaled misses -- the empirical shape of G
    """
    p = np.clip(np.asarray(p_play, dtype=float), 1e-9, 1.0)
    mu = np.asarray(mu, dtype=float)
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-9)

    # G evaluated at zero: the chance a player who PLAYS still finishes at or
    # below zero wins. This is what decides how much of the lump the interval
    # has already passed by the time it reaches zero.
    g0 = _shape_cdf((0.0 - mu) / sigma, zs)

    below = p * g0                    # all the probability strictly below zero
    above = below + (1.0 - p)         # ... and everything at or below zero

    # Three cases, one per region of the inverted step function.
    #   q below the step  -> a negative answer, read off the shape directly
    #   q inside the step -> exactly zero
    #   q above the step  -> a positive answer, with the lump's mass removed
    #                        first so the shape is asked the right question
    lo_u = np.clip(q / p, 0.0, 1.0)
    hi_u = np.clip((q - (1.0 - p)) / p, 0.0, 1.0)
    x_lo = mu + sigma * _shape_quantile(lo_u, zs)
    x_hi = mu + sigma * _shape_quantile(hi_u, zs)

    return np.where(q <= below, x_lo, np.where(q <= above, 0.0, x_hi))


def randomized_pit(draws: np.ndarray, outcome: float, u: float) -> float:
    """Where an outcome falls in a forecast's own distribution, when that
    distribution has lumps.

    The probability integral transform of a continuous forecast is F(outcome),
    and it is uniform on [0, 1] exactly when the forecast is calibrated. A
    distribution with a point mass breaks that: the salary floor puts many
    dollar paths at one value, non-participation puts a season at exactly
    zero, and an outcome sitting on the lump has F jump across it. A nominal
    80% interval whose end sits on the lump then contains the whole lump and
    can honestly hold far more than 80%.

    The randomized transform spreads an outcome on a lump uniformly across the
    lump's share of probability,

        PIT = F(outcome-) + u * (F(outcome) - F(outcome-)),   u ~ U(0, 1),

    and is uniform again under calibration, lumps or no lumps. That is the
    test used here instead of counting outcomes inside an interval.

    `draws` are the forecast's own simulated values; F is their empirical
    distribution.
    """
    d = np.asarray(draws, dtype=float)
    below = float(np.mean(d < outcome))
    at_or_below = float(np.mean(d <= outcome))
    return below + float(u) * (at_or_below - below)


def mixture_pit(x, p_play, mu, sigma, zs: np.ndarray, u) -> np.ndarray:
    """The randomized transform for the season mixture `mixture_quantile`
    inverts: a lump of (1 - p_play) at exactly zero, and p_play of the
    conditional shape around mu. An unplayed season is an outcome of exactly
    zero and is spread across the lump; a played season is not on the lump
    (the conditional shape is continuous) and takes the ordinary value."""
    x = np.asarray(x, dtype=float)
    p = np.clip(np.asarray(p_play, dtype=float), 1e-9, 1.0)
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-9)
    g = _shape_cdf((x - np.asarray(mu, dtype=float)) / sigma, zs)
    lump = (1.0 - p) * (x >= 0.0)
    below = p * g + (1.0 - p) * (x > 0.0)
    at = p * g + lump
    return below + np.asarray(u, dtype=float) * (at - below)


def _shape_cdf(x, zs: np.ndarray) -> np.ndarray:
    """P(scaled miss <= x), by linear interpolation between the observed
    misses. Beyond the observed range it saturates at 0 and 1 -- the shape is
    empirical, so it declines to invent a tail it has never seen."""
    grid = np.linspace(0.0, 1.0, len(zs))
    return np.interp(np.asarray(x, dtype=float), zs, grid, left=0.0, right=1.0)


def _shape_quantile(u, zs: np.ndarray) -> np.ndarray:
    """The exact inverse of `_shape_cdf`, so that a value put through one and
    back through the other comes out where it started. Using numpy's quantile
    here instead would agree to within a rounding error and disagree at the
    ends, which is precisely where an interval lives."""
    grid = np.linspace(0.0, 1.0, len(zs))
    return np.interp(np.clip(np.asarray(u, dtype=float), 0.0, 1.0), grid, zs)


def _grid_mean(zs: np.ndarray) -> float:
    """The mean of the piecewise-linear quantile function built on `zs`.

    `_shape_quantile` interpolates linearly between the sorted misses on an
    even probability grid, so the distribution it describes is a chain of
    straight segments and its mean is the trapezoid rule over them -- which
    gives the first and last miss half the weight the others get. The plain
    sample mean answers a slightly different question and would leave a small
    offset in the distribution that is actually sampled.
    """
    n = len(zs)
    if n < 2:
        return float(zs.mean()) if n else 0.0
    return float(np.trapezoid(zs, dx=1.0 / (n - 1)))


def mixture_mean(p_play, mu, sigma, zs: np.ndarray, grid: int = 2001) -> np.ndarray:
    """The mean of the season-total distribution, by integrating its own
    quantile function.

    Deliberately NOT computed from the algebra. The algebra says the answer is
    p_play * mu once the shape is centred, and that is exactly the claim being
    checked; deriving the check from the claim would test nothing. This
    integrates what `mixture_quantile` actually returns, over the whole
    probability range, so it would catch a mistake in the inversion, in the
    handling of the lump, or in the centring, none of which the algebra can
    see.
    """
    u = np.linspace(0.0, 1.0, grid)
    acc = np.zeros(len(np.atleast_1d(mu)), dtype=float)
    for i, q in enumerate(u):
        x = mixture_quantile(float(q), p_play, mu, sigma, zs)
        w = 0.5 if i in (0, grid - 1) else 1.0
        acc += w * np.asarray(x, dtype=float)
    return acc / (grid - 1)


# ---------------------------------------------------------------------------
# The calibrator
# ---------------------------------------------------------------------------
class SpreadModel:
    """How wrong the model tends to be, fitted from its own earlier misses.

    One instance belongs to one decision date. `fit()` is called with the same
    `before` the forecast model was fitted with, and reads nothing dated at or
    after it.
    """

    def __init__(self, first_page: int = CAL_FIRST_PAGE):
        self.first_page = first_page
        self.scale_: dict[int, tuple[float, float, float]] = {}   # h -> (a, b, floor)
        self.zs_: np.ndarray = np.array([])
        self.z_by_h_: dict[int, np.ndarray] = {}
        self.n_cal_: dict[int, int] = {}
        self.extended_: set[int] = set()
        self.cal_pages_: tuple[int, ...] = ()

    # -- fitting ------------------------------------------------------------
    def fit(self, model, table: pd.DataFrame, before: int, horizons) -> "SpreadModel":
        """Replay `model` on the pages before `before` and learn its misses.

        `model` must already be fitted. `table` is the same season table the
        forecast model was handed, which the harness has already cut to
        seasons the decision date could see -- so every outcome read here
        finished before the decision date by construction, and the horizon
        filter below is a second lock on the same door.
        """
        horizons = tuple(sorted(int(h) for h in horizons))
        rows = []
        pages = []
        for c in range(self.first_page, before):
            # WHICH HORIZONS THIS CALIBRATION PAGE CAN CARRY. A page four
            # years back can tell us about a four-season-ahead miss and no
            # further, because the fifth season had not been played when the
            # decision date arrived.
            usable = [h for h in horizons if c + h < before]
            usable = [h for h in usable
                      if h in getattr(model, "fitted_horizons_", horizons)]
            if not usable:
                continue
            got = self._replay(model, table, c, usable)
            if got is not None and len(got):
                rows.append(got)
                pages.append(c)
        self.cal_pages_ = tuple(pages)
        if not rows:
            raise ValueError(
                f"no calibration evidence before {before}: the spread cannot be "
                "fitted, and a model that states an interval it has not "
                "calibrated is worse than one that states none.")
        d = pd.concat(rows, ignore_index=True)
        self._fit_scale(d, horizons)
        self._fit_shape(d)
        # KEPT for the path simulation, which fits the cross-season dependence
        # of these same misses. Re-running the replay to get them a second time
        # would be a second copy of the thing whose first copy is the reason
        # this tree keeps warning about second copies.
        self.pairs_ = d
        return self

    def _replay(self, model, table, page: int, horizons) -> pd.DataFrame | None:
        """One page: what the model said, and what happened."""
        import forecast_harness as H          # local: avoids an import cycle

        iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
        subs = H.subjects_at(iset)
        if subs.empty:
            return None
        pred = model.predict(iset, subs, horizons)

        # The conditional forecast, which is the quantity the spread is about.
        # It is the harness's own integration rule with the participation term
        # left off, because participation is handled by the mixture and
        # dividing it in here would count it twice.
        pred = pred.copy()
        pred["mu"] = pred["rate_82"] * pred["gp_share"]
        pred["season"] = page + pred["h"].astype(int)

        act = table.set_index(["career_key", "syr"])
        ix = pd.MultiIndex.from_arrays([pred["career_key"], pred["season"]])
        pred["act_war"] = act["WAR"].reindex(ix).to_numpy()
        pred["act_gp"] = act["GP"].reindex(ix).to_numpy()
        # A player absent from the source that season did not play: a zero,
        # not a missing row. He belongs to the lump, so he carries no
        # information about the spread of the seasons that DID happen and is
        # dropped one line below.
        pred["played"] = np.nan_to_num(pred["act_gp"]) >= C.PARTICIPATION_GP
        # career_key is carried so the joint simulation can ask a question the
        # interval never had to: how much of one player's miss at one horizon
        # comes back at the next. That needs the misses paired by player, which
        # means keeping the player.
        out = pred.loc[pred["played"], ["career_key", "h", "mu", "act_war"]].copy()
        out["r"] = out["act_war"].fillna(0.0) - out["mu"]
        out["page"] = page
        return out

    def _fit_scale(self, d: pd.DataFrame, horizons) -> None:
        """Scale as a straight line in the size of the forecast, per horizon.

        The regression is of the ABSOLUTE miss on the absolute forecast. Two
        deliberate choices:

        - The slope is floored at zero. A fitted negative slope would say the
          model's best players are its most predictable in wins, which is the
          opposite of every diagnostic this project has run, and it would
          produce a nonsensical negative width somewhere out past 4 wins. A
          thin horizon can produce one by noise; it is refused rather than
          carried.
        - The whole line is floored at a share of the typical miss, so a
          player forecast at zero still gets a band. Without that floor the
          fourth-liners -- who are most of the rows -- would be scored against
          a band of nearly no width and the coverage number would be about
          them rather than about the model.
        """
        for h in horizons:
            g = d[d["h"] == h]
            self.n_cal_[h] = len(g)
            if len(g) >= MIN_CAL_ROWS:
                absr = g["r"].abs().to_numpy()
                x = g["mu"].abs().to_numpy()
                X = np.column_stack([np.ones_like(x), x])
                a, b = np.linalg.lstsq(X, absr, rcond=None)[0]
                self.scale_[h] = (float(a), float(max(b, 0.0)),
                                  float(SCALE_FLOOR_SHARE * np.median(absr)))
        self._extend_scale(horizons)

    def _extend_scale(self, horizons) -> None:
        """Horizons with too little evidence of their own.

        At the earliest development pages the replay cannot reach the longest
        horizons: to see a five-season miss at the 2015 page the model would
        have had to be asked in 2009 and answered by 2014, and the pages that
        far back are thinner than the ones that follow. Rather than leave
        those horizons without a band -- which would silently drop the longest
        contracts, the ones the thesis cares most about, out of every coverage
        figure -- the scale is CONTINUED at the growth rate already visible
        across the horizons that were fitted.

        This is the same device `ability_forecast.predict_beyond_fit` uses for
        the forecast itself, for the same reason and with the same caveat: it
        is an extrapolation, every row produced by it is tagged, and a
        coverage figure that leans on one says so.
        """
        fitted = sorted(self.scale_)
        if not fitted:
            raise ValueError("no horizon had enough calibration rows to fit a scale")
        # The growth rate: how much wider the band gets per extra season, read
        # at a reference forecast of one win a season so the intercept and the
        # slope are both represented. Measured over the last two fitted
        # horizons, or held flat if only one horizon was fitted.
        def width_at(h, ref=1.0):
            a, b, fl = self.scale_[h]
            return max(fl, a + b * ref)
        if len(fitted) >= 2:
            ratio = width_at(fitted[-1]) / max(width_at(fitted[-2]), 1e-9)
            ratio = float(np.clip(ratio, 1.0, 1.5))   # never narrows with distance
        else:
            ratio = 1.0
        last = fitted[-1]
        for h in sorted(horizons):
            if h in self.scale_:
                continue
            a, b, fl = self.scale_[last]
            k = ratio ** (h - last)
            self.scale_[h] = (a * k, b * k, fl * k)
            self.extended_.add(h)

    def _fit_shape(self, d: pd.DataFrame) -> None:
        """The shape of a miss, once its own scale is divided out.

        Pooled across horizons ON PURPOSE. The scale already carries what
        changes with distance -- the band gets wider further out -- and what
        is left is the character of the error, which there is no reason to
        think differs between a one-season and a four-season miss. Pooling
        buys the tails: the 5th and 95th percentiles of a shape fitted on a
        few hundred rows are two order statistics, and an interval read off
        them is noise. `report()` prints the per-horizon shapes so the
        assumption is checked rather than trusted.
        """
        z = []
        for h, g in d.groupby("h"):
            a, b, fl = self.scale_[int(h)]
            s = np.maximum(fl, a + b * g["mu"].abs().to_numpy())
            zi = g["r"].to_numpy() / s
            self.z_by_h_[int(h)] = np.sort(zi)
            z.append(zi)
        zs = np.sort(np.concatenate(z))

        # CENTRED, AND THIS IS NOT A DETAIL.
        #
        # The raw scaled misses do not average to zero. They average to about
        # +0.10, because the shape has a long right tail and the mean of a
        # right-skewed distribution sits above its middle. Left uncentred, the
        # conditional distribution is mu + sigma * Z with expectation
        # mu + sigma * E[Z], which is NOT mu -- so the distribution's own mean
        # would sit roughly 0.09 wins above the point forecast for a one-win
        # player at five seasons out, while the forecast columns beside it
        # still read mu.
        #
        # That is the same silent move this wrapper exists to make impossible.
        # It preserved the point-forecast COLUMNS and moved the expectation
        # they stand for, which is worse than moving the columns, because
        # nothing downstream would have noticed. The Phase 5 simulation
        # averages priced paths, so it would have drawn its paths from a
        # distribution whose mean disagreed with the harness's own integration
        # rule, and every contract would have been revalued by an amount
        # nobody put there on purpose.
        #
        # CENTRING IS THE COHERENT CHOICE, not the only conceivable one. The
        # alternative is to treat the residual mean as a bias correction and
        # move the point forecast to mu + sigma * E[Z]. That is a change to the
        # FORECAST -- it would move every score in the variant register and it
        # belongs in the forecast's own phase with its own test, not smuggled
        # in through an interval. So the mean is removed here and reported as a
        # measured quantity, which is what it is: evidence that the forecast
        # runs low on the seasons that happened.
        #
        # The quantity removed is the mean of the piecewise-linear quantile
        # function that _shape_quantile() actually interpolates, not the plain
        # sample mean of the misses. The two differ because linear
        # interpolation across the sorted misses gives the two extreme order
        # statistics half the weight of the rest. Centring on the sample mean
        # would leave a small residual offset in the thing being used.
        self.shape_mean_raw_ = float(_grid_mean(zs))
        self.zs_ = zs - self.shape_mean_raw_

    # -- use ----------------------------------------------------------------
    def ensure_horizons(self, horizons) -> "SpreadModel":
        """Extend the fitted scale to cover horizons it has not seen.

        A contract can outrun the page that prices it -- the forecast has a
        declared extrapolation rule for exactly that, and the band needs the
        same. Rather than a second rule, this calls the one `_extend_scale`
        already applies to a horizon with too little calibration evidence, so
        an eight-year deal priced from a page reaching five gets a band
        continued at the growth rate the fitted horizons show, and the rows are
        already tagged as extrapolated by the forecast side.
        """
        want = [int(h) for h in horizons if int(h) not in self.scale_]
        if want:
            self._extend_scale(sorted(set(self.scale_) | set(want)))
        return self

    def sigma(self, h: int, mu) -> np.ndarray:
        a, b, fl = self.scale_[int(h)]
        return np.maximum(fl, a + b * np.abs(np.asarray(mu, dtype=float)))

    def interval(self, h: int, mu, p_play, level: float = DEFAULT_LEVEL):
        """The stated range, as (lo, hi), with equal probability left outside
        on each side."""
        tail = (1.0 - level) / 2.0
        return self.quantile(h, mu, p_play, tail), self.quantile(h, mu, p_play, 1 - tail)

    def quantile(self, h: int, mu, p_play, q: float) -> np.ndarray:
        return mixture_quantile(q, p_play, mu, self.sigma(h, mu), self.zs_)

    def mean(self, h: int, mu, p_play) -> np.ndarray:
        """What a simulation drawing from this distribution would average to.
        It must equal the point forecast the harness scores, p_play * mu."""
        return mixture_mean(p_play, mu, self.sigma(h, mu), self.zs_)

    # -- reporting ----------------------------------------------------------
    def report(self) -> list[str]:
        out = [f"  calibration pages {self.cal_pages_[0]}-{self.cal_pages_[-1]}"
               f"  ({len(self.zs_)} replayed misses)",
               f"  shape centred by {self.shape_mean_raw_:+.4f}: that much of the"
               f" average miss is the forecast running low",
               f"  on the seasons that happened, and it is reported here rather"
               f" than absorbed into the band"]
        out.append(f"  {'seasons ahead':<16}{'misses':>9}{'band at 0':>12}"
                   f"{'band at 2 wins':>17}   source")
        for h in sorted(self.scale_):
            a, b, fl = self.scale_[h]
            src = "extended from the horizon below" if h in self.extended_ else "fitted"
            out.append(f"  {h:<16}{self.n_cal_.get(h, 0):>9}{max(fl, a):>12.3f}"
                       f"{max(fl, a + 2 * b):>17.3f}   {src}")
        out.append("")
        out.append("  shape of a scaled miss, by horizon (pooled shape is the one used):")
        out.append(f"  {'seasons ahead':<16}{'5th':>9}{'25th':>9}{'50th':>9}"
                   f"{'75th':>9}{'95th':>9}")
        for h in sorted(self.z_by_h_):
            z = self.z_by_h_[h]
            qs = np.quantile(z, [0.05, 0.25, 0.5, 0.75, 0.95])
            out.append(f"  {h:<16}" + "".join(f"{v:>9.2f}" for v in qs))
        qs = np.quantile(self.zs_, [0.05, 0.25, 0.5, 0.75, 0.95])
        out.append(f"  {'pooled':<16}" + "".join(f"{v:>9.2f}" for v in qs))
        return out


# ---------------------------------------------------------------------------
# The wrapper
# ---------------------------------------------------------------------------
class WithIntervals:
    """Any forecast model, plus a stated range.

    Wraps rather than subclasses so that every candidate in
    `ability_forecast.py` -- and any candidate written after this -- gets
    intervals without a line of its own changing. The wrapper forwards
    `fit` and `predict` unaltered and adds columns; it cannot move a point
    forecast, which is what keeps a model's score on the existing metrics
    identical whether it is wrapped or not. `run_uncertainty.py` asserts that.
    """

    def __init__(self, model, level: float = DEFAULT_LEVEL,
                 levels=REPORT_LEVELS, first_page: int = CAL_FIRST_PAGE):
        self.model = model
        self.level = level
        self.levels = tuple(levels)
        self.first_page = first_page
        self.spread_: SpreadModel | None = None
        self.spreads_: dict[int, SpreadModel] = {}

    @property
    def name(self) -> str:
        return self.model.name

    @property
    def fitted_horizons_(self):
        return self.model.fitted_horizons_

    @property
    def FITTED_HORIZONS(self):
        return self.model.FITTED_HORIZONS

    def fit(self, table: pd.DataFrame, before: int):
        self.model.fit(table, before=before)
        self.spread_ = SpreadModel(self.first_page).fit(
            self.model, table, before=before, horizons=self.model.fitted_horizons_)
        # EVERY PAGE'S CALIBRATOR IS KEPT, because `spread_` is overwritten on
        # each page and after a harness run it holds the LAST page's fit. A
        # diagnostic that divides a 2015 miss by the 2021 band is not dividing
        # a miss by the band it was given -- the 2015 forecast was handed a
        # different scale and a different shape. Reports that scale residuals
        # look the page up here.
        self.spreads_[int(before)] = self.spread_
        return self

    def predict(self, iset, subs, horizons) -> pd.DataFrame:
        p = self.model.predict(iset, subs, horizons).copy()
        mu = (p["rate_82"] * p["gp_share"]).to_numpy()
        pp = p["p_play"].to_numpy()
        hs = p["h"].astype(int).to_numpy()

        # One horizon at a time, because the scale is per horizon. Written as
        # a masked assignment rather than a groupby-apply so that the row
        # order the harness's grid check depends on is untouched.
        cols = {f"q{int(round(q * 100)):02d}": np.full(len(p), np.nan)
                for q in self._all_quantiles()}
        for h in np.unique(hs):
            m = hs == h
            for q in self._all_quantiles():
                cols[f"q{int(round(q * 100)):02d}"][m] = mixture_quantile(
                    q, pp[m], mu[m], self.spread_.sigma(int(h), mu[m]),
                    self.spread_.zs_)
        for k, v in cols.items():
            p[k] = v
        tail = (1.0 - self.level) / 2.0
        p["lo"] = p[f"q{int(round(tail * 100)):02d}"]
        p["hi"] = p[f"q{int(round((1 - tail) * 100)):02d}"]
        # Which rows lean on an extended rather than a fitted scale, carried
        # through to scoring so a coverage figure can say how much of itself
        # rests on extrapolation.
        p["band_extended"] = np.isin(hs, sorted(self.spread_.extended_))
        return p

    def _all_quantiles(self) -> list[float]:
        qs = set()
        for lv in (self.level,) + self.levels:
            tail = (1.0 - lv) / 2.0
            qs.add(round(tail, 4))
            qs.add(round(1 - tail, 4))
        return sorted(qs)

    def predict_beyond_fit(self, iset, subs, horizons):
        return self.model.predict_beyond_fit(iset, subs, horizons)


# ---------------------------------------------------------------------------
# The self test
# ---------------------------------------------------------------------------
def self_test(n: int = 200_000, seed: int = 20260915,
              verbose: bool = True) -> None:
    """Does the arithmetic do what it claims, on a case whose answer is known?

    WHY THIS EXISTS AND WHY IT IS SYNTHETIC. Coverage measured on real hockey
    confounds two questions -- is the mixture inverted correctly, and is the
    spread fitted well -- and only the second one is interesting. Here the
    truth is constructed: seasons are drawn from a mixture whose parameters
    we chose, the same parameters are handed to the quantile function, and
    the stated range must then contain the outcome at the stated rate. Any
    gap is an error in the arithmetic, because there is nothing else left.

    The cases are chosen to be the ones that break a naive implementation:
    a fringe player whose honest tenth percentile is exactly zero, a star
    whose lump is negligible, and a lopsided shape, which is what real win
    totals have.
    """
    rng = np.random.default_rng(seed)
    # A deliberately lopsided shape: a long right tail and a short left one,
    # centred so it has no mean offset of its own.
    shape = rng.gumbel(0.0, 1.0, size=50_000)
    shape = (shape - shape.mean()) / shape.std()
    zs = np.sort(shape)

    failures = []
    for label, p_play, mu, sigma in [
        ("a fringe player, half likely to play", 0.50, 0.40, 0.55),
        ("a regular", 0.92, 1.10, 0.70),
        ("a star", 0.99, 3.00, 1.10),
        ("a player the model expects to be replacement level", 0.75, 0.00, 0.50),
        ("a negative forecast", 0.60, -0.30, 0.45),
    ]:
        plays = rng.random(n) < p_play
        draw = mu + sigma * zs[rng.integers(0, len(zs), size=n)]
        y = np.where(plays, draw, 0.0)
        for level in REPORT_LEVELS:
            tail = (1 - level) / 2
            lo = float(mixture_quantile(tail, np.full(1, p_play), np.full(1, mu),
                                        np.full(1, sigma), zs)[0])
            hi = float(mixture_quantile(1 - tail, np.full(1, p_play), np.full(1, mu),
                                        np.full(1, sigma), zs)[0])
            # THE SHARP CHECK. Compare each stated endpoint against the
            # quantile of the simulated seasons themselves. Coverage alone is
            # a weaker test: a band that is too wide on the left and too
            # narrow on the right covers the right share of outcomes while
            # being wrong at both ends. This compares the ends.
            #
            # It also handles the lump without a special case. When the true
            # quantile IS zero -- which happens whenever the probability level
            # falls inside the lump -- the simulated quantile is zero too, so
            # the two still have to agree.
            e_lo, e_hi = (float(v) for v in np.quantile(y, [tail, 1 - tail]))
            tol = 0.02 + 0.02 * sigma      # Monte Carlo error at 200k draws
            if abs(lo - e_lo) > tol or abs(hi - e_hi) > tol:
                failures.append(
                    f"{label} at {level:.0%}: stated [{lo:+.3f}, {hi:+.3f}], "
                    f"simulated [{e_lo:+.3f}, {e_hi:+.3f}]")
            # And coverage, which is what the harness will score, must land on
            # the stated level -- except where a stated end sits on the lump,
            # in which case the interval necessarily holds MORE than it claims
            # and cannot do otherwise.
            cov = float(((y >= lo) & (y <= hi)).mean())
            on_lump = abs(lo) < 1e-12 or abs(hi) < 1e-12
            if cov < level - 0.01 or (not on_lump and cov > level + 0.01):
                failures.append(f"{label} at {level:.0%}: covered {cov:.1%}")

    # THE MEAN OF THE DISTRIBUTION IS THE FORECAST, at nonzero uncertainty.
    # The zero-spread identity below checks the case where the shape has been
    # replaced by zeros, which cannot catch an off-centre shape because there
    # is no shape left to be off centre. This is the test that can.
    #
    # IT IS RUN BOTH WAYS ON PURPOSE. The shape used everywhere else in this
    # test was standardised when it was built, so it is centred already and a
    # check run only on it would pass whatever the calibrator did -- a guard
    # nobody has seen fail. So the first half feeds in a shape with a real mean
    # (a raw Gumbel, mean about +0.58) and REQUIRES the gap to appear; the
    # second half centres it the way the calibrator does and requires the gap
    # to close. A change that stopped centring would fail the second half; a
    # change that broke the integration, the inversion or the handling of the
    # lump would fail the first.
    raw = np.sort(rng.gumbel(0.0, 1.0, size=50_000))
    centred = raw - _grid_mean(raw)
    cases = [("a fringe player", 0.50, 0.40, 0.55),
             ("a star", 0.99, 3.00, 1.10),
             ("a negative forecast", 0.60, -0.30, 0.45),
             ("a replacement-level forecast", 0.75, 0.00, 0.50)]
    for label, p_play, mu, sigma in cases:
        want = p_play * mu
        off = float(mixture_mean(np.full(1, p_play), np.full(1, mu),
                                 np.full(1, sigma), raw)[0])
        # An uncentred shape must visibly move the mean, or this check is
        # asleep. The expected gap is p_play * sigma * E[Z].
        expect_gap = p_play * sigma * _grid_mean(raw)
        if abs((off - want) - expect_gap) > 5e-3:
            failures.append(
                f"{label}: an uncentred shape should shift the mean by "
                f"{expect_gap:+.4f}; it shifted it by {off - want:+.4f}")
        on = float(mixture_mean(np.full(1, p_play), np.full(1, mu),
                                np.full(1, sigma), centred)[0])
        if abs(on - want) > 2e-3:
            failures.append(
                f"{label}: with the shape centred the distribution's mean is "
                f"{on:+.4f} where the forecast it is built around is {want:+.4f}")

    # And the degenerate case that Phase 5 will lean on: with no spread and
    # certain participation, every quantile must collapse onto the point
    # forecast. This is the same identity the plan asks the simulation to
    # satisfy, one layer down.
    z0 = np.zeros(1001)
    for q in (0.05, 0.5, 0.95):
        x = mixture_quantile(q, np.array([1.0]), np.array([1.234]),
                             np.array([1e-12]), z0)
        if abs(float(x[0]) - 1.234) > 1e-6:
            failures.append(f"zero-spread identity at q={q}: got {float(x[0])}")

    if failures:
        raise AssertionError("predictive_interval self test FAILED:\n  " +
                             "\n  ".join(failures))
    if verbose:
        print(f"predictive_interval self test PASSED "
              f"({len(REPORT_LEVELS)} levels x 5 player types, {n:,} draws each)")


if __name__ == "__main__":
    self_test()
