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
    are reported beside it. A lower WAR error is not assumed to carry through:
    the league-minimum floor and the control options make dollars a bent
    function of the path.

    ONE DOLLAR TARGET. Each forecast fits its own price line, and version 1.0
    priced each forecast's realised dollars on that forecast's own line -- so
    changing the forecast changed the answer it was scored against (by $0.51M
    a contract on average, $5.57M at most). The comparison between forecasts
    is now made in ONE declared currency, SCORING_LINE: the default forecast's
    line prices both forecasts' valuations and the realised path, and the
    realised target is asserted identical across the two. The rate forecast's
    line is the sensitivity. Each forecast on its own line is kept as a
    separate, labelled sensitivity, not as a comparison.

    CALIBRATION WITH LUMPS. The floor puts many dollar paths at exactly one
    value, and non-participation puts a season at exactly zero, so a nominal
    80% interval whose end sits on a lump can honestly hold far more than 80%.
    Version 1.0 read 93% against 80% as "too wide"; that does not follow. The
    test is now the randomized probability integral transform
    (`predictive_interval.randomized_pit`), uniform under calibration with
    lumps or without, and beside it the interval's coverage of the model's
    OWN draws -- what a calibrated forecast would show. At season level the
    two parts are tested apart: participation against what happened, and the
    CONDITIONAL performance band on the seasons he played.

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
import predictive_interval as PI
import forecast_harness as H
from contract_price_model import contract_sample, attach_forecasts
from player_season_table import birthdate_source, build as build_skater_table
from production_currency import ProductionCurrency, FEATURES

SCRIPT_VERSION = "1.2"
KEY = RCY.KEY

# The two forecasts, declared before the run: the label, the harness arm the
# band is built on, and the `ability` the point forecast is priced with. The
# arm and the ability must be the same forecast; the parity assertion below
# enforces it.
FORECASTS = (("production", GR.ProdTrail, "production"),
             ("rate", GR.FlatShare, "rate"))
# THE COMMON SCORING CURRENCY, declared before the comparison: the default
# forecast's price line. The other is reported as the sensitivity.
SCORING_LINE = "production"
PIT_SEED = 20260923


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


def term_extra(lines: dict, keep: dict):
    """The contract's own term priced on the drawn paths, on the forecast's OWN
    line (the own-line sensitivity), and the paths' term averages kept in
    `keep` so the same draws can be repriced on the common scoring line."""
    def f(cid, r, paths) -> dict:
        L = int(r["length"])
        wps, y1 = paths[:, :L].mean(axis=1), paths[:, 0].copy()
        keep[int(cid)] = (wps, y1)
        v = SIM.contract_value(lines[r["cut"]], r, wps, y1, SIM.dollar_factor(r))
        q10, q90 = np.percentile(v, [10, 90])
        return {"term_sim_mean": float(v.mean()), "term_sim_sd": float(v.std(ddof=1)),
                "term_sim_q10": float(q10), "term_sim_q90": float(q90),
                "cost": float(r["cost"]), "value_point": float(r["value_point"])}
    return f


def ci(values: pd.DataFrame, stat, n: int = 2000, seed: int = 20260923) -> tuple:
    """A statistic and its 95% interval from resampling GOALTENDERS."""
    g = {k: v for k, v in values.groupby("pkey")}
    ks = list(g)
    rng = np.random.default_rng(seed)
    b = [stat(pd.concat([g[k] for k in rng.choice(ks, len(ks), replace=True)]))
         for _ in range(n)]
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(stat(values)), float(lo), float(hi)


def pit_block(d: pd.DataFrame, label: str) -> None:
    """Uniformity of randomized PITs, with goaltender-resampled intervals.
    Under calibration: central 80% share 0.80, central 50% share 0.50, mean
    0.5, variance 1/12 = 0.0833. A variance BELOW 1/12 means outcomes sit
    nearer the middle than the forecast says -- too wide; above, too narrow."""
    rows = [("central 80% (0.1 to 0.9)", 0.80, lambda x: x["pit"].between(0.1, 0.9).mean()),
            ("central 50% (0.25 to 0.75)", 0.50, lambda x: x["pit"].between(0.25, 0.75).mean()),
            ("mean", 0.5, lambda x: x["pit"].mean()),
            ("variance", 1 / 12, lambda x: x["pit"].var(ddof=0))]
    C.log(f"    {label}  ({len(d)} outcomes)")
    for name, want, stat in rows:
        v, lo, hi = ci(d, stat)
        flag = "" if lo <= want <= hi else "   <- outside"
        C.log(f"      {name:<28}{v:>8.3f}   [{lo:.3f}, {hi:.3f}]   calibrated {want:.3f}{flag}")


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
    # --participation observable: the candidate participation, switched for the
    # scored arms and the priced forecast together (GP.PART_CONTRACT_STATE).
    # Outputs carry a suffix so the default run's files are not overwritten.
    import run_goalie_participation as GPM
    suffix = ""
    if "--participation" in sys.argv:
        GPM.PART_CONTRACT_STATE = sys.argv[sys.argv.index("--participation") + 1]
        suffix = f"_{GPM.PART_CONTRACT_STATE}"
    C.banner("run_goalie_control_years.py", SCRIPT_VERSION)
    C.log(f"  participation contract state: {GPM.PART_CONTRACT_STATE}")
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

    # ---- price both forecasts first: the scoring currency needs both lines --
    priced = {}
    for label, arm, ability in FORECASTS:
        gf = PL.goalie_forecasts(go_s, g_table, participation="model", ability=ability)
        go = go_dev.merge(gf, on=KEY, how="inner")
        priced[label] = point_valuation(sk, go)

    real = realised_path(g_table)
    results, draws, arms = {}, {}, {}
    for label, arm, ability in FORECASTS:
        C.log("=" * 74)
        C.log(f"FORECAST: {label} ({arm.name})")
        C.log("=" * 74)
        pt, lines = priced[label]
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
        # control years carry them too.
        span = {int(c): own.get(int(c), []) for c in pt[KEY]}
        keep = {}
        out = RCY.price_span(span, go_dev, g_table, pt, lines, label,
                             check_leakage=True, blocks=(blocks, spreads),
                             extra=term_extra(lines, keep))
        ok = out[out["status"] == "ok"].merge(
            pt[[KEY, "pkey", "end_yr", "war_per_season", "length"]
               ].rename(columns={"length": "length_pt"}), on=KEY)
        ok["owns_ctrl"] = ok["n_ctrl"] > 0
        C.log(f"  {len(ok)} contracts simulated ({int(ok['owns_ctrl'].sum())} with "
              f"control years); {int((out['status'] != 'ok').sum())} skipped for a "
              f"band that did not reach every season")
        attrition(go_dev, cmap, pt, blocks, ok)
        RCY.rule_guards(ok[ok["owns_ctrl"]])
        results[label], draws[label], arms[label] = ok, keep, arm

    # ---- 1. the control years ----------------------------------------------
    C.log("WHAT THE CONTROL YEARS ARE WORTH, mean $M per contract that owns")
    C.log("them, discounted to the signing, each forecast on its OWN price line")
    C.log("(a valuation, not a scored comparison). Six rules on the same draws.")
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
    both = results["production"][[KEY, "owns_ctrl", "ctrl_informed"]].merge(
        results["rate"][[KEY, "ctrl_informed"]], on=KEY, suffixes=("_prod", "_rate"))
    bc = both[both["owns_ctrl"]]
    C.log(f"  on the {len(bc)} contracts both price, rank correlation of the informed "
          f"value {bc['ctrl_informed_prod'].corr(bc['ctrl_informed_rate'], method='spearman'):.3f}")
    C.log("")

    # ---- the term, as a distribution (each forecast on its own line) --------
    C.log("THE CONTRACT'S OWN TERM, AS A DISTRIBUTION, each forecast on its own")
    C.log("line. The price of the expected season against the average price of")
    C.log("the drawn seasons -- they differ because the floor bends the price. $M.")
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

    # ---- 2. against what happened, in ONE currency ---------------------------
    common = sorted(set.intersection(*[
        set(ok.loc[ok["end_yr"] <= C.LAST_SOURCE_SEASON, KEY]) for ok in results.values()]))
    rows_of = {lab: priced[lab][0].set_index(KEY) for lab in priced}

    def score_on(line_label: str) -> pd.DataFrame:
        """Both forecasts' point and simulated valuations, and the realised
        path, priced on ONE line. The realised target is computed from each
        forecast's own contract row and asserted identical -- it cannot depend
        on which forecast is being scored."""
        lines = priced[line_label][1]
        out = []
        for cid in common:
            rp = rows_of["production"].loc[cid]
            cur = lines[rp["cut"]]
            k = SIM.dollar_factor(rp)
            yrs = list(range(int(rp["start_yr"]), int(rp["end_yr"]) + 1))
            w = real(rp["pkey"], yrs)
            targets = []
            rec = {KEY: cid, "pkey": rp["pkey"]}
            for lab in ("production", "rate"):
                row = rows_of[lab].loc[cid].copy()
                row[KEY] = cid
                targets.append(float(SIM.contract_value(cur, row, np.array([w.mean()]),
                                                        np.array([w[0]]), k)[0]))
                rec[f"point_{lab}"] = float(cur.value(pd.DataFrame([row])).iloc[0])
                wps, y1 = draws[lab][cid]
                v = SIM.contract_value(cur, row, wps, y1, k)
                rec[f"sim_{lab}"] = float(v.mean())
                rec[f"draws_{lab}"] = v
            assert abs(targets[0] - targets[1]) < 1e-6, (
                f"contract {cid}: the realised target differs by forecast")
            rec["realised"] = targets[0]
            out.append(rec)
        return pd.DataFrame(out)

    C.log("AGAINST WHAT HAPPENED, IN ONE CURRENCY. Ended terms. Both forecasts'")
    C.log("valuations and the realised path are priced on the same line, so the")
    C.log("target cannot move with the forecast (asserted, contract by contract).")
    C.log("Squared error is the primary score (declared); $M.")
    C.log("")
    scored = {}
    for line_label in (SCORING_LINE, "rate" if SCORING_LINE == "production" else "production"):
        d = score_on(line_label)
        scored[line_label] = d
        tag = "PRIMARY" if line_label == SCORING_LINE else "sensitivity"
        C.log(f"  on the {line_label} forecast's line ({tag}), {len(d)} contracts:")
        C.log(f"    {'forecast':<12}{'valuation':<11}{'RMSE':>8}{'MAE':>8}{'bias':>9}")
        for lab in ("production", "rate"):
            for how_ in ("point", "sim"):
                e = (d[f"{how_}_{lab}"] - d["realised"]) / 1e6
                d[f"se_{how_}_{lab}"], d[f"ae_{how_}_{lab}"] = e ** 2, e.abs()
                C.log(f"    {lab:<12}{('point' if how_ == 'point' else 'simulated'):<11}"
                      f"{np.sqrt((e ** 2).mean()):>8.3f}{e.abs().mean():>8.3f}{e.mean():>+9.3f}")
        for how_ in ("sim", "point"):
            ws = career_bootstrap(d, f"se_{how_}_production", f"se_{how_}_rate")
            wa = career_bootstrap(d, f"ae_{how_}_production", f"ae_{how_}_rate")
            C.log(f"    rate against production, {('simulated' if how_ == 'sim' else 'point')}: "
                  f"lower squared error in {ws:.0%}, lower absolute in {wa:.0%}")
        C.log("")
    C.log("  Each forecast on its OWN line and its own realised target -- the 1.0")
    C.log("  comparison -- is not a common-target test and is kept as a sensitivity:")
    for label, ok in results.items():
        pt, lines = priced[label]
        e = []
        for cid in common:
            row = rows_of[label].loc[cid].copy(); row[KEY] = cid
            yrs = list(range(int(row["start_yr"]), int(row["end_yr"]) + 1))
            w = real(row["pkey"], yrs)
            r_own = float(SIM.contract_value(lines[row["cut"]], row, np.array([w.mean()]),
                                             np.array([w[0]]), SIM.dollar_factor(row))[0])
            sim = float(ok.loc[ok[KEY] == cid, "term_sim_mean"].iloc[0])
            e.append((sim - r_own) / 1e6)
        e = np.array(e)
        C.log(f"    {label:<12}simulated, own line   RMSE {np.sqrt((e ** 2).mean()):.3f}   "
              f"bias {e.mean():+.3f}")
    C.log("")

    # ---- 3. is the contract distribution calibrated? -------------------------
    d = scored[SCORING_LINE]
    C.log("IS THE CONTRACT DISTRIBUTION CALIBRATED? On the scoring line. The floor")
    C.log("puts many draws at exactly one value, so an interval's coverage is")
    C.log("compared with its coverage of the MODEL'S OWN DRAWS, and the randomized")
    C.log("PIT (uniform under calibration, lumps or not) is tested directly.")
    C.log("")
    for lab in ("production", "rate"):
        rng_pit = []
        cov = []
        for r in d.itertuples():
            v = getattr(r, f"draws_{lab}")
            u = float(np.random.default_rng([PIT_SEED, int(r.contract_id)]).random())
            rng_pit.append(PI.randomized_pit(v, r.realised, u))
            q10, q25, q75, q90 = np.percentile(v, [10, 25, 75, 90])
            floor = float(v.min())
            cov.append({"own80": np.mean((v >= q10) & (v <= q90)),
                        "obs80": float(q10 <= r.realised <= q90),
                        "own50": np.mean((v >= q25) & (v <= q75)),
                        "obs50": float(q25 <= r.realised <= q75),
                        "atom": np.mean(v == floor),
                        "real_at_floor": float(abs(r.realised - floor) < 1e-6)})
        dd = pd.concat([d[[KEY, "pkey"]].reset_index(drop=True),
                        pd.DataFrame(cov), pd.Series(rng_pit, name="pit")], axis=1)
        v, lo, hi = ci(dd, lambda x: (x["real_at_floor"] - x["atom"]).mean())
        C.log(f"  {lab}: {dd['atom'].mean():.1%} of each contract's draws sit exactly on "
              f"its lowest value (the floor); {dd['real_at_floor'].mean():.1%} of outcomes do")
        C.log(f"    outcomes on the floor minus the model's own share: {100 * v:+.1f} points "
              f"[{100 * lo:+.1f}, {100 * hi:+.1f}]")
        for band in ("80", "50"):
            v, lo, hi = ci(dd, lambda x, b=band: (x[f"obs{b}"] - x[f"own{b}"]).mean())
            C.log(f"    {band}% interval: holds {dd[f'obs{band}'].mean():.1%} of outcomes "
                  f"against {dd[f'own{band}'].mean():.1%} of its own draws; excess "
                  f"{100 * v:+.1f} points [{100 * lo:+.1f}, {100 * hi:+.1f}]")
        pit_block(dd, f"{lab}, randomized PIT of the term value")
        C.log("")

    # ---- 4. which component: participation, or the conditional band? ---------
    C.log("WHICH COMPONENT, AT SEASON LEVEL. The season distribution is a lump at")
    C.log("zero (he does not play) and a conditional band (he plays). Tested apart,")
    C.log("development pages, every goaltender-season the harness scores.")
    C.log("")
    for lab, arm in arms.items():
        m = PI.WithIntervals(arm())
        h = H.Harness(g_table).run(m, pages=C.DEV_PAGES, horizons=GR.HORIZONS)
        h["mu"] = h["rate_82"] * h["gp_share"]
        h["sigma"] = np.nan
        for (page, hh), idx in h.groupby(["page", "h"]).groups.items():
            h.loc[idx, "sigma"] = m.spreads_[int(page)].sigma(int(hh), h.loc[idx, "mu"].to_numpy())
        u = np.random.default_rng(PIT_SEED).random(len(h))
        zs = {pg: sp.zs_ for pg, sp in m.spreads_.items()}
        h["pit_mix"] = np.nan
        h["pit_cond"] = np.nan
        for page, idx in h.groupby("page").groups.items():
            g = h.loc[idx]
            h.loc[idx, "pit_mix"] = PI.mixture_pit(g["act_war"], g["p_play"], g["mu"],
                                                   g["sigma"], zs[int(page)], u[h.index.get_indexer(idx)])
            h.loc[idx, "pit_cond"] = PI._shape_cdf((g["act_war"] - g["mu"]) / g["sigma"],
                                                   zs[int(page)])
        C.log(f"  {lab}:")
        C.log("    whether he plays, predicted against observed by fifth of the prediction:")
        h["pq"] = pd.qcut(h["p_play"], 5, labels=False, duplicates="drop")
        line = "      " + "  ".join(f"{g['p_play'].mean():.2f}/{g['played'].mean():.2f}"
                                    for _, g in h.groupby("pq"))
        C.log(line)
        top = h[h["pq"] == h["pq"].max()].assign(pkey=h["career_key"])
        v, lo, hi = ci(top, lambda x: (x["p_play"] - x["played"].astype(float)).mean())
        C.log(f"      top fifth: predicted minus observed {v:+.3f} [{lo:+.3f}, {hi:+.3f}]")
        pit_block(h.assign(pkey=h["career_key"]).rename(columns={"pit_cond": "pit"})
                  .loc[h["played"]], "the conditional band, on seasons he played")
        pit_block(h.assign(pkey=h["career_key"]).rename(columns={"pit_mix": "pit"}),
                  "the whole season distribution, every cell")
        C.log("")

    out = pd.concat([ok.assign(forecast=l) for l, ok in results.items()],
                    ignore_index=True)
    out.to_csv(C.out_path("goalie_control_years" + suffix + ".csv"), index=False)
    sc = scored[SCORING_LINE].drop(columns=[c for c in scored[SCORING_LINE].columns
                                            if c.startswith("draws_")])
    sc.to_csv(C.out_path("goalie_control_years_scored" + suffix + ".csv"), index=False)
    # THE DRAWS, the contract rows and the lines, kept so that a comparison
    # ACROSS runs (two participation models, say) can reprice both on one
    # fixed line. Each run's own lines differ, so comparing two runs' scores
    # as printed would score them against different targets.
    import pickle
    with open(C.out_path(f"goalie_control_years{suffix}.pkl"), "wb") as fh:
        pickle.dump({"priced": priced, "draws": draws, "common": common}, fh)
    C.log(f"  wrote goalie_control_years{suffix}.csv and the scored table")
    C.write_log(f"goalie_control_years{suffix}_run_log.txt")


if __name__ == "__main__":
    main()
