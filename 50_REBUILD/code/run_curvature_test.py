"""run_curvature_test.py -- is the surplus gradient mispricing, or a straight
line drawn through a curved price function?

EXPERIMENTAL (50_REBUILD). Gates the thesis's central claim.

THE QUESTION
    Surplus under the fitted currency rises with forecast production, and the
    implied price per forecast win falls fourfold across the range. Read one
    way that is "clubs underpay for elite production" -- the finding the
    project exists to establish. Read the other way it is "the price function
    is concave and we fitted a straight line", which is a modelling error
    wearing the finding's clothes. The arithmetic is identical; only an
    out-of-sample test separates them.

WHY IT IS BEING RUN AGAIN
    The locked record rejected a curved price line out of sample at Stage 3.
    That test used anchors dated at the CONTRACT START, and the signing-date
    audit later showed 30% of that sample was signed before its trailing
    seasons had finished, rising to 58% at 3+ wins. Curvature is a claim about
    the top of the market, and the top of the market is exactly where the
    start-dated anchors were most wrong. The old answer may have been right
    for the wrong reason, or wrong. It is cheap to check and it decides
    whether the headline number survives.

THE RULE, FIXED BEFORE LOOKING
    If a curved specification beats the straight line out of sample, the
    currency adopts the curve and the surplus gradient is an artifact to that
    extent. If the straight line holds, the gradient stands as a finding. The
    comparison is the same rolling held-out protocol used for decision B, on
    identical rows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
from contract_price_model import contract_sample, attach_forecasts, tobit, predict_tobit
from player_season_table import build as build_table
from ability_forecast import A1AgingParticipationImputedNC
from run_phase4_decisions import prep

SCRIPT_VERSION = "1.0"

BASE = ["length", "is_RFA", "rfa_x_war", "is_D", "one_year", "war_year1"]


def add_shapes(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    w = d["war_per_season"]
    d["war_sq"] = w ** 2
    # Square root of the positive part: concave by construction, and defined
    # for the below-replacement players a log would throw away.
    d["war_sqrt"] = np.sqrt(np.clip(w, 0, None))
    d["war_log"] = np.log1p(np.clip(w, 0, None))
    # A hinge at one win a season: lets the price per win change slope once,
    # without imposing a shape on either side of it.
    d["war_hi"] = np.clip(w - 1.0, 0, None)
    return d


SPECS = {
    "straight line": ["war_per_season"],
    "plus a square": ["war_per_season", "war_sq"],
    "square root": ["war_sqrt"],
    "log": ["war_log"],
    "hinge at 1 win": ["war_per_season", "war_hi"],
}


def rolling(d: pd.DataFrame, cols) -> tuple[float, int, dict]:
    err, n, by_yr = [], 0, {}
    for yr in range(2018, 2026):
        tr, te = d[d["start_yr"] < yr], d[d["start_yr"] == yr]
        if len(tr) < 200 or not len(te):
            continue
        b, _, _ = tobit(tr[cols + BASE].to_numpy(float),
                        tr["cap_share"].to_numpy(float),
                        tr["floor_share"].to_numpy(float))
        p = np.maximum(predict_tobit(b, te[cols + BASE].to_numpy(float)),
                       te["floor_share"].to_numpy(float))
        e = np.abs(p - te["cap_share"].to_numpy(float))
        by_yr[yr] = float(e.mean())
        err.append(e.sum()); n += len(te)
    return float(np.sum(err) / n), n, by_yr


def main() -> None:
    C.banner("run_curvature_test.py", SCRIPT_VERSION)
    table = build_table(birthdate_csv=C.OUT_DIR / "birthdates.csv", verbose=False)
    d = add_shapes(prep(attach_forecasts(contract_sample(),
                                         A1AgingParticipationImputedNC, table,
                                         verbose=False)))
    C.log(f"  {len(d)} contracts, forecasts dated at each signing")
    C.log("  Held out by season, error in cap share. 0.001 is a tenth of a")
    C.log("  percent of the cap, about $88,000 in 2024.")
    C.log("")

    res = {}
    for name, cols in SPECS.items():
        mae, n, by_yr = rolling(d, cols)
        res[name] = (mae, n, by_yr)
    base = res["straight line"][0]

    C.log(f"  {'specification':<18}{'n':>6}{'error':>10}{'vs straight':>14}{'seasons won':>14}")
    for name, (mae, n, by_yr) in res.items():
        wins = sum(1 for y, v in by_yr.items()
                   if v < res["straight line"][2].get(y, np.inf))
        tag = "-" if name == "straight line" else f"{100 * (mae / base - 1):+.2f}%"
        won = "-" if name == "straight line" else f"{wins} of {len(by_yr)}"
        C.log(f"  {name:<18}{n:>6}{mae:>10.5f}{tag:>14}{won:>14}")
    C.log("")

    best = min(res, key=lambda k: res[k][0])
    if best == "straight line":
        C.log("  VERDICT: the straight line holds. No curved specification beats it out")
        C.log("  of sample, so the falling price per win is not the line failing to bend")
        C.log("  where the data bends. The surplus gradient stands as a finding.")
    else:
        C.log(f"  VERDICT: '{best}' beats the straight line out of sample. The currency")
        C.log("  should adopt it, and the surplus gradient is an artifact to that extent.")
    C.log("")
    C.log("  This is the Stage 3 test rerun on signing-dated forecasts. The locked")
    C.log("  record rejected curvature on start-dated anchors; the result above is")
    C.log("  what that test says once the anchors are dated when the pen moved.")
    C.write_log("curvature_test_run_log.txt")


if __name__ == "__main__":
    main()
