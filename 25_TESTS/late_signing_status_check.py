"""late_signing_status_check.py -- what reading contract status on July 1 costs late-signed contracts.

WHY (2026-10-04). contract_npv.py values each contract from its first season's
page with the as-of date left at its default, July 1 of that season. xNPV 1's
chance of playing reads contract status at the as-of date
(skater_forecast.ContractForecaster.forecast: the signing-dated path,
p_play_signed, runs only when an as-of date other than the page date is
passed). A contract signed after July 1 is therefore invisible to its own
chance of playing: the player is "not under contract" for each of its
seasons, while its cap hit is counted in full. skater_forecast.py's docstring
says a contract valuation reads status "at a contract's signing"; in the
priced sweep it does not. The rebuild's dollar scoring did read it at the
signing (40_DOCS/model_evidence/xNPV1_Migration_Plan.md).

WHAT IT DOES (nothing is changed or adopted)
    1. Reads 30_OUTPUT/contract_npv_spine.csv, the priced sweep, and the
       PuckPedia signing dates (skater_forward_projection.load_signing_dates).
    2. Keeps skater contracts signed after July 1 of their first season and
       before July 1 of the next, the window check_as_of accepts.
    3. Re-values each with as_of = its signing date, and compares npv_total
       with the sweep's July 1 value. Assumed: the as-of date changes only the
       chance of playing here (the chain can also pick up an extension signed
       by that date; the log counts contracts whose season count changed).

Result on 2026-10-04 (laptop, the spine written by the 2026-10-03 dashboard
refresh): 1,533 of 2,759 priced skater contracts signed after July 1; 1,530
inside the window; 1,351 move up; median +$0.33M, mean +$0.41M, total
+$622.0M; largest +$4.11M (Kris Letang, 2022). Season counts unchanged in all.

HOW TO RUN (repo root, after contract_npv.py; about ten minutes):
    python 25_TESTS/late_signing_status_check.py
Writes 30_OUTPUT/late_signing_status_check.csv and _log.txt.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import pandas as pd

import contract_npv as CN

SCRIPT_VERSION = "1.0"
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def main():
    log(f"late_signing_status_check.py v{SCRIPT_VERSION}")
    eng = CN.NPVEngine()
    d = pd.read_csv(OUTPUT_DIR / "contract_npv_spine.csv")
    d = d[d["position"] == "skater"].copy()
    # join key: contract_id -> PuckPedia signing date (NaT where not on file)
    d["signed"] = d["contract_id"].map(eng.sp.signed)
    july1 = pd.to_datetime(d["valuation_season"].astype(str) + "-07-01")
    late = d[d["signed"] > july1]
    inwin = late[late["signed"] < july1[late.index] + pd.DateOffset(years=1)]
    log(f"skater contracts priced {len(d):,}; signed after July 1 of their first season "
        f"{len(late):,}; inside the as-of window {len(inwin):,}")
    rows = []
    for _, r in inwin.iterrows():
        _, s = eng.npv(int(r["player_id"]), int(r["valuation_season"]), as_of=r["signed"])
        if s.get("status") != "ok":
            continue
        rows.append(dict(contract_id=r["contract_id"], name=r["full_name"],
                         valuation_season=r["valuation_season"], signed=r["signed"].date(),
                         n_seasons=r["n_seasons"], n_seasons_signed=s["n_contract_seasons"],
                         npv_july1=r["npv_total"], npv_signed=s["npv_total"]))
    x = pd.DataFrame(rows)
    # money compared at $1 precision (CLAUDE.md)
    x["diff"] = (x["npv_signed"] - x["npv_july1"]).round(0)
    log(f"re-valued {len(x):,}; up {int((x['diff'] > 0).sum()):,}, down {int((x['diff'] < 0).sum()):,}, "
        f"unchanged {int((x['diff'] == 0).sum()):,}; season count changed in "
        f"{int((x['n_seasons'] != x['n_seasons_signed']).sum()):,}")
    log(f"change in NPV: median ${x['diff'].median() / 1e6:+.2f}M, mean ${x['diff'].mean() / 1e6:+.2f}M, "
        f"total ${x['diff'].sum() / 1e6:+,.1f}M")
    log("by contract length (count, mean $M):")
    for n, g in x.groupby("n_seasons"):
        log(f"  {n} seasons: {len(g):5,d}  {g['diff'].mean() / 1e6:+.2f}")
    log("largest five:")
    for _, r in x.nlargest(5, "diff").iterrows():
        log(f"  {r['name']:24s} {r['valuation_season']}  {r['n_seasons']}yr  "
            f"${r['npv_july1'] / 1e6:+.2f}M -> ${r['npv_signed'] / 1e6:+.2f}M")
    x.to_csv(OUTPUT_DIR / "late_signing_status_check.csv", index=False)
    (OUTPUT_DIR / "late_signing_status_check_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
