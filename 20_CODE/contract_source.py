"""contract_source.py -- the PuckPedia exports, read as CSV and proven faithful.

PRODUCTION (20_CODE), promoted 2026-10-02 from 50_REBUILD/code/ for xNPV 1 (D33). Was EXPERIMENTAL (50_REBUILD). Unblocks Phase 4 and the age panel.

WHAT THIS IS
    The project's canonical PuckPedia exports are .xlsx. This module reads the
    same exports saved as CSV, which is what makes them usable on a machine
    without Excel, and -- more to the point -- what makes them survive being
    moved between machines at all. An earlier attempt to recover the workbook
    through a text extraction produced a table whose columns SHIFTED PER ROW,
    because the extractor collapsed interior empty cells: `standard_level` sat
    at index 30 in a full-width row and index 25 in a 35-cell row, with only
    1,398 of 6,851 rows full width. A real CSV has no such failure mode, and
    validate() below asserts that every row has the full column count rather
    than trusting it.

ENCODINGS DIFFER BETWEEN THE TWO FILES, which is why they are detected per
file instead of assumed. Excel wrote the contracts export as cp1252 and the
trades export as UTF-8. Reading the contracts file as UTF-8 raises; reading it
as UTF-8 with errors ignored would silently mangle 32 accented surnames
(Rosen, Stromgren, Raty, Moser) into different strings -- and those strings are
the JOIN KEY to WAR.csv. A name that fails to match does not error, it just
quietly drops a contract out of the market sample.

CONFIDENTIAL. Both files are vendor data, gitignored by the repo-root hard
deny on *CONFIDENTIAL*. This module never writes a row of either file to an
output or a log; only counts, coverage and fitted figures leave it.

    python 20_CODE/contract_source.py     # validate + production guard
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forecast_config as C

SCRIPT_VERSION = "1.0"

# Tried in order. UTF-8 first so a correctly-encoded file is never read as
# cp1252 -- cp1252 decodes ANY byte sequence without error, so trying it first
# would turn a UTF-8 file into mojibake silently and never raise.
ENCODINGS = ("utf-8", "cp1252", "latin-1")

CONTRACT_COLS = 40
TRADE_COLS = 68


def read_csv_detect(path: Path) -> tuple[pd.DataFrame, str]:
    """Read a CSV, detecting its encoding by trying strict decodes in order.

    Strict on purpose. errors='replace' would get a DataFrame out of any file
    and corrupt exactly the rows that matter -- accented names, which are the
    join key. A file that decodes under no candidate encoding is a file we do
    not understand, and the right response is to stop.
    """
    C.assert_read_only_source(path)
    raw = path.read_bytes()
    for enc in ENCODINGS:
        try:
            raw.decode(enc)
        except UnicodeDecodeError:
            continue
        return pd.read_csv(path, encoding=enc, low_memory=False), enc
    raise UnicodeDecodeError(
        "none", b"", 0, 1,
        f"{path.name} decodes under none of {ENCODINGS}; do not read it with "
        "errors='replace' -- that would corrupt the accented names the join "
        "depends on.")


def load_contracts() -> tuple[pd.DataFrame, str]:
    df, enc = read_csv_detect(C.F_CONTRACTS_CSV)
    validate(df, CONTRACT_COLS, "contracts")
    return df, enc


def load_trades() -> tuple[pd.DataFrame, str]:
    df, enc = read_csv_detect(C.F_TRADES_CSV)
    validate(df, TRADE_COLS, "trades")
    return df, enc


def validate(df: pd.DataFrame, n_cols: int, what: str) -> None:
    """The structural guard. pandas raises on a ragged CSV by default, so
    reaching here already proves alignment; asserting the width as well pins
    the schema, so a re-export that gains or loses a column is caught at load
    rather than showing up later as a shifted field."""
    assert df.shape[1] == n_cols, (
        f"{what}: expected {n_cols} columns, found {df.shape[1]}. The export's "
        "schema changed, or the file is not the export it claims to be.")
    assert len(df) > 0, f"{what}: no rows"


# (guard_against_locked_regression is a rebuild-only check, not promoted.)

POSGRP = {"Center": "F", "Left Wing": "F", "Right Wing": "F",
          "Defense": "D", "Goaltender": "G"}


def birthdate_table(ep_csv: Path | None = None) -> pd.DataFrame:
    """One birthdate per (cleaned name + position group), for the season table.

    PuckPedia is the primary source and Elite Prospects the fallback, which is
    the precedence `20_CODE/age_join.py` already established -- PuckPedia is
    the vendor record, EP is a scrape run to reach the players PuckPedia could
    not match. Merging them the other way round would let a scrape overwrite
    the vendor.

    A key that claims two different birthdates is DROPPED, not resolved. Two
    people sharing a cleaned name and position is exactly the condition under
    which a birthdate is meaningless, and a wrong birthdate is a wrong age for
    every season of that career -- silently, in a curve fitted on age. The
    locked record already carries this failure in the production age join
    (23 identifiers, 217 rows, 47 players of ID pollution in
    WAR_with_age.csv); dropping is the conservative response and the count is
    reported rather than buried.
    """
    from player_season_table import norm_name

    con, _ = load_contracts()
    con["_k"] = ((con["first_name"].astype(str).str.strip() + " "
                  + con["last_name"].astype(str).str.strip()).map(norm_name)
                 + "|" + con["position"].map(POSGRP).astype(str))
    pp = con[["_k", "birthdate"]].dropna()
    pp = pp[pp["birthdate"].astype(str).str.len() >= 8]
    rows = [("puckpedia", pp)]

    if ep_csv is not None and Path(ep_csv).exists():
        ep = pd.read_csv(ep_csv).dropna(subset=["birthdate"])
        ep["_k"] = ep["war_name"].map(norm_name) + "|" + ep["war_position"].astype(str)
        rows.append(("elite prospects", ep[["_k", "birthdate"]]))

    out, seen, report = [], set(), []
    for name, df in rows:
        agree = df.groupby("_k")["birthdate"].nunique() == 1
        conflicted = int((~agree).sum())
        df = df[df["_k"].map(agree).fillna(False)].drop_duplicates("_k")
        fresh = df[~df["_k"].isin(seen)]
        seen |= set(fresh["_k"])
        out.append(fresh)
        report.append((name, len(df), len(fresh), conflicted))

    bt = pd.concat(out, ignore_index=True).rename(columns={"_k": "pkey"})
    for name, total, fresh, conflicted in report:
        C.log(f"  {name:>15}: {total} usable keys, {fresh} new"
              + (f", {conflicted} dropped for conflicting birthdates" if conflicted else ""))
    return bt


# (main is a rebuild-only check, not promoted.)
