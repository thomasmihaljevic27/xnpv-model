"""
=============================================================================
 goalie_value_engine.py   v2.0                    D20 rebuild (2026-07-05)
                                          review item 1.1 (2026-07-26)
=============================================================================
 WHAT CHANGED IN v2.0 (Thomas, 2026-10-21, on 25_TESTS/goalie_review.py v1.0)
 ---------------------------------------------------------------------------
 STAGE G fits the goaltender price line the valuation engine locks (contract_npv.GOALIE_RATE): cap share on the
 goaltender's forecast WAR -- contract_npv.GoalieProjector's, kept 35%, pulled toward the league average, with its age
 term -- dated at the contract's signing (xnpv1_price_line.signing_page; the season h = start - page ahead), left-censored
 at the league minimum, with a term for contract length (and the same fit without term, the sensitivity). Sample:
 standard-level goaltender contracts starting 2015-2025 with a forecast at the signing. Every run must give the lock back
 (GUARD). Until v1.3 Stage G fitted least squares on the unpulled trailing WAR at the contract's start, and the valuation
 applied it to the pulled forecast (mean error +$0.52M a contract). The v2 spine's priced rows now carry the valuation
 engine's forecast for the season (forecast_war) and its price at the contract's own remaining term; contract_npv's
 check [1b] compares the forecasts.

 WHAT CHANGED IN v1.3 (Thomas, 2026-10-14: retire the 60/40 checks)
 ---------------------------------------------------------------------
 The RAW (un-prorated, 60/40) regime is removed: Stage P (the rebuild of the locked July spine
 to the cent), the raw rate guard in Stage G and the raw lambda check in Stage L. Each proved
 the code still reproduced a July figure; none priced anything. The live regime is unchanged
 (prorated D20 inputs, 50/30/20 with 62.5/37.5 for two seasons, lambda 0.65), so
 goalie_value_spine_v2.csv is identical (checked against the file before the change). The
 descriptions of Stage P and the raw guards below are the record of what v1.2 ran; a v1.2 run
 needs git at the commit before this one.

 WHAT CHANGED IN v1.2 (Thomas, 2026-10-05: "change it to 62.5/37.5 to match the skaters")
 -----------------------------------------------------------------------------------------
 A goaltender with exactly two prior seasons (t-1 and t-2) is weighted 62.5/37.5 in the
 live (prorated, D20 v2) regime: the 50/30 of the 50/30/20 cascade rescaled over the seasons
 he has, as the skater forecast weights every trailing measure. Until v1.2 it was a fixed
 60/40. The RAW regime keeps 60/40, because it must rebuild the locked spine to the cent
 (Stage P) and reproduce the locked rate and lambda (the raw guards). Through the cascade the
 change reaches the prorated rate fit, the prorated lambda search and the v2 spine; Stage L
 now stops if the prorated lambda leaves 0.65, the value contract_npv.LAMBDA_G applies.
 contract_npv.py's own goalie cascade changes with it (v2.3).

 WHAT CHANGED IN v1.1 (review item 1.1 -- flat carry into out-years)
 -------------------------------------------------------------------
 The locked pipeline priced every contract season beyond the last observed
 WAR season at the LEAGUE AVERAGE (2.189172466). That contradicts the
 flat-carry rule the goalie pillar already adopted, which requires a
 goaltender's OWN shrunken projection to be held constant across his
 contract. The placeholder is not neutral: it asserts that a specific
 goaltender is exactly average, and its error is signed by how far he
 actually sits from average. Elite starters on long deals were undervalued
 by roughly $1M to $2M in each affected season, weak goaltenders
 overvalued by a similar margin.

 v1.1 replaces the placeholder with a PLAYER-LEVEL FLAT CARRY: for a
 season the cascade cannot reach, the row takes the goaltender's own
 trailing anchor from the most recent season at which an anchor IS
 computable, and shrinks it with the same lambda. 98 rows across 38
 goaltenders are affected.

 Two properties of that rule worth stating, since both touch the paper's
 identification section:
   * It is look-ahead SAFE and strictly reduces the information used. The
     carried anchor is drawn from a season EARLIER than the row it fills,
     so its trailing window is older than the row's own would be.
   * It has no decay, by design -- the flat-carry rule specifies no aging
     curve for goaltenders. A carried anchor can therefore be more than
     one season stale where a goaltender has a gap in his WAR record. One
     row in the current data is stale by two seasons (M. Tomkins).

 Rows the cascade cannot reach AND for which no earlier anchor exists are
 never-played goaltenders (drafted or entry-level, contracts starting
 2026+), not out-years. There is nothing to carry for them. v1.1 leaves
 their VALUES untouched and only retags them, so the panel stops
 describing them as out-year rows. 83 rows across 47 goaltenders.
 Re-pricing that population is a separate, open decision: it is also the
 population contract_npv.py reads to recover GOALIE_LEAGUE_AVG at import
 (the mode of shrunk_projection over rows tagged no_observed_war_history),
 so removing the league-average fill there breaks a downstream startup
 assert until that recovery is re-plumbed. Do not fold it into this fix.

 REGIME GATING (why the carry is behind a flag)
 ----------------------------------------------
 build_spine() serves two masters: the Stage P parity rebuild, which must
 reproduce the LOCKED v1 file to the cent AND on every weight_scheme tag,
 and the Stage L v2 build, which is the corrected artifact. An
 unconditional carry fails parity on 98 rows and two tags, and __main__
 halts before Stage G and Stage L ever run. So the carry is behind
 carry_out_years=, default False. Stage P calls it False (the lock stays
 exactly reproducible); Stage L calls it True.
=============================================================================
 WHY THIS FILE EXISTS
 --------------------
 The goalie value chain (trailing 50/30/20 cascade -> lambda shrinkage ->
 dollar rate -> goalie_value_spine.csv) was built inside the 2026-07-02
 session and only its OUTPUT survived to disk -- the builder itself was
 never delivered. That is a reproducibility hole for the paper and a
 blocker for D20 (schedule proration), which must re-run the lambda
 estimation and the rate fit on prorated inputs, not just reuse numbers.

 This file closes both: it is a from-scratch rebuild that must FIRST
 reproduce the locked spine exactly (the parity gate below), and only
 then applies D20.

 HOW IT RUNS (three stages, in plain English)
 --------------------------------------------
   STAGE P  PARITY GATE. Rebuild every row of the locked spine in RAW
            (un-prorated) mode and compare against goalie_value_spine.csv
            on disk. Every priced row must match to the cent. If this
            fails, this file is NOT the pipeline that built the lock and
            nothing downstream can be trusted.
   STAGE G  RATE GUARD + D20 REFIT. Reproduce the locked goalie market
            rate from the raw contract sample (n=350; alpha=1.398%,
            beta=1.097% cap-share), then refit the same regression on
            prorated trailing WAR. The prorated coefficients become the
            D20 goalie rate.
   STAGE L  LAMBDA RE-ESTIMATION (D20). Re-run the original shrinkage
            procedure -- 5-fold cross-validation split BY PLAYER (so a
            goalie's seasons never sit in both training and test folds),
            GP>=20 season pairs, multiple random seeds -- on prorated
            data. Then build goalie_value_spine.csv v2 with the prorated
            cascade, the re-estimated lambda, and the refit rate.

 LOCKED BEHAVIOR PRESERVED EXACTLY (recovered by forensics, 2026-07-05)
 ----------------------------------------------------------------------
 * Cascade: 50/30/20 over (t-1, t-2, t-3) when all three prior seasons
   exist; 60/40 over (t-1, t-2) when only those two; t-1 alone when only
   it exists; league average when no history at all.
 * NO GP filter on cascade inputs (verified: a 2-GP season was used as a
   t-1 anchor in the locked spine). Documented quirk, deliberately kept:
   changing it would silently change hundreds of rows outside D20's
   mandate. The GP>=20 filter applies only inside the lambda CV, exactly
   as in the original estimation.
 * Shrinkage: shrunk = (1 - LAMBDA) * trailing + LAMBDA * LEAGUE_AVG.
   LAMBDA is the weight on the LEAGUE AVERAGE (0.65 locked -- a goalie
   keeps only 0.35 of his trailing signal). This direction was flipped
   once in old documentation; the spine itself was always correct and
   this file matches the spine.
 * LEAGUE_AVG = 2.189172466: recovered from the locked spine's no-history
   rows. Its exact estimation formula did not survive the session; it is
   treated as a locked constant and NOT re-estimated under D20 (it is a
   center point; proration moves the would-be mean second-order).
 * Team-split seasons (goalie traded mid-year) collapse to one row per
   goalie-season with WAR and GP summed, before anything else.
 * Season rows before 2015 -> excluded (pre-date the rate sample).
   Season rows 2026+ with no reachable anchor -> static league-average
   placeholder. THIS IS THE v1.1 CORRECTION TARGET: preserved only in the
   parity regime (carry_out_years=False), replaced by the flat carry in
   the v2 build. See the v1.1 note at the top of this header.
 * Cap ceilings: published values 2015-2025; 3%/yr extrapolation beyond.

 D20 (the only behavioral change, and only in Stage L's v2 output)
 -----------------------------------------------------------------
 WAR season totals from the two schedule-shortened seasons are scaled to
 an 82-game basis BEFORE the cascade: 2019-20 x 82/70, 2020-21 x 82/56.
 This corrects a league-wide mechanical artifact only -- games a goalie
 missed within a normal-length season still count against him.

 HOW TO RUN (Windows):  python 20_CODE/goalie_value_engine.py  (needs .env)
 Inputs -- SOURCE_DIR: Goalies_WAR.csv;  OUTPUT_DIR: contract_season_spine.csv,
   goalie_value_spine.csv (the parity oracle);  PUCKPEDIA_CONTRACTS_XLSX
 Outputs (OUTPUT_DIR): goalie_value_spine_v2.csv, goalie_value_engine_run_log.txt
=============================================================================
"""

import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from dotenv import load_dotenv

load_dotenv()

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])   # vendor inputs, read-only
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])   # generated spines / logs
F_GOALIE_WAR   = SOURCE_DIR / "Goalies_WAR.csv"
F_SEASON_SPINE = OUTPUT_DIR / "contract_season_spine.csv"
F_LOCKED_SPINE = OUTPUT_DIR / "goalie_value_spine.csv"      # the July file; read only by the carry report
F_CONTRACT_XLSX = Path(os.environ["PUCKPEDIA_CONTRACTS_XLSX"])
OUT_SPINE_V2 = OUTPUT_DIR / "goalie_value_spine_v2.csv"
OUT_LOG      = OUTPUT_DIR / "goalie_value_engine_run_log.txt"

# ---------------------------------------------------------------------------
# CONSTANTS (v1.3: the raw regime's locked constants and guards are retired)
# ---------------------------------------------------------------------------
# The two-season fallback's weights (t-1, t-2): 50/30 rescaled (Thomas, 2026-10-05).
TWO_SEASON = (0.625, 0.375)
LAMBDA_LIVE = 0.65            # contract_npv.LAMBDA_G; Stage L stops if the search leaves it
LEAGUE_AVG  = 2.189172466     # shrinkage target (recovered constant, see header)
# ---- A1/A2 stale-anchor constants (2026-07-29) ---------------------------
# A goaltender with no t-1 season but a usable t-2 or t-3 is a real player
# with a real, older anchor -- not a player with no history. Both numbers
# below were measured on the 93 affected in-window contract-season rows and
# independently re-verified 2026-07-29 (gate reproduced exactly at 29/93).
#
#   STALE_TARGET   the conditional mean WAR of that population GIVEN the
#                  goaltender plays (0.650, n=29). LEAGUE_AVG is the mean of
#                  a population he is not in, so shrinking him toward it
#                  pushes his value UP, which is the wrong direction.
#
#   STALE_MAXBACK  how many seasons back the carry search may reach for these
#                  rows. 3 seasons. The mean carry gap is 1.26 seasons and
#                  capping changes the mean anchor not at all, so this does
#                  not bind on the 93. It exists to stop the 69 rows whose
#                  last season is more than three years back from acquiring
#                  an anchor they should not have -- a goaltender four years
#                  absent is a different asset, not a stale one.
STALE_TARGET  = 0.650
STALE_MAXBACK = 3

# D20 schedule-proration factors (single source of truth is
# skater_value_engine.PRORATION; duplicated here with an import guard so
# this file also runs standalone -- the assert keeps the two in sync).
PRORATION = {2019: 82 / 70, 2020: 82 / 56}
try:
    from skater_value_engine import PRORATION as _SK_PRORATION
    assert _SK_PRORATION == PRORATION, "PRORATION drifted between engines"
except ImportError:
    pass                                  # standalone run: local dict governs

CAP_CEILING = {                           # published ceilings, dollars
    2015: 71.4e6, 2016: 73.0e6, 2017: 75.0e6, 2018: 79.5e6, 2019: 81.5e6,
    2020: 81.5e6, 2021: 81.5e6, 2022: 82.5e6, 2023: 83.5e6, 2024: 88.0e6,
    2025: 95.5e6,
    2026: 104.0e6, 2027: 113.5e6,   # published in the 2025 MOU -> 'actual'
}
CAP_GROWTH = 0.03                         # extrapolation past 2027 (D11/D17)

LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))


def norm_name(s):
    """Same normalization family as the rest of the project: accents
    stripped, lower-case, punctuation removed. Goalies have no known
    same-name collisions, so no position key is needed."""
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().replace("-", " ")
    s = re.sub(r"[.'\u2019]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# BUILDING BLOCKS
# ---------------------------------------------------------------------------
def goalie_war_lut(prorate):
    """(normalized name, season start year) -> season-total WAR.
    Team-split seasons summed FIRST, then (optionally) D20 proration."""
    import contract_source as _CSG               # 2026-10-21: the two Matt Murrays kept apart
    g = _CSG.read_goalie_war(F_GOALIE_WAR)
    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    agg = (g.groupby(["Goalie", "syr"], as_index=False)
             .agg(WAR=("WAR", "sum"), GP=("GP", "sum")))
    if prorate:
        agg["WAR"] = agg["WAR"] * agg["syr"].map(PRORATION).fillna(1.0)
    agg["nk"] = agg["Goalie"].map(norm_name)
    return (agg.set_index(["nk", "syr"])["WAR"].sort_index(),
            agg.set_index(["nk", "syr"])["GP"].sort_index())


def cascade(nk, t0, lut, prorate=False):
    """The trailing cascade. Returns (trailing value or None, tag).
    NO GP filter -- see header. 50/30/20 needs all three priors; with t-1
    and t-2 only, 62.5/37.5 (TWO_SEASON; v1.3: the raw regime's 60/40 is
    retired, so `prorate` no longer changes the weights); t-1 alone otherwise; None if no t-1..t-3
    history is usable under those rules (t-2/t-3 without t-1 -> no history,
    which is what the locked spine does)."""
    def get(y):
        v = lut.get((nk, y), np.nan)
        return np.nan if isinstance(v, pd.Series) else v
    w1, w2, w3 = get(t0 - 1), get(t0 - 2), get(t0 - 3)
    if pd.notna(w1) and pd.notna(w2) and pd.notna(w3):
        return 0.5 * w1 + 0.3 * w2 + 0.2 * w3, "50/30/20"
    if pd.notna(w1) and pd.notna(w2):
        a, b = TWO_SEASON
        return a * w1 + b * w2, "62.5/37.5"
    if pd.notna(w1):
        return w1, "t-1 only"
    return None, "no_observed_war_history"


def carry_anchor(nk, t0, lut, maxback=12, prorate=False):
    """REVIEW ITEM 1.1 -- the player-level flat carry.

    Plain English: this row sits past the end of the goaltender's observed
    record, so the trailing cascade has nothing to work with. Instead of
    substituting the league average, walk BACKWARDS from this season and
    find the most recent season at which the cascade COULD still reach a
    real anchor for this goaltender, then use that anchor.

    Concretely, if WAR runs through 2025-26, the last season with a
    reachable anchor is 2026-27 (its t-1 is the completed 2025-26). A
    contract season of 2027-28 or later therefore carries the 2026-27
    anchor. A goaltender with a gap in his record carries from further
    back, which is the flat-carry rule working as specified -- there is no
    aging curve for goaltenders and so no decay to apply.

    Search bound: 12 seasons. That is longer than any NHL contract, so the
    bound can never bite on a goaltender who has a record at all; it exists
    so a never-played goaltender exits in bounded time rather than walking
    to the beginning of the data.

    Returns (trailing anchor, source season, cascade tag) or (None, None,
    None) when no earlier anchor exists anywhere -- which means the
    goaltender has never played, not that this is an out-year.
    """
    # maxback=12 (the default) preserves item 1.1 exactly: longer than any
    # NHL contract, so the bound cannot bite on a goaltender with a record.
    # The A1 in-window caller passes STALE_MAXBACK=3 instead, because a
    # four-year absence is a different asset rather than a stale anchor.
    for s in range(t0 - 1, t0 - 1 - maxback, -1):
        tw, scheme = cascade(nk, s, lut, prorate)
        if tw is not None:
            return tw, s, scheme
    return None, None, None


def ceiling_for(season):
    """Published ceiling, or 3%/yr extrapolation past the last known year."""
    if season in CAP_CEILING:
        return CAP_CEILING[season], "actual"
    last = max(CAP_CEILING)
    return CAP_CEILING[last] * (1 + CAP_GROWTH) ** (season - last), "extrapolated"


def build_spine(lam, alpha_g, beta_g, prorate, carry_out_years=False):
    """One spine build. Row population and all tags mirror the locked file;
    lam/alpha_g/beta_g/prorate select the regime (raw parity vs D20 v2).

    carry_out_years (v1.1, review item 1.1): False reproduces the LOCKED
    behaviour exactly, including the league-average placeholder on
    unreachable seasons -- this is what Stage P must call, or parity fails
    on 98 rows and the run halts. True applies the player-level flat carry
    and is what the v2 artifact is built with. The default is False so that
    any caller who has not thought about the regime gets the reproducible
    one rather than the corrected one."""
    lut, _ = goalie_war_lut(prorate)
    cs = pd.read_csv(F_SEASON_SPINE)
    gl = cs[cs["position"] == "Goaltender"].copy()
    gl["full_name"] = gl["first_name"].astype(str) + " " + gl["last_name"].astype(str)
    import contract_source as _CS                # 2026-10-14: WAR spelling for crosswalked ids
    gl["full_name"] = _CS.war_full_name(gl, gl["full_name"])
    gl["nk"] = gl["full_name"].map(norm_name)
    gl["cost"] = gl["model_cap_hit"].astype(float)   # 2026-10-19/20 (Thomas): PuckPedia's, the clause figure after a late signing's year 1

    rows = []
    for r in gl.itertuples():
        t0 = int(r.season_start)
        base = dict(contract_id=r.contract_id, player_id=r.player_id,
                    ep_id=r.ep_id, nhl_id=r.nhl_id, full_name=r.full_name,
                    season=r.season, season_start=t0)
        # pre-2015 rows sit outside the rate sample -> excluded, cost only
        if t0 < 2015:
            rows.append({**base, "trailing_war": "",
                         "weight_scheme": "excluded",
                         "shrunk_projection": "", "predicted_cap_pct": "",
                         "cap_ceiling_used": "", "cap_ceiling_source": "pre_2015_excluded",
                         "carry_source_season": "",   # v1.1 column, never set here
                         "value_dollars": "", "cost_dollars": r.cost,
                         "surplus_dollars": ""})
            continue
        # cascade for every row -- a 2026 valuation legitimately sees the
        # completed 2025-26 season as its t-1. Only when the cascade finds
        # NOTHING does the future/no-history split apply.
        tw, scheme = cascade(r.nk, t0, lut, prorate)
        carry_src = ""                     # v1.1: season the anchor came from
        stale = False                      # A1: in-window stale-anchor row?
        if tw is None and t0 >= 2026:
            if not carry_out_years:
                # LOCKED regime: league-average placeholder, tag verbatim.
                scheme = "future_season_static_placeholder"
            else:
                # v1.1 regime: carry this goaltender's own anchor forward.
                # maxback left at the default -- item 1.1 unchanged.
                ctw, csrc, cscheme = carry_anchor(r.nk, t0, lut, prorate=prorate)
                if ctw is not None:
                    tw, carry_src = ctw, csrc
                    scheme = f"flat_carry_out_year[{cscheme}@{csrc}]"
                else:
                    # Never played. Nothing to carry -- values unchanged from
                    # the locked file, tag corrected so the panel no longer
                    # describes these as out-year rows. Re-pricing them is a
                    # separate open decision (see header).
                    scheme = "no_history_future_season"
        elif tw is None and carry_out_years:
            # A1 (2026-07-29). An IN-WINDOW season with no t-1 but a usable
            # older anchor. This is the same defect item 1.1 fixed for
            # out-years, and the same function fixes it: carry_anchor walks
            # back to the most recent season at which the cascade could still
            # reach a real anchor. Before this branch existed, these rows fell
            # through to "no observed WAR history", which is how Carey Price,
            # Corey Crawford, Ben Bishop, Spencer Knight and Carter Hart were
            # all recorded as never having played.
            #
            # Bounded at STALE_MAXBACK rather than the out-year default: an
            # out-year carry is asking "what is this goaltender worth in a
            # season beyond our data", where any reachable anchor beats the
            # league average. This branch is asking "what is he worth now,
            # having missed a season", and a four-year absence is a different
            # question.
            ctw, csrc, cscheme = carry_anchor(r.nk, t0, lut,
                                              maxback=STALE_MAXBACK, prorate=prorate)
            if ctw is not None:
                tw, carry_src = ctw, csrc
                stale = True
                scheme = f"stale_anchor_carry[{cscheme}@{csrc}]"
            # else: genuinely no reachable history. Tag and value are left
            # exactly as cascade returned them, which keeps decision A4 (the
            # old "83 rows" question) untouched and keeps guard (5) passing.
        # A2 (2026-07-29): route the shrinkage target by population. An
        # in-window stale-anchor goaltender shrinks toward the conditional mean
        # of goaltenders who came back, not toward the league average.
        # NOTE: item 1.1's out-year carried rows deliberately still shrink
        # toward LEAGUE_AVG. Two carried populations therefore now use
        # different targets. That inconsistency is recorded as an open
        # question rather than resolved silently inside this patch.
        target = STALE_TARGET if stale else LEAGUE_AVG
        # shrinkage: lam is the weight on the shrinkage TARGET
        shrunk = LEAGUE_AVG if tw is None else (1 - lam) * tw + lam * target
        pc = alpha_g + beta_g * shrunk
        ceil, src = ceiling_for(t0)
        val = pc * ceil
        rows.append({**base,
                     # REVIEW ITEM 1.9. This column used to carry the text
                     # "no_observed_war_history" on 748 rows, which turned the
                     # whole column into text and made every arithmetic use of
                     # it fail silently or need a conversion first. The locked
                     # v1 file has it as a proper number, so this was a
                     # regression, not the original design. The information is
                     # not lost: weight_scheme already says
                     # "no_observed_war_history" on exactly those rows, which
                     # is where a reader should look for it. Blank here means
                     # "no number exists", the same as it does for the
                     # pre-2015 excluded rows.
                     "trailing_war": ("" if tw is None else tw),
                     "weight_scheme": scheme, "shrunk_projection": shrunk,
                     "predicted_cap_pct": pc,
                     "cap_ceiling_used": ceil / 1e6, "cap_ceiling_source": src,
                     "carry_source_season": carry_src,
                     "value_dollars": val, "cost_dollars": r.cost,
                     "surplus_dollars": (val - r.cost) if pd.notna(r.cost) else ""})
    out = pd.DataFrame(rows)

    # ---- v1.1 guards -------------------------------------------------------
    # These run on every build, in both regimes, and are cheap. Each one
    # protects a property something downstream relies on.
    # Both carry families are checked by the same guards below. The
    # look-ahead assert (carry source strictly earlier than the row) is the
    # one that matters most for the A1 rows, since they sit inside the
    # observed window where a forward-looking carry would be a real
    # violation rather than an impossibility.
    carried = (out["weight_scheme"].astype(str)
               .str.startswith(("flat_carry_out_year", "stale_anchor_carry")))
    if not carry_out_years:
        # (1) The parity regime must be byte-for-byte the locked behaviour.
        assert not carried.any(), \
            "parity regime produced flat-carry rows -- the flag leaked"
        assert (out["carry_source_season"] == "").all(), \
            "parity regime populated carry_source_season"
    else:
        # (2) Every carried row must name the season it carried FROM, and
        #     that season must be strictly earlier than the row itself. This
        #     is the look-ahead guard: a carry from the row's own season or
        #     later would be using information that did not exist yet.
        assert carried.any(), "carry regime produced no flat-carry rows at all"
        cr = out[carried]
        assert (cr["carry_source_season"] != "").all(), \
            "flat-carry row with no recorded source season"
        assert (pd.to_numeric(cr["carry_source_season"])
                < cr["season_start"]).all(), \
            "flat-carry source season is not strictly earlier than the row"
        # (3) No carried row may sit on the league average unless the
        #     goaltender's own carried anchor genuinely lands there. This is
        #     the negative test on the fix: if the placeholder were still
        #     leaking through, it would show up here.
        on_avg = (cr["shrunk_projection"] - LEAGUE_AVG).abs() < 1e-9
        if on_avg.any():
            tw_num = pd.to_numeric(cr.loc[on_avg, "trailing_war"], errors="coerce")
            assert ((tw_num - LEAGUE_AVG).abs() < 1e-9).all(), \
                "carried row sits on LEAGUE_AVG without a matching own anchor"
        # (4) The placeholder tag must be gone entirely.
        assert not (out["weight_scheme"] == "future_season_static_placeholder").any(), \
            "future_season_static_placeholder survived the carry regime"
    # (5) contract_npv.py recovers GOALIE_LEAGUE_AVG at import time as the
    #     mode of shrunk_projection over rows tagged no_observed_war_history.
    #     That population is deliberately NOT touched by item 1.1; if this
    #     assert ever fires, that downstream startup assert is about to fail.
    # (5b) REVIEW ITEM 1.9. Every value in trailing_war must be either a
    #      number or blank -- never text. A single text value re-types the
    #      whole column and turns any later arithmetic into a silent failure.
    tw_col = out["trailing_war"]
    non_blank = tw_col[tw_col.astype(str).str.strip() != ""]
    assert pd.to_numeric(non_blank, errors="coerce").notna().all(), \
        "trailing_war holds a non-numeric value -- the column has re-typed " \
        "itself to text and downstream arithmetic will fail quietly"

    nh = out[out["weight_scheme"] == "no_observed_war_history"]
    assert len(nh) > 0 and ((nh["shrunk_projection"] - LEAGUE_AVG).abs() < 1e-9).all(), \
        "no_observed_war_history rows no longer carry LEAGUE_AVG exactly -- " \
        "contract_npv._recover_goalie_constants() will fail"
    return out


# ---------------------------------------------------------------------------
# STAGE G -- rate guard (raw) + D20 refit (prorated)
# ---------------------------------------------------------------------------
def _rate_sample(lut, prorate):
    """The n=350 goalie contract sample: goaltender contracts starting
    2015-2026, standard level, UFA/RFA, with a computable trailing anchor
    at the start year. Mirrors the skater engine's sample construction."""
    raw = pd.read_excel(F_CONTRACT_XLSX)
    raw["end_yr"] = pd.to_numeric(
        raw["contract_end"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")
    import contract_source as _CS0               # 2026-10-19: the one seasons rule (a buyout's first season)
    raw["start_yr"] = _CS0.contract_terms(raw)["first_yr"]
    g = raw[(raw["position"] == "Goaltender")
            & (raw["contract_level"] == "standard_level")
            & raw["start_yr"].between(2015, 2026)].copy()
    import contract_source as _CS                # 2026-10-14: WAR spelling for crosswalked ids
    g["nk"] = _CS.war_full_name(g, g["first_name"].astype(str) + " " + g["last_name"].astype(str)).map(norm_name)
    g["wWAR"] = [cascade(k, int(s), lut, prorate)[0] if pd.notna(s) else None
                 for k, s in zip(g["nk"], g["start_yr"])]
    g = g[g["wWAR"].notna()].copy()
    g["cap_pct"] = g["aav"] / g["start_yr"].map(
        lambda s: ceiling_for(int(s))[0])
    return g[g["cap_pct"].notna()]


def _projector():
    """contract_npv's GoalieProjector on the contract-season spine, as NPVEngine builds it."""
    import contract_npv as CN
    import contract_source as _CS
    from skater_forward_projection import norm_name as _nn
    full = pd.read_csv(F_SEASON_SPINE)
    full["full_name"] = _CS.war_full_name(full, full["first_name"].astype(str) + " " + full["last_name"].astype(str))
    full["nname"] = full["full_name"].map(_nn)
    full["bd"] = pd.to_datetime(full["birthdate"], errors="coerce")
    return CN, CN.GoalieProjector(full), _nn


def stage_rate():
    """v2.0: the goaltender price line, fitted on the forecast dated at each contract's signing (see the header)."""
    import hashlib
    import xnpv1_price_line as XPL
    from skater_forward_projection import league_min_path
    log("=" * 74)
    log("STAGE G: the goaltender price line (v2.0: the pulled forecast with its age term, dated at the signing, "
        "censored at the league minimum, with term)")
    log("=" * 74)
    CN, GP, _nn = _projector()
    raw = pd.read_excel(F_CONTRACT_XLSX)
    import contract_source as _CS
    raw["start_yr"] = _CS.contract_terms(raw)["first_yr"]
    d = raw[(raw["position"] == "Goaltender") & (raw["contract_level"] == "standard_level")
            & raw["start_yr"].between(2015, 2025)].copy()
    d["nname"] = _CS.war_full_name(d, d["first_name"].astype(str) + " " + d["last_name"].astype(str)).map(_nn)
    d["cap"] = d["start_yr"].map(lambda y: ceiling_for(int(y))[0])
    d["cap_pct"] = d["aav"] / d["cap"]
    d["floor_pct"] = d["start_yr"].map(league_min_path) / d["cap"]
    d["signed"] = pd.to_datetime(d["signing_date"], errors="coerce")
    d["bd"] = pd.to_datetime(d["birthdate"], errors="coerce")
    d["length"] = pd.to_numeric(d["length"], errors="coerce")
    xs, why = [], []
    for r in d.itertuples():
        page, ok = XPL.signing_page(r.signed)
        h = None if page is None else int(r.start_yr) - int(page)
        if not ok or h is None or h < 0:
            xs.append(np.nan); why.append("no signing page" if not ok else "signed after start"); continue
        a0 = None if pd.isna(r.bd) else int(page) - r.bd.year - ((9, 15) < (r.bd.month, r.bd.day))
        fc, src = GP.forecast(r.nname, int(page), h, a0)
        # a season in the year before the signing, as the tested sample required (goalie_review.py Part D): a stale
        # anchor's forecast is a fallback for valuing a goaltender who missed a season, not a price the market set
        if fc is not None and src == "stale_anchor":
            xs.append(np.nan); why.append("no season in the year before the signing (stale anchor)"); continue
        xs.append(np.nan if fc is None else fc[h][1]); why.append("" if fc is not None else "no forecast at the signing")
    d["x"] = xs
    for w, n in pd.Series(why)[pd.Series(why) != ""].value_counts().items():
        log(f"  left out, {w}: {n}")
    d = d[np.isfinite(d["x"]) & d["cap_pct"].notna() & d["length"].notna()].reset_index(drop=True)
    key = d[["nname", "start_yr", "cap_pct"]].astype(str).agg("|".join, axis=1).sort_values()
    fp = hashlib.sha1("\n".join(key).encode()).hexdigest()[:12]
    cap25 = ceiling_for(2025)[0]
    out = {}
    for lab, cols in (("term-in", ["x", "length"]), ("term-free", ["x"])):
        f = XPL.fit_censored(d["cap_pct"], d[cols].to_numpy(float), d["floor_pct"])
        c = f["coef"]
        out[lab] = dict(alpha=float(c[0]), beta=float(c[1]), gamma_term=float(c[2]) if len(c) > 2 else 0.0,
                        sigma=float(f["sigma"]), n=int(len(d)), rows_fingerprint=fp, converged=bool(f["converged"]))
        log(f"  {lab}: n={len(d)} (fingerprint {fp}; {int((d['cap_pct'] <= d['floor_pct'] + 1e-12).sum())} at the minimum)  "
            f"alpha={c[0]:.10f} (${c[0] * cap25 / 1e6:.2f}M)  beta={c[1]:.10f} (${c[1] * cap25 / 1e6:.3f}M per WAR)"
            + (f"  gamma_term={c[2]:.10f} (${c[2] * cap25 / 1e6:.3f}M per year)" if len(c) > 2 else "")
            + f"  sigma={f['sigma']:.8f}  converged {f['converged']}")
    lock = {"term-in": CN.GOALIE_RATE, "term-free": CN.GOALIE_RATE_TERM_FREE}
    if lock["term-in"] is None:
        log("  [guard] contract_npv.GOALIE_RATE is not locked yet; to lock, in contract_npv.py:")
    bad = []
    for lab, got in out.items():
        lk = lock[lab]
        if lk is not None:
            gap = max(abs(got[k] - lk[k]) for k in ("alpha", "beta", "gamma_term"))
            same = got["converged"] and gap <= 1e-8 and got["n"] == lk["n"] and got["rows_fingerprint"] == lk["rows_fingerprint"]
            log(f"  [guard] {lab} against the lock: n {got['n']} (locked {lk['n']}), fingerprint {fp} "
                f"(locked {lk['rows_fingerprint']}), largest gap {gap:.1e}: {'PASS' if same else 'GUARD FAILED'}")
            bad += [] if same else [lab]
        nm = "GOALIE_RATE" if lab == "term-in" else "GOALIE_RATE_TERM_FREE"
        log(f"    {nm} = dict(alpha={got['alpha']:.10f}, beta={got['beta']:.10f}, gamma_term={got['gamma_term']:.10f}, "
            f"n={got['n']}, sigma={got['sigma']:.8f}, rows_fingerprint=\"{fp}\")")
    if bad:
        Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
        raise SystemExit(1)
    return out


# ---------------------------------------------------------------------------
# STAGE L -- lambda re-estimation (original procedure, prorated data)
# ---------------------------------------------------------------------------
def estimate_lambda(prorate, seeds=(0, 1, 2, 3, 4, 5), folds=5, min_gp=20):
    """5-fold PLAYER-SPLIT cross-validation (a goalie's seasons never
    straddle folds -- prevents the model 'remembering' a goalie across
    train/test). For each candidate lambda, predict each GP>=min_gp
    season's WAR from the trailing cascade shrunk toward LEAGUE_AVG, and
    score mean squared error on held-out players. Averaged over seeds."""
    lut, gplut = goalie_war_lut(prorate)
    # target seasons: every goalie-season with GP>=min_gp and a usable anchor
    pairs = []
    for (nk, yr) in lut.index:
        gp = gplut.get((nk, yr), 0)
        gp = 0 if isinstance(gp, pd.Series) else gp
        if gp < min_gp:
            continue
        tw, scheme = cascade(nk, yr, lut, prorate)
        if tw is None:
            continue
        pairs.append((nk, tw, float(lut.loc[(nk, yr)])))
    d = pd.DataFrame(pairs, columns=["nk", "trailing", "actual"])
    players = d["nk"].unique()
    grid = np.round(np.arange(0.0, 1.0001, 0.05), 2)
    scores = {l: [] for l in grid}
    for seed in seeds:
        rng = np.random.default_rng(seed)
        fold_of = {p: i % folds for i, p in
                   enumerate(rng.permutation(players))}
        d["fold"] = d["nk"].map(fold_of)
        for lam in grid:
            errs = []
            for f in range(folds):
                test = d[d["fold"] == f]
                pred = (1 - lam) * test["trailing"] + lam * LEAGUE_AVG
                errs.append(((pred - test["actual"]) ** 2).mean())
            scores[lam].append(np.mean(errs))
    mse = {l: float(np.mean(v)) for l, v in scores.items()}
    best = min(mse, key=mse.get)
    return best, mse, len(d), len(players)


def _log_carry_impact(v2):
    """REVIEW ITEM 1.1 -- audit trail. Reports exactly what the carry moved,
    measured against the locked file's placeholder on the same rows, so the
    change is documented in the run log rather than only in the artifact.
    Read-only: it does not alter v2."""
    log("\n  --- item 1.1: flat carry into out-years -----------------------")
    locked = pd.read_csv(F_LOCKED_SPINE)
    ph = locked[locked["weight_scheme"] == "future_season_static_placeholder"]
    log(f"  locked-file placeholder rows: {len(ph):,} "
        f"({ph['full_name'].nunique()} goaltenders)")

    carried = v2[v2["weight_scheme"].astype(str)
                 .str.startswith("flat_carry_out_year")]
    nohist = v2[v2["weight_scheme"] == "no_history_future_season"]
    log(f"    -> flat carry applied:      {len(carried):,} rows "
        f"({carried['full_name'].nunique()} goaltenders)")
    log(f"    -> never played, retag only:{len(nohist):,} rows "
        f"({nohist['full_name'].nunique()} goaltenders)")
    # 2026-10-14: a placeholder row may now be priced from the goaltender's own seasons because
    # war_name_crosswalk.py joined his contract to them (PuckPedia and Goalies_WAR spell him differently).
    # Each such row must belong to a crosswalk-matched goaltender; nothing else may leave the set.
    import contract_source as _CS
    key = lambda d: set(zip(d["contract_id"], d["season_start"]))          # noqa: E731
    gone = key(ph) - key(carried) - key(nohist)
    # 2026-10-19: a placeholder row may be a season that no longer exists: a bought-out deal's rows placed before it
    # started (contract_source.contract_terms). Each must be on such a deal, before its first season.
    sp_now = pd.read_csv(F_SEASON_SPINE, usecols=["contract_id", "pp_first_season", "pp_cut_short"])
    first_now = sp_now.drop_duplicates("contract_id").set_index("contract_id")
    misplaced = {k for k in gone - key(v2)}
    assert all(k[0] in first_now.index and int(first_now.at[k[0], "pp_cut_short"]) == 1
               and k[1] < int(first_now.at[k[0], "pp_first_season"]) for k in misplaced), \
        "a placeholder row left the spine that is not a bought-out deal's misplaced season"
    gone = gone - misplaced
    joined = v2[[k in gone for k in zip(v2["contract_id"], v2["season_start"])]]
    xw_names = set(_CS.war_name_map().values())
    assert len(joined) == len(gone) and joined["full_name"].isin(xw_names).all(), \
        "a placeholder row left the set without a crosswalk join"
    log(f"    -> now priced from his own seasons (name crosswalk): {len(joined):,} rows "
        f"({', '.join(sorted(joined['full_name'].unique()))})")
    log(f"    -> gone, seasons placed before a bought-out deal started (2026-10-19): {len(misplaced):,} rows")
    assert len(carried) + len(nohist) + len(joined) + len(misplaced) == len(ph), \
        "carried + retagged + crosswalk-joined + misplaced does not reconstruct the locked placeholder set"

    # Dollar movement on the carried rows. The locked value on these rows was
    # the placeholder value, so the difference IS the correction. Signed:
    # negative means the locked file was overvaluing (a below-average
    # goaltender was being priced as average).
    j = carried.merge(locked[["contract_id", "season_start", "value_dollars"]],
                      on=["contract_id", "season_start"],
                      suffixes=("", "_locked"))
    assert len(j) == len(carried), "carried rows did not all match the locked file"
    d = pd.to_numeric(j["value_dollars"]) - pd.to_numeric(j["value_dollars_locked"])
    log(f"  value change on carried rows: mean |diff| ${d.abs().mean():,.0f}/season, "
        f"max ${d.abs().max():,.0f}/season, net ${d.sum()/1e6:+.1f}M")
    per = (j.assign(diff=d)
             .groupby("full_name")
             .agg(rows=("diff", "size"), own_proj=("shrunk_projection", "first"),
                  mean_diff=("diff", "mean"))
             .sort_values("mean_diff", ascending=False))
    log("  largest upward corrections (locked file was UNDERvaluing):")
    for n, r in per.head(6).iterrows():
        log(f"    {n:<22} {int(r['rows'])} season(s)  own proj {r['own_proj']:.3f}  "
            f"{r['mean_diff']:+,.0f}/season")
    log("  largest downward corrections (locked file was OVERvaluing):")
    for n, r in per.tail(4).iloc[::-1].iterrows():
        log(f"    {n:<22} {int(r['rows'])} season(s)  own proj {r['own_proj']:.3f}  "
            f"{r['mean_diff']:+,.0f}/season")
    # Staleness: how far back did each carry reach? Flat carry has no decay,
    # so a multi-season reach is worth reporting rather than hiding.
    gap = (pd.to_numeric(carried["season_start"])
           - pd.to_numeric(carried["carry_source_season"]))
    log(f"  carry reach (seasons back): min {gap.min()}, median "
        f"{gap.median():.0f}, max {gap.max()}")
    log("  ---------------------------------------------------------------")


def stage_lambda_and_v2(rate_out):
    log("=" * 74)
    log("STAGE L: lambda re-estimation + goalie_value_spine_v2.csv")
    log("=" * 74)
    # v1.3: the raw procedure check against the locked 0.65 is retired
    for label, prorate in [("PRORATED", True)]:
        best, mse, n, npl = estimate_lambda(prorate)
        near = {l: round(mse[l], 6) for l in
                sorted(mse) if abs(l - best) <= 0.10}
        log(f"  {label:>9}: lambda* = {best:.2f}   "
            f"(n={n} season-targets, {npl} goalies)  MSE near optimum: {near}")
        if True:
            lam_new = best
            # v1.2: contract_npv applies LAMBDA_G = 0.65 to the same goaltenders, so a
            # search that leaves it would price one goalie two ways. Stop and say so: a
            # moved lambda is a decision for Thomas, not a side effect of the 62.5/37.5.
            if abs(lam_new - LAMBDA_LIVE) > 1e-9:
                log(f"    STOP: the prorated lambda search picked {lam_new:.2f}, not {LAMBDA_LIVE} "
                    "(contract_npv.LAMBDA_G). Nothing written; a decision for Thomas.")
                return None
    # v2.0: build_spine's own price is the retired least-squares line (alpha 0, beta 1 here only keep its columns
    # numeric); every priced row's value is replaced below by the valuation engine's forecast and locked line
    v2 = build_spine(lam_new, 0.0, 1.0, prorate=True,
                     carry_out_years=True)
    CN, GP, _nn = _projector()
    from skater_forward_projection import league_min_path
    if CN.GOALIE_RATE is None:
        log("  the goaltender line is not locked: the spine's values are left empty (lock Stage G, then run again)")
    cs = pd.read_csv(F_SEASON_SPINE)
    cs = cs[cs["position"] == "Goaltender"]
    end_of = cs.groupby("contract_id")["season_start"].max().to_dict()
    bd_of = pd.to_datetime(cs.drop_duplicates("player_id").set_index("player_id")["birthdate"], errors="coerce").to_dict()
    fw, vals, pcs = [], [], []
    for r in v2.itertuples():
        t0 = int(r.season_start)
        if t0 < 2015 or r.value_dollars in ("", None) or pd.isna(r.value_dollars):
            fw.append(np.nan); vals.append(r.value_dollars); pcs.append(r.predicted_cap_pct); continue
        b = bd_of.get(r.player_id)
        a0 = None if b is None or pd.isna(b) else t0 - b.year - ((9, 15) < (b.month, b.day))
        fc, src = GP.forecast(_nn(r.full_name), t0, 0, a0)
        if fc is None:
            fw.append(np.nan); vals.append(np.nan); pcs.append(np.nan); continue
        w0 = fc[0][1]
        term_left = int(end_of[r.contract_id]) - t0 + 1
        ceil = ceiling_for(t0)[0]
        pc = CN.goalie_line(w0, term_left) if CN.GOALIE_RATE is not None else np.nan
        fw.append(w0)
        vals.append(max(pc * ceil, league_min_path(t0)) if CN.GOALIE_RATE is not None else np.nan)
        pcs.append(pc)
    v2["forecast_war"], v2["value_dollars"], v2["predicted_cap_pct"] = fw, vals, pcs
    v2["surplus_dollars"] = pd.to_numeric(v2["value_dollars"], errors="coerce") - pd.to_numeric(v2["cost_dollars"], errors="coerce")
    _log_carry_impact(v2)
    v2.to_csv(OUT_SPINE_V2, index=False)
    priced = pd.to_numeric(v2["value_dollars"], errors="coerce").notna().sum()
    log(f"\n  goaltender constants: lambda={lam_new:.2f}; the price line is contract_npv.GOALIE_RATE "
        f"({rate_out['term-in']['n']} contracts, fingerprint {rate_out['term-in']['rows_fingerprint']})")
    log(f"  wrote {OUT_SPINE_V2.name}: {len(v2):,} rows ({priced:,} priced)")
    return lam_new


if __name__ == "__main__":
    stage_lambda_and_v2(stage_rate())     # v1.3: no parity gate, no raw guard
    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")
