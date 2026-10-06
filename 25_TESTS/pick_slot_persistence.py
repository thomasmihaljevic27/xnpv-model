"""
pick_slot_persistence.py -- how well a team's draft slot one year predicts its
slot one, two and three years later.

SCRIPT_VERSION = 1.0  (2026-10-06)

WHY THIS EXISTS
---------------
Directive 6's restart (MODEL_DIRECTIVES.md) prices a pick whose number is not
yet final at the slot it holds on the trade date. Two cases have no slot to
read: a next-draft pick traded in the off-season (no standings yet), and a pick
two or more drafts out. Thomas (2026-10-06) asked to explore both candidate
rules for them -- the team's slot in the last draft held, or the round average
-- and to see first how persistent a team's slot is from one year to the next.
If it barely persists, that is an argument for the round average.

WHAT IT MEASURES
----------------
For every franchise and draft year, the position its OWN first-round pick held
in the first round (pick-in-round 1..N), whoever ended up making the pick. Then,
for lags of one, two and three drafts:
  1. the correlation between the slot at year y and at year y+k, with an 80%
     interval from resampling whole franchises (the independent unit is the
     franchise, not the team-year pair: one club's run of bad seasons produces
     several pairs);
  2. a table by starting band (1-5, 6-10, 11-16, 17-24, 25-32): where those
     teams' own picks landed k drafts later -- average slot, the 10th-90th
     percentile range, and the average size of the move;
  3. the error of the two candidate rules at predicting the slot k drafts later:
     (a) last draft's slot, (b) the middle of the round. Squared error first (the
     declared primary score for a forecast feeding an expected-value sum), then
     absolute error. This is error in SLOTS. It is not yet error in value: the
     curve is steepest at the top, so a miss of five slots near the top costs far
     more than five near the bottom. That comparison waits for the new curve.

ASSUMPTIONS (each a place a result could move)
----------------------------------------------
- "The original team" is the first code in the NHL Records `teamPickHistory`
  chain ("TOR-SJS-STL" is Toronto's pick), the convention slot_curve.py used.
- Franchises that moved or renamed are one team: Phoenix / Arizona / Utah, and
  Atlanta / Winnipeg (the 2011 move). A relocated roster carries its standing.
- First round only. The first round includes the lottery, which is part of what
  a traded first conveys. Later rounds follow the same standings order without
  the lottery, so they are not measured separately.
- A franchise with no own first-round pick in a year (forfeited) uses its own
  second-round position, flagged and counted; failing that, the year is dropped.
- Pick-in-round comes from the record. A compensatory first-round pick shifts
  later positions by one in its year; not corrected.
- Teams per round: 30 through 2016, 31 for 2017-2020, 32 from 2021. Slots are
  compared as recorded, not rescaled; the expansion clubs enter in their first
  draft (Vegas 2017, Seattle 2021) and have fewer pairs.
- The round middle is (N + 1) / 2 for the target year's N.

INPUTS:  OUTPUT_DIR/draft_raw/draft_YYYY.json (cached by draft_pick_linkage.py;
         this script never fetches)
OUTPUT:  OUTPUT_DIR/pick_slot_persistence.csv (one row per franchise-year)
RUN:     python 25_TESTS/pick_slot_persistence.py      (from the repo root)
"""

import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
load_dotenv()

SCRIPT_VERSION = "1.0"
print(f"pick_slot_persistence.py SCRIPT_VERSION {SCRIPT_VERSION}")

OUTPUT_DIR = os.environ["OUTPUT_DIR"]
DRAFT_RAW = os.path.join(OUTPUT_DIR, "draft_raw")
OUT_CSV = os.path.join(OUTPUT_DIR, "pick_slot_persistence.csv")

LAGS = (1, 2, 3)
N_BOOT = 2000                 # franchise resamples for the correlation interval
BANDS = [(1, 5), (6, 10), (11, 16), (17, 24), (25, 32)]
rng = np.random.default_rng(20261006)   # fixed seed: reproducible intervals

# Franchise identity: one code per franchise across moves and renames.
FRANCHISE = {"PHX": "ARI", "UTA": "ARI", "ARI": "ARI", "ATL": "WPG"}


def franchise(code):
    code = str(code)
    return FRANCHISE.get(code, code)


def teams_in_draft(year):
    return 30 if year <= 2016 else (31 if year <= 2020 else 32)


# ----------------------------------------------------------------------------
# 1. Load the cached draft records. Print the real path and what was found, so
#    a run against the wrong folder is visible before any figure is read.
# ----------------------------------------------------------------------------
files = sorted(glob.glob(os.path.join(DRAFT_RAW, "draft_*.json")))
print(f"[input] {DRAFT_RAW}: {len(files)} draft files")
if not files:
    sys.exit("no cached draft files -- run 20_CODE/draft_pick_linkage.py first")
rows = []
for f in files:
    with open(f) as fh:
        rows += json.load(fh)["data"]
d = pd.DataFrame(rows)
d = d[d["teamPickHistory"].notna()].copy()
d["orig"] = d["teamPickHistory"].astype(str).str.split("-").str[0].map(franchise)
print(f"[input] {len(d):,} picks, drafts {d['draftYear'].min()}-{d['draftYear'].max()}")

# ----------------------------------------------------------------------------
# 2. One slot per franchise-year: its own first-round position, else its own
#    second-round position (flagged). If a franchise somehow shows two own picks
#    in a round (should not happen), the first is taken and counted.
# ----------------------------------------------------------------------------
out, dup = [], 0
for yr, g in d.groupby("draftYear"):
    n = teams_in_draft(int(yr))
    for team in sorted(g["orig"].unique()):
        mine = g[g["orig"] == team]
        r1 = mine[mine["roundNumber"] == 1].sort_values("pickInRound")
        r2 = mine[mine["roundNumber"] == 2].sort_values("pickInRound")
        if len(r1) > 1 or len(r2) > 1:
            dup += 1
        if len(r1):
            slot, src = int(r1.iloc[0]["pickInRound"]), "R1"
        elif len(r2):
            slot, src = int(r2.iloc[0]["pickInRound"]), "R2 stand-in"
        else:
            continue
        out.append({"franchise": team, "year": int(yr), "slot": slot,
                    "teams": n, "source": src})
s = pd.DataFrame(out)

# Guard: each draft must show about one own slot per team. A large shortfall
# means the original-team parse broke (an API change), not a real gap.
per_year = s.groupby("year").size()
bad = per_year[(per_year < s.groupby("year")["teams"].first() - 2)]
assert bad.empty, f"too few franchises with an own slot in: {bad.to_dict()}"
print(f"[slots] {len(s):,} franchise-years, {s['franchise'].nunique()} franchises; "
      f"{(s['source'] != 'R1').sum()} use the second-round stand-in; "
      f"{dup} franchise-years showed two own picks in one round")
s.to_csv(OUT_CSV, index=False)
print(f"[output] {OUT_CSV}")

# ----------------------------------------------------------------------------
# 3. Pairs: slot at y and at y+k for the same franchise.
# ----------------------------------------------------------------------------
def pairs(k):
    a = s[["franchise", "year", "slot"]]
    b = s[["franchise", "year", "slot", "teams"]].copy()
    b["year"] -= k
    p = a.merge(b, on=["franchise", "year"], suffixes=("_t", "_tk"))
    return p


def corr_by_franchise(p):
    """Correlation of slot_t and slot_tk, with an 80% interval from resampling
    franchises (all of a franchise's pairs travel together)."""
    r = float(np.corrcoef(p["slot_t"], p["slot_tk"])[0, 1])
    groups = [g for _, g in p.groupby("franchise")]
    boots = np.empty(N_BOOT)
    for i in range(N_BOOT):
        pick = rng.integers(0, len(groups), len(groups))
        q = pd.concat([groups[j] for j in pick])
        boots[i] = np.corrcoef(q["slot_t"], q["slot_tk"])[0, 1]
    lo, hi = np.percentile(boots, [10, 90])
    return r, lo, hi


print("\n[1] Correlation of a franchise's own first-round slot with its slot k drafts later")
print("    (80% interval from 2,000 resamples of franchises; Spearman = rank correlation)")
print(f"    {'lag':>3} {'pairs':>6} {'franchises':>10} {'corr':>6} {'80% interval':>16} {'Spearman':>9}")
for k in LAGS:
    p = pairs(k)
    r, lo, hi = corr_by_franchise(p)
    rho = p[["slot_t", "slot_tk"]].rank().corr().iloc[0, 1]
    print(f"    {k:>3} {len(p):>6} {p['franchise'].nunique():>10} {r:>6.2f} "
          f"   [{lo:>5.2f}, {hi:>5.2f}] {rho:>9.2f}")

print("\n[2] Where teams' own first-rounders landed k drafts later, by starting slot")
print("    avg = average slot; p10-p90 = the middle 80% of outcomes; move = average "
      "absolute change in slots")
for k in LAGS:
    p = pairs(k)
    print(f"\n    {k} draft(s) later")
    print(f"    {'start':>6} {'pairs':>6} {'avg':>6} {'p10-p90':>9} {'move':>6}")
    for lo_b, hi_b in BANDS:
        q = p[(p["slot_t"] >= lo_b) & (p["slot_t"] <= hi_b)]
        if q.empty:
            continue
        p10, p90 = np.percentile(q["slot_tk"], [10, 90])
        move = (q["slot_tk"] - q["slot_t"]).abs().mean()
        print(f"    {lo_b:>2}-{hi_b:<3} {len(q):>6} {q['slot_tk'].mean():>6.1f} "
              f"{int(round(p10)):>4}-{int(round(p90)):<4} {move:>6.1f}")

print("\n[3] Predicting the slot k drafts later: last draft's slot against the round middle")
print("    RMSE = root mean squared error (primary); MAE = mean absolute error; in slots.")
print("    'last slot wins' = share of franchise resamples where its squared error is lower.")
print(f"    {'lag':>3} {'pairs':>6} {'RMSE last':>10} {'RMSE mid':>9} {'MAE last':>9} "
      f"{'MAE mid':>8} {'last slot wins':>15}")
for k in LAGS:
    p = pairs(k).copy()
    p["mid"] = (p["teams"] + 1) / 2.0
    p["se_last"] = (p["slot_tk"] - p["slot_t"]) ** 2
    p["se_mid"] = (p["slot_tk"] - p["mid"]) ** 2
    p["ae_last"] = (p["slot_tk"] - p["slot_t"]).abs()
    p["ae_mid"] = (p["slot_tk"] - p["mid"]).abs()
    groups = [g for _, g in p.groupby("franchise")]
    wins = 0
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(groups), len(groups))
        q = pd.concat([groups[j] for j in pick])
        wins += q["se_last"].mean() < q["se_mid"].mean()
    print(f"    {k:>3} {len(p):>6} {np.sqrt(p['se_last'].mean()):>10.2f} "
          f"{np.sqrt(p['se_mid'].mean()):>9.2f} {p['ae_last'].mean():>9.2f} "
          f"{p['ae_mid'].mean():>8.2f} {wins:>9,} of {N_BOOT:,}")

print("\nRead [3] as slots only. Which rule prices picks better is a value question and "
      "needs the new curve.")
