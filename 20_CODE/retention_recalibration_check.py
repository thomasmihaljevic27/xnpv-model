"""
retention_recalibration_check.py  --  review item 4.2.
======================================================
SCRIPT VERSION: v1.0 (2026-07-27)

THE QUESTION
------------
The old intercept said a zero-win player was worth $1.75M, which is 2.3 times
the league minimum. That made nearly every fringe restricted free agent look
worth retaining: the model predicted only 18% of the walk-aways that actually
happened. The D14(c) empirical calibration exists to repair that mismatch.

The review's own words: "A meaningful share of the calibration step is
repairing damage the price equation created."

We have since repaired the price equation. The censored intercept is $1.265M,
and $0.977M for forwards once the position term is included. So fringe players
are now worth less on their own, before any retention gate is applied.

Three things now push fringe terminal value down at once:
  1. the lower intercept, so a fringe player is worth less;
  2. the D14(c) retention gate applied on top;
  3. item 4.1, which made that gate more aggressive in the negative bucket.

Each is defensible alone. Stacked, they could drive fringe and below-
replacement terminal value below what the observed record supports, and those
are the same players the calibration was built to protect.

WHAT THIS SCRIPT MEASURES
-------------------------
For each observable qualify-or-walk decision it asks whether the model, on its
own, implies the control year was worth qualifying: is the player's projected
value above his qualifying-offer cost? It then compares that verdict against
what the team actually did, under three price regimes.

The decisive number is the MODEL-IMPLIED RETENTION RATE by bucket, set against
the OBSERVED rate:

  * model-implied ABOVE observed  -> the model is still too generous, and the
    empirical gate is doing real work. D14(c) stands as is.
  * model-implied BELOW observed  -> the model is now MORE pessimistic than
    teams actually are. Applying the empirical gate on top would then be
    correcting a bias that has already been removed, and the stack is
    over-correcting.

This is a measurement. It changes nothing and adopts nothing.

WHAT IT IS NOT
--------------
It is not a claim that D14(c) should be dropped. The gate answers "will he be
retained?" and the intercept answers "what is he worth if retained." Those two
multiply legitimately, so there is no mechanical double-count. The point is
narrower: the 18% figure that justified the gate was computed under a price
equation that no longer exists, and it needs restating either way.

CHOICES MADE HERE, AND THEY ARE MINE RATHER THAN THE PROJECT'S
---------------------------------------------------------------
1. THE DECISION RULE. A team is taken to qualify a player when his projected
   control-year value exceeds his qualifying-offer cost. This is a one-year
   test. Real teams weigh later control years too, so this understates
   retention for young players on an upward path. Reported, not corrected.
2. THE PRODUCTION ESTIMATE. The trailing anchor is used directly as the
   control-year production estimate, rather than running the full aging path.
   At one season out the curve multiplier is close to 1.0, so the
   approximation is small, and it keeps the criterion transparent.
3. NO-ANCHOR DECISIONS enter at zero wins, consistent with item 4.1 placing
   them in the negative bucket.
4. A SENSITIVITY BAND is reported around the rule, because a strict
   value-above-cost threshold is arbitrary at the margin.

HOW IT RUNS
-----------
    python retention_recalibration_check.py

OUTPUTS
-------
  retention_recalibration_rows.csv
  retention_recalibration_runlog.txt
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(os.environ.get("XNPV_DATA", "."))
OUT_ROWS = DATA_DIR / "retention_recalibration_rows.csv"
OUT_LOG = DATA_DIR / "retention_recalibration_runlog.txt"

# ---------------------------------------------------------------------------
# THE THREE PRICE REGIMES, in cap share.
#
# OLD is the rate currently in the chain (skater_forward_projection.ALPHA/BETA).
# CENSORED and CENSORED+POSITION come from price_equation_censored.py and
# price_equation_spline.py, run 2026-07-27 on the locked n=2,349 sample. They
# are quoted here in cap share at the 2025-26 ceiling of $95.5M:
#     censored straight line          $1.270M + $2.073M per win
#     censored + position interaction $1.265M + $2.028M (F) / $2.302M (D)
# The script asserts these reproduce those dollar figures, so a typo cannot
# pass silently.
# ---------------------------------------------------------------------------
CAP25 = 95.5e6
REGIMES = {
    "old (in the chain now)":      dict(a=0.01831864, bF=0.01924854, bD=0.01924854),
    "censored, no position":       dict(a=1.270e6 / CAP25, bF=2.073e6 / CAP25,
                                        bD=2.073e6 / CAP25),
    "censored + position":         dict(a=1.265e6 / CAP25, bF=2.028e6 / CAP25,
                                        bD=2.302e6 / CAP25),
}

BUCKETS = ["star", "regular", "fringe", "negative"]

LOG = []
def log(m=""):
    print(m); LOG.append(str(m))

def die(m):
    log("\n" + "!" * 70); log("HALTED: " + m); log("!" * 70)
    OUT_LOG.write_text("\n".join(LOG), encoding="utf-8"); sys.exit(1)


def main():
    log("retention_recalibration_check.py v1.0 (2026-07-27)")
    log("Review item 4.2. Measures only; adopts nothing.\n")

    sys.path.insert(0, str(DATA_DIR))
    try:
        import rfa_terminal_value as RTV
    except Exception as e:
        die(f"could not import rfa_terminal_value.py: {type(e).__name__}: {e}")

    # sanity: the regime constants must reproduce the dollar figures quoted
    for name, r in REGIMES.items():
        if name.startswith("censored"):
            got = r["a"] * CAP25
            if not (1.2e6 < got < 1.35e6):
                die(f"regime '{name}' intercept reads ${got:,.0f}, outside the "
                    "expected $1.2M-$1.35M band. Check the constants.")
    log("  regime constants pass the sanity band")

    try:
        tv = RTV.TerminalValuer()
    except Exception as e:
        die(f"could not build TerminalValuer: {type(e).__name__}: {e}")
    sp = tv.sp

    # Rebuild the eligible decision set EXACTLY as _calibrate_qualify_rates
    # does, so this diagnostic and the calibration describe the same events.
    last = (sp.spine.sort_values("season_start")
            .groupby("contract_id").tail(1))
    elig = last[last["season_start"].between(2018, 2024)
                & last["pp_expiry"].isin(["RFA", "UFA no QO"])]
    log(f"  observable qualify-or-walk decisions: {len(elig)}")

    rows = []
    n_signyear_fallback = [0]
    for _, r in elig.iterrows():
        season = int(r["season_start"])
        a, _src = sp.anchor(r["nk"], season + 1)
        no_anchor = bool(pd.isna(a))
        war = 0.0 if no_anchor else float(a)
        bucket = "negative" if no_anchor else RTV._anchor_bucket(war)
        qualified = 1 if r["pp_expiry"] == "RFA" else 0

        # position, for the regime that splits the slope
        pos = str(r.get("position", "")) or ""
        is_D = pos.upper().startswith("D")

        # The qualifying offer, using the project's own CBA mechanics.
        prior_sal = r.get("cs_nhl_salary", np.nan)
        prior_cap = r.get("cs_cap_hit", np.nan)
        if pd.isna(prior_cap):
            prior_cap = r.get("pp_cap_hit", np.nan)
        if pd.isna(prior_sal):
            prior_sal = r.get("pp_aav", prior_cap)      # D-C fallback, unchanged
        if pd.isna(prior_sal) or pd.isna(prior_cap):
            continue
        # Whether the contract was signed after July 2020 decides if the
        # 120%-of-cap-hit ceiling applies. `start_season_year` is NOT on the
        # season spine, and using the contract's FINAL season here would
        # misclassify every multi-year deal signed before 2020. Derive the
        # first season from the contract length instead, and say so if even
        # that is unavailable.
        plen = r.get("pp_length", np.nan)
        if pd.notna(plen) and float(plen) > 0:
            signed_2020_plus = (season - int(plen) + 1) >= 2020
        else:
            signed_2020_plus = season >= 2020
            n_signyear_fallback[0] += 1
        try:
            qo = RTV.qualifying_offer(float(prior_sal), float(prior_cap),
                                      season + 1, signed_2020_plus)
        except Exception:
            continue

        try:
            ceil = RTV.cap_path(season + 1, 0)
        except Exception:
            ceil = CAP25
        try:
            lmin = RTV.league_min_path(season + 1)
        except Exception:
            lmin = 775_000.0

        row = dict(contract_id=r["contract_id"], season=season,
                   nk=r["nk"], bucket=bucket, no_anchor=no_anchor,
                   war=war, is_D=is_D, qualified=qualified, qo=qo)
        for name, rg in REGIMES.items():
            b = rg["bD"] if is_D else rg["bF"]
            val = max((rg["a"] + b * war) * ceil, lmin)
            row[f"value::{name}"] = val
            row[f"worth_qualifying::{name}"] = int(val > qo)
        rows.append(row)

    if not rows:
        die("no decisions could be evaluated. Check the spine columns.")
    df = pd.DataFrame(rows)
    log(f"  decisions evaluated: {len(df)} "
        f"(of which no anchor: {int(df['no_anchor'].sum())})")
    log(f"  observed overall retention: {df['qualified'].mean()*100:.1f}%")
    if n_signyear_fallback[0]:
        log(f"  WARNING: {n_signyear_fallback[0]} decisions had no contract "
            "length, so the signing year fell back to the final season. This "
            "can misapply the 120% ceiling, which binds on ~1.9% of contracts.")
    log("")

    # ---- the headline comparison ----------------------------------------
    log("=" * 74)
    log("MODEL-IMPLIED RETENTION vs WHAT TEAMS ACTUALLY DID")
    log("=" * 74)
    log("  'implied' = share of decisions where projected value exceeds the")
    log("  qualifying offer. 'observed' = share teams actually qualified.\n")
    hdr = f"  {'bucket':10s} {'n':>5s} {'observed':>10s}"
    for name in REGIMES:
        hdr += f" {name[:22]:>24s}"
    log(hdr)
    summary = []
    for b in BUCKETS + ["ALL"]:
        g = df if b == "ALL" else df[df["bucket"] == b]
        if not len(g):
            continue
        obs = g["qualified"].mean()
        line = f"  {b:10s} {len(g):>5d} {obs*100:>9.1f}%"
        rec = dict(bucket=b, n=len(g), observed=obs)
        for name in REGIMES:
            imp = g[f"worth_qualifying::{name}"].mean()
            gap = imp - obs
            line += f" {imp*100:>14.1f}% ({gap*100:+5.1f})"
            rec[f"implied::{name}"] = imp
        summary.append(rec)
        log(line)

    # ---- how many real walk-aways does each regime predict? --------------
    log("\n" + "=" * 74)
    log("SHARE OF REAL WALK-AWAYS THE MODEL PREDICTS ON ITS OWN")
    log("=" * 74)
    log("  This is the 18% figure that justified the D14(c) calibration,")
    log("  restated under each price regime.\n")
    walked = df[df["qualified"] == 0]
    for name in REGIMES:
        caught = 1 - walked[f"worth_qualifying::{name}"].mean()
        log(f"  {name:28s} predicts {caught*100:5.1f}% of the "
            f"{len(walked)} real walk-aways")

    # ---- the over-correction test ----------------------------------------
    log("\n" + "=" * 74)
    log("IS THE STACK OVER-CORRECTING?")
    log("=" * 74)
    verdict_lines = []
    for b in ("fringe", "negative"):
        g = df[df["bucket"] == b]
        if not len(g):
            continue
        obs = g["qualified"].mean()
        imp = g["worth_qualifying::censored + position"].mean()
        if imp < obs:
            verdict_lines.append(
                f"  {b}: model implies {imp*100:.1f}% retention against an "
                f"observed {obs*100:.1f}%. The corrected price equation is "
                f"ALREADY more pessimistic than teams are. Applying the "
                f"D14(c) gate on top of this would correct a bias that the "
                f"price fix has already removed.")
        else:
            verdict_lines.append(
                f"  {b}: model implies {imp*100:.1f}% retention against an "
                f"observed {obs*100:.1f}%. The model remains more generous "
                f"than teams are, so the D14(c) gate is still doing real "
                f"work and the stack is not over-correcting.")
    for l in verdict_lines:
        log(l)

    # ---- sensitivity: the value-above-cost threshold is arbitrary --------
    log("\n" + "=" * 74)
    log("SENSITIVITY: the 'worth qualifying' threshold")
    log("=" * 74)
    log("  A strict value-above-cost rule is arbitrary at the margin. Below,")
    log("  the implied retention rate when the bar is moved by a margin.\n")
    rg = REGIMES["censored + position"]
    for margin in (-0.5e6, 0.0, 0.5e6, 1.0e6):
        imp = (df[f"value::censored + position"] > df["qo"] + margin).mean()
        log(f"    value must exceed QO by ${margin/1e6:+.1f}M -> "
            f"implied retention {imp*100:5.1f}%  "
            f"(observed {df['qualified'].mean()*100:.1f}%)")

    df.to_csv(OUT_ROWS, index=False)
    pd.DataFrame(summary).to_csv(
        DATA_DIR / "retention_recalibration_summary.csv", index=False)
    log(f"\n  wrote {OUT_ROWS.name} and retention_recalibration_summary.csv")
    OUT_LOG.write_text("\n".join(LOG), encoding="utf-8")
    log(f"  wrote {OUT_LOG.name}")


if __name__ == "__main__":
    main()
