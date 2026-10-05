"""aging_investigations_abc.py -- investigations A, B and C on the built forecast (plan of record, step 2).

WHY (Thomas, 2026-10-04/05; 00_STATE/MODEL_DIRECTIVES.md, "To investigate" A, B, C). All three change
the comparable-player aging curve, so they run in one script, on one set of rows, against one
baseline: the built forecast (skater_forecast v2.0, `64ab8bf`, directives 1-3). Each version below is
ONE change, scored alone against the baseline; combinations come only after Thomas picks.
TEST ONLY: nothing in 20_CODE changes and nothing is adopted by running it.

THE VERSIONS (arm list approved by Thomas 2026-10-05, with C6 added)
  A1  a separate yardstick (the curve's bandwidth h) for forwards and for defencemen, each the median
      within-position distance from the same samples the pooled one uses
  A2  no self-pairs: the pooled yardstick measured without pairs of one player's own seasons
  B1  comparables only: the league average enters only where no comparable has a value at that age
      (aging_curve.SHRINK_K's blend removed, for the level and for every year-to-year change)
  B2  thin histories: a player with no 20-game season at his last counted age gets, as his
      comparables' level, the league level of 10+ game seasons (the own rate's rule) by position and
      age, instead of the league level of 20-game seasons
  C1  the assumed level of a departed player's missing season: -0.50, -0.25, +0.25 (baseline 0)
  C2  returning players: a player absent at age a+1 who appears again later (before the page) is
      not filled in
  C3a next seasons of 1-19 games (dropped today) filled in like a departure (rate 0, 82 games)
  C3b next seasons of 1-19 games measured on the short season itself (its rate and its games)
  C4  no filled-in seasons at all
  C5  thin histories: for players with one or two counted seasons, comparables from a pool without
      the two-consecutive-20-game-season requirement (single-season profiles admitted, first seasons
      included); everyone else keeps the baseline curve
  C6  the filled-in departure season counted at his own last season's games instead of 82
      (aging_curve.DEPARTED_GP, the setting the build carries that nobody chose)

HOW EACH VERSION IS RUN. Per development page t0 (2015-2021) production XNPV1 is fitted once
(games share and chance of playing do not depend on the curve). For each version the model's curve
(`curve_`) is replaced by the version's curve, its path cache cleared, and production's own
`XNPV1._rate` / `_path` produce the rate per 82 for every player on the page, seasons 0-5 ahead.
A1, A2 and B1 change one method or attribute of the production curve; B2 replaces the comparables'
level only on production's no-profile branch; C1-C4 and C6 rebuild the departures with
`curve_variant` below, which with default settings must equal skater_forecast.imputed_aging_model on
every page (asserted); C5 builds the same on a pool-relaxed AgingModel.

SCORES (same rows as every step-1 test: 40,510 player-seasons, 1,609 players)
    start / whole   rate per 82 in seasons played, the valuation season / one to five seasons out,
                    games-weighted RMSE (and bias where stated)
    season WAR      chance of playing x rate x games share against his actual season WAR (0 if he
                    did not play), RMSE and MAE
  Breakdowns: seasons counted (1, 2, 3); age at the valuation season (under 22, 22-34, 35+); for B,
  the league average's share of the baseline comparables' level at his last age (no profile = all
  league). 2,000 career resamples against the baseline. Baseline guard: 1.1506 / 1.3598 / 0.8093.
  CAVEAT for any write-up: the development pages have been examined by many variants; results here
  choose between versions, they are not fresh evidence.

HOW TO RUN (repo root, laptop; needs the contract export; roughly 20-40 minutes):
    python 25_TESTS/aging_investigations_abc.py
Writes 30_OUTPUT/aging_investigations_abc_log.txt.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import aging_curve as AC
import forecast_config as C
import information_set as ISET
import player_season_table as PST
import skater_forecast as SF

SCRIPT_VERSION = "1.0"
PAGES = C.DEV_PAGES
HS = tuple(range(6))
NBOOT = 2000
TOL = 1e-12
BASE = {"start": 1.1506, "whole": 1.3598, "war_rmse": 0.8093, "rows": 40510}
ARMS = ["A1 yardstick by position", "A2 no self-pairs", "B1 comparables only",
        "B2 thin: 10-game league fallback", "C1 departed level -0.50", "C1 departed level -0.25",
        "C1 departed level +0.25", "C2 returners not filled", "C3a short next season = departure",
        "C3b short next season measured", "C4 no filled-in seasons", "C5 thin: relaxed pool",
        "C6 departed games = his own"]
LOG = []


def log(s=""):
    print(s)
    LOG.append(str(s))


# =========================================================================== curve variants
class RelaxedAgingModel(AC.AgingModel):
    """C5's pool: every 20-game season enters the comparables pool, a single-season profile where the
    season before is not one year earlier (and for a first season). Production's _build_bank skips
    those (review item 1.7). Everything after the pool is production's code, copied."""

    def _build_bank(self):
        rows = []
        self.n_bank_skipped = 0
        for name, p in self.players.items():
            ss = p["seasons"]
            for i in range(len(ss)):
                adj = p["adjacent"].get(ss[i]["age"], False)
                lo = i - (AC.WIN - 1) if (adj and i >= AC.WIN - 1) else i
                rows.append((name, p["pos"], ss[i]["age"], AC._profile(ss[lo: i + 1], p["sm"][ss[i]["age"]])))
        self.names = np.array([r[0] for r in rows]); self.pos = np.array([r[1] for r in rows])
        self.agek = np.array([r[2] for r in rows]); X = np.array([r[3] for r in rows], dtype=float)
        self.stats = {}; Z = np.empty_like(X)
        for pp in np.unique(self.pos):
            m = self.pos == pp; mu = X[m].mean(0); sd = X[m].std(0); sd[sd == 0] = 1e-9
            Z[m] = (X[m] - mu) / sd; self.stats[pp] = (mu, sd)
        self.fw = AC._attr_weights(); self.Zw = Z * np.sqrt(self.fw)

        def series(p):
            L = np.full(self.nages, np.nan); D = np.full(self.nages, np.nan)
            for a, v in p["sm"].items():
                L[a - self.AMIN] = v
                if (a + 1) in p["sm"]:
                    D[a - self.AMIN] = p["sm"][a + 1] - v
            return L, D
        pser = {n: series(p) for n, p in self.players.items()}
        self.Lser = np.array([pser[n][0] for n in self.names]); self.Dser = np.array([pser[n][1] for n in self.names])
        self.by_age = {}
        for r in range(len(self.names)):
            self.by_age.setdefault(int(self.agek[r]), []).append(r)
        self.by_age = {k: np.array(v) for k, v in self.by_age.items()}
        rng = np.random.default_rng(0); ds = []
        for pp in np.unique(self.pos):
            Xi = self.Zw[self.pos == pp]
            if len(Xi) < 3:
                continue
            idx = rng.choice(len(Xi), size=min(1200, len(Xi)), replace=False); Xi = Xi[idx]
            sq = (Xi ** 2).sum(1); d2 = np.clip(sq[:, None] + sq[None, :] - 2 * Xi @ Xi.T, 0, None)
            ds.append(np.sqrt(d2[np.triu_indices(len(Xi), 1)]))
        self.h = float(np.median(np.concatenate(ds)))


def curve_variant(path, before, rate=0.0, gp_rule="82", returners_filled=True, short=None,
                  impute=True, relaxed=False):
    """The curve with departures filled in as skater_forecast.imputed_aging_model does, with the
    departure rule's settings exposed. Defaults reproduce production exactly (asserted in main)."""
    m = (RelaxedAgingModel if relaxed else AC.AgingModel)(path, before=before)
    m.n_imputed = 0
    if not impute:
        return m
    df = pd.read_csv(path)
    df["syr"] = df["Season"].str.split("-").str[0].astype(int) + 2000
    df = df[df["syr"] < int(before)].copy()
    df["career"] = df["Player"].map(AC.career_key)
    df = df[df["age"].notna()]
    df["age_i"] = df["age"].astype(int)
    present = set(zip(df["career"], df["age_i"]))
    syr_of = df.groupby(["career", "age_i"])["syr"].max().to_dict()
    tot = df.groupby(["career", "age_i"]).agg(GP=("GP", "sum"), WAR=("WAR", "sum"))
    last_age = df.groupby("career")["age_i"].max().to_dict()
    imputed = {}
    for name, p in m.players.items():
        byage = {s["age"]: s for s in p["seasons"]}
        for s in p["seasons"]:
            a = s["age"]
            if (a + 1) in p["sm"]:
                continue                                  # a 20-game season at a+1: observed
            if (name, a + 1) in present:                  # 1-19 games at a+1
                if short is None:
                    continue                              # production: neither filled nor measured
                if short == "departure":
                    fill = {"w82": rate, "gp": AC.DEPARTED_GP}
                else:                                     # "measure": his short season itself
                    t = tot.loc[(name, a + 1)]
                    if not t["GP"] > 0:
                        continue
                    fill = {"w82": float(t["WAR"] / t["GP"] * 82.0), "gp": float(t["GP"])}
            else:
                sy = syr_of.get((name, a))
                if sy is None or sy + 1 >= int(before):
                    continue                              # the next season is not over yet
                if not returners_filled and last_age.get(name, a) > a + 1:
                    continue                              # C2: he came back later
                fill = {"w82": rate, "gp": AC.DEPARTED_GP if gp_rule == "82" else float(s["gp"])}
            b2 = dict(byage); b2[a + 1] = fill
            imputed[(name, a)] = AC.level_at(b2, a + 1) - p["sm"][a]
    m.n_imputed = len(imputed)
    by_name = {}
    for (nm, a), d in imputed.items():
        by_name.setdefault(nm, []).append((a, d))
    D = m.Dser.copy()
    for r, name in enumerate(m.names):
        for a, d in by_name.get(name, ()):
            assert np.isnan(D[r, a - m.AMIN])
            D[r, a - m.AMIN] = d
    m.Dser = D
    dn, dc = {}, {}
    for name, p in m.players.items():
        pos, ss, ser = p["pos"], p["seasons"], p["sm"]
        for i, s in enumerate(ss):
            a = s["age"]
            if i + 1 < len(ss) and ss[i + 1]["age"] - a == 1:
                d = ser[ss[i + 1]["age"]] - ser[a]
            elif (name, a) in imputed:
                d = imputed[(name, a)]
            else:
                continue
            dn[(pos, a)] = dn.get((pos, a), 0.0) + d
            dc[(pos, a)] = dc.get((pos, a), 0) + 1
    m.gdelta = {k: dn[k] / dc[k] for k in dn}
    return m


def yardsticks(m, by_position=False, no_self=False):
    """The bandwidth from the same samples production draws (rng seed 0, 1,200 per position):
    pooled (production), per position (A1), or pooled without same-player pairs (A2)."""
    rng = np.random.default_rng(0); ds, keep, per = [], [], {}
    for pp in np.unique(m.pos):
        sel = m.pos == pp
        Xi = m.Zw[sel]; Ni = m.names[sel]
        if len(Xi) < 3:
            continue
        idx = rng.choice(len(Xi), size=min(1200, len(Xi)), replace=False); Xi = Xi[idx]; Ni = Ni[idx]
        sq = (Xi ** 2).sum(1); d2 = np.clip(sq[:, None] + sq[None, :] - 2 * Xi @ Xi.T, 0, None)
        iu = np.triu_indices(len(Xi), 1)
        d = np.sqrt(d2[iu]); other = Ni[iu[0]] != Ni[iu[1]]
        ds.append(d); keep.append(other); per[pp] = float(np.median(d))
    pooled = float(np.median(np.concatenate(ds)))
    assert abs(pooled - m.h) < TOL, "yardstick resampling does not reproduce production's"
    if by_position:
        return per
    if no_self:
        return float(np.median(np.concatenate(ds)[np.concatenate(keep)]))
    return pooled


def weights_by_position(hpos):
    """AgingModel._weights with the bandwidth chosen by the target's position (A1)."""
    def _weights(self, target_z, pos, age, exclude=None):
        cand = self.by_age.get(age, np.array([], int))
        cand = cand[self.pos[cand] == pos] if len(cand) else cand
        if len(cand) == 0:
            return cand, None
        h = hpos[pos]
        w = np.exp(-((self.Zw[cand] - target_z) ** 2).sum(1) / (2 * h ** 2))
        if exclude is not None:
            w[self.names[cand] == exclude] = 0.0
        return cand, w
    return _weights


def shrunk_comparables_only(self, vals_col, cand, w, glob_target):
    """AgingModel._shrunk without the league blend (B1): the comparables' weighted average, and the
    league value only where no comparable has a value at that age."""
    mk = ~np.isnan(vals_col); ww = w * mk; s = ww.sum()
    if not s > 0:
        return glob_target
    return float(np.sum(ww * np.where(mk, vals_col, 0.0)) / s)


def league_share(m, key, pos, age_last):
    """The league average's share of the comparables' level at his last age, on the baseline curve:
    SHRINK_K / (comparables' weight + SHRINK_K); 1.0 with no profile or no comparables."""
    if not np.isfinite(age_last):
        return 1.0
    a = int(age_last)
    if key not in m.players or a not in m.players[key]["sm"]:
        return 1.0
    p = m.players[key]; ss = p["seasons"]
    idx = next(q for q, s in enumerate(ss) if s["age"] == a)
    lo = idx if not p["adjacent"].get(a, False) else max(0, idx - (AC.WIN - 1))
    mu, sd = m.stats[p["pos"]]
    tv = ((AC._profile(ss[lo: idx + 1], p["sm"][a]) - mu) / sd) * np.sqrt(m.fw)
    cand, wt = m._weights(tv, p["pos"], a, exclude=key)
    if cand is None or not len(cand):
        return 1.0
    ww = wt * ~np.isnan(m.Lser[cand, a - m.AMIN])
    return AC.SHRINK_K / (ww.sum() + AC.SHRINK_K)


# =========================================================================== scoring
def wrmse(e, w):
    return float(np.sqrt(np.sum(w * e ** 2) / np.sum(w)))


def boot_lower(la, lb, groups, rng):
    codes, uniq = pd.factorize(groups)
    sa = np.bincount(codes, la, len(uniq)); sb = np.bincount(codes, lb, len(uniq))
    n = len(uniq)
    return int(sum(sa[ix].sum() < sb[ix].sum() for ix in (rng.integers(0, n, n) for _ in range(NBOOT))))


def main():
    C.banner("aging_investigations_abc.py", SCRIPT_VERSION)
    log(f"skater_forecast v{SF.SCRIPT_VERSION}")
    bd, how = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"))

    frames = []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        base_curve = mod.curve_
        # guard: the departure builder with default settings is production's curve
        cv = curve_variant(path, t0)
        assert list(cv.names) == list(base_curve.names) and cv.h == base_curve.h
        for nm in ("Lser", "Dser"):
            a_, b_ = getattr(cv, nm), getattr(base_curve, nm)
            assert np.array_equal(np.isnan(a_), np.isnan(b_)) and np.nanmax(np.abs(a_ - b_)) < TOL, nm
        assert cv.gdelta.keys() == base_curve.gdelta.keys()
        assert max(abs(cv.gdelta[k] - base_curve.gdelta[k]) for k in cv.gdelta) < TOL
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        out = {"base": {h: mod._rate(pa, h) for h in HS}}
        lsh = np.array([league_share(base_curve, k, p_, al) for k, p_, al in
                        zip(pa.index, pa["pos"], pa["age_last"].to_numpy(float))])

        def run(curve, wrap=None, mask=None):
            mod.curve_ = curve; mod._paths = {}
            if wrap is not None:
                mod._path = types.MethodType(wrap, mod)
            r = {h: mod._rate(pa, h) for h in HS}
            if wrap is not None:
                del mod._path
            mod.curve_ = base_curve; mod._paths = {}
            if mask is not None:
                r = {h: np.where(mask, r[h], out["base"][h]) for h in HS}
            return r

        # A1 / A2
        hpos = yardsticks(base_curve, by_position=True)
        c = curve_variant(path, t0); c._weights = types.MethodType(weights_by_position(hpos), c)
        out[ARMS[0]] = run(c)
        c = curve_variant(path, t0); c.h = yardsticks(c, no_self=True)
        out[ARMS[1]] = run(c)
        # B1
        c = curve_variant(path, t0); c._shrunk = types.MethodType(shrunk_comparables_only, c)
        out[ARMS[2]] = run(c)
        # B2: the league level of 10+ game seasons, on production's no-profile branch only
        old = AC.MIN_GP; AC.MIN_GP = C.MIN_GP
        try:
            lvl10 = AC.AgingModel(path, before=t0).glevel
        finally:
            AC.MIN_GP = old
        orig_path = SF.XNPV1._path

        def path_b2(self, key, pos, age_last, gap, _lvl=lvl10):
            cn, p_ = orig_path(self, key, pos, age_last, gap)
            if np.isfinite(age_last):
                aa = int(age_last); m = self.curve_
                if not (key in m.players and aa in m.players[key]["sm"]):
                    g = "D" if pos == "D" else "F"
                    cn = _lvl.get((g, aa), self.league_rate_[g])
            return cn, p_
        out[ARMS[3]] = run(base_curve, wrap=path_b2)
        # C arms
        for arm, kw in ((ARMS[4], dict(rate=-0.50)), (ARMS[5], dict(rate=-0.25)), (ARMS[6], dict(rate=0.25)),
                        (ARMS[7], dict(returners_filled=False)), (ARMS[8], dict(short="departure")),
                        (ARMS[9], dict(short="measure")), (ARMS[10], dict(impute=False)),
                        (ARMS[12], dict(gp_rule="own"))):
            out[arm] = run(curve_variant(path, t0, **kw))
        thin = pa["n_seasons"].to_numpy(float) <= 2
        out[ARMS[11]] = run(curve_variant(path, t0, relaxed=True), mask=thin)

        rows = []
        for h in HS:
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(pa.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            d = pd.DataFrame({"career_key": pa.index, "t0": t0, "h": h, "share": ph["gp_share"].to_numpy(),
                              "p": ph["p_play"].to_numpy(), "gp": gp, "y82": rr["y"].to_numpy(),
                              "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                              "n_seasons": pa["n_seasons"].to_numpy(float), "age": pa["age"].to_numpy(float),
                              "lshare": lsh})
            for arm, r in out.items():
                d[f"r|{arm}"] = r[h]
            rows.append(d)
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players; departures filled in {cv.n_imputed:,}; yardstick pooled "
            f"{base_curve.h:.3f}, F {hpos.get('F', np.nan):.3f}, D {hpos.get('D', np.nan):.3f}")

    D = pd.concat(frames, ignore_index=True)
    arms = ["base"] + ARMS
    g = D["career_key"].to_numpy()
    played = ((D["gp"] > 0) & np.isfinite(D["y82"])).to_numpy()
    w = np.where(played, D["gp"], 0.0)
    h0 = (D["h"] == 0).to_numpy(); h15 = (D["h"] > 0).to_numpy()
    L = {}
    for arm in arms:
        e = (D[f"r|{arm}"] - D["y82"]).to_numpy()
        ew = (D["p"] * D[f"r|{arm}"] * D["share"] - D["war_act"]).to_numpy()
        L[arm] = {"e": np.where(played, e, 0.0), "start_sq": np.where(played & h0, w * e ** 2, 0.0),
                  "whole_sq": np.where(played & h15, w * e ** 2, 0.0), "war_sq": ew ** 2, "war_abs": np.abs(ew)}

    def score(arm, mask=None):
        m = np.ones(len(D), bool) if mask is None else mask
        s0 = played & h0 & m; s1 = played & h15 & m
        e = L[arm]["e"]
        return {"start": wrmse(e[s0], w[s0]) if s0.any() else np.nan,
                "bias0": float(np.sum(w[s0] * e[s0]) / np.sum(w[s0])) if s0.any() else np.nan,
                "whole": wrmse(e[s1], w[s1]) if s1.any() else np.nan,
                "war_rmse": float(np.sqrt(L[arm]["war_sq"][m].mean())), "war_mae": float(L[arm]["war_abs"][m].mean())}

    b = score("base")
    log(f"\nbaseline (the build): start {b['start']:.4f}, whole {b['whole']:.4f}, season WAR {b['war_rmse']:.4f}, "
        f"rows {len(D):,} (recorded {BASE['start']}, {BASE['whole']}, {BASE['war_rmse']}, {BASE['rows']:,})")
    if (abs(round(b["start"], 4) - BASE["start"]) > 1e-9 or abs(round(b["whole"], 4) - BASE["whole"]) > 1e-9
            or abs(round(b["war_rmse"], 4) - BASE["war_rmse"]) > 1e-9 or len(D) != BASE["rows"]):
        raise RuntimeError("the baseline does not reproduce the build check's figures; results not read")
    log("  PASS")

    rng = np.random.default_rng(20261005)
    log("\nALL ROWS. Rate per 82 in seasons played (games-weighted RMSE); season WAR = p x rate x share.")
    log("  'lower in' = resamples (of 2,000 careers) in which the version's summed squared error is below the baseline's")
    log(f"  {'version':36s}{'start':>8s}{'whole':>8s}{'WAR RMSE':>10s}{'WAR MAE':>9s}{'moved':>8s}"
        f"   lower in: start / whole / WAR")
    for arm in arms:
        s = score(arm)
        moved = int(np.sum(np.abs(D[f"r|{arm}"] - D["r|base"]) > 1e-9))
        if arm == "base":
            log(f"  {arm:36s}{s['start']:8.4f}{s['whole']:8.4f}{s['war_rmse']:10.4f}{s['war_mae']:9.4f}{'':>8s}")
            continue
        c = [boot_lower(L[arm][k], L["base"][k], g, rng) for k in ("start_sq", "whole_sq", "war_sq")]
        log(f"  {arm:36s}{s['start']:8.4f}{s['whole']:8.4f}{s['war_rmse']:10.4f}{s['war_mae']:9.4f}{moved:8,d}"
            f"   {c[0]:5d} / {c[1]:5d} / {c[2]:5d}")

    log("\nBY SEASON AHEAD, rate per 82 RMSE (seasons played)")
    log(f"  {'version':36s}" + "".join(f"{'+' + str(h):>8s}" for h in HS))
    for arm in arms:
        e = L[arm]["e"]
        hh = D["h"].to_numpy()
        log(f"  {arm:36s}" + "".join(f"{wrmse(e[played & (hh == h)], w[played & (hh == h)]):8.4f}" for h in HS))

    ns = D["n_seasons"].to_numpy()
    log("\nBY SEASONS COUNTED: start RMSE / start bias / whole RMSE")
    log(f"  {'version':36s}" + "".join(f"{f'{k} season' + ('s' if k > 1 else ''):>27s}" for k in (1, 2, 3)))
    for arm in arms:
        cells = []
        for k in (1, 2, 3):
            s = score(arm, ns == k)
            cells.append(f"{s['start']:9.4f} {s['bias0']:+7.3f} {s['whole']:8.4f}")
        log(f"  {arm:36s}" + "".join(f"{c:>27s}" for c in cells))

    age = D["age"].to_numpy()
    bands = (("under 22", age < 22), ("22-34", (age >= 22) & (age < 35)), ("35+", age >= 35))
    log("\nBY AGE AT THE VALUATION SEASON: whole RMSE (rows: " +
        ", ".join(f"{n} {int((m & played & h15).sum()):,}" for n, m in bands) + ")")
    log(f"  {'version':36s}" + "".join(f"{n:>10s}" for n, _ in bands))
    for arm in arms:
        log(f"  {arm:36s}" + "".join(f"{score(arm, m)['whole']:10.4f}" for _, m in bands))

    ls = D["lshare"].to_numpy()
    sb = (("under 10%", ls < 0.10), ("10-25%", (ls >= 0.10) & (ls < 0.25)), ("25-99%", (ls >= 0.25) & (ls < 1.0)),
          ("no profile (100%)", ls >= 1.0))
    log("\nB: BY THE LEAGUE AVERAGE'S SHARE of the baseline comparables' level: start RMSE / whole RMSE (rows: " +
        ", ".join(f"{n} {int((m & played & h0).sum()):,}" for n, m in sb) + ")")
    log(f"  {'version':36s}" + "".join(f"{n:>20s}" for n, _ in sb))
    for arm in ["base", ARMS[2], ARMS[3]]:
        log(f"  {arm:36s}" + "".join(f"{score(arm, m)['start']:9.4f} / {score(arm, m)['whole']:.4f}" for _, m in sb))

    C.record_inspection("aging_investigations_abc.py", "pages", PAGES,
                        "investigations A, B, C on the built forecast (Thomas 2026-10-05)")
    p = C.out_path("aging_investigations_abc_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
