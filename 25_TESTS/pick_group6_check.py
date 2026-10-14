"""
pick_group6_check.py -- does CBA Group 6 change the star value?

QUESTION (Thomas, 2026-10-14): "cba group 6 rule: does this really affect anything?"

CBA 2013 Section 10.1(c): a player aged 25 or older with three or more professional seasons, whose contract has
expired, and who has played under 80 NHL games (goalies under 28), becomes an unrestricted free agent. pick_curve.py
ends club control under Group 3 only (27 by June 30, or seven Accrued Seasons).

WHAT THIS SCRIPT DOES
  Takes the bound draft_window_count.py already computes (end_with_g6_bound: Group 6 applied at 25 to every player
  under the games ceiling by then, assuming each has three professional seasons, which overstates it, because the
  data holds no minor-league games), drops each drafted player's priced seasons after that end
  (pick_curve_seasons.csv, the adopted arbitration cost), keeps lapsed-rights picks at zero, and refits the star
  value with pick_curve's regression (through zero, sum-to-zero draft-year columns, robust errors).
  Truncating a window changes no earlier season's cost: each season's cost depends only on the seasons before it.

DECLARED READING (before the run): the bound is the most Group 6 could move the star value. Under 2% is "no
material effect"; above it, Group 6 is put to Thomas to build properly.

INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_seasons.csv, pick_curve_scales.csv, draft_window_count.csv.
Run from the repo root:  python 25_TESTS/pick_group6_check.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_group6_check.py v1.0 (2026-10-14)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
print(SCRIPT_VERSION)
F = {k: OUTPUT_DIR / f"{k}.csv" for k in ("pick_curve_players", "pick_curve_seasons", "pick_curve_scales",
                                          "draft_window_count")}
for k, p in F.items():
    print(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

d = pd.read_csv(F["pick_curve_players"])
se = pd.read_csv(F["pick_curve_seasons"])
main = float(pd.read_csv(F["pick_curve_scales"]).set_index("scale_kind").loc["main", "scale_M"])
w = pd.read_csv(F["draft_window_count"])[["draftYear", "overall", "end_g3", "end_with_g6_bound"]] \
    .rename(columns={"overall": "pick"})


def fit_scale(frame, col):
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    X = [frame["p_star"].values] + [(yrs == c).astype(float) - (yrs == cl[-1]).astype(float) for c in cl[:-1]]
    m = sm.OLS(frame[col].values / 1e6, np.column_stack(X)).fit(cov_type="HC1")
    return m.params[0], m.bse[0]


# GUARD: seasons add up to each pick's surplus, and the full fit reproduces pick_curve.py
tot = se.groupby(["draftYear", "pick"])["surplus_2025_cap"].sum()
chk = d.set_index(["draftYear", "pick"])["surplus_before_rights"]
assert (tot.reindex(chk.index).fillna(0.0) - chk).abs().max() < 1.0
b0, _ = fit_scale(d, "surplus")
assert abs(b0 - main) < 1e-9
print(f"\nguard: seasons add up to each pick; star value reproduces {b0:.2f}")

dd = d.merge(w, on=["draftYear", "pick"], how="left")
assert (dd["window_end"] == dd["end_g3"]).fillna(True).all()
g6 = dd.set_index(["draftYear", "pick"])["end_with_g6_bound"]
se["g6_end"] = [g6.get((a, b), np.nan) for a, b in zip(se["draftYear"], se["pick"])]
keep = se[se["g6_end"].isna() | (se["season"] <= se["g6_end"] - 1)]
dropped = se.drop(keep.index)
tot6 = keep.groupby(["draftYear", "pick"])["surplus_2025_cap"].sum()
dd["surplus_g6"] = tot6.reindex(pd.MultiIndex.from_frame(dd[["draftYear", "pick"]])).fillna(0.0).values
dd.loc[dd["surplus"] == 0.0, "surplus_g6"] = 0.0            # lapsed rights stay zero (and players with none)

played_cut = dropped[dropped["gp"] > 0]
pk = played_cut.groupby(["draftYear", "pick"]).size()
print(f"\nseasons in the windows: {len(se):,}; after the Group 6 bound: {len(keep):,}")
print(f"  NHL seasons dropped: {len(played_cut):,}, from {len(pk):,} drafted players "
      f"(games in them: {int(played_cut['gp'].sum()):,})")
print(f"  surplus dropped: ${dropped['surplus_2025_cap'].sum() / 1e6:,.1f}M of "
      f"${se['surplus_2025_cap'].sum() / 1e6:,.1f}M (2025-26 cap, before lapsed rights)")
changed = dd[(dd["surplus_g6"] - dd["surplus"]).abs() > 1.0]
print(f"  picks whose surplus changes: {len(changed)}; "
      f"largest change ${(changed['surplus_g6'] - changed['surplus']).abs().max() / 1e6:,.2f}M"
      if len(changed) else "  picks whose surplus changes: 0")
b6, s6 = fit_scale(dd, "surplus_g6")
print(f"\nSTAR VALUE ($M): Group 3 only {b0:.2f}; with the Group 6 bound {b6:.2f} (se {s6:.2f}); "
      f"change {100 * (b6 / b0 - 1):+.2f}%")
print("  reading: " + ("no material effect (under 2%)" if abs(b6 / b0 - 1) < 0.02
                       else "material: put to Thomas to build Group 6 properly"))
