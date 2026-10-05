"""control_weight_check.py -- why the control-year weights sit below July's, for two buckets.

WHY (2026-10-05, plan of record step 6; Thomas: "run the check"). The control-year weight built for open
decision 1 measures P(plays next season | qualified) on NHL regulars at the decision (Thomas: 10+ games in
one of the three seasons before it). On the laptop run it gave star 100%, regular 99.4%, fringe 83.9%,
below replacement 74.9%. July's figures, backed out of DECISIONS.md ("Control-year departure": corrected
weights below-replacement 0.694 -> 0.619, fringe 0.795 -> 0.753, regular 0.888 -> 0.877, star unchanged),
are about 100%, 98.8%, 94.7% and 89.2%. Two differences could explain the fringe and below-replacement gap,
neither verified: (1) the build buckets players on xNPV 1's FORECAST, July on the trailing 60/40 WAR total;
(2) the "NHL regular" condition (July's definition is not in the record). Until one of them is shown to
carry it, a build error is not ruled out (CLAUDE.md, 2026-10-05). MEASUREMENT ONLY: nothing changes.

WHAT IT MEASURES, on production's own decision set (rfa_terminal_value.TerminalValuer: the last season of
every skater contract ending 2018-2024 whose expiry reads RFA = qualified or "UFA no QO" = walked):
    bucket basis   forecast  xNPV 1's WAR if he plays at the decision (the build)
                   trailing  the trailing 60/40 WAR total at the decision (skater_value_engine's rule;
                             July's basis); none = below replacement
    NHL regular    10 in 3   a forecast at the decision: 10+ games in one of the three seasons before
                             (Thomas's rule; the build)
                   20 final  20+ games in the contract's final season (stricter)
                   anyone    no condition (the first build)
    "plays"        one NHL game or more the next season (forecast_config.PARTICIPATION_GP)
  For each pair: n qualified and P(plays | qualified) by bucket, beside July's.
GUARD: forecast buckets under "10 in 3" must equal production's own table (TerminalValuer.plays_given_q).

HOW TO RUN (repo root, laptop; about five minutes):
    python 25_TESTS/control_weight_check.py
Writes 30_OUTPUT/control_weight_check_log.txt.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C
import rfa_terminal_value as RTV
import skater_value_engine as SVE

SCRIPT_VERSION = "1.0"
BUCKETS = ["star", "regular", "fringe", "negative"]
JULY = {"star": 1.000, "regular": 0.877 / 0.888, "fringe": 0.753 / 0.795, "negative": 0.619 / 0.694}
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def main():
    log(f"control_weight_check.py v{SCRIPT_VERSION}")
    tv = RTV.TerminalValuer()
    sp = tv.sp
    fc = sp.forecaster
    tbl = fc.table
    gp_of = tbl.groupby(["career_key", "syr"])["GP"].sum().to_dict()
    lut = SVE.build_skater_war_lookup(exclude_merged=False, prorate=True)

    last = sp.spine.sort_values("season_start").groupby("contract_id").tail(1)
    elig = last[last["season_start"].between(2018, 2024) & last["pp_expiry"].isin(["RFA", "UFA no QO"])]
    rows = []
    for _, r in elig.iterrows():
        t_dec = int(r["season_start"]) + 1
        f = fc.forecast(r["nk"], t_dec, 0)
        a = np.nan if f is None else float(f.iloc[0]["war_if_plays"])
        tw, _src = SVE.trailing_weighted_war(r["nk"], t_dec, lut)
        ck = fc.career_of.get(r["nk"])
        rows.append(dict(
            q=int(r["pp_expiry"] == "RFA"),
            b_forecast="negative" if pd.isna(a) else RTV._anchor_bucket(a),
            b_trailing="negative" if pd.isna(tw) else RTV._anchor_bucket(float(tw)),
            reg_10in3=not pd.isna(a),
            reg_20final=gp_of.get((ck, t_dec - 1), 0.0) >= 20,
            plays=gp_of.get((ck, t_dec), 0.0) >= C.PARTICIPATION_GP))
    d = pd.DataFrame(rows)
    q = d[d["q"] == 1]
    log(f"decisions: {len(d):,}; qualified: {len(q):,}")

    # guard: the build's own table
    g = q[q["reg_10in3"]].groupby("b_forecast")["plays"].mean().to_dict()
    gap = max(abs(g.get(b, np.nan) - tv.plays_given_q[b]) for b in tv.plays_given_q)
    log(f"guard: forecast buckets, 10-in-3 rule reproduce the build's table (largest gap {gap:.1e})")
    assert gap < 1e-12, "this check does not rebuild the production table; nothing below is read"

    log("\nP(plays next season | qualified), n qualified in brackets; July's figure in the last column")
    head = f"  {'bucket basis':10s}{'NHL regular':12s}" + "".join(f"{b:>18s}" for b in BUCKETS)
    log(head)
    for basis in ("forecast", "trailing"):
        for reg, lab in (("reg_10in3", "10 in 3"), ("reg_20final", "20 final"), (None, "anyone")):
            sub = q if reg is None else q[q[reg]]
            cells = []
            for b in BUCKETS:
                s = sub[sub[f"b_{basis}"] == b]
                cells.append(f"{s['plays'].mean() * 100:6.1f}% ({len(s):4d})" if len(s) else f"{'--':>14s}")
            log(f"  {basis:10s}{lab:12s}" + "".join(f"{c:>18s}" for c in cells))
    log(f"  {'July':22s}" + "".join(f"{JULY[b] * 100:16.1f}%  " for b in BUCKETS))

    log("\nhow the two bucket bases sort the same qualified regulars (10-in-3 rule): rows forecast, columns trailing")
    ct = pd.crosstab(q.loc[q["reg_10in3"], "b_forecast"], q.loc[q["reg_10in3"], "b_trailing"]).reindex(
        index=BUCKETS, columns=BUCKETS).fillna(0).astype(int)
    log(ct.to_string())
    p = Path(os.environ["OUTPUT_DIR"]) / "control_weight_check_log.txt"
    p.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
