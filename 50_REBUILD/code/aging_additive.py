"""aging_additive.py -- the aging curve as a difference, not a ratio.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 3, step one of three: the
UNCORRECTED curve. The survivorship correction needs participation
probabilities from Phase 2 and comes after, so that the additive-versus-ratio
change and the survivorship change can be told apart.

WHAT IT IS
    For a player of a given age, position and current level, the expected
    CHANGE in his WAR per 82 over the next season. A projection walks that
    change forward one year at a time:

        level(k) = level(k-1) + step(age + k - 1, level(k-1), position)

WHY A DIFFERENCE AND NOT A RATIO
    The production chain multiplies a raw trailing WAR total by an aging
    ratio. That needs four guards to stay sane -- a floor on the base, a cap
    on the ratio, a floor on the ratio, and a flat fallback -- because a ratio
    applied to a number near or below zero does something meaningless. Under a
    straight-line price on wins a difference is exactly right, and all four
    guards disappear rather than being retuned. A negative anchor stops being
    a special case; it is just a low level that ages like any other.

WHAT IS DELIBERATELY NOT IN HERE
    Mean reversion. `20_CODE/aging_curve.py` pulls a player 45% of the way to
    a comparables norm (LAMBDA = 0.55) BEFORE applying any aging, inside the
    thing called the aging curve. The rebuilt forecast already does that job,
    per component, by an amount fitted from evidence. Running both would shrink
    every player twice, once visibly and once hidden inside "aging". So this
    file computes aging and nothing else.

THE LEVEL TERM, AND THE TRAP IN IT (measured, not theorised)
    Better players decline faster IN WINS: a 3-win player losing a tenth of
    his ability loses more wins than a 1-win player losing a tenth. That is a
    real aging effect and it belongs here.

    But a decline-on-level regression is also how you would measure mean
    reversion, and the two are not the same thing. The change from season t to
    t+1 is (rate at t+1) minus (rate at t). If the level regressor is ALSO the
    rate at t, then whatever noise made season t look good appears on both
    sides -- positively in the regressor, negatively in the outcome -- and the
    fitted coefficient collects regression to the mean and reports it as
    aging.

    This was measured on the panel rather than argued about. The yearly change
    correlates -0.447 with the same-season level and -0.052 with the level one
    season earlier. Nearly all of the apparent "the best decline fastest"
    effect is the arithmetic of measuring a change against its own starting
    point. Fitted the naive way the curve claimed a 3-win 27-year-old loses
    0.8 wins a year, which is not a finding about hockey.

    THE FIX IS THE LAGGED LEVEL. The regressor is the player's rate in season
    t-1, whose noise is independent of the t-to-t+1 change by construction, so
    the coefficient measures the real effect and not the arithmetic. What
    survives is small and plausible. The cost is the seasons that have no
    t-1 to look back at (2,080 of 10,937 pairs), which fall back to the
    age-and-position curve rather than being dropped -- dropping them would
    select against players early in a career, which is its own bias.

KNOWN AND UNCORRECTED, FOR NOW
    A year-over-year change can only be measured on a player who played both
    seasons. The players who decline hardest are the ones who stop playing, so
    their worst year is never in the sample and this curve UNDERSTATES decline,
    worst at the ages where it matters most. That is the survivorship problem,
    it is real, and step three of Phase 3 addresses it. Until then every figure
    from this curve should be read as an upper bound on how well old players
    age.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C

SCRIPT_VERSION = "1.0"

# Ages outside this band have too few seasons to fit a shape on; a player
# beyond it takes the step at the nearest edge. Without the clamp the cubic
# would extrapolate off the end of the data and hand a 41-year-old a number
# driven by curvature rather than by evidence.
AGE_LO, AGE_HI = 19.0, 39.0
CENTRE = 27.0          # roughly peak, so the linear term reads per year off prime
MIN_PAIRS = 300        # below this the window cannot support a shape


class AdditiveAging:
    """The yearly change in WAR per 82, as a smooth function of age."""

    def __init__(self, level_mode: str = "lagged", use_experience: bool = False):
        """level_mode:
             "lagged"  the player's rate one season before the change begins.
                       The default, and the only one that identifies aging
                       rather than mean reversion.
             "same"    the rate the change starts from. Kept ONLY as the
                       diagnostic that demonstrates the bias; never ship it.
             "none"    age and position alone.
        """
        assert level_mode in ("lagged", "same", "none"), level_mode
        self.level_mode = level_mode
        self.use_level = level_mode != "none"
        self.use_experience = use_experience
        self.coef_ = None
        self.n_pairs_ = 0

    # -- design ------------------------------------------------------------
    def _design(self, age, level, is_d, exp) -> np.ndarray:
        a = np.clip(np.asarray(age, dtype=float), AGE_LO, AGE_HI) - CENTRE
        cols = [np.ones_like(a), a, a ** 2, a ** 3, np.asarray(is_d, dtype=float)]
        if self.use_level:
            lv = np.asarray(level, dtype=float)
            # level, and level interacted with age: the "more to lose" effect
            # is not constant across a career, it bites hardest on the decline.
            cols += [lv, lv * a]
        if self.use_experience:
            cols.append(np.asarray(exp, dtype=float))
        return np.column_stack(cols)

    # -- fit ---------------------------------------------------------------
    def fit(self, table: pd.DataFrame, before: int, level_col: str = "WAR_82"):
        """Fit on within-player changes whose OUTCOME season completed before
        `before`.

        Within-player by construction: every row is one player's season t and
        the same player's season t+1, so a difference between two players of
        different quality can never enter. Consecutive seasons only -- a pair
        straddling a missed year is not a one-year change, and treating it as
        one is the error the production curve's review item 1.7 found (339 of
        7,869 windows, the worst pairing ages 21 and 30 as back-to-back).

        Weighted by the smaller of the two seasons' games, so a change measured
        across two full seasons counts for more than one resting on a nine-game
        cameo at either end.
        """
        s = table[table["GP"] >= C.MIN_GP]
        nxt = s.assign(syr=s["syr"] - 1)
        p = s.merge(nxt, on=["career_key", "syr"], suffixes=("", "_n"))
        p = p[p["syr"] + 1 < before]                      # outcome completed
        p = p[p["age"].notna()]

        # The lagged level: the same player's rate one season before the change
        # begins. Independent noise, which is the whole point -- see the
        # docstring. Rows without one keep a missing level and are fitted on
        # age and position alone rather than dropped.
        lag = s[["career_key", "syr", level_col]].rename(columns={level_col: "_lvl"})
        lag["syr"] = lag["syr"] + 1
        p = p.merge(lag, on=["career_key", "syr"], how="left")
        lvl = p["_lvl"] if self.level_mode == "lagged" else p[level_col]

        self.n_pairs_ = len(p)
        if len(p) < MIN_PAIRS:
            self.coef_ = None
            return self

        y = (p[level_col + "_n"] - p[level_col]).to_numpy(float)
        X = self._design(p["age"], lvl, (p["pos"] == "D"), p["exp_seasons"])
        w = np.minimum(p["GP"].to_numpy(float), p["GP_n"].to_numpy(float))
        ok = np.isfinite(y) & np.isfinite(X).all(axis=1) & np.isfinite(w)
        Xw = X[ok] * np.sqrt(w[ok])[:, None]
        yw = y[ok] * np.sqrt(w[ok])
        try:
            self.coef_, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
        except np.linalg.LinAlgError:
            self.coef_ = None
        return self

    # -- apply -------------------------------------------------------------
    def step(self, age, level, is_d, exp=0.0) -> np.ndarray:
        """Expected change in WAR per 82 over the next season."""
        if self.coef_ is None:
            return np.zeros(np.size(age))
        return self._design(age, level, is_d, exp) @ self.coef_

    def walk(self, level0, age0, is_d, h: int, exp=0.0) -> np.ndarray:
        """Carry a level forward h seasons, one year at a time.

        Year by year rather than in one jump because the step depends on the
        level, and the level is what the walk is changing -- a player who
        declines into a lower level declines more slowly in wins from there.
        This is also the shape Phase 5's simulation needs: the same walk, with
        a shock drawn at each step.
        """
        level = np.asarray(level0, dtype=float).copy()
        age = np.asarray(age0, dtype=float).copy()
        for _ in range(int(h)):
            level = level + self.step(age, level, is_d, exp)
            age = age + 1.0
        return level

    # -- inspection --------------------------------------------------------
    def curve(self, levels=(0.5, 1.5, 3.0), is_d=False) -> pd.DataFrame:
        """The fitted yearly change by age, at a few levels. For reading the
        shape out loud rather than for the model."""
        ages = np.arange(20, 39)
        out = {"age": ages}
        for lv in levels:
            out[f"level {lv}"] = self.step(ages, np.full(len(ages), lv),
                                           np.full(len(ages), float(is_d)))
        return pd.DataFrame(out)
