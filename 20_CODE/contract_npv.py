"""
=============================================================================
 contract_npv.py   v2.1                             Phase 1d
                                  xNPV 1 prices skater contracts (2026-10-02)
=============================================================================
 WHAT CHANGED IN v2.1 (2026-10-05, plan of record step 6; MODEL_DIRECTIVES.md directive 4)
 ------------------------------------------------------------------------------------------
 The price line is TERM-IN (XNPV1_RATE re-locked on xnpv1_price_line.py v2.0: signing-dated
 forecasts, one linear term for years). A contract season is priced on the term REMAINING at the
 valuation date, the same for every remaining season; an RFA control year on one year. The
 term-free line (XNPV1_RATE_TERM_FREE) is priced beside every value as the sensitivity, and each
 contract season reports its term premium (gamma_term x remaining term x ceiling) in its own column.
 Each priced contract also carries npv_total_term_free (and its contract and terminal parts) and
 term_years; goalies (no term in their line) carry the same number in both.
 WHAT CHANGED IN v2.0 (2026-10-02): xNPV 0 ARCHIVED
 --------------------------------------------------
 Skaters are priced on xNPV 1 only. PV_k = (p_play_k x value_k - cap hit_k)
 / 1.03^k, k = 0 included, with value_k on xNPV 1's own price line. Removed
 with xNPV 0: the skater exit-hazard tables (h_sk_for, the per-page
 transitions), the Layer 1 identity check (check [1a] is xNPV 1's own) and
 the review-item-1.2 audit sweep (check [5]), which measured the old skater
 hazard index. Goalies are untouched: their exit hazard, its k-1 indexing
 and the goalie terminal value run exactly as before. The file as it stood
 is in git at 7f91f0e.
=============================================================================
 WHAT CHANGED IN v1.6 (the skater forecast is xNPV 1, decision D33)
 -------------------------------------------------------------------
 Under xNPV 1 (skater_forward_projection.SKATER_MODEL, the default) a skater
 contract season's survival is xNPV 1's chance he plays that season,
 including the valuation season itself, read directly rather than chained
 from the exit hazard: PV_k = (p_play_k x value_k - cap hit_k) / 1.03^k.
 value_k is priced on xNPV 1's WAR if he plays (see the projection's v1.5
 note). The exit hazard is not used for skaters under xNPV 1 (D18
 superseded for skaters by D33); it is still built, because the goalie
 branch uses its goalie table and "xNPV 0" still runs. Every summary and
 spine row records the model that built it. Goalies are unchanged.
 validate(): check [1a] (the valuation season equals Layer 1) holds by
 design for xNPV 0 only, so under xNPV 1 it checks instead that each
 priced valuation season carries xNPV 1's own forecast; check [5] (the
 hazard index audit) runs only under xNPV 0. xNPV 1's forecasts for every
 page priced are written to 30_OUTPUT/xnpv1_forecasts.csv.
=============================================================================
 WHAT CHANGED IN v1.5 (the skater exit hazard sees only earlier exits)
 ---------------------------------------------------------------------
 D18 REVISION, adopted by Thomas 2026-09-28. The skater survival factor used
 one exit-hazard table fitted on transitions 2018-2024, so a 2018 valuation
 read exits from 2019-2025. h_sk_for(t0) now fits one table per valuation
 page on transitions 2007 .. t0-2 (exit_hazard.pre_valuation_window), the
 same builder and guards as before, cached per page. Evidence:
 40_DOCS/model_evidence/Exit_Hazard_Window_Test.md (Brier -5.8%, season-WAR RMSE
 -0.32% on the forecast harness). NOT changed: the goalie table, the D14(c)
 control-year chain (which never used the hazard), the k-1 indexing (v1.2).
=============================================================================
 WHAT CHANGED IN v1.4 (signed extensions are part of the asset)
 ---------------------------------------------------------------
 npv(player_id, valuation_season, as_of=None). The valuation now covers
 the contract being played PLUS every extension signed on or before the
 as-of date (default July 1 of the valuation season, the date the page
 comes into force; any date up to the following June 30 is accepted).
 Extension seasons are contract seasons: survival x projected value minus
 the real cap hit, discounted. The RFA terminal value attaches to the end
 of that chain. The chain rule and the as-of window are defined once, in
 skater_forward_projection (contract_chain / check_as_of), and used by
 both the skater and the goalie branch here, so the two cannot disagree.
 Before v1.4 an already-extended player was valued as if his next years
 would be bought at the qualifying offer (Lane Hutson, any date after
 2025-10-13: $17.65M of RFA control value for years signed at $8.85M).
 Pages with no extension signed by the as-of date are unchanged.
=============================================================================
 WHAT CHANGED IN v1.2 (review item 1.2 -- the survival lookup was shifted
 one season forward on BOTH of its axes)
 -----------------------------------------------------------------------
 The exit-hazard table is built in exit_hazard.build_transitions(), which
 records, for each player-season t, the player's age and quality IN SEASON
 t, and then flags whether he has no NHL season at t+1. A cell therefore
 answers one question: given a player of this quality at this age NOW,
 what is the chance he is gone NEXT year.

 The survival factor this engine needs for season k is the probability of
 getting from season k-1 into season k. Both lookup indices must therefore
 be read at k-1. v1.1 read them at k:

     h = self._hazard(self.h_sk, r["projected_war"], age0 + k)

 which asked the odds of surviving from k into k+1 and then applied the
 answer to the k-1 -> k step. Two consequences:

   * AGE. Risk rises steeply with age, so every player was charged the
     risk of a season he had not yet reached. It bites only where a
     contract crosses an age-bracket boundary (23, 27, 31, 35); inside a
     bracket the effect is exactly zero. Measured: 692 of 2,909 contracts
     move, aggregate +$123.9M, largest single +$1.87M.
   * QUALITY. Not identified in the review, same root cause. The bucket
     boundaries (0, 1, 3 wins) carry order-of-magnitude hazard jumps
     (regular 27-30 = 0.7% against fringe 27-30 = 9.5%), so the shift
     bites harder than the age one where it bites. It also moves in the
     OPPOSITE direction for young players, whose projections rise, so
     their true k-1 quality is lower than v1.1 used. Measured: 527
     further contracts move, 193 up and 334 down.

 Fixing only one axis would leave the engine conditioning on age at one
 season and quality at another, which is neither of the two internally
 consistent choices, so both are corrected together.

 IDENTIFICATION NOTE (this is not a look-ahead relaxation)
 ---------------------------------------------------------
 The corrected lookup reads the projected state at k-1, which the engine
 has already computed from the valuation-season anchor. It introduces no
 new information and no realized outcome. If anything it is stricter: it
 stops the model from conditioning survival on a season that has not
 happened at the point the survival is being paid for.

 SEQUENCING, NOW RESOLVED (item 1.4 has landed -- read this before
 quoting any figure above)
 -----------------------------------------------------------------
 The figures above were measured against the RAW hazard table, which
 contained two cells reading exactly 0.0% (star aged 31-34 on n=40, star
 aged 22 and under on n=26). A material share of the downward movement ran
 through those cells rather than through anything the data supported.
 exit_hazard.py v1.2 (review item 1.4) replaced the cell means with a
 fitted additive model, so no cell asserts certainty any more.

 Re-measured on the corrected table, item 1.2 moves 925 of 2,909
 contracts (31.8%), 481 up and 444 down, aggregate +$143.0M -- against
 +$162.6M on the raw table. The $143.0M figure is the one that belongs in
 the write-up. Downward movers are now explained by the QUALITY axis
 rather than by the zero cells: young players' projections rise, so their
 true k-1 quality is lower than v1.1 used.

 The [5] block below recomputes this every run, so the number in the log
 is always measured against whatever table is currently in force.

 The run log carries a legacy-vs-corrected sweep ([5] below) so the
 movement is recorded in the artifact rather than only in a session.
=============================================================================
 WHAT THIS DOES (plain English)
 ------------------------------
 This is the module Phase 1 has been building toward: it takes everything
 that exists -- Layer 2's projected contract seasons, 1c's RFA terminal
 value, and 1a's discount structure -- and stacks them into ONE number per
 contract: the discounted net present value of the asset, as seen from a
 chosen valuation season. This is the number the back-test will compare
 across the two sides of every trade.

 THE FORMULA (D15-D18, all locked)
 ---------------------------------
   NPV = SUM over contract seasons k of:
             [ S_k x Value_k  -  Cost_k ] / (1 + g)^k
         + SUM over RFA control years j of:
             SurplusAdjusted_j / (1 + g)^(k_j)

   * Value_k / Cost_k  -- Layer 2's projected value (aging-curve decay,
     D10 floor, D11 ex-ante ceiling path) and the known cap hit.
   * S_k -- SURVIVAL: the compounded probability the player is still in
     the league to produce season k, from the exit-hazard table estimated
     in exit_hazard.py (quality x age, re-estimated from the panel every
     run). S_0 = 1: the current season is not discounted for exit.
     Survival multiplies VALUE ONLY (D16(i)): a player who exits stops
     producing, but his cap hit does not automatically vanish (injured
     and buried players still count against the cap). Retirement can
     void a cap hit -- treated as a documented simplification; keeping
     the cost unconditional errs conservative on NPV.
   * g = 3% (D17) -- the cap-growth discount, the SAME constant D11 uses
     to grow future ceilings. The two mesh: value holds constant in
     cap-share terms while a fixed cap hit gets relatively cheaper each
     year ("good contracts age well in a rising cap"), and dollars from
     different years become comparable in today's cap-share units.
   * Control years carry the D14(c) empirical qualify-rate survival chain
     INSTEAD of the exit hazard (locked split: the qualify gates were
     calibrated on real tender decisions, which already internalize
     player-departure at the decision point; applying both would count
     the same risk twice). They are g-discounted like everything else.

 GOALTENDERS (the position gets its own, simpler forward model)
 --------------------------------------------------------------
 No aging curve exists for goalies (locked earlier: age-conditioning was
 judged not worth it given weak signal + 64% birthdate coverage). The
 goalie projection from a valuation season is therefore:
   trailing WAR (locked 50/30/20 cascade over t-1/t-2/t-3, with the
   60/40 and t-1-only fallbacks) -> shrunk toward the league-average
   goalie (lambda = 0.65, target 2.19) -> HELD FLAT over the horizon.
 Holding flat is the natural zero-information extension: the shrinkage
 IS the mean-reversion device for goalies. [D19, flagged for the batch]
 Goalie value = (1.398% + 1.097% x shrunk WAR) x ceiling, D10-floored.
 Goalie exit hazard: estimated from Goalies_WAR.csv with the same shared
 builder (ages joined from the contract spine). Goalie RFA terminal value
 uses the same QO mechanics and D13 truncation but NOT the D14(c) gates
 -- those were calibrated on skater decisions and goalie WAR sits on a
 different scale, so borrowing the table would be sloppy. [flagged gap:
 goalie qualify-rate calibration, deferred -- goalie RFA TV is a small
 share of trade value]
 v2.1 (2026-10-05, open decision 1): the gap is closed with Thomas's July
 sub-decisions -- ONE pooled goalie weight a control year, P(qualified) x
 P(plays | qualified) at a one-game bar, measured from the goalie spine on
 every run (NPVEngine._calibrate_goalie_control), the chain starting from his
 survival into the contract's final season.

 WHAT THIS DOES NOT DO
 ---------------------
 * No behavioral/GM-impatience discounting (D15 -- that is a FINDING the
   back-test measures, never an input).
 * No draft picks or prospects (Phase 3 pillars).
 * No mid-season proration (Phase 4a-ii applies GV shares at trade dates).
=============================================================================
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

from skater_forward_projection import valuation_as_of, page_date
from skater_forward_projection import (SkaterProjector, cap_path,
                                       league_min_path, norm_name,
                                       CAP_GROWTH, CAP_CEILING,
                                       contract_chain, check_as_of)
from rfa_terminal_value import TerminalValuer, qualifying_offer
from exit_hazard import (build_transitions, build_hazard_table, bucket,
                         age_group, report_item_14)       # goalie hazard only (v2.0)

from dotenv import load_dotenv

load_dotenv()

SOURCE_DIR = Path(os.environ["SOURCE_DIR"])   # vendor inputs, read-only
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])   # generated spines / logs
F_GOALIE_WAR = SOURCE_DIR / "Goalies_WAR.csv"
# D20 (2026-07-05): constants self-calibrate from the PRORATED goalie
# spine. Run goalie_value_engine.py first -- it writes the v2 file after
# its parity gate + rate refit. Pointing at the old spine would silently
# price goalies at the pre-D20 rate.
F_GOALIE_SPINE = OUTPUT_DIR / "goalie_value_spine_v2.csv"
F_SEASON_SPINE = OUTPUT_DIR / "contract_season_spine.csv"
OUT_SPINE = OUTPUT_DIR / "contract_npv_spine.csv"
OUT_LOG = OUTPUT_DIR / "contract_npv_run_log.txt"
SCRIPT_VERSION = "2.1"   # printed first in the run log (25_TESTS/xnpv0_removal_check.py reads it)

# ---- locked goalie constants (P2 close-out, 2026-06-30) --------------------
# The documented narrative values (alpha 1.398% cap, beta 1.097%/WAR, league
# average 2.19) are ROUNDED. The spine was built at full precision, and a
# rounded re-implementation drifts ~$250/row -- so the engine recovers the
# exact constants FROM goalie_value_spine.csv at startup (self-calibrating;
# it can never diverge from the locked artifact by rounding again). The
# recovered values are asserted against the documented ones to 3 decimals,
# so a corrupted spine cannot silently smuggle in a different rate.
ALPHA_G = None           # recovered in _recover_goalie_constants()
BETA_G = None
GOALIE_LEAGUE_AVG = None
LAMBDA_G = 0.65          # weight on the LEAGUE AVERAGE (kept-trailing = 0.35;
                         # see the convention-correction note below)
G = CAP_GROWTH           # D17: one constant, two uses (D11 ceilings + here)

# ---- A1/A2/A3 stale-anchor constants (2026-07-29) -------------------------
# A goaltender with no t-1 season but a usable older one is a real player
# with a real, older anchor -- not a player with no history. Before this he
# fell through to no_history_unpriced, which is how Carey Price, Corey
# Crawford, Ben Bishop, Spencer Knight and Carter Hart were all recorded as
# never having played.
#
#   STALE_TARGET   conditional mean WAR of that population GIVEN he plays
#                  (0.650, n=29). GOALIE_LEAGUE_AVG is the mean of a
#                  population he is not in, so shrinking him toward it
#                  pushes his value UP, which is the wrong direction.
#
#   STALE_GATE     P(the season happens at all) = 29/93 = 0.312. This does
#                  most of the work, because the goalie rate carries a
#                  ~1.39%-of-cap intercept: ungated, a goaltender who never
#                  plays still books roughly $1.3M of modelled value.
#
#   STALE_MAXBACK  how far the carry search may reach. Matches
#                  goalie_value_engine.STALE_MAXBACK exactly. A goaltender
#                  four years absent is a different asset, not a stale one.
STALE_TARGET  = 0.650
STALE_GATE    = 0.312
STALE_MAXBACK = 3


def _recover_goalie_constants():
    """Back out the full-precision goalie rate and shrinkage target from
    the locked spine. All spine rows lie on one line, predicted_cap_pct =
    alpha + beta x shrunk_projection, so a first-degree fit recovers alpha
    and beta to machine precision; the rookie-fallback rows carry the raw
    shrinkage target as their shrunk_projection."""
    global ALPHA_G, BETA_G, GOALIE_LEAGUE_AVG
    gvs = pd.read_csv(F_GOALIE_SPINE)
    ok = gvs[gvs["shrunk_projection"].notna() & gvs["predicted_cap_pct"].notna()]
    beta, alpha = np.polyfit(ok["shrunk_projection"], ok["predicted_cap_pct"], 1)
    rook = gvs[gvs["weight_scheme"] == "no_observed_war_history"]
    target = float(rook["shrunk_projection"].mode().iloc[0])
    # guard: recovered values must round to the documented narrative ones
    assert abs(alpha - 0.01398) < 5e-4 and abs(beta - 0.01097) < 5e-4,         f"recovered goalie rate {alpha:.5f}/{beta:.5f} != documented 0.01398/0.01097"
    assert abs(target - 2.19) < 5e-3, f"recovered target {target:.4f} != ~2.19"
    ALPHA_G, BETA_G, GOALIE_LEAGUE_AVG = float(alpha), float(beta), target


_recover_goalie_constants()

LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))


class GoalieProjector:
    """The goalie-side mini engine: trailing 50/30/20 anchor -> lambda
    shrinkage -> flat projection. Mirrors the locked goalie wiring."""

    def __init__(self, spine):
        gw = pd.read_csv(F_GOALIE_WAR)
        gw["syr"] = gw["Season"].str.split("-").str[0].astype(int) + 2000
        # team-split rows collapse: one row per goalie-season, WAR summed
        gw = (gw.groupby(["Goalie", "syr"], as_index=False)
                .agg(WAR=("WAR", "sum"), GP=("GP", "sum")))
        # D20: schedule proration, same factors as every other anchor path
        try:
            from skater_value_engine import PRORATION as _PR
        except ImportError:
            _PR = {2019: 82 / 70, 2020: 82 / 56}
        gw["WAR"] = gw["WAR"] * gw["syr"].map(_PR).fillna(1.0)
        gw["nname"] = gw["Goalie"].map(norm_name)
        self.lut = gw.set_index(["nname", "syr"])["WAR"].sort_index()
        self.gp_lut = gw.set_index(["nname", "syr"])["GP"].sort_index()   # open decision 1
        self.spine = spine[spine["position"] == "Goaltender"].copy()

    def _get(self, nname, syr):
        v = self.lut.get((nname, syr), np.nan)
        return np.nan if isinstance(v, pd.Series) else v

    def shrunk_projection(self, nname, t0):
        """Locked cascade: 50/30/20 with three priors, 60/40 with two,
        t-1 alone with one (low-confidence). Then shrink toward the league
        average, KEEPING 35% of trailing (= shrinking 65% toward 2.19).

        CONVENTION CORRECTION (2026-07-05, for the doc batch): the locked
        lambda = 0.65 is the weight on the LEAGUE AVERAGE, not on trailing.
        Evidence: (a) goalie_value_spine.csv's stored shrunk_projection
        values back out kept = 0.35 exactly; (b) a head-to-head on 645
        goalie-seasons -- kept=0.35 predicts next-season WAR better (MAE
        2.084 vs 2.131); (c) reliability logic -- optimal kept-weight ~=
        the YoY persistence, and goalie r ~= 0.26-0.35. PROJECT_STATE's
        "lambda=0.65 kept, surprisingly close to the skater 0.55" wording
        has the label flipped; the true story is goalies keep 35% vs
        skaters' 55%, i.e. much harder shrinkage, as expected a priori.

        NO NHL history -> return NaN: a never-played goalie is prospect-
        pillar territory, exactly like a no-anchor skater. (The earlier
        league-average fallback priced AHL prospects as average NHL
        starters -- the sweep's top-8 was all unknown ELC goalies.)"""
        w1, w2, w3 = (self._get(nname, t0 - k) for k in (1, 2, 3))
        if pd.notna(w1) and pd.notna(w2) and pd.notna(w3):
            tr, src = 0.5 * w1 + 0.3 * w2 + 0.2 * w3, "503020"
        elif pd.notna(w1) and pd.notna(w2):
            tr, src = 0.6 * w1 + 0.4 * w2, "6040"
        elif pd.notna(w1):
            tr, src = w1, "t1_only"
        else:
            # A1 (2026-07-29). No t-1 season, so the locked cascade has nothing
            # to stand on. Rather than declaring no history, walk back to the
            # most recent season at which the SAME cascade could still reach a
            # real anchor, bounded at STALE_MAXBACK seasons. Mirrors
            # goalie_value_engine.carry_anchor() deliberately: both files
            # compute their own goalie anchor, and different rules would give
            # the same goaltender two different values.
            tr, src = np.nan, "no_history_unpriced"
            for s in range(t0 - 1, t0 - 1 - STALE_MAXBACK, -1):
                a1, a2, a3 = (self._get(nname, s - k) for k in (1, 2, 3))
                if pd.notna(a1) and pd.notna(a2) and pd.notna(a3):
                    tr = 0.5 * a1 + 0.3 * a2 + 0.2 * a3
                elif pd.notna(a1) and pd.notna(a2):
                    tr = 0.6 * a1 + 0.4 * a2
                elif pd.notna(a1):
                    tr = a1
                else:
                    continue          # nothing reachable at s, try one earlier
                src = "stale_anchor"
                break
            if pd.isna(tr):
                # Genuinely no reachable history within the bound. Unchanged
                # behaviour: prospect-pillar territory, not priced here.
                return np.nan, "no_history_unpriced"
        KEPT = 1 - LAMBDA_G          # = 0.35, see convention note above
        # A2 (2026-07-29): route the shrinkage target by population. A stale-
        # anchor goaltender shrinks toward the conditional mean of goaltenders
        # who came back, not toward the league average.
        target = STALE_TARGET if src == "stale_anchor" else GOALIE_LEAGUE_AVG
        return KEPT * tr + (1 - KEPT) * target, src


class NPVEngine:
    def __init__(self):
        # v1.2 goalie hazard index: False is the corrected, locked path (the
        # hazard read at k-1). Nothing sets it True since the audit sweep that
        # used it went with xNPV 0 (v2.0); it stays so the goalie path reads
        # exactly as before.
        self.legacy_hazard_index = False
        self.sp = SkaterProjector()
        self.tv = TerminalValuer(self.sp)

        # ---- goalie panel + hazard -----------------------------------------
        full = pd.read_csv(F_SEASON_SPINE)
        full["posgrp"] = "G"
        full["full_name"] = (full["first_name"].astype(str) + " "
                             + full["last_name"].astype(str))
        full["nname"] = full["full_name"].map(norm_name)
        full["cost"] = full["cs_cap_hit"].fillna(full["pp_cap_hit"])
        full["bd"] = pd.to_datetime(full["birthdate"], errors="coerce")
        self.gp_spine = full[full["position"] == "Goaltender"].copy()
        self.g_proj = GoalieProjector(full)

        # goalie transitions from the goalie panel; ages joined from the
        # spine birthdates (Goalies_WAR carries no age column)
        d_g = build_transitions(F_GOALIE_WAR, None, name_col="Goalie")
        bd_map = (self.gp_spine.drop_duplicates("nname")
                  .set_index("nname")["bd"].to_dict())
        def g_age(row):
            b = bd_map.get(norm_name(row["player"]))
            if pd.isna(b) or b is None:
                return None
            ref = pd.Timestamp(year=int(row["t"]) + 1, month=2, day=1)
            return int(ref.year - b.year
                       - ((ref.month, ref.day) < (b.month, b.day)))
        d_g["age"] = d_g.apply(g_age, axis=1)
        d_g["age_grp"] = d_g["age"].map(age_group)
        self.h_g = build_hazard_table(d_g)
        self._d_g = d_g                      # kept for the validation report
        self._calibrate_goalie_control()

    # ---- survival helpers ----------------------------------------------------
    def first_season_as_of(self, pid, t0):
        """OPEN DECISION 2, keyed on the contract npv() VALUES (chain[0], the
        contract with a row in t0, found as contract_chain finds it at 1 July),
        not on whichever contract a caller iterates over. A player with two
        contracts carrying rows in t0 gets ONE date for the player-season; v2.1
        keyed it on the caller's contract and gave the dashboard two values for
        one page (player 6054, 2019; dashboard guard, 2026-10-05). Returns that
        contract's signing date when t0 is its first season and it was signed
        after 1 July (skater_forward_projection.valuation_as_of), else None."""
        spine = self.sp.spine if (self.sp.spine["player_id"] == pid).any() else self.gp_spine
        chain = contract_chain(spine, pid, t0, self.sp.signed, page_date(t0))
        if not chain:
            return None
        first = spine.loc[spine["contract_id"] == chain[0], "season_start"].min()
        return valuation_as_of(chain[0], t0, self.sp.signed) if first == t0 else None

    def _calibrate_goalie_control(self):
        """OPEN DECISION 1, goalies (Thomas, 2026-10-05; his July sub-decisions):
        ONE pooled yearly weight, P(qualified) x P(plays | qualified), from every
        observable goalie qualify-or-walk decision (contracts ending 2018-2024,
        pp_expiry RFA = qualified or "UFA no QO" = walked), "plays" = one NHL
        game or more the next season. NHL REGULARS ONLY, for both numbers as in
        July (Thomas 2026-10-05: 10+ NHL games in one of the three seasons before
        the decision, the skater forecast's own rule): an AHL goaltender on an
        NHL contract was never in the league to leave it (the first v2.1 build
        kept him: 0.679 x 0.513 = 0.348 against July's 0.788). Until v2.1 goalie
        control years carried weight 1.0 (the gap the goalie TV comment recorded)."""
        last = (self.gp_spine.sort_values("season_start").groupby("contract_id").tail(1))
        elig = last[last["season_start"].between(2018, 2024)
                    & last["pp_expiry"].isin(["RFA", "UFA no QO"])]
        def _gp(n, syr):
            v = self.g_proj.gp_lut.get((n, int(syr)), 0.0)
            v = float(v.sum()) if isinstance(v, pd.Series) else float(v)   # merged-name rows: summed
            return v if np.isfinite(v) else 0.0
        # NHL regular at the decision: 10+ games (forecast_config.MIN_GP) in one of
        # the three seasons before it (the final contract season and the two before)
        import forecast_config as _FC
        reg = np.array([max(_gp(n, int(s) - j) for j in (0, 1, 2)) >= _FC.MIN_GP
                        for n, s in zip(elig["nname"], elig["season_start"])], dtype=bool)
        elig = elig[reg]
        q = (elig["pp_expiry"] == "RFA").to_numpy()
        gp = np.array([_gp(n, int(s) + 1) for n, s in zip(elig["nname"], elig["season_start"])], dtype=float)
        self.g_qualify_p = float(q.mean()) if len(q) else 1.0
        self.g_plays_given_q = float((gp[q] >= 1).mean()) if q.any() else 1.0
        self.g_control_n = (int(len(q)), int(q.sum()))
        self.g_control_weight = self.g_qualify_p * self.g_plays_given_q

    def _hazard(self, table, pw, age):
        """One-year exit probability for a projected quality + age. Falls
        back to the bucket marginal when age is unknown or the cell empty."""
        b = bucket(pw)
        g = age_group(age) if age is not None else "unknown"
        return table.get((b, g), table.get((b, "ALL"), 0.0))

    # ---- the main query -------------------------------------------------------
    def npv(self, player_id, valuation_season, as_of=None):
        """Full discounted NPV from `valuation_season`, over the contract
        being played plus every extension signed by `as_of` (v1.4; default
        July 1 of valuation_season). Returns (per-season detail DataFrame
        incl. terminal rows, summary dict)."""
        row = self.sp.spine[self.sp.spine["player_id"] == player_id]
        if not row.empty:
            return self._npv_skater(player_id, valuation_season, as_of)
        row = self.gp_spine[self.gp_spine["player_id"] == player_id]
        if not row.empty:
            return self._npv_goalie(player_id, valuation_season, as_of)
        return pd.DataFrame(), {"status": "unknown_player"}

    def _npv_skater(self, pid, t0, as_of=None):
        pr = self.sp.project_contract(pid, t0, as_of)
        if pr.empty:
            return pr, {"status": "unpriced_no_anchor"}
        det = []
        for _, r in pr.iterrows():
            k = int(r["k"])
            # xNPV 1's chance he plays season k, k = 0 included, read directly
            # (each season's own probability, not a chain of exits).
            S = float(r["p_play"])
            disc = (1 + G) ** (-k)
            pv = (S * r["value_dollars"] - r["cost_dollars"]) * disc
            # directive 4: the term-free sensitivity, same chance and discount
            pv_f = (S * r["value_dollars_term_free"] - r["cost_dollars"]) * disc
            det.append({**r, "row_type": "contract", "survival": S,
                        "discount": disc, "pv_dollars": pv, "pv_dollars_term_free": pv_f})
        npv_contract = sum(d["pv_dollars"] for d in det)
        npv_contract_f = sum(d["pv_dollars_term_free"] for d in det)

        tvd, tvs = self.tv.terminal_value(pid, t0, as_of)
        npv_tv, npv_tv_f = 0.0, 0.0
        if tvs.get("status") == "ok":
            end = int(pr["season_start"].max())
            for _, r in tvd.iterrows():
                k = (end - t0) + int(r["j"])
                disc = (1 + G) ** (-k)
                pv = r["surplus_adjusted"] * disc     # D14c chain, no h (locked)
                npv_tv += pv
                npv_tv_f += r["surplus_adjusted_term_free"] * disc
                det.append({"player_id": pid, "full_name": r["full_name"],
                            "contract_id": r["contract_id"],
                            "season_start": r["control_season"], "k": k,
                            "row_type": "terminal",
                            "projected_war": r["projected_war"],
                            "value_dollars": r["value_dollars"],
                            "cost_dollars": r["qo_cost"],
                            "surplus_dollars": r["surplus_adjusted"],
                            "survival": r["qualify_survival"],
                            "discount": disc, "pv_dollars": pv,
                            "pv_dollars_term_free": r["surplus_adjusted_term_free"] * disc})
        d = pd.DataFrame(det)
        return d, {"status": "ok", "position": "skater",
                   # v1.4: the information date and the contracts valued
                   "as_of": pr.iloc[0]["as_of"],
                   "chain": [int(c) for c in dict.fromkeys(pr["contract_id"])],
                   "full_name": pr.iloc[0]["full_name"],
                   "path": pr.iloc[0]["path"],
                   "model": self.sp.model,
                   "n_contract_seasons": len(pr),
                   "npv_contract": npv_contract, "npv_terminal": npv_tv,
                   "npv_total": npv_contract + npv_tv,
                   # directive 4: term-in is the headline; term-free beside it
                   "term_years": int(pr["term_years"].iloc[0]),
                   "npv_contract_term_free": npv_contract_f,
                   "npv_terminal_term_free": npv_tv_f,
                   "npv_total_term_free": npv_contract_f + npv_tv_f,
                   "surplus_no_survival":
                       float(pr["surplus_dollars"].sum())
                       + tvs.get("tv_adjusted", 0.0)}

    def _npv_goalie(self, pid, t0, as_of=None):
        # v1.4: the same contract chain as the skater branch -- the contract
        # being played plus every extension signed by `as_of`.
        as_of = check_as_of(t0, as_of)
        chain = contract_chain(self.gp_spine, pid, t0, self.sp.signed, as_of)
        if not chain:
            return pd.DataFrame(), {"status": "no_contract"}
        cid = chain[0]
        crows = (self.gp_spine[self.gp_spine["contract_id"].isin(chain)]
                 .sort_values("season_start"))
        crows = crows[crows["season_start"] >= t0]
        # GUARD: k is the row position, so one row per consecutive season
        ss = crows["season_start"].to_numpy()
        assert len(ss) and ss[0] == t0 and (np.diff(ss) == 1).all(), (
            f"goalie {pid} t0={t0}: contract chain {chain} does not give one "
            f"row per consecutive season: {list(ss)}")
        # the contract whose expiry decides the terminal value: the chain end
        lrows = crows[crows["contract_id"] == chain[-1]]
        nname = crows.iloc[0]["nname"]
        pw, src = self.g_proj.shrunk_projection(nname, t0)
        if pd.isna(pw):
            return pd.DataFrame(), {"status": "unpriced_no_history"}
        bd = crows.iloc[0]["bd"]
        age0 = (None if pd.isna(bd) else
                int(pd.Timestamp(year=t0 + 1, month=2, day=1).year - bd.year
                    - ((2, 1) < (bd.month, bd.day))))

        # A3 (2026-07-29): seed S with the materialisation gate for stale-
        # anchor goaltenders, 1.0 for everyone else (unchanged behaviour).
        # Seeding rather than applying at k=0 means the gate carries forward:
        # of stale-anchor rows where the goaltender did not play at k=0, only
        # 5 of 54 appeared at k=1, so the state is near-absorbing. Slightly
        # conservative, and named as such.
        det = []
        S = STALE_GATE if src == "stale_anchor" else 1.0
        for k, (_, r) in enumerate(crows.iterrows()):
            season = int(r["season_start"])
            if k > 0:
                # REVIEW ITEM 1.2, goalie side. Same off-by-one, same table
                # semantics. Age only: the goalie projection is held flat by
                # design, so pw is already the k-1 quality.
                h = self._hazard(self.h_g, pw,
                                 None if age0 is None else
                                 age0 + (k if self.legacy_hazard_index
                                         else k - 1))
                S *= (1.0 - h)
            ceil = cap_path(t0, k)
            val = max((ALPHA_G + BETA_G * pw) * ceil,
                      league_min_path(season))          # D10 floor
            disc = (1 + G) ** (-k)
            pv = (S * val - r["cost"]) * disc
            det.append({"player_id": pid, "full_name": r["full_name"],
                        "contract_id": int(r["contract_id"]),
                        "season_start": season, "k": k,
                        "row_type": "contract", "projected_war": pw,
                        "value_dollars": val, "cost_dollars": r["cost"],
                        "surplus_dollars": val - r["cost"],
                        "survival": S, "discount": disc, "pv_dollars": pv})
        npv_contract = sum(d["pv_dollars"] for d in det)

        # ---- goalie RFA terminal value: same QO mechanics, D13 truncation,
        # ---- flat projection; v2.1: a pooled control-year weight (open decision 1) ---
        npv_tv = 0.0
        end = int(crows["season_start"].max())
        # v1.4: expiry, UFA year and the 2020+ proxy from the chain's END.
        # With no extension lrows is exactly the old t0-filtered crows.
        expiry = lrows.iloc[0]["pp_expiry"]
        ufa_year = lrows.iloc[0]["ufa_year"]
        if expiry == "RFA" and pd.notna(ufa_year):
            final = crows[crows["season_start"] == end].iloc[0]
            sal = (float(final["cs_nhl_salary"])
                   if pd.notna(final["cs_nhl_salary"])
                   else float(final["pp_aav"]))
            cap_hit = float(final["cost"])
            s20 = int(lrows["season_start"].min()) >= 2020
            truncated = False
            # open decision 1: start from his survival into the final contract
            # season, then the pooled weight compounds each control year
            S_tv = S
            for j, season in enumerate(range(end + 1, int(ufa_year)), 1):
                k = (end - t0) + j
                ceil = cap_path(t0, k)
                val = max((ALPHA_G + BETA_G * pw) * ceil,
                          league_min_path(season))
                qo = qualifying_offer(sal, cap_hit, season, s20)
                surplus = val - qo
                if surplus < 0:
                    truncated = True                    # D13
                if truncated:
                    break
                S_tv *= self.g_control_weight
                disc = (1 + G) ** (-k)
                npv_tv += S_tv * surplus * disc
                det.append({"player_id": pid, "full_name": final["full_name"],
                            "contract_id": chain[-1], "season_start": season,
                            "k": k, "row_type": "terminal",
                            "projected_war": pw, "value_dollars": val,
                            "cost_dollars": qo, "surplus_dollars": surplus,
                            "survival": S_tv, "discount": disc,
                            "pv_dollars": S_tv * surplus * disc})
                sal, cap_hit = qo, qo
        d = pd.DataFrame(det)
        return d, {"status": "ok", "position": "goalie",
                   "as_of": as_of.date().isoformat(), "chain": list(chain),
                   "full_name": crows.iloc[0]["full_name"],
                   "path": f"goalie_flat_{src}",
                   "model": "goalie branch (unchanged)",
                   "n_contract_seasons": len(crows),
                   "npv_contract": npv_contract, "npv_terminal": npv_tv,
                   "npv_total": npv_contract + npv_tv,
                   # directive 4 is the skater price line; the goalie line has
                   # no term, so its term-free value is the same number
                   "term_years": len(crows),
                   "npv_contract_term_free": npv_contract, "npv_terminal_term_free": npv_tv,
                   "npv_total_term_free": npv_contract + npv_tv,
                   "surplus_no_survival":
                       float(sum(x["surplus_dollars"] for x in det))}


# ---------------------------------------------------------------------------
# VALIDATION BATTERY
# ---------------------------------------------------------------------------
def _check_xnpv1_valuation_season(eng, l1):
    """[1a] under xNPV 1 (v1.6). The valuation season is a forecast, not the
    observed Layer 1 season, so the Layer 1 identity does not apply. What must
    hold instead, on the same 200 sampled player-seasons: every priced
    valuation season carries xNPV 1's own forecast for that player and page
    (WAR if he plays, chance of playing), the chance of playing is inside
    (0, 1), and the value is the floored price of that WAR."""
    from skater_forecast import war_if_plays_sd
    checked, worst = 0, 0.0
    for _, r in l1.sample(200, random_state=11).iterrows():
        d, s = eng.npv(int(r["player_id"]), int(r["season_start"]))
        if s.get("status") != "ok":
            continue
        r0 = d[(d["k"] == 0) & (d["row_type"] == "contract")]
        if r0.empty:
            continue
        r0 = r0.iloc[0]
        fc = eng.sp.forecaster.forecast(eng.sp.spine.loc[eng.sp.spine["player_id"] == r["player_id"], "nk"].iloc[0],
                                        int(r["season_start"]), 0)
        assert fc is not None, "a priced skater has no xNPV 1 forecast"
        worst = max(worst, abs(float(fc.iloc[0]["war_if_plays"]) - float(r0["projected_war"])),
                    abs(float(fc.iloc[0]["p_play"]) - float(r0["survival"])))
        assert 0.0 < float(r0["survival"]) < 1.0, "a chance of playing outside (0, 1)"
        assert abs(float(r0["proj_sd_war"]) - war_if_plays_sd(0)) < 1e-12, "valuation-season spread"
        checked += 1
    log(f"\n[1a] skater valuation season under xNPV 1: {checked} sampled rows carry xNPV 1's own")
    log(f"     forecast (largest gap {worst:.1e})")
    assert checked >= 50 and worst < 1e-12, "valuation seasons do not carry xNPV 1's forecast"


def validate():
    eng = NPVEngine()
    log("=" * 74)
    log("PHASE 1d VALIDATION BATTERY")
    log(f"contract_npv.py v{SCRIPT_VERSION}")
    log("=" * 74)

    log(f"  skater model: {eng.sp.model}")
    # ---- 1. k=0 consistency, both positions ---------------------------------
    l1 = pd.read_csv(OUTPUT_DIR / "skater_value_spine.csv")
    l1 = l1[l1["trailing_war"].notna() & l1["season_start"].between(2018, 2025)]
    _check_xnpv1_valuation_season(eng, l1)

    gv = pd.read_csv(F_GOALIE_SPINE)
    gv = gv[gv["season_start"].between(2018, 2025)
            & gv["value_dollars"].notna()]
    gdiffs, gchecked = [], 0
    for _, r in gv.iterrows():
        d, s = eng.npv(int(r["player_id"]), int(r["season_start"]))
        if s.get("status") != "ok":
            continue
        r0 = d[(d["k"] == 0) & (d["row_type"] == "contract")]
        if r0.empty or r0.iloc[0]["contract_id"] != r["contract_id"]:
            continue
        gchecked += 1
        gdiffs.append(abs(r0.iloc[0]["value_dollars"] - r["value_dollars"]))
    log(f"[1b] goalie k=0 value vs goalie spine: {gchecked} rows, "
        f"max diff ${max(gdiffs):,.2f}")
    big = [x for x in gdiffs if x > 1.0]
    log(f"     rows beyond $1: {len(big)} -- each one must be a JOIN RECOVERY "
        f"(this engine's name normalizer finds an NHL history the spine's "
        f"weaker join missed, e.g. Zachary->Zach Sawchenko); anything else "
        f"is a real inconsistency.")
    assert len(big) <= max(2, int(0.03 * gchecked)), \
        "goalie consistency: too many rows diverge from the spine"

    # ---- 2. goalie hazard table ----------------------------------------------
    dg = eng._d_g
    log(f"\n[1c] goalie control-year weight (open decision 1): {eng.g_control_n[0]} decisions, "
        f"{eng.g_control_n[1]} qualified (NHL regulars at the decision); P(qualified) {eng.g_qualify_p:.3f} x P(plays | qualified) "
        f"{eng.g_plays_given_q:.3f} = {eng.g_control_weight:.3f} a year (July 2026 test: 0.909 x "
        f"0.867 = 0.788, n 99)")
    log(f"\n[2] goalie exit hazard (GP>=10 goalie-seasons, t=2018-2024, "
        f"n={len(dg):,}):")
    log(f"    overall: {dg['exited'].mean()*100:.2f}%/yr   "
        f"age known: {(dg['age_grp'] != 'unknown').mean()*100:.0f}%")
    for gr in ["<=22", "23-26", "27-30", "31-34", "35+"]:
        s = dg[dg["age_grp"] == gr]
        if len(s):
            log(f"    {gr:6s} {s['exited'].mean()*100:5.2f}%   (n={len(s):,})")

    # REVIEW ITEM 1.4. The goalie table is the thinner of the two -- 502
    # transitions across 20 cells, three of which held no departures -- so its
    # raw-versus-fitted audit belongs in THIS log, where the goalie panel is
    # built. The skater equivalent prints in exit_hazard.py's own run log.
    for _ln in report_item_14(dg, "GOALIES"):
        log(_ln)

    # ---- 3. full NPV sweep: every contract from its first 2018+ season ------
    log("\n[3] full sweep: NPV of every contract from its first season in "
        "2018-2025...")
    spine_all = pd.concat([eng.sp.spine, eng.gp_spine])
    firsts = (spine_all.sort_values("season_start")
              .groupby("contract_id").head(1))
    firsts = firsts[firsts["season_start"].between(2018, 2025)]
    def _sweep(engine):
        """One full pass over every contract's first 2018-2025 season."""
        out = []
        for _, r in firsts.iterrows():
            # open decision 2: a contract signed after 1 July of its first
            # season is valued at its signing (valuation_as_of)
            aod = engine.first_season_as_of(int(r["player_id"]), int(r["season_start"]))
            d, s = engine.npv(int(r["player_id"]), int(r["season_start"]), aod)
            if s.get("status") != "ok":
                continue
            out.append({"contract_id": r["contract_id"],
                        "player_id": r["player_id"], "model": s.get("model"),
                        "full_name": s["full_name"], "position": s["position"],
                        "valuation_season": int(r["season_start"]),
                        "as_of_date": s.get("as_of"),
                        "n_seasons": s["n_contract_seasons"],
                        "path": s["path"],
                        "npv_contract": s["npv_contract"],
                        "npv_terminal": s["npv_terminal"],
                        "npv_total": s["npv_total"],
                        "npv_total_term_free": s["npv_total_term_free"],
                        "term_years": s["term_years"],
                        "surplus_no_survival": s["surplus_no_survival"]})
        return pd.DataFrame(out)

    assert eng.legacy_hazard_index is False, \
        "the priced sweep must run on the corrected goalie hazard index"
    dfo = _sweep(eng)
    dfo.to_csv(OUT_SPINE, index=False)
    log(f"    priced: {len(dfo):,} contracts "
        f"({(dfo['position']=='skater').sum():,} skater, "
        f"{(dfo['position']=='goalie').sum():,} goalie)")
    log(f"    NPV distribution ($M): "
        f"p10 {dfo['npv_total'].quantile(.1)/1e6:+.2f}  "
        f"median {dfo['npv_total'].median()/1e6:+.2f}  "
        f"p90 {dfo['npv_total'].quantile(.9)/1e6:+.2f}")
    log(f"    discounting bite: median (undiscounted - NPV) = "
        f"${(dfo['surplus_no_survival']-dfo['npv_total']).median()/1e6:.2f}M")

    log("\n    top 8 ASSET BUNDLES by NPV -- contract + remaining RFA control")
    log("    years (D14c). Cheap control years, not famous extensions, are")
    log("    where surplus lives, so expect young RFA-controlled players here:")
    for _, r in dfo.nlargest(8, "npv_total").iterrows():
        log(f"      {r['full_name']:24s} {r['valuation_season']}  "
            f"{r['n_seasons']}yr  NPV ${r['npv_total']/1e6:+7.2f}M "
            f"(contract {r['npv_contract']/1e6:+.2f} / "
            f"terminal {r['npv_terminal']/1e6:+.2f})")
    log("\n    bottom 5 (should read like famous albatrosses):")
    for _, r in dfo.nsmallest(5, "npv_total").iterrows():
        log(f"      {r['full_name']:24s} {r['valuation_season']}  "
            f"{r['n_seasons']}yr  NPV ${r['npv_total']/1e6:+7.2f}M")

    # ---- 4. decomposition demo ------------------------------------------------
    log("\n[4] decomposition demo -- Michkov 2025 (contract + terminal):")
    pid = int(eng.sp.spine[eng.sp.spine["full_name"] == "Matvei Michkov"]
              .iloc[0]["player_id"])
    d, s = eng.npv(pid, 2025)
    for _, r in d.iterrows():
        log(f"      {r['row_type']:8s} {int(r['season_start'])}  k={int(r['k'])}  "
            f"WAR {r['projected_war']:+.2f}  S={r['survival']:.3f}  "
            f"disc={r['discount']:.3f}  pv ${r['pv_dollars']/1e6:+6.2f}M")
    log(f"      NPV total ${s['npv_total']/1e6:+.2f}M  "
        f"(contract {s['npv_contract']/1e6:+.2f} + "
        f"terminal {s['npv_terminal']/1e6:+.2f}; "
        f"undiscounted {s['surplus_no_survival']/1e6:+.2f})")

    p = eng.sp.forecaster.write(OUTPUT_DIR / "xnpv1_forecasts.csv")
    log(f"\n    xNPV 1 forecasts used by this run written: {p}")
    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")
    log(f"NPV spine written: {OUT_SPINE}")

if __name__ == "__main__":
    validate()
