"""
=============================================================================
 rfa_terminal_value.py   v1.2                       Phase 1c

 v1.2 (2026-07-28) rebuilt from the verified 2026-07-06 Drive copy, with:
   * a position-split price adapter (Stage 3) that detects what the
     projection module exports and fails loudly if it recognises neither
     shape,
   * item 1.10, the qualifying-offer salary fallback, as option 3: prefer a
     real salary anywhere on the contract, tag and report the substitute,
   * the Stage 4 retention-calibration fix: a player with no recent NHL
     games is treated as below replacement rather than dropped from the
     sample, with the pre-fix table computed alongside for comparison.
 NOT VERIFIED against the local post-review copy. Run it and compare.
=============================================================================
 WHAT THIS DOES (plain English)
 ------------------------------
 When a contract ends, the asset doesn't always end with it. If the player
 exits into UNRESTRICTED free agency, the team keeps nothing -- terminal
 value is zero (locked). But if he exits into RESTRICTED free agency, the
 team still owns his negotiating rights for every season until he reaches
 UFA eligibility. Those "control years" have real value: the team can
 retain the player by extending a QUALIFYING OFFER (QO) -- a CBA-formula
 one-year offer -- which is typically far below what his production is
 worth on the open market. This module prices that.

 THE LOCKED METHODOLOGY (from Resolved Decisions, coded here for the
 first time): re-run the player model over the expected RFA-control years
 at projected qualifying-offer cost, using the WAR-only rate (which under
 D7 is simply THE locked skater rate -- one market, no length terms, so
 the original reason for insisting on WAR-only, that remaining control
 years are not "expected contract length", is honored automatically).

 HOW A TERMINAL VALUE IS BUILT
 -----------------------------
 For a contract valued from season t0 (same standpoint as Layer 2):
   1. Contract end + expiry status from the spine. UFA or "UFA no QO"
      (team already declined to qualify) -> terminal value = 0. Done.
   2. RFA -> control seasons run from (end + 1) to (ufa_year - 1).
   3. VALUE side: the Layer 2 projection simply keeps walking -- same
      trailing anchor at t0, same aging-curve decay path (D3), same
      replacement-reversion for negative anchors (D12 v3), same ex-ante
      cap path (D11), same league-minimum floor (D10). A control year is
      just another future season of the same player.
   4. COST side: the CBA qualifying-offer formula, iterated year over
      year (each QO is a one-year deal; the next QO escalates off it),
      floored at the league minimum. Era-aware bands -- see QO RULES.
   5. D13 (flagged for the end-of-session batch): control is a RIGHT,
      not an obligation. The team qualifies while the player is worth
      it and walks away when he isn't -- and once they walk away, the
      remaining control years vanish (you cannot skip a year and
      re-qualify later). So the terminal value TRUNCATES at the first
      control year whose projected surplus goes negative. The untruncated
      raw sum is also reported so the choice is visible in the output.

 QO RULES (verified against PuckPedia / CBA summaries, 2026-07-05)
 -----------------------------------------------------------------
 QOs are computed on BASE SALARY (excluding signing bonuses), one year:
   Offseasons through summer 2026 (the 2013/2020 CBA):
     salary <= $660K            -> 110%
     $660K < salary < $1.0M     -> 105%, capped at $1.0M
     salary >= $1.0M            -> 100%
     PLUS, for contracts signed after July 2020: the QO cannot exceed
     120% of the contract's CAP HIT (anti-front-loading rule). Signing
     date is not in the spine, so "contract starts 2020+" is the proxy
     (documented approximation; the rule only ever binds on heavily
     front-loaded deals, which are rare among RFA-expiring contracts).
   Offseasons from summer 2026 (the 2026 CBA):
     salary <= $1.25M           -> 110%
     $1.25M < salary < $1.75M   -> 105%, capped at $1.75M
     salary >= $1.75M           -> min(100% of salary, 120% of cap hit)
   Every QO is floored at that season's league minimum.
 EX-ANTE CAVEAT (same class as the league-min schedule note in D11): the
 2026 bands were unknown before Sept 2025, so early-dated valuations
 technically could not have known them. Third-order -- the band change
 moves QOs of sub-$1.75M players by <= 10% -- documented, not modeled.

 DATA NOTES
 ----------
 * Final-year base salary: cs_nhl_salary where the clause pipeline matched
   the season (66% of RFA-expiring contracts), else pp_aav as a documented
   fallback (aav ~= salary for non-front-loaded deals; source flagged).
 * 6 contracts (of 1,973) carry pp_expiry = RFA but zero computed control
   years (ufa_year inconsistency) -- terminal value 0, flagged in output.
=============================================================================
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

import skater_forward_projection as _sfp
from skater_forward_projection import (SkaterProjector, cap_path,
                                       league_min_path)

# ---------------------------------------------------------------------------
# PRICE-RATE ADAPTER  (added 2026-07-28)
# ---------------------------------------------------------------------------
# Stage 3 of the model review replaced the single price line with a
# POSITION-SPLIT one. In words: a player is worth a base amount plus an
# amount per win, and the amount per win is larger for a defenceman than for
# a forward. The 2026-07-06 file this was rebuilt from predates that and
# imports one ALPHA and one BETA, which cannot express a position split.
#
# This adapter reads whatever the projection module actually exports and
# adapts to it, rather than assuming a name. If it finds a position-split
# rate it uses it. If it finds only the old single rate it uses that and
# says so out loud. If it finds neither it stops the script, because
# guessing here would silently misprice every defenceman in the file.
def _resolve_rate():
    a = getattr(_sfp, "ALPHA", None)
    if a is None:
        raise ImportError("skater_forward_projection exports no ALPHA.")

    # PREFERRED. The projection module defines its own slope function. Using
    # it means there is ONE definition of the rate in the project rather than
    # a copy here that can drift out of step the next time the rate is refit.
    fn = getattr(_sfp, "skater_slope", None)
    if callable(fn):
        return (float(a), float(fn("F")), float(fn("D")),
                "split (skater_slope helper)")

    # FALLBACK. Named constants, in the naming actually used by this project:
    # BETA is the forward slope and BETA_D the defence slope. The pair is
    # asymmetric, so it is listed explicitly rather than guessed at.
    for fwd, dfn in (("BETA", "BETA_D"), ("BETA_F", "BETA_D"),
                     ("BETA_FWD", "BETA_DEF")):
        bf, bd = getattr(_sfp, fwd, None), getattr(_sfp, dfn, None)
        if bf is not None and bd is not None:
            return float(a), float(bf), float(bd), f"split ({fwd}/{dfn})"

    # LAST RESORT. One slope for both positions. This is the pre-Stage-3
    # shape and it underprices defencemen, so it warns loudly.
    b = getattr(_sfp, "BETA", None)
    if b is not None:
        return float(a), float(b), float(b), "single (BETA, pre-Stage-3)"
    raise ImportError(
        "Could not find a usable price rate in skater_forward_projection. "
        "Send me the rate constants from that file and I will wire them in."
    )


ALPHA, BETA_F, BETA_D, _RATE_MODE = _resolve_rate()


def price(projected_war, posgrp, ceiling):
    """Value of one season, in dollars, before the league-minimum floor.

    posgrp is 'F' or 'D'. Under the single-rate fallback both slopes are the
    same, so that path reproduces the old behaviour exactly.
    """
    beta = BETA_D if str(posgrp).upper().startswith("D") else BETA_F
    return (ALPHA + beta * projected_war) * ceiling

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])   # generated logs land here
OUT_LOG = OUTPUT_DIR / "rfa_terminal_value_run_log.txt"

LOG = []
def log(msg=""):
    print(msg)
    LOG.append(str(msg))


log(f"[rate] price line in force: {_RATE_MODE}")
log(f"[rate]   alpha={ALPHA:.8f}  beta_F={BETA_F:.8f}  beta_D={BETA_D:.8f}")
if _RATE_MODE.startswith("single"):
    log("[rate]   WARNING: this is the PRE-Stage-3 single-slope rate. "
        "Defencemen are being priced on the forward slope.")


# ---------------------------------------------------------------------------
# QUALIFYING-OFFER MECHANICS (era-aware)
# ---------------------------------------------------------------------------
def qualifying_offer(prior_salary, prior_cap_hit, offseason_year,
                     signed_2020_plus):
    """The CBA QO formula for a single offseason. `offseason_year` is the
    calendar summer (= season_start of the season the QO covers).
    Returns the QO salary (= its cap hit; QOs are one-year deals)."""
    if offseason_year >= 2026:                     # 2026 CBA bands
        if prior_salary <= 1_250_000:
            qo = prior_salary * 1.10
        elif prior_salary < 1_750_000:
            qo = min(prior_salary * 1.05, 1_750_000)
        else:
            qo = min(prior_salary, 1.20 * prior_cap_hit)
    else:                                          # 2013/2020 CBA bands
        if prior_salary <= 660_000:
            qo = prior_salary * 1.10
        elif prior_salary < 1_000_000:
            qo = min(prior_salary * 1.05, 1_000_000)
        else:
            qo = prior_salary
            if signed_2020_plus:                   # 120%-of-cap-hit rule
                qo = min(qo, 1.20 * prior_cap_hit)
    return max(qo, league_min_path(offseason_year))


def _qo_self_test():
    """Mechanics asserts -- run on import so a band typo can never ship."""
    # old bands
    assert abs(qualifying_offer(600_000, 600_000, 2022, False) - 750_000) < 1  # 110% -> 660K, floored to 2022 min 750K
    assert abs(qualifying_offer(900_000, 900_000, 2022, False) - 945_000) < 1  # 105%
    assert abs(qualifying_offer(980_000, 980_000, 2022, False) - 1_000_000) < 1  # 105% capped at 1M
    assert abs(qualifying_offer(4_000_000, 4_000_000, 2022, False) - 4_000_000) < 1  # 100%
    # 120% rule: front-loaded deal, final salary 6M on a 4M AAV, signed 2020+
    assert abs(qualifying_offer(6_000_000, 4_000_000, 2022, True) - 4_800_000) < 1
    # new bands
    assert abs(qualifying_offer(1_200_000, 1_200_000, 2027, True) - 1_320_000) < 1  # 110%
    assert abs(qualifying_offer(1_700_000, 1_700_000, 2027, True) - 1_750_000) < 1  # 105% capped
    assert abs(qualifying_offer(5_000_000, 5_000_000, 2027, True) - 5_000_000) < 1  # 100%
    # league-min floor
    assert qualifying_offer(500_000, 500_000, 2024, False) == 775_000
_qo_self_test()


# ---------------------------------------------------------------------------
# TERMINAL VALUE
# ---------------------------------------------------------------------------
def final_year_salary(crows, final):
    """Base salary used to start the qualifying-offer chain (item 1.10).

    THE PROBLEM, IN PLAIN ENGLISH. A qualifying offer is capped at 120% of
    the contract's cap hit, and that cap only bites when the final-year
    SALARY sits well above the cap hit. Average annual value is, by
    definition, the number that erases that gap. So substituting the average
    when a real salary is missing switches the cap off exactly where it was
    meant to apply.

    THE FIX (Stage 1 item 1.10, option 3). Prefer the real final-year
    salary. Failing that, use the highest real salary recorded anywhere on
    the same contract, which is strictly better than the average and costs
    nothing. Only if the contract carries no real salary at all do we fall
    back to the average, and that case is now TAGGED rather than silent.

    Why it is a limitation and not a repair: of the contracts with no
    final-year salary, only 11 have a salary on any season. The feed covers
    a whole contract or none of it, so there is nothing else to recover.
    """
    if pd.notna(final["cs_nhl_salary"]):
        return float(final["cs_nhl_salary"]), "cs_nhl_salary"
    real = crows["cs_nhl_salary"].dropna()
    if len(real):
        return float(real.max()), "max_contract_salary"
    return float(final["pp_aav"]), "pp_aav_fallback"


def _anchor_bucket(w):
    """Talent buckets used for the D14(c) qualify-rate calibration."""
    if w < 0:   return "negative"
    if w < 1:   return "fringe"
    if w < 3:   return "regular"
    return "star"


class TerminalValuer:
    def __init__(self, projector=None):
        self.sp = projector or SkaterProjector()
        self._calibrate_qualify_rates()

    def _calibrate_qualify_rates(self):
        """D14(c), locked 2026-07-05. The intercept convention makes nearly
        every control year look worth qualifying (predicts only 18% of real
        walk-aways), while a net-of-replacement frame over-corrects (wrongly
        zeroes 44% of players teams kept). Resolution: neither theoretical
        extreme -- use REALITY. From every observable qualify-or-walk
        decision in the spine (contracts ending 2018-2024 with pp_expiry of
        RFA = qualified or 'UFA no QO' = walked), estimate P(qualified) by
        talent bucket, and weight each projected control year by the
        compounded survival of those gates. Fully data-driven: the table is
        re-estimated from the spine on every run, no hardcoded rates."""
        sp = self.sp
        last = (sp.spine.sort_values("season_start")
                .groupby("contract_id").tail(1))
        elig = last[last["season_start"].between(2018, 2024)
                    & last["pp_expiry"].isin(["RFA", "UFA no QO"])]
        # ---- STAGE 4 FIX (2026-07-28) -----------------------------------
        # THE BUG, IN PLAIN ENGLISH. Sorting a player into a talent bucket
        # needs a production figure. A player with no recent NHL games has
        # none, so the original code SKIPPED him. But a player who could not
        # hold an NHL job is exactly the player a club walks away from, so
        # the sample was fitted with the departures removed. That made the
        # reasoning circular: exit risk was switched off because these
        # retention rates were supposed to cover departure, and the rates
        # were then fitted without the departures in them.
        #
        # THE FIX. A missing production figure is INFORMATIVE, not missing.
        # It means below replacement. Those players now enter the negative
        # bucket rather than vanishing.
        #
        # Expected effect, from the review: overall walk-away rate moves
        # from 21.3% (n=1,231) to 27.0% (n=2,270), and the star, regular and
        # fringe rates DO NOT MOVE. That last part is the check that the fix
        # landed where it was supposed to. Both tables are computed below so
        # the comparison is visible in the run log instead of asserted.
        tab, tab_old = {}, {}
        for _, r in elig.iterrows():
            a, _ = sp.anchor(r["nk"], int(r["season_start"]) + 1)
            q = 1 if r["pp_expiry"] == "RFA" else 0
            if pd.isna(a):
                b = "negative"                     # no NHL games -> below replacement
            else:
                b = _anchor_bucket(a)
                tab_old.setdefault(b, []).append(q)   # the pre-fix sample
            tab.setdefault(b, []).append(q)
        self.qualify_p = {b: float(np.mean(v)) for b, v in tab.items()}
        self.qualify_n = {b: len(v) for b, v in tab.items()}
        self.qualify_p_prefix = {b: float(np.mean(v)) for b, v in tab_old.items()}
        self.qualify_n_prefix = {b: len(v) for b, v in tab_old.items()}
        # structural guards: the fix must ADD decisions and must not disturb
        # the three buckets that were already being measured correctly.
        assert sum(self.qualify_n.values()) >= sum(self.qualify_n_prefix.values()), \
            "Stage 4 fix removed decisions; it should only add them"
        for b in ("star", "regular", "fringe"):
            if b in self.qualify_p and b in self.qualify_p_prefix:
                assert abs(self.qualify_p[b] - self.qualify_p_prefix[b]) < 1e-9, \
                    f"Stage 4 fix moved the {b} bucket, which it must not"

    def terminal_value(self, player_id, valuation_season):
        """RFA terminal value for the contract active at `valuation_season`,
        from that season's standpoint (same information set as Layer 2).
        Returns (per-control-year DataFrame, summary dict)."""
        sp = self.sp
        rows = sp.spine[(sp.spine["player_id"] == player_id)
                        & (sp.spine["season_start"] >= valuation_season)]
        active = rows[rows["season_start"] == valuation_season]
        empty = pd.DataFrame()
        if active.empty:
            return empty, {"status": "no_contract"}
        cid = active.iloc[0]["contract_id"]
        crows = (sp.spine[sp.spine["contract_id"] == cid]
                 .sort_values("season_start"))
        end = int(crows["season_start"].max())
        expiry = crows.iloc[0]["pp_expiry"]
        ufa_year = crows.iloc[0]["ufa_year"]

        # --- locked rule: UFA expiry (incl. team-declined "no QO") -> zero --
        if expiry != "RFA":
            return empty, {"status": "ufa_expiry", "tv_raw": 0.0,
                           "tv_truncated": 0.0, "n_control": 0}

        ctrl_seasons = [s for s in range(end + 1, int(ufa_year))]
        if not ctrl_seasons:
            return empty, {"status": "rfa_no_control_years_DATA_FLAG",
                           "tv_raw": 0.0, "tv_truncated": 0.0, "n_control": 0}

        # --- VALUE side: extend the Layer 2 walk through the control years -
        nk = crows.iloc[0]["nk"]
        a, src = sp.anchor(nk, valuation_season)
        if pd.isna(a):
            return empty, {"status": "no_anchor"}
        age = sp.age_at(crows.iloc[0]["bd"], valuation_season)
        horizon = (end - valuation_season) + len(ctrl_seasons)
        ratios, path = sp.ratio_path(nk, age, horizon)
        if a < 0:
            path = "replacement_reversion"          # D12 v3, same as Layer 2

        # --- COST side: final contract-year base salary -> iterated QOs ----
        final = crows[crows["season_start"] == end].iloc[0]
        sal, sal_src = final_year_salary(crows, final)
        # guard: never take the average-annual-value substitute while a real
        # salary sits on the contract. If this fires, the helper regressed.
        assert not (sal_src == "pp_aav_fallback"
                    and crows["cs_nhl_salary"].notna().any()), (
            f"contract {cid}: fell back to AAV while a real salary exists")
        cap_hit = float(final["cost"])
        signed_2020_plus = int(crows["season_start"].min()) >= 2020  # proxy
        posgrp = crows.iloc[0]["posgrp"]           # 'F' or 'D', for the rate

        out, tv_raw, tv_trunc, tv_adj = [], 0.0, 0.0, 0.0
        truncated, survival = False, 1.0
        for j, season in enumerate(ctrl_seasons, start=1):
            k = (end - valuation_season) + j
            mult = sp.multiplier(a, ratios[k], k)
            pw = a * mult
            ceil = cap_path(valuation_season, k)
            lm = league_min_path(season)
            val = max(price(pw, posgrp, ceil), lm)             # D10 floor
            qo = qualifying_offer(sal, cap_hit, season, signed_2020_plus)
            surplus = val - qo
            tv_raw += surplus
            if not truncated and surplus < 0:
                truncated = True                    # D13: walk away, rights end
            if not truncated:
                tv_trunc += surplus
            # D14(c): each control year passes a qualify-or-walk gate; the
            # chance of passing is the OBSERVED qualify rate for players of
            # this year's projected quality, and gates compound (a player
            # let go in year 2 cannot be re-qualified in year 3).
            survival *= self.qualify_p.get(_anchor_bucket(pw), 1.0)
            if truncated:
                survival = 0.0                     # hard walk dominates
            tv_adj += survival * surplus
            out.append({
                "player_id": player_id, "full_name": final["full_name"],
                "contract_id": cid, "control_season": season, "j": j,
                "valuation_season": valuation_season, "path": path,
                "projected_war": pw, "value_dollars": val,
                "qo_cost": qo, "qo_salary_source": sal_src,
                "surplus_dollars": surplus, "qualify_survival": survival,
                "surplus_adjusted": survival * surplus,
                "counted_after_truncation": not truncated,
            })
            # next year's QO escalates off THIS QO (a one-year deal at qo)
            sal, cap_hit = qo, qo
        return pd.DataFrame(out), {
            "status": "ok", "n_control": len(ctrl_seasons),
            "tv_raw": tv_raw, "tv_truncated": tv_trunc,
            "tv_adjusted": tv_adj,                 # D14(c) -- the headline TV
            "anchor": a, "path": path, "qo_salary_source": sal_src}


# ---------------------------------------------------------------------------
# VALIDATION BATTERY
# ---------------------------------------------------------------------------
def validate():
    tv = TerminalValuer()
    sp = tv.sp
    log("=" * 74)
    log("PHASE 1c VALIDATION BATTERY  (QO mechanics self-test passed on import)")
    log("=" * 74)

    # ---- 1. expiry accounting: every contract ending 2018-2025 -------------
    last = (sp.spine.sort_values("season_start")
            .groupby("contract_id").tail(1))
    ending = last[last["season_start"].between(2018, 2025)]
    log(f"\n[1] skater contracts ending 2018-2025: {len(ending):,}")
    for st, n in ending["pp_expiry"].value_counts().items():
        rule = "TV = 0 (locked)" if st != "RFA" else "TV computed"
        log(f"    {st:10s} {n:5,d}   -> {rule}")

    # ---- 2. realized comparison: projected QO vs what players ACTUALLY ----
    # signed next. QO is the team's option cost; real re-signings should sit
    # at or above it. The gap quantifies how conservative pricing control at
    # QO is -- a paper-ready limitation statistic.
    log("\n[2] projected first-control-year QO vs the player's ACTUAL next contract:")
    n, gaps, salary_sources = 0, [], []
    rfa_end = ending[ending["pp_expiry"] == "RFA"]
    for _, r in rfa_end.iterrows():
        end = int(r["season_start"])
        if end >= 2025:
            continue                                   # no next season observed
        # actual next contract = the spine row for this player in end+1
        nxt = sp.spine[(sp.spine["player_id"] == r["player_id"])
                       & (sp.spine["season_start"] == end + 1)
                       & (sp.spine["contract_id"] != r["contract_id"])]
        if nxt.empty or pd.isna(nxt.iloc[0]["cost"]):
            continue
        crows_v = sp.spine[sp.spine["contract_id"] == r["contract_id"]]
        sal, sal_src_v = final_year_salary(crows_v, r)
        salary_sources.append(sal_src_v)
        qo = qualifying_offer(sal, float(r["cost"]), end + 1,
                              int(end) >= 2020)
        gaps.append(float(nxt.iloc[0]["cost"]) - qo)
        n += 1
    gaps = np.array(gaps)
    log(f"    n = {n:,} RFA-expiring contracts with an observed next deal")
    log(f"    actual cap hit >= projected QO: {(gaps >= -1).mean()*100:.1f}% of cases")
    log(f"    median (actual - QO) = ${np.median(gaps)/1e6:+.2f}M   "
        f"mean = ${gaps.mean()/1e6:+.2f}M")
    log("    Reading: at the MEDIAN, real re-signings land almost exactly at the")
    log("    QO -- so QO-cost pricing is approximately right for the typical")
    log("    (fringe) RFA. The positive MEAN gap is concentrated in good players,")
    log("    who really do cost more than their QO to retain -- for them, QO")
    log("    pricing is the team-favourable upper bound on surplus. [paper note]")
    # item 1.10 exposure: how often is the substitute actually in use?
    _sub = sum(1 for x in salary_sources if x == "pp_aav_fallback")
    _real = len(salary_sources) - _sub
    if salary_sources:
        log(f"    [1.10] qualifying-offer salary source: {_real:,} real vs "
            f"{_sub:,} substitutes ({100*_sub/len(salary_sources):.0f}% "
            f"substituted) -- documented limitation, not a repair")

    # ---- 3. terminal-value distribution over RFA-expiring contracts --------
    log("\n[3] terminal values, valued from each contract's FINAL season:")
    res = []
    for _, r in rfa_end.iterrows():
        _, s = tv.terminal_value(int(r["player_id"]), int(r["season_start"]))
        if s.get("status") == "ok":
            s["anchor_bucket"] = ("negative" if s["anchor"] < 0 else
                                  "fringe 0-1" if s["anchor"] < 1 else
                                  "regular 1-3" if s["anchor"] < 3 else "star 3+")
            res.append(s)
    df = pd.DataFrame(res)
    log("    D14(c) calibration table (estimated from the spine this run):")
    log(f"      {'bucket':9s} {'P(qual) FIXED':>14s} {'n':>7s}   "
        f"{'P(qual) PRE-FIX':>16s} {'n':>7s}")
    for b in ["star", "regular", "fringe", "negative"]:
        if b in tv.qualify_p:
            po = tv.qualify_p_prefix.get(b)
            no = tv.qualify_n_prefix.get(b)
            old = f"{po*100:15.1f}% {no:7,d}" if po is not None else f"{'--':>16s} {'--':>7s}"
            log(f"      {b:9s} {tv.qualify_p[b]*100:13.1f}% {tv.qualify_n[b]:7,d}   {old}")
    _nn = sum(tv.qualify_n.values())
    _no = sum(tv.qualify_n_prefix.values())
    _wn = sum(tv.qualify_n[b]*(1-tv.qualify_p[b]) for b in tv.qualify_p)
    _wo = sum(tv.qualify_n_prefix[b]*(1-tv.qualify_p_prefix[b])
              for b in tv.qualify_p_prefix)
    log(f"    [Stage 4] overall walk-away rate: {100*_wo/max(_no,1):.1f}% "
        f"(n={_no:,}, pre-fix) -> {100*_wn/max(_nn,1):.1f}% (n={_nn:,}, fixed)")
    log("    [Stage 4] review expected 21.3% (n=1,231) -> 27.0% (n=2,270), "
        "with star/regular/fringe unchanged. Compare the table above.")
    log(f"    computed for {len(df):,} contracts "
        f"(status ok; others: no anchor / data flags)")
    log(f"    truncation (D13) binds on {(df['tv_truncated'] < df['tv_raw']).mean()*100:.1f}% "
        f"of contracts (raw sum > truncated)")
    log(f"    {'bucket':14s} {'n':>5s}  {'median TV':>10s}  {'mean TV':>10s}  (truncated)")
    for b in ["star 3+", "regular 1-3", "fringe 0-1", "negative"]:
        d = df[df["anchor_bucket"] == b]
        if d.empty:
            continue
        log(f"    {b:14s} {len(d):5,d}  ${d['tv_truncated'].median()/1e6:8.2f}M  "
            f"${d['tv_truncated'].mean()/1e6:8.2f}M   -> adjusted: "
            f"${d['tv_adjusted'].median()/1e6:6.2f}M med, "
            f"${d['tv_adjusted'].mean()/1e6:6.2f}M mean")
    log("    NOTE (D14c, resolved): under the intercept convention alone, fringe")
    log("    and negative players carried inflated TVs (the model predicted only")
    log("    18% of real walk-aways). The adjusted column applies the empirical")
    log("    qualify-rate survival chain above, calibrated from 1,200+ observed")
    log("    team decisions -- reality-weighted, not theory-picked.")

    # ---- 4. spot demos ------------------------------------------------------
    log("\n[4] spot demos (valued from the contract's final season):")
    for name in ["Matvei Michkov", "Lane Hutson", "Wyatt Johnston"]:
        prow = sp.spine[sp.spine["full_name"] == name]
        if prow.empty:
            continue
        pid = int(prow.iloc[0]["player_id"])
        # find his current/latest contract's final season
        cid = prow.sort_values("season_start").iloc[-1]["contract_id"]
        end = int(sp.spine[sp.spine["contract_id"] == cid]["season_start"].max())
        t0 = min(end, 2025)                       # anchor needs observed WAR
        det, s = tv.terminal_value(pid, t0)
        if s.get("status") != "ok":
            log(f"    {name}: {s.get('status')}")
            continue
        log(f"    {name} (valued from {t0}, anchor {s['anchor']:+.2f} WAR, "
            f"{s['n_control']} control years, path={s['path']}):")
        for _, r in det.iterrows():
            log(f"      {r['control_season']}-{str(r['control_season']+1)[2:]}  "
                f"WAR {r['projected_war']:+.2f}  value ${r['value_dollars']/1e6:5.2f}M  "
                f"QO ${r['qo_cost']/1e6:4.2f}M  surplus ${r['surplus_dollars']/1e6:+6.2f}M"
                + ("" if r["counted_after_truncation"] else "  [past truncation]"))
        log(f"      TERMINAL VALUE: ${s['tv_adjusted']/1e6:.2f}M adjusted (D14c) "
            f"| ${s['tv_truncated']/1e6:.2f}M unadjusted | ${s['tv_raw']/1e6:.2f}M raw")

    Path(OUT_LOG).write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nrun log written: {OUT_LOG}")


if __name__ == "__main__":
    validate()
