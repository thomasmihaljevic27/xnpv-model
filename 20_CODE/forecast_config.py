"""forecast_config.py -- paths, constants and guard rails for the xNPV 1 skater forecast.

PRODUCTION (20_CODE). Promoted 2026-10-02 from 50_REBUILD/code/rebuild_config.py
(v1.6) when xNPV 1 became the player model (decision D33). The modules promoted
with it read their constants from here and nowhere else:
player_season_table, information_set, contract_source, participation_model,
forecast_harness and skater_forecast.

WHAT CHANGED FROM THE REBUILD COPY, and only this:
    * outputs go to OUTPUT_DIR (30_OUTPUT), the production output folder,
      instead of 50_REBUILD/output; out_path() refuses anything outside it;
    * the cap path, league-minimum and market-cohort helpers are left out:
      production prices with skater_forward_projection's own (Stage 3 rate,
      D10, D11), and the rebuild's market price line was not adopted;
    * the banner says production.
Every modelling constant below is the rebuild's value, unchanged, so the
promoted forecast reproduces the one D33 adopted (checked by
25_TESTS/xnpv1_promotion_check.py).

VERSIONING
    Every script prints SCRIPT_VERSION through banner(). Three stale-file
    incidents in this project were traced to a script that ran without anyone
    knowing which version ran.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

SCRIPT_VERSION = "1.0"

# --- Layout -----------------------------------------------------------------
CODE_DIR = Path(__file__).resolve().parent          # 20_CODE
REPO_ROOT = CODE_DIR.parent

try:  # .env is optional; the fallbacks below are the documented default
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

# Vendor inputs. Shared with production, READ ONLY from this tree.
#
# WHY THIS IS A FUNCTION AND NOT ONE LINE. The first version trusted
# os.environ["SOURCE_DIR"] outright. On a machine whose .env still carried the
# template's placeholder (XNPV_ROOT=C:/path/to/xnpv-model, which SOURCE_DIR
# expands through) that produced a path no file has ever lived at, and the
# first thing to touch it -- a hash, not a read -- died with a bare
# FileNotFoundError pointing at C:\path\to\xnpv-model. The env var is a hint
# about where the data might be, so it is CHECKED rather than believed, the
# repo layout is the fallback, and the run log says which one won. A config
# that cannot find its data should say what it tried.
def _resolve_source_dir() -> tuple[Path, str, list[str]]:
    tried: list[str] = []
    candidates = []
    env = os.environ.get("SOURCE_DIR")
    if env:
        candidates.append((Path(env), "SOURCE_DIR from the environment/.env"))
    candidates.append((REPO_ROOT / "10_SOURCE", "the repo layout"))
    for path, why in candidates:
        # WAR.csv is the sentinel: it is committed, so it is present in every
        # checkout, which makes it the one file whose absence means "this is
        # not the source directory" rather than "this machine lacks the
        # confidential extras".
        if (path / "WAR.csv").exists():
            return path, why, tried
        tried.append(f"{path}  ({why}) -- no WAR.csv here")
    return REPO_ROOT / "10_SOURCE", "the repo layout (nothing verified)", tried


SOURCE_DIR, SOURCE_DIR_WHY, SOURCE_DIR_TRIED = _resolve_source_dir()

# Outputs: production's own folder.
OUT_DIR = Path(os.environ.get("OUTPUT_DIR", REPO_ROOT / "30_OUTPUT"))
PROD_OUTPUT_DIR = OUT_DIR
PROD_CODE_DIR = CODE_DIR

F_WAR_SKATERS = SOURCE_DIR / "WAR.csv"
F_WAR_GOALIES = SOURCE_DIR / "Goalies_WAR.csv"

# The PuckPedia exports, as CSV. Confidential vendor data, gitignored by the
# repo-root hard deny on *CONFIDENTIAL*, never committed and never echoed row
# by row into a log. The project's canonical copies are .xlsx; these CSVs are
# the same export saved as text, which is what makes them readable outside a
# machine with Excel. Their encodings differ and are detected per file -- see
# contract_source.py -- because Excel wrote one as cp1252 and one as UTF-8.
F_CONTRACTS_CSV = SOURCE_DIR / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.csv"
F_TRADES_CSV = SOURCE_DIR / "PuckPedia_Trades_Contract_Export_May_22_2026__CONFIDENTIAL.csv"

# --- Shared modelling constants -------------------------------------------
# Copies of skater_value_engine's values (they were copied when the forecast
# was built separately, and stay copies so the forecast's inputs are named in
# one place). player_season_table.guard_against_production() asserts them
# equal to the engine's -- that assert, not this comment, keeps the two in step.

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

# THE HORIZONS EVERY FITTED MODEL ESTIMATES, named once so that the fitted
# range and the requested range cannot drift apart. The rebuild plan specified
# a harness over six forecast seasons and that is what is fitted here.
#
# A contract can run longer than this, and the market and named-player runners
# used to request horizons 6, 7 and 8 against models fitted only to 5. Nothing
# refused them: participation returned a flat 0.6 for every player and the
# rate and games fits returned the trailing value, so the tail of any long
# contract was priced on numbers no fit had produced. The guards now refuse
# those horizons. Covering real contract terms needs either fits extended to
# the horizons a contract actually reaches or a declared and tested
# extrapolation, which is a modelling decision and not this constant's job.
FITTED_HORIZONS = tuple(range(6))

# HOW FAR OUT A FIT MAY BE ATTEMPTED, and how much evidence a horizon needs
# before it counts as fitted.
#
# The six above is not arbitrary and it is not a free choice: it is what the
# EARLIEST development page can support. A training pair at horizon h needs an
# anchor at t0 and an outcome at t0+h completed before the valuation season, and
# the source starts in 2007, so at the 2015 page horizon 6 has 270 pairs and
# horizon 7 has none at all. At the 2021 page horizon 7 has 1,246 and the range
# reaches 11.
#
# A contract, meanwhile, does not care: an eight-year deal needs eight seasons
# priced wherever it was signed. So the fitted range is decided per page from
# the evidence actually available, rather than fixed at the worst page's answer
# and then quietly extrapolated past it. Beyond what a page supports the models
# refuse, which is the point: the alternative that was in place returned a flat
# 0.6 and the trailing rate.
#
# MIN_HORIZON_PAIRS is a judgement and worth revisiting. 200 league-wide pairs
# is thin for the tail of a long deal; it is set above the rate fit's own floor
# of 50 so that a horizon can be declared fitted only on more than the bare
# minimum that lets least squares return a number.
MAX_HORIZON = 12
CANDIDATE_HORIZONS = tuple(range(MAX_HORIZON + 1))
MIN_HORIZON_PAIRS = 200

MIN_GP = 10           # a season needs this many games to count as a signal

# THE PARTICIPATION EVENT, which is a different question from the one MIN_GP
# answers and had been sharing its number.
#
# MIN_GP asks whether a season carries enough evidence to be used as an INPUT.
# Ten games is a reasonable answer to that. The participation model asks a
# different question, whether the player is in the NHL at all in a future
# season, and the rebuild plan specified one or more games for it. Using ten
# for both made the two halves of the forecast condition on different events:
# participation predicted the odds of a ten-game season, while the rate and
# games targets were read from any season with a number in it, cameos
# included. The forecast is participation multiplied by production, so the two
# have to be the same event or the product is not an expectation of anything.
#
# Moving to one game brings 2,918 cameo seasons into the played state. They are
# 17.1% of season rows and -0.10% of total WAR, and their per-82 rates run from
# -8.4 to +41.5 because dividing by one to nine games and multiplying by 82
# amplifies noise by up to eighty times. That is why RATE_WEIGHT_BY_GAMES below
# exists: the conditioning is fixed by changing the event, and the noise the
# change admits is handled by weighting rather than by quietly excluding the
# seasons again.
PARTICIPATION_GP = 1

# MINIMUM AGE COVERAGE the season table will proceed on without being told to.
#
# The birthdate join reads PuckPedia plus an Elite Prospects file, and the
# Elite Prospects file is not in the repository. Without it coverage falls from
# 98.3% of season rows to 69.2%, and nothing fails: the aging model simply has
# far less to work with, so the rebuild's improvement over the benchmark at
# five seasons out reads 23.6% instead of 43.5%. A missing input that silently
# shrinks a headline result is worse than one that stops the run, because the
# shrunken number looks like a finding. The threshold sits below the known-good
# 98.3% and far above the degraded 69.2%.
MIN_AGE_COVERAGE = 0.95

# WEIGHT RATE OBSERVATIONS BY GAMES PLAYED. A per-82 rate computed from a
# handful of games is an estimate of the same quantity as a full season's rate,
# but a far noisier one: its sampling variance scales roughly as one over the
# games behind it, so games played IS the precision weight rather than a
# convenient way of down-weighting inconvenient rows. Without it a single
# one-game season carrying a rate of 41.5 sits in a least-squares fit with the
# same authority as a full season.
#
# DECISION OWED. This is the choice the review left open: weight the cameo
# seasons, or model short appearances as their own low-production state. The
# weighting is the smaller change and it keeps the plan's one-game event
# intact, so it is what ships here, and it is flagged rather than locked.
RATE_WEIGHT_BY_GAMES = True

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

# THE MARKET SIDE OF THE SAME RESERVATION, by contract start year. The page
# seal above covered forecast scoring only, so both market runners swept start
# years 2018 through 2025 on every development run and selected a price
# specification on cohorts the project was describing as untouched. Sealing the
# pages and not the cohorts is not a split sample.
#
# The boundary mirrors the forecast pages because that is the conservative
# reading, NOT because it has been decided: where the market holdout should sit
# is a decision owed, and until it is taken this constant is the proposal being
# enforced rather than a locked line.
CONFIRMATORY_START_YEARS = tuple(range(2022, 2026))

# THE INSPECTION LEDGER. Every evaluation that consumes a page or a cohort
# appends one line here, so what has been looked at is a record rather than a
# reconstruction from session logs after the fact.
#
# This is the one file written outside OUTPUT_DIR, and deliberately:
# an output regenerates and is gitignored, while the point of this file is that
# it accumulates and is committed. It is a record of what was done, not a model
# artifact, so out_path()'s rule does not apply to it and it gets its own
# writer below rather than a way around that rule.
# Where the ledger lives until the rebuild documents move (migration plan step 4).
INSPECTION_LEDGER = REPO_ROOT / "50_REBUILD" / "docs" / "inspection_ledger.csv"

def record_inspection(runner: str, kind: str, keys, reason: str = "") -> None:
    """Append one line recording what an evaluation just consumed.

    Never raises into the caller. A ledger that can break a run would get
    switched off the first time it did, and a record nobody keeps is worse
    than one that occasionally misses a line on a read-only checkout.
    """
    import csv
    try:
        keys = sorted(int(k) for k in keys)
        sealed = [k for k in keys
                  if k in CONFIRMATORY_PAGES or k in CONFIRMATORY_START_YEARS]
        new_file = not INSPECTION_LEDGER.exists()
        INSPECTION_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(INSPECTION_LEDGER, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new_file:
                w.writerow(["utc", "runner", "kind", "keys", "reserved_keys",
                            "reason"])
            w.writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        runner, kind,
                        " ".join(str(k) for k in keys),
                        " ".join(str(k) for k in sealed), reason])
    except Exception as e:                      # noqa: BLE001
        log(f"  [ledger] could not record this inspection ({e.__class__.__name__})")

class ConfirmatorySealBroken(RuntimeError):
    """Raised when code asks the harness to score a sealed page without the
    explicit, logged unseal. Phase 5 is the only caller that may unseal."""


def out_path(name: str) -> Path:
    """The only sanctioned way to name an output file.

    Refuses anything that would land outside OUTPUT_DIR (30_OUTPUT) -- an
    absolute path, a parent-directory escape, or a name that resolves into
    the code or source trees.
    """
    p = (OUT_DIR / name).resolve()
    if not str(p).startswith(str(OUT_DIR.resolve()) + os.sep):
        raise ValueError(
            f"refusing to write outside the production output folder: {p}. "
            "The forecast never writes to 20_CODE or 10_SOURCE.")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def assert_read_only_source(path: Path) -> Path:
    """Sanity check before reading a vendor input: it must exist and it must
    live under SOURCE_DIR. Catches a mis-set .env pointing the rebuild at a
    generated file, which is how a look-ahead leak gets in unnoticed."""
    p = Path(path).resolve()
    if not p.exists():
        lines = [f"{p} not found.",
                 f"SOURCE_DIR resolved to {SOURCE_DIR} via {SOURCE_DIR_WHY}."]
        if SOURCE_DIR_TRIED:
            lines.append("Already tried, and rejected:")
            lines += [f"  {t}" for t in SOURCE_DIR_TRIED]
        lines.append("Set SOURCE_DIR in .env to the folder holding WAR.csv, or run "
                     "from a checkout where 10_SOURCE/ is populated.")
        if "CONFIDENTIAL" in p.name:
            lines.append("This one is confidential vendor data and is not in the repo: "
                         "it has to be copied onto this machine by hand.")
        raise FileNotFoundError("\n".join(lines))
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
    log(f" {script}  v{version}   [production -- 20_CODE]")
    log(f" run {time.strftime('%Y-%m-%d %H:%M:%S')}   python {sys.version.split()[0]}")
    log(f" source {SOURCE_DIR}  (via {SOURCE_DIR_WHY})")
    for t in SOURCE_DIR_TRIED:
        log(f"   skipped {t}")
    log("=" * 74)


def write_log(name: str) -> Path:
    p = out_path(name)
    p.write_text("\n".join(_LOG) + "\n", encoding="utf-8")
    return p
