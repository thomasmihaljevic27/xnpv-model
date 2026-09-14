"""player_season_table.py -- the one season table every rebuild script reads.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 0, item 2.

WHAT IT IS
    One row per (player career key, position, season start year), carrying
    everything the forecast needs and nothing it does not: the six WAR
    components and the total, games, ice time, per-82 rates for all seven,
    the player's share of his team's games, NHL experience, and age where a
    birthdate is available. D20 proration is applied ONCE, here, so no
    downstream script can apply it twice or forget it.

WHY IT EXISTS
    Three production scripts each load WAR.csv with their own copy of the
    cleaning rules (skater_value_engine.py, skater_forward_projection.py,
    aging_curve.py, the last with a DIFFERENT fallback cleaner). Those
    copies stay exactly as they are -- the rebuild does not edit production
    -- but the new chain reads one table so that a forecast, an aging fit
    and a market fit cannot silently disagree about who a player is.

THE NAME RULES, RECONCILED
    The engine's norm_name strips a parenthesised tag, so "Elias
    Pettersson(D)" cleans to "elias pettersson" -- the same string as the
    Canucks forward. The engine survives that because its key carries the
    position ("elias pettersson|D" vs "|F"). aging_curve.py keys on the name
    ALONE, so it needs CURVE_NAME_SPLITS to pull them apart. Both keys are
    emitted here and both are correct:
        pkey        cleaned name + "|" + position. Byte-identical to the
                    engine's key, which is what lets the guard below compare
                    the two tables row for row.
        career_key  one key per real human, name-based, with the explicit
                    split for the Petterssons. Use this for anything that
                    follows a player across seasons (aging, experience)
                    because a player who changes position group keeps one
                    career; use pkey for anything that joins to production.
    The source already writes "Sebastian Aho Swe" and "Erik Gustafsson 88",
    which survive cleaning as distinct keys on their own and need no rule.

WHAT IS NOT HERE YET
    Birthdates. They come from the PuckPedia export (confidential, and not
    present in every checkout) via 20_CODE/age_join.py, with the Elite
    Prospects scrape as the second source. This module reads a birthdate CSV
    if one is supplied and otherwise emits age as missing and says so in the
    log -- it never guesses an age and never silently drops the ageless. The
    plan's Phase 0 item 4 (finish the EP pull; ~40% of careers have no age)
    is still open, and every age-using model must report its age coverage.

READ ONLY on 10_SOURCE. Writes only under 50_REBUILD/output/.

    python 50_REBUILD/code/player_season_table.py      # builds + guards + logs
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C

SCRIPT_VERSION = "1.0"

# --- Name normalisation ---------------------------------------------------
# Reproduced from skater_value_engine.norm_name rather than imported, so this
# tree stands alone. guard_against_production() below asserts the two agree
# on every name in the source; if a production edit ever changes the rule,
# that assert fails loudly instead of the two chains quietly diverging.
_VARIANTS = {
    "alexander": "alex", "alexandre": "alex", "nicholas": "nick",
    "michael": "mike", "matthew": "matt", "christopher": "chris",
    "maxime": "max", "zachary": "zach", "joshua": "josh", "samuel": "sam",
    "benjamin": "ben", "daniel": "dan", "jonathan": "jon",
    "steven": "steve", "gregory": "greg", "patrick": "pat",
}

# Same-name players the cleaning would merge on a name-only key. The value is
# the career key each gets. Keyed on the RAW source spelling, so adding one
# never changes any other player's key.
CAREER_SPLITS = {"Elias Pettersson(D)": "elias pettersson d"}


def norm_name(s) -> str:
    """Accent-strip, lowercase, drop punctuation and generational suffixes,
    resolve common first-name variants. Identical to the production engine's
    rule; see the guard."""
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().replace("-", " ")
    s = re.sub(r"\(.*?\)", "", s)               # strip "(D)"-style tags
    s = re.sub(r"[.'’]", "", s)
    s = re.sub(r"\b(jr|sr|iii|ii|iv)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split()
    if parts:
        parts[0] = _VARIANTS.get(parts[0], parts[0])
    return " ".join(parts)


def career_key(raw_player: str) -> str:
    """One key per real human. Cleaning first, then the manual splits."""
    if raw_player in CAREER_SPLITS:
        return CAREER_SPLITS[raw_player]
    return norm_name(raw_player)


# --- The table ------------------------------------------------------------
RATE_COLS = [c + "_82" for c in C.COMPONENTS_MODEL] + ["WAR_82"]


def build(birthdate_csv: Path | None = None, verbose: bool = True) -> pd.DataFrame:
    """Build the season table. Order of operations matters and is fixed:

      1. parse the season to a start year
      2. drop the merged-name rows (two humans under one row-name) BEFORE
         anything is summed -- a merged row must never reach an anchor
      3. apply D20 proration to every component AND the total, so the parts
         still add to the whole
      4. sum a traded player's team-halves into one season row BEFORE the
         games filter, so a player whose smaller half falls under MIN_GP
         keeps that production (production review item 1.5, the Nick Paul
         case: keeping the 21-game half and dropping the 59-game one flipped
         his 2022 anchor negative and routed him onto a different projection)
      5. only then compute rates, shares and experience
    """
    src = C.assert_read_only_source(C.F_WAR_SKATERS)
    w = pd.read_csv(src)
    n_raw = len(w)

    w["syr"] = w["Season"].str.split("-").str[0].astype(int) + 2000

    bare = w["Player"].map(norm_name)
    merged = bare.isin(C.MERGED_WAR_NAMES)
    w = w[~merged].copy()

    w["career_key"] = w["Player"].map(career_key)
    w["pkey"] = w["Player"].map(norm_name) + "|" + w["Position"]

    # UNALLOCATED WAR. Computed on the RAW source row, before proration, so
    # it is the vendor's own residual and not an artifact of anything this
    # tree does. See rebuild_config.UNALLOCATED for the finding and why the
    # residual is carried rather than rescaled away. Zero by construction for
    # every season through 2022-23, where the six components already add up.
    w[C.UNALLOCATED] = w["WAR"] - w[C.COMPONENTS].sum(axis=1)

    # D20. Applied to the components and the total together; scaling only the
    # total would leave the parts no longer summing to it, and the component
    # forecast reads both.
    pr = w["syr"].map(C.PRORATION).fillna(1.0)
    for c in C.COMPONENTS_MODEL + ["WAR"]:
        w[c] = w[c] * pr

    # GUARD before summing. Two halves of one player's season may be summed;
    # two different players sharing a cleaned name and position may not. A
    # SINGLE source row can already exceed 82 games (the source merges most
    # traded players into one row -- Cody Ceci 24-25, S.J/DAL, 85 GP), so the
    # check is on DUPLICATED keys only, which is what the production engine
    # checks too.
    dup = w.duplicated(["pkey", "syr"], keep=False)
    n_merged_halves = int(dup.sum())
    if dup.any():
        tot = w[dup].groupby(["pkey", "syr"])["GP"].sum()
        bad = list(tot[tot > 82].index)
        assert not bad, (
            f"combined games above a full season for {bad} -- two different "
            "players sharing a name and position, not one player's two "
            "team-halves. Give one a disambiguating career split, do not sum.")

    agg = {c: (c, "sum") for c in C.COMPONENTS_MODEL + ["WAR"]}
    agg.update(GP=("GP", "sum"), TOI=("TOI", "sum"),
               career_key=("career_key", "first"), pos=("Position", "first"),
               teams=("Team", lambda s: "/".join(sorted(set(s)))))
    a = pd.DataFrame(w.groupby(["pkey", "syr"], as_index=False).agg(**agg))

    # Per-82 RATES. The rate is the quantity that persists year to year; the
    # season total confounds it with availability, which is forecast
    # separately (plan, Phase 1: "games share is forecast separately from the
    # rate"). Dividing by the player's OWN games, not the schedule, is what
    # makes this a rate rather than a prorated total.
    for c in C.COMPONENTS_MODEL + ["WAR"]:
        a[c + "_82"] = a[c] / a["GP"] * C.FULL_SEASON

    # GAMES SHARE. Availability, on the schedule the player's season actually
    # had. Distinct from D20 above: proration corrects the league-wide
    # schedule for the VALUE of a season, this measures what fraction of it
    # the player was there for. Clipped at 1 because the source's merged
    # trade rows can carry up to 85 games across two teams' schedules.
    sched = a["syr"].map(C.SEASON_LEN).fillna(float(C.FULL_SEASON))
    a["gp_share"] = (a["GP"] / sched).clip(upper=1.0)
    a["toi_pg"] = a["TOI"] / a["GP"]

    # NHL EXPERIENCE, from this table only, so it is available at any
    # decision date without a second source. LEFT-CENSORED: a player whose
    # first row is the source's first season may have debuted earlier, so his
    # experience is a lower bound. The flag travels with the number; a model
    # that uses experience must decide what to do with it rather than
    # inherit a quiet bias toward "young" for the 2007 cohort.
    a = a.sort_values(["career_key", "syr"]).reset_index(drop=True)
    first = a.groupby("career_key")["syr"].transform("min")
    a["exp_seasons"] = a["syr"] - first          # 0 in the debut season
    a["exp_censored"] = first <= C.FIRST_SOURCE_SEASON

    a["age"], a["age_exact"] = np.nan, np.nan
    a["has_age"] = False
    if birthdate_csv is not None:
        a = _attach_age(a, Path(birthdate_csv))

    a = a.sort_values(["career_key", "syr", "pkey"]).reset_index(drop=True)

    if verbose:
        C.log(f"  source rows              {n_raw}")
        C.log(f"  dropped, merged names    {int(merged.sum())} "
              f"({', '.join(sorted(C.MERGED_WAR_NAMES))})")
        C.log(f"  team-halves summed       {n_merged_halves} rows into "
              f"{n_merged_halves - (n_raw - int(merged.sum()) - len(a))} "
              "(the source already merges most traded players itself; only "
              "differing spellings across the two halves land here)")
        C.log(f"  season rows              {len(a)}")
        C.log(f"  careers                  {a['career_key'].nunique()}")
        C.log(f"  seasons covered          {a['syr'].min()}-{a['syr'].max()}")
        C.log(f"  experience left-censored {int(a['exp_censored'].sum())} rows "
              f"({a['exp_censored'].mean():.1%}) -- debut at or before "
              f"{C.FIRST_SOURCE_SEASON}")
        C.log(f"  age coverage             {a['has_age'].mean():.1%}"
              + ("" if birthdate_csv else "  [no birthdate table supplied]"))
    return a


def _attach_age(a: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Join birthdates if a table is available. Age convention follows
    age_join.py: age on 1 February of the season's ENDING year, so
    consecutive seasons differ by exactly one year of age -- which is what a
    within-player delta aging curve needs. Unmatched players keep a missing
    age; nothing is imputed here."""
    if not path.exists():
        C.log(f"  [age] {path} not found -- ages left missing")
        return a
    bd = pd.read_csv(path)
    col = next((c for c in bd.columns if c.lower() in ("birthdate", "dob", "birth_date")), None)
    key = next((c for c in bd.columns if c.lower() in ("career_key", "nkey", "player")), None)
    if col is None or key is None:
        C.log(f"  [age] {path} has no usable birthdate/key columns -- ages left missing")
        return a
    bd["career_key"] = bd[key] if key == "career_key" else bd[key].map(career_key)
    bd = bd.dropna(subset=[col]).drop_duplicates("career_key")
    m = a.merge(bd[["career_key", col]], on="career_key", how="left")
    b = pd.to_datetime(m[col], errors="coerce")
    ref = pd.to_datetime(dict(year=m["syr"] + 1, month=2, day=1))
    m["age_exact"] = ((ref - b).dt.days / 365.25).round(2)
    m["age"] = np.floor(m["age_exact"])
    m["has_age"] = m["age_exact"].notna()
    return m.drop(columns=[col])


# --- Reproduction guard ---------------------------------------------------
def guard_against_production(a: pd.DataFrame) -> bool:
    """Prove the new table is the old pipeline where they overlap.

    skater_value_engine.build_skater_war_lookup() is the production loader.
    Filtered to GP >= MIN_GP and keyed the same way, this table's season-total
    WAR must equal it to floating-point tolerance on every key. That is the
    reproduction guard PROJECT_STATE asks of any new build: the rebuild is
    allowed to change what the model does with a season, not what a season is.

    Returns True if the guard ran and passed, False if 20_CODE could not be
    imported (a checkout without .env, or without the vendor paths set). A
    skipped guard is reported, never passed silently.
    """
    try:
        sys.path.insert(0, str(C.PROD_CODE_DIR))
        os.environ.setdefault("SOURCE_DIR", str(C.SOURCE_DIR))
        os.environ.setdefault("OUTPUT_DIR", str(C.OUT_DIR))  # never written to
        # The engine resolves the PuckPedia export paths at IMPORT time, so
        # the import fails without them even though build_skater_war_lookup()
        # reads WAR.csv alone. A placeholder satisfies the constant; no
        # confidential file is opened, and nothing downstream of this guard
        # touches a contract. If a real .env is present its values win.
        for v in ("PUCKPEDIA_CONTRACTS_XLSX", "PUCKPEDIA_TRADES_XLSX",
                  "GAMELOG_DB", "CLAUSES_DB", "EP_AGES_DB", "EP_PROSPECTS_DB",
                  "CODE_DIR", "STATE_DIR", "SCRAPE_OUT_DIR", "DROPBOX_ROOT"):
            os.environ.setdefault(v, str(C.OUT_DIR / "_unused_placeholder"))
        from skater_value_engine import (build_skater_war_lookup, norm_name as prod_norm,
                                         MERGED_WAR_NAMES as prod_merged,
                                         PRORATION as prod_proration, MIN_GP as prod_min_gp)
    except Exception as e:                       # noqa: BLE001 -- report, do not pass
        C.log(f"  GUARD SKIPPED: could not import the production engine ({e.__class__.__name__}: {e})")
        return False

    # 1. the constants this tree copied are still the production values
    assert prod_merged == C.MERGED_WAR_NAMES, "MERGED_WAR_NAMES drifted from production"
    assert prod_proration == C.PRORATION, "D20 PRORATION drifted from production"
    assert prod_min_gp == C.MIN_GP, "MIN_GP drifted from production"

    # 2. the name rule agrees on every name in the source, not just a sample
    names = pd.read_csv(C.F_WAR_SKATERS, usecols=["Player"])["Player"].drop_duplicates()
    mism = [n for n in names if norm_name(n) != prod_norm(n)]
    assert not mism, f"name normalisation differs from production for {mism[:5]}"

    # 3. the season totals match, key for key
    prod = build_skater_war_lookup(exclude_merged=True, prorate=True)
    mine = (a[a["GP"] >= C.MIN_GP].set_index(["pkey", "syr"])["WAR"].sort_index())
    prod.index.names = ["pkey", "syr"]
    assert set(mine.index) == set(prod.index), (
        f"key sets differ: {len(set(mine.index) ^ set(prod.index))} keys, "
        f"examples {list(set(mine.index) ^ set(prod.index))[:5]}")
    d = (mine - prod.reindex(mine.index)).abs().max()
    assert d < 1e-9, f"season-total WAR differs from production by up to {d}"

    # 4. the SEVEN modelled components sum to the total, exactly, in every
    #    season. With the unallocated residual carried this is an identity,
    #    which is the point: the rebuild never loses or invents WAR.
    dc = (a[C.COMPONENTS_MODEL].sum(axis=1) - a["WAR"]).abs().max()
    assert dc < 1e-9, f"the seven components do not sum to WAR, max gap {dc}"

    # 5. and the SIX source components sum to the total only before the
    #    vendor break. Asserting the break is where we found it turns the
    #    finding into a standing check: if a future export restores the
    #    identity, or breaks it earlier, this fails and we look again.
    pre = a[a["syr"] < C.UNALLOCATED_FIRST_SEASON]
    post = a[a["syr"] >= C.UNALLOCATED_FIRST_SEASON]
    d_pre = (pre[C.COMPONENTS].sum(axis=1) - pre["WAR"]).abs().max()
    assert d_pre < 1e-9, (
        f"the six source components stop summing to WAR before "
        f"{C.UNALLOCATED_FIRST_SEASON} (max gap {d_pre}) -- the vendor break "
        "is not where rebuild_config records it; re-run the diagnosis.")
    share = (post[C.UNALLOCATED] / post["WAR"]).replace([np.inf, -np.inf], np.nan)

    C.log(f"  GUARD PASS: {len(mine)} keys match the production loader exactly "
          f"(max |diff| {d:.2e})")
    C.log(f"  GUARD PASS: seven components sum to WAR (max gap {dc:.2e}); six "
          f"components sum to WAR before {C.UNALLOCATED_FIRST_SEASON} "
          f"(max gap {d_pre:.2e})")
    C.log(f"  unallocated WAR: {(post[C.UNALLOCATED].abs() > 1e-6).mean():.1%} of "
          f"{C.UNALLOCATED_FIRST_SEASON}+ rows nonzero, median "
          f"{share.median():.2%} of WAR, largest {post[C.UNALLOCATED].abs().max():.3f} wins")
    return True


def main() -> None:
    C.banner("player_season_table.py", SCRIPT_VERSION)
    C.log("Building the shared season table (rebuild plan, Phase 0 item 2)")
    C.log(f"  input  {C.F_WAR_SKATERS}  sha256:{C.file_hash(C.F_WAR_SKATERS)}")
    a = build(birthdate_csv=os.environ.get("REBUILD_BIRTHDATES"))
    C.log("")
    C.log("Reproduction guard against the production loader")
    passed = guard_against_production(a)
    C.log("")
    p = C.out_path("player_season_table.csv")
    a.to_csv(p, index=False)
    C.log(f"  wrote {p}  ({len(a)} rows)  sha256:{C.file_hash(p)}")
    C.log(f"  guard: {'PASS' if passed else 'SKIPPED -- do not trust downstream results'}")
    C.write_log("player_season_table_run_log.txt")


if __name__ == "__main__":
    main()
