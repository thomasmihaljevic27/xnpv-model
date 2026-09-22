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

    THE LEAGUE MINIMUM. A club cannot pay less than the floor, so a season
    where the player collapses costs the same as a season where he is merely
    poor. The downside is truncated and the upside is not, which makes the
    value of a path convex from below in its production, so the average of the
    values sits ABOVE the value of the average -- and by more for a player
    whose paths straddle the floor than for one whose do not.

    THAT IS THE ONLY CONVEXITY HERE. An earlier version of this comment also
    credited the censored price line with bending near the floor. It does not:
    `predict_tobit` returns a linear predictor, and censoring changes the
    fitted coefficients rather than the shape of the prediction. The floor that
    is applied afterwards is the whole of it.

    The gap is not a correction to the point valuation; it is the quantity the
    point valuation was approximating. A point valuation is also not wrong to
    average under dependence -- an expectation averages whatever the dependence
    is. What dependence changes is the SPREAD, and the value of a path once the
    price line stops being straight.

WHAT IS DRAWN, AND WHAT MAKES IT JOINT
    Two things per season, and the second one is why the plan asked for this.

    1. WHETHER HE IS IN THE LEAGUE AT ALL, as a path rather than a probability.
       The point chain multiplies each season's production by that season's
       probability of playing, which prices every player as a blend of himself
       and a ghost who plays 78% of a season. On a path he plays or he does
       not, a man who sits out may come back, and the model's own marginal
       probabilities are reproduced exactly by construction -- so nothing about
       the forecast changes, and what changes is that the zeros arrive together
       instead of being smeared across every season.

    2. HOW WRONG THE FORECAST IS, CORRELATED ACROSS SEASONS. This decides how
       uncertain a long contract is. If the misses were independent, a six-year
       deal's total would be six draws averaging out and its spread would scale
       as the square root of the term; if a miss persisted entirely it would
       scale with the term. Measured on the replayed misses, the same player's
       standardised miss correlates about 0.4 between adjacent seasons at every
       page in the window, so neither.

       THE SPLIT BETWEEN PERMANENT AND FADING IS A MODEL, NOT A MEASUREMENT.
       It is fitted per page, it moves a great deal across pages while the
       total adjacent correlation barely moves, and the parameters describe
       rank dependence imposed through a copula. They are not identified
       fractions of mistakes caused by permanent as against temporary things.

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

SCRIPT_VERSION = "1.2"

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
        return self._fit_curve(gaps, y)

    def _fit_curve(self, gaps: np.ndarray, y: np.ndarray) -> "Persistence":
        """The curve rho(gap) = w_perm + w_fade * phi ** gap through the
        observed rank correlations. Separate from `fit` so the search can be
        checked on a curve whose right answer is known."""
        gaps = np.asarray(gaps, dtype=float)
        y = np.asarray(y, dtype=float)
        # phi is searched on a grid and the two weights solved for each
        # candidate, which avoids an optimiser and its starting point.
        #
        # THE WEIGHTS ARE CONSTRAINED INSIDE THE SEARCH, NOT CLIPPED AFTER IT.
        # A negative weight would say a miss reverses itself with distance, and
        # the two together cannot exceed one. The first version solved each
        # candidate unconstrained, kept the phi with the lowest UNCONSTRAINED
        # error, and clipped the winner afterwards -- so the curve it returned
        # was never one the search had scored. On the goalie 2018 page the
        # observed correlations were 0.25, 0.21 and 0.06 at one, two and three
        # seasons; the unconstrained winner had a negative permanent part and
        # phi at the top of the grid, and clipping turned it into 0.95 ** gap:
        # a miss that persists almost entirely, on data that says a quarter of
        # it does. Now every candidate is fitted within the constraints
        # (non-negative least squares, then the sum held to one), and phi is
        # chosen on the error of the curve actually returned.
        from scipy.optimize import nnls
        best = None
        for phi in np.linspace(0.05, 0.95, 91):
            X = np.column_stack([np.ones_like(gaps, dtype=float), phi ** gaps])
            coef, _ = nnls(X, y)
            if coef.sum() > 1.0:
                # On the boundary w_perm + w_fade = 1: y - phi**g =
                # w_perm * (1 - phi**g), one parameter, held to [0, 1].
                u = 1.0 - X[:, 1]
                wp = float(np.clip((u @ (y - X[:, 1])) / max(u @ u, 1e-12), 0.0, 1.0))
                coef = np.array([wp, 1.0 - wp])
            sse = float(((X @ coef - y) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, float(phi), float(coef[0]), float(coef[1]))
        self.sse_, self.phi_, self.w_perm_, self.w_fade_ = best
        return self

    def rho(self, gap) -> np.ndarray:
        gap = np.asarray(gap, dtype=float)
        return np.where(gap == 0, 1.0,
                        self.w_perm_ + self.w_fade_ * self.phi_ ** gap)

    @staticmethod
    def gaussian_from_rank(rho_s):
        """The latent Gaussian correlation that DELIVERS a given rank
        correlation through a Gaussian copula.

        THIS CONVERSION WAS MISSING AND THE OMISSION WAS THE BUG. The
        persistence is measured as a Spearman rank correlation, which is the
        right thing to measure on a long-tailed shape, and the fitted numbers
        were then handed straight to the normal draws as if the two scales were
        the same. They are not: a Gaussian copula with latent correlation r
        produces rank correlation

            rho_s = (6 / pi) * arcsin(r / 2)

        which is always a little below r. Feeding 0.427 in as r delivered 0.410
        of rank correlation -- close enough that a three-thousand-path check
        could not see it, and far enough to be wrong. Inverting gives what to
        ask the normals for:

            r = 2 * sin(pi * rho_s / 6)
        """
        return 2.0 * np.sin(np.pi * np.asarray(rho_s, dtype=float) / 6.0)

    @staticmethod
    def rank_from_gaussian(r):
        """The inverse, used by the self test to check the relationship holds
        as arithmetic rather than only as a simulated average."""
        return (6.0 / np.pi) * np.arcsin(np.asarray(r, dtype=float) / 2.0)

    def matrix(self, T: int) -> np.ndarray:
        """The LATENT GAUSSIAN correlation matrix for a T-season term, built so
        that the RANK correlations it delivers are the fitted ones, and nudged
        to the nearest usable matrix if that shape is not quite positive
        definite."""
        i = np.arange(T)
        R = self.gaussian_from_rank(self.rho(np.abs(i[:, None] - i[None, :])))
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


def return_rate(table: pd.DataFrame, before: int, lookback: int = 2) -> float:
    """How often a player who has just dropped out plays again the next season.

    Estimated on seasons that completed before `before`, so a path drawn at a
    decision date uses only what that date could know.

    The population is a FRESH absence: a player who appeared within the last
    `lookback` seasons and did not appear this one. Counting every season after
    a career ends instead would drive the answer to nearly zero, because a
    retired player is absent forever and each of those seasons would be another
    failure to return. The question is what happens after a man misses a year,
    not what happens after he stops playing.
    """
    t = table[table["syr"] < before]
    played = {(r.career_key, int(r.syr)) for r in
              t[t["GP"] >= C.PARTICIPATION_GP].itertuples()}
    seasons = sorted({int(x) for x in t["syr"].unique()})
    if len(seasons) < 3:
        return 0.0
    careers = {k for k, _ in played}
    out_n = back_n = 0
    for yr in seasons[lookback:-1]:
        for k in careers:
            if (k, yr) in played:
                continue
            if not any((k, yr - j) in played for j in range(1, lookback + 1)):
                continue                       # not a fresh absence
            out_n += 1
            back_n += (k, yr + 1) in played
    return float(back_n / out_n) if out_n else 0.0


def exit_schedule(p_play: np.ndarray, r_return: float = 0.0):
    """The chance of dropping out in each season, solved so the model's own
    marginal probability of playing still comes back exactly:

        S[h] = S[h-1] * (1 - exit[h]) + (1 - S[h-1]) * r_return

    Returned separately from the path because the control-year work needs it
    for a different question -- what a club, standing at a control year and
    knowing whether the player is in the league, should expect next season --
    and a second copy of this solve is how a rule drifts.
    """
    S = np.clip(np.asarray(p_play, dtype=float), 1e-9, 1.0)
    T = len(S)
    e = np.empty(T)
    e[0] = 0.0
    clipped = 0
    for h in range(1, T):
        raw = 1.0 - (S[h] - (1.0 - S[h - 1]) * r_return) / max(S[h - 1], 1e-12)
        e[h] = min(max(raw, 0.0), 1.0)
        clipped += int(raw < -1e-9 or raw > 1 + 1e-9)
    return e, clipped


def participation_path(p_play: np.ndarray, u: np.ndarray,
                       r_return: float = 0.0) -> tuple[np.ndarray, int]:
    """Whether he is in the league each season, as a path that allows a return.

    THE ABSORBING VERSION WAS WRONG, AND THE ARGUMENT FOR IT WAS WORSE. It made
    an absence permanent and justified that by observing that no term in the
    sample asks for a probability of playing that RISES. That does not follow,
    and the review's counterexample settles it: sixty per cent of players play
    both seasons, thirty per cent only the first, ten per cent only the second.
    The marginal falls from 90% to 70% and one path in ten is a return. A
    falling marginal says nothing at all about whether anybody comes back.

    So this is a two-state chain. `r_return` is the chance a player who sat out
    plays again next season, estimated from seasons before the decision date.
    The chance of dropping out is then solved season by season so that the
    model's own marginals still come back exactly:

        S[h] = S[h-1] * (1 - exit[h]) + (1 - S[h-1]) * r_return

    Setting `r_return` to zero recovers the absorbing path, which is kept as
    the declared sensitivity rather than as the default.

    Returns the path and the number of seasons where the solved exit
    probability had to be clipped into [0, 1] -- where it does, the marginal is
    not reproduced exactly and the caller is told rather than not.
    """
    S = np.clip(np.asarray(p_play, dtype=float), 1e-9, 1.0)
    T = len(S)
    e, clipped = exit_schedule(p_play, r_return)

    out = np.empty(u.shape, dtype=float)
    alive = u[:, 0] < S[0]
    out[:, 0] = alive
    for h in range(1, T):
        stay = u[:, h] < (1.0 - e[h])
        come_back = u[:, h] < r_return
        alive = np.where(alive, stay, come_back)
        out[:, h] = alive
    return out, clipped


def rising_marginals(p_play: np.ndarray) -> int:
    """How many seasons of this term ask for a probability of playing higher
    than the season before, which the absorbing path cannot deliver."""
    return int((np.diff(np.asarray(p_play, dtype=float)) > 1e-9).sum())


def draw_paths(mu, sigma, p_play, shape: np.ndarray, persistence: Persistence,
               n_paths: int = DEFAULT_PATHS, rng=None,
               r_return: float = 0.0, normals=None, u_part=None,
               return_parts: bool = False):
    """One player, one contract: `n_paths` draws of production per season.

    Returns an array of shape (n_paths, T) in wins, with a zero wherever the
    path has him out of the league.

    `return_parts` also hands back the correlated normals behind the draws and
    the played/not-played indicator. The control-year work needs both: a club
    standing at a control year knows how wrong the forecast has been so far
    (the normals) and whether the player is in the league (the indicator), and
    a produced zero cannot stand in for the second because a player who plays
    badly enough produces zero or less.
    """
    rng = np.random.default_rng() if rng is None else rng
    mu = np.asarray(mu, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    p_play = np.clip(np.asarray(p_play, dtype=float), 1e-9, 1.0)
    T = len(mu)

    # THE COPULA. Correlated normals to uniforms to the empirical shape, so
    # every season keeps the distribution the interval layer fitted and only
    # their dependence is imposed.
    # COMMON DRAWS when the caller supplies them, so two variants of the same
    # contract can be compared on the same randomness instead of on two
    # samples that differ by luck as well as by design.
    L = np.linalg.cholesky(persistence.matrix(T))
    raw = rng.standard_normal((n_paths, T)) if normals is None else normals[:, :T]
    g = raw @ L.T
    u = stats.norm.cdf(g)
    if len(shape) and np.ptp(shape) > 0:
        grid = np.linspace(0.0, 1.0, len(shape))
        z = np.interp(u, grid, shape)
    else:
        z = np.zeros_like(u)            # the zero-spread case, exactly
    cond = mu[None, :] + sigma[None, :] * z

    # THE PARTICIPATION DRAWS ARE SHARED TOO WHEN THE CALLER SUPPLIES THEM.
    # The runner built these and then never passed them, so two arms of a
    # comparison shared their performance draws and redrew participation
    # independently. That left avoidable sampling noise in every difference and
    # made the one-season identity approximate when it should be exact.
    u = rng.random((n_paths, T)) if u_part is None else u_part[:, :T]
    played, _ = participation_path(p_play, u, r_return)
    if return_parts:
        return cond * played, g, played
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
    """What the arithmetic has to do, on cases whose answers are known.

    THE DEPENDENCE IS CHECKED AS ARITHMETIC FIRST. A Monte Carlo check on a
    correlation cannot tell a small systematic error from a small sampling one
    without a very large sample, and the previous version of this test could
    not: the rank-to-Gaussian conversion was missing, the delivered correlation
    was 0.41 against a requested 0.43, and three thousand paths never saw it.
    So the relationship is now checked in closed form, where the error is
    either there or it is not, and the simulated check is a sanity test on top
    with a tolerance derived from the sampling error of a rank correlation
    rather than chosen to pass.
    """
    rng = np.random.default_rng(seed)
    shape = np.sort(rng.gumbel(0.0, 1.0, 20_000))
    shape = shape - np.trapezoid(shape, dx=1.0 / (len(shape) - 1))

    pers = Persistence()
    pers.w_perm_, pers.w_fade_, pers.phi_ = 0.19, 0.24, 0.60

    failures = []

    # -- the conversion, in closed form ------------------------------------
    for target in (0.05, 0.2, 0.4266, 0.6, 0.85):
        r = Persistence.gaussian_from_rank(target)
        back = float(Persistence.rank_from_gaussian(r))
        if abs(back - target) > 1e-12:
            failures.append(f"rank {target} maps to a matrix delivering {back}")
    R = pers.matrix(4)
    for gap in (1, 2, 3):
        want = float(pers.rho(gap))
        got = float(Persistence.rank_from_gaussian(R[0, gap]))
        if abs(got - want) > 1e-10:
            failures.append(f"matrix at gap {gap} delivers rank {got}, fitted {want}")

    mu = np.array([1.2, 1.1, 1.0, 0.9, 0.8, 0.7])
    sigma = np.array([0.7, 0.8, 0.85, 0.9, 0.95, 1.0])
    paths = draw_paths(mu, sigma, np.ones(6), shape, pers, n_paths, rng)

    # -- the marginals are untouched ---------------------------------------
    for h in range(6):
        want = mu[h] + sigma[h] * np.quantile(shape, [0.1, 0.5, 0.9])
        got = np.quantile(paths[:, h], [0.1, 0.5, 0.9])
        # Scales with the sample, because a sample quantile's error does.
        if np.max(np.abs(got - want)) > 10.0 * sigma[h] / np.sqrt(n_paths):
            failures.append(f"season {h} marginal moved: {got} against {want}")

    # -- and the dependence is the one asked for ---------------------------
    want_rho = float(pers.rho(1))
    got_rho = float(stats.spearmanr(paths[:, 0], paths[:, 1]).statistic)
    # Four standard errors of a rank correlation at this sample size.
    tol = 4.0 * (1.0 - want_rho ** 2) / np.sqrt(n_paths)
    if abs(got_rho - want_rho) > tol:
        failures.append(f"adjacent rank correlation {got_rho:.4f} against "
                        f"{want_rho:.4f}, tolerance {tol:.4f}")

    # -- participation: marginals hold, and returns happen -----------------
    p = np.array([0.95, 0.90, 0.82, 0.73, 0.61, 0.48])
    for r_ret, label in ((0.0, "absorbing"), (0.18, "with returns")):
        alive, clipped = participation_path(p, rng.random((60_000, 6)), r_ret)
        if clipped:
            failures.append(f"{label}: {clipped} seasons could not hold the marginal")
        if np.max(np.abs(alive.mean(axis=0) - p)) > 4.0 / np.sqrt(60_000):
            failures.append(f"{label}: marginals off, {alive.mean(axis=0)} against {p}")
        came_back = int(((alive[:, :-1] == 0) & (alive[:, 1:] == 1)).sum())
        if r_ret == 0.0 and came_back:
            failures.append(f"absorbing path let {came_back} players return")
        if r_ret > 0.0 and came_back == 0:
            failures.append("return-capable path produced no returns at all")

    # -- the identity ------------------------------------------------------
    flat = draw_paths(mu, np.zeros(6), np.ones(6), np.zeros(1001), pers, 64, rng)
    if np.max(np.abs(flat - mu[None, :])) > 1e-12:
        failures.append("zero-spread paths are not the point forecast")

    if failures:
        raise AssertionError("npv_simulation self test FAILED:\n  " + "\n  ".join(failures))
    if verbose:
        print(f"npv_simulation self test PASSED ({n_paths:,} paths)")


if __name__ == "__main__":
    self_test(verbose=True)
