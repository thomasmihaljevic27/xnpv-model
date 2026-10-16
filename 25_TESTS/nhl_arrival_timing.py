"""
nhl_arrival_timing.py -- in which season after the draft do drafted players reach the NHL? (report only)

ASKED (the supervisor, meeting of 2026-10-15), as evidence for the slot's value fading after D+3: "of all the people
who made the jump, ... how many years after they got drafted?" Thomas's guess in the meeting: most in the first
season, a few more in the second, about 15% later or never.

ARRIVAL uses the model's own line between a prospect and an NHL player (prospect_values.is_prospect):
  * a skater arrives in the first season he plays 10 or more NHL games (the skater forecast's minimum);
  * a goaltender arrives in the first season he plays an NHL game (the goalie rule: any game).
He is valued as a prospect up to and including that season and by the player model from the next one.
Seasons are named from the draft: D+1 is the season starting the autumn after his draft (season start year =
draft year). The NHL seasons are pick_curve_seasons.csv's, which hold each player's seasons up to the end of his
club control (CBA Group 3: 27, or seven accrued seasons); a first arrival after control ended is not seen, and in
this currency such a player is worth nothing to the drafting club. Every 2007-2017 draft is observed through
2025-26, i.e. through at least D+9.

The six drafted players who died before reaching the NHL are left out, as from every fit (pick_curve.py
v1.6, excluded_deceased).
INPUTS: OUTPUT_DIR/pick_curve_players.csv, pick_curve_seasons.csv (pick_curve.py).
OUTPUTS: OUTPUT_DIR/nhl_arrival_timing.csv (one row per drafted player), nhl_arrival_timing_log.txt.
Run from the repo root:  python 25_TESTS/nhl_arrival_timing.py
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

SCRIPT_VERSION = "nhl_arrival_timing.py v1.0 (2026-10-15)"
load_dotenv()
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


log(SCRIPT_VERSION)
F = {"players": OUTPUT_DIR / "pick_curve_players.csv", "seasons": OUTPUT_DIR / "pick_curve_seasons.csv"}
for k, p in F.items():
    log(f"  input {k}: {p.resolve()}  (modified {pd.Timestamp(p.stat().st_mtime, unit='s'):%Y-%m-%d %H:%M})")

SKATER_GP, GOALIE_GP = 10, 1        # prospect_values.SKATER_GP; goalies: any NHL game
LAST_D = 9                          # 2017 draft + 8 = 2025-26, its D+9: every draft is observed through D+9

p = pd.read_csv(F["players"])
s = pd.read_csv(F["seasons"])
p = p[p["draftYear"].between(2007, 2017) & ~p["excluded_deceased"].astype(bool)].copy()   # deceased draftees out
s = s.merge(p[["draftYear", "pick", "is_goalie"]], on=["draftYear", "pick"])
s["need"] = np.where(s["is_goalie"].astype(bool), GOALIE_GP, SKATER_GP)
first = s[s["gp"] >= s["need"]].groupby(["draftYear", "pick"])["season"].min().rename("arrival_season")
p = p.merge(first, on=["draftYear", "pick"], how="left")
p["arrival_D"] = p["arrival_season"] - p["draftYear"] + 1            # D+1 = season starting in the draft year
assert (p["arrival_D"].dropna() >= 1).all()
p["group"] = np.select([p["pick"] <= 10, p["round"] == 1, p["round"] == 2], ["picks 1-10", "rest of round 1",
                                                                           "round 2"], "rounds 3-7")
log(f"\n{len(p):,} drafted players 2007-2017 ({int(p['is_goalie'].sum())} goaltenders); arrived in the NHL within club "
    f"control: {int(p['arrival_D'].notna().sum()):,} ({p['arrival_D'].notna().mean():.1%})")
late = int((p["arrival_D"] > LAST_D).sum())
log(f"  arrivals after D+{LAST_D} (not seen for every draft, shown as 'D+10 or later'): {late}")


def table(frame, title):
    n, arr = len(frame), frame["arrival_D"]
    log(f"\n  {title}: {n:,} players, {int(arr.notna().sum()):,} arrived ({arr.notna().mean():.1%})")
    log(f"    {'season':<16}{'arrived':>8}{'% of arrivals':>15}{'cumulative':>12}{'% of all picks':>16}")
    cum = 0
    rows = []
    for dd in list(range(1, LAST_D + 1)) + ["10+"]:
        k = int((arr >= 10).sum()) if dd == "10+" else int((arr == dd).sum())
        cum += k
        lab = f"D+{dd}" if dd != "10+" else "D+10 or later"
        share = k / max(arr.notna().sum(), 1)
        log(f"    {lab:<16}{k:>8,}{share:>15.1%}{cum / max(arr.notna().sum(), 1):>12.1%}{k / n:>16.1%}")
        rows.append({"group": title, "season": lab, "arrived": k, "share_of_arrivals": share, "share_of_all": k / n})
    log(f"    {'never':<16}{int(arr.isna().sum()):>8,}{'':>15}{'':>12}{arr.isna().mean():>16.1%}")
    rows.append({"group": title, "season": "never", "arrived": int(arr.isna().sum()), "share_of_arrivals": np.nan,
                 "share_of_all": arr.isna().mean()})
    return rows


log("\nSEASON OF NHL ARRIVAL (skaters: first 10+ game season; goaltenders: first game)")
summary = table(p, "all drafted players")
for g in ["picks 1-10", "rest of round 1", "round 2", "rounds 3-7"]:
    summary += table(p[p["group"] == g], g)
summary += table(p[~p["is_goalie"].astype(bool)], "skaters only")

p[["draftYear", "pick", "round", "player", "is_goalie", "group", "arrival_season", "arrival_D"]].to_csv(
    OUTPUT_DIR / "nhl_arrival_timing.csv", index=False)
pd.DataFrame(summary).to_csv(OUTPUT_DIR / "nhl_arrival_timing_summary.csv", index=False)
(OUTPUT_DIR / "nhl_arrival_timing_log.txt").write_text("\n".join(LOG), encoding="utf-8")
log(f"\nwrote nhl_arrival_timing.csv, nhl_arrival_timing_summary.csv and the log in {OUTPUT_DIR}")
