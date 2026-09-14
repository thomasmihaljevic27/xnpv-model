"""run_phase0_acceptance.py -- the gate that lets Phase 1 start.

EXPERIMENTAL (50_REBUILD). Rebuild plan, Phase 0 acceptance:

    "the production chain's own forecast, re-expressed as a model, scores on
     the harness and reproduces the tilt already measured (+24% at 3+ on
     2020-25 pages). That is the reproduction guard for the harness itself."

The logic is the same one every script in this project uses before its output
is trusted: before believing a new measurement, reproduce a known one. If the
harness scores A0 -- the production starting point -- as unbiased at the top,
then the harness is measuring something other than what the chain does, and
every later comparison run on it is worthless.

Runs on development pages only. The confirmatory seal is not touched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from ability_forecast import A0Production, A1Calibrated, A2Raw, A2Component
from player_season_table import build as build_table, guard_against_production

SCRIPT_VERSION = "1.0"
pd.set_option("display.width", 200, "display.max_columns", 50)


def main() -> None:
    C.banner("run_phase0_acceptance.py", SCRIPT_VERSION)
    C.log(f"input  {C.F_WAR_SKATERS}  sha256:{C.file_hash(C.F_WAR_SKATERS)}")
    C.log("")

    C.log("STEP 1  season table + reproduction guard against production")
    # Ages come from the PuckPedia/EP birthdate table that contract_source.py
    # builds. Where it is absent the run still works and reports 0% coverage;
    # it does not fail, because Phases 0-1 are defined without ages.
    bd = C.OUT_DIR / "birthdates.csv"
    if not bd.exists():
        C.log(f"        note: {bd.name} absent -- run contract_source.py first for ages")
    table = build_table(birthdate_csv=bd if bd.exists() else None, verbose=True)
    if not guard_against_production(table):
        C.log("  guard did not run; results below are NOT acceptance evidence")
    C.log("")

    C.log(f"STEP 2  harness, development pages {C.DEV_PAGES[0]}-{C.DEV_PAGES[-1]} "
          f"(confirmatory {C.CONFIRMATORY_PAGES[0]}-{C.CONFIRMATORY_PAGES[-1]} sealed)")
    harness = H.Harness(table)

    C.log("        seal check: asking for a confirmatory page must be refused")
    try:
        harness.run(A0Production(), pages=(2023,))
        raise SystemExit("SEAL FAILED -- a sealed page was scored")
    except C.ConfirmatorySealBroken:
        C.log("        refused, as designed")
    C.log("")

    C.log("STEP 3  A0, the production chain's forecast, scored on the harness")
    a0 = harness.run(A0Production())
    C.log(f"        {len(a0)} scored rows, {a0['career_key'].nunique()} careers, "
          f"{a0['page'].nunique()} pages")
    C.log("")
    C.log("  by horizon:")
    C.log(_fmt(H.Harness.summary(a0, "h")))
    C.log("")
    C.log("  ACCEPTANCE TEST -- the tilt, by trailing level tier:")
    tilt = H.Harness.summary(a0[a0["h"] <= 2], ["tier"])
    C.log(_fmt(tilt))

    top = tilt[tilt["tier"] == "3+"].iloc[0]
    C.log("")
    C.log(f"        3+ tier: bias {top['bias_war']:+.3f} wins on n={int(top['n'])}, "
          f"against a mean outcome of {top['bias_war'] / max(top['n'], 1) * 0 + 0:.0f}")
    act3 = a0[(a0["tier"] == "3+") & (a0["h"] <= 2)]
    mean_act = act3["act_war"].mean()
    C.log(f"        mean actual {mean_act:.3f}, mean predicted {act3['pred_war'].mean():.3f}, "
          f"over-projection {100 * top['bias_war'] / mean_act:+.1f}%")
    passed = top["bias_war"] > 0.3
    C.log(f"        ACCEPTANCE: {'PASS' if passed else 'FAIL'} -- the harness reproduces the "
          "production chain's over-projection of stars"
          if passed else
          "        ACCEPTANCE: FAIL -- the harness does not reproduce the known tilt; "
          "do not run Phase 1 comparisons on it")
    C.log("")

    C.log("STEP 4  the Phase 1 candidates on the same rows (first look)")
    a1 = harness.run(A1Calibrated())
    m2 = A2Component()
    a2 = harness.run(m2)
    a2r = harness.run(A2Raw())
    C.log(f"  fitted reliability constants k_c on the last page ({C.DEV_PAGES[-1]}), "
          "in games of evidence needed to match the norm:")
    kg = m2.K_GRID
    for c, k in m2.k_.items():
        edge = ("  <-- AT THE GRID EDGE: this component carries essentially no "
                "predictive signal and is shrunk to the norm" if k >= kg[-1] else
                "  <-- at the grid edge: trusted almost unshrunk" if k <= kg[0] else "")
        C.log(f"     {c:10s} k={k:7.0f}{edge}")
    for nm, s in (("A0", a0), ("A1", a1), ("A2raw", a2r), ("A2", a2)):
        r = H.Harness.summary(s, "h")
        C.log(f"  {nm}: " + "  ".join(
            f"h{int(x.h)} mae {x.mae_war:.3f} bias {x.bias_war:+.3f}" for x in r.itertuples()))
    C.log("")
    C.log("  A1 vs A2, paired, bootstrap clustered by career (negative favours A2):")
    C.log(_fmt(H.Harness.compare(a1, a2)))
    C.log("")
    C.log("  A1 vs A2-raw (no shrinkage), same test -- isolates what shrinkage buys:")
    C.log(_fmt(H.Harness.compare(a1, a2r)))
    C.log("")
    C.log("  tilt by tier, h<=2 (bias in wins; pct is bias over the tier's mean outcome).")
    C.log("  The plan's Phase 1 acceptance asks for every tier within 5%:")
    for nm, s in (("A0", a0), ("A1", a1), ("A2raw", a2r), ("A2", a2)):
        s2 = s[s["h"] <= 2]
        t = H.Harness.summary(s2, ["tier"])
        act = s2.groupby("tier", observed=True)["act_war"].mean()
        parts = []
        for x in t.itertuples():
            m = act.get(x.tier, np.nan)
            pct = 100 * x.bias_war / m if m and abs(m) > 0.25 else np.nan
            parts.append(f"{x.tier}: {x.bias_war:+.2f}" + (f" ({pct:+.0f}%)" if np.isfinite(pct) else ""))
        C.log(f"    {nm:6s} " + "   ".join(parts))

    for nm, s in (("A0", a0), ("A1", a1), ("A2raw", a2r), ("A2", a2)):
        s.to_csv(C.out_path(f"phase0_scored_{nm}.csv"), index=False)
    C.log("")
    C.log(f"  wrote scored rows to {C.OUT_DIR}")
    C.write_log("phase0_acceptance_run_log.txt")


def _fmt(df: pd.DataFrame) -> str:
    return df.to_string(index=False, float_format=lambda v: f"{v:8.3f}")


if __name__ == "__main__":
    main()
