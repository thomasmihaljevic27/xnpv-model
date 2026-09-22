"""run_goalie_rate.py -- how good is he per game, forecast as a rate?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch, fourth
step. Development pages only. Nothing adopted.

WHY A RATE, AND WHY NOW
    A goaltender's expected season is three numbers multiplied together: the
    chance he plays at all, the share of the schedule he plays if he does, and
    how good he is per game. The last step built the first two as models.
    The third is still production's projector, and production's projector
    does not forecast a rate. It forecasts a SEASON TOTAL shrunk toward a
    league average of 2.19 WAR, which is what a starter produces. To fit the
    three-way product the harness needs, that total is divided by the
    goaltender's trailing share -- and for a backup, whose total has been
    pulled toward a starter's, the division inflates his implied rate. Carried
    with his trailing share the inflation multiplies straight back out; fed a
    better share forecast, it does not, and the share model made the season
    forecast worse (backup bias +0.13 -> +0.54) while forecasting share
    better. A rate forecast is what lets the share model be used at all.

WHAT IS FORECAST
    WAR per 82 games in a season he plays, for each horizon h:

        rate = w * trailing rate + (1 - w) * norm(role)
        w    = G / (G + k)

    THE TRAILING RATE pools his last three seasons, each weighted by its games
    and by recency (the locked 60/40 decay, carried to a third season). A rate
    is a per-game quantity, so a 12-game cameo is 12 games of evidence and not
    a season's worth; production's cascade and the anchors elsewhere in the
    rebuild average seasons, which is right for totals and wrong for rates.
    Every season the source records counts, down to its two-game floor --
    production's own lookup also has no games filter, and weighting by games
    is what makes that safe.

    THE EVIDENCE G is the same recency-weighted games, so the pull toward the
    norm weakens as the games behind the number grow. k is the number of games
    at which his own record and the norm carry equal weight. It is fitted per
    horizon on a grid, because a rate four seasons out should lean on the
    norm more than one a season out, and a fixed k cannot learn that.

    THE NORM is what a goaltender in his role produces per game, a + b * share,
    with share his recency-weighted trailing share of the schedule. This is
    the part a season-total model cannot express. Coaches give starts to the
    goaltender they think is better, so role carries information about
    ability, and a backup shrunk toward the league's average goaltender is
    shrunk toward a starter. The flat-norm version (b = 0) is run alongside
    as the comparison that says whether role earns its place.

HOW IT IS FITTED, AND WHAT IT CANNOT SEE
    Per horizon, on (goaltender, t0) pairs whose OUTCOME season t0 + h is
    strictly before the page -- the rebuild's outcome-window rule, asserted.
    The subject rule is the harness's: a qualifying season (MIN_GP games) in
    the three seasons before t0. The outcome is the per-82 rate of a season he
    played, weighted by that season's games, because a rate from two games
    estimates the same thing as one from sixty with thirty times the noise.
    Given k the model is linear in a and b (y - w r = (1 - w) a + (1 - w) b s),
    so each k on the grid is an ordinary weighted least squares, and the k
    with the lowest weighted squared error is kept.

    It is fitted on seasons the goaltender PLAYED, so it answers "how good,
    given that he plays", which is exactly the factor the product needs --
    whether he plays is the participation model's question. The norm at long
    horizons is therefore a norm among survivors, and that is correct here
    rather than a bias: an unplayed season is priced at zero by the other
    factor, not by this one.

    WHAT THE WEIGHTED FIT ESTIMATES. Weighting squared error by the games of
    the outcome season targets an EXPOSURE-WEIGHTED rate -- WAR per 82 per game
    played -- and not the plain average rate of a randomly chosen played
    season. The two differ whenever games and performance move together, which
    for goaltenders they do: the one playing well gets the starts. And the
    product of a separately fitted rate and a separately fitted share is the
    expected season only if rate and share are uncorrelated given the anchor;
    in general E[rate x share] = E[rate] E[share] + their covariance. That is
    a stated assumption of this decomposition, not an identity, and a joint
    rate-and-workload path has to define its target explicitly.

    NO AGE, for the reason recorded in run_goalie_participation.py: a
    goaltender's birthdate is available mostly because he survived into the
    contract era, so age would carry the outcome in with it.

WHAT IS SCORED
    First the rate alone, against production's implied rate (its season total
    over the trailing share), on played seasons, games-weighted and not. Then
    the season, with the participation model in every arm, so the only things
    that differ are the rate and whether the share is trailing or modelled.
    The share model's arm is the test the previous step could not pass: rate
    times share times participation as a real decomposition.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import goalie_season_table as GST
import run_goalie_bakeoff as GB
import run_goalie_participation as GP
from ability_forecast import W_T1, W_T2
from player_season_table import birthdate_source

SCRIPT_VERSION = "1.1"

HORIZONS = GP.HORIZONS
LAGS = (1, 2, 3)
DECAY = W_T2 / W_T1              # 0.667: the locked 60/40, carried to a third season
# The last entry is effectively infinite: his own record gets no weight and the
# forecast IS the norm. Offered so the fit can say so rather than stop at the
# grid's edge.
K_GRID = (5, 10, 20, 40, 60, 90, 120, 160, 220, 300, 400, 600, 900, 1500, 3000, 1e9)
MIN_RATE_ROWS = 150              # outcome seasons a horizon needs before it is fitted
SUBJECT_WINDOW = H.ACTIVE_WINDOW  # the harness's subject rule, reused


def trailing_rates(seasons: pd.DataFrame, t0s) -> pd.DataFrame:
    """For every goaltender who is a SUBJECT at each t0 in `t0s`, the pooled
    trailing rate, the games behind it and his trailing share of the schedule.

    Reads seasons t0-1, t0-2, t0-3 only -- every lag is positive, so season t0
    and later cannot enter. A subject has a qualifying season (MIN_GP games)
    in that window, which is the harness's own eligibility rule, so the
    training pairs are drawn from the same population the forecast is asked
    about.
    """
    s = seasons.drop_duplicates(["career_key", "syr"])
    out = []
    for t0 in t0s:
        w = s[s["syr"].between(t0 - SUBJECT_WINDOW, t0 - 1)].copy()
        subj = w.loc[w["GP"] >= C.MIN_GP, "career_key"].unique()
        w = w[w["career_key"].isin(subj)]
        if w.empty:
            continue
        # Recency weight: 1 for last season, DECAY for the one before, DECAY^2
        # for the one before that. A season he did not play is simply absent.
        w["rw"] = DECAY ** (t0 - 1 - w["syr"])
        # A RATE IS POOLED BY GAMES. The raw total behind each per-82 rate is
        # WAR_82 * GP / 82, so weighting the rates by recency x games and
        # dividing by the weighted games gives recency-weighted WAR per 82.
        w["wg"] = w["rw"] * w["GP"]
        w["wr"] = w["wg"] * w["WAR_82"]
        w["ws"] = w["rw"] * w["gp_share"]
        g = w.groupby("career_key").agg(wg=("wg", "sum"), wr=("wr", "sum"),
                                        ws=("ws", "sum"), rw=("rw", "sum"))
        g["t0"] = int(t0)
        g["r_trail"] = g["wr"] / g["wg"]
        g["games"] = g["wg"]                   # evidence, in recency-weighted games
        g["s_trail"] = g["ws"] / g["rw"]       # role, renormalised over seasons played
        out.append(g[["t0", "r_trail", "games", "s_trail"]].reset_index())
    if not out:
        return pd.DataFrame(columns=["career_key", "t0", "r_trail", "games", "s_trail"])
    return pd.concat(out, ignore_index=True)


class RateModel:
    """E[WAR per 82 | he plays, h seasons out], shrunk toward a role norm.

    `role_norm=False` fits the flat norm (b = 0), the comparison that says
    whether role earns its place in the shrinkage target.
    """

    def __init__(self, role_norm: bool = True):
        self.role_norm = role_norm

    def fit(self, seasons: pd.DataFrame, before: int) -> "RateModel":
        assert seasons["syr"].max() < before, "rate model handed the future"
        s = seasons.drop_duplicates(["career_key", "syr"])
        played = s[s["GP"] >= C.PARTICIPATION_GP].set_index(["career_key", "syr"])
        first = int(s["syr"].min()) + 1
        self.k_, self.coef_, self.n_, self.from_h_ = {}, {}, {}, {}
        for h in HORIZONS:
            # THE OUTCOME-WINDOW RULE: t0 + h < before, so the outcome season
            # of every pair is one the page could already see.
            t0s = range(first, before - h)
            a = trailing_rates(s, t0s)
            ix = pd.MultiIndex.from_arrays([a["career_key"], a["t0"] + h])
            a["y"] = played["WAR_82"].reindex(ix).to_numpy()
            a["gp"] = played["GP"].reindex(ix).to_numpy()
            a = a[a["y"].notna()]
            assert (a["t0"] + h < before).all()
            self.n_[h] = len(a)
            if len(a) < MIN_RATE_ROWS:
                continue
            self.k_[h], self.coef_[h] = self._fit_one(a)
            self.from_h_[h] = h
        # A horizon with too few outcomes borrows the nearest shorter horizon's
        # fit, which leans on the norm LESS than a longer one would. Reported,
        # not hidden: `from_h_` says which fit every horizon uses.
        fitted = sorted(self.coef_)
        assert fitted, f"no horizon has {MIN_RATE_ROWS} outcomes before {before}"
        for h in HORIZONS:
            if h not in self.coef_:
                src = max([f for f in fitted if f < h], default=fitted[0])
                self.k_[h], self.coef_[h], self.from_h_[h] = (
                    self.k_[src], self.coef_[src], src)
        return self

    def _design(self, a: pd.DataFrame, k: float):
        w = a["games"].to_numpy(float) / (a["games"].to_numpy(float) + k)
        one = 1.0 - w
        X = (np.column_stack([one, one * a["s_trail"].to_numpy(float)])
             if self.role_norm else one[:, None])
        return w, X

    def _fit_one(self, a: pd.DataFrame):
        y = a["y"].to_numpy(float)
        r = a["r_trail"].to_numpy(float)
        rw = np.sqrt(a["gp"].to_numpy(float))       # games-weighted least squares
        best = (np.inf, None, None)
        for k in K_GRID:
            w, X = self._design(a, k)
            z = y - w * r
            beta = np.linalg.lstsq(X * rw[:, None], z * rw, rcond=None)[0]
            sse = float((((z - X @ beta) * rw) ** 2).sum())
            if sse < best[0]:
                best = (sse, float(k), beta)
        return best[1], best[2]

    def norm(self, share, h: int) -> np.ndarray:
        beta = self.coef_[h]
        share = np.asarray(share, dtype=float)
        return beta[0] + (beta[1] * share if self.role_norm else 0.0)

    def predict(self, a: pd.DataFrame, h: int) -> np.ndarray:
        w, X = self._design(a, self.k_[h])
        return w * a["r_trail"].to_numpy(float) + X @ self.coef_[h]


class ConditionalSeason:
    """E[season | he plays] = rate x share at one page: THE ONE IMPLEMENTATION.

    The scored arms below and the price runner's goalie forecast both call
    this, so the forecast that is tested and the forecast that is priced are
    the same numbers. An earlier version gave the price runner its own share
    fallback -- all recorded seasons, recency-decayed -- while the scored arm
    fell back to `GB.trailing_share`, and 435 page-goaltender-horizon cells
    differed by up to 1.6 WAR. Everything that decides the number lives here:

      * the rate (`RateModel.predict` on `trailing_rates` at the page);
      * the share, by `GP.role_share` over `GB.trailing_share`, so a horizon
        the share model cannot fit falls back one way only;
      * the horizon clamp: a horizon past the fitted range takes the last
        fitted one, as every goalie forecast here does.

    Built from seasons strictly before the page, asserted.
    """

    def __init__(self, seasons: pd.DataFrame, t0: int, rate_model: RateModel,
                 share_model=None):
        assert seasons["syr"].max() < t0, "conditional season handed the page"
        self.t0, self.rm, self.sm = int(t0), rate_model, share_model
        self.tr_ = trailing_rates(seasons, [t0]).set_index("career_key")
        self.qual_ = seasons[seasons["GP"] >= C.MIN_GP]
        a = GP.goalie_anchors(self.qual_)
        self.anchors_ = (a[a["t0"] == t0].drop_duplicates("career_key")
                         .set_index("career_key"))

    @staticmethod
    def clamp(h: int) -> int:
        return min(int(h), max(HORIZONS))

    def rate(self, keys, h: int) -> np.ndarray:
        """WAR per 82 if he plays; NaN for a goaltender with no trailing rate."""
        rows = self.tr_.reindex(list(keys)).reset_index()
        out = np.full(len(rows), np.nan)
        ok = rows["r_trail"].notna().to_numpy()
        if ok.any():
            out[ok] = self.rm.predict(rows[ok], self.clamp(h))
        return out

    def share(self, keys, h: int) -> np.ndarray:
        trail = GB.trailing_share(self.qual_, self.t0, list(keys))
        anchors = self.anchors_.reindex(list(keys)).reset_index()
        return GP.role_share(self.sm, anchors, trail.to_numpy(), self.clamp(h))

    def season(self, keys, h: int) -> np.ndarray:
        return self.rate(keys, h) * self.share(keys, h)


class RateArm(GP.Arm):
    """The participation runner's arm, with production's season total replaced
    by the rate forecast. Participation and share come from the parent, so
    these arms differ from the participation runner's only in the rate."""

    part_model = True
    rate_model = None           # None: production's implied rate (the parent's)

    def _fit(self, seasons, before):
        super()._fit(seasons, before)
        if self.rate_model is not None:
            self.rate_ = RateModel(role_norm=(self.rate_model == "role")).fit(
                seasons, before)

    def predict(self, iset, subs, horizons):
        out = super().predict(iset, subs, horizons)
        if self.rate_model is None:
            return out
        assert subs["career_key"].is_unique
        cs = ConditionalSeason(iset.seasons[iset.seasons["syr"] < iset.t0],
                               iset.t0, self.rate_,
                               self.share_ if self.share_model else None)
        keys = subs["career_key"].to_numpy()
        for h in horizons:
            rate = cs.rate(keys, int(h))
            # Every harness subject has a qualifying season in the window, so
            # every one has a trailing rate. A missing rate is a broken join.
            assert np.isfinite(rate).all(), "a subject has no trailing rate"
            m = (out["h"] == int(h)).to_numpy()
            assert (out.loc[m, "career_key"].to_numpy() == keys).all()
            # The parent computed the share by the same rule; asserted, so the
            # two can never drift apart again inside one arm.
            assert np.allclose(out.loc[m, "gp_share"].to_numpy(float),
                               cs.share(keys, int(h))), "share rules diverged"
            out.loc[m, "rate_82"] = rate
        return out


class ProdTrail(RateArm):
    name = "production's total, trailing share"


class ProdShare(RateArm):
    name = "production's total, share model"
    share_model = True


class FlatTrail(RateArm):
    name = "rate, flat norm, trailing share"
    rate_model = "flat"


class RoleTrail(RateArm):
    name = "rate, role norm, trailing share"
    rate_model = "role"


class FlatShare(RateArm):
    name = "rate, flat norm, share model"
    rate_model = "flat"
    share_model = True


class RoleShare(RateArm):
    name = "rate, role norm, share model"
    rate_model = "role"
    share_model = True


ARMS = (ProdTrail, ProdShare, FlatTrail, RoleTrail, FlatShare, RoleShare)


def _k(k: float) -> str:
    return "all" if k >= 1e8 else f"{k:.0f}"


def games_weighted_mae(d: pd.DataFrame) -> float:
    p = d[d["played"]]
    return float(np.average(p["e_rate"].abs(), weights=p["act_gp"]))


def main() -> None:
    C.banner("run_goalie_rate.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how} (not used by any model here)")
    table = GST.build(birthdate_csv=path, verbose=False, allow_thin_ages=True)
    har = H.Harness(table)

    scored = {}
    for cls in ARMS:
        m = cls()
        scored[m.name] = har.run(m, pages=C.DEV_PAGES, horizons=HORIZONS)
        C.log(f"  ran {m.name}: {len(scored[m.name])} cells")
    C.log("")
    base = scored[ProdTrail.name]

    # ---- 0. what the fits came out at ---------------------------------------
    C.log("WHAT THE RATE FIT CHOSE on each development page. k is the games at")
    C.log("which a goaltender's own record and the norm weigh equally; the norm")
    C.log("is a + b x trailing share, in WAR per 82.")
    C.log("")
    C.log(f"    {'page':<6}{'h':>3}{'pairs':>7}{'k':>7}{'a':>9}{'b':>9}"
          f"{'norm, backup 0.25':>19}{'norm, starter 0.65':>20}{'k flat':>8}")
    for page in C.DEV_PAGES:
        past = table[table["syr"] < page]
        rm = RateModel(True).fit(past, page)
        fm = RateModel(False).fit(past, page)
        for h in HORIZONS:
            a, b = rm.coef_[h]
            tag = "" if rm.from_h_[h] == h else f"  (uses h{rm.from_h_[h]})"
            C.log(f"    {page:<6}{h:>3}{rm.n_[h]:>7}{_k(rm.k_[h]):>7}{a:>+9.3f}"
                  f"{b:>+9.3f}{rm.norm(0.25, h):>+19.3f}{rm.norm(0.65, h):>+20.3f}"
                  f"{_k(fm.k_[h]):>8}{tag}")
    C.log("  k = 'all' means the fit gave his own record no weight at all.")
    C.log("")

    # ---- 1. the rate alone --------------------------------------------------
    C.log("THE RATE ALONE. WAR per 82 against the season he actually played,")
    C.log("on played seasons. Production's rate is its season total over his")
    C.log("trailing share. Games-weighted counts a 60-game season as 60 games")
    C.log("of evidence about the rate and a 3-game one as 3.")
    C.log("")
    C.log(f"    {'rule':<40}{'MAE':>8}{'games-wtd MAE':>15}{'games-wtd bias':>16}")
    for name in (ProdTrail.name, FlatTrail.name, RoleTrail.name):
        d = scored[name]
        p = d[d["played"]]
        C.log(f"    {name:<40}{p['e_rate'].abs().mean():>8.3f}"
              f"{games_weighted_mae(d):>15.3f}"
              f"{np.average(p['e_rate'], weights=p['act_gp']):>+16.3f}")
    for name in (FlatTrail.name, RoleTrail.name):
        gap, share = GP.career_bootstrap(base[base["played"]],
                                         scored[name][scored[name]["played"]],
                                         "e_rate")
        C.log(f"  {name}: unweighted MAE {gap:+.3f} against production's,")
        C.log(f"  lower in {share:.0%} of goaltender-resamples")
    C.log("")

    # ---- 2. the season -------------------------------------------------------
    C.log("THE SEASON. Season WAR, participation model in every arm; the arms")
    C.log("differ only in the rate and in trailing versus modelled share.")
    C.log("")
    C.log("TWO SCORES, because they ask different questions. Mean absolute error")
    C.log("rewards the MEDIAN outcome; squared error rewards the MEAN. Almost half")
    C.log("these cells are seasons he did not play, scored as zero, so the two")
    C.log("can disagree -- and a forecast that feeds a sum of expected dollars is")
    C.log("a forecast of the mean.")
    C.log("")
    for d in scored.values():
        d["se_war"] = d["e_war"] ** 2
    C.log(f"    {'arm':<40}{'MAE':>8}{'beats row 1':>13}{'RMSE':>8}"
          f"{'beats row 1':>13}{'bias':>9}")
    for name, d in scored.items():
        mae, rmse = d["e_war"].abs().mean(), np.sqrt(d["se_war"].mean())
        if d is base:
            C.log(f"    {name:<40}{mae:>8.3f}{'--':>13}{rmse:>8.3f}{'--':>13}"
                  f"{d['e_war'].mean():>+9.3f}")
            continue
        _, s_abs = GP.career_bootstrap(base, d, "e_war")
        _, s_sq = GP.career_bootstrap(base, d, "se_war")
        C.log(f"    {name:<40}{mae:>8.3f}{s_abs:>12.0%} {rmse:>8.3f}{s_sq:>12.0%} "
              f"{d['e_war'].mean():>+9.3f}")
    C.log("  'beats row 1' is the share of goaltender-resamples in which the arm's")
    C.log("  error is lower than the first row's.")
    C.log("")
    for a_name, b_name in ((RoleTrail.name, RoleShare.name),
                           (FlatTrail.name, FlatShare.name),
                           (ProdTrail.name, ProdShare.name)):
        g_abs, s_abs = GP.career_bootstrap(scored[a_name], scored[b_name], "e_war")
        g_sq, s_sq = GP.career_bootstrap(scored[a_name], scored[b_name], "se_war")
        C.log(f"  adding the share model to '{a_name}':")
        C.log(f"    MAE {g_abs:+.3f} (lower in {s_abs:.0%}),  mean squared error "
              f"{g_sq:+.3f} (lower in {s_sq:.0%})")
    C.log("")

    C.log(f"    {'h':<4}" + "".join(f"{n.split(',')[0][:9] + n.split(',')[-1][:10]:>20}"
                                  for n in scored))
    for h in HORIZONS:
        C.log(f"    {h:<4}" + "".join(
            f"{d.loc[d['h'] == h, 'e_war'].abs().mean():>20.3f}" for d in scored.values()))
    C.log("")

    # ---- 3. the backup test -------------------------------------------------
    C.log("THE TEST THE LAST STEP FAILED. Bias in season WAR by trailing role.")
    C.log("With production's total, the share model raised backup bias from")
    C.log("+0.13 to +0.54; a rate forecast should not.")
    C.log("")
    cols = list(scored)
    C.log(f"    {'role':<13}{'cells':>7}" + "".join(f"{i + 1:>8}" for i in range(len(cols))))
    for i, n in enumerate(cols):
        C.log(f"      {i + 1} = {n}")
    # One cut for every arm: the trailing share the trailing-share arm carried.
    cut = base.set_index(["career_key", "page", "h"])["gp_share"]
    ter = pd.qcut(cut, 3, labels=["backup-ish", "middle", "starter-ish"])
    for role in ["backup-ish", "middle", "starter-ish"]:
        keys = ter[ter == role].index
        row = f"    {role:<13}{len(keys):>7}"
        for d in scored.values():
            e = d.set_index(["career_key", "page", "h"])["e_war"].reindex(keys)
            row += f"{e.mean():>+8.3f}"
        C.log(row)
    row = f"    {'mean |bias|':<13}{'':>7}"
    for d in scored.values():
        e = d.set_index(["career_key", "page", "h"])["e_war"]
        row += f"{np.mean([abs(e.reindex(ter[ter == r].index).mean()) for r in ['backup-ish', 'middle', 'starter-ish']]):>8.3f}"
    C.log(row)
    C.log("")

    out = pd.concat([d.assign(arm=n) for n, d in scored.items()], ignore_index=True)
    out.to_csv(C.out_path("goalie_rate.csv"), index=False)
    C.log(f"  wrote {C.out_path('goalie_rate.csv').name} ({len(out)} rows)")
    C.write_log("goalie_rate_run_log.txt")


if __name__ == "__main__":
    main()
