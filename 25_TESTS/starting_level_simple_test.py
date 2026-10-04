"""starting_level_simple_test.py -- simple trailing weights, then a simple pull, for the starting level.

WHY (2026-10-04, Thomas). xNPV 1's starting level is an eight-term regression on a
trailing total whose weights' decay is chosen from the data on each page
(skater_forecast._fit_decay; 47/32/21 from 2016). Thomas approved 50/30/20 (D33's
wording) and asked for something simpler he can explain:
  1. check that 50/30/20 is the best of the simple three-season weightings;
  2. take the best, and pull it toward a league average or a comparable-player
     average to set the starting level.
TEST ONLY. Nothing in 20_CODE changes and nothing is adopted by running this.

WHAT IT SCORES
    Rows: each skater on each development page t0 (2015-2021; DEV_PAGES only, the
    2022-2025 pages are not touched) with at least one 10-game season among
    t0-1..t0-3 (xNPV 1's own anchor rule), who played in t0.
    Target: his rate per 82 games in t0 (WAR_82), each row weighted by his games
    in t0 -- the target and weight xNPV 1's start line is fitted on.
    Scores: games-weighted RMSE and MAE of the rate. Comparisons count 2,000
    player resamples (whole careers drawn with replacement), same rows each arm.

    Trailing rate for weights (w1, w2, w3) on t0-1, t0-2, t0-3, 10+ game seasons
    only, renormalised over the seasons he has (a missing season is not a zero):
        games-weighted   sum(w_i * GP_i * rate_i) / sum(w_i * GP_i)   [primary]
        plain            sum(w_i * rate_i) / sum(w_i)
    Part 1 scores each weighting raw, and pulled toward the position league
    average with its own best k, so the choice is not an artifact of the pull.

    Part 2, the winning weights: start = k * trailing rate + (1 - k) * target,
    k swept over 0.30-1.00 in steps of 0.05 (one number for all pages), targets:
        league     games-weighted rate of all 10+ game seasons before t0, by position
        league_age the aging curve's league level for his position and last age
                   (aging_curve.AgingModel.glevel, fitted before t0)
        comps      the comparable players' level at his last age, blended with
                   league_age at weight ten (AgingModel.project's compnorm,
                   the curve xNPV 1 uses, fitted before t0; league_age where he
                   has no 20-game profile)
    each with and without the comparables' change from his last age to t0 (the
    aging step xNPV 1's walk does not take for the valuation season).
    Reference: xNPV 1's current fitted start (skater_forecast.XNPV1, start line
    refitted per page exactly as production does) on the same rows.

HOW TO RUN (repo root, about ten minutes):
    python 25_TESTS/starting_level_simple_test.py
Writes 30_OUTPUT/starting_level_simple_test_log.txt and _rows.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
WEIGHTS = {"33/33/33": (1, 1, 1), "40/35/25": (40, 35, 25), "40/40/20": (40, 40, 20),
           "50/25/25": (50, 25, 25), "50/30/20": (50, 30, 20), "50/35/15": (50, 35, 15),
           "60/25/15": (60, 25, 15), "60/30/10": (60, 30, 10), "70/20/10": (70, 20, 10),
           "47/32/21 (fitted, reference)": (1, 0.667, 0.667 ** 2)}
KGRID = np.round(np.arange(0.30, 1.0001, 0.05), 2)
NBOOT = 2000
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def wrmse(e, w):
    return float(np.sqrt(np.sum(w * e ** 2) / np.sum(w)))


def wmae(e, w):
    return float(np.sum(w * np.abs(e)) / np.sum(w))


def build_rows(table):
    """One row per (player, page) with the three trailing seasons and the outcome."""
    q = table[table["GP"] >= C.MIN_GP]
    out = []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        assert iset.latest_season == t0 - 1
        prev = {}
        for lag in (1, 2, 3):
            s = q[q["syr"] == t0 - lag].set_index("career_key")
            prev[lag] = s
        keys = set().union(*[set(prev[l].index) for l in prev])
        res = table[table["syr"] == t0].groupby("career_key").agg(GP=("GP", "sum"), WAR_82=("WAR_82", "first"))
        for k in keys:
            if k not in res.index or not res.loc[k, "GP"] > 0:
                continue
            row = {"career_key": k, "t0": t0, "y": float(res.loc[k, "WAR_82"]), "w": float(res.loc[k, "GP"])}
            last = None
            for lag in (1, 2, 3):
                if k in prev[lag].index:
                    r = prev[lag].loc[k]
                    if isinstance(r, pd.DataFrame):
                        r = r.iloc[0]
                    row[f"r{lag}"], row[f"g{lag}"] = float(r["WAR_82"]), float(r["GP"])
                    if last is None:
                        last = lag
                        row["pos"], row["pkey"] = r["pos"], r["pkey"]
                        row["age_last"] = float(r["age"]) if pd.notna(r["age"]) else np.nan
                        row["last_lag"] = lag
                else:
                    row[f"r{lag}"], row[f"g{lag}"] = np.nan, 0.0
            out.append(row)
    d = pd.DataFrame(out)
    return d[np.isfinite(d["y"])].reset_index(drop=True)


def trailing(d, wts, games=True):
    num = np.zeros(len(d)); den = np.zeros(len(d))
    for lag, w in zip((1, 2, 3), wts):
        r = d[f"r{lag}"].to_numpy(float); g = d[f"g{lag}"].to_numpy(float)
        ok = np.isfinite(r)
        ww = w * (g if games else 1.0) * ok
        num += np.where(ok, r, 0.0) * ww; den += ww
    return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)


def best_k(x, target, y, w):
    errs = [wrmse(k * x + (1 - k) * target - y, w) for k in KGRID]
    i = int(np.argmin(errs))
    return float(KGRID[i]), errs[i], errs


def boot_lower(e_a, e_b, w, groups, rng):
    """Resamples (of NBOOT) in which arm a's weighted squared error is below arm b's."""
    codes, uniq = pd.factorize(groups)
    sa = np.bincount(codes, w * e_a ** 2, len(uniq)); sb = np.bincount(codes, w * e_b ** 2, len(uniq))
    n = len(uniq); lower = 0
    for _ in range(NBOOT):
        ix = rng.integers(0, n, n)
        lower += sa[ix].sum() < sb[ix].sum()
    return lower


def main():
    C.banner("starting_level_simple_test.py", SCRIPT_VERSION)
    bd, how = PST.birthdate_source()
    log(f"birthdates: {how}")
    table = PST.build(birthdate_csv=bd, verbose=False)
    SF.check_age_coverage(SF.war_age_path())
    d = build_rows(table)
    y, w, g = d["y"].to_numpy(float), d["w"].to_numpy(float), d["career_key"].to_numpy()
    rng = np.random.default_rng(20261004)
    log(f"rows: {len(d):,} player-pages, {d['career_key'].nunique():,} players, pages {PAGES[0]}-{PAGES[-1]}; "
        f"target = rate per 82 in the valuation season, weighted by its games")

    # league average by position, from 10+ game seasons before each page
    q = table[table["GP"] >= C.MIN_GP]
    lg = {}
    for t0 in PAGES:
        s = q[q["syr"] < t0]
        for pos, gg in s.groupby("pos"):
            lg[(t0, pos)] = float(np.sum(gg["WAR_82"] * gg["GP"]) / np.sum(gg["GP"]))
    d["league"] = [lg[(t, p)] for t, p in zip(d["t0"], d["pos"])]

    # ---------------- part 1: the weights ---------------------------------------
    log("\n[1] simple three-season weights (games-weighted form), same rows")
    log(f"    {'weights':30s}{'raw RMSE':>10}{'raw MAE':>9}   {'pulled RMSE':>12}{'best k':>8}")
    res = {}
    for name, wts in WEIGHTS.items():
        x = trailing(d, wts)
        e_raw = x - y
        k, r, _ = best_k(x, d["league"].to_numpy(), y, w)
        e_pull = k * x + (1 - k) * d["league"].to_numpy() - y
        res[name] = (x, e_raw, e_pull, k)
        log(f"    {name:30s}{wrmse(e_raw, w):10.4f}{wmae(e_raw, w):9.4f}   {wrmse(e_pull, w):12.4f}{k:8.2f}")
    log("    plain form (no games weighting), pulled RMSE:  " + "  ".join(
        f"{n.split(' ')[0]} {wrmse(best_k(trailing(d, wt, False), d['league'].to_numpy(), y, w)[0] * trailing(d, wt, False) + (1 - best_k(trailing(d, wt, False), d['league'].to_numpy(), y, w)[0]) * d['league'].to_numpy() - y, w):.4f}"
        for n, wt in WEIGHTS.items()))
    simple = [n for n in WEIGHTS if "reference" not in n]
    win = min(simple, key=lambda n: wrmse(res[n][2], w))
    log(f"\n    best simple weighting (pulled RMSE): {win}")
    for n in simple:
        if n != win:
            log(f"      {win} lower than {n:9s} in {boot_lower(res[win][2], res[n][2], w, g, rng):4d} of {NBOOT} resamples (pulled)"
                f", {boot_lower(res[win][1], res[n][1], w, g, rng):4d} raw")
    if win != "50/30/20":
        log(f"      50/30/20 against {win}: 50/30/20 lower in "
            f"{boot_lower(res['50/30/20'][2], res[win][2], w, g, rng)} of {NBOOT} (pulled)")

    # ---------------- part 2: the pull --------------------------------------------
    x = res[win][0]
    log(f"\n[2] the pull, on {win}: start = k x trailing + (1 - k) x target")
    la, cn, step = np.full(len(d), np.nan), np.full(len(d), np.nan), np.zeros(len(d))
    n_comp = 0
    for t0 in PAGES:
        m = SF.imputed_aging_model(str(SF.war_age_path()), t0)
        ix = np.where(d["t0"].to_numpy() == t0)[0]
        for i in ix:
            r = d.iloc[i]
            pos, ck = ("D" if r["pos"] == "D" else "F"), r["career_key"]
            if not np.isfinite(r["age_last"]):
                la[i] = cn[i] = d.at[i, "league"]
                continue
            a = int(r["age_last"])
            la[i] = m.glevel.get((pos, a), d.at[i, "league"])
            cn[i] = la[i]
            gap = int(r["last_lag"])                 # seasons from his last one to t0
            if ck in m.players and a in m.players[ck]["sm"]:
                try:
                    p = m.players[ck]; ss = p["seasons"]
                    idx = next(j for j, s in enumerate(ss) if s["age"] == a)
                    lo = idx if not p["adjacent"].get(a, False) else max(0, idx - 1)
                    tv = SF_profile(m, ss[lo: idx + 1], p["sm"][a], pos)
                    cand, wt = m._weights(tv, pos, a, exclude=ck)
                    if cand is not None and len(cand):
                        cn[i] = m._shrunk(m.Lser[cand, a - m.AMIN], cand, wt, la[i]); n_comp += 1
                    tr = m.project(ck, current_age=a, horizon=gap)
                    lv = dict(zip(tr["age"].astype(int), tr["projected_war_per_82"]))
                    if (a + gap) in lv:
                        step[i] = lv[a + gap] - lv[a]
                        continue
                except (ValueError, KeyError, IndexError, StopIteration):
                    pass
            step[i] = sum(m.gdelta.get((pos, a + j), 0.0) for j in range(gap))
    log(f"    comparable-player average available for {n_comp:,} of {len(d):,} rows (others: league by age)")
    targets = {"league (position)": d["league"].to_numpy(), "league (position, age)": la, "comparables": cn}
    arms = {}
    log(f"    {'target':26s}{'aging to t0':>12}{'best k':>8}{'RMSE':>9}{'MAE':>9}   RMSE at k = 0.45 / 0.55 / 0.65 / 0.75")
    for tn, tgt in targets.items():
        for aged in (False, True):
            xx = x + (step if aged else 0.0); tt = tgt + (step if aged else 0.0)
            k, r, errs = best_k(xx, tt, y, w)
            e = k * xx + (1 - k) * tt - y
            arms[(tn, aged)] = (e, k)
            pick = "  ".join(f"{errs[list(KGRID).index(kk)]:.4f}" for kk in (0.45, 0.55, 0.65, 0.75))
            log(f"    {tn:26s}{('yes' if aged else 'no'):>12}{k:8.2f}{r:9.4f}{wmae(e, w):9.4f}   {pick}")

    # reference: xNPV 1's current fitted start on the same rows
    cur = np.full(len(d), np.nan)
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mm = SF.XNPV1(); mm.before = t0
        mm.decay_ = mm._fit_decay(iset.seasons, t0)
        pairs = mm._training_pairs(iset.seasons, t0, (0,))
        r0 = pairs.dropna(subset=["y_rate"])
        coef = SF._ols(r0[SF.RATE_FEATURES], r0["y_rate"], SF._rate_weight(r0))
        a = SF._anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP], mm.N_SEASONS, mm.decay_)
        a = a[a["t0"] == t0].drop_duplicates("career_key").set_index("career_key")
        ix = np.where(d["t0"].to_numpy() == t0)[0]
        aa = a.reindex(d.loc[ix, "career_key"])
        cur[ix] = SF._apply(coef, aa[SF.RATE_FEATURES], aa["tw_WAR"])
    ok = np.isfinite(cur)
    e_cur = cur - y
    log(f"\n    xNPV 1's current start (8-term line, fitted decay), {ok.sum():,} of {len(d):,} rows: "
        f"RMSE {wrmse(e_cur[ok], w[ok]):.4f}, MAE {wmae(e_cur[ok], w[ok]):.4f}")
    best = min(arms, key=lambda a_: wrmse(arms[a_][0], w))
    eb = arms[best][0]
    log(f"    best simple arm: {best[0]}, aging to t0 {'yes' if best[1] else 'no'}, k = {arms[best][1]:.2f}: "
        f"RMSE {wrmse(eb[ok], w[ok]):.4f} on those rows; current start lower in "
        f"{boot_lower(e_cur[ok], eb[ok], w[ok], g[ok], rng)} of {NBOOT} resamples")
    for (tn, aged), (e, k) in arms.items():
        if (tn, aged) != best:
            log(f"      {best[0]}/{'aged' if best[1] else 'not aged'} lower than {tn}/{'aged' if aged else 'not aged'} in "
                f"{boot_lower(eb, e, w, g, rng)} of {NBOOT}")
    # by trailing tier, best arm against current
    tier = pd.cut(res[win][0], [-99, 0, 1, 2, 3, 99], labels=["below 0", "0-1", "1-2", "2-3", "3+"])
    log("\n    bias (predicted minus actual rate) by trailing rate, best simple arm against current:")
    for t in ["below 0", "0-1", "1-2", "2-3", "3+"]:
        mk = (tier == t) & ok
        if mk.sum():
            log(f"      {t:8s} n {int(mk.sum()):6,d}   simple {np.sum(w[mk] * eb[mk]) / np.sum(w[mk]):+.3f}   "
                f"current {np.sum(w[mk] * e_cur[mk]) / np.sum(w[mk]):+.3f}")
    C.record_inspection("starting_level_simple_test.py", "pages", PAGES,
                        "simple trailing weights and pull for the starting level (Thomas 2026-10-04)")
    out = C.out_path("starting_level_simple_test_log.txt")
    out.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    d.assign(trailing=x, current=cur).to_csv(C.out_path("starting_level_simple_test_rows.csv"), index=False)
    log(f"\nwritten: {out}")


def SF_profile(m, rows, level, pos):
    """The target's standardised profile, exactly as AgingModel.project builds it."""
    import aging_curve as AC
    tv_raw = AC._profile(rows, level)
    mu, sd = m.stats[pos]
    return ((tv_raw - mu) / sd) * np.sqrt(m.fw)


if __name__ == "__main__":
    main()
