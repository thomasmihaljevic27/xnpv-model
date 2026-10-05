"""aging_abc_followup.py -- the adopted A/C changes together, and the thin-history fix on the level only.

WHY (Thomas, 2026-10-05, on aging_investigations_abc.py v1.0). Adopted, each scored alone: A1 (a
yardstick for forwards and one for defencemen), C2 (a player absent one season who returns later is
not filled in as departed), C6 (the filled-in departure season counts as his own last season's games,
not 82). CLAUDE.md: score parts alone AND in combination before crediting the whole. And C5 (a
comparables pool without the two-consecutive-20-game-season requirement, for players with one or
two counted seasons) cut the one-season start bias from +0.166 to +0.104 but worsened the two-season
walk, because it changed both the comparables' LEVEL and the WALK. This run tries it on the level
only. TEST ONLY: nothing in 20_CODE changes and nothing is adopted by running it.

VERSIONS (each scored against the build; the two C5 versions also against the combination)
    A1, C2, C6        alone, as in v1.0 (they must reproduce v1.0's figures: guard)
    A1+C2+C6          the combination
    C5 level only     thin histories (1-2 counted seasons): the comparables' level from the relaxed
                      pool, the walk from the baseline curve; everyone else unchanged
    combo + C5 level  the same on top of the combination (relaxed pool built with C2 and C6, its own
                      per-position yardstick)
    combo + C5 full   the relaxed pool for level and walk on top of the combination (v1.0's C5,
                      for comparison)
Built with aging_investigations_abc.py's curve_variant / RelaxedAgingModel / yardsticks /
weights_by_position, imported unchanged; every rate comes from production's XNPV1._rate / _path.
Rows, scores and resamples as in v1.0 (40,510 player-seasons; 2,000 career resamples).

HOW TO RUN (repo root, laptop; needs the contract export; about 15-25 minutes):
    python 25_TESTS/aging_abc_followup.py
Writes 30_OUTPUT/aging_abc_followup_log.txt.
"""
import copy
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF
from aging_investigations_abc import (boot_lower, curve_variant, weights_by_position, wrmse,
                                      yardsticks)

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
# aging_investigations_abc.py v1.0, laptop 2026-10-05: start, whole, season-WAR RMSE
RECORDED = {"base": (1.1506, 1.3598, 0.8093), "A1": (1.1505, 1.3598, 0.8093),
            "C2": (1.1507, 1.3588, 0.8089), "C6": (1.1506, 1.3596, 0.8092)}
ARMS = ["A1", "C2", "C6", "A1+C2+C6", "C5 level only", "combo + C5 level", "combo + C5 full"]
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


def with_a1(curve):
    """A1 on a curve: its own per-position yardsticks, from its own pool."""
    curve._weights = types.MethodType(weights_by_position(yardsticks(curve, by_position=True)), curve)
    return curve


def main():
    C.banner("aging_abc_followup.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"))
    combo_kw = dict(returners_filled=False, gp_rule="own")

    frames = []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        base_curve = mod.curve_
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        thin_keys = set(pa.index[pa["n_seasons"].to_numpy(float) <= 2])

        def run(curve, level_curve=None):
            """Rates with `curve` for the walk; for thin histories, the comparables' level from
            `level_curve` (a second model copy, so the two path caches never mix)."""
            mod.curve_ = curve; mod._paths = {}
            if level_curve is not None:
                twin = copy.copy(mod); twin.curve_ = level_curve; twin._paths = {}
                orig = SF.XNPV1._path

                def path_level(self, key, pos, age_last, gap):
                    cn, p_ = orig(self, key, pos, age_last, gap)
                    if key in thin_keys:
                        cn = orig(twin, key, pos, age_last, gap)[0]
                    return cn, p_
                mod._path = types.MethodType(path_level, mod)
            r = {h: mod._rate(pa, h) for h in HS}
            if level_curve is not None:
                del mod._path
            mod.curve_ = base_curve; mod._paths = {}
            return r

        out = {"base": run(base_curve)}
        out["A1"] = run(with_a1(curve_variant(path, t0)))
        out["C2"] = run(curve_variant(path, t0, returners_filled=False))
        out["C6"] = run(curve_variant(path, t0, gp_rule="own"))
        combo = with_a1(curve_variant(path, t0, **combo_kw))
        out["A1+C2+C6"] = run(combo)
        out["C5 level only"] = run(base_curve, level_curve=curve_variant(path, t0, relaxed=True))
        relaxed_combo = with_a1(curve_variant(path, t0, relaxed=True, **combo_kw))
        out["combo + C5 level"] = run(combo, level_curve=relaxed_combo)
        full = run(relaxed_combo)
        thin = np.array([k in thin_keys for k in pa.index])
        out["combo + C5 full"] = {h: np.where(thin, full[h], out["A1+C2+C6"][h]) for h in HS}

        rows = []
        for h in HS:
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(pa.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            d = pd.DataFrame({"career_key": pa.index, "h": h, "share": ph["gp_share"].to_numpy(),
                              "p": ph["p_play"].to_numpy(), "gp": gp, "y82": rr["y"].to_numpy(),
                              "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                              "n_seasons": pa["n_seasons"].to_numpy(float), "age": pa["age"].to_numpy(float)})
            for arm, r in out.items():
                d[f"r|{arm}"] = r[h]
            rows.append(d)
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players, {len(thin_keys):,} with one or two counted seasons")

    D = pd.concat(frames, ignore_index=True)
    arms = ["base"] + ARMS
    g = D["career_key"].to_numpy()
    played = ((D["gp"] > 0) & np.isfinite(D["y82"])).to_numpy()
    w = np.where(played, D["gp"], 0.0)
    hh = D["h"].to_numpy(); h0 = hh == 0; h15 = hh > 0
    L = {}
    for arm in arms:
        e = (D[f"r|{arm}"] - D["y82"]).to_numpy()
        ew = (D["p"] * D[f"r|{arm}"] * D["share"] - D["war_act"]).to_numpy()
        L[arm] = {"e": np.where(played, e, 0.0), "start_sq": np.where(played & h0, w * e ** 2, 0.0),
                  "whole_sq": np.where(played & h15, w * e ** 2, 0.0), "war_sq": ew ** 2, "war_abs": np.abs(ew)}

    def score(arm, m=None):
        m = np.ones(len(D), bool) if m is None else m
        s0 = played & h0 & m; s1 = played & h15 & m; e = L[arm]["e"]
        return {"start": wrmse(e[s0], w[s0]), "bias0": float(np.sum(w[s0] * e[s0]) / np.sum(w[s0])),
                "whole": wrmse(e[s1], w[s1]), "war_rmse": float(np.sqrt(L[arm]["war_sq"][m].mean())),
                "war_mae": float(L[arm]["war_abs"][m].mean())}

    log(f"\nreproduction of aging_investigations_abc.py v1.0 (start / whole / season WAR), {len(D):,} rows:")
    for arm, rec in RECORDED.items():
        s = score(arm); got = (round(s["start"], 4), round(s["whole"], 4), round(s["war_rmse"], 4))
        ok = all(abs(x - y) < 1e-9 for x, y in zip(got, rec)) and len(D) == 40510
        log(f"  {arm:6s} {got[0]:.4f} / {got[1]:.4f} / {got[2]:.4f}   recorded {rec[0]:.4f} / {rec[1]:.4f} / {rec[2]:.4f}"
            f"   {'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"{arm} does not reproduce v1.0; results not read")

    rng = np.random.default_rng(20261005)
    log("\nALL ROWS. 'lower in' = resamples (of 2,000 careers) in which the version's summed squared error is lower")
    log(f"  {'version':20s}{'start':>8s}{'whole':>8s}{'WAR RMSE':>10s}{'WAR MAE':>9s}   vs the build: start / whole / WAR")
    for arm in arms:
        s = score(arm)
        tail = "" if arm == "base" else "   " + " / ".join(
            f"{boot_lower(L[arm][k], L['base'][k], g, rng):5d}" for k in ("start_sq", "whole_sq", "war_sq"))
        log(f"  {arm:20s}{s['start']:8.4f}{s['whole']:8.4f}{s['war_rmse']:10.4f}{s['war_mae']:9.4f}{tail}")
    log("  against the combination (A1+C2+C6):")
    for arm in ("combo + C5 level", "combo + C5 full"):
        log(f"    {arm:18s}" + " / ".join(f"{boot_lower(L[arm][k], L['A1+C2+C6'][k], g, rng):5d}"
                                         for k in ("start_sq", "whole_sq", "war_sq")))

    log("\nBY SEASON AHEAD, rate per 82 RMSE (seasons played)")
    log(f"  {'version':20s}" + "".join(f"{'+' + str(h):>8s}" for h in HS))
    for arm in arms:
        e = L[arm]["e"]
        log(f"  {arm:20s}" + "".join(f"{wrmse(e[played & (hh == h)], w[played & (hh == h)]):8.4f}" for h in HS))

    ns = D["n_seasons"].to_numpy()
    log("\nBY SEASONS COUNTED: start RMSE / start bias / whole RMSE / season-WAR RMSE")
    log(f"  {'version':20s}" + "".join(f"{f'{k} season' + ('s' if k > 1 else ''):>36s}" for k in (1, 2, 3)))
    for arm in arms:
        cells = []
        for k in (1, 2, 3):
            s = score(arm, ns == k)
            cells.append(f"{s['start']:8.4f} {s['bias0']:+7.3f} {s['whole']:8.4f} {s['war_rmse']:8.4f}")
        log(f"  {arm:20s}" + "".join(f"{c:>36s}" for c in cells))

    age = D["age"].to_numpy()
    bands = (("under 22", age < 22), ("22-34", (age >= 22) & (age < 35)), ("35+", age >= 35))
    log("\nBY AGE AT THE VALUATION SEASON: whole RMSE")
    log(f"  {'version':20s}" + "".join(f"{n:>10s}" for n, _ in bands))
    for arm in arms:
        log(f"  {arm:20s}" + "".join(f"{score(arm, m)['whole']:10.4f}" for _, m in bands))

    C.record_inspection("aging_abc_followup.py", "pages", PAGES,
                        "A1+C2+C6 together; C5 on the comparables' level only (Thomas 2026-10-05)")
    p = C.out_path("aging_abc_followup_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
