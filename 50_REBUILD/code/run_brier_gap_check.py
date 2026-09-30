"""run_brier_gap_check.py -- why xNPV 0's chance-of-playing score differs by machine.

EXPERIMENTAL (50_REBUILD). Diagnostic only: no model is fitted beyond xNPV 0's
own tables, nothing is adopted, no production file is edited. Development pages
only. It does not need the contract export.

THE GAP (Contract_Status_Test.md, 2026-09-30)
    xNPV 0 (production_adapter.ProductionChain) scored a Brier of 0.249 on the
    laptop against 0.192 in the cloud, on 35,878 answerable forecasts in both
    runs. Two inputs differ between the machines:
      A. the harness table's birthdates: the laptop reads the merged file
         (50_REBUILD/output/birthdates.csv, PuckPedia first, then Elite
         Prospects); the cloud rebuilds production's own join;
      B. production's age table, 30_OUTPUT/WAR_with_age.csv, from which
         xNPV 0's exit-risk tables are fitted (the laptop's was rebuilt
         2026-09-28 with the Elite Prospects ages restored).
    Checked in the cloud and ruled out: the separation fix (exit_hazard v1.3).
    Forcing it on windows the ordinary fit handles moves no cell by more than
    0.007, and the cloud's 2015 page already takes it.

WHAT THIS PRINTS, for each harness table this machine can build
    * the row set and target fingerprints (hashes), so two machines' runs can
      be compared row for row;
    * how many answerable rows have an age, and the age mix;
    * Brier, mean predicted and observed chance of playing, by seasons ahead
      and by page;
    * each page's exit-risk table: exit rate in its window, and three cells.
    Arm 1 always rebuilds production's join (the cloud's table). Arm 2 is the
    merged file, where this machine has one. On the laptop, arm 1 against arm 2
    isolates A on one machine. Arm 1 on the laptop against arm 1 in the cloud
    (recorded in the session log, 2026-09-30) isolates B.

HOW TO RUN (Windows PowerShell, from the repo root, after syncing):
    python 50_REBUILD\\code\\run_brier_gap_check.py
Output: 50_REBUILD/output/brier_gap_run_log.txt, the file to send back.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
from player_season_table import build as build_table, birthdate_source
import production_adapter as PA
import run_aging_choices_test as RAC

SCRIPT_VERSION = "1.0"
HORIZONS = (0, 1, 2, 3, 4, 5)
KEYS = ["career_key", "page", "h"]


def _hash(values) -> str:
    return hashlib.sha1(pd.util.hash_pandas_object(pd.Series(values), index=False)
                        .to_numpy().tobytes()).hexdigest()[:12]


def _file_hash(p: Path) -> str:
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()[:12]


def production_join():
    """Production's own join, even where a merged file exists: RAC._birthdates
    with the merged file hidden from it."""
    real = RAC.birthdate_source
    RAC.birthdate_source = lambda: (None, "hidden for this arm")
    try:
        return RAC._birthdates()
    finally:
        RAC.birthdate_source = real


def one_arm(label: str, path, how: str) -> None:
    C.log(f"ARM {label}: birthdates {how}")
    C.log(f"  file {Path(path).resolve()} sha1 {_file_hash(path)}")
    table = build_table(birthdate_csv=path, verbose=False)
    model = PA.ProductionChain()
    PA.ProductionChain._cache.clear()           # each arm fits its own tables
    d = H.Harness(table).run(model, pages=C.DEV_PAGES, horizons=HORIZONS)
    d = d.sort_values(KEYS).reset_index(drop=True)
    a = d[d["outside_production"].eq(0)].copy()
    a["b"] = (a["p_play"] - a["played"].astype(float)) ** 2
    C.log(f"  forecasts {len(d)}, answerable {len(a)}, players {a['career_key'].nunique()}")
    C.log(f"  fingerprints: rows {_hash(a[KEYS].astype(str).agg('|'.join, axis=1))}, "
          f"played {_hash(a['played'].astype(int))}, act_war {_hash(a['act_war'].round(9))}, "
          f"age {_hash(a['age'].round(6))}")
    C.log(f"  answerable rows with an age: {a['age'].notna().mean():.4f}; age mean "
          f"{a['age'].mean():.3f}; age groups: " + ", ".join(
              f"{k} {v:.3f}" for k, v in pd.cut(a["age"], [0, 22, 26, 30, 34, 60],
                                                labels=["<=22", "23-26", "27-30", "31-34", "35+"])
              .value_counts(normalize=True, dropna=False).sort_index().items()))
    C.log(f"  BRIER {a['b'].mean():.4f}")
    g = a.groupby("h").agg(brier=("b", "mean"), pred=("p_play", "mean"), obs=("played", "mean"))
    C.log("  by seasons ahead:  " + " | ".join(
        f"h{h} {r.brier:.3f} ({r.pred:.3f}/{r.obs:.3f})" for h, r in g.iterrows()))
    g = a.groupby("page")["b"].mean()
    C.log("  by page:           " + " | ".join(f"{p} {v:.3f}" for p, v in g.items()))
    C.log("  exit-risk tables (mean of the four quality marginals; cells star 27-30, regular 31-34, fringe 35+):")
    for t0 in C.DEV_PAGES:
        tab = PA.ProductionChain._cache["singleton"][1]["tables"].get(t0, {})
        cells = [tab.get(k, float("nan")) for k in
                 (("star", "27-30"), ("regular", "31-34"), ("fringe", "35+"))]
        allm = np.nanmean([v for (b, g_), v in tab.items() if g_ == "ALL"]) if tab else float("nan")
        C.log(f"    {t0}: mean of bucket marginals {allm:.4f}; cells " +
              ", ".join(f"{v:.4f}" for v in cells))
    C.log("")


def main() -> None:
    C.banner("run_brier_gap_check.py", SCRIPT_VERSION)
    SFP = PA._production()[0]
    age = Path(SFP.F_WAR_AGE).resolve()
    w = pd.read_csv(age, low_memory=False)
    C.log(f"  production age table: {age}, sha1 {_file_hash(age)}, {len(w)} rows, "
          f"birthdate present on {w['birthdate'].notna().mean():.4f}")
    C.log("")
    p1, h1 = production_join()
    one_arm("1 (production's join, the cloud's table)", p1, h1)
    p2, h2 = birthdate_source()
    if p2 is not None and Path(p2).name == "birthdates.csv":
        one_arm("2 (merged file, the laptop's table)", p2, h2)
    else:
        C.log(f"ARM 2 not run: this machine has no merged birthdate file ({h2})")
    C.write_log("brier_gap_run_log.txt")


if __name__ == "__main__":
    main()
