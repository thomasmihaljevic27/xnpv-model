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

THE SURVIVORSHIP CORRECTION (level_mode aside, the other switch here)
    A year-over-year change can only be measured on a player who played both
    seasons. The players who decline hardest are the ones who stop playing, so
    their worst year is never in the sample: the curve is fitted on survivors
    and UNDERSTATES decline, worst at the ages where it matters most.

    The fix is inverse-probability weighting. Each observed change is weighted
    by one over the probability that it would have been observed at all, so a
    35-year-old whose decline we did get to see stands in for all the
    35-year-olds like him, including the ones who never got a next season. If
    only a fifth of players like him are still around to be measured, his
    observed change counts five times, because it is the only evidence we have
    about the four who left.

    The probability comes from a retention model fitted here rather than
    borrowed from `participation_model.py`. They are the same family, but IPW
    needs the probability that THIS ROW is observed -- a player who played
    season t having a qualifying season at t+1 -- and the participation model
    answers a differently-conditioned question off a three-season anchor. Using
    the wrong conditioning would put a plausible number in the denominator and
    quietly reweight the panel toward nothing in particular.

    Weights are floored and trimmed. A probability near zero would otherwise
    hand one player's single observed season the weight of twenty careers, and
    the estimate would be that player rather than the league.

    WHAT TO EXPECT, WRITTEN DOWN BEFORE RUNNING IT: a steeper decline after
    about 33. If the correction does not move the curve that way, the
    correction is wrong rather than the expectation.
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

# Inverse-probability weights: floor the probability and trim the top of the
# resulting weights. Without both, a handful of improbable survivors become the
# entire old-age curve.
SELECTION_FLOOR = 0.05
SELECTION_TRIM_PCT = 99.0


class AdditiveAging:
    """The yearly change in WAR per 82, as a smooth function of age."""

    def __init__(self, level_mode: str = "lagged", use_experience: bool = False,
                 selection: str = "none", impute_level: float = 0.0,
                 impute_returners: bool = False):
        """level_mode:
             "lagged"  the player's rate one season before the change begins.
                       The default, and the only one that identifies aging
                       rather than mean reversion.
             "same"    the rate the change starts from. Kept ONLY as the
                       diagnostic that demonstrates the bias; never ship it.
             "none"    age and position alone.
        """
        assert level_mode in ("lagged", "same", "none"), level_mode
        assert selection in ("none", "ipw", "impute"), selection
        self.selection = selection
        self.retention_ = None
        self.n_imputed_ = 0
        self.n_returners_ = 0
        # WHERE A DEPARTING PLAYER IS ASSUMED TO HAVE BEEN. Zero is
        # replacement level, the default and the natural anchor: a player who
        # cannot hold an NHL job is worth about what a free replacement is
        # worth. It is an assumption doing real work, so it is a dial with a
        # sweep behind it rather than a constant buried in the fit.
        self.impute_level = float(impute_level)
        # A player who is absent and then comes back was usually hurt, not
        # finished, and we OBSERVE what he did on his return. Using that
        # instead of an assumption replaces a guess with data for the cases
        # where data exists, and leaves the assumption carrying only the
        # players who never played again.
        self.impute_returners = bool(impute_returners)
        self.mean_weight_ = 1.0
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

        if self.selection == "impute":
            # THE MISSING SEASONS, PUT BACK EXPLICITLY. Every row above is a
            # player who played both seasons. A player who played season t and
            # then did not play t+1 contributes nothing, and he is the whole
            # problem: he left BECAUSE of the season we never observed.
            #
            # The assumption, stated rather than hidden: a player who cannot
            # hold an NHL job the following season would have been at about
            # replacement level, which is zero on this scale by construction.
            # That is not a measurement, it is an identifying assumption, and
            # it is the one thing that makes the missing data informative. It
            # is deliberately a hard case -- some of those players were injured
            # and would have been fine -- so the corrected curve is a bound on
            # decline rather than a point estimate of it.
            miss = self._missing_next(s, before, level_col)
            if len(miss):
                lvl_m = miss["_lvl"] if self.level_mode == "lagged" else miss[level_col]
                y = np.concatenate([y, (miss["_impute_at"] - miss[level_col]).to_numpy(float)])
                X = np.vstack([X, self._design(miss["age"], lvl_m,
                                               (miss["pos"] == "D"),
                                               miss["exp_seasons"])])
                w_extra = miss["GP"].to_numpy(float)
                self.n_imputed_ = len(miss)
        w = np.minimum(p["GP"].to_numpy(float), p["GP_n"].to_numpy(float))
        if self.selection == "impute" and getattr(self, "n_imputed_", 0):
            w = np.concatenate([w, w_extra])

        if self.selection == "ipw":
            # THE CORRECTION. Every row in `p` is a pair that WAS observed, so
            # the panel is already the survivors; reweighting by the inverse
            # probability of surviving is what puts the missing players back
            # in, in the only way the data allows.
            pr = self._retention_probability(s, p, before)
            inv = 1.0 / np.clip(pr, SELECTION_FLOOR, 1.0)
            # Trim before use. One row at a probability of 0.02 would carry
            # fifty times the weight of a typical row and the old-age curve
            # would be that one player.
            cap = np.nanpercentile(inv, SELECTION_TRIM_PCT)
            inv = np.minimum(inv, cap)
            self.mean_weight_ = float(np.nanmean(inv))
            w = w * inv

        ok = np.isfinite(y) & np.isfinite(X).all(axis=1) & np.isfinite(w)
        Xw = X[ok] * np.sqrt(w[ok])[:, None]
        yw = y[ok] * np.sqrt(w[ok])
        try:
            self.coef_, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
        except np.linalg.LinAlgError:
            self.coef_ = None
        return self

    def _missing_next(self, s: pd.DataFrame, before: int, level_col: str) -> pd.DataFrame:
        """Player-seasons that qualified but had no qualifying season after.

        Restricted to seasons whose FOLLOW-UP had completed before the
        decision date, so a player who simply has not played his next season
        yet is not counted as gone. Without that, the most recent page would
        treat every current player as retired.
        """
        cand = s[s["syr"] + 1 < before].copy()
        nxt = s[["career_key", "syr"]].assign(syr=s["syr"] - 1, _has_next=1)
        cand = cand.merge(nxt, on=["career_key", "syr"], how="left")
        cand = cand[cand["_has_next"].isna() & cand["age"].notna()]
        lag = s[["career_key", "syr", level_col]].rename(columns={level_col: "_lvl"})
        lag["syr"] = lag["syr"] + 1
        cand = cand.merge(lag, on=["career_key", "syr"], how="left")

        # RETURNERS. A player absent at t+1 who plays again at t+2 or t+3 was
        # usually injured rather than finished, and his rate on return is
        # observed. Where that is available it replaces the assumption -- the
        # level he actually came back at, rather than the level we suppose a
        # departing player would have had. The assumption then carries only
        # the players who never appeared again, which is what it was for.
        cand["_impute_at"] = self.impute_level
        cand["_returner"] = False
        if self.impute_returners:
            for gap in (2, 3):
                ret = s[["career_key", "syr", level_col]].rename(
                    columns={level_col: "_ret"})
                ret["syr"] = ret["syr"] - gap
                cand = cand.merge(ret, on=["career_key", "syr"], how="left")
                hit = cand["_ret"].notna() & ~cand["_returner"]
                cand.loc[hit, "_impute_at"] = cand.loc[hit, "_ret"]
                cand.loc[hit, "_returner"] = True
                cand = cand.drop(columns=["_ret"])
        self.n_returners_ = int(cand["_returner"].sum())
        return cand

    def _retention_probability(self, s: pd.DataFrame, pairs: pd.DataFrame,
                               before: int) -> np.ndarray:
        """P(a player who played season t has a qualifying season at t+1).

        Fitted on every qualifying player-season whose FOLLOW-UP season had
        completed before the decision date, so the probability is estimated
        from what was knowable and nothing else. Features are the same ones
        that drive the curve -- age, level, games, experience, position --
        because the selection we are correcting for is selection on exactly
        those.
        """
        import statsmodels.api as sm

        base = s[s["syr"] + 1 < before].copy()
        if not len(base):
            return np.ones(len(pairs))
        nxt = s[["career_key", "syr"]].assign(syr=s["syr"] - 1, _played_next=1.0)
        base = base.merge(nxt, on=["career_key", "syr"], how="left")
        base["_played_next"] = base["_played_next"].fillna(0.0)
        base = base[base["age"].notna()]

        def design(d):
            a = np.clip(d["age"].to_numpy(float), AGE_LO, AGE_HI) - CENTRE
            return np.column_stack([a, a ** 2, d["WAR_82"].to_numpy(float),
                                    d["gp_share"].to_numpy(float),
                                    d["exp_seasons"].to_numpy(float),
                                    (d["pos"] == "D").astype(float).to_numpy()])

        X = design(base)
        y = base["_played_next"].to_numpy(float)
        ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
        if ok.sum() < MIN_PAIRS:
            return np.ones(len(pairs))
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = sm.Logit(y[ok], sm.add_constant(X[ok], has_constant="add")
                               ).fit_regularized(alpha=1e-4, disp=0, maxiter=200)
            self.retention_ = np.asarray(res.params, dtype=float)
        except Exception:                        # noqa: BLE001
            C.log("  [aging] retention fit failed; survivorship correction skipped")
            return np.ones(len(pairs))

        Xp = design(pairs)
        okp = np.isfinite(Xp).all(axis=1)
        out = np.ones(len(pairs))
        z = np.clip(np.column_stack([np.ones(okp.sum()), Xp[okp]]) @ self.retention_,
                    -30, 30)
        out[okp] = 1.0 / (1.0 + np.exp(-z))
        return out

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
