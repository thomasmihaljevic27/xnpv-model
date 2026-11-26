"""model_choices_current.py -- the skater forecast's tested choices, re-measured on the model as it runs today.

WHY (Thomas, 2026-11-25: "All five now"). "Valuing Players, Draft Picks, and Prospects" v5.0 defends the forecast's
settings with figures measured on 2026-10-04 and 2026-10-05, each against the model of that day
(starting_level_simple_test.py, level_games_weighting_test.py, aging_investigations_abc.py, games_and_playing_de.py,
war_input_uniformity_test.py). The model then adopted each winner, so those scripts' baselines no longer exist and their
guards stop. This script asks the same questions with TODAY'S MODEL AS THE BASELINE: each version below changes one thing
in skater_forecast v2.4 back to an alternative the document says was tested and rejected (or, for a weight, to another
value), and is scored on the same rows, weights and targets as the build.
TEST ONLY: nothing in 20_CODE changes and nothing is adopted by running it. The back-test is not read.

THE VERSIONS (each one change against the build; the build's setting first)
  STARTING LEVEL (Table 2)
    W   the weights on his recent seasons, 50/30/20 over three seasons: each of 33/33/33, 40/35/25, 40/40/20, 50/25/25,
        50/35/15, 60/25/15, 60/30/10, 70/20/10, and 60/40 over two seasons. The weights are skater_forecast.TRAIL_WEIGHTS,
        read by every trailing measure of the player (his own rate, the games share's and the chance of playing's
        inputs), so each version is a full refit of the page. The comparables' level keeps its own 50/30/20
        (aging_curve.LEVEL_WEIGHTS, directive 2), as in the build.
    K   the share of his own rate kept in the start, 65%: every share from 30% to 100% in steps of 5%.
    3W  a three-way blend: a x his own rate + b x his comparable players' level WITHOUT the league average in it + c x
        the league level for his position and age, a + b + c = 1, every cell in steps of 0.05, chosen on the starting
        level's error; the best cell is then scored in full.
    NS  no step from his most recent counted season to the valuation season (start at that season's level).
  THE AGING CURVE (Table 3 and its text)
    A1  one yardstick (the curve's bandwidth) for all players: the pooled median, AgingModel.h, instead of one per position.
    A2  the yardstick without pairs of two seasons by the same player (recomputed on production's own sample).
    B1  comparable players alone: the league average enters only where no comparable has a value (no weight of ten).
    BK  the weight on the league average: 0.01, 1, 5, 20 and 50 instead of 10 (aging_curve.SHRINK_K).
    C1  the level given to a departed player's missing season: -0.50, -0.25 and +0.25 WAR per 82 instead of 0.
    C2  players who come back later filled in as departures.
    C6  the departed season counted at 82 games instead of his own most recent season's.
    C4  no departed seasons filled in.
    C3  next seasons of 1-19 games filled in like a departure (rate 0, his own games).
  THE GAMES SHARE AND THE CHANCE OF PLAYING (Table 4 and its text)
    D2  the games share without age squared.
    D1  the games share as a fractional logit (statsmodels GLM, binomial family, logit link; Papke and Wooldridge 1996),
        the build's inputs; no cap or floor needed.
    U1  quality read as his games-weighted rate per 82 (own_82) instead of his trailing WAR total, in the games share AND
        the chance of playing (a full refit with the anchors' tw_WAR replaced by own_82; the start reads own_82 already).
    U2  the games share with a term for the trailing WAR total above one win added.
    E3  the chance of playing with an under-contract x trailing WAR total term added.
    E2  (a separate table) contracts whose first season is the page's season and that were signed after July 1 of it:
        their chance of playing read at July 1 against read at the signing (the build's XNPV1.p_play_signed), each against
        whether he played. Pages 2018-2021 (the export sees contracts from 2018).

SCORES. The rows, the scores and the p-values are forecast_term_audit.py's (its evaluate() is imported, seed 20261021,
2,000 redraws of careers): 40,510 player-seasons on the development pages 2015-2021, seasons 0-5 ahead; start and one to
five ahead in WAR per 82 (games-weighted, seasons he played), season WAR in wins, share, log loss. A version that leaves
rows unanswered (60/40 over two seasons) is scored on the rows it answers, beside the build on the same rows.
Breakdowns for the curve versions: one to five ahead by age at the valuation season (under 22, 22-34, 35 and over).
GUARD: the build reproduces forecast_term_audit.py's figures on today's model (run 2026-11-25): start 1.1506, one to five
ahead 1.3569, season WAR 0.8054, 40,510 rows; this script's own rebuild of the start (K and the step) equals production's
rate to 1e-12; the departure-curve builder with the build's settings equals skater_forecast.imputed_aging_model on every
page; the yardstick recomputed with self-pairs in equals production's.
CAVEAT for a write-up: the development pages have been examined by many variants; these results choose between versions,
they are not fresh evidence.

HOW TO RUN (repo root; needs the contract export; about 30-60 minutes):
    python 25_TESTS/model_choices_current.py
Writes 30_OUTPUT/model_choices_current_log.txt and model_choices_current_scores.csv.
"""
import copy
import sys
import types
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "20_CODE"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import aging_curve as AC
import forecast_config as C
import information_set as ISET
import participation_model as PM
import player_season_table as PST
import skater_forecast as SF
import forecast_term_audit as FTA        # evaluate(), fit_share(), the rows and the redraws
import games_and_playing_de as GPD       # the fractional logit fit and the contract x quality model

SCRIPT_VERSION = "model_choices_current.py v1.0 (2026-11-25)"
PAGES = C.DEV_PAGES
HS = FTA.HS
RECORDED = {"start": 1.1506, "whole": 1.3569, "war": 0.8054, "rows": 40510}   # forecast_term_audit.py, 2026-11-25
WEIGHTS = {"33/33/33": (1 / 3, 1 / 3, 1 / 3), "40/35/25": (0.40, 0.35, 0.25), "40/40/20": (0.40, 0.40, 0.20),
           "50/25/25": (0.50, 0.25, 0.25), "50/35/15": (0.50, 0.35, 0.15), "60/25/15": (0.60, 0.25, 0.15),
           "60/30/10": (0.60, 0.30, 0.10), "70/20/10": (0.70, 0.20, 0.10), "60/40 over two seasons": (0.60, 0.40, 0.0)}
KGRID = np.round(np.arange(0.30, 1.0001, 0.05), 2)
K_REPORT = (0.45, 0.55, 0.75)
BK = (0.01, 1.0, 5.0, 20.0, 50.0)
C1 = (-0.50, -0.25, 0.25)
LOG = FTA.LOG
log = FTA.log
ORIG_W, ORIG_K, ORIG_SHRINK, ORIG_ANCHORS = SF.TRAIL_WEIGHTS, SF.K_OWN, AC.SHRINK_K, SF._anchors
TOL = 1e-12


# =========================================================================== the departure curve, with its settings
def departure_curve(path, before, rate=0.0, gp_rule="own", returners=False, short=False, impute=True):
    """skater_forecast.imputed_aging_model with its settings as arguments. With the defaults it is production's, line for
    line (asserted on every page in main()). rate: the missing season's level; gp_rule 'own' (his own season's games,
    C6) or '82'; returners: fill in a player who appears again later (C2 not applied); short: a next season of 1-19
    games filled in like a departure; impute False: no departures at all."""

    class V(AC.AgingModel):
        def __init__(self, war_age_path, before):
            super().__init__(war_age_path, before=before)
            self.imputed_, self.n_imputed = {}, 0
            if not impute:
                return
            df = pd.read_csv(war_age_path)
            df["syr"] = df["Season"].str.split("-").str[0].astype(int) + 2000
            df = df[df["syr"] < int(before)].copy()
            df["career"] = df["Player"].map(AC.career_key)
            df = df[df["age"].notna()]
            present = set(zip(df["career"], df["age"].astype(int)))
            syr_of = df.groupby(["career", df["age"].astype(int)])["syr"].max().to_dict()
            last_age = df.groupby("career")["age"].max().astype(int).to_dict()
            imputed = {}
            for name, p in self.players.items():
                byage = {s["age"]: s for s in p["seasons"]}
                for s in p["seasons"]:
                    a = s["age"]
                    if (a + 1) in p["sm"]:
                        continue                              # a 20-game season at a+1: observed
                    if (name, a + 1) in present:              # he played at a+1, under 20 games
                        if not short:
                            continue
                    else:
                        sy = syr_of.get((name, a))
                        if sy is None or sy + 1 >= int(before):
                            continue                          # the next season is not over yet
                        if not returners and last_age.get(name, a) > a + 1:
                            continue                          # he came back later
                    b2 = dict(byage)
                    b2[a + 1] = {"w82": float(rate), "gp": 82.0 if gp_rule == "82" else float(s["gp"])}
                    imputed[(name, a)] = AC.level_at(b2, a + 1) - p["sm"][a]
            self.imputed_, self.n_imputed = imputed, len(imputed)
            by_name = {}
            for (nm, a), d in imputed.items():
                by_name.setdefault(nm, []).append((a, d))
            D = self.Dser.copy()
            for r, name in enumerate(self.names):
                for a, d in by_name.get(name, ()):
                    assert np.isnan(D[r, a - self.AMIN]), "an imputed change overwrote an observed one"
                    D[r, a - self.AMIN] = d
            self.Dser = D
            dn, dc = {}, {}
            for name, p in self.players.items():
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
            self.gdelta = {k: dn[k] / dc[k] for k in dn}

    return V(path, before)


def same_curve(a, b):
    """Two curves carry the same changes, levels and league tables (NaN-aware)."""
    if not (np.array_equal(np.isnan(a.Dser), np.isnan(b.Dser)) and np.nanmax(np.abs(a.Dser - b.Dser)) < TOL):
        return False
    return (a.gdelta.keys() == b.gdelta.keys() and max(abs(a.gdelta[k] - b.gdelta[k]) for k in a.gdelta) < TOL
            and a.glevel.keys() == b.glevel.keys())


def yardstick(m, self_pairs=True):
    """The per-position yardstick as AgingModel._build_bank samples it (same generator, same order); with
    self_pairs=False the pairs of two rows of one player are left out of each median."""
    rng = np.random.default_rng(0)
    out, ds = {}, []
    for pp in np.unique(m.pos):
        sel = np.where(m.pos == pp)[0]
        if len(sel) < 3:
            continue
        idx = rng.choice(len(sel), size=min(1200, len(sel)), replace=False)
        Xi, nm = m.Zw[sel][idx], m.names[sel][idx]
        sq = (Xi ** 2).sum(1)
        d2 = np.clip(sq[:, None] + sq[None, :] - 2 * Xi @ Xi.T, 0, None)
        iu = np.triu_indices(len(Xi), 1)
        d = np.sqrt(d2[iu])
        if not self_pairs:
            d = d[nm[iu[0]] != nm[iu[1]]]
        out[pp] = float(np.median(d)); ds.append(d)
    return out, float(np.median(np.concatenate(ds)))


def comps_only(curve):
    """B1: a shallow copy of the curve whose blend gives the comparables' weighted mean alone, and the league value only
    where no comparable has a value."""
    v = copy.copy(curve)

    def _shrunk(self, vals_col, cand, w, glob_target):
        m = ~np.isnan(vals_col); ww = w * m
        return float(np.sum(ww * np.where(m, vals_col, 0.0)) / ww.sum()) if ww.sum() > 0 else glob_target
    v._shrunk = types.MethodType(_shrunk, v)
    return v


# =========================================================================== the start, rebuilt from its parts
def start_parts(mod, pa):
    """Each player's own rate, comparables' level, step to the valuation season (path[g]) and walk (path[g + h]), from
    production's own _path: the pieces XNPV1._rate adds."""
    own = pa["own_82"].to_numpy(float)
    n = len(pa)
    cn, pg, walk = np.full(n, np.nan), np.full(n, np.nan), np.full((n, len(HS)), np.nan)
    league = np.full(n, np.nan)
    for i, (k, pos, al, g) in enumerate(zip(pa.index, pa["pos"].to_numpy(), pa["age_last"].to_numpy(float),
                                            pa["last_lag"].to_numpy(float))):
        if not np.isfinite(own[i]):
            continue
        c, path = mod._path(k, pos, al, int(g))
        g = int(g)
        cn[i], pg[i] = c, path[g]
        walk[i] = [path[g + min(h, SF.HMAX)] for h in HS]
        pp = "D" if pos == "D" else "F"
        league[i] = (mod.curve_.glevel.get((pp, int(al)), mod.league_rate_[pp]) if np.isfinite(al)
                     else mod.league_rate_[pp])
    return own, cn, pg, walk, league


def rate_from(parts, k=None, step=True, three=None, cn=None):
    """The rate per 82 for seasons 0-5 ahead: start = k x own + (1 - k) x comparables (+ the step), or the three-way
    blend; then the walk from the valuation season."""
    own, cn0, pg, walk, league = parts
    cn = cn0 if cn is None else cn
    if three is not None:
        a, b, c = three
        start = a * own + b * cn + c * league
    else:
        start = k * own + (1 - k) * cn0
    if step:
        start = start + pg
    return {h: start + (walk[:, j] - pg) for j, h in enumerate(HS)}


# =========================================================================== a full refit under a setting
def refit(iset, t0, subs, weights=None, anchors=None):
    SF.TRAIL_WEIGHTS = weights if weights is not None else ORIG_W
    SF._anchors = anchors if anchors is not None else ORIG_ANCHORS
    try:
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        return mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
    finally:
        SF.TRAIL_WEIGHTS, SF._anchors = ORIG_W, ORIG_ANCHORS


def rate_anchors(*args, **kw):
    """U1: the level the games share and the chance of playing read (tw_WAR) is his games-weighted rate per 82."""
    a = ORIG_ANCHORS(*args, **kw)
    if "own_82" in a.columns:
        a["tw_WAR"] = a["own_82"]
    return a.dropna(subset=["tw_WAR"]).reset_index(drop=True)


def share_line(pairs, pa, feats, h, extra=None):
    """A games-share line on production's training pairs, the prediction clipped to 0-1 as the build does."""
    P, A = pairs, pa
    if extra is not None:
        P, A = extra(pairs.copy()), extra(pa.copy())
    return np.clip(SF._apply(FTA.fit_share(P, h, feats), A[feats], A["tr_gp_share"]), 0.0, 1.0)


def share_logit(pairs, pa, feats, h):
    model = GPD.fit_share(pairs[pairs["h"] == h], feats, logit=True)
    fb = pa["tr_gp_share"].to_numpy(float)
    if model is None:
        return np.clip(fb, 0.0, 1.0)
    cols, beta = model[1]
    M = pa[cols].to_numpy(float); ok = np.isfinite(M).all(axis=1)
    out = fb.copy()
    out[ok] = 1.0 / (1.0 + np.exp(-(beta[0] + M[ok] @ beta[1:])))
    return out


def hinge(df):
    df["tw_hi1"] = np.clip(df["tw_WAR"] - 1.0, 0, None)
    return df


# =========================================================================== main
def main():
    C.banner("model_choices_current.py", SCRIPT_VERSION)
    log(f"{SCRIPT_VERSION}; skater_forecast v{SF.SCRIPT_VERSION}; scoring from {FTA.SCRIPT_VERSION}")
    bd, _ = PST.birthdate_source()
    table = PST.build(birthdate_csv=bd, verbose=False)
    path = str(SF.war_age_path()); SF.check_age_coverage(SF.war_age_path())
    log(f"age table: {path}")
    from contract_source import load_contracts
    contracts, _ = load_contracts()
    spans = PM.contract_spans(contracts)
    career_of = table.drop_duplicates("pkey").set_index("pkey")["career_key"].to_dict()
    last = int(table["syr"].max())
    res = table.groupby(["career_key", "syr"]).agg(GP=("GP", "sum"), y=("WAR_82", "first"), war=("WAR", "sum"),
                                                   share=("gp_share", "first"))
    f_noage = [f for f in SF.GP_FEATURES if f != "age_c2"]
    frames, e2_rows, grid_rows, notes = [], [], [], []
    for t0 in PAGES:
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        mod = SF.XNPV1().fit(iset.seasons, before=t0)
        a = mod._signed_anchor_frame(iset)
        subs = pd.DataFrame({"career_key": a.index.to_numpy()})
        pr = mod.predict(iset, subs, list(HS)).set_index(["career_key", "h"])
        pa = mod._page_anchors(iset, subs)
        pairs = mod._training_pairs(iset.seasons, t0, C.CANDIDATE_HORIZONS)
        base_curve = mod.curve_
        R, S, Pp, full = {}, {}, {}, {}

        # ---- the start: K, the step, the three-way blend (GUARD: the rebuild equals production's rate)
        parts = start_parts(mod, pa)
        prod = {h: mod._rate(pa, h) for h in HS}
        mine = rate_from(parts, k=SF.K_OWN)
        for h in HS:
            x, y = prod[h], mine[h]
            assert np.array_equal(np.isnan(x), np.isnan(y)) and np.nanmax(np.abs(x - y)) < TOL, f"{t0} +{h}: start rebuild"
        for k in KGRID:
            if abs(k - SF.K_OWN) > 1e-9:
                R[f"K own {int(round(100 * k))}%"] = rate_from(parts, k=k)
        R["NS no step to the valuation season"] = rate_from(parts, k=SF.K_OWN, step=False)
        mod.curve_, mod._paths = comps_only(base_curve), {}
        cn_pure = start_parts(mod, pa)[1]
        mod.curve_, mod._paths = base_curve, {}
        grid_rows.append(pd.DataFrame({"t0": t0, "career_key": pa.index, "own": parts[0], "cn_pure": cn_pure,
                                       "league": parts[4], "pg": parts[2]}))
        parts_pure = parts

        # ---- the aging curve: each version swaps the page's curve; the games share and the chance of playing stay
        dflt = departure_curve(path, t0)
        assert same_curve(dflt, base_curve), f"{t0}: the departure builder with the build's settings is not production's"
        ys, ypool = yardstick(base_curve)
        assert all(abs(ys[p] - base_curve.h_by_pos[p]) < TOL for p in ys) and abs(ypool - base_curve.h) < TOL, \
            f"{t0}: the yardstick recomputed is not production's"
        ys_ns, _ = yardstick(base_curve, self_pairs=False)
        notes.append(f"  {t0}: yardstick by position {', '.join(f'{p} {v:.4f}' for p, v in ys.items())}; pooled {ypool:.4f}; "
                     f"without self-pairs {', '.join(f'{p} {v:.4f}' for p, v in ys_ns.items())}; departures filled in "
                     f"{dflt.n_imputed:,}")
        curves = {}
        v = copy.copy(base_curve); v.h_by_pos = {p: base_curve.h for p in base_curve.h_by_pos}
        curves["A1 one yardstick for all players"] = v
        v = copy.copy(base_curve); v.h_by_pos = dict(ys_ns)
        curves["A2 yardstick without self-pairs"] = v
        curves["B1 comparable players alone"] = comps_only(base_curve)
        for r_ in C1:
            curves[f"C1 departed season at {r_:+.2f} WAR per 82"] = departure_curve(path, t0, rate=r_)
        curves["C2 players who came back filled in"] = departure_curve(path, t0, returners=True)
        curves["C6 departed season at 82 games"] = departure_curve(path, t0, gp_rule="82")
        curves["C4 no departed seasons filled in"] = departure_curve(path, t0, impute=False)
        curves["C3 short next seasons filled in"] = departure_curve(path, t0, short=True)
        for arm, cv in curves.items():
            mod.curve_, mod._paths = cv, {}
            R[arm] = {h: mod._rate(pa, h) for h in HS}
        mod.curve_, mod._paths = base_curve, {}
        for kk in BK:
            AC.SHRINK_K = kk
            mod._paths = {}
            try:
                R[f"BK league weight {kk:g}"] = {h: mod._rate(pa, h) for h in HS}
            finally:
                AC.SHRINK_K = ORIG_SHRINK
                mod._paths = {}

        # ---- the games share
        S["D2 games share without age squared"] = {h: share_line(pairs, pa, f_noage, h) for h in HS}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            S["D1 games share as a fractional logit"] = {h: share_logit(pairs, pa, list(SF.GP_FEATURES), h) for h in HS}
        S["U2 games share + total above one win"] = {h: share_line(pairs, pa, list(SF.GP_FEATURES) + ["tw_hi1"], h, hinge)
                                                     for h in HS}
        # ---- the chance of playing: contract x quality
        n = mod.N_SEASONS
        part = GPD.QualityContractModel(contracts, exclude=tuple(mod.PART_EXCLUDE), contract_state=mod.CONTRACT_STATE).fit(
            iset.seasons, t0, anchors_fn=lambda p: SF._anchors(p, n), horizons=mod.fitted_horizons_)
        keep = mod.part_; mod.part_ = part
        Pp["E3 contract x quality"] = {h: mod._p_play(pa, subs, h) for h in HS}
        mod.part_ = keep
        notes.append(f"  {t0}: E3's term entered the chance of playing at seasons ahead "
                     f"{[h for h in HS if 'uc_x_level' in part.used_.get(h, [])]}")

        # ---- full refits: the weights, and quality read as a rate
        for arm, w in WEIGHTS.items():
            full[f"W {arm}"] = refit(iset, t0, subs, weights=w)
        full["U1 quality as rate per 82 (share and playing)"] = refit(iset, t0, subs, anchors=rate_anchors)

        # ---- E2: late-signed contracts starting this season
        if t0 >= int(spans["end_yr"].min()):
            jul1 = pd.Timestamp(year=t0, month=7, day=1)
            late = spans[(spans["start_yr"] == t0) & (spans["signed"] > jul1)
                         & (spans["signed"] < pd.Timestamp(year=t0 + 1, month=7, day=1))].copy()
            late["career_key"] = late["pkey"].map(career_of)
            late = late[late["career_key"].isin(set(pa.index))].sort_values("signed").drop_duplicates("career_key")
            if len(late):
                hs = list(range(0, min(int(late["end_yr"].max()) - t0, max(mod.fitted_horizons_)) + 1))
                sig = mod.p_play_signed(iset, late["career_key"].tolist(), hs, late["signed"].tolist())
                j1 = mod.p_play_signed(iset, late["career_key"].tolist(), hs, [jul1] * len(late))
                for h in hs:
                    s = t0 + h
                    cov = (late["end_yr"].to_numpy() >= s) & (s <= last)
                    if not cov.any():
                        continue
                    rr = res.reindex(pd.MultiIndex.from_arrays([late["career_key"], np.full(len(late), s)]))
                    played = (np.nan_to_num(rr["GP"].to_numpy()) >= C.PARTICIPATION_GP).astype(float)
                    e2_rows.append(pd.DataFrame({"career_key": late["career_key"].to_numpy()[cov], "t0": t0, "h": h,
                                                 "played": played[cov], "p_jul1": j1[h][cov], "p_signed": sig[h][cov]}))

        # ---- the rows
        rows = []
        for j, h in enumerate(HS):
            if t0 + h > last:
                continue
            ph = pr.xs(h, level="h").reindex(pa.index)
            rr = res.reindex(pd.MultiIndex.from_arrays([pa.index, np.full(len(pa), t0 + h)]))
            gp = np.nan_to_num(rr["GP"].to_numpy())
            d = pd.DataFrame({"career_key": pa.index, "t0": t0, "h": h, "gp": gp, "y82": rr["y"].to_numpy(),
                              "share_act": np.where(gp > 0, rr["share"].to_numpy(), np.nan),
                              "war_act": np.where(gp > 0, rr["war"].to_numpy(), 0.0),
                              "played": (gp >= C.PARTICIPATION_GP).astype(float), "age": pa["age"].to_numpy(float),
                              "r|base": ph["rate_82"].to_numpy(), "s|base": ph["gp_share"].to_numpy(),
                              "p|base": ph["p_play"].to_numpy(),
                              "own": parts_pure[0], "cn_pure": cn_pure, "league": parts_pure[4], "pg": parts_pure[2],
                              "walk": parts_pure[3][:, j]})
            for arm, v in R.items():
                d[f"r|{arm}"] = v[h]
            for arm, v in S.items():
                d[f"s|{arm}"] = v[h]
            for arm, v in Pp.items():
                d[f"p|{arm}"] = v[h]
            for arm, p2 in full.items():
                q = p2.xs(h, level="h").reindex(pa.index)
                d[f"r|{arm}"], d[f"s|{arm}"], d[f"p|{arm}"] = (q["rate_82"].to_numpy(), q["gp_share"].to_numpy(),
                                                               q["p_play"].to_numpy())
            rows.append(d)
        frames.append(pd.concat(rows, ignore_index=True))
        log(f"  page {t0}: {len(pa):,} players")
    log("\n".join(notes))

    D = pd.concat(frames, ignore_index=True)
    # ---- GUARD: the build's figures, as forecast_term_audit.py gives them today
    ok_ = ((D["gp"] > 0) & np.isfinite(D["y82"]) & np.isfinite(D["r|base"])).to_numpy()
    e_, w_ = (D["r|base"] - D["y82"]).to_numpy(), np.where(ok_, D["gp"], 0.0)
    h0, hp = (D["h"] == 0).to_numpy(), (D["h"] > 0).to_numpy()
    got = {"start": FTA.wrmse(e_[ok_ & h0], w_[ok_ & h0]), "whole": FTA.wrmse(e_[ok_ & hp], w_[ok_ & hp]),
           "war": float(np.sqrt(np.mean((D["p|base"] * D["r|base"] * D["s|base"] - D["war_act"]) ** 2))), "rows": len(D)}
    bad = [k for k, v in RECORDED.items() if (got[k] != v if k == "rows" else abs(round(got[k], 4) - v) > 1e-9)]
    log(f"\nGUARD: rows {got['rows']:,}; start {got['start']:.4f}, one to five ahead {got['whole']:.4f}, season WAR "
        f"{got['war']:.4f}, against forecast_term_audit.py's {RECORDED['start']}, {RECORDED['whole']}, {RECORDED['war']} "
        f"on {RECORDED['rows']:,} rows: {'PASS' if not bad else 'FAIL ' + str(bad)}")
    if bad:
        raise RuntimeError("the build is not reproduced; results not read")

    # ---- the three-way blend: chosen on the starting level's error, then scored in full
    st = ok_ & h0 & np.isfinite(D["own"].to_numpy())
    best, grid = None, []
    for a_ in np.round(np.arange(0.0, 1.0001, 0.05), 2):
        for b_ in np.round(np.arange(0.0, 1.0001 - a_ + 1e-9, 0.05), 2):
            c_ = round(1.0 - a_ - b_, 2)
            s_ = a_ * D["own"] + b_ * D["cn_pure"] + c_ * D["league"] + D["pg"]
            r_ = FTA.wrmse((s_ - D["y82"]).to_numpy()[st], w_[st])
            grid.append((a_, b_, c_, r_))
            if best is None or r_ < best[3]:
                best = (a_, b_, c_, r_)
    a_, b_, c_, _ = best
    s_all = a_ * D["own"] + b_ * D["cn_pure"] + c_ * D["league"] + D["pg"]
    arm3 = f"3W best three-way {a_:.2f}/{b_:.2f}/{c_:.2f}"
    D[f"r|{arm3}"] = (s_all + D["walk"] - D["pg"]).to_numpy()
    log(f"\nTHE THREE-WAY BLEND (own / comparables without the league / league by position and age), chosen on the "
        f"starting level: best {a_:.2f} / {b_:.2f} / {c_:.2f}, RMSE {best[3]:.4f}; five best cells: "
        + "; ".join(f"{x[0]:.2f}/{x[1]:.2f}/{x[2]:.2f} {x[3]:.4f}" for x in sorted(grid, key=lambda x: x[3])[:5])
        + f"; comparables and own only (c = 0) best "
        f"{min(x[3] for x in grid if x[2] == 0):.4f}; the build (65/35 with the league inside) {got['start']:.4f}")

    arms = sorted({c.split("|", 1)[1] for c in D.columns if "|" in c} - {"base"})
    for arm in arms:
        for part in ("r", "s", "p"):
            if f"{part}|{arm}" not in D:
                D[f"{part}|{arm}"] = D[f"{part}|base"]
    order = (["base"] + [a for a in arms if a.startswith("W ")] + [f"K own {int(round(100 * k))}%" for k in K_REPORT]
             + [a for a in arms if a.startswith(("K own", "NS", "3W")) and a not in
                [f"K own {int(round(100 * k))}%" for k in K_REPORT]]
             + [a for a in arms if a[:2] in ("A1", "A2", "B1", "BK", "C1", "C2", "C6", "C4", "C3")]
             + [a for a in arms if a[:2] in ("D2", "D1", "U1", "U2", "E3")])
    assert sorted(order) == sorted(["base"] + arms), "an arm is missing from the report order"
    base_ok = np.isfinite(D["r|base"].to_numpy())
    allv = [x for x in order if np.isfinite(D.loc[base_ok, f"r|{x}"]).all()]
    rest = [x for x in order if x not in allv]
    out = FTA.evaluate(D[base_ok].reset_index(drop=True), allv,
                       f"ALL {int(base_ok.sum()):,} ROWS THE BUILD ANSWERS (versions that answer every one of them)")
    for x in rest:
        m_ = base_ok & np.isfinite(D[f"r|{x}"].to_numpy())
        out += FTA.evaluate(D[m_].reset_index(drop=True), ["base", x],
                            f"THE {int(m_.sum()):,} ROWS {x} ANSWERS ({int(base_ok.sum() - m_.sum()):,} of the build's not)")

    # ---- the curve versions by age at the valuation season, one to five ahead
    Db = D[base_ok].reset_index(drop=True)
    pl = ((Db["gp"] > 0) & np.isfinite(Db["y82"])).to_numpy() & (Db["h"] > 0).to_numpy()
    wb = np.where(pl, Db["gp"], 0.0)
    bands = {"under 22": Db["age"] < 22, "22-34": (Db["age"] >= 22) & (Db["age"] < 35), "35 and over": Db["age"] >= 35}
    log("\nTHE AGING-CURVE VERSIONS BY AGE AT THE VALUATION SEASON: one to five ahead, WAR per 82 (games-weighted); rows")
    log(f"  {'version':<44}" + "".join(f"{b:>14}" for b in bands))
    log(f"  {'(player-seasons played, one to five ahead)':<44}" + "".join(f"{int((pl & m.to_numpy()).sum()):>14,}"
                                                                       for m in bands.values()))
    for x in ["base"] + [a for a in order if a[:2] in ("A1", "A2", "B1", "BK", "C1", "C2", "C6", "C4", "C3")]:
        e = (Db[f"r|{x}"] - Db["y82"]).to_numpy()
        log(f"  {x:<44}" + "".join(f"{FTA.wrmse(e[pl & m.to_numpy()], wb[pl & m.to_numpy()]):>14.4f}"
                                   for m in bands.values()))

    # ---- E2
    E2 = pd.concat(e2_rows, ignore_index=True)
    yy = E2["played"].to_numpy()
    lj, ls = FTA.logloss(E2["p_jul1"].to_numpy(), yy), FTA.logloss(E2["p_signed"].to_numpy(), yy)
    codes, uniq = pd.factorize(E2["career_key"])
    rng = np.random.default_rng(FTA.SEED)
    sj, ss_ = np.bincount(codes, lj, len(uniq)), np.bincount(codes, ls, len(uniq))
    p_sig = 1.0 - float(np.mean([ss_[ix].sum() < sj[ix].sum()
                                 for ix in (rng.integers(0, len(uniq), len(uniq)) for _ in range(FTA.NBOOT))]))
    log(f"\nE2: contracts signed after July 1 of their first season, pages {int(E2['t0'].min())}-{int(E2['t0'].max())}: "
        f"{E2.groupby(['career_key', 't0']).ngroups:,} contracts, {len(E2):,} contract-seasons, "
        f"{E2['career_key'].nunique():,} players; played {yy.mean():.3f}")
    log(f"  read at July 1:      mean chance {E2['p_jul1'].mean():.3f}, log loss {lj.mean():.4f}, Brier "
        f"{np.mean((E2['p_jul1'] - yy) ** 2):.4f}")
    log(f"  read at the signing: mean chance {E2['p_signed'].mean():.3f}, log loss {ls.mean():.4f}, Brier "
        f"{np.mean((E2['p_signed'] - yy) ** 2):.4f}")
    log(f"  p (one-sided, 2,000 redraws of players) that reading at the signing is not better: {p_sig:.4f}")

    sc = pd.DataFrame(out)
    e2s = pd.DataFrame([{"rows_set": "E2 late-signed contracts", "version": "read at July 1", "logloss": lj.mean(),
                         "rows": len(E2), "mean_p": E2["p_jul1"].mean(), "played": yy.mean()},
                        {"rows_set": "E2 late-signed contracts", "version": "read at the signing", "logloss": ls.mean(),
                         "rows": len(E2), "mean_p": E2["p_signed"].mean(), "played": yy.mean(),
                         "p_build_better_logloss": p_sig}])
    pd.concat([sc, e2s], ignore_index=True).to_csv(C.out_path("model_choices_current_scores.csv"), index=False)
    C.record_inspection("model_choices_current.py", "pages", PAGES,
                        "the forecast's tested choices on today's model (Thomas 2026-11-25: All five now)")
    p = C.out_path("model_choices_current_log.txt")
    p.write_text("\n".join(C._LOG + LOG) + "\n", encoding="utf-8")
    log(f"\nwritten: {p}")


if __name__ == "__main__":
    main()
