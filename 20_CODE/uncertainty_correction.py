"""
uncertainty_correction.py  --  Review item 3.6.
===============================================
SCRIPT VERSION: v1.0 (2026-07-27)

WHAT THIS IS
------------
For each future season the model takes one number, its single best guess of the
player's production, and runs that number through the price equation. The future
is not one number. It is a range.

When the price equation is a straight line, this does not matter: the value of
the average outcome equals the average of the outcome values, so pricing the
best guess is exactly right. We rejected the bent curve in item 3.2, so the
straight line is what the model uses.

ONE thing in the chain is still not a straight line, and that is the league
minimum floor. Value is `max(price, minimum)`, which has a kink at the floor.
For a player near the floor, the downside is capped and the upside is not, so
the average of the outcomes is worth more than the single best guess. The model
currently books only the best guess, which understates weak players.

This script measures that gap and reports how far it would move each output. It
does NOT modify the valuation chain. Nothing is wired in until the size is known.

WHY THE REVIEW'S TABLE NO LONGER APPLIES
----------------------------------------
The review measured this against the bent price curve and reported +$1.19M at
zero wins three years out, with NEGATIVE corrections for good players because
the bent curve flattened at the top. A straight line has no flattening. Every
correction here is positive and dies out above roughly 1.5 wins, and the
figures are about half the review's.

WHAT THIS DOES NOT TOUCH
------------------------
Item 4.4 was closed with NO change: the floor stays before the survival
adjustment. The floor is a property of the player conditional on being
employed, not a property of the roster spot, so it is correctly risked along
with everything else. This correction therefore sits INSIDE the survival
discount, exactly where the point-estimate value sits now.

Goaltenders are out of scope: they price on a separate rate, project flat
rather than through the aging curve, and the spread used here comes from the
skater backcast. The count of goalie contracts skipped is reported.

Terminal-value rows are out of scope. They run through a separate chain with
its own survival machinery, and mixing this in without tracing that chain would
repeat a mistake made earlier in this review.

THE THREE CHOICES BAKED IN, AND WHICH ONES COULD MATTER
--------------------------------------------------------
1. SPREAD OF THE RANGE. Taken from the projection script's own backcast, which
   reports mean absolute error of 0.522, 0.735, and 0.803 wins at one, two, and
   three seasons out. Converted to a standard deviation by multiplying by
   1.2533, which is the relationship between the two for a normal distribution.
   Beyond three seasons the three-season figure is held flat, because the
   backcast stops there. THIS IS A PLACEHOLDER for k >= 4 and is flagged in the
   output rather than presented as an estimate.

2. SHAPE OF THE RANGE. Assumed normal. Production forecast errors are probably
   right-skewed, which would make the correction slightly larger than reported
   here, since the upside tail is what the floor lets through. The direction of
   that error is therefore conservative.

3. ONE SPREAD FOR EVERYONE. The backcast figures are pooled across players.
   Better players almost certainly have wider ranges in absolute terms. That
   would matter if the correction were large for good players, and it is not:
   it is near zero above 1.5 wins whatever spread is used. So the pooled figure
   is adequate where it does any work.

A FOURTH ISSUE, WHICH IS A REAL LIMITATION RATHER THAN A CHOICE
---------------------------------------------------------------
The projection already floors its point estimate at zero wins for
below-replacement players, through replacement-reversion and the RATIO_FLOOR
guard. Spreading a symmetric range around a point estimate that has itself been
truncated will overstate the upside for the players sitting at that truncation.
The output reports how many contract-seasons are in that position so the
exposure is visible.

HOW IT RUNS
-----------
    python uncertainty_correction.py

Read-only with respect to the model. Writes its own results and log.

OUTPUTS
-------
  uncertainty_correction_rows.csv      one row per contract-season
  uncertainty_correction_summary.csv   aggregates by length, age, and anchor
  uncertainty_correction_runlog.txt
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SCRIPT_VERSION = "v1.0 (2026-07-27)"
DATA_DIR = Path(os.environ.get("XNPV_DATA", "."))
OUT_ROWS = DATA_DIR / "uncertainty_correction_rows.csv"
OUT_SUM = DATA_DIR / "uncertainty_correction_summary.csv"
OUT_LOG = DATA_DIR / "uncertainty_correction_runlog.txt"

# ---------------------------------------------------------------------------
# The spread of the projection range, from the projection script's own backcast
# (validation battery, test [2], positive anchors). MAE in WAR by horizon.
# ---------------------------------------------------------------------------
BACKCAST_MAE = {1: 0.522, 2: 0.735, 3: 0.803}
MAE_TO_SD = 1.2533          # for a normal distribution, SD = MAE x sqrt(pi/2)
MAX_BACKCAST_K = 3          # beyond this the spread is a held-flat placeholder

LOG = []
def log(m=""):
    print(m); LOG.append(str(m))

def die(m):
    log("\n" + "!" * 74); log("HALTED: " + m); log("!" * 74)
    OUT_LOG.write_text("\n".join(LOG), encoding="utf-8"); sys.exit(1)

def sd_for_horizon(k):
    """Standard deviation of projected WAR, k seasons ahead.

    k=0 is the valuation season and carries the trailing anchor itself, which
    is observed rather than projected, so its spread is zero and no correction
    applies there."""
    if k <= 0:
        return 0.0
    mae = BACKCAST_MAE.get(min(k, MAX_BACKCAST_K))
    return mae * MAE_TO_SD

def expected_floored_value(point_value, sd_dollars, floor_dollars):
    """The average of what the outcomes are worth, rather than the worth of the
    average outcome.

    Value is `max(price, floor)`. With price normally distributed around the
    point estimate, the average of the floored values has a closed form:

        E[max(X, F)] = F*Phi(d) + mu*(1 - Phi(d)) + sigma*phi(d),  d = (F-mu)/sigma

    where Phi and phi are the normal cumulative and density functions. The
    correction is that quantity minus what the model books today, which is
    max(mu, F). It is never negative: a floor can only ever help.
    """
    if sd_dollars <= 0:
        return max(point_value, floor_dollars)
    d = (floor_dollars - point_value) / sd_dollars
    return (floor_dollars * stats.norm.cdf(d)
            + point_value * (1.0 - stats.norm.cdf(d))
            + sd_dollars * stats.norm.pdf(d))

def main():
    log(f"uncertainty_correction.py {SCRIPT_VERSION}")
    log("Review item 3.6. Measures only; changes nothing in the chain.")
    log(f"data dir: {DATA_DIR.resolve()}\n")

    # The valuation chain lives in contract_npv.py, which already assembles the
    # projections, the survival chain, and the discounting. Rather than rebuild
    # any of that, this script drives the existing engine and recomputes the
    # value column two ways for each contract-season.
    sys.path.insert(0, str(DATA_DIR))
    try:
        import contract_npv as CN
    except Exception as e:
        die(f"could not import contract_npv.py from {DATA_DIR}: "
            f"{type(e).__name__}: {e}")

    try:
        engine = CN.NPVEngine()
    except Exception as e:
        die(f"could not build the NPV engine: {type(e).__name__}: {e}. "
            "Run contract_npv.py on its own first and make sure it completes.")

    spine = pd.read_csv(DATA_DIR / "contract_npv_spine.csv")
    log(f"  contracts in the NPV spine: {len(spine)}")

    # The rate in force. Read from the projection module so this script cannot
    # drift from the engine it is measuring.
    try:
        import skater_forward_projection as SFP
        ALPHA, BETA = SFP.ALPHA, SFP.BETA
    except Exception as e:
        die(f"could not read the locked rate from skater_forward_projection: {e}")
    log(f"  locked rate in force: ALPHA={ALPHA:.8f}  BETA={BETA:.8f}")
    log("  NOTE: if the price equation has been re-fitted since (interaction "
        "specification, censored), these constants will be stale and this "
        "measurement is provisional until the chain is rebuilt on the new rate.")

    rows = []
    n_fail = 0
    n_goalie = 0
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
        # SKATERS ONLY. Goalie rows carry row_type "contract" as well, but they
        # are built by a different branch of the engine: a separate rate, a flat
        # projection instead of the aging curve, and no cap_ceiling_exante or
        # league_min on the row. The spread used here comes from the SKATER
        # backcast, so applying it to goalies would be inventing a number rather
        # than measuring one. Counted and reported, not estimated.
        if meta.get("position") != "skater":
            n_goalie += 1
            continue
        d = det[det["row_type"] == "contract"]      # terminal rows out of scope
        for _, r in d.iterrows():
            k = int(r["k"])
            pw = r.get("projected_war", np.nan)
            val = float(r["value_dollars"])
            if pd.isna(pw):
                continue
            # The cap ceiling and the floor are BOTH carried on the projection
            # row (`cap_ceiling_exante`, `league_min`). Read them directly.
            # An earlier version of this script looked for a column that does
            # not exist and then back-solved the ceiling from value_dollars.
            # That was circular, because value_dollars is already floored: it
            # set the floor equal to the point estimate on every row and turned
            # the whole measurement into an artifact. Hence the hard guard below.
            if "cap_ceiling_exante" not in r or "league_min" not in r:
                die("projection rows are missing cap_ceiling_exante or "
                    "league_min. Do not substitute a fallback here: a wrong "
                    "floor silently produces a plausible-looking result.")
            ceil = float(r["cap_ceiling_exante"])
            floor_d = float(r["league_min"])
            raw_check = (ALPHA + BETA * pw) * ceil
            # The engine's own value must be the floored raw value. If this
            # fails, the rate or the ceiling being used here is not the one the
            # engine used, and nothing downstream is meaningful.
            if abs(max(raw_check, floor_d) - val) > 1.0:
                die(f"reconstruction check failed: engine value ${val:,.0f} "
                    f"but max(raw ${raw_check:,.0f}, floor ${floor_d:,.0f}) "
                    f"= ${max(raw_check, floor_d):,.0f}. The rate or ceiling "
                    "in this script does not match the engine.")
            sd_war = sd_for_horizon(k)
            sd_dollars = BETA * sd_war * ceil
            raw_value = raw_check
            e_val = expected_floored_value(raw_value, sd_dollars, floor_d)
            corr = e_val - max(raw_value, floor_d)
            rows.append(dict(
                contract_id=sr.get("contract_id"), player_id=pid,
                full_name=sr.get("full_name"), valuation_season=t0, k=k,
                projected_war=pw, point_value=val, expected_value=e_val,
                correction=corr, survival=float(r.get("survival", 1.0)),
                discount=float(r.get("discount", 1.0)),
                pv_correction=corr * float(r.get("survival", 1.0))
                              * float(r.get("discount", 1.0)),
                placeholder_spread=bool(k > MAX_BACKCAST_K),
                at_projection_floor=bool(abs(pw) < 1e-9)))
    if n_goalie:
        log(f"  goalie contracts skipped (out of scope, see header): {n_goalie}")
    if n_fail:
        log(f"  contracts skipped (engine did not return a priced result): {n_fail}")
    if not rows:
        die("no contract-seasons were priced. The engine returned nothing usable.")

    df = pd.DataFrame(rows)
    log(f"  contract-seasons measured: {len(df)}")

    # ---- exposure to the two flagged limitations -------------------------
    ph = int(df["placeholder_spread"].sum())
    log(f"  seasons using the held-flat placeholder spread (k>{MAX_BACKCAST_K}): "
        f"{ph} ({ph/len(df)*100:.1f}%)")
    tf = int(df["at_projection_floor"].sum())
    log(f"  seasons sitting exactly at the projection's own zero-WAR floor: "
        f"{tf} ({tf/len(df)*100:.1f}%) -- the symmetric range overstates the "
        "upside for these")

    # ---- how far does the answer move? -----------------------------------
    per_contract = df.groupby("contract_id", as_index=False).agg(
        npv_correction=("pv_correction", "sum"),
        seasons=("k", "count"))
    m = spine.merge(per_contract, on="contract_id", how="left")
    m["npv_correction"] = m["npv_correction"].fillna(0.0)
    m["npv_new"] = m["npv_total"] + m["npv_correction"]

    log("\n" + "=" * 74)
    log("HOW FAR THE OUTPUT MOVES")
    log("=" * 74)
    log(f"  mean correction per contract:   ${m['npv_correction'].mean()/1e6:+.4f}M")
    log(f"  median correction per contract: ${m['npv_correction'].median()/1e6:+.4f}M")
    log(f"  largest single correction:      ${m['npv_correction'].max()/1e6:+.4f}M")
    flip = int(((m["npv_total"] < 0) & (m["npv_new"] >= 0)).sum())
    log(f"  contracts moving from negative NPV to positive: {flip} of "
        f"{int((m['npv_total']<0).sum())} currently negative")

    log("\n  by contract length:")
    if "n_seasons" in m.columns:
        for L, g in m.groupby("n_seasons"):
            log(f"    {int(L)}yr  n={len(g):>4}  mean correction "
                f"${g['npv_correction'].mean()/1e6:+.4f}M  "
                f"mean NPV ${g['npv_total'].mean()/1e6:+7.2f}M -> "
                f"${g['npv_new'].mean()/1e6:+7.2f}M")

    log("\n  correction by projected production (the shape of the effect):")
    df["war_band"] = pd.cut(df["projected_war"], [-99, 0, 0.5, 1, 2, 99],
                            labels=["<=0", "0 to 0.5", "0.5 to 1", "1 to 2", ">2"])
    for b, g in df.groupby("war_band", observed=True):
        log(f"    {str(b):<10} n={len(g):>5}  mean correction "
            f"${g['correction'].mean()/1e6:+.4f}M per season")

    df.to_csv(OUT_ROWS, index=False)
    m[["contract_id", "player_id", "full_name", "npv_total",
       "npv_correction", "npv_new"]].to_csv(OUT_SUM, index=False)
    log(f"\n  wrote {OUT_ROWS.name} and {OUT_SUM.name}")
    OUT_LOG.write_text("\n".join(LOG), encoding="utf-8")
    log(f"  wrote {OUT_LOG.name}")

if __name__ == "__main__":
    main()
