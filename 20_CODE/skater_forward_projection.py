"""
=============================================================================
 skater_forward_projection.py   v2.1            Phase 1b -- Layer 2
                                  xNPV 1 prices skater contracts (D33)
=============================================================================
 WHAT CHANGED IN v2.1 (2026-10-05, plan of record step 6; MODEL_DIRECTIVES.md directive 4)
 ------------------------------------------------------------------------------------------
 The price line is TERM-IN (XNPV1_RATE re-locked on xnpv1_price_line.py v2.0: signing-dated
 forecasts, one linear term for years). A contract season is priced on the term REMAINING at the
 valuation date, the same for every remaining season; an RFA control year on one year. The
 term-free line (XNPV1_RATE_TERM_FREE) is priced beside every value as the sensitivity, and each
 contract season reports its term premium (gamma_term x remaining term x ceiling) in its own column.
 WHAT THIS DOES
 --------------
 Values every remaining season of a skater's contract, plus every extension
 signed by the as-of date, from the standpoint of one valuation page. For
 season k (k = 0 is the valuation season, unplayed on 1 July):

   1. WAR: xNPV 1's forecast of the WAR he produces IF HE PLAYS (rate per 82
      games x games share), from skater_forecast.ContractForecaster, fitted
      once per page on seasons before it.
   2. CHANCE OF PLAYING: xNPV 1's p_play for that season, contract status
      read at the as-of date. contract_npv.py multiplies the value by it.
   3. PRICE: WAR -> cap share on xNPV 1's own price line (XNPV1_RATE, D33
      addendum: one intercept, a separate defence slope, fitted on the
      forecast) -> dollars at the ex-ante cap path (D11: the page's ceiling
      grown 3% a year).
   4. FLOOR: E[max(price, league minimum)] (D10), the price spread around
      its point estimate set by xNPV 1's own misses at k
      (skater_forecast.war_if_plays_sd).
   5. COST: the season's real cap hit.
 contract_npv.py applies the chance of playing, discounts and sums;
 rfa_terminal_value.py adds the RFA control years on the same forecast and
 price line.

 WHAT CHANGED IN v2.0 (2026-10-02): xNPV 0 ARCHIVED
 --------------------------------------------------
 The anchor-and-ratio projection (the trailing 60/40 anchor walked by the
 comparable-player aging ratio) is removed, with its switch
 (XNPV_SKATER_MODEL) and its validation battery. Thomas accepted the switch
 comparison on 2026-10-02. The file as it stood, with its full version
 history (v1.0 to v1.6), is in git at commit 7f91f0e and in
 90_ARCHIVE/2026-10-02/ on the laptop. The removal was checked to leave
 every xNPV 1 value identical.
 Setting XNPV_SKATER_MODEL to anything but "xNPV 1" now stops the run, so
 an old environment cannot silently price something else.

 USAGE
 -----
   python skater_forward_projection.py          # validation battery
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

# ---------------------------------------------------------------------------
# CONFIG -- file locations
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "xNPV 1"           # the one skater forecast (D33)
# v2.0: the switch is gone. A leftover setting from the two-model period must
# not pass silently, so anything but xNPV 1 stops the run.
_env_model = os.environ.get("XNPV_SKATER_MODEL")
assert _env_model in (None, "", MODEL_NAME), (
    f"XNPV_SKATER_MODEL={_env_model!r}: xNPV 0 was archived 2026-10-02 (git 7f91f0e); "
    f"unset the variable or set it to {MODEL_NAME!r}")
SKATER_MODEL = MODEL_NAME       # kept for callers that read the name

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])   # vendor inputs, read-only
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])   # generated spines / panels / logs
F_SEASON_SPINE = OUTPUT_DIR / "contract_season_spine.csv"
OUT_LOG        = OUTPUT_DIR / "skater_projection_run_log.txt"

# ---------------------------------------------------------------------------
# LOCKED CONSTANTS
# ---------------------------------------------------------------------------
CAP_CEILING = {             # realized ceilings -- used ONLY for t0 itself
    2015: 71.4e6, 2016: 73.0e6, 2017: 75.0e6, 2018: 79.5e6, 2019: 81.5e6,
    2020: 81.5e6, 2021: 81.5e6, 2022: 82.5e6, 2023: 83.5e6, 2024: 88.0e6,
    2025: 95.5e6,
    2026: 104.0e6, 2027: 113.5e6,   # v1.3: published in the 2025 MOU; same
                                    # figures as goalie_value_engine.py. Read
                                    # only as the t0 ceiling of a 2026/2027 page.
}
CAP_GROWTH = 0.03           # D11: future ceilings grow 3%/yr from t0's ceiling

LEAGUE_MIN_SALARY = {       # CBA-published; 2026+ from the 2025 MOU schedule
    2015: 575_000, 2016: 575_000, 2017: 650_000, 2018: 650_000,
    2019: 700_000, 2020: 700_000, 2021: 750_000, 2022: 750_000,
    2023: 775_000, 2024: 775_000, 2025: 775_000, 2026: 850_000,
    2027: 900_000, 2028: 950_000, 2029: 1_000_000,
}
MIN_GROWTH = 0.03           # beyond the published schedule

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
# Stage 3 is no longer what prices skater contracts (xNPV 1 prices on its own
# line, below). It stays here as the fallback price_constants() returns when
# XNPV1_RATE is None, and because rfa_terminal_value logs it. BETA is the
# FORWARD slope; call skater_rate_cap_pct for a position-aware rate.
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


# --- v1.6: xNPV 1's OWN PRICE LINE (deliberate revisit of the Stage 3 rate,
# approved by Thomas 2026-10-02) ----------------------------------------------
# The Stage 3 line above was fitted on each contract's TRAILING 60/40 WAR. xNPV
# 1 prices its FORECAST, which is shrunk toward the league (0.180 + 0.674 x
# trailing on the development pages), so a per-trailing-win slope applied to
# forecast wins under-prices every win above the intercept. xnpv1_price_line.py
# re-fits the SAME specification (left-censored at the league minimum, one
# intercept, a defence slope) on the SAME 2,349 contracts with the input
# replaced by xNPV 1's valuation-season forecast of WAR if he plays.
#
# LOCKED 2026-10-02 from the laptop run (xnpv1_price_line.py v1.0, log
# 30_OUTPUT/xnpv1_price_line_log.txt): 2,347 of the 2,349 Stage 3 contracts
# (two have no xNPV 1 forecast); the re-fit on the trailing total on those rows
# gave back the Stage 3 line. At the 2025-26 ceiling: $0.735M at zero forecast
# wins, $2.950M per forecast win for forwards, $4.350M for defencemen (Stage 3:
# $1.265M, $2.028M, $2.302M per trailing win). Censored log-likelihood 4,048.2
# against 3,902.1 for the trailing total on the same rows. Evidence and
# reading: 40_DOCS/model_evidence/xNPV1_Price_Line.md. If XNPV1_RATE is set
# back to None, xNPV 1 prices on Stage 3 and every row says "Stage 3
# (provisional for xNPV 1)".
# The draft curve (draft_yield_curve.py) keeps its own Stage 3 copy, because it
# prices realised wins, not this forecast.
#
# RE-LOCKED 2026-10-05 (Thomas; plan of record step 6, directives 4 and 5), from the laptop run of
# xnpv1_price_line.py v2.0 on skater_forecast v2.2: each contract's forecast dated at its SIGNING,
# and contract length in the line as one linear term (gamma_term, cap share per year of term). 2,296
# of the 2,349 Stage 3 contracts (50 with no forecast at the signing, 3 signed after their start).
# At the 2025-26 ceiling: -$0.416M at zero forecast wins and zero term, $1.668M per forecast win for
# forwards, $2.012M for defencemen, +$0.853M a season per year of term; censored log-likelihood
# 4,526.4 against 3,897.2 for the same signing-dated fit without term. The v1.x lock above this
# comment's first paragraph (alpha 0.0076921739, beta 0.0308904772, beta_d_add 0.0146619104, n 2347)
# was fitted on the v1.x forecast, start-dated, without term; it is in git at 3ee2f88.
# HOW TERM IS USED (directive 4's details, Thomas 2026-10-05): a contract season is priced on the
# term REMAINING at the valuation date, the same for every remaining season (_project_xnpv1); an RFA
# control year on one year (rfa_terminal_value). XNPV1_RATE_TERM_FREE is the same signing-dated fit
# without term: the term-free sensitivity reported beside every term-in value.
XNPV1_RATE = dict(alpha=-0.0043574069, beta=0.0174691916, beta_d_add=0.0035971954,
                  gamma_term=0.0089321965, n=2296, sigma=0.01570309, rows_fingerprint="b9067879bf72")
XNPV1_RATE_TERM_FREE = dict(alpha=0.0081646316, beta=0.0310794541, beta_d_add=0.0135178851,
                            gamma_term=0.0, n=2296, sigma=0.02192174, rows_fingerprint="b9067879bf72")


def price_constants(model=None, term_free=False):
    """(alpha, beta_F, beta_D, gamma_term, label): the price line skater
    seasons are priced on, in cap share (per win; per year of term). The only
    place the choice is made. term_free=True gives the sensitivity line
    (gamma_term 0). `model` is accepted for callers written when two models
    ran; anything but "xNPV 1" (or None) is refused."""
    assert model in (None, MODEL_NAME), f"unknown skater model {model!r}; only {MODEL_NAME} remains"
    r = XNPV1_RATE_TERM_FREE if term_free else XNPV1_RATE
    if r is not None:
        return (float(r["alpha"]), float(r["beta"]), float(r["beta"]) + float(r["beta_d_add"]),
                float(r.get("gamma_term", 0.0)),
                "xNPV 1 term-free line" if term_free else "xNPV 1 term-in line")
    return ALPHA, BETA, BETA_D, 0.0, "Stage 3 (provisional for xNPV 1)"


# --- REVIEW ITEM 3.6: value the range of outcomes, not the best guess ------
# The price line is straight, so for an unfloored value the average outcome
# and the average of the outcome values are identical. The league-minimum
# floor is the one thing that is not straight: it caps the downside and leaves
# the upside open, so for a player near the floor the average of the outcomes
# is worth more than the single best guess. Each season is therefore valued as
# E[max(price, floor)], with the price normally distributed about its point
# estimate. The spread is xNPV 1's own season-WAR miss at k
# (skater_forecast.war_if_plays_sd: mean absolute error x 1.2533), converted
# to dollars with the season's own slope and ceiling.
from scipy import stats as _st_36


def expected_floored_value(point_value, sd_dollars, floor_dollars):
    """E[max(value, floor)] with value normally distributed about its point
    estimate. Closed form:

        E[max(X,F)] = F*Phi(d) + mu*(1-Phi(d)) + sigma*phi(d),  d = (F-mu)/sigma

    Verified against a four-million-draw simulation to within $1,000 across
    the range in use. Returns max(point, floor) exactly when sd is zero."""
    if sd_dollars <= 0:
        return max(point_value, floor_dollars)
    d = (floor_dollars - point_value) / sd_dollars
    return (floor_dollars * _st_36.norm.cdf(d)
            + point_value * (1.0 - _st_36.norm.cdf(d))
            + sd_dollars * _st_36.norm.pdf(d))
# --- end item 3.6 ---------------------------------------------------------

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


# ---------------------------------------------------------------------------
# v1.3: the information date and the contract chain
# ---------------------------------------------------------------------------
# Confidential vendor file, read-only. The spine carries no signing date, so
# it is joined from here by contract_id (the key player_dashboard.py uses).
F_PP_CONTRACTS = Path(os.environ["PUCKPEDIA_CONTRACTS_XLSX"])


def page_date(t0):
    """The date a season-t0 page comes into force: July 1 of t0. Every input
    the page reads (seasons t0-1 and earlier) is complete by then."""
    return pd.Timestamp(year=int(t0), month=7, day=1)


def check_as_of(t0, as_of):
    """Default the as-of date to the page date, and refuse a date outside the
    page's window [July 1 of t0, June 30 of t0+1]. Earlier, the page's own
    inputs are not all complete; later, the next page's inputs exist and
    valuing on this page would ignore them."""
    as_of = page_date(t0) if as_of is None else pd.Timestamp(as_of)
    assert page_date(t0) <= as_of < page_date(t0 + 1), (
        f"as-of date {as_of.date()} is outside the {t0} page's window "
        f"({page_date(t0).date()} to "
        f"{(page_date(t0 + 1) - pd.Timedelta(days=1)).date()})")
    return as_of


def load_signing_dates():
    """contract_id -> PuckPedia signing date (NaT where not on file)."""
    pp = pd.read_excel(F_PP_CONTRACTS, usecols=["contract_id", "signing_date"])
    assert pp["contract_id"].is_unique, "PuckPedia export: duplicate contract_id"
    dates = pd.to_datetime(pp["signing_date"], errors="coerce")
    return dict(zip(pp["contract_id"].astype(int), dates))


def contract_chain(spine, player_id, t0, signed, as_of):
    """The contracts a team holds for this player as of `as_of`, in order.

    Starts at the contract with a spine row in season t0 (the one being
    played; the first one found, exactly as before v1.3). Then repeatedly
    adds the contract that STARTS the season after the chain ends -- an
    extension -- provided its signing date is on or before `as_of`.
      * join key: contract_id within this player's spine rows
      * contiguity: an extension must start at end + 1; a later contract
        after a gap is not an extension of this one and is never added
      * missing signing date: never added (conservative, cannot be dated)
      * two candidates starting the same season (duplicate records): the
        lower contract_id, so the choice is deterministic
    Returns [] when no contract is active in t0."""
    rows = spine[spine["player_id"] == player_id]
    active = rows[rows["season_start"] == t0]
    if active.empty:
        return []
    first = rows.groupby("contract_id")["season_start"].min()
    last = rows.groupby("contract_id")["season_start"].max()
    chain = [int(active.iloc[0]["contract_id"])]
    while True:
        starts_next = first.index[first == last[chain[-1]] + 1]
        nxt = sorted(int(c) for c in starts_next
                     if int(c) not in chain
                     and pd.notna(signed.get(int(c), pd.NaT))
                     and signed[int(c)] <= as_of)
        if not nxt:
            return chain
        chain.append(nxt[0])


class SkaterProjector:
    """Builds the contract spine and signing dates once, then answers
    per-contract projection queries with xNPV 1's forecasts."""

    def __init__(self, model=None):
        # `model` is accepted for callers written when two models ran.
        assert model in (None, MODEL_NAME), (
            f"unknown skater model {model!r}; only {MODEL_NAME} remains "
            "(xNPV 0 archived 2026-10-02)")
        self.model = MODEL_NAME
        self._forecaster = None

        # ---- contract spine: seasons, costs, birthdates ---------------------
        #   * goalies are dropped here (contract_npv prices them separately)
        #   * join key to xNPV 1: nk = normalised "first last" + "|" + F/D,
        #     the key player_season_table builds as pkey; NAME_ALIASES
        #     resolves the one known collision
        #   * cost: the clause pipeline's cap hit, else PuckPedia's
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

        # ---- signing dates, for deciding which extensions are known (v1.3) --
        self.signed = load_signing_dates()

    @property
    def forecaster(self):
        """xNPV 1's per-page forecasts, built on first use."""
        if self._forecaster is None:
            import skater_forecast
            self._forecaster = skater_forecast.ContractForecaster()
        return self._forecaster

    def age_at(self, birthdate, season_start):
        """Integer age on Feb 1 of the season's ENDING year (the age_join.py
        convention). Reported on each row; xNPV 1 reads its own ages."""
        if pd.isna(birthdate):
            return None
        ref = pd.Timestamp(year=season_start + 1, month=2, day=1)
        a = ref.year - birthdate.year - (
            (ref.month, ref.day) < (birthdate.month, birthdate.day))
        return int(a)

    def project_contract(self, player_id, valuation_season, as_of=None):
        """All remaining seasons of the contract active at t0, plus every
        extension signed on or before `as_of` (default July 1 of t0), valued
        from the standpoint of `valuation_season` (t0). One row per season
        k = 0..end of the chain; empty when the player has no contract in t0
        or xNPV 1 has no forecast for him on this page."""
        as_of = check_as_of(valuation_season, as_of)
        chain = contract_chain(self.spine, player_id, valuation_season,
                               self.signed, as_of)
        if not chain:
            return pd.DataFrame()
        cid = chain[0]                    # the contract being played in t0
        rows = (self.spine[self.spine["contract_id"].isin(chain)
                           & (self.spine["season_start"] >= valuation_season)]
                .sort_values("season_start"))
        # GUARD: k is the row position, so the chain must give exactly one
        # row per consecutive season. A duplicate season row would shift
        # every later season's discount, chance of playing and cap path.
        ss = rows["season_start"].to_numpy()
        assert len(ss) and ss[0] == valuation_season and (
            np.diff(ss) == 1).all(), (
            f"player {player_id} t0={valuation_season}: contract chain "
            f"{chain} does not give one row per consecutive season: {list(ss)}")
        nk = rows.iloc[0]["nk"]
        return self._project_xnpv1(player_id, valuation_season, as_of, rows, cid, nk)

    def _project_xnpv1(self, player_id, valuation_season, as_of, rows, cid, nk):
        """One row per contract season: the WAR and chance of playing from
        xNPV 1, priced on xNPV 1's price line.

        For season k (k = 0 is the valuation season, unplayed on 1 July):
          projected_war  xNPV 1's WAR if he plays, rate_82 x gp_share
          p_play         xNPV 1's chance he plays that season, contract
                         status read at `as_of` (1 July of the page unless an
                         in-season date is given); contract_npv multiplies
                         the value by it (D16(i): survival on the value side)
          value_dollars  E[max(price, league minimum)] with the price on
                         xNPV 1's line (position slope) and the ex-ante cap
                         path, the spread being xNPV 1's own miss at k
                         (skater_forecast.war_if_plays_sd), k = 0 included
        Returns an empty frame when xNPV 1 has no anchor for the player on
        this page (no qualifying season in its three-season window or the
        returning-player lookback)."""
        from skater_forecast import war_if_plays_sd, MODEL_NAME
        horizon = len(rows) - 1
        fc = self.forecaster.forecast(nk, valuation_season, horizon, as_of)
        if fc is None:
            return pd.DataFrame()
        age = self.age_at(rows.iloc[0]["bd"], valuation_season)
        _posgrp = posgrp_from_nk(nk)
        # v1.6: xNPV 1's own price line once locked, Stage 3 until then.
        # v2.0 (directive 4): the TERM-IN line, priced on the term REMAINING at
        # the valuation date, the same for every remaining season (the chain's
        # seasons from t0 on, extensions signed by as_of included; at the first
        # season of a contract this is its full length). The term-free line is
        # priced beside it as the sensitivity.
        _alpha, _bf, _bd, _gamma, _line = price_constants(MODEL_NAME)
        _slope = _bd if _posgrp.startswith("D") else _bf
        _af, _bff, _bdf, _gf, _linef = price_constants(MODEL_NAME, term_free=True)
        _slopef = _bdf if _posgrp.startswith("D") else _bff
        term_years = len(rows)
        out = []
        for k, (_, r) in enumerate(rows.iterrows()):
            f = fc.iloc[k]
            assert int(f["h"]) == k, "forecast rows out of step with contract seasons"
            season = int(r["season_start"])
            w = float(f["war_if_plays"])
            ceil = cap_path(valuation_season, k)
            lm = league_min_path(season)
            val_raw = (_alpha + _slope * w + _gamma * term_years) * ceil
            sd_w = war_if_plays_sd(k)
            val = expected_floored_value(val_raw, _slope * sd_w * ceil, lm)   # D10 floor
            val_raw_f = (_af + _slopef * w) * ceil                            # term-free
            val_f = expected_floored_value(val_raw_f, _slopef * sd_w * ceil, lm)
            out.append({
                "player_id": player_id, "full_name": r["full_name"],
                "contract_id": int(r["contract_id"]),
                "active_contract_id": cid,
                "is_extension": int(r["contract_id"]) != cid,
                "as_of": as_of.date().isoformat(),
                "season_start": season, "k": k,
                "valuation_season": valuation_season, "age_at_valuation": age,
                "model": MODEL_NAME,
                "anchor_war": float(f["tw_WAR"]),          # xNPV 1's trailing total
                "anchor_source": "stale_history" if f["stale_history"] else "trailing_3",
                "path": MODEL_NAME,
                "decay_ratio": np.nan, "multiplier_applied": np.nan,
                "ratio_floored": False, "decay_ratio_raw": np.nan,
                "rate_82": float(f["rate_82"]), "gp_share": float(f["gp_share"]),
                "projected_war": w,
                "p_play": float(f["p_play"]), "p_play_dated": f["p_play_dated"],
                "expected_war": float(f["p_play"]) * w,
                "extrapolated": bool(f["extrapolated"]),
                "cap_ceiling_exante": ceil, "league_min": lm,
                "posgrp": _posgrp, "slope_used": _slope,
                "alpha_used": _alpha, "price_line": _line,
                "term_years": term_years, "gamma_used": _gamma,
                "term_premium_dollars": _gamma * term_years * ceil,
                "value_dollars_term_free": val_f,
                "surplus_dollars_term_free": val_f - r["cost"],
                "value_dollars": val, "floor_bound": val_raw < lm,
                "value_point_estimate": max(val_raw, lm),
                "uncertainty_correction": val - max(val_raw, lm),
                "proj_sd_war": sd_w,
                "sd_placeholder": False,
                "cost_dollars": r["cost"],
                "surplus_dollars": val - r["cost"],
            })
        return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# VALIDATION BATTERY (runs when executed directly; v2.0 tests xNPV 1)
# ---------------------------------------------------------------------------
def validate():
    log("=" * 74)
    log("LAYER 2 VALIDATION BATTERY  (xNPV 1)")
    log("=" * 74)

    # ---- 1. the price lines ---------------------------------------------------
    # Stage 3 must equal the value engine's locked constants (one definition
    # in the project), and xNPV 1 must be priced on its own locked line, not
    # the provisional fallback.
    import skater_value_engine as SVE
    L = SVE.NEW_LOCKED
    gap = max(abs(ALPHA - L["alpha"]), abs(BETA - L["beta"]), abs(BETA_D_ADD - L["beta_d_add"]))
    log(f"\n[1] Stage 3 constants equal skater_value_engine.NEW_LOCKED: largest gap {gap:.1e}")
    assert gap < 1e-10, "this file's Stage 3 constants differ from the value engine's"
    assert XNPV1_RATE is not None, "XNPV1_RATE is None: xNPV 1 would price on the provisional line"
    a, bf, bd, g, line = price_constants()
    af, bff, bdf, _gf, linef = price_constants(term_free=True)
    c = CAP_CEILING[2025]
    log(f"    in force: {line}: ${a * c / 1e6:.3f}M + ${bf * c / 1e6:.3f}M per forecast win "
        f"(forwards), ${bd * c / 1e6:.3f}M (defence), + ${g * c / 1e6:.3f}M a season per year of "
        f"remaining term, at the ${c / 1e6:.1f}M ceiling")
    log(f"    sensitivity: {linef}: ${af * c / 1e6:.3f}M + ${bff * c / 1e6:.3f}M per forecast win "
        f"(forwards), ${bdf * c / 1e6:.3f}M (defence)")

    # ---- 2. the floor formula against a simulation ----------------------------
    # E[max(X, F)] for X ~ N(mu, sd): closed form against 4M draws, tolerance
    # five of the simulation's own standard errors.
    log("\n[2] E[max(price, floor)], closed form against 4,000,000 draws:")
    rng = np.random.default_rng(36)
    for mu, sd, fl in ((0.5e6, 1.5e6, 0.775e6), (0.9e6, 1.0e6, 0.775e6), (3.0e6, 2.5e6, 0.775e6)):
        x = np.maximum(rng.normal(mu, sd, 4_000_000), fl)
        cf = expected_floored_value(mu, sd, fl)
        se = x.std() / np.sqrt(len(x))
        log(f"    point ${mu / 1e6:.2f}M, spread ${sd / 1e6:.2f}M: closed ${cf:,.0f}  "
            f"simulated ${x.mean():,.0f}  (gap ${abs(cf - x.mean()):,.0f}, 5 s.e. ${5 * se:,.0f})")
        assert abs(cf - x.mean()) < 5 * se, "the floor formula disagrees with the simulation"

    # ---- 3. priced contracts: the arithmetic, row by row ----------------------
    # A fixed sample of contracts at their first 2018-2025 season. Each priced
    # season is recomputed from the forecast, the price line, the cap path and
    # the floor, and must match to a millionth of a dollar.
    from skater_forecast import war_if_plays_sd
    sp = SkaterProjector()
    firsts = (sp.spine[sp.spine["season_start"].between(2018, 2025)]
              .sort_values(["contract_id", "season_start"])
              .groupby("contract_id", as_index=False).first())
    sample = firsts.sample(min(300, len(firsts)), random_state=7)
    priced, unpriced, rows_checked, worst = 0, 0, 0, 0.0
    for _, r in sample.iterrows():
        t0 = int(r["season_start"])
        pr = sp.project_contract(int(r["player_id"]), t0)
        if pr.empty:
            unpriced += 1
            continue
        priced += 1
        assert (pr["model"] == MODEL_NAME).all() and (pr["price_line"] == line).all()
        assert list(pr["k"]) == list(range(len(pr))), "seasons out of order"
        assert pr["p_play"].between(0, 1).all(), "a chance of playing outside [0, 1]"
        fc = sp.forecaster.forecast(r["nk"], t0, len(pr) - 1)
        slope = bd if posgrp_from_nk(r["nk"]).startswith("D") else bf
        slopef = bdf if posgrp_from_nk(r["nk"]).startswith("D") else bff
        assert (pr["term_years"] == len(pr)).all(), "the remaining term is not the seasons left"
        for k, x in pr.iterrows():
            ceil = cap_path(t0, int(x["k"]))
            wk = float(fc.iloc[int(x["k"])]["war_if_plays"])
            sd_ = war_if_plays_sd(int(x["k"]))
            lm_ = league_min_path(int(x["season_start"]))
            raw = (a + slope * wk + g * len(pr)) * ceil
            want = expected_floored_value(raw, slope * sd_ * ceil, lm_)
            want_f = expected_floored_value((af + slopef * wk) * ceil, slopef * sd_ * ceil, lm_)
            worst = max(worst, abs(want - x["value_dollars"]), abs(want_f - x["value_dollars_term_free"]))
            assert x["value_dollars"] >= x["league_min"] - 1e-6, "a season valued below the minimum"
            rows_checked += 1
    log(f"\n[3] {len(sample)} sampled contracts (first 2018-2025 season): {priced} priced, "
        f"{unpriced} with no xNPV 1 forecast on their page")
    log(f"    {rows_checked:,} seasons recomputed from forecast, line, cap path and floor: "
        f"largest gap ${worst:.2e}")
    # Most contracts have a forecast (2,759 of the skaters in the 2026-10-02 sweep);
    # fewer than half would mean the spine-to-forecast join has broken.
    assert priced >= 0.5 * len(sample), "under half the sampled contracts are priced: check the name join"
    assert worst < 1e-6, "priced seasons do not reproduce from their inputs"

    # ---- 4. spot demos ----------------------------------------------------------
    log("\n[4] spot demos:")
    for name, t0 in (("Connor McDavid", 2024), ("Brad Marchand", 2023), ("Matvei Michkov", 2025)):
        pid = sp.spine[(sp.spine["full_name"] == name)
                       & (sp.spine["season_start"] == t0)]["player_id"]
        if pid.empty:
            log(f"    {name}: no contract-season at {t0}")
            continue
        pr = sp.project_contract(int(pid.iloc[0]), t0)
        if pr.empty:
            log(f"    {name}: no xNPV 1 forecast at {t0}")
            continue
        log(f"    {name} from {t0} (age {pr.iloc[0]['age_at_valuation']}, "
            f"trailing total {pr.iloc[0]['anchor_war']:.2f} WAR):")
        for _, x in pr.iterrows():
            log(f"      {x['season_start']}-{str(x['season_start'] + 1)[2:]}  k={x['k']}  "
                f"WAR if plays {x['projected_war']:+.2f}  plays {x['p_play']:.3f}  "
                f"value ${x['value_dollars'] / 1e6:5.2f}M  cost ${x['cost_dollars'] / 1e6:5.2f}M  "
                f"surplus ${x['surplus_dollars'] / 1e6:+6.2f}M" + ("  [floor]" if x["floor_bound"] else ""))

    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")


if __name__ == "__main__":
    validate()
