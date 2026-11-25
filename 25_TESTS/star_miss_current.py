"""
star_miss_current.py v1.0 (2026-11-25) - report only; writes OUTPUT_DIR/star_miss_current_log.txt.

WHY (Thomas, 2026-11-25: "Re-measure them first"). The final paper states as a limitation that the forecast under-forecasts
the best players, a figure last measured in September on an earlier forecast (40_DOCS/model_evidence/Star_Miss_Checks.md).
A document may not describe an earlier model, so the figure is measured again on the forecast as it runs.

WHAT. xNPV 1 (skater_forecast.XNPV1) scored by the live forecast harness (forecast_harness.Harness) on the development
pages (forecast_config.DEV_PAGES), zero to five seasons ahead, on ContractForecaster's season table. The star tier is the
harness's own label, a 50/30/20 trailing WAR total of 3 or more (forecast_harness.subjects_at). The miss is forecasted
season WAR less delivered season WAR (the harness's e_war: zero delivered for a season not played), so a negative miss is
an under-forecast. Reported for one to five seasons ahead: the tier's mean miss, with an interval from 2,000 resamples of
players (seed 20261125); each player's total; the tier without the five players the September check named.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C
import forecast_harness as H
import skater_forecast as SF

SCRIPT_VERSION = "star_miss_current.py v1.0 (2026-11-25)"
OUT = Path(os.environ.get("OUTPUT_DIR", Path(__file__).resolve().parents[1] / "30_OUTPUT"))
FIVE = ["connor mcdavid", "leon draisaitl", "nathan mackinnon", "auston matthews", "sidney crosby"]
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def boot_mean(d, rng, n=2000):
    ids = d["career_key"].unique()
    g = d.groupby("career_key")["e_war"].agg(["sum", "count"])
    out = []
    for _ in range(n):
        s = g.loc[rng.choice(ids, size=len(ids), replace=True)]
        out.append(s["sum"].sum() / s["count"].sum())
    return np.percentile(out, [2.5, 97.5])


def main():
    log(SCRIPT_VERSION)
    fc = SF.ContractForecaster()
    d = H.Harness(fc.table).run(SF.XNPV1(), pages=C.DEV_PAGES, horizons=(0, 1, 2, 3, 4, 5))
    if "e_war" not in d.columns:
        d = H._score_rows(d)
    log(f"  harness rows {len(d):,} on pages {min(C.DEV_PAGES)}-{max(C.DEV_PAGES)}; tiers {sorted(d['tier'].dropna().unique())}")
    star = d[(d["tier"] == "3+") & d["h"].between(1, 5)].copy()
    rng = np.random.default_rng(20261125)
    lo, hi = boot_mean(star, rng)
    log(f"\nSTAR TIER (trailing 50/30/20 WAR total 3+), one to five seasons ahead: {len(star):,} forecasts of "
        f"{star['career_key'].nunique()} players")
    log(f"  mean miss (forecast less delivered, season WAR): {star['e_war'].mean():+.3f} [{lo:+.3f}, {hi:+.3f}]")
    by = star.groupby("career_key")["e_war"].agg(total="sum", forecasts="count", mean="mean").sort_values("total")
    log("  the ten largest under-forecasts by player (total over his forecasts):")
    for k, r in by.head(10).iterrows():
        log(f"    {k:<28}{r['total']:>+8.1f}{int(r['forecasts']):>5} forecasts  mean {r['mean']:+.2f}")
    found = [k for k in by.index if any(k.startswith(f) for f in FIVE)]
    rest = star[~star["career_key"].isin(found)]
    lo2, hi2 = boot_mean(rest, rng)
    log(f"\n  without the five named in September ({', '.join(found)}): {len(rest):,} forecasts of "
        f"{rest['career_key'].nunique()} players, mean miss {rest['e_war'].mean():+.3f} [{lo2:+.3f}, {hi2:+.3f}]")
    log("  by seasons ahead, the tier with them | without them:")
    for h in range(1, 6):
        a, b = star[star["h"] == h]["e_war"].mean(), rest[rest["h"] == h]["e_war"].mean()
        log(f"    {h}: {a:+.3f} | {b:+.3f}")
    (OUT / "star_miss_current_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
