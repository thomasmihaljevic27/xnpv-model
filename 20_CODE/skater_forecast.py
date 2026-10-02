"""skater_forecast.py -- xNPV 1, the skater forecast production values contracts on.

PRODUCTION (20_CODE). Decision D33 (2026-09-30) adopted this model; its one
confirmatory run on the 2022-2025 pages passed (season-WAR RMSE 0.9001 against
xNPV 0's 0.9724, lower in 2,000 of 2,000 player resamples, 2026-10-02, on the
rebuilt age table). Promoted 2026-10-02 from the rebuild tree, where it was
`star_candidates.XNPV1` ("Model 6"): `candidate(gp=True, contracts=True)` on
`obvious_fixes.ObviousFixes` on `ability_forecast.A1HingeExposure`.

WHAT IT FORECASTS, for a player valued at page t0 and each season h ahead
(h = 0 is the valuation season itself, which has not been played on 1 July):
    rate_82   WAR per 82 games if he plays
    gp_share  the share of his team's games he plays, if he plays
    p_play    the chance he plays at all that season (one game or more)
    so expected WAR = p_play x rate_82 x gp_share, and the WAR if he plays is
    rate_82 x gp_share.

HOW, step by step (each step is the rebuild's code, copied, not rewritten):
    1. THE START. A three-season weighted trailing total, with the weights'
       decay fitted on earlier seasons (BaseModel._fit_decay), pulled toward
       the league by a fitted line (RATE_FEATURES; games-weighted least
       squares on pairs whose outcome finished before the page).
    2. THE AGING WALK. The comparable-player curve, 20_CODE/aging_curve.py
       (D3's comparables, settings unchanged), fitted on seasons before the
       page. Its yearly changes are ADDED to the start (not multiplied), read
       from the player's profile one age back, then two, as production's
       ratio path does. Players who left the league enter the curve at
       replacement level for the season they missed (imputed_aging_model).
       No replacement floor is applied to a negative start (D12 v3 is
       superseded for skaters by D33).
    3. THE GAMES SHARE. A fitted line per horizon on the trailing share,
       position, experience, age AND the player's level (GP_FEATURES), so a
       star and a depth player with the same recent share are not forecast
       the same share.
    4. THE CHANCE OF PLAYING. participation_model.ParticipationModel, reading
       contract status where the vendor export's coverage is complete
       ("observable"), the before/after-2018 indicator left out. Read at
       1 July of the page for the page forecast, and at a contract's signing
       for a contract valuation (p_play_signed). It replaces the exit-hazard
       survival chain for skaters (D18 superseded for skaters by D33).
    5. PAST THE FITTED RANGE. Seasons a page cannot fit (fewer than
       MIN_HORIZON_PAIRS training pairs) continue the league-wide decay
       measured between the last two fitted seasons (predict_beyond_fit).

WHAT WAS LEFT OUT IN PROMOTION, and why it changes nothing
    The rebuild class also fitted the rebuilt model's aging EQUATION
    (aging_additive.AdditiveAging) twice and a rate line for every horizon,
    and used neither: the comparable-player walk replaced the equation and only
    the valuation-season rate line feeds the walk. They are not fitted here.
    25_TESTS/xnpv1_promotion_check.py shows this module's forecasts equal the
    rebuild class's on the development pages.

THE FLOOR SPREAD (decision 3 of the migration plan, Thomas 2026-10-02)
    WAR_IF_PLAYS_MAE: xNPV 1's own mean absolute miss of the WAR-if-plays,
    seasons played, every row it forecasts on the development pages 2015-2021
    (40,510 forecasts; cloud, 2026-10-02). contract_npv turns it into the
    spread behind the league-minimum floor (MAE x 1.2533, as production does),
    the valuation season included. Held flat past five seasons.

NEEDS: OUTPUT_DIR/WAR_with_age.csv at 99%+ birthdate coverage (age_join.py),
and the PuckPedia contract export as CSV in SOURCE_DIR (refuses without it).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forecast_config as C
from participation_model import ParticipationModel

SCRIPT_VERSION = "1.0"
MODEL_NAME = "xNPV 1"

W_T1, W_T2 = 0.6, 0.4    # the locked recency weighting; 0.4/0.6 is the starting decay
STALE_LOOKBACK = 3       # matches forecast_harness.ACTIVE_WINDOW
HMAX = C.MAX_HORIZON     # how far the comparables walk is tabulated

# The fitted start's terms (ability_forecast.A1HingeExposure.FEATURES).
RATE_FEATURES = ["tw_WAR", "tw_hi1", "tw_x_exposure", "one_season", "is_D",
                 "exp_seasons", "age_c", "age_c2"]
# The games-share line's terms (star_candidates.GP_WITH_LEVEL).
GP_FEATURES = ["tr_gp_share", "is_D", "exp_seasons", "age_c", "tw_WAR", "tw_hi1"]

# xNPV 1's own WAR-if-plays misses by season ahead (see the docstring).
WAR_IF_PLAYS_MAE = {0: 0.6730, 1: 0.7486, 2: 0.7991, 3: 0.8516, 4: 0.8792, 5: 0.8926}
MAE_TO_SD = 1.2533       # SD = MAE * sqrt(pi/2) for a normal, production's conversion

MIN_AGE_COVERAGE = 0.99  # the age table must carry the Elite Prospects birthdates


def war_if_plays_sd(k: int) -> float:
    """The spread of the WAR-if-plays k seasons ahead (k = 0 is the valuation
    season), for the expected value of the league-minimum floor."""
    return WAR_IF_PLAYS_MAE[min(max(int(k), 0), max(WAR_IF_PLAYS_MAE))] * MAE_TO_SD


# --------------------------------------------------------------------------- the anchors
def _anchors(played: pd.DataFrame, n_seasons: int = 2,
             decay: float = W_T2 / W_T1, stale: bool = True,
             cols: list | None = None) -> pd.DataFrame:
    """For every player and every season t0 he could have been valued at, the
    trailing facts from the seasons before t0 only (copied from
    ability_forecast._anchors). Structurally incapable of seeing season t0:
    every part is built by adding a POSITIVE lag to the season it came from."""
    cols = list(C.COMPONENTS_MODEL + ["WAR"] if cols is None else cols)
    rate_cols = [c + "_82" for c in cols]
    keep = ["career_key", "pkey", "pos", "syr", "GP", "gp_share", "toi_pg",
            "exp_seasons", "exp_censored", "age", "has_age"] + cols + rate_cols
    s = played[keep]
    lags = list(range(1, n_seasons + 1))
    parts = []
    for lag in lags:
        q = s.assign(t0=s["syr"] + lag).set_index(["career_key", "t0"])
        parts.append(q.add_suffix(f"_{lag}"))
    m = pd.concat(parts, axis=1).reset_index()

    # Geometric weights: the most recent season 1, the one before `decay`, ...
    w = np.array([decay ** (i - 1) for i in lags], dtype=float)
    avail = np.column_stack([m[f"GP_{lag}"].notna().to_numpy() for lag in lags])

    out = pd.DataFrame({"career_key": m["career_key"], "t0": m["t0"]})
    out["n_seasons"] = avail.sum(axis=1)
    out["one_season"] = (out["n_seasons"] == 1).astype(float)
    out["pkey"] = _first_available(m, "pkey", lags)
    out["pos"] = _first_available(m, "pos", lags)
    out["is_D"] = (out["pos"] == "D").astype(float)
    for c in ["exp_seasons", "exp_censored", "has_age", "toi_pg"]:
        out[c] = _first_available(m, c, lags)

    # Age AT THE VALUATION SEASON: each lag stepped forward by its own distance.
    aged = [m[f"age_{lag}"] + float(lag) for lag in lags]
    age = aged[0]
    for nxt in aged[1:]:
        age = age.fillna(nxt)
    out["age"] = age
    out["age_c"] = out["age"] - 27.0          # centred near the peak
    out["age_c2"] = out["age_c"] ** 2

    def blend(col):
        """Weighted average over the seasons the player actually has,
        renormalised over what is available."""
        vals = np.column_stack([m[f"{col}_{lag}"].to_numpy(float) for lag in lags])
        ok = np.isfinite(vals)
        ww = np.where(ok, w[None, :], 0.0)
        tot = ww.sum(axis=1)
        num = np.where(ok, np.nan_to_num(vals) * ww, 0.0).sum(axis=1)
        return np.where(tot > 0, num / np.where(tot > 0, tot, 1.0), np.nan)

    for c in cols:
        out["tw_" + c] = blend(c)              # trailing weighted TOTAL
        out["tr_" + c] = blend(c + "_82")      # trailing weighted RATE
    out["tr_gp_share"] = blend("gp_share")

    # Evidence behind the anchor, in games; NOT renormalised, so a short
    # history counts as less evidence.
    gp = np.column_stack([m[f"GP_{lag}"].fillna(0).to_numpy(float) for lag in lags])
    out["exposure_gp"] = (gp * w[None, :]).sum(axis=1) / w.sum()
    out["stale_history"] = 0.0

    # Returning players: an anchor from the most recent qualifying season alone
    # when the window holds none, tagged, added only where missing.
    if stale and n_seasons < STALE_LOOKBACK:
        deep = _anchors(played, STALE_LOOKBACK, decay, stale=False, cols=cols)
        have = pd.MultiIndex.from_arrays([out["career_key"], out["t0"]])
        want = pd.MultiIndex.from_arrays([deep["career_key"], deep["t0"]])
        add = deep[~want.isin(have)].copy()
        if len(add):
            add["stale_history"] = 1.0
            out = pd.concat([out, add], ignore_index=True)

    # The level terms the fitted start and the games share read.
    out["tw_hi1"] = np.clip(out["tw_WAR"] - 1.0, 0, None)
    out["tw_hi2"] = np.clip(out["tw_WAR"] - 2.0, 0, None)
    out["tw_x_exposure"] = out["tw_WAR"] * (out["exposure_gp"] / 82.0)
    return out.dropna(subset=["tw_WAR"]).reset_index(drop=True)


def _first_available(m: pd.DataFrame, col: str, lags) -> pd.Series:
    """The value from the most recent lag that has one."""
    out = m[f"{col}_{lags[0]}"]
    for lag in lags[1:]:
        out = out.fillna(m[f"{col}_{lag}"])
    return out


# --------------------------------------------------------------------------- fitting helpers
def _ols(X: pd.DataFrame, y: pd.Series, w: pd.Series | None = None):
    """Least squares with an intercept on complete rows; None if thin or
    rank-deficient (the caller then falls back to the trailing value). `w` is
    a precision weight, the games behind each rate."""
    parts = [X, y.rename("_y")]
    if w is not None:
        parts.append(w.rename("_w"))
    d = pd.concat(parts, axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < 50:
        return None
    A = np.column_stack([np.ones(len(d)), d[X.columns].to_numpy(float)])
    b = d["_y"].to_numpy(float)
    if w is not None:
        rw = np.sqrt(np.clip(d["_w"].to_numpy(float), 0.0, None))
        if not rw.any():
            return None
        A, b = A * rw[:, None], b * rw
    try:
        beta, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return list(X.columns), beta


def _rate_weight(g: pd.DataFrame) -> pd.Series | None:
    """The games behind each rate observation, or None when weighting is off."""
    if not C.RATE_WEIGHT_BY_GAMES or "y_gp" not in g.columns:
        return None
    return g["y_gp"].clip(lower=0.0)


def _apply(coef, X: pd.DataFrame, fallback: pd.Series) -> np.ndarray:
    """Apply a fitted line, falling back row-wise where a feature is missing."""
    fb = np.asarray(fallback, dtype=float)
    if coef is None:
        return fb
    cols, beta = coef
    M = X[cols].to_numpy(float)
    ok = np.isfinite(M).all(axis=1)
    out = fb.copy()
    out[ok] = beta[0] + M[ok] @ beta[1:]
    return out


# --------------------------------------------------------------------------- the age table
def war_age_path() -> Path:
    return Path(C.PROD_OUTPUT_DIR) / "WAR_with_age.csv"


_age_checked: dict = {}


def check_age_coverage(path: Path) -> float:
    """Refuse an age table without the Elite Prospects birthdates. The laptop's
    copy sat at 70.9% from 2026-07-28 to 2026-10-02 and every run on it fitted
    the comparables pool without the older careers, silently."""
    path = Path(path)
    if not path.exists():
        raise RuntimeError(f"{path} is missing; run 20_CODE/age_join.py first")
    key = (str(path), path.stat().st_mtime)
    if key not in _age_checked:
        cov = float(pd.read_csv(path, usecols=["birthdate"])["birthdate"].notna().mean())
        if cov < MIN_AGE_COVERAGE:
            raise RuntimeError(
                f"{path} has a birthdate on only {cov:.1%} of season rows (a rebuilt table "
                "carries 99.9%). Check age_join_log.txt for 'Pass 4 EP matches', re-run "
                "20_CODE/age_join.py, then this.")
        C.log(f"  production age table: birthdate on {cov:.2%} of season rows ({path})")
        _age_checked[key] = cov
    return _age_checked[key]


def imputed_aging_model(path: str, before: int):
    """Production's comparable-player AgingModel (aging_curve.py) fitted on
    seasons before the page, with departures entered at replacement level
    (copied from obvious_fixes.imputed_aging_model). A pool season at age a
    whose player has NO row at age a+1 (he did not appear), with that season
    finished before the page, gets an imputed next level of (rate + 0) / 2,
    the pool's own two-season smoothing; the league-average changes are
    recomputed with the imputed changes included. A player who played at a+1
    under 20 games is NOT a departure."""
    import aging_curve as AC

    class ImputedAgingModel(AC.AgingModel):
        def __init__(self, war_age_path, before):
            super().__init__(war_age_path, before=before)
            df = pd.read_csv(war_age_path)
            df["syr"] = df["Season"].str.split("-").str[0].astype(int) + 2000
            df = df[df["syr"] < int(before)].copy()
            df["career"] = df["Player"].map(AC.career_key)
            df = df[df["age"].notna()]
            present = set(zip(df["career"], df["age"].astype(int)))
            syr_of = (df.groupby(["career", df["age"].astype(int)])["syr"].max().to_dict())
            self.n_imputed = 0
            imputed = {}
            for name, p in self.players.items():
                for s in p["seasons"]:
                    a = s["age"]
                    if (a + 1) in p["sm"] or (name, a + 1) in present:
                        continue                      # he played at a+1 (any games)
                    sy = syr_of.get((name, a))
                    if sy is None or sy + 1 >= int(before):
                        continue                      # the next season is not over yet
                    nxt = (s["w82"] + 0.0) / 2.0 if AC.WIN > 1 else 0.0
                    imputed[(name, a)] = nxt - p["sm"][a]
            self.imputed_ = imputed
            self.n_imputed = len(imputed)
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

    return ImputedAgingModel(path, before)


# --------------------------------------------------------------------------- the model
class XNPV1:
    """xNPV 1. `fit(table, before)` uses only pairs whose OUTCOME season is
    before `before`; `predict(iset, subs, horizons)` answers the fitted
    horizons; `predict_beyond_fit` extends past them by a declared rule;
    `p_play_signed` reads contract status at a contract's own signing."""

    name = MODEL_NAME
    N_SEASONS = 3
    DECAY = W_T2 / W_T1
    DECAY_GRID = np.array([0.40, 0.50, 0.60, 0.667, 0.75, 0.85, 1.00])
    FITTED_HORIZONS = C.FITTED_HORIZONS
    FEATURES = RATE_FEATURES
    CONTRACT_STATE = "observable"
    PART_EXCLUDE = ("contract_unknown",)
    _curves: dict = {}      # one comparables curve per page, shared across instances

    # ---- fit -----------------------------------------------------------------
    def fit(self, table: pd.DataFrame, before: int) -> "XNPV1":
        self.before = before
        self.fitted_horizons_ = None
        self.decay_ = self._fit_decay(table, before)
        pairs = self._training_pairs(table, before, C.CANDIDATE_HORIZONS)

        # 1. The start: the valuation-season rate line (the only one the walk reads).
        g0 = pairs[pairs["h"] == 0]
        r = g0.dropna(subset=["y_rate"])
        self.coef_ = {0: (_ols(r[self.FEATURES], r["y_rate"], _rate_weight(r))
                          if len(r) > 50 else None)}

        # 3. The games share, one line per horizon, reading the player's level.
        self.gp_coef_ = {}
        for h, g in pairs.groupby("h"):
            s = g.dropna(subset=["y_gp_share"] + GP_FEATURES)
            self.gp_coef_[h] = _ols(s[GP_FEATURES], s["y_gp_share"]) if len(s) > 50 else None

        # 4. The chance of playing, reading contract status. Refuses without the
        # export: without it the model silently becomes the no-contract twin.
        from contract_source import load_contracts
        try:
            contracts, _ = load_contracts()
        except Exception as e:                    # noqa: BLE001
            raise RuntimeError(
                f"xNPV 1 needs the contract export ({type(e).__name__}: {e}); expected at "
                f"{C.F_CONTRACTS_CSV}") from e
        n, d = self.N_SEASONS, self.decay_
        self.part_ = ParticipationModel(
            contracts, exclude=tuple(self.PART_EXCLUDE),
            contract_state=self.CONTRACT_STATE).fit(
            table, before, anchors_fn=lambda p: _anchors(p, n, d),
            horizons=self.fitted_horizons_)

        # 2. The comparable-player curve for this page.
        path = war_age_path()
        check_age_coverage(path)
        if before not in self._curves:
            self._curves[before] = imputed_aging_model(str(path), before)
        self.curve_ = self._curves[before]
        self._cum = {}
        return self

    def _fit_decay(self, table: pd.DataFrame, before: int) -> float:
        """Pick the trailing weights' decay on the rolling window: score each
        candidate's blended rate against the season it anchors, outcomes
        completed before the page only, errors weighted by the outcome's games."""
        s = table[table["GP"] >= C.MIN_GP]
        act = s.set_index(["career_key", "syr"])
        best, best_sse = self.DECAY, np.inf
        for d in self.DECAY_GRID:
            a = _anchors(s, self.N_SEASONS, float(d))
            a = a[a["t0"] < before]
            ix = pd.MultiIndex.from_arrays([a["career_key"], a["t0"]])
            y = act["WAR_82"].reindex(ix).to_numpy()
            gp = act["GP"].reindex(ix).to_numpy()
            ok = np.isfinite(y) & np.isfinite(a["tr_WAR"].to_numpy())
            if ok.sum() < 200:
                continue
            e = a["tr_WAR"].to_numpy()[ok] - y[ok]
            sse = float((gp[ok] * e ** 2).sum())
            if sse < best_sse:
                best, best_sse = float(d), sse
        return best

    def _record_fitted_horizons(self, pairs: pd.DataFrame) -> None:
        """The horizons this page can carry: those with MIN_HORIZON_PAIRS pairs."""
        n = pairs.dropna(subset=["y_rate"]).groupby("h").size()
        self.fitted_horizons_ = tuple(
            sorted(int(h) for h, k in n.items() if k >= C.MIN_HORIZON_PAIRS))

    def _training_pairs(self, table: pd.DataFrame, before: int, horizons) -> pd.DataFrame:
        """Every (inputs at t, outcome at t+h) pair whose OUTCOME completed
        before `before`, the one place training data is built."""
        s = table[table["GP"] >= C.MIN_GP]
        anchors = _anchors(s, self.N_SEASONS, self.decay_)
        out = []
        for h in horizons:
            a = anchors.copy()
            a["season"] = a["t0"] + h
            a["h"] = h
            a = a[a["season"] < before]          # the rule, in one line
            out.append(a)
        pairs = pd.concat(out, ignore_index=True)
        act = table.set_index(["career_key", "syr"])
        ix = pd.MultiIndex.from_arrays([pairs["career_key"], pairs["season"]])
        pairs["y_war"] = act["WAR"].reindex(ix).to_numpy()
        pairs["y_rate"] = act["WAR_82"].reindex(ix).to_numpy()
        pairs["y_gp_share"] = act["gp_share"].reindex(ix).to_numpy()
        pairs["y_gp"] = act["GP"].reindex(ix).to_numpy()
        pairs["y_played"] = np.nan_to_num(pairs["y_gp"]) >= C.PARTICIPATION_GP
        self._record_fitted_horizons(pairs)
        return pairs

    # ---- predict ---------------------------------------------------------------
    def _page_anchors(self, iset, subs) -> pd.DataFrame:
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        return a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])

    def predict(self, iset, subs, horizons) -> pd.DataFrame:
        self._guard_horizons(horizons)
        a = self._page_anchors(iset, subs)
        rate0 = _apply(self.coef_.get(0), a[self.FEATURES], a["tw_WAR"])
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = self._walk(r, rate0, a, h)
            gp = _apply(self.gp_coef_.get(h), a[GP_FEATURES], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = self._p_play(a, subs, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)

    def _changes(self, key, age, is_d):
        """Cumulative change from `age` to age+k, k = 0..HMAX, and its source:
        the player's own comparables (read one age back, then two), else the
        league-average curve for his position."""
        m = self.curve_
        ck = (key, age)
        if ck in self._cum:
            return self._cum[ck]
        max_age = m.AMIN + m.nages - 1
        out, src = None, None
        if key in m.players:
            for lag in (1, 2):
                base = age - lag
                hz = min(HMAX + lag, max_age - base - 1)
                if hz < lag:
                    continue
                try:
                    tr = m.project(key, current_age=base, horizon=hz)
                except (ValueError, KeyError, IndexError):
                    continue
                lv = dict(zip(tr["age"].astype(int), tr["projected_war_per_82"]))
                if age not in lv:
                    continue
                out = [lv[age + k] - lv[age] if (age + k) in lv else np.nan
                       for k in range(HMAX + 1)]
                src = "own_comparables"
                break
        if out is None:
            pos = "D" if is_d else "F"
            out, c = [0.0], 0.0
            for k in range(1, HMAX + 1):
                g = m.gdelta.get((pos, age + k - 1))
                c = c + g if g is not None else np.nan
                out.append(c)
            src = "league_curve"
        for k in range(1, HMAX + 1):                  # past the oldest age: hold flat
            if not np.isfinite(out[k]):
                out[k] = out[k - 1]
        self._cum[ck] = (np.array(out, dtype=float), src)
        return self._cum[ck]

    def _walk(self, r, rate0, a, h):
        """The start plus the comparables' cumulative change; a player with no
        age is carried flat."""
        rate0 = np.asarray(rate0, dtype=float)
        if h == 0:
            return rate0
        out = rate0.copy()
        ages = a["age"].to_numpy(float)
        is_d = a["is_D"].to_numpy(float)
        keys = r["career_key"].to_numpy()
        for i in range(len(out)):
            if not (np.isfinite(ages[i]) and np.isfinite(rate0[i])):
                continue
            cum, _ = self._changes(keys[i], int(round(ages[i])), bool(is_d[i]))
            out[i] = rate0[i] + cum[min(h, HMAX)]
        return out

    # ---- participation -----------------------------------------------------
    @property
    def reads_contracts(self) -> bool:
        return getattr(self.part_, "spans", None) is not None

    def _part_predict(self, rows, h, as_of=None):
        return self.part_.predict(rows, h, as_of=as_of)

    def _p_play(self, a, subs, h):
        p = self._part_predict(a.reset_index(), h)
        p = p[~p.index.duplicated()]
        base = self.part_.base_[h]
        return p.reindex(subs["career_key"]).fillna(base).to_numpy()

    def p_play_signed(self, iset, keys, horizons, dates) -> dict:
        """The chance of playing for each (player, date) row, contract state
        read at that row's DATE (a contract's signing) instead of 1 July of the
        page. Horizons past the fitted range follow predict_beyond_fit's rule.
        Returns {h: array aligned with `keys`}."""
        keys = list(keys)
        dates = pd.to_datetime(np.asarray(dates))
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP],
                     self.N_SEASONS, self.decay_)
        a = a[a["t0"] == iset.t0].drop_duplicates("career_key").set_index("career_key")
        rows = a.reindex(keys).reset_index()
        fitted = sorted(getattr(self, "fitted_horizons_", None) or self.FITTED_HORIZONS)
        out = {}
        for h in sorted({int(x) for x in horizons}):
            hh = h if h in fitted else fitted[-1]
            base = self.part_.base_[hh]
            p = self._part_predict(rows, hh, as_of=dates).to_numpy(float)
            p = np.where(np.isfinite(p), p, base)
            if h not in fitted:
                _g_prod, g_play = self._tail_decay(iset, fitted[-1], fitted[-2])
                p = np.clip(p * g_play ** (h - fitted[-1]), 0.005, 0.995)
            out[h] = p
        return out

    # ---- horizons past the fitted range --------------------------------------
    def _guard_horizons(self, horizons) -> None:
        """Refuse a horizon this page never fitted (use predict_beyond_fit)."""
        fitted = getattr(self, "fitted_horizons_", None)
        if fitted is None:
            fitted = self.FITTED_HORIZONS
        missing = sorted({int(h) for h in horizons} - set(fitted))
        if missing:
            raise ValueError(
                f"{self.name} was asked for horizon(s) {missing} but is fitted only to "
                f"{sorted(fitted)}; use predict_beyond_fit for the declared extension.")

    def predict_beyond_fit(self, iset, subs, horizons) -> pd.DataFrame:
        """Forecast past the fitted range by continuing the league-wide decay
        between the last two fitted seasons: the decay of the PRODUCT measured
        on a fixed reference population, split so participation keeps its own
        observed rate and the rate carries the rest. Games share is carried
        forward. Every extrapolated row is tagged. Known to overstate mildly
        (+3% to +20% one to three seasons past the range, ability_forecast)."""
        fitted = sorted(getattr(self, "fitted_horizons_", None) or self.FITTED_HORIZONS)
        want = sorted(int(h) for h in horizons)
        inside = [h for h in want if h in fitted]
        beyond = [h for h in want if h not in fitted]
        if beyond and len(fitted) < 2:
            raise ValueError(f"{self.name} needs two fitted horizons to measure a decay rate")
        need = sorted(set(inside) | ({fitted[-1]} if beyond else set()))
        full = self.predict(iset, subs, need)
        full["extrapolated"] = 0.0
        out = full[full["h"].isin(inside)].copy()
        if beyond:
            g_prod, g_play = self._tail_decay(iset, fitted[-1], fitted[-2])
            g_rate = float(np.clip(g_prod / g_play, 0.5, 1.05))
            last = full[full["h"] == fitted[-1]]
            for h in beyond:
                k = h - fitted[-1]
                nxt = last.copy()
                nxt["h"] = h
                nxt["rate_82"] = last["rate_82"] * g_rate ** k
                nxt["p_play"] = (last["p_play"] * g_play ** k).clip(0.005, 0.995)
                nxt["extrapolated"] = 1.0
                out = pd.concat([out, nxt], ignore_index=True)
        return out

    def _tail_decay(self, iset, hmax: int, prev: int):
        """League-wide decay between two fitted horizons, on the harness's
        reference population, cached per page."""
        key = (int(iset.t0), int(hmax), int(prev))
        cache = getattr(self, "_decay_cache", None)
        if cache is None:
            cache = self._decay_cache = {}
        if key not in cache:
            import forecast_harness as _H          # lazy, to avoid a cycle
            ref = _H.subjects_at(iset)
            p = self.predict(iset, ref, [prev, hmax])
            a, b = p[p["h"] == prev], p[p["h"] == hmax]
            war = lambda x: (x["p_play"] * x["rate_82"] * x["gp_share"]).mean()
            cache[key] = (
                float(np.clip(war(b) / war(a), 0.5, 1.0)),
                float(np.clip(b["p_play"].mean() / a["p_play"].mean(), 0.5, 1.0)))
        return cache[key]
