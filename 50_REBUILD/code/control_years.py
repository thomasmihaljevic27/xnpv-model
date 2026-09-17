"""control_years.py -- what a club still owns when the contract ends.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5: the RFA walk-away option and
the control years, which the simulator has been leaving out.

WHAT IS MISSING WITHOUT THIS
    When a contract expires the asset does not always expire with it. A player
    who reaches unrestricted free agency walks and the club keeps nothing. A
    player who is still RESTRICTED does not: the club holds his rights for
    every season until he becomes unrestricted, and it can keep him by tabling
    a qualifying offer -- a one-year offer whose size the CBA fixes off his
    last salary, usually far below what he is worth. Those seasons are an
    asset, and the simulator has been valuing 252 of the 1,217 development
    contracts as though they ended at expiry.

    It matters most where the simulator currently sits BELOW the production
    chain: 134 of those 252 are one-year deals and 87 are two-year deals.

WHY IT IS AN OPTION AND NOT A STREAM
    Control is a right, not an obligation. The club tables an offer while the
    player is worth more than the offer and walks away when he is not, and
    once it walks away the remaining control years are gone -- there is no
    skipping a year and re-qualifying later. So the value of the control years
    is the value of a stopping rule, and a stopping rule is worth more than
    the stream it stops.

    That is exactly the quantity a point valuation cannot reach. Production
    prices the same right (D13) by walking its single projected path and
    truncating at the first control year whose PROJECTED surplus goes
    negative. On one path that is the best it can do. Over drawn paths the
    club gets to be right sometimes, and the option is worth more.

WHAT THE CLUB IS ASSUMED TO KNOW -- the whole identification question here
    A stopping rule is only as honest as the information it stands on, and it
    is very easy to write one that quietly reads the future. So four rules are
    priced on the SAME draws, and they bracket the answer:

      committed      the club takes every control year, good or bad. Not a
                     right at all. The floor.
      declared       the club decides the whole schedule in advance, off the
                     point projection, before a single path is drawn. This is
                     production's rule (D13), and it uses no path information
                     whatsoever.
      informed       at each control year the club decides on what it knows
                     THEN: the forecast, updated by how wrong the forecast has
                     turned out so far on this path, and whether the player is
                     still in the league. It cannot see the season it is
                     deciding about. This is the honest rule.
      oracle         the club sees the season's realised production before
                     tendering. Impossible, and the ceiling.

    `informed` must land between `declared`/`committed` and `oracle`, and the
    runner asserts it. A rule that beat the oracle would be reading the future
    twice.

    The conditional update is the copula's own dependence, not a new model:
    the miss in each season is a standard normal before the empirical shape is
    applied, the fitted persistence gives their correlation matrix, so the
    club's expectation of next season is the linear projection of that normal
    on the misses it has already seen, integrated through the shape. Nothing
    is fitted here that was not already fitted for the paths.

THE QUALIFYING OFFER
    The CBA formula, iterated year over year (each offer is a one-year deal
    and the next one escalates off it), floored at that season's league
    minimum, with the 2026 CBA's bands from the 2026 offseason on. The bands
    are reimplemented here rather than imported from `20_CODE`, because this
    tree is meant to stand on the sources rather than on production's chain --
    and then checked against production's implementation when it can be
    imported, so the two cannot drift apart unnoticed.

    THE BASE SALARY IS AN APPROXIMATION HERE AND IT IS THE WEAK POINT. The
    formula runs off the final year's BASE SALARY, and the PuckPedia contract
    export this tree reads carries one row per contract with an average annual
    value, not a salary schedule. So the average is used, and
    `qo_base_divergence` measures what that costs against the per-season
    salaries production joins from the clause feed. The substitution matters
    in one direction only: a front-loaded deal's final salary sits above its
    average, so using the average UNDERSTATES the offer and overstates what
    the control year is worth.
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

# How many Gauss-Hermite nodes the conditional expectation integrates over.
# The club's expectation of next season is a normal pushed through the
# empirical shape, so it is an integral rather than a substitution; 15 nodes
# reproduce the unconditional mean of the shape to better than $1 of a win.
GH_NODES = 15


# ---------------------------------------------------------------------------
# QUALIFYING-OFFER MECHANICS
# ---------------------------------------------------------------------------
def qualifying_offer(prior_salary: float, prior_cap_hit: float,
                     offseason_year: int, signed_2020_plus: bool,
                     floor: float | None = None) -> float:
    """The CBA qualifying offer for one offseason, in dollars.

    `offseason_year` is the calendar summer, which is the season_start of the
    season the offer covers. A qualifying offer is a one-year deal, so its
    salary is also its cap hit and the next year's offer escalates off it.

    `floor` is that season's league minimum. Left out it is the published
    schedule in full, which is what production uses and what the drift check
    compares against; anything valuing a contract passes the minimum as its
    own signing date could have known it, because the 2026 CBA's schedule was
    not public until the summer of 2025.
    """
    if int(offseason_year) >= 2026:                     # 2026 CBA bands
        if prior_salary <= 1_250_000:
            qo = prior_salary * 1.10
        elif prior_salary < 1_750_000:
            qo = min(prior_salary * 1.05, 1_750_000)
        else:
            qo = min(prior_salary, 1.20 * prior_cap_hit)
    else:                                               # 2013/2020 CBA bands
        if prior_salary <= 660_000:
            qo = prior_salary * 1.10
        elif prior_salary < 1_000_000:
            qo = min(prior_salary * 1.05, 1_000_000)
        else:
            qo = prior_salary
            if signed_2020_plus:                        # anti-front-loading
                qo = min(qo, 1.20 * prior_cap_hit)
    if floor is None:
        floor = C.league_min_path(int(offseason_year))
    return max(qo, float(floor))


def _qo_self_test() -> None:
    """The bands, on cases whose answers are arithmetic. Runs on import so a
    typo in a threshold cannot ship."""
    f = qualifying_offer
    assert abs(f(600_000, 600_000, 2022, False) - 750_000) < 1      # 110%, floored
    assert abs(f(900_000, 900_000, 2022, False) - 945_000) < 1      # 105%
    assert abs(f(980_000, 980_000, 2022, False) - 1_000_000) < 1    # 105%, capped
    assert abs(f(4_000_000, 4_000_000, 2022, False) - 4_000_000) < 1
    assert abs(f(6_000_000, 4_000_000, 2022, True) - 4_800_000) < 1  # 120% of cap hit
    assert abs(f(1_200_000, 1_200_000, 2027, True) - 1_320_000) < 1  # new bands
    assert abs(f(1_700_000, 1_700_000, 2027, True) - 1_750_000) < 1
    assert abs(f(5_000_000, 5_000_000, 2027, True) - 5_000_000) < 1
    assert f(500_000, 500_000, 2024, False) == 775_000              # league min
    # THE FLOOR IS THE SEASON'S, NOT A CONSTANT. A control year past the
    # published schedule is priced off the grown minimum, and that has to
    # reach the offer rather than stopping at the table's last row.
    assert abs(f(500_000, 500_000, 2027, False) - 900_000) < 1
    # AND IT IS THE MINIMUM THE CALLER HANDS IT when the caller knows less
    # than the published schedule does.
    assert abs(f(500_000, 500_000, 2027, False, floor=822_198) - 822_198) < 1


_qo_self_test()


def qo_schedule(base_salary: float, cap_hit: float, years, signed_year: int,
                decision_date=None):
    """The offer in each control season, each one escalating off the last."""
    out, prior_sal, prior_hit = [], float(base_salary), float(cap_hit)
    for y in years:
        qo = qualifying_offer(prior_sal, prior_hit, int(y),
                              int(signed_year) >= 2020,
                              floor=C.league_min_path(int(y), decision_date))
        out.append(qo)
        # THE NEXT OFFER ESCALATES OFF THIS ONE, and a one-year offer's salary
        # is its cap hit, so both carry forward as the same number.
        prior_sal = prior_hit = qo
    return np.asarray(out, dtype=float)


def control_span(expiry_status, end_yr, ufa_year) -> list[int]:
    """The seasons a club holds the player's rights for after the contract.

    Empty unless the contract expires with the player still restricted. "UFA
    no QO" is a club that has ALREADY declined to qualify him, so it holds
    nothing either.
    """
    if str(expiry_status).strip().upper() != "RFA":
        return []
    if pd.isna(ufa_year) or pd.isna(end_yr):
        return []
    first, last = int(end_yr) + 1, int(ufa_year) - 1
    if last < first:
        # The export puts a handful of RFA-expiring contracts at a UFA year
        # that has already passed. Production reports the same inconsistency
        # (6 of 1,973) and prices them at zero; so does this, visibly.
        return []
    return list(range(first, last + 1))


# ---------------------------------------------------------------------------
# WHAT A CONTROL SEASON IS WORTH ON A PATH
# ---------------------------------------------------------------------------
def season_share(currency, row: pd.Series, war, floor_share: float):
    """The cap share a one-year deal would be priced at for this production.

    A qualifying offer IS a one-year contract, so it is priced as one --
    length 1, the one-season flag set, restricted status set -- whatever term
    mode the contract itself was valued under. That is a statement about the
    asset, not a convenience: the club is buying one season at a time.
    """
    from production_currency import FEATURES
    from contract_price_model import predict_tobit

    war = np.atleast_1d(np.asarray(war, dtype=float))
    X = np.empty((len(war), len(FEATURES)))
    for j, f in enumerate(FEATURES):
        if f in ("war_per_season", "war_year1"):
            X[:, j] = war
        elif f == "length":
            X[:, j] = 1.0
        elif f == "one_year":
            X[:, j] = 1.0
        elif f == "is_RFA":
            X[:, j] = 1.0
        elif f == "rfa_x_war":
            X[:, j] = war
        else:
            X[:, j] = float(row[f])
    return np.maximum(predict_tobit(currency.coef_, X), floor_share)


def control_inputs(row: pd.Series, years) -> dict:
    """The cost and denominator of each control season, as knowable at the
    signing: the offer schedule, the cap ceiling, the league-minimum share and
    the discount factor back to the signing."""
    from production_currency import _offset

    caps = C.cap_path(row["signed"], [int(y) for y in years])
    cap = np.array([caps[int(y)] for y in years], dtype=float)
    floor = np.array([C.league_min_path(int(y), row["signed"])
                      for y in years]) / cap
    disc = np.array([(1.0 + C.DISCOUNT_RATE) ** -_offset(row["signed"], int(y))
                     for y in years], dtype=float)
    signed_year = pd.Timestamp(row["signed"]).year
    qo = qo_schedule(row["aav"], row["aav"], years, signed_year,
                     decision_date=row["signed"])
    return {"cap": cap, "floor": floor, "disc": disc, "qo": qo}


# ---------------------------------------------------------------------------
# THE FOUR STOPPING RULES
# ---------------------------------------------------------------------------
def _run_while(flag: np.ndarray) -> np.ndarray:
    """Take a season only while every season before it was taken too.

    Walking away is final: a club that declines to qualify a player loses the
    remaining control years, it does not skip one and come back. So the
    cumulative product, not the flag itself.
    """
    return np.cumprod(flag.astype(float), axis=-1)


def conditional_nodes(g: np.ndarray, sigma_mat: np.ndarray, j: int,
                      shape: np.ndarray):
    """What the club knows about season `j`'s miss, standing at season `j`.

    `g` are the correlated standard normals behind the paths and `sigma_mat`
    their correlation matrix, both already fitted for the simulation. Given
    the misses in seasons 0..j-1 on this path, g[j] is normal with a mean that
    is a linear projection of them and a variance that does not depend on the
    path. Returns that law as a quadrature: the shaped miss at each node and
    the node weights, so the caller can take the expectation of ANY function
    of next season rather than substituting a mean into it.

    Only seasons strictly before `j` enter. That is the whole point of the
    rule, and the runner checks it by scrambling the future and confirming
    nothing moves.
    """
    n = len(g)
    if j == 0:
        m, v = np.zeros(n), 1.0
    else:
        S11 = sigma_mat[:j, :j]
        s12 = sigma_mat[:j, j]
        w = np.linalg.solve(S11, s12)
        m = g[:, :j] @ w
        v = max(float(sigma_mat[j, j] - s12 @ w), 1e-12)
    x, wt = np.polynomial.hermite_e.hermegauss(GH_NODES)
    wt = wt / wt.sum()
    nodes = m[:, None] + np.sqrt(v) * x[None, :]
    if not len(shape) or np.ptp(shape) == 0:
        return np.zeros_like(nodes), wt
    grid = np.linspace(0.0, 1.0, len(shape))
    return np.interp(stats.norm.cdf(nodes), grid, shape), wt


def expected_surplus(currency, row: pd.Series, g: np.ndarray,
                     alive_prev: np.ndarray, sigma_mat: np.ndarray, j: int,
                     mu_j: float, sigma_j: float, shape: np.ndarray,
                     e_j: float, r_return: float, cap_j: float,
                     floor_j: float, qo_j: float) -> np.ndarray:
    """What the club expects this control season to be worth, on what it knows.

    Two things are integrated, not substituted. The miss, over the conditional
    law above. And whether he plays: a club standing at a control year knows
    whether the player is in the league, so the chance he plays next season is
    the chain's own transition -- one minus the exit probability if he is in
    it, the return rate if he is not -- rather than the unconditional marginal
    the point valuation uses.

    A season he does not play is still priced, at the floor, because the offer
    is a signed one-year deal: the club pays it and gets nothing.
    """
    z, wt = conditional_nodes(g, sigma_mat, j, shape)
    war = mu_j + sigma_j * z
    v_play = (season_share(currency, row, war.ravel(), floor_j)
              .reshape(war.shape) * cap_j) @ wt
    v_out = float(season_share(currency, row, np.zeros(1), floor_j)[0]) * cap_j
    p = np.where(alive_prev > 0, 1.0 - e_j, r_return)
    return p * v_play + (1.0 - p) * v_out - qo_j


def value_paths(currency, row: pd.Series, years, mu, sigma, p_play,
                shape: np.ndarray, sigma_mat: np.ndarray, war_paths: np.ndarray,
                g: np.ndarray, played: np.ndarray, e_sched: np.ndarray,
                r_return: float, offset: int) -> dict:
    """The control years' value per path, under each of the four rules.

    `offset` is how many columns of the drawn horizon belong to the contract
    itself, so the control years start there. Everything is discounted back to
    the signing, the same origin the contract's own cost and value use.
    """
    inp = control_inputs(row, years)
    n_paths = war_paths.shape[0]
    n_ctrl = len(years)
    drawn = np.empty((n_paths, n_ctrl))
    point = np.empty(n_ctrl)
    informed = np.empty((n_paths, n_ctrl))
    for j in range(n_ctrl):
        t = offset + j
        # WHAT THE SEASON TURNED OUT TO BE WORTH on each path.
        drawn[:, j] = (season_share(currency, row, war_paths[:, t],
                                    inp["floor"][j]) * inp["cap"][j]
                       - inp["qo"][j])
        # WHAT THE POINT PROJECTION SAID BEFORE ANY PATH EXISTED. The forecast
        # is conditional on playing, so the probability multiplies it exactly
        # once, as everywhere else in this tree.
        point[j] = (float(season_share(currency, row,
                                       np.array([mu[t] * p_play[t]]),
                                       inp["floor"][j])[0]) * inp["cap"][j]
                    - inp["qo"][j])
        # WHAT THE CLUB EXPECTED, STANDING THERE, on this path's history.
        alive_prev = played[:, t - 1] if t > 0 else np.ones(n_paths)
        informed[:, j] = expected_surplus(
            currency, row, g, alive_prev, sigma_mat, t, mu[t], sigma[t],
            shape, float(e_sched[t]), r_return, inp["cap"][j],
            inp["floor"][j], inp["qo"][j])
    dsurp = drawn * inp["disc"][None, :]
    out = {}
    for rule in RULES:
        if rule == "oracle":
            out[rule] = best_stop(dsurp)
            continue
        take = take_matrix(rule, drawn, point, informed)
        out[rule] = (take * dsurp).sum(axis=1)
    out["_point_surplus"] = point
    out["_qo"] = inp["qo"]
    out["_taken_informed"] = take_matrix("informed", drawn, point,
                                         informed).sum(axis=1)
    return out


def best_stop(discounted: np.ndarray) -> np.ndarray:
    """The most a club could have got out of these control years if it had
    known the whole path in advance and could only choose WHEN TO STOP.

    Not "take every year that turns out positive": walking away is final, so
    a club that wants the good third year has to sit through a bad second
    one. On a path worth +5, -1, +10 the myopic rule stops after the first
    year and collects 5, while taking all three collects 14 -- which is why
    stopping at the first negative is not the ceiling, and an earlier version
    of this module used it as one. The ceiling is the best PREFIX, including
    the empty one, so it is never below zero and never below any other rule
    here.
    """
    cum = np.concatenate([np.zeros((len(discounted), 1)),
                          np.cumsum(discounted, axis=1)], axis=1)
    return cum.max(axis=1)


def take_matrix(rule: str, surplus_drawn: np.ndarray, surplus_point: np.ndarray,
                surplus_informed: np.ndarray) -> np.ndarray:
    """Which control seasons the club actually takes, under one rule.

    The oracle has no take matrix of its own because its answer is a maximum
    over prefixes rather than a rule applied season by season; `best_stop`
    computes it from the discounted surpluses directly.
    """
    if rule == "committed":
        return np.ones_like(surplus_drawn)
    if rule == "declared":
        return _run_while(np.broadcast_to(surplus_point > 0,
                                          surplus_drawn.shape))
    if rule == "informed":
        return _run_while(surplus_informed > 0)
    raise ValueError(rule)


RULES = ("committed", "declared", "informed", "oracle")
