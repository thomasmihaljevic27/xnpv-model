"""run_npv_simulation.py -- contract value as a distribution, and what the
point valuation was approximating.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5. Development start years only;
the reserved market cohorts are refused by the guard. Nothing adopted.

WHAT IT DOES
    Every development contract is valued twice on the same forecast, the same
    price line, the same cost and the same discounting. Once the way the chain
    values it now -- one production per season, averaged, pushed through the
    price line. And once by drawing career paths, pricing each path, and
    averaging the prices.

    The two differ because the value of a path is not a straight line in the
    production on it: the league minimum truncates the downside and the
    censored price line bends near it. So the average of the values sits above
    the value of the average. The gap is not an error in the point valuation.
    It is the quantity the point valuation was approximating, measured for the
    first time.

WHAT THE PATHS CARRY THAT THE AVERAGE DOES NOT
    An exit that sticks, rather than every season multiplied by a probability;
    and a miss that persists across seasons at a fitted rate rather than
    washing out independently. The second is what decides a long contract's
    spread, and it is fitted here rather than assumed.

REPORTS
    1. how much of a miss persists, fitted
    2. the identity: with no uncertainty the simulation IS the point valuation
    3. what the paths are worth against the point valuation, by term and tier
    4. the spread of a contract's value, which is the thing that did not exist
    5. how far the term is from being a straight line in production
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import information_set as ISET
import predictive_interval as PI
import npv_simulation as SIM
from contract_price_model import contract_sample, attach_forecasts
from production_currency import ProductionCurrency
from player_season_table import build as build_table, birthdate_source
from run_phase4_decisions import prep
from ability_forecast import A1HingeExposure

SCRIPT_VERSION = "1.0"

LEADER = A1HingeExposure
KEY = "contract_id"
N_PATHS = 2000
TIER_EDGES = [-np.inf, 0, 0.5, 1.0, 2.0, np.inf]
TIER_NAMES = ["below 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2+"]


def per_season(sample: pd.DataFrame, table: pd.DataFrame):
    """For every contract, the forecast for each season of its term AND the
    band around it: the conditional total, its scale, and the probability of
    playing. `attach_forecasts` collapses these into an average, which is all a
    point valuation needs and not enough to walk a path.

    Batched by the last season readable at the signing, exactly as
    `attach_forecasts` batches, so every contract sees the same information set
    its point valuation saw and the two are comparable row by row.
    """
    rows, spreads = {}, {}
    for L, grp in sample.groupby("latest_complete"):
        t0 = int(L) + 1
        if t0 < C.FIRST_SOURCE_SEASON + 3:
            continue
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        model = PI.WithIntervals(LEADER())
        model.fit(iset.seasons, before=t0)
        subs = H.subjects_at(iset)
        if subs.empty:
            continue
        hs = sorted({int(s - t0) for r in grp.itertuples()
                     for s in range(int(r.start_yr), int(r.end_yr) + 1)
                     if s - t0 >= 0})
        if not hs:
            continue
        model.spread_.ensure_horizons(hs)
        pred = model.model.predict_beyond_fit(iset, subs, hs)
        pred = pred.merge(subs[["career_key", "pkey"]], on="career_key", how="left")
        pred["mu"] = pred["rate_82"] * pred["gp_share"]
        pred["sigma"] = np.concatenate([
            model.spread_.sigma(int(h), pred.loc[pred["h"] == h, "mu"])
            for h in sorted(pred["h"].unique())])[
                np.argsort(np.argsort(pred["h"].to_numpy(), kind="stable"), kind="stable")]
        lut = pred.set_index(["pkey", "h"])[["mu", "sigma", "p_play"]]
        spreads[t0] = model.spread_
        for r in grp.itertuples():
            hh = [int(s - t0) for s in range(int(r.start_yr), int(r.end_yr) + 1)]
            try:
                block = lut.loc[[(r.pkey, x) for x in hh]]
            except KeyError:
                continue
            if block[["mu", "sigma", "p_play"]].isna().to_numpy().any():
                continue
            rows[r.contract_id] = (t0, block["mu"].to_numpy(),
                                   block["sigma"].to_numpy(),
                                   block["p_play"].to_numpy())
    return rows, spreads


def main() -> None:
    C.banner("run_npv_simulation.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    table = build_table(birthdate_csv=path, verbose=False)
    C.log(f"  birthdates: {how}")
    C.log("")

    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_npv_simulation")

    # The point valuation, on exactly the protocol the rest of the tree uses.
    d = prep(attach_forecasts(sample, LEADER, table, verbose=False))
    d = d[d["start_yr"].isin(cohorts)
          & (d["signed"] >= pd.Timestamp("2015-07-01"))].copy()
    d["cut"] = d["signed"].dt.to_period("Q").dt.start_time

    priced, lines = [], {}
    for cut, te in d.groupby("cut"):
        cur = ProductionCurrency("in").fit(d, before_date=cut)
        if cur.coef_ is None:
            continue
        lines[cut] = cur
        te = te.copy()
        te["value_point"] = cur.value(te)
        te["cost"] = cur.cost(te)
        priced.append(te)
    pt = pd.concat(priced, ignore_index=True).drop_duplicates(KEY)
    pt["surplus_point"] = pt["value_point"] - pt["cost"]
    C.log(f"  {len(pt)} contracts valued the existing way")

    seasons, _ = per_season(sample, table)
    C.log(f"  {len(seasons)} contracts carry a season-by-season band")
    C.log("")

    # ---- 1. persistence ---------------------------------------------------
    t0 = time.time()
    anchor_page = max(s[0] for s in seasons.values())
    anchor = PI.WithIntervals(LEADER())
    iset = ISET.build(table, ISET.decision_date_for_page(anchor_page), t0=anchor_page)
    anchor.fit(iset.seasons, before=anchor_page)
    pers = SIM.Persistence().fit(
        anchor.spread_.pairs_,
        lambda h, mu: np.concatenate([
            anchor.spread_.sigma(int(x), mu[h == x]) for x in np.unique(h)])[
                np.argsort(np.argsort(h, kind="stable"), kind="stable")])
    C.log("REPORT 1  HOW MUCH OF A MISS PERSISTS. If the seasons of a contract")
    C.log("were independent misses, a six-year deal would average them out and")
    C.log("its spread would scale as the square root of the term. If a miss")
    C.log("persisted entirely, it would scale with the term. Neither is true and")
    C.log("the mix is fitted, on the same replayed misses the band is fitted on.")
    C.log("")
    for line in pers.report():
        C.log(line)
    C.log(f"  ({time.time() - t0:.0f}s)")
    C.log("")

    # ---- 2. the identity --------------------------------------------------
    C.log("REPORT 2  THE IDENTITY. With the spread set to nothing and")
    C.log("participation certain, every path is the same path, so the simulation")
    C.log("must return the point valuation exactly. This replaces the retired")
    C.log("k=0 identity the plan withdrew, and it is checked on real contracts")
    C.log("rather than on a constructed case.")
    C.log("")
    rng = np.random.default_rng(20260916)
    INDEP = SIM.Persistence()          # every weight zero: seasons independent
    ids = [i for i in pt[KEY] if i in seasons]
    worst = 0.0
    for cid in ids[:300]:
        r = pt[pt[KEY] == cid].iloc[0]
        t0_, mu, sg, pp = seasons[cid]
        k = SIM.dollar_factor(r)
        flat = SIM.draw_paths(mu, np.zeros_like(sg), np.ones_like(pp),
                              np.zeros(1001), pers, 8, rng)
        got = SIM.contract_value(lines[r["cut"]], r, flat.mean(axis=1),
                                 flat[:, 0], k)
        want = SIM.contract_value(lines[r["cut"]], r,
                                  np.array([float(np.mean(mu))]),
                                  np.array([float(mu[0])]), k)[0]
        worst = max(worst, float(np.max(np.abs(got - want))))
    assert worst < 1.0, f"the identity fails by ${worst:,.2f}"
    C.log(f"    300 contracts, largest gap ${worst:.6f}  [PASS]")
    C.log("")

    # ---- 3. simulate ------------------------------------------------------
    t0 = time.time()
    out = []
    for cid in ids:
        r = pt[pt[KEY] == cid].iloc[0]
        page, mu, sg, pp = seasons[cid]
        k = SIM.dollar_factor(r)
        paths = SIM.draw_paths(mu, sg, pp, anchor.spread_.zs_, pers, N_PATHS, rng)
        wps = paths.mean(axis=1)
        val = SIM.contract_value(lines[r["cut"]], r, wps, paths[:, 0], k)
        sur = val - float(r["cost"])
        # THE SAME CONTRACT WITH THE SEASONS MADE INDEPENDENT, which is what a
        # point valuation implicitly assumes when it averages them. Run on the
        # same contract rather than compared across terms, because long deals
        # go to better players with wider bands and a comparison across terms
        # would be measuring that instead.
        ind = SIM.draw_paths(mu, sg, pp, anchor.spread_.zs_, INDEP, N_PATHS, rng)
        sur_ind = SIM.contract_value(lines[r["cut"]], r, ind.mean(axis=1),
                                     ind[:, 0], k) - float(r["cost"])
        out.append({KEY: cid, "term": len(mu), "war_per_season": r["war_per_season"],
                    "surplus_point": float(r["surplus_point"]),
                    "surplus_sim": float(sur.mean()),
                    "sim_sd": float(sur.std()),
                    "sim_p10": float(np.quantile(sur, 0.10)),
                    "sim_p90": float(np.quantile(sur, 0.90)),
                    "p_negative": float((sur < 0).mean()),
                    "sd_independent": float(sur_ind.std()),
                    "wps_point": float(r["war_per_season"]),
                    "wps_sim": float(wps.mean()),
                    "rising_p": SIM.rising_marginals(pp)})
    s = pd.DataFrame(out)
    s["gap"] = s["surplus_sim"] - s["surplus_point"]
    C.log(f"  {len(s)} contracts simulated, {N_PATHS} paths each "
          f"({time.time() - t0:.0f}s)")
    C.log("")

    C.log("REPORT 3  WHAT THE PATHS ARE WORTH AGAINST THE POINT VALUATION.")
    C.log("The average production per season is the same either way -- that is")
    C.log("arithmetic, and the check below confirms it -- so the whole of the")
    C.log("difference is the price line's curvature and the league minimum.")
    C.log("")
    C.log(f"    average production per season: point {s['wps_point'].mean():.4f}, "
          f"simulated {s['wps_sim'].mean():.4f}, "
          f"largest gap {np.abs(s['wps_point'] - s['wps_sim']).max():.4f}")
    C.log("")
    # NO PERCENTAGE COLUMN. The point surplus averages near zero by
    # construction -- the price line is fitted to these contracts -- so a gap
    # expressed as a share of it reads in the hundreds of percent and means
    # nothing. The dollars are the number.
    C.log(f"  {'term':<8}{'n':>6}{'point $M':>11}{'simulated':>11}{'gap':>9}")
    for L, g in s.groupby("term"):
        if len(g) < 15:
            continue
        C.log(f"  {int(L)} yr{'':<3}{len(g):>6}{g['surplus_point'].mean()/1e6:>11.2f}"
              f"{g['surplus_sim'].mean()/1e6:>11.2f}{g['gap'].mean()/1e6:>9.2f}")
    C.log(f"  {'ALL':<8}{len(s):>6}{s['surplus_point'].mean()/1e6:>11.2f}"
          f"{s['surplus_sim'].mean()/1e6:>11.2f}{s['gap'].mean()/1e6:>9.2f}")
    C.log("")
    tiers = pd.cut(s["war_per_season"], TIER_EDGES, labels=TIER_NAMES)
    C.log(f"  {'forecast':<10}{'n':>6}{'point $M':>11}{'simulated':>11}{'gap':>9}")
    for t, g in s.groupby(tiers, observed=True):
        C.log(f"  {str(t):<10}{len(g):>6}{g['surplus_point'].mean()/1e6:>11.2f}"
              f"{g['surplus_sim'].mean()/1e6:>11.2f}{g['gap'].mean()/1e6:>9.2f}")
    C.log("")

    # ---- 4. the spread ----------------------------------------------------
    C.log("REPORT 4  THE SPREAD OF A CONTRACT'S VALUE, which is the thing that")
    C.log("did not exist before. A club signing a deal is not buying a number.")
    C.log("")
    C.log(f"  {'term':<8}{'n':>6}{'mean $M':>10}{'sd':>9}{'10th':>9}{'90th':>9}"
          f"{'chance it loses':>17}{'sd if seasons':>15}{'widened by':>12}")
    for L, g in s.groupby("term"):
        if len(g) < 15:
            continue
        C.log(f"  {int(L)} yr{'':<3}{len(g):>6}{g['surplus_sim'].mean()/1e6:>10.2f}"
              f"{g['sim_sd'].mean()/1e6:>9.2f}{g['sim_p10'].mean()/1e6:>9.2f}"
              f"{g['sim_p90'].mean()/1e6:>9.2f}{100*g['p_negative'].mean():>16.0f}%"
              f"{g['sd_independent'].mean()/1e6:>15.2f}"
              f"{100*(g['sim_sd'].mean()/max(g['sd_independent'].mean(), 1) - 1):>11.0f}%")
    C.log("")
    C.log("  WHAT PERSISTENCE IS WORTH, measured rather than asserted. The last")
    C.log("  two columns redraw the SAME contracts with the seasons made")
    C.log("  independent, which is what averaging them implicitly assumes. The")
    C.log("  comparison is within a contract, not across terms: long deals go to")
    C.log("  better players with wider bands, so a spread that grows with the")
    C.log("  term says nothing on its own about whether misses persist.")
    C.log("")

    rise = int((s["rising_p"] > 0).sum())
    C.log(f"  LIMITATION, counted rather than described: {rise} of {len(s)} terms")
    C.log("  ask for a probability of playing that RISES from one season to the")
    C.log("  next, which the absorbing exit cannot honour. Those paths keep the")
    C.log("  player gone where the participation model would have let him come")
    C.log("  back, so their spread is understated.")
    C.log("")

    s.to_csv(C.out_path("npv_simulation.csv"), index=False)
    C.log(f"  wrote {C.out_path('npv_simulation.csv').name}")
    C.write_log("npv_simulation_run_log.txt")


if __name__ == "__main__":
    main()
