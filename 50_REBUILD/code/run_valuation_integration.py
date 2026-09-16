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

SCRIPT_VERSION = "1.0"

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

    # ---- the adopted column, and every other forecast beside it -----------
    base = sens[sens["forecast"] == ADOPTED].copy()
    cols = [c for c in FROM_SENSITIVITY if c in base.columns]
    out = base[[KEY] + cols].copy()

    wide = sens.pivot_table(index=KEY, columns="forecast", values="surplus")
    wide.columns = ["surplus_" + c.replace("'", "").replace(" ", "_")
                    for c in wide.columns]
    out = out.merge(wide.reset_index(), on=KEY, how="left")

    # ---- the distribution around the adopted one --------------------------
    keep = [c for c in FROM_SIMULATION if c in sim.columns]
    out = out.merge(sim[[KEY] + keep], on=KEY, how="left")

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
    assert matched == min(n_sens, n_sim), (
        f"only {matched} contracts joined against {min(n_sens, n_sim)} available; "
        "the two runners disagree about which contracts exist")
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
        C.log("WHAT IS AND IS NOT COMPARABLE. Both sides are a dollar surplus over")
        C.log("the contract, discounted. They are NOT the same construct: production")
        C.log("prices production on the locked censored regression and carries it")
        C.log("with survival weights, while the rebuild prices a signing-dated")
        C.log("forecast on a rolling currency with participation inside the")
        C.log("forecast rather than as a weight on top. So the LEVELS are two")
        C.log("different definitions of surplus and their difference is not an")
        C.log("error in either. What is comparable is the MOVEMENT: whether the")
        C.log("two order the same contracts the same way.")
        C.log("")
        j = out.merge(spine[["contract_id", "position", "npv_total",
                             "surplus_no_survival"]],
                      on=KEY, how="inner")
        C.log(f"  {len(spine)} contracts in the production spine, {len(out)} in the")
        C.log(f"  rebuild's development sample, {len(j)} in both.")
        C.log("")
        for label, col in (("production NPV (survival-weighted)", "npv_total"),
                           ("production surplus, no survival", "surplus_no_survival")):
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
        # HOW MUCH OF THAT GRADIENT IS THE SURVIVAL WEIGHT? The spine carries
        # production's surplus with the weighting removed, so the two candidate
        # explanations can be separated instead of argued about: the weight
        # itself, or everything else production does to a long deal.
        C.log("  and how much of the term gradient is production's survival weight,")
        C.log("  which the spine lets us remove:")
        C.log(f"    {'term':<8}{'n':>6}{'production':>13}{'no survival':>14}"
              f"{'the weight':>13}{'rest of gap':>14}")
        for L, k in j.groupby("length"):
            if len(k) < 10:
                continue
            weight = (k["surplus_no_survival"] - k["npv_total"]).mean() / 1e6
            rest = (k["surplus"] - k["surplus_no_survival"]).mean() / 1e6
            C.log(f"    {int(L)} yr{'':<3}{len(k):>6}{k['npv_total'].mean()/1e6:>13.2f}"
                  f"{k['surplus_no_survival'].mean()/1e6:>14.2f}"
                  f"{weight:>13.2f}{rest:>14.2f}")
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
        out = out.merge(spine[["contract_id", "npv_total", "surplus_no_survival"]]
                        .rename(columns={"npv_total": "production_npv",
                                         "surplus_no_survival": "production_npv_no_survival"}),
                        on=KEY, how="left")

    out.to_csv(C.out_path("contract_valuation.csv"), index=False)
    C.log(f"  wrote {C.out_path('contract_valuation.csv').name} "
          f"({len(out)} contracts, {out.shape[1]} columns)")
    C.write_log("valuation_integration_run_log.txt")


if __name__ == "__main__":
    main()
