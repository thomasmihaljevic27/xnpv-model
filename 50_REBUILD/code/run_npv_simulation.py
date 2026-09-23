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
from ability_forecast import A1HingeExposure, A1HingeExposureStatus

SCRIPT_VERSION = "2.5"

# THE SKATER LEADER, adopted provisionally 2026-09-23: the previous leader with
# visible contract status in its participation (Skater_Contract_Test.md).
# Every downstream runner imports LEADER from here, so this line is the switch.
# The previous leader, which reads no contract data, is kept by name as the
# sensitivity.
LEADER = A1HingeExposureStatus
PRIOR_LEADER = A1HingeExposure
KEY = "contract_id"
N_PATHS = 2000
TIER_EDGES = [-np.inf, 0, 0.5, 1.0, 2.0, np.inf]
TIER_NAMES = ["below 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2+"]


def term_seasons(r) -> list[int]:
    """The seasons of a contract's own term. The default question asked of the
    forecast, and the one the point valuation asks."""
    return list(range(int(r.start_yr), int(r.end_yr) + 1))


def forecast_blocks(sample: pd.DataFrame, table: pd.DataFrame,
                    seasons_for=term_seasons, model_factory=None):
    """For every contract, the forecast for each season ASKED FOR and the band
    around it: the conditional total, its scale, and the probability of
    playing. `attach_forecasts` collapses these into an average, which is all a
    point valuation needs and not enough to walk a path.

    `seasons_for` decides which seasons are fetched. The default is the
    contract's own term. The control-year work asks for the term PLUS the
    seasons the club holds the player's rights for afterwards, which is the
    same question at longer horizons, so it passes its own function rather
    than getting a second copy of this routine. Returns the season list with
    each block, because a caller asking for more than the term has to know
    which row is which.

    Batched by the last season readable at the signing, exactly as
    `attach_forecasts` batches, so every contract sees the same information set
    its point valuation saw and the two are comparable row by row.

    `model_factory` builds the forecast model; the default is the skater
    leader. The goalie control-year runner passes its own goalie arms, so the
    band, the replayed misses and the dependence fit are this routine's for
    both positions rather than a goalie copy of it. `table` must then be the
    goalie panel.
    """
    rows, spreads = {}, {}
    for L, grp in sample.groupby("latest_complete"):
        t0 = int(L) + 1
        if t0 < C.FIRST_SOURCE_SEASON + 3:
            continue
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        model = PI.WithIntervals((model_factory or LEADER)())
        model.fit(iset.seasons, before=t0)
        subs = H.subjects_at(iset)
        if subs.empty:
            continue
        hs = sorted({int(s - t0) for r in grp.itertuples()
                     for s in seasons_for(r) if s - t0 >= 0})
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
        # SIGNING-DATED PARTICIPATION, exactly as `attach_forecasts` does it.
        # A model whose participation reads contract state is asked at each
        # contract's signing, not at 1 July of the page, so the paths and the
        # point valuation carry the same probability of playing (the identity
        # in report 2 depends on it). One call per batch; rows are the
        # contracts themselves, so two signings by one player on one page get
        # their own dates. A model reading no contract data skips this and is
        # unchanged bit for bit.
        inner = model.model
        signed = None
        if getattr(inner, "reads_contracts", False):
            ck = subs.drop_duplicates("pkey").set_index("pkey")["career_key"]
            keys = ck.reindex(grp["pkey"]).to_numpy()
            signed = inner.p_play_signed(iset, keys, hs, grp["signed"].to_numpy())
            pos = {ix: i for i, ix in enumerate(grp.index)}
        for r in grp.itertuples():
            yrs = [s for s in seasons_for(r) if s - t0 >= 0]
            hh = [int(s - t0) for s in yrs]
            try:
                block = lut.loc[[(r.pkey, x) for x in hh]]
            except KeyError:
                continue
            if signed is not None:
                block = block.copy()
                block["p_play"] = [float(signed[x][pos[r.Index]]) for x in hh]
            if block[["mu", "sigma", "p_play"]].isna().to_numpy().any():
                continue
            rows[r.contract_id] = (t0, block["mu"].to_numpy(),
                                   block["sigma"].to_numpy(),
                                   block["p_play"].to_numpy(), yrs)
    return rows, spreads


def per_season(sample: pd.DataFrame, table: pd.DataFrame):
    """`forecast_blocks` over each contract's own term, in the four-element
    shape this runner and the review scripts read. One implementation, asked a
    narrower question -- not a copy of it."""
    rows, spreads = forecast_blocks(sample, table)
    return {k: v[:4] for k, v in rows.items()}, spreads


def page_scale(spread):
    """A spread's scale as a function of (horizon array, mu array)."""
    def f(h, mu):
        h = np.asarray(h)
        order = np.argsort(np.argsort(h, kind="stable"), kind="stable")
        return np.concatenate([spread.sigma(int(x), mu[h == x])
                               for x in np.unique(h)])[order]
    return f


def calibration_for(page: int, spreads: dict, pers: dict, rets: dict):
    """The shape, dependence and return rate a contract on `page` is entitled
    to.

    A THREE-LINE FUNCTION WITH ITS OWN NAME, because this selection is where
    the look-ahead lived: the runner used to reach for the LATEST page's
    calibration for every contract. The corrected indexing was inline, so a
    guard could check the calibrators and still not touch the thing that picks
    between them -- which is exactly what the first version of check 25 did,
    and it went on passing when the runner was stubbed out entirely.

    Now there is one place to pick, the runner calls it, and the guard drives
    the runner. Reverting to `max(spreads)` here fails that guard.
    """
    return spreads[page], pers[page], rets[page]


def page_dependence(spreads: dict, table: pd.DataFrame):
    """One persistence fit and one return rate PER PAGE, from what that page
    could see.

    THIS IS THE REPAIR THE REVIEW REQUIRED. The first version fitted a single
    calibrator on the latest page in the whole contract input -- 2025, whose
    replay contains outcomes through 2024 -- and used its residual shape and
    its persistence for every contract, all of which are earlier. The price
    lines were rolling and the forecasts were dated; the uncertainty around
    them was not, and it is the only part of this chain that reads outcomes.

    It is not a harmless reuse of the same numbers either. Fitted on what 2015
    could see, the permanent part of a miss is 0.00; on 2025 it is 0.25.
    """
    pers, rets = {}, {}
    for page, sp in spreads.items():
        pers[page] = SIM.Persistence().fit(sp.pairs_, page_scale(sp))
        rets[page] = SIM.return_rate(table, before=page)
    return pers, rets


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

    seasons, spreads = per_season(sample, table)
    C.log(f"  {len(seasons)} contracts carry a season-by-season band")
    C.log("")

    # ---- 1. persistence, per page -----------------------------------------
    t0 = time.time()
    pers_by_page, ret_by_page = page_dependence(spreads, table)
    C.log("REPORT 1  HOW MUCH OF A MISS PERSISTS, FITTED PER PAGE. If the")
    C.log("seasons of a contract were independent misses, a six-year deal would")
    C.log("average them out and its spread would scale as the square root of the")
    C.log("term. If a miss persisted entirely it would scale with the term.")
    C.log("Neither is true, and the mix is fitted on the same replayed misses the")
    C.log("band is fitted on -- each page on its own, using only outcomes that")
    C.log("page could see.")
    C.log("")
    C.log(f"  {'page':<8}{'permanent':>11}{'fading':>9}{'fade rate':>11}"
          f"{'rank rho at 1':>15}{'return rate':>13}")
    for page in sorted(pers_by_page):
        q = pers_by_page[page]
        C.log(f"  {page:<8}{q.w_perm_:>11.3f}{q.w_fade_:>9.3f}{q.phi_:>11.2f}"
              f"{float(q.rho(1)):>15.3f}{ret_by_page[page]:>13.3f}")
    C.log("")
    C.log("  The permanent part GROWS with the page, from nothing at the start of")
    C.log("  the window to a quarter at the end, because an early page's replay")
    C.log("  cannot reach far enough to tell a standing misjudgement from one")
    C.log("  that fades. That is a fact about how much evidence each date had,")
    C.log("  and using the last page's answer everywhere -- which is what the")
    C.log("  first version of this runner did -- would hand a 2015 contract a")
    C.log("  parameter fitted on outcomes through 2024.")
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
        page, mu, sg, pp = seasons[cid]
        k = SIM.dollar_factor(r)
        flat = SIM.draw_paths(mu, np.zeros_like(sg), np.ones_like(pp),
                              np.zeros(1001), pers_by_page[page], 8, rng)
        got = SIM.contract_value(lines[r["cut"]], r, flat.mean(axis=1),
                                 flat[:, 0], k)
        # AGAINST THE CURRENCY'S OWN value(), not against this file's pricing
        # helper on both sides. The first version called the same helper twice
        # and would have passed with a shared pricing bug in it; the review
        # made that point and it is right.
        row = r.copy()
        row["war_per_season"] = float(np.mean(mu))
        row["war_year1"] = float(mu[0])
        row["rfa_x_war"] = float(row["is_RFA"]) * float(np.mean(mu))
        want = float(lines[r["cut"]].value(pd.DataFrame([row])).iloc[0])
        worst = max(worst, float(np.max(np.abs(got - want))))
    assert worst < 1e-3, f"the identity fails by ${worst:,.6f}"
    C.log(f"    300 contracts against ProductionCurrency.value, largest gap "
          f"${worst:.2e}  [PASS]")
    C.log("")

    # ---- 3. simulate ------------------------------------------------------
    t0 = time.time()
    out = []
    for cid in ids:
        r = pt[pt[KEY] == cid].iloc[0]
        page, mu, sg, pp = seasons[cid]
        k = SIM.dollar_factor(r)
        sp, pers, r_ret = calibration_for(page, spreads, pers_by_page, ret_by_page)
        shape = sp.zs_
        # COMMON DRAWS across every variant of this contract, so a difference
        # between two of them is the design and not the luck of two samples.
        normals = rng.standard_normal((N_PATHS, len(mu)))
        u_part = rng.random((N_PATHS, len(mu)))

        paths = SIM.draw_paths(mu, sg, pp, shape, pers, N_PATHS, rng,
                               r_return=r_ret, normals=normals, u_part=u_part)
        wps = paths.mean(axis=1)
        val = SIM.contract_value(lines[r["cut"]], r, wps, paths[:, 0], k)
        sur = val - float(r["cost"])

        # WHAT THE CROSS-SEASON DEPENDENCE OF THE FORECAST'S MISS IS WORTH.
        # Only that: participation stays exactly as it is in both arms, so the
        # seasons are NOT independent in this counterfactual and the label says
        # conditional-error dependence rather than independence.
        ind = SIM.draw_paths(mu, sg, pp, shape, INDEP, N_PATHS, rng,
                             r_return=r_ret, normals=normals, u_part=u_part)
        sur_ind = SIM.contract_value(lines[r["cut"]], r, ind.mean(axis=1),
                                     ind[:, 0], k) - float(r["cost"])

        # AND WHAT ALLOWING A RETURN IS WORTH, against the absorbing exit the
        # first version shipped as though it were free.
        # Same uniforms here too, though the transition rules differ, so the
        # indicators legitimately diverge where a return would have happened.
        abso = SIM.draw_paths(mu, sg, pp, shape, pers, N_PATHS, rng,
                              r_return=0.0, normals=normals, u_part=u_part)
        sur_abs = SIM.contract_value(lines[r["cut"]], r, abso.mean(axis=1),
                                     abso[:, 0], k) - float(r["cost"])

        _, clipped = SIM.participation_path(pp, u_part, r_ret)
        # A ONE-SEASON TERM HAS NO DEPENDENCE TO IMPOSE, so on shared draws the
        # two arms must agree PATH BY PATH, not to a tolerance. Asserted rather
        # than reported: it is an identity, and the previous version printed it
        # as a rounded zero while the arms actually differed.
        if len(mu) == 1:
            assert np.array_equal(paths, ind), (
                "a one-season term differs between the dependence arms on "
                "shared draws, so the draws are not shared")
        out.append({KEY: cid, "page": page, "term": len(mu),
                    "war_per_season": r["war_per_season"],
                    "surplus_point": float(r["surplus_point"]),
                    "surplus_sim": float(sur.mean()),
                    "sim_sd": float(sur.std()),
                    "sim_p10": float(np.quantile(sur, 0.10)),
                    "sim_p90": float(np.quantile(sur, 0.90)),
                    "p_negative": float((sur < 0).mean()),
                    "sd_indep_errors": float(sur_ind.std()),
                    "surplus_absorbing": float(sur_abs.mean()),
                    "sd_absorbing": float(sur_abs.std()),
                    "wps_point": float(r["war_per_season"]),
                    "wps_sim": float(wps.mean()),
                    "marginal_clipped": clipped})
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
              f"{g['sd_indep_errors'].mean()/1e6:>15.2f}"
              f"{100*(g['sim_sd'].mean()/max(g['sd_indep_errors'].mean(), 1) - 1):>11.0f}%")
    C.log("")
    C.log("  WHAT THE MISS'S CROSS-SEASON DEPENDENCE IS WORTH. The last two")
    C.log("  columns redraw the SAME contracts on the SAME random draws with")
    C.log("  that dependence removed. PARTICIPATION IS UNCHANGED IN BOTH ARMS,")
    C.log("  so the seasons are not independent there and the column is not an")
    C.log("  independence counterfactual -- it isolates the conditional")
    C.log("  performance error and nothing else. The comparison is within a")
    C.log("  contract, because long deals go to better players with wider bands.")
    C.log("")
    C.log("  A point valuation is not wrong to average under dependence: an")
    C.log("  expectation averages whatever the dependence is. What dependence")
    C.log("  changes is the SPREAD, and the value of a path once the price line")
    C.log("  stops being straight.")
    C.log("")

    clip = int((s["marginal_clipped"] > 0).sum())
    C.log("  RETURNS, AND WHAT THE ABSORBING EXIT COST. The first version made")
    C.log("  an absence permanent and argued that nothing was lost because no")
    C.log("  term asks for a probability of playing that RISES. That does not")
    C.log("  follow: a marginal can fall from 90% to 70% while one path in ten")
    C.log("  is a man coming back. The path now allows a return at a rate")
    C.log("  estimated from seasons before each decision date, and the absorbing")
    C.log("  version is reported beside it as the sensitivity it always was.")
    C.log("")
    C.log(f"  {'term':<8}{'n':>6}{'mean, returns':>15}{'mean, absorbing':>17}"
          f"{'sd, returns':>13}{'sd, absorbing':>15}")
    for L, g in s.groupby("term"):
        if len(g) < 15:
            continue
        C.log(f"  {int(L)} yr{'':<3}{len(g):>6}{g['surplus_sim'].mean()/1e6:>15.2f}"
              f"{g['surplus_absorbing'].mean()/1e6:>17.2f}"
              f"{g['sim_sd'].mean()/1e6:>13.2f}{g['sd_absorbing'].mean()/1e6:>15.2f}")
    C.log("")
    C.log(f"  {clip} of {len(s)} terms needed an exit probability clipped into")
    C.log("  [0,1] to hold the marginal, so for those the model's own")
    C.log("  probability of playing is not reproduced exactly.")
    C.log("")

    flips = int((np.sign(s["surplus_point"]) != np.sign(s["surplus_sim"])).sum())
    C.log(f"  SIGN CHANGES: {flips} of {len(s)} individual contracts change sign")
    C.log("  between the point valuation and the simulation. The first version of")
    C.log("  this report said there were none, which was read off the tier means")
    C.log("  and was false of the contracts. Group means are a different")
    C.log("  statement from contracts and the two are reported apart.")
    C.log("")

    # The model the paths were drawn from, by name, so the integration can
    # refuse a market comparison built on a different one before comparing
    # a single number (run_valuation_integration.py).
    s["model_class"] = LEADER.__name__
    s.to_csv(C.out_path("npv_simulation.csv"), index=False)
    C.log(f"  wrote {C.out_path('npv_simulation.csv').name}")
    C.write_log("npv_simulation_run_log.txt")


if __name__ == "__main__":
    main()
