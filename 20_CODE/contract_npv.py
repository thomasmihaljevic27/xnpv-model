"""
=============================================================================
 contract_npv.py   v1.3                             Phase 1d
                                     review items 1.2, 1.4 (2026-07-26)
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

from skater_forward_projection import (SkaterProjector, cap_path,
                                       league_min_path, norm_name,
                                       ALPHA, BETA, CAP_GROWTH, CAP_CEILING)
from rfa_terminal_value import TerminalValuer, qualifying_offer
from exit_hazard import (build_transitions, build_hazard_table, bucket,
                         age_group, report_item_14)

DATA_DIR = Path(os.environ.get("XNPV_DATA", "."))
F_GOALIE_WAR = DATA_DIR / "Goalies_WAR.csv"
# D20 (2026-07-05): constants self-calibrate from the PRORATED goalie
# spine. Run goalie_value_engine.py first -- it writes the v2 file after
# its parity gate + rate refit. Pointing at the old spine would silently
# price goalies at the pre-D20 rate.
F_GOALIE_SPINE = DATA_DIR / "goalie_value_spine_v2.csv"
F_SEASON_SPINE = DATA_DIR / "contract_season_spine.csv"
OUT_SPINE = DATA_DIR / "contract_npv_spine.csv"
OUT_LOG = DATA_DIR / "contract_npv_run_log.txt"

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
        # v1.2 audit switch. False is the corrected, locked pricing path
        # (hazard indices read at k-1). True reproduces the v1.1 shifted
        # lookup and is used ONLY by validate()'s [5] comparison sweep, so
        # the size of the correction is recorded in the run log. Nothing in
        # the pricing path ever sets it True.
        self.legacy_hazard_index = False
        self.sp = SkaterProjector()
        self.tv = TerminalValuer(self.sp)

        # ---- skater exit-hazard table (shared builder, same numbers as ----
        # ---- the standalone exit_hazard.py report) -------------------------
        d_sk = build_transitions(DATA_DIR / "WAR.csv",
                                 DATA_DIR / "WAR_with_age.csv")
        self.h_sk = build_hazard_table(d_sk)

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

    # ---- survival helpers ----------------------------------------------------
    def _hazard(self, table, pw, age):
        """One-year exit probability for a projected quality + age. Falls
        back to the bucket marginal when age is unknown or the cell empty."""
        b = bucket(pw)
        g = age_group(age) if age is not None else "unknown"
        return table.get((b, g), table.get((b, "ALL"), 0.0))

    # ---- the main query -------------------------------------------------------
    def npv(self, player_id, valuation_season):
        """Full discounted contract NPV from `valuation_season`. Returns
        (per-season detail DataFrame incl. terminal rows, summary dict)."""
        row = self.sp.spine[self.sp.spine["player_id"] == player_id]
        if not row.empty:
            return self._npv_skater(player_id, valuation_season)
        row = self.gp_spine[self.gp_spine["player_id"] == player_id]
        if not row.empty:
            return self._npv_goalie(player_id, valuation_season)
        return pd.DataFrame(), {"status": "unknown_player"}

    def _npv_skater(self, pid, t0):
        pr = self.sp.project_contract(pid, t0)
        if pr.empty:
            return pr, {"status": "unpriced_no_anchor"}
        age0 = pr.iloc[0]["age_at_valuation"]
        det, S = [], 1.0
        prev_war = None                  # v1.2: quality in season k-1
        for _, r in pr.iterrows():
            k = int(r["k"])
            if k > 0:      # S_0 = 1: current season carries no exit discount
                # REVIEW ITEM 1.2. The hazard cell is defined on the state in
                # the season the player is LEAVING, so both indices read k-1.
                # legacy_hazard_index reproduces the v1.1 (shifted) lookup and
                # exists only for the audit sweep in validate() -- it is never
                # the pricing path.
                assert prev_war is not None, \
                    "k>0 reached with no k-1 projection -- projection rows " \
                    "are out of order, the hazard index would be undefined"
                h_age = (None if age0 is None else
                         age0 + (k if self.legacy_hazard_index else k - 1))
                h_war = (r["projected_war"] if self.legacy_hazard_index
                         else prev_war)
                h = self._hazard(self.h_sk, h_war, h_age)
                S *= (1.0 - h)
            prev_war = r["projected_war"]
            disc = (1 + G) ** (-k)
            pv = (S * r["value_dollars"] - r["cost_dollars"]) * disc
            det.append({**r, "row_type": "contract", "survival": S,
                        "discount": disc, "pv_dollars": pv})
        npv_contract = sum(d["pv_dollars"] for d in det)

        tvd, tvs = self.tv.terminal_value(pid, t0)
        npv_tv = 0.0
        if tvs.get("status") == "ok":
            end = int(pr["season_start"].max())
            for _, r in tvd.iterrows():
                k = (end - t0) + int(r["j"])
                disc = (1 + G) ** (-k)
                pv = r["surplus_adjusted"] * disc     # D14c chain, no h (locked)
                npv_tv += pv
                det.append({"player_id": pid, "full_name": r["full_name"],
                            "contract_id": r["contract_id"],
                            "season_start": r["control_season"], "k": k,
                            "row_type": "terminal",
                            "projected_war": r["projected_war"],
                            "value_dollars": r["value_dollars"],
                            "cost_dollars": r["qo_cost"],
                            "surplus_dollars": r["surplus_adjusted"],
                            "survival": r["qualify_survival"],
                            "discount": disc, "pv_dollars": pv})
        d = pd.DataFrame(det)
        return d, {"status": "ok", "position": "skater",
                   "full_name": pr.iloc[0]["full_name"],
                   "path": pr.iloc[0]["path"],
                   "n_contract_seasons": len(pr),
                   "npv_contract": npv_contract, "npv_terminal": npv_tv,
                   "npv_total": npv_contract + npv_tv,
                   "surplus_no_survival":
                       float(pr["surplus_dollars"].sum())
                       + tvs.get("tv_adjusted", 0.0)}

    def _npv_goalie(self, pid, t0):
        rows = self.gp_spine[(self.gp_spine["player_id"] == pid)
                             & (self.gp_spine["season_start"] >= t0)]
        active = rows[rows["season_start"] == t0]
        if active.empty:
            return pd.DataFrame(), {"status": "no_contract"}
        cid = active.iloc[0]["contract_id"]
        crows = (self.gp_spine[self.gp_spine["contract_id"] == cid]
                 .sort_values("season_start"))
        crows = crows[crows["season_start"] >= t0]
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
                        "contract_id": cid, "season_start": season, "k": k,
                        "row_type": "contract", "projected_war": pw,
                        "value_dollars": val, "cost_dollars": r["cost"],
                        "surplus_dollars": val - r["cost"],
                        "survival": S, "discount": disc, "pv_dollars": pv})
        npv_contract = sum(d["pv_dollars"] for d in det)

        # ---- goalie RFA terminal value: same QO mechanics, D13 truncation,
        # ---- flat projection, NO D14c gates (flagged gap, see docstring) ---
        npv_tv = 0.0
        end = int(crows["season_start"].max())
        expiry = crows.iloc[0]["pp_expiry"]
        ufa_year = crows.iloc[0]["ufa_year"]
        if expiry == "RFA" and pd.notna(ufa_year):
            final = crows[crows["season_start"] == end].iloc[0]
            sal = (float(final["cs_nhl_salary"])
                   if pd.notna(final["cs_nhl_salary"])
                   else float(final["pp_aav"]))
            cap_hit = float(final["cost"])
            s20 = int(crows["season_start"].min()) >= 2020
            truncated = False
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
                disc = (1 + G) ** (-k)
                npv_tv += surplus * disc
                det.append({"player_id": pid, "full_name": final["full_name"],
                            "contract_id": cid, "season_start": season,
                            "k": k, "row_type": "terminal",
                            "projected_war": pw, "value_dollars": val,
                            "cost_dollars": qo, "surplus_dollars": surplus,
                            "survival": 1.0, "discount": disc,
                            "pv_dollars": surplus * disc})
                sal, cap_hit = qo, qo
        d = pd.DataFrame(det)
        return d, {"status": "ok", "position": "goalie",
                   "full_name": crows.iloc[0]["full_name"],
                   "path": f"goalie_flat_{src}",
                   "n_contract_seasons": len(crows),
                   "npv_contract": npv_contract, "npv_terminal": npv_tv,
                   "npv_total": npv_contract + npv_tv,
                   "surplus_no_survival":
                       float(sum(x["surplus_dollars"] for x in det))}


# ---------------------------------------------------------------------------
# VALIDATION BATTERY
# ---------------------------------------------------------------------------
def validate():
    eng = NPVEngine()
    log("=" * 74)
    log("PHASE 1d VALIDATION BATTERY")
    log("=" * 74)

    # ---- 1. k=0 consistency, both positions ---------------------------------
    l1 = pd.read_csv(DATA_DIR / "skater_value_spine.csv")
    l1 = l1[l1["trailing_war"].notna() & l1["season_start"].between(2018, 2025)]
    diffs, checked, worst = [], 0, None
    for _, r in l1.sample(200, random_state=11).iterrows():
        d, s = eng.npv(int(r["player_id"]), int(r["season_start"]))
        if s.get("status") != "ok":
            continue
        r0 = d[(d["k"] == 0) & (d["row_type"] == "contract")]
        if r0.empty or r0.iloc[0]["contract_id"] != r["contract_id"]:
            continue
        checked += 1
        diff = abs(r0.iloc[0]["value_dollars"] - r["value_dollars"])
        diffs.append(diff)
        if worst is None or diff > worst[0]:
            worst = (diff, r, r0.iloc[0])
    log(f"\n[1a] skater k=0 value vs Layer 1: {checked} rows, "
        f"max diff ${max(diffs):,.2f}")
    if max(diffs) >= 1.0:
        wd, wr, wr0 = worst
        log("    !! MISMATCH DETAIL (diagnose before trusting anything downstream) !!")
        log(f"    player: {wr['full_name']}   season: {int(wr['season_start'])}   "
            f"contract_id: {wr['contract_id']}")
        log(f"    Layer 1 spine  -- trailing_war={wr['trailing_war']:.4f}  "
            f"war_source={wr['war_source']}  value=${wr['value_dollars']:,.2f}")
        log(f"    NPV engine     -- anchor={wr0['anchor_war']:.4f}  "
            f"anchor_source={wr0['anchor_source']}  value=${wr0['value_dollars']:,.2f}")
        log("    If trailing_war != anchor: the two files disagree on this")
        log("    player's trailing WAR -- almost always a stale/mismatched copy")
        log("    of skater_value_spine.csv, WAR.csv, or contract_season_spine.csv.")
        log("    Re-run age_join.py -> skater_value_engine.py -> contract_npv.py")
        log("    fresh, all reading the SAME current data files.")
    assert max(diffs) < 1.0, "k=0 must reproduce Layer 1 exactly"

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
        """One full pass over every contract's first 2018-2025 season.
        Factored out in v1.2 so the same sweep can be run under the legacy
        hazard index for the [5] comparison, with no risk of the two paths
        drifting apart."""
        out = []
        for _, r in firsts.iterrows():
            d, s = engine.npv(int(r["player_id"]), int(r["season_start"]))
            if s.get("status") != "ok":
                continue
            out.append({"contract_id": r["contract_id"],
                        "player_id": r["player_id"],
                        "full_name": s["full_name"], "position": s["position"],
                        "valuation_season": int(r["season_start"]),
                        "n_seasons": s["n_contract_seasons"],
                        "path": s["path"],
                        "npv_contract": s["npv_contract"],
                        "npv_terminal": s["npv_terminal"],
                        "npv_total": s["npv_total"],
                        "surplus_no_survival": s["surplus_no_survival"]})
        return pd.DataFrame(out)

    assert eng.legacy_hazard_index is False, \
        "the priced sweep must run on the corrected hazard index"
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

    # ---- 5. review item 1.2: how much did the index correction move? --------
    # Re-runs the identical sweep with the v1.1 shifted lookup and diffs it.
    # This is an audit, not a pricing path: the spine on disk is the corrected
    # run above, and the flag is reset before anything else can read it.
    log("\n[5] review item 1.2 -- survival lookup indexed at k-1 (both axes).")
    log("    Comparison against the v1.1 shifted lookup. The corrected run is")
    log("    what was written to disk; this is the size of the correction.")
    eng.legacy_hazard_index = True
    try:
        dlg = _sweep(eng)
    finally:
        eng.legacy_hazard_index = False
    assert eng.legacy_hazard_index is False, "audit flag left set"

    j = dfo.merge(dlg, on=["contract_id", "valuation_season"],
                  suffixes=("_fix", "_lg"))
    assert len(j) == len(dfo) == len(dlg), \
        "the two sweeps priced different contract sets -- not comparable"
    d = j["npv_total_fix"] - j["npv_total_lg"]
    moved = d.abs() > 1_000            # $1k: below this is float noise
    # NEGATIVE TEST: a one-season contract has no k>0 row, so no hazard is
    # ever applied to it. If any single-season contract moves, the patch is
    # touching something it should not.
    assert (j.loc[moved, "n_seasons_fix"] > 1).all(), \
        "a single-season contract moved -- the hazard patch has side effects"
    log(f"    contracts moved: {int(moved.sum()):,} of {len(j):,} "
        f"({100*moved.mean():.1f}%)   {int((d > 1_000).sum()):,} up / "
        f"{int((d < -1_000).sum()):,} down")
    log(f"    on moved contracts: mean ${d[moved].mean()/1e6:+.3f}M   "
        f"median ${d[moved].median()/1e6:+.3f}M   "
        f"range ${d[moved].min()/1e6:+.2f}M to ${d[moved].max()/1e6:+.2f}M")
    log(f"    aggregate NPV shift: ${d.sum()/1e6:+.1f}M")
    for pos in ["skater", "goalie"]:
        mp = moved & (j["position_fix"] == pos)
        if mp.any():
            log(f"      {pos:7s}: {int(mp.sum()):,} moved, "
                f"net ${d[mp].sum()/1e6:+.1f}M")
    jj = j.assign(d=d).sort_values("d", ascending=False)
    log("    largest upward (v1.1 was overstating exit risk):")
    for _, r in jj.head(5).iterrows():
        log(f"      {r['full_name_fix']:24s} {int(r['valuation_season'])} "
            f"{int(r['n_seasons_fix'])}yr  ${r['npv_total_lg']/1e6:+7.2f}M -> "
            f"${r['npv_total_fix']/1e6:+7.2f}M  ({r['d']/1e6:+.2f}M)")
    log("    largest downward -- young players on long deals, whose true")
    log("    k-1 quality is lower than the shifted lookup used:")
    for _, r in jj.tail(4).iloc[::-1].iterrows():
        log(f"      {r['full_name_fix']:24s} {int(r['valuation_season'])} "
            f"{int(r['n_seasons_fix'])}yr  ${r['npv_total_lg']/1e6:+7.2f}M -> "
            f"${r['npv_total_fix']/1e6:+7.2f}M  ({r['d']/1e6:+.2f}M)")

    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")
    log(f"NPV spine written: {OUT_SPINE}")


if __name__ == "__main__":
    validate()
