#!/usr/bin/env python3
"""
xg_model.py  --  Script 2 of the Tier 2 game-level model build

WHAT THIS DOES, IN PLAIN ENGLISH
---------------------------------
For every unblocked shot attempt in the database, this script estimates the
probability that the shot becomes a goal, based on where it was taken from,
what kind of shot it was, the manpower situation, and whether it was a
rebound. That probability is the shot's "expected goals" (xG) value.

Why this is the right yardstick for the paper: xG is denominated directly in
goals. A shot with a 12% chance of scoring is worth 0.12 goals -- no
arbitrary point system, no borrowed weights. Summed over a player's shots it
measures offensive contribution; summed over shots taken AGAINST a player's
team while he is on the ice (using Script 1's on-ice table) it measures
defensive exposure. Goals then convert to wins using the goals-per-win rate
estimated from our own games table (Script 4).

MODEL CHOICE, AND WHY (plain English)
--------------------------------------
The model is a logistic regression: a standard statistical tool that takes a
set of inputs (distance, angle, shot type, ...) and produces a probability
between 0 and 1. Two reasons it is the right choice here over fancier
machine-learning alternatives:
  1. INTERPRETABILITY. Every input gets one coefficient with a plain reading
     ("rebounds roughly double the odds of scoring, all else equal"). In
     front of an economics committee, a model whose every moving part can be
     stated in one sentence beats a black box that scores 1% better.
  2. CALIBRATION IS WHAT MATTERS. This model's job is not to classify
     individual shots correctly -- it is to produce probabilities that are
     RIGHT ON AVERAGE, so that summing them yields honest goal totals.
     Logistic regression is naturally well-calibrated; the validation below
     checks this directly.

SAMPLE RULES (each one flagged, per project convention)
--------------------------------------------------------
1. UNBLOCKED ATTEMPTS ONLY (goals, shots on goal, missed shots). Blocked
   shots are excluded because the NHL records a blocked shot's coordinates
   at the BLOCKER's position, not the shooter's -- the model's key input
   ("where was this shot from") is wrong for exactly those rows. Standard
   practitioner solution; the data forces it regardless.
2. EMPTY-NET SHOTS EXCLUDED (no goalie_id on the row). The model prices
   "expected goals against a goalie" -- an empty-net tap-in is not
   information about shooting skill or chance quality. 4,068 empty-net
   goals are excluded by this rule.
3. SHOOTOUTS EXCLUDED (regular-season period 5). A skills contest, not
   game play. Same rule as Script 1.
4. FITTING SAMPLE IS REGULAR SEASON ONLY (locked Decision 4: playoff
   hockey is systematically different -- tighter checking, more blocking).
   Playoff shots still RECEIVE an xG score from the fitted model so the
   metric exists for them; whether they enter the back-test is a separate,
   analysis-time decision.
5. ROWS WITH MISSING COORDINATES DROPPED (14 rows of ~1.03M -- counted,
   not silent).

STRENGTH STATE -- WHERE IT COMES FROM (the suspect-game rule)
--------------------------------------------------------------
Each shot's manpower situation (even strength / power play / shorthanded,
from the SHOOTER's perspective) normally comes from the league's own
situation code on the shot row. Exception: in the ~117 games where Script 1
proved the league's codes are stuck/corrupted (see on_ice_game_qc.codes_
suspect), strength is derived instead from Script 1's reconstructed on-ice
skater counts (on_ice_event_qc.away_found / home_found), which in those
games are the more reliable record. This is the downstream rule locked when
the suspect-code phenomenon was discovered, now implemented.

FEATURES (the model's inputs, and why each earns its place)
------------------------------------------------------------
- DISTANCE to the net and ANGLE off the net's centerline, computed from
  shot coordinates. The two dominant drivers of shot quality: close and
  central beats far and wide. Distance enters LINEARLY -- a log form
  (log(1+distance)) was tested during development on theoretical grounds
  and made calibration measurably WORSE at both tails (top-decile
  overprediction widened from 21.9%-vs-17.0% to 25.2%-vs-17.1%, and the
  low-danger deciles inflated too), so the theoretically-motivated form was
  rejected on empirical evidence. The residual top-decile overprediction
  under the linear form is documented in the validation output and in the
  limitations note below.
- SHOT TYPE (wrist/slap/snap/backhand/tip-in/deflection/wrap-around...).
  A tip-in from 15 feet and a slapshot from 15 feet are different chances.
  IMPORTANT: shots with a MISSING type (151 rows of ~1.03M) get no type
  indicator at all and are priced by location/strength/rebound alone.
  Reason: the feed omits shot type disproportionately on GOALS (those 151
  rows convert at 80%), so a "type unknown" indicator would smuggle the
  outcome into the inputs -- a label leak. Caught in the coefficient sanity
  check (the unknown dummy fitted at +1.67, wildly out of line) before
  shipping, and verified against the raw data.
- STRENGTH STATE (EV / PP / SH). Power-play shots come with more time,
  space, and pre-shot movement than the location alone reveals.
- REBOUND flag: same team's attempt within 3 seconds of a SAVED shot on
  goal. Goalies are out of position on rebounds; this is one of the largest
  effects in every public xG model. The generator must be a SAVED shot
  specifically: a missed shot produces no goalie rebound, and a goal stops
  play -- a first version of this script counted any prior attempt and the
  rebound effect came out slightly NEGATIVE, which is how the definition
  error was caught (coefficient sanity check, before shipping). Same-second
  follow-ups count: they are the most dangerous rebounds, and the feed's
  whole-second clock cannot separate them further. One further guard: the
  game clock FREEZES during stoppages, so "2 seconds after a save" can hide
  a whistle and faceoff in between (goalie froze the puck). A rebound
  therefore also requires that NO faceoff occurred between the save and the
  shot -- checked against the faceoff_events table.

WHAT IS DELIBERATELY NOT IN THE MODEL (documented, not hidden)
----------------------------------------------------------------
- Pre-shot passing (royal-road passes, one-timers): not recorded in the
  public feed at all. Every public-data xG model shares this gap.
- Shooter identity/skill: excluded BY DESIGN, not by limitation. The metric
  must price the CHANCE, not the shooter, or player value gets
  double-counted when chances and finishing are later attributed.
- Score state: excluded from the xG model itself; score effects are handled
  at the RATE level in Script 3 (a shot's goal probability given its
  location does not change with the score; how many shots a team GENERATES
  does).

VALIDATION (what "the model works" means here, concretely)
------------------------------------------------------------
Fit on regular seasons 2017-18 through 2023-24; test on held-out 2024-25 +
2025-26 regular seasons -- data the model has never seen, mimicking real
forward prediction. Two checks:
  1. AUC ("area under the curve"): hand the model one random goal and one
     random non-goal; AUC is the probability it ranks the goal as the more
     dangerous shot. 0.5 = coin flip, 1.0 = perfect. Public xG models on
     comparable feature sets land around 0.75-0.78.
  2. CALIBRATION BY DECILE: sort held-out shots into ten buckets by
     predicted danger; within each bucket, compare predicted goal rate to
     the actual goal rate. If the model says "8% chance" and those shots
     score 8% of the time, the sums downstream can be trusted. This is the
     check that matters most for the paper.
After validation, the model is refit on ALL regular-season data (standard
practice: never throw away data once out-of-sample performance is
established) and every unblocked, goalie-in shot -- all seasons, playoffs
included -- receives an xG score in the shot_xg output table.

KNOWN LIMITATION, DOCUMENTED NOT HIDDEN: the top danger decile overpredicts
on the holdout (about 21.9% predicted vs 17.0% actual). Part of this is era
drift -- the holdout seasons convert high-danger chances at a lower rate
than the 2017-24 training era -- and part is the linear functional form.
Two protections downstream: (1) the refit-on-everything final model sums to
actual goals at a ratio of ~1.000 over the full sample, so aggregate totals
are honest; (2) Script 4's team-game validation regression is the formal
check that the assembled metric tracks real goal differential. Documented
here and in the calibration CSV so the limitation is visible to any reader
of the model outputs.

THIRD-PARTY CROSS-CHECK (planned, separate step)
--------------------------------------------------
Per the locked decision, the nhlscraper R package's pre-built xG model will
be used as an external sanity check on our scores in a later validation
pass. It is NOT used in fitting -- our model must stand on its own data.

OUTPUTS
--------
  shot_xg            (DB table)  one row per scored shot: xG + all features
  xg_coefficients.csv            every model coefficient, named
  xg_calibration.csv             decile calibration table (holdout)
  xg_model_runlog.txt            plain-text run log

DEPENDENCIES
-------------
  pip install scikit-learn numpy
(scikit-learn is the standard Python statistics/machine-learning library;
numpy comes with it. One-time install.)

USAGE
------
  python3 xg_model.py                # full run against DB_PATH below
Deterministic and idempotent: the shot_xg table is dropped and rebuilt on
every run; re-running never double-writes.
"""

import csv
import math
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from dotenv import load_dotenv

load_dotenv()

SCRIPT_VERSION = "v1.0 (2026-07-03) -- initial xG model"

# ---------------------------------------------------------------------------
# CONFIG -- GAMELOG_DB comes from .env (see .env.example). It must be the same
# database Script 1 wrote its on_ice_* tables into.
# ---------------------------------------------------------------------------
DB_PATH = Path(os.environ["GAMELOG_DB"])
OUT_DIR = DB_PATH.parent

# Holdout seasons for honest out-of-sample validation (regular season only).
HOLDOUT_SEASONS = {"20242025", "20252026"}

# Rebound window: attempt within this many seconds of a SAVED shot on goal.
# 3s is the standard practitioner window (e.g. MoneyPuck's public model).
REBOUND_WINDOW_S = 3

RUNLOG = []
def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line)
    RUNLOG.append(line)


def mmss_to_seconds(t: str) -> int | None:
    try:
        m, s = str(t).split(":")
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# GEOMETRY. NHL coordinates: center ice is (0,0), the two goal lines sit at
# x = +89 and x = -89 feet, y runs -42.5 to +42.5. Teams switch ends between
# periods, so a raw x value alone does not say which net was attacked. The
# standard public-data convention (used by every public xG model) is to fold
# the rink in half with |x|: the shot is assumed to target the NEARER net.
# This is correct for the ~95% of unblocked attempts taken in the offensive
# zone and a harmless approximation for long-range clears on net.
#   distance = straight-line feet to the net's center point (89-|x|, 0)
#   angle    = degrees off the line straight out from the net's center;
#              0 = dead center, 90 = at the goal line, >90 = behind the net
# ---------------------------------------------------------------------------
def shot_geometry(x: float, y: float) -> tuple[float, float]:
    dx = 89.0 - abs(x)
    dy = abs(y)
    distance = math.sqrt(dx * dx + dy * dy)
    angle = math.degrees(math.atan2(dy, dx))   # dx<0 (behind net) -> angle>90
    return distance, angle


def strength_bucket(sk_for: int, sk_against: int) -> str:
    """Collapses skater counts into the three categories that matter for shot
    quality. 5v5, 4v4, and 3v3 all price as even strength (EV); any manpower
    edge for the shooter is a power play (PP); any deficit is shorthanded (SH)."""
    if sk_for > sk_against:
        return "PP"
    if sk_for < sk_against:
        return "SH"
    return "EV"


def main() -> None:
    print(f"xg_model.py {SCRIPT_VERSION}")
    if not DB_PATH.exists():
        print(f"Database not found at:\n  {DB_PATH}\n"
            f"Set GAMELOG_DB in .env (see .env.example).", file=sys.stderr)
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    tables = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing = {"games", "shot_events", "skater_games", "goalie_games",
               "faceoff_events", "on_ice_event_qc", "on_ice_game_qc"} - tables
    if missing:
        print(f"Required tables missing: {sorted(missing)}. Run the v2.2 "
            f"scraper and on_ice_reconstruction.py first.", file=sys.stderr)
        raise SystemExit(1)

    # -----------------------------------------------------------------------
    # STEP 1: load the lookup layers.
    # -----------------------------------------------------------------------
    log("Loading game metadata and suspect-game flags...")
    game_meta = {}   # game_id -> (season, game_type, away_ab, home_ab)
    for gid, season, gtype, away, home in cur.execute(
            "SELECT game_id, season, game_type, away_team, home_team FROM games"):
        game_meta[int(gid)] = (str(season), int(gtype), away, home)

    suspect_games = {int(r[0]) for r in cur.execute(
        "SELECT game_id FROM on_ice_game_qc WHERE codes_suspect = 1")}
    log(f"{len(game_meta):,} games; {len(suspect_games):,} with suspect codes "
        f"(strength will use reconstructed counts there).")

    # Reconstructed skater counts, loaded ONLY for suspect games (memory-light).
    recon_counts = {}   # (game_id, event_id) -> (away_found, home_found)
    if suspect_games:
        marks = ",".join("?" * len(suspect_games))
        for gid, eid, af, hf in cur.execute(
                f"SELECT game_id, event_id, away_found, home_found "
                f"FROM on_ice_event_qc WHERE game_id IN ({marks})",
                sorted(suspect_games)):
            recon_counts[(int(gid), int(eid))] = (af, hf)

    # Faceoff clock times per game-period, sorted, for the rebound guard:
    # a rebound is only real if no faceoff happened between save and shot.
    log("Loading faceoff times for the rebound stoppage-guard...")
    from bisect import bisect_right
    faceoffs = defaultdict(list)   # (game_id, period) -> sorted [seconds]
    for gid, period, tstr in cur.execute(
            "SELECT game_id, period, time_in_period FROM faceoff_events"):
        t = mmss_to_seconds(tstr)
        if t is not None:
            faceoffs[(int(gid), int(period))].append(t)
    for k in faceoffs:
        faceoffs[k].sort()

    # Shooter -> team map (ID-based join via the box score; no name matching).
    log("Building player->team map per game from box scores...")
    player_team = defaultdict(dict)   # game_id -> {player_id: team_ab}
    for table in ("skater_games", "goalie_games"):
        for gid, pid, team in cur.execute(
                f"SELECT game_id, player_id, team FROM {table}"):
            player_team[int(gid)][int(pid)] = team

    # -----------------------------------------------------------------------
    # STEP 2: assemble the shot sample, applying every sample rule.
    # Single pass in game/period/time order so the rebound flag can be
    # computed from the immediately preceding attempt by the same team.
    # -----------------------------------------------------------------------
    log("Assembling shot sample (unblocked, goalie in, no shootouts)...")
    counters = defaultdict(int)
    shots = []          # one dict per usable shot: features + label + ids
    prev_save = {}      # (game_id, period, team) -> clock seconds of that
                        # team's most recent SAVED shot on goal (the only
                        # event that can generate a true goalie rebound)

    for row in cur.execute("""
            SELECT game_id, event_id, period, time_in_period, situation_code,
                   shot_result, x_coord, y_coord, shot_type,
                   shooting_player_id, goalie_id
            FROM shot_events
            WHERE shot_result != 'blocked-shot'
            ORDER BY game_id, period, time_in_period, event_id"""):
        gid, eid, period = int(row[0]), int(row[1]), int(row[2])
        tstr, sit, result = row[3], row[4], row[5]
        x, y, shot_type = row[6], row[7], row[8]
        shooter_id = int(row[9]) if row[9] not in (None, "") else None
        goalie_id = row[10]

        counters["unblocked_seen"] += 1
        meta = game_meta.get(gid)
        if meta is None:
            counters["skipped_no_game_meta"] += 1
            continue
        season, gtype, away_ab, home_ab = meta

        # Rule 3: shootout exclusion (regular-season period 5).
        if gtype == 2 and period == 5:
            counters["skipped_shootout"] += 1
            continue
        # Rule 2: empty-net exclusion -- the model prices shots at a goalie.
        if goalie_id in (None, ""):
            counters["skipped_empty_net"] += 1
            continue
        # Rule 5: coordinates required (distance/angle are the core inputs).
        if x in (None, "") or y in (None, ""):
            counters["skipped_no_coords"] += 1
            continue
        if shooter_id is None:
            counters["skipped_no_shooter"] += 1
            continue

        t = mmss_to_seconds(tstr)
        if t is None:
            counters["skipped_bad_time"] += 1
            continue

        # Shooter's team and side (ID-based lookup via box score).
        team = player_team.get(gid, {}).get(shooter_id)
        if team is None:
            counters["skipped_shooter_unmapped"] += 1
            continue
        shooter_is_home = 1 if team == home_ab else 0

        # ---- strength state: league code normally; reconstruction in the
        #      ~117 suspect-code games (the locked downstream rule) ----------
        used_recon = 0
        sk_away = sk_home = None
        if gid in suspect_games:
            rc = recon_counts.get((gid, eid))
            if rc is not None and rc[0] is not None and rc[1] is not None:
                sk_away, sk_home = int(rc[0]), int(rc[1])
                used_recon = 1
        if sk_away is None:
            s4 = str(sit) if sit is not None else ""
            if len(s4) == 4 and s4.isdigit():
                sk_away, sk_home = int(s4[1]), int(s4[2])
            else:
                counters["skipped_no_strength"] += 1
                continue
        sk_for = sk_home if shooter_is_home else sk_away
        sk_against = sk_away if shooter_is_home else sk_home
        strength = strength_bucket(sk_for, sk_against)

        # ---- rebound: same team's attempt within the window after a SAVED
        #      shot on goal. Same-second (diff = 0) counts -- scrambles in
        #      front are recorded within one clock second. The generator
        #      timestamp is updated AFTER the check, so a shot never
        #      matches against itself. ------------------------------------
        key = (gid, period, team)
        last_save_t = prev_save.get(key)
        rebound = 0
        if (last_save_t is not None
                and 0 <= t - last_save_t <= REBOUND_WINDOW_S):
            # stoppage guard: a faceoff strictly after the save and strictly
            # BEFORE the shot means play stopped in between -- not a rebound.
            # "Strictly before" matters: the clock freezes at a goal, so the
            # post-goal center-ice faceoff is recorded at the SAME second as
            # the goal itself. A first version used <= here and thereby
            # unflagged exactly the rebounds that SCORED (every rebound goal
            # is followed by a same-second faceoff), inverting the rebound
            # effect to strongly negative. Caught by inspecting the actual
            # goal rate of flagged shots (2.7% vs the ~20% real rebounds
            # run), not by the model failing to fit.
            fo = faceoffs.get((gid, period), ())
            i = bisect_right(fo, last_save_t)
            had_faceoff_between = i < len(fo) and fo[i] < t
            rebound = 0 if had_faceoff_between else 1
        if result == "shot-on-goal":      # saved shot: can generate a rebound
            prev_save[key] = t

        distance, angle = shot_geometry(float(x), float(y))
        st = (shot_type or "unknown").strip().lower() or "unknown"

        shots.append({
            "game_id": gid, "event_id": eid, "season": season,
            "game_type": gtype, "is_goal": 1 if result == "goal" else 0,
            "distance": distance, "angle": angle, "shot_type": st,
            "strength": strength, "rebound": rebound,
            "used_recon_strength": used_recon,
            "shooter_id": shooter_id, "team": team,
        })

    log(f"Sample assembled: {len(shots):,} usable shots.")
    for k in sorted(counters):
        log(f"  {k}: {counters[k]:,}")

    # -----------------------------------------------------------------------
    # STEP 3: build the model matrix. Categorical inputs (shot type,
    # strength) are expanded into 0/1 indicator columns -- "one-hot
    # encoding," the standard way to hand categories to a regression. The
    # most common category of each (wrist shot; even strength) is the
    # baseline the others are measured against.
    # -----------------------------------------------------------------------
    shot_type_levels = sorted({s["shot_type"] for s in shots})
    if "wrist" in shot_type_levels:           # wrist = baseline (most common)
        shot_type_levels.remove("wrist")
    if "unknown" in shot_type_levels:         # missing type gets NO dummy --
        shot_type_levels.remove("unknown")    # see the label-leak note in the
                                              # FEATURES section above
    strength_levels = ["PP", "SH"]            # EV = baseline

    feature_names = (["distance", "angle", "rebound"]
                     + [f"shot_type={t}" for t in shot_type_levels]
                     + [f"strength={s}" for s in strength_levels])

    def make_X(sub):
        X = np.zeros((len(sub), len(feature_names)))
        for i, s in enumerate(sub):
            X[i, 0] = s["distance"]
            X[i, 1] = s["angle"]
            X[i, 2] = s["rebound"]
            if s["shot_type"] in shot_type_levels:
                X[i, 3 + shot_type_levels.index(s["shot_type"])] = 1.0
            if s["strength"] in strength_levels:
                X[i, 3 + len(shot_type_levels)
                    + strength_levels.index(s["strength"])] = 1.0
        return X

    y_all = np.array([s["is_goal"] for s in shots])

    # -----------------------------------------------------------------------
    # STEP 4: honest out-of-sample validation. Train on 2017-18..2023-24
    # regular season; test on the held-out 2024-25 + 2025-26 regular seasons.
    # -----------------------------------------------------------------------
    reg = [i for i, s in enumerate(shots) if s["game_type"] == 2]
    train_idx = [i for i in reg if shots[i]["season"] not in HOLDOUT_SEASONS]
    test_idx = [i for i in reg if shots[i]["season"] in HOLDOUT_SEASONS]
    log(f"Fitting sample: {len(train_idx):,} reg-season shots "
        f"(2017-18..2023-24); holdout: {len(test_idx):,} shots "
        f"(2024-25 + 2025-26).")

    # max_iter raised from the default because with ~1M rows the fitting
    # procedure needs more steps to fully converge; C=1.0 is the default,
    # near-unregularized setting appropriate when observations vastly
    # outnumber features (~1M rows vs ~15 columns).
    model = LogisticRegression(max_iter=2000, C=1.0)
    model.fit(make_X([shots[i] for i in train_idx]), y_all[train_idx])

    p_test = model.predict_proba(make_X([shots[i] for i in test_idx]))[:, 1]
    y_test = y_all[test_idx]
    auc = roc_auc_score(y_test, p_test)
    log(f"HOLDOUT AUC: {auc:.4f}  (0.5 = coin flip; public xG models on "
        f"comparable features land ~0.75-0.78)")

    # Decile calibration: predicted vs actual goal rate, ten buckets.
    order = np.argsort(p_test)
    calib_rows = []
    for d in range(10):
        idx = order[int(d * len(order) / 10):int((d + 1) * len(order) / 10)]
        calib_rows.append((d + 1, len(idx),
                           float(np.mean(p_test[idx])),
                           float(np.mean(y_test[idx]))))
        log(f"  decile {d+1:>2}: n={len(idx):>6,}  "
            f"predicted {calib_rows[-1][2]*100:5.2f}%  "
            f"actual {calib_rows[-1][3]*100:5.2f}%")
    overall_pred = float(np.mean(p_test)); overall_act = float(np.mean(y_test))
    log(f"  overall: predicted {overall_pred*100:.2f}% vs actual "
        f"{overall_act*100:.2f}% (these should be close)")

    # -----------------------------------------------------------------------
    # STEP 5: refit on ALL regular-season data (standard practice once
    # out-of-sample performance is established), then score EVERY usable
    # shot -- all seasons, playoffs included -- and write shot_xg.
    # -----------------------------------------------------------------------
    log("Refitting on all regular-season shots and scoring everything...")
    final_model = LogisticRegression(max_iter=2000, C=1.0)
    final_model.fit(make_X([shots[i] for i in reg]), y_all[reg])
    p_all = final_model.predict_proba(make_X(shots))[:, 1]

    cur.executescript("""
        DROP TABLE IF EXISTS shot_xg;
        CREATE TABLE shot_xg (
            game_id     INTEGER NOT NULL,
            event_id    INTEGER NOT NULL,
            season      TEXT    NOT NULL,
            game_type   INTEGER NOT NULL,
            shooter_id  INTEGER NOT NULL,
            team        TEXT    NOT NULL,
            is_goal     INTEGER NOT NULL,
            xg          REAL    NOT NULL,
            distance    REAL, angle REAL, shot_type TEXT, strength TEXT,
            rebound     INTEGER,
            used_recon_strength INTEGER,   -- 1 = suspect-code game, strength
                                           --     came from reconstruction
            PRIMARY KEY (game_id, event_id)
        );
    """)
    cur.executemany(
        "INSERT INTO shot_xg VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(s["game_id"], s["event_id"], s["season"], s["game_type"],
          s["shooter_id"], s["team"], s["is_goal"], float(p_all[i]),
          s["distance"], s["angle"], s["shot_type"], s["strength"],
          s["rebound"], s["used_recon_strength"])
         for i, s in enumerate(shots)])
    conn.commit()
    log(f"shot_xg written: {len(shots):,} rows.")

    # Sanity check that belongs in the run log, not just in conversation:
    # summed xG across all regular-season shots should be close to the
    # actual number of (non-empty-net) regular-season goals.
    tot_xg = float(np.sum(p_all[reg])); tot_goals = int(np.sum(y_all[reg]))
    log(f"Sum of reg-season xG: {tot_xg:,.0f} vs actual goals {tot_goals:,} "
        f"(ratio {tot_xg/tot_goals:.3f}; ~1.000 confirms calibration).")

    # -----------------------------------------------------------------------
    # STEP 6: write the coefficient and calibration files + run log.
    # -----------------------------------------------------------------------
    coef_path = OUT_DIR / "xg_coefficients.csv"
    with open(coef_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["feature", "coefficient", "plain_reading"])
        w.writerow(["(intercept)", float(final_model.intercept_[0]),
                    "baseline log-odds: a 0-ft, dead-center, non-rebound "
                    "wrist shot at even strength"])
        for name, c in zip(feature_names, final_model.coef_[0]):
            w.writerow([name, float(c),
                        "negative = lowers scoring odds; positive = raises"])
    log(f"Coefficients written to {coef_path}")

    calib_path = OUT_DIR / "xg_calibration.csv"
    with open(calib_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["decile", "n_shots", "predicted_goal_rate",
                    "actual_goal_rate"])
        w.writerows(calib_rows)
        w.writerow(["overall", len(test_idx), overall_pred, overall_act])
        w.writerow(["holdout_auc", "", auc, ""])
    log(f"Calibration table written to {calib_path}")

    (OUT_DIR / "xg_model_runlog.txt").write_text(
        "\n".join(RUNLOG) + "\n", encoding="utf-8")
    conn.close()
    log("Done.")


if __name__ == "__main__":
    main()
