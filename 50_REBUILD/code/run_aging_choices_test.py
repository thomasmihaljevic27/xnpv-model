"""run_aging_choices_test.py -- hand-set aging choices, both models, one harness.

EXPERIMENTAL (50_REBUILD). Development pages 2015-2021 only. Nothing is
adopted by this run and no production file is edited.

WHAT IS SCORED
    A supervisor walkthrough of the CURRENT aging curve (20_CODE/aging_curve.py,
    2026-09-28) listed choices made without a stated reason. The rebuilt model
    has no comparables, yardstick or pooled weight, so most of those questions
    do not apply to it, and it already refits its curve at each decision date.
    It has hand-set choices of its own that no earlier run scored. This runner
    puts both sets on the SAME harness rows and the SAME realised target.

    THE REBUILT MODEL'S AGING CURVE (aging_additive.py), one change each:
      quadratic / quartic    the age polynomial (recorded: cubic)
      clamp_20_38 / 18_40    the age band beyond which the step is held at the
                             edge (recorded: 19-39)
      equal_pair_weight      every season pair counts once (recorded: each
                             weighted by the smaller of its two seasons' games)
    Not scored, and why: the age centring (27) cannot change a fit that has
    every power of age and the level-by-age term together, which is a change
    of basis; the level terms, the survivorship imputation, the imputed level,
    and recency weighting were each scored in earlier runs; MIN_GP = 20 is the
    whole chain's qualifying rule, not an aging choice.

    Carried by `A1HingeExposure`, the adopted leader without contract data.
    The adopted leader (`A1HingeExposureStatus`) differs ONLY in participation,
    which reads the confidential contract export; its ability, aging, rate and
    games share are identical (its docstring). This container has no contract
    export, so the no-contract twin carries the aging change, and every rebuilt
    arm shares its participation exactly.

    THE CURRENT MODEL, run as the live chain (`production_adapter.ProductionChain`:
    the locked aging path and survival), one change each to its aging curve:
      pre_valuation_pool     the curve refitted on each page from seasons that
                             had finished before the page (question 5). This
                             moves the comparables, the z-score means and SDs,
                             the yardstick and the league-average curves
                             together, because production builds all four from
                             the whole file.
      yard_by_position       a separate yardstick for forwards and defence (3)
      yard_all_pairs         the yardstick from every pair, not a sample (1)
      share_5pct             the league average takes a fixed 5% share instead
                             of 10 comparable-weight units (6)
      kernel_flat            every same-age, same-position comparable weight 1 (4)
      ep_pool                (v1.1) the curve fitted on the age table with
                             age_join.py's Elite Prospects pass applied
                             (built by 20_CODE/aging_ep_pool_test.py); the
                             live table has none, so about 1,276 older careers
                             are missing from the pool
      ep_pool_pre_valuation  (v1.1) both: that table, and the pool limited to
                             seasons finished before the page
    The exit-hazard table the chain multiplies by is production's own and is
    NOT refitted by the pre-valuation arm; that arm fixes the aging curve's
    look-ahead only.

    Where production has no anchor, ProductionChain carries the trailing total
    flat and tags the row `outside_production`. Scores are reported on the
    full grid AND on the rows production answers, same rows for every arm.

THE SCORES, DECLARED BEFORE THE RUN
    Season WAR (rate x games share x participation, the harness's integration
    rule), horizons 0-5: squared error primary, absolute error and bias
    beside it. The rate per 82 among seasons played, which is where an aging
    change acts, beside that. The three-win-and-up tier's WAR bias by horizon.
    Every comparison is paired on identical rows; the share of 2,000
    player-resamples in which the arm's error is lower prints as a count.

GUARDS
    * every arm is scored on byte-identical harness rows (asserted);
    * the rebuilt arms at their defaults fit coefficients identical to the
      unmodified curve AND to the committed aging_additive.py, on every page;
    * degree and clamp arms fit exactly the recorded rows and weights (the
      check-46 fingerprint); the equal-weight arm the same rows, new weights;
    * the current-chain wrapper with no change reproduces ProductionChain's
      forecasts exactly on every page, and its variant aging model at defaults
      reproduces AgingModel.project on every forecast;
    * the recomputed yardstick equals AgingModel.h exactly.

AGES. Both models read ages from one birthdate table. Where this tree's merged
table (output/birthdates.csv, PuckPedia with the Elite Prospects scrape) is
absent, the birthdates are taken from production's own join,
30_OUTPUT/WAR_with_age.csv, so the two models age every player identically.
The label is printed.
"""
from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table, birthdate_source
from ability_forecast import A1HingeExposure
from aging_additive import AdditiveAging
import production_adapter as PA
from run_skater_contract_test import Boot, _count

SCRIPT_VERSION = "1.2"
HORIZONS = (0, 1, 2, 3, 4, 5)
STAR = "3+"

# ---------------------------------------------------------------------------
# THE REBUILT MODEL'S ARMS
# ---------------------------------------------------------------------------
class _AgingChoice:
    """Refit the aging curve with extra options, everything else untouched."""
    AGING_KW: dict = {}

    def fit(self, table, before):
        super().fit(table, before)
        self.aging_ = AdditiveAging(level_mode=self.AGING_LEVEL_MODE,
                                    selection=self.AGING_SELECTION,
                                    sample=self.AGING_SAMPLE,
                                    level_knot=self.AGING_LEVEL_KNOT,
                                    sustained=self.AGING_SUSTAINED,
                                    recency_halflife=self.AGING_RECENCY_HALFLIFE,
                                    **self.AGING_KW).fit(table, before)
        return self


def _rebuilt(tag, label, **kw):
    return type(f"Rebuilt_{tag}", (_AgingChoice, A1HingeExposure),
                {"name": f"rebuilt, {label}", "AGING_KW": kw})


REBUILT = {
    "rebuilt":           A1HingeExposure,
    "quadratic":         _rebuilt("quadratic", "age curve quadratic", degree=2),
    "quartic":           _rebuilt("quartic", "age curve quartic", degree=4),
    "clamp_20_38":       _rebuilt("clamp_20_38", "age band 20-38", age_lo=20.0, age_hi=38.0),
    "clamp_18_40":       _rebuilt("clamp_18_40", "age band 18-40", age_lo=18.0, age_hi=40.0),
    "equal_pair_weight": _rebuilt("equal_pw", "every season pair weighted equally",
                                  pair_weight="equal"),
}
_DEFAULTS = _rebuilt("defaults", "all options at their defaults")
SAME_ROWS_AND_WEIGHTS = ("quadratic", "quartic", "clamp_20_38", "clamp_18_40")


def _committed_aging():
    """aging_additive.py as committed at HEAD, so the new options can be shown
    to change nothing at their defaults (not just against themselves)."""
    src = subprocess.run(["git", "show", "HEAD:50_REBUILD/code/aging_additive.py"],
                         cwd=C.REPO_ROOT, capture_output=True, text=True, check=True).stdout
    tmp = Path(tempfile.mkdtemp()) / "aging_additive_head.py"
    tmp.write_text(src)
    spec = importlib.util.spec_from_file_location("aging_additive_head", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def guard_rebuilt(table) -> None:
    """Defaults reproduce the recorded curve; arms change only what they name.

    The leader is fitted once per page to read its own curve; each arm's curve
    is then fitted directly with the leader's aging settings plus the arm's
    options. One page also fits every arm through its model class, to show the
    class path builds the same curve as the direct one."""
    import information_set as ISET
    head = _committed_aging()
    base_kw = lambda m: dict(level_mode=m.AGING_LEVEL_MODE, selection=m.AGING_SELECTION,
                             sample=m.AGING_SAMPLE, level_knot=m.AGING_LEVEL_KNOT,
                             sustained=m.AGING_SUSTAINED, recency_halflife=m.AGING_RECENCY_HALFLIFE)
    moved = {}
    for page in C.DEV_PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
        ref = A1HingeExposure(); ref.fit(iset.seasons, before=page)
        kw = base_kw(ref)
        old = head.AdditiveAging(**kw).fit(iset.seasons, page)
        assert np.array_equal(ref.aging_.coef_, old.coef_), f"curve differs from the committed file, page {page}"
        arms = {k: AdditiveAging(**kw, **cls.AGING_KW).fit(iset.seasons, page)
                for k, cls in REBUILT.items() if k != "rebuilt"}
        dft = AdditiveAging(**kw, **_DEFAULTS.AGING_KW).fit(iset.seasons, page)
        assert np.array_equal(ref.aging_.coef_, dft.coef_), f"defaults moved the curve, page {page}"
        ages = np.arange(18, 42, dtype=float)       # includes the ages a clamp holds
        for k in SAME_ROWS_AND_WEIGHTS:
            assert arms[k].fit_key_ == ref.aging_.fit_key_, f"{k} changed rows or weights, page {page}"
        for k, a in arms.items():
            # A clamp moves nothing on a page with no training row outside
            # the new band, so this is counted, not asserted.
            for lv in (0.5, 3.0):
                moved[k] = moved.get(k, 0) + int(not np.allclose(
                    a.step(ages, np.full(len(ages), lv), np.zeros(len(ages))),
                    ref.aging_.step(ages, np.full(len(ages), lv), np.zeros(len(ages))),
                    rtol=0, atol=1e-12))
        e = arms["equal_pair_weight"]
        assert e.rows_key_ == ref.aging_.rows_key_, f"equal weights changed the rows, page {page}"
        assert e.fit_key_ != ref.aging_.fit_key_, "equal weights did not change the weights"
        assert np.allclose(e.fit_rows_["w"], 1.0), "equal weights are not all one"
        if page == C.DEV_PAGES[-1]:
            for k, cls in {**{k: v for k, v in REBUILT.items() if k != "rebuilt"},
                           "defaults": _DEFAULTS}.items():
                m = cls(); m.fit(iset.seasons, before=page)
                want = dft if k == "defaults" else arms[k]
                assert np.array_equal(m.aging_.coef_, want.coef_), f"{k}: class path differs"
    C.log(f"  guard: rebuilt defaults identical to the committed curve on {len(C.DEV_PAGES)} pages; "
          "degree and clamp arms on the recorded rows and weights; equal weights on the same rows")
    C.log("  curve moved by each arm (pages x two levels, of " + str(2 * len(C.DEV_PAGES)) + "): "
          + ", ".join(f"{k} {v}" for k, v in moved.items()))


# ---------------------------------------------------------------------------
# THE CURRENT MODEL'S ARMS
# ---------------------------------------------------------------------------
def _variant_aging_class():
    """AgingModel with the arm's yardstick and blend. Built lazily because the
    production modules need .env set before import."""
    PA._production()
    import aging_curve as AC
    from aging_arbitrary_choices_test import yardsticks

    class VariantAging(AC.AgingModel):
        def __init__(self, path, yard="prod", share=None, kernel="gauss"):
            self._yard, self._share, self._kernel = yard, share, kernel
            super().__init__(path)
            y = yardsticks(self, self.Zw, want_all=(yard == "all_pairs"))
            assert y["prod"] == self.h, "recomputed yardstick differs from AgingModel.h"
            self.h_by_pos = (y["by_position"] if yard == "by_position" else
                             {p: (y["all_pairs"] if yard == "all_pairs" else self.h)
                              for p in np.unique(self.pos)})
            self.yard_info = y

        def _weights(self, target_z, pos, age, exclude=None):
            cand = self.by_age.get(age, np.array([], int))
            cand = cand[self.pos[cand] == pos] if len(cand) else cand
            if len(cand) == 0:
                return cand, None
            d2 = ((self.Zw[cand] - target_z) ** 2).sum(1)
            h = self.h_by_pos[pos]
            w = np.ones_like(d2) if self._kernel == "flat" else np.exp(-d2 / (2 * h ** 2))
            if exclude is not None:
                w[self.names[cand] == exclude] = 0.0
            return cand, w

        def _shrunk(self, vals_col, cand, w, glob_target):
            if self._share is None:
                return super()._shrunk(vals_col, cand, w, glob_target)
            m = ~np.isnan(vals_col); ww = w * m; sw = ww.sum()
            if sw <= 0:
                return glob_target
            s = self._share
            return (1 - s) * np.nansum(ww * np.where(m, vals_col, 0.0)) / sw + s * glob_target

    return VariantAging


class CurrentChain(PA.ProductionChain):
    """The live chain with a variant aging curve swapped into its projector.
    Everything else -- anchor, D3 decay path, multiplier, hazard -- is
    production's own object, shared with ProductionChain through its cache."""
    AGING: dict = {}
    PER_PAGE = False
    # v1.1: an alternative age table in OUTPUT_DIR for the curve (None: the
    # live WAR_with_age.csv). The harness subjects' ages are unchanged.
    AGE_FILE = None
    _curves: dict = {}

    def _curve(self, before):
        SFP = sys.modules["skater_forward_projection"]
        VA = _variant_aging_class()
        key = (type(self).__name__, before if self.PER_PAGE else None)
        if key not in self._curves:
            path = SFP.F_WAR_AGE if self.AGE_FILE is None else Path(C.PROD_OUTPUT_DIR) / self.AGE_FILE
            assert Path(path).exists(), f"{path} is missing; run 20_CODE/aging_ep_pool_test.py first"
            if self.PER_PAGE:
                wa = pd.read_csv(path)
                syr = wa["Season"].str.split("-").str[0].astype(int) + 2000
                tmp = Path(tempfile.mkdtemp()) / "war_with_age_pre.csv"
                wa[syr < before].to_csv(tmp, index=False)   # seasons finished before the page
                path = tmp
            self._curves[key] = VA(str(path), **self.AGING)
        return self._curves[key]

    def fit(self, table, before):
        super().fit(table, before)
        proj = copy.copy(self.proj_)
        # v1.2: production's projector (v1.4) asks curve_for(t0) for the page's
        # curve; the wrapper answers with its own for this page.
        curve = self._curve(before)
        proj._curves = {}
        proj.curve_for = lambda t0, _c=curve: _c
        proj.last_ratio_floored = []
        self.proj_ = proj


def _current(tag, label, per_page=False, age_file=None, **aging):
    return type(f"Current_{tag}", (CurrentChain,),
                {"name": f"current, {label}", "AGING": aging, "PER_PAGE": per_page,
                 "AGE_FILE": age_file})


# v1.1 (2026-09-28): the age table with age_join.py's Elite Prospects pass
# applied, built by 20_CODE/aging_ep_pool_test.py. The live table has none,
# because age_join.py reads the scrape from OUTPUT_DIR/ep_out/ and the file
# sits in 10_SOURCE/ (1,278 of 3,199 skaters without an age).
EP_TABLE = "aging_ep_pool_test_war_with_age.csv"


# v1.2 (2026-09-28): production adopted the pre-valuation curve (D3 revision,
# SkaterProjector v1.4), so ProductionChain IS the pre-valuation chain and the
# former reference, the whole-file chain, is the arm "full_era_pool". The
# hand-set arms stay whole-file, as recorded in v1.0-v1.1, and are scored
# against it.
CURRENT = {
    "full_era_pool":      _current("full_era", "aging curve fitted on the whole file (pre-revision)"),
    "pre_valuation_pool": _current("pre_pool", "aging pool from seasons before the page", per_page=True),
    "yard_by_position":   _current("yard_pos", "a yardstick per position", yard="by_position"),
    "yard_all_pairs":     _current("yard_all", "yardstick from every pair", yard="all_pairs"),
    "share_5pct":         _current("share5", "league average a fixed 5% share", share=0.05),
    "kernel_flat":        _current("flat", "every comparable weight 1", kernel="flat"),
    "ep_pool":            _current("ep_pool", "older careers added to the aging pool", age_file=EP_TABLE),
    "ep_pool_pre_valuation": _current("ep_pre", "older careers added, pool from seasons before the page",
                                      per_page=True, age_file=EP_TABLE),
}
_CURRENT_DEFAULTS = _current("defaults", "wrapper, no change", per_page=True)


def guard_current(har) -> pd.DataFrame:
    """The wrapper with no change reproduces ProductionChain exactly. Returns
    ProductionChain's scored run, reused as the 'current' arm."""
    a = har.run(PA.ProductionChain(), pages=C.DEV_PAGES, horizons=HORIZONS)
    b = har.run(_CURRENT_DEFAULTS(), pages=C.DEV_PAGES, horizons=HORIZONS)
    key = ["career_key", "page", "h"]
    a, b = a.set_index(key).sort_index(), b.set_index(key).sort_index()
    assert a.index.equals(b.index), "the wrapper answered different rows"
    for c in ("rate_82", "p_play", "gp_share"):
        assert np.array_equal(a[c].to_numpy(), b[c].to_numpy()), f"the wrapper moved {c}"
    C.log(f"  guard: the current-chain wrapper reproduces ProductionChain exactly on {len(a)} forecasts")
    return a.reset_index()


# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------
def scores(runs: dict, ref: str, label: str, mask=None) -> pd.DataFrame:
    keys = ["career_key", "page", "h"]
    lead = runs[ref].set_index(keys)
    al = {}
    for k, d in runs.items():
        x = d.set_index(keys).reindex(lead.index)
        assert x.index.equals(lead.index) and x["e_war"].notna().all(), f"{k} rows differ"
        assert np.array_equal(x["act_war"].to_numpy(), lead["act_war"].to_numpy()), f"{k} target differs"
        al[k] = x.reset_index()
    # mask: a function of the REFERENCE run's rows, evaluated in its own order
    sel = np.ones(len(lead), bool) if mask is None else np.asarray(mask(lead.reset_index()), bool)
    base = al[ref][sel]
    boot = Boot(base["career_key"])
    out = []
    C.log(f"  {label}: {int(sel.sum())} forecasts, {base['career_key'].nunique()} players")
    C.log(f"    {'arm':<20}{'WAR RMSE':>10}{'lower':>11}{'WAR MAE':>9}{'lower':>11}{'bias':>8}"
          f"{'rate MAE':>10}{'lower':>11}")
    for k, d in al.items():
        d = d[sel]
        se, ae = d["e_war"] ** 2, d["e_war"].abs()
        pl = d["played"].astype(bool).to_numpy()
        re_ = d["e_rate"].abs().where(pl, 0.0)
        lower = lambda a_ref, a: "--" if k == ref else _count(boot.lower_share(a_ref, a))
        # rate error is defined on played seasons only; played rows are the same
        # for every arm (one target), so a per-player sum over them is paired
        r_ref = base["e_rate"].abs().where(pl, 0.0)
        row = dict(sample=label, arm=k, n=int(sel.sum()),
                   rmse=float(np.sqrt(se.mean())), mae=float(ae.mean()), bias=float(d["e_war"].mean()),
                   rate_mae=float(d.loc[pl, "e_rate"].abs().mean()))
        C.log(f"    {k:<20}{row['rmse']:>10.4f}{lower(base['e_war'] ** 2, se):>11}"
              f"{row['mae']:>9.4f}{lower(base['e_war'].abs(), ae):>11}{row['bias']:>+8.4f}"
              f"{row['rate_mae']:>10.4f}{lower(r_ref, re_):>11}")
        out.append(row)
    C.log("")
    C.log(f"    season WAR RMSE by seasons ahead ({label}):")
    C.log("    " + f"{'arm':<20}" + "".join(f"{'h' + str(h):>9}" for h in HORIZONS))
    for k, d in al.items():
        d = d[sel]
        C.log("    " + f"{k:<20}" + "".join(
            f"{np.sqrt((d.loc[d['h'] == h, 'e_war'] ** 2).mean()):>9.4f}" for h in HORIZONS))
    C.log("")
    C.log(f"    three-win-and-up tier, season WAR bias by seasons ahead ({label}):")
    C.log("    " + f"{'arm':<20}" + "".join(f"{'h' + str(h):>9}" for h in HORIZONS))
    for k, d in al.items():
        d = d[sel]
        C.log("    " + f"{k:<20}" + "".join(
            f"{d.loc[(d['h'] == h) & (d['tier'] == STAR), 'e_war'].mean():>+9.3f}" for h in HORIZONS))
    C.log("")
    return pd.DataFrame(out)


def _birthdates() -> tuple[Path, str]:
    """One birthdate table for both models.

    This tree's merged table (output/birthdates.csv) is used when present.
    Otherwise it is rebuilt by the same rule contract_source.birthdate_table
    applies: a primary source, then the Elite Prospects scrape for keys the
    primary lacks, keyed on cleaned name + position (pkey). The primary here is
    production's own join (30_OUTPUT/WAR_with_age.csv), so wherever production
    has a birthdate both models use the same one."""
    path, how = birthdate_source()
    if path is not None and path.name == "birthdates.csv":
        return path, how
    from player_season_table import norm_name
    prod_age = Path(C.PROD_OUTPUT_DIR) / "WAR_with_age.csv"
    if not prod_age.exists():
        raise RuntimeError(f"no merged birthdate table and no {prod_age}; cannot age players")
    wa = pd.read_csv(prod_age, usecols=["Player", "Position", "birthdate"]).dropna(subset=["birthdate"])
    wa["pkey"] = wa["Player"].map(norm_name) + "|" + wa["Position"].astype(str)
    wa["birthdate"] = pd.to_datetime(wa["birthdate"], format="mixed").dt.strftime("%Y-%m-%d")
    prim = wa[["pkey", "birthdate"]].drop_duplicates()
    parts, n_ep = [prim], 0
    ep_path = C.SOURCE_DIR / "ep_birthdates.csv"
    if ep_path.exists():
        ep = pd.read_csv(ep_path).dropna(subset=["birthdate"])
        ep["pkey"] = ep["war_name"].map(norm_name) + "|" + ep["war_position"].astype(str)
        fresh = ep.loc[~ep["pkey"].isin(set(prim["pkey"])), ["pkey", "birthdate"]].drop_duplicates()
        parts.append(fresh); n_ep = len(fresh)
    bd = pd.concat(parts, ignore_index=True)
    out = C.out_path("aging_choices_birthdates.csv")
    bd.to_csv(out, index=False)
    return out, (f"production's own join (30_OUTPUT/WAR_with_age.csv, {len(prim)} keys) as primary, "
                 f"then the Elite Prospects scrape for {n_ep} keys it lacks "
                 "(the rule contract_source.birthdate_table applies)")


def main() -> None:
    C.banner("run_aging_choices_test.py", SCRIPT_VERSION)
    path, how = _birthdates()
    C.log(f"  birthdates: {how}")
    table = build_table(birthdate_csv=path, verbose=True)
    C.log("")
    guard_rebuilt(table)
    har = H.Harness(table)
    runs = {"current": guard_current(har)}
    C.log("")
    for k, cls in {**REBUILT, **CURRENT}.items():
        if k in runs:
            continue
        runs[k] = har.run(cls(), pages=C.DEV_PAGES, horizons=HORIZONS)
        C.log(f"  ran {k}: {len(runs[k])} forecasts")
    C.log("")
    cur = CurrentChain._curves
    for key, m in cur.items():
        if key[1] is None:
            C.log(f"  current-model yardstick, {key[0]}: pooled {m.yard_info['prod']:.4f}, "
                  + ", ".join(f"{p} {v:.4f}" for p, v in m.yard_info['by_position'].items())
                  + (f", all pairs {m.yard_info['all_pairs']:.4f}" if 'all_pairs' in m.yard_info else ""))
    C.log("")

    C.log("THE REBUILT MODEL'S AGING CHOICES (reference: rebuilt, the adopted leader without contracts)")
    s1 = scores({k: runs[k] for k in REBUILT}, "rebuilt", "full grid")
    # v1.2 GUARD: production as adopted reproduces the pre-valuation arm scored
    # before adoption, on every forecast.
    key = ["career_key", "page", "h"]
    a = runs["current"].set_index(key).sort_index()
    b = runs["pre_valuation_pool"].set_index(key).sort_index()
    assert a.index.equals(b.index)
    gap = {c: float(np.abs(a[c].to_numpy() - b[c].to_numpy()).max()) for c in ("rate_82", "p_play")}
    assert all(v <= 1e-12 for v in gap.values()), f"adopted production differs from the tested arm: {gap}"
    C.log(f"  guard: adopted production equals the pre-valuation arm on {len(a)} forecasts "
          f"(largest gap {max(gap.values()):.1e})")
    C.log("")
    C.log("THE CURRENT MODEL'S AGING CHOICES (reference: full_era_pool, the pre-revision chain)")
    answer = lambda d: d["outside_production"].eq(0)
    arms = {k: runs[k] for k in CURRENT}
    s2 = scores(arms, "full_era_pool", "full grid (production plus its fallback)")
    s3 = scores(arms, "full_era_pool", "rows production answers", mask=answer)
    C.log("BOTH MODELS ON ONE TARGET (reference: current, production as adopted 2026-09-28)")
    s4 = scores({"current": runs["current"], "full_era_pool": runs["full_era_pool"],
                 "ep_pool_pre_valuation": runs["ep_pool_pre_valuation"],
                 "rebuilt": runs["rebuilt"]}, "current", "rows production answers", mask=answer)

    pd.concat([s1, s2, s3, s4.assign(sample="cross-model, rows production answers")]).to_csv(
        C.out_path("aging_choices_summary.csv"), index=False)
    pd.concat([d.assign(arm=k) for k, d in runs.items()], ignore_index=True).to_csv(
        C.out_path("aging_choices_forecasts.csv"), index=False)
    C.write_log("aging_choices_run_log.txt")


if __name__ == "__main__":
    main()
