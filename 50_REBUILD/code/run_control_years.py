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

SCRIPT_VERSION = "2.0"


def control_map(sample: pd.DataFrame, by_age: bool = False) -> dict:
    """Which seasons each contract still owns after it ends.

    Eligibility decides it, never the expiry label the export records years
    later. `by_age` runs the same span off the age rule alone -- the season
    the player turns 27, which needs nothing but a birthdate -- as the
    sensitivity for the part of eligibility that accrued seasons decide.
    """
    out = {}
    for r in sample.itertuples():
        ufa = CY.ufa_year_by_age(r.birthdate) if by_age else r.ufa_year
        yrs = CY.control_span(r.end_yr, ufa)
        if yrs:
            out[int(r.contract_id)] = yrs
    return out


def eligibility_audit(sample: pd.DataFrame, pt: pd.DataFrame,
                      cmap: dict) -> None:
    """Where the export's eligibility year comes from, and what of it a club
    at the signing could have known.

    A player is unrestricted at 27 whatever else is true, and that year is
    fixed by his birthdate, so the club knows it the day it signs him. He can
    also get there earlier on seven accrued seasons, and a season accrues by
    being played -- so for a player short of seven at the signing, part of
    that route runs through seasons that had not happened yet.

    This says how much of the sample takes the early route, which is the size
    of the exposure. The run also prices the whole thing again on the age rule
    alone, which uses nothing but the birthdate, so the exposure is bounded
    rather than only described.
    """
    d = sample[sample[KEY].isin(pt[KEY])].copy()
    d["by_age"] = [CY.ufa_year_by_age(b) for b in d["birthdate"]]
    d["gap"] = pd.to_numeric(d["ufa_year"], errors="coerce") - d["by_age"]
    C.log("WHERE ELIGIBILITY COMES FROM. A player is unrestricted at 27 on the")
    C.log("age rule alone, which his birthdate fixes and the club knows the day")
    C.log("it signs him. Seven accrued seasons can get him there sooner, and a")
    C.log("season accrues by being played.")
    C.log("")
    C.log(f"    {'the export agrees with the age rule exactly':<50}"
          f"{int((d['gap'] == 0).sum()):>6}   "
          f"{100 * (d['gap'] == 0).mean():.1f}%")
    C.log(f"    {'earlier than the age rule (accrued seasons)':<50}"
          f"{int((d['gap'] < 0).sum()):>6}")
    C.log(f"    {'later than the age rule':<50}"
          f"{int((d['gap'] > 0).sum()):>6}")
    C.log("")
    C.log("  Never later, which is what the rule says: eligibility is the")
    C.log("  earlier of the two routes. The early ones are the exposure, and")
    C.log("  the run prices the whole sample again on the age rule alone to")
    C.log("  bound it.")
    C.log("")
    # WHAT THE OLD LABEL WOULD HAVE DONE. Kept as a count, because the label
    # is an outcome and this is the only place it may be looked at.
    lab = d[d[KEY].isin(cmap)]["expiry_status"].value_counts().to_dict()
    C.log("  Of the contracts that own control years on eligibility, the")
    C.log("  expiry the export eventually recorded -- an OUTCOME, and never an")
    C.log("  input to the rule:")
    for k in ("RFA", "UFA no QO", "UFA"):
        C.log(f"    {k:<14}{lab.get(k, 0):>6}")
    C.log("  The first version of this runner read that column and gave")
    C.log("  nothing to the 101 marked 'UFA no QO', on the grounds that the")
    C.log("  club had declined to qualify the player. It declines YEARS after")
    C.log("  the signing being valued, and it is the very decision the")
    C.log("  stopping rule exists to make.")
    C.log("")


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


def leakage_check(g: np.ndarray, mat: np.ndarray, shape: np.ndarray,
                  played: np.ndarray) -> None:
    """Two things the club must not be able to see, tested rather than argued.

    THE FUTURE. The seasons from the decision onward are replaced by different
    draws and the club's expectation has to come back bit for bit.

    WHAT IT WAS NEVER SHOWN. The misses of seasons the player spent out of the
    league exist inside the simulator and nobody ever saw them: watching a
    player miss a year tells you he missed it, not how well he would have
    played. Those are redrawn too, and the expectation has to be unmoved. The
    first version of this rule conditioned on them, and the review measured
    what that was worth -- the first control year's decision moved on 188 of
    252 contracts and 26,519 path decisions flipped.

    And one it MUST see, or the rule is vacuous: the misses of seasons he did
    play.
    """
    # ITS OWN GENERATOR. A diagnostic that draws from the run's stream moves
    # every valuation after it, which would make the run's figures depend on
    # whether a check was switched on.
    rng = np.random.default_rng(20260918)
    T = mat.shape[0]
    assert CY.shape_is_monotone(shape), (
        "the production shape is not monotone, so observing a played season's "
        "production is not the same as observing its miss and the observation "
        "model this rule states does not hold")
    moved = 0
    for j in range(min(T, 4)):
        base, _ = CY.conditional_nodes(g, mat, j, shape, played)
        fut = g.copy()
        fut[:, j:] = rng.standard_normal(fut[:, j:].shape)
        alt, _ = CY.conditional_nodes(fut, mat, j, shape, played)
        assert float(np.abs(base - alt).max()) == 0.0, (
            f"the club's expectation moves when the future is redrawn at "
            f"season {j}: it is reading the season it decides about")
        unseen = g.copy()
        mask = (played[:, :j] == 0)
        if mask.any():
            block = unseen[:, :j]
            block[mask] = rng.standard_normal(int(mask.sum()))
            unseen[:, :j] = block
            hid, _ = CY.conditional_nodes(unseen, mat, j, shape, played)
            assert float(np.abs(base - hid).max()) == 0.0, (
                f"the club's expectation moves when the misses of seasons he "
                f"did not play are redrawn at season {j}: it is using what it "
                f"was never shown")
        if j:
            seen = g.copy()
            seen[:, :j] = rng.standard_normal(seen[:, :j].shape)
            sw, _ = CY.conditional_nodes(seen, mat, j, shape, played)
            moved += int(float(np.abs(base - sw).max()) > 1e-9)
    assert moved == min(T, 4) - 1, (
        "the expectation ignores the observed past too, so the rule is not "
        "using the information it claims to")
    C.log("  redrawing every season from the decision onward moves nothing,")
    C.log("  bit for bit. Redrawing the misses of seasons he did not play")
    C.log("  moves nothing either -- the club never saw them. Redrawing the")
    C.log("  seasons he DID play moves it at every horizon, so the rule is")
    C.log("  using what it claims and only that.")
    C.log("")


def against_production(ok: pd.DataFrame) -> None:
    """The same right, as production prices it.

    Production walks its single projected path and truncates at the first
    control year whose projected surplus goes negative, which is the
    `production_point` rule here and nothing else -- not the declared rule,
    which prices the same way the informed one does so that the two can be
    compared. The two are not on the same information date
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
    C.log(f"    production's own rule, rebuilt here    "
          f"{j['ctrl_production_point'].mean()/1e6:>8.3f} $M")
    C.log(f"    deciding in advance, priced alike     "
          f"{j['ctrl_declared'].mean()/1e6:>8.3f} $M")
    C.log(f"    deciding as it goes, mean             "
          f"{j['ctrl_informed'].mean()/1e6:>8.3f} $M")
    C.log(f"    rank correlation, production vs its rule  "
          f"{j['npv_terminal'].corr(j['ctrl_production_point'], method='spearman'):>6.3f}")
    C.log(f"    rank correlation, production vs informed "
          f"{j['npv_terminal'].corr(j['ctrl_informed'], method='spearman'):>6.3f}")
    n0 = int((j["npv_terminal"].abs() < 1.0).sum())
    C.log(f"    production prices {n0} of them at zero, where this tree finds a")
    C.log(f"    right worth {j.loc[j['npv_terminal'].abs() < 1.0, 'ctrl_informed'].mean()/1e6:.3f} $M on average")
    C.log("")


def price_span(span: dict, sample, table, pt, lines, label: str,
               check_leakage: bool = False) -> pd.DataFrame:
    """Price every contract's control years under one eligibility rule.

    Called twice: once on the export's own eligibility year, once on the age
    rule alone. The second uses nothing but a birthdate, so the difference
    between them is the whole exposure to eligibility that accrued seasons
    decide -- bounded rather than described.
    """
    def wanted(r):
        return term_seasons(r) + span.get(int(r.contract_id), [])

    t0 = time.time()
    blocks, spreads = forecast_blocks(sample, table, seasons_for=wanted)
    pers_by_page, ret_by_page = page_dependence(spreads, table)
    C.log(f"  [{label}] {len(blocks)} contracts carry a band over the term and")
    C.log(f"  the control years together ({time.time() - t0:.0f}s)")
    C.log("")

    rng = np.random.default_rng(20260917)
    rows, checked = [], not check_leakage
    for cid in [int(c) for c in pt[KEY] if int(c) in span]:
        if cid not in blocks:
            continue
        r = pt[pt[KEY] == cid].iloc[0]
        page, mu, sg, pp, yrs = blocks[cid]
        ctrl = span[cid]
        term = [y for y in yrs if y not in ctrl]
        if len(term) != int(r["length"]) or len(yrs) != len(term) + len(ctrl):
            # A control year the forecast could not reach is not quietly
            # dropped to a shorter schedule; the contract is skipped and
            # counted, because a half-priced right is worse than none.
            rows.append({KEY: cid, "status": "partial band"})
            continue
        sp, pers, r_ret = calibration_for(page, spreads, pers_by_page,
                                          ret_by_page)
        shape = sp.zs_
        T = len(yrs)
        normals = rng.standard_normal((N_PATHS, T))
        u_part = rng.random((N_PATHS, T))
        paths, g, played = SIM.draw_paths(
            mu, sg, pp, shape, pers, N_PATHS, rng, r_return=r_ret,
            normals=normals, u_part=u_part, return_parts=True)
        e_sched, _ = SIM.exit_schedule(pp, r_ret)
        if not checked:
            C.log("CAN THE CLUB SEE WHAT IT HAS NOT BEEN SHOWN?")
            leakage_check(g, pers.matrix(T), shape, played)
            checked = True
        vals = CY.value_paths(lines[r["cut"]], r, ctrl, mu, sg, pp, shape,
                              pers.matrix(T), paths, g, played, e_sched,
                              r_ret, offset=len(term))
        row = {KEY: cid, "status": "ok", "n_ctrl": len(ctrl),
               "uncond_first": float(vals["_uncond_surplus"][0]),
               "term": int(r["length"]), "start_yr": int(r["start_yr"]),
               "page": int(page), "qo_first": float(vals["_qo"][0]),
               "qo_total": float(vals["_qo"].sum()),
               "point_first": float(vals["_point_surplus"][0]),
               "taken_informed": float(vals["_taken_informed"].mean()),
               "surplus_contract": float(r["surplus_point"])}
        for rule in CY.RULES:
            row[f"ctrl_{rule}"] = float(vals[rule].mean())
        row["ctrl_informed_sd"] = float(vals["informed"].std(ddof=1))
        rows.append(row)
    return pd.DataFrame(rows)


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
    C.log("WHO OWNS CONTROL YEARS. A club holds the player's rights from the")
    C.log("season after the contract until the season before he is")
    C.log("unrestricted. That is eligibility, and it is all this reads: what")
    C.log("the club eventually DID with the rights is an outcome.")
    C.log("")
    eligibility_audit(sample, pt, cmap)
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
        return term_seasons(r) + span.get(int(r.contract_id), [])

    out = price_span(cmap, sample, table, pt, lines,
                     "eligibility", check_leakage=True)
    ok = out[out["status"] == "ok"].copy()
    skipped = int((out["status"] != "ok").sum())
    C.log(f"  {len(ok)} contracts priced over their control years, "
          f"{skipped} skipped for a band that did not reach every one")
    C.log("")

    # ---- the guards, before any table is read ------------------------------
    # THE CEILING IS A CEILING. A club that knew the whole path and could only
    # choose when to stop does at least as well as any rule here and at least
    # as well as walking away at once. Anything that beat it would be reading
    # the season it is deciding about. Asserted, not printed.
    neg = ok.loc[ok["ctrl_hindsight"] < -1.0, KEY].tolist()
    assert not neg, f"the ceiling is negative on {len(neg)}: {neg[:6]}"
    for rule in ("committed", "production_point", "declared",
                 "informed_myopic", "informed"):
        worse = ok.loc[ok[f"ctrl_{rule}"] > ok["ctrl_hindsight"] + 1.0,
                       KEY].tolist()
        assert not worse, (f"the {rule} rule beats knowing the whole path on "
                           f"{len(worse)} contracts: {worse[:6]}")
    C.log("  nothing beats the club that knew the whole path, and that ceiling")
    C.log("  is never below walking away at once. Asserted, not printed.")
    C.log("")
    # DECIDING WELL IS NOT THE SAME AS NOT LOSING. A club deciding on an
    # expectation can tender a player who then disappoints, so these rules are
    # allowed to come out negative and how often they do is reported rather
    # than asserted away.
    for rule in ("declared", "informed"):
        n = int((ok[f"ctrl_{rule}"] < 0).sum())
        C.log(f"  the {rule} rule loses money on {n} of {len(ok)} contracts, "
              f"which is not a defect: it tenders on an expectation")
    C.log("")

    # ---- what the right is worth ------------------------------------------
    C.log("WHAT THE CONTROL YEARS ARE WORTH, $M a contract. Each rule differs")
    C.log("from the one before it in ONE thing, so a difference between two of")
    C.log("them means something:")
    C.log("")
    C.log("    take every year        no right at all, the obligation")
    C.log("    production's rule      price of the mean, stop at the first loss")
    C.log("    decide in advance      expected price, no path seen, but the")
    C.log("                           later years counted")
    C.log("    myopic, informed       the path's observed history, first loss")
    C.log("    decide as you go       the same history, later years counted")
    C.log("    knew the path          the ceiling")
    C.log("")
    cols = [("committed", "take all"), ("production_point", "production"),
            ("declared", "in advance"), ("informed_myopic", "myopic"),
            ("informed", "as you go"), ("hindsight", "hindsight")]
    head = f"    {'control yrs':<13}{'n':>5}"
    for _, lab in cols:
        head += f"{lab:>12}"
    C.log(head)
    for n, g in list(ok.groupby("n_ctrl")) + [("all", ok)]:
        line = (f"    {str(n):<13}{len(g):>5}" if n != "all"
                else f"    {'all':<13}{len(g):>5}")
        for rule, _ in cols:
            line += f"{g[f'ctrl_{rule}'].mean()/1e6:>12.3f}"
        C.log(line)
    C.log("")
    voi = (ok["ctrl_informed"] - ok["ctrl_declared"]).mean() / 1e6
    vcont = (ok["ctrl_informed"] - ok["ctrl_informed_myopic"]).mean() / 1e6
    C.log("  TWO DIFFERENCES THAT MEAN SOMETHING, because only one thing")
    C.log("  changes across each:")
    C.log(f"    seeing the path so far, pricing and decision logic held"
          f"{voi:>10.3f} $M")
    C.log(f"    counting the later years, information held         "
          f"{vcont:>10.3f} $M")
    C.log("")
    C.log("  AND ONE THAT DOES NOT, kept only because it is the comparison the")
    C.log("  first version of this runner reported as the value of deciding as")
    C.log("  you go. Production's rule differs from the informed one in BOTH")
    C.log("  ways AND in pricing the mean rather than averaging the price, so")
    C.log("  the gap between them is a mixture and not an option premium:")
    C.log(f"    deciding as you go, against production's rule       "
          f"{(ok['ctrl_informed'] - ok['ctrl_production_point']).mean()/1e6:>9.3f} $M")
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

    # ---- how much of this rests on eligibility we could not have known -----
    C.log("THE SAME THING PRICED ON THE AGE RULE ALONE. A player is")
    C.log("unrestricted at 27 whatever else happens, and his birthdate fixes")
    C.log("that year, so a club knows it the day it signs him. Seven accrued")
    C.log("seasons can get him there sooner, and for a player short of seven")
    C.log("at the signing that route runs partly through seasons not yet")
    C.log("played. Pricing the whole sample again on the age rule alone bounds")
    C.log("what the export's eligibility year is doing.")
    C.log("")
    alt = price_span(control_map(sample, by_age=True), sample, table, pt,
                     lines, "age rule")
    alt_ok = alt[alt["status"] == "ok"]
    j = ok.merge(alt_ok[[KEY, "n_ctrl", "ctrl_informed"]], on=KEY, how="outer",
                 suffixes=("", "_age"))
    C.log(f"    {'contracts owning control years, on eligibility':<50}"
          f"{len(ok):>6}")
    C.log(f"    {'the same, on the age rule alone':<50}{len(alt_ok):>6}")
    C.log(f"    {'control years each, eligibility':<50}"
          f"{ok['n_ctrl'].mean():>6.2f}")
    C.log(f"    {'control years each, age rule':<50}"
          f"{alt_ok['n_ctrl'].mean():>6.2f}")
    C.log(f"    {'deciding as you go, eligibility  $M':<50}"
          f"{ok['ctrl_informed'].mean()/1e6:>6.3f}")
    C.log(f"    {'deciding as you go, age rule     $M':<50}"
          f"{alt_ok['ctrl_informed'].mean()/1e6:>6.3f}")
    both = j.dropna(subset=["ctrl_informed", "ctrl_informed_age"])
    C.log(f"    {'on the contracts in both, the difference $M':<50}"
          f"{(both['ctrl_informed_age'] - both['ctrl_informed']).mean()/1e6:>6.3f}")
    C.log("")
    C.log("  The age rule gives the club MORE years, because it never brings")
    C.log("  eligibility forward, so it is an upper bound on the window rather")
    C.log("  than a neutral alternative. What it bounds is how much of the")
    C.log("  answer rests on an eligibility year the signing might not have")
    C.log("  known in full.")
    C.log("")

    out.to_csv(C.out_path("control_years.csv"), index=False)
    C.log(f"  wrote {C.out_path('control_years.csv').name} "
          f"({len(out)} contracts, {out.shape[1]} columns)")
    C.write_log("control_years_run_log.txt")


if __name__ == "__main__":
    main()
