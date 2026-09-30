"""obvious_fixes.py -- the current model with every listed fix, and nothing else.

EXPERIMENTAL (50_REBUILD). Nothing here changes a production file.

THE QUESTION (Thomas, 2026-09-30)
    Suppose the current model took every fix that has an obvious case, and
    kept everything else, most visibly its comparable-player aging method. How
    far would it close the gap to the rebuilt model?

WHAT "EVERY LISTED FIX" MEANS HERE, piece by piece
    starting level  a three-season weighted rate per 82 games, pulled toward
                    the league average by the rebuilt model's fitted rule
                    (added at Thomas's request: "include the starting rate
                    fix as well"). The plain 50/30/20 rate with no pull is
                    kept as a lower rung (`PlainStart`) so the pull's share can
                    be read off.
    games share     the rebuilt model's own games-share forecast.
    chance he plays the rebuilt model's participation model, without contract
                    data (reading contract status was not on the list).
    aging           the CURRENT model's comparable-player curve (aging_curve.
                    AgingModel), fitted per valuation page on earlier seasons
                    and on the corrected age table (the look-ahead and age-table
                    fixes), with its yearly changes ADDED to the rate rather
                    than multiplied (the additive fix), and with players who
                    left the league put back at replacement level (the
                    survivorship fix, `ImputedAgingModel` below).
    valuation date  every fit rolls forward on the harness; in dollars the
                    rebuild's signing-dated machinery values the forecast.
    RFA rights      not part of a season forecast or of the dollar score of the
                    term; see the dollar runner.

    NOT CHANGED: the comparable-player method itself (pool rule, eight measures,
    group weights, yardstick, bell-shaped weights, league weight of ten, 55/45
    pull used only inside the curve, production's basing of the path one or two
    ages back). Its settings are exactly production's.

THE SURVIVORSHIP FIX FOR COMPARABLES, the one piece built new here
    The rebuilt equation's fix (aging_additive, selection "impute") enters every
    player who played season t and did not play t+1 at replacement level, zero,
    for the season he missed, but only where season t+1 had finished before the
    page. The comparable pool's analogue, in its own terms:
      * the pool keeps seasons of 20+ games and measures change in a
        two-season smoothed level (WIN = 2);
      * a pool season at age a whose player has NO row at all at age a+1 in the
        age table (he did not appear in the NHL), with that season finished
        before the page, gets an imputed next season of 0 per 82, smoothed
        the pool's own way: next level = (rate at a + 0) / 2, so the change is
        that minus the smoothed level at a;
      * a player who did play at a+1 but under 20 games is NOT a departure; his
        change stays missing, exactly as in production's pool;
      * the league-average changes the comparables are blended with are
        recomputed with the imputed changes included.
    It is a construction choice with an assumption doing real work (zero is
    replacement), stated rather than hidden, as in the rebuilt equation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import production_adapter as PA
from ability_forecast import A1HingeExposure, _anchors, _apply

SCRIPT_VERSION = "1.0"
HMAX = C.MAX_HORIZON             # dollars ask past five seasons; the harness stops at five
START_WEIGHTS = {1: 0.5, 2: 0.3, 3: 0.2}   # the 50/30/20 three-season weighting


def _aging_module():
    PA._production()             # puts 20_CODE on sys.path and checks the age table exists
    import aging_curve as AC
    return AC, sys.modules["skater_forward_projection"]


def imputed_aging_model(path: str, before: int):
    """Production's AgingModel with departures entered at replacement level."""
    AC, _ = _aging_module()

    class ImputedAgingModel(AC.AgingModel):
        def __init__(self, war_age_path, before):
            super().__init__(war_age_path, before=before)
            # Every (career, age) with ANY NHL row, and the season year of each
            # qualifying age, from the same file, cleaning and page filter.
            df = pd.read_csv(war_age_path)
            df["syr"] = df["Season"].str.split("-").str[0].astype(int) + 2000
            df = df[df["syr"] < int(before)].copy()
            df["career"] = df["Player"].map(AC.career_key)
            df = df[df["age"].notna()]
            present = set(zip(df["career"], df["age"].astype(int)))
            syr_of = (df.groupby(["career", df["age"].astype(int)])["syr"].max().to_dict())
            self.n_imputed = 0
            imputed = {}
            for name, p in self.players.items():
                for s in p["seasons"]:
                    a = s["age"]
                    if (a + 1) in p["sm"] or (name, a + 1) in present:
                        continue                      # he played at a+1 (any games)
                    sy = syr_of.get((name, a))
                    if sy is None or sy + 1 >= int(before):
                        continue                      # the next season is not over yet
                    nxt = (s["w82"] + 0.0) / 2.0 if AC.WIN > 1 else 0.0
                    imputed[(name, a)] = nxt - p["sm"][a]
            self.imputed_ = imputed
            self.n_imputed = len(imputed)
            # Rebuild the per-row delta series with the imputed changes added.
            by_name = {}
            for (nm, a), d in imputed.items():
                by_name.setdefault(nm, []).append((a, d))
            D = self.Dser.copy()
            for r, name in enumerate(self.names):
                for a, d in by_name.get(name, ()):
                    assert np.isnan(D[r, a - self.AMIN]), "an imputed change overwrote an observed one"
                    D[r, a - self.AMIN] = d
            self.Dser = D
            # League-average changes, survivors plus the imputed departures.
            dn, dc = {}, {}
            for name, p in self.players.items():
                pos, ss, ser = p["pos"], p["seasons"], p["sm"]
                for i, s in enumerate(ss):
                    a = s["age"]
                    if i + 1 < len(ss) and ss[i + 1]["age"] - a == 1:
                        d = ser[ss[i + 1]["age"]] - ser[a]
                    elif (name, a) in imputed:
                        d = imputed[(name, a)]
                    else:
                        continue
                    dn[(pos, a)] = dn.get((pos, a), 0.0) + d
                    dc[(pos, a)] = dc.get((pos, a), 0) + 1
            self.gdelta = {k: dn[k] / dc[k] for k in dn}

    return ImputedAgingModel(path, before)


class _ComparablesAging:
    """Carry the starting rate forward by the comparables curve's yearly
    changes, ADDED (the additive fix). Production's basing: the path is read
    from the player's profile one age back, then two, as ratio_path does."""
    IMPUTE = True
    _curves: dict = {}

    def fit(self, table, before):
        super().fit(table, before)
        key = (self.IMPUTE, before)
        if key not in self._curves:
            AC, SFP = _aging_module()
            path = str(SFP.F_WAR_AGE)
            self._curves[key] = (imputed_aging_model(path, before) if self.IMPUTE
                                 else AC.AgingModel(path, before=before))
        self.curve_ = self._curves[key]
        self.page_ = before
        self._cum = {}
        return self

    def _changes(self, key, age, is_d):
        """Cumulative change from `age` to age+k, k = 0..HMAX, and its source."""
        m = self.curve_
        ck = (key, age)
        if ck in self._cum:
            return self._cum[ck]
        max_age = m.AMIN + m.nages - 1
        out, src = None, None
        if key in m.players:
            for lag in (1, 2):
                base = age - lag
                hz = min(HMAX + lag, max_age - base - 1)
                if hz < lag:
                    continue
                try:
                    tr = m.project(key, current_age=base, horizon=hz)
                except (ValueError, KeyError, IndexError):
                    continue
                lv = dict(zip(tr["age"].astype(int), tr["projected_war_per_82"]))
                if age not in lv:
                    continue
                out = [lv[age + k] - lv[age] if (age + k) in lv else np.nan
                       for k in range(HMAX + 1)]
                src = "own_comparables"
                break
        if out is None:
            pos = "D" if is_d else "F"
            out, c = [0.0], 0.0
            for k in range(1, HMAX + 1):
                g = m.gdelta.get((pos, age + k - 1))
                c = c + g if g is not None else np.nan
                out.append(c)
            src = "league_curve"
        for k in range(1, HMAX + 1):                  # past the oldest age: hold flat
            if not np.isfinite(out[k]):
                out[k] = out[k - 1]
        self._cum[ck] = (np.array(out, dtype=float), src)
        return self._cum[ck]

    def _walk(self, r, rate0, a, h):
        rate0 = np.asarray(rate0, dtype=float)
        if h == 0:
            return rate0
        out = rate0.copy()
        ages = a["age"].to_numpy(float)
        is_d = a["is_D"].to_numpy(float)
        keys = r["career_key"].to_numpy()
        for i in range(len(out)):
            if not (np.isfinite(ages[i]) and np.isfinite(rate0[i])):
                continue                              # no age: carried flat, as every arm does
            cum, _ = self._changes(keys[i], int(round(ages[i])), bool(is_d[i]))
            out[i] = rate0[i] + cum[min(h, HMAX)]
        return out


class ObviousFixes(_ComparablesAging, A1HingeExposure):
    """THE HEADLINE: fitted starting rate, rebuilt games share and chance of
    playing, comparables aging (added, departures imputed)."""
    name = "obvious fixes: fitted start, comparables aging with departures"
    IMPUTE = True


class ObviousFixesSurvivors(_ComparablesAging, A1HingeExposure):
    """The same with production's survivors-only pool. On the harness horizons
    it reproduces run_aging_method_test's comparables arm (checked by the
    runner)."""
    name = "obvious fixes, comparables pool of survivors only"
    IMPUTE = False


class PlainStart(ObviousFixes):
    """A lower rung: the 50/30/20 three-season rate per 82 with NO pull toward
    the league. Games-weighted, so a ten-game season does not carry half the
    weight on its rate: rate = sum(w * GP * rate82) / sum(w * GP), which is the
    weighted WAR per weighted game, the rate analogue of production's weighted
    total. Seasons of 10+ games only (production's anchor rule). Where the
    player has no such season in the three before the page (the rebuilt model's
    returning-player anchors), the rebuilt anchor's trailing rate is used."""
    name = "obvious fixes without the fitted pull: plain 50/30/20 rate"

    def _plain_rate(self, iset, subs):
        s = iset.seasons
        s = s[(s["GP"] >= C.MIN_GP) & s["syr"].between(iset.t0 - 3, iset.t0 - 1)].copy()
        s["w"] = (iset.t0 - s["syr"]).map(START_WEIGHTS) * s["GP"]
        g = s.assign(num=s["w"] * s["WAR_82"]).groupby("career_key")[["num", "w"]].sum()
        return (g["num"] / g["w"]).reindex(subs["career_key"]).to_numpy(float)

    def predict(self, iset, subs, horizons):
        self._guard_horizons(horizons)
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])
        rate0 = self._plain_rate(iset, subs)
        self.n_fallback_ = int((~np.isfinite(rate0)).sum())
        rate0 = np.where(np.isfinite(rate0), rate0, a["tr_WAR"].to_numpy(float))
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
