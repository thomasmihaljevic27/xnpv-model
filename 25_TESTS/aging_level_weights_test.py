"""aging_level_weights_test.py -- how should the aging curve average a player's recent seasons?

WHY (2026-10-04, Thomas). The comparable-player curve (20_CODE/aging_curve.py) measures each
player's level as the EQUAL average of his rates per 82 in his last two consecutive 20-game
seasons (WIN = 2). Weighting improved the starting level (25_TESTS/starting_level_simple_test.py:
50/30/20 beat equal three-season weights), and the directed starting level
(00_STATE/MODEL_DIRECTIVES.md, entry 1) puts 50/30/20 on the player's own side. Equal weighting in
the curve had never been tested against a weighted average. TEST ONLY: nothing in 20_CODE changes.

WHAT CHANGES, AND ONLY THIS: the curve's level at each age (AgingModel's "sm"), which it uses
three ways -- the recent-rate measure in the matching profile; the year-to-year changes the walk
adds (each comparable's level at a+1 minus at a); and the comparables' level at his age (entry 1's
35%). Versions, over the player's 20-game seasons at ages a, a-1, a-2 (only those he has, weights
renormalised; a missing season is not a zero):
    (a) equal two-season    1/2, 1/2            -- production; must reproduce it exactly
    (b) 60/40 two-season    0.6, 0.4
    (c) 50/30/20            0.5, 0.3, 0.2
    (d) 50/30/20 by games   0.5, 0.3, 0.2, each times that season's games
Everything else in the curve is unchanged: the pool rule (two consecutive 20-game seasons), the
style, ice-time and trend measures, the yardstick rule, the weighting formula, the league weight of
ten. Departed players (no NHL row the next season, that season finished before the page) are
entered as xNPV 1 enters them, a next season at replacement (rate 0, counted as 82 games for (d)),
smoothed by the version's own rule; the league changes are recomputed with them. Version (a) with
this rule must reproduce skater_forecast.imputed_aging_model exactly (asserted on the 2018 page).

HOW EACH VERSION IS SCORED (development pages 2015-2021 only; rows and outcomes as in
starting_level_simple_test.py; rate per 82 in seasons played, games-weighted; 2,000 player
resamples):
    start   entry 1's starting level: 0.65 x his 50/30/20 games-weighted rate + 0.35 x the
            comparables' level at his last age (league weight ten), plus the curve's change from
            his last age to the valuation season; scored in the valuation season.
    aging   one to five seasons out, start held at version (a)'s so only the curve's changes
            differ: predicted rate = start + the curve's change from the valuation age.
    whole   one to five seasons out, each version's own start and own changes.
Fallbacks, identical for each version: no 20-game profile at his last age -> the league-average
changes and level for his position and age; no age -> carried flat. Past the curve's oldest age the
rate is held.

HOW TO RUN (repo root, about fifteen minutes):
    python 25_TESTS/aging_level_weights_test.py
Writes 30_OUTPUT/aging_level_weights_test_log.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
import numpy as np
import pandas as pd

import aging_curve as AC
import forecast_config as C
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
H = 5
K_OWN = 0.65
VERSIONS = {"(a) equal two-season": ((0.5, 0.5), False), "(b) 60/40 two-season": ((0.6, 0.4), False),
            "(c) 50/30/20": ((0.5, 0.3, 0.2), False), "(d) 50/30/20 by games": ((0.5, 0.3, 0.2), True)}
NBOOT = 2000
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def level(byage, a, wts, games):
    num = den = 0.0
    for lag, wt in enumerate(wts):
        s = byage.get(a - lag)
        if s is None:
            continue
        ww = wt * (s["gp"] if games else 1.0)
        num += ww * s["w82"]; den += ww
    return num / den


def build_curve(path, before, wts, games):
    """AgingModel with the level rule replaced, then departures imputed by the same rule."""
    m = AC.AgingModel(path, before=before)
    for p in m.players.values():
        byage = {s["age"]: s for s in p["seasons"]}
        p["sm"] = {a: level(byage, a, wts, games) for a in byage}
    m._build_bank()
    m._build_globals()
    # departures at replacement, copied from skater_forecast.imputed_aging_model with the
    # next level built by this version's rule instead of (rate + 0) / 2
    df = pd.read_csv(path)
    df["syr"] = df["Season"].str.split("-").str[0].astype(int) + 2000
    df = df[df["syr"] < int(before)].copy()
    df["career"] = df["Player"].map(AC.career_key)
    df = df[df["age"].notna()]
    present = set(zip(df["career"], df["age"].astype(int)))
    syr_of = df.groupby(["career", df["age"].astype(int)])["syr"].max().to_dict()
    imputed = {}
    for name, p in m.players.items():
        byage = {s["age"]: s for s in p["seasons"]}
        for s in p["seasons"]:
            a = s["age"]
            if (a + 1) in p["sm"] or (name, a + 1) in present:
                continue
            sy = syr_of.get((name, a))
            if sy is None or sy + 1 >= int(before):
                continue
            b2 = dict(byage); b2[a + 1] = {"w82": 0.0, "gp": 82.0}
            imputed[(name, a)] = level(b2, a + 1, wts, games) - p["sm"][a]
    D = m.Dser.copy()
    by_name = {}
    for (nm, a), dd in imputed.items():
        by_name.setdefault(nm, []).append((a, dd))
    for r, name in enumerate(m.names):
        for a, dd in by_name.get(name, ()):
            assert np.isnan(D[r, a - m.AMIN])
            D[r, a - m.AMIN] = dd
    m.Dser = D
    dn, dc = {}, {}
    for name, p in m.players.items():
        pos, ss, ser = p["pos"], p["seasons"], p["sm"]
        for i, s in enumerate(ss):
            a = s["age"]
            if i + 1 < len(ss) and ss[i + 1]["age"] - a == 1:
                dd = ser[ss[i + 1]["age"]] - ser[a]
            elif (name, a) in imputed:
                dd = imputed[(name, a)]
            else:
                continue
            dn[(pos, a)] = dn.get((pos, a), 0.0) + dd
            dc[(pos, a)] = dc.get((pos, a), 0) + 1
    m.gdelta = {k: dn[k] / dc[k] for k in dn}
    m.n_imputed = len(imputed)
    return m


def wrmse(e, w):
    return float(np.sqrt(np.sum(w * e ** 2) / np.sum(w)))


def wmae(e, w):
    return float(np.sum(w * np.abs(e)) / np.sum(w))


def boot_lower(e_a, e_b, w, groups, rng):
    codes, uniq = pd.factorize(groups)
    sa = np.bincount(codes, w * e_a ** 2, len(uniq)); sb = np.bincount(codes, w * e_b ** 2, len(uniq))
    n = len(uniq)
    return int(sum(sa[ix].sum() < sb[ix].sum() for ix in (rng.integers(0, n, n) for _ in range(NBOOT))))


def anchors(table):
    """Each player with a 10-game season among t0-1..t0-3 on each page: his three seasons, last age."""
    q = table[table["GP"] >= C.MIN_GP]
    out = []
    for t0 in PAGES:
        prev = {lag: q[q["syr"] == t0 - lag].drop_duplicates("career_key").set_index("career_key")
                for lag in (1, 2, 3)}
        for k in set().union(*[set(v.index) for v in prev.values()]):
            row = {"career_key": k, "t0": t0}
            for lag in (1, 2, 3):
                if k in prev[lag].index:
                    r = prev[lag].loc[k]
                    row[f"r{lag}"], row[f"g{lag}"] = float(r["WAR_82"]), float(r["GP"])
                    if "last_lag" not in row:
                        row.update(last_lag=lag, pos=("D" if r["pos"] == "D" else "F"),
                                   age_last=float(r["age"]) if pd.notna(r["age"]) else np.nan)
                else:
                    row[f"r{lag}"], row[f"g{lag}"] = np.nan, 0.0
            out.append(row)
    d = pd.DataFrame(out)
    num = sum(np.where(np.isfinite(d[f"r{l}"]), d[f"r{l}"], 0) * w * d[f"g{l}"] for l, w in ((1, .5), (2, .3), (3, .2)))
    den = sum(w * d[f"g{l}"] * np.isfinite(d[f"r{l}"]) for l, w in ((1, .5), (2, .3), (3, .2)))
    d["own"] = num / den
    return d.reset_index(drop=True)


def curve_paths(d, m, t0, league_pos):
    """For each anchor row on page t0: the comparables' level at his last age and his level path
    (relative, from the last age) for steps 0 .. gap + H."""
    ix = np.where(d["t0"].to_numpy() == t0)[0]
    cn = np.full(len(ix), np.nan); paths = np.zeros((len(ix), 3 + H + 1))
    for j, i in enumerate(ix):
        r = d.iloc[i]; pos, ck = r["pos"], r["career_key"]
        if not np.isfinite(r["age_last"]):
            cn[j] = league_pos[pos]
            continue                                   # no age: carried flat
        a = int(r["age_last"]); n = int(r["last_lag"]) + H
        cn[j] = m.glevel.get((pos, a), league_pos[pos])
        got = False
        if ck in m.players and a in m.players[ck]["sm"]:
            try:
                p = m.players[ck]; ss = p["seasons"]
                idx = next(q for q, s in enumerate(ss) if s["age"] == a)
                lo = idx if not p["adjacent"].get(a, False) else max(0, idx - 1)
                mu, sd = m.stats[p["pos"]]
                tv = ((AC._profile(ss[lo: idx + 1], p["sm"][a]) - mu) / sd) * np.sqrt(m.fw)
                cand, wt = m._weights(tv, p["pos"], a, exclude=ck)
                if cand is not None and len(cand):
                    cn[j] = m._shrunk(m.Lser[cand, a - m.AMIN], cand, wt, cn[j])
                tr = m.project(ck, current_age=a, horizon=n)
                lv = dict(zip(tr["age"].astype(int), tr["projected_war_per_82"]))
                base, last = lv[a], 0.0
                for st in range(n + 1):
                    if (a + st) in lv:
                        last = lv[a + st] - base
                    paths[j, st] = last                 # past the curve: held
                got = True
            except (ValueError, KeyError, IndexError, StopIteration):
                got = False
        if not got:
            c = 0.0
            for st in range(n + 1):
                paths[j, st] = c
                c += m.gdelta.get((pos, a + st), 0.0)
    return ix, cn, paths


def main():
    C.banner("aging_level_weights_test.py", SCRIPT_VERSION)
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    d = anchors(table)
    log(f"anchor rows: {len(d):,} player-pages, {d['career_key'].nunique():,} players, pages {PAGES[0]}-{PAGES[-1]}")

    # guard: version (a) reproduces xNPV 1's curve exactly
    ref = SF.imputed_aging_model(path, 2018)
    mine = build_curve(path, 2018, *VERSIONS["(a) equal two-season"])
    dD = np.nanmax(np.abs(np.nan_to_num(ref.Dser, nan=9e9) - np.nan_to_num(mine.Dser, nan=9e9)))
    dL = np.nanmax(np.abs(np.nan_to_num(ref.Lser, nan=9e9) - np.nan_to_num(mine.Lser, nan=9e9)))
    dg = max(abs(ref.gdelta[k] - mine.gdelta[k]) for k in ref.gdelta)
    assert set(ref.gdelta) == set(mine.gdelta) and max(dD, dL, dg) < 1e-12 and ref.h == mine.h, (dD, dL, dg)
    log(f"guard: version (a) reproduces xNPV 1's curve on the 2018 page (largest gap {max(dD, dL, dg):.1e}, "
        f"{mine.n_imputed:,} departures imputed)")

    q = table[table["GP"] >= C.MIN_GP]
    out = {}
    for vn, (wts, games) in VERSIONS.items():
        cn = np.full(len(d), np.nan); paths = np.zeros((len(d), 3 + H + 1))
        for t0 in PAGES:
            m = build_curve(path, t0, wts, games)
            s = q[q["syr"] < t0]
            lp = {pp: float(np.sum(g["WAR_82"] * g["GP"]) / np.sum(g["GP"])) for pp, g in
                  s.assign(pp=np.where(s["pos"] == "D", "D", "F")).groupby("pp")}
            ix, c, pth = curve_paths(d, m, t0, lp)
            cn[ix], paths[ix] = c, pth
        out[vn] = (cn, paths)
        log(f"  built {vn}")

    # outcomes
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"))
    gap = d["last_lag"].to_numpy(int)
    rows = []
    for h in range(0, H + 1):
        ix = pd.MultiIndex.from_arrays([d["career_key"], d["t0"] + h])
        rr = res.reindex(ix)
        ok = (rr["GP"].to_numpy() > 0) & np.isfinite(rr["y"].to_numpy())
        rows.append((h, ok, rr["y"].to_numpy(), rr["GP"].to_numpy()))
    rng = np.random.default_rng(20261004)
    ia = np.arange(len(d))
    base_cn, base_paths = out["(a) equal two-season"]
    start_a = K_OWN * d["own"].to_numpy() + (1 - K_OWN) * base_cn + base_paths[ia, gap]

    def preds(cn, paths, start_override=None):
        st = K_OWN * d["own"].to_numpy() + (1 - K_OWN) * cn + paths[ia, gap]
        s0 = st if start_override is None else start_override
        return {h: s0 + (paths[ia, gap + h] - paths[ia, gap]) for h in range(0, H + 1)}

    def pooled(pr, hs):
        e, w, g = [], [], []
        for h, ok, y, gp in rows:
            if h in hs:
                e.append(pr[h][ok] - y[ok]); w.append(gp[ok]); g.append(d["career_key"].to_numpy()[ok])
        return np.concatenate(e), np.concatenate(w), np.concatenate(g)

    log("\nRMSE / MAE of the rate per 82, seasons played, games-weighted")
    log(f"  {'version':24s}{'start (valuation season)':>28s}{'aging only, 1-5 out':>24s}{'whole, 1-5 out':>20s}")
    store = {}
    for vn, (cn, paths) in out.items():
        p_own = preds(cn, paths); p_ag = preds(cn, paths, start_a)
        e0, w0, g0 = pooled(p_own, {0}); ea, wa, ga = pooled(p_ag, set(range(1, H + 1)))
        ew, ww, gw = pooled(p_own, set(range(1, H + 1)))
        store[vn] = (e0, ea, ew)
        log(f"  {vn:24s}{wrmse(e0, w0):14.4f} / {wmae(e0, w0):.4f}{wrmse(ea, wa):12.4f} / {wmae(ea, wa):.4f}"
            f"{wrmse(ew, ww):10.4f} / {wmae(ew, ww):.4f}")
    log("\n  by season ahead, aging only (RMSE):  " + "   ".join(f"h{h}" for h in range(1, H + 1)))
    for vn, (cn, paths) in out.items():
        p_ag = preds(cn, paths, start_a)
        log(f"  {vn:24s}" + "  ".join(f"{wrmse(*[x for x in pooled(p_ag, {h})][:2]):.4f}" for h in range(1, H + 1)))
    log("\n  resamples (of 2,000) in which each version's squared error is lower than (a)'s:")
    for vn in VERSIONS:
        if vn.startswith("(a)"):
            continue
        a0, aa, aw = store["(a) equal two-season"]; v0, va, vw = store[vn]
        _, w0, g0 = pooled(preds(*out[vn]), {0}); _, wa, ga = pooled(preds(*out[vn], start_a), set(range(1, H + 1)))
        _, ww, gw = pooled(preds(*out[vn]), set(range(1, H + 1)))
        log(f"  {vn:24s} start {boot_lower(v0, a0, w0, g0, rng):5d}   aging {boot_lower(va, aa, wa, ga, rng):5d}"
            f"   whole {boot_lower(vw, aw, ww, gw, rng):5d}")
    # 3+ players, aging-only bias five seasons out
    tier = d["own"].to_numpy() >= 3
    log("\n  bias five seasons out (predicted minus actual), aging only: all players / own rate 3+")
    for vn, (cn, paths) in out.items():
        p_ag = preds(cn, paths, start_a)
        h, ok, y, gp = rows[H]
        e = p_ag[H] - y
        log(f"  {vn:24s}{np.sum(gp[ok] * e[ok]) / np.sum(gp[ok]):+.3f} / "
            f"{np.sum(gp[ok & tier] * e[ok & tier]) / np.sum(gp[ok & tier]):+.3f}  (n {int((ok & tier).sum())})")
    C.record_inspection("aging_level_weights_test.py", "pages", PAGES,
                        "aging curve level weighting: equal two-season vs weighted (Thomas 2026-10-04)")
    p = C.out_path("aging_level_weights_test_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
