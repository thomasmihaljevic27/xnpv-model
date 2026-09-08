"""
term_premium_test.py  --  Review item 2.1, the term premium test.
=================================================================
SCRIPT VERSION: v1.0 (2026-07-27)

WHAT THIS SCRIPT ANSWERS
------------------------
The locked price equation explains a contract's annual cap hit with trailing
production and nothing else. Adding contract length to it moves the price of a
win from $1.84M to $0.99M and lifts explained variation from 46.5% to 72.7%.
Two readings of that are possible:

  (1) term has a genuine market price, so the VALUE side of the model should
      carry it, and today's big negative NPVs on long deals are an artifact; or
  (2) the length coefficient is absorbing private team information about future
      production, so those negative NPVs are a real finding.

This script estimates the SHARE attributable to reading (2), by asking whether
contract length predicts REALIZED production once the trailing anchor is
already controlled for. Realized production is measured with the Game Value
metric, which contains no Bacon input, so the outcome side is independent of
the vendor that produced the projection being tested.

The design was pre-specified and signed off BEFORE this script was written:
see `term_premium_test_specification_v1.md`. Nothing here may drift from that
document. Where the specification fixed a number, that number is hard-coded
below and asserted rather than recomputed loosely.

HOW IT RUNS
-----------
    python term_premium_test.py                 (full run)
    python term_premium_test.py --sample-only   (stages 0-1 only, no database)
    python term_premium_test.py --schema        (print DB schema and exit)

`--sample-only` builds and guards the contract sample without touching the
game-log database. Use it first: if the sample guards fail, nothing downstream
is trustworthy and there is no point opening the database.

The script is deterministic and idempotent. Output files are overwritten in
full on each run; no state is carried between runs.

INPUTS
------
  PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx
  WAR.csv                     (Bacon skater WAR; the trailing anchor only)
  nhl_gamelogs.sqlite         (canonical copy: Desktop\\test, the only copy
                               holding `gv_adjusted`)

OUTPUTS
-------
  term_premium_test_sample.csv     one row per contract, with the premium,
                                   realized production, and each flag
  term_premium_test_results.csv    every coefficient, interval, and share,
                                   main specification and each robustness leg
  term_premium_test_diagnostics.csv join rate, zero-season counts by length
  term_premium_test_runlog.txt     full console transcript
"""

import argparse
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from dotenv import load_dotenv

load_dotenv()

SCRIPT_VERSION = "v1.0 (2026-07-27)"

# ===========================================================================
# CONFIG
# ===========================================================================
# Split source (vendor inputs, read-only) from output (generated files).
# Both come from .env (see .env.example).
SOURCE_DIR = Path(os.environ["SOURCE_DIR"])
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])

F_CONTRACT_XLSX = Path(os.environ["PUCKPEDIA_CONTRACTS_XLSX"])
F_WAR_SKATERS   = SOURCE_DIR / "WAR.csv"

# CANONICAL game-log database (PROJECT_STATE v2.3): the copy holding
# `gv_adjusted` and `player_game_value_repl`. Set GAMELOG_DB in .env to that
# copy -- the superseded `new_scrape` output must not be used here.
DB_PATH = Path(os.environ["GAMELOG_DB"])

OUT_SAMPLE = OUTPUT_DIR / "term_premium_test_sample.csv"
OUT_RESULT = OUTPUT_DIR / "term_premium_test_results.csv"
OUT_DIAG   = OUTPUT_DIR / "term_premium_test_diagnostics.csv"
OUT_LOG    = OUTPUT_DIR / "term_premium_test_runlog.txt"

# ===========================================================================
# LOCKED CONSTANTS -- fixed by the signed specification. Do not edit these
# without recording a deviation in the specification document.
# ===========================================================================
# Salary cap ceilings by season start year (NHL/NHLPA published).
CAP_CEILING = {
    2015: 71.4e6, 2016: 73.0e6, 2017: 75.0e6, 2018: 79.5e6, 2019: 81.5e6,
    2020: 81.5e6, 2021: 81.5e6, 2022: 82.5e6, 2023: 83.5e6, 2024: 88.0e6,
    2025: 95.5e6,
}

# D20 schedule proration. WAR and Game Value are both season TOTALS, so the
# two shortened seasons mechanically deflate anything drawn from them. The
# same factors are applied to the anchor (input side) and to realized Game
# Value (outcome side), which the specification requires.
PRORATION = {2019: 82 / 70, 2020: 82 / 56}

MIN_GP = 10            # a prior season needs >=10 GP to count toward the anchor
W_T1, W_T2 = 0.6, 0.4  # locked 60/40 trailing weighting

# Goals per win, recovered from the team-season regression inside the
# game-level model itself (metric_validation.csv). Used ONLY to convert the
# Game Value outcome from goals into wins. No dollars touch the outcome side.
GOALS_PER_WIN = 5.903

# The price equation, estimated once on the full locked sample (n=2,349) and
# NOT re-fitted on the subsample. Values below were derived and independently
# reproduced on 2026-07-27 and are asserted at run time, so a silent change
# anywhere upstream halts the script instead of quietly moving the answer.
PRICE_EQ_LOCKED = dict(
    n=2349,
    alpha=0.00272035,      # intercept, cap share
    b_war=0.01040552,      # cap share per win,      = $0.9937M at the 25-26 cap
    c_len=0.00859642,      # cap share per year term, = $0.8210M at the 25-26 cap
    r2=0.727279,   # reproduced 2026-07-27; the specification quotes it as 72.7%
)
TOL_COEF = 5e-5
TOL_N    = 5

# Mean contract length in the locked sample. The term premium is expressed
# relative to this, so a contract of average length carries a premium of zero.
MEAN_LENGTH_LOCKED = 2.3057
TOL_MEAN_LENGTH = 5e-4

# The pre-specified estimation window. K=3 is the main specification; 2 and 4
# are robustness legs. LAST_OBS_SEASON is the last season start year present
# in the game-log store, which is what makes K seasons observable.
K_MAIN = 3
K_LEGS = (2, 4)
LAST_OBS_SEASON = 2025
FIRST_SIGNING_YEAR = 2018

# Expected sample sizes at each horizon, from the pre-flight run. Asserted so
# that any upstream data change is visible immediately.
EXPECTED_N = {2: 2070, 3: 1781, 4: 1505}

# Phase 4b achieved an 88% join between the contract spine and the Game Value
# tables. The specification halts the reading rule if the rate falls
# materially below that, because the identifier match would then be
# reintroducing selection.
JOIN_RATE_FLOOR = 0.80

# Names known to be two different humans merged under one row-name in WAR.csv.
MERGED_WAR_NAMES = {"ryan johnson", "nathan smith"}
# Spine-side alias: the NYI defenceman is "Sebastian Aho Swe" in WAR.csv.
NAME_ALIASES = {("sebastian aho", "D"): "sebastian aho swe"}

POSGRP = {"Center": "F", "Left Wing": "F", "Right Wing": "F",
          "Defense": "D", "Goaltender": "G"}

# ===========================================================================
# LOGGING
# ===========================================================================
LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))

def die(msg):
    """Halt loudly. Every failure in this script is a halt, never a warning
    that lets a bad number reach the results file."""
    log("\n" + "!" * 74)
    log("HALTED: " + msg)
    log("!" * 74)
    _flush_log()
    sys.exit(1)

def _flush_log():
    try:
        OUT_LOG.write_text("\n".join(LOG), encoding="utf-8")
    except Exception as e:
        print(f"(could not write log: {e})")

# ===========================================================================
# NAME NORMALIZATION -- identical rules to age_join.py and
# skater_value_engine.py, so that every pipeline matches names the same way.
# ===========================================================================
_VARIANTS = {
    "alexander": "alex", "alexandre": "alex", "nicholas": "nick",
    "michael": "mike", "matthew": "matt", "christopher": "chris",
    "maxime": "max", "zachary": "zach", "joshua": "josh", "samuel": "sam",
    "benjamin": "ben", "daniel": "dan", "jonathan": "jon",
    "steven": "steve", "gregory": "greg", "patrick": "pat",
}

def norm_name(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().replace("-", " ")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[.'\u2019]", "", s)
    s = re.sub(r"\b(jr|sr|iii|ii|iv)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split()
    if parts:
        parts[0] = _VARIANTS.get(parts[0], parts[0])
    return " ".join(parts)

# ===========================================================================
# THE TRAILING ANCHOR
# ===========================================================================
def build_skater_war_lookup(exclude_merged=False):
    """One entry per (normalized name + position group, season start year) ->
    prorated season-total WAR, for seasons of at least MIN_GP games.

    IMPORTANT -- this mirrors `skater_value_engine.py` line 311, which is the
    call that estimates the locked price equation:

        lut_p = build_skater_war_lookup(exclude_merged=False, prorate=True)

    The rate stage of the locked engine does NOT drop merged names and does
    NOT apply the Sebastian Aho alias; both enter later, at the valuation
    stage. Applying them here instead would move the price coefficients away
    from the locked values, which is a silent change to the premium this whole
    test is built on. The affected contracts are therefore FLAGGED in the
    output rather than corrected, and the flag columns make the count visible.
    """
    war = pd.read_csv(F_WAR_SKATERS)
    war["syr"] = war["Season"].str.split("-").str[0].astype(int) + 2000
    war["WAR"] = war["WAR"] * war["syr"].map(PRORATION).fillna(1.0)
    war["nk"] = war["Player"].map(norm_name) + "|" + war["Position"]
    q = war[war["GP"] >= MIN_GP].copy()
    if exclude_merged:
        bare = q["Player"].map(norm_name)
        q = q[~bare.isin(MERGED_WAR_NAMES)]
    q = q.drop_duplicates(["nk", "syr"])
    return q.set_index(["nk", "syr"])["WAR"].sort_index()

def trailing_weighted_war(key, start_yr, lut):
    """The locked trailing rule: 60% of season t-1 plus 40% of season t-2. If
    only one of the two exists, use it alone; if neither, return NaN. Season t
    itself is never read, which is the model's look-ahead defence."""
    def get(k):
        v = lut.get(k, np.nan)
        return np.nan if isinstance(v, pd.Series) else v   # duplicate-key guard
    if pd.isna(start_yr):
        return np.nan
    w1 = get((key, int(start_yr) - 1))
    w2 = get((key, int(start_yr) - 2))
    if pd.notna(w1) and pd.notna(w2):
        return W_T1 * w1 + W_T2 * w2
    if pd.notna(w1):
        return w1
    if pd.notna(w2):
        return w2
    return np.nan

# ===========================================================================
# STAGE 1 -- build and guard the contract sample
# ===========================================================================
def stage1_sample():
    """Rebuild the locked estimation sample, re-fit the price equation on it,
    assert both against the specification, and return the K-horizon subsample.

    Everything here is reproduction, not new estimation. If any assert in this
    stage fires, an input has moved and no downstream number is meaningful."""
    log("=" * 74)
    log("STAGE 1: contract sample and the locked price equation")
    log("=" * 74)

    if not F_CONTRACT_XLSX.exists():
        die(f"contract export not found at {F_CONTRACT_XLSX}")
    if not F_WAR_SKATERS.exists():
        die(f"WAR.csv not found at {F_WAR_SKATERS}")

    raw = pd.read_excel(F_CONTRACT_XLSX)

    # True first season. The export's own `season` field is unreliable for
    # active multi-year deals (it stores the LAST season for those), so the
    # locked fix is end year minus length plus one.
    raw["end_yr"] = pd.to_numeric(
        raw["contract_end"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")
    raw["start_yr"] = raw["end_yr"] - raw["length"] + 1
    raw["posgrp"] = raw["position"].map(POSGRP)

    # Name key for the WAR join. No alias is applied, matching the locked
    # rate stage; the two known identity problems are flagged instead.
    base = (raw["first_name"].astype(str) + " " + raw["last_name"].astype(str)).map(norm_name)
    raw["nname"] = base
    raw["nk"] = base + "|" + raw["posgrp"].astype(str)
    raw["merged_name_flag"] = base.isin(MERGED_WAR_NAMES)
    raw["alias_case_flag"] = [(n, p) in NAME_ALIASES
                             for n, p in zip(base, raw["posgrp"].astype(str))]

    raw["cap_pct"] = raw["aav"] / raw["start_yr"].map(CAP_CEILING)

    lut = build_skater_war_lookup()
    raw["wWAR"] = [trailing_weighted_war(k, y, lut)
                   for k, y in zip(raw["nk"], raw["start_yr"])]

    ss = raw["signing_status"].astype(str)
    eligible = (raw["contract_level"] == "standard_level") & ss.isin(["UFA", "RFA"]) \
               & (raw["posgrp"] != "G") & raw["cap_pct"].notna()

    # ---- the FULL locked sample: 2018-2025 starts, anchor present ---------
    locked = raw[eligible & raw["start_yr"].between(2018, 2025) & raw["wWAR"].notna()].copy()
    log(f"  full locked sample: n={len(locked)} (specification: {PRICE_EQ_LOCKED['n']})")
    if abs(len(locked) - PRICE_EQ_LOCKED["n"]) > TOL_N:
        die(f"locked sample size moved: {len(locked)} vs {PRICE_EQ_LOCKED['n']}. "
            "An input has changed. Do not use this run.")

    # Re-fit the two-variable price equation on that sample and assert it.
    X = sm.add_constant(locked[["wWAR", "length"]].astype(float))
    pr = sm.OLS(locked["cap_pct"], X).fit(cov_type="HC3")
    a_hat, b_hat, c_hat = pr.params["const"], pr.params["wWAR"], pr.params["length"]
    cap25 = CAP_CEILING[2025]
    log(f"  price equation  R2={pr.rsquared:.6f} (spec {PRICE_EQ_LOCKED['r2']:.6f})")
    log(f"    intercept  {a_hat:.8f}  (spec {PRICE_EQ_LOCKED['alpha']:.8f})")
    log(f"    per win    {b_hat:.8f}  = ${b_hat*cap25/1e6:.4f}M   "
        f"(spec {PRICE_EQ_LOCKED['b_war']:.8f})")
    log(f"    per year   {c_hat:.8f}  = ${c_hat*cap25/1e6:.4f}M   t={pr.tvalues['length']:.1f}  "
        f"(spec {PRICE_EQ_LOCKED['c_len']:.8f})")
    for nm, got, want in (("intercept", a_hat, PRICE_EQ_LOCKED["alpha"]),
                          ("per win", b_hat, PRICE_EQ_LOCKED["b_war"]),
                          ("per year of term", c_hat, PRICE_EQ_LOCKED["c_len"])):
        if abs(got - want) > TOL_COEF:
            die(f"price equation {nm} moved: {got:.8f} vs specification {want:.8f}.")

    mean_len = locked["length"].astype(float).mean()
    log(f"  mean length {mean_len:.4f} (spec {MEAN_LENGTH_LOCKED})")
    if abs(mean_len - MEAN_LENGTH_LOCKED) > TOL_MEAN_LENGTH:
        die(f"mean contract length moved: {mean_len:.4f} vs {MEAN_LENGTH_LOCKED}.")

    # The share conversion factor, b/c. The cap ceiling cancels, so this is
    # identical whether computed in cap share or in dollars.
    share_factor = PRICE_EQ_LOCKED["b_war"] / PRICE_EQ_LOCKED["c_len"]
    log(f"  share conversion  s = {share_factor:.4f} x f")
    log(f"    s=1.00 requires f={1/share_factor:.4f} wins/season/year of term "
        f"({(1/share_factor)*(8-MEAN_LENGTH_LOCKED):.2f} wins/season on an 8-year deal)")
    log(f"    s=0.25 requires f={0.25/share_factor:.4f} "
        f"({(0.25/share_factor)*(8-MEAN_LENGTH_LOCKED):.2f} wins/season on an 8-year deal)")

    # ---- selection accounting: who is dropped for want of an anchor ------
    window = raw[eligible & raw["start_yr"].between(FIRST_SIGNING_YEAR,
                                                    LAST_OBS_SEASON - K_MAIN + 1)]
    na = window[window["wWAR"].isna()]
    log(f"\n  anchor availability, {FIRST_SIGNING_YEAR}-{LAST_OBS_SEASON-K_MAIN+1} signings:")
    log(f"    eligible {len(window)}, anchored {window['wWAR'].notna().sum()}, "
        f"dropped {len(na)} ({len(na)/max(len(window),1)*100:.1f}%)")
    if len(na):
        log(f"    dropped group: mean length {na['length'].mean():.3f}, "
            f"mean AAV ${na['aav'].mean()/1e6:.2f}M, "
            f"contracts of 6+ years {int((na['length'] >= 6).sum())}")
        # The specification rests on the dropped group carrying no long terms.
        # If that stops being true, the selection argument needs rewriting.
        if (na["length"] >= 6).sum() > 0:
            log("    NOTE: the dropped group now contains contracts of 6+ years. "
                "The specification's selection argument (Section 7) assumed none. "
                "Report this before citing the selection check.")

    # ---- the K-horizon estimation samples --------------------------------
    samples = {}
    for K in (K_MAIN, *K_LEGS):
        s = locked[locked["start_yr"] <= LAST_OBS_SEASON - K + 1].copy()
        s["K"] = K
        samples[K] = s
        exp = EXPECTED_N.get(K)
        flag = ""
        if exp is not None and abs(len(s) - exp) > TOL_N:
            flag = f"  <-- EXPECTED {exp}"
        log(f"  K={K} sample: n={len(s)}  starts "
            f"{int(s['start_yr'].min())}-{int(s['start_yr'].max())}  "
            f"mean length {s['length'].mean():.3f}  sd {s['length'].std():.3f}{flag}")
        if exp is not None and abs(len(s) - exp) > TOL_N:
            die(f"K={K} sample size moved: {len(s)} vs expected {exp}.")

    main = samples[K_MAIN]
    log(f"\n  K={K_MAIN} composition: forwards {(main.posgrp=='F').sum()}, "
        f"defencemen {(main.posgrp=='D').sum()}, "
        f"RFA {(main.signing_status=='RFA').sum()}, "
        f"UFA {(main.signing_status=='UFA').sum()}")
    by_len = main["length"].value_counts().sort_index()
    log("  by length: " + ", ".join(f"{int(L)}yr:{int(n)}" for L, n in by_len.items()))

    dup = int(main["contract_id"].duplicated().sum())
    log(f"  duplicate contract_id rows in the K={K_MAIN} sample: {dup}")

    # Known identity problems, carried as flags because the locked rate stage
    # does not correct them. These rows have a polluted or missing anchor.
    log(f"  merged-name contracts (anchor may be another player's): "
        f"{int(main['merged_name_flag'].sum())}")
    log(f"  alias cases (Sebastian Aho, D): {int(main['alias_case_flag'].sum())}")

    # nhl_id is the join key to the Game Value tables. Report coverage now,
    # because a gap here becomes a join failure two stages later.
    miss_id = int(main["nhl_id"].isna().sum())
    log(f"  contracts with no nhl_id: {miss_id} "
        f"({miss_id/max(len(main),1)*100:.1f}%)")

    # Attach the term premium. This is a pure linear transformation of length,
    # centred so that an average-length contract carries zero premium.
    for K, s in samples.items():
        s["term_premium_cap_pct"] = PRICE_EQ_LOCKED["c_len"] * (
            s["length"].astype(float) - MEAN_LENGTH_LOCKED)
        s["term_premium_dollars"] = s["term_premium_cap_pct"] * cap25

    log("  Stage 1 PASSED.\n")
    return samples, share_factor

# ===========================================================================
# STAGE 2 -- the Game Value outcome
# ===========================================================================
# `gv_adjusted` was built after the scripts held in the project folder, so its
# exact column names are not known to this script in advance. Rather than
# guessing and silently picking up the wrong column, stage 2 discovers the
# schema, matches it against candidate names, and halts with the actual schema
# printed if it cannot find what it needs.
CANDIDATE_TABLES = ["gv_adjusted", "player_game_value_adj", "gv_adj",
                    "player_season_gv_adjusted"]
CANDIDATE_VALUE_COLS = ["gv_adj", "gv_adjusted", "game_value_adj", "value_adj",
                        "gv", "game_value", "adj_value"]
CANDIDATE_PLAYER_COLS = ["player_id", "nhl_id", "playerId"]
CANDIDATE_SEASON_COLS = ["season", "season_start", "season_id", "syr"]

def parse_season(v):
    """Return the season START year from whatever format the store uses.
    Handles 20192020, '2019-20', '2019-2020', and a bare 2019."""
    s = str(v).strip()
    if re.fullmatch(r"\d{8}", s):
        return int(s[:4])
    m = re.match(r"^(\d{4})\s*[-/]\s*\d{2,4}$", s)
    if m:
        return int(m.group(1))
    if re.fullmatch(r"\d{4}", s):
        return int(s)
    return np.nan

def print_schema(conn):
    tabs = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    log(f"  tables in the database ({len(tabs)}):")
    for t in tabs:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info('{t}')")]
        log(f"    {t}: {', '.join(cols)}")
    return tabs

def stage2_outcome():
    """Pull GV-adj, aggregate to one row per player-season in WIN units, and
    apply the D20 proration. No dollar figure touches this stage."""
    log("=" * 74)
    log("STAGE 2: Game Value outcome (GV-adj), win units")
    log("=" * 74)
    if not DB_PATH.exists():
        die(f"game-log database not found at:\n  {DB_PATH}\n"
            "Set GAMELOG_DB in .env (see .env.example) to the canonical copy "
            "that holds gv_adjusted; the superseded new_scrape output does "
            "not hold it.")
    conn = sqlite3.connect(DB_PATH)
    tabs = print_schema(conn)

    tbl = next((t for t in CANDIDATE_TABLES if t in tabs), None)
    if tbl is None:
        die("could not find the GV-adj table. Candidates tried: "
            f"{CANDIDATE_TABLES}. The schema above lists what is actually "
            "present; add the correct name to CANDIDATE_TABLES and re-run.")
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info('{tbl}')")]
    log(f"\n  using table `{tbl}` with columns: {', '.join(cols)}")

    def pick(cands, what):
        hit = next((c for c in cands if c in cols), None)
        if hit is None:
            die(f"no {what} column found in `{tbl}`. Tried {cands}; the table "
                f"has {cols}. Add the correct name to the CANDIDATE_* list.")
        return hit

    c_val = pick(CANDIDATE_VALUE_COLS, "value")
    c_pid = pick(CANDIDATE_PLAYER_COLS, "player identifier")
    c_szn = pick(CANDIDATE_SEASON_COLS, "season")
    log(f"  value={c_val}  player={c_pid}  season={c_szn}")

    gv = pd.read_sql(f"SELECT * FROM `{tbl}`", conn)
    conn.close()
    log(f"  rows read: {len(gv):,}")

    # Regular season only, matching the Phase 4b robustness convention. If the
    # table carries no game_type, it is already season-level or already
    # filtered; say which rather than assuming silently.
    if "game_type" in cols:
        before = len(gv)
        gv = gv[pd.to_numeric(gv["game_type"], errors="coerce") == 2]
        log(f"  regular season filter (game_type=2): {before:,} -> {len(gv):,}")
    else:
        log("  no game_type column present; treating the table as already "
            "regular-season or season-level. VERIFY this before citing.")

    gv["season_start"] = gv[c_szn].map(parse_season)
    if gv["season_start"].isna().any():
        die(f"could not parse {int(gv['season_start'].isna().sum())} season "
            f"values from column `{c_szn}`. Sample: "
            f"{gv.loc[gv['season_start'].isna(), c_szn].head(5).tolist()}")

    gv["player_id"] = pd.to_numeric(gv[c_pid], errors="coerce")
    gv["value_goals"] = pd.to_numeric(gv[c_val], errors="coerce")
    if gv["value_goals"].isna().any():
        log(f"  WARNING: {int(gv['value_goals'].isna().sum())} non-numeric "
            f"values in `{c_val}`, treated as zero.")
        gv["value_goals"] = gv["value_goals"].fillna(0.0)

    # Aggregate to player-season. Whether the source is per game or already
    # per season, summing within (player, season) gives the season total; a
    # season-level source simply sums one row.
    ps = gv.groupby(["player_id", "season_start"], as_index=False)["value_goals"].sum()
    rows_per = len(gv) / max(len(ps), 1)
    log(f"  player-seasons: {len(ps):,}  (mean {rows_per:.1f} source rows each "
        f"-- near 1.0 means the source was already season-level)")

    # D20 proration, then goals to wins.
    ps["prorate"] = ps["season_start"].map(PRORATION).fillna(1.0)
    ps["realized_wins"] = ps["value_goals"] * ps["prorate"] / GOALS_PER_WIN

    log(f"  seasons covered: {int(ps['season_start'].min())}-"
        f"{int(ps['season_start'].max())}")
    log(f"  realized wins: mean {ps['realized_wins'].mean():+.3f}, "
        f"sd {ps['realized_wins'].std():.3f}, "
        f"min {ps['realized_wins'].min():+.3f}, max {ps['realized_wins'].max():+.3f}")
    # Sanity band. GV-adj is a differential metric, so a per-player-season
    # figure far outside roughly -5 to +10 wins would mean the wrong column
    # or a missing conversion.
    if ps["realized_wins"].abs().max() > 25:
        log("  WARNING: at least one player-season exceeds 25 wins in absolute "
            "value. Check that `" + c_val + "` is in GOALS, not already wins, "
            "and that GOALS_PER_WIN is the right divisor.")

    # Coverage needed for the main specification, so a thin tail season is
    # visible before it silently becomes a zero.
    per_season = ps.groupby("season_start").size()
    log("  player-seasons by season: " +
        ", ".join(f"{int(y)}:{int(n)}" for y, n in per_season.items()))

    log("  Stage 2 done.\n")
    return ps[["player_id", "season_start", "realized_wins"]]

# ===========================================================================
# STAGE 3 -- join, build the realized average, and diagnose the zeros
# ===========================================================================
def stage3_join(sample, gv_ps, K):
    """Attach realized production to each contract.

    Two conventions from the specification are implemented here and matter a
    great deal to the result:

      1. The window is a FIXED K seasons after signing, whether or not the
         contract is still in force. Measuring over the life of the contract
         would select on length, which is the variable under test.
      2. A season in which the player played no National Hockey League games
         contributes ZERO, not a missing value. Dropping those observations
         would select on survival, which is the direction that flatters the
         private-information reading."""
    log("-" * 74)
    log(f"STAGE 3: join and realized production, K={K}")
    log("-" * 74)

    s = sample.copy()
    s["nhl_id"] = pd.to_numeric(s["nhl_id"], errors="coerce")

    # Tripwire from Phase 4b: the Game Value tables key on NHL identifiers,
    # NOT PuckPedia ones. A zero overlap means the wrong key is in use.
    overlap = set(s["nhl_id"].dropna()) & set(gv_ps["player_id"].dropna())
    log(f"  identifier overlap: {len(overlap)} distinct players")
    if len(overlap) == 0:
        die("zero identifier overlap between the contract sample and the Game "
            "Value tables. The Game Value store keys on NHL player ids; check "
            "that nhl_id is populated and that the GV player column is the NHL "
            "id rather than a PuckPedia id.")

    gv_lut = gv_ps.set_index(["player_id", "season_start"])["realized_wins"]

    realized, n_zero, n_obs = [], [], []
    for pid, y0 in zip(s["nhl_id"], s["start_yr"]):
        vals = []
        for k in range(K):
            yr = int(y0) + k
            v = gv_lut.get((pid, yr), np.nan)
            if isinstance(v, pd.Series):      # duplicate-key guard
                v = float(v.sum())
            vals.append(0.0 if pd.isna(v) else float(v))
        realized.append(np.mean(vals))
        n_zero.append(sum(1 for v in vals if v == 0.0))
        n_obs.append(sum(1 for v in vals if v != 0.0))
    s["realized_wins_avg"] = realized
    s["n_zero_seasons"] = n_zero
    s["n_played_seasons"] = n_obs

    # Join rate: contracts with at least one observed season. A contract of
    # all zeros is either a genuine departure or a failed identifier match,
    # and the two cannot be told apart from inside this script, which is
    # exactly why the rate is reported and floored.
    joined = (s["n_played_seasons"] > 0).mean()
    log(f"  contracts with at least one observed season: "
        f"{int((s['n_played_seasons']>0).sum())}/{len(s)} ({joined*100:.1f}%)")
    log(f"    Phase 4b achieved 88%; the specification floors this at "
        f"{JOIN_RATE_FLOOR*100:.0f}%")
    if joined < JOIN_RATE_FLOOR:
        die(f"join rate {joined*100:.1f}% is below the pre-specified floor of "
            f"{JOIN_RATE_FLOOR*100:.0f}%. The identifier match would be "
            "reintroducing selection. Fix the join before reading any result.")

    # The zero-season diagnostic. The specification halts the reading rule if
    # zero seasons rise steeply with contract length, because the zero-coding
    # convention would then be load-bearing rather than conservative.
    diag = s.groupby("length").agg(
        n=("length", "size"),
        zero_share=("n_zero_seasons", lambda x: x.sum() / (len(x) * K)),
        all_zero=("n_played_seasons", lambda x: int((x == 0).sum())))
    log("  zero-season diagnostic by contract length:")
    for L, row in diag.iterrows():
        log(f"    {int(L)}yr  n={int(row['n']):>4}  share of seasons at zero="
            f"{row['zero_share']*100:5.1f}%  contracts with no observed season="
            f"{int(row['all_zero'])}")
    corr_zero = s["length"].astype(float).corr(s["n_zero_seasons"].astype(float))
    log(f"  corr(length, count of zero seasons) = {corr_zero:+.3f}")
    if corr_zero > 0.10:
        log("  WARNING: zero seasons rise with contract length. Under the "
            "specification the zero-coding convention is load-bearing here, "
            "so the drop-zeros leg must be reported alongside the main "
            "specification and the reading rule treated as provisional "
            "pending review.")
    diag = diag.reset_index()
    diag["K"] = K
    diag["corr_length_zeros"] = corr_zero
    diag["join_rate"] = joined
    return s, diag

# ===========================================================================
# STAGE 4 -- estimate
# ===========================================================================
def estimate(df, label, share_factor, drop_zeros=False):
    """Estimate the pre-specified equation and apply the reading rule.

        realized_wins_avg = d + e*anchor + f*(length - mean length)
                            + signing-year indicators + u

    Standard errors are clustered on player identity, because a player can
    sign more than once inside the window and his own observation windows
    then overlap.

    The coefficient f is extra realized wins per season per additional year of
    term, beyond what the trailing anchor already predicts. The share is
    s = (price per win / price per year of term) * f."""
    d = df.copy()
    if drop_zeros:
        d = d[d["n_played_seasons"] > 0]
    if len(d) < 100:
        log(f"  [{label}] SKIPPED: only {len(d)} observations.")
        return None

    d["len_c"] = d["length"].astype(float) - MEAN_LENGTH_LOCKED
    X = pd.DataFrame({"anchor": d["wWAR"].astype(float), "len_c": d["len_c"]},
                     index=d.index)
    # Signing-year indicators absorb league-wide differences in the level of
    # realized production across cohorts. The first year is the reference.
    yr = pd.get_dummies(d["start_yr"].astype(int), prefix="yr", drop_first=True)
    X = pd.concat([X, yr.astype(float)], axis=1)
    X = sm.add_constant(X)

    groups = d["nhl_id"].fillna(-1).astype(np.int64)
    res = sm.OLS(d["realized_wins_avg"].astype(float), X).fit(
        cov_type="cluster", cov_kwds={"groups": groups})

    f = res.params["len_c"]
    se = res.bse["len_c"]
    lo, hi = res.conf_int().loc["len_c"]
    s_hat, s_lo, s_hi = share_factor * f, share_factor * lo, share_factor * hi
    sig = not (lo <= 0 <= hi)

    # The reading rule, pre-committed. If the interval on f contains zero the
    # main share is set to zero and the upper bound is carried separately. The
    # value side carries max(s, 0); a negative estimate is reported as
    # estimated and is not truncated in the reported figure.
    s_applied = 0.0 if not sig else max(s_hat, 0.0)

    log(f"\n  [{label}]  n={int(res.nobs)}  clusters={groups.nunique()}  "
        f"R2={res.rsquared:.4f}")
    log(f"    anchor coefficient e = {res.params['anchor']:+.4f} "
        f"(t={res.tvalues['anchor']:+.2f})")
    log(f"    term coefficient  f = {f:+.4f} wins/season/year of term  "
        f"(se {se:.4f}, t={res.tvalues['len_c']:+.2f})")
    log(f"      95% interval on f: [{lo:+.4f}, {hi:+.4f}]  "
        f"{'excludes' if sig else 'CONTAINS'} zero")
    log(f"    share s = {s_hat:+.3f}   interval [{s_lo:+.3f}, {s_hi:+.3f}]")
    log(f"    share applied to the value side: {s_applied:.3f}   "
        f"(bounds: 0.000 = current model, 1.000 = fully term-aware)")
    log(f"    an 8-year contract implies {f*(8-MEAN_LENGTH_LOCKED):+.2f} extra "
        f"wins per season beyond its anchor")

    return dict(leg=label, n=int(res.nobs), clusters=int(groups.nunique()),
                r2=res.rsquared, e_anchor=res.params["anchor"],
                f=f, f_se=se, f_t=res.tvalues["len_c"], f_lo=lo, f_hi=hi,
                excludes_zero=sig, s=s_hat, s_lo=s_lo, s_hi=s_hi,
                s_applied=s_applied)

# ===========================================================================
# MAIN
# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-only", action="store_true",
                    help="build and guard the contract sample, then stop")
    ap.add_argument("--schema", action="store_true",
                    help="print the game-log database schema and stop")
    args = ap.parse_args()

    log(f"term_premium_test.py {SCRIPT_VERSION}")
    log(f"Review item 2.1. Design fixed by term_premium_test_specification_v1.md.")
    log(f"source dir: {SOURCE_DIR.resolve()}")
    log(f"output dir: {OUTPUT_DIR.resolve()}")
    log("")

    if args.schema:
        if not DB_PATH.exists():
            die(f"database not found at {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        print_schema(conn)
        conn.close()
        _flush_log()
        return

    samples, share_factor = stage1_sample()
    if args.sample_only:
        log("--sample-only: stopping before the database stages.")
        _flush_log()
        return

    gv_ps = stage2_outcome()

    log("=" * 74)
    log("STAGES 3-4: main specification and robustness legs")
    log("=" * 74)

    results, diags, joined = [], [], {}
    for K in (K_MAIN, *K_LEGS):
        s, dg = stage3_join(samples[K], gv_ps, K)
        joined[K] = s
        diags.append(dg)

    main_df = joined[K_MAIN]

    # --- main specification ------------------------------------------------
    r = estimate(main_df, f"MAIN  GV-adj, K={K_MAIN}", share_factor)
    if r:
        results.append(r)

    # --- pre-specified robustness legs ------------------------------------
    for K in K_LEGS:
        r = estimate(joined[K], f"horizon K={K}", share_factor)
        if r:
            results.append(r)

    for grp, name in (("F", "forwards"), ("D", "defencemen")):
        r = estimate(main_df[main_df["posgrp"] == grp], f"position: {name}",
                     share_factor)
        if r:
            results.append(r)

    for st in ("RFA", "UFA"):
        r = estimate(main_df[main_df["signing_status"] == st],
                     f"signing status: {st}", share_factor)
        if r:
            results.append(r)

    r = estimate(main_df, "zeros dropped (rejected alternative)", share_factor,
                 drop_zeros=True)
    if r:
        results.append(r)

    # NOTE: the GV-raw legs (rebased and zero-sum) are pre-specified but are
    # not wired here, because the raw tables live under different column names
    # in the same database and stage 2 resolves exactly one value column per
    # run. Re-run with CANDIDATE_TABLES and CANDIDATE_VALUE_COLS pointed at
    # the raw table to produce them, and record both runs together. This is a
    # deliberate limitation of v1.0, recorded rather than hidden.
    log("\n  GV-raw legs: not produced by this run. Re-run with "
        "CANDIDATE_TABLES/CANDIDATE_VALUE_COLS pointed at the raw Game Value "
        "table (rebased, then zero-sum) and file all three runs together.")

    # --- write outputs ----------------------------------------------------
    pd.DataFrame(results).to_csv(OUT_RESULT, index=False)
    pd.concat(diags, ignore_index=True).to_csv(OUT_DIAG, index=False)
    keep = ["contract_id", "player_id", "nhl_id", "first_name", "last_name",
            "posgrp", "signing_status", "start_yr", "length", "aav", "cap_pct",
            "wWAR", "term_premium_cap_pct", "term_premium_dollars",
            "realized_wins_avg", "n_zero_seasons", "n_played_seasons", "K"]
    main_df[[c for c in keep if c in main_df.columns]].to_csv(OUT_SAMPLE, index=False)

    log("\n" + "=" * 74)
    log("HEADLINE")
    log("=" * 74)
    if results:
        m = results[0]
        log(f"  f = {m['f']:+.4f} wins per season per year of term, "
            f"95% interval [{m['f_lo']:+.4f}, {m['f_hi']:+.4f}]")
        log(f"  share s = {m['s']:+.3f}, interval [{m['s_lo']:+.3f}, {m['s_hi']:+.3f}]")
        log(f"  share carried on the value side = {m['s_applied']:.3f}")
        log(f"  bounds: 0.000 is the current model, 1.000 is fully term-aware.")
        log("  f is measured with no Bacon input. The conversion to s multiplies "
            "by the Bacon-derived price of a win, so s inherits any error in "
            "that level and must be cited alongside f, never instead of it.")
    log(f"\n  wrote {OUT_RESULT.name}, {OUT_DIAG.name}, {OUT_SAMPLE.name}")
    _flush_log()
    log(f"  wrote {OUT_LOG.name}")

if __name__ == "__main__":
    main()
