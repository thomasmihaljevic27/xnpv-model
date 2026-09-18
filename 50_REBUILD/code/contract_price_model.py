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

SCRIPT_VERSION = "1.4"


def contract_sample(positions: tuple = ("F", "D")) -> pd.DataFrame:
    """Standard-level contracts with a usable price and signing date.

    `positions` selects which position group the sample covers. The default
    is the skaters this model was built for; the goalie branch passes ("G",)
    rather than carrying a second copy of the census, the cap-share
    denominator, the floor and the signing-date rules, all of which are the
    same question asked of a different set of players.
    """
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
          & c["pkey"].str.endswith(tuple("|" + p for p in positions))]
    c = c[c["start_yr"].between(2015, 2025) & c["signed"].notna()]
    # THE DENOMINATOR HAS TO BE KNOWABLE AT THE SIGNING TOO. Dating the fit at
    # the signing while dividing by the REALISED start-year ceiling leaves
    # future cap information in the target itself: an extension signed in
    # January 2019 for a 2019 start entered training under its own signing
    # date while its denominator was a ceiling not yet announced. The fix uses
    # the start-year ceiling as it was knowable on the signing date, which for
    # a deal signed the summer before the start is the published figure and for
    # an early extension is the 3% extrapolation.
    # A SIGNING THAT PREDATES THE CAP TABLE CANNOT BE PRICED THIS WAY. The
    # earliest ceiling on record is the 2015-16 one, announced in June 2015, so
    # a deal signed in November 2014 for a 2015 start genuinely did not know its
    # own denominator. That is a real information constraint rather than an
    # artifact, and inventing a pre-2015 ceiling to get around it would be
    # inventing the very number the constraint is about. The 31 affected
    # contracts, 0.9% of the eligible sample and all 2015 starts, are dropped
    # and counted. Adding the published pre-2015 ceilings to CAP_CEILING from
    # source would return them.
    first_known = pd.Timestamp(f"{min(C.CAP_CEILING)}-07-01")
    n_pre = int((c["signed"] < first_known).sum())
    if n_pre:
        C.log(f"  {n_pre} contracts signed before {first_known.date()} dropped: "
              "the cap ceiling for their start year had not been announced and "
              "this table holds no earlier one to project from")
    c = c[c["signed"] >= first_known]
    known_ceiling = np.array([
        C.cap_path(sg, [int(sy)])[int(sy)]
        for sg, sy in zip(c["signed"], c["start_yr"])])
    c["cap_ceiling_at_signing"] = known_ceiling
    c["cap_share"] = c["aav"] / known_ceiling
    # The censoring point: no contract prices below the league minimum, so the
    # bottom of the distribution is a pile-up at the floor rather than a tail.
    c["floor_share"] = c["start_yr"].map(C.LEAGUE_MIN_SALARY) / known_ceiling
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
    # Contracts the forecast cannot cover, kept so the loss is reportable
    # rather than a silent thinning of the sample in the join at the end.
    rejected: list[dict] = []
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
        # NO CEILING ON THE REQUEST. This used to stop at horizon eight, so a
        # term reaching nine was never asked about, then failed the full-term
        # requirement below and vanished in the join with no record. The model
        # refuses or extrapolates a horizon on its own terms; clipping the
        # question here decided for it, invisibly. Negative offsets are still
        # excluded: a season before the valuation is not a forecast.
        hs = sorted({int(s - t0) for r in grp.itertuples()
                     for s in range(int(r.start_yr), int(r.end_yr) + 1)
                     if s - t0 >= 0})
        if not hs:
            continue
        # A contract can outrun what its own page supports. predict() refuses
        # an unfitted horizon; this is the declared path that carries the last
        # fitted season forward, and it tags what it extrapolated.
        pred = model.predict_beyond_fit(iset, subs, hs)
        pred = pred.merge(subs[["career_key", "pkey"]], on="career_key", how="left")
        pred["war"] = pred["p_play"] * pred["rate_82"] * pred["gp_share"]
        lut = pred.set_index(["pkey", "h"])["war"]

        ex = pred.set_index(["pkey", "h"])["extrapolated"]
        for r in grp.itertuples():
            hh = [int(s - t0) for s in range(int(r.start_yr), int(r.end_yr) + 1)]
            vals = [lut.get((r.pkey, x), np.nan) for x in hh]
            # THE WHOLE TERM, OR NOTHING. This used to clip the horizon list at
            # eight and then drop whatever came back missing, so a contract
            # could be priced on part of itself and reported as though it were
            # priced on all of it. A player the batch cannot answer for is
            # skipped entirely, which is visible; a term silently shortened is
            # not.
            if not all(np.isfinite(v) for v in vals):
                # RECORDED, not merely skipped. A contract dropped here
                # disappears in the join below, so without this the sample
                # silently loses exactly the terms the model cannot cover.
                rejected.append({"idx": r.Index, "pkey": r.pkey, "page": t0,
                                 "term": len(hh),
                                 "reason": "no forecast for every season of the term"})
                continue
            n_ex = int(sum(float(ex.get((r.pkey, x), 0.0)) for x in hh))
            out.append({"idx": r.Index, "war_total": float(np.sum(vals)),
                        "war_per_season": float(np.mean(vals)),
                        "war_year1": float(vals[0]), "n_years_forecast": len(vals),
                        # Carried so a dollar total can say how much of itself
                        # came from beyond the fitted range.
                        "n_years_extrapolated": n_ex})
        if verbose:
            C.log(f"  batch readable-through {L}: {len(grp)} contracts")

    # THE REJECTIONS ARE PUBLISHED BEFORE THE JOIN, and the empty case is built
    # with its schema rather than inferred from rows that do not exist. When
    # every submitted contract was rejected, `out` was empty, set_index("idx")
    # raised a KeyError, and the caller got neither a result nor the rejection
    # report this function had just promised. An empty batch is an ordinary
    # no-history outcome, not an error.
    cols = ["war_total", "war_per_season", "war_year1", "n_years_forecast",
            "n_years_extrapolated"]
    f = (pd.DataFrame(out).set_index("idx") if out
         else pd.DataFrame(columns=cols, index=pd.Index([], name="idx")))
    attach_forecasts.rejected_ = pd.DataFrame(rejected)
    joined = sample.join(f, how="inner")
    if rejected:
        rej = pd.DataFrame(rejected)
        C.log(f"  {len(rej)} contracts dropped for want of a full-term forecast "
              f"(longest {int(rej['term'].max())} seasons); written to "
              "attach_forecasts_rejected.csv")
        rej.to_csv(C.out_path("attach_forecasts_rejected.csv"), index=False)
    return joined


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
