"""
gv_4b_inventory.py -- Phase 4b, Step 0 (READ-ONLY database inventory)
======================================================================

WHAT THIS DOES (plain English):
  Before the main circularity-validation script can be written, we need to
  know exactly what lives inside your local game-log database: the real
  table names for GV-raw, GV-adj, and any replacement-rebased variants,
  plus which seasons they cover. This script opens the database in
  READ-ONLY mode, looks around, and prints a report. It changes NOTHING.

HOW TO RUN (Windows, from the folder containing this file):
  python gv_4b_inventory.py

THEN: copy the full printed output and paste it back into the chat.

READ-ONLY GUARANTEE:
  The connection is opened with mode=ro (read-only). Even a bug in this
  script cannot write to or alter the database.
"""

import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# DB PATH -- edit this ONE line if your database lives somewhere else.
# Canonical location per project convention: new_scrape\nhl_gamelogs.sqlite
# (Last session you also ran from a consolidated folder on your Desktop --
#  if this path fails, point it at wherever the current single source of
#  truth copy sits.)
# ---------------------------------------------------------------------------
DB_PATH = Path(r"nhl_gamelogs.sqlite")

# Keywords that flag a table as relevant to Phase 4b. Anything whose name
# contains one of these gets the FULL report (columns + season coverage);
# everything else is just listed by name so nothing is invisible.
RELEVANT_KEYWORDS = ("game_value", "gv", "rebase", "adjust", "rapm",
                     "replacement", "metric")


def fail(msg: str) -> None:
    print("\n" + "!" * 70)
    print("INVENTORY STOPPED: " + msg)
    print("!" * 70)
    sys.exit(1)


def main() -> None:
    print("=" * 70)
    print("PHASE 4B STEP 0 -- GAME-LOG DATABASE INVENTORY (read-only)")
    print("=" * 70)

    # ---- 1. Confirm the database file actually exists at the path above ---
    if not DB_PATH.exists():
        # Help future-you: show what IS in the expected folder, if it exists.
        parent = DB_PATH.parent
        listing = ("\n  Folder contents: " +
                   ", ".join(p.name for p in parent.iterdir())
                   if parent.exists() else
                   f"\n  (folder '{parent}' does not exist either)")
        fail(f"Database not found at: {DB_PATH.resolve()}{listing}\n"
             "  -> Edit the DB_PATH line near the top of this script to the\n"
             "     folder that holds the CURRENT nhl_gamelogs.sqlite, then rerun.")

    print(f"\nDatabase file: {DB_PATH.resolve()}")
    print(f"File size    : {DB_PATH.stat().st_size / 1e6:,.1f} MB")

    # ---- 2. Open READ-ONLY. mode=ro makes writes impossible at the
    #         driver level -- belt-and-suspenders on top of "we never write".
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    cur = con.cursor()

    # ---- 3. List EVERY table so nothing is hidden --------------------------
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    if not tables:
        fail("Database opened but contains zero tables -- almost certainly "
             "the wrong file. Check DB_PATH.")

    print(f"\nAll tables ({len(tables)}):")
    for t in tables:
        print(f"  - {t}")

    # ---- 4. Full report on every 4b-relevant table -------------------------
    relevant = [t for t in tables
                if any(k in t.lower() for k in RELEVANT_KEYWORDS)]
    print(f"\n4b-relevant tables (name matched a GV/rebase keyword): "
          f"{len(relevant)}")

    for t in relevant:
        print("\n" + "-" * 70)
        print(f"TABLE: {t}")
        # Columns and types
        cols = cur.execute(f'PRAGMA table_info("{t}")').fetchall()
        print("  columns:")
        for c in cols:
            print(f"    {c[1]:<28} {c[2]}")
        # Row count
        n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"  rows: {n:,}")
        # Season coverage, if any recognizable season column exists.
        # (Different scripts named it differently over time -- check all.)
        colnames = {c[1].lower(): c[1] for c in cols}
        season_col = next((colnames[k] for k in
                           ("season", "season_start", "season_start_year")
                           if k in colnames), None)
        if season_col is not None:
            cov = cur.execute(
                f'SELECT MIN("{season_col}"), MAX("{season_col}"), '
                f'COUNT(DISTINCT "{season_col}") FROM "{t}"').fetchone()
            print(f"  season coverage: {cov[0]} -> {cov[1]} "
                  f"({cov[2]} distinct)")
        else:
            print("  season coverage: (no season column found)")
        # Player-ID column check -- the 4b join to the contract spine needs
        # an NHL player id; confirm which id column each table carries.
        id_cols = [c[1] for c in cols
                   if "player" in c[1].lower() or c[1].lower() == "nhl_id"]
        print(f"  id columns: {id_cols if id_cols else '(none found!)'}")

    con.close()
    print("\n" + "=" * 70)
    print("DONE. Copy EVERYTHING above and paste it into the chat.")
    print("=" * 70)


if __name__ == "__main__":
    main()
