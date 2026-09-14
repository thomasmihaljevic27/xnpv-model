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

SCRIPT_VERSION = "1.0"

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

    def fit(self, table: pd.DataFrame, before: int) -> None:
        self.before = before

    def predict(self, iset, subs, horizons) -> pd.DataFrame:
        raise NotImplementedError

    @staticmethod
    def _training_pairs(table: pd.DataFrame, before: int, horizons) -> pd.DataFrame:
        """Every (inputs at t, outcome at t+h) pair whose OUTCOME completed
        before `before`. One row per player-anchor-horizon."""
        s = table[table["GP"] >= C.MIN_GP]
        anchors = _anchors(s)
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
        pairs["y_played"] = act["GP"].reindex(ix).fillna(0).to_numpy() >= C.MIN_GP
        # A season that never happened is not a training row for the RATE, but
        # IS one for participation. Rate fits drop it; the participation
        # placeholder below uses the full frame.
        return pairs


def _anchors(played: pd.DataFrame) -> pd.DataFrame:
    """For every player and every season t0 he could have been valued at, the
    trailing facts from t0-1 and t0-2 only.

    Structurally incapable of seeing season t0: it reads t0-1 and t0-2 by
    construction, the same property the production engine's lookup has. The
    caller is responsible for restricting t0 itself.
    """
    cols = C.COMPONENTS_MODEL + ["WAR"]
    rate_cols = [c + "_82" for c in cols]
    keep = ["career_key", "pkey", "pos", "syr", "GP", "gp_share", "toi_pg",
            "exp_seasons", "exp_censored", "age", "has_age"] + cols + rate_cols
    s = played[keep]

    t1 = s.assign(t0=s["syr"] + 1)
    t2 = s.assign(t0=s["syr"] + 2)
    m = t1.merge(t2, on=["career_key", "t0"], how="outer", suffixes=("_1", "_2"))

    out = pd.DataFrame({"career_key": m["career_key"], "t0": m["t0"]})
    out["pkey"] = m["pkey_1"].fillna(m["pkey_2"])
    out["pos"] = m["pos_1"].fillna(m["pos_2"])
    out["n_seasons"] = m["GP_1"].notna().astype(int) + m["GP_2"].notna().astype(int)
    out["one_season"] = (out["n_seasons"] == 1).astype(float)
    out["is_D"] = (out["pos"] == "D").astype(float)
    for c in ["exp_seasons", "exp_censored", "has_age", "toi_pg"]:
        out[c] = m[c + "_1"].fillna(m[c + "_2"])
    # AGE AT THE VALUATION SEASON, not at the trailing season the anchor came
    # from. The anchor may be two years old; the player is not. `age` on a
    # season row is his age in that season, so stepping it forward to t0 is
    # what puts him on the right point of the curve.
    a1 = m["age_1"] + 1.0
    a2 = m["age_2"] + 2.0
    out["age"] = a1.fillna(a2)
    # Centred at 27, roughly the peak, so the linear term reads as "per year
    # either side of prime" and the square is small and well conditioned.
    out["age_c"] = out["age"] - 27.0
    out["age_c2"] = out["age_c"] ** 2

    # THE BLEND. 60/40 when both seasons qualify, the single season alone when
    # only one does -- the locked rule. Applied identically to the totals, the
    # per-82 rates and the games share, so A0 and A2 differ ONLY in what they
    # blend, never in how.
    def blend(col):
        a, b = m[col + "_1"], m[col + "_2"]
        both = a * W_T1 + b * W_T2
        return both.fillna(a).fillna(b)

    for c in cols:
        out["tw_" + c] = blend(c)              # trailing weighted TOTAL
        out["tr_" + c] = blend(c + "_82")      # trailing weighted RATE
    out["tr_gp_share"] = blend("gp_share")
    # Exposure: how many games the evidence rests on. A nine-game season is
    # weak evidence, not a missing one -- this is what lets A2 shrink by
    # evidence rather than by a games threshold.
    out["exposure_gp"] = m["GP_1"].fillna(0) * W_T1 + m["GP_2"].fillna(0) * W_T2
    return out.dropna(subset=["tw_WAR"]).reset_index(drop=True)


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
    name = "A0 production 60/40"

    def predict(self, iset, subs, horizons):
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP])
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
    name = "A1 calibrated total"
    FEATURES = ["tw_WAR", "one_season", "is_D", "exp_seasons", "age_c", "age_c2"]

    def fit(self, table, before):
        super().fit(table, before)
        pairs = self._training_pairs(table, before, range(6))
        self.coef_, self.gp_coef_ = {}, {}
        for h, g in pairs.groupby("h"):
            r = g.dropna(subset=["y_rate"])           # rate fit: seasons played
            self.coef_[h] = _ols(r[self.FEATURES], r["y_rate"]) if len(r) > 50 else None
            s = g.dropna(subset=["y_gp_share"])
            self.gp_coef_[h] = _ols(s[["tr_gp_share", "is_D", "exp_seasons", "age_c"]],
                                    s["y_gp_share"]) if len(s) > 50 else None

    def predict(self, iset, subs, horizons):
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP])
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
    name = "A2-raw components, no shrinkage"

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
    name = "A2 component-wise, shrunk"

    # Candidate reliability constants, in games. Spans "trust the player
    # almost fully after a few games" to "even two full seasons barely move
    # him off the norm", so the grid cannot bind at either end unnoticed --
    # the fit logs where each k_c lands and a k_c at a boundary is a flag.
    K_GRID = np.array([1, 2, 5, 10, 20, 40, 80, 160, 320, 640, 1280], dtype=float)

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

        pairs = self._training_pairs(table, before, range(6))
        pairs = self._shrink(pairs)
        self.coef_, self.gp_coef_ = {}, {}
        for h, g in pairs.groupby("h"):
            r = g.dropna(subset=["y_rate"])
            self.coef_[h] = _ols(r[self.RATE_FEATURES], r["y_rate"]) if len(r) > 50 else None
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
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP])
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


def _ols(X: pd.DataFrame, y: pd.Series):
    """Least squares with an intercept, on complete rows only. Returns None if
    the design is rank-deficient or too thin -- the caller then falls back to
    the raw trailing value, which is the honest answer when the window has not
    yet accumulated enough history to fit anything."""
    d = pd.concat([X, y.rename("_y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < 50:
        return None
    A = np.column_stack([np.ones(len(d)), d[X.columns].to_numpy(float)])
    try:
        beta, *_ = np.linalg.lstsq(A, d["_y"].to_numpy(float), rcond=None)
    except np.linalg.LinAlgError:
        return None
    return list(X.columns), beta


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
