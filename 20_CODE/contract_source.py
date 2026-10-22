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

SCRIPT_VERSION = "1.4"   # 1.4 (2026-10-21): read_goalie_war(), the two Matt Murrays apart; 1.1 (2026-10-14): war_full_name(), the WAR spelling for crosswalked ids
                         # 1.2 (2026-10-16): parse_export_dates(), either date style the exports carry
                         # 1.3 (2026-10-19): contract_terms(), the seasons a contract covers

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


def parse_export_dates(s: pd.Series, what: str) -> pd.Series:
    """A date column of a PuckPedia export, read in either of the two styles the copies on Thomas's computers carry
    (1.2, 2026-10-16): month/day/year ("9/2/2009") on one, year-month-day ("2009-09-02") on the laptop's contracts
    file. Each value must fit one style exactly; nothing is guessed (no day-first reading, no inferred format).
    GUARD: stops if any non-missing value fits neither."""
    mdy = pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    out = mdy.fillna(iso)
    bad = s.notna() & out.isna()
    assert not bad.any(), f"{what}: {int(bad.sum())} dates fit neither m/d/Y nor Y-m-d, e.g. {s[bad].head(3).tolist()}"
    return out


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


# ---- v1.1 (2026-10-14): the WAR tables' spelling for players the two sources spell differently ----------
_WAR_NAMES = None


def war_name_map() -> dict:
    """{NHL id: the name as WAR.csv / Goalies_WAR.csv spell it} for the ids war_name_crosswalk.py matched on the
    NHL game logs (Evgenii Dadonov -> Evgeny Dadonov, Matthew Beniers -> Matty Beniers; 34 on 2026-10-14). Refuses
    to run without the crosswalk: a missing file would silently drop those players again."""
    global _WAR_NAMES
    if _WAR_NAMES is None:
        path = Path(C.PROD_OUTPUT_DIR) / "war_name_crosswalk.csv"
        if not path.exists():
            raise RuntimeError(f"{path} is missing; run 20_CODE/war_name_crosswalk.py first")
        x = pd.read_csv(path)
        x = x[x["method"].astype(str).str.startswith("game-log")]
        _WAR_NAMES = dict(zip(x["nhl_id"].astype(int), x["war_name"].astype(str)))
    return _WAR_NAMES


def war_full_name(df: pd.DataFrame, base: pd.Series, id_col: str = "nhl_id") -> pd.Series:
    """The caller's own PuckPedia "first last" (`base`), with the WAR spelling put in for a matched NHL id.
    Every other row is returned unchanged, byte for byte, so a player who already joined is untouched."""
    xw = war_name_map()
    ids = pd.to_numeric(df[id_col], errors="coerce")
    sub = pd.Series([xw.get(int(i)) if pd.notna(i) else None for i in ids], index=df.index, dtype=object)
    return base.where(sub.isna(), sub)

POSGRP = {"Center": "F", "Left Wing": "F", "Right Wing": "F",
          "Defense": "D", "Goaltender": "G"}


# ---- v1.3 (2026-10-19, Thomas: "Everywhere, re-lock"; "Full term until buyout"): the seasons a contract covers ---
# The day free agency opened each summer where it was not July 1. The buyout window closes the day before it opens:
# in 2020 after the delayed playoffs (window September 25 to October 8), in 2021 after the July Final (to July 27).
FREE_AGENCY_OPENS = {2020: pd.Timestamp("2020-10-09"), 2021: pd.Timestamp("2021-07-28")}


def free_agency_opens(year: int) -> pd.Timestamp:
    """The day free agency opened in the summer of `year`: July 1, except 2020 (October 9) and 2021 (July 28)."""
    return FREE_AGENCY_OPENS.get(int(year), pd.Timestamp(int(year), 7, 1))


def _start_year(s: pd.Series) -> pd.Series:
    """A season label's starting year ("2018-2019" -> 2018)."""
    return pd.to_numeric(s.astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")


def contract_terms(df: pd.DataFrame) -> pd.DataFrame:
    """The seasons each PuckPedia contract covers: one row per contract, on `df`'s index.

    The export gives a contract's LENGTH (the years signed for) and its END season. For every contract but one kind
    the first season is end - length + 1, the rule the engine has always used: the export's own `season` field is
    the first season for some deals, the last for others and the current one for running deals, and end - length + 1
    also places an entry-level deal that slid in the seasons it was actually played. The exception is a deal that
    ended early. For a bought-out contract PuckPedia moves the END back to the last season played but keeps the full
    LENGTH, so end - length + 1 lands seasons before the deal was signed (Corey Perry's 2013 extension on 2011-12,
    Jeff Skinner's 2019 Buffalo deal on 2016-17). Such a deal is a "history" contract whose `season` field, its first
    season, falls after end - length + 1: 38 contracts on 2026-10-19, each starting in its signing season or the one
    after (asserted).

      first_yr        the first season: end - length + 1, or the `season` field for a deal that ended early
      last_played_yr  the export's end season, the last season played on the deal
      signed_end_yr   first_yr + length - 1, the last season signed for
      cut_short       signed_end_yr > last_played_yr: the deal ended early
      off_contract    for a deal that ended early, the day its end is taken as known: free agency's opening day after
                      its last season played (a buyout is done the day before at the latest); NaT otherwise
    Thomas, 2026-10-19 ("Full term until buyout"): a valuation dated before off_contract sees the full signed term,
    one dated on or after it sees the deal ended after last_played_yr."""
    end = _start_year(df["contract_end"])
    length = pd.to_numeric(df["length"], errors="coerce")
    back = end - length + 1
    field = _start_year(df["season"])
    cut = (df["contract_type"].astype(str) == "history") & (field > back)
    first = back.where(~cut, field)
    out = pd.DataFrame({"first_yr": first, "last_played_yr": end, "signed_end_yr": first + length - 1,
                        "cut_short": cut}, index=df.index)
    out["off_contract"] = pd.to_datetime([free_agency_opens(int(e) + 1) if c else pd.NaT
                                          for e, c in zip(end, cut)])
    # GUARD: a deal that ended early starts in the season it was signed or the one after
    sd = df["signing_date"]
    signed = sd if pd.api.types.is_datetime64_any_dtype(sd) else parse_export_dates(sd, "PuckPedia signing_date")
    signed = pd.to_datetime(signed)
    sign_season = signed.dt.year - (signed.dt.month < 7).astype(int)
    gap = (first - sign_season)[cut & signed.notna()]
    assert gap.isin([0, 1]).all(), f"a contract that ended early starts {sorted(gap.unique())} seasons from its signing"
    return out


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
    con["_k"] = (war_full_name(con, con["first_name"].astype(str).str.strip() + " "
                               + con["last_name"].astype(str).str.strip()).map(norm_name)   # v1.1
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

# ---- goaltenders who share a name (v1.4, 2026-10-21) ----------------------------------------------------------------
# Thomas, 2026-10-21: "fix the Matt Murray merge". Goalies_WAR.csv names goaltenders only, and two NHL goaltenders are
# called Matt Murray (NHL ids 8476899, born 1994-05-25, and 8483575, born 1998-02-02; goalie_birthdates.py matches each
# row to one of them by season and games). In 2022-23 the file has a Toronto row (26 games, the elder) and a Dallas row
# (3 games, the younger); every reader that sums a goaltender's team rows by name made them one 29-game season. Each split
# row below is renamed for the younger player, in letters only so that every name normaliser in the tree keeps it apart.
# Hand-verified against the NHL's goalie bios (games played by NHL id and season). The younger player has no contract
# in PuckPedia's export and no trade, so the rename only stops his games being read as the elder's.
GOALIE_WAR_SPLITS = {("Matt Murray", "22-23", "DAL"): ("Matt Murray Younger", 3)}


def read_goalie_war(path, usecols=None) -> pd.DataFrame:
    """Goalies_WAR.csv with each GOALIE_WAR_SPLITS row renamed (GUARD: each found exactly once, with its games)."""
    cols = None if usecols is None else list(dict.fromkeys(list(usecols) + ["Goalie", "Season", "Team", "GP"]))
    w = pd.read_csv(path, usecols=cols)
    for (name, season, team), (new, gp) in GOALIE_WAR_SPLITS.items():
        hit = (w["Goalie"] == name) & (w["Season"].astype(str) == season) & (w["Team"].astype(str) == team)
        assert int(hit.sum()) == 1 and int(w.loc[hit, "GP"].iloc[0]) == gp, (name, season, team, int(hit.sum()))
        w.loc[hit, "Goalie"] = new
    return w if usecols is None else w[list(usecols)]
