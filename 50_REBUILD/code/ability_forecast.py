"""ability_forecast.py -- candidate models of what a player will be.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 1; A0 is also the Phase 0
acceptance test for the harness itself.

The models, in the plan's own numbering:

  A0  PRODUCTION BASELINE. The locked 60/40 blend of the last two qualifying
      seasons' WAR TOTALS, carried flat across every horizon, with everyone
      assumed to play a full season. This is the production chain's starting
      point, re-expressed as a harness model. It exists to be beaten -- and,
      first, to prove the harness reproduces the tilt already measured on the
      production chain. If A0 does not over-project stars here, the harness
      is wrong, not the chain.

  A1  The age-aware calibrated total. A fitted pull-back of the blend toward
      the league, with position and a one-season-history flag. The mandatory
      benchmark: complexity beyond this has to earn its place against it.

  A2  COMPONENT-WISE. Each of the seven components forecast on its own per-82
      rate with its own fitted persistence, games as the exposure, then summed.
      The lead candidate.

Later in Phase 1: A3 adds an in-season Game Value update for trade dates.
Phases 2 and 3 replace the placeholder participation and the flat carry-
forward here with the real participation model and the additive aging curve;
until then every model carries the SAME placeholders, so a comparison between
them is still a fair comparison of the one thing that differs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import information_set as ISET

SCRIPT_VERSION = "2.2"

W_T1, W_T2 = 0.6, 0.4    # the locked recency weighting, reproduced for A0


class BaseModel:
    """Shared plumbing, and the one assertion that keeps every model honest.

    THE OUTCOME-WINDOW RULE. `fit(table, before)` may use a training pair only
    if the pair's OUTCOME season is strictly before `before`. Filtering the
    INPUT window is not enough: a pair whose inputs end in t0-3 but whose
    outcome lands in t0+1 has seen the future. _training_pairs() below is the
    only place any model builds training data, and it enforces this.
    """
    name = "base"

    # HOW MANY TRAILING SEASONS the anchor reads, and how fast older ones are
    # discounted. The defaults reproduce the locked 60/40 two-season rule
    # exactly (a decay of 0.667 over two seasons IS 60/40), so a model that
    # overrides nothing behaves as it always did.
    N_SEASONS = 2
    DECAY = W_T2 / W_T1
    FIT_DECAY = False

    # Candidate decay rates. 1.0 means "weight all seasons in the window
    # equally"; 0.4 means last season carries more than twice the one before.
    # The grid stops at 1.0 on purpose: a rate above it would trust a
    # three-year-old season more than last year's, which is not a hypothesis
    # worth spending a degree of freedom on.
    DECAY_GRID = np.array([0.40, 0.50, 0.60, 0.667, 0.75, 0.85, 1.00])

    # WHICH HORIZONS THIS MODEL HAS ACTUALLY FITTED. None means unrestricted,
    # which is true only of a model that carries a trailing number flat and
    # therefore has nothing to fit.
    FITTED_HORIZONS = C.FITTED_HORIZONS

    def predict_beyond_fit(self, iset, subs, horizons):
        """Forecast horizons past the fitted range, by a DECLARED rule.

        predict() refuses an unfitted horizon and will go on refusing it. This
        is the separate, explicitly-called path for the case the refusal
        exposed: a contract runs longer than its own page can support. At the
        2014 page the fitted range reaches five seasons and an eight-year deal
        needs eight, because a training pair at eight seasons out needs an
        outcome that had not happened yet. 28 of 1,927 development contracts
        are in this position, 1.5%, and every one of them is a long deal, which
        is the population the thesis cares most about. Dropping them would
        change the market sample in exactly the direction that flatters it.

        THE RULE: continue the decay already visible at the end of the fitted
        range. The league-wide ratio between the last two fitted horizons is
        measured separately for the rate and for participation, and each is
        applied once per extra season. Games share is carried forward.

        WHY NOT SIMPLY HOLD FLAT, which was the first thing tried. Measured
        against pages where these horizons ARE fitted, holding flat overstates
        forecast production by 36% one season past the range, 88% two past and
        170% three past. Production declines steeply out there and
        participation declines with it, so flat is not conservative, it is
        wrong. Continuing the observed decay leaves +3.0%, +10.0% and +19.8%
        over four pages. A rule that tries to capture the ACCELERATION of the
        decay overshoots the other way, and a log-linear trend is worse than
        both, so the plain ratio is what ships. Those are means over four pages;
        on the worst of them the three-season error is +32%, which is the real
        cost of pricing an eight-year deal from a page that reaches five.

        THE REMAINING BIAS IS UP, and it is not corrected. It could be divided
        out using the figures above, but they are three constants tuned to
        repair 1.5% of the sample, and that is not a trade worth making. The
        direction is stated instead: an extrapolated tail is worth slightly
        more than a fitted one would be, so a contract priced partly on
        extrapolation is flattered, mildly and knowably.

        A ratio is measured LEAGUE-WIDE rather than per player: per-player
        ratios were tested and are worse, being a noisy quotient of two
        forecasts for one man.

        Every extrapolated row is tagged, so a total built on one can say how
        much of itself was extrapolated.
        """
        raw_fitted = getattr(self, "fitted_horizons_", None) or self.FITTED_HORIZONS
        want = sorted(int(h) for h in horizons)
        if raw_fitted is None:
            # A model with no fitted range answers every horizon by
            # construction, which is true of anything that carries a rule
            # forward rather than estimating one. There is nothing to
            # extrapolate past, so this path is a plain predict with the tag
            # attached for a consistent frame.
            out = self.predict(iset, subs, want)
            out["extrapolated"] = 0.0
            return out
        fitted = sorted(raw_fitted)
        inside = [h for h in want if h in fitted]
        beyond = [h for h in want if h not in fitted]
        if beyond and len(fitted) < 2:
            raise ValueError(
                f"{self.name} needs two fitted horizons to measure a decay "
                f"rate from, and has {len(fitted)}.")

        # THE ENDPOINT IS THE MODEL'S, NOT THE CALLER'S. The decay rate was
        # already measured on a fixed population, but it was applied to the
        # last fitted horizon the CALLER HAPPENED TO REQUEST, so asking for
        # horizons 3, 4 and 6 still answered differently from 4, 5 and 6, by
        # 0.505 WAR at horizon six. The check that was meant to catch this kept
        # horizon five in both of its requests and so could not.
        #
        # The final fitted season is now always computed internally, whether or
        # not it was asked for, every extrapolation runs from it, and only the
        # requested rows are returned. A request for an extrapolated year alone
        # therefore works too, where it used to raise.
        need = sorted(set(inside) | ({fitted[-1]} if beyond else set()))
        full = self.predict(iset, subs, need)
        full["extrapolated"] = 0.0
        out = full[full["h"].isin(inside)].copy()
        if beyond:
            g_prod, g_play = self._tail_decay(iset, fitted[-1], fitted[-2])
            # The ratio is measured on the PRODUCT, which is the quantity that
            # has to decay correctly, and then split between the two parts.
            # Measuring a ratio for each part separately and applying both
            # decays the product by their product, which double-counts the
            # decline: tested, it undershoots by 21% to 45% instead of the
            # 3% to 20% the product ratio leaves. Participation keeps its own
            # observed rate so it stays interpretable, and the rate carries
            # whatever is left over.
            g_rate = float(np.clip(g_prod / g_play, 0.5, 1.05))
            last = full[full["h"] == fitted[-1]]
            for h in beyond:
                k = h - fitted[-1]
                nxt = last.copy()
                nxt["h"] = h
                nxt["rate_82"] = last["rate_82"] * g_rate ** k
                nxt["p_play"] = (last["p_play"] * g_play ** k).clip(0.005, 0.995)
                nxt["extrapolated"] = 1.0
                out = pd.concat([out, nxt], ignore_index=True)
        return out

    def _tail_decay(self, iset, hmax: int, prev: int):
        """League-wide decay between two fitted horizons, on a fixed reference
        population and cached per page, so an extrapolated forecast does not
        depend on which horizons or which players were asked about."""
        key = (int(iset.t0), int(hmax), int(prev))
        cache = getattr(self, "_decay_cache", None)
        if cache is None:
            cache = self._decay_cache = {}
        if key not in cache:
            import forecast_harness as _H          # lazy, to avoid a cycle
            ref = _H.subjects_at(iset)
            p = self.predict(iset, ref, [prev, hmax])
            a, b = p[p["h"] == prev], p[p["h"] == hmax]
            war = lambda x: (x["p_play"] * x["rate_82"] * x["gp_share"]).mean()
            cache[key] = (
                float(np.clip(war(b) / war(a), 0.5, 1.0)),
                float(np.clip(b["p_play"].mean() / a["p_play"].mean(), 0.5, 1.0)))
        return cache[key]

    def _guard_horizons(self, horizons) -> None:
        """Refuse a horizon this model never fitted.

        Returning something for an unfitted horizon is worse than failing,
        because the something looks like a forecast. Before this guard a
        request for year seven got a flat 0.6 participation and the player's
        trailing rate and games share, and that fabricated tail went into the
        long-contract averages and from there into the fitted price line.
        Refusing is the first repair and not the whole one: a contract that
        runs past the fitted range still needs either a fit that reaches it or
        a declared extrapolation, and this raise is what forces that choice to
        be made rather than defaulted into.
        """
        # What THIS FIT managed, when it recorded it, rather than the class
        # default: the range a page can support depends on how much history
        # sits behind it, so a 2021 valuation legitimately reaches further than
        # a 2015 one and should not be held to the earlier page's limit.
        fitted = getattr(self, "fitted_horizons_", None)
        if fitted is None:
            fitted = self.FITTED_HORIZONS
        if fitted is None:
            return
        missing = sorted({int(h) for h in horizons} - set(fitted))
        if missing:
            raise ValueError(
                f"{self.name} was asked for horizon(s) {missing} but is fitted "
                f"only to {sorted(fitted)}. On this page the later horizons "
                f"have fewer than {C.MIN_HORIZON_PAIRS} training pairs, so "
                "there is nothing behind them. Price the contract from a page "
                "that reaches far enough, or declare and test an "
                "extrapolation. Do not take the fallback value silently.")

    def fit(self, table: pd.DataFrame, before: int) -> None:
        self.before = before
        # UNRESTRICTED UNTIL A FIT NARROWS IT. None is the convention
        # _guard_horizons already reads through a getattr default, and it means
        # "this model fitted nothing, so no horizon is outside its range" --
        # true of the flat benchmark and of the production adapter, which carry
        # a number forward rather than estimating one.
        #
        # Setting it here rather than leaving the attribute absent is what
        # stops a model that SHOULD have recorded a range from failing with
        # AttributeError somewhere downstream instead of being caught. The
        # component model did exactly that, and the error surfaced inside its
        # own fit rather than anywhere that named the cause.
        self.fitted_horizons_ = None
        self.decay_ = self.DECAY
        if self.FIT_DECAY:
            self.decay_ = self._fit_decay(table, before)

    def _fit_decay(self, table: pd.DataFrame, before: int) -> float:
        """Pick the decay rate on the rolling window, by the job it does.

        For each candidate rate, build the anchor as of each past valuation
        season and score its blended per-82 rate against what the player
        actually did that season. Only outcomes that completed before the
        decision date are used, so the rate is chosen without seeing anything
        the forecast has not lived through.

        Errors are weighted by the OUTCOME season's games, because a rate
        measured over eighty games is a sharper target than one measured over
        twelve, and an unweighted fit would let the noisiest seasons choose
        the shape of the window.
        """
        s = table[table["GP"] >= C.MIN_GP]
        act = s.set_index(["career_key", "syr"])
        best, best_sse = self.DECAY, np.inf
        for d in self.DECAY_GRID:
            a = _anchors(s, self.N_SEASONS, float(d))
            a = a[a["t0"] < before]
            ix = pd.MultiIndex.from_arrays([a["career_key"], a["t0"]])
            y = act["WAR_82"].reindex(ix).to_numpy()
            gp = act["GP"].reindex(ix).to_numpy()
            ok = np.isfinite(y) & np.isfinite(a["tr_WAR"].to_numpy())
            if ok.sum() < 200:
                continue
            e = a["tr_WAR"].to_numpy()[ok] - y[ok]
            sse = float((gp[ok] * e ** 2).sum())
            if sse < best_sse:
                best, best_sse = float(d), sse
        return best

    def predict(self, iset, subs, horizons) -> pd.DataFrame:
        raise NotImplementedError

    def _record_fitted_horizons(self, pairs: pd.DataFrame) -> None:
        """WHICH HORIZONS THIS PAGE CAN ACTUALLY CARRY, recorded on the model so
        the guard can refuse the rest by evidence rather than by a constant.

        THIS LIVES IN ONE PLACE ON PURPOSE. It used to be three lines at the
        end of the base pair builder, and the component model's own builder --
        which had to override that method to construct its anchors differently
        -- was written by copying the rest of it and dropping these. The result
        was a registered candidate that raised AttributeError inside its own
        fit, before it could price a single contract, because the horizons it
        was about to be asked about had never been recorded.

        That is the second-copy-of-a-rule failure this codebase has been bitten
        by twice before and warns about in two other files. Adding the three
        lines back to the second builder would have made a third copy. Any
        builder that produces pairs calls this instead.
        """
        n = pairs.dropna(subset=["y_rate"]).groupby("h").size()
        self.fitted_horizons_ = tuple(
            sorted(int(h) for h, k in n.items() if k >= C.MIN_HORIZON_PAIRS))

    def _training_pairs(self, table: pd.DataFrame, before: int, horizons) -> pd.DataFrame:
        """Every (inputs at t, outcome at t+h) pair whose OUTCOME completed
        before `before`. One row per player-anchor-horizon."""
        s = table[table["GP"] >= C.MIN_GP]
        anchors = _anchors(s, self.N_SEASONS, self.decay_)
        out = []
        for h in horizons:
            a = anchors.copy()
            a["season"] = a["t0"] + h
            a["h"] = h
            a = a[a["season"] < before]          # the rule, in one line
            out.append(a)
        pairs = pd.concat(out, ignore_index=True)
        act = table.set_index(["career_key", "syr"])
        ix = pd.MultiIndex.from_arrays([pairs["career_key"], pairs["season"]])
        pairs["y_war"] = act["WAR"].reindex(ix).to_numpy()
        pairs["y_rate"] = act["WAR_82"].reindex(ix).to_numpy()
        pairs["y_gp_share"] = act["gp_share"].reindex(ix).to_numpy()
        # THE SAME EVENT the participation model predicts. These two used to
        # disagree: participation predicted a ten-game season while the rate
        # and games targets were taken from any season with a number in it, so
        # a cameo was simultaneously a played season for the rate and an
        # unplayed one for participation, and their product was an expectation
        # of nothing.
        pairs["y_gp"] = act["GP"].reindex(ix).to_numpy()
        pairs["y_played"] = np.nan_to_num(pairs["y_gp"]) >= C.PARTICIPATION_GP
        self._record_fitted_horizons(pairs)
        # A season that never happened is not a training row for the RATE, but
        # IS one for participation. Rate fits drop it; the participation
        # placeholder below uses the full frame.
        return pairs


# HOW FAR BACK A STALE ANCHOR MAY REACH. Matches the harness's eligibility
# window (forecast_harness.ACTIVE_WINDOW): a player the harness is willing to
# ask about must be a player the models can answer about, or he is dropped from
# scoring and the drop falls entirely on players who missed a season.
STALE_LOOKBACK = 3


def _anchors(played: pd.DataFrame, n_seasons: int = 2,
             decay: float = W_T2 / W_T1, stale: bool = True,
             cols: list | None = None) -> pd.DataFrame:
    """For every player and every season t0 he could have been valued at, the
    trailing facts from t0-1 and t0-2 only.

    Structurally incapable of seeing season t0: it reads t0-1 and t0-2 by
    construction, the same property the production engine's lookup has. The
    caller is responsible for restricting t0 itself.

    `cols` are the production columns blended into trailing totals and rates.
    The default is the skater components plus WAR. The goalie branch passes
    ["WAR"] alone, because a goaltender has one number and no components --
    and passes it here rather than keeping a second copy of the blend, the
    stale-history rule and the age stepping, which are the same for both.
    """
    cols = list(C.COMPONENTS_MODEL + ["WAR"] if cols is None else cols)
    rate_cols = [c + "_82" for c in cols]
    keep = ["career_key", "pkey", "pos", "syr", "GP", "gp_share", "toi_pg",
            "exp_seasons", "exp_censored", "age", "has_age"] + cols + rate_cols
    s = played[keep]
    lags = list(range(1, n_seasons + 1))

    # One frame per lag, aligned on (player, valuation season). Structurally
    # incapable of seeing season t0: every part is built by adding a POSITIVE
    # lag to the season it came from, so nothing at or after t0 can enter.
    parts = []
    for lag in lags:
        q = s.assign(t0=s["syr"] + lag).set_index(["career_key", "t0"])
        parts.append(q.add_suffix(f"_{lag}"))
    m = pd.concat(parts, axis=1).reset_index()

    # THE WEIGHTS. Geometric decay: the most recent season gets 1, the one
    # before it `decay`, the one before that `decay` squared. One number
    # controls the whole shape, which is the point -- a three-season window
    # with three free weights is three chances to overfit, while a decay rate
    # is one, and it cannot produce the nonsense of trusting a three-year-old
    # season more than last year's. The locked 60/40 rule is exactly this with
    # two seasons and a decay of 0.667, so the production baseline remains a
    # special case of the general form rather than a different code path.
    w = np.array([decay ** (i - 1) for i in lags], dtype=float)

    avail = np.column_stack([m[f"GP_{lag}"].notna().to_numpy() for lag in lags])

    out = pd.DataFrame({"career_key": m["career_key"], "t0": m["t0"]})
    out["n_seasons"] = avail.sum(axis=1)
    out["one_season"] = (out["n_seasons"] == 1).astype(float)
    out["pkey"] = _first_available(m, "pkey", lags)
    out["pos"] = _first_available(m, "pos", lags)
    out["is_D"] = (out["pos"] == "D").astype(float)
    for c in ["exp_seasons", "exp_censored", "has_age", "toi_pg"]:
        out[c] = _first_available(m, c, lags)

    # AGE AT THE VALUATION SEASON, not at the trailing season the anchor came
    # from. The anchor may be three years old; the player is not. `age` on a
    # season row is his age in that season, so each lag is stepped forward by
    # its own distance before the most recent available one is taken.
    aged = [m[f"age_{lag}"] + float(lag) for lag in lags]
    age = aged[0]
    for nxt in aged[1:]:
        age = age.fillna(nxt)
    out["age"] = age
    # Centred at 27, roughly the peak, so the linear term reads as "per year
    # either side of prime" and the square is small and well conditioned.
    out["age_c"] = out["age"] - 27.0
    out["age_c2"] = out["age_c"] ** 2

    def blend(col):
        """Weighted average over the seasons the player actually has.

        Renormalised over what is AVAILABLE, so a player with one qualifying
        season gets that season rather than a fraction of it. That is the
        locked rule generalised, and it is what keeps a short history from
        being silently pulled toward zero by the missing years.
        """
        vals = np.column_stack([m[f"{col}_{lag}"].to_numpy(float) for lag in lags])
        ok = np.isfinite(vals)
        ww = np.where(ok, w[None, :], 0.0)
        tot = ww.sum(axis=1)
        num = np.where(ok, np.nan_to_num(vals) * ww, 0.0).sum(axis=1)
        return np.where(tot > 0, num / np.where(tot > 0, tot, 1.0), np.nan)

    for c in cols:
        out["tw_" + c] = blend(c)              # trailing weighted TOTAL
        out["tr_" + c] = blend(c + "_82")      # trailing weighted RATE

    out["tr_gp_share"] = blend("gp_share")

    # Exposure: how much evidence the anchor rests on, in games. NOT
    # renormalised, deliberately -- unlike the blend above. A missing season
    # contributes zero games, so a player with one season of history has
    # genuinely less evidence behind his number than one with three, and the
    # shrinkage should pull him harder. Renormalising here would erase exactly
    # the distinction the shrinkage exists to act on.
    gp = np.column_stack([m[f"GP_{lag}"].fillna(0).to_numpy(float) for lag in lags])
    out["exposure_gp"] = (gp * w[None, :]).sum(axis=1) / w.sum()

    out["stale_history"] = 0.0

    # RETURNING PLAYERS. A player whose most recent qualifying season is older
    # than this model's window has no row above at all, because every row is
    # built by adding a lag inside the window to a season inside it. The
    # harness was willing to ask about him -- its eligibility window is three
    # seasons -- so dropping him here does not make him disappear evenly: it
    # removes exactly the players who missed a season and came back, which is
    # the population the participation model exists to price.
    #
    # He gets an anchor from his most recent qualifying season alone, tagged so
    # that a model, a report or a subgroup can treat a two-year-old number as
    # what it is. Only pairs MISSING from the window above are added, so no
    # existing anchor changes by a single digit.
    if stale and n_seasons < STALE_LOOKBACK:
        deep = _anchors(played, STALE_LOOKBACK, decay, stale=False, cols=cols)
        have = pd.MultiIndex.from_arrays([out["career_key"], out["t0"]])
        want = pd.MultiIndex.from_arrays([deep["career_key"], deep["t0"]])
        add = deep[~want.isin(have)].copy()
        if len(add):
            add["stale_history"] = 1.0
            out = pd.concat([out, add], ignore_index=True)

    # ELITE RELIEF TERMS. A straight pull-back toward the league is the best
    # LINEAR predictor, and a linear predictor under-shoots at the top whenever
    # the true relationship bends -- which it does here, because a high
    # trailing number from a genuinely good player regresses less than the same
    # number from a lucky one, and at the top of the distribution most of them
    # are good. The stress test measured the cost: 0.279 wins low in the top
    # decile, with all of it in the rate rather than participation.
    #
    # These terms let the pull weaken where the evidence is strongest. They are
    # OFFERED, not imposed: a model that does not list them in FEATURES behaves
    # exactly as before, and the bake-off decides whether they earn their place.
    #
    # Hinges rather than a square, because a square bends everywhere -- including
    # among the below-replacement players, where there is no reason to think the
    # relationship changes -- and because a hinge says exactly where the change
    # is being claimed.
    out["tw_hi1"] = np.clip(out["tw_WAR"] - 1.0, 0, None)
    out["tw_hi2"] = np.clip(out["tw_WAR"] - 2.0, 0, None)
    # Level interacted with the evidence behind it: a big number off a full
    # season is worth more than the same number off half of one.
    out["tw_x_exposure"] = out["tw_WAR"] * (out["exposure_gp"] / 82.0)
    return out.dropna(subset=["tw_WAR"]).reset_index(drop=True)


def _first_available(m: pd.DataFrame, col: str, lags) -> pd.Series:
    """The value from the most recent lag that has one."""
    out = m[f"{col}_{lags[0]}"]
    for lag in lags[1:]:
        out = out.fillna(m[f"{col}_{lag}"])
    return out


def _placeholder_participation(subs: pd.DataFrame, h) -> np.ndarray:
    """PLACEHOLDER until Phase 2. Everyone plays, every season.

    Deliberately crude and deliberately shared by every model in Phase 1: a
    placeholder that is identical across candidates cancels out of a
    comparison BETWEEN them, while a half-fitted one would not. Its cost shows
    up honestly in the harness as a Brier score of roughly the league's exit
    rate, and Phase 2 replaces it.
    """
    return np.ones(len(subs))


class A0Production(BaseModel):
    """The production chain's starting point. Nothing is fitted."""

    # Unrestricted, because nothing is fitted: this model carries one trailing
    # number flat at every horizon. That is why it is valid at any horizon and
    # also why it is a benchmark rather than a forecast.
    FITTED_HORIZONS = None
    # NOT "today's model". This is the chain's STARTING POINT with the aging
    # path and the survival weighting removed, and calling it today's model
    # put a comparison against a simpler rule into every report as though it
    # were a comparison against production. production_adapter.ProductionChain
    # is the live chain; this is the flat benchmark.
    name = "flat benchmark (trailing 60/40, carried flat)"

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].set_index("career_key")
        rows = []
        for h in horizons:
            r = subs.copy()
            tw = a["tw_WAR"].reindex(r["career_key"]).to_numpy()
            # The production chain prices and projects the TOTAL. Expressed as
            # a rate it is that total over a full 82, i.e. it assumes the
            # player repeats last year's availability as well as last year's
            # level -- exactly the conflation the rebuild separates.
            r["rate_82"] = tw
            r["gp_share"] = 1.0
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A1Calibrated(BaseModel):
    """The mandatory benchmark: the blend, pulled back toward the league by a
    coefficient FITTED on the rolling window, with position, the one-season
    flag and experience. Availability is forecast as its own trailing share
    instead of assumed full.

    Why a pull-back at all: a trailing total is a noisy measure of ability, so
    the best guess of next season sits between it and the league average. The
    fitted slope IS the shrinkage -- and because it is fitted per horizon, the
    model learns that a four-year-ahead forecast should sit closer to average
    than a one-year-ahead one, which the production chain's flat carry cannot.
    """
    name = "calibrated total"
    FEATURES = ["tw_WAR", "one_season", "is_D", "exp_seasons", "age_c", "age_c2"]

    def fit(self, table, before):
        super().fit(table, before)
        pairs = self._training_pairs(table, before, C.CANDIDATE_HORIZONS)
        self.coef_, self.gp_coef_ = {}, {}
        for h, g in pairs.groupby("h"):
            r = g.dropna(subset=["y_rate"])           # rate fit: seasons played
            self.coef_[h] = (_ols(r[self.FEATURES], r["y_rate"], _rate_weight(r))
                             if len(r) > 50 else None)
            s = g.dropna(subset=["y_gp_share"])
            self.gp_coef_[h] = _ols(s[["tr_gp_share", "is_D", "exp_seasons", "age_c"]],
                                    s["y_gp_share"]) if len(s) > 50 else None

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = _apply(self.coef_.get(h), a[self.FEATURES], a["tw_WAR"])
            gp = _apply(self.gp_coef_.get(h), a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]],
                        a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A2Raw(A1Calibrated):
    """A2 WITHOUT the shrinkage: the seven component rates fed to the same
    regression A1 uses. Kept as a diagnostic, not a candidate.

    It isolates one question -- does splitting the total into components help
    on its own? -- and the answer on the development pages is no: a per-82
    component rate is a much noisier regressor than a trailing total, and
    seven of them are seven times as noisy. That result is what makes the
    shrinkage in A2Component load-bearing rather than decorative.
    """
    name = "component split, no shrinking (diagnostic)"

    @property
    def FEATURES(self):
        return (["tr_" + c for c in C.COMPONENTS_MODEL]
                + ["tr_gp_share", "exposure_gp", "one_season", "is_D", "exp_seasons"])


class A2Component(A1Calibrated):
    """The lead candidate: seven components, each shrunk by its own reliability.

    THE CASE FOR THE STRUCTURE. Shooting is about half the covariance of WAR
    per 82 with itself but carries a year-to-year correlation of only 0.35,
    while even-strength offence carries 0.66. A model that forecasts the TOTAL
    applies one average persistence to both, so it over-carries a hot shooting
    season and under-carries an even-strength one. That is the same defect as
    the star tilt, one level down.

    THE SHRINKAGE, which is the part that matters. For each component c, the
    player's observed per-82 rate is pulled toward the norm for his position
    by an amount that depends on how much evidence there is:

        shrunk = (games * observed + k_c * norm) / (games + k_c)

    k_c is that component's RELIABILITY CONSTANT, in games: the number of
    games of evidence needed before the player's own rate carries as much
    weight as the norm. A noisy component (shooting) gets a large k_c and is
    pulled hard; a stable one (even-strength offence) gets a small k_c and is
    left nearly alone. k_c is FITTED, per component, on the rolling training
    window -- never assumed, never carried across pages.

    This is why exposure belongs in the shrinkage rather than in the
    regression as a linear term. A forty-game season is not a season with a
    smaller number attached to it; it is the same number believed half as
    much, which is a multiplicative statement about evidence, not an additive
    one about level. A1 cannot express that. This is the whole argument for
    the component structure -- not the headline margin, which is small.
    """
    name = "component model"

    # Candidate reliability constants, in games of evidence needed before a
    # player's own rate outweighs the league norm.
    #
    # THE TOP OF THE GRID USED TO BIND. At 1280 the penalty-kill constant
    # pinned at the ceiling for every horizon from three seasons out, and the
    # unallocated residual pinned everywhere -- 9 of 42 cells, concentrated at
    # exactly the horizons where the component model was losing. A pinned cell
    # is the fit saying "shrink this harder than you are letting me", and
    # answering that with a ceiling is a modelling choice made by an array
    # literal rather than by the data.
    #
    # The grid now runs to 1e9, which is not a number of games but a way of
    # spelling "ignore this player's own rate and use the norm": at that size
    # the weighted average is the norm to seven decimal places. Some components
    # genuinely carry no signal five seasons out, and the honest answer for
    # those is the norm, not the norm plus a thousandth of a stale observation.
    K_GRID = np.array([1, 2, 5, 10, 20, 40, 80, 160, 320, 640, 1280,
                       2560, 5120, 10240, 1e9], dtype=float)

    RATE_FEATURES = ["sh_" + c for c in C.COMPONENTS_MODEL] + [
        "tr_gp_share", "one_season", "is_D", "exp_seasons", "age_c", "age_c2"]

    def fit(self, table, before):
        BaseModel.fit(self, table, before)
        s = table[table["GP"] >= C.MIN_GP]

        # THE NORM each component is shrunk toward. Position-specific and
        # computed on the training window ONLY, so it is a fact about the
        # league as it was known, not as it turned out. Age enters here in
        # Phase 3, once birthdates cover enough of the panel to support it;
        # with 0% age coverage in this checkout, position alone is the norm
        # and the harness reports it as such rather than silently degrading.
        self.norm_ = self._fit_norms(s)
        self.k_ = self._fit_reliability(s, before)

        pairs = self._training_pairs(table, before, C.CANDIDATE_HORIZONS)
        pairs = self._shrink(pairs)
        self.coef_, self.gp_coef_ = {}, {}
        for h, g in pairs.groupby("h"):
            r = g.dropna(subset=["y_rate"])
            self.coef_[h] = (_ols(r[self.RATE_FEATURES], r["y_rate"], _rate_weight(r))
                             if len(r) > 50 else None)
            q = g.dropna(subset=["y_gp_share"])
            self.gp_coef_[h] = _ols(q[["tr_gp_share", "is_D", "exp_seasons", "age_c"]],
                                    q["y_gp_share"]) if len(q) > 50 else None

    # A norm cell needs this many seasons before it is trusted on its own;
    # thinner cells fall back to the position norm. Without the floor the
    # 41-year-old cell would be three players and the shrinkage target for a
    # 38-year-old would be noise dressed up as a norm.
    MIN_NORM_CELL = 40
    AGE_LO, AGE_HI = 19, 38

    def _fit_norms(self, s: pd.DataFrame) -> dict:
        """The AGE-AND-POSITION norm each component is shrunk toward.

        The plan specifies age here and it matters: shrinking a 35-year-old
        toward the average 27-year-old builds the aging curve into the
        shrinkage, in the wrong direction, before Phase 3 gets a say. Ages are
        clipped into a range where the cells are populated, so the oldest and
        youngest players shrink toward the edge cell rather than toward a cell
        of three people.

        Computed on the training window only, so it is a fact about the league
        as it was known on the decision date.
        """
        s = s.copy()
        s["_ab"] = s["age"].clip(self.AGE_LO, self.AGE_HI).round()
        norms = {}
        for c in C.COMPONENTS_MODEL:
            col = c + "_82"
            by_pos = s.groupby("pos")[col].mean().to_dict()
            g = s.groupby(["pos", "_ab"])[col].agg(["mean", "size"])
            cell = {k: (v["mean"] if v["size"] >= self.MIN_NORM_CELL else by_pos.get(k[0]))
                    for k, v in g.iterrows()}
            norms[c] = {"cell": cell, "pos": by_pos}
        return norms

    def _norm_for(self, c: str, pos: pd.Series, age: pd.Series) -> np.ndarray:
        """Look up the norm per row, falling back to the position norm where a
        player has no age at all -- 1.7% of rows, and they must not be dropped."""
        n = self.norm_[c]
        ab = age.clip(self.AGE_LO, self.AGE_HI).round()
        out = [n["cell"].get((p, a), n["pos"].get(p)) if pd.notna(a) else n["pos"].get(p)
               for p, a in zip(pos, ab)]
        return np.array([np.nan if v is None else v for v in out], dtype=float)

    def _fit_reliability(self, s: pd.DataFrame, before: int) -> dict:
        """Fit k_c per component on consecutive season pairs whose OUTCOME is
        before `before`.

        The criterion is the one the constant is FOR: shrink season t's rate
        with candidate k, then see how well it predicts season t+1's rate.
        Errors are weighted by the OUTCOME season's games, because a rate
        measured over eighty games is a sharper target than one measured over
        twelve, and an unweighted fit would let the noisiest outcomes choose k.
        """
        pairs = s.merge(s.assign(syr=s["syr"] - 1), on=["career_key", "syr"],
                        suffixes=("", "_n"))
        pairs = pairs[pairs["syr"] + 1 < before]
        k = {}
        if len(pairs) < 100:
            return {c: 100.0 for c in C.COMPONENTS_MODEL}   # thin window: shrink hard
        w = pairs["GP_n"].to_numpy(float)
        for c in C.COMPONENTS_MODEL:
            obs = pairs[c + "_82"].to_numpy(float)
            gp = pairs["GP"].to_numpy(float)
            nxt = pairs[c + "_82_n"].to_numpy(float)
            norm = self._norm_for(c, pairs["pos"], pairs["age"])
            sse = [(w * ((gp * obs + kk * norm) / (gp + kk) - nxt) ** 2).sum()
                   for kk in self.K_GRID]
            k[c] = float(self.K_GRID[int(np.argmin(sse))])
        return k

    def _shrink(self, d: pd.DataFrame) -> pd.DataFrame:
        """Apply the fitted constants. Exposure is the trailing weighted games
        behind the blended rate, so the same 60/40 window that produces the
        rate produces the evidence count for it."""
        d = d.copy()
        gp = d["exposure_gp"].to_numpy(float)
        pos = d["pos"]
        for c in C.COMPONENTS_MODEL:
            norm = self._norm_for(c, pos, d["age"])
            obs = d["tr_" + c].to_numpy(float)
            kk = self.k_[c]
            d["sh_" + c] = (gp * obs + kk * norm) / (gp + kk)
        return d

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = self._shrink(a[a["t0"] == iset.t0]).set_index("career_key").reindex(
            subs["career_key"])
        rows = []
        for h in horizons:
            r = subs.copy()
            # Fallback when the fit is too thin: the SHRUNK total, not the raw
            # one. A model whose fallback is the unshrunk number would look
            # better than it is in early pages.
            fb = a[["sh_" + c for c in C.COMPONENTS_MODEL]].sum(axis=1)
            r["rate_82"] = _apply(self.coef_.get(h), a[self.RATE_FEATURES], fb)
            gp = _apply(self.gp_coef_.get(h), a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]],
                        a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


def _ols(X: pd.DataFrame, y: pd.Series, w: pd.Series | None = None):
    """Least squares with an intercept, on complete rows only. Returns None if
    the design is rank-deficient or too thin -- the caller then falls back to
    the raw trailing value, which is the honest answer when the window has not
    yet accumulated enough history to fit anything.

    `w` is a precision weight, in practice the games behind each rate. A rate
    from a handful of games estimates the same quantity as a full season's
    rate with far more noise, so weighting by games is what stops one cameo
    from carrying a full season's authority in the fit. Rows are scaled by the
    square root of the weight, which is the standard way of writing weighted
    least squares as an ordinary one.
    """
    parts = [X, y.rename("_y")]
    if w is not None:
        parts.append(w.rename("_w"))
    d = pd.concat(parts, axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < 50:
        return None
    A = np.column_stack([np.ones(len(d)), d[X.columns].to_numpy(float)])
    b = d["_y"].to_numpy(float)
    if w is not None:
        rw = np.sqrt(np.clip(d["_w"].to_numpy(float), 0.0, None))
        if not rw.any():
            return None
        A, b = A * rw[:, None], b * rw
    try:
        beta, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return list(X.columns), beta


def _rate_weight(g: pd.DataFrame) -> pd.Series | None:
    """The games behind each rate observation, or None when weighting is off."""
    if not C.RATE_WEIGHT_BY_GAMES or "y_gp" not in g.columns:
        return None
    return g["y_gp"].clip(lower=0.0)


def _apply(coef, X: pd.DataFrame, fallback: pd.Series) -> np.ndarray:
    """Apply a fitted line, falling back row-wise where a feature is missing.
    Row-wise on purpose: a player with one trailing season should not be
    dropped from the page, he should get the simpler answer."""
    fb = np.asarray(fallback, dtype=float)
    if coef is None:
        return fb
    cols, beta = coef
    M = X[cols].to_numpy(float)
    ok = np.isfinite(M).all(axis=1)
    out = fb.copy()
    out[ok] = beta[0] + M[ok] @ beta[1:]
    return out


# ---------------------------------------------------------------------------
# VARIANTS. Each isolates one design choice so the bake-off can attribute a
# change in accuracy to that choice and nothing else. They are candidates, not
# replacements: the rebuild plan's own sequence keeps every live candidate
# running through aging, participation and pricing before anything is retired,
# because a model can be behind on raw forecast accuracy and still win once
# it is carrying dollars.
# ---------------------------------------------------------------------------

class A2NoAgeTerms(A2Component):
    """The component model with age in the SHRINKAGE TARGET only.

    The full component model knows a player's age twice: once because each
    component is pulled toward the norm for his age and position, and again
    because age enters the regression as its own term. That may be telling it
    the same thing twice. Doubling up is not free -- the second copy gives the
    fit another way to bend itself around the training seasons, and the place
    that shows up is the far end of a contract, where the trailing evidence has
    decayed and there is little left to constrain it.

    This variant removes the second copy and keeps the first.
    """
    name = "component model, age in the norm only"
    RATE_FEATURES = ["sh_" + c for c in C.COMPONENTS_MODEL] + [
        "tr_gp_share", "one_season", "is_D", "exp_seasons"]


class A1NoAgeTerms(A1Calibrated):
    """The calibrated total with its age terms removed.

    The control. Without it, a win for the variant above could mean either
    "age terms hurt the component model specifically" or "age terms hurt every
    model here", and those have opposite implications. Running both arms is
    what makes the comparison a test rather than an anecdote.
    """
    name = "calibrated total, no age terms"
    FEATURES = ["tw_WAR", "one_season", "is_D", "exp_seasons"]


class A2PerHorizonTrust(A2Component):
    """The component model that decides how far to trust a player SEPARATELY
    for each season it is forecasting.

    The reliability constant answers "how many games of evidence before this
    player's own rate outweighs the league norm?". The base model fits it once,
    against next season, and then reuses that answer for all six seasons of a
    contract. That is the wrong shape: a rate that half-predicts next season
    predicts the season after that less, and the season after that less again,
    so a six-year-out forecast should sit closer to the norm than a one-year-out
    forecast. The base model cannot say so, and the horizons where it loses are
    exactly the ones where it should be shrinking harder.

    Here the constant is fitted per horizon, on pairs the right distance apart,
    still using only outcomes that completed before the decision date.
    """
    name = "component model, trust fitted per horizon"

    def fit(self, table, before):
        super().fit(table, before)
        s = table[table["GP"] >= C.MIN_GP]
        self.k_by_h_ = {}
        for h in self.fitted_horizons_:
            self.k_by_h_[h] = self._fit_reliability_at(s, before, h + 1)

    def _fit_reliability_at(self, s, before, gap):
        """Same criterion as the base fit, but predicting `gap` seasons ahead
        instead of always one. Falls back to the one-season constants when a
        gap has too few completed pairs, which is what the early pages hit."""
        pairs = s.merge(s.assign(syr=s["syr"] - gap), on=["career_key", "syr"],
                        suffixes=("", "_n"))
        pairs = pairs[pairs["syr"] + gap < before]
        if len(pairs) < 100:
            return dict(self.k_)
        w = pairs["GP_n"].to_numpy(float)
        k = {}
        for c in C.COMPONENTS_MODEL:
            obs = pairs[c + "_82"].to_numpy(float)
            gp = pairs["GP"].to_numpy(float)
            nxt = pairs[c + "_82_n"].to_numpy(float)
            norm = self._norm_for(c, pairs["pos"], pairs["age"])
            sse = [(w * ((gp * obs + kk * norm) / (gp + kk) - nxt) ** 2).sum()
                   for kk in self.K_GRID]
            k[c] = float(self.K_GRID[int(np.argmin(sse))])
        return k

    def _shrink_with(self, d, k):
        d = d.copy()
        gp = d["exposure_gp"].to_numpy(float)
        for c in C.COMPONENTS_MODEL:
            norm = self._norm_for(c, d["pos"], d["age"])
            obs = d["tr_" + c].to_numpy(float)
            d["sh_" + c] = (gp * obs + k[c] * norm) / (gp + k[c])
        return d

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        base = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        base = base[base["t0"] == iset.t0]
        rows = []
        for h in horizons:
            # The whole point: this horizon's own trust constants, not the
            # one-season-ahead ones.
            a = self._shrink_with(base, self.k_by_h_.get(h, self.k_)) \
                    .set_index("career_key").reindex(subs["career_key"])
            r = subs.copy()
            fb = a[["sh_" + c for c in C.COMPONENTS_MODEL]].sum(axis=1)
            r["rate_82"] = _apply(self.coef_.get(h), a[self.RATE_FEATURES], fb)
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A2PerHorizonTrustNoAge(A2PerHorizonTrust):
    """Both repairs at once: trust fitted per horizon AND age carried only by
    the shrinkage target. If the two fixes address different parts of the same
    problem, this is where that shows."""
    name = "component model, per-horizon trust, age in the norm only"
    RATE_FEATURES = ["sh_" + c for c in C.COMPONENTS_MODEL] + [
        "tr_gp_share", "one_season", "is_D", "exp_seasons"]


# ---------------------------------------------------------------------------
# THREE-SEASON WINDOW. The rebuild plan specifies "weights over three or more
# seasons ... fitted, not fixed", and until now every model here read only the
# last two through the locked 60/40 blend. More evidence behind the anchor
# should matter most at the long horizons, which is exactly where the
# component model has been losing -- so this is the test that could change the
# standing, and it is applied to BOTH models so the comparison stays fair.
# ---------------------------------------------------------------------------

class A1Calibrated3(A1Calibrated):
    """The calibrated total, reading three seasons with a fitted decay rate."""
    name = "calibrated total, three-season window"
    N_SEASONS = 3
    FIT_DECAY = True


class A2PerHorizonTrust3(A2PerHorizonTrust):
    """The component model with per-horizon trust, reading three seasons.

    Two mechanisms that should compound. A third season is more evidence, so
    the shrinkage has more to work with and pulls less hard toward the norm;
    and the components that needed the most pulling -- shooting, penalty kill --
    are precisely the noisy ones a longer window helps most, because averaging
    three seasons of finishing luck leaves less luck in the number than
    averaging two.
    """
    name = "component model, per-horizon trust, three-season window"
    N_SEASONS = 3
    FIT_DECAY = True


class A2PerHorizonTrust4(A2PerHorizonTrust):
    """Four seasons. Included to find where the window stops paying rather
    than assuming three is the answer because three was the number in the
    plan. A window that keeps helping is telling us something; one that turns
    over tells us the anchor has all the evidence it can use."""
    name = "component model, per-horizon trust, four-season window"
    N_SEASONS = 4
    FIT_DECAY = True


class A2PerHorizonAll3(A2PerHorizonTrust3):
    """The component model with BOTH window settings fitted per horizon.

    Per-horizon trust is already in. This adds the symmetric half: how fast to
    discount older seasons is also allowed to differ by how far ahead the
    forecast reaches. The reasoning is the same as for trust. Last season is
    the most informative thing about next season, so a short-horizon forecast
    should lean on it; but five seasons out, last season's particular bounces
    matter less than a stable read on what the player is, so the window should
    flatten. A single decay rate chosen against next season cannot say that.
    """
    name = "component model, trust and window both fitted per horizon"

    def fit(self, table, before):
        super().fit(table, before)
        s = table[table["GP"] >= C.MIN_GP]
        act = s.set_index(["career_key", "syr"])
        self.decay_by_h_ = {}
        for h in self.fitted_horizons_:
            self.decay_by_h_[h] = self._fit_decay_at(s, act, before, h)

    def _fit_decay_at(self, s, act, before, h):
        """Same criterion as the shared decay fit, but scored against the
        season h ahead rather than the valuation season. Falls back to the
        shared rate where a horizon has too few completed outcomes."""
        best, best_sse = self.decay_, np.inf
        for d in self.DECAY_GRID:
            a = _anchors(s, self.N_SEASONS, float(d))
            a = a[a["t0"] + h < before]
            ix = pd.MultiIndex.from_arrays([a["career_key"], a["t0"] + h])
            y = act["WAR_82"].reindex(ix).to_numpy()
            gp = act["GP"].reindex(ix).to_numpy()
            ok = np.isfinite(y) & np.isfinite(a["tr_WAR"].to_numpy())
            if ok.sum() < 200:
                continue
            e = a["tr_WAR"].to_numpy()[ok] - y[ok]
            sse = float((gp[ok] * e ** 2).sum())
            if sse < best_sse:
                best, best_sse = float(d), sse
        return best

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        played = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
        rows = []
        for h in horizons:
            # This horizon's own window shape AND its own trust settings.
            base = _anchors(played, self.N_SEASONS, self.decay_by_h_.get(h, self.decay_))
            base = base[base["t0"] == iset.t0]
            a = self._shrink_with(base, self.k_by_h_.get(h, self.k_)) \
                    .set_index("career_key").reindex(subs["career_key"])
            r = subs.copy()
            fb = a[["sh_" + c for c in C.COMPONENTS_MODEL]].sum(axis=1)
            r["rate_82"] = _apply(self.coef_.get(h), a[self.RATE_FEATURES], fb)
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A1Calibrated3PerHorizon(A1Calibrated3):
    """The control arm: the same per-horizon window, on the simple model. If
    per-horizon windows help both, it is a general fix and says nothing about
    which anchor is better."""
    name = "calibrated total, window fitted per horizon"

    def fit(self, table, before):
        super().fit(table, before)
        s = table[table["GP"] >= C.MIN_GP]
        act = s.set_index(["career_key", "syr"])
        self.decay_by_h_ = {h: A2PerHorizonAll3._fit_decay_at(self, s, act, before, h)
                            for h in self.fitted_horizons_}

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        played = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
        rows = []
        for h in horizons:
            a = _anchors(played, self.N_SEASONS, self.decay_by_h_.get(h, self.decay_))
            a = a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])
            r = subs.copy()
            r["rate_82"] = _apply(self.coef_.get(h), a[self.FEATURES], a["tw_WAR"])
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------------------
# A WINDOW PER COMPONENT. The one place the component idea has not yet been
# allowed to speak. Every model so far reads the same number of trailing
# seasons, discounted at the same rate, for every skill -- which is exactly
# the assumption the component thesis denies. Shooting is the noisiest part of
# WAR, so averaging three or four seasons of finishing luck should leave less
# luck in the number; even-strength offence is the stickiest, so last season
# is already a good read and reaching further back mostly adds stale
# information about a player who has since changed.
#
# If the component thesis is right anywhere, it should be right here: this is
# a claim a single blended total is structurally incapable of making.
# ---------------------------------------------------------------------------

def _anchors_per_component(played: pd.DataFrame, n_seasons: int,
                           decays: dict, default_decay: float) -> pd.DataFrame:
    """Anchors where each component is blended over its OWN window shape.

    Built by assembling anchors at each distinct decay rate and taking each
    component's column from the build that used its own rate. Splicing rather
    than rewriting the anchor builder is deliberate: the shared builder stays
    the single definition of how a window is formed, so this variant cannot
    drift away from it, and the regression guard that pins the two-season path
    keeps covering both.

    Exposure is spliced per component too. Exposure is the count of evidence
    behind a number, and if a component is blended over a different window it
    rests on a different amount of evidence -- carrying one shared exposure
    would tell the shrinkage the wrong thing about six of the seven parts.
    """
    base = _anchors(played, n_seasons, default_decay).set_index(["career_key", "t0"])
    built = {d: _anchors(played, n_seasons, d).set_index(["career_key", "t0"])
             for d in set(decays.values())}
    for c, d in decays.items():
        src = built[d]
        base["tr_" + c] = src["tr_" + c].reindex(base.index)
        base["exp_" + c] = src["exposure_gp"].reindex(base.index)
    return base.reset_index()


class A2PerComponentWindow(A2PerHorizonTrust3):
    """The component model with a window fitted separately for each skill.

    Everything else is the standing best component model: trust fitted per
    horizon, three seasons available, age in both the norm and the regression.
    The only change is that each of the seven components chooses how fast to
    discount older seasons for itself.
    """
    name = "component model, window fitted per component"

    def fit(self, table, before):
        # ORDER MATTERS. The inherited fit builds training pairs through
        # _anchor_frame, which needs the per-component windows to already
        # exist, so they are fitted first. The shared decay is settled before
        # that because it is this fit's fallback when a component has too few
        # completed outcomes to choose for itself.
        BaseModel.fit(self, table, before)
        s = table[table["GP"] >= C.MIN_GP]
        self.comp_decay_ = self._fit_component_decays(s, before)
        super().fit(table, before)

    def _fit_component_decays(self, s: pd.DataFrame, before: int) -> dict:
        """One decay rate per component, on the rolling window.

        Criterion matches what the number is for: blend component c over the
        window, then see how well it predicts the SAME component next season.
        Errors weighted by the outcome season's games, so a rate measured over
        eighty games counts for more than one measured over twelve.
        """
        act = s.set_index(["career_key", "syr"])
        cache = {d: _anchors(s, self.N_SEASONS, float(d)) for d in self.DECAY_GRID}
        out = {}
        for c in C.COMPONENTS_MODEL:
            best, best_sse = self.decay_, np.inf
            for d in self.DECAY_GRID:
                a = cache[float(d)]
                a = a[a["t0"] < before]
                ix = pd.MultiIndex.from_arrays([a["career_key"], a["t0"]])
                y = act[c + "_82"].reindex(ix).to_numpy()
                gp = act["GP"].reindex(ix).to_numpy()
                x = a["tr_" + c].to_numpy()
                ok = np.isfinite(y) & np.isfinite(x)
                if ok.sum() < 200:
                    continue
                sse = float((gp[ok] * (x[ok] - y[ok]) ** 2).sum())
                if sse < best_sse:
                    best, best_sse = float(d), sse
            out[c] = best
        return out

    def _shrink_with(self, d, k):
        """As the parent, but each component is shrunk against the evidence
        behind ITS OWN window rather than a single shared exposure."""
        d = d.copy()
        for c in C.COMPONENTS_MODEL:
            gp = d["exp_" + c].to_numpy(float) if ("exp_" + c) in d.columns \
                else d["exposure_gp"].to_numpy(float)
            norm = self._norm_for(c, d["pos"], d["age"])
            obs = d["tr_" + c].to_numpy(float)
            d["sh_" + c] = (gp * obs + k[c] * norm) / (gp + k[c])
        return d

    def _anchor_frame(self, played):
        return _anchors_per_component(played, self.N_SEASONS, self.comp_decay_,
                                      self.decay_)

    def _training_pairs(self, table, before, horizons):
        """Same outcome-window rule as every other model; only the anchor
        construction differs, so the pairs are still built from anchors that
        cannot see the season they predict."""
        s = table[table["GP"] >= C.MIN_GP]
        anchors = self._anchor_frame(s)
        out = []
        for h in horizons:
            a = anchors.copy()
            a["season"] = a["t0"] + h
            a["h"] = h
            out.append(a[a["season"] < before])
        pairs = pd.concat(out, ignore_index=True)
        act = table.set_index(["career_key", "syr"])
        ix = pd.MultiIndex.from_arrays([pairs["career_key"], pairs["season"]])
        pairs["y_war"] = act["WAR"].reindex(ix).to_numpy()
        pairs["y_rate"] = act["WAR_82"].reindex(ix).to_numpy()
        pairs["y_gp_share"] = act["gp_share"].reindex(ix).to_numpy()
        # Same event as the other pair builder and as the participation model.
        pairs["y_gp"] = act["GP"].reindex(ix).to_numpy()
        pairs["y_played"] = np.nan_to_num(pairs["y_gp"]) >= C.PARTICIPATION_GP
        self._record_fitted_horizons(pairs)
        return pairs

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        played = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
        base = self._anchor_frame(played)
        base = base[base["t0"] == iset.t0]
        rows = []
        for h in horizons:
            a = self._shrink_with(base, self.k_by_h_.get(h, self.k_)) \
                    .set_index("career_key").reindex(subs["career_key"])
            r = subs.copy()
            fb = a[["sh_" + c for c in C.COMPONENTS_MODEL]].sum(axis=1)
            r["rate_82"] = _apply(self.coef_.get(h), a[self.RATE_FEATURES], fb)
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A2PerComponentWindow4(A2PerComponentWindow):
    """Four seasons available, so a noisy component can reach further back
    than three if the fit wants it to. With a shared window a fourth season
    was a null; the question is whether it is still a null once the
    components that cannot use it are free to ignore it."""
    name = "component model, window per component, four seasons available"
    N_SEASONS = 4


# ---------------------------------------------------------------------------
# AGING. Until now every model reached each horizon through its own separate
# regression: six independent maps from the anchor to six future seasons, each
# free to fit its own age coefficients. That is a REDUCED FORM. It can imitate
# an aging curve, but it never states one, it cannot be audited as one, and it
# cannot be walked forward a year at a time -- which is what Phase 5's
# simulation needs, because a career path is drawn step by step.
#
# These variants replace it with a STRUCTURAL form: map the anchor to the
# valuation season once, then walk that level forward on an explicit aging
# curve. Fewer parameters, an auditable curve, and the shape Phase 5 needs.
# The test is whether the structure costs accuracy against the six free
# regressions it replaces.
# ---------------------------------------------------------------------------

from aging_additive import AdditiveAging  # noqa: E402


class _AgingMixin:
    """Walk the valuation-season rate forward on the fitted aging curve."""
    AGING_LEVEL_MODE = "lagged"

    def fit(self, table, before):
        super().fit(table, before)
        self.aging_ = AdditiveAging(level_mode=self.AGING_LEVEL_MODE).fit(table, before)
        return self

    def _walk(self, r, rate0, a, h):
        """Walk the level forward, carrying it FLAT where the player has no age.

        An aging curve cannot age a player whose birthdate is unknown. The
        honest fallback is no aging at all -- the status quo before this curve
        existed -- rather than a guessed age, which would put a real number on
        a made-up position on the curve. It is 0.6% of rows here and every one
        of them is still scored, because a model that declines to predict its
        hard cases is scored on an easier sample than its rivals.
        """
        rate0 = np.asarray(rate0, dtype=float)
        if h == 0:
            return rate0
        age = a["age"].to_numpy(float)
        walked = self.aging_.walk(rate0, age, a["is_D"].to_numpy(float), h)
        return np.where(np.isfinite(age) & np.isfinite(walked), walked, rate0)


class A1Calibrated3Aging(_AgingMixin, A1Calibrated3):
    """The standing leader, reaching later seasons by aging rather than by a
    separate regression per horizon."""
    name = "calibrated total, three seasons, additive aging"

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])
        rate0 = _apply(self.coef_.get(0), a[self.FEATURES], a["tw_WAR"])
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = self._walk(r, rate0, a, h)
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A2ComponentAging(_AgingMixin, A2PerComponentWindow):
    """The best component model, likewise."""
    name = "component model, per-component window, additive aging"

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        played = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
        base = self._anchor_frame(played)
        base = base[base["t0"] == iset.t0]
        a = self._shrink_with(base, self.k_by_h_.get(0, self.k_)) \
                .set_index("career_key").reindex(subs["career_key"])
        fb = a[["sh_" + c for c in C.COMPONENTS_MODEL]].sum(axis=1)
        rate0 = _apply(self.coef_.get(0), a[self.RATE_FEATURES], fb)
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = self._walk(r, rate0, a, h)
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = _placeholder_participation(r, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A1Calibrated3AgingNaive(A1Calibrated3Aging):
    """The SAME model with the biased aging curve -- level measured from the
    season the change starts from. Kept as a candidate so the register carries
    the cost of the bias in forecast error, not just in a correlation. It
    should lose; if it does not, the identification argument needs rechecking
    rather than repeating."""
    name = "calibrated total, aging fitted the naive way (diagnostic)"
    AGING_LEVEL_MODE = "same"


# ---------------------------------------------------------------------------
# PARTICIPATION. Replaces the placeholder in which everyone plays forever.
# The diagnosis from the aging work was that the walk's long-horizon deficit
# was a participation deficit: at five seasons out among the 34-and-overs it
# predicted below zero for 99% of them while 98% had already stopped playing.
# These variants are the test of that diagnosis.
# ---------------------------------------------------------------------------

from participation_model import ParticipationModel  # noqa: E402


class _ParticipationMixin:
    """Fit a participation model alongside, and use it instead of the
    placeholder. `USE_CONTRACTS` is the switch that says how much of the
    answer rests on the contract export, whose coverage on the development
    seasons runs from 11% in 2015 to 99% in 2021 -- so a variant that leans on
    it is being judged mostly on its late pages."""
    USE_CONTRACTS = True
    # WHAT THE CONTRACT COLUMNS MEAN when contracts are used, and which of them
    # are left out. The defaults reproduce every recorded run. The skater
    # contract-data test (run_skater_contract_test.py) varies these to separate
    # the export-membership signal, the before/after-2018 period indicator the
    # "observable" definition carries, and visible contract status -- the same
    # split the goalie branch needed (Goalie_Participation_Top.md).
    CONTRACT_STATE = "as_known"
    PART_EXCLUDE = ()

    def fit(self, table, before):
        super().fit(table, before)
        contracts = None
        if self.USE_CONTRACTS:
            try:
                from contract_source import load_contracts
                contracts, _ = load_contracts()
            except Exception:                     # noqa: BLE001
                contracts = None
        n, d = self.N_SEASONS, self.decay_
        # THE SAME HORIZONS THE RATE WAS FITTED TO. Participation used to take
        # its own default of six while the rate reached as far as the page
        # allowed, so the two halves of the forecast could disagree about which
        # seasons existed.
        self.part_ = ParticipationModel(
            contracts, exclude=tuple(self.PART_EXCLUDE),
            contract_state=self.CONTRACT_STATE).fit(
            table, before, anchors_fn=lambda p: _anchors(p, n, d),
            horizons=self.fitted_horizons_)
        return self

    @property
    def reads_contracts(self) -> bool:
        """Whether this model's participation depends on contract state, and
        so on the date that state is read at."""
        return bool(self.USE_CONTRACTS) and getattr(self.part_, "spans", None) is not None

    def p_play_signed(self, iset, keys, horizons, dates) -> dict:
        """Participation for each (player, date) row, contract state read at
        that row's DATE -- a contract's signing -- instead of 1 July of the
        page. Returns {h: array aligned with `keys`}.

        WHY: a contract is valued at its signing, and a deal signed in October
        is part of what the club knew when it signed it. The page-dated forecast
        treats it as unknown, which moved participation from 34% to 59% for one
        contract (Chara, October 2021) under visible contract status. The
        harness scores pages at 1 July, where the page date is the right one;
        a contract valuation is dated at its own decision.

        Horizons past the fitted range follow `predict_beyond_fit`'s rule: the
        last fitted horizon's participation times the model's own cached
        league-wide decay per extra season, clipped as there. So the only
        thing that changes is the date contract state is read at.
        """
        keys = list(keys)
        dates = pd.to_datetime(np.asarray(dates))
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].drop_duplicates("career_key").set_index("career_key")
        rows = a.reindex(keys).reset_index()
        fitted = sorted(getattr(self, "fitted_horizons_", None) or self.FITTED_HORIZONS)
        out = {}
        for h in sorted({int(x) for x in horizons}):
            hh = h if h in fitted else fitted[-1]
            base = self.part_.base_[hh]
            p = self._part_predict(rows, hh, as_of=dates).to_numpy(float)
            p = np.where(np.isfinite(p), p, base)
            if h not in fitted:
                _g_prod, g_play = self._tail_decay(iset, fitted[-1], fitted[-2])
                p = np.clip(p * g_play ** (h - fitted[-1]), 0.005, 0.995)
            out[h] = p
        return out

    def _part_predict(self, rows, h, as_of=None):
        """The one place participation is asked for a horizon, so a variant
        that changes how a horizon is answered changes it for the harness,
        the page-dated and the signing-dated callers alike."""
        return self.part_.predict(rows, h, as_of=as_of)

    def _p_play(self, a, subs, h):
        p = self._part_predict(a.reset_index(), h)
        p = p[~p.index.duplicated()]
        # The horizon is guaranteed fitted by _guard_horizons, so this horizon
        # HAS a base rate and the fallback is the league's own number for it
        # rather than a hardcoded 0.6. It applies per player, to a subject the
        # anchor frame has no row for, not to a whole unfitted horizon.
        base = self.part_.base_[h]
        return p.reindex(subs["career_key"]).fillna(base).to_numpy()


class A1AgingParticipation(_ParticipationMixin, A1Calibrated3Aging):
    """The calibrated total with the aging walk AND participation."""
    name = "calibrated total, aging, participation"

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])
        rate0 = _apply(self.coef_.get(0), a[self.FEATURES], a["tw_WAR"])
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = self._walk(r, rate0, a, h)
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = self._p_play(a, subs, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A1AgingParticipationNoContracts(A1AgingParticipation):
    """The same without the contract export, so the register carries how much
    of the participation gain rests on a feature whose coverage differs
    sharply between the development and the confirmatory seasons."""
    name = "calibrated total, aging, participation (no contract data)"
    USE_CONTRACTS = False


class A1ParticipationNoAging(_ParticipationMixin, A1Calibrated3):
    """Participation WITHOUT the aging walk -- the six free regressions again.
    Isolates how much participation is worth on its own, so the aging result
    can be read against a like-for-like baseline rather than against a model
    that changed two things at once."""
    name = "calibrated total, participation, no aging walk"

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = _apply(self.coef_.get(h), a[self.FEATURES], a["tw_WAR"])
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = self._p_play(a, subs, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


class A2AgingParticipation(_ParticipationMixin, A2ComponentAging):
    """The best component model, with aging and participation."""
    name = "component model, aging, participation"

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        played = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
        base = self._anchor_frame(played)
        base = base[base["t0"] == iset.t0]
        a = self._shrink_with(base, self.k_by_h_.get(0, self.k_)) \
                .set_index("career_key").reindex(subs["career_key"])
        fb = a[["sh_" + c for c in C.COMPONENTS_MODEL]].sum(axis=1)
        rate0 = _apply(self.coef_.get(0), a[self.RATE_FEATURES], fb)
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = self._walk(r, rate0, a, h)
            gp = _apply(self.gp_coef_.get(h),
                        a[["tr_gp_share", "is_D", "exp_seasons", "age_c"]], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = self._p_play(a, subs, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------------------
# SURVIVORSHIP-CORRECTED AGING. Step three of Phase 3. The aging curve is
# fitted on players who played both seasons; the ones who declined hardest
# stopped playing and are missing. Two corrections, run as competitors.
# ---------------------------------------------------------------------------

class A1AgingParticipationImputed(A1AgingParticipation):
    """The leader, with the missing seasons put back at replacement level."""
    name = "calibrated total, aging (survivorship-imputed), participation"
    AGING_SELECTION = "impute"

    def fit(self, table, before):
        super().fit(table, before)
        self.aging_ = AdditiveAging(level_mode=self.AGING_LEVEL_MODE,
                                    selection=self.AGING_SELECTION).fit(table, before)
        return self


class A1AgingParticipationIPW(A1AgingParticipationImputed):
    """The same with inverse-probability weighting instead. Registered so the
    approach that does not work is on the record with a number against it,
    rather than being dropped because it disagreed with expectation."""
    name = "calibrated total, aging (survivorship-IPW), participation"
    AGING_SELECTION = "ipw"


class A1AgingParticipationImputedNC(A1AgingParticipationImputed):
    """The standing leader's configuration -- no contract data -- plus the
    survivorship correction. This is the like-for-like test."""
    name = "calibrated total, aging (survivorship-imputed), participation (no contracts)"
    USE_CONTRACTS = False


class A2AgingParticipationImputed(A2AgingParticipation):
    """The component model, likewise."""
    name = "component model, aging (survivorship-imputed), participation"
    AGING_SELECTION = "impute"

    def fit(self, table, before):
        super().fit(table, before)
        self.aging_ = AdditiveAging(level_mode=self.AGING_LEVEL_MODE,
                                    selection=self.AGING_SELECTION).fit(table, before)
        return self


class _ImputeLevel:
    """Sensitivity arms: where a departing player is assumed to have been."""
    AGING_IMPUTE_LEVEL = 0.0
    AGING_RETURNERS = False

    def fit(self, table, before):
        super(A1AgingParticipationImputed, self).fit(table, before)
        self.aging_ = AdditiveAging(level_mode=self.AGING_LEVEL_MODE,
                                    selection="impute",
                                    impute_level=self.AGING_IMPUTE_LEVEL,
                                    impute_returners=self.AGING_RETURNERS).fit(table, before)
        return self


class A1ImputeMinus50(_ImputeLevel, A1AgingParticipationImputedNC):
    name = "leader, departing players assumed half a win below replacement"
    AGING_IMPUTE_LEVEL = -0.50


class A1ImputeMinus25(_ImputeLevel, A1AgingParticipationImputedNC):
    name = "leader, departing players assumed a quarter win below replacement"
    AGING_IMPUTE_LEVEL = -0.25


class A1ImputePlus25(_ImputeLevel, A1AgingParticipationImputedNC):
    name = "leader, departing players assumed a quarter win above replacement"
    AGING_IMPUTE_LEVEL = 0.25


class A1ImputeReturners(_ImputeLevel, A1AgingParticipationImputedNC):
    name = "leader, returners given their observed level on return"
    AGING_RETURNERS = True


# ---------------------------------------------------------------------------
# THE ELITE-RELIEF TEST. Stress test 1 located the star bias in the rate rather
# than participation: the top decile is predicted at 2.360 against an actual
# 2.698, while the probability of playing is almost exactly right. These
# variants let the regression bend where the stress test says it should.
# ---------------------------------------------------------------------------

class A1Hinge(A1AgingParticipationImputedNC):
    """The leader with a second slope above one win a season."""
    name = "leader + a second slope above one win"
    FEATURES = ["tw_WAR", "tw_hi1", "one_season", "is_D", "exp_seasons",
                "age_c", "age_c2"]


class A1HingeTwo(A1AgingParticipationImputedNC):
    """Two hinges: above one win and above two."""
    name = "leader + slopes above one and two wins"
    FEATURES = ["tw_WAR", "tw_hi1", "tw_hi2", "one_season", "is_D",
                "exp_seasons", "age_c", "age_c2"]


class A1Exposure(A1AgingParticipationImputedNC):
    """Level interacted with how many games stand behind it."""
    name = "leader + level interacted with evidence"
    FEATURES = ["tw_WAR", "tw_x_exposure", "one_season", "is_D", "exp_seasons",
                "age_c", "age_c2"]


class A1HingeExposure(A1AgingParticipationImputedNC):
    """Both."""
    name = "leader + hinge and evidence interaction"
    FEATURES = ["tw_WAR", "tw_hi1", "tw_x_exposure", "one_season", "is_D",
                "exp_seasons", "age_c", "age_c2"]


class A1HingeExposureStatus(A1HingeExposure):
    """The skater leader with VISIBLE CONTRACT STATUS in its participation
    model. Adopted provisionally 2026-09-23 (Skater_Contract_Test.md).

    Identical to `A1HingeExposure` in ability, aging, rate and games share.
    Only participation changes:
      - USE_CONTRACTS: participation reads the vendor contract export;
      - CONTRACT_STATE "observable": status counts only deals covering seasons
        from the export's earliest end year (2018), where a covering contract
        must be in the export IF the vendor snapshot is complete -- assumed,
        not verified. Before that, status is zero for everyone, so it cannot
        encode having survived into the snapshot;
      - PART_EXCLUDE ("contract_unknown",): the before/after-2018 period
        indicator is dropped. Scored alone it added nothing for skaters.

    Contract state is read at 1 July of each page when the harness scores it,
    and at the SIGNING when a contract is valued (`attach_forecasts`,
    `forecast_blocks`). The model is trained on the 1 July state, so priced
    contracts' first seasons still run about 5.5 points low.

    The previous leader, `A1HingeExposure`, stays importable as the
    no-contract sensitivity.
    """
    name = "leader, visible contract status in participation"
    USE_CONTRACTS = True
    CONTRACT_STATE = "observable"
    PART_EXCLUDE = ("contract_unknown",)


# ---------------------------------------------------------------------------
# THE STAR RESIDUAL, located (2026-09-24, run_star_residual.py). For players
# three wins and up, the adopted leader's rate is right at the valuation
# season (-0.03 per 82) and then falls about 0.27 a season along the aging
# walk -- 3.24 to 1.90 over five seasons -- where the stars who played fell
# from 3.26 to 2.82. Every tier shows the same too-steep walk. So the residual
# is in how the rate is carried forward, not in the starting shrinkage the
# hinge terms addressed. Three candidates, each ONE change from the adopted
# leader, scored alone before any combination:
# ---------------------------------------------------------------------------

class A1StatusSurvivorAging(A1HingeExposureStatus):
    """The adopted leader with the aging curve fitted on survivors only (no
    replacement-level imputation of the seasons departing players never
    played). The forecast rate is conditional on playing and departure is
    priced by the participation model, so the imputed curve may count an exit
    twice. One change: `AGING_SELECTION`."""
    name = "adopted leader, aging curve on survivors"
    AGING_SELECTION = "none"


class A1StatusNoLevelAging(A1HingeExposureStatus):
    """The adopted leader with the aging curve's level terms removed: age and
    position alone, so a star is not walked down faster for being a star. One
    change: `AGING_LEVEL_MODE`."""
    name = "adopted leader, aging curve without level terms"
    AGING_LEVEL_MODE = "none"


class A1StatusReducedForm(A1HingeExposureStatus):
    """The adopted leader with the rate at each horizon taken from that
    horizon's own regression on the anchor (the reduced form the aging walk
    replaced in Phase 3), instead of walking the valuation-season rate forward.
    Each horizon's regression is fitted on seasons actually played, so it
    estimates the rate given playing directly; participation is unchanged. One
    change: `_walk`."""
    name = "adopted leader, rate regressed per horizon"

    def _walk(self, r, rate0, a, h):
        if h == 0:
            return np.asarray(rate0, dtype=float)
        return _apply(self.coef_.get(h), a[self.FEATURES], a["tw_WAR"])


class A1HingeExposureStatusCarry(A1HingeExposureStatus):
    """SENSITIVITY, not adopted (2026-09-23): the adopted leader with contract
    status CARRIED PAST ITS SUPPORT.

    In the adopted leader, contract status enters participation only at
    horizons where training rows support it (from the 2019 page, up to four
    to six seasons ahead). Past that the fit is the no-contract one, so a
    player under contract for eight seasons reads about 0.93 to play in
    season seven and 0.45 in season eight: a cliff.

    THE RULE, borrowed from `predict_beyond_fit`: at a horizon h past the last
    supported one, L, use horizon L's fit with the player's features held at
    L and his contract status read for season t0 + h, times a decay per extra
    season. The decay is the league's observed participation ratio between
    horizons L and L-1 in this fit's own training rows (`base_`), clipped to
    [0.5, 1]. Where no horizon carries status (the 2017 and 2018 pages) the
    model is the adopted leader exactly.

    This is an assumption -- that being under contract matters past the
    horizon where it can be measured about as much as it does at the last
    one -- and it is scored before anything is adopted
    (`run_status_carry_sensitivity.py`).
    """
    name = "adopted leader, contract status carried past its support"

    def fit(self, table, before):
        super().fit(table, before)
        pm = self.part_
        L = pm.status_last_horizon()
        self.status_last_ = L
        g = 1.0
        if L is not None and (L - 1) in pm.base_ and pm.base_[L - 1] > 0:
            g = float(np.clip(pm.base_[L] / pm.base_[L - 1], 0.5, 1.0))
        self.status_decay_ = g
        return self

    def _part_predict(self, rows, h, as_of=None):
        L = getattr(self, "status_last_", None)
        if L is None or int(h) <= L:
            return super()._part_predict(rows, h, as_of=as_of)
        p = self.part_.predict_carried(rows, int(h), L, as_of=as_of)
        return (p * self.status_decay_ ** (int(h) - L)).clip(0.005, 0.995)
