# =============================================================================
# draft_yield_curve.py -- Phase 3a, Step 2: the draft-pick yield curve
# SCRIPT_VERSION = 1.0  (2026-07-14)
#
# WHAT THIS DOES, IN PLAIN ENGLISH
# --------------------------------
# For every draft pick in the fitting cohorts (2007-2017), this script adds
# up the surplus value the drafted player actually delivered to the team
# that held his cheap years, then averages those totals within pick-number
# buckets. The result is the yield curve: one expected-surplus number per
# bucket, in the SAME currency as the player pillar (cap-share priced at
# the locked market rate), convertible to dollars at any season's cap.
#
# THE UNIT: SUMMED CAP-SHARE (why there is no explicit discounting line)
# ----------------------------------------------------------------------
# Under the project's locked conventions, discounting cancels exactly:
# D11 grows future caps at 3%/yr and D17 discounts at the same 3%, so a
# flow worth s% of the cap in season D+k is worth (s% x cap_0 x 1.03^k)
# / 1.03^k = s% x cap_0 in draft-day dollars. Therefore the curve's
# primitive is the plain SUM of per-season cap-share surpluses over the
# window, and pricing a pick in any valuation season is just
# (curve share-sum) x (that season's cap ceiling). The 3% discount is not
# skipped -- it is applied and cancels by construction (the D17 "mesh").
#
# WINDOW: D+1 .. D+9 (season_start in [draftYear, draftYear+8])
#   Nine league seasons beginning with the season right after the draft.
#   Chosen (with Thomas, 2026-07-14) over a status-based control-window to
#   avoid reconstructing contract status for pre-2015 cohorts; widened from
#   7 to 9 seasons so late arrivers (NCAA/Europe paths) are not undercounted.
#   Seasons with no NHL WAR row contribute zero value AND zero cost (the
#   player is in junior/AHL/Europe: no NHL production, no NHL cap charge).
#
# FITTING COHORTS: 2007-2017 (11 cohorts, complete windows only)
#   2005-06 are left-truncated (WAR coverage starts 2007-08); 2018+ are
#   right-censored under the D+9 window (draftYear+8 must be <= 2025).
#   NOTE: the original batch note said 2007-2019 -- that was arithmetic for
#   a 7-season window and is corrected here; the locked principle is
#   "complete windows only."
#
# PER-SEASON SURPLUS (the locked player-pillar currency)
#   Skater value share  = alpha + beta x WAR   (D20 refit: 0.01831864 /
#                         0.01924854), floored at that season's league
#                         minimum as a share of that season's cap (D10).
#   Goalie value share  = alpha_G + beta_G x gWAR (D20: 0.01391356 /
#                         0.01059314); NO floor -- the locked goalie engine
#                         applies none, and the curve mirrors the engines.
#   Goalie WAR is SUMMED within (player, season): Goalies_WAR splits traded
#   goalies into one row per team.
#
#   ELC seasons (the first N NHL seasons with GP >= 10, where N follows the
#   CBA's signing-age schedule -- 3 years if the player is <=21 at his first
#   counted season, 2 at 22-23, 1 at 24+; age taken as of Sept 15, the CBA
#   convention, from the draft record's birthdate). The age rule matters:
#   KHL/NCAA late arrivers (Kaprizov, Sorokin) sign SHORT ELCs, and a flat
#   3-year rule priced their big second contracts at $925K -- inflating
#   exactly the mid/late-round slots where late arrivers cluster. v1.0 had
#   the flat rule; the age schedule was added after Kaprizov outranked
#   McDavid in the spot-check.
#     cost share = (ELC maximum for the draft-year class) / (season cap).
#     The slotted maximum is used for every pick -- late picks sign under
#     the max, so this OVERSTATES their cost and errs conservative on pick
#     value; performance-bonus overages for stars are ignored (understates
#     star ELC cost) -- both documented, both small.
#     Cameo seasons (GP < 10, before the 3rd ELC year burns): cost AND the
#     D10 floor prorate by GP/82 -- a 3-game callup neither pays a full
#     year's ELC nor "produces" a full year of league-minimum value. This
#     mirrors slide-rule reality (sub-10-GP seasons don't burn ELC years).
#
#   POST-ELC seasons -- PRIMARY rule (A), agreed 2026-07-14:
#     cost share = the market-predicted share for the production actually
#     delivered = the value share itself. Surplus is therefore ZERO BY
#     CONSTRUCTION in post-ELC years. This is not an accident: the locked
#     D7 finding is that the market prices RFA and UFA production at one
#     statistically indistinguishable rate, so a player paid "the going
#     rate" post-ELC generates no expected surplus. The curve under (A) is
#     effectively an ELC-surplus curve. FLAGGED for review -- see the
#     sensitivity below and the session summary.
#
#   POST-ELC seasons -- SENSITIVITY (B), reported alongside:
#     cost share = market-predicted share on the player's TRAILING
#     production (60/40 blend of the two prior seasons, >=10 GP to count,
#     D20-prorated -- the engine's own anchor convention). Realized surplus
#     then = beta x (realized - trailing): teams paying on yesterday's
#     production capture the improvement of ascending players. Skaters
#     only; goalie post-ELC years stay at rule (A) in both variants.
#
# SHORT-SEASON PRORATION (extends D20's principle to the pre-2018 era)
#   Value-side WAR for 2012-13 (48 games), 2019-20 (~70), 2020-21 (56) is
#   scaled to an 82-game basis (x82/48, x82/70, x82/56): the curve is a
#   STRUCTURAL object (one fixed curve, agreed 2026-07-14) and mechanical
#   schedule deflation is not signal about slot quality. 82/48 is a NEW
#   factor (12-13 predates D20's window) -- flagged for the decision log.
#   Costs are NOT prorated: cap accounting charged full AAV against the
#   (prorated) cap in those seasons; shares stay annualized ratios.
#
# EXOGENOUS CBA CONSTANTS (verified via web sources, 2026-07-14; all are
# public, pre-determined figures -- no outcome data, no identification risk)
#   - Cap ceilings 2007-08..2025-26: Kukla's Korner/CapWages histories,
#     mutually consistent; 2012-13 uses the $60.0M accounting ceiling.
#   - League minimums: PuckPedia (2012+); 2007-2011 ($475/475/500/500/525K)
#     cross-checked by arithmetic vs Puck Report cap-percentage comparisons.
#   - ELC maxima by draft class: $850K (2005-06), $875K (2007-08),
#     $900K (2009-10), $925K (2011-2021), $950K (2022-23), $975K (2024-25);
#     2011+ press-verified, 2007-2010 validated against known #1-overall
#     ELC bases (Kane $875K, Tavares $900K, Hall $900K).
#
# INPUTS:  draft_pick_linkage.csv (step 1), WAR.csv, Goalies_WAR.csv
# OUTPUTS: draft_pick_outcomes.csv (per-pick audit panel)
#          draft_yield_curve.csv   (the curve: one row per bucket)
# =============================================================================

import os
import re
import unicodedata

import numpy as np
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

SCRIPT_VERSION = "1.1"
print(f"draft_yield_curve.py SCRIPT_VERSION {SCRIPT_VERSION}")
rng = np.random.default_rng(31415)          # fixed seed: reproducible bootstrap

# ----------------------------------------------------------------------------
# CONFIG -- paths from .env (see .env.example). SOURCE_DIR: vendor WAR files +
# draft_slot_baseline.csv (read-only). OUTPUT_DIR: generated tree -- the step-1
# linkage this reads, and the panel + curve this writes.
# ----------------------------------------------------------------------------
SOURCE_DIR   = os.environ["SOURCE_DIR"]
OUTPUT_DIR   = os.environ["OUTPUT_DIR"]
LINKAGE_PATH = os.path.join(OUTPUT_DIR, "draft_pick_linkage.csv")
WAR_PATH     = os.path.join(SOURCE_DIR, "WAR.csv")
GW_PATH      = os.path.join(SOURCE_DIR, "Goalies_WAR.csv")
OUT_PANEL    = os.path.join(OUTPUT_DIR, "draft_pick_outcomes.csv")
OUT_CURVE    = os.path.join(OUTPUT_DIR, "draft_yield_curve.csv")

FIT_LO, FIT_HI = 2007, 2017     # complete-window cohorts under D+9 (see header)
WINDOW_LEN     = 9              # D+1..D+9: season_start in [year, year+8]

# --- Locked market rates (source: PROJECT_STATE.md, D20 prorated refit) -----
# ITEM 4.3(a) / 4.5: the censored interaction rate replaces the old
# single-slope least-squares one. Censored at the league minimum (item 3.3),
# straight in production (item 3.2 rejected the bend out of sample), contract
# length omitted (item 2.1 found term buys no realized production), and the
# position entering as a slope difference with a common intercept (item 3.4).
OLD_RATE_PRE_4_5 = (0.01831864, 0.01924854)   # superseded 2026-07-27
ALPHA            = 0.0132478230               # $1.2652M at the 2025-26 ceiling
BETA             = 0.0212322891               # $2.0277M per win, forwards
BETA_D_ADD       = 0.0028702824               # $0.2741M per win extra, defence
BETA_D           = BETA + BETA_D_ADD          # $2.3018M per win, defencemen


def skater_slope(is_d):
    """Price of one win in cap share. Defencemen carry a steeper slope and the
    SAME intercept: at zero measured wins the market pays the two positions
    alike, which is why position enters as an interaction, not a constant."""
    return BETA_D if is_d else BETA

ALPHA_G, BETA_G = 0.01391356, 0.01059314    # goalie cap-share = aG + bG*gWAR

MIN_GP = 10          # engine convention: a season needs >=10 GP as WAR signal
W_T1, W_T2 = 0.6, 0.4                        # locked trailing 60/40 blend

# --- Verified CBA constants (see header for sources) -------------------------
CAP_CEILING = {   # $M by season start year
    2007: 50.3, 2008: 56.7, 2009: 56.8, 2010: 59.4, 2011: 64.3,
    2012: 60.0, 2013: 64.3, 2014: 69.0, 2015: 71.4, 2016: 73.0,
    2017: 75.0, 2018: 79.5, 2019: 81.5, 2020: 81.5, 2021: 81.5,
    2022: 82.5, 2023: 83.5, 2024: 88.0, 2025: 95.5,
}
LEAGUE_MIN = {    # $ by season start year (base salary)
    2007: 475_000, 2008: 475_000, 2009: 500_000, 2010: 500_000,
    2011: 525_000, 2012: 525_000, 2013: 550_000, 2014: 550_000,
    2015: 575_000, 2016: 575_000, 2017: 650_000, 2018: 650_000,
    2019: 700_000, 2020: 700_000, 2021: 750_000, 2022: 750_000,
    2023: 775_000, 2024: 775_000, 2025: 775_000,
}
ELC_MAX = {}      # $ by DRAFT year (the class's slotted maximum)
for y in (2005, 2006):              ELC_MAX[y] = 850_000
for y in (2007, 2008):              ELC_MAX[y] = 875_000
for y in (2009, 2010):              ELC_MAX[y] = 900_000
for y in range(2011, 2022):         ELC_MAX[y] = 925_000
for y in (2022, 2023):              ELC_MAX[y] = 950_000
for y in (2024, 2025):              ELC_MAX[y] = 975_000

# Short seasons scaled to an 82-game basis on the VALUE side (see header).
PRORATE = {2012: 82/48, 2019: 82/70, 2020: 82/56}

BUCKETS = [(1,1),(2,2),(3,5),(6,10),(11,20),(21,32),(33,50),(51,100),(101,150),(151,224)]

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()

def season_start(s):
    y = int(str(s).split("-")[0])
    return y if y > 1900 else 2000 + y

def bucket(n):
    for lo, hi in BUCKETS:
        if lo <= n <= hi:
            return f"{lo}-{hi}"
    return "225+"

# ----------------------------------------------------------------------------
# STEP 1 -- load inputs; build one season table per position group
# ----------------------------------------------------------------------------
link = pd.read_csv(LINKAGE_PATH)
war  = pd.read_csv(WAR_PATH)
gw   = pd.read_csv(GW_PATH)

assert {"war_names", "link_status"}.issubset(link.columns), \
    "linkage file schema unexpected -- regenerate with draft_pick_linkage.py v1.1+"

war["name_n"] = war["Player"].apply(norm)
war["syear"]  = war["Season"].apply(season_start)
war["war_82"] = war["WAR"] * war["syear"].map(PRORATE).fillna(1.0)   # value-side proration

# Goalies: SUM within (name, season) first -- per-team split rows -- then prorate.
gw["name_n"] = gw["Goalie"].apply(norm)
gw["syear"]  = gw["Season"].apply(season_start)
g_seas = (gw.groupby(["name_n", "syear"], as_index=False)
            .agg(GP=("GP", "sum"), gWAR=("WAR", "sum")))
g_seas["war_82"] = g_seas["gWAR"] * g_seas["syear"].map(PRORATE).fillna(1.0)

# Skater seasons keyed by normalized name (this also unifies accent variants
# like Matej Blumel / Matěj Blümel automatically).
s_seas = (war.groupby(["name_n", "syear"], as_index=False)
             .agg(GP=("GP", "sum"), sWAR=("WAR", "sum"), war_82=("war_82", "sum")))

cap_share_min = {y: LEAGUE_MIN[y] / (CAP_CEILING[y] * 1e6) for y in CAP_CEILING}

# ----------------------------------------------------------------------------
# STEP 2 -- walk every fitting-cohort pick through its D+1..D+9 window
# ----------------------------------------------------------------------------
fit = link[link["draftYear"].between(FIT_LO, FIT_HI)].copy()
print(f"[fit] cohorts {FIT_LO}-{FIT_HI}: {len(fit)} picks "
      f"({(fit['link_status']=='excluded_merged_name').sum()} merged-name exclusions dropped)")
fit = fit[fit["link_status"] != "excluded_merged_name"]
fit["birth_dt"] = pd.to_datetime(fit["birthDate"], errors="coerce")

rows = []
N_POS_BLANK = [0]        # ITEM 4.3(a): blank-position rows, reported below
for _, p in fit.iterrows():
    yr        = int(p["draftYear"])
    window    = range(yr, yr + WINDOW_LEN)          # season_start values D+1..D+9
    elc_cost  = ELC_MAX[yr]
    is_goalie = bool(p["is_goalie"])
    # ITEM 4.3(a): the rate is now position-dependent. The linkage file's
    # `position` column carries "D" for defencemen; a handful of rows are
    # blank and are treated as forwards, counted in the run log below.
    _pos_raw = p.get("position", None)
    is_d = (str(_pos_raw).strip().upper() == "D")
    if pd.isna(_pos_raw) and not is_goalie:
        N_POS_BLANK[0] += 1
    _slope = skater_slope(is_d)

    # Collect the player's seasons inside the window (empty for busts).
    if pd.isna(p["war_names"]):
        seasons = pd.DataFrame(columns=["syear", "GP", "war_82"])
    else:
        keys = {norm(n) for n in str(p["war_names"]).split("|")}
        src  = g_seas if is_goalie else s_seas
        seasons = (src[src["name_n"].isin(keys) & src["syear"].isin(window)]
                   .groupby("syear", as_index=False)
                   .agg(GP=("GP", "sum"), war_82=("war_82", "sum")))

    # For sensitivity (B): trailing anchor needs prior-season rows even from
    # OUTSIDE the window (a D+1 season's anchor looks at D-1/D0 -- rare) --
    # pull the player's full season history once.
    if not is_goalie and pd.notna(p["war_names"]):
        keys = {norm(n) for n in str(p["war_names"]).split("|")}
        # aggregate across spelling variants FIRST: a union player can
        # have rows under both spellings in one season (trade splits)
        hist = (s_seas[s_seas["name_n"].isin(keys)]
                .groupby("syear").agg(GP=("GP", "sum"),
                                      war_82=("war_82", "sum")))
    else:
        hist = None

    # CBA signing-age schedule for ELC length (3 / 2 / 1 years). Age is
    # taken as of Sept 15 of the player's FIRST GP>=10 season -- a proxy for
    # signing age that is exact for late arrivers (they sign when they come
    # over) and correct for junior-path players (signed young -> 3 years).
    elc_len = 3
    if pd.notna(p["birth_dt"]) and not seasons.empty:
        burn_seasons = seasons.loc[seasons["GP"] >= MIN_GP, "syear"]
        if len(burn_seasons):
            first = int(burn_seasons.min())
            age = (pd.Timestamp(year=first, month=9, day=15)
                   - p["birth_dt"]).days / 365.25
            elc_len = 3 if age <= 21.99 else (2 if age <= 23.99 else 1)

    elc_burned   = 0
    surplus_A    = 0.0      # primary: post-ELC surplus = 0 by construction
    surplus_B    = 0.0      # sensitivity: post-ELC cost on trailing anchor
    elc_component = 0.0     # ELC-year surplus (identical in A and B)
    n_nhl_seasons = 0

    for sy in window:
        row = seasons[seasons["syear"] == sy]
        if row.empty:
            continue                                # no NHL season: 0 value, 0 cost
        n_nhl_seasons += 1
        gp, w82 = float(row["GP"].iloc[0]), float(row["war_82"].iloc[0])
        cap     = CAP_CEILING[sy] * 1e6

        if is_goalie:
            value_share = ALPHA_G + BETA_G * w82    # no floor (engine convention)
        else:
            value_share = ALPHA + _slope * w82      # ITEM 4.3(a)

        if elc_burned < elc_len:
            # ---- ELC-slot season ----
            if gp < MIN_GP:
                # cameo: cost and floor prorate by GP/82; ELC year does NOT burn
                frac = gp / 82.0
                if not is_goalie:
                    value_share = max(ALPHA + _slope * w82,        # ITEM 4.3(a)
                                      cap_share_min[sy] * frac)  # prorated floor
                cost_share = (elc_cost / cap) * frac
            else:
                if not is_goalie:
                    value_share = max(value_share, cap_share_min[sy])  # D10 full floor
                cost_share = elc_cost / cap
                elc_burned += 1
            s = value_share - cost_share
            elc_component += s
            surplus_A += s
            surplus_B += s
        else:
            # ---- post-ELC season ----
            if not is_goalie:
                value_share = max(value_share, cap_share_min[sy])
            # (A) cost = market price of realized production => surplus 0
            # (B) skaters: cost on the trailing 60/40 anchor where available
            if (not is_goalie) and hist is not None:
                t1 = hist["war_82"].get(sy - 1, np.nan)
                g1 = hist["GP"].get(sy - 1, 0)
                t2 = hist["war_82"].get(sy - 2, np.nan)
                g2 = hist["GP"].get(sy - 2, 0)
                ok1 = pd.notna(t1) and g1 >= MIN_GP
                ok2 = pd.notna(t2) and g2 >= MIN_GP
                if ok1 and ok2:
                    anchor = W_T1 * t1 + W_T2 * t2
                elif ok1:
                    anchor = t1
                elif ok2:
                    anchor = t2
                else:
                    anchor = None
                if anchor is not None:
                    cost_B = max(ALPHA + BETA * anchor, cap_share_min[sy])
                    surplus_B += value_share - cost_B
                # no anchor -> falls back to (A): contributes 0

    rows.append(dict(
        draftYear=yr, overall=int(p["overallPickNumber"]),
        bucket=bucket(int(p["overallPickNumber"])),
        playerName=p["playerName"], is_goalie=is_goalie,
        link_status=p["link_status"], n_nhl_seasons=n_nhl_seasons,
        elc_years_burned=elc_burned, elc_len_rule=elc_len,
        share_elc=elc_component, share_total_A=surplus_A, share_total_B=surplus_B,
    ))

panel = pd.DataFrame(rows)
# Integrity: rule (A) total must equal the ELC component for every pick
# (post-ELC surplus is zero by construction) -- catches logic drift.
assert np.allclose(panel["share_total_A"], panel["share_elc"], atol=1e-12), \
    "rule (A) total != ELC component -- post-ELC leak into the primary rule"

panel.to_csv(OUT_PANEL, index=False)
print(f"[panel] wrote {OUT_PANEL}: {len(panel)} picks, "
      f"{(panel['n_nhl_seasons']==0).sum()} true-zero busts")

# ----------------------------------------------------------------------------
# STEP 3 -- the curve: bucket means/medians + bootstrap SEs; dollarized view
# ----------------------------------------------------------------------------
CAP_NOW = CAP_CEILING[2025] * 1e6      # readability conversion only
order   = [f"{lo}-{hi}" for lo, hi in BUCKETS]

def boot_se(x, B=2000):
    x = np.asarray(x)
    return float(np.std([np.mean(rng.choice(x, size=len(x), replace=True))
                         for _ in range(B)], ddof=1))

curve = (panel.groupby("bucket")
         .agg(n=("share_total_A", "size"),
              mean_share_A=("share_total_A", "mean"),
              median_share_A=("share_total_A", "median"),
              mean_share_B=("share_total_B", "mean"),
              share_elc_mean=("share_elc", "mean"),
              p_any_nhl=("n_nhl_seasons", lambda s: (s > 0).mean()))
         .reindex(order))
curve["se_share_A"] = [boot_se(panel.loc[panel["bucket"] == b, "share_total_A"])
                       for b in order]
curve["mean_$M_at_25-26_cap_A"] = curve["mean_share_A"] * CAP_NOW / 1e6
curve["mean_$M_at_25-26_cap_B"] = curve["mean_share_B"] * CAP_NOW / 1e6
curve = curve.round(5)
curve.to_csv(OUT_CURVE)

print(f"\n[curve] fitting cohorts {FIT_LO}-{FIT_HI}, window D+1..D+{WINDOW_LEN}")
print(curve.to_string())

# Smoke test 1: the primary curve should decline monotonically in pick number.
vals = curve["mean_share_A"].values
mono_ok = all(vals[i] >= vals[i+1] for i in range(len(vals)-1))
print(f"\n[smoke] monotone decreasing bucket means (rule A): {mono_ok}")
if not mono_ok:
    print("        -> inspect; small-n top buckets may legitimately wiggle")

# Smoke test 2: shape vs Bacon's independent per-slot NHLer probabilities.
try:
    base = pd.read_csv(os.path.join(SOURCE_DIR, "draft_slot_baseline.csv"))
    per_slot = panel.groupby("overall")["share_total_A"].mean().rename("mean_A")
    m = base.merge(per_slot, left_on="draft_pick", right_index=True)
    r = np.corrcoef(m["p_nhler"], m["mean_A"])[0, 1]
    print(f"[smoke] per-slot corr(mean surplus, Bacon p_nhler): r={r:.3f} "
          "(independent shape check, not an input)")
except FileNotFoundError:
    print("[smoke] draft_slot_baseline.csv not found -- shape check skipped")

print(f"\n[done] v{SCRIPT_VERSION}: wrote {OUT_CURVE}")
