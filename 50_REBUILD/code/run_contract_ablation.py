"""run_contract_ablation.py -- does contract data help the participation model?

EXPERIMENTAL (50_REBUILD). Re-measures the Phase 2 contract ablation after a
defect in the shared participation model was found and fixed. Development
pages only. Nothing adopted.

WHY IT IS BEING MEASURED A FOURTH TIME
    The recorded answer (Phase2_Participation.md) is that contract data makes
    the participation forecast WORSE, by 0.26% to 0.91% of mean absolute error
    from one to five seasons out -- and the standing leader was chosen, in
    part, on that: it fits participation without contract data.

    That comparison was taken with a defect in the with-contract model. When
    every player the contract export knows about is also under contract for
    the season, the two contract columns are exact mirror images and the
    logistic design loses a rank. The regularised fit then reported
    convergence with an arbitrary split between the two columns. That split
    reproduces the training rows exactly and extrapolates to nonsense on the
    page itself, where the two columns no longer mirror each other: on the
    2019 page five seasons out it predicted 0.556 participation against an
    observed 0.406. It happened on fifteen skater fits, 2015-2019 pages,
    horizons one to five -- exactly where the contract feature was judged
    worst.

    `participation_model` now drops redundant columns in a fixed order until
    the design has full rank. This runner scores the with-contract model
    BEFORE and AFTER that fix and the without-contract model once, on the same
    harness and the same rows, so the effect of the fix and the effect of the
    contract data are both measured here rather than quoted.

THE CONVENTION, STATED ONCE
    "Effect of adding contract data" is the with-contract model's mean
    absolute error in season WAR minus the without-contract model's, as a
    percentage of the latter. POSITIVE means contract data makes the forecast
    worse. The interval resamples whole careers.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import participation_model as PM
from ability_forecast import A1AgingParticipation, A1AgingParticipationNoContracts
from player_season_table import build as build_table

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)


def effect(with_c: pd.DataFrame, without_c: pd.DataFrame, n: int = 1000,
           seed: int = 20260922) -> pd.DataFrame:
    """Per horizon: % change in mean absolute WAR error from adding contract
    data, with a 95% interval from resampling careers. Paired on the forecast."""
    keys = ["career_key", "page", "h"]
    j = (with_c[keys + ["e_war"]]
         .merge(without_c[keys + ["e_war"]], on=keys, suffixes=("_w", "_o"),
                validate="one_to_one"))
    rng = np.random.default_rng(seed)
    out = []
    for h, g in j.groupby("h"):
        base = g["e_war_o"].abs().mean()
        pct = 100.0 * (g["e_war_w"].abs().mean() - base) / base
        groups = {k: v for k, v in g.groupby("career_key")}
        ks = list(groups)
        boot = []
        for _ in range(n):
            s = pd.concat([groups[k] for k in rng.choice(ks, len(ks), replace=True)])
            b = s["e_war_o"].abs().mean()
            boot.append(100.0 * (s["e_war_w"].abs().mean() - b) / b)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        out.append({"h": int(h), "pct": pct, "lo": lo, "hi": hi,
                    "brier_w": None, "n": len(g)})
    return pd.DataFrame(out)


def main() -> None:
    C.banner("run_contract_ablation.py", SCRIPT_VERSION)
    bd = C.OUT_DIR / "birthdates.csv"
    table = build_table(birthdate_csv=bd, verbose=False)
    har = H.Harness(table)

    without = har.run(A1AgingParticipationNoContracts(), horizons=HORIZONS)
    after = har.run(A1AgingParticipation(), horizons=HORIZONS)

    # THE OLD BEHAVIOUR, reproduced in the same run: the rank check switched
    # off, so a singular design reaches the optimiser as it used to.
    real = PM._full_rank
    PM._full_rank = lambda d, use: (list(use), [])
    try:
        before = har.run(A1AgingParticipation(), horizons=HORIZONS)
    finally:
        PM._full_rank = real

    C.log("EFFECT OF ADDING CONTRACT DATA to the participation model, % of mean")
    C.log("absolute error in season WAR. POSITIVE = contract data makes it worse.")
    C.log("95% interval from resampling careers.")
    C.log("")
    C.log(f"    {'h':<4}{'before the fix':>26}{'after the fix':>26}"
          f"{'Brier w/o':>11}{'Brier with':>12}")
    eb, ea = effect(before, without), effect(after, without)
    for h in HORIZONS:
        b = eb[eb["h"] == h].iloc[0]
        a = ea[ea["h"] == h].iloc[0]
        bw = without.loc[without["h"] == h, "brier"].mean()
        ba = after.loc[after["h"] == h, "brier"].mean()
        C.log(f"    {h:<4}{b['pct']:>+8.2f}% [{b['lo']:+.2f}, {b['hi']:+.2f}]"
              f"{a['pct']:>+8.2f}% [{a['lo']:+.2f}, {a['hi']:+.2f}]"
              f"{bw:>11.4f}{ba:>12.4f}")
    C.log("")
    C.log("  Mean participation predicted against observed, by arm:")
    for name, d in (("without contracts", without), ("with, before the fix", before),
                    ("with, after the fix", after)):
        C.log(f"    {name:<24} predicted {d['p_play'].mean():.3f}   observed "
              f"{d['played'].mean():.3f}   Brier {d['brier'].mean():.4f}")
    C.log("")
    out = pd.concat([eb.assign(arm="before"), ea.assign(arm="after")])
    out.to_csv(C.out_path("contract_ablation.csv"), index=False)
    C.write_log("contract_ablation_run_log.txt")


if __name__ == "__main__":
    main()
