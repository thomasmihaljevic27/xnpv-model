#!/usr/bin/env python3
"""
gv_old_vs_new_compare.py  --  READ-ONLY diagnostic: old vs new Game Value.

WHAT THIS IS FOR
-----------------
replacement_rebase.py (Script 5) writes player_game_value_repl, which carries
BOTH the original average-based `game_value` and the new replacement-based
`gv_repl` on every row. This script summarises how the two differ at the
SEASON level (the paper's horizon and Phase 4b's level) so you can eyeball
whether the rebasing did something sane on real data. It writes NOTHING to the
DB and prints only small aggregates -- safe to paste back into chat.

RUN ORDER
----------
    python replacement_rebase.py       # must have produced player_game_value_repl
    python gv_old_vs_new_compare.py

WHAT IT REPORTS (all at the season x team x player "stint" level, reg season)
-----------------------------------------------------------------------------
  1. How tightly the two rankings agree (Pearson + rank correlation). Expect
     HIGH but not 1.0: the shift is ice-time-weighted, so it re-orders players
     a little -- that re-ordering is the whole point of a replacement baseline.
  2. How many stints flip sign (old <= 0 but new > 0). The rebase lifts
     everyone, so below-average-but-above-replacement players cross zero.
  3. Mean/median shift, and the shift's correlation with ice time (should be
     strongly positive: the adjustment IS rate x TOI).
  4. Top 10 and bottom 10 by the new number, with the old number alongside --
     the plausibility check (are the top names real stars? are the bottom
     names low-minute/replacement types?).
"""

import os
import sqlite3
from pathlib import Path
import numpy as np

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.environ["GAMELOG_DB"]   # <-- SAME shared path, from .env

def rankcorr(a, b):
    """Spearman-style: Pearson correlation of the ranks (no scipy needed)."""
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])

def main():
    if not Path(DB_PATH).exists():
        raise SystemExit(f"DB not found at {DB_PATH} -- set GAMELOG_DB in .env.")
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if not cur.execute("""SELECT name FROM sqlite_master
            WHERE type='table' AND name='player_game_value_repl'""").fetchone():
        raise SystemExit("player_game_value_repl not found -- run replacement_rebase.py first.")

    # Season-summed stint totals for BOTH metrics, regular season only.
    rows = cur.execute("""
        SELECT season, team, player_id, MAX(player_name) AS name,
               MAX(pos_bucket) AS pos,
               SUM(game_value) AS old_gv,
               SUM(gv_repl)    AS new_gv,
               SUM(toi_minutes) AS toi
        FROM player_game_value_repl
        WHERE is_regular_season = 1
        GROUP BY season, team, player_id""").fetchall()

    old = np.array([r["old_gv"] for r in rows], float)
    new = np.array([r["new_gv"] for r in rows], float)
    toi = np.array([r["toi"] if r["toi"] is not None else 0.0 for r in rows], float)
    shift = new - old

    print("="*68)
    print(f"OLD vs NEW Game Value -- {len(rows):,} season-team-player stints")
    print("="*68)
    print(f"1. agreement:  Pearson r = {np.corrcoef(old,new)[0,1]:.4f}   "
          f"rank corr = {rankcorr(old,new):.4f}")
    flips = int(np.sum((old <= 0) & (new > 0)))
    print(f"2. sign flips (old<=0 -> new>0): {flips:,}  "
          f"({100*flips/len(rows):.1f}% of stints)")
    print(f"3. shift (new-old):  mean = {shift.mean():+.3f}  median = "
          f"{np.median(shift):+.3f}  min = {shift.min():+.3f}  max = {shift.max():+.3f}")
    print(f"   corr(shift, TOI) = {np.corrcoef(shift,toi)[0,1]:.4f}  "
          f"(should be strongly +; adjustment is rate x TOI)")
    print(f"   league totals:  old sum = {old.sum():+.1f} (~0)   "
          f"new sum = {new.sum():+.1f} (>0, above replacement)")

    order = np.argsort(-new)
    print("\n4a. TOP 10 by NEW gv_repl (plausibility -- expect real stars):")
    print(f"    {'name':<22}{'season':<10}{'pos':<4}{'old':>9}{'new':>9}{'TOI':>8}")
    for i in order[:10]:
        r = rows[i]
        print(f"    {(r['name'] or '?')[:21]:<22}{r['season']:<10}{r['pos']:<4}"
              f"{old[i]:>9.2f}{new[i]:>9.2f}{toi[i]:>8.0f}")
    print("\n4b. BOTTOM 10 by NEW gv_repl (expect low-minute / replacement types):")
    for i in order[-10:]:
        r = rows[i]
        print(f"    {(r['name'] or '?')[:21]:<22}{r['season']:<10}{r['pos']:<4}"
              f"{old[i]:>9.2f}{new[i]:>9.2f}{toi[i]:>8.0f}")
    print("="*68)
    conn.close()

if __name__ == "__main__":
    main()
