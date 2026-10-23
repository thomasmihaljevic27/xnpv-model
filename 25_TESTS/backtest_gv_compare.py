"""
backtest_gv_compare.py -- the Game Value check of the back-test: each result on Bacon's WAR beside the same result with
the outcome measured on Game Value, and the protocol's verdict for each.

THE RULE (40_DOCS/Backtest_Protocol.md, "The Game Value check", committed before the run, db3e04e): a result holds on
Game Value when, on GV-adj (the primary validator), its estimate keeps the WAR run's sign and its 95% interval still
excludes its null (zero; one half for the favoured-club share); otherwise it is not confirmed. GV-raw is reported beside,
not decisive. A result that was not statistically significant at 5% on WAR is "not a WAR finding" and is shown only.

INPUTS: OUTPUT_DIR/backtest_results.csv, backtest_results_gv_adj.csv, backtest_results_gv_raw.csv, and the matching
backtest_sides*.csv and backtest_assets*.csv (backtest.py v1.5, XNPV_OUTCOME_METRIC = war, gv_adj, gv_raw).
OUTPUTS: OUTPUT_DIR/backtest_gv_compare.csv, backtest_gv_compare_log.txt.
Run from the repo root, after the three back-test runs:  python 25_TESTS/backtest_gv_compare.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "backtest_gv_compare.py v1.0 (2026-10-20)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
RUNS = {"war": "", "gv_adj": "_gv_adj", "gv_raw": "_gv_raw"}
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def main():
    sys.stdout.reconfigure(errors="replace")
    log(SCRIPT_VERSION)
    for m, suf in RUNS.items():
        first = (OUTPUT_DIR / f"backtest_log{suf}.txt").read_text(encoding="utf-8").splitlines()[:2]
        log(f"  {m}: {' | '.join(first)}")
        assert f"outcome metric: {m}" in " ".join(first), (m, first)          # GUARD: each file is its metric's run
    R = {m: pd.read_csv(OUTPUT_DIR / f"backtest_results{suf}.csv") for m, suf in RUNS.items()}
    key = ["test", "group"]
    t = R["war"][key + ["n_trades", "estimate", "lo95", "hi95", "p"]]
    for m in ("gv_adj", "gv_raw"):
        t = t.merge(R[m][key + ["estimate", "lo95", "hi95"]].rename(
            columns={"estimate": f"est_{m}", "lo95": f"lo_{m}", "hi95": f"hi_{m}"}), on=key, how="left")
    # GUARD: the forecast side does not change with the outcome's metric
    f = t[t["test"].str.endswith(": forecast")]
    assert (f["estimate"] - f["est_gv_adj"]).abs().max() < 1e-9, "forecast rows differ between runs"

    def verdict(r):
        if r["test"].endswith(": forecast") or "sensitivity" in r["test"] or "decomposition" in r["test"]:
            return "not an outcome result"
        if pd.notna(r["n_trades"]) and r["n_trades"] < 5:
            return "too few trades"                       # the star group's single side
        null = 0.5 if r["test"].startswith("A. share") else 0.0
        if not np.isfinite(r["lo95"]) or not (r["lo95"] > null or r["hi95"] < null):
            return "not a WAR finding"
        same = np.sign(r["est_gv_adj"] - null) == np.sign(r["estimate"] - null)
        excl = r["lo_gv_adj"] > null or r["hi_gv_adj"] < null
        return "holds on Game Value" if (same and excl) else "not confirmed"
    t["verdict"] = t.apply(verdict, axis=1)
    show = t[t["verdict"] != "not an outcome result"]
    log("\nEACH RESULT: WAR [95%]; GV-adj [95%]; GV-raw [95%]; verdict (the declared rule)")
    for r in show.itertuples():
        log(f"  {r.test} ({r.group})\n      WAR {r.estimate:+.3f} [{r.lo95:+.3f}, {r.hi95:+.3f}]   GV-adj {r.est_gv_adj:+.3f} "
            f"[{r.lo_gv_adj:+.3f}, {r.hi_gv_adj:+.3f}]   GV-raw {r.est_gv_raw:+.3f} [{r.lo_gv_raw:+.3f}, "
            f"{r.hi_gv_raw:+.3f}]   -> {r.verdict}")
    log("\n  verdicts: " + ", ".join(f"{k} {v}" for k, v in show["verdict"].value_counts().items()))

    # ---- the rate-free leg: club sides' net wins delivered, on each metric ----------------------------------------------
    S = {m: pd.read_csv(OUTPUT_DIR / f"backtest_sides{suf}.csv") for m, suf in RUNS.items()}
    k2 = ["trade_id", "club"]
    w = S["war"].loc[S["war"]["complete"], k2 + ["out_wins", "out_net_M"]]
    for m in ("gv_adj", "gv_raw"):
        w = w.merge(S[m][k2 + ["out_wins", "out_net_M"]].rename(columns={"out_wins": f"wins_{m}", "out_net_M": f"net_{m}"}),
                    on=k2)
    log(f"\nRATE-FREE LEG ({len(w)} club sides of complete trades): correlation of net wins delivered with Bacon's")
    for m in ("gv_adj", "gv_raw"):
        log(f"  {m}: wins r = {np.corrcoef(w['out_wins'], w[f'wins_{m}'])[0, 1]:.3f}; outcome dollars r = "
            f"{np.corrcoef(w['out_net_M'], w[f'net_{m}'])[0, 1]:.3f}")
    # ---- asset level, by position --------------------------------------------------------------------------------------
    A = {m: pd.read_csv(OUTPUT_DIR / f"backtest_assets{suf}.csv") for m, suf in RUNS.items()}
    k3 = ["asset_id", "asset_type"]
    a = A["war"][k3 + ["pos", "wins_delivered", "source"]].merge(
        A["gv_adj"][k3 + ["wins_delivered"]].rename(columns={"wins_delivered": "w_adj"}), on=k3).merge(
        A["gv_raw"][k3 + ["wins_delivered"]].rename(columns={"wins_delivered": "w_raw"}), on=k3)
    a = a[a["pos"].isin(["F", "D"]) & ((a["wins_delivered"].abs() > 0) | (a["w_adj"].abs() > 0))]
    log("\nASSET LEVEL: wins delivered, Bacon against Game Value, skaters with any realised season")
    for pos, g in a.groupby("pos"):
        log(f"  {pos}: {len(g)} assets; GV-adj r = {np.corrcoef(g['wins_delivered'], g['w_adj'])[0, 1]:.3f}, "
            f"GV-raw r = {np.corrcoef(g['wins_delivered'], g['w_raw'])[0, 1]:.3f}; totals Bacon {g['wins_delivered'].sum():,.0f}, "
            f"GV-adj {g['w_adj'].sum():,.0f}, GV-raw {g['w_raw'].sum():,.0f} wins")
    t.to_csv(OUTPUT_DIR / "backtest_gv_compare.csv", index=False)
    (OUTPUT_DIR / "backtest_gv_compare_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    log(f"\nwrote backtest_gv_compare.csv and its log in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
