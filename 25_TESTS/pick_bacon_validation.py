"""
pick_bacon_validation.py -- does our own draft data back up Bacon's pick curve?

WHY (Thomas, 2026-10-09)
-------------------------------------------------------------------
The pick curve is priced on Bacon's NHL-player and star probabilities by
slot: surplus = a + b x P(NHL player) + d x P(star), with draft-year
indicators, read at the average draft year (pick_curve_shape_test.py's
"bacon" shape). Thomas: "maybe this regression can be used to validate that
his approximation is backed up." REPORT ONLY: no rule decides anything here.

TWO CHECKS
  1. Does the slot say anything Bacon's probabilities do not? Add log(pick)
     to the Bacon regression. If its coefficient is near zero and adding it
     does not lower the held-out miss, our data finds no slot information
     his probabilities leave out.
  2. Do our own best slot curves (from the shape test: the bendable curve
     and log + log-squared, fitted on slot alone) give the same dollars per
     pick as the curve on his probabilities?

CAVEAT (recorded 2026-10-09): his probabilities are fitted on largely the
same drafts as ours, so agreement is not independent confirmation. It shows
his shape and ours agree on this sample; it cannot show he is right where
both could share an error.

INPUTS: OUTPUT_DIR/pick_first_look_players.csv (v1.1), OUTPUT_DIR/
pick_curve_shape_curves.csv (pick_curve_shape_test.py v1.0), SOURCE_DIR/
draft_slot_baseline.csv.

Run from the repo root:  python 25_TESTS/pick_bacon_validation.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_bacon_validation.py v1.0 (2026-10-09)"
print(SCRIPT_VERSION)
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
F = {"players": OUT / "pick_first_look_players.csv", "curves": OUT / "pick_curve_shape_curves.csv",
     "bacon": SRC / "draft_slot_baseline.csv", "fl_log": OUT / "pick_first_look_log.txt"}
for k, p in F.items():
    print(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
assert F["fl_log"].read_text(encoding="utf-8").startswith("pick_regression_first_look.py v1.1")

d = pd.read_csv(F["players"]).merge(pd.read_csv(F["bacon"])[["draft_pick", "p_nhler", "p_star"]],
                                     left_on="pick", right_on="draft_pick", validate="many_to_one")
d["y"], d["log_pick"], d["cls"] = d["surplus"] / 1e6, np.log(d["pick"]), d["draftYear"].astype(str)
YR = " + C(cls, Sum)"

# ---- check 1: does log(pick) add anything? -------------------------------------
base = smf.ols("y ~ p_nhler + p_star" + YR, data=d).fit(cov_type="HC1")
both = smf.ols("y ~ p_nhler + p_star + log_pick" + YR, data=d).fit(cov_type="HC1")
print(f"\nCHECK 1 (all {len(d):,} skater picks, $M)")
for nm, m in (("Bacon only", base), ("Bacon + log(pick)", both)):
    terms = ", ".join(f"{k} {m.params[k]:+.3f} (se {m.bse[k]:.3f})" for k in ("p_nhler", "p_star", "log_pick")
                      if k in m.params)
    print(f"  {nm:18s} {terms}; R2 {m.rsquared:.4f}")
print(f"  log(pick) t = {both.tvalues['log_pick']:+.2f}, p = {both.pvalues['log_pick']:.3f}")

# held-out: leave one class out, the same scoring as the shape test
miss = {"Bacon only": [], "Bacon + log(pick)": []}
for c in sorted(d["draftYear"].unique()):
    tr, te = d[d["draftYear"] != c], d[d["draftYear"] == c]
    for nm, f in (("Bacon only", "y ~ p_nhler + p_star"), ("Bacon + log(pick)", "y ~ p_nhler + p_star + log_pick")):
        m = smf.ols(f + YR, data=tr).fit()
        pred = m.params["Intercept"] + sum(m.params[k] * te[k] for k in ("p_nhler", "p_star", "log_pick")
                                           if k in m.params)
        miss[nm].append((te["y"] - pred) ** 2)
for nm, v in miss.items():
    print(f"  held-out RMSE {nm:18s} {np.sqrt(pd.concat(v).mean()):.4f}")

# ---- check 2: our slot-only curves against the curve on his probabilities -------
g = pd.read_csv(F["curves"]).set_index("pick")
at = [1, 2, 3, 5, 10, 15, 20, 32, 64, 100, 150, 200]
raw = d.groupby("pick")["y"].mean()
t = g.loc[at, ["bacon", "bend", "logsq", "log"]].copy()
t["raw mean"] = raw.reindex(at).values
print("\nCHECK 2: fitted $M at an average draft year (shape test, all classes)")
print(t.round(2).to_string())
for k in ("bend", "logsq", "log"):
    gap = (g[k] - g["bacon"]).loc[1:217]
    print(f"  {k:6s} minus Bacon's curve over picks 1-217: largest gap {gap.abs().max():.2f} "
          f"(pick {gap.abs().idxmax()}), mean absolute gap {gap.abs().mean():.3f}; "
          f"picks 1-32 {gap.loc[1:32].abs().mean():.3f}, 33-217 {gap.loc[33:217].abs().mean():.3f}")
