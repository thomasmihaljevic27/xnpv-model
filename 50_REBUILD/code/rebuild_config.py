"""rebuild_config.py -- paths, constants and guard rails for the rebuild tree.

EXPERIMENTAL. Nothing in 50_REBUILD/ is production. This module is the only
place the rebuild learns where anything lives, and it enforces the one rule
that keeps the experiment separate from the live model: every write goes to
50_REBUILD/output/, and an attempted write anywhere else raises.

WHY A SECOND CONFIG AT ALL
    The production scripts read SOURCE_DIR / OUTPUT_DIR out of .env. The
    rebuild reads the same SOURCE_DIR (vendor inputs are read-only for both,
    so sharing them costs nothing and guarantees both chains see identical
    source bytes) but never touches OUTPUT_DIR. If .env is absent the paths
    fall back to the repo layout, so the tree runs in a fresh clone with no
    setup -- deliberately, because a rebuild that needs a machine-specific
    file to start cannot be reproduced by a reader.

VERSIONING
    Every rebuild script carries SCRIPT_VERSION and prints it through
    banner(). Three stale-file incidents in this project were traced to a
    script that ran without anyone knowing which version ran.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

SCRIPT_VERSION = "1.0"

# --- Tree layout ----------------------------------------------------------
# resolve() first: __file__ can be relative depending on how python was
# invoked, and every path below hangs off this one.
CODE_DIR = Path(__file__).resolve().parent
REBUILD_ROOT = CODE_DIR.parent
REPO_ROOT = REBUILD_ROOT.parent

try:  # .env is optional; the fallbacks below are the documented default
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

# Vendor inputs. Shared with production, READ ONLY from this tree. If .env
# points SOURCE_DIR somewhere else on a given machine we honour it, so the
# rebuild and the live model can never read two different WAR.csv files.
SOURCE_DIR = Path(os.environ.get("SOURCE_DIR", REPO_ROOT / "10_SOURCE"))

# The rebuild's own output. NOT OUTPUT_DIR -- the live 30_OUTPUT tree is
# never written to, never read as an input, and never cleaned by this code.
OUT_DIR = REBUILD_ROOT / "output"
DOCS_DIR = REBUILD_ROOT / "docs"

# Production paths, recorded so the isolation guard can refuse them by name
# rather than by a fragile prefix comparison alone.
PROD_OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", REPO_ROOT / "30_OUTPUT"))
PROD_CODE_DIR = REPO_ROOT / "20_CODE"

F_WAR_SKATERS = SOURCE_DIR / "WAR.csv"
F_WAR_GOALIES = SOURCE_DIR / "Goalies_WAR.csv"

# --- Shared modelling constants -------------------------------------------
# These are reproduced from the production engine rather than imported, so
# 50_REBUILD/ stands alone and so a production edit cannot silently change a
# rebuild result. player_season_table.py asserts them equal to the engine's
# copies whenever 20_CODE is importable -- that assert, not this comment, is
# what keeps the two in step.

# D20 schedule proration. WAR is a season TOTAL, so the two shortened
# seasons mechanically deflate any anchor drawn from them.
PRORATION = {2019: 82 / 70, 2020: 82 / 56}

# Team games actually played, by season start year. Used for the games
# SHARE (availability), which is a different quantity from the D20 total
# correction above: proration fixes the league-wide schedule, the share
# measures what fraction of his team's season the player was available for.
SEASON_LEN = {2019: 70, 2020: 56}
FULL_SEASON = 82

# Two different humans merged under one row-name in WAR.csv.
MERGED_WAR_NAMES = {"ryan johnson", "nathan smith"}

# The six WAR components, in the source's own column names and order.
COMPONENTS = ["EVO WAR", "EVD WAR", "PP WAR", "PK WAR", "Pens WAR", "Shoot WAR"]

# UNALLOCATED WAR -- found 2026-09-14 by this tree's reproduction guard and
# not previously recorded anywhere in 00_STATE.
#
#   For 2007-08 through 2022-23 the six components above add to the WAR total
#   exactly (max |gap| 3e-14, floating point). From 2023-24 they stop: 98% of
#   rows carry a residual, it is positive on average, and it grows with the
#   player's WAR (r = 0.79 for forwards, 0.53 for defencemen; about 2% of WAR
#   at the median and at 3+ WAR). It is small in absolute terms -- median
#   0.0026 wins, largest 0.33 (Sam Reinhart 2023-24).
#
#   The cause is on the vendor's side: the export's recent seasons carry
#   something in the total that is not broken out into the six columns. We do
#   not know what, and this tree does not guess.
#
#   HOW THE REBUILD HANDLES IT. Carrying the residual as a seventh, explicitly
#   unallocated component. Three reasons. (1) A component-wise forecast that
#   sums the six would systematically under-predict recent seasons for exactly
#   the players who carry the money, which is the tilt the rebuild exists to
#   remove. (2) Rescaling the six to hit the total would spread an unknown
#   quantity across six known ones in proportion to them, asserting something
#   about its nature that no evidence supports. (3) Named and carried, it gets
#   its own persistence estimate in the harness, so the data says how much of
#   it is signal instead of a convention deciding.
UNALLOCATED = "UNAL WAR"
COMPONENTS_MODEL = COMPONENTS + [UNALLOCATED]

# The season from which the residual appears. Before this the identity holds.
UNALLOCATED_FIRST_SEASON = 2023

MIN_GP = 10           # a season needs this many games to count as a signal
PAIR_MIN_GP = 20      # the aging curve's own filter, for persistence pairs

# WAR.csv coverage. Experience counted from this table is LEFT-CENSORED at
# the first year: a player whose first row is 2007 may have debuted earlier,
# so his experience is a lower bound and every model that uses experience
# must carry the censor flag the season table emits.
FIRST_SOURCE_SEASON = 2007
LAST_SOURCE_SEASON = 2025

# DECISION D (holdout policy), rebuild plan section 2. Development pages are
# the only pages any candidate may be scored on while it is being chosen.
# The confirmatory pages are touched ONCE, at the end of Phase 5. The split
# is enforced in code by forecast_harness.py, not by discipline.
DEV_PAGES = tuple(range(2015, 2022))          # 2015-2021 valuation seasons
CONFIRMATORY_PAGES = tuple(range(2022, 2026))  # 2022-2025, sealed


class ConfirmatorySealBroken(RuntimeError):
    """Raised when code asks the harness to score a sealed page without the
    explicit, logged unseal. Phase 5 is the only caller that may unseal."""


def out_path(name: str) -> Path:
    """The only sanctioned way to name an output file.

    Refuses anything that would land outside 50_REBUILD/output/ -- an
    absolute path, a parent-directory escape, or a name that resolves into
    the production tree. This is the isolation guarantee in executable form:
    a rebuild script physically cannot overwrite a production artifact
    through this function, and no rebuild script writes any other way.
    """
    p = (OUT_DIR / name).resolve()
    if not str(p).startswith(str(OUT_DIR.resolve()) + os.sep):
        raise ValueError(
            f"refusing to write outside the rebuild output tree: {p}. "
            "The rebuild is experimental and never writes to 30_OUTPUT, "
            "20_CODE or 10_SOURCE.")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def assert_read_only_source(path: Path) -> Path:
    """Sanity check before reading a vendor input: it must exist and it must
    live under SOURCE_DIR. Catches a mis-set .env pointing the rebuild at a
    generated file, which is how a look-ahead leak gets in unnoticed."""
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(
            f"{p} not found. Vendor inputs live in {SOURCE_DIR}; copy .env.example "
            "to .env if this machine keeps them elsewhere.")
    if not str(p).startswith(str(SOURCE_DIR.resolve())):
        raise ValueError(f"{p} is not under SOURCE_DIR ({SOURCE_DIR})")
    return p


def file_hash(path: Path) -> str:
    """SHA-256, first 16 hex chars. PROJECT_STATE's rule: file size is not an
    integrity check (two draft_yield_curve.csv builds were both 845 bytes
    with different contents). Every run log records input hashes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


_LOG: list[str] = []


def log(msg: str = "") -> None:
    print(msg)
    _LOG.append(str(msg))


def banner(script: str, version: str) -> None:
    log("=" * 74)
    log(f" {script}  v{version}   [EXPERIMENTAL -- 50_REBUILD, not production]")
    log(f" run {time.strftime('%Y-%m-%d %H:%M:%S')}   python {sys.version.split()[0]}")
    log("=" * 74)


def write_log(name: str) -> Path:
    p = out_path(name)
    p.write_text("\n".join(_LOG) + "\n", encoding="utf-8")
    return p
