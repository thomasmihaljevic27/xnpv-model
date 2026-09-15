"""contract_price_model.py -- what a player signs for, and what production is worth.

EXPERIMENTAL (50_REBUILD). Rebuild plan Phase 4.

TWO MODELS, KEPT APART
    The CONTRACT PRICE model predicts what a player actually signs for. Term
    and rights belong in it, because they are part of how a deal gets priced.
    The PRODUCTION CURRENCY prices forecast production under a declared
    reference market. They answer different questions and mixing them is how a
    term premium ends up inside a player's production value.

EVERY REGRESSOR IS DATED AT THE SIGNING
    Not at the contract start. The locked market sample dates contracts by
    start season and reads the two prior seasons, and the audit found 30% of it
    was signed before those seasons were complete -- rising to 58% at 3+ wins,
    because the best players re-sign early. On this sample, 596 of 3,550 deals
    (16.8%) were signed before the prior season was readable. Dating at the
    start hands those contracts an anchor built from games that had not been
    played when the pen moved, and the players it flatters most are the
    expensive ones.

    Here each contract's forecast is built from an information set frozen at
    its own signing date, through the same machinery every other forecast in
    this tree uses. Contracts are batched by which seasons were readable when
    they were signed, which is the only thing that varies.

WHAT IS NOT CLAIMED
    Term and rights coefficients are conditional associations, not causal
    prices. A seven-year deal is signed by a different sort of player than a
    one-year deal, and no regression here separates the price of term from the
    selection into term.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_config as C
import information_set as ISET
from contract_source import load_contracts, POSGRP
from player_season_table import norm_name, build as build_table

SCRIPT_VERSION = "1.0"


def contract_sample() -> pd.DataFrame:
    """Skater standard-level contracts with a usable price and signing date."""
    con, _ = load_contracts()
    c = con.copy()
    c["pkey"] = ((c["first_name"].astype(str).str.strip() + " "
                  + c["last_name"].astype(str).str.strip()).map(norm_name)
                 + "|" + c["position"].map(POSGRP).astype(str))
    c["end_yr"] = pd.to_numeric(
        c["contract_end"].astype(str).str.extract(r"^(\d{4})")[0], errors="coerce")
    c["start_yr"] = c["end_yr"] - c["length"] + 1
    c["signed"] = pd.to_datetime(c["signing_date"], errors="coerce")
    c = c[(c["contract_level"] == "standard_level")
          & c["signing_status"].isin(["UFA", "RFA"])
          & c["pkey"].str.endswith(("|F", "|D"))]
    c = c[c["start_yr"].between(2015, 2025) & c["signed"].notna()]
    c["cap_share"] = c["aav"] / c["start_yr"].map(C.CAP_CEILING)
    # The censoring point: no contract prices below the league minimum, so the
    # bottom of the distribution is a pile-up at the floor rather than a tail.
    c["floor_share"] = (c["start_yr"].map(C.LEAGUE_MIN_SALARY)
                        / c["start_yr"].map(C.CAP_CEILING))
    c = c[c["cap_share"].notna() & c["floor_share"].notna()]
    c["is_RFA"] = (c["signing_status"] == "RFA").astype(float)
    c["is_D"] = c["pkey"].str.endswith("|D").astype(float)
    # Which seasons were readable when the pen moved.
    c["latest_complete"] = [max(ISET.seasons_complete_at(d.date()))
                            for d in c["signed"]]
    return c.reset_index(drop=True)


def attach_forecasts(sample: pd.DataFrame, model_cls, table: pd.DataFrame,
                     verbose: bool = True) -> pd.DataFrame:
    """For every contract, the forecast production over its term, built only
    from what was readable at the signing.

    Batched by `latest_complete`, the last season readable at the signing,
    because that is the only thing that changes the information set. Within a
    batch every contract sees the same seasons and the model is fitted once.
    """
    import forecast_harness as H

    out = []
    for L, grp in sample.groupby("latest_complete"):
        t0 = int(L) + 1
        if t0 < C.FIRST_SOURCE_SEASON + 3:
            continue
        iset = ISET.build(table, ISET.decision_date_for_page(t0), t0=t0)
        model = model_cls()
        # Rolling: fitted only on outcomes completed before the valuation
        # season this batch stands at.
        model.fit(iset.seasons, before=t0)
        subs = H.subjects_at(iset)
        if subs.empty:
            continue
        # Horizons needed: from the contract's first season to its last,
        # measured from t0. A deal signed a year early reaches further out.
        hs = sorted({int(s - t0) for r in grp.itertuples()
                     for s in range(int(r.start_yr), int(r.end_yr) + 1)
                     if 0 <= s - t0 <= 8})
        if not hs:
            continue
        pred = model.predict(iset, subs, hs)
        pred = pred.merge(subs[["career_key", "pkey"]], on="career_key", how="left")
        pred["war"] = pred["p_play"] * pred["rate_82"] * pred["gp_share"]
        lut = pred.set_index(["pkey", "h"])["war"]

        for r in grp.itertuples():
            hh = [int(s - t0) for s in range(int(r.start_yr), int(r.end_yr) + 1)]
            vals = [lut.get((r.pkey, x), np.nan) for x in hh if 0 <= x <= 8]
            vals = [v for v in vals if np.isfinite(v)]
            if not vals:
                continue
            out.append({"idx": r.Index, "war_total": float(np.sum(vals)),
                        "war_per_season": float(np.mean(vals)),
                        "war_year1": float(vals[0]), "n_years_forecast": len(vals)})
        if verbose:
            C.log(f"  batch readable-through {L}: {len(grp)} contracts")

    f = pd.DataFrame(out).set_index("idx")
    return sample.join(f, how="inner")


# ---------------------------------------------------------------------------
# Censored (Tobit) fit
# ---------------------------------------------------------------------------
def tobit(X: np.ndarray, y: np.ndarray, floor: np.ndarray):
    """Left-censored normal MLE.

    Contracts cannot price below the league minimum, so the observations at
    the floor are censored rather than measured: the market wanted to pay that
    player less and could not. Ordinary least squares would read the pile-up as
    genuine and flatten the slope on everyone.
    """
    Xc = np.column_stack([np.ones(len(y)), X])
    cens = y <= floor + 1e-12

    def nll(p):
        b, ls = p[:-1], p[-1]
        sd = np.exp(np.clip(ls, -10, 5))
        mu = Xc @ b
        ll = np.empty(len(y))
        ll[~cens] = stats.norm.logpdf(y[~cens], mu[~cens], sd)
        ll[cens] = stats.norm.logcdf((floor[cens] - mu[cens]) / sd)
        return -np.sum(ll)

    start = np.append(np.linalg.lstsq(Xc, y, rcond=None)[0], np.log(y.std() + 1e-6))
    res = optimize.minimize(nll, start, method="L-BFGS-B",
                            options={"maxiter": 800})
    return res.x[:-1], float(np.exp(res.x[-1])), bool(res.success)


def predict_tobit(coef, X):
    return np.column_stack([np.ones(len(X)), X]) @ coef
