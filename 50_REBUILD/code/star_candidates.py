"""star_candidates.py -- three single changes aimed at the star under-forecast.

EXPERIMENTAL (50_REBUILD). Nothing here changes a production file.

WHERE THE MISS IS (obvious_fixes.ObviousFixes, 3+ win tier, the rows the
current model answers, 88 players; run_obvious_fixes_test v1.0 forecasts)
    season WAR bias -0.19 in the valuation season, -0.54 five seasons out, in
    three parts:
      games share  predicted 0.84 against 0.89 among seasons played, from the
                   valuation season on: that is the whole valuation-season miss,
                   since the rate (3.23 against 3.26) and the chance of playing
                   (0.99 against 0.99) are right there;
      rate         walked down about 0.17 per 82 a season (3.23 to 2.40 in five),
                   where the stars who kept playing fell about 0.09 (3.26 to 2.82);
                   measured on seasons played, a selected group;
      chance       0.80 against 0.89 five seasons out; right through three.

THE CANDIDATES, each ONE change to ObviousFixes, scored alone and together
    GP_LEVEL     the games-share forecast also reads the player's level: the
                 trailing total and its second slope above one win (tw_WAR,
                 tw_hi1, the terms the fitted start already uses). The current
                 games-share line reads only his trailing share, position,
                 experience and age, so a star and a depth player with the same
                 recent share are forecast the same share.
    PART_HINGE   the chance-of-playing model gets a second level slope above
                 two wins (level_hi2 = max(level - 2, 0)), so the best players'
                 odds of staying in the league are not tied to the slope fitted
                 mostly on depth players.
    RAW_STEPS    the comparables' yearly changes are measured on raw seasons
                 AFTER the seasons they were matched on. The pool measures change
                 in a two-season smoothed level, so the first step the walk uses
                 (from the valuation age) is half of (season b+2 minus season
                 b), and season b is one the comparable was MATCHED on: a
                 comparable who looks like a star partly because of a lucky
                 season b carries half of that luck's reversal into the step.
                 The starting rate has already been pulled toward the league for
                 exactly that noise, so the walk takes it off twice. With raw
                 steps the change at age a is season a+1 minus season a, both
                 after the match. League-average changes are rebuilt the same
                 way, and departures (the survivorship fix) enter as 0 minus the
                 rate at a. This is a reading of the mechanism, and the test is
                 whether the change helps, not a proof of the reading.
    (v1.3, 2026-09-30, after the late star miss was split by age: good players
    aged 29+ played more often than forecast, and stars aged 24 or under
    improved far more than forecast, starting 0.47 per 82 too low)
    PART_LEVEL_AGE  participation with level x age, so age can cost a good
                 player less than a depth player
    START_LEVEL_AGE the fitted start with level x age (tw_WAR x age_c), so the
                 pull toward the league can differ for young and old stars
    HALF_H       (v1.1, added after v1.0's results were read) the comparables'
                 similarity window at half the yardstick. A star sits in the thin
                 top of the level scale, so at the full width much of his weight
                 goes to players well below him. Half the width was better
                 overall in the 2026-09-28 held-out test (0.2% to 0.6%) and was
                 not adopted there because it was one of many settings tried on
                 the same data; that caution applies here too.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import obvious_fixes as OF
from ability_forecast import A1HingeExposure, _anchors, _apply, _ols
from participation_model import ParticipationModel

SCRIPT_VERSION = "1.3"
GP_BASE = ["tr_gp_share", "is_D", "exp_seasons", "age_c"]
GP_WITH_LEVEL = GP_BASE + ["tw_WAR", "tw_hi1"]


class HingeParticipation(ParticipationModel):
    """The participation model with a second level slope above two wins."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.features = list(self.features) + ["level_hi2"]

    def _rows(self, anchors, h, as_of=None, table=None):
        d = super()._rows(anchors, h, as_of=as_of, table=table)
        d["level_hi2"] = np.clip(d["level"].to_numpy(float) - 2.0, 0, None)
        return d


class LevelAgeParticipation(ParticipationModel):
    """(v1.3) The participation model with level interacted with age (age in
    the target season, centred at 27, as `_rows` builds it), so age can cost a
    good player less than a depth player. One added column; everything else is
    the shared model."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.features = list(self.features) + ["level_x_age"]

    def _rows(self, anchors, h, as_of=None, table=None):
        d = super()._rows(anchors, h, as_of=as_of, table=table)
        d["level_x_age"] = d["level"].to_numpy(float) * d["age"].to_numpy(float)
        return d


def raw_step_curve(base_model):
    """A copy of a fitted AgingModel whose yearly changes are raw next-season
    changes, both seasons after any match, instead of changes in the smoothed
    level. Departures already imputed on `base_model` (obvious_fixes) enter as
    0 minus the raw rate; the survivors-only pool has none."""
    import copy
    m = copy.copy(base_model)
    imputed = getattr(base_model, "imputed_", {})
    ser = {}
    for name, p in m.players.items():
        D = np.full(m.nages, np.nan)
        for a, v in p["raw"].items():
            if (a + 1) in p["raw"]:
                D[a - m.AMIN] = p["raw"][a + 1] - v
            elif (name, a) in imputed:
                D[a - m.AMIN] = 0.0 - v
        ser[name] = D
    m.Dser = np.array([ser[n] for n in m.names])
    dn, dc = {}, {}
    for name, p in m.players.items():
        pos = p["pos"]
        for a, v in p["raw"].items():
            if (a + 1) in p["raw"]:
                d = p["raw"][a + 1] - v
            elif (name, a) in imputed:
                d = 0.0 - v
            else:
                continue
            dn[(pos, a)] = dn.get((pos, a), 0.0) + d
            dc[(pos, a)] = dc.get((pos, a), 0) + 1
    m.gdelta = {k: dn[k] / dc[k] for k in dn}
    return m


class StarCandidate(OF.ObviousFixes):
    """ObviousFixes with any of the three switches on. All off reproduces
    ObviousFixes exactly (checked by the runner)."""
    GP_LEVEL = False
    PART_HINGE = False
    RAW_STEPS = False
    HALF_H = False
    PART_LEVEL_AGE = False       # v1.3: participation with level x age
    START_LEVEL_AGE = False      # v1.3: the fitted start with level x age (set in FEATURES)
    _raw: dict = {}

    name = "obvious fixes (star candidate, all switches off)"

    def fit(self, table, before):
        super().fit(table, before)
        if self.RAW_STEPS:
            key = (self.IMPUTE, before)
            if key not in self._raw:
                self._raw[key] = raw_step_curve(self.curve_)
            self.curve_ = self._raw[key]
            self._cum = {}
        if self.HALF_H:
            import copy
            m = copy.copy(self.curve_)
            m.h = self.curve_.h / 2.0
            self.curve_ = m
            self._cum = {}
        self.gp_cols_ = GP_WITH_LEVEL if self.GP_LEVEL else GP_BASE
        if self.GP_LEVEL:
            pairs = self._training_pairs(table, before, C.CANDIDATE_HORIZONS)
            self.gp_coef_ = {}
            for h, g in pairs.groupby("h"):
                s = g.dropna(subset=["y_gp_share"] + GP_WITH_LEVEL)
                self.gp_coef_[h] = _ols(s[GP_WITH_LEVEL], s["y_gp_share"]) if len(s) > 50 else None
        if self.PART_LEVEL_AGE:
            assert not self.PART_HINGE, "one participation change at a time"
            n, d = self.N_SEASONS, self.decay_
            self.part_ = LevelAgeParticipation(
                None, exclude=tuple(self.PART_EXCLUDE),
                contract_state=self.CONTRACT_STATE).fit(
                table, before, anchors_fn=lambda p: _anchors(p, n, d),
                horizons=self.fitted_horizons_)
        if self.PART_HINGE:
            n, d = self.N_SEASONS, self.decay_
            self.part_ = HingeParticipation(
                None, exclude=tuple(self.PART_EXCLUDE),
                contract_state=self.CONTRACT_STATE).fit(
                table, before, anchors_fn=lambda p: _anchors(p, n, d),
                horizons=self.fitted_horizons_)
        return self

    def _training_pairs(self, table, before, horizons):
        pairs = super()._training_pairs(table, before, horizons)
        if "tw_x_age" in self.FEATURES:
            pairs["tw_x_age"] = pairs["tw_WAR"] * pairs["age_c"]
        return pairs

    def predict(self, iset, subs, horizons):
        """ability_forecast.A1AgingParticipation.predict, with the games-share
        columns read from `gp_cols_` instead of written in."""
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])
        if "tw_x_age" in self.FEATURES:
            a["tw_x_age"] = a["tw_WAR"] * a["age_c"]
        rate0 = _apply(self.coef_.get(0), a[self.FEATURES], a["tw_WAR"])
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = self._walk(r, rate0, a, h)
            gp = _apply(self.gp_coef_.get(h), a[self.gp_cols_], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = self._p_play(a, subs, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)


def candidate(gp=False, part=False, raw=False, half=False, part_age=False, start_age=False):
    tag = "".join(c for c, on in (("G", gp), ("P", part), ("R", raw), ("H", half),
                                  ("A", part_age), ("S", start_age)) if on) or "base"
    on = [w for w, f in (("games share reads level", gp), ("participation hinge", part),
                         ("raw comparables steps", raw), ("half-width comparables", half),
                         ("participation level x age", part_age),
                         ("start level x age", start_age)) if f]
    attrs = {"GP_LEVEL": gp, "PART_HINGE": part, "RAW_STEPS": raw, "HALF_H": half,
             "PART_LEVEL_AGE": part_age, "START_LEVEL_AGE": start_age,
             "name": "obvious fixes" + ("; " + ", ".join(on) if on else "")}
    if start_age:
        attrs["FEATURES"] = list(A1HingeExposure.FEATURES) + ["tw_x_age"]
    return type(f"Star_{tag}", (StarCandidate,), attrs)


class RebuiltGamesLevel(A1HingeExposure):
    """(v1.2) The rebuilt model with change G only, so the two models can be
    compared with the same games-share fix. Fit and predict as StarCandidate's
    G path; the rate walk is the rebuilt model's own."""
    name = "rebuilt model; games share reads level"
    GP_LEVEL, PART_HINGE, RAW_STEPS, HALF_H = True, False, False, False

    def fit(self, table, before):
        super().fit(table, before)
        self.gp_cols_ = GP_WITH_LEVEL
        pairs = self._training_pairs(table, before, C.CANDIDATE_HORIZONS)
        self.gp_coef_ = {}
        for h, g in pairs.groupby("h"):
            s = g.dropna(subset=["y_gp_share"] + GP_WITH_LEVEL)
            self.gp_coef_[h] = _ols(s[GP_WITH_LEVEL], s["y_gp_share"]) if len(s) > 50 else None
        return self

    predict = StarCandidate.predict
