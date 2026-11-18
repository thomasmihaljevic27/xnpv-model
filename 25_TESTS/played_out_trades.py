"""
played_out_trades.py - the back-test's headline on trades whose result is fully played out (Thomas, 2026-11-18, a comment
on "Trade Back-test, What We Found and How": "I still think it may be best to not include any of the models own valuations
when doing this comparison ... but I want to know how much it shrinks the sample size". Report only.)

WHAT IT DOES. A trade is FULLY PLAYED OUT when no asset in it has any value left to the models at 2026-27: every asset's
`revalued_M` (the part of its outcome that is the models valuing it again at the 2026-27 page) is zero to $1e-6. Its result
is then made only of seasons already played. On those trades, and beside them on all complete trades, it computes the
back-test's own Test A figures exactly as backtest.py does (one favoured club a trade: the side with the largest trade-day
grade, if above zero; the slope through zero of each side's result on its grade; the correlation and its square) with 95%
intervals from 2,000 resamples of trades (seed 20261118).

BAKED-IN: complete trades only (backtest.py's `complete`); the declared window ends 2022-03-28; a side whose result is
exactly zero (to $1e-9) does not count as "ahead". The tie rule is shown both ways because played-out trades hold many
minor-league swaps in which no asset ever played.

INPUTS: OUTPUT_DIR/_extended_run/backtest_assets.csv, backtest_sides.csv (backtest.py v1.7 on the extended ledger)
OUTPUTS: OUTPUT_DIR/played_out_trades_log.txt
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
EXT = OUTPUT_DIR / "_extended_run"
SCRIPT_VERSION = "played_out_trades.py v1.0 (2026-11-18)"
DECLARED_END = "2022-03-28"
N_BOOT, SEED = 2000, 20261118
LOG = []


def log(s=""):
    print(s)
    LOG.append(s)


def stats(d):
    """Test A as backtest.py computes it, on the sides in d (complete trades)."""
    x, y = d["net_M"].values, d["out_net_M"].values
    slope = (x * y).sum() / (x * x).sum()
    r = np.corrcoef(x, y)[0, 1]
    fav = d.loc[d.groupby("trade_id")["net_M"].idxmax()]
    fav = fav[fav["net_M"] > 0]
    ahead = (fav["out_net_M"] > 0).mean()
    nz = fav[fav["out_net_M"].abs() > 1e-9]
    return np.array([ahead, (nz["out_net_M"] > 0).mean(), slope, r, r * r, len(fav) - len(nz)])


def main():
    log(SCRIPT_VERSION)
    a = pd.read_csv(EXT / "backtest_assets.csv")
    s = pd.read_csv(EXT / "backtest_sides.csv")
    s = s[s["complete"]].copy()
    pending = a.assign(p=a["revalued_M"].abs() > 1e-6).groupby("trade_id")["p"].any()
    s["played_out"] = ~s["trade_id"].map(pending).fillna(True)
    rng = np.random.default_rng(SEED)
    labels = ["favoured club ahead", "the same, sides with a result of exactly zero set aside", "slope of result on grade",
              "correlation", "R-squared", "favoured sides with a result of exactly zero"]
    for scope, msk in (("declared window (2017-07-01 to 2022-03-28)", s["trade_date"] <= DECLARED_END),
                       ("after 2022-03-28", s["trade_date"] > DECLARED_END), ("all trades", s["trade_date"].notna())):
        for sub, m2 in (("all complete trades", s["trade_id"].notna()), ("fully played out", s["played_out"])):
            d = s[msk & m2].reset_index(drop=True)
            ids = d["trade_id"].unique()
            by = {t: g for t, g in d.groupby("trade_id")}
            est = stats(d)
            boots = np.array([stats(pd.concat([by[t] for t in ids[rng.integers(0, len(ids), len(ids))]]).reset_index(drop=True))
                              for _ in range(N_BOOT)])
            lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
            pa = a[a["trade_id"].isin(ids)]
            log(f"\n{scope}, {sub}: {len(ids)} trades, {len(d)} club sides; assets: "
                + ", ".join(f"{k} {v}" for k, v in pa["asset_type"].value_counts().items())
                + f"; median |grade| {d['net_M'].abs().median():.3f}")
            for i, lab in enumerate(labels[:5]):
                log(f"  {lab:<58}{est[i]:.3f} [{lo[i]:.3f}, {hi[i]:.3f}]")
            log(f"  {labels[5]:<58}{int(est[5])}")
    (OUTPUT_DIR / "played_out_trades_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
