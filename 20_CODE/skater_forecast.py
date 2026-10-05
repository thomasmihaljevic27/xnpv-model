"""skater_forecast.py -- xNPV 1, the skater forecast production values contracts on.

PRODUCTION (20_CODE). Decision D33 (2026-09-30) adopted this model; its one
confirmatory run on the 2022-2025 pages passed (season-WAR RMSE 0.9001 against
xNPV 0's 0.9724, lower in 2,000 of 2,000 player resamples, 2026-10-02, on the
rebuilt age table). Promoted 2026-10-02 from the rebuild tree, where it was
`star_candidates.XNPV1` ("Model 6"): `candidate(gp=True, contracts=True)` on
`obvious_fixes.ObviousFixes` on `ability_forecast.A1HingeExposure`.

v2.2 (2026-10-05): investigations D2 (age squared in the games-share line) and
E1 (the before-2018 marker in the chance of playing), adopted by Thomas on
25_TESTS/games_playing_followup.py. v2.1 is at a61b607.
v2.1 (2026-10-05): investigations A1 (a yardstick per position, aging_curve),
C2 (returners are not departures) and C6 (a departed season at his own games),
adopted by Thomas on 25_TESTS/aging_abc_followup.py. v2.0 is at 669198b.
v2.0 (2026-10-05, branch claude/amazing-einstein-tk4b08): THE DIRECTED FORECAST.
Thomas's directives 1-3 and the build rules in 00_STATE/MODEL_DIRECTIVES.md
replace the fitted start and the fitted decay. PROVISIONAL: the price line
(XNPV1_RATE), the qualify rates and WAR_IF_PLAYS_MAE below were all measured
on the v1.x forecast and are re-measured at the plan of record's step 6; the
2022-2025 confirmation above was run on v1.x, not on this. The v1.x forecast is
in git at 2bc0399 and before.

WHAT IT FORECASTS, for a player valued at page t0 and each season h ahead
(h = 0 is the valuation season itself, which has not been played on 1 July):
    rate_82   WAR per 82 games if he plays
    gp_share  the share of his team's games he plays, if he plays
    p_play    the chance he plays at all that season (one game or more)
    so expected WAR = p_play x rate_82 x gp_share, and the WAR if he plays is
    rate_82 x gp_share.

HOW, step by step (v2.0; MODEL_DIRECTIVES.md entries 1-3 and build rules):
    1. THE START, no fitted line. 65% x his own rate per 82 (own_82: the
       seasons t0-1, t0-2, t0-3 weighted 50/30/20, each weight times that
       season's games, 10+ game seasons only, rescaled over the ones he has)
       + 35% x his comparable players' level at the age of his last counted
       season (aging_curve, blended with the league level at weight ten),
       + the curve's change from that age to the valuation season. (v1.x: a
       trailing total with a fitted decay, pulled by an eight-term fitted line.)
    2. THE AGING WALK. The comparable-player curve, 20_CODE/aging_curve.py
       (level games-weighted 50/30/20 by age, directive 2), fitted on seasons
       before the page. Its changes are ADDED to the start (not multiplied).
       One match, at his last counted age, gives the step to the valuation
       season and every later change; with no 20-game profile there, the
       league-average changes (XNPV1._path; v1.x read his profile one season
       before the valuation season, else two). Players who left the league
       enter the curve at replacement level for the season they missed
       (imputed_aging_model). No replacement floor is applied to a negative
       start (D12 v3 is superseded for skaters by D33).
    3. THE GAMES SHARE. A fitted line per horizon on the trailing share,
       position, experience, age, age squared (v2.2) and the trailing WAR total
       (GP_FEATURES; plain 50/30/20), capped at 1.0 and floored at 0.05. The
       total-above-one-win term was dropped in v2.0.
    4. THE CHANCE OF PLAYING. participation_model.ParticipationModel (its
       level input: the plain 50/30/20 trailing WAR total), reading
       contract status where the vendor export's coverage is complete
       ("observable"), with the before/after-2018 marker (v2.2; left out before). Read at
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
    STALE IN v2.0: measured on the v1.x forecast; re-measured at step 6.
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
import information_set as ISET
from participation_model import ParticipationModel

SCRIPT_VERSION = "2.2"
MODEL_NAME = "xNPV 1"

# DIRECTIVE 1 (Thomas, 2026-10-04): "We are not using fitted decay." Every
# trailing measure weights the three seasons before the valuation season
# 50/30/20 (last season first), rescaled over the 10+ game seasons he has, so a
# missing season is not a zero (detail 4, settled 2026-10-05).
TRAIL_WEIGHTS = (0.5, 0.3, 0.2)
# The start's own-versus-comparables blend (directive 1; directive 3 makes it the
# model's only one): 65% his own rate, 35% his comparable players' level.
K_OWN = 0.65
STALE_LOOKBACK = 3       # matches forecast_harness.ACTIVE_WINDOW
HMAX = C.MAX_HORIZON     # how far the comparables walk is tabulated

# The games-share line's terms. Its level input is the plain 50/30/20 trailing
# WAR TOTAL (Thomas, 2026-10-05, on 25_TESTS/war_input_uniformity_test.py: the
# total beat the rate per 82 on season WAR). The total-above-one-win term
# (`tw_hi1`) was dropped the same day: it helped the share but cost season WAR.
# v2.2: age squared added (`age_c2`, a curved age effect; investigation D2,
# Thomas 2026-10-05, on 25_TESTS/games_and_playing_de.py: season WAR 0.8078
# against 0.8088). The straight line, its cap at 1.0 and floor at 0.05 stay
# (the logistic curve, D1, fitted the share better but cost season WAR).
GP_FEATURES = ["tr_gp_share", "is_D", "exp_seasons", "age_c", "tw_WAR", "age_c2"]

# xNPV 1's own WAR-if-plays misses by season ahead (see the docstring).
WAR_IF_PLAYS_MAE = {0: 0.6730, 1: 0.7486, 2: 0.7991, 3: 0.8516, 4: 0.8792, 5: 0.8926}
MAE_TO_SD = 1.2533       # SD = MAE * sqrt(pi/2) for a normal, production's conversion

MIN_AGE_COVERAGE = 0.99  # the age table must carry the Elite Prospects birthdates


def war_if_plays_sd(k: int) -> float:
    """The spread of the WAR-if-plays k seasons ahead (k = 0 is the valuation
    season), for the expected value of the league-minimum floor."""
    return WAR_IF_PLAYS_MAE[min(max(int(k), 0), max(WAR_IF_PLAYS_MAE))] * MAE_TO_SD


# --------------------------------------------------------------------------- the anchors
def _anchors(played: pd.DataFrame, n_seasons: int = 3,
             decay: float | None = None, stale: bool = True,
             cols: list | None = None, weights=None) -> pd.DataFrame:
    """For every player and every season t0 he could have been valued at, the
    trailing facts from the seasons before t0 only (copied from
    ability_forecast._anchors). Structurally incapable of seeing season t0:
    every part is built by adding a POSITIVE lag to the season it came from.

    WEIGHTS (v2.0). Production uses TRAIL_WEIGHTS, 50/30/20 (no fitted decay,
    directive 1). `decay` (geometric 1, d, d^2, ...) is kept only so the recorded
    tests that compare against the old trailing total can still build it; no
    production call passes it.

    COLUMNS the forecast reads (v2.0):
      own_82       his rate per 82, each season's 50/30/20 weight TIMES its games
                   (directive 1, detail 1): the own side of the start
      tw_WAR       the trailing WAR total, plain weights: the level the games share
                   and the chance of playing read
      tr_gp_share  the trailing games share, plain weights
      age          age at the valuation season; age_last and last_lag: the age at,
                   and seasons back to, his most recent counted season (the curve's
                   step to the valuation season starts there, detail 3)"""
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

    if weights is None and decay is None:
        weights = TRAIL_WEIGHTS[:n_seasons]
    if weights is not None:
        assert len(weights) == n_seasons, (weights, n_seasons)
        w = np.asarray(weights, dtype=float)
    else:                                   # geometric: 1, decay, decay^2 (tests only)
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
    # His most recent counted season: its age (not stepped forward) and how many
    # seasons before t0 it was. The start is measured there and aged to t0.
    out["age_last"] = _first_available(m, "age", lags)
    last_lag = pd.Series(np.nan, index=m.index)
    for lag in reversed(lags):
        last_lag = last_lag.where(m[f"GP_{lag}"].isna(), float(lag))
    out["last_lag"] = last_lag

    def blend(col, games=False):
        """Weighted average over the seasons the player actually has,
        renormalised over what is available. games=True multiplies each
        season's weight by its games (directive 1, detail 1)."""
        vals = np.column_stack([m[f"{col}_{lag}"].to_numpy(float) for lag in lags])
        ok = np.isfinite(vals)
        ww = np.where(ok, w[None, :], 0.0)
        if games:
            gp = np.column_stack([m[f"GP_{lag}"].to_numpy(float) for lag in lags])
            ww = np.where(ok, ww * np.nan_to_num(gp), 0.0)
        tot = ww.sum(axis=1)
        num = np.where(ok, np.nan_to_num(vals) * ww, 0.0).sum(axis=1)
        return np.where(tot > 0, num / np.where(tot > 0, tot, 1.0), np.nan)

    for c in cols:
        out["tw_" + c] = blend(c)              # trailing weighted TOTAL
        out["tr_" + c] = blend(c + "_82")      # trailing weighted RATE (plain)
    out["tr_gp_share"] = blend("gp_share")
    out["own_82"] = blend("WAR_82", games=True) if "WAR" in cols else np.nan

    # Evidence behind the anchor, in games; NOT renormalised, so a short
    # history counts as less evidence.
    gp = np.column_stack([m[f"GP_{lag}"].fillna(0).to_numpy(float) for lag in lags])
    out["exposure_gp"] = (gp * w[None, :]).sum(axis=1) / w.sum()
    out["stale_history"] = 0.0

    # Returning players: an anchor from the most recent qualifying season alone
    # when the window holds none, tagged, added only where missing. (Never runs
    # at three seasons, production's window.)
    if stale and n_seasons < STALE_LOOKBACK:
        deep = _anchors(played, STALE_LOOKBACK, decay, stale=False, cols=cols)
        have = pd.MultiIndex.from_arrays([out["career_key"], out["t0"]])
        want = pd.MultiIndex.from_arrays([deep["career_key"], deep["t0"]])
        add = deep[~want.isin(have)].copy()
        if len(add):
            add["stale_history"] = 1.0
            out = pd.concat([out, add], ignore_index=True)

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
    finished before the page, gets an imputed next level: the curve's own level
    rule (aging_curve.level_at, directive 2: games-weighted 50/30/20) with the
    missing season entered at rate 0 and HIS OWN games at age a (C6; v2.0 used
    82). Until v2.0 it was (rate + 0) / 2, the old two-season average. The
    league-average changes are recomputed with the imputed changes included. A
    player who played at a+1 under 20 games is NOT a departure, and since v2.1
    neither is one who appears again at a later age before the page (C2: he
    came back). Investigations C2 and C6, Thomas 2026-10-05; equal to
    25_TESTS/aging_investigations_abc.curve_variant(returners_filled=False,
    gp_rule="own")."""
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
            # C2: the oldest age at which he appears in the NHL before the page
            last_age = df.groupby("career")["age"].max().astype(int).to_dict()
            self.n_imputed = 0
            imputed = {}
            for name, p in self.players.items():
                byage = {s["age"]: s for s in p["seasons"]}
                for s in p["seasons"]:
                    a = s["age"]
                    if (a + 1) in p["sm"] or (name, a + 1) in present:
                        continue                      # he played at a+1 (any games)
                    sy = syr_of.get((name, a))
                    if sy is None or sy + 1 >= int(before):
                        continue                      # the next season is not over yet
                    if last_age.get(name, a) > a + 1:
                        continue                      # C2: he came back later; not a departure
                    b2 = dict(byage)
                    b2[a + 1] = {"w82": 0.0, "gp": float(s["gp"])}   # C6: his own games
                    nxt = AC.level_at(b2, a + 1)
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
    FITTED_HORIZONS = C.FITTED_HORIZONS
    CONTRACT_STATE = "observable"
    # v2.2: nothing excluded. Under "observable", `contract_unknown` is 1 exactly
    # for seasons before the export's first end year (2018): the before/after-2018
    # marker D33 left out, put back by investigation E1 (Thomas 2026-10-05: season
    # WAR 0.8085 against 0.8088, MAE 0.4653 against 0.4673). It can enter a fit
    # only from the 2019 page on (earlier pages have no training season from 2018).
    PART_EXCLUDE = ()
    _curves: dict = {}      # one comparables curve per page, shared across instances

    # ---- fit -----------------------------------------------------------------
    def fit(self, table: pd.DataFrame, before: int) -> "XNPV1":
        self.before = before
        self.fitted_horizons_ = None
        pairs = self._training_pairs(table, before, C.CANDIDATE_HORIZONS)

        # 1. The start needs no fitted line (directive 1). Its fallback when he
        # has no age: the league's games-weighted rate per 82 for his position
        # group, from 10+ game seasons before the page.
        q = table[(table["GP"] >= C.MIN_GP) & (table["syr"] < before)]
        grp = np.where(q["pos"] == "D", "D", "F")
        self.league_rate_ = {g: float(np.sum(x["WAR_82"] * x["GP"]) / np.sum(x["GP"]))
                             for g, x in q.assign(_g=grp).groupby("_g")}

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
        n = self.N_SEASONS
        self.part_ = ParticipationModel(
            contracts, exclude=tuple(self.PART_EXCLUDE),
            contract_state=self.CONTRACT_STATE).fit(
            table, before, anchors_fn=lambda p: _anchors(p, n),
            horizons=self.fitted_horizons_)

        # 2. The comparable-player curve for this page.
        path = war_age_path()
        check_age_coverage(path)
        if before not in self._curves:
            self._curves[before] = imputed_aging_model(str(path), before)
        self.curve_ = self._curves[before]
        self._paths = {}
        return self

    def _record_fitted_horizons(self, pairs: pd.DataFrame) -> None:
        """The horizons this page can carry: those with MIN_HORIZON_PAIRS pairs."""
        n = pairs.dropna(subset=["y_rate"]).groupby("h").size()
        self.fitted_horizons_ = tuple(
            sorted(int(h) for h, k in n.items() if k >= C.MIN_HORIZON_PAIRS))

    def _training_pairs(self, table: pd.DataFrame, before: int, horizons) -> pd.DataFrame:
        """Every (inputs at t, outcome at t+h) pair whose OUTCOME completed
        before `before`, the one place training data is built."""
        s = table[table["GP"] >= C.MIN_GP]
        anchors = _anchors(s, self.N_SEASONS)
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
        a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP], self.N_SEASONS)
        return a[a["t0"] == iset.t0].set_index("career_key").reindex(subs["career_key"])

    def predict(self, iset, subs, horizons) -> pd.DataFrame:
        self._guard_horizons(horizons)
        a = self._page_anchors(iset, subs)
        rows = []
        for h in horizons:
            r = subs.copy()
            r["rate_82"] = self._rate(a, h)
            gp = _apply(self.gp_coef_.get(h), a[GP_FEATURES], a["tr_gp_share"])
            r["gp_share"] = np.clip(gp, 0.05, 1.0)
            r["p_play"] = self._p_play(a, subs, h)
            r["h"] = h
            rows.append(r[["career_key", "h", "rate_82", "gp_share", "p_play"]])
        return pd.concat(rows, ignore_index=True)

    def _path(self, key, pos, age_last, gap):
        """(comparables' level at his last counted age, cumulative change from
        that age for 0 .. gap + HMAX seasons) for one player. The rule Thomas
        took on 2026-10-05 (the tested one, 25_TESTS/aging_level_weights_test
        .curve_paths, line for line):
          - one match, at his LAST COUNTED season's age a, gives both his
            comparables' level (blended with the league level for his position
            and age at weight aging_curve.SHRINK_K) and every change after a;
          - no 20-game profile at a (e.g. his last counted season had 10-19
            games), or no comparables: the league level, and the league-average
            changes for his position by age (a missing age adds 0);
          - past the curve's oldest age: the change is held (the projection
            stops there; v2.0 fixes the tested code's fallback, see below);
          - no age at all: the league rate for his position group, carried flat.
        """
        import aging_curve as AC
        m = self.curve_
        pos = "D" if pos == "D" else "F"
        ck = (key, age_last, gap)
        if ck in self._paths:
            return self._paths[ck]
        n = int(gap) + HMAX
        path = np.zeros(n + 1)
        if not np.isfinite(age_last):
            self._paths[ck] = (self.league_rate_[pos], path)
            return self._paths[ck]
        a = int(age_last)
        cn = m.glevel.get((pos, a), self.league_rate_[pos])
        got = False
        if key in m.players and a in m.players[key]["sm"]:
            try:
                p = m.players[key]; ss = p["seasons"]
                idx = next(q for q, s in enumerate(ss) if s["age"] == a)
                lo = idx if not p["adjacent"].get(a, False) else max(0, idx - (AC.WIN - 1))
                mu, sd = m.stats[p["pos"]]
                tv = ((AC._profile(ss[lo: idx + 1], p["sm"][a]) - mu) / sd) * np.sqrt(m.fw)
                cand, wt = m._weights(tv, p["pos"], a, exclude=key)
                if cand is not None and len(cand):
                    cn = m._shrunk(m.Lser[cand, a - m.AMIN], cand, wt, cn)
                # The walk stops at the curve's oldest age and the change is held
                # from there. Asked to go further, AgingModel.project indexes past
                # its age table and raises IndexError; the tested code caught that
                # and fell back to the league path for the whole player, which is
                # not the stated rule (found by 25_TESTS/directed_build_check.py,
                # 2026-10-05: it hit only players walked past the oldest age).
                hz = max(0, min(n, m.AMIN + m.nages - a))
                tr = m.project(key, current_age=a, horizon=hz)
                lv = dict(zip(tr["age"].astype(int), tr["projected_war_per_82"]))
                base, last = lv[a], 0.0
                for st in range(n + 1):
                    if (a + st) in lv:
                        last = lv[a + st] - base
                    path[st] = last                     # past the curve: held
                got = True
            except (ValueError, KeyError, IndexError, StopIteration):
                got = False
        if not got:
            c = 0.0
            for st in range(n + 1):
                path[st] = c
                c += m.gdelta.get((pos, a + st), 0.0)
        self._paths[ck] = (cn, path)
        return self._paths[ck]

    def _rate(self, a, h):
        """The rate per 82 if he plays, h seasons after the valuation season.
        THE START (directive 1, details 1-4 settled 2026-10-04c/2026-10-05):
            0.65 x own_82 + 0.35 x comparables' level at his last counted age
            + the curve's change from that age to the valuation season (detail 3)
        THE WALK: then the curve's change from the valuation season onward,
        added in rate units. A player with no anchor gets NaN."""
        own = a["own_82"].to_numpy(float)
        out = np.full(len(a), np.nan)
        keys = a.index.to_numpy()
        for i, (pos, al, g) in enumerate(zip(a["pos"].to_numpy(), a["age_last"].to_numpy(float),
                                             a["last_lag"].to_numpy(float))):
            if not np.isfinite(own[i]):
                continue
            cn, path = self._path(keys[i], pos, al, int(g))
            g = int(g)
            start = K_OWN * own[i] + (1 - K_OWN) * cn + path[g]
            out[i] = start + (path[g + min(h, HMAX)] - path[g])
        return out

    # ---- participation -----------------------------------------------------
    @property
    def reads_contracts(self) -> bool:
        return getattr(self.part_, "spans", None) is not None

    def _signed_anchor_frame(self, iset):
        """This page's anchors, one row per career, computed once per page and
        reused (v1.1). The contract engine asks for signing-dated chances of
        playing one contract at a time; recomputing every player's anchors for
        each call is the same frame each time and costs most of the call."""
        memo = getattr(self, "_signed_anchor_memo", None)
        if memo is None or memo[0] is not iset:
            a = _anchors(iset.seasons[iset.seasons["GP"] >= C.MIN_GP], self.N_SEASONS)
            a = a[a["t0"] == iset.t0].drop_duplicates("career_key").set_index("career_key")
            self._signed_anchor_memo = (iset, a)
        return self._signed_anchor_memo[1]

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
        a = self._signed_anchor_frame(iset)
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


# --------------------------------------------------------------------------- for the contract engine
class ContractForecaster:
    """xNPV 1's forecasts, served to the contract engine (contract_npv.py via
    skater_forward_projection.SkaterProjector, and rfa_terminal_value.py).

    One season table for the whole run (production's birthdate rule); one
    xNPV 1 fit per valuation page t0, on seasons before it, with the decision
    date 1 July of t0 -- the date the harness scored and the date a page is
    valued at. For every player with an anchor on the page, the forecast for
    seasons 0..MAX_H ahead is computed once (predict_beyond_fit, so seasons
    past the page's fitted range follow the declared extension) and cached.

    A valuation dated after 1 July (an in-season extension, D28) keeps the
    page's rate and games share and reads the chance of playing with contract
    status at that date (p_play_signed), as the dollar scoring did.

    The key is production's player key (cleaned name + "|" + position group),
    which is the season table's `pkey`; it maps to one career.
    """
    MAX_H = 20

    def __init__(self):
        import player_season_table as PST
        bd, how = PST.birthdate_source()
        C.log(f"  [{MODEL_NAME}] birthdates: {how}")
        self.table = PST.build(birthdate_csv=bd, verbose=False)
        self.career_of = (self.table.drop_duplicates("pkey")
                          .set_index("pkey")["career_key"].to_dict())
        self._pages = {}

    def page(self, t0: int):
        """(model, information set, forecasts indexed by (career_key, h),
        anchors indexed by career_key) for valuation page t0."""
        t0 = int(t0)
        if t0 not in self._pages:
            iset = ISET.build(self.table, ISET.decision_date_for_page(t0), t0=t0)
            m = XNPV1().fit(iset.seasons, before=t0)
            a = m._signed_anchor_frame(iset)
            subs = pd.DataFrame({"career_key": a.index.to_numpy()})
            p = m.predict_beyond_fit(iset, subs, list(range(self.MAX_H + 1)))
            p["war_if_plays"] = p["rate_82"] * p["gp_share"]
            p = p.set_index(["career_key", "h"]).sort_index()
            self._pages[t0] = (m, iset, p, a)
            C.log(f"  [{MODEL_NAME}] page {t0}: fitted through season {max(iset.seasons['syr'])}, "
                  f"{len(a)} players forecast, fitted horizons {m.fitted_horizons_[0]}-"
                  f"{m.fitted_horizons_[-1]}, reads contracts: {m.reads_contracts}")
        return self._pages[t0]

    def forecast(self, pkey: str, t0: int, horizon: int, as_of=None):
        """Seasons 0..horizon ahead for one player, or None when xNPV 1 has no
        anchor for him on this page (no qualifying season in its window).
        Columns: h, rate_82, gp_share, war_if_plays, p_play, extrapolated,
        tw_WAR (the trailing total the start is built from), stale_history."""
        ck = self.career_of.get(pkey)
        if ck is None:
            return None
        if horizon > self.MAX_H:
            raise ValueError(f"horizon {horizon} is past the cached {self.MAX_H}")
        m, iset, p, a = self.page(t0)
        if ck not in a.index:
            return None
        f = p.loc[ck].loc[0:horizon].reset_index()
        if len(f) != horizon + 1 or not np.isfinite(f["war_if_plays"]).all():
            return None
        page_date = pd.Timestamp(ISET.decision_date_for_page(int(t0)))
        if as_of is not None and pd.Timestamp(as_of).normalize() != page_date:
            sig = m.p_play_signed(iset, [ck], list(range(horizon + 1)), [pd.Timestamp(as_of)])
            f["p_play"] = [float(sig[h][0]) for h in f["h"]]
            f["p_play_dated"] = pd.Timestamp(as_of).date().isoformat()
        else:
            f["p_play_dated"] = page_date.date().isoformat()
        f["tw_WAR"] = float(a.loc[ck, "tw_WAR"])
        f["stale_history"] = float(a.loc[ck, "stale_history"])
        return f

    def write(self, path) -> Path:
        """Every page forecast this run made, for audit, tagged with the model
        and code versions."""
        import participation_model as PM
        frames = [p.reset_index().assign(page=t0) for t0, (_, _, p, _) in sorted(self._pages.items())]
        d = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        d["model"] = MODEL_NAME
        d["skater_forecast_version"] = SCRIPT_VERSION
        d["participation_model_version"] = PM.SCRIPT_VERSION
        d.to_csv(path, index=False)
        return Path(path)
