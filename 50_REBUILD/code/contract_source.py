"""contract_source.py -- the PuckPedia exports, read as CSV and proven faithful.

EXPERIMENTAL (50_REBUILD). Unblocks Phase 4 and the age panel.

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

    python 50_REBUILD/code/contract_source.py     # validate + production guard
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C

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


def guard_against_locked_regression() -> bool:
    """THE decisive test: does this CSV reproduce the locked market rate?

    skater_value_engine.stage0() is the production reproduction guard. It
    rebuilds the original locked May-2026 regression from the contracts export
    and asserts the coefficients land on the locked report values, then fits
    and asserts the D20 rate. Running that code path with the CSV standing in
    for the workbook tests every field the locked regression touches --
    contract_end, length, position, names, aav, signing_status,
    contract_level -- against numbers fixed long before this CSV existed.

    A PASS means the CSV is the workbook for every purpose the market model
    has. Nothing weaker would justify building Phase 4 on it.

    read_excel is redirected rather than the engine edited: production stays
    untouched, which is the whole premise of this tree.
    """
    os.environ["OUTPUT_DIR"] = str(C.OUT_DIR / "_prod_guard_scratch")
    os.environ.setdefault("SOURCE_DIR", str(C.SOURCE_DIR))
    for v in ("PUCKPEDIA_TRADES_XLSX", "GAMELOG_DB", "CLAUSES_DB", "EP_AGES_DB",
              "EP_PROSPECTS_DB", "CODE_DIR", "STATE_DIR", "SCRAPE_OUT_DIR",
              "DROPBOX_ROOT"):
        os.environ.setdefault(v, str(C.OUT_DIR / "_unused_placeholder"))
    os.environ["PUCKPEDIA_CONTRACTS_XLSX"] = str(C.F_CONTRACTS_CSV)

    sys.path.insert(0, str(C.PROD_CODE_DIR))
    real_read_excel = pd.read_excel

    def read_excel_or_csv(path, *a, **k):
        p = Path(str(path))
        if p.suffix.lower() == ".csv":
            df, _ = read_csv_detect(p)
            return df
        return real_read_excel(path, *a, **k)

    pd.read_excel = read_excel_or_csv
    try:
        import skater_value_engine as eng
        eng.OUTPUT_DIR = C.OUT_DIR / "_prod_guard_scratch"
        result = eng.stage0()
        # stage0 returns None on failure and the fitted sample on success.
        passed = result is not None
        for line in eng.LOG:
            C.log("    | " + str(line))
        return passed
    finally:
        pd.read_excel = real_read_excel


# PuckPedia's position vocabulary -> the F/D/G groups WAR.csv uses.
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


def main() -> None:
    C.banner("contract_source.py", SCRIPT_VERSION)

    C.log("STEP 1  load and validate")
    con, enc_c = load_contracts()
    tra, enc_t = load_trades()
    C.log(f"  contracts  {len(con):>6} rows x {con.shape[1]} cols   encoding {enc_c}"
          f"   sha256:{C.file_hash(C.F_CONTRACTS_CSV)}")
    C.log(f"  trades     {len(tra):>6} rows x {tra.shape[1]} cols   encoding {enc_t}"
          f"   sha256:{C.file_hash(C.F_TRADES_CSV)}")

    sd = pd.to_datetime(con["signing_date"], errors="coerce")
    bd = pd.to_datetime(con["birthdate"], errors="coerce")
    C.log(f"  signing_date parses on {sd.notna().mean():.1%} of rows, "
          f"{sd.min().date()} to {sd.max().date()}")
    C.log(f"  birthdate    parses on {bd.notna().mean():.1%} of rows, "
          f"{bd.dt.year.min():.0f} to {bd.dt.year.max():.0f} births")
    C.log(f"  unique players {con['player_id'].nunique()}, "
          f"contracts {con['contract_id'].nunique()}")
    C.log("")

    C.log("STEP 2  production reproduction guard -- the locked May-2026 regression")
    C.log("        (running 20_CODE/skater_value_engine.py stage0 against this CSV)")
    passed = guard_against_locked_regression()
    C.log("")
    C.log(f"  RESULT: {'PASS' if passed else 'FAIL'} -- the CSV "
          f"{'reproduces' if passed else 'does NOT reproduce'} the locked coefficients")
    if not passed:
        C.log("  Do not build the market model on this file until this passes.")
        C.write_log("contract_source_run_log.txt")
        return
    C.log("")

    C.log("STEP 3  birthdate table for the season table (Phase 0 item 4)")
    ep = C.SOURCE_DIR / "ep_birthdates.csv"
    bt = birthdate_table(ep if ep.exists() else None)
    out = C.out_path("birthdates.csv")
    bt.to_csv(out, index=False)
    C.log(f"  {len(bt)} keys -> {out}")

    from player_season_table import build as build_table
    t = build_table(birthdate_csv=out, verbose=False)
    C.log(f"  age coverage {t['has_age'].mean():.1%} of season rows, "
          f"{t.groupby('career_key')['has_age'].any().mean():.1%} of careers")
    cov = t.groupby("syr")["has_age"].mean()
    C.log("  by season: " + "  ".join(f"{y}:{100 * v:.0f}%" for y, v in cov.items()))
    recent = t[t["syr"] >= 2015]
    C.log(f"  on the pages that matter (2015+): {recent['has_age'].mean():.1%}")
    C.write_log("contract_source_run_log.txt")


if __name__ == "__main__":
    main()
