"""thin_history_check.py -- does the directed start mis-forecast players with fewer than three seasons?

WHY (2026-10-05, Thomas; MODEL_DIRECTIVES.md, plan of record step 1, directive 1 detail 4). The
directed start is 65% x the player's own games-weighted 50/30/20 rate per 82 + 35% x his comparable
players' level, aged to the valuation season (details 1 and 3, settled 2026-10-04c). Where he has
fewer than three counted seasons (10+ games) among t0-1..t0-3, the weights are rescaled over the
seasons he has: a missing season is not a zero, and one season stands alone at 65% however few
games it holds. On the development pages 1,881 of 6,916 rows (27%) have one counted season (median
29 games). level_games_weighting_test.py found the start runs HIGH (+0.110 per 82) for rows whose
shortest counted season is under 41 games, a group that mixes thin histories with three-season
players who had one short year. Thomas: check before settling detail 4.
DIAGNOSTIC ONLY: nothing in 20_CODE changes, nothing is adopted, and no rule is proposed by it.

THE START SCORED (the directed design, every setting as settled or as carried by the earlier tests)
    own     games-weighted 50/30/20 over 10+ game seasons in t0-1..t0-3, rescaled over those he has
    comps   the games-weighted comparable-player curve's level at his last counted age, blended with
            the league average at weight ten (aging_curve.SHRINK_K; detail 2 / investigation B open)
    step    the curve's change from his last counted age to t0 (detail 3)
    start = 0.65 x own + 0.35 x comps + step
  Built with aging_level_weights_test.anchors / build_curve / curve_paths, as
  level_games_weighting_test.py v1.0's "games / games" arm; the run stops unless that arm's recorded
  figures come back (start 1.1506, whole 1-5 out 1.3598, laptop 2026-10-04).

WHAT IT REPORTS, for each group (rows, players; outcome = his rate per 82 in seasons played,
weighted by those games; 2,000 career resamples):
    start RMSE and bias (predicted minus actual: positive = the start runs high), with the bias's
    95% range over career resamples; the same bias one to five seasons out
    the bias if the start used his own rate alone (k = 1) and the comparables alone (k = 0), each
    with the step, to show which side runs high
    DESCRIPTIVE ONLY: the own share k (0.30-1.00 by 0.05) that would have fitted the group best on
    these same scored pages, and its RMSE beside the 65% one. This is a size, not a candidate: a
    share that varies by group would be a new setting, and that is Thomas's decision.
  Groups:
    (a) seasons counted: 1, 2, 3
    (b) one-season rows by that season's games: 10-19, 20-39, 40-81, 82 (a full season, as the
        source can carry up to 85 games for a traded player: 82+)
    (c) total counted trailing games: under 41, 41-81, 82-163, 164 and over
    (d) seasons since his last counted one (1 = last season; 2 or 3 = he missed the most recent),
        where the step covers that many years of aging

HOW TO RUN (repo root, about five minutes):
    python 25_TESTS/thin_history_check.py
Writes 30_OUTPUT/thin_history_check_log.txt.
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
from aging_level_weights_test import anchors, build_curve, curve_paths, wrmse

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
H = 5
K_OWN = 0.65
W = (0.5, 0.3, 0.2)
NBOOT = 2000
KGRID = np.round(np.arange(0.30, 1.0001, 0.05), 2)
# level_games_weighting_test.py v1.0, "games / games" with the step, laptop 2026-10-04
REPRO_START, REPRO_WHOLE = 1.1506, 1.3598
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def wbias(e, w):
    return float(np.sum(w * e) / np.sum(w))


def bias_range(e, w, g, rng):
    """95% range of the games-weighted bias over NBOOT resamples of whole careers."""
    codes, uniq = pd.factorize(g)
    se = np.bincount(codes, w * e, len(uniq)); sw = np.bincount(codes, w, len(uniq))
    n = len(uniq)
    b = [se[ix].sum() / sw[ix].sum() for ix in (rng.integers(0, n, n) for _ in range(NBOOT))]
    return np.percentile(b, [2.5, 97.5])


def main():
    C.banner("thin_history_check.py", SCRIPT_VERSION)
    bd, how = PST.birthdate_source()
    log(f"birthdates: {how}")
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    d = anchors(table)                       # d["own"] is the games-weighted 50/30/20 rate
    log(f"rows: {len(d):,} player-pages, {d['career_key'].nunique():,} players, pages {PAGES[0]}-{PAGES[-1]}")

    q = table[table["GP"] >= C.MIN_GP]
    cn = np.full(len(d), np.nan); paths = np.zeros((len(d), 3 + H + 1))
    for t0 in PAGES:
        m = build_curve(path, t0, W, True)   # games-weighted curve (directive 2 as changed 2026-10-04c)
        s = q[q["syr"] < t0]
        lp = {pp: float(np.sum(g["WAR_82"] * g["GP"]) / np.sum(g["GP"])) for pp, g in
              s.assign(pp=np.where(s["pos"] == "D", "D", "F")).groupby("pp")}
        ix, c, pth = curve_paths(d, m, t0, lp)
        cn[ix], paths[ix] = c, pth

    ia = np.arange(len(d)); gap = d["last_lag"].to_numpy(int); own = d["own"].to_numpy(float)
    step = paths[ia, gap]

    def path_from(start):
        return {h: start + (paths[ia, gap + h] - paths[ia, gap]) for h in range(0, H + 1)}

    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"))
    rows = []
    for h in range(0, H + 1):
        rr = res.reindex(pd.MultiIndex.from_arrays([d["career_key"], d["t0"] + h]))
        ok = (rr["GP"].to_numpy() > 0) & np.isfinite(rr["y"].to_numpy())
        rows.append((h, ok, rr["y"].to_numpy(), rr["GP"].to_numpy()))
    keys = d["career_key"].to_numpy()

    def pooled(pr, hs, mask):
        e, w, g = [], [], []
        for h, ok, y, gp in rows:
            if h in hs:
                k = ok & mask
                e.append(pr[h][k] - y[k]); w.append(gp[k]); g.append(keys[k])
        return np.concatenate(e), np.concatenate(w), np.concatenate(g)

    allrows = np.ones(len(d), bool)
    directed = path_from(K_OWN * own + (1 - K_OWN) * cn + step)

    # ---- reproduction ------------------------------------------------------------------------
    e0, w0, _ = pooled(directed, {0}, allrows); ew, ww, _ = pooled(directed, set(range(1, H + 1)), allrows)
    got = (round(wrmse(e0, w0), 4), round(wrmse(ew, ww), 4))
    log(f"\nreproduction: directed start {got[0]:.4f}, whole 1-5 out {got[1]:.4f} "
        f"(level_games_weighting_test.py v1.0 games / games with the step: {REPRO_START:.4f}, {REPRO_WHOLE:.4f})")
    if abs(got[0] - REPRO_START) > 1e-9 or abs(got[1] - REPRO_WHOLE) > 1e-9:
        raise RuntimeError("the directed start does not reproduce the recorded figures; results not read")
    log("  PASS")

    # ---- groups ------------------------------------------------------------------------------
    nseas = sum(np.isfinite(d[f"r{l}"]).astype(int) for l in (1, 2, 3)).to_numpy()
    gtot = sum(d[f"g{l}"] for l in (1, 2, 3)).to_numpy(float)
    groups = [("all rows", allrows)]
    groups += [(f"(a) {k} season{'s' if k > 1 else ''} counted", nseas == k) for k in (1, 2, 3)]
    groups += [("(b) one season, 10-19 games", (nseas == 1) & (gtot < 20)),
               ("(b) one season, 20-39 games", (nseas == 1) & (gtot >= 20) & (gtot < 40)),
               ("(b) one season, 40-81 games", (nseas == 1) & (gtot >= 40) & (gtot < 82)),
               ("(b) one season, 82+ games", (nseas == 1) & (gtot >= 82))]
    groups += [("(c) trailing games under 41", gtot < 41),
               ("(c) trailing games 41-81", (gtot >= 41) & (gtot < 82)),
               ("(c) trailing games 82-163", (gtot >= 82) & (gtot < 164)),
               ("(c) trailing games 164+", gtot >= 164)]
    groups += [(f"(d) last counted season t0-{k}", gap == k) for k in (1, 2, 3)]

    own_only = path_from(own + step)
    comp_only = path_from(cn + step)
    rng = np.random.default_rng(20261005)
    log("\nTHE DIRECTED START (65% own + 35% comparables, aged), rate per 82, games-weighted")
    log("  bias = predicted minus actual (positive: the start runs high); range = 95% over career resamples")
    log(f"  {'group':32s}{'rows':>7s}{'players':>9s}{'start RMSE':>12s}{'start bias':>12s}{'95% range':>18s}"
        f"{'bias 1-5 out':>14s}")
    for name, mk in groups:
        e0, w0, g0 = pooled(directed, {0}, mk)
        if len(e0) == 0:
            log(f"  {name:32s}  no scored rows"); continue
        ew, ww, _ = pooled(directed, set(range(1, H + 1)), mk)
        lo, hi = bias_range(e0, w0, g0, rng)
        log(f"  {name:32s}{len(e0):7,d}{len(np.unique(g0)):9,d}{wrmse(e0, w0):12.4f}{wbias(e0, w0):+12.3f}"
            f"{f'[{lo:+.3f}, {hi:+.3f}]':>18s}{wbias(ew, ww) if len(ew) else float('nan'):+14.3f}")

    log("\nWHICH SIDE RUNS HIGH: start bias with the own rate alone, the comparables alone, and the 65/35 blend")
    log("  DESCRIPTIVE ONLY: best own share on these scored pages, and its RMSE beside 65%'s (not a candidate)")
    log(f"  {'group':32s}{'own alone':>11s}{'comps alone':>13s}{'65/35':>9s}{'best k':>9s}{'RMSE at k':>11s}{'at 0.65':>9s}")
    for name, mk in groups:
        e0, w0, _ = pooled(directed, {0}, mk)
        if len(e0) == 0:
            continue
        eo, wo, _ = pooled(own_only, {0}, mk); ec, wc, _ = pooled(comp_only, {0}, mk)
        sc = {}
        for k in KGRID:
            ek, wk, _ = pooled(path_from(k * own + (1 - k) * cn + step), {0}, mk)
            sc[float(k)] = wrmse(ek, wk)
        kb = min(sc, key=sc.get)
        log(f"  {name:32s}{wbias(eo, wo):+11.3f}{wbias(ec, wc):+13.3f}{wbias(e0, w0):+9.3f}{kb:9.2f}"
            f"{sc[kb]:11.4f}{sc[0.65]:9.4f}")

    C.record_inspection("thin_history_check.py", "pages", PAGES,
                        "directive 1 detail 4: directed start by seasons counted and trailing games (Thomas 2026-10-05)")
    p = C.out_path("thin_history_check_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
