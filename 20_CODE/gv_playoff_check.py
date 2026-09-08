"""
gv_playoff_check.py -- does `gv_adjusted` contain playoff games?

WHY THIS IS NEEDED
------------------
`term_premium_test.py` found no `game_type` column on `gv_adjusted`, so it
could not confirm the table is regular season only and said so in the log.
This matters because the signed specification defines the outcome as
regular-season Game Value. If playoff games are in there, players on good
teams pick up extra production, and players on good teams tend to hold longer
contracts, which would push the term coefficient upward. The main result came
out at zero, so this would work against the finding rather than for it, but it
should be confirmed rather than assumed.

THE LOGIC, IN PLAIN TERMS
-------------------------
A hockey game contains roughly 48 to 50 minutes of five-on-five play. Ten
skaters are on the ice for each of those minutes, five a side. So one game
contributes roughly 480 to 500 player-minutes of five-on-five time.

Take the total five-on-five minutes recorded in `gv_adjusted` for a season and
divide it by the number of games. If we divide by REGULAR SEASON games only
and the answer lands near 480-500, the table holds regular season only. If
that figure comes out well above 500, there is more ice time in the table than
the regular season can account for, and playoff games are the explanation.

The check is made sharper by the two irregular seasons. 2019-20 was cut short
and then followed by an unusually large 24-team playoff, so playoff games are
a much bigger share of that season than of any other. If playoffs are in the
table, 2019-20 is where it will show up most clearly.

HOW TO RUN
----------
    python gv_playoff_check.py

Read-only. It opens the database, runs two counts, and prints a verdict. It
writes nothing and changes nothing.
"""

import re
import sqlite3
import sys
from pathlib import Path

# Canonical game-log database, same path term_premium_test.py uses.
DB_PATH = Path(r"C:\Users\thoma\OneDrive\Desktop\test\nhl_gamelogs.sqlite")

# A single game's expected five-on-five player-minutes: about 48-50 minutes of
# five-on-five play, times ten skaters on the ice. The band is deliberately
# wide so that normal season-to-season variation does not trip it.
EXPECTED_LOW, EXPECTED_HIGH = 430, 540


def parse_season(v):
    """Return the season START year from whatever format the store uses.
    Handles 20192020, '2019-20', '2019-2020', and a bare 2019. Same rule as
    term_premium_test.py, so the two scripts agree on what a season is."""
    s = str(v).strip()
    if re.fullmatch(r"\d{8}", s):
        return int(s[:4])
    m = re.match(r"^(\d{4})\s*[-/]\s*\d{2,4}$", s)
    if m:
        return int(m.group(1))
    if re.fullmatch(r"\d{4}", s):
        return int(s)
    return None


def main():
    if not DB_PATH.exists():
        print(f"Database not found at:\n  {DB_PATH}\nEdit DB_PATH and re-run.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    # Game counts by season and type. game_type 2 is regular season, 3 is
    # playoffs, which is the NHL API's own convention and the one used
    # throughout the scrape.
    games = {}
    for season, gtype, n in conn.execute(
            "SELECT season, game_type, COUNT(DISTINCT game_id) "
            "FROM games GROUP BY season, game_type"):
        y = parse_season(season)
        if y is None:
            continue
        rec = games.setdefault(y, {"reg": 0, "post": 0})
        if int(gtype) == 2:
            rec["reg"] += n
        elif int(gtype) == 3:
            rec["post"] += n

    # Total five-on-five minutes in gv_adjusted, by season.
    toi = {}
    for season, t in conn.execute(
            "SELECT season, SUM(toi_5v5_min) FROM gv_adjusted GROUP BY season"):
        y = parse_season(season)
        if y is not None:
            toi[y] = float(t or 0.0)
    conn.close()

    if not toi:
        print("No rows found in gv_adjusted. Check the table name.")
        sys.exit(1)

    print(f"Expected five-on-five player-minutes per game: "
          f"{EXPECTED_LOW}-{EXPECTED_HIGH}\n")
    header = (f"{'season':>8} {'reg':>6} {'post':>5} {'5v5 min':>12} "
              f"{'per reg gm':>11} {'per all gm':>11}   verdict")
    print(header)
    print("-" * len(header))

    flagged = []
    for y in sorted(toi):
        g = games.get(y, {"reg": 0, "post": 0})
        reg, post = g["reg"], g["post"]
        if reg == 0:
            print(f"{y:>8} {'--':>6} {'--':>5} {toi[y]:>12,.0f} "
                  f"{'n/a':>11} {'n/a':>11}   no game rows for this season")
            continue
        per_reg = toi[y] / reg
        per_all = toi[y] / (reg + post) if (reg + post) else float("nan")

        # If dividing by regular season games alone lands in the expected
        # band, the table holds regular season only. If it lands above the
        # band while dividing by ALL games lands inside it, playoffs are in.
        if EXPECTED_LOW <= per_reg <= EXPECTED_HIGH:
            verdict = "regular season only"
        elif per_reg > EXPECTED_HIGH and EXPECTED_LOW <= per_all <= EXPECTED_HIGH:
            verdict = "PLAYOFFS INCLUDED"
            flagged.append(y)
        elif per_reg > EXPECTED_HIGH:
            verdict = "too much ice time -- investigate"
            flagged.append(y)
        else:
            verdict = "too little ice time -- investigate"
            flagged.append(y)

        print(f"{y:>8} {reg:>6} {post:>5} {toi[y]:>12,.0f} "
              f"{per_reg:>11.1f} {per_all:>11.1f}   {verdict}")

    print()
    if not flagged:
        print("VERDICT: gv_adjusted looks like regular season only. The "
              "specification's outcome definition holds and item 2.1 needs "
              "no revision.")
    else:
        print(f"VERDICT: seasons needing attention: "
              f"{', '.join(str(y) for y in flagged)}")
        print("If these read PLAYOFFS INCLUDED, the outcome variable is not "
              "what the specification defines. The direction of the problem "
              "would push the term coefficient upward, and the main result "
              "was already at zero, so the finding is unlikely to reverse. "
              "It would still need recording before the result is cited.")
    print("\nNote the 2019 row in particular: that season pairs a shortened "
          "schedule with a 24-team playoff, so it is where playoff contamination "
          "shows up most sharply.")


if __name__ == "__main__":
    main()
