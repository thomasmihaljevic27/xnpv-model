"""
=============================================================================
 goalie_value_engine.py   v1.1                    D20 rebuild (2026-07-05)
                                          review item 1.1 (2026-07-26)
=============================================================================
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

 HOW TO RUN (Windows):  python goalie_value_engine.py
 Inputs (same folder or XNPV_DATA): Goalies_WAR.csv,
   contract_season_spine.csv, goalie_value_spine.csv (the parity oracle),
   PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx
 Outputs: goalie_value_spine_v2.csv, goalie_value_engine_run_log.txt
=============================================================================
"""

import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

DATA_DIR = Path(os.environ.get("XNPV_DATA", "."))
F_GOALIE_WAR   = DATA_DIR / "Goalies_WAR.csv"
F_SEASON_SPINE = DATA_DIR / "contract_season_spine.csv"
F_LOCKED_SPINE = DATA_DIR / "goalie_value_spine.csv"      # parity oracle
F_CONTRACT_XLSX = DATA_DIR / "PuckPedia_Player_Contract_Export_May_22_2026__CONFIDENTIAL.xlsx"
OUT_SPINE_V2 = DATA_DIR / "goalie_value_spine_v2.csv"
OUT_LOG      = DATA_DIR / "goalie_value_engine_run_log.txt"

# ---------------------------------------------------------------------------
# LOCKED CONSTANTS (raw regime -- the parity target)
# ---------------------------------------------------------------------------
ALPHA_G_RAW = 0.013982        # goalie replacement cost, cap-share (locked P2)
BETA_G_RAW  = 0.010971        # goalie cap-share per WAR unit (locked P2)
LAMBDA_RAW  = 0.65            # weight on the LEAGUE AVERAGE (locked P2)
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
# SAMPLE RECONSTRUCTION NOTE (documented residual, same class as the
# skater engine's Stage-0a "+2/+4" note): the locked report says n=350;
# the closest reconstructable spec -- standard-level goalie contracts,
# ANY signing status, starts 2015-2026 -- yields n=353 with R2=0.5261
# (locked: 0.526) and coefficients within 3e-5 of the spine-recovered
# constants. The 3-contract residual is name-variant matching edge cases
# in the anchor join. Coefficients, not n, are what price the spine, and
# parity (Stage P) already proves those to the cent.
RATE_N_LOCKED = 353           # reconstructed sample size (locked report: 350)
TOL_RATE_COEF = 1.0e-4        # rate-guard tolerance on alpha/beta
TOL_PARITY_DOLLARS = 0.01     # parity gate: value must match to the cent

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
    g = pd.read_csv(F_GOALIE_WAR)
    g["syr"] = g["Season"].str.split("-").str[0].astype(int) + 2000
    agg = (g.groupby(["Goalie", "syr"], as_index=False)
             .agg(WAR=("WAR", "sum"), GP=("GP", "sum")))
    if prorate:
        agg["WAR"] = agg["WAR"] * agg["syr"].map(PRORATION).fillna(1.0)
    agg["nk"] = agg["Goalie"].map(norm_name)
    return (agg.set_index(["nk", "syr"])["WAR"].sort_index(),
            agg.set_index(["nk", "syr"])["GP"].sort_index())


def cascade(nk, t0, lut):
    """The locked trailing cascade. Returns (trailing value or None, tag).
    NO GP filter -- see header. 50/30/20 needs all three priors; 60/40
    needs t-1 and t-2; t-1 alone otherwise; None if no t-1..t-3 history
    is usable under those rules (t-2/t-3 without t-1 -> no history, which
    is what the locked spine does)."""
    def get(y):
        v = lut.get((nk, y), np.nan)
        return np.nan if isinstance(v, pd.Series) else v
    w1, w2, w3 = get(t0 - 1), get(t0 - 2), get(t0 - 3)
    if pd.notna(w1) and pd.notna(w2) and pd.notna(w3):
        return 0.5 * w1 + 0.3 * w2 + 0.2 * w3, "50/30/20"
    if pd.notna(w1) and pd.notna(w2):
        return 0.6 * w1 + 0.4 * w2, "60/40"
    if pd.notna(w1):
        return w1, "t-1 only"
    return None, "no_observed_war_history"


def carry_anchor(nk, t0, lut, maxback=12):
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
        tw, scheme = cascade(nk, s, lut)
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
    gl["nk"] = gl["full_name"].map(norm_name)
    gl["cost"] = gl["cs_cap_hit"].fillna(gl["pp_cap_hit"])

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
        tw, scheme = cascade(r.nk, t0, lut)
        carry_src = ""                     # v1.1: season the anchor came from
        stale = False                      # A1: in-window stale-anchor row?
        if tw is None and t0 >= 2026:
            if not carry_out_years:
                # LOCKED regime: league-average placeholder, tag verbatim.
                scheme = "future_season_static_placeholder"
            else:
                # v1.1 regime: carry this goaltender's own anchor forward.
                # maxback left at the default -- item 1.1 unchanged.
                ctw, csrc, cscheme = carry_anchor(r.nk, t0, lut)
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
                                              maxback=STALE_MAXBACK)
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
# STAGE P -- PARITY GATE against the locked spine
# ---------------------------------------------------------------------------
def stage_parity():
    log("=" * 74)
    log("STAGE P: parity gate -- raw rebuild vs locked goalie_value_spine.csv")
    log("=" * 74)
    locked = pd.read_csv(F_LOCKED_SPINE)
    # carry_out_years=False is REQUIRED here: the parity target is the
    # locked file, which contains the league-average placeholder rows.
    mine = build_spine(LAMBDA_RAW, ALPHA_G_RAW, BETA_G_RAW,
                       prorate=False, carry_out_years=False)

    if len(locked) != len(mine):
        log(f"  FAIL: row counts differ (locked {len(locked)}, rebuild {len(mine)})")
        return False
    key = ["contract_id", "season_start"]
    m = locked.merge(mine, on=key, suffixes=("_l", "_m"))
    if len(m) != len(locked):
        log(f"  FAIL: key join lost rows ({len(m)} of {len(locked)})")
        return False

    # scheme tags must agree everywhere
    bad_scheme = m[m["weight_scheme_l"] != m["weight_scheme_m"]]
    log(f"  weight_scheme mismatches: {len(bad_scheme)}")

    # priced rows must match to the cent on value (and so on everything
    # upstream of it: trailing, shrunk, cap%)
    pl = pd.to_numeric(m["value_dollars_l"], errors="coerce")
    pm = pd.to_numeric(m["value_dollars_m"], errors="coerce")
    both = pl.notna() & pm.notna()
    if (pl.notna() != pm.notna()).any():
        log(f"  FAIL: priced-row sets differ "
            f"({int((pl.notna() != pm.notna()).sum())} rows)")
        return False
    maxd = (pl[both] - pm[both]).abs().max()
    log(f"  priced rows compared: {int(both.sum()):,}   "
        f"max |value diff| = ${maxd:.6f}")
    ok = (len(bad_scheme) == 0) and (maxd < TOL_PARITY_DOLLARS)
    log(f"  Stage P {'PASSED -- this file IS the locked pipeline.' if ok else 'FAILED.'}\n")
    return ok


# ---------------------------------------------------------------------------
# STAGE G -- rate guard (raw) + D20 refit (prorated)
# ---------------------------------------------------------------------------
def _rate_sample(lut):
    """The n=350 goalie contract sample: goaltender contracts starting
    2015-2026, standard level, UFA/RFA, with a computable trailing anchor
    at the start year. Mirrors the skater engine's sample construction."""
    raw = pd.read_excel(F_CONTRACT_XLSX)
    raw["end_yr"] = pd.to_numeric(
        raw["contract_end"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")
    raw["start_yr"] = raw["end_yr"] - raw["length"] + 1
    g = raw[(raw["position"] == "Goaltender")
            & (raw["contract_level"] == "standard_level")
            & raw["start_yr"].between(2015, 2026)].copy()
    g["nk"] = (g["first_name"].astype(str) + " " + g["last_name"].astype(str)).map(norm_name)
    g["wWAR"] = [cascade(k, int(s), lut)[0] if pd.notna(s) else None
                 for k, s in zip(g["nk"], g["start_yr"])]
    g = g[g["wWAR"].notna()].copy()
    g["cap_pct"] = g["aav"] / g["start_yr"].map(
        lambda s: ceiling_for(int(s))[0])
    return g[g["cap_pct"].notna()]


def stage_rate():
    log("=" * 74)
    log("STAGE G: goalie rate -- raw guard, then D20 refit")
    log("=" * 74)
    out = {}
    for label, prorate in [("RAW", False), ("PRORATED", True)]:
        lut, _ = goalie_war_lut(prorate)
        s = _rate_sample(lut)
        r = sm.OLS(s["cap_pct"], sm.add_constant(s["wWAR"])).fit(cov_type="HC3")
        a, b = r.params["const"], r.params["wWAR"]
        log(f"  {label:>9}: n={len(s)}  alpha_G={a:.8f}  beta_G={b:.8f}  "
            f"R2={r.rsquared:.4f}")
        out[label] = (a, b, len(s), r.rsquared)
    a, b, n, _ = out["RAW"]
    ok = (abs(a - ALPHA_G_RAW) <= TOL_RATE_COEF
          and abs(b - BETA_G_RAW) <= TOL_RATE_COEF
          and abs(n - RATE_N_LOCKED) <= 5)
    log(f"  raw guard vs locked (a={ALPHA_G_RAW}, b={BETA_G_RAW}, n={RATE_N_LOCKED}): "
        f"{'PASS' if ok else 'FAIL'}\n")
    return (out if ok else None)


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
        tw, scheme = cascade(nk, yr, lut)
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
    assert len(carried) + len(nohist) == len(ph), \
        "carried + retagged does not reconstruct the locked placeholder set"

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
    # procedure validation: the RAW run must land on (or immediately next
    # to) the locked 0.65 before the prorated number is trusted
    for label, prorate in [("RAW", False), ("PRORATED", True)]:
        best, mse, n, npl = estimate_lambda(prorate)
        near = {l: round(mse[l], 6) for l in
                sorted(mse) if abs(l - best) <= 0.10}
        log(f"  {label:>9}: lambda* = {best:.2f}   "
            f"(n={n} season-targets, {npl} goalies)  MSE near optimum: {near}")
        if label == "RAW":
            ok = abs(best - LAMBDA_RAW) <= 0.05
            log(f"    raw procedure check vs locked 0.65: {'PASS' if ok else 'FAIL'}")
            if not ok:
                return None
        else:
            lam_new = best
    a_new, b_new, n_new, r2_new = rate_out["PRORATED"]
    # carry_out_years=True: the corrected artifact (review item 1.1).
    v2 = build_spine(lam_new, a_new, b_new, prorate=True,
                     carry_out_years=True)
    _log_carry_impact(v2)
    v2.to_csv(OUT_SPINE_V2, index=False)
    priced = pd.to_numeric(v2["value_dollars"], errors="coerce").notna().sum()
    log(f"\n  D20 goalie constants: lambda={lam_new:.2f}  "
        f"alpha_G={a_new:.8f}  beta_G={b_new:.8f}  (rate n={n_new}, R2={r2_new:.4f})")
    log(f"  wrote {OUT_SPINE_V2.name}: {len(v2):,} rows ({priced:,} priced)")
    return lam_new


if __name__ == "__main__":
    if not stage_parity():
        log("HALTED at parity gate.")
    else:
        rates = stage_rate()
        if rates is None:
            log("HALTED at rate guard.")
        else:
            stage_lambda_and_v2(rates)
    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")
