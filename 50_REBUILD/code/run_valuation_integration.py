"""run_valuation_integration.py -- one contract-level table, all the way through.

EXPERIMENTAL (50_REBUILD). Development start years only. Nothing adopted.

WHY THIS EXISTS
    The rebuild's dollar answers are spread across three runners. The market
    comparison produces a surplus per contract under five forecasts; the path
    simulation produces a distribution around one of them; production's own
    forecast is priced in a third place. Reading them together has meant
    joining CSVs by hand, and a join done by hand is a join done differently
    each time.

    This is the single artifact everything downstream should read: one row per
    contract, carrying what the contract cost, what each forecast says it is
    worth, and what the distribution around the adopted one looks like.

WHAT IT IS NOT
    Not the reconciliation. The plan asks for full-chain movement against the
    PRODUCTION SPINE, contract by contract, and the spine is production's own
    contract NPV rather than production's forecast repriced here. Building it
    needs `goalie_value_spine_v2.csv`: `contract_npv.py` prices both positions
    and reads the goalie spine at startup, so the skater half cannot be run
    without it. Every other production input is now present and its guards
    reproduce -- the locked regression at Stage 0a and 0b, 6,892 priced skater
    rows, and the k=0 identity at $0.00.

    When that file arrives this runner gains one more column and the
    reconciliation is a comparison within it rather than another join.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C

SCRIPT_VERSION = "1.2"

KEY = "contract_id"
ADOPTED = "the adopted candidate"

# What each source contributes. Named here rather than inline so the schema of
# the artifact is readable in one place.
FROM_SENSITIVITY = ["term", "length", "is_RFA", "is_D", "start_yr", "end_yr",
                    "signed", "aav", "cap_share", "war_per_season", "war_year1",
                    "cost", "value", "surplus", "surplus_free", "fixed_group"]
FROM_SIMULATION = ["surplus_sim", "sim_sd", "sim_p10", "sim_p90", "p_negative",
                   "sd_indep_errors", "surplus_absorbing", "page"]


def main() -> None:
    C.banner("run_valuation_integration.py", SCRIPT_VERSION)

    f_sens = C.out_path("valuation_sensitivity.csv")
    f_sim = C.out_path("npv_simulation.csv")
    for f in (f_sens, f_sim):
        if not f.exists():
            raise SystemExit(
                f"{f.name} is missing. Run run_valuation_sensitivity.py and "
                "run_npv_simulation.py first; this runner joins them rather "
                "than recomputing, so that one number cannot mean two things.")

    sens = pd.read_csv(f_sens)
    sim = pd.read_csv(f_sim)

    # ---- what this consumer refuses ---------------------------------------
    # THREE MUTATIONS WENT THROUGH THE PREVIOUS VERSION UNTOUCHED: a dollar
    # added to every simulated baseline, a duplicated production contract that
    # came out as 1,218 rows with a repeated id, and a reserved 2022 cohort.
    # A table that is meant to be the one everything downstream reads has to
    # refuse its inputs, not average them.
    for name, frame, need in (
            ("the market comparison", sens,
             {KEY, "forecast", "surplus", "cost", "start_yr", "length"}),
            ("the path simulation", sim,
             {KEY, "surplus_point", "surplus_sim", "term"})):
        missing = need - set(frame.columns)
        assert not missing, f"{name} is missing {sorted(missing)}"

    # One row per contract per forecast, and one row per contract in the
    # simulation. A duplicate here is what produced the extra row.
    dup = sens.duplicated([KEY, "forecast"]).sum()
    assert not dup, f"the market comparison has {dup} duplicate contract/forecast rows"
    dup = sim.duplicated([KEY]).sum()
    assert not dup, f"the path simulation has {dup} duplicate contracts"

    # THE DEVELOPMENT SEAL, enforced HERE and not only upstream. A consumer
    # that trusts its inputs to have been sealed is a consumer that will
    # publish a reserved cohort the day one of them is not.
    reserved = sorted(set(sens["start_yr"].dropna().astype(int))
                      & set(C.CONFIRMATORY_START_YEARS))
    assert not reserved, (
        f"reserved start years {reserved} are in the market comparison; this "
        "table is development-only and will not launder a sealed cohort")

    # THE TWO ARTIFACTS MUST AGREE ABOUT WHAT THEY SHARE. The simulation
    # carries the point surplus it was built around; it has to be the same
    # number the market comparison calls the adopted forecast's surplus, or the
    # two files are describing different runs and the join is meaningless.
    shared = (sens[sens["forecast"] == ADOPTED][[KEY, "surplus"]]
              .merge(sim[[KEY, "surplus_point"]], on=KEY, how="inner"))
    gap = (shared["surplus"] - shared["surplus_point"]).abs()
    assert len(shared), "no contract appears in both artifacts"
    assert float(gap.max()) < 1.0, (
        f"the two artifacts disagree about the adopted point surplus by up to "
        f"${float(gap.max()):,.2f} on {int((gap >= 1.0).sum())} contracts; they "
        "are not from the same run")
    C.log(f"  input checks pass: {len(shared)} contracts agree on the adopted "
          f"point surplus to ${float(gap.max()):.2e}")
    C.log("")

    # ---- the adopted column, and every other forecast beside it -----------
    base = sens[sens["forecast"] == ADOPTED].copy()
    cols = [c for c in FROM_SENSITIVITY if c in base.columns]
    out = base[[KEY] + cols].copy()

    wide = sens.pivot_table(index=KEY, columns="forecast", values="surplus")
    wide.columns = ["surplus_" + c.replace("'", "").replace(" ", "_")
                    for c in wide.columns]
    out = out.merge(wide.reset_index(), on=KEY, how="left", validate="one_to_one")

    # ---- the distribution around the adopted one --------------------------
    keep = [c for c in FROM_SIMULATION if c in sim.columns]
    out = out.merge(sim[[KEY] + keep], on=KEY, how="left", validate="one_to_one")

    # ---- the join is checked, not assumed ---------------------------------
    # A silent left-join loss here would look like a smaller sample rather than
    # a broken join, which is the failure this tree has been caught by before.
    assert out[KEY].is_unique, "the artifact has duplicate contracts"
    n_sens = base[KEY].nunique()
    n_sim = sim[KEY].nunique()
    matched = int(out["surplus_sim"].notna().sum())
    C.log(f"  {n_sens} contracts from the market comparison")
    C.log(f"  {n_sim} contracts from the path simulation")
    C.log(f"  {matched} carry both, {n_sens - matched} carry a point valuation only")
    # NOT min(n_sens, n_sim) AS PROOF THE POPULATIONS AGREE. If they differ,
    # the missing ids are named rather than counted, because a count cannot be
    # chased and an id can.
    only_sens = sorted(set(base[KEY]) - set(sim[KEY]))
    only_sim = sorted(set(sim[KEY]) - set(base[KEY]))
    if only_sens or only_sim:
        C.log(f"  {len(only_sens)} contracts have a point valuation and no "
              f"simulation: {only_sens[:8]}{'...' if len(only_sens) > 8 else ''}")
        C.log(f"  {len(only_sim)} the other way: "
              f"{only_sim[:8]}{'...' if len(only_sim) > 8 else ''}")
    assert matched == len(set(base[KEY]) & set(sim[KEY])), (
        "the join lost contracts that are present in both inputs")
    C.log("")

    # ---- what is in the artifact ------------------------------------------
    C.log("THE ARTIFACT, one row per contract. Dollars are over the whole deal,")
    C.log("discounted from the signing, on the cap path knowable at the signing.")
    C.log("")
    groups = [
        ("what the club committed", ["aav", "length", "cost"]),
        ("what the adopted forecast says", ["war_per_season", "value", "surplus"]),
        ("the same under the other forecasts",
         [c for c in out.columns if c.startswith("surplus_") and
          c not in ("surplus_free", "surplus_sim", "surplus_absorbing")]),
        ("the distribution around the adopted one",
         ["surplus_sim", "sim_sd", "sim_p10", "sim_p90", "p_negative"]),
        ("declared sensitivities",
         ["surplus_free", "sd_indep_errors", "surplus_absorbing"]),
    ]
    for label, fields in groups:
        have = [f for f in fields if f in out.columns]
        if have:
            C.log(f"  {label}:")
            C.log(f"    {', '.join(have)}")
    C.log("")

    # ---- the one thing worth saying about it now ---------------------------
    C.log("WHERE THE POINT VALUATION AND THE DISTRIBUTION DISAGREE. The mean of")
    C.log("the distribution is not the point valuation, because the league")
    C.log("minimum truncates a path's downside and the point valuation prices")
    C.log("the average path rather than averaging the values of paths.")
    C.log("")
    d = out.dropna(subset=["surplus_sim"]).copy()
    d["gap"] = d["surplus_sim"] - d["surplus"]
    C.log(f"  {'group':<12}{'n':>6}{'point $M':>11}{'simulated':>11}{'gap':>9}"
          f"{'sd':>9}{'chance it loses':>17}")
    for g, k in d.groupby("fixed_group", observed=True):
        C.log(f"  {str(g):<12}{len(k):>6}{k['surplus'].mean()/1e6:>11.2f}"
              f"{k['surplus_sim'].mean()/1e6:>11.2f}{k['gap'].mean()/1e6:>9.2f}"
              f"{k['sim_sd'].mean()/1e6:>9.2f}{100*k['p_negative'].mean():>16.0f}%")
    C.log(f"  {'ALL':<12}{len(d):>6}{d['surplus'].mean()/1e6:>11.2f}"
          f"{d['surplus_sim'].mean()/1e6:>11.2f}{d['gap'].mean()/1e6:>9.2f}"
          f"{d['sim_sd'].mean()/1e6:>9.2f}{100*d['p_negative'].mean():>16.0f}%")
    C.log("")
    # ---- the reconciliation, contract by contract -------------------------
    spine_f = Path(C.PROD_OUTPUT_DIR) / "contract_npv_spine.csv"
    if not spine_f.exists():
        C.log("  RECONCILIATION SKIPPED: production's contract_npv_spine.csv is not")
        C.log("  present. Run the production chain to produce it.")
        C.log("")
    else:
        spine = pd.read_csv(spine_f)
        C.log("FULL-CHAIN MOVEMENT AGAINST THE PRODUCTION SPINE, contract by")
        C.log("contract. This is the plan's Phase 5 acceptance item.")
        C.log("")
        C.log("WHAT IS AND IS NOT COMPARABLE. Both sides are a dollar surplus")
        C.log("over the contract, but they are NOT the same construct and they")
        C.log("are not even dated alike. Production prices on the locked")
        C.log("censored regression, carries survival weights on top, and values")
        C.log("from 1 July of the first contract season; the rebuild prices a")
        C.log("signing-dated forecast on a rolling currency with participation")
        C.log("inside the forecast rather than as a weight over it. Production")
        C.log("also carries terminal control value on contracts the rebuild")
        C.log("stops at expiry. So the LEVELS are different definitions of")
        C.log("surplus on different information dates, and their difference is")
        C.log("not an error in either. What is comparable is the MOVEMENT:")
        C.log("whether the two order the same contracts the same way. Which")
        C.log("rows survive an identity, date, cost and terminal-value check is")
        C.log("run_production_reconciliation.py, not this script.")
        C.log("")
        j = out.merge(spine[["contract_id", "position", "npv_total",
                             "surplus_no_survival"]]
                      .rename(columns={"surplus_no_survival":
                                       "surplus_nominal_no_survival"}),
                      on=KEY, how="inner")
        C.log(f"  {len(spine)} contracts in the production spine, {len(out)} in the")
        C.log(f"  rebuild's development sample, {len(j)} in both.")
        C.log("")
        # THE SECOND COLUMN IS NOT AN NPV. contract_npv.py builds
        # surplus_no_survival as UNDISCOUNTED contract surplus plus terminal
        # value at its own reference date, so it drops the discounting along
        # with the hazard and is not comparable to npv_total. It is reported
        # for what it is and nothing is decomposed out of it here; the
        # hazard held against cost, discounting and terminal value is
        # run_production_reconciliation.py.
        for label, col in (("production NPV (survival-weighted)", "npv_total"),
                           ("production's nominal surplus (UNDISCOUNTED, no survival)",
                            "surplus_nominal_no_survival")):
            r = j[["surplus", col]].dropna()
            C.log(f"  against {label}:")
            C.log(f"    rank correlation        {r['surplus'].corr(r[col], method='spearman'):>8.3f}")
            C.log(f"    linear correlation      {r['surplus'].corr(r[col]):>8.3f}")
            C.log(f"    agree on sign           "
                  f"{100*(np.sign(r['surplus'])==np.sign(r[col])).mean():>7.0f}%")
            C.log(f"    median level, rebuild   {r['surplus'].median()/1e6:>8.2f} $M")
            C.log(f"    median level, production{r[col].median()/1e6:>8.2f} $M")
            C.log("")
        C.log("  by the rebuild's own group, median $M on both definitions:")
        C.log(f"    {'group':<12}{'n':>6}{'rebuild':>10}{'production':>13}"
              f"{'rank corr':>12}{'same sign':>11}")
        for g, k in j.groupby("fixed_group", observed=True):
            if len(k) < 10:
                continue
            C.log(f"    {str(g):<12}{len(k):>6}{k['surplus'].median()/1e6:>10.2f}"
                  f"{k['npv_total'].median()/1e6:>13.2f}"
                  f"{k['surplus'].corr(k['npv_total'], method='spearman'):>12.3f}"
                  f"{100*(np.sign(k['surplus'])==np.sign(k['npv_total'])).mean():>10.0f}%")
        C.log("")
        j["prod_gap"] = j["surplus"] - j["npv_total"]
        # THE TOP-TEN LIST BELOW IS ALL EIGHT-YEAR DEALS, so the gap is
        # measured against term before it is read as being about players.
        C.log("  and by term, because the largest disagreements are all long deals:")
        C.log(f"    {'term':<8}{'n':>6}{'rebuild $M':>13}{'production $M':>16}"
              f"{'mean gap':>11}{'rank corr':>12}")
        for L, k in j.groupby("length"):
            if len(k) < 10:
                continue
            C.log(f"    {int(L)} yr{'':<3}{len(k):>6}{k['surplus'].mean()/1e6:>13.2f}"
                  f"{k['npv_total'].mean()/1e6:>16.2f}"
                  f"{(k['surplus']-k['npv_total']).mean()/1e6:>11.2f}"
                  f"{k['surplus'].corr(k['npv_total'], method='spearman'):>12.3f}")
        C.log("")
        # NO SURVIVAL DECOMPOSITION IS ATTEMPTED HERE. An earlier version of
        # this script subtracted npv_total from surplus_no_survival and called
        # the difference the survival weight. That subtraction removes the
        # discounting too, and it produced negative weights, which cannot
        # happen when value is nonnegative and everything else is held. The
        # isolated hazard is computed from production's own season details in
        # run_production_reconciliation.py.
        C.log("  the exit hazard is NOT isolated in this table. Removing it while")
        C.log("  holding cost, discounting and terminal value needs production's")
        C.log("  per-season detail: see run_production_reconciliation.py.")
        C.log("")
        C.log("  the ten contracts the two systems disagree about most, in dollars:")
        C.log(f"    {'player':<26}{'yr':>6}{'term':>6}{'rebuild':>10}"
              f"{'production':>12}{'gap':>10}")
        top = j.reindex(j["prod_gap"].abs().sort_values(ascending=False).index).head(10)
        names = spine.set_index("contract_id")["full_name"]
        for _, r in top.iterrows():
            C.log(f"    {str(names.get(r[KEY], '?'))[:25]:<26}"
                  f"{int(r['start_yr']):>6}{int(r['length']):>6}"
                  f"{r['surplus']/1e6:>10.2f}{r['npv_total']/1e6:>12.2f}"
                  f"{r['prod_gap']/1e6:>10.2f}")
        C.log("")
        # production_surplus_nominal_no_survival is NOT an NPV and NOT
        # production's value with the hazard switched off. It is undiscounted
        # surplus plus terminal value at production's own reference date.
        out = out.merge(spine[["contract_id", "npv_total", "surplus_no_survival"]]
                        .rename(columns={
                            "npv_total": "production_npv",
                            "surplus_no_survival":
                                "production_surplus_nominal_no_survival"}),
                        on=KEY, how="left", validate="one_to_one")
        assert out[KEY].is_unique, "the production merge duplicated contracts"

    out.to_csv(C.out_path("contract_valuation.csv"), index=False)
    C.log(f"  wrote {C.out_path('contract_valuation.csv').name} "
          f"({len(out)} contracts, {out.shape[1]} columns)")
    C.write_log("valuation_integration_run_log.txt")


if __name__ == "__main__":
    main()
