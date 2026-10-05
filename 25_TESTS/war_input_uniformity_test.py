"""war_input_uniformity_test.py -- one per-82 rate wherever a player's WAR enters, or the trailing total?

WHY (2026-10-05, Thomas; plan of record step 1, before the build). Under directive 1 the start reads
the player's games-weighted 50/30/20 rate per 82. The two other equations that read a player's WAR,
the games share and the chance of playing, read his trailing WAR TOTAL instead (skater_forecast:
GP_FEATURES' tw_WAR and tw_hi1; participation_model's `level`). That choice was inherited from the
rebuild and never tested against a rate. Thomas: "any time a players WAR is being considered in a
calculation, I want them to be as uniformly inputted as possible. Test first, sure, but I will lean
to have things as uniform as possible when possible." This test scores the two inputs.
TEST ONLY: nothing in 20_CODE changes and nothing is adopted by running it.

WHAT CHANGES BETWEEN ARMS, AND ONLY THIS: the player level the two equations read.
    T   trailing WAR total, plain 50/30/20 over his 10+ game seasons in t0-1..t0-3, rescaled over
        the seasons he has (today's input with the fitted decay removed, as directed)
    R   his own rate per 82, games-weighted 50/30/20 over the same seasons (directive 1's own side;
        the uniform input)
  The games-share equation also carries a term for the level above 1.0 (today: the total above one
  win). Its cut-off was set on the total's scale; on the rate's scale 1.0 per 82 picks out different
  players, and nobody has chosen a value for it. So each input is scored with the term (cut-off 1.0
  in its own units, a carried setting) and without it:  T+h, T, R+h, R. The chance of playing has no
  such term, so it has two arms, T and R.

EVERYTHING ELSE AS TODAY'S CODE FITS IT, per development page t0 (2015-2021), on seasons readable on
1 July of t0 (information_set.build) and pairs whose outcome season finished before t0:
    games share   skater_forecast._ols on [trailing games share, defence, experience, age - 27,
                  level (, level above 1.0)], one line per season ahead, prediction clipped to
                  0.05-1.0 (skater_forecast.XNPV1.predict's rule)
    chance of     participation_model.ParticipationModel(contracts, exclude=("contract_unknown",),
    playing       contract_state="observable"), xNPV 1's settings; the event is one NHL game or more
                  (forecast_config.PARTICIPATION_GP = 1)
  The trailing games share is plain 50/30/20 in every arm (a share already counts games; it is not
  WAR). Rule 1 (Thomas, 2026-10-05): the aging walk is the tested one; it enters only the season-WAR
  score below, identically in every arm.

SCORES (seasons ahead 0-5, outcome seasons through the last complete one in the table; the same
rows for every arm; 2,000 career resamples):
    games share   RMSE of the share, seasons he appeared in (as the line is fitted)
    playing       log loss and Brier score of the chance of playing, every row
    season WAR    expected WAR = chance of playing x rate per 82 x games share, against his actual
                  season WAR (0 when he did not play), RMSE and MAE. The rate per 82 is the directed
                  start and walk (games-weighted both sides, 65/35, with the step), identical in
                  every arm, built as thin_history_check.py builds it; it must reproduce that test's
                  recorded start 1.1506 and whole 1.3598 first.
  Broken out by seasons counted (1, 2, 3), where a short season's noisy rate could hurt a rate input.

GUARD: this script's trailing builder, given today's geometric weights (1, d, d^2), must give the same
trailing total, games share, age and experience as skater_forecast._anchors on the 2018 page's seasons.

HOW TO RUN (repo root, laptop; needs the contract export as CSV in SOURCE_DIR):
    python 25_TESTS/war_input_uniformity_test.py
Writes 30_OUTPUT/war_input_uniformity_test_log.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import forecast_config as C
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF
from participation_model import ParticipationModel
from aging_level_weights_test import anchors as rate_rows, build_curve, curve_paths, wrmse

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
W3 = (0.5, 0.3, 0.2)
K_OWN = 0.65
NBOOT = 2000
REPRO_START, REPRO_WHOLE = 1.1506, 1.3598     # thin_history_check.py v1.0, laptop 2026-10-05
GP_BASE = ["tr_gp_share", "is_D", "exp_seasons", "age_c"]
ARMS = {"T+h": ("total", True), "T": ("total", False), "R+h": ("rate", True), "R": ("rate", False)}
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


# --------------------------------------------------------------------------- the trailing inputs
def trail(played, weights=W3):
    """skater_forecast._anchors' structure for three seasons, with explicit lag weights instead of
    a geometric decay. Each part is built by adding a POSITIVE lag to the season it came from, so a
    row cannot see season t0. Returns, per (career_key, t0): the plain-weighted trailing WAR total
    (tw_WAR) and games share (tr_gp_share), the games-weighted rate per 82 (own_82), age at t0,
    experience, position, and the number of seasons counted."""
    keep = ["career_key", "pkey", "pos", "syr", "GP", "gp_share", "exp_seasons", "age", "WAR", "WAR_82"]
    s = played[keep]
    lags = (1, 2, 3)
    m = pd.concat([s.assign(t0=s["syr"] + lag).set_index(["career_key", "t0"]).add_suffix(f"_{lag}")
                   for lag in lags], axis=1).reset_index()
    w = np.asarray(weights, dtype=float)

    def first(col):
        out = m[f"{col}_1"]
        for lag in lags[1:]:
            out = out.fillna(m[f"{col}_{lag}"])
        return out

    def blend(col, games=False):
        vals = np.column_stack([m[f"{col}_{l}"].to_numpy(float) for l in lags])
        gp = np.column_stack([m[f"GP_{l}"].to_numpy(float) for l in lags])
        ok = np.isfinite(vals)
        ww = np.where(ok, w[None, :] * (np.nan_to_num(gp) if games else 1.0), 0.0)
        tot = ww.sum(axis=1)
        num = (np.nan_to_num(vals) * ww).sum(axis=1)
        return np.where(tot > 0, num / np.where(tot > 0, tot, 1.0), np.nan)

    out = pd.DataFrame({"career_key": m["career_key"], "t0": m["t0"]})
    out["n_seasons"] = np.column_stack([m[f"GP_{l}"].notna() for l in lags]).sum(axis=1)
    out["pkey"], out["pos"] = first("pkey"), first("pos")
    out["is_D"] = (out["pos"] == "D").astype(float)
    out["exp_seasons"] = first("exp_seasons")
    age = m["age_1"] + 1.0
    for lag in lags[1:]:
        age = age.fillna(m[f"age_{lag}"] + float(lag))
    out["age"] = age
    out["age_c"] = out["age"] - 27.0
    out["tw_WAR"] = blend("WAR")
    out["tr_gp_share"] = blend("gp_share")
    out["own_82"] = blend("WAR_82", games=True)
    return out.dropna(subset=["tw_WAR"]).reset_index(drop=True)


def with_level(a, kind, hinge):
    """The frame both equations read, with `tw_WAR` holding the arm's level (the column name the
    production code reads it under) and `tw_hi1` its excess over 1.0 in its own units."""
    b = a.copy()
    b["tw_WAR"] = a["tw_WAR"] if kind == "total" else a["own_82"]
    b["tw_hi1"] = np.clip(b["tw_WAR"] - 1.0, 0, None)
    return b, GP_BASE + ["tw_WAR"] + (["tw_hi1"] if hinge else [])


# --------------------------------------------------------------------------- scoring helpers
def logloss(p, y):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def boot_lower(la, lb, groups, rng):
    """Resamples (of NBOOT, whole careers) in which arm a's summed loss is below arm b's."""
    codes, uniq = pd.factorize(groups)
    sa = np.bincount(codes, la, len(uniq)); sb = np.bincount(codes, lb, len(uniq))
    n = len(uniq)
    return int(sum(sa[ix].sum() < sb[ix].sum() for ix in (rng.integers(0, n, n) for _ in range(NBOOT))))


def main():
    C.banner("war_input_uniformity_test.py", SCRIPT_VERSION)
    bd, how = PST.birthdate_source()
    log(f"birthdates: {how}")
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    log(f"contract export: {C.F_CONTRACTS_CSV.name}, {len(contracts):,} rows")
    last = int(table["syr"].max())
    log(f"outcome seasons scored through {last} (the last in the table)")

    # ---- guard: the trailing builder reproduces today's _anchors under today's weights ----------
    iset = ISET.build(table, ISET.decision_date_for_page(2018), t0=2018)
    pl = iset.seasons[iset.seasons["GP"] >= C.MIN_GP]
    d_ = 0.667
    ref = SF._anchors(pl, 3, d_, cols=["WAR"]).set_index(["career_key", "t0"]).sort_index()
    mine = trail(pl, (1.0, d_, d_ ** 2)).set_index(["career_key", "t0"]).sort_index()
    assert ref.index.equals(mine.index), "trailing builder: different rows from skater_forecast._anchors"
    for c in ("tw_WAR", "tr_gp_share", "age", "exp_seasons", "is_D"):
        gap = np.nanmax(np.abs(ref[c].to_numpy(float) - mine[c].to_numpy(float)))
        assert gap < 1e-12 and (ref[c].isna() == mine[c].isna()).all(), (c, gap)
    log(f"guard: trailing builder equals skater_forecast._anchors on the 2018 page ({len(mine):,} rows)")

    # ---- the directed rate per 82, identical in every arm -----------------------------------
    dr = rate_rows(table)
    cn = np.full(len(dr), np.nan); paths = np.zeros((len(dr), 3 + 5 + 1))
    q = table[table["GP"] >= C.MIN_GP]
    for t0 in PAGES:
        m = build_curve(path, t0, W3, True)
        s = q[q["syr"] < t0]
        lp = {pp: float(np.sum(g["WAR_82"] * g["GP"]) / np.sum(g["GP"])) for pp, g in
              s.assign(pp=np.where(s["pos"] == "D", "D", "F")).groupby("pp")}
        ix, c, pth = curve_paths(dr, m, t0, lp)
        cn[ix], paths[ix] = c, pth
    ia = np.arange(len(dr)); gp_ = dr["last_lag"].to_numpy(int)
    start = K_OWN * dr["own"].to_numpy() + (1 - K_OWN) * cn + paths[ia, gp_]
    rate = {h: start + (paths[ia, gp_ + h] - paths[ia, gp_]) for h in HS}
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"),
                                                   war=("WAR", "sum"), share=("gp_share", "first"))
    e0, w0, ew, ww = [], [], [], []
    for h in HS:
        rr = res.reindex(pd.MultiIndex.from_arrays([dr["career_key"], dr["t0"] + h]))
        ok = (rr["GP"].to_numpy() > 0) & np.isfinite(rr["y"].to_numpy())
        e = rate[h][ok] - rr["y"].to_numpy()[ok]
        (e0 if h == 0 else ew).append(e); (w0 if h == 0 else ww).append(rr["GP"].to_numpy()[ok])
    got = (round(wrmse(np.concatenate(e0), np.concatenate(w0)), 4), round(wrmse(np.concatenate(ew), np.concatenate(ww)), 4))
    log(f"reproduction: directed rate start {got[0]:.4f}, whole 1-5 out {got[1]:.4f} (recorded {REPRO_START}, {REPRO_WHOLE})")
    if abs(got[0] - REPRO_START) > 1e-9 or abs(got[1] - REPRO_WHOLE) > 1e-9:
        raise RuntimeError("the directed rate does not reproduce the recorded figures; results not read")
    log("  PASS")
    rate_of = {}
    for h in HS:
        rate_of.update({(k, t, h): r for k, t, r in zip(dr["career_key"], dr["t0"], rate[h])})

    # ---- per page: fit both equations under each arm, predict the page's players ------------
    out = []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        seas = iset.seasons
        played = seas[seas["GP"] >= C.MIN_GP]
        allA = trail(played)
        act = seas.set_index(["career_key", "syr"])
        page = allA[allA["t0"] == t0].drop_duplicates("career_key").reset_index(drop=True)
        rows = []
        for h in HS:
            if t0 + h > last:
                continue
            r = page[["career_key", "pkey", "n_seasons"]].copy(); r["t0"] = t0; r["h"] = h
            rr = res.reindex(pd.MultiIndex.from_arrays([page["career_key"], page["t0"] + h]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            r["played"] = (gp >= C.PARTICIPATION_GP).astype(float)
            r["share_act"] = np.where(gp > 0, rr["share"].to_numpy(), np.nan)
            r["war_act"] = np.where(gp > 0, rr["war"].to_numpy(), 0.0)
            r["rate"] = [rate_of.get((k, t0, h), np.nan) for k in page["career_key"]]
            rows.append(r)
        rows = pd.concat(rows, ignore_index=True)
        p_by = {}
        for kind in ("total", "rate"):
            part = ParticipationModel(contracts, exclude=("contract_unknown",), contract_state="observable")
            part.fit(seas, t0, anchors_fn=lambda p, k=kind: with_level(trail(p), k, False)[0], horizons=HS)
            pa, _ = with_level(page, kind, False)
            p_by[kind] = {h: part.predict(pa, h).reindex(page["career_key"]).fillna(part.base_[h]).to_numpy()
                          for h in HS}
        for an, (kind, hinge) in ARMS.items():
            fa, feats = with_level(allA, kind, hinge)
            pa, _ = with_level(page, kind, hinge)
            share, pp = {}, {}
            for h in HS:
                tr = fa[fa["t0"] + h < t0].copy()
                tr["y"] = act["gp_share"].reindex(pd.MultiIndex.from_arrays([tr["career_key"], tr["t0"] + h])).to_numpy()
                tr = tr.dropna(subset=["y"] + feats)
                coef = SF._ols(tr[feats], tr["y"]) if len(tr) > 50 else None
                share[h] = np.clip(SF._apply(coef, pa[feats], pa["tr_gp_share"]), 0.05, 1.0)
                pp[h] = p_by[kind][h]
            hh = rows["h"].to_numpy(); pos = {k: i for i, k in enumerate(page["career_key"])}
            ii = np.array([pos[k] for k in rows["career_key"]])
            rows[f"share_{an}"] = [share[h][i] for h, i in zip(hh, ii)]
            rows[f"p_{an}"] = [pp[h][i] for h, i in zip(hh, ii)]
        out.append(rows)
        log(f"  page {t0}: {len(page):,} players, {len(rows):,} player-seasons scored")
    D = pd.concat(out, ignore_index=True)
    have_rate = np.isfinite(D["rate"].to_numpy())
    log(f"\nrows: {len(D):,} player-seasons, {D['career_key'].nunique():,} players; directed rate available on "
        f"{int(have_rate.sum()):,} (season WAR is scored on those only)")

    # ---- scores ------------------------------------------------------------------------------
    g = D["career_key"].to_numpy()
    app = np.isfinite(D["share_act"].to_numpy())
    y = D["played"].to_numpy()
    loss = {}
    for an in ARMS:
        loss[an] = {
            "share": np.where(app, (D[f"share_{an}"] - D["share_act"]) ** 2, 0.0),
            "logloss": logloss(D[f"p_{an}"].to_numpy(), y),
            "brier": (D[f"p_{an}"].to_numpy() - y) ** 2,
            "war_sq": np.where(have_rate, (D[f"p_{an}"] * D["rate"] * D[f"share_{an}"] - D["war_act"]) ** 2, 0.0),
            "war_abs": np.where(have_rate, np.abs(D[f"p_{an}"] * D["rate"] * D[f"share_{an}"] - D["war_act"]), 0.0)}

    def table_for(mask, label):
        log(f"\n{label}")
        log(f"  {'arm':6s}{'share RMSE':>12s}{'play logloss':>14s}{'play Brier':>12s}{'WAR RMSE':>10s}{'WAR MAE':>9s}")
        for an in ARMS:
            L = loss[an]
            sa = mask & app; wa = mask & have_rate
            log(f"  {an:6s}{np.sqrt(L['share'][sa].mean()):12.4f}{L['logloss'][mask].mean():14.4f}"
                f"{L['brier'][mask].mean():12.4f}{np.sqrt(L['war_sq'][wa].mean()):10.4f}{L['war_abs'][wa].mean():9.4f}")
        log(f"  rows: share {int((mask & app).sum()):,}, playing {int(mask.sum()):,}, season WAR {int((mask & have_rate).sum()):,}")

    allm = np.ones(len(D), bool)
    table_for(allm, "ALL ROWS, seasons ahead 0-5 (T = trailing total, R = rate per 82, +h = level-above-1.0 term)")
    hh = D["h"].to_numpy()
    log("\nBY SEASON AHEAD, season-WAR RMSE")
    log("  " + f"{'arm':6s}" + "".join(f"{'+' + str(h):>9s}" for h in HS))
    for an in ARMS:
        log(f"  {an:6s}" + "".join(f"{np.sqrt(loss[an]['war_sq'][(hh == h) & have_rate].mean()):9.4f}" for h in HS))
    ns = D["n_seasons"].to_numpy()
    for k in (1, 2, 3):
        table_for(ns == k, f"SEASONS COUNTED = {k}")

    rng = np.random.default_rng(20261005)
    log("\nRESAMPLES (of 2,000, whole careers): how often the first arm's summed loss is lower")
    log(f"  {'':14s}{'share':>8s}{'logloss':>9s}{'Brier':>8s}{'WAR sq':>8s}")
    for a, b in (("R+h", "T+h"), ("R", "T"), ("T", "T+h"), ("R", "R+h"), ("R", "T+h")):
        cells = [boot_lower(loss[a][k], loss[b][k], g, rng) for k in ("share", "logloss", "brier", "war_sq")]
        log(f"  {a + ' vs ' + b:14s}" + "".join(f"{c:8d}" if i != 1 else f"{c:9d}" for i, c in enumerate(cells)))
    log("  (the chance of playing has no level-above-1.0 term, so T and T+h, and R and R+h, share it:"
        " their logloss and Brier counts read 0)")

    C.record_inspection("war_input_uniformity_test.py", "pages", PAGES,
                        "trailing total vs rate per 82 in games share and chance of playing (Thomas 2026-10-05)")
    p = C.out_path("war_input_uniformity_test_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
