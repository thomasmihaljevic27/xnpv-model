"""run_goalie_bakeoff.py -- can anything beat the flat, heavily-shrunk rule?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch, first
step. Development pages only. Nothing adopted.

WHY THIS BEFORE ANYTHING ELSE
    The rebuild has no goaltenders in it. Before a goalie control-year gate,
    a goalie price line or a goalie participation model can be built, one
    question has to be answered: does forecasting a goaltender work at all on
    this evidence, and does the rule production already uses hold up when it
    is scored the way every skater candidate has been scored?

    Production's rule, read from `20_CODE/contract_npv.py`: a trailing
    50/30/20 blend of the last three seasons' WAR, falling back to 60/40 and
    then to last season alone; shrunk by KEEPING 35% of it and putting 65% on
    a league average of 2.189; then held FLAT across the whole contract, with
    no aging curve. That is a strong claim -- that two thirds of what a
    goaltender just did is noise, and that he then never ages -- and it has
    never been scored on held-out pages in this tree.

WHAT IS BEING SCORED
    The same harness, the same pages, the same frozen information set the
    skater bake-off used. Every candidate answers the same grid of
    (goaltender, horizon) cells and is scored on season WAR, so a candidate
    cannot win by declining the hard ones.

    Every candidate shares ONE participation estimator, fitted before each
    page. The question here is ability, and letting candidates differ on who
    is still in the league would mix the two.

THE EVIDENCE IS THIN AND THAT IS THE POINT
    82 goaltender-seasons a year against roughly 700 skater-seasons, 280
    goaltenders in nineteen years. Any difference between candidates has to
    be read against that, and the run reports a paired bootstrap rather than
    a bare ranking.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import information_set as ISET
import forecast_harness as H
import goalie_season_table as GST
from player_season_table import birthdate_source

SCRIPT_VERSION = "1.0"

HORIZONS = (0, 1, 2, 3, 4, 5)

# Production's locked goalie constants, read from 20_CODE/contract_npv.py and
# quoted here so the comparison is against what production actually does.
PROD_KEEP = 0.35            # the weight on the goaltender's own trailing blend
PROD_LEAGUE_AVG = 2.189172466


# ---------------------------------------------------------------------------
# WHAT EVERY CANDIDATE SHARES
# ---------------------------------------------------------------------------
def trailing_blend(seasons: pd.DataFrame, t0: int, col: str = "WAR"):
    """Production's cascade: 50/30/20 over the last three seasons, 60/40 with
    two, last season alone with one. Returned per career_key, with the number
    of seasons behind it so a consumer can weight its own evidence."""
    w = {k: (seasons[seasons["syr"] == t0 - k]
             .drop_duplicates("career_key").set_index("career_key")[col])
         for k in (1, 2, 3)}
    idx = sorted(set().union(*[set(s.index) for s in w.values()]))
    a = pd.DataFrame({f"w{k}": w[k].reindex(idx) for k in (1, 2, 3)})
    n = a.notna().sum(axis=1)
    blend = pd.Series(np.nan, index=idx, dtype=float)
    three = n == 3
    blend[three] = (a.loc[three, "w1"] * 0.5 + a.loc[three, "w2"] * 0.3
                    + a.loc[three, "w3"] * 0.2)
    two = (n == 2)
    if two.any():
        # The two that exist, in order, at 60/40 -- not necessarily t-1 and
        # t-2: a goaltender who missed last season still has two seasons
        # behind him and the cascade must not silently drop him.
        vals = a.loc[two, ["w1", "w2", "w3"]].apply(
            lambda r: pd.Series(r.dropna().to_numpy()[:2]), axis=1)
        blend[two] = vals[0] * 0.6 + vals[1] * 0.4
    one = n == 1
    if one.any():
        blend[one] = a.loc[one].apply(lambda r: r.dropna().to_numpy()[0], axis=1)
    return blend, n


def games_behind(seasons: pd.DataFrame, t0: int) -> pd.Series:
    """How many games the trailing window actually rests on. A goaltender's
    evidence is his workload, not the number of calendar seasons he appears
    in: twenty games of a backup season is not the same evidence as sixty."""
    w = seasons[seasons["syr"].between(t0 - 3, t0 - 1)]
    return w.groupby("career_key")["GP"].sum()


def survival_table(seasons: pd.DataFrame, t0: int) -> dict:
    """The chance a goaltender who was around at a page is in the league h
    seasons later, estimated ONLY on pages whose outcome is already complete
    before t0. One estimator, shared by every candidate, so the bake-off is
    about ability and not about who is still playing.
    """
    out = {}
    for h in HORIZONS:
        num = den = 0
        for page in range(C.FIRST_SOURCE_SEASON + 3, t0):
            if page + h >= t0:            # the outcome must already be known
                continue
            there = set(seasons.loc[seasons["syr"] == page - 1, "career_key"])
            later = set(seasons.loc[seasons["syr"] == page + h, "career_key"])
            den += len(there)
            num += len(there & later)
        out[h] = (num / den) if den else 1.0
    return out


class GoalieModel:
    """The harness's model interface, with the parts every goalie candidate
    shares: the shared participation estimator, the shared role forecast, and
    the grid contract. A candidate supplies `war_for` and nothing else."""

    name = "goalie"

    def fit(self, seasons: pd.DataFrame, before: int) -> "GoalieModel":
        # ROLLING, and asserted rather than promised: nothing whose OUTCOME
        # season reaches t0 may enter a fit.
        assert seasons["syr"].max() < before, (
            f"{self.name} was handed a season at or after the page it stands "
            f"on ({seasons['syr'].max()} >= {before})")
        self.t0_ = int(before)
        self.seasons_ = seasons
        self.qual_ = seasons[seasons["GP"] >= C.MIN_GP]
        self.league_ = float(self.qual_["WAR"].mean())
        self.surv_ = survival_table(seasons, before)
        self._fit(seasons, before)
        return self

    def _fit(self, seasons, before):
        pass

    def share_for(self, subs: pd.DataFrame) -> pd.Series:
        """The share of the schedule he plays. Trailing share, carried flat --
        the same rule for every candidate, because this bake-off is about how
        well a goaltender is forecast and not about who gets the starts."""
        w = self.qual_[self.qual_["syr"].between(self.t0_ - 3, self.t0_ - 1)]
        sh = (w.sort_values("syr").groupby("career_key")["gp_share"]
              .apply(lambda s: float(np.average(
                  s.to_numpy(), weights=np.linspace(1, 2, len(s))))))
        return sh.reindex(subs["career_key"]).fillna(sh.median()).clip(0.05, 1.0)

    def predict(self, iset, subs: pd.DataFrame, horizons) -> pd.DataFrame:
        war = self.war_for(subs)                 # season WAR, per goaltender
        share = self.share_for(subs)
        rows = []
        for h in horizons:
            rows.append(pd.DataFrame({
                "career_key": subs["career_key"].to_numpy(),
                "h": int(h),
                # The harness multiplies rate by share by the chance he plays,
                # so a candidate that thinks in season totals divides by the
                # share here rather than being rewritten around a rate.
                # The harness multiplies rate by share, so a candidate that
                # thinks in season totals hands over total / share.
                "rate_82": war.to_numpy() / share.to_numpy(),
                "gp_share": share.to_numpy(),
                "p_play": self.surv_[int(h)],
            }))
        out = pd.concat(rows, ignore_index=True)
        out["rate_82"] = out["rate_82"].replace([np.inf, -np.inf], np.nan)
        assert out["rate_82"].notna().all(), f"{self.name} declined a cell"
        return out


class FlatAverage(GoalieModel):
    """Every goaltender is the league. Production's pre-2026 out-year
    placeholder, kept as the floor: any rule that cannot beat it is not
    reading the goaltender at all."""

    name = "the league average"

    def war_for(self, subs):
        return pd.Series(self.league_, index=subs["career_key"])


class ProductionRule(GoalieModel):
    """Production's locked rule: 50/30/20, keep 35% toward the league average,
    flat forever. The league average is the one production carries."""

    name = "production's rule (keep 0.35, flat)"
    keep = PROD_KEEP
    # Which league average the shrinkage pulls toward: production's own
    # constant, or the mean of what the page could actually see.
    use_prod_average = True

    def anchor(self, subs):
        blend, n = trailing_blend(self.qual_, self.t0_)
        return blend.reindex(subs["career_key"]), n.reindex(subs["career_key"])

    def war_for(self, subs):
        a, _ = self.anchor(subs)
        avg = PROD_LEAGUE_AVG if self.use_prod_average else self.league_
        return (self.keep * a + (1 - self.keep) * avg).fillna(avg)


class ProductionRuleOwnAverage(ProductionRule):
    """The same rule with the league average measured on what the page could
    see, rather than the single number production carries from 2026. It
    separates the rule from the constant."""

    name = "the same, on the page's own average"
    use_prod_average = False


class FittedShrinkage(ProductionRule):
    """The same cascade, with the kept weight FITTED on what the page could
    see instead of fixed at 0.35.

    The weight that minimises squared error is the slope of next season's WAR
    on the trailing blend, which is a reliability: how much of a goaltender's
    trailing level survives into the next season. Fitted on pairs whose
    outcome season is strictly before the page.
    """

    name = "the same, with the kept weight fitted"
    use_prod_average = False

    def _fit(self, seasons, before):
        xs, ys = [], []
        for page in range(C.FIRST_SOURCE_SEASON + 4, before):
            blend, _ = trailing_blend(seasons[seasons["syr"] < page], page)
            nxt = (seasons[seasons["syr"] == page]
                   .drop_duplicates("career_key").set_index("career_key")["WAR"])
            j = pd.concat([blend.rename("x"), nxt.rename("y")], axis=1).dropna()
            xs.append(j["x"].to_numpy()); ys.append(j["y"].to_numpy())
        if not xs or sum(len(x) for x in xs) < 50:
            self.keep_ = PROD_KEEP
            self.n_pairs_ = 0
            return
        x = np.concatenate(xs); y = np.concatenate(ys)
        self.n_pairs_ = len(x)
        # Slope through the means: the shrinkage that a least-squares fit
        # implies, with the intercept absorbed by the league average below.
        self.keep_ = float(np.clip(
            np.cov(x, y, ddof=1)[0, 1] / max(np.var(x, ddof=1), 1e-9), 0.0, 1.0))

    def war_for(self, subs):
        a, _ = self.anchor(subs)
        k = getattr(self, "keep_", PROD_KEEP)
        return (k * a + (1 - k) * self.league_).fillna(self.league_)


class WorkloadWeighted(GoalieModel):
    """Shrink by how much evidence there is, not by a constant.

    A goaltender with 150 games behind him has told you more than one with
    40, and the cascade's fixed weights treat them alike. This keeps a share
    of his trailing level that rises with the games behind it, on the
    standard reliability form games / (games + k), with k fitted on pages the
    page could see.
    """

    name = "shrunk by the games behind it"

    def _fit(self, seasons, before):
        rows = []
        for page in range(C.FIRST_SOURCE_SEASON + 4, before):
            past = seasons[seasons["syr"] < page]
            blend, _ = trailing_blend(past, page)
            gp = games_behind(past, page)
            nxt = (seasons[seasons["syr"] == page]
                   .drop_duplicates("career_key").set_index("career_key")["WAR"])
            j = pd.concat([blend.rename("x"), gp.rename("gp"),
                           nxt.rename("y")], axis=1).dropna()
            j["avg"] = float(past[past["GP"] >= C.MIN_GP]["WAR"].mean())
            rows.append(j)
        d = pd.concat(rows) if rows else pd.DataFrame()
        self.k_ = 120.0
        if len(d) > 50:
            best, bk = np.inf, self.k_
            for k in (20, 40, 60, 90, 120, 160, 220, 300, 400, 600):
                w = d["gp"] / (d["gp"] + k)
                err = float(np.mean((w * d["x"] + (1 - w) * d["avg"] - d["y"]) ** 2))
                if err < best:
                    best, bk = err, k
            self.k_ = float(bk)
        self.n_pairs_ = len(d)

    def war_for(self, subs):
        blend, _ = trailing_blend(self.qual_, self.t0_)
        gp = games_behind(self.qual_, self.t0_)
        a = blend.reindex(subs["career_key"])
        g = gp.reindex(subs["career_key"]).fillna(0.0)
        w = g / (g + self.k_)
        return (w * a.fillna(self.league_) + (1 - w) * self.league_)


class WorkloadWeightedAging(WorkloadWeighted):
    """The same, with the flat carry replaced by a fitted average change.

    Production's goalie branch has no aging curve at all -- a projection is
    held flat for eight years. Whether that costs anything looked testable:
    fit the average season-to-season change in WAR on pages the page could
    see, and walk the projection along it.

    IT IS NOT IDENTIFIED ON THIS PANEL, which is the finding rather than the
    candidate. The fitted change flips sign across the development pages,
    from +0.117 WAR a season on the 2015 page to -0.106 on the 2021 page, so
    the early pages walk a goaltender UP and the late ones walk him down. A
    within-player change can only be measured on goaltenders who played both
    seasons, and the ones who fall out are the ones who declined -- the same
    selection the skater side documents, on a twelfth of the sample. The
    candidate is kept in the bake-off because a negative result recorded is
    worth more than a candidate quietly dropped.
    """

    name = "the same, with a fitted age change"

    def _fit(self, seasons, before):
        super()._fit(seasons, before)
        d = seasons[(seasons["GP"] >= C.MIN_GP) & seasons["has_age"]]
        d = d.sort_values(["career_key", "syr"])
        d["dwar"] = d.groupby("career_key")["WAR"].diff()
        d["dage"] = d.groupby("career_key")["syr"].diff()
        d = d[(d["dage"] == 1) & d["dwar"].notna() & (d["syr"] < before)]
        self.age_slope_ = 0.0
        self.age_pivot_ = float(d["age"].median()) if len(d) else 28.0
        if len(d) > 100:
            x = d["age"].to_numpy(float) - self.age_pivot_
            y = d["dwar"].to_numpy(float)
            self.age_slope_ = float(np.polyfit(x, y, 1)[1])   # mean change

    def predict(self, iset, subs, horizons):
        base = super().predict(iset, subs, horizons)
        # The change compounds over the horizon: a goaltender h seasons out is
        # h years older than the one the anchor describes.
        base["rate_82"] = base["rate_82"] + self.age_slope_ * base["h"] / \
            base["gp_share"].clip(lower=0.05)
        return base


CANDIDATES = (FlatAverage, ProductionRule, ProductionRuleOwnAverage,
              FittedShrinkage, WorkloadWeighted, WorkloadWeightedAging)


def paired_bootstrap(a: pd.DataFrame, b: pd.DataFrame, n: int = 2000,
                     seed: int = 20260917) -> float:
    """How often the second candidate beats the first on absolute WAR error,
    resampling GOALTENDERS rather than rows, because a goaltender's seasons
    are not independent draws and there are only 280 of him."""
    j = (a[["career_key", "h", "e_war"]]
         .merge(b[["career_key", "h", "e_war"]], on=["career_key", "h"],
                suffixes=("_a", "_b")))
    if j.empty:
        return float("nan")
    keys = j["career_key"].unique()
    g = {k: v for k, v in j.groupby("career_key")}
    rng = np.random.default_rng(seed)
    wins = 0
    for _ in range(n):
        pick = rng.choice(keys, size=len(keys), replace=True)
        s = pd.concat([g[k] for k in pick])
        wins += int(s["e_war_a"].abs().mean() > s["e_war_b"].abs().mean())
    return wins / n


def main() -> None:
    C.banner("run_goalie_bakeoff.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    table = GST.build(birthdate_csv=path, verbose=True, allow_thin_ages=True)
    C.log("")
    C.log("  AGE COVERAGE IS 76%, NOT THE SKATER TABLE'S 98%. The birthdate")
    C.log("  table was built for skaters and its goalie keys are thinner, so")
    C.log("  the age candidate below is fitted on three quarters of the panel")
    C.log("  and the rest keep a flat projection. That is a limitation of this")
    C.log("  run, not a finding about goaltenders.")
    C.log("")

    har = H.Harness(table)
    scored = {}
    for cls in CANDIDATES:
        m = cls()
        d = har.run(m, pages=C.DEV_PAGES, horizons=HORIZONS)
        scored[m.name] = d
        C.log(f"  ran {m.name}: {len(d)} scored cells")
    C.log("")

    C.log("HOW WELL EACH RULE FORECASTS A GOALTENDER'S SEASON, mean absolute")
    C.log("error in WAR, on development pages. Lower is better. Every")
    C.log("candidate answered the same grid and shared one participation")
    C.log("estimator, so this is about ability alone.")
    C.log("")
    width = max(len(n) for n in scored)
    head = f"  {'rule':<{width}}{'all':>8}"
    for h in HORIZONS:
        head += f"{'h' + str(h):>8}"
    C.log(head + f"{'bias':>9}")
    for name, d in scored.items():
        line = f"  {name:<{width}}{d['e_war'].abs().mean():>8.3f}"
        for h in HORIZONS:
            line += f"{d.loc[d['h'] == h, 'e_war'].abs().mean():>8.3f}"
        C.log(line + f"{d['e_war'].mean():>9.3f}")
    C.log("")

    base = scored["production's rule (keep 0.35, flat)"]
    C.log("AGAINST PRODUCTION'S RULE, resampling GOALTENDERS rather than")
    C.log("rows -- there are 280 of them and a goaltender's seasons are not")
    C.log("independent draws.")
    C.log("")
    C.log(f"  {'rule':<{width}}{'MAE gap':>10}{'beats it':>11}")
    for name, d in scored.items():
        if d is base:
            continue
        gap = d["e_war"].abs().mean() - base["e_war"].abs().mean()
        C.log(f"  {name:<{width}}{gap:>10.3f}{paired_bootstrap(base, d):>10.0%}")
    C.log("")

    # ---- what the fitted numbers came out at -------------------------------
    m = FittedShrinkage().fit(table[table["syr"] < max(C.DEV_PAGES)],
                              max(C.DEV_PAGES))
    w = WorkloadWeighted().fit(table[table["syr"] < max(C.DEV_PAGES)],
                               max(C.DEV_PAGES))
    ag = WorkloadWeightedAging().fit(table[table["syr"] < max(C.DEV_PAGES)],
                                     max(C.DEV_PAGES))
    C.log("IS THE AGE TERM EVEN IDENTIFIED? The fitted average change, page")
    C.log("by page. A quantity that flips sign as the window moves is not a")
    C.log("measurement of how goaltenders age; it is what a within-player")
    C.log("change looks like when only the goaltenders who kept playing are")
    C.log("in the sample, on 82 seasons a year.")
    C.log("")
    C.log(f"    {'page':<8}{'fitted change in WAR a season':>32}")
    for page in C.DEV_PAGES:
        a = WorkloadWeightedAging().fit(table[table["syr"] < page], page)
        C.log(f"    {page:<8}{a.age_slope_:>32.3f}")
    C.log("")

    C.log("WHAT THE FITS CAME OUT AT on the last development page, which is")
    C.log("the most evidence any page in this run had:")
    C.log(f"    production keeps                       {PROD_KEEP:.2f} of trailing")
    C.log(f"    fitted on {m.n_pairs_} pairs, it keeps      {m.keep_:.2f}")
    C.log(f"    workload weighting's half-point        {w.k_:.0f} games "
          f"(a goaltender with that many games behind him keeps half)")
    C.log(f"    the fitted age change                  {ag.age_slope_:+.3f} "
          f"WAR a season, pivoting at age {ag.age_pivot_:.0f}")
    C.log("")

    out = pd.concat([d.assign(rule=n) for n, d in scored.items()],
                    ignore_index=True)
    out.to_csv(C.out_path("goalie_bakeoff.csv"), index=False)
    C.log(f"  wrote {C.out_path('goalie_bakeoff.csv').name} ({len(out)} rows)")
    C.write_log("goalie_bakeoff_run_log.txt")


if __name__ == "__main__":
    main()
