"""run_production_reconciliation.py -- the same asset, at the same date, or not at all.

EXPERIMENTAL (50_REBUILD). Development start years only. Nothing adopted, and no
production file is changed: production's own engine is imported and called.

WHY THIS IS A SEPARATE RUNNER FROM THE INTEGRATION
    The first attempt at reconciliation joined the rebuild's contracts to
    production's exported spine on `contract_id` and read the difference as
    full-chain movement. The review found three reasons that is not a
    like-for-like comparison, and all three need production's per-season
    detail rather than its 11-column export, which is why this is its own
    runner with its own output.

    1. THE EXPORTED ID IS THE REQUESTED ID, NOT THE VALUED ONE. Production's
       sweep calls `npv(player_id, season)` and labels the result with the
       contract id it asked about. The engine follows a contract CHAIN and can
       value a different contract. Ten of 1,141 matched rows turned out to
       carry a valuation of some other contract entirely. A unique id on both
       sides does not make it the same asset.

    2. THE DATES DIFFER. Production values from 1 July of the first contract
       season. The rebuild values at the signing. The previous report said both
       were discounted from the signing, which was false of production.

    3. THE ASSETS DIFFER. Production carries terminal control value on
       contracts that expire into restricted free agency. The rebuild's
       simulator has no walk-away option and excludes control years entirely.

    So each row is classified before it is compared, the exceptions are
    quarantined with a reason rather than dropped, and the attrition is
    reported.

AND THE SURVIVAL DECOMPOSITION IS REDONE PROPERLY
    The previous version subtracted production's `surplus_no_survival` from its
    NPV and called the difference the exit hazard's contribution. That column
    is the sum of UNDISCOUNTED contract surplus plus terminal value, so the
    subtraction removed the discounting as well as the hazard. The tell was in
    the output and went unread: two of the terms came back NEGATIVE, and
    removing a haircut cannot lower a value when everything else is held.

    The isolated quantity is computed here from the per-season detail, holding
    cost, discount and terminal value fixed and setting the survival multiplier
    to one:

        no-hazard NPV = sum((value - cost) * discount) + terminal NPV
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C

SCRIPT_VERSION = "1.1"
KEY = "contract_id"


def production_engine():
    sys.path.insert(0, str(C.PROD_CODE_DIR))
    warnings.filterwarnings("ignore")
    import contract_npv as NPV
    return NPV.NPVEngine(), NPV


def main() -> None:
    C.banner("run_production_reconciliation.py", SCRIPT_VERSION)

    f_int = C.out_path("contract_valuation.csv")
    if not f_int.exists():
        raise SystemExit("run_valuation_integration.py first")
    reb = pd.read_csv(f_int)

    spine_f = Path(C.PROD_OUTPUT_DIR) / "contract_npv_spine.csv"
    if not spine_f.exists():
        raise SystemExit("production's contract_npv_spine.csv is not present")
    spine = pd.read_csv(spine_f)

    eng, NPV = production_engine()
    C.log("  production's own engine imported; nothing in 20_CODE is modified")
    C.log("")

    j = reb.merge(spine[[KEY, "player_id", "full_name", "valuation_season",
                         "npv_total", "npv_terminal"]], on=KEY, how="inner")
    C.log(f"  {len(j)} contracts appear in both, before any check")
    C.log("")

    rows = []
    for r in j.itertuples():
        det, s = eng.npv(int(r.player_id), int(r.valuation_season))
        if s.get("status") != "ok" or det.empty:
            rows.append({KEY: getattr(r, KEY), "status": s.get("status", "no detail")})
            continue
        con = det[det["row_type"] == "contract"]
        # THE IDENTITY CHECK the exported spine cannot support.
        chain = s.get("chain", [])
        identity_ok = int(getattr(r, KEY)) in [int(c) for c in chain]
        # The isolated hazard effect: survival to one, everything else held.
        nohaz_contract = float(((con["value_dollars"] - con["cost_dollars"])
                                * con["discount"]).sum())
        nohaz_total = nohaz_contract + float(r.npv_terminal)
        rows.append({
            KEY: int(getattr(r, KEY)),
            "status": "ok",
            "identity_ok": identity_ok,
            "chain_len": len(chain),
            "prod_seasons": int(len(con)),
            "reb_term": int(r.length),
            "has_terminal": abs(float(r.npv_terminal)) > 1.0,
            "prod_valuation_season": int(r.valuation_season),
            "reb_start_yr": int(r.start_yr),
            # THE SIGNING YEAR, not the start year. Comparing production's
            # valuation season against the contract's START year is vacuous --
            # production values from 1 July of the first contract season, so
            # they agree by construction. The informative comparison is against
            # when the pen moved, which for an extension can be years earlier.
            "reb_signed_yr": int(pd.Timestamp(r.signed).year
                                 if pd.Timestamp(r.signed).month >= 7
                                 else pd.Timestamp(r.signed).year - 1),
            "prod_cost": float((con["cost_dollars"] * con["discount"]).sum()),
            "reb_cost": float(r.cost),
            "npv_total": float(r.npv_total),
            "nohaz_total": nohaz_total,
            "hazard_effect": nohaz_total - float(r.npv_total),
            "reb_surplus": float(r.surplus),
        })
    d = pd.DataFrame(rows)
    ok = d[d["status"] == "ok"].copy()
    C.log(f"  {len(ok)} priced by the engine on this call, "
          f"{len(d) - len(ok)} returned no usable detail")
    C.log("")

    # ---- who is actually comparable ---------------------------------------
    ok["cost_gap"] = (ok["prod_cost"] - ok["reb_cost"]).abs()
    ok["cost_ok"] = ok["cost_gap"] < 0.10 * ok["reb_cost"].abs().clip(lower=1e5)
    ok["term_ok"] = ok["prod_seasons"] == ok["reb_term"]
    ok["clean"] = (ok["identity_ok"] & ok["term_ok"] & ok["cost_ok"]
                   & ~ok["has_terminal"])

    C.log("WHO IS COMPARABLE, and why the rest is not. Each test is reported")
    C.log("separately because they overlap and the reasons matter more than")
    C.log("the count.")
    C.log("")
    for label, mask in [
        ("production valued a DIFFERENT contract", ~ok["identity_ok"]),
        ("production covers a different number of seasons", ~ok["term_ok"]),
        ("production carries terminal control value", ok["has_terminal"]),
        ("the two sides disagree about cost by >10%", ~ok["cost_ok"]),
        ("the valuation year differs from the signing year",
         ok["prod_valuation_season"] != ok["reb_signed_yr"]),
    ]:
        C.log(f"    {label:<52}{int(mask.sum()):>6}")
    C.log("")
    C.log(f"    {'comparable on every test':<52}{int(ok['clean'].sum()):>6}"
          f"   of {len(ok)}")
    C.log("")
    C.log("  The date test is reported and NOT used to exclude: production")
    C.log("  values from 1 July of the first contract season and the rebuild")
    C.log("  values at the signing, so the two are on different information")
    C.log("  dates even when the years agree. Equal years would not make them")
    C.log("  the same date. That is a limitation of the whole comparison rather")
    C.log("  than a property of particular rows.")
    C.log("")

    bad_ids = sorted(ok.loc[~ok["identity_ok"], KEY].tolist())
    if bad_ids:
        C.log(f"  the {len(bad_ids)} mislabelled contracts: {bad_ids}")
        C.log("  Production's sweep labels its output with the contract id it")
        C.log("  ASKED about; the engine follows a chain and may value another.")
        C.log("")

    # ---- the hazard, isolated ---------------------------------------------
    C.log("THE EXIT HAZARD, ISOLATED. Survival set to one, cost, discounting")
    C.log("and terminal value all held. The previous report subtracted a column")
    C.log("that is undiscounted and called the difference the hazard, which")
    C.log("removed the discounting too and produced negative effects that")
    C.log("cannot happen.")
    C.log("")
    for label, sub in (("all matched rows", ok),
                       ("comparable rows only", ok[ok["clean"]])):
        C.log(f"  {label}:")
        C.log(f"    {'term':<8}{'n':>6}{'production':>13}{'no hazard':>12}"
              f"{'hazard worth':>14}{'gap to rebuild':>16}")
        for L, k in sub.groupby("reb_term"):
            if len(k) < 8:
                continue
            C.log(f"    {int(L)} yr{'':<3}{len(k):>6}{k['npv_total'].mean()/1e6:>13.2f}"
                  f"{k['nohaz_total'].mean()/1e6:>12.2f}"
                  f"{k['hazard_effect'].mean()/1e6:>14.2f}"
                  f"{(k['reb_surplus']-k['npv_total']).mean()/1e6:>16.2f}")
        C.log("")
    neg = int((ok["hazard_effect"] < -1.0).sum())
    C.log(f"  rows where removing the hazard LOWERS value: {neg} "
          f"(should be none; value is nonnegative and all else is held)")
    C.log("")
    C.log("  WHAT THIS SUPPORTS, AND ONLY THIS: the exit hazard alone does not")
    C.log("  explain the long-contract gap. It does NOT identify the aging path")
    C.log("  or the price line as the cause, and it does not test whether the")
    C.log("  hazard historically offset over-projection against outcomes. The")
    C.log("  previous report claimed the first of those and it was not earned.")
    C.log("")

    # ---- the cost disagreements, named ------------------------------------
    # THESE ARE SOURCE INCONSISTENCIES, not something this comparison
    # introduced: the supplied season spine carries a cap hit an order of
    # magnitude away from the contract's AAV on a handful of deals, and
    # production prices the cap hit. Nothing here changes a production input.
    worst = ok.loc[~ok["cost_ok"]].copy()
    worst["ratio"] = worst["prod_cost"] / worst["reb_cost"].replace(0, pd.NA)
    worst = worst.reindex(worst["ratio"].sort_values(ascending=False).index)
    C.log(f"COST DISAGREEMENTS: {len(worst)} contracts price more than 10% apart.")
    C.log("  The largest are a cap hit that sits an order of magnitude from the")
    C.log("  contract's own AAV in the supplied season spine. Production prices")
    C.log("  the cap hit. That is a source inconsistency, not a defect here, and")
    C.log("  no production input was changed to make the comparison look better.")
    C.log(f"    {'contract':<10}{'production $M':>15}{'rebuild $M':>13}{'ratio':>9}"
          f"  also a wrong contract?")
    for _, r in worst.head(6).iterrows():
        C.log(f"    {int(r[KEY]):<10}{r['prod_cost']/1e6:>15.3f}"
              f"{r['reb_cost']/1e6:>13.3f}{float(r['ratio']):>9.1f}"
              f"  {'yes' if not r['identity_ok'] else 'no'}")
    C.log("")

    # ---- how much of the gap is term at all --------------------------------
    # THE TERM GRADIENT IS STRONG BUT IT IS NOT THE WHOLE DISAGREEMENT, and
    # the share is worth stating rather than implying. This is the between-
    # group share of squared variation in the dollar gap, term as the group.
    g = ok["reb_surplus"] - ok["npv_total"]
    between = ((g.groupby(ok["reb_term"]).transform("mean") - g.mean()) ** 2).sum()
    total = ((g - g.mean()) ** 2).sum()
    C.log(f"  term-group means account for {100*between/total:.1f}% of the squared")
    C.log("  variation in the dollar gap. Strong, and not literally all of it.")
    C.log("")

    # ---- the flags go into the artifact, not just the log -------------------
    flags = ok[[KEY, "cost_ok", "term_ok", "clean"]].copy()
    flags["date_ok"] = (ok["prod_valuation_season"] == ok["reb_signed_yr"])
    reasons = []
    for _, r in ok.iterrows():
        why = []
        if not r["identity_ok"]:
            why.append("production valued a different contract")
        if not r["term_ok"]:
            why.append("different season count")
        if r["has_terminal"]:
            why.append("production carries terminal control value")
        if not r["cost_ok"]:
            why.append("cost differs by >10%")
        reasons.append("; ".join(why))
    flags["exclusion_reasons"] = reasons
    d = d.merge(flags, on=KEY, how="left")

    d.to_csv(C.out_path("production_reconciliation.csv"), index=False)
    C.log(f"  wrote {C.out_path('production_reconciliation.csv').name}")
    C.write_log("production_reconciliation_run_log.txt")


if __name__ == "__main__":
    main()
