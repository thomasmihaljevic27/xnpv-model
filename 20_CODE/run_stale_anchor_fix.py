"""
run_stale_anchor_fix.py                                       2026-07-29
===========================================================================
ONE COMMAND. Finishes the goalie stale-anchor fix end to end.

    python run_stale_anchor_fix.py

Does four things, stops loudly on the first problem, and never leaves a file
half-patched:

    0. Checks no output CSV is locked by Excel BEFORE doing any work.
    1. Confirms the engine patch is already applied.
    2. Applies the contract_npv.py patch, if not already applied.
    3. Runs goalie_value_engine.py, then contract_npv.py.

Safe to run more than once. Step 2 detects its own marker and skips. Steps 1
and 3 are read-only and idempotent by nature.

Everything printed is also written to run_stale_anchor_fix_log.txt. Send me
that one file.
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

F_ENG = HERE / "goalie_value_engine.py"
F_NPV = HERE / "contract_npv.py"

# Outputs that Excel commonly holds open. Checked before any work is done,
# because the previous run died on exactly this after twenty seconds of
# compute.
LOCKABLE = [
    "goalie_value_spine_v2.csv",
    "goalie_value_engine_run_log.txt",
    "contract_npv_spine.csv",
    "contract_npv_panel.csv",
    "contract_npv_run_log.txt",
]

# Marker proving the contract_npv patch is in. Chosen to be a string that
# cannot appear for any other reason.
NPV_MARKER = 'STALE_MAXBACK = 3'

# Marker proving the engine patch is in.
ENG_MARKER = 'stale_anchor_carry'

LOG = []


def say(msg=""):
    print(msg)
    LOG.append(msg)


def finish(code):
    (HERE / "run_stale_anchor_fix_log.txt").write_text(
        "\n".join(LOG), encoding="utf-8")
    say()
    print("log written: run_stale_anchor_fix_log.txt")
    sys.exit(code)


say("=" * 74)
say("STALE-ANCHOR FIX RUNNER")
say("=" * 74)

# --------------------------------------------------------------------------
# STEP 0 -- lock check. Do this first so a locked file costs a second, not a
# full run. Opening in append mode is the reliable Windows test: it needs the
# same write handle to_csv does, but appends nothing.
# --------------------------------------------------------------------------
say("\n[0] checking no output file is open in Excel")
locked = []
for name in LOCKABLE:
    p = HERE / name
    if not p.exists():
        continue
    try:
        with open(p, "a", encoding="utf-8"):
            pass
    except PermissionError:
        locked.append(name)

if locked:
    say("    LOCKED. Close these in Excel and re-run:")
    for name in locked:
        say(f"      {name}")
    finish(1)
say("    ok, nothing locked")

# --------------------------------------------------------------------------
# STEP 1 -- the engine patch must already be in. This runner does not apply
# it, because it is already applied on this machine and re-applying an
# exact-string patch to a file that has moved on is how you corrupt it.
# --------------------------------------------------------------------------
say("\n[1] confirming the engine patch is applied")
if not F_ENG.exists():
    say(f"    MISSING: {F_ENG}")
    finish(1)
if ENG_MARKER not in F_ENG.read_text(encoding="utf-8"):
    say("    NOT APPLIED. Run patch_goalie_stale_anchor_v2.py first, then")
    say("    re-run this script.")
    finish(1)
say("    ok, goalie_value_engine.py carries the stale_anchor_carry branch")

# --------------------------------------------------------------------------
# STEP 2 -- apply the contract_npv patch. Three exact-string edits, each of
# which must match exactly once. Nothing is written unless all three match,
# so a partial patch is impossible.
# --------------------------------------------------------------------------
say("\n[2] patching contract_npv.py")
if not F_NPV.exists():
    say(f"    MISSING: {F_NPV}")
    finish(1)

npv_text = F_NPV.read_text(encoding="utf-8")

if NPV_MARKER in npv_text:
    say("    already applied, skipping")
else:
    EDITS = []

    # ---- EDIT 1: the three constants -------------------------------------
    EDITS.append((
        "constants",
        'G = CAP_GROWTH           # D17: one constant, two uses (D11 ceilings + here)',
        'G = CAP_GROWTH           # D17: one constant, two uses (D11 ceilings + here)\n'
        '\n'
        '# ---- A1/A2/A3 stale-anchor constants (2026-07-29) -------------------------\n'
        '# A goaltender with no t-1 season but a usable older one is a real player\n'
        '# with a real, older anchor -- not a player with no history. Before this he\n'
        '# fell through to no_history_unpriced, which is how Carey Price, Corey\n'
        '# Crawford, Ben Bishop, Spencer Knight and Carter Hart were all recorded as\n'
        '# never having played.\n'
        '#\n'
        '#   STALE_TARGET   conditional mean WAR of that population GIVEN he plays\n'
        '#                  (0.650, n=29). GOALIE_LEAGUE_AVG is the mean of a\n'
        '#                  population he is not in, so shrinking him toward it\n'
        '#                  pushes his value UP, which is the wrong direction.\n'
        '#\n'
        '#   STALE_GATE     P(the season happens at all) = 29/93 = 0.312. This does\n'
        '#                  most of the work, because the goalie rate carries a\n'
        '#                  ~1.39%-of-cap intercept: ungated, a goaltender who never\n'
        '#                  plays still books roughly $1.3M of modelled value.\n'
        '#\n'
        '#   STALE_MAXBACK  how far the carry search may reach. Matches\n'
        '#                  goalie_value_engine.STALE_MAXBACK exactly. A goaltender\n'
        '#                  four years absent is a different asset, not a stale one.\n'
        'STALE_TARGET  = 0.650\n'
        'STALE_GATE    = 0.312\n'
        'STALE_MAXBACK = 3',
    ))

    # ---- EDIT 2: the walk-back and target routing ------------------------
    # Same algorithm as carry_anchor() in the engine, inline because this class
    # has no equivalent helper. The search runs over anchor SEASONS, not raw
    # WAR rows, which is what makes it a weighted cascade result rather than a
    # single stale figure: at s = t0-1 the cascade sees t0-2, t0-3 and t0-4.
    EDITS.append((
        "stale-anchor walk-back",
        '''        elif pd.notna(w1):
            tr, src = w1, "t1_only"
        else:
            return np.nan, "no_history_unpriced"
        KEPT = 1 - LAMBDA_G          # = 0.35, see convention note above
        return KEPT * tr + (1 - KEPT) * GOALIE_LEAGUE_AVG, src''',
        '''        elif pd.notna(w1):
            tr, src = w1, "t1_only"
        else:
            # A1 (2026-07-29). No t-1 season, so the locked cascade has nothing
            # to stand on. Rather than declaring no history, walk back to the
            # most recent season at which the SAME cascade could still reach a
            # real anchor, bounded at STALE_MAXBACK seasons. Mirrors
            # goalie_value_engine.carry_anchor() deliberately: both files
            # compute their own goalie anchor, and different rules would give
            # the same goaltender two different values.
            tr, src = np.nan, "no_history_unpriced"
            for s in range(t0 - 1, t0 - 1 - STALE_MAXBACK, -1):
                a1, a2, a3 = (self._get(nname, s - k) for k in (1, 2, 3))
                if pd.notna(a1) and pd.notna(a2) and pd.notna(a3):
                    tr = 0.5 * a1 + 0.3 * a2 + 0.2 * a3
                elif pd.notna(a1) and pd.notna(a2):
                    tr = 0.6 * a1 + 0.4 * a2
                elif pd.notna(a1):
                    tr = a1
                else:
                    continue          # nothing reachable at s, try one earlier
                src = "stale_anchor"
                break
            if pd.isna(tr):
                # Genuinely no reachable history within the bound. Unchanged
                # behaviour: prospect-pillar territory, not priced here.
                return np.nan, "no_history_unpriced"
        KEPT = 1 - LAMBDA_G          # = 0.35, see convention note above
        # A2 (2026-07-29): route the shrinkage target by population. A stale-
        # anchor goaltender shrinks toward the conditional mean of goaltenders
        # who came back, not toward the league average.
        target = STALE_TARGET if src == "stale_anchor" else GOALIE_LEAGUE_AVG
        return KEPT * tr + (1 - KEPT) * target, src''',
    ))

    # ---- EDIT 3: seed the goalie survival weight with the gate ------------
    # Anchored on the goalie loop. The skater loop opens with the same two
    # lines but different following text, so this is unique.
    EDITS.append((
        "materialisation gate",
        '''        det, S = [], 1.0
        for k, (_, r) in enumerate(crows.iterrows()):''',
        '''        # A3 (2026-07-29): seed S with the materialisation gate for stale-
        # anchor goaltenders, 1.0 for everyone else (unchanged behaviour).
        # Seeding rather than applying at k=0 means the gate carries forward:
        # of stale-anchor rows where the goaltender did not play at k=0, only
        # 5 of 54 appeared at k=1, so the state is near-absorbing. Slightly
        # conservative, and named as such.
        det = []
        S = STALE_GATE if src == "stale_anchor" else 1.0
        for k, (_, r) in enumerate(crows.iterrows()):''',
    ))

    working = npv_text
    failures = []
    for desc, old, new in EDITS:
        n = working.count(old)
        if n != 1:
            failures.append((desc, n))
            continue
        working = working.replace(old, new, 1)

    if failures:
        say("    NOTHING WRITTEN. anchor check failed:")
        for desc, n in failures:
            say(f"      {desc}: found {n}, expected exactly 1")
        say("    send me contract_npv.py and I will re-cut.")
        finish(1)

    bak = F_NPV.with_suffix(".py.pre_stale_anchor_v2.bak")
    shutil.copy2(F_NPV, bak)
    F_NPV.write_text(working, encoding="utf-8")
    say(f"    applied 3 edits   (backup: {bak.name})")

# --------------------------------------------------------------------------
# STEP 3 -- run both scripts, in order. The engine writes the v2 spine, and
# contract_npv.py reads it at import time, so the order is not optional.
# --------------------------------------------------------------------------
for script in ("goalie_value_engine.py", "contract_npv.py"):
    say(f"\n[3] running {script}")
    say("-" * 74)
    proc = subprocess.run([sys.executable, script], cwd=HERE,
                          capture_output=True, text=True)
    for line in (proc.stdout or "").rstrip().split("\n"):
        say(line)
    if proc.returncode != 0:
        say("-" * 74)
        say(f"    {script} FAILED (exit {proc.returncode})")
        for line in (proc.stderr or "").rstrip().split("\n")[-25:]:
            say(line)
        say("\n    Stopped here. Nothing after this ran.")
        finish(1)
    say("-" * 74)
    say(f"    {script} completed")

say("\n" + "=" * 74)
say("DONE. Both scripts completed.")
say("=" * 74)
finish(0)
