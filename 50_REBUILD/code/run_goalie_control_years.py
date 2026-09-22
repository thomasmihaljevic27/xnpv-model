"""run_goalie_control_years.py -- a goaltender's control years, and his contract in dollars.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the goalie branch, fifth
step. Development start years only; the reserved cohorts are refused by the
guard. Nothing adopted, and no production file is written.

WHAT IT ANSWERS
    1. What a goaltender's control years are worth -- the seasons a club still
       holds his rights for after the contract, kept by qualifying offer --
       under the six stopping rules the skater run uses.
    2. What his contract is worth as a distribution of dollars, not only as
       the price of an expected season.
    3. Whether those expected dollars are any good: scored against the dollars
       the goaltender actually delivered, on contracts whose term has ended.

    Each is run on TWO goalie forecasts, declared before any number was read:
      production   production's season total, the participation model and his
                   trailing share -- the DEFAULT (decided 2026-09-22);
      rate         the per-82 rate, the share model and the participation
                   model -- the SENSITIVITY.

HOW THE SCORES ARE READ, DECLARED IN ADVANCE
    The target is expected dollars, so squared dollar error is the primary
    score of a valuation against what happened; mean absolute error and bias
    are reported beside it, and the coverage of the simulated 10-90% band says
    whether the spread is right. A lower WAR error is not assumed to carry
    through: the league-minimum floor and the control options make dollars a
    bent function of the path.

WHAT IS REUSED, NOT COPIED
    * The control-year machinery: `run_control_years.price_span` (draws,
      calibration, dependence, the six rules, the leakage check) and
      `rule_guards` (nothing beats hindsight).
    * The forecast band: `run_npv_simulation.forecast_blocks`, handed the goalie
      arm and the goalie panel, so the interval replay, the residual shape and
      the dependence fit are the skater routine's own.
    * The price line: the pooled line with the goaltender LEVEL, the
      specification that earned its place (`run_goalie_price_line`), fitted by
      that runner's `fit_rolling` at each signing quarter.
    * The point forecast: `run_goalie_price_line.goalie_forecasts`, with
      participation read at the signing. The simulated forecast's expected
      season must reproduce it contract by contract, which is asserted: the
      forecast simulated is the forecast priced.

THE PRICE LINE, FOLDED
    Every goaltender row has is_G = 1, so the level adds to the intercept and
    the pooled line is an ordinary line over the shared skater features. The
    folded line is exactly the pooled line on every goaltender row (asserted),
    and it is what lets `ProductionCurrency.value`, `control_years.season_share`
    and `npv_simulation.contract_value` price a goaltender unchanged.

REALISED DOLLARS, AND WHAT THEY ARE
    The same signing-dated price line applied to the WAR he actually produced
    in each term season, a season he did not play counting as zero: what the
    market that signed him would have paid for the production he delivered.
    It inherits the currency's circularity (the line is fitted to contracts),
    so it scores valuations against each other on one scale and is not an
    absolute measure of value. Only terms that have ended are scored, and the
    realised seasons are read only here, never by a rule or a forecast.

GOALTENDER-SPECIFIC LIMITS, STATED
    * Beyond five seasons out every goalie forecast holds the last fitted
      horizon (production's own flat carry); the skater side continues the
      decay.
    * Eligibility comes from the export's own year. Besides accrued seasons,
      the CBA's Group VI route (age 25, three professional seasons, few NHL
      games) can make a goaltender unrestricted before 27, and its games
      threshold is one backups can miss. The eligibility audit counts how much
      of the priced sample goes early. The skater run's age-rule sensitivity is
      not repeated: it would add control years to exactly the goaltenders the
      early routes release, and on this sample it is a small count.
    * The qualifying offer runs off the average annual value, the same
      approximation the skater run states.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import control_years as CY
import npv_simulation as SIM
import goalie_season_table as GST
import run_control_years as RCY
import run_npv_simulation as RNS
import run_goalie_price_line as PL
import run_goalie_rate as GR
from contract_price_model import contract_sample, attach_forecasts
from player_season_table import birthdate_source, build as build_skater_table
from production_currency import ProductionCurrency, FEATURES

SCRIPT_VERSION = "1.0"
KEY = RCY.KEY

# The two forecasts, declared before the run: the label, the harness arm the
# band is built on, and the `ability` the point forecast is priced with. The
# arm and the ability must be the same forecast; the parity assertion below
# enforces it.
FORECASTS = (("production", GR.ProdTrail, "production"),
             ("rate", GR.FlatShare, "rate"))


class GoalieCurrency(ProductionCurrency):
    """The pooled price line with the goaltender level, folded for goaltenders.

    Fitted by `run_goalie_price_line.fit_rolling` on skaters and goaltenders
    signed before the decision date, with the level-only specification. On a
    goaltender row is_G is 1, so the fitted line is intercept + level + the
    shared terms; the folded coefficient vector carries intercept + level in
    the intercept's place and is an ordinary line over FEATURES.
    """

    def fit(self, d: pd.DataFrame, before_date=None):
        coef, n = PL.fit_rolling(d, PL.LEVEL_ONLY, before_date)
        if coef is None:
            return self
        assert PL.LEVEL_ONLY[:-1] == FEATURES and PL.LEVEL_ONLY[-1] == "is_G"
        self.pooled_coef_ = coef
        self.g_level_ = float(coef[-1])
        self.coef_ = np.concatenate([[coef[0] + coef[-1]], coef[1:-1]])
        self.n_fit_ = n
        # THE FOLD IS EXACT on goaltender rows, asserted on the rows themselves.
        g = d[d["is_G"] == 1.0]
        if len(g):
            from contract_price_model import predict_tobit
            a = predict_tobit(coef, g[PL.LEVEL_ONLY].to_numpy(float))
            b = predict_tobit(self.coef_, g[FEATURES].to_numpy(float))
            assert np.allclose(a, b, atol=1e-12), "the folded line is not the pooled line"
        return self


def point_valuation(sk: pd.DataFrame, go: pd.DataFrame):
    """Each goaltender contract priced on the line in force at its signing
    quarter: value, cost, surplus. Returns the priced rows and the lines."""
    d = PL.prep_pooled(sk, go)
    d["cut"] = d["signed"].dt.to_period("Q").dt.start_time
    priced, lines = [], {}
    gd = d[(d["is_G"] == 1.0) & (d["signed"] >= pd.Timestamp("2015-07-01"))]
    for cut, te in gd.groupby("cut"):
        cur = GoalieCurrency("in").fit(d, before_date=cut)
        if cur.coef_ is None:
            continue
        lines[cut] = cur
        te = te.copy()
        te["value_point"] = cur.value(te)
        te["cost"] = cur.cost(te)
        priced.append(te)
    pt = pd.concat(priced, ignore_index=True).drop_duplicates(KEY)
    pt["surplus_point"] = pt["value_point"] - pt["cost"]
    return pt, lines


def goalie_blocks(sample: pd.DataFrame, table: pd.DataFrame, arm, span: dict):
    """The band over the term and the control years, from the goalie arm, with
    the chance he plays each season read at the SIGNING -- the same dating the
    point forecast uses, so the two describe one forecast."""
    def wanted(r):
        return RNS.term_seasons(r) + span.get(int(r.contract_id), [])

    blocks, spreads = RNS.forecast_blocks(sample, table, seasons_for=wanted,
                                          model_factory=arm)
    for L, grp in sample.groupby("latest_complete"):
        t0 = int(L) + 1
        grp = grp[grp[KEY].isin(list(blocks))]
        if grp.empty:
            continue
        pfun = PL.participation_at_page(table, t0)
        for r in grp.itertuples():
            page, mu, sg, pp, yrs = blocks[r.contract_id]
            assert page == t0
            hs = [int(y - t0) for y in yrs]
            p_sign = np.array([float(pfun([r.pkey], h, [pd.Timestamp(r.signed)])[0])
                               for h in hs])
            blocks[r.contract_id] = (page, mu, sg, p_sign, yrs)
    return blocks, spreads


def forecast_parity(pt: pd.DataFrame, blocks: dict) -> tuple[int, float]:
    """THE FORECAST SIMULATED IS THE FORECAST PRICED. The band's expected
    season over the term, mu x p averaged, must equal the point forecast's
    war_per_season, contract by contract."""
    worst, n = 0.0, 0
    for r in pt.itertuples():
        if r.contract_id not in blocks:
            continue
        _, mu, _, pp, yrs = blocks[r.contract_id]
        L = int(r.length)
        got = float(np.mean(mu[:L] * pp[:L]))
        worst = max(worst, abs(got - float(r.war_per_season)))
        n += 1
    assert worst < 1e-9, (
        f"the simulated forecast's expected season differs from the priced one "
        f"by up to {worst:.4f} WAR")
    return n, worst


def eligibility_audit(sample: pd.DataFrame, pt: pd.DataFrame, cmap: dict) -> None:
    """Where the goaltenders' eligibility year comes from. Counts only: the
    skater audit's wording promises an age-rule rerun, which this runner does
    not do, so it is not borrowed."""
    d = sample[sample[KEY].isin(pt[KEY])].copy()
    by_age = np.array([CY.ufa_year_by_age(b) for b in d["birthdate"]])
    gap = pd.to_numeric(d["ufa_year"], errors="coerce").to_numpy() - by_age
    C.log("WHERE ELIGIBILITY COMES FROM, on the priced goaltender contracts:")
    C.log(f"    the export agrees with the age-27 rule         {int((gap == 0).sum()):>5}")
    C.log(f"    earlier than the age rule                      {int((gap < 0).sum()):>5}"
          "   (accrued seasons, or Group VI)")
    C.log(f"    later than the age rule                        {int((gap > 0).sum()):>5}")
    C.log(f"    no birthdate                                   {int(np.isnan(by_age).sum()):>5}")
    C.log("  The early route is part of what a club at the signing could not")
    C.log("  know for certain; the export's year is used as the skater run uses it.")
    C.log("")


def attrition(go_dev: pd.DataFrame, cmap: dict, pt: pd.DataFrame, blocks: dict,
              ok: pd.DataFrame) -> None:
    """How the contracts that own control years thin out before they are
    priced -- a selection, because the ones lost are the ones with the least
    NHL history."""
    own = set(int(c) for c in go_dev[KEY] if int(c) in cmap)
    signed = set(go_dev.loc[go_dev["signed"] >= pd.Timestamp("2015-07-01"), KEY]) & own
    priced = set(pt[KEY]) & own
    banded = set(blocks) & own
    sim = set(ok.loc[ok["n_ctrl"] > 0, KEY])
    C.log("  CONTRACTS THAT OWN CONTROL YEARS, stage by stage:")
    for lab, n in (("in the development census", own),
                   ("signed from July 2015", signed),
                   ("with a point forecast and a price", priced),
                   ("a harness subject at the page (a band)", banded),
                   ("simulated", sim)):
        C.log(f"    {lab:<44}{len(n):>5}")
    lost = go_dev[go_dev[KEY].isin(signed - banded)]
    kept = go_dev[go_dev[KEY].isin(sim)]
    C.log(f"  The ones lost are mostly goaltenders without a 10-game NHL season in")
    C.log(f"  the three before the signing -- prospects on their first deals. Mean")
    C.log(f"  cap hit ${lost['aav'].mean() / 1e6:.2f}M lost against "
          f"${kept['aav'].mean() / 1e6:.2f}M kept. The control values below are")
    C.log(f"  for goaltenders with an NHL record, not for the whole population")
    C.log(f"  that owns control years.")
    C.log("")


def realised_path(table: pd.DataFrame):
    """WAR by (pkey, season), a season he did not play counting as zero."""
    played = table[table["GP"] >= C.PARTICIPATION_GP]
    lut = played.groupby(["pkey", "syr"])["WAR"].sum()

    def f(pkey, yrs) -> np.ndarray:
        return np.array([float(lut.get((pkey, int(y)), 0.0)) for y in yrs])
    return f


def term_extra(pt_idx: pd.DataFrame, lines: dict):
    """The contract's own term priced on the drawn paths: its mean, its 10th
    and 90th percentiles, and the zero-spread identity."""
    def f(cid, r, paths) -> dict:
        L = int(r["length"])
        k = SIM.dollar_factor(r)
        cur = lines[r["cut"]]
        v = SIM.contract_value(cur, r, paths[:, :L].mean(axis=1), paths[:, 0], k)
        q10, q25, q75, q90 = np.percentile(v, [10, 25, 75, 90])
        return {"term_sim_mean": float(v.mean()), "term_sim_q10": float(q10),
                "term_sim_q25": float(q25), "term_sim_q75": float(q75),
                "term_sim_q90": float(q90), "term_sim_sd": float(v.std(ddof=1)),
                "cost": float(r["cost"]), "value_point": float(r["value_point"])}
    return f


def career_bootstrap(d: pd.DataFrame, a: str, b: str, n: int = 2000,
                     seed: int = 20260922) -> float:
    """Share of goaltender-resamples in which column b's mean is lower than
    column a's. Resamples goaltenders, since one signs several contracts."""
    g = {k: v for k, v in d.groupby("pkey")}
    ks = list(g)
    rng = np.random.default_rng(seed)
    wins = 0
    for _ in range(n):
        s = pd.concat([g[k] for k in rng.choice(ks, len(ks), replace=True)])
        wins += int(s[b].mean() < s[a].mean())
    return wins / n


def main() -> None:
    C.banner("run_goalie_control_years.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    C.log(f"  birthdates: {how}")
    sk_table = build_skater_table(birthdate_csv=path, verbose=False)
    g_table = GST.build(birthdate_csv=path, verbose=False, allow_thin_ages=True)

    sk_s = contract_sample(("F", "D"))
    go_s = contract_sample(("G",))
    sk = RNS.prep(attach_forecasts(sk_s, RNS.LEADER, sk_table, verbose=False))
    dev = [int(y) for y in sorted(sk["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_goalie_control_years")
    sk = sk[sk["start_yr"].isin(cohorts)].copy()
    go_dev = go_s[go_s["start_yr"].isin(cohorts)].copy()

    cmap = RCY.control_map(go_s)
    C.log(f"  {len(go_dev)} development goaltender contracts in the census; "
          f"{sum(int(c) in cmap for c in go_dev[KEY])} own control years on eligibility")
    C.log("")

    real = realised_path(g_table)
    results = {}
    for label, arm, ability in FORECASTS:
        C.log("=" * 74)
        C.log(f"FORECAST: {label} ({arm.name})")
        C.log("=" * 74)
        gf = PL.goalie_forecasts(go_s, g_table, participation="model",
                                 ability=ability)
        go = go_dev.merge(gf, on=KEY, how="inner")
        pt, lines = point_valuation(sk, go)
        if label == "production":
            eligibility_audit(go_s, pt, cmap)
        blocks, spreads = goalie_blocks(go_dev[go_dev[KEY].isin(pt[KEY])],
                                        g_table, arm, cmap)
        n_par, worst = forecast_parity(pt, blocks)
        C.log(f"  {len(pt)} goaltender contracts priced; {n_par} carry a band, and")
        C.log(f"  on every one the band's expected season equals the priced")
        C.log(f"  forecast (largest gap {worst:.1e} WAR)")
        C.log("")
        own = {c: v for c, v in cmap.items() if c in set(pt[KEY])}
        # Every priced contract is simulated over its term; the ones that own
        # control years carry them too. A contract without control years gets
        # an empty span, which price_span needs to see to price it at all.
        span = {int(c): own.get(int(c), []) for c in pt[KEY]}
        out = RCY.price_span(span, go_dev, g_table, pt, lines, label,
                             check_leakage=True, blocks=(blocks, spreads),
                             extra=term_extra(pt, lines))
        ok = out[out["status"] == "ok"].merge(
            pt[[KEY, "pkey", "end_yr", "war_per_season", "length"]
               ].rename(columns={"length": "length_pt"}), on=KEY)
        # A contract with no control years has nothing for the rules to price;
        # its control columns are zero by construction and are dropped from the
        # control-year tables, kept for the term tables.
        ok["owns_ctrl"] = ok["n_ctrl"] > 0
        C.log(f"  {len(ok)} contracts simulated ({int(ok['owns_ctrl'].sum())} with "
              f"control years); {int((out['status'] != 'ok').sum())} skipped for a "
              f"band that did not reach every season")
        attrition(go_dev, cmap, pt, blocks, ok)
        RCY.rule_guards(ok[ok["owns_ctrl"]])
        # Realised term dollars, on ended terms only. Read here and nowhere else.
        done = ok["end_yr"] <= C.LAST_SOURCE_SEASON
        rv = []
        for r in ok.itertuples():
            if r.end_yr > C.LAST_SOURCE_SEASON:
                rv.append(np.nan)
                continue
            row = pt[pt[KEY] == r.contract_id].iloc[0]
            yrs = list(range(int(row["start_yr"]), int(row["end_yr"]) + 1))
            w = real(row["pkey"], yrs)
            rv.append(float(SIM.contract_value(lines[row["cut"]], row,
                                               np.array([w.mean()]),
                                               np.array([w[0]]),
                                               SIM.dollar_factor(row))[0]))
        ok["term_realised"] = rv
        C.log(f"  {int(done.sum())} of them have an ended term and are scored "
              f"against realised dollars")
        C.log("")
        results[label] = ok

    # ---- 1. the control years ----------------------------------------------
    C.log("WHAT THE CONTROL YEARS ARE WORTH, mean $M per contract that owns")
    C.log("them, discounted to the signing. Six rules on the same draws; the")
    C.log("informed rule is the club deciding as it goes.")
    C.log("")
    rules = [("committed", "take all"), ("production_point", "prod rule"),
             ("declared", "in advance"), ("informed_myopic", "myopic"),
             ("informed", "as you go"), ("hindsight", "hindsight")]
    C.log(f"    {'forecast':<12}{'n':>4}" + "".join(f"{lab:>12}" for _, lab in rules))
    for label, ok in results.items():
        c = ok[ok["owns_ctrl"]]
        C.log(f"    {label:<12}{len(c):>4}" + "".join(
            f"{c[f'ctrl_{r}'].mean() / 1e6:>12.3f}" for r, _ in rules))
    C.log("")
    for label, ok in results.items():
        c = ok[ok["owns_ctrl"]]
        voi = (c["ctrl_informed"] - c["ctrl_declared"]).mean() / 1e6
        vpr = (c["ctrl_informed"] - c["ctrl_production_point"]).mean() / 1e6
        C.log(f"  {label}: seeing the path so far is worth {voi:+.3f} $M, and "
              f"deciding as you go against")
        C.log(f"    production's rule {vpr:+.3f} $M; the informed rule keeps him "
              f"{c['taken_informed'].mean():.2f} of the {c['n_ctrl'].mean():.2f} "
              f"control seasons owned, on average")
    C.log("")
    both = results["production"][[KEY, "pkey", "owns_ctrl", "ctrl_informed"]].merge(
        results["rate"][[KEY, "ctrl_informed"]], on=KEY, suffixes=("_prod", "_rate"))
    bc = both[both["owns_ctrl"]]
    if len(bc) > 2:
        C.log(f"  on the {len(bc)} contracts both forecasts price, the informed value "
              f"is {bc['ctrl_informed_prod'].mean() / 1e6:.3f} $M on production's")
        C.log(f"  forecast and {bc['ctrl_informed_rate'].mean() / 1e6:.3f} $M on the "
              f"rate's; rank correlation "
              f"{bc['ctrl_informed_prod'].corr(bc['ctrl_informed_rate'], method='spearman'):.3f}")
    C.log("")

    # ---- 2. the term, as a distribution --------------------------------------
    C.log("THE CONTRACT'S OWN TERM, AS A DISTRIBUTION. The price of the expected")
    C.log("season against the average price of the drawn seasons -- they differ")
    C.log("because the floor bends the price -- and the spread, in $M.")
    C.log("")
    C.log(f"    {'forecast':<12}{'n':>5}{'point':>9}{'simulated':>11}{'gap':>8}"
          f"{'cost':>8}{'sd':>8}{'10-90 width':>13}")
    for label, ok in results.items():
        C.log(f"    {label:<12}{len(ok):>5}{ok['value_point'].mean() / 1e6:>9.3f}"
              f"{ok['term_sim_mean'].mean() / 1e6:>11.3f}"
              f"{(ok['term_sim_mean'] - ok['value_point']).mean() / 1e6:>+8.3f}"
              f"{ok['cost'].mean() / 1e6:>8.3f}{ok['term_sim_sd'].mean() / 1e6:>8.3f}"
              f"{(ok['term_sim_q90'] - ok['term_sim_q10']).mean() / 1e6:>13.3f}")
    C.log("")

    # ---- 3. against what happened --------------------------------------------
    C.log("AGAINST WHAT HAPPENED. Ended terms, the realised dollars as defined in")
    C.log("the docstring. Squared error is the primary score (declared); mean")
    C.log("absolute error and bias beside it; coverage of the simulated 10-90%")
    C.log("band should be near 80% if the spread is right. $M.")
    C.log("")
    common = set.intersection(*[set(ok.loc[ok["term_realised"].notna(), KEY])
                                for ok in results.values()])
    C.log(f"    scored on the {len(common)} ended contracts both forecasts price")
    C.log(f"    {'forecast':<12}{'valuation':<11}{'RMSE':>8}{'MAE':>8}{'bias':>9}"
          f"{'10-90 cover':>13}{'25-75 cover':>13}")
    sc = {}
    for label, ok in results.items():
        e = ok[ok[KEY].isin(common)].copy()
        for how_, col in (("point", "value_point"), ("simulated", "term_sim_mean")):
            err = (e[col] - e["term_realised"]) / 1e6
            sc[(label, how_)] = e.assign(se=err ** 2, ae=err.abs())
            cover = ((e["term_realised"] >= e["term_sim_q10"])
                     & (e["term_realised"] <= e["term_sim_q90"])).mean()
            c50 = ((e["term_realised"] >= e["term_sim_q25"])
                   & (e["term_realised"] <= e["term_sim_q75"])).mean()
            tail = (f"{cover:>13.1%}{c50:>13.1%}" if how_ == "simulated"
                    else f"{'--':>13}{'--':>13}")
            C.log(f"    {label:<12}{how_:<11}{np.sqrt((err ** 2).mean()):>8.3f}"
                  f"{err.abs().mean():>8.3f}{err.mean():>+9.3f}" + tail)
    C.log("")
    pair = (sc[("production", "simulated")][[KEY, "pkey", "se", "ae"]]
            .merge(sc[("rate", "simulated")][[KEY, "se", "ae"]], on=KEY,
                   suffixes=("_prod", "_rate")))
    C.log(f"  the rate forecast's simulated value has lower squared dollar error in "
          f"{career_bootstrap(pair, 'se_prod', 'se_rate'):.0%} of goaltender-resamples,")
    C.log(f"  lower absolute error in "
          f"{career_bootstrap(pair, 'ae_prod', 'ae_rate'):.0%}")
    for label in ("production", "rate"):
        pp_ = (sc[(label, "point")][[KEY, "pkey", "se"]]
               .merge(sc[(label, "simulated")][[KEY, "se"]], on=KEY,
                      suffixes=("_point", "_sim")))
        C.log(f"  {label}: the simulated value beats the point value on squared "
              f"error in {career_bootstrap(pp_, 'se_point', 'se_sim'):.0%}")
    C.log("")

    out = pd.concat([ok.assign(forecast=l) for l, ok in results.items()],
                    ignore_index=True)
    out.to_csv(C.out_path("goalie_control_years.csv"), index=False)
    C.log(f"  wrote {C.out_path('goalie_control_years.csv').name} ({len(out)} rows)")
    C.write_log("goalie_control_years_run_log.txt")


if __name__ == "__main__":
    main()
