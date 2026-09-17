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
    asset, and the simulator has been valuing 398 of the 1,217 development
    contracts as though they ended at expiry.

    It matters most where the simulator sits BELOW the production chain: 219
    of those 398 are one-year deals and 138 are two-year deals.

OWNERSHIP IS ELIGIBILITY, AND NOTHING ELSE
    The first version asked the export what each contract's expiry turned out
    to be, and gave nothing to the 101 marked "UFA no QO" -- a club that had
    declined to qualify the player. That decision happens years after the
    signing this values, and it is the very decision the stopping rule exists
    to make. A further 45 were dropped on a plain "UFA" label while listing an
    eligibility year after their own expiry.

    So `control_span` reads eligibility alone and cannot see the label at all.
    What the club eventually did is an OUTCOME, for evaluating the rule and
    never for setting it up.

WHY IT IS AN OPTION AND NOT A STREAM
    Control is a right, not an obligation. The club tables an offer while the
    player is worth keeping and walks away when he is not, and once it walks
    away the remaining control years are gone -- there is no skipping a year
    and re-qualifying later. So the value of the control years is the value of
    a stopping rule, and a stopping rule is worth more than the stream it
    stops.

    Because walking away is final, "worth keeping" is not "does next season
    pay". A year that loses money is worth taking when the years behind it
    more than pay for it: on a path worth +5, -1, +10 a club that stops at the
    first loss leaves 9 behind. That is true of the ceiling and equally true
    of the policy, and the first version of this module fixed only the
    ceiling.

WHAT THE CLUB IS ASSUMED TO KNOW -- the whole identification question here
    Six rules are priced on the SAME draws, and each differs from its
    neighbour in ONE thing, so that a difference between two of them means
    something:

      committed          takes every control year. No right at all.
      production_point   prices the mean projection and stops at the first
                         loss. Production's rule (D13), kept because it is
                         production's, and the baseline for neither comparison
                         below: it differs from the informed rule in the
                         pricing AND the information AND the policy.
      declared           expected price, no path seen, later years counted.
      informed_myopic    the path's OBSERVED history, first loss.
      informed           the same history, later years counted.
      hindsight          knew the whole path, best stopping point. The ceiling.

    informed - declared is the value of information, with pricing and policy
    held. informed - informed_myopic is what counting the later years is
    worth, with information held. Nothing beats hindsight, and the runner
    asserts it.

    THE EXPECTATION IS OF THE PRICE, NOT THE PRICE OF THE EXPECTATION. The
    league-minimum floor bends the price, so those two differ even when no
    information has arrived. The first version compared a rule using one
    against a rule using the other and called the difference an option
    premium; it was a mixture.

    OBSERVED MEANS OBSERVED. The club conditions on the misses of seasons the
    player actually played, and the misses of seasons he missed are
    integrated out -- watching a player miss a year tells you he missed it,
    not how well he would have played. The first version conditioned on all of
    them, which moved the first control year's decision on 188 of 252
    contracts. Conditioning on the played seasons is exactly right rather than
    an approximation, because the joint law is Gaussian and the participation
    draws are independent of it; and seeing a played season's production is
    the same as seeing its miss because the shape is monotone, which
    `shape_is_monotone` asserts.

THE QUALIFYING OFFER
    The CBA formula, iterated year over year (each offer is a one-year deal
    and the next one escalates off it), floored at that season's league
    minimum, with the 2026 CBA's bands from the 2026 offseason on. The bands
    are reimplemented here rather than imported from `20_CODE`, because this
    tree is meant to stand on the sources rather than on production's chain --
    and then checked against production's implementation when it can be
    imported, so the two cannot drift apart unnoticed.

    THE REGIME IS DATED, not just the floor. The agreement carrying the 2026
    bands was ratified in the summer of 2025, so a contract signed in 2021
    pricing a 2026 control year sees the bands it could see: $1.00M on a $1M
    salary, not the $1.10M the first version handed it.

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

SCRIPT_VERSION = "2.0"

# How many Gauss-Hermite nodes the conditional expectation integrates over.
# The club's expectation of next season is a normal pushed through the
# empirical shape, so it is an integral rather than a substitution; 15 nodes
# reproduce the unconditional mean of the shape to better than $1 of a win.
GH_NODES = 15


# ---------------------------------------------------------------------------
# QUALIFYING-OFFER MECHANICS
# ---------------------------------------------------------------------------
# WHEN THE 2026 BANDS BECAME KNOWABLE. The agreement carrying them was
# ratified in the summer of 2025, so a contract signed before that could not
# have priced a 2026 control year on them, any more than it could have priced
# a season on a cap ceiling that had not been announced. The floor was dated
# from the start; the BANDS were not, and a 2021 signing was being handed a
# $1.10M offer in 2026 where the rules it could see gave $1.00M.
NEW_BANDS_RATIFIED = pd.Timestamp("2025-07-01")
NEW_BANDS_FROM = 2026


def new_bands_knowable(decision_date) -> bool:
    """Could a valuation made on this date have known the 2026 offer bands?"""
    if decision_date is None:
        return True
    return pd.Timestamp(decision_date) >= NEW_BANDS_RATIFIED


def qualifying_offer(prior_salary: float, prior_cap_hit: float,
                     offseason_year: int, signed_2020_plus: bool,
                     floor: float | None = None,
                     new_bands: bool | None = None) -> float:
    """The CBA qualifying offer for one offseason, in dollars.

    `offseason_year` is the calendar summer, which is the season_start of the
    season the offer covers. A qualifying offer is a one-year deal, so its
    salary is also its cap hit and the next year's offer escalates off it.

    `floor` is that season's league minimum and `new_bands` says whether the
    2026 agreement's bands were public yet. Left out, both take the whole
    published record, which is what production does and what the drift check
    compares against; anything VALUING a contract passes what its own signing
    date could have known, because neither the 2026 schedule nor the 2026
    bands existed before the summer of 2025.
    """
    if new_bands is None:
        new_bands = True
    if int(offseason_year) >= NEW_BANDS_FROM and new_bands:   # 2026 CBA bands
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
    # AND THE BANDS ARE DATED. A $1.0M salary qualifies at 110% under the 2026
    # agreement and at 100% under the rules a 2021 signing could see.
    assert abs(f(1_000_000, 1_000_000, 2026, True, floor=0,
                 new_bands=True) - 1_100_000) < 1
    assert abs(f(1_000_000, 1_000_000, 2026, True, floor=0,
                 new_bands=False) - 1_000_000) < 1
    assert new_bands_knowable("2025-07-01") and not new_bands_knowable("2021-07-01")


_qo_self_test()


def qo_schedule(base_salary: float, cap_hit: float, years, signed_year: int,
                decision_date=None):
    """The offer in each control season, each one escalating off the last."""
    out, prior_sal, prior_hit = [], float(base_salary), float(cap_hit)
    for y in years:
        qo = qualifying_offer(prior_sal, prior_hit, int(y),
                              int(signed_year) >= 2020,
                              floor=C.league_min_path(int(y), decision_date),
                              new_bands=new_bands_knowable(decision_date))
        out.append(qo)
        # THE NEXT OFFER ESCALATES OFF THIS ONE, and a one-year offer's salary
        # is its cap hit, so both carry forward as the same number.
        prior_sal = prior_hit = qo
    return np.asarray(out, dtype=float)


def control_span(end_yr, ufa_year) -> list[int]:
    """The seasons a club holds the player's rights for after the contract.

    ELIGIBILITY DECIDES THIS, NOT THE EXPIRY LABEL. The first version read the
    export's `expiry_status` and gave nothing to a contract marked "UFA no QO"
    -- a club that had already declined to qualify the player. But that
    declining happens YEARS AFTER the signing this values, and it is the very
    decision the stopping rule is supposed to make. Using it to remove the
    right beforehand is the model being told the answer: 101 development
    contracts carry that label and every one of them lists an eligibility year
    after its own expiry. A further 45 carry a plain "UFA" label while listing
    an eligibility year after expiry, and they were being dropped for the same
    reason.

    So ownership is a matter of eligibility alone: the club holds the rights
    from the season after the contract until the season before the player is
    unrestricted. What actually happened afterwards is an OUTCOME, kept for
    evaluating the rule and never for setting it up.
    """
    if pd.isna(ufa_year) or pd.isna(end_yr):
        return []
    first, last = int(end_yr) + 1, int(ufa_year) - 1
    if last < first:
        return []
    return list(range(first, last + 1))


def ufa_year_by_age(birthdate) -> float:
    """The season a player is unrestricted on the age rule alone.

    A player is unrestricted at 27, measured on 30 June, whatever else is
    true, so this needs nothing but a birthdate and is knowable the day the
    contract is signed. It is the audit against the export's own eligibility
    year, which can also come early through accrued seasons -- a route that
    depends in part on seasons not yet played at the signing.
    """
    b = pd.Timestamp(birthdate)
    if pd.isna(b):
        return float("nan")
    after_june30 = 1 if (b.month > 6 or (b.month == 6 and b.day > 30)) else 0
    return float(b.year + 27 + after_june30)


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
                      shape: np.ndarray, played: np.ndarray | None = None,
                      upto: int | None = None):
    """What the club knows about season `j`'s miss, standing at season `j`.

    `g` are the correlated standard normals behind the paths and `sigma_mat`
    their correlation matrix, both already fitted for the simulation. Given
    the misses the club has SEEN, g[j] is normal with a mean that is a linear
    projection of them and a variance that does not depend on the path.
    Returns that law as a quadrature -- the shaped miss at each node and the
    node weights -- so the caller can take the expectation of any function of
    next season rather than substituting a mean into it.

    `played` IS THE OBSERVATION MODEL AND IT IS NOT OPTIONAL IN PRACTICE. The
    first version conditioned on every earlier season's miss, including the
    seasons the player spent out of the league. Those misses exist inside the
    simulator, but nobody ever saw them: a club watching a player miss a year
    learns that he missed it, not how well he would have played. Changing only
    those unseen misses moved the first control year's decision on 188 of 252
    contracts and flipped 26,519 path decisions, which is the measure of how
    much unavailable information the rule was using.

    Conditioning on the played seasons alone integrates the missed ones out,
    because the joint law is Gaussian and the participation draws are
    independent of it -- so whether he played carries no information about how
    well he would have played, and dropping those coordinates is exactly the
    right thing rather than an approximation.

    Observing the production of a played season is the same as observing its
    miss here, because the empirical shape is monotone: the same draw always
    maps to the same production, and a bigger draw never maps to a smaller
    one. `shape_is_monotone` asserts that rather than assuming it.

    Paths are grouped by which seasons they observed, so the linear solve runs
    once per pattern instead of once per path.
    """
    n = len(g)
    m = np.zeros(n)
    v = np.ones(n)
    # `upto` is where the club is STANDING, which is not always the season it
    # is thinking about: deciding whether to keep a player for a third control
    # year means forming a view of that year now, on what is known now. It
    # defaults to the target season, which is the one-step-ahead case.
    cut = j if upto is None else int(upto)
    if cut > 0:
        obs = (np.ones((n, cut), dtype=bool) if played is None
               else played[:, :cut] > 0)
        keys = obs @ (1 << np.arange(cut))
        for k in np.unique(keys):
            idx = np.flatnonzero(keys == k)
            cols = np.flatnonzero(obs[idx[0]])
            if not len(cols):
                continue                      # saw nothing: the prior stands
            S11 = sigma_mat[np.ix_(cols, cols)]
            s12 = sigma_mat[cols, j]
            w = np.linalg.solve(S11, s12)
            m[idx] = g[np.ix_(idx, cols)] @ w
            v[idx] = max(float(sigma_mat[j, j] - s12 @ w), 1e-12)
        # A SEASON FURTHER OUT IS LESS PINNED DOWN, which falls out of the
        # matrix rather than being imposed: the projection uses the same
        # observations and the correlation with them is weaker.
    x, wt = np.polynomial.hermite_e.hermegauss(GH_NODES)
    wt = wt / wt.sum()
    nodes = m[:, None] + np.sqrt(v)[:, None] * x[None, :]
    if not len(shape) or np.ptp(shape) == 0:
        return np.zeros_like(nodes), wt
    grid = np.linspace(0.0, 1.0, len(shape))
    return np.interp(stats.norm.cdf(nodes), grid, shape), wt


def shape_is_monotone(shape: np.ndarray) -> bool:
    """Does a bigger draw always mean at least as much production?

    If it does, seeing a played season's production is the same as seeing its
    miss, and conditioning on the misses of played seasons is a statement
    about what the club saw rather than a convenience.
    """
    return bool(len(shape) < 2 or np.all(np.diff(np.asarray(shape)) >= -1e-12))


def alive_forward(alive_prev: np.ndarray, e_sched: np.ndarray, frm: int,
                  to: int, r_return: float) -> np.ndarray:
    """The chance the player is in the league in season `to`, given whether he
    was in it in season `frm - 1`, walked forward through the participation
    chain one season at a time. One step is the transition the point valuation
    already uses; several steps is the same transition iterated."""
    p = np.where(np.asarray(alive_prev) > 0, 1.0 - e_sched[frm], r_return)
    for t in range(frm + 1, to + 1):
        p = p * (1.0 - e_sched[t]) + (1.0 - p) * r_return
    return p


def expected_surplus(currency, row: pd.Series, g: np.ndarray,
                     alive_prob: np.ndarray, sigma_mat: np.ndarray, t: int,
                     mu_t: float, sigma_t: float, shape: np.ndarray,
                     cap_t: float, floor_t: float, qo_t: float,
                     played: np.ndarray | None = None,
                     upto: int | None = None) -> np.ndarray:
    """What the club expects season `t` to be worth, on what it knows now.

    Two things are integrated, not substituted. The miss, over the conditional
    law above. And whether he plays: `alive_prob` is the chance he is in the
    league that season given what the club can see of his participation now.

    A season he does not play is still priced, at the floor, because the offer
    is a signed one-year deal: the club pays it and gets nothing.

    THE EXPECTATION IS OF THE PRICE, NOT THE PRICE OF THE EXPECTATION. The
    league-minimum floor makes the price a bent function of production, so the
    two differ, and an earlier version compared a rule using one against a
    rule using the other -- which mixed the value of information together with
    the difference between those two calculations. Every rule that decides on
    an expectation now uses this function, and they differ only in what they
    are allowed to condition on.
    """
    z, wt = conditional_nodes(g, sigma_mat, t, shape, played, upto)
    war = mu_t + sigma_t * z
    v_play = (season_share(currency, row, war.ravel(), floor_t)
              .reshape(war.shape) * cap_t) @ wt
    v_out = float(season_share(currency, row, np.zeros(1), floor_t)[0]) * cap_t
    p = np.asarray(alive_prob, dtype=float)
    return p * v_play + (1.0 - p) * v_out - qo_t


def best_outlook(expected: np.ndarray, disc: np.ndarray, j: int) -> np.ndarray:
    """Is there ANY number of further control years worth keeping?

    The club at control year `j` is not choosing whether this one season pays.
    It is choosing whether to hold the right at all, and holding it means
    holding every season it might still want -- so a year that loses money is
    worth taking when the years behind it more than pay for it. The same
    +5, -1, +10 that made stopping at the first loss the wrong ceiling makes
    it the wrong policy: a club that stops there leaves 9 on the table.

    `expected[i]` is what the club expects season `i` to be worth, standing at
    `j`. Continue while the best run of seasons starting here is positive.
    """
    run = np.cumsum(expected * disc[None, j:], axis=1)
    return run.max(axis=1) > 0


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


def value_paths(currency, row: pd.Series, years, mu, sigma, p_play,
                shape: np.ndarray, sigma_mat: np.ndarray, war_paths: np.ndarray,
                g: np.ndarray, played: np.ndarray, e_sched: np.ndarray,
                r_return: float, offset: int) -> dict:
    """The control years' value per path, under each rule.

    `offset` is how many columns of the drawn horizon belong to the contract
    itself, so the control years start there. Everything is discounted back to
    the signing, the same origin the contract's own cost and value use.

    THE RULES DIFFER IN ONE THING EACH, DELIBERATELY. Against `declared`, the
    `informed` rule adds the path's observed history and nothing else -- same
    pricing, same decision logic -- so the difference between them is the
    value of information. Against `informed_myopic`, the `informed` rule adds
    the continuation value and nothing else, so the difference between those
    is what holding the later years is worth. `production_point` is kept
    separate because it is production's rule and differs in BOTH ways, which
    is why it cannot be the baseline for either comparison.
    """
    inp = control_inputs(row, years)
    n_paths = war_paths.shape[0]
    n_ctrl = len(years)
    disc = inp["disc"]
    drawn = np.empty((n_paths, n_ctrl))
    point = np.empty(n_ctrl)            # production's rule: price of the mean
    uncond = np.empty(n_ctrl)           # no conditioning, but the same pricing
    for j in range(n_ctrl):
        t = offset + j
        drawn[:, j] = (season_share(currency, row, war_paths[:, t],
                                    inp["floor"][j]) * inp["cap"][j]
                       - inp["qo"][j])
        point[j] = (float(season_share(currency, row,
                                       np.array([mu[t] * p_play[t]]),
                                       inp["floor"][j])[0]) * inp["cap"][j]
                    - inp["qo"][j])
        uncond[j] = float(expected_surplus(
            currency, row, g[:1], np.array([p_play[t]]), sigma_mat, t, mu[t],
            sigma[t], shape, inp["cap"][j], inp["floor"][j], inp["qo"][j],
            played=played[:1], upto=0)[0])

    # THE CONDITIONAL OUTLOOK, season by season, standing at each decision.
    # cond[j][i] is what the club at control year j expects control year i to
    # be worth, for every i it could still keep.
    cond = []
    for j in range(n_ctrl):
        t = offset + j
        alive_prev = played[:, t - 1] if t > 0 else np.ones(n_paths)
        block = np.empty((n_paths, n_ctrl - j))
        for i in range(j, n_ctrl):
            ti = offset + i
            block[:, i - j] = expected_surplus(
                currency, row, g,
                alive_forward(alive_prev, e_sched, t, ti, r_return),
                sigma_mat, ti, mu[ti], sigma[ti], shape, inp["cap"][i],
                inp["floor"][i], inp["qo"][i], played=played, upto=t)
        cond.append(block)

    takes = {}
    takes["committed"] = np.ones((n_paths, n_ctrl))
    takes["production_point"] = _run_while(
        np.broadcast_to(point > 0, (n_paths, n_ctrl)))
    takes["declared"] = _run_while(np.broadcast_to(
        np.array([bool(np.cumsum(uncond[j:] * disc[j:]).max() > 0)
                  for j in range(n_ctrl)]), (n_paths, n_ctrl)))
    takes["informed_myopic"] = _run_while(
        np.stack([cond[j][:, 0] > 0 for j in range(n_ctrl)], axis=1))
    takes["informed"] = _run_while(
        np.stack([best_outlook(cond[j], disc, j) for j in range(n_ctrl)],
                 axis=1))

    dsurp = drawn * disc[None, :]
    out = {rule: (takes[rule] * dsurp).sum(axis=1) for rule in takes}
    out["hindsight"] = best_stop(dsurp)
    out["_point_surplus"] = point
    out["_uncond_surplus"] = uncond
    out["_qo"] = inp["qo"]
    out["_taken_informed"] = takes["informed"].sum(axis=1)
    return out


RULES = ("committed", "production_point", "declared",
         "informed_myopic", "informed", "hindsight")
