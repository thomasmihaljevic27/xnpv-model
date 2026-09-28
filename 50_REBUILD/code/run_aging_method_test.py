"""run_aging_method_test.py -- one fitted equation against comparable players, aging alone.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

THE QUESTION
    Two ways of aging a player's level forward:
      comparables  the current model (20_CODE/aging_curve.py): for each player,
                   the similarity-weighted yearly changes of same-age,
                   same-position players, blended with the league average;
      regression   the rebuilt model (aging_additive.py): one equation for
                   everyone, the yearly change as a cubic in age, a defence
                   shift, and a level term (the rate one season earlier) with
                   its age interaction, fitted on consecutive-season pairs.
    Earlier comparisons scored the two whole forecasts, which differ in their
    starting level and participation as well. This run holds everything but
    the aging steps fixed.

WHAT IS HELD FIXED
    Every arm is the rebuilt forecast without contract data
    (`A1HingeExposure`, the adopted leader's no-contract twin): the same
    starting level at the valuation season (its fitted pull toward the
    league), the same games share and the same participation, on the same
    harness rows. Only the change added to reach seasons 1-5 differs, and each
    arm's aging is fitted on seasons that finished before the page.

THE ARMS
    regression            the adopted curve: departing players entered at
                          replacement level (survivorship correction)
    regression_survivors  the same equation on players who played both seasons
                          only. The comparables curve is also built on
                          survivors, so this arm separates the equation's form
                          from the survivorship correction
    comparables           production's own curve (AgingModel(before=page), the
                          D3 revision), per player: its path's change from the
                          valuation age to each later age, added to the shared
                          starting level. Its own 55/45 starting pull is NOT
                          used (the starting level is shared), so only its
                          yearly changes enter. Based at the season before the
                          valuation season, then two before, as production's
                          ratio path does. Where it has no profile for the
                          player, its own league-average curve is used; where
                          the age is unknown, the level is carried flat (as the
                          regression arms do)
    no_aging              the starting level carried flat: the floor

THE SCORES AND THE RULE, DECLARED BEFORE THE RUN
    1. the rate per 82 games in seasons played, absolute error (what aging
       predicts directly);
    2. season WAR, squared error (the harness's primary score).
    Both are scored on the full grid and on the rows where the comparables arm
    used a player's own comparables, the same rows for every arm, with shares
    of 2,000 player resamples. Horizons 1-5 carry the comparison; the
    valuation season is identical across arms by construction.
    A method is called better only if it is lower on BOTH scores, on both
    samples, in at least 1,950 of 2,000 resamples. Otherwise: no clear winner.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table
from ability_forecast import A1HingeExposure
import production_adapter as PA
from run_skater_contract_test import Boot, _count
import run_aging_choices_test as RAC

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)
HMAX = max(HORIZONS)


class RegressionSurvivors(A1HingeExposure):
    name = "rebuilt forecast, regression aging on survivors only"
    AGING_SELECTION = "none"


class NoAging(A1HingeExposure):
    name = "rebuilt forecast, no aging (starting level carried)"

    def _walk(self, r, rate0, a, h):
        return np.asarray(rate0, dtype=float)


class Comparables(A1HingeExposure):
    """The rebuilt forecast with the current model's comparables aging steps."""
    name = "rebuilt forecast, comparables aging"
    _curves: dict = {}

    def fit(self, table, before):
        super().fit(table, before)
        if before not in self._curves:
            PA._production()                                  # production on sys.path, .env loaded
            import aging_curve as AC
            SFP = sys.modules["skater_forward_projection"]
            self._curves[before] = AC.AgingModel(str(SFP.F_WAR_AGE), before=before)
        self.curve_ = self._curves[before]
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
            for lag in (1, 2):                                # production's D21 basing
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
                out = [lv[age + k] - lv[age] if (age + k) in lv else np.nan for k in range(HMAX + 1)]
                src = "own_comparables"
                break
        if out is None:
            # the comparables method's own fallback: its league-average yearly changes
            pos = "D" if is_d else "F"
            out, c = [0.0], 0.0
            for k in range(1, HMAX + 1):
                g = m.gdelta.get((pos, age + k - 1))
                c = c + g if g is not None else np.nan
                out.append(c)
            src = "league_curve"
        # beyond the curve's oldest age, hold the last change flat
        for k in range(1, HMAX + 1):
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
                self.source_[(self.page_, keys[i])] = "no_age"
                continue
            cum, src = self._changes(keys[i], int(round(ages[i])), bool(is_d[i]))
            out[i] = rate0[i] + cum[h]
            self.source_[(self.page_, keys[i])] = src
        return out

    source_: dict = {}


ARMS = {"regression": A1HingeExposure, "regression_survivors": RegressionSurvivors,
        "comparables": Comparables, "no_aging": NoAging}


def score(runs, label, sel_fn=None):
    keys = ["career_key", "page", "h"]
    al = {k: d.set_index(keys).sort_index() for k, d in runs.items()}
    ref = al["regression"]
    for k, d in al.items():
        assert d.index.equals(ref.index), f"{k} answered different rows"
        assert np.array_equal(d["act_war"].to_numpy(), ref["act_war"].to_numpy()), f"{k} target differs"
        # the valuation season is identical by construction
        h0 = d.index.get_level_values("h") == 0
        assert np.array_equal(d.loc[h0, "rate_82"].to_numpy(), ref.loc[h0, "rate_82"].to_numpy()), k
        for c in ("gp_share", "p_play"):
            assert np.array_equal(d[c].to_numpy(), ref[c].to_numpy()), f"{k} moved {c}"
    base = ref.reset_index()
    sel = (base["h"] >= 1).to_numpy().copy()
    if sel_fn is not None:
        sel &= sel_fn(base).to_numpy(dtype=bool)
    b = base[sel]
    played = b["played"].astype(bool).to_numpy()
    boot_all = Boot(b["career_key"])
    boot_pl = Boot(b.loc[played, "career_key"])
    C.log(f"  {label}: {int(sel.sum())} forecasts at seasons 1-5 ({int(played.sum())} played), "
          f"{b['career_key'].nunique()} players")
    C.log(f"    {'arm':<22}{'rate MAE':>10}{'lower':>11}{'WAR RMSE':>10}{'lower':>11}{'rate bias':>11}")
    rows = []
    r_ref = b.loc[played, "e_rate"].abs()
    w_ref = b["e_war"] ** 2
    for k, d in al.items():
        d = d.reset_index()[sel]
        re_ = d.loc[played, "e_rate"].abs()
        we = d["e_war"] ** 2
        lr = "--" if k == "regression" else _count(boot_pl.lower_share(r_ref, re_))
        lw = "--" if k == "regression" else _count(boot_all.lower_share(w_ref, we))
        row = dict(sample=label, arm=k, n=int(sel.sum()), rate_mae=float(re_.mean()),
                   war_rmse=float(np.sqrt(we.mean())), rate_bias=float(d.loc[played, "e_rate"].mean()))
        C.log(f"    {k:<22}{row['rate_mae']:>10.4f}{lr:>11}{row['war_rmse']:>10.4f}{lw:>11}{row['rate_bias']:>+11.4f}")
        rows.append(row)
    C.log("    ('lower' = resamples in which the arm's error is below the regression's)")
    C.log("")
    C.log(f"    rate MAE among seasons played, by seasons ahead ({label}):")
    C.log("    " + f"{'arm':<22}" + "".join(f"{'h' + str(h):>9}" for h in HORIZONS[1:]))
    for k, d in al.items():
        d = d.reset_index()[sel]
        C.log("    " + f"{k:<22}" + "".join(
            f"{d.loc[(d['h'] == h) & d['played'].astype(bool), 'e_rate'].abs().mean():>9.4f}" for h in HORIZONS[1:]))
    C.log(f"    rate MAE among seasons played, seasons 1-5, by tier of trailing total ({label}):")
    tiers = [t for t in ("below 0", "0 to 1", "1 to 2", "2 to 3", "3+") if t in set(b["tier"])]
    C.log("    " + f"{'arm':<22}" + "".join(f"{t:>10}" for t in tiers) + f"{'  rows (3+)':>12}")
    for k, d in al.items():
        d = d.reset_index()[sel]
        pl = d["played"].astype(bool)
        C.log("    " + f"{k:<22}" + "".join(f"{d.loc[pl & (d['tier'] == t), 'e_rate'].abs().mean():>10.4f}" for t in tiers)
              + f"{int((pl & (d['tier'] == '3+')).sum()):>12}")
    C.log(f"    rate bias among seasons played by tier of trailing total, five seasons out ({label}):")
    tiers = [t for t in ("below 0", "0 to 1", "1 to 2", "2 to 3", "3+") if t in set(b["tier"])]
    C.log("    " + f"{'arm':<22}" + "".join(f"{t:>10}" for t in tiers))
    for k, d in al.items():
        d = d.reset_index()[sel]
        m5 = (d["h"] == 5) & d["played"].astype(bool)
        C.log("    " + f"{k:<22}" + "".join(f"{d.loc[m5 & (d['tier'] == t), 'e_rate'].mean():>+10.3f}" for t in tiers))
    C.log("")
    return rows, {k: dict(rate=None if k == "regression" else boot_pl.lower_share(r_ref, al[k].reset_index()[sel].loc[played, "e_rate"].abs()),
                          war=None if k == "regression" else boot_all.lower_share(w_ref, al[k].reset_index()[sel]["e_war"] ** 2))
                  for k in al}


def main() -> None:
    C.banner("run_aging_method_test.py", SCRIPT_VERSION)
    path, how = RAC._birthdates()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=False)
    har = H.Harness(table)
    runs = {}
    for k, cls in ARMS.items():
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS)
        C.log(f"  ran {k}: {len(runs[k])} forecasts")
    src = pd.Series(Comparables.source_)
    C.log("  comparables arm, where its changes came from (player-pages): "
          + ", ".join(f"{k} {v:,}" for k, v in src.value_counts().items()))
    C.log("")
    own = {k for k, v in Comparables.source_.items() if v == "own_comparables"}
    sel_own = lambda d: pd.Series([(p, c) in own for p, c in zip(d["page"], d["career_key"])], index=d.index)
    r1, s1 = score(runs, "full grid")
    r2, s2 = score(runs, "rows where the comparables arm used the player's own comparables", sel_own)
    # the declared rule
    C.log("  THE DECLARED RULE (lower on both scores, both samples, in >= 1,950 of 2,000):")
    for k in ("comparables", "regression_survivors", "no_aging"):
        shares = [s1[k]["rate"], s1[k]["war"], s2[k]["rate"], s2[k]["war"]]
        beats = all(x >= 0.975 for x in shares)          # arm better than regression
        loses = all(x <= 0.025 for x in shares)          # regression better than arm
        verdict = (f"{k} better than regression" if beats else
                   f"regression better than {k}" if loses else "no clear winner")
        C.log(f"    {k:<22} shares lower than regression {[_count(x) for x in shares]}: {verdict}")
    pd.DataFrame(r1 + r2).to_csv(C.out_path("aging_method_summary.csv"), index=False)
    pd.concat([d.assign(arm=k) for k, d in runs.items()], ignore_index=True).to_csv(
        C.out_path("aging_method_forecasts.csv"), index=False)
    C.write_log("aging_method_run_log.txt")


if __name__ == "__main__":
    main()
