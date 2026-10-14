"""
pick_class_overlap_check.py -- does the pick curve contain the outcome of the pick it values?

FLAG (STANDING_FLAGS 2026-10-09, WORK_QUEUE reading-week item 6): the curve's star value is fitted on
the realised careers of the 2007-2017 drafts, and the back-test's trades start in 2017-18, so "a 2017
pick traded then is valued by a curve that contains its own outcome". Asked (Thomas, 2026-10-14): run
the check that refits the curve without the class being valued.

WHAT THIS SCRIPT DOES
  1. Counts the traded picks (traded_pick_values.csv) by the draft they are for. A pick whose draft is
     one of the curve's drafts (2007-2017) carries its own outcome inside the curve. A pick for a draft
     already held at the trade is not valued as a pick (traded_pick_values.py: "draft already held");
     after the draft he is a drafted player (a prospect), not a pick.
  2. Refits the star value eleven times, leaving out one draft each time, with the same regression as
     pick_curve.fit_scale() (surplus on Bacon's star chance, through zero, draft-year indicators that
     sum to zero, robust errors), on the adopted arbitration cost and on the qualifying-offer chain
     beside it. A drafted player from draft Y who is valued from his slot (the prospect model's likely
     starting value) would be priced on the curve without Y; this shows how far that moves him.
  3. Bacon's star chance itself (the shape) was fitted on his own data; his star rates were compared
     with ours on 2007-2015 (pick_star_and_rights_checks.py). Not refitted here.

DECLARED READING (before the run): if no valued traded pick is for a 2007-2017 draft, the flag does
not apply to traded picks and is restated as a prospect-side limitation. The leave-one-draft-out
values are reported, not judged: a change under 5% of the star value is described as small.

INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_scales.csv, traded_pick_values.csv.
Run from the repo root:  python 25_TESTS/pick_class_overlap_check.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_class_overlap_check.py v1.0 (2026-10-14)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
print(SCRIPT_VERSION)
F = {k: OUTPUT_DIR / f"{k}.csv" for k in ("pick_curve_players", "pick_curve_scales", "traded_pick_values")}
for k, p in F.items():
    print(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

d = pd.read_csv(F["pick_curve_players"])
scales = pd.read_csv(F["pick_curve_scales"]).set_index("scale_kind")
v = pd.read_csv(F["traded_pick_values"])
CURVE = sorted(d["draftYear"].unique())


def fit_scale(frame, col):
    """pick_curve.fit_scale(), with the surplus column named: through zero, sum-to-zero year columns."""
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    X = [frame["p_star"].values] + [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]
    m = sm.OLS(frame[col].values / 1e6, np.column_stack(X)).fit(cov_type="HC1")
    return m.params[0], m.bse[0]


# GUARD: the full fits reproduce pick_curve.py's saved star values (else the inputs are stale)
main, _ = fit_scale(d, "surplus")
chain, _ = fit_scale(d, "surplus_qo")
assert abs(main - scales.loc["main", "scale_M"]) < 1e-9, (main, scales.loc["main", "scale_M"])
assert abs(chain - scales.loc["qo_chain", "scale_M"]) < 1e-9
print(f"\nguard: star value reproduces pick_curve.py ({main:.2f} adopted cost; {chain:.2f} qualifying-offer chain); "
      f"{len(d):,} drafted players, drafts {CURVE[0]}-{CURVE[-1]}")

# ---- 1. which drafts the traded picks are for --------------------------------------------------------
print("\n1. TRADED PICKS BY THE DRAFT THEY ARE FOR (trades from "
      f"{v['trade_date'].min()} to {v['trade_date'].max()})")
v["valued"] = v["value_M"].notna()
t = v.groupby("pick_year").agg(picks=("asset_id", "size"), valued=("valued", "sum"))
print(t.to_string())
inside = v[v["valued"] & v["pick_year"].isin(CURVE)]
held = v[~v["valued"]]
print(f"  valued picks for a draft inside the curve ({CURVE[0]}-{CURVE[-1]}): {len(inside)}")
print(f"  not valued (draft already held at the trade): {len(held)}")
print("  reading: " + ("the flag does not apply to traded picks; every valued pick is for a later draft "
                       "than the curve's last" if len(inside) == 0 else "the flag applies to the picks counted above"))

# ---- 2. the star value without each draft ------------------------------------------------------------
print("\n2. STAR VALUE WITH ONE DRAFT LEFT OUT ($M at the 2025-26 cap; robust se)")
rows = []
for y in CURVE:
    rest = d[d["draftYear"] != y]
    a, ase = fit_scale(rest, "surplus")
    q, qse = fit_scale(rest, "surplus_qo")
    rows.append({"draft_left_out": y, "players": int((d["draftYear"] == y).sum()),
                 "star_value": a, "se": ase, "change_pct": 100 * (a / main - 1),
                 "chain_star_value": q, "chain_change_pct": 100 * (q / chain - 1)})
r = pd.DataFrame(rows)
print(f"  all eleven drafts: adopted cost {main:.2f}; qualifying-offer chain {chain:.2f}")
print(r.round(2).to_string(index=False))
big = r[r["change_pct"].abs() >= 5]
print(f"  drafts whose removal moves the adopted star value by 5% or more: {len(big)} of {len(r)}"
      + (" (" + ", ".join(f"{int(x.draft_left_out)} {x.change_pct:+.1f}%" for x in big.itertuples()) + ")"
         if len(big) else ""))
print(f"  range: {r['star_value'].min():.2f} to {r['star_value'].max():.2f} "
      f"({r['change_pct'].min():+.1f}% to {r['change_pct'].max():+.1f}%)")
r.to_csv(OUTPUT_DIR / "pick_class_overlap_check.csv", index=False)
print(f"\nwrote {OUTPUT_DIR / 'pick_class_overlap_check.csv'}")
