"""run_goalie_participation.py -- will he play, and how much?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch, third
step. Development pages only. Nothing adopted.

TWO QUESTIONS, NOT ONE
    A goaltender's expected season is three numbers multiplied together: the
    chance he plays in the NHL at all, the share of the schedule he plays if
    he does, and how good he is per game. The bake-off settled the third --
    production's own projector, which nothing beat. The first two have been
    stood in for by a flat survival rate and his trailing share, carried
    forward unchanged, and the bake-off's diagnostic showed the first of those
    predicting 64.1% of goaltender-seasons played where 55.3% were.

    They are different forecasting problems and are built and scored apart:

      WHETHER HE PLAYS. The skater participation model, reused rather than
      copied: one rolling logistic fit per horizon on trailing level,
      trailing share of the schedule, experience, and contract state as it
      was known on the decision date -- and NOT age, for the reason below. A goaltender's trailing share is his
      ROLE, and a starter stays in the league where a third-stringer does not,
      so the same features mean something sharper here.

      HOW MUCH, IF HE PLAYS. A rolling linear fit per horizon of next season's
      share of the schedule on trailing share, trailing level and experience,
      fitted only on seasons he actually played. Against the flat carry it replaces,
      the question is whether a backup's share drifts up, a starter's drifts
      down, and a good goaltender keeps the net.

WHAT IS HELD FIXED
    The ability forecast. Every arm uses production's projector, so the
    comparison is about participation and role and nothing else. That
    projector forecasts a SEASON total at the goaltender's trailing role, not
    a rate, so it is divided by his trailing share to give the per-82 rate the
    harness multiplies back out. With the flat carry that division undoes
    itself exactly; with a modelled share, a forecast that he will play more
    raises his expected season in proportion. That is a statement about how
    production's number is being decomposed, and it is made here rather than
    left for somebody to find.

WHY NO AGE -- A SELECTION ON THE OUTCOME
    A goaltender's birthdate comes mostly from the contract export, so having
    one means he was still in the league in the contract era. On the 2019
    page, goalie anchors WITH a birthdate go on to play at 0.908, 0.902 and
    0.894 at zero, three and five seasons out; those WITHOUT one at 0.557,
    0.257 and 0.119. The first version of this model dropped the ageless rows,
    as the skater model does, and so learned only from survivors: it predicted
    about 0.87 at every horizon against an observed rate falling from 0.72 to
    0.37, and scored far worse than the flat rate it was meant to beat. It also
    carried a has-a-birthdate flag in the share model, which is the future
    written down as a column.

    Skaters have 98% birthdate coverage, so the same rule barely bites there.
    Goaltenders have about half, and the half they have is the survivors.
    Experience, counted from the panel itself, stands in for age.

WHAT THE SOURCE CANNOT SEE
    The goalie source floors at about 100 minutes in net -- the lightest
    season on record is two games and 100.5 minutes. A goaltender who dressed
    for one game, or relieved for a period, is ABSENT, and absent is scored as
    not having played. So the participation event here is "played a season
    the source records", which for a goaltender means roughly two games or
    more, not the one-game event the skater side scores. It is the same event
    in the fit and in the scoring, so the two halves agree with each other;
    it is a narrower event than the name suggests, and it is said so.
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
from ability_forecast import _anchors, W_T1, W_T2
from participation_model import ParticipationModel
from player_season_table import birthdate_source

SCRIPT_VERSION = "1.1"

HORIZONS = GB.HORIZONS
DECAY = W_T2 / W_T1            # the locked 60/40 recency weighting
# NO AGE, AND ABOVE ALL NO AGE FLAG. A goaltender's birthdate comes mostly
# from the contract export, so whether he HAS one says whether he was still in
# the league in the contract era -- the future, encoded as a column. The first
# version of this model carried `has_age` as a feature, which is a leak, and
# fitted participation only on goaltenders with an age, which is selection on
# the outcome. Experience, read from the panel itself, is the age proxy here:
# it needs nothing but the seasons already played.
SHARE_FEATURES = ["tr_gp_share", "tw_WAR", "exp_seasons"]
PART_EXCLUDE = ("age", "age_sq")
MIN_SHARE_ROWS = 150


def goalie_anchors(played: pd.DataFrame) -> pd.DataFrame:
    """The skater anchor builder, asked for goaltenders: WAR is the only
    production column a goaltender has."""
    return _anchors(played, 2, DECAY, cols=["WAR"])


class ShareModel:
    """E[share of the schedule | he plays], one rolling fit per horizon.

    Fitted on (anchor, outcome) pairs whose outcome season is strictly before
    the page, and ONLY on outcome seasons he actually played: this is the
    intensive margin, and a season he did not play belongs to the other half
    of the forecast.
    """

    def fit(self, seasons: pd.DataFrame, before: int) -> "ShareModel":
        assert seasons["syr"].max() < before, "share model handed the future"
        played = seasons[seasons["GP"] >= C.MIN_GP]
        a = goalie_anchors(played)
        act = (seasons[seasons["GP"] >= C.PARTICIPATION_GP]
               .drop_duplicates(["career_key", "syr"])
               .set_index(["career_key", "syr"])["gp_share"])
        self.coef_, self.n_ = {}, {}
        for h in HORIZONS:
            d = a[a["t0"] + h < before].copy()
            d["season"] = d["t0"] + h
            ix = pd.MultiIndex.from_arrays([d["career_key"], d["season"]])
            d["y"] = act.reindex(ix).to_numpy()
            d = d[d["y"].notna()]
            X = self._x(d)
            ok = np.isfinite(X).all(axis=1)
            self.n_[h] = int(ok.sum())
            if ok.sum() < MIN_SHARE_ROWS:
                self.coef_[h] = None
                continue
            self.coef_[h] = np.linalg.lstsq(X[ok], d["y"].to_numpy(float)[ok],
                                            rcond=None)[0]
        return self

    @staticmethod
    def _x(d: pd.DataFrame) -> np.ndarray:
        return np.column_stack([np.ones(len(d))]
                               + [d[f].to_numpy(float) for f in SHARE_FEATURES])

    def predict(self, a: pd.DataFrame, h: int) -> np.ndarray | None:
        coef = self.coef_.get(h)
        if coef is None:
            return None
        X = self._x(a)
        out = np.full(len(a), np.nan)
        ok = np.isfinite(X).all(axis=1)
        out[ok] = X[ok] @ coef
        return np.clip(out, 0.02, 1.0)


class Arm(GB.ProductionProjector):
    """Production's projector for ability, with participation and role each
    either the old stand-in or the new model. Four arms, and each pair that
    differs in one component isolates that component."""

    part_model = False
    share_model = False

    def _fit(self, seasons, before):
        super()._fit(seasons, before)
        if self.part_model:
            from contract_source import load_contracts
            contracts, _ = load_contracts()
            self.part_ = ParticipationModel(contracts, exclude=PART_EXCLUDE).fit(
                seasons, before, anchors_fn=goalie_anchors, horizons=HORIZONS)
        if self.share_model:
            self.share_ = ShareModel().fit(seasons, before)

    def _anchor_rows(self, iset, subs):
        a = goalie_anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP])
        a = a[a["t0"] == iset.t0]
        a = a.drop_duplicates("career_key").set_index("career_key")
        return a.reindex(subs["career_key"])

    def predict(self, iset, subs, horizons):
        war = self.war_for(subs)
        trail = self.share_for(subs)
        # PRODUCTION'S SEASON TOTAL, DECOMPOSED. Divided by the trailing share
        # it came from to give a rate; with the flat carry the harness's
        # multiplication undoes this exactly.
        rate = war.to_numpy() / trail.to_numpy()
        a = self._anchor_rows(iset, subs)
        rows = []
        for h in horizons:
            if self.part_model:
                p = self.part_.predict(a.reset_index(), int(h))
                p = p[~p.index.duplicated()].reindex(subs["career_key"])
                p = p.fillna(self.part_.base_.get(int(h), self.surv_[int(h)]))
                p = p.to_numpy(float)
            else:
                p = np.full(len(subs), self.surv_[int(h)])
            share = trail.to_numpy()
            if self.share_model:
                sm = self.share_.predict(a.reset_index(), int(h))
                if sm is not None:
                    share = np.where(np.isfinite(sm), sm, share)
            rows.append(pd.DataFrame({
                "career_key": subs["career_key"].to_numpy(), "h": int(h),
                "rate_82": rate, "gp_share": np.clip(share, 0.02, 1.0),
                "p_play": np.clip(p, 0.005, 0.995)}))
        return pd.concat(rows, ignore_index=True)


class Baseline(Arm):
    name = "flat survival, trailing share (the stand-ins)"


class PartOnly(Arm):
    name = "participation model, trailing share"
    part_model = True


class ShareOnly(Arm):
    name = "flat survival, share model"
    share_model = True


class Both(Arm):
    name = "participation model and share model"
    part_model = True
    share_model = True


ARMS = (Baseline, PartOnly, ShareOnly, Both)


def career_bootstrap(a: pd.DataFrame, b: pd.DataFrame, col: str,
                     n: int = 2000, seed: int = 20260922) -> tuple:
    """Second arm's mean absolute `col` minus the first's, and the share of
    goaltender-resamples in which the second is lower. Paired on the forecast:
    one (page, goaltender, horizon) is one forecast."""
    keys = ["career_key", "page", "h"]
    j = a[keys + [col]].merge(b[keys + [col]], on=keys, suffixes=("_a", "_b"),
                              validate="one_to_one").dropna()
    g = {k: v for k, v in j.groupby("career_key")}
    ks = list(g)
    rng = np.random.default_rng(seed)
    wins = 0
    for _ in range(n):
        s = pd.concat([g[k] for k in rng.choice(ks, len(ks), replace=True)])
        wins += int(s[f"{col}_b"].abs().mean() < s[f"{col}_a"].abs().mean())
    return (float(j[f"{col}_b"].abs().mean() - j[f"{col}_a"].abs().mean()),
            wins / n)


def main() -> None:
    C.banner("run_goalie_participation.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = GST.build(birthdate_csv=path, verbose=False, allow_thin_ages=True)
    C.log(f"  {len(table)} goalie-seasons; the lightest the source records is "
          f"{int(table['GP'].min())} games, so a one-game season is invisible")
    C.log("")

    har = H.Harness(table)
    scored = {}
    for cls in ARMS:
        m = cls()
        d = har.run(m, pages=C.DEV_PAGES, horizons=HORIZONS)
        scored[m.name] = d
        C.log(f"  ran {m.name}: {len(d)} cells")
    C.log("")
    base = scored[Baseline.name]

    # ---- 1. whether he plays -----------------------------------------------
    C.log("WHETHER HE PLAYS. Predicted against observed share of goaltender-")
    C.log("seasons played, and the Brier score (lower is better), by horizon.")
    C.log("")
    C.log(f"    {'arm':<46}{'predicted':>10}{'observed':>10}{'Brier':>8}")
    for name in (Baseline.name, PartOnly.name):
        d = scored[name]
        C.log(f"    {name:<46}{d['p_play'].mean():>10.3f}"
              f"{d['played'].mean():>10.3f}{d['brier'].mean():>8.4f}")
    C.log("")
    C.log(f"    {'h':<4}{'observed':>10}{'flat':>8}{'model':>8}"
          f"{'Brier flat':>12}{'Brier model':>13}")
    for h in HORIZONS:
        a = base[base["h"] == h]
        b = scored[PartOnly.name]
        b = b[b["h"] == h]
        C.log(f"    {h:<4}{a['played'].mean():>10.3f}{a['p_play'].mean():>8.3f}"
              f"{b['p_play'].mean():>8.3f}{a['brier'].mean():>12.4f}"
              f"{b['brier'].mean():>13.4f}")
    C.log("")
    gap, share = career_bootstrap(base, scored[PartOnly.name], "brier")
    C.log(f"  the participation model changes the Brier score by {gap:+.4f},")
    C.log(f"  lower in {share:.0%} of goaltender-resamples")
    C.log("")

    # ---- 2. how much, if he plays -------------------------------------------
    C.log("HOW MUCH, IF HE PLAYS. Share of the schedule, scored ONLY on seasons")
    C.log("he played -- the other seasons belong to the first question.")
    C.log("")
    frames = {}
    for name in (Baseline.name, ShareOnly.name):
        d = scored[name]
        d = d[d["played"]].copy()
        d["e_share"] = d["gp_share"] - d["act_gp_share"]
        frames[name] = d
        C.log(f"    {name:<46}{len(d):>7} seasons   mean abs "
              f"{d['e_share'].abs().mean():.4f}   bias {d['e_share'].mean():+.4f}")
    gap, share = career_bootstrap(frames[Baseline.name], frames[ShareOnly.name],
                                  "e_share")
    C.log(f"  the share model changes mean absolute error by {gap:+.4f}, lower")
    C.log(f"  in {share:.0%} of goaltender-resamples")
    C.log("")

    # ---- 3. the season, all three together ----------------------------------
    C.log("THE SEASON. Mean absolute error and mean error in season WAR, ability")
    C.log("held at production's projector in every arm.")
    C.log("")
    C.log(f"    {'arm':<46}{'MAE':>8}{'bias':>9}{'beats stand-ins':>17}")
    for name, d in scored.items():
        if d is base:
            C.log(f"    {name:<46}{d['e_war'].abs().mean():>8.3f}"
                  f"{d['e_war'].mean():>+9.3f}{'--':>17}")
            continue
        gap, share = career_bootstrap(base, d, "e_war")
        C.log(f"    {name:<46}{d['e_war'].abs().mean():>8.3f}"
              f"{d['e_war'].mean():>+9.3f}{share:>16.0%}")
    C.log("")

    out = pd.concat([d.assign(arm=n) for n, d in scored.items()],
                    ignore_index=True)
    out.to_csv(C.out_path("goalie_participation.csv"), index=False)
    C.log(f"  wrote {C.out_path('goalie_participation.csv').name} ({len(out)} rows)")
    C.write_log("goalie_participation_run_log.txt")


if __name__ == "__main__":
    main()
