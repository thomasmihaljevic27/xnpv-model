"""run_stress_tests.py -- where does the leading player model break?

EXPERIMENTAL (50_REBUILD). Development seasons only; the confirmatory seal is
not touched.

An average is a place for a failure to hide. Every number reported for the
leading model so far has been a mean over 6,124 player-seasons a horizon, and
a model can win that comfortably while being useless on defencemen, or on
players with one season of history, or in 2020. These tests look for the
subgroup where it falls over, and for the calibration and leakage problems
that an error metric cannot see at all.

Six tests:
  1. calibration -- when it says 2 wins, does it get 2 wins?
  2. subgroups -- position, age, experience, availability, history length
  3. per-page stability -- is the advantage every year, or three good years?
  4. full-chain look-ahead -- does deleting the future change the forecast?
  5. edge cases -- negative anchors, thin history, the very old and very young
  6. the 2023 export break -- does the unallocated residual distort anything
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import forecast_harness as H
import information_set as ISET
from player_season_table import build as build_table
from ability_forecast import (A1AgingParticipationImputedNC, A0Production,
                              A2AgingParticipationImputed)

SCRIPT_VERSION = "1.3"
# THE ADOPTED CANDIDATE, which is the hinge-and-evidence variant. The battery
# used to run the earlier leader while the register recorded a different model
# as adopted, so the six-part suite was testing something nobody had chosen.
# The two are within a third of a percent of each other at every horizon, so
# this changes no conclusion; it changes what the suite is evidence ABOUT.
# The adopted skater leader, from the one switch (run_npv_simulation.LEADER),
# not a class named here: a copy pinned by name is how these diagnostics kept
# testing the old leader after it changed on 2026-09-23.
from run_npv_simulation import LEADER  # noqa: E402


def fmt(x, n=3):
    return "n/a" if not np.isfinite(x) else f"{x:.{n}f}"


def main() -> None:
    C.banner("run_stress_tests.py", SCRIPT_VERSION)
    table = build_table(birthdate_csv=C.OUT_DIR / "birthdates.csv", verbose=False)
    h = H.Harness(table)
    s = h.run(LEADER())
    base = h.run(A0Production())
    C.log(f"  leading model scored on {len(s)} rows, {s['career_key'].nunique()} careers")
    C.log("")

    # ---- 1. calibration ---------------------------------------------------
    C.log("TEST 1  CALIBRATION. When the model says a player is worth N wins,")
    C.log("does he deliver N? Rows binned by prediction; perfect calibration")
    C.log("puts predicted and actual in the same column.")
    C.log("")
    q = s[s["h"] <= 2].copy()
    q["bin"] = pd.qcut(q["pred_war"], 10, duplicates="drop")
    g = q.groupby("bin", observed=True).agg(n=("pred_war", "size"),
                                            predicted=("pred_war", "mean"),
                                            actual=("act_war", "mean"))
    g["miss"] = g["predicted"] - g["actual"]
    C.log(f"  {'decile':<8}{'n':>7}{'predicted':>12}{'actual':>10}{'miss':>9}")
    for i, (_, r) in enumerate(g.iterrows(), 1):
        C.log(f"  {i:<8}{int(r['n']):>7}{r['predicted']:>12.3f}{r['actual']:>10.3f}"
              f"{r['miss']:>+9.3f}")
    worst = g["miss"].abs().max()
    C.log(f"  worst decile miss: {worst:.3f} wins")
    C.log("")

    # ---- 2. subgroups -----------------------------------------------------
    # THE COMPARATOR IS THE FLAT BENCHMARK (A0Production), not the live chain:
    # production's trailing anchor carried flat, without its aging path or
    # exit hazard. This label used to say "what the chain does today", and a
    # summary repeated it as "beats production's forecast" (corrected
    # 2026-09-24). The live chain is production_adapter.ProductionChain.
    C.log("TEST 2  SUBGROUPS. The leading model against the FLAT BENCHMARK")
    C.log("(A0Production: production's trailing anchor carried flat, no aging")
    C.log("path, no exit hazard -- NOT the live chain), within each group. A")
    C.log("negative percentage means the rebuild is better. Any group where it")
    C.log("is WORSE is a failure the average hid.")
    C.log("")
    j = s.merge(base, on=["career_key", "page", "h"], suffixes=("", "_b"))
    j["one_season_hist"] = (j["exp_seasons"] == 0).astype(int)

    def grp(col, label, bins=None, names=None):
        d = j.copy()
        key = d[col] if bins is None else pd.cut(d[col], bins, labels=names)
        out = d.groupby(key, observed=True).apply(
            lambda x: pd.Series({
                "n": len(x),
                "rebuilt": x["e_war"].abs().mean(),
                "today": x["e_war_b"].abs().mean()}), include_groups=False)
        out["change"] = 100 * (out["rebuilt"] / out["today"] - 1)
        C.log(f"  by {label}:")
        for k, r in out.iterrows():
            flag = "   <-- WORSE" if r["change"] > 0 else ""
            C.log(f"    {str(k):<14}{int(r['n']):>7}{r['rebuilt']:>9.3f}"
                  f"{r['today']:>9.3f}{r['change']:>+9.1f}%{flag}")
        C.log("")

    grp("pos", "position")
    grp("age_band", "age band")
    grp("exp_band", "experience")
    grp("tier", "trailing level")
    grp("h", "seasons ahead")
    grp("one_season_hist", "history length (1 = debut season only)")

    # ---- 3. per-page stability -------------------------------------------
    C.log("TEST 3  PER-PAGE STABILITY. Is the advantage every season, or a few")
    C.log("good ones? A model that wins on average by winning three years and")
    C.log("losing four is not a better model.")
    C.log("")
    p = j.groupby("page").apply(lambda x: pd.Series({
        "n": len(x), "rebuilt": x["e_war"].abs().mean(),
        "today": x["e_war_b"].abs().mean()}), include_groups=False)
    p["change"] = 100 * (p["rebuilt"] / p["today"] - 1)
    for k, r in p.iterrows():
        C.log(f"    {int(k):<8}{int(r['n']):>7}{r['rebuilt']:>9.3f}{r['today']:>9.3f}"
              f"{r['change']:>+9.1f}%")
    C.log(f"  seasons where the rebuild wins: {int((p['change'] < 0).sum())} of {len(p)}")
    C.log("")

    # ---- 4. full-chain look-ahead ----------------------------------------
    C.log("TEST 4  FULL-CHAIN LOOK-AHEAD. The season table is guarded, but the")
    C.log("guard has never been run on the WHOLE chain with aging, participation")
    C.log("and the survivorship correction in it. Deleting every season at or")
    C.log("after the decision date must leave that date's forecast unchanged.")
    C.log("")
    ok = True
    for page in (2017, 2020):
        iset = ISET.build(table, ISET.decision_date_for_page(page), t0=page)
        subs = H.subjects_at(iset)
        full, trunc = LEADER(), LEADER()
        full.fit(iset.seasons, before=page)
        trunc.fit(table[table["syr"] < page], before=page)
        a = full.predict(iset, subs, [0, 3])
        b = trunc.predict(iset, subs, [0, 3])
        d = (a["rate_82"].to_numpy() - b["rate_82"].to_numpy())
        worst_d = float(np.nanmax(np.abs(d)))
        ok &= worst_d < 1e-9
        C.log(f"    page {page}: largest change from deleting the future "
              f"{worst_d:.2e}  [{'PASS' if worst_d < 1e-9 else 'FAIL'}]")
    C.log(f"  {'PASS -- the whole chain is frozen at the decision date' if ok else 'FAIL'}")
    C.log("")

    # ---- 5. edge cases ---------------------------------------------------
    C.log("TEST 5  EDGE CASES. Small populations where a model tends to do")
    C.log("something stupid rather than something slightly wrong.")
    C.log("")
    for label, mask in [
        ("negative trailing anchor", s["tier"] == "below 0"),
        ("debut-season players", s["exp_seasons"] == 0),
        ("aged 36 and over", s["age"] >= 36),
        ("aged 20 and under", s["age"] <= 20),
        ("played under 20 games", s["act_gp"].between(1, 19)),
    ]:
        x = s[mask]
        if not len(x):
            continue
        C.log(f"    {label:<28}{len(x):>7}  mae {fmt(x['e_war'].abs().mean())}"
              f"  bias {fmt(x['e_war'].mean()):>7}"
              f"  worst {fmt(x['e_war'].abs().max(), 2):>6}")
    C.log("")

    # ---- 6. the export break ---------------------------------------------
    C.log("TEST 6  THE 2023-24 EXPORT BREAK. The six WAR components stop summing")
    C.log("to the total from 2023-24, and the rebuild carries the residual as a")
    C.log("seventh component. If that were distorting anything, seasons on either")
    C.log("side of the break would score differently.")
    C.log("")
    for label, mask in [("outcome seasons before 2023", s["season"] < 2023),
                        ("outcome seasons 2023 on", s["season"] >= 2023)]:
        x = s[mask]
        C.log(f"    {label:<30}{len(x):>7}  mae {fmt(x['e_war'].abs().mean())}"
              f"  bias {fmt(x['e_war'].mean()):>7}")
    C.log("")
    C.write_log("stress_tests_run_log.txt")


if __name__ == "__main__":
    main()
