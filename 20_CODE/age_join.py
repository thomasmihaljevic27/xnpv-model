"""
age_join.py
===========
Attach a player AGE to every season-row in Bacon's skater WAR file (WAR.csv) by
joining birthdates from the PuckPedia player export. This produces the `age`
column that similarity_aging.build_delta_table()/project_curve() require to
place the aging curve on an age axis.

WHY THIS IS NEEDED
------------------
WAR.csv has no birthdate or age column - only a player NAME and an F/D position.
PuckPedia has birthdates but joins to WAR only by name (WAR carries no IDs). So
this script is a careful NAME-based join, hardened against the two things that
break name joins: same-name collisions and nickname/spelling differences.

HOW THE JOIN WORKS (and every assumption it bakes in)
-----------------------------------------------------
1. NAME NORMALISATION. Both sides are reduced to a comparable key: accents
   stripped, lower-cased, hyphens -> spaces, apostrophes/periods removed,
   Jr/Sr/III suffixes removed, AND parenthetical tags removed. That last point
   matters: WAR.csv self-disambiguates its one F/D name clash by storing the
   defenceman as "Elias Pettersson(D)" - we strip "(D)" for the name match but
   still read the real position from WAR's Position column.

2. POSITION GROUP IS PART OF THE KEY. PuckPedia's detailed position
   (Center/Left Wing/Right Wing/Defense/Goaltender) is collapsed to F/D/G, and
   we join on (normalised name + F-or-D). This is deliberate: all four known
   same-name collisions (Sebastian Aho, Elias Pettersson, Connor Murphy, Josh
   Anderson) split by position in PuckPedia, so (name + position group) lands a
   UNIQUE, CORRECT player every time - and it auto-drops the goaltender
   "Connor Murphy", who has no business in a skater-WAR file. Verified: this key
   has zero remaining (name+posgroup) duplicates among PuckPedia skaters.

3. TWO-PASS MATCHING.
   * Pass 1 (exact): join on (normalised full name + position group).
   * Pass 2 (fuzzy, only for what Pass 1 missed): join on
     (normalised LAST name + position group + first initial), accepted ONLY when
     exactly one PuckPedia skater fits. This recovers nickname mismatches such
     as WAR's "Alex Nylander" vs PuckPedia's "Alexander Nylander" without risking
     a wrong match on common last names.

4. AGE CONVENTION (documented, configurable). A player's age for a season is
   their age on 1 FEBRUARY of the season's ENDING year - e.g. season "23-24" ->
   1 Feb 2024. This is the standard Hockey-Reference convention and guarantees
   consecutive seasons differ by exactly one year of age, which is what the
   delta-method curve needs. We output both an integer `age` and a continuous
   `age_exact`.

COVERAGE REALITY (so the run log is honest)
-------------------------------------------
The PuckPedia export is a CURRENT-contract file, so players who retired before
~2018 are simply not in it and cannot get a birthdate here. About 59% of all
WAR players match, but ~99% of players last seen in 2018+ match (only a dozen
recent misses). Since the back-test window is 2018+, the players being VALUED
are well covered; the unmatched are mostly older comp-pool history. Unmatched
players are written to a misses file for optional secondary sourcing (Elite
Prospects / Hockey-Reference) later.

IDENTIFICATION NOTES
--------------------
* Birthdate is a static biographical fact, not a performance metric, so this
  join introduces no look-ahead bias and no single-provider conflict (it is not
  a value input).
* Read-only on all inputs. Deterministic. Outputs: one CSV (WAR + age), one
  misses CSV, one plaintext run log.

USAGE
-----
    python3 age_join.py
(adjust the path constants below if your filenames differ)
"""

import re
import os
import unicodedata
from datetime import date

import pandas as pd

# ----------------------------------------------------------------------------
# CONFIG -- paths and the age convention. Nothing magic is hidden below this.
# ----------------------------------------------------------------------------
WAR_PATH = "WAR.csv"
PUCKPEDIA_PATH = "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx"

OUT_WAR_AGE = "WAR_with_age.csv"
OUT_MISSES = "age_join_misses.csv"
OUT_LOG = "age_join_log.txt"
OUT_ID_CONFLICTS = "age_join_id_conflicts.csv"   # review item 1.8


# ---------------------------------------------------------------------------
# REVIEW ITEM 1.8 -- one identifier can carry several players
# ---------------------------------------------------------------------------
# This file was built by matching players across sources, and some of those
# matches attached the same identifier to more than one person. The pairs are
# lookalike names: Mark and Matt Cullen share an id, so do Marcel and Marian
# Hossa, Taylor and Tom Pyatt, Rick and Riley Nash, and one id carries three
# Sutters (Brandon, Brett, Brody).
#
# It changes nothing today, because nothing currently joins to this file on
# the identifier -- the aging curve keys on the player name and the projection
# gets its ids from the contract spine. The exposure is forward-looking: this
# file is now permanent project data, and any future join on identifier alone
# will attach the wrong player silently, with no error raised.
#
# Two things below. id_name_conflicts() finds and reports them, and
# join_on_id_and_name() is the guard any future join through this file should
# use instead of a plain merge -- it is the same rule draft_pick_linkage.py
# already applies.
def id_name_conflicts(df, id_col="player_id", name_col="Player"):
    """Every identifier in `df` that carries more than one distinct name.
    Returns one row per (identifier, name) pair, with the row count."""
    d = df[df[id_col].notna()]
    per_id = d.groupby(id_col)[name_col].nunique()
    bad = per_id[per_id > 1].index
    out = (d[d[id_col].isin(bad)]
           .groupby([id_col, name_col], as_index=False)
           .size().rename(columns={"size": "rows"})
           .sort_values([id_col, name_col]))
    return out


def join_on_id_and_name(left, right, id_col="player_id", name_col="Player",
                        how="left", strict=True):
    """Join through this file on identifier AND name together, never on the
    identifier alone.

    strict=True raises if any left-hand row matches on identifier but fails on
    name, which is exactly the silent wrong-player attachment this guard
    exists to prevent. Set strict=False only when a partial match is expected
    and handled by the caller."""
    merged = left.merge(right, on=[id_col, name_col], how=how,
                        suffixes=("", "_r"))
    if strict:
        id_only = left.merge(right[[id_col]].drop_duplicates(), on=id_col,
                             how="inner")
        both = left.merge(right[[id_col, name_col]].drop_duplicates(),
                          on=[id_col, name_col], how="inner")
        lost = len(id_only) - len(both)
        assert lost <= 0, (
            f"{lost} row(s) match on {id_col} but disagree on {name_col}. "
            f"That is the wrong-player attachment this guard exists to catch. "
            f"Resolve the identifier before joining, or pass strict=False if "
            f"the caller handles it.")
    return merged


# Optional SECOND birthdate source: the Elite Prospects scrape (ep_age_scraper.py)
# that recovers pre-2018 retirees PuckPedia never had. If this file is absent the
# script still runs; those players just stay unmatched. Keyed on the exact WAR
# `Player` string. Applied in Pass 4, after the PuckPedia passes.
EP_BIRTHDATES_PATH = "ep_birthdates.csv"

# Corrections for the EP rows the scraper resolved to the WRONG person (its
# review pile). Each was re-checked against Elite Prospects by hand. These
# OVERRIDE whatever ep_birthdates.csv holds for the same name, so a bad scrape
# guess (e.g. "Brian Lee" -> Brian Leetch, off by 19 years) cannot leak in.
EP_BIRTHDATE_OVERRIDES = {
    "Brian Lee": "1987-03-26",          # scraper grabbed Brian Leetch
    "Petr Sykora": "1976-11-19",        # grabbed the other Petr Sykora (1978)
    "J-f Jacques": "1985-04-29",        # grabbed Jacques Lemaire
    "Sean Collins Can": "1983-10-30",   # grabbed junk ("Canon Pieper")
    "Colin White Can": "1977-12-12",    # grabbed junk; this is the Canadian D
    "Michael Ryan": "1980-05-16",       # grabbed Mike Halmo
    "Jeffrey Hamilton": "1977-09-04",   # grabbed Curtis Hamilton
    "Maxim Kondratiev": "1983-01-20",   # grabbed a 2011 junior (spelling: Kondratyev)
    "James Dowd": "1968-12-25",         # grabbed a 2001 junior (listed as Jim Dowd)
    "Erik Gustafsson 88": "1988-12-15", # scraper left unmatched (the "88" broke search)
    # --- pre-2018 retirees a PuckPedia auto-match sent to a YOUNG namesake
    #     (caught by the plausibility gate below); re-resolved against EP ---
    "Scott Walker": "1973-07-19",
    "Michael Peca": "1974-03-26",
    "Matt Ellis": "1981-08-31",
    "Mathieu Roy": "1983-08-10",
    "Jason Blake": "1973-09-02",
    "James Wright": "1990-03-24",
    "Curtis Brown": "1976-02-12",
    "Craig Adams": "1977-04-26",
    "Cory Stillman": "1973-12-20",
    "Cory Murphy": "1978-02-13",
    "Conor Allen": "1990-01-31",
    "Byron Ritchie": "1977-04-24",
    "Brendan Morrison": "1975-08-15",
    "Todd Bertuzzi": "1975-02-02",
    "Wyatt Smith": "1977-02-13",
    "Blair Jones": "1986-09-27",
    # NOTE: "Ryan Johnson" and "Nathan Smith" are deliberately NOT here. Each is
    # TWO different players merged under one name in WAR.csv (a gap in their
    # seasons gives it away), so no single birthdate is correct. The gate voids
    # their bad match and they stay unmatched until WAR disambiguates the names.
}

# Age is measured on this month/day of the season's ENDING year (Hockey-Ref = Feb 1).
REFERENCE_MONTH = 2
REFERENCE_DAY = 1

# PuckPedia detailed position -> coarse group used in the join key.
POSITION_GROUP = {
    "Center": "F", "Left Wing": "F", "Right Wing": "F",
    "Defense": "D", "Goaltender": "G",
}

# ----------------------------------------------------------------------------
# MANUAL OVERRIDES (Pass 3): the handful of recent players the automatic passes
# cannot reach, each verified individually against PuckPedia by birthdate.
# Maps the exact WAR.csv `Player` string -> PuckPedia player_id. Applied LAST and
# authoritatively. Grouped by WHY the automatic match failed so the logic is
# auditable. (All 13 were players last seen in the 2018+ back-test window.)
# ----------------------------------------------------------------------------
MANUAL_OVERRIDES = {
    # --- Russian transliteration differences (Egor/Yegor, -ev/-yov, ai/ay) ---
    "Egor Zamula": 17619,        # PuckPedia "Yegor Zamula"
    "Nikita Okhotiuk": 18014,    # "Nikita Okhotyuk"
    "Vladimir Tkachev": 18841,   # "Vladimir Tkachyov"
    "Danil Yurtaykin": 17932,    # "Danil Yurtaikin"
    "Egor Korshkov": 6749,       # "Yegor Korshkov"
    "Mikhail Vorobyev": 6465,    # "Mikhail Vorobyov"
    # --- nicknames the first-initial fuzzy pass could not separate ---
    "Sasha Chmelevski": 17127,   # "Alexander Chmelevski" (Sasha = Alexander)
    "Mike Benning": 18446,       # "Michael Benning" (vs older Matt Benning, also D)
    # --- F/D "tweeners": WAR lists D, PuckPedia lists a forward; birthdate
    #     confirms identity, so accept across the position-group mismatch ---
    "Ian Moore": 18418,          # WAR D / PuckPedia C, dob 2002-01-04
    "Mason Geertsen": 5719,      # WAR D / PuckPedia LW
    "Kurtis MacDermid": 4994,    # WAR D / PuckPedia LW
    "Hunter Drew": 17501,        # WAR D / PuckPedia C
    # --- the THIRD Sebastian Aho: the Swedish NYI defenceman (WAR suffixes
    #     "Swe"); maps to the Defense Aho, distinct from the Carolina centre ---
    "Sebastian Aho Swe": 17081,  # "Sebastian Aho" (Defense), dob 1996-02-17
}


# ----------------------------------------------------------------------------
# NAME NORMALISATION
# ----------------------------------------------------------------------------
def normalise_name(name):
    """
    Reduce a display name to a robust join key.
    'Tim Stützle' -> 'tim stutzle' ; 'Elias Pettersson(D)' -> 'elias pettersson'
    'K'Andre Miller' -> 'kandre miller' ; 'Pierre-Luc Dubois' -> 'pierre luc dubois'
    """
    if not isinstance(name, str):
        return ""
    # strip accents to plain ASCII
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\(.*?\)", "", s)            # drop parenthetical tags like (D)
    s = s.lower()
    s = s.replace("-", " ").replace("'", "").replace(".", "")
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)   # drop generational suffixes
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ----------------------------------------------------------------------------
# SEASON -> AGE
# ----------------------------------------------------------------------------
def season_end_year(season_str):
    """'23-24' -> 2024 ; '99-00' -> 2000. Two-digit years; >50 means 19xx start."""
    yy = int(str(season_str).split("-")[0])
    start = 1900 + yy if yy > 50 else 2000 + yy
    return start + 1


def compute_age(birthdate, end_year):
    """
    Exact and integer age on (REFERENCE_MONTH/REFERENCE_DAY) of `end_year`.
    Returns (age_int, age_exact) or (None, None) if birthdate is missing.
    """
    if pd.isna(birthdate):
        return None, None
    bd = pd.to_datetime(birthdate, errors="coerce")
    if pd.isna(bd):           # malformed string (e.g. an EP "2001-00-00")
        return None, None
    bd = bd.date()
    ref = date(end_year, REFERENCE_MONTH, REFERENCE_DAY)
    days = (ref - bd).days
    age_exact = days / 365.25
    # integer years completed by the reference date
    age_int = end_year - bd.year - ((ref.month, ref.day) < (bd.month, bd.day))
    return age_int, round(age_exact, 2)


# ----------------------------------------------------------------------------
# BUILD THE PUCKPEDIA BIRTHDATE LOOKUP (one row per player)
# ----------------------------------------------------------------------------
def build_puckpedia_lookup(path):
    raw = pd.read_excel(path).drop_duplicates("player_id").copy()
    raw["full_name"] = raw["first_name"].astype(str) + " " + raw["last_name"].astype(str)
    raw["nkey"] = raw["full_name"].map(normalise_name)
    raw["posgroup"] = raw["position"].map(POSITION_GROUP)
    raw["last_norm"] = raw["last_name"].astype(str).map(normalise_name)
    raw["first_init"] = raw["first_name"].astype(str).str[:1].str.lower()
    # id-indexed bio (any position) so the manual-override pass can fetch a
    # birthdate straight from a known player_id.
    id_bio = raw.set_index("player_id")[["birthdate", "eliteprospects_id", "nhl_id"]]
    # skaters only (drops the goaltender half of the Connor Murphy collision)
    sk = raw[raw["posgroup"].isin(["F", "D"])].copy()
    keep = ["player_id", "full_name", "nkey", "posgroup", "last_norm",
            "first_init", "birthdate", "eliteprospects_id", "nhl_id"]
    return sk[keep], id_bio


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    log = []
    def record(msg):
        log.append(msg)
        print(msg)

    war = pd.read_csv(WAR_PATH)
    pp, id_bio = build_puckpedia_lookup(PUCKPEDIA_PATH)

    # WAR-side keys (one lookup row per distinct player)
    players = war.drop_duplicates("Player")[["Player", "Position"]].copy()
    players["nkey"] = players["Player"].map(normalise_name)
    players["last_norm"] = players["Player"].map(
        lambda x: normalise_name(x).split()[-1] if normalise_name(x) else "")
    players["first_init"] = players["Player"].map(
        lambda x: normalise_name(x)[:1] if normalise_name(x) else "")
    players["posgroup"] = players["Position"]   # WAR Position is already F/D

    # ---- PASS 1: exact (nkey + posgroup) ----
    p1 = players.merge(
        pp[["nkey", "posgroup", "player_id", "birthdate", "eliteprospects_id", "nhl_id"]],
        on=["nkey", "posgroup"], how="left")
    p1["match_type"] = p1["player_id"].notna().map({True: "exact", False: ""})

    # ---- PASS 2: fuzzy (last_norm + posgroup + first_init), unique only ----
    # candidate counts so we only accept unambiguous fuzzy hits
    fuzz = pp.groupby(["last_norm", "posgroup", "first_init"])
    fuzz_unique = fuzz.filter(lambda g: g["player_id"].nunique() == 1) \
                      .drop_duplicates(["last_norm", "posgroup", "first_init"])
    need = p1["player_id"].isna()
    recovered = p1.loc[need, ["Player", "last_norm", "posgroup", "first_init"]].merge(
        fuzz_unique[["last_norm", "posgroup", "first_init", "player_id",
                     "birthdate", "eliteprospects_id", "nhl_id"]],
        on=["last_norm", "posgroup", "first_init"], how="left")
    recovered = recovered.set_index("Player")
    for col in ["player_id", "birthdate", "eliteprospects_id", "nhl_id"]:
        hit = recovered[col].notna()
        p1.loc[p1["Player"].isin(recovered.index[hit]), col] = \
            p1.loc[p1["Player"].isin(recovered.index[hit]), "Player"].map(recovered[col])
    p1.loc[(p1["match_type"] == "") & p1["player_id"].notna(), "match_type"] = "fuzzy"

    # ---- PLAUSIBILITY GATE: void any exact/fuzzy match with an impossible age --
    # A pre-2018 retiree absent from PuckPedia can auto-match a YOUNG namesake who
    # IS in the contract file, producing a birthdate decades off (e.g. a 2003-born
    # "Jason Blake" for the 1973 one). Reject any auto-match whose implied age sits
    # outside [16, 50] across the player's WAR seasons, so it falls through to the
    # EP source / correction table instead of poisoning the curve.
    _sy = war["Season"].str[:2].astype(int).map(lambda y: 1900 + y if y > 50 else 2000 + y)
    _first = war.assign(_sy=_sy).groupby("Player")["_sy"].min()
    _last = war.assign(_sy=_sy).groupby("Player")["_sy"].max()
    gate_voided = 0
    for i in p1.index:
        if p1.at[i, "match_type"] not in ("exact", "fuzzy"):
            continue
        yr = pd.to_datetime(p1.at[i, "birthdate"], errors="coerce")
        nm = p1.at[i, "Player"]
        if pd.isna(yr) or nm not in _first.index:
            continue
        by = yr.year
        age_first, age_last = _first[nm] - by, _last[nm] - by
        if age_first < 16 or age_last > 50 or age_last < 16:
            p1.at[i, "player_id"] = float("nan")
            p1.at[i, "birthdate"] = pd.NaT
            p1.at[i, "match_type"] = ""
            gate_voided += 1

    # ---- PASS 3: manual overrides (authoritative; see MANUAL_OVERRIDES) ----
    for player_name, pid in MANUAL_OVERRIDES.items():
        mask = p1["Player"] == player_name
        if not mask.any():
            continue                       # name not in this WAR vintage -> skip
        p1.loc[mask, "player_id"] = pid
        if pid in id_bio.index:
            p1.loc[mask, "birthdate"] = id_bio.loc[pid, "birthdate"]
            p1.loc[mask, "eliteprospects_id"] = id_bio.loc[pid, "eliteprospects_id"]
            p1.loc[mask, "nhl_id"] = id_bio.loc[pid, "nhl_id"]
        p1.loc[mask, "match_type"] = "manual"

    # ---- PASS 4: Elite Prospects birthdates for the pre-2018 retirees ----
    # Fills players PuckPedia never had. Birthdate is enough for age; these rows
    # carry no PuckPedia player_id, which is fine.
    # PuckPedia gave the column a datetime64 dtype; switch to object so EP's
    # string dates (and any malformed one) can be stored without a coercion crash.
    p1["birthdate"] = p1["birthdate"].astype(object)
    if os.path.exists(EP_BIRTHDATES_PATH):
        ep = pd.read_csv(EP_BIRTHDATES_PATH).dropna(subset=["birthdate"])
        ep_map = ep.drop_duplicates("war_name").set_index("war_name")["birthdate"].to_dict()
        for i in p1.index[p1["birthdate"].isna()]:
            nm = p1.at[i, "Player"]
            if nm in ep_map:
                p1.at[i, "birthdate"] = ep_map[nm]
                if p1.at[i, "match_type"] == "":
                    p1.at[i, "match_type"] = "ep"
    # hand-verified corrections OVERRIDE any EP value (fixes the scraper's wrong
    # picks, and fills the one name EP left unmatched)
    for player_name, bd in EP_BIRTHDATE_OVERRIDES.items():
        mask = p1["Player"] == player_name
        if mask.any():
            p1.loc[mask, "birthdate"] = bd
            p1.loc[mask, "match_type"] = "ep_fixed"

    # truly unmatched = nothing from any of the four passes
    p1.loc[p1["match_type"] == "", "match_type"] = "unmatched"

    # ---- attach the per-player birthdate back onto every WAR season-row ----
    lut = p1.set_index("Player")[["player_id", "birthdate", "eliteprospects_id",
                                  "nhl_id", "match_type"]]
    out = war.merge(lut, left_on="Player", right_index=True, how="left")

    # ---- compute age per season-row ----
    out["end_year"] = out["Season"].map(season_end_year)
    ages = out.apply(lambda r: compute_age(r["birthdate"], r["end_year"]), axis=1)
    out["age"] = [a[0] for a in ages]
    out["age_exact"] = [a[1] for a in ages]
    out = out.drop(columns=["end_year"])

    # ---- reporting ----
    war["sy"] = war["Season"].str[:2].astype(int).map(lambda y: 1900 + y if y > 50 else 2000 + y)
    last_seen = war.groupby("Player")["sy"].max()
    n_players = len(players)
    n_exact = (p1["match_type"] == "exact").sum()
    n_fuzzy = (p1["match_type"] == "fuzzy").sum()
    n_manual = (p1["match_type"] == "manual").sum()
    n_ep = (p1["match_type"] == "ep").sum()
    n_ep_fixed = (p1["match_type"] == "ep_fixed").sum()
    n_un = (p1["match_type"] == "unmatched").sum()
    miss = p1[p1["match_type"] == "unmatched"][["Player", "Position"]].copy()
    miss["last_season_seen"] = miss["Player"].map(last_seen)
    miss = miss.sort_values("last_season_seen", ascending=False)
    recent_miss = (miss["last_season_seen"] >= 2018).sum()

    record("=== age_join run log ===")
    record("WAR season-rows: %d  |  distinct WAR players: %d" % (len(war), n_players))
    record("Age convention: age on %02d-%02d of season-ending year" % (REFERENCE_MONTH, REFERENCE_DAY))
    record("")
    record("Pass 1 exact matches : %d" % n_exact)
    record("Pass 2 fuzzy matches : %d" % n_fuzzy)
    record("Pass 3 manual matches: %d" % n_manual)
    record("Pass 4 EP matches     : %d  (+ %d hand-corrected)" % (n_ep, n_ep_fixed))
    record("Implausible auto-matches voided by age gate: %d" % gate_voided)
    record("Unmatched players    : %d  (of which last seen 2018+: %d)" % (n_un, recent_miss))
    record("Player match rate    : %.1f%%" % (
        100 * (n_exact + n_fuzzy + n_manual + n_ep + n_ep_fixed) / n_players))
    record("Season-rows with age : %d / %d (%.1f%%)" % (
        out["age"].notna().sum(), len(out), 100 * out["age"].notna().mean()))
    record("")
    record("Collision resolutions (known same-name pairs):")
    for nm in ["Elias Pettersson", "Elias Pettersson(D)", "Sebastian Aho",
               "Connor Murphy", "Josh Anderson"]:
        r = p1[p1["Player"] == nm]
        if len(r):
            r = r.iloc[0]
            pid = r["player_id"]
            record("   %-22s pos=%s -> player_id=%s (%s)" % (
                nm, r["posgroup"], "NA" if pd.isna(pid) else int(pid), r["match_type"]))

    # ---- review item 1.8: identifiers carrying more than one player --------
    conf = id_name_conflicts(out)
    n_ids = conf["player_id"].nunique() if len(conf) else 0
    n_rows = int(conf["rows"].sum()) if len(conf) else 0
    n_names = conf["Player"].nunique() if len(conf) else 0
    record("")
    record("Identifier / name conflicts (review item 1.8):")
    record("   identifiers carrying more than one name: %d" % n_ids)
    record("   rows affected: %d   distinct players involved: %d" % (n_rows, n_names))
    record("   These change nothing today -- nothing joins to this file on the")
    record("   identifier. Any future join must go through")
    record("   join_on_id_and_name(), which matches on identifier AND name and")
    record("   raises if the two disagree.")
    if len(conf):
        conf.to_csv(OUT_ID_CONFLICTS, index=False)
        record("   written: %s" % OUT_ID_CONFLICTS)
        for pid, grp in list(conf.groupby("player_id"))[:6]:
            record("     id %s -> %s" % (int(pid), ", ".join(grp["Player"])))
    # Self-test: the guard must actually fire on this file's own conflicts.
    # A guard that cannot trigger is the failure mode item 1.5 was about.
    if len(conf):
        probe_id = conf["player_id"].iloc[0]
        wrong = conf[conf["player_id"] == probe_id]["Player"].tolist()
        left = pd.DataFrame({"player_id": [probe_id], "Player": [wrong[-1]]})
        right = pd.DataFrame({"player_id": [probe_id], "Player": [wrong[0]]})
        try:
            join_on_id_and_name(left, right)
            raise SystemExit("item 1.8 guard did NOT fire on a known conflict")
        except AssertionError:
            record("   guard self-test: fires correctly on a known conflict.")

    out.to_csv(OUT_WAR_AGE, index=False)
    miss.to_csv(OUT_MISSES, index=False)
    record("")
    record("Wrote: %s (%d rows), %s (%d rows), %s" % (
        OUT_WAR_AGE, len(out), OUT_MISSES, len(miss), OUT_LOG))
    with open(OUT_LOG, "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
