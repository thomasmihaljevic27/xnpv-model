"""
output_compare.py -- what moved between two runs of the chain: contract values, the star value, traded picks.

USE (Thomas, 2026-10-14): each step of the age-and-arbitration build is compared with the run before it,
so each change is scored on its own. Copy 30_OUTPUT's files to a folder before a change, run the chain,
then:   python 25_TESTS/output_compare.py <folder with the earlier files> [--label "what changed"]

COMPARED (each only if both runs have it)
  contract_npv_panel.csv   by (contract_id, valuation_season): npv_total (the headline), npv_total_qo
                           (the qualifying-offer chain beside), npv_total_term_free; rows present in one
                           run only are counted, not compared. Money compared at a declared precision
                           of $0.01 (CLAUDE.md: never exact equality on money).
  goalie_value_spine_v2.csv value_dollars by (contract_id, season_start).
  pick_curve_scales.csv    each scale kind.
  traded_pick_values.csv   total value and by pick.
Reports counts, never "all"/"none" without the count.
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "output_compare.py v1.0 (2026-10-14)"
load_dotenv()
NOW = Path(os.environ["OUTPUT_DIR"])
CENT = 0.01

ap = argparse.ArgumentParser()
ap.add_argument("before")
ap.add_argument("--label", default="")
a = ap.parse_args()
BEFORE = Path(a.before)
print(SCRIPT_VERSION, "|", a.label)
print(f"  before: {BEFORE}\n  after:  {NOW}")


def both(name):
    f0, f1 = BEFORE / name, NOW / name
    if not (f0.exists() and f1.exists()):
        print(f"\n{name}: not in both runs, skipped")
        return None, None
    return pd.read_csv(f0, low_memory=False), pd.read_csv(f1, low_memory=False)


# ---- contract values ---------------------------------------------------------------------------
p0, p1 = both("contract_npv_panel.csv")
if p0 is not None:
    key = ["contract_id", "valuation_season"]
    m = p0.merge(p1, on=key, how="outer", suffixes=("_0", "_1"), indicator=True)
    print(f"\nCONTRACT VALUES (contract_npv_panel.csv): {len(p0):,} before, {len(p1):,} after; "
          f"in one run only: {int((m['_merge'] != 'both').sum())}")
    m = m[m["_merge"] == "both"]
    for col in ("npv_total", "npv_total_qo", "npv_total_term_free"):
        if f"{col}_0" not in m or f"{col}_1" not in m:
            continue
        x0, x1 = m[f"{col}_0"], m[f"{col}_1"]
        priced = x0.notna() & x1.notna()
        d = (x1 - x0)[priced]
        moved = d.abs() >= CENT
        print(f"  {col}: {int(priced.sum()):,} priced in both; moved by a cent or more: {int(moved.sum()):,} "
              f"(up {int((d >= CENT).sum()):,}, down {int((d <= -CENT).sum()):,}); priced in one only: "
              f"{int((x0.notna() != x1.notna()).sum())}")
        if moved.any():
            dm = d[moved] / 1e6
            print(f"    among those that moved: median {dm.median():+.2f}M, largest fall {dm.min():+.2f}M, "
                  f"largest rise {dm.max():+.2f}M; total {d.sum() / 1e6:+,.1f}M")
            by = m[priced].assign(d=d).groupby("valuation_season")["d"].agg(
                moved=lambda s: int((s.abs() >= CENT).sum()), total_M=lambda s: s.sum() / 1e6)
            print("    by page: " + "; ".join(f"{int(k)} {int(r.moved)} ({r.total_M:+.1f}M)" for k, r in by.iterrows()))
        if col == "npv_total" and moved.any():
            name = "full_name_1" if "full_name_1" in m else ("full_name" if "full_name" in m else None)
            t = m[priced].assign(d=d / 1e6).reindex(d.abs().sort_values(ascending=False).index[:10])
            print("    ten largest moves:")
            for r in t.itertuples():
                nm = getattr(r, name) if name else ""
                print(f"      {nm!s:<24} page {int(r.valuation_season)}: {getattr(r, 'npv_total_0') / 1e6:7.2f} -> "
                      f"{getattr(r, 'npv_total_1') / 1e6:7.2f} ({r.d:+.2f}M)")

# ---- goalie spine -------------------------------------------------------------------------------
g0, g1 = both("goalie_value_spine_v2.csv")
if g0 is not None:
    key = ["contract_id", "season_start"]
    m = g0.merge(g1, on=key, suffixes=("_0", "_1"))
    x0, x1 = pd.to_numeric(m["value_dollars_0"], errors="coerce"), pd.to_numeric(m["value_dollars_1"], errors="coerce")
    pr = x0.notna() & x1.notna()
    print(f"\nGOALIE SPINE: rows {len(g0):,} / {len(g1):,}; matched {len(m):,}; priced in both {int(pr.sum()):,}; "
          f"value moved by a cent or more: {int(((x1 - x0)[pr].abs() >= CENT).sum())}; "
          f"priced in one only: {int((x0.notna() != x1.notna()).sum())}")

# ---- pick curve ---------------------------------------------------------------------------------
s0, s1 = both("pick_curve_scales.csv")
if s0 is not None:
    m = s0.merge(s1, on="scale_kind", how="outer", suffixes=("_0", "_1"))
    print("\nSTAR VALUE ($M) by scale kind: before -> after")
    for r in m.itertuples():
        print(f"  {r.scale_kind:<34} {r.scale_M_0 if pd.notna(r.scale_M_0) else float('nan'):8.2f} -> "
              f"{r.scale_M_1 if pd.notna(r.scale_M_1) else float('nan'):8.2f}")
t0_, t1_ = both("traded_pick_values.csv")
if t0_ is not None:
    v0, v1 = t0_["value_M"].sum(), t1_["value_M"].sum()
    print(f"\nTRADED PICKS: {len(t0_)} / {len(t1_)} picks; total ${v0:,.1f}M -> ${v1:,.1f}M ({v1 - v0:+,.1f}M)")
