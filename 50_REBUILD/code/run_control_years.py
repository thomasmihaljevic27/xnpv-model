"""run_control_years.py -- the value of the seasons after the contract ends.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 5, the RFA walk-away and control
years. Development start years only; the reserved cohorts are refused by the
guard. Nothing adopted, and no production file is written.

WHAT IT ANSWERS
    1. How much of the development sample owns control years at all, and what
       the qualifying-offer schedule costs.
    2. What those years are worth per path, under four stopping rules that
       differ ONLY in what the club is allowed to know when it decides.
    3. Where the option value sits -- the gap between deciding in advance and
       deciding as you go -- which is the part a point valuation cannot reach.
    4. What it does to the contract's surplus, reported beside the surplus
       without it rather than folded into it.

WHAT IT DOES NOT DO
    It does not adopt. Every comparison already run in this tree values a
    contract to its expiry, and moving the headline surplus would silently
    re-date all of them. The control value is written as its own column and
    the runner reports the contract's surplus both ways.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import control_years as CY
import npv_simulation as SIM
from contract_price_model import contract_sample
from player_season_table import build as build_table
from production_currency import ProductionCurrency
from run_npv_simulation import (LEADER, KEY, N_PATHS, birthdate_source,
                                calibration_for, forecast_blocks, page_dependence,
                                prep, term_seasons)
from contract_price_model import attach_forecasts

SCRIPT_VERSION = "1.0"


def control_map(sample: pd.DataFrame) -> dict:
    """Which seasons each contract still owns after it ends."""
    out = {}
    for r in sample.itertuples():
        yrs = CY.control_span(r.expiry_status, r.end_yr, r.ufa_year)
        if yrs:
            out[int(r.contract_id)] = yrs
    return out


def qo_base_divergence(sample: pd.DataFrame, cmap: dict) -> None:
    """What using the average annual value as the offer's base salary costs.

    The formula runs off the final year's base salary and this tree's source
    carries an average. Production joins a per-season salary from the clause
    feed for two thirds of contracts, so where that file is present the
    substitution can be measured instead of asserted. Read-only, and skipped
    without complaint when the file is not there.
    """
    f = Path(C.PROD_OUTPUT_DIR) / "contract_season_spine.csv"
    if not f.exists():
        C.log("  (the season spine is not here, so the size of that")
        C.log("   substitution is not measured this run)")
        C.log("")
        return
    sp = pd.read_csv(f)
    sp = sp[sp["contract_id"].isin(cmap)]
    if sp.empty:
        return
    final = (sp.sort_values("season_start").groupby("contract_id").tail(1)
             [["contract_id", "cs_nhl_salary", "pp_aav"]])
    j = final.merge(sample[["contract_id", "aav"]], on="contract_id", how="inner")
    have = j[j["cs_nhl_salary"].notna()].copy()
    if have.empty:
        return
    have["ratio"] = have["cs_nhl_salary"] / have["aav"]
    C.log(f"  measured against the season spine on {len(have)} of the "
          f"{len(cmap)} contracts that own control years:")
    C.log(f"    final-year salary equals the average within 1%      "
          f"{int((have['ratio'].between(0.99, 1.01)).sum()):>5}")
    C.log(f"    final salary ABOVE the average (offer understated)  "
          f"{int((have['ratio'] > 1.01).sum()):>5}")
    C.log(f"    final salary BELOW the average (offer overstated)   "
          f"{int((have['ratio'] < 0.99).sum()):>5}")
    C.log(f"    median ratio {have['ratio'].median():.3f}, "
          f"90th percentile {have['ratio'].quantile(0.9):.3f}")
    C.log("  A front-loaded deal's last salary sits above its average, so the")
    C.log("  average makes the offer too cheap and the control year too")
    C.log("  valuable. That is the direction of this approximation.")
    C.log("")


def check_against_production() -> None:
    """The qualifying-offer bands here against production's own, so the two
    cannot drift. Production's module is heavy and needs the vendor workbook,
    so this is attempted and reported rather than required."""
    try:
        sys.path.insert(0, str(C.PROD_CODE_DIR))
        import warnings
        warnings.filterwarnings("ignore")
        import rfa_terminal_value as RTV
    except Exception as exc:                      # noqa: BLE001 - reported
        C.log(f"  (production's own module did not import here: "
              f"{type(exc).__name__}; the bands are checked only against this")
        C.log("   file's own self-test)")
        C.log("")
        return
    rng = np.random.default_rng(20260917)
    worst, n = 0.0, 0
    for _ in range(4000):
        sal = float(rng.uniform(5e5, 9e6))
        hit = sal * float(rng.uniform(0.6, 1.4))
        yr = int(rng.integers(2016, 2031))
        s20 = bool(rng.integers(0, 2))
        a = CY.qualifying_offer(sal, hit, yr, s20)
        b = float(RTV.qualifying_offer(sal, hit, yr, s20))
        worst = max(worst, abs(a - b)); n += 1
    C.log(f"  the offer bands agree with production's implementation on all "
          f"{n} random cases, largest difference ${worst:,.2f}")
    assert worst < 1e-6, "the rebuild's QO bands have drifted from production's"
    C.log("")


def leakage_check(g: np.ndarray, mat: np.ndarray, shape: np.ndarray) -> None:
    """The club's expectation of a control season cannot move when the seasons
    it has not seen yet are replaced by different draws.

    This is the whole claim the informed rule rests on, so it is tested rather
    than argued: the conditional law is recomputed with every season from the
    decision onward scrambled, and it has to come back bit for bit. A rule
    that peeked would move.
    """
    # ITS OWN GENERATOR. A diagnostic that draws from the run's stream moves
    # every valuation after it, which would make the run's figures depend on
    # whether a check was switched on.
    rng = np.random.default_rng(20260918)
    T = mat.shape[0]
    for j in range(min(T, 4)):
        base, _ = CY.conditional_nodes(g, mat, j, shape)
        h = g.copy()
        h[:, j:] = rng.standard_normal(h[:, j:].shape)
        alt, _ = CY.conditional_nodes(h, mat, j, shape)
        gap = float(np.abs(base - alt).max())
        assert gap == 0.0, (f"the informed rule moves by {gap:.3g} when the "
                            f"future is scrambled at season {j}: it is "
                            f"reading the season it decides about")
    C.log("  the club's expectation is identical when every season from the")
    C.log("  decision onward is redrawn, at each of the first four horizons.")
    C.log("  Asserted bit for bit, not to a tolerance.")
    C.log("")


def against_production(ok: pd.DataFrame) -> None:
    """The same right, as production prices it.

    Production walks its single projected path and truncates at the first
    control year whose projected surplus goes negative, which is the DECLARED
    rule here and nothing else. The two are not on the same information date
    -- production discounts to 1 July of the first contract season and this
    discounts to the signing -- so the levels are not expected to match and
    the comparison is about whether the same contracts carry the right and
    whether they rank alike.
    """
    f = Path(C.PROD_OUTPUT_DIR) / "contract_npv_spine.csv"
    if not f.exists():
        return
    sp = pd.read_csv(f)[["contract_id", "npv_terminal"]]
    j = ok.merge(sp, on=KEY, how="inner")
    if j.empty:
        return
    C.log("AGAINST PRODUCTION'S OWN TERMINAL VALUE. Production prices the same")
    C.log("right by truncating one projected path at the first negative control")
    C.log("year, which is the declared rule here. Different information dates,")
    C.log("so the levels are not expected to agree.")
    C.log("")
    C.log(f"  {len(j)} of the {len(ok)} contracts with control years are also in")
    C.log("  the production spine")
    C.log(f"    production terminal value, mean       "
          f"{j['npv_terminal'].mean()/1e6:>8.3f} $M")
    C.log(f"    declared rule here, mean              "
          f"{j['ctrl_declared'].mean()/1e6:>8.3f} $M")
    C.log(f"    deciding as it goes, mean             "
          f"{j['ctrl_informed'].mean()/1e6:>8.3f} $M")
    C.log(f"    rank correlation, production vs declared "
          f"{j['npv_terminal'].corr(j['ctrl_declared'], method='spearman'):>6.3f}")
    C.log(f"    rank correlation, production vs informed "
          f"{j['npv_terminal'].corr(j['ctrl_informed'], method='spearman'):>6.3f}")
    n0 = int((j["npv_terminal"].abs() < 1.0).sum())
    C.log(f"    production prices {n0} of them at zero, where this tree finds a")
    C.log(f"    right worth {j.loc[j['npv_terminal'].abs() < 1.0, 'ctrl_informed'].mean()/1e6:.3f} $M on average")
    C.log("")


def main() -> None:
    C.banner("run_control_years.py", SCRIPT_VERSION)
    path, how = birthdate_source()
    table = build_table(birthdate_csv=path, verbose=False)
    C.log(f"  birthdates: {how}")
    C.log("")

    sample = contract_sample()
    dev = [int(y) for y in sorted(sample["start_yr"].dropna().unique())
           if int(y) not in C.CONFIRMATORY_START_YEARS]
    cohorts = C.check_market_cohorts(dev, "run_control_years")

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

    cmap = control_map(sample)
    own = [int(c) for c in pt[KEY] if int(c) in cmap]
    C.log("WHO OWNS CONTROL YEARS. A contract that expires with the player")
    C.log("still restricted leaves the club holding his rights until he is")
    C.log("unrestricted. A contract that expires into unrestricted free agency")
    C.log("leaves it holding nothing, and so does one the club has already")
    C.log("declined to qualify.")
    C.log("")
    st = (sample[sample[KEY].isin(pt[KEY])]["expiry_status"]
          .value_counts().to_dict())
    for k in ("RFA", "UFA", "UFA no QO"):
        C.log(f"    {k:<12}{st.get(k, 0):>6}")
    C.log("")
    C.log(f"  {len(own)} of {len(pt)} development contracts own at least one")
    C.log("  control year. By how many, and by the contract's own term:")
    tab = pd.DataFrame({KEY: own})
    tab["n_ctrl"] = [len(cmap[c]) for c in own]
    tab = tab.merge(pt[[KEY, "length"]], on=KEY, how="left")
    C.log(f"    {'control yrs':<13}{'contracts':>10}")
    for n, g in tab.groupby("n_ctrl"):
        C.log(f"    {int(n):<13}{len(g):>10}")
    C.log("")
    C.log(f"    {'contract term':<15}{'own control yrs':>17}")
    for L, g in tab.groupby("length"):
        C.log(f"    {int(L):<15}{len(g):>17}")
    C.log("")

    C.log("THE QUALIFYING OFFER. The CBA formula off the last salary, iterated,")
    C.log("floored at the league minimum, with the 2026 bands from 2026 on.")
    check_against_production()
    qo_base_divergence(sample, cmap)

    # ---- the forecast over the term AND the control years ------------------
    def wanted(r):
        return term_seasons(r) + cmap.get(int(r.contract_id), [])

    t0 = time.time()
    blocks, spreads = forecast_blocks(sample, table, seasons_for=wanted)
    pers_by_page, ret_by_page = page_dependence(spreads, table)
    C.log(f"  {len(blocks)} contracts carry a band over the term and the")
    C.log(f"  control years together ({time.time() - t0:.0f}s)")
    C.log("")

    rng = np.random.default_rng(20260917)
    rows, checked_leakage = [], False
    for cid in own:
        if cid not in blocks:
            continue
        r = pt[pt[KEY] == cid].iloc[0]
        page, mu, sg, pp, yrs = blocks[cid]
        ctrl = cmap[cid]
        term = [y for y in yrs if y not in ctrl]
        if len(term) != int(r["length"]) or len(yrs) != len(term) + len(ctrl):
            # A control year the forecast could not reach is not quietly
            # dropped to a shorter schedule; the contract is skipped and
            # counted, because a half-priced right is worse than none.
            rows.append({KEY: cid, "status": "partial band"})
            continue
        sp, pers, r_ret = calibration_for(page, spreads, pers_by_page, ret_by_page)
        shape = sp.zs_
        T = len(yrs)
        normals = rng.standard_normal((N_PATHS, T))
        u_part = rng.random((N_PATHS, T))
        paths, g, played = SIM.draw_paths(
            mu, sg, pp, shape, pers, N_PATHS, rng, r_return=r_ret,
            normals=normals, u_part=u_part, return_parts=True)
        e_sched, _ = SIM.exit_schedule(pp, r_ret)
        if not checked_leakage:
            C.log("CAN THE CLUB SEE THE SEASON IT IS DECIDING ABOUT?")
            leakage_check(g, pers.matrix(T), shape)
            checked_leakage = True
        vals = CY.value_paths(lines[r["cut"]], r, ctrl, mu, sg, pp, shape,
                              pers.matrix(T), paths, g, played, e_sched,
                              r_ret, offset=len(term))
        row = {KEY: cid, "status": "ok", "n_ctrl": len(ctrl),
               "term": int(r["length"]), "start_yr": int(r["start_yr"]),
               "page": int(page), "qo_first": float(vals["_qo"][0]),
               "qo_total": float(vals["_qo"].sum()),
               "point_first": float(vals["_point_surplus"][0]),
               "taken_informed": float(vals["_taken_informed"].mean()),
               "surplus_contract": float(r["surplus_point"])}
        for rule in CY.RULES:
            row[f"ctrl_{rule}"] = float(vals[rule].mean())
            row[f"ctrl_{rule}_sd"] = float(vals[rule].std(ddof=1))
        rows.append(row)
    out = pd.DataFrame(rows)
    ok = out[out["status"] == "ok"].copy()
    skipped = int((out["status"] != "ok").sum())
    C.log(f"  {len(ok)} contracts priced over their control years, "
          f"{skipped} skipped for a band that did not reach every one")
    C.log("")

    # ---- the guards, before any table is read ------------------------------
    # THE CEILING IS A CEILING. A club that knew the whole path and could only
    # choose when to stop would do at least as well as any rule here, and at
    # least as well as walking away at once, so the oracle is non-negative and
    # nothing beats it. A rule that did would be reading the season it is
    # deciding about. Asserted, not printed.
    neg = ok.loc[ok["ctrl_oracle"] < -1.0, KEY].tolist()
    assert not neg, f"the ceiling is negative on {len(neg)}: {neg[:6]}"
    for rule in ("committed", "declared", "informed"):
        worse = ok.loc[ok[f"ctrl_{rule}"] > ok["ctrl_oracle"] + 1.0, KEY].tolist()
        assert not worse, (f"the {rule} rule beats knowing the whole path on "
                           f"{len(worse)} contracts: {worse[:6]}")
    C.log("  nothing beats the club that knew the whole path, and that ceiling")
    C.log("  is never below walking away at once. Asserted, not printed.")
    C.log("")
    # DECIDING WELL IS NOT THE SAME AS NOT LOSING. A club that decides in
    # advance, or on what it knows at the time, can still tender a player who
    # then disappoints, so those two rules are allowed to come out negative
    # and how often they do is reported rather than asserted away.
    for rule in ("declared", "informed"):
        n = int((ok[f"ctrl_{rule}"] < 0).sum())
        C.log(f"  the {rule} rule loses money on {n} of {len(ok)} contracts, "
              f"which is not a defect: it tenders on an expectation")
    C.log("")

    # ---- what the right is worth ------------------------------------------
    C.log("WHAT THE CONTROL YEARS ARE WORTH, $M a contract, by how many the")
    C.log("club holds. The four rules differ ONLY in what the club knows when")
    C.log("it decides: take every year; decide the schedule in advance off the")
    C.log("point projection (production's rule); decide each year on what the")
    C.log("path has shown so far; or see the season first.")
    C.log("")
    C.log(f"    {'control yrs':<13}{'n':>6}{'committed':>12}{'declared':>11}"
          f"{'informed':>11}{'oracle':>10}{'option worth':>14}")
    for n, g in ok.groupby("n_ctrl"):
        C.log(f"    {int(n):<13}{len(g):>6}"
              f"{g['ctrl_committed'].mean()/1e6:>12.3f}"
              f"{g['ctrl_declared'].mean()/1e6:>11.3f}"
              f"{g['ctrl_informed'].mean()/1e6:>11.3f}"
              f"{g['ctrl_oracle'].mean()/1e6:>10.3f}"
              f"{(g['ctrl_informed'] - g['ctrl_declared']).mean()/1e6:>14.3f}")
    C.log(f"    {'all':<13}{len(ok):>6}"
          f"{ok['ctrl_committed'].mean()/1e6:>12.3f}"
          f"{ok['ctrl_declared'].mean()/1e6:>11.3f}"
          f"{ok['ctrl_informed'].mean()/1e6:>11.3f}"
          f"{ok['ctrl_oracle'].mean()/1e6:>10.3f}"
          f"{(ok['ctrl_informed'] - ok['ctrl_declared']).mean()/1e6:>14.3f}")
    C.log("")
    C.log("  'option worth' is the last column against the declared schedule:")
    C.log("  what deciding as you go is worth over deciding in advance. It is")
    C.log("  the part of this asset a point valuation cannot reach, because a")
    C.log("  point valuation has one path and nothing to decide.")
    C.log("")
    C.log(f"  the club tables an offer in {ok['taken_informed'].mean():.2f} of "
          f"its {ok['n_ctrl'].mean():.2f} control years on average, deciding as")
    C.log("  it goes")
    C.log("")

    # ---- against the contract itself --------------------------------------
    C.log("AGAINST THE CONTRACT. The control years are reported beside the")
    C.log("contract's own surplus, not folded into it: every comparison already")
    C.log("run in this tree values a contract to its expiry, and moving the")
    C.log("headline would re-date all of them without saying so.")
    C.log("")
    C.log(f"    {'term':<8}{'n':>6}{'surplus $M':>13}{'control $M':>13}"
          f"{'with control':>14}{'control / total':>17}")
    for L, g in ok.groupby("term"):
        s0 = g["surplus_contract"].mean()
        cv = g["ctrl_informed"].mean()
        C.log(f"    {int(L)} yr{'':<3}{len(g):>6}{s0/1e6:>13.3f}{cv/1e6:>13.3f}"
              f"{(s0 + cv)/1e6:>14.3f}"
              f"{(cv / abs(s0 + cv) if abs(s0 + cv) > 1 else float('nan')):>17.2f}")
    C.log("  The last column is above one wherever the contract itself loses")
    C.log("  money: on a one-year deal the right to keep the player afterwards")
    C.log("  is worth more than the season the club just bought.")
    C.log("")

    against_production(ok)

    out.to_csv(C.out_path("control_years.csv"), index=False)
    C.log(f"  wrote {C.out_path('control_years.csv').name} "
          f"({len(out)} contracts, {out.shape[1]} columns)")
    C.write_log("control_years_run_log.txt")


if __name__ == "__main__":
    main()
