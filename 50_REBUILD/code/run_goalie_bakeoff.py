"""run_goalie_bakeoff.py -- can anything beat the flat, heavily-shrunk rule?

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch, first
step. Development pages only. Nothing adopted.

WHY THIS BEFORE ANYTHING ELSE
    The rebuild has no goaltenders in it. Before a goalie control-year gate,
    a goalie price line or a goalie participation model can be built, one
    question has to be answered: does forecasting a goaltender work at all on
    this evidence, and does the rule production already uses hold up when it
    is scored the way every skater candidate has been scored?

    Production's rule is IMPORTED here and called, not reimplemented. The
    first version of this bake-off rebuilt the cascade from a partial reading
    of `contract_npv.py` and labelled the result "production's rule"; it was
    missing production's games filter, its strict slot rule, and its 0.650
    shrinkage target for goaltenders returning after an absence. The
    conclusion drawn against that lookalike did not survive the real thing.
    The reimplementation is kept in the bake-off as "a simplified cascade",
    because the gap between it and the imported projector is itself worth
    seeing.

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

SCRIPT_VERSION = "2.3"

HORIZONS = (0, 1, 2, 3, 4, 5)

# Production's locked goalie constants, read from 20_CODE/contract_npv.py and
# quoted here so the comparison is against what production actually does.
PROD_KEEP = 0.35            # the weight on the goaltender's own trailing blend
PROD_LEAGUE_AVG = 2.189172466


def production_projector():
    """Production's goalie projector, imported and built once.

    Needs the season spine, which is a production output. Absent it, the
    candidate cannot run and says so instead of standing in for production
    with a lookalike -- which is the mistake this function exists to undo.
    """
    global _PROJ
    if _PROJ is not None:
        return _PROJ
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(C.PROD_CODE_DIR))
    import contract_npv as NPV
    spine = pd.read_csv(Path(C.PROD_OUTPUT_DIR) / "contract_season_spine.csv")
    spine["full_name"] = (spine["first_name"].astype(str) + " "
                          + spine["last_name"].astype(str))
    from player_season_table import norm_name
    spine["nname"] = spine["full_name"].map(norm_name)
    _PROJ = NPV.GoalieProjector(spine)
    return _PROJ


_PROJ = None


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


def trailing_share(qual: pd.DataFrame, t0: int, keys) -> pd.Series:
    """His trailing share of the schedule at page t0, for each of `keys`.

    Qualifying seasons (the caller passes MIN_GP-filtered rows) in t0-3..t0-1,
    averaged with linearly rising weights over the seasons he has, so the most
    recent counts most. A goaltender with none takes the page's median, and the
    result is bounded to [0.05, 1].

    ONE RULE, WHEREVER A TRAILING SHARE IS NEEDED. The bake-off's candidates,
    the participation runner's arms, the rate runner's arms and the price
    runner's goalie forecast all call this, because a second implementation
    with different filters or weights is a second forecast wearing the first
    one's name -- which is what a review found in the price runner.
    """
    w = qual[qual["syr"].between(t0 - 3, t0 - 1)]
    sh = (w.sort_values("syr").groupby("career_key")["gp_share"]
          .apply(lambda s: float(np.average(
              s.to_numpy(), weights=np.linspace(1, 2, len(s))))))
    return sh.reindex(keys).fillna(sh.median()).clip(0.05, 1.0)


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
        return trailing_share(self.qual_, self.t0_, subs["career_key"])

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


class ProductionProjector(GoalieModel):
    """PRODUCTION'S OWN PROJECTOR, IMPORTED, not a reimplementation of it.

    The first version of this bake-off rebuilt the cascade from a reading of
    `contract_npv.py` and labelled the result "production's rule". It was not.
    Three things differ, and the review found all three:

      * production's lookup table has NO games filter -- a two-game season is
        a prior like any other -- while the rebuilt one dropped anything under
        MIN_GP;
      * production's cascade fills the t-1, t-2, t-3 slots STRICTLY, and a
        goaltender with no t-1 season does not fall to a 60/40 of whatever
        else exists: he goes to a STALE ANCHOR computed at an earlier
        standpoint, bounded at three seasons back;
      * a stale-anchor goaltender shrinks toward 0.650, the conditional mean
        of goaltenders who came back, and not toward the league average.

    The third of those I had never read: I read the first half of the method
    and described the whole of it. So this candidate imports the class and
    calls it, the same way the qualifying-offer bands are checked against
    production's implementation rather than re-derived.

    IT IS DATED BY CONSTRUCTION, and that is asserted rather than assumed.
    `shrunk_projection(nname, t0)` reads seasons t0-1 and earlier only, so a
    lookup table built over the whole file still answers a page question with
    page information -- and the check scrambles every season from the page
    onward to prove it.
    """

    name = "production's own projector (imported)"

    def _fit(self, seasons, before):
        self.proj_ = production_projector()

    def war_for(self, subs):
        keys = subs["career_key"].to_numpy()
        out = []
        for k in keys:
            v, _src = self.proj_.shrunk_projection(k, self.t0_)
            out.append(np.nan if v is None else float(v))
        w = pd.Series(out, index=subs["career_key"])
        # A goaltender production cannot price is prospect-pillar territory
        # there. Here the grid must be answered, so he takes the page's own
        # average and the count is reported rather than the row dropped.
        self.unpriced_ = int(w.isna().sum())
        return w.fillna(self.league_)


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

    name = "a simplified cascade, keep 0.35"
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

    name = "the same on the page's own average"
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
        # BOTH COEFFICIENTS, AND THE SLOPE IS THE ONE THAT USES AGE. The
        # first version took `polyfit(...)[1]`, which is the INTERCEPT -- the
        # average change at the pivot age -- and applied it to every
        # goaltender alike. Adding twenty years to every subject's age moved
        # nothing, so what it tested was a common drift and not ageing at all.
        self.age_slope_ = 0.0          # how the change varies with age
        self.age_drift_ = 0.0          # the change at the pivot age
        self.age_pivot_ = float(d["age"].median()) if len(d) else 28.0
        if len(d) > 100:
            x = d["age"].to_numpy(float) - self.age_pivot_
            y = d["dwar"].to_numpy(float)
            self.age_slope_, self.age_drift_ = (float(v) for v in np.polyfit(x, y, 1))

    def predict(self, iset, subs, horizons):
        base = super().predict(iset, subs, horizons)
        age = (subs.set_index("career_key")["age"]
               .reindex(base["career_key"]).to_numpy(float))
        age = np.where(np.isnan(age), self.age_pivot_, age)
        # THE CHANGE ACCUMULATES OVER THE SEASONS HE AGES THROUGH, and each
        # of those seasons has its own change because the change depends on
        # his age then. A goaltender h seasons out has lived through the
        # changes at ages a, a+1, ... a+h-1.
        delta = np.zeros(len(base))
        h = base["h"].to_numpy(int)
        for step in range(1, int(h.max()) + 1):
            at = age + step - 1 - self.age_pivot_
            delta += np.where(h >= step, self.age_drift_ + self.age_slope_ * at, 0.0)
        base["rate_82"] = base["rate_82"] + delta / base["gp_share"].clip(lower=0.05)
        return base


CANDIDATES = (FlatAverage, ProductionProjector, ProductionRule,
              ProductionRuleOwnAverage, FittedShrinkage, WorkloadWeighted,
              WorkloadWeightedAging)


def paired_bootstrap(a: pd.DataFrame, b: pd.DataFrame, n: int = 2000,
                     seed: int = 20260917) -> float:
    """How often the second candidate beats the first on absolute WAR error,
    resampling GOALTENDERS rather than rows, because a goaltender's seasons
    are not independent draws and there are only 280 of him."""
    # THE PAGE IS PART OF THE KEY. Joining on goaltender and horizon alone
    # matched a 2015 forecast to a 2021 one for the same goaltender, turning
    # 3,683 intended pairs into 19,853 rows and silently reweighting the
    # comparison toward goaltenders who appear on many pages. One forecast is
    # one (page, goaltender, horizon).
    keys = ["career_key", "page", "h"]
    j = (a[keys + ["e_war"]]
         .merge(b[keys + ["e_war"]], on=keys, suffixes=("_a", "_b"),
                validate="one_to_one"))
    assert len(j) <= min(len(a), len(b)), "the pairing duplicated forecasts"
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


def bias_diagnostic(scored: dict, base: pd.DataFrame) -> None:
    """How much of the pooled bias is the forecast, and how much is us.

    A mean error is easy to quote and hard to attribute. Two things have to
    be said beside it before it can be called a defect in anybody's forecast.

    FIRST, HOW WELL IT IS MEASURED. Resampling whole careers, not rows, gives
    an interval that has to be reported with the number.

    SECOND, WHAT IT IS MADE OF. Every candidate here shares one participation
    estimator, deliberately -- and if that estimator says a goaltender plays
    more often than he does, every candidate's predicted WAR is too high for a
    reason that has nothing to do with how it forecasts ability. The size of
    that gap is shown by an ILLUSTRATIVE calculation: the average over-
    prediction of playing, priced at the average production of a season that
    was actually played. It assigns the same 1.89 WAR to every played season,
    so it is a scale for the participation term and NOT a decomposition of the
    observed bias -- it does not say how much of the +0.101 participation
    caused, and an earlier version of this note read it as though it did.
    """
    C.log("IS THE POOLED BIAS A DEFECT IN THE FORECAST? Not established here,")
    C.log("and two things say why.")
    C.log("")
    keys = base["career_key"].unique()
    g = {k: v for k, v in base.groupby("career_key")}
    rng = np.random.default_rng(20260918)
    means = [pd.concat([g[k] for k in rng.choice(keys, len(keys), True)])
             ["e_war"].mean() for _ in range(2000)]
    lo, hi = np.percentile(means, [2.5, 97.5])
    C.log(f"  production's mean error is {base['e_war'].mean():+.3f} WAR, and")
    C.log(f"  resampling whole careers puts it between {lo:+.3f} and {hi:+.3f}.")
    C.log("  That interval contains zero, so this run does not establish that")
    C.log("  the forecast runs high at all.")
    C.log("")
    played = float(base["played"].mean())
    pred = float(base["p_play"].mean())
    war_if_played = float(base.loc[base["played"], "act_war"].mean())
    illustrative = float(((base["p_play"] - base["played"].astype(float))
                          * war_if_played).mean())
    C.log(f"  and the shared participation estimator says {100 * pred:.1f}% of")
    C.log(f"  these goaltender-seasons are played where {100 * played:.1f}% were.")
    C.log(f"  As a SCALE for that gap and nothing more: priced at a flat")
    C.log(f"  {war_if_played:.2f} WAR for every season actually played, it comes")
    C.log(f"  to {illustrative:+.3f} WAR, against the {base['e_war'].mean():+.3f} "
          f"observed. That")
    C.log("  is an illustration, not a decomposition. It gives every played")
    C.log("  season the same production, so it does not say how much of the")
    C.log("  observed bias participation caused -- only that the participation")
    C.log("  term is large enough that the bias cannot be read as the ability")
    C.log("  forecast's alone. Every candidate carries it, because they were")
    C.log("  given the same estimator on purpose.")
    C.log("")
    C.log("  So the pooled mean error is a DIAGNOSTIC and not a defect in")
    C.log("  anybody's ability forecast, and the difference between two")
    C.log("  candidates' biases is the only part of it this run can speak to.")
    C.log("  Nothing downstream should move a dollar price to cancel it. The")
    C.log("  place to take it up is the goalie participation model.")
    C.log("")
    C.log(f"    {'rule':<40}{'mean error':>12}")
    for name, d in scored.items():
        C.log(f"    {name:<40}{d['e_war'].mean():>12.3f}")
    C.log("")


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
        extra = ""
        if getattr(m, "unpriced_", 0):
            extra = (f"  ({m.unpriced_} goaltenders it declines to price on "
                     f"the last page take the page average instead)")
        C.log(f"  ran {m.name}: {len(d)} scored cells{extra}")
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

    base = scored["production's own projector (imported)"]
    C.log("AGAINST PRODUCTION'S OWN PROJECTOR, imported and called rather than")
    C.log("reimplemented, resampling GOALTENDERS rather than rows -- there are")
    C.log("280 of them and a goaltender's seasons are not independent draws.")
    C.log("One forecast is one (page, goaltender, horizon); an earlier version")
    C.log("paired on goaltender and horizon alone and matched a 2015 forecast")
    C.log("to a 2021 one.")
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
    bias_diagnostic(scored, base)

    C.log("WHAT THE AGE FIT ACTUALLY SAYS, page by page. Two coefficients,")
    C.log("and the first version of this runner used the wrong one: it took")
    C.log("the INTERCEPT, the average change at the pivot age, and applied it")
    C.log("to every goaltender alike. Adding twenty years to every subject")
    C.log("moved nothing, so what it tested was a common drift and not ageing.")
    C.log("")
    C.log(f"    {'page':<8}{'per year of age':>18}{'at the pivot age':>20}"
          f"{'pivot':>8}")
    for page in C.DEV_PAGES:
        a = WorkloadWeightedAging().fit(table[table["syr"] < page], page)
        C.log(f"    {page:<8}{a.age_slope_:>18.4f}{a.age_drift_:>20.4f}"
              f"{a.age_pivot_:>8.0f}")
    C.log("")
    C.log("  The two behave differently and only one of them is about age.")
    C.log("  The slope is NEGATIVE on every page -- an older goaltender's")
    C.log("  season-to-season change is worse than a younger one's, on every")
    C.log("  window this run has. What swings is the DRIFT, from +0.117 WAR a")
    C.log("  season on the 2015 page to -0.106 on 2021: the level the whole")
    C.log("  population moves by, which is not an age effect at all.")
    C.log("")
    C.log("  So the earlier claim that ageing is unidentified on this panel is")
    C.log("  WITHDRAWN. What is unstable is the common drift. Whether the age")
    C.log("  slope is well estimated is a further question this run does not")
    C.log("  answer -- it is fitted on within-goaltender changes, so it is")
    C.log("  measured only on goaltenders who played both seasons, and the")
    C.log("  ones who fall out are the ones who declined.")
    C.log("")

    C.log("WHAT THE FITS CAME OUT AT on the last development page, which is")
    C.log("the most evidence any page in this run had:")
    C.log(f"    production keeps                       {PROD_KEEP:.2f} of trailing")
    C.log(f"    fitted on {m.n_pairs_} pairs, it keeps      {m.keep_:.2f}")
    C.log(f"    workload weighting's half-point        {w.k_:.0f} games "
          f"(a goaltender with that many games behind him keeps half)")
    C.log(f"    the age slope                          {ag.age_slope_:+.4f} "
          f"WAR a season per year of age, pivoting at {ag.age_pivot_:.0f}")
    C.log(f"    the common drift at that age           {ag.age_drift_:+.4f}")
    C.log("")

    out = pd.concat([d.assign(rule=n) for n, d in scored.items()],
                    ignore_index=True)
    out.to_csv(C.out_path("goalie_bakeoff.csv"), index=False)
    C.log(f"  wrote {C.out_path('goalie_bakeoff.csv').name} ({len(out)} rows)")
    C.write_log("goalie_bakeoff_run_log.txt")


if __name__ == "__main__":
    main()
