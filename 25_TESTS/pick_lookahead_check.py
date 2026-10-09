"""
pick_lookahead_check.py -- does the pick curve borrow from the future?

WHY (STANDING_FLAGS 2026-10-09; Thomas 2026-10-09: start with this check)
-------------------------------------------------------------------
The adopted curve is surplus = b x Bacon's star chance for the slot (through
zero, draft-year indicators, average year). Two parts of it use information a
club did not have at a trade:
  * the SHAPE: Bacon's probabilities are fitted on drafts up to 2021, with
    outcomes through 2025-26 (hockeystats.com/draft/guide);
  * the SCALE b: fitted on the realised careers of the 2007-2017 classes.
This check measures how much each would differ if built only from what was
knowable earlier. It cannot refit Bacon's own model on earlier drafts.

THREE PARTS (REPORT ONLY; no rule decides anything)
  A. SHAPE BY ERA. Split the classes 2007-2011 / 2012-2017. In each: the scale;
     whether log(pick) adds anything to his star chance (the validation test,
     within the era); and actual against predicted surplus by pick range.
  B. THE SCALE KNOWABLE AT EACH TRADE SEASON. For trade season T (2017-18 on),
     fit b only on classes drafted in T-9 or earlier, whose control windows had
     largely run out by then (the window runs to about age 27, nine seasons
     after an 18-year-old's draft).
  C. THE PICKS ACTUALLY TRADED. Every pick traded from 2017-07-01 with a known
     final slot (trades.db), valued at that slot with the pooled scale and with
     its trade season's knowable scale. SIMPLIFICATION for this check: the
     final slot stands in for the value at the trade (the round average for
     future picks and the trade-date slot are not built yet).

SURPLUS USED: skaters, pick_regression_first_look.py v1.1 (slides modelled,
goalies out). The decided package (no slides, goalies pooled) moves the scale
by about +1.5% in total and is not yet built; a relative check is unaffected.

Run from the repo root:  python 25_TESTS/pick_lookahead_check.py
"""

import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv

SCRIPT_VERSION = "pick_lookahead_check.py v1.0 (2026-10-09)"
load_dotenv()
OUT, SRC = Path(os.environ["OUTPUT_DIR"]), Path(os.environ["SOURCE_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"players": OUT / "pick_first_look_players.csv", "fl_log": OUT / "pick_first_look_log.txt",
     "bacon": SRC / "draft_slot_baseline.csv", "trades": SRC / "trades.db"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")
assert F["fl_log"].read_text(encoding="utf-8").startswith("pick_regression_first_look.py v1.1")

bacon = pd.read_csv(F["bacon"]).set_index("draft_pick")["p_star"]
d = pd.read_csv(F["players"])
d["y"], d["p_star"], d["log_pick"] = d["surplus"] / 1e6, d["pick"].map(bacon), np.log(d["pick"])


def design(frame, cols):
    """Columns plus sum-to-zero draft-year indicators for the classes in this frame (no intercept)."""
    cl = sorted(frame["draftYear"].unique())
    yrs = frame["draftYear"].values
    X = [frame[c].values for c in cols]
    for c in cl[:-1]:
        X.append((yrs == c).astype(float) - (yrs == cl[-1]).astype(float))
    return np.column_stack(X)


def fit(frame, cols, const=False):
    X = design(frame, cols)
    if const:
        X = np.column_stack([np.ones(len(frame)), X])
    return sm.OLS(frame["y"].values, X).fit(cov_type="HC1")


B_ALL = fit(d, ["p_star"]).params[0]
log(f"\npooled scale, all eleven classes: {B_ALL:.2f} ($M per 100% star chance)")

# ---- A. shape by era ---------------------------------------------------------------------
log("\nA. SHAPE BY ERA")
bands = [(1, 5), (6, 15), (16, 32), (33, 64), (65, 128), (129, 217)]
for name, lo, hi in (("2007-2011", 2007, 2011), ("2012-2017", 2012, 2017)):
    e = d[d["draftYear"].between(lo, hi)]
    m0 = fit(e, ["p_star"])
    m1 = fit(e, ["p_star", "log_pick"], const=True)
    b = m0.params[0]
    log(f"  {name}: {len(e):,} picks; scale {b:.2f} (se {m0.bse[0]:.2f}); log(pick) added to the star chance: "
        f"{m1.params[2]:+.3f} (se {m1.bse[2]:.3f}, p {m1.pvalues[2]:.3f})")
    row = []
    for blo, bhi in bands:
        s = e[e["pick"].between(blo, bhi)]
        row.append(f"{blo}-{bhi}: {s['y'].mean() / (b * s['p_star'].mean()):.2f}")
    log("     actual / predicted by pick range (1.00 = the shape fits): " + ", ".join(row))

# ---- B. knowable scale by trade season ---------------------------------------------------------
log("\nB. THE SCALE KNOWABLE AT EACH TRADE SEASON (classes drafted T-9 or earlier)")
known = {}
for T in range(2017, 2025):
    e = d[d["draftYear"] <= T - 9]
    m = fit(e, ["p_star"])
    known[T] = m.params[0]
    log(f"  {T}-{str(T + 1)[2:]}: classes 2007-{T - 9} ({e['draftYear'].nunique()}), scale {m.params[0]:.2f} "
        f"(se {m.bse[0]:.2f}), {100 * (m.params[0] / B_ALL - 1):+.0f}% against pooled; "
        f"#1 ${m.params[0] * bacon[1]:.1f}M, #10 ${m.params[0] * bacon[10]:.1f}M, #32 ${m.params[0] * bacon[32]:.2f}M")

# ---- C. the picks actually traded ----------------------------------------------------------------
con = sqlite3.connect(F["trades"])
t = pd.read_sql("select a.pick_number, a.pick_round, t.trade_date from trade_assets a join trades t using(trade_id) "
                "where a.asset_type = 'pick'", con)
t["date"] = pd.to_datetime(t["trade_date"])
t = t[(t["date"] >= "2017-07-01") & t["pick_number"].notna()].copy()
t["T"] = np.where(t["date"].dt.month >= 7, t["date"].dt.year, t["date"].dt.year - 1)
t = t[t["T"].isin(known)]
t["p_star"] = t["pick_number"].astype(int).map(bacon)
t = t[t["p_star"].notna()]
t["pooled"] = B_ALL * t["p_star"]
t["knowable"] = t["T"].map(known) * t["p_star"]
log(f"\nC. PICKS TRADED FROM 2017-07-01 with a final slot: {len(t)}")
log(f"  total value, pooled scale ${t['pooled'].sum():.1f}M; knowable scale ${t['knowable'].sum():.1f}M "
    f"({100 * (t['knowable'].sum() / t['pooled'].sum() - 1):+.1f}%)")
by = t.groupby("T").agg(picks=("pooled", "size"), pooled=("pooled", "sum"), knowable=("knowable", "sum"))
by["change %"] = 100 * (by["knowable"] / by["pooled"] - 1)
log(by.round(1).to_string())
first = t[t["pick_round"] == 1]
log(f"  first-round picks ({len(first)}): mean ${first['pooled'].mean():.2f}M pooled, "
    f"${first['knowable'].mean():.2f}M knowable")

(OUT / "pick_lookahead_check_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote pick_lookahead_check_log.txt in {OUT}")
