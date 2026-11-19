"""
trend_both.py - the change over time in how lopsided trades are, on the trade-day grade and on the realized value
(Thomas, 2026-11-18, on the findings document: "Why not use both? Why be inconsistent with how we're measuring this";
declared in 40_DOCS/Backtest_Protocol.md before it was built. Report only.)

WHAT IT DOES. backtest_cuts.py cut 12's trend, unchanged: for each complete trade, the larger absolute club net (in a
two-team trade the two nets are equal and opposite, so this is the size of the gap); regressed on the trade's season
(starting year; July 1 starts a season), 2017-18 to 2025-26. Run on the trade-day grade (net_M) and on the realized value
(out_net_M, WAR). Each slope with a robust standard error and p-value (one row a trade, so this is clustering by trade),
beside cut 12's resampled 95% interval (2,000 resamples of trades).

EXPECTED, BY CONSTRUCTION. Recent trades' realized values are partly forecast (their unplayed seasons are the models'
forecast) and have had fewer seasons to spread out, so the realized trend leans downward whatever the market did.

GUARD: the trade-day slope reproduces cut 12's -0.019 $M a season.

INPUTS: OUTPUT_DIR/_extended_run/backtest_cuts_all_sides.csv. OUTPUTS: OUTPUT_DIR/trend_both_log.txt, trend_both.csv
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "trend_both.py v1.0 (2026-11-18)"
N_BOOT, SEED = 2000, 20261118
LOG, OUT = [], []


def log(s=""):
    print(s)
    LOG.append(s)


def main():
    log(SCRIPT_VERSION)
    m = pd.read_csv(EXT / "backtest_cuts_all_sides.csv")
    m["date"] = pd.to_datetime(m["trade_date"])
    m["season"] = m["date"].map(lambda d: d.year if d.month >= 7 else d.year - 1)     # cut 12's season
    rng = np.random.default_rng(SEED)
    log(f"  {m['trade_id'].nunique()} trades, seasons {m['season'].min()} to {m['season'].max()}")
    for lab, col in (("trade-day grade", "net_M"), ("realized value, WAR", "out_net_M")):
        tr = m.groupby("trade_id").agg(size=(col, lambda x: x.abs().max()), season=("season", "first"))
        fit = sm.OLS(tr["size"], sm.add_constant(tr["season"].astype(float))).fit(cov_type="HC1")
        b, se, p = float(fit.params["season"]), float(fit.bse["season"]), float(fit.pvalues["season"])
        ids = tr.index.values
        bs = np.array([np.polyfit(*tr.loc[ids[rng.integers(0, len(ids), len(ids))]][["season", "size"]].T.values, 1)[0]
                       for _ in range(N_BOOT)])
        if col == "net_M":
            assert abs(b + 0.019) < 0.0005, b                                       # GUARD: cut 12
        means = tr.groupby("season")["size"].mean().round(2).to_dict()
        log(f"  {lab:<22} slope {b:+.3f} $M a season (se {se:.3f}) p = {p:.3f}; resampled [{np.percentile(bs, 2.5):+.3f}, "
            f"{np.percentile(bs, 97.5):+.3f}]; mean size by season {means}")
        OUT.append({"value": lab, "n_trades": len(tr), "slope": b, "se": se, "p": p,
                    "lo": np.percentile(bs, 2.5), "hi": np.percentile(bs, 97.5)})
    log("  check: the trade-day slope reproduces backtest_cuts.py cut 12's -0.019 (PASS)")
    pd.DataFrame(OUT).to_csv(OUTPUT_DIR / "trend_both.csv", index=False)
    (OUTPUT_DIR / "trend_both_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
