"""npv_simulation.py -- a contract's value as a distribution over career paths.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5.

WHAT A POINT VALUATION CANNOT DO
    The chain values a contract by taking one forecast per season, averaging it
    into a production per season, and pushing that through the price line. That
    is the value of the AVERAGE path. A contract is worth the AVERAGE OF THE
    VALUES, and the two differ whenever the price of a path is not a straight
    line in the production on it.

    It is not a straight line, for two reasons that both matter here and both
    push the same way:

    - THE LEAGUE MINIMUM. A club cannot pay less than the floor, so a season
      where the player collapses costs the same as a season where he is merely
      poor. The downside is truncated and the upside is not.
    - THE CENSORED PRICE LINE. The market's own fit is censored at that floor,
      so the price of forecast production bends near the bottom.

    Both make the value of a path convex from below in its production, so the
    average of the values sits ABOVE the value of the average, and by more for
    a player whose paths straddle the floor than for one whose do not. That gap
    is what this file computes. It is not a correction to the point valuation;
    it is the quantity the point valuation was approximating.

WHAT IS DRAWN, AND WHAT MAKES IT JOINT
    Two things per season, and the second one is why the plan asked for this.

    1. WHETHER HE IS IN THE LEAGUE AT ALL, as a path rather than a probability.
       The point chain multiplies each season's production by that season's
       probability of playing, which prices every player as a blend of himself
       and a ghost who plays 78% of a season. On a path he either plays or he
       does not, and an exit carries forward: a player gone in year three is
       gone in years four and five. The marginal probabilities the
       participation model reports are reproduced exactly by construction, so
       nothing about the forecast changes -- what changes is that the zeros now
       arrive together instead of being smeared across every season.

    2. HOW WRONG THE FORECAST IS, CORRELATED ACROSS SEASONS. This is the part
       that decides everything about a long contract, and it had never been
       measured. If the misses were independent, a six-year deal's total would
       be six draws averaging out and its spread would scale as the square root
       of the term. If a miss persisted entirely, the spread would scale with
       the term itself. Measured on the replayed misses, the same player's
       standardised miss correlates 0.39 between adjacent seasons, decaying to
       a floor near 0.19 five seasons apart -- so neither. Some of being wrong
       about a player is a permanent misjudgement and some of it washes out,
       and the mix is fitted rather than assumed.

    ONE THING IS DELIBERATELY NOT DRAWN SEPARATELY. The rate per 82 and the
    share of the schedule are not given their own draws, because the quantity
    with a fitted spread is the season TOTAL given he played, and that total's
    miss already contains both -- a player who was healthy but worse and a
    player who was as good but hurt are both in it. Splitting them would need
    two spreads where the data supports one, and their product is what a dollar
    total reads anyway.

HOW THE MARGINALS SURVIVE
    The dependence is imposed with a Gaussian copula: correlated normals,
    pushed through the normal CDF to uniforms, then through the empirical shape
    the interval layer already fitted. That leaves each season's own
    distribution EXACTLY as it was -- the same shape whose coverage has been
    measured and reviewed -- and changes only how the seasons move together.
    A scheme that added a shared shock to each season would have changed both
    at once, and the marginal it changed is the one with evidence behind it.

THE IDENTITY THIS HAS TO SATISFY
    With the spread set to nothing and participation certain, every path is the
    same path and the simulation must return the point valuation exactly. The
    plan asks for that guard in place of the retired k=0 identity, and it is
    the reason the arithmetic below is written to collapse rather than to
    approximate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C

SCRIPT_VERSION = "1.0"

DEFAULT_PATHS = 2000        # matches the draft bootstrap's resample count
MIN_PAIRS = 200             # a horizon pair needs this many players to count


class Persistence:
    """How much of a miss about one player comes back the following season.

    Fitted as a permanent part plus a part that fades:

        rho(gap) = w_perm + w_fade * phi ** gap

    The permanent part is a standing misjudgement of the player -- the model
    has him wrong and goes on having him wrong. The fading part is a run of
    form, an injury, a role, something that passes. Three numbers, fitted on
    the rank correlations between the same player's standardised misses at
    different horizons on the same page.

    RANK correlation rather than linear, because the shape has a long right
    tail and one career year would otherwise set the parameter.
    """

    def __init__(self):
        self.w_perm_ = 0.0
        self.w_fade_ = 0.0
        self.phi_ = 0.5
        self.observed_: dict[int, float] = {}
        self.n_ = 0

    def fit(self, pairs: pd.DataFrame, scale) -> "Persistence":
        """`pairs` is the interval layer's replayed misses; `scale` turns a
        miss into a standardised one at its own horizon."""
        d = pairs.copy()
        d["z"] = d["r"].to_numpy() / np.maximum(
            scale(d["h"].to_numpy(), d["mu"].to_numpy()), 1e-9)
        w = d.pivot_table(index=["page", "career_key"], columns="h", values="z")
        hs = sorted(int(c) for c in w.columns)
        obs: dict[int, list[float]] = {}
        for i, a in enumerate(hs):
            for b in hs[i + 1:]:
                pair = w[[a, b]].dropna()
                if len(pair) < MIN_PAIRS:
                    continue
                r = pair[a].corr(pair[b], method="spearman")
                if np.isfinite(r):
                    obs.setdefault(b - a, []).append(float(r))
                    self.n_ += len(pair)
        self.observed_ = {g: float(np.mean(v)) for g, v in obs.items()}
        if len(self.observed_) < 2:
            # Not enough evidence to separate permanent from fading. Fall back
            # to treating every season's miss as independent, which is the
            # assumption a point valuation already makes, and say so.
            self.w_perm_ = self.w_fade_ = 0.0
            return self

        gaps = np.array(sorted(self.observed_))
        y = np.array([self.observed_[g] for g in gaps])
        # phi is searched on a grid and the two weights solved in closed form
        # for each candidate, which avoids an optimiser and its starting point.
        best = None
        for phi in np.linspace(0.05, 0.95, 91):
            X = np.column_stack([np.ones_like(gaps, dtype=float), phi ** gaps])
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            sse = float(((X @ coef - y) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, float(phi), float(coef[0]), float(coef[1]))
        _, self.phi_, w_perm, w_fade = best
        # A NEGATIVE WEIGHT IS REFUSED rather than carried. Either part going
        # below zero would say a miss reverses itself with distance, which no
        # pair in the table shows; it is what a three-parameter fit does to a
        # five-point curve when the curve is nearly flat.
        self.w_perm_ = float(np.clip(w_perm, 0.0, 1.0))
        self.w_fade_ = float(np.clip(w_fade, 0.0, 1.0 - self.w_perm_))
        return self

    def rho(self, gap) -> np.ndarray:
        gap = np.asarray(gap, dtype=float)
        return np.where(gap == 0, 1.0,
                        self.w_perm_ + self.w_fade_ * self.phi_ ** gap)

    def matrix(self, T: int) -> np.ndarray:
        """The correlation matrix for a T-season term, nudged to the nearest
        usable one if the fitted shape is not quite positive definite."""
        i = np.arange(T)
        R = self.rho(np.abs(i[:, None] - i[None, :]))
        R[np.diag_indices(T)] = 1.0
        vals, vecs = np.linalg.eigh(R)
        if vals.min() < 1e-8:
            R = vecs @ np.diag(np.clip(vals, 1e-8, None)) @ vecs.T
            dg = np.sqrt(np.diag(R))
            R = R / np.outer(dg, dg)
        return R

    def report(self) -> list[str]:
        out = [f"  a miss persists: {self.w_perm_:.3f} permanently, plus "
               f"{self.w_fade_:.3f} fading at {self.phi_:.2f} a season",
               f"  {'seasons apart':<16}{'observed':>10}{'fitted':>9}"]
        for g in sorted(self.observed_):
            out.append(f"  {g:<16}{self.observed_[g]:>10.3f}"
                       f"{float(self.rho(g)):>9.3f}")
        return out


def survival_path(p_play: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Whether he is in the league each season, as an absorbing path.

    `p_play[h]` is the model's marginal probability of playing in season h.
    The conditional chance of still being there given he was there last season
    is the ratio of consecutive marginals, so drawing sequentially reproduces
    those marginals exactly while making an exit stick.

    RETURNS ARE NOT MODELLED HERE. The participation model allows a player to
    come back after a missed season, and roughly one exiter in five does. On a
    path that shows up as a marginal probability that RISES, which this rule
    cannot honour -- the ratio is clipped at one and the player stays gone. The
    effect is to understate how often a path recovers, and it is reported by
    `rising_marginals()` rather than left silent.
    """
    T = len(p_play)
    q = np.empty(T)
    q[0] = p_play[0]
    q[1:] = np.clip(p_play[1:] / np.maximum(p_play[:-1], 1e-12), 0.0, 1.0)
    alive = np.ones(u.shape[0], dtype=bool)
    out = np.empty(u.shape, dtype=float)
    for h in range(T):
        alive = alive & (u[:, h] < q[h])
        out[:, h] = alive
    return out


def rising_marginals(p_play: np.ndarray) -> int:
    """How many seasons of this term ask for a probability of playing higher
    than the season before, which the absorbing path cannot deliver."""
    return int((np.diff(np.asarray(p_play, dtype=float)) > 1e-9).sum())


def draw_paths(mu, sigma, p_play, shape: np.ndarray, persistence: Persistence,
               n_paths: int = DEFAULT_PATHS, rng=None) -> np.ndarray:
    """One player, one contract: `n_paths` draws of production per season.

    Returns an array of shape (n_paths, T) in wins, with a zero wherever the
    path has him out of the league.
    """
    rng = np.random.default_rng() if rng is None else rng
    mu = np.asarray(mu, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    p_play = np.clip(np.asarray(p_play, dtype=float), 1e-9, 1.0)
    T = len(mu)

    # THE COPULA. Correlated normals to uniforms to the empirical shape, so
    # every season keeps the distribution the interval layer fitted and only
    # their dependence is imposed.
    L = np.linalg.cholesky(persistence.matrix(T))
    g = rng.standard_normal((n_paths, T)) @ L.T
    u = stats.norm.cdf(g)
    if len(shape) and np.ptp(shape) > 0:
        grid = np.linspace(0.0, 1.0, len(shape))
        z = np.interp(u, grid, shape)
    else:
        z = np.zeros_like(u)            # the zero-spread case, exactly
    cond = mu[None, :] + sigma[None, :] * z

    played = survival_path(p_play, rng.random((n_paths, T)))
    return cond * played


def contract_value(currency, row: pd.Series, war_per_season, war_year1,
                   k_dollars: float) -> np.ndarray:
    """Dollars for many paths of one contract, in one call.

    `k_dollars` is the contract's cap-path-and-discount factor, which depends
    on the contract and not on the path, so it is computed once by
    `dollar_factor` and multiplied in. Without that this would call the
    currency's own per-row loop once per path, and a two-thousand-path run over
    a thousand contracts would spend all its time rebuilding the same cap path.
    """
    from production_currency import FEATURES
    from contract_price_model import predict_tobit

    n = len(np.atleast_1d(war_per_season))
    X = np.empty((n, len(FEATURES)))
    for j, f in enumerate(FEATURES):
        if f == "war_per_season":
            X[:, j] = war_per_season
        elif f == "war_year1":
            X[:, j] = war_year1
        elif f == "rfa_x_war":
            X[:, j] = float(row["is_RFA"]) * np.asarray(war_per_season)
        else:
            X[:, j] = float(row[f])
    if currency.term_mode == "free":
        X[:, FEATURES.index("length")] = 1.0
        X[:, FEATURES.index("one_year")] = 1.0
    share = np.maximum(predict_tobit(currency.coef_, X),
                       float(row["floor_share"]))
    return share * k_dollars


def dollar_factor(row: pd.Series) -> float:
    """The cap ceiling in each contract season, discounted from the signing and
    summed. Multiplying a cap share by this gives dollars."""
    from production_currency import _offset
    yrs = list(range(int(row["start_yr"]), int(row["end_yr"]) + 1))
    path = C.cap_path(row["signed"], yrs)
    return float(sum(path[y] / (1.0 + C.DISCOUNT_RATE) ** _offset(row["signed"], y)
                     for y in yrs))


def self_test(n_paths: int = 4000, seed: int = 20260916,
              verbose: bool = False) -> None:
    """Three things the arithmetic has to do, on cases whose answers are known.

    1. THE MARGINALS SURVIVE THE COPULA. Correlating the seasons must not move
       any season's own distribution, because that distribution is the one with
       measured coverage behind it.
    2. THE PARTICIPATION PATH REPRODUCES ITS MARGINALS, while making an exit
       absorbing. Those two are in tension and the construction has to satisfy
       both.
    3. THE ZERO-UNCERTAINTY IDENTITY. With no spread and certain participation,
       every path is the point forecast. This is the guard the plan asks for in
       place of the retired k=0 identity.
    """
    rng = np.random.default_rng(seed)
    shape = np.sort(rng.gumbel(0.0, 1.0, 20_000))
    shape = shape - np.trapezoid(shape, dx=1.0 / (len(shape) - 1))

    pers = Persistence()
    pers.w_perm_, pers.w_fade_, pers.phi_ = 0.19, 0.24, 0.60

    failures = []
    mu = np.array([1.2, 1.1, 1.0, 0.9, 0.8, 0.7])
    sigma = np.array([0.7, 0.8, 0.85, 0.9, 0.95, 1.0])

    # 1. marginals unchanged by the dependence
    paths = draw_paths(mu, sigma, np.ones(6), shape, pers, n_paths, rng)
    for h in range(6):
        want = mu[h] + sigma[h] * np.quantile(shape, [0.1, 0.5, 0.9])
        got = np.quantile(paths[:, h], [0.1, 0.5, 0.9])
        # THE TOLERANCE SCALES WITH THE SAMPLE, because a sample quantile's own
        # error does. It was a flat 0.12, which passed at four thousand paths
        # and failed at three thousand on the ninetieth percentile -- not
        # because anything was wrong but because the shape has a long right
        # tail, the density out there is thin, and that quantile is the noisiest
        # thing being checked. A constant tolerance on a Monte Carlo quantity is
        # a check that passes or fails on the draw count.
        tol = 10.0 * sigma[h] / np.sqrt(n_paths)
        if np.max(np.abs(got - want)) > tol:
            failures.append(f"season {h} marginal moved: {got} against {want}")

    # and the dependence is actually there
    got_rho = stats.spearmanr(paths[:, 0], paths[:, 1]).statistic
    if abs(got_rho - pers.rho(1)) > 3.0 / np.sqrt(n_paths) + 0.01:
        failures.append(f"adjacent correlation {got_rho:.3f}, asked for {float(pers.rho(1)):.3f}")

    # 2. participation marginals, and exits that stick
    p = np.array([0.95, 0.90, 0.82, 0.73, 0.61, 0.48])
    alive = survival_path(p, rng.random((40_000, 6)))
    if np.max(np.abs(alive.mean(axis=0) - p)) > 0.01:
        failures.append(f"participation marginals off: {alive.mean(axis=0)} against {p}")
    revived = int(((alive[:, :-1] == 0) & (alive[:, 1:] == 1)).sum())
    if revived:
        failures.append(f"{revived} paths came back after leaving; exit must absorb")

    # 3. the identity
    flat = draw_paths(mu, np.zeros(6), np.ones(6), np.zeros(1001), pers, 64, rng)
    if np.max(np.abs(flat - mu[None, :])) > 1e-12:
        failures.append("zero-spread paths are not the point forecast")

    if failures:
        raise AssertionError("npv_simulation self test FAILED:\n  " + "\n  ".join(failures))
    if verbose:
        print(f"npv_simulation self test PASSED ({n_paths:,} paths)")


if __name__ == "__main__":
    self_test(verbose=True)
