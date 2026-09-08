# =============================================================================
# draft_pick_linkage.py -- Phase 3a, Step 1: draft record pull + player linkage
# SCRIPT_VERSION = 1.1  (2026-07-14)
#
# WHAT THIS DOES, IN PLAIN ENGLISH
# --------------------------------
# The draft-pick yield curve needs to know, for every pick made since 2005,
# WHICH player was taken and WHERE that player's career production lives in
# our data. This script does only that -- the linkage -- and produces a file
# with one row per pick, each row resolved to one of five statuses:
#
#   matched_id          -> linked by NHL player ID + name agreement (safest)
#   matched_name        -> linked by exact name, after two safety guards
#   matched_alias       -> linked via a hand-verified name-variant table
#   excluded_merged_name-> the WAR file mixes two humans under this name;
#                          per the standing project rule we EXCLUDE, never guess
#   zero_no_nhl_record  -> the pick produced no NHL career (a bust) OR was
#                          invalidated (player unsigned, re-entered the draft).
#                          These are REAL ZEROS, not missing data -- they are
#                          the bust mass the yield curve exists to measure.
#
# The output's `war_names` column can hold MULTIPLE pipe-separated names,
# because WAR.csv sometimes spells one human two ways across seasons
# (Nick Paul / Nicholas Paul). Step 2 must attach season rows for EVERY
# listed name, matching on normalized names (accents stripped), and must
# SUM goalie rows within a season (Goalies_WAR splits traded goalies into
# one row per team).
#
# WHY THE GUARDS EXIST (each one caught a real error during development)
# ----------------------------------------------------------------------
# 1. ID stage + NAME AGREEMENT: WAR_with_age.csv's nhl_id column is polluted
#    -- its fuzzy/EP-fixed age-join stages assigned 33 IDs to the wrong
#    person's rows (Rick Nash's career carries Riley Nash's ID; Todd
#    Bertuzzi carries Tyler's; Jeff Schultz carries Justin's...). Every
#    polluted ID still contains the CORRECT name among its candidates, so
#    the rule is: an ID match only resolves to the candidate name that
#    normalize-equals the pick's own name. No agreement -> the ID stage
#    fails and the name stages take over. A naive ID join would have handed
#    Rick Nash's career to the 2007 #21 pick.
# 2. ID-first at all: players whose careers ended before ~2015 (PuckPedia
#    coverage) have WAR rows but NO ID in WAR_with_age -- including
#    #1-overall Nail Yakupov. Hence the name fallback stages.
# 3. Collision blocklist: some names belong to TWO different drafted players
#    (Erik Karlsson 2008 + 2012; Josh Anderson 2012 + 2016). Any name
#    drafted more than once in 2005-2026, plus the project's known
#    same-name list, is blocked from the name stage.
# 4. Temporal guard: a drafted bust can share a name with an UNDRAFTED or
#    pre-2005 NHLer (2016 pick "Ryan Jones" vs the 2004-drafted Ryan Jones).
#    A career cannot begin BEFORE its draft year; exact-name matches whose
#    first WAR season predates the draft are rejected as different humans.
# 5. Alias table: ~19 real careers hide behind first-name variants
#    (Alexander->Alex, Mathew->Matt, Evgenii->Evgeny). Fuzzy matching is NOT
#    used -- a last-name+initial scan also "matched" brothers and
#    near-namesakes (Emil vs Elias Pettersson, Vincent Dunn 2013 vs the real
#    Vince Dunn 2015, Mathieu Roy vs Matt Roy). Every alias is pick-specific
#    and was verified by hand. Do not add entries by pattern.
# 6. Variant unions: 12 verified cases where WAR.csv spells ONE human two
#    ways; the union table adds the secondary spelling so careers attach in
#    full. Same discipline: pick-keyed, hand-verified, never pattern-based
#    (the pollution pairs above look superficially like spelling variants).
#
# MERGED-NAME EXCLUSIONS (standing project rule: exclude until split by ID)
# -------------------------------------------------------------------------
# WAR.csv merges two different humans under one name for Ryan Johnson and
# Nathan Smith (known). This build DISCOVERED A THIRD: Erik Gustafsson --
# the 13-14 PHI row belongs to the undrafted b.1988 player; 15-16 onward is
# the b.1992 player drafted 2012 #93. Affected picks are excluded.
#
# NOTE: the two VAN Elias Petterssons are ALREADY separated in WAR.csv
# ("Elias Pettersson" vs "Elias Pettersson(D)") and the "(D)" survives
# normalization -- no action needed, recorded here so nobody re-checks.
#
# INPUTS (paths configurable below)
#   - NHL Records draft API (cached locally as JSON per year; offline re-runs)
#   - WAR.csv           (Bacon skater WAR; names only; seasons '07-08'...)
#   - WAR_with_age.csv  (same rows + nhl_id where the age join succeeded)
#   - Goalies_WAR.csv   (Bacon goalie WAR; names only; per-team split rows)
#
# OUTPUT
#   - draft_pick_linkage.csv  (one row per pick, 2005-2026)
#   - console diagnostics: match rates by pick bucket, guard trips, residuals
# =============================================================================

import json
import os
import re
import time
import unicodedata
import urllib.request

import pandas as pd

from dotenv import load_dotenv

load_dotenv()

SCRIPT_VERSION = "1.1"
print(f"draft_pick_linkage.py SCRIPT_VERSION {SCRIPT_VERSION}")

# ----------------------------------------------------------------------------
# CONFIG -- all paths come from .env (see .env.example). SOURCE_DIR holds the
# vendor WAR files (read-only); OUTPUT_DIR is the generated tree. WAR_with_age
# (age_join.py) and draft_pick_linkage.csv are generated; the draft-API JSON
# cache lands under OUTPUT_DIR too so nothing is written to the working dir.
# ----------------------------------------------------------------------------
SOURCE_DIR = os.environ["SOURCE_DIR"]
OUTPUT_DIR = os.environ["OUTPUT_DIR"]

CACHE_DIR  = os.path.join(OUTPUT_DIR, "draft_raw")   # per-year JSON cache lands here
OUT_PATH   = os.path.join(OUTPUT_DIR, "draft_pick_linkage.csv")

WAR_PATH   = os.path.join(SOURCE_DIR, "WAR.csv")
WAGE_PATH  = os.path.join(OUTPUT_DIR, "WAR_with_age.csv")
GW_PATH    = os.path.join(SOURCE_DIR, "Goalies_WAR.csv")

PULL_YEARS = range(2005, 2027)        # full pull; the CURVE fits on 2007-2019
FIT_LO, FIT_HI = 2007, 2019           # fitting window for the diagnostics

# The API rejects Python's default user agent (403); a browser UA works.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# ----------------------------------------------------------------------------
# Known same-name hazards, from the project's standing flags + this build.
# ----------------------------------------------------------------------------
KNOWN_COLLISION_NAMES = {
    "sebastian aho", "elias pettersson", "connor murphy", "josh anderson",
    # merged-name rows (two humans under one WAR.csv name):
    "ryan johnson", "nathan smith",
    "erik gustafsson",   # NEW discovery this build -- see header
}

MERGED_NAME_EXCLUDED_PICKS = {
    (2019, 31):  "Ryan Johnson (BUF) -- WAR.csv merges two Ryan Johnsons",
    (2012, 93):  "Erik Gustafsson (EDM, b.1992) -- WAR.csv merges with the "
                 "undrafted b.1988 Erik Gustafsson (13-14 PHI row)",
}

# Hand-verified alias table: pick -> exact WAR.csv Player string. Every entry
# checked against career timing (first WAR season >= draft year) and identity.
SKATER_ALIASES = {
    (2007,  71): "Evgeny Dadonov",
    (2009,  73): "Alex Urbom",
    (2010,   8): "Alex Burmistrov",
    (2010,  36): "Alex Petrovic",
    (2011,  82): "Nick Shore",
    (2012,   7): "Matt Dumba",
    (2013,  14): "Alex Wennberg",
    (2013,  61): "Zach Sanford",
    (2015, 115): "Alex Carrier",
    (2016,  85): "Josh Mahura",
    (2017,  23): "Pierre-olivier Joseph",
    (2017,  45): "Alex Texier",
    (2017,  48): "Alex Volkov",
    (2017,  50): "Max Comtois",
    (2017, 139): "Sebastian Aho Swe",   # the Swedish D (NYI); the CAR star is a different pick
    (2018,  31): "Alex Alexeyev",
    (2018,  38): "Alex Romanov",
    (2019, 129): "Arseny Gritsyuk",
}
GOALIE_ALIASES = {
    (2011,  49): "Chris Gibson",        # drafted as Christopher Gibson
}

# Variant unions: ONE human whose WAR.csv rows appear under TWO spellings.
# Key = the pick; value = the SECONDARY WAR.csv Player string(s) to attach in
# addition to whatever the pick resolves to. Verified by hand (team/season
# continuity). Accent-only variants (Matej Blumel / Matěj Blümel) need no
# entry -- normalized-name attachment unifies them automatically.
VARIANT_UNIONS = {
    (2013, 101): ["Nicholas Paul"],          # resolves to Nick Paul
    (2015,  85): ["Thomas Novak"],           # resolves to Tommy Novak
    (2014, 210): ["Jacob Middleton"],        # resolves to Jake Middleton
    (2015,  92): ["William Borgen"],         # resolves to Will Borgen
    (2016, 133): ["Max Lajoie"],             # resolves to Maxime Lajoie
    (2017, 185): ["Alex Chmelevski"],        # resolves to Sasha Chmelevski
    (2017, 113): ["Alexei Toropchenko"],     # resolves to Alexey Toropchenko
    (2018,  54): ["Benoit-olivier Groulx"],  # resolves to Bo Groulx
    (2019, 124): ["Nicholas Abruzzese"],     # resolves to Nick Abruzzese
    (2015,  30): ["Nicholas Merkley"],       # resolves to Nick Merkley
    (2017, 200): ["Samuel Walker"],          # resolves to Sammy Walker (NOT Scott Walker)
    (2021,  60): ["Janis Moser"],            # resolves to J.J. Moser (outside fit window)
}

# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def norm(s):
    """Normalize a name for comparison: strip accents, lowercase, drop
    punctuation. 'Matěj Blümel' == 'Matej Blumel'; 'Elias Pettersson(D)'
    stays distinct from 'Elias Pettersson' (the trailing d survives)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()

def season_start(s):
    """WAR season strings come as '07-08'. Return the starting year as int."""
    y = int(str(s).split("-")[0])
    return y if y > 1900 else 2000 + y

# ----------------------------------------------------------------------------
# STEP 1 -- pull (or re-use cached) draft records, one JSON per year
# ----------------------------------------------------------------------------
os.makedirs(CACHE_DIR, exist_ok=True)
rows = []
for yr in PULL_YEARS:
    cache = os.path.join(CACHE_DIR, f"draft_{yr}.json")
    if not os.path.exists(cache):
        url = f"https://records.nhl.com/site/api/draft?cayenneExp=draftYear={yr}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
        # Guard: the endpoint must return a sane number of picks for a year.
        assert 180 <= len(payload["data"]) <= 260, \
            f"{yr}: implausible pick count {len(payload['data'])} -- API change?"
        with open(cache, "w") as f:
            json.dump(payload, f)
        time.sleep(0.4)                       # be polite to the endpoint
    with open(cache) as f:
        rows.extend(json.load(f)["data"])

draft = pd.DataFrame(rows)[[
    "draftYear", "roundNumber", "overallPickNumber", "pickInRound",
    "playerId", "playerName", "position", "birthDate",
    "removedOutright", "removedOutrightWhy", "triCode",
]]
print(f"[pull] {len(draft)} picks, {draft['draftYear'].min()}-{draft['draftYear'].max()}")

assert draft.duplicated(["draftYear", "overallPickNumber"]).sum() == 0, \
    "duplicate (year, overall) slots -- inspect the raw pull"
id_cov = draft["playerId"].notna().mean()
assert id_cov > 0.99, f"playerId coverage fell to {id_cov:.1%} -- API change?"

draft["name_n"]    = draft["playerName"].apply(norm)
draft["is_goalie"] = draft["position"].eq("G")   # 'F', hybrids, NaN => skater side

# ----------------------------------------------------------------------------
# STEP 2 -- load WAR sources and precompute the lookups the guards need
# ----------------------------------------------------------------------------
war  = pd.read_csv(WAR_PATH)
wage = pd.read_csv(WAGE_PATH)
gw   = pd.read_csv(GW_PATH)

war["name_n"] = war["Player"].apply(norm)
war["syear"]  = war["Season"].apply(season_start)
gw["name_n"]  = gw["Goalie"].apply(norm)
gw["syear"]   = gw["Season"].apply(season_start)

# ID -> the SET of Player names carried under that nhl_id in WAR_with_age.
# Multiple names per ID is a known defect of the age join (33 polluted IDs
# at build time): fuzzy stages stamped the wrong person's ID onto lookalike
# names. Resolution below requires name agreement, which defuses all of them.
_w = wage.loc[wage["nhl_id"].notna(), ["nhl_id", "Player"]].copy()
_w["nhl_id"] = _w["nhl_id"].astype(int)
id_to_names = _w.groupby("nhl_id")["Player"].agg(lambda s: sorted(set(s)))
n_polluted = (id_to_names.str.len() > 1).sum()
print(f"[guards] {n_polluted} nhl_ids carry multiple names in WAR_with_age "
      "(known age-join pollution; name-agreement rule handles them)")

war_first_season = war.groupby("name_n")["syear"].min()   # temporal guard
gw_first_season  = gw.groupby("name_n")["syear"].min()
war_names        = set(war["name_n"])
gw_names         = set(gw["name_n"])
war_exact        = set(war["Player"])

# Blocklist for the name stage: known hazards PLUS any name drafted twice.
multi_drafted = set(
    draft[draft["removedOutright"] == "N"]
    .groupby("name_n")["playerId"].nunique().loc[lambda s: s > 1].index
)
blocked_names = KNOWN_COLLISION_NAMES | multi_drafted
print(f"[guards] {len(blocked_names)} names blocked from the exact-name stage")

# ----------------------------------------------------------------------------
# STEP 3 -- resolve every pick, walking the stages in safety order
# ----------------------------------------------------------------------------
def resolve(row):
    """Return (link_status, primary_war_name_or_None)."""
    key = (row["draftYear"], row["overallPickNumber"])

    # Invalidated picks: the selection was voided (player unsigned,
    # re-entered a later draft). The pick was SPENT and returned nothing --
    # a true zero. The real career credits the later, valid selection.
    if row["removedOutright"] == "Y":
        return "zero_no_nhl_record", None

    # Merged-name exclusions override everything (never attach mixed rows).
    if key in MERGED_NAME_EXCLUDED_PICKS:
        return "excluded_merged_name", None

    if row["is_goalie"]:
        # ---- goalie side: Goalies_WAR carries no IDs, so name stages only ----
        if key in GOALIE_ALIASES:
            return "matched_alias", GOALIE_ALIASES[key]
        n = row["name_n"]
        if n in gw_names and n not in blocked_names:
            if gw_first_season[n] >= row["draftYear"]:   # temporal guard
                return "matched_name", gw.loc[gw["name_n"] == n, "Goalie"].iloc[0]
        return "zero_no_nhl_record", None

    # ---- skater side ----
    # Stage 1: ID join WITH NAME AGREEMENT. The ID's candidate names must
    # include one that normalize-equals the pick's own name; that candidate
    # wins. Polluted IDs (wrong person's rows stamped with this ID) always
    # ALSO carry the right name, so agreement discards the pollution. If no
    # candidate agrees, the ID evidence is unusable -- fall through.
    pid = row["playerId"]
    if pd.notna(pid) and int(pid) in id_to_names.index:
        agreeing = [nm for nm in id_to_names[int(pid)] if norm(nm) == row["name_n"]]
        if len(agreeing) == 1:
            return "matched_id", agreeing[0]

    # Stage 2: hand-verified aliases (checked before exact-name on purpose:
    # they exist precisely because exact-name cannot see these players).
    if key in SKATER_ALIASES:
        alias = SKATER_ALIASES[key]
        assert alias in war_exact, f"alias target '{alias}' not in WAR.csv"
        return "matched_alias", alias

    # Stage 3: exact-name, with the collision blocklist + temporal guard.
    n = row["name_n"]
    if n in war_names and n not in blocked_names:
        if war_first_season[n] >= row["draftYear"]:
            return "matched_name", war.loc[war["name_n"] == n, "Player"].iloc[0]

    # Nothing left: no NHL production record => a bust (real zero).
    return "zero_no_nhl_record", None

res = draft.apply(resolve, axis=1, result_type="expand")
draft["link_status"], draft["war_name_primary"] = res[0], res[1]

# Append variant-union secondary spellings, then pipe-join into `war_names`.
def full_names(row):
    if row["war_name_primary"] is None or pd.isna(row["war_name_primary"]):
        return None
    names = [row["war_name_primary"]]
    extra = VARIANT_UNIONS.get((row["draftYear"], row["overallPickNumber"]), [])
    for e in extra:
        assert e in war_exact, f"variant-union target '{e}' not in WAR.csv"
        names.append(e)
    return "|".join(names)

draft["war_names"] = draft.apply(full_names, axis=1)

# ----------------------------------------------------------------------------
# STEP 4 -- integrity guards on the finished linkage
# ----------------------------------------------------------------------------
# (a) A WAR name (any spelling) may serve at most ONE pick; otherwise one
#     career would be double-credited.
served = draft.loc[draft["war_names"].notna(), ["draftYear", "overallPickNumber",
                                                "playerName", "war_names"]].copy()
served = served.assign(nm=served["war_names"].str.split("|")).explode("nm")
dup = served[served.duplicated("nm", keep=False)]
assert len(dup) == 0, "one WAR career resolved to multiple picks:\n" + dup.to_string()

# (b) Every alias must actually have fired.
for (yr, ov), tgt in {**SKATER_ALIASES, **GOALIE_ALIASES}.items():
    st = draft.loc[(draft["draftYear"] == yr) & (draft["overallPickNumber"] == ov),
                   "link_status"]
    assert len(st) == 1, f"alias pick ({yr},{ov}) not found in the pull"
    assert st.iloc[0] in ("matched_alias", "matched_id"), \
        f"alias pick ({yr},{ov}) resolved as {st.iloc[0]} -- inspect"

# (c) Every variant-union pick must be matched (a union on an unmatched pick
#     means its key is wrong).
for (yr, ov) in VARIANT_UNIONS:
    st = draft.loc[(draft["draftYear"] == yr) & (draft["overallPickNumber"] == ov),
                   "link_status"].iloc[0]
    assert st.startswith("matched"), f"variant-union pick ({yr},{ov}) is {st}"

# ----------------------------------------------------------------------------
# STEP 5 -- diagnostics (reported on the FITTING window, 2007-2019)
# ----------------------------------------------------------------------------
BUCKETS = [(1,1),(2,2),(3,5),(6,10),(11,20),(21,32),(33,50),(51,100),(101,150),(151,224)]
def bucket(n):
    for lo, hi in BUCKETS:
        if lo <= n <= hi:
            return f"{lo}-{hi}"
    return "225+"

fit = draft[draft["draftYear"].between(FIT_LO, FIT_HI)].copy()
fit["bucket"]  = fit["overallPickNumber"].apply(bucket)
fit["matched"] = fit["link_status"].str.startswith("matched")

print(f"\n[diag] fitting window {FIT_LO}-{FIT_HI}: {len(fit)} picks")
print(fit["link_status"].value_counts().to_string())

order = [f"{lo}-{hi}" for lo, hi in BUCKETS]
tbl = (fit[~fit["is_goalie"]].groupby("bucket")["matched"]
       .agg(n="count", match_rate="mean").reindex(order).round(3))
print("\n[diag] skater match rate by pick bucket "
      "(unmatched = never produced NHL WAR = the bust mass):")
print(tbl.to_string())

g = fit[fit["is_goalie"]]
print(f"\n[diag] goalies: {len(g)} picks, "
      f"{g['matched'].sum()} matched ({g['matched'].mean():.1%}) -- "
      "low rates late in the draft are genuine bust mass")

top_um = fit[(~fit["matched"]) & (fit["link_status"] != "excluded_merged_name")
             & (fit["overallPickNumber"] <= 30) & (~fit["is_goalie"])]
print(f"\n[diag] top-30 skater picks with no NHL record ({len(top_um)}) -- "
      "each should be a recognizable bust; anything surprising here means a "
      "linkage gap, stop and investigate:")
print(top_um[["draftYear", "overallPickNumber", "playerName"]].to_string(index=False))

# ----------------------------------------------------------------------------
# STEP 6 -- write the output
# ----------------------------------------------------------------------------
out_cols = ["draftYear", "roundNumber", "overallPickNumber", "pickInRound",
            "playerId", "playerName", "position", "is_goalie", "birthDate",
            "triCode", "removedOutright", "link_status", "war_names"]
draft[out_cols].to_csv(OUT_PATH, index=False)
print(f"\n[done] v{SCRIPT_VERSION}: wrote {OUT_PATH} ({len(draft)} picks)")
print("[note] Step 2 must: (1) attach WAR rows for EVERY pipe-separated name "
      "in war_names, matching on normalized names; (2) SUM goalie rows "
      "within (name, Season) -- Goalies_WAR splits traded goalies by team.")
