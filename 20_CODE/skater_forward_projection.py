"""
=============================================================================
 skater_forward_projection.py   v1.2            Phase 1b -- Layer 2
                                          review item 1.3 (2026-07-26)
=============================================================================
 WHAT CHANGED IN v1.2 (the multiplier had a ceiling but no floor)
 ----------------------------------------------------------------
 The projection multiplies the anchor by the curve's ratio path. That path
 was capped above at 3.0 and bounded by nothing below. The curve's own
 per-82 level turns negative at old ages, and a negative level over a
 positive base is a negative ratio, so the model was predicting that 75
 contract-seasons across 48 contracts would produce in the OPPOSITE
 direction. The worst wanted a multiplier of -3.07.

 v1.2 adds RATIO_FLOOR = 0.0. A declining player can be projected all the
 way down to replacement level and no further, which is exactly where
 D12 v3 already puts a player arriving at replacement from below. Same
 attractor from both directions, no new parameter, and D12 v3's evidence
 (93% of below-replacement players who keep playing improve) is the
 empirical basis for both halves.

 WHAT THE REVIEW GOT WRONG HERE, checked against the live panel
 --------------------------------------------------------------
 The review proposed a second change -- raising CURVE_BASE_FLOOR from 0.25
 to about 0.40 -- on the theory that the pathology lives in small curve
 bases. It does not. Median base among the 75 affected rows is 0.56,
 running to 1.58, and only 18 of the 75 sit at or below 0.40. Raising the
 threshold would leave 57 pathological rows in place (worst still -1.30)
 while routing 197 rows across 70 contracts to a flat projection they do
 not need. The instability it was meant to prevent was also checked for:
 rows with bases in the 0.25-0.40 band top out at a multiplier of 1.38,
 LOWER than the 1.59 seen among large-base rows. Declined deliberately;
 the threshold stays at 0.25.

 Two further review claims did not survive checking. The league-minimum
 floor was said to hide part of this: no affected row is floor-bound, so
 the impossible figure reached the reported dollar value directly. And the
 3.0 cap was called biasing: it binds on zero live rows.

 MEASURED EFFECT: 41 contracts move, all upward, +$8.4M in total. Most of
 that is not the direct dollar change -- the projections involved are tiny
 -- but the risk tier. A negative projected WAR put the player in the
 "negative" exit-risk tier (17-52% a year) instead of "fringe" (5-34%),
 and after item 1.2 that tier is read from the PRIOR season, so one
 impossible row was also taxing the season after it.
                                                 (D20 + D21, 2026-07-05)
=============================================================================
 WHAT THIS DOES (plain English)
 ------------------------------
 Layer 1 (skater_value_engine.py) says what each OBSERVED season was worth.
 This module answers the forward-looking question the back-test needs:

   "Standing in season t0, what is each REMAINING season of this player's
    contract worth?"

 For each remaining season it produces projected WAR -> predicted cap% ->
 dollars (floored at the league minimum) -> surplus vs the known cap hit.
 It does NOT discount or sum -- that is Phase 1d, blocked on the discount
 rate (Phase 1a).

 HOW A PROJECTION IS BUILT (the D3 "decay path" design)
 ------------------------------------------------------
 1. ANCHOR: the player's trailing 60/40 weighted raw WAR at the valuation
    season -- the exact same number Layer 1 feeds the market-rate regression.
    Raw units in, raw units out: no unit mismatch with the locked rate.
 2. SHAPE: the locked aging curve (aging_curve.py, lambda = 0.55) projects
    the player's WAR-per-82 trajectory from his current age. We take only
    its SHAPE -- the ratio of each future level to its own starting level --
    and multiply the raw-WAR anchor by that ratio path. The mean-reversion
    pull and age-conditional decline flow through the ratios; the units
    stay regression-native.
 3. PRICE: projected WAR -> the locked skater rate -> cap% -> dollars at
    the ex-ante cap-ceiling path -> floored at the league minimum (D10).

 DECISIONS BAKED IN (IDs continue Layer 1's numbering)
 -----------------------------------------------------
 D3  (locked earlier): aging curve used as a multiplicative decay path on
     the raw-WAR anchor, not as a per-82 level substitute.
 D11 EX-ANTE CAP PATH: future ceilings = the valuation season's ceiling
     grown at CAP_GROWTH per year. Realized future ceilings are NEVER used
     -- a 2019 valuation must not "know" COVID froze the cap (extends the
     D2b trade-date-information-set principle). Both sides of any trade
     share the same path, so path error largely cancels in surplus ratios.
     League minimums use the CBA's PUBLISHED forward schedule (genuinely
     ex-ante over most horizons; the 2026+ steps come from the 2025 MOU --
     a third-order vintage caveat, documented, affecting only floor-bound
     fringe rows).
 D12 (v3, LOCKED after empirical testing -- full trail preserved because
     the evolution itself is paper-appendix material):
       v1 (freeze): hold any anchor below +0.25 flat. Rejected -- threw
           away curve information for small-positive players.
       v2 (Thomas's reflection): for negative anchors, reflect the curve
           multiplier around 1 (2 - ratio) so "decline" pushes a bad player
           further below zero. Theoretically coherent, and it beat hold-flat
           at k=1 (+1.8%) -- but INVERTED at longer horizons (-4.1% at k=2,
           -8.3% at k=3). Diagnosis: below-replacement players who keep
           playing overwhelmingly BOUNCE BACK (93% improved at k=1, 81%
           ended positive; mean -0.22 -> +0.32). A negative trailing WAR is
           mostly noise; the aging curve is the wrong instrument for this
           population -- mean reversion to replacement is.
       v3 (locked): negative anchor -> season t0 keeps the actual anchor
           (Layer 1 consistency), every FUTURE season projects at exactly
           0 WAR = replacement level. Zero parameters, so nothing was tuned
           to the test set. Beat every alternative at every horizon in the
           2018-2022 backcast (MAE 0.364/0.569/0.562 vs hold-flat's
           0.551/0.733/0.662). Also robust to the backcast's survivorship
           conditioning: players who wash out of the league produce ~0 NHL
           WAR anyway, which is exactly what the rule predicts for them.
     Separately, if the CURVE's own per-82 base is <= +0.25 the ratio is
     numerically unstable (division by near-zero); those players hold flat
     (positive anchors) -- a ratio-construction guard, distinct from D12.

 LOOK-AHEAD DEFENSES (Karl axis #2)
 ----------------------------------
 * The anchor uses seasons t0-1 / t0-2 only -- never t0 or later.
 * The curve projection excludes the player's own future seasons from his
   comparable set (aging_curve.py default _exclude_self=True).
 * D21: the curve is based at age-1/age-2 (trailing seasons only). v1.0
   based it at the t0-season age, which leaked valuation-season GP into
   the routing and valuation-season form into the comparable profile.
 * No realized future cap ceilings (D11).
 * INHERITED, DOCUMENTED LIMITATION: the aging curve's comparable bank and
   delta curves are estimated on the full 2007-2025 panel, so a 2019-dated
   projection uses aging PARAMETERS partly estimated from post-2019 data.
   Logged 2026-07-01 as "document, do not rebuild" (same class as the
   Bacon-vintage issue); planned defense is a split-sample stability check.

 FALLBACK CASCADE (every projected season carries a path tag)
 ------------------------------------------------------------
   curve            -- positive anchor, ratio applied directly
   curve_reflected  -- negative anchor, reflected multiplier (D12 v2)
   flat_low_curve_base -- curve exists but its own per-82 base <= +0.25,
                          so the ratio is numerically unreliable; hold flat
   flat_no_curve    -- no usable curve (player not in the fitted panel, no
                       GP>=20 season at the valuation age, or no birthdate)
   (rows with no trailing WAR at all cannot be anchored and are returned
    unpriced, mirroring Layer 1 -- those belong to the prospect pillar)

 USAGE
 -----
   python skater_forward_projection.py          # fit + validation battery
   from skater_forward_projection import SkaterProjector
   sp = SkaterProjector()
   sp.project_contract(player_id=..., valuation_season=2023)
=============================================================================
"""

import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from aging_curve import AgingModel, career_key

# ---------------------------------------------------------------------------
# CONFIG -- file locations
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

load_dotenv()

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])   # vendor inputs, read-only
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])   # generated spines / panels / logs
F_WAR_AGE      = OUTPUT_DIR / "WAR_with_age.csv"        # generated by age_join.py
F_WAR_SKATERS  = SOURCE_DIR / "WAR.csv"
F_SEASON_SPINE = OUTPUT_DIR / "contract_season_spine.csv"
OUT_LOG        = OUTPUT_DIR / "skater_projection_run_log.txt"

# ---------------------------------------------------------------------------
# LOCKED CONSTANTS -- identical to skater_value_engine.py where shared
# ---------------------------------------------------------------------------
ALPHA = 0.01831864          # locked skater rate (D6-D9 spec + D20 proration)
BETA  = 0.01924854          # (pre-D20 values 0.01845160/0.02021386 retired)
W_T1, W_T2 = 0.6, 0.4       # trailing weighting
MIN_GP = 10                 # qualifying-season GP filter for the ANCHOR
                            # (the curve uses its own GP>=20 internally)

CAP_CEILING = {             # realized ceilings -- used ONLY for t0 itself
    2015: 71.4e6, 2016: 73.0e6, 2017: 75.0e6, 2018: 79.5e6, 2019: 81.5e6,
    2020: 81.5e6, 2021: 81.5e6, 2022: 82.5e6, 2023: 83.5e6, 2024: 88.0e6,
    2025: 95.5e6,
}
CAP_GROWTH = 0.03           # D11: future ceilings grow 3%/yr from t0's ceiling

LEAGUE_MIN_SALARY = {       # CBA-published; 2026+ from the 2025 MOU schedule
    2015: 575_000, 2016: 575_000, 2017: 650_000, 2018: 650_000,
    2019: 700_000, 2020: 700_000, 2021: 750_000, 2022: 750_000,
    2023: 775_000, 2024: 775_000, 2025: 775_000, 2026: 850_000,
    2027: 900_000, 2028: 950_000, 2029: 1_000_000,
}
MIN_GROWTH = 0.03           # beyond the published schedule

CURVE_BASE_FLOOR = 0.25     # D12 v2: min per-82 base for a stable ratio
RATIO_CAP = 3.0             # sanity cap on growth ratios (young players)

# --- ITEM 4.5 STEP 2: the censored interaction rate -------------------------
# Superseded on 2026-07-27. The old single-slope rate was ALPHA=0.01831864,
# BETA=0.01924854, fitted by ordinary least squares with the 529 contracts
# pinned at the league minimum treated as if they were negotiated prices.
#
# The rate now in force is left-censored at the league minimum (item 3.3),
# straight in production (item 3.2 rejected the bend out of sample), omits
# contract length (item 2.1 found term buys no realized production), and lets
# the slope differ by position while holding the intercept common (item 3.4).
#
# ALPHA and BETA below are overwritten with the new values. BETA remains the
# FORWARD slope so existing imports keep working, but nothing should use it
# directly for a defenceman -- call skater_rate_cap_pct instead.
OLD_RATE_PRE_4_5 = dict(alpha=0.01831864, beta=0.01924854)
ALPHA = 0.0132478230          # $1.2652M at the 2025-26 ceiling
BETA = 0.0212322891           # $2.0277M per win, forwards
BETA_D_ADD = 0.0028702824     # $0.2741M per win extra, defencemen
BETA_D = BETA + BETA_D_ADD    # $2.3018M per win, defencemen


def posgrp_from_nk(nk):
    """The name key already carries the position as "name|F" or "name|D"."""
    try:
        return str(nk).rsplit("|", 1)[-1].strip().upper()
    except Exception:
        return "F"


def skater_slope(posgrp):
    """Price of one win, in cap share, for this position group."""
    return BETA_D if str(posgrp).upper().startswith("D") else BETA


def skater_rate_cap_pct(war, posgrp):
    """Predicted cap share at `war` trailing wins for this position group.
    Common intercept, position-dependent slope."""
    return ALPHA + skater_slope(posgrp) * war
# --- end item 4.5 step 2 ----------------------------------------------------


# --- REVIEW ITEM 3.6: value the range of outcomes, not the best guess ------
# The price equation is a straight line (item 3.2 rejected the bend), so for
# an unfloored value the average outcome and the average of the outcome values
# are identical and none of this would matter. The league-minimum floor is the
# one thing in the chain that is not straight. It caps the downside and leaves
# the upside open, so for a player near the floor the average of the outcomes
# is worth more than the single best guess.
#
# Measured effect before wiring in (uncertainty_correction.py, old rate):
# mean +$68,200 per contract, median zero, 9 of 921 negative contracts flip
# sign. Concentrated at zero projected wins and effectively nil above two.
#
# The spread comes from this script's own backcast (validation test [2],
# positive anchors): mean absolute error 0.522, 0.735, 0.803 WAR at k=1,2,3,
# converted to a standard deviation by the normal-distribution factor 1.2533.
# Beyond k=3 the k=3 figure is held flat -- a PLACEHOLDER, not an estimate,
# affecting roughly 13% of projected seasons, all on long contracts.
#
# Known limitation: below-replacement projections are already truncated at
# zero wins, so a symmetric spread around them overstates the upside. That
# affects about 9.5% of seasons and inflates the mean correction by roughly
# $11,000 per contract. Judged not worth special handling; recorded here.
from scipy import stats as _st_36

_BACKCAST_MAE_36 = {1: 0.522, 2: 0.735, 3: 0.803}
_MAE_TO_SD_36 = 1.2533          # SD = MAE * sqrt(pi/2) for a normal
_MAX_BACKCAST_K_36 = 3


def _proj_sd_war(k):
    """Standard deviation of projected WAR k seasons out. Zero at k=0, where
    the anchor is observed rather than projected."""
    if k <= 0:
        return 0.0
    return _BACKCAST_MAE_36[min(k, _MAX_BACKCAST_K_36)] * _MAE_TO_SD_36


def expected_floored_value(point_value, sd_dollars, floor_dollars):
    """E[max(value, floor)] with value normally distributed about its point
    estimate. Closed form:

        E[max(X,F)] = F*Phi(d) + mu*(1-Phi(d)) + sigma*phi(d),  d = (F-mu)/sigma

    Verified against a four-million-draw simulation to within $1,000 across
    the range in use. Returns max(point, floor) exactly when sd is zero, which
    preserves the k=0 identity with Layer 1."""
    if sd_dollars <= 0:
        return max(point_value, floor_dollars)
    d = (floor_dollars - point_value) / sd_dollars
    return (floor_dollars * _st_36.norm.cdf(d)
            + point_value * (1.0 - _st_36.norm.cdf(d))
            + sd_dollars * _st_36.norm.pdf(d))
# --- end item 3.6 ---------------------------------------------------------

RATIO_FLOOR = 0.0           # review item 1.3: the matching bound underneath.
                            # The curve's own per-82 level goes negative at old
                            # ages, and a negative level over a positive base
                            # gives a negative ratio -- the model then predicts
                            # a player will produce in the OPPOSITE direction,
                            # which is not a possible outcome. Flooring at 0
                            # says the worst a declining player can be projected
                            # to do is replacement level, which is exactly what
                            # D12 v3 already asserts for players arriving at
                            # replacement from below. Same attractor from both
                            # directions, no new parameter. See the item 1.3
                            # note in the header for what was measured.
# (v2's reflection clip band retired with D12 v3 -- see docstring trail)

MERGED_WAR_NAMES = {"ryan johnson", "nathan smith"}   # locked exclusions
NAME_ALIASES = {("sebastian aho", "D"): "sebastian aho swe"}

_VARIANTS = {
    "alexander": "alex", "alexandre": "alex", "nicholas": "nick",
    "michael": "mike", "matthew": "matt", "christopher": "chris",
    "maxime": "max", "zachary": "zach", "joshua": "josh", "samuel": "sam",
    "benjamin": "ben", "daniel": "dan", "jonathan": "jon",
    "steven": "steve", "gregory": "greg", "patrick": "pat",
}

def norm_name(s):
    """Same normalization rules as the Layer 1 engine / age join."""
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

POSGRP = {"Center": "F", "Left Wing": "F", "Right Wing": "F",
          "Defense": "D", "Goaltender": "G"}

LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))


def cap_path(t0, k):
    """D11: the ceiling a GM standing in season t0 would plan with for
    season t0+k. k=0 -> the known ceiling; k>=1 -> grown at CAP_GROWTH.
    No realized future ceilings, ever."""
    base = CAP_CEILING[t0]
    return base * (1 + CAP_GROWTH) ** k


def league_min_path(season):
    """League minimum for a season: published schedule, grown past its end."""
    if season in LEAGUE_MIN_SALARY:
        return LEAGUE_MIN_SALARY[season]
    last = max(LEAGUE_MIN_SALARY)
    return LEAGUE_MIN_SALARY[last] * (1 + MIN_GROWTH) ** (season - last)


class SkaterProjector:
    """Builds everything once, then answers per-player projection queries."""

    def __init__(self):
        # ---- the locked aging model (fitted on the age-joined WAR panel) ----
        self.curve = AgingModel(str(F_WAR_AGE))

        # ---- anchor lookup: identical construction to Layer 1 --------------
        # D20: schedule proration applied BEFORE anything else, using the
        # engine's own factor dict when importable (single source of truth).
        try:
            from skater_value_engine import PRORATION as _PR
        except ImportError:
            _PR = {2019: 82 / 70, 2020: 82 / 56}      # standalone fallback
        war = pd.read_csv(F_WAR_SKATERS)
        war["syr"] = war["Season"].str.split("-").str[0].astype(int) + 2000
        war["WAR"] = war["WAR"] * war["syr"].map(_PR).fillna(1.0)
        war["nk"] = war["Player"].map(norm_name) + "|" + war["Position"]
        bare = war["Player"].map(norm_name)
        war = war[~bare.isin(MERGED_WAR_NAMES)].copy()

        # REVIEW ITEM 1.5, second copy. This file rebuilds the WAR lookup
        # rather than importing skater_value_engine's, so it carried its own
        # copy of the discard-a-team-half bug -- and THIS is the copy that
        # actually prices contracts, so fixing only the value engine changed
        # nothing downstream. Both are fixed; the logic is identical and the
        # guard is the same. See build_skater_war_lookup() for the full note.
        dup = war.duplicated(["nk", "syr"], keep=False)
        if dup.any():
            tot = war[dup].groupby(["nk", "syr"])["GP"].sum()
            assert (tot <= 82).all(), (
                "combined games above a full season for "
                f"{list(tot[tot > 82].index)} -- two different players sharing "
                "a name, not one player's two team-halves. Do not sum them.")
        agg = war.groupby(["nk", "syr"], as_index=False).agg(
            GP=("GP", "sum"), WAR=("WAR", "sum"))
        q = agg[agg["GP"] >= MIN_GP]
        assert not q.duplicated(["nk", "syr"]).any(), \
            "the projection's WAR lookup still holds duplicate keys"
        self.war_lut = q.set_index(["nk", "syr"])["WAR"].sort_index()
        # normalized key -> the raw WAR.csv Player string (the curve is keyed
        # on raw strings like "Sebastian Aho Swe" / "Elias Pettersson(D)").
        # NOTE: where the source spells one player two ways, this still picks
        # whichever spelling appears first, which for Nick Paul is the
        # two-season fragment rather than his ten-season career. That is
        # review item 1.6 and is fixed with the curve rebuild, not here.
        self.raw_name = (war.drop_duplicates("nk").set_index("nk")["Player"]
                         .to_dict())

        # ---- contract spine: seasons, costs, birthdates ---------------------
        cs = pd.read_csv(F_SEASON_SPINE)
        sk = cs[cs["position"] != "Goaltender"].copy()
        sk["posgrp"] = sk["position"].map(POSGRP)
        sk["full_name"] = sk["first_name"].astype(str) + " " + sk["last_name"].astype(str)
        sk["nname"] = sk["full_name"].map(norm_name)
        def make_key(row):
            alias = NAME_ALIASES.get((row["nname"], row["posgrp"]))
            return (alias if alias else row["nname"]) + "|" + row["posgrp"]
        sk["nk"] = sk.apply(make_key, axis=1)
        sk["cost"] = sk["cs_cap_hit"].fillna(sk["pp_cap_hit"])
        sk["bd"] = pd.to_datetime(sk["birthdate"], errors="coerce")
        self.spine = sk

    # ---- building blocks ---------------------------------------------------
    def anchor(self, nk, t0):
        """Trailing 60/40 weighted raw WAR at season t0 (Layer 1 rule).
        Returns (value, source) -- source in both/t1_only/t2_only/none."""
        def get(k):
            v = self.war_lut.get(k, np.nan)
            return np.nan if isinstance(v, pd.Series) else v
        w1, w2 = get((nk, t0 - 1)), get((nk, t0 - 2))
        if pd.notna(w1) and pd.notna(w2):
            return W_T1 * w1 + W_T2 * w2, "both"
        if pd.notna(w1):
            return w1, "t1_only"
        if pd.notna(w2):
            return w2, "t2_only"
        return np.nan, "none"

    def age_at(self, birthdate, season_start):
        """Integer age on Feb 1 of the season's ENDING year -- the exact
        convention age_join.py used to build the curve's panel, so the
        'qualifying season at this age' lookup lines up."""
        if pd.isna(birthdate):
            return None
        ref = pd.Timestamp(year=season_start + 1, month=2, day=1)
        a = ref.year - birthdate.year - (
            (ref.month, ref.day) < (birthdate.month, birthdate.day))
        return int(a)

    def ratio_path(self, nk, age, horizon):
        """The D3 decay path: curve trajectory divided by its own anchor.
        Returns (list of ratios for k=0..horizon, path_tag). Falls back to
        flat (all 1.0) when the curve cannot be used.

        D21 (locked 2026-07-05): the curve is based at age-1 (fallback
        age-2), never at the valuation-season age. The old v1.0 behavior
        asked the curve for a qualifying season at the player's age AT t0
        -- but his age-at-t0 season IS the t0 season, so both the routing
        (does the curve apply?) and the comparable profile leaked
        valuation-season information, violating the trailing-only rule.
        Basing at age-1 keys everything to the t-1 season -- the same
        information set the anchor already uses. The returned ratios are
        renormalized so k=0 (the t0 season) keeps ratio 1.0 exactly,
        preserving the k=0 == Layer 1 identity."""
        flat = [1.0] * (horizon + 1)
        self.last_ratio_floored = []      # item 1.3: cleared on every entry
        self.last_raw_ratios = []
        # REVIEW ITEM 1.6. The curve is now keyed on the cleaned career name,
        # not the raw source spelling, so the lookup goes through career_key.
        # Before this, a player the source spells two ways was looked up under
        # whichever spelling appeared first in the file -- for Nick Paul, the
        # two-season fragment rather than his full career.
        raw = self.raw_name.get(nk)
        key = career_key(raw) if raw is not None else None
        if key is None or key not in self.curve.players or age is None:
            return flat, "flat_no_curve"
        raw = key
        # BOUNDARY GUARD: the fitted panel only has age-delta data up to its
        # oldest observed age. Walking past that edge raises inside the locked
        # engine (left untouched per project discipline) -- so cap the horizon
        # we ask it for, and hold the last ratio flat for the remainder.
        max_age = self.curve.AMIN + self.curve.nages - 1
        levels = None
        for lag in (1, 2):                            # D21: t-1, then t-2
            base_age = age - lag
            # the walk starts at base_age and must reach at least age (k=0)
            safe_h = min(horizon + lag, max(0, max_age - base_age - 1))
            if safe_h < lag + 1:
                continue                              # cannot even reach k=1
            try:
                tr = self.curve.project(raw, current_age=base_age,
                                        horizon=safe_h)
            except (ValueError, KeyError, IndexError):
                continue                              # no qualifying season
            lv = tr["projected_war_per_82"].tolist()
            if len(lv) <= lag:
                continue
            levels = lv[lag:]                         # ages age, age+1, ...
            break
        if levels is None:
            return flat, "flat_no_curve"
        base = levels[0]                              # the k=0 (age) level
        if base <= CURVE_BASE_FLOOR:                  # ratio-construction guard
            self.last_ratio_floored = []
            return flat, "flat_low_curve_base"
        raw_ratios = [l / base for l in levels]
        # REVIEW ITEM 1.3. Bound on BOTH sides now. The cap above was already
        # here; the floor below is new. Recorded per season so the run log can
        # report exactly which rows it caught rather than silently smoothing.
        ratios = [min(max(r, RATIO_FLOOR), RATIO_CAP) for r in raw_ratios]
        floored = [r < RATIO_FLOOR for r in raw_ratios]
        # the curve may stop early (no delta data at extreme ages):
        # hold the last ratio flat for any remaining seasons
        while len(ratios) < horizon + 1:
            ratios.append(ratios[-1])
            floored.append(floored[-1])
        assert len(floored) == len(ratios), "floor flags out of step with ratios"
        # Stashed on the instance rather than returned, because ratio_path()'s
        # two-value signature is also consumed by rfa_terminal_value.py and
        # changing it would break that caller. project_contract() reads this
        # immediately after its own call, so there is no chance of a stale read.
        self.last_ratio_floored = floored
        # Keep the UNFLOORED ratio too, purely so the run log can say what the
        # curve originally wanted. Nothing prices off it.
        self.last_raw_ratios = raw_ratios + [raw_ratios[-1]] * (
            len(ratios) - len(raw_ratios))
        return ratios, "curve"

    @staticmethod
    def multiplier(anchor, ratio, k):
        """D12 v3 (locked after testing -- see module docstring for the
        v1 freeze -> v2 reflection -> v3 trail and the backcast evidence).

        Positive anchor: apply the curve's ratio directly -- 'decline 15%'
        means x0.85. This branch beats hold-flat by 7-9% at every horizon.

        Negative anchor: season t0 (k=0) keeps the real anchor so Layer 2
        collapses exactly onto Layer 1; every future season projects at
        REPLACEMENT (0 WAR). Empirical basis: below-replacement players who
        keep playing overwhelmingly revert to ~replacement (93% improved at
        k=1, 81% ended positive), and those who wash out produce ~0 NHL WAR
        anyway -- so 0 is the right prediction on both branches of their
        future. Returns the multiplier to apply to the anchor."""
        if anchor >= 0:
            return ratio
        return 1.0 if k == 0 else 0.0

    # ---- the main query -----------------------------------------------------
    def project_contract(self, player_id, valuation_season):
        """All remaining contract seasons for this player, valued from the
        standpoint of `valuation_season` (t0). Returns a DataFrame with one
        row per season k = 0..end-of-contract."""
        rows = self.spine[(self.spine["player_id"] == player_id)
                          & (self.spine["season_start"] >= valuation_season)]
        # the contract active AT t0 (guards against a future extension's rows)
        active = rows[rows["season_start"] == valuation_season]
        if active.empty:
            return pd.DataFrame()
        cid = active.iloc[0]["contract_id"]
        rows = rows[rows["contract_id"] == cid].sort_values("season_start")

        nk = rows.iloc[0]["nk"]
        a, src = self.anchor(nk, valuation_season)
        if pd.isna(a):
            return pd.DataFrame()                     # prospect-pillar territory
        age = self.age_at(rows.iloc[0]["bd"], valuation_season)
        horizon = len(rows) - 1
        ratios, path = self.ratio_path(nk, age, horizon)
        # ITEM 1.3: read the floor flags straight after the call that set them.
        # A negative-anchor player never uses the ratio at all (D12 v3 sends
        # him to replacement regardless), so the flag is only meaningful, and
        # only recorded, when the anchor is positive.
        floored = list(getattr(self, "last_ratio_floored", []))
        raw_ratios = list(getattr(self, "last_raw_ratios", []))
        while len(floored) < horizon + 1:
            floored.append(False)
        while len(raw_ratios) < horizon + 1:
            raw_ratios.append(ratios[len(raw_ratios)])
        if a < 0:
            # D12 v3 applies to every negative anchor, curve-eligible or not
            # (the multiplier keys on anchor sign) -- the tag must say so.
            path = "replacement_reversion"

        _posgrp = posgrp_from_nk(nk)      # ITEM 4.5 STEP 2
        out = []
        for k, (_, r) in enumerate(rows.iterrows()):
            season = int(r["season_start"])
            mult = self.multiplier(a, ratios[k], k)
            pw = a * mult
            ceil = cap_path(valuation_season, k)
            lm = league_min_path(season)
            # ITEM 4.5 STEP 2: position-dependent slope, common intercept.
            _slope = skater_slope(_posgrp)
            val_raw = (ALPHA + _slope * pw) * ceil
            # ITEM 3.6: integrate over the projection range rather than
            # pricing the point estimate. At k=0 the spread is zero and this
            # collapses to max(val_raw, lm), the original D10 floor. The spread
            # scales with the SAME slope, so a defenceman's uncertainty is
            # measured on his own price of a win.
            _sd_val = _slope * _proj_sd_war(k) * ceil
            val = expected_floored_value(val_raw, _sd_val, lm)   # D10 floor
            out.append({
                "player_id": player_id, "full_name": r["full_name"],
                "contract_id": cid, "season_start": season, "k": k,
                "valuation_season": valuation_season, "age_at_valuation": age,
                "anchor_war": a, "anchor_source": src, "path": path,
                "decay_ratio": ratios[k], "multiplier_applied": mult,
                "ratio_floored": bool(floored[k] and a >= 0),   # item 1.3
                "decay_ratio_raw": raw_ratios[k],   # pre-floor, log only
                "projected_war": pw,
                "cap_ceiling_exante": ceil, "league_min": lm,
                "posgrp": _posgrp, "slope_used": _slope,
                "value_dollars": val, "floor_bound": val_raw < lm,
                "value_point_estimate": max(val_raw, lm),
                "uncertainty_correction": val - max(val_raw, lm),
                "proj_sd_war": _proj_sd_war(k),
                "sd_placeholder": k > _MAX_BACKCAST_K_36,
                "cost_dollars": r["cost"],
                "surplus_dollars": val - r["cost"],
            })
        return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# VALIDATION BATTERY (runs when executed directly)
# ---------------------------------------------------------------------------
def validate():
    sp = SkaterProjector()
    log("=" * 74)
    log("LAYER 2 VALIDATION BATTERY")
    log("=" * 74)

    # ---- 1. k=0 consistency vs Layer 1 -------------------------------------
    # At k=0 the projection uses the identical anchor, rate, real ceiling and
    # floor as Layer 1, so values must agree to the cent on shared rows.
    l1 = pd.read_csv(OUTPUT_DIR / "skater_value_spine.csv")
    l1p = l1[l1["trailing_war"].notna()]
    rng = np.random.default_rng(7)
    sample = l1p[l1p["season_start"].between(2018, 2025)].sample(400, random_state=7)
    diffs, checked = [], 0
    for _, r in sample.iterrows():
        pr = sp.project_contract(int(r["player_id"]), int(r["season_start"]))
        if pr.empty:
            continue
        row0 = pr[pr["k"] == 0]
        if row0.empty or row0.iloc[0]["contract_id"] != r["contract_id"]:
            continue
        checked += 1
        diffs.append(abs(row0.iloc[0]["value_dollars"] - r["value_dollars"]))
    log(f"\n[1] k=0 consistency vs Layer 1: {checked} shared rows checked, "
        f"max |value diff| = ${max(diffs):,.2f}" if diffs else "no rows checked")
    assert max(diffs) < 1.0, "k=0 must reproduce Layer 1 exactly"

    # ---- 2. backcast: projected vs realized trailing anchors ---------------
    # Stand at t0 in 2018-2022, project k=1..3 WAR, compare against the
    # trailing anchor Layer 1 actually used in those later seasons (the
    # dollar-relevant target), and against a hold-flat persistence baseline.
    # SPLIT BY BRANCH: positive anchors (ratio direct) and negative anchors
    # (D12 v2 reflected multiplier) are scored separately -- the reflected
    # branch is the new rule under test and must beat hold-flat to lock.
    log("\n[2] backcast (t0 = 2018..2022, k = 1..3), target = realized trailing anchor:")
    err = {}   # (branch, method, k) -> list of abs errors
    for t0 in range(2018, 2023):
        cand = sp.spine[(sp.spine["season_start"] == t0)].drop_duplicates("player_id")
        for _, r in cand.iterrows():
            a, src = sp.anchor(r["nk"], t0)
            if pd.isna(a):
                continue
            age = sp.age_at(r["bd"], t0)
            ratios, path = sp.ratio_path(r["nk"], age, 3)
            if path != "curve":
                continue
            branch = "neg_reflected" if a < 0 else "pos_direct"
            for k in (1, 2, 3):
                target, _ = sp.anchor(r["nk"], t0 + k)
                if pd.isna(target):
                    continue
                pred = a * sp.multiplier(a, ratios[k], k)
                err.setdefault((branch, "curve", k), []).append(abs(pred - target))
                err.setdefault((branch, "flat", k), []).append(abs(a - target))
    for branch, label in [("pos_direct", "positive anchors, ratio direct"),
                          ("neg_reflected", "NEGATIVE anchors, D12 v3 replacement-reversion")]:
        log(f"    -- {label} --")
        for k in (1, 2, 3):
            ec = err.get((branch, "curve", k))
            ef = err.get((branch, "flat", k))
            if not ec:
                log(f"    k={k}: no observations"); continue
            mc, mf = np.mean(ec), np.mean(ef)
            log(f"    k={k}: n={len(ec):5d}  curve MAE={mc:.3f} WAR  "
                f"hold-flat MAE={mf:.3f} WAR  improvement={100*(1-mc/mf):+.1f}%")

    # ---- 3. coverage: which projection path do contract-seasons get? -------
    log("\n[3] path coverage across all 2018+ valuation points (player x season):")
    pts = sp.spine[sp.spine["season_start"].between(2018, 2025)].drop_duplicates(
        ["player_id", "season_start"])
    tally = {"curve": 0, "replacement_reversion": 0, "flat_low_curve_base": 0,
             "flat_no_curve": 0, "no_anchor": 0}
    for _, r in pts.iterrows():
        a, _ = sp.anchor(r["nk"], int(r["season_start"]))
        if pd.isna(a):
            tally["no_anchor"] += 1
            continue
        age = sp.age_at(r["bd"], int(r["season_start"]))
        _, path = sp.ratio_path(r["nk"], age, 1)
        if a < 0:
            path = "replacement_reversion"
        tally[path] += 1
    tot = sum(tally.values())
    for k2, v in tally.items():
        log(f"    {k2:20s} {v:6,d}  ({100*v/tot:.1f}%)")

    # ---- 3b. review item 1.3: what the ratio floor caught -------------------
    # Walks every contract the engine actually prices and reports the rows
    # where the curve wanted a negative multiplier. Read-only.
    log("\n[3b] review item 1.3 -- lower bound on the projection multiplier:")
    log(f"     RATIO_FLOOR = {RATIO_FLOOR}, RATIO_CAP = {RATIO_CAP} "
        f"(the cap was already here; the floor is new)")
    firsts = (sp.spine[sp.spine["season_start"].between(2018, 2025)]
              .sort_values(["contract_id", "season_start"])
              .groupby("contract_id", as_index=False).first())
    hit, panel = [], 0
    for _, r in firsts.iterrows():
        pr = sp.project_contract(int(r["player_id"]), int(r["season_start"]))
        if not len(pr):
            continue
        panel += len(pr)
        f = pr[pr["ratio_floored"]]
        if len(f):
            hit.append(f)
    if hit:
        h = pd.concat(hit, ignore_index=True)
        # Guard: the floor must have bitten, and it must have produced exactly
        # replacement level -- never a negative projection, which is the whole
        # point of the item.
        assert (h["multiplier_applied"] == 0.0).all(), \
            "a floored row did not come out at exactly the floor"
        assert (h["projected_war"] == 0.0).all(), \
            "a floored row still carries a negative projected WAR"
        assert (h["anchor_war"] >= 0).all(), \
            "a floored row has a negative anchor -- D12 v3 should own that row"
        log(f"     rows caught: {len(h)} of {panel:,} projected contract-seasons, "
            f"across {h['contract_id'].nunique()} contracts")
        log("     each one wanted a negative multiplier, meaning the model was")
        log("     predicting production in the opposite direction; each now sits")
        log("     at replacement level (0 WAR), the same place D12 v3 puts a")
        log("     below-replacement player.")
        log("     worst cases, by how far below zero the projection would have gone:")
        for _, x in h.nsmallest(6, "decay_ratio_raw").iterrows():
            log(f"       {x['full_name']:22s} {int(x['valuation_season'])} "
                f"k={int(x['k'])}  anchor {x['anchor_war']:+.2f} WAR  "
                f"wanted multiplier x{x['decay_ratio_raw']:.2f}  "
                f"(would have projected {x['anchor_war']*x['decay_ratio_raw']:+.2f} WAR)")
    else:
        log("     rows caught: 0 -- no negative multipliers in the priced panel")

    # ---- 4. spot demos ------------------------------------------------------
    log("\n[4] spot demos:")
    demos = [("Connor McDavid", 2024), ("Brad Marchand", 2023), ("Matvei Michkov", 2025)]
    # add one NEGATIVE-anchor player dynamically to show the reflection working
    for _, r in sp.spine[sp.spine["season_start"] == 2023].drop_duplicates("player_id").iterrows():
        a, _ = sp.anchor(r["nk"], 2023)
        if pd.notna(a) and a < -0.5:
            age = sp.age_at(r["bd"], 2023)
            _, path = sp.ratio_path(r["nk"], age, 2)
            if path == "curve":
                demos.append((r["full_name"], 2023))
                break
    for name, t0 in demos:
        pid = sp.spine[(sp.spine["full_name"] == name)
                       & (sp.spine["season_start"] == t0)]["player_id"]
        if pid.empty:
            log(f"    {name}: no contract-season at {t0}")
            continue
        pr = sp.project_contract(int(pid.iloc[0]), t0)
        if pr.empty:
            log(f"    {name}: unpriced at {t0}")
            continue
        log(f"    {name} from {t0} (age {pr.iloc[0]['age_at_valuation']}, "
            f"path={pr.iloc[0]['path']}, anchor {pr.iloc[0]['anchor_war']:.2f} WAR):")
        for _, r in pr.iterrows():
            log(f"      {r['season_start']}-{str(r['season_start']+1)[2:]}  k={r['k']}  "
                f"mult x{r['multiplier_applied']:.3f}  WAR {r['projected_war']:+.2f}  "
                f"value ${r['value_dollars']/1e6:5.2f}M  "
                f"cost ${r['cost_dollars']/1e6:5.2f}M  surplus ${r['surplus_dollars']/1e6:+6.2f}M"
                + ("  [floor]" if r["floor_bound"] else ""))

    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")


if __name__ == "__main__":
    validate()
