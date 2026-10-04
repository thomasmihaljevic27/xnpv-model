"""level_games_weighting_test.py -- plain or games-weighted 50/30/20, the same on both sides of the blend.

WHY (2026-10-04, Thomas; MODEL_DIRECTIVES.md, plan of record step 1, directive 1 detail 1).
Directive 1's starting level is 65% x the player's own 50/30/20 rate per 82 + 35% x his comparable
players' level. Detail 1 asks whether a short season counts for less (each season's weight 50/30/20
TIMES its games) or not (plain 50/30/20 on the per-82 rates). Directive 2 made the aging curve's
level plain, and the curve's level is what the comparables' 35% is measured on. Thomas: "if this is
going to be games weighted then the comparable's level should be as well. i want them to be the
same." So the two arms that can be adopted use ONE weighting on both sides:
    plain / plain   own rate plain;          curve level plain (directive 2 as written)
    games / games   own rate games-weighted; curve level games-weighted
The evidence so far (starting_level_simple_test.py v1.1: games-weighted 1.1683 against plain 1.1708)
was measured with the start pulled toward the LEAGUE average, with no resample count, and with the
curve left on its old equal two-season level. This test scores the two arms on the directed design.
TEST ONLY: nothing in 20_CODE changes and nothing is adopted by running it.

THE TWO MIXED ARMS ARE REFERENCES, NOT CANDIDATES. Thomas requires the two sides to match. The
mixed arms (own games / curve plain; own plain / curve games) are scored only to show which side
carries any difference between the two matched arms (CLAUDE.md: score each part alone and in
combination before crediting one part). "own games / curve plain" is exactly version (c) of
25_TESTS/aging_level_weights_test.py v1.0 and must give back its recorded whole-forecast RMSE,
1.3596 (2026-10-04); the run stops if it does not.

WHAT CHANGES BETWEEN ARMS, AND ONLY THIS
  own side    the player's own 50/30/20 rate per 82 over t0-1, t0-2, t0-3:
                plain   sum(w_i * rate_i) / sum(w_i)
                games   sum(w_i * GP_i * rate_i) / sum(w_i * GP_i)
              seasons of 10+ games only (forecast_config.MIN_GP; Thomas 2026-10-04: "10 games, as
              tested"); weights renormalised over the seasons he has, so a missing season is not a
              zero (directive 1 detail 4 as tested; not yet settled).
  curve side  the comparable-player curve's level at each age, from 20+ game seasons at ages a,
              a-1, a-2 (aging_curve.MIN_GP; directive 2), renormalised the same way, plain or
              games-weighted. It is used everywhere the curve uses a level (directive 2): the
              recent-rate measure that finds comparable players, the year-to-year changes the walk
              adds, and the comparables' level in the 35%.
Built by aging_level_weights_test.build_curve, imported unchanged, so this test and that one build
the same curve for the same weights.

SETTINGS CARRIED IN, NOT CHOSEN HERE (named so none rides in unnoticed)
  - The 65/35 blend (directive 1), fixed; not re-tuned per arm.
  - The comparables' level is blended with the league average for his position and age at a weight
    of ten (aging_curve.SHRINK_K): directive 1 detail 2 and investigation B are still open, so the
    code's rule stays.
  - Departed players (no NHL row the next season, that season finished before the page) are entered
    at replacement, rate 0. Under games weighting that filled-in season is counted as 82 games, as
    aging_level_weights_test.py version (d) did. That makes the zero weigh more under games
    weighting than under plain. Investigation C covers departures; this test does not vary it.
  - The step to the valuation season (directive 1 detail 3, still open): every arm is scored both
    with the comparables' change from his last season's age to the valuation season and without it,
    so the answer here does not depend on how detail 3 is settled.
  - The rest of the curve is unchanged: the pool rule, the style, ice-time and trend measures, the
    yardstick, the weighting formula. aging_curve.LAMBDA (55/45) does not enter: only the curve's
    changes are read, and the anchor it sets cancels out of them.

ROWS AND SCORES (development pages 2015-2021 only; the 2022-2025 pages are not touched)
  Rows: each skater on each page t0 with a 10-game season among t0-1..t0-3
  (aging_level_weights_test.anchors). Outcome: his rate per 82 in each season he played, t0 to t0+5,
  each weighted by its games. Scores are games-weighted RMSE and MAE on the same rows for every arm.
    start   the valuation season (t0)
    whole   one to five seasons out, each arm's own start and own changes
  Comparisons count 2,000 player resamples (whole careers drawn with replacement). Rows are
  player-pages; the independent units are the players, which is what the resamples draw.

HOW TO RUN (repo root, about ten minutes):
    python 25_TESTS/level_games_weighting_test.py
Writes 30_OUTPUT/level_games_weighting_test_log.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import forecast_config as C
import player_season_table as PST
import skater_forecast as SF
# The recorded curve-weights test's own functions, imported, not copied, so both tests build the
# same rows and the same curves (the 1.3596 reproduction below checks it).
from aging_level_weights_test import anchors, boot_lower, build_curve, curve_paths, wmae, wrmse

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
H = 5
K_OWN = 0.65                       # directive 1's own-versus-comparables blend
W = (0.5, 0.3, 0.2)                # directives 1 and 2
NBOOT = 2000
REPRO_WHOLE_C = 1.3596             # aging_level_weights_test.py v1.0, version (c), whole 1-5 out
# Arms: (own side games-weighted?, curve side games-weighted?)
ARMS = {"plain / plain": (False, False), "games / games": (True, True),
        "games own / plain curve (reference)": (True, False),
        "plain own / games curve (reference)": (False, True)}
MATCHED = ("plain / plain", "games / games")
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def own_rate(d, games):
    """The player's own 50/30/20 rate per 82, plain or games-weighted, over the 10+ game seasons
    he has among t0-1..t0-3 (anchors() stores NaN rate and 0 games for a missing one)."""
    num = np.zeros(len(d)); den = np.zeros(len(d))
    for lag, wt in zip((1, 2, 3), W):
        r = d[f"r{lag}"].to_numpy(float); g = d[f"g{lag}"].to_numpy(float)
        ok = np.isfinite(r)
        ww = np.where(ok, wt * (g if games else 1.0), 0.0)
        num += np.where(ok, r, 0.0) * ww; den += ww
    return np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)


def main():
    C.banner("level_games_weighting_test.py", SCRIPT_VERSION)
    bd, how = PST.birthdate_source()
    log(f"birthdates: {how}")
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    d = anchors(table)
    own = {False: own_rate(d, False), True: own_rate(d, True)}
    # anchors() builds the games-weighted rate itself; ours must equal it, or the arms are mislabelled
    assert np.allclose(own[True], d["own"].to_numpy(), equal_nan=True), "own-rate builder disagrees"
    log(f"rows: {len(d):,} player-pages, {d['career_key'].nunique():,} players, pages {PAGES[0]}-{PAGES[-1]}")

    # ---- the two curves, one per page each: plain and games-weighted 50/30/20 ----------------
    q = table[table["GP"] >= C.MIN_GP]
    curves = {}
    for games in (False, True):
        cn = np.full(len(d), np.nan); paths = np.zeros((len(d), 3 + H + 1))
        n_imp = []
        for t0 in PAGES:
            m = build_curve(path, t0, W, games)
            n_imp.append(m.n_imputed)
            s = q[q["syr"] < t0]
            lp = {pp: float(np.sum(g["WAR_82"] * g["GP"]) / np.sum(g["GP"])) for pp, g in
                  s.assign(pp=np.where(s["pos"] == "D", "D", "F")).groupby("pp")}
            ix, c, pth = curve_paths(d, m, t0, lp)
            cn[ix], paths[ix] = c, pth
        curves[games] = (cn, paths)
        log(f"  built the {'games-weighted' if games else 'plain'} curve on {len(PAGES)} pages "
            f"(departures filled in per page: {min(n_imp):,}-{max(n_imp):,})")

    # ---- outcomes t0 .. t0+5, identical for every arm --------------------------------------
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"))
    gap = d["last_lag"].to_numpy(int)
    ia = np.arange(len(d))
    keys = d["career_key"].to_numpy()
    rows = []
    for h in range(0, H + 1):
        rr = res.reindex(pd.MultiIndex.from_arrays([d["career_key"], d["t0"] + h]))
        ok = (rr["GP"].to_numpy() > 0) & np.isfinite(rr["y"].to_numpy())
        rows.append((h, ok, rr["y"].to_numpy(), rr["GP"].to_numpy()))

    def preds(own_v, cn, paths, step):
        """Start = 65% own + 35% comparables (+ the step from his last age to t0 if `step`);
        each later season adds the curve's change from t0's age."""
        st = K_OWN * own_v + (1 - K_OWN) * cn + (paths[ia, gap] if step else 0.0)
        return {h: st + (paths[ia, gap + h] - paths[ia, gap]) for h in range(0, H + 1)}

    def pooled(pr, hs, mask=None):
        e, w, g = [], [], []
        for h, ok, y, gp in rows:
            if h in hs:
                k = ok if mask is None else ok & mask
                e.append(pr[h][k] - y[k]); w.append(gp[k]); g.append(keys[k])
        return np.concatenate(e), np.concatenate(w), np.concatenate(g)

    errs = {}
    for step in (True, False):
        for an, (og, cg) in ARMS.items():
            pr = preds(own[og], *curves[cg], step)
            errs[(an, step)] = {"start": pooled(pr, {0}), "whole": pooled(pr, set(range(1, H + 1))),
                                "by_h": {h: pooled(pr, {h}) for h in range(1, H + 1)}, "pr": pr}

    # ---- reproduction: the reference arm must give back the recorded figure ----------------
    e, w, _ = errs[("games own / plain curve (reference)", True)]["whole"]
    got = round(wrmse(e, w), 4)
    log(f"\nreproduction: own games / curve plain, with the step, whole 1-5 out = {got:.4f} "
        f"(aging_level_weights_test.py v1.0 version (c), recorded {REPRO_WHOLE_C:.4f})")
    if abs(got - REPRO_WHOLE_C) > 1e-9:
        raise RuntimeError(f"reference arm gives {got:.4f}, recorded {REPRO_WHOLE_C:.4f}: the rows, the "
                           "age table or the curve builder differ from the recorded run; results not read")
    log("  PASS")

    # ---- the table ----------------------------------------------------------------------------
    for step in (True, False):
        log(f"\nRATE PER 82, seasons played, games-weighted; step to the valuation season: "
            f"{'yes' if step else 'no'}")
        log(f"  {'arm (own / curve)':38s}{'start RMSE / MAE':>20s}{'whole 1-5 RMSE / MAE':>24s}")
        for an in ARMS:
            e0, w0, _ = errs[(an, step)]["start"]; ew, ww, _ = errs[(an, step)]["whole"]
            log(f"  {an:38s}{wrmse(e0, w0):11.4f} / {wmae(e0, w0):.4f}{wrmse(ew, ww):15.4f} / {wmae(ew, ww):.4f}")
        log(f"  by season ahead (RMSE):{'':15s}" + "".join(f"{'+' + str(h):>9s}" for h in range(1, H + 1)))
        for an in ARMS:
            log(f"  {an:38s}" + "".join(f"{wrmse(*errs[(an, step)]['by_h'][h][:2]):9.4f}" for h in range(1, H + 1)))

    # ---- resamples: the matched arms against each other, then the references ---------------
    rng = np.random.default_rng(20261004)
    log("\nRESAMPLES (of 2,000, whole careers): how often the first arm's squared error is lower")
    for step in (True, False):
        log(f"  step to the valuation season: {'yes' if step else 'no'}")
        pairs = [("games / games", "plain / plain"),
                 ("games own / plain curve (reference)", "plain / plain"),
                 ("plain own / games curve (reference)", "plain / plain")]
        for a, b in pairs:
            ea0, wa0, ga0 = errs[(a, step)]["start"]; eb0, _, _ = errs[(b, step)]["start"]
            eaw, waw, gaw = errs[(a, step)]["whole"]; ebw, _, _ = errs[(b, step)]["whole"]
            log(f"    {a:38s} vs {b:14s} start {boot_lower(ea0, eb0, wa0, ga0, rng):5d}   "
                f"whole {boot_lower(eaw, ebw, waw, gaw, rng):5d}")

    # ---- where weighting can matter: players with a short trailing season --------------------
    gcols = np.column_stack([np.where(np.isfinite(d[f"r{l}"]), d[f"g{l}"], np.nan) for l in (1, 2, 3)])
    short = np.nanmin(gcols, axis=1) < 41
    log(f"\nBY TRAILING GAMES (step: yes): rows whose shortest counted trailing season is under 41 games "
        f"({int(short.sum()):,} rows) against the rest ({int((~short).sum()):,})")
    log(f"  {'arm':38s}{'short: start / whole':>24s}{'full: start / whole':>24s}   bias, short start")
    for an in MATCHED:
        pr = errs[(an, True)]["pr"]
        out = []
        for mk in (short, ~short):
            e0, w0, _ = pooled(pr, {0}, mk); ew, ww, _ = pooled(pr, set(range(1, H + 1)), mk)
            out.append(f"{wrmse(e0, w0):11.4f} / {wrmse(ew, ww):.4f}")
        e0, w0, _ = pooled(pr, {0}, short)
        log(f"  {an:38s}{out[0]:>24s}{out[1]:>24s}   {np.sum(w0 * e0) / np.sum(w0):+.3f}")

    C.record_inspection("level_games_weighting_test.py", "pages", PAGES,
                        "directive 1 detail 1: plain vs games-weighted 50/30/20, both sides (Thomas 2026-10-04)")
    p = C.out_path("level_games_weighting_test_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
