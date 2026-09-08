#!/usr/bin/env python3
# =============================================================================
# join_clauses_to_spine.py
#
# PURPOSE
#   Attach the cap-space.com NTC/NMC clause schedule and bonus structure onto
#   the PuckPedia contract spine, producing the analytical table the clause
#   regression and the point-in-time back-test both draw from.
#
# WHAT IT PRODUCES (three files, written next to this script)
#   1. contract_season_spine.csv  - one row per PuckPedia contract-SEASON, with
#                                    clause + bonus columns attached per season.
#                                    (Use this for point-in-time clause status.)
#   2. contract_level_spine.csv   - one row per PuckPedia CONTRACT, with the
#                                    clause schedule summarised (as-signed, ever,
#                                    most-restrictive, min team count).
#                                    (Use this as the clause-discount regression
#                                    table.)
#   3. join_clauses_runlog.txt    - plaintext diagnostics for the methods section.
#
# IT IS READ-ONLY on all inputs, deterministic, and idempotent (re-running
# overwrites the three outputs and nothing else).
#
# -----------------------------------------------------------------------------
# WHY THE DESIGN LOOKS THE WAY IT DOES  (read this before trusting the numbers)
#
#   A. The two sources sit at DIFFERENT grains.
#      - PuckPedia export  = ONE row per CONTRACT (its `season` field is a single
#        season label, and `length` says how many years the deal runs).
#      - cap-space clauses = ONE row per CONTRACT-SEASON (clause status can differ
#        season to season within the same deal).
#      The earlier project note ("both are one-row-per-contract-season, clean
#      inner join on (ep_id, season)") is therefore WRONG. A naive inner join on
#      (ep_id, season) would match only each contract's FIRST season and silently
#      record every clause that activates later (e.g. an NTC that kicks in at UFA
#      eligibility) as "no clause". 419 contracts in the data change clause status
#      across their seasons, so this is a real bias, not a corner case.
#
#   B. So we make PuckPedia the authoritative spine and EXPAND it to seasons.
#      We do NOT trust the stored `season` start year, because PuckPedia stores
#      the FIRST season for completed deals but the LAST season for active
#      long-term deals. Instead we count BACK from `contract_end` by `length`:
#          seasons = [end_year - length + 1, ... , end_year]
#      This is correct regardless of the first/last-season storage quirk, and it
#      replaces the ad-hoc "end - length + 1" start-year fix with a full, correct
#      season expansion.
#
#   C. We join on (eliteprospects_id, season) -- NOT on signing_date.
#      PuckPedia and cap-space agree on signing_date only ~72% of the time, so it
#      is not a reliable cross-source contract key. (eliteprospects_id == the
#      cap-space `puckpedia_ep_id`, the identity-verified key from the scrape.)
#
#   D. Two clean-up rules replace the old "(player_id, signing_date, cap_hit)"
#      dedup, which does not fit the season grain:
#        - cap-space side: collapse to one record per (ep_id, season), keeping the
#          MOST RESTRICTIVE clause record. This removes cap-space's spurious
#          duplicate-contract rows (e.g. Loui Eriksson recorded at two cap hits
#          for the same signing).
#        - spine side: ~39 players carry two contracts covering the SAME season
#          (an expiring deal + an extension). The single cap-space season record
#          is attached to whichever contract's cap_hit is NEAREST cap-space's
#          recorded cap_hit, and nulled on the other, so the clause is not
#          double-counted across two contracts in one season.
#
#   These choices are logged in the run-log so they are documented, not implicit.
# =============================================================================

import os
import re
import sqlite3
import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# CONFIG  -- edit these paths to match your local layout, then run once.
# -----------------------------------------------------------------------------
PUCKPEDIA_XLSX = "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx"

# cap-space clauses: read from CSV by default. If you prefer to read from your
# local SQLite DB instead, set CLAUSES_DB to the .db path and CLAUSES_TABLE to
# the table name; the CSV path is then ignored.
CLAUSES_CSV   = "capspace_clauses.csv"
CLAUSES_DB    = None          # e.g. "capspace_clauses.db"
CLAUSES_TABLE = "clauses"     # only used if CLAUSES_DB is set

OUT_SEASON   = "contract_season_spine.csv"
OUT_CONTRACT = "contract_level_spine.csv"
OUT_LOG      = "join_clauses_runlog.txt"

# -----------------------------------------------------------------------------
# small run-log helper: print to console AND collect for the .txt file
# -----------------------------------------------------------------------------
_LOG = []
def log(msg=""):
    print(msg)
    _LOG.append(str(msg))

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

# Spelled-out team counts in cap-space's clause_limits text ("Ten team ...").
_WORD2NUM = {
    "one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,
    "nine":9,"ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,
    "fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,
    "twenty":20,"twentyone":21,"twentytwo":22,"twentythree":23,"twentyfour":24,
}

def parse_clause_limits(text):
    """
    Turn a clause_limits string like 'Ten team no trade list' into:
      team_count (int or NaN)  -- the number of teams on the list
      list_type  (str or NaN)  -- 'no trade list' / 'trade list' / 'no list' / ...
    NOTE ON SEMANTICS (flagged, not decided here): a 'no trade list' of N teams
    means N teams the player CANNOT be dealt to, whereas a 'trade list' of N means
    those are the ONLY N he can be dealt to (so 32-N are blocked). The graded-
    restrictiveness encoding in section 2.2 should account for that direction;
    this parser just exposes the raw integer and the list type.
    """
    if not isinstance(text, str) or text.strip() == "" or text.lower().startswith("details unknown"):
        return (np.nan, np.nan)
    t = text.strip().lower()
    # first token before "team" is the spelled-out count
    m = re.match(r"([a-z]+)\s+team", t)
    n = np.nan
    if m:
        n = _WORD2NUM.get(m.group(1), np.nan)
    # list type = everything after "team"
    lt = np.nan
    m2 = re.search(r"team\s+(.*)$", t)
    if m2:
        lt = m2.group(1).strip()
    return (n, lt)

def restrictiveness_rank(row):
    """Ordinal restrictiveness so we can keep the strongest clause when a season
    has duplicate cap-space records, and summarise 'most restrictive' per contract.
    full NMC (4) > full NTC (3) > modified NMC (2) > modified NTC (1) > none (0)."""
    if row.get("nmc_full"): return 4
    if row.get("ntc_full"): return 3
    if row.get("m_nmc"):    return 2
    if row.get("m_ntc"):    return 1
    return 0

_RANK2TYPE = {4:"NMC", 3:"NTC", 2:"M-NMC", 1:"M-NTC", 0:"none"}

# -----------------------------------------------------------------------------
# 1. LOAD + EXPAND THE PUCKPEDIA SPINE  (one row per contract -> contract-season)
# -----------------------------------------------------------------------------
def load_spine():
    p = pd.read_excel(PUCKPEDIA_XLSX)
    n_contracts = len(p)
    n_players   = p["player_id"].nunique()

    # 5 contracts have no EP id and therefore cannot be joined to cap-space.
    no_ep = p["eliteprospects_id"].isna().sum()

    # end-season start year: 'contract_end' is a season label like "2024-2025",
    # whose START year (2024) is how NHL seasons are indexed everywhere here.
    p["end_sy"] = p["contract_end"].astype(str).str.slice(0, 4).astype(int)

    # Expand each contract backward from its end season by `length` years.
    spine_rows = []
    for r in p.itertuples(index=False):
        L = int(r.length)
        for k in range(L):
            sy = r.end_sy - L + 1 + k
            spine_rows.append({
                "contract_id":  r.contract_id,
                "player_id":    r.player_id,
                "ep_id":        (int(r.eliteprospects_id)
                                 if pd.notna(r.eliteprospects_id) else np.nan),
                "nhl_id":       r.nhl_id,
                "last_name":    r.last_name,
                "first_name":   r.first_name,
                "position":     r.position,
                "season_start": sy,
                "season":       f"{sy}-{sy+1}",
                "pp_cap_hit":   r.cap_hit,
                "pp_aav":       r.aav,
                "pp_length":    L,
                "pp_ctype":     r.contract_type,
                "pp_expiry":    r.expiry_status,
                "ufa_year":     r.ufa_year,
                "birthdate":    r.birthdate,
                "draft_year":   r.draft_year,
            })
    spine = pd.DataFrame(spine_rows)

    log(f"[spine] PuckPedia contracts: {n_contracts}  players: {n_players}")
    log(f"[spine] contracts with NO eliteprospects_id (cannot join): {no_ep}")
    log(f"[spine] expanded to contract-seasons: {len(spine)}")
    return spine

# -----------------------------------------------------------------------------
# 2. LOAD + DEDUP THE CAP-SPACE CLAUSE/BONUS DATA  (-> one row per ep_id, season)
# -----------------------------------------------------------------------------
def load_clauses():
    if CLAUSES_DB:
        con = sqlite3.connect(CLAUSES_DB)
        c = pd.read_sql(f"SELECT * FROM {CLAUSES_TABLE}", con)
        con.close()
        log(f"[clauses] read from DB {CLAUSES_DB}::{CLAUSES_TABLE}")
    else:
        c = pd.read_csv(CLAUSES_CSV)
        log(f"[clauses] read from CSV {CLAUSES_CSV}")

    c = c.copy()
    c["ep_id"] = c["puckpedia_ep_id"].astype(int)

    # restrictiveness rank for the dedup tie-break
    c["_rk"] = c.apply(restrictiveness_rank, axis=1)

    before = len(c)
    # Collapse spurious duplicate cap-space contract records: keep, per
    # (ep_id, season), the MOST restrictive record (then highest cap_hit as a
    # final deterministic tie-break so the run is reproducible).
    c = c.sort_values(["ep_id", "season", "_rk", "cap_hit"],
                      ascending=[True, True, False, False])
    c = c.drop_duplicates(subset=["ep_id", "season"], keep="first")
    log(f"[clauses] season-rows: {before} -> {len(c)} after (ep_id,season) "
        f"most-restrictive dedup ({before-len(c)} duplicate season-rows removed)")

    # parse the graded team count + list type out of the text field
    parsed = c["clause_limits"].apply(parse_clause_limits)
    c["cs_team_count"] = [t[0] for t in parsed]
    c["cs_list_type"]  = [t[1] for t in parsed]
    c["cs_clause_type"] = c["_rk"].map(_RANK2TYPE)

    keep = ["ep_id", "season",
            "cap_hit", "aav", "nhl_salary", "minors_salary",
            "signing_bonus", "perf_bonuses",
            "nmc_full", "ntc_full", "m_ntc", "m_nmc", "has_any_clause",
            "cs_clause_type", "cs_team_count", "cs_list_type",
            "clause_limits", "clause_raw", "expiration_status",
            "entry_level", "extension", "_rk"]
    c = c[keep].rename(columns={
        "cap_hit":"cs_cap_hit", "aav":"cs_aav",
        "nhl_salary":"cs_nhl_salary", "minors_salary":"cs_minors_salary",
        "signing_bonus":"cs_signing_bonus", "perf_bonuses":"cs_perf_bonuses",
        "expiration_status":"cs_expiry",
        "entry_level":"cs_entry_level", "extension":"cs_extension",
    })
    return c

# -----------------------------------------------------------------------------
# 3. JOIN  (left join clause data onto the authoritative spine + overlap fix)
# -----------------------------------------------------------------------------
def join_spine_clauses(spine, clauses):
    clause_value_cols = [col for col in clauses.columns if col not in ("ep_id", "season")]

    m = spine.merge(clauses, on=["ep_id", "season"], how="left", indicator=True)

    # ---- overlap fix: ~39 players have 2 contracts in the same season; the one
    # cap-space season record matched both. Keep the clause on the contract whose
    # cap_hit is NEAREST cap-space's cap_hit; null the clause cols on the other(s).
    m["_capdiff"] = (m["pp_cap_hit"] - m["cs_cap_hit"]).abs()
    grp = m.groupby(["ep_id", "season"])
    m["_n_contracts_this_season"] = grp["contract_id"].transform("nunique")
    # within an overlapping (ep_id, season), rank contracts by cap_hit closeness
    m["_rank_in_overlap"] = (m.sort_values("_capdiff")
                              .groupby(["ep_id", "season"]).cumcount())
    overlap_loser = (m["_n_contracts_this_season"] > 1) & (m["_merge"] == "both") \
                    & (m["_rank_in_overlap"] > 0)
    n_overlap_fixed = int(overlap_loser.sum())
    m.loc[overlap_loser, clause_value_cols] = np.nan
    m.loc[overlap_loser, "_merge"] = "left_only"

    # clean grain assertion: exactly one row per (contract_id, season)
    dup = m.duplicated(subset=["contract_id", "season"], keep=False).sum()
    assert dup == 0, f"grain broken: {dup} duplicate (contract_id, season) rows"

    m["clause_matched"] = (m["_merge"] == "both")
    m = m.drop(columns=["_merge", "_capdiff", "_rank_in_overlap"])

    # ---- diagnostics ----
    total = len(m)
    matched = int(m["clause_matched"].sum())
    in_target = m["ep_id"].isin(clauses["ep_id"].unique())
    matched_in_target = int(m.loc[in_target, "clause_matched"].sum())
    n_in_target = int(in_target.sum())

    log("")
    log(f"[join] overlap-season clause re-attributions (cap_hit-nearest): {n_overlap_fixed}")
    log(f"[join] MATCH RATE all spine contract-seasons: "
        f"{matched}/{total} = {matched/total:.1%}")
    log(f"[join] MATCH RATE within cap-space target players: "
        f"{matched_in_target}/{n_in_target} = {matched_in_target/max(n_in_target,1):.1%}")
    log(f"[join]   (the gap to 100% on all rows is contracts outside the "
        f"cap-space bounded sample, e.g. non-UFA-signed pre-2018 deals.)")

    mm = m[m["clause_matched"]]
    if len(mm):
        agree = ((mm["pp_cap_hit"] - mm["cs_cap_hit"]).abs() < 1).mean()
        log(f"[join] cap_hit agreement PP vs cap-space on matched rows (<$1): {agree:.1%}")
        log(f"[join]   (a cross-source check that the (ep_id,season) join landed "
            f"the right contract; gap = retained salary / rounding / dup contracts.)")
        log(f"[join] matched contract-seasons carrying a clause: "
            f"{int(mm['has_any_clause'].fillna(0).sum())} "
            f"({mm['has_any_clause'].fillna(0).mean():.1%})")
    return m

# -----------------------------------------------------------------------------
# 4. CONTRACT-LEVEL ROLLUP  (the clause-discount regression table)
# -----------------------------------------------------------------------------
def contract_rollup(season_df):
    """
    Collapse the per-season spine to one row per contract, summarising the clause
    schedule. We expose BOTH conventions so the regression can choose:
      clause_as_signed_* : status in the contract's FIRST season (clause at signing)
      clause_ever_*      : did the contract carry the clause in ANY season
      clause_most_restr_*: the strongest clause across the contract's life
    plus the minimum team count seen (the most restrictive graded value) and a
    flag for contracts whose clause status changes across seasons.
    """
    df = season_df.sort_values(["contract_id", "season_start"]).copy()

    # first-season (as-signed) row per contract.
    # NOTE (fragility guard, 2026-07-01): pandas groupby.first() takes the
    # first NON-NULL value PER COLUMN, not literally the first season's row.
    # That is harmless here because every attribute carried below is
    # contract-constant -- but if you ever add a SEASON-VARYING column to the
    # `attrs` list, this will silently mix values across seasons. Use
    # .nth(0) or an explicit sort+drop_duplicates if that day comes.
    first = df.groupby("contract_id", as_index=False).first()

    def agg_one(g):
        ranks = g["_rk"].fillna(0)
        most = int(ranks.max()) if len(ranks) else 0
        first_row = g.sort_values("season_start").iloc[0]
        as_signed_rank = int(first_row["_rk"]) if pd.notna(first_row["_rk"]) else 0
        tc = g["cs_team_count"].dropna()
        return pd.Series({
            "n_clause_seasons":      int((ranks > 0).sum()),
            "n_seasons":             len(g),
            "clause_ever":           bool((ranks > 0).any()),
            "clause_ever_type":      _RANK2TYPE[most],
            "clause_as_signed":      bool(as_signed_rank > 0),
            "clause_as_signed_type": _RANK2TYPE[as_signed_rank],
            "clause_most_restr_type":_RANK2TYPE[most],
            "min_team_count":        (int(tc.min()) if len(tc) else np.nan),
            "clause_changes":        bool(g["_rk"].fillna(0).nunique() > 1),
            "any_clause_matched":    bool(g["clause_matched"].any()),
        })

    roll = df.groupby("contract_id").apply(agg_one).reset_index()

    # carry the static contract attributes from the first-season row
    attrs = ["player_id","ep_id","nhl_id","last_name","first_name","position",
             "pp_length","pp_ctype","pp_expiry","ufa_year","birthdate","draft_year",
             "pp_cap_hit","pp_aav","season_start"]
    out = first[["contract_id"] + attrs].merge(roll, on="contract_id", how="left")
    out = out.rename(columns={"season_start":"start_season_year"})

    log("")
    log(f"[rollup] contracts: {len(out)}")
    log(f"[rollup]   carrying a clause as signed: {int(out['clause_as_signed'].sum())}")
    log(f"[rollup]   carrying a clause ever:      {int(out['clause_ever'].sum())}")
    log(f"[rollup]   clause status CHANGES across seasons: {int(out['clause_changes'].sum())}")
    log(f"[rollup]   (these are why a start-season-only join would mis-measure "
        f"the clause variable.)")

    # FLAG ENCODING FIX (2026-07-01): same rationale as the season file --
    # write contract-level booleans as 1/0 so every downstream consumer gets
    # a plain numeric column. These four have no missing state, so plain int.
    for col in ["clause_ever", "clause_as_signed", "clause_changes",
                "any_clause_matched"]:
        out[col] = out[col].astype(int)
    return out

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    log("="*72)
    log("JOIN: cap-space clauses/bonuses -> PuckPedia contract spine")
    log("="*72)

    spine   = load_spine()
    clauses = load_clauses()
    season  = join_spine_clauses(spine, clauses)
    contract = contract_rollup(season)

    # drop internal helper col before writing the season file
    season_out = season.drop(columns=["_rk","_n_contracts_this_season"], errors="ignore")

    # -------------------------------------------------------------------------
    # FLAG ENCODING FIX (2026-07-01). The clause flags used to round-trip
    # through the CSV as a mix of True/False and blanks, which pandas reads
    # back as an object column of Python bools + NaN. That three-state,
    # type-ambiguous shape caused a silent bug in the 2026-06-30 power
    # analysis (a string comparison `== 'True'` matched nothing and zeroed
    # the monopsony count). We now write every boolean flag as 1/0, with
    # blank preserved ONLY where the clause data is genuinely missing
    # (unmatched rows). Read back, these become plain numeric columns
    # (1.0 / 0.0 / NaN): sums, means, and comparisons all behave, and there
    # is no string trap. `clause_matched` has no missing state, so it is a
    # clean 1/0 with no blanks.
    # -------------------------------------------------------------------------
    BOOL_FLAGS_NULLABLE = ["nmc_full", "ntc_full", "m_ntc", "m_nmc",
                           "has_any_clause", "cs_entry_level", "cs_extension"]
    for col in BOOL_FLAGS_NULLABLE:
        # map True->1, False->0, keep NaN as NaN (nullable Int64 writes it blank)
        season_out[col] = season_out[col].map({True: 1, False: 0}).astype("Int64")
    season_out["clause_matched"] = season_out["clause_matched"].astype(int)

    season_out.to_csv(OUT_SEASON, index=False)
    contract.to_csv(OUT_CONTRACT, index=False)
    log("")
    log(f"[write] {OUT_SEASON}   ({len(season_out)} rows, one per contract-season)")
    log(f"[write] {OUT_CONTRACT} ({len(contract)} rows, one per contract)")

    with open(OUT_LOG, "w") as f:
        f.write("\n".join(_LOG) + "\n")
    print(f"\n[write] {OUT_LOG}")

if __name__ == "__main__":
    main()
