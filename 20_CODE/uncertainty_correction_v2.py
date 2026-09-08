"""
uncertainty_correction_v2.py  --  re-measure review item 3.6 on the new rate.
=============================================================================
SCRIPT VERSION: v2.0 (2026-07-27)

WHY A SECOND VERSION
--------------------
v1 measured the item 3.6 correction BEFORE it was wired into the chain, so it
had to reconstruct each season's value from ALPHA and BETA and compare that
against the engine's own figure. Two things have since made that approach
wrong:

  1. The correction is now applied inside the projection (apply_3_6_patch.py),
     so `value_dollars` IS the corrected figure. Reconstructing the point
     estimate and calling the difference a correction would double-count.
  2. The rate is now position-dependent (item 4.5 steps 1 to 3). Rebuilding
     value from a single BETA would price every defenceman on the forward
     slope.

v2 does no reconstruction at all. The 3.6 patch writes the correction to each
projection row as its own column, so this script reads it. That removes the
entire class of error that produced v1's first run, where a circular fallback
set the floor equal to the point estimate on every row and turned the whole
measurement into an artifact.

WHY RE-MEASURE
--------------
The correction lives entirely at the league-minimum floor. Lowering the
intercept from $1.749M to $1.265M moved the floor's bite from about -0.53
projected wins to about -0.24, and floor-bound rows in Layer 1 went from 379
(5.5%) to 1,055 (15.3%). The correction measured at the old rate, $68,200 per
contract, is therefore an understatement of the figure now in force.

WHAT IT REPORTS
---------------
The correction per contract, in present-value terms, with the survival and
discount weights the chain itself applied; the shape by projected production,
which must FALL as production rises; the two exposures flagged in v1; and a
before-and-after against the old-rate measurement.

GOALTENDERS are excluded, as in v1. They price on a separate rate through a
different branch, project flat rather than through the aging curve, and carry
none of these columns.

HOW IT RUNS
-----------
    python uncertainty_correction_v2.py

OUTPUTS
-------
  uncertainty_correction_v2_rows.csv
  uncertainty_correction_v2_runlog.txt
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(os.environ.get("XNPV_DATA", "."))
OUT_ROWS = DATA_DIR / "uncertainty_correction_v2_rows.csv"
OUT_LOG = DATA_DIR / "uncertainty_correction_v2_runlog.txt"

# v1 results, measured at the OLD rate, for the before-and-after.
V1_MEAN_PER_CONTRACT = 68_200.0
V1_FLIPS = 9
V1_NEGATIVE = 921

REQUIRED_COLS = ["uncertainty_correction", "value_point_estimate",
                 "proj_sd_war", "sd_placeholder"]

LOG = []
def log(m=""):
    print(m); LOG.append(str(m))

def die(m):
    log("\n" + "!" * 70); log("HALTED: " + m); log("!" * 70)
    OUT_LOG.write_text("\n".join(LOG), encoding="utf-8"); sys.exit(1)


def main():
    log("uncertainty_correction_v2.py v2.0 (2026-07-27)")
    log("Re-measures review item 3.6 against the corrected rate.")
    log("Reads the patch's own columns; reconstructs nothing.\n")

    sys.path.insert(0, str(DATA_DIR))
    try:
        import contract_npv as CN
    except Exception as e:
        die(f"could not import contract_npv.py: {type(e).__name__}: {e}")
    try:
        import skater_forward_projection as SFP
    except Exception as e:
        die(f"could not import skater_forward_projection.py: {e}")

    if not hasattr(SFP, "expected_floored_value"):
        die("the item 3.6 patch is not present in skater_forward_projection.py. "
            "There is nothing to measure.")
    if not hasattr(SFP, "BETA_D"):
        die("the item 4.5 rate patch is not present. Run "
            "apply_rate_patch_step23.py first, or this measures the old rate.")
    cap25 = 95.5e6
    log(f"  rate in force: intercept ${SFP.ALPHA*cap25/1e6:.4f}M, "
        f"${SFP.BETA*cap25/1e6:.4f}M per win (F), "
        f"${SFP.BETA_D*cap25/1e6:.4f}M per win (D)")

    try:
        engine = CN.NPVEngine()
    except Exception as e:
        die(f"could not build the NPV engine: {type(e).__name__}: {e}")

    spine = pd.read_csv(DATA_DIR / "contract_npv_spine.csv")
    log(f"  contracts in the NPV spine: {len(spine)}")

    rows, n_goalie, n_fail = [], 0, 0
    for _, sr in spine.iterrows():
        pid, t0 = int(sr["player_id"]), int(sr["valuation_season"])
        try:
            det, meta = engine.npv(pid, t0)
        except Exception:
            n_fail += 1
            continue
        if meta.get("status") != "ok" or det is None or not len(det):
            n_fail += 1
            continue
        if meta.get("position") != "skater":
            n_goalie += 1
            continue
        d = det[det["row_type"] == "contract"]
        for _, r in d.iterrows():
            missing = [c for c in REQUIRED_COLS if c not in r]
            if missing:
                die(f"projection rows are missing {missing}. The 3.6 patch "
                    "writes these columns; if they are absent the patch is "
                    "not applied to the module this engine is importing.")
            corr = float(r["uncertainty_correction"])
            point = float(r["value_point_estimate"])
            val = float(r["value_dollars"])
            # The engine's value must be the point estimate plus the
            # correction, exactly. If it is not, this script is reading a
            # different quantity from the one the chain applied.
            if abs((point + corr) - val) > 1.0:
                die(f"consistency check failed: value ${val:,.0f} but "
                    f"point ${point:,.0f} + correction ${corr:,.0f} = "
                    f"${point+corr:,.0f}. Do not read this run.")
            S = float(r.get("survival", 1.0))
            disc = float(r.get("discount", 1.0))
            rows.append(dict(
                contract_id=sr.get("contract_id"), player_id=pid,
                full_name=sr.get("full_name"), valuation_season=t0,
                k=int(r["k"]), posgrp=r.get("posgrp", "?"),
                projected_war=float(r.get("projected_war", np.nan)),
                point_value=point, correction=corr,
                survival=S, discount=disc, pv_correction=corr * S * disc,
                sd_placeholder=bool(r["sd_placeholder"])))

    if n_goalie:
        log(f"  goalie contracts skipped (out of scope): {n_goalie}")
    if n_fail:
        log(f"  contracts skipped (engine returned nothing usable): {n_fail}")
    if not rows:
        die("no contract-seasons measured.")

    df = pd.DataFrame(rows)
    log(f"  contract-seasons measured: {len(df)}")
    log(f"  consistency check passed on every row")

    ph = int(df["sd_placeholder"].sum())
    log(f"  seasons using the held-flat placeholder spread (k>3): "
        f"{ph} ({ph/len(df)*100:.1f}%)")
    bad_pos = df[~df["posgrp"].isin(["F", "D"])]
    log(f"  rows whose position did not resolve to F or D: {len(bad_pos)}"
        + ("  <-- the posgrp_from_nk fallback fired; these priced on the "
           "forward slope" if len(bad_pos) else ""))

    per = df.groupby("contract_id", as_index=False)["pv_correction"].sum()
    m = spine.merge(per, on="contract_id", how="left")
    m["pv_correction"] = m["pv_correction"].fillna(0.0)
    # npv_total already CONTAINS the correction, since the patch is live.
    m["npv_without"] = m["npv_total"] - m["pv_correction"]

    log("\n" + "=" * 74)
    log("THE CORRECTION NOW IN FORCE")
    log("=" * 74)
    mean_now = m["pv_correction"].mean()
    log(f"  mean per contract:   ${mean_now/1e6:+.4f}M "
        f"(at the old rate: ${V1_MEAN_PER_CONTRACT/1e6:+.4f}M)")
    log(f"  change vs the old-rate measurement: "
        f"{(mean_now/V1_MEAN_PER_CONTRACT - 1)*100:+.0f}%")
    log(f"  median per contract: ${m['pv_correction'].median()/1e6:+.4f}M")
    log(f"  largest:             ${m['pv_correction'].max()/1e6:+.4f}M")
    flips = int(((m["npv_without"] < 0) & (m["npv_total"] >= 0)).sum())
    log(f"  contracts the correction moves from negative to positive: {flips} "
        f"(at the old rate: {V1_FLIPS} of {V1_NEGATIVE})")

    log("\n  shape by projected production -- MUST fall as production rises:")
    df["band"] = pd.cut(df["projected_war"], [-99, 0, 0.5, 1, 2, 99],
                        labels=["<=0", "0 to 0.5", "0.5 to 1", "1 to 2", ">2"])
    for b, g in df.groupby("band", observed=True):
        log(f"    {str(b):<10} n={len(g):>5}  mean correction "
            f"${g['correction'].mean()/1e6:+.4f}M per season")

    log("\n  by position (defencemen carry a steeper slope, so a wider spread):")
    for p, g in df.groupby("posgrp"):
        log(f"    {p}: n={len(g):>5}  mean correction "
            f"${g['correction'].mean()/1e6:+.4f}M per season")

    log("\n  by contract length:")
    if "n_seasons" in m.columns:
        for L, g in m.groupby("n_seasons"):
            log(f"    {int(L)}yr  n={len(g):>4}  mean correction "
                f"${g['pv_correction'].mean()/1e6:+.4f}M   "
                f"mean NPV without ${g['npv_without'].mean()/1e6:+7.2f}M -> "
                f"with ${g['npv_total'].mean()/1e6:+7.2f}M")

    df.to_csv(OUT_ROWS, index=False)
    log(f"\n  wrote {OUT_ROWS.name}")
    OUT_LOG.write_text("\n".join(LOG), encoding="utf-8")
    log(f"  wrote {OUT_LOG.name}")


if __name__ == "__main__":
    main()
